from typing import Any, List, Dict, Optional, Tuple, Deque
from collections import deque
import os
import time
import requests
import logging
import json
import sys
import importlib
import base64
import threading
from pathlib import Path
from http import HTTPStatus
from concurrent.futures import ThreadPoolExecutor, as_completed
import tempfile
import signal
import hashlib

import numpy as np

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


_EMBED_MODEL = os.getenv("EMBED_MODEL", "codet5p").lower()
_EMBED_SIM_THRESHOLD = float(os.getenv("EMBED_SIM_THRESHOLD", "0.60"))
_FETCH_FULL_CONTENT = os.getenv("API_CODE_SEARCH_FETCH_FULL_CONTENT", "0").lower() in {"1", "true", "yes", "on"}

# --------------------------------------------------------------------------- #
# Global secondary-limit cooldown. GitHub's secondary limits are per-IP, so a
# single 429/403 throttles every request from this process regardless of which
# token is used. We remember the cooldown deadline globally so that requests
# arriving right after a rate-limit do NOT fire immediately and re-trigger the
# escalating backoff (2s -> 1s -> 735s observed earlier).
# --------------------------------------------------------------------------- #
_SECONDARY_LOCK = threading.Lock()
_SECONDARY_BLOCKED_UNTIL = 0.0        # epoch seconds; all GitHub calls wait until then
_SECONDARY_CONSECUTIVE_HITS = 0       # consecutive rate-limit hits since last success


def _secondary_wait() -> float:
    """Return how many seconds to sleep (0 if none) before the next GitHub call.

    Central gate so a rate-limit backoff applies to ALL callers, not just the
    one that hit the limit.
    """
    global _SECONDARY_BLOCKED_UNTIL
    with _SECONDARY_LOCK:
        remaining = _SECONDARY_BLOCKED_UNTIL - time.time()
        if remaining <= 0:
            return 0.0
        return remaining + 1.0  # n+1 strict


def _secondary_mark_blocked(wait_seconds: float) -> None:
    """Record a secondary-limit backoff deadline (n+1 strict, shared globally)."""
    global _SECONDARY_BLOCKED_UNTIL, _SECONDARY_CONSECUTIVE_HITS
    with _SECONDARY_LOCK:
        _SECONDARY_BLOCKED_UNTIL = time.time() + wait_seconds + 1.0
        _SECONDARY_CONSECUTIVE_HITS += 1
    logger.warning("Secondary-limit backoff set: %.0fs (consecutive hits=%d)",
                   wait_seconds + 1.0, _SECONDARY_CONSECUTIVE_HITS)


def _secondary_mark_success() -> None:
    global _SECONDARY_CONSECUTIVE_HITS
    with _SECONDARY_LOCK:
        _SECONDARY_CONSECUTIVE_HITS = 0


# --------------------------------------------------------------------------- #
# Global serialization. Only ONE GitHub HTTP request may be in flight at any
# moment, regardless of how many callers/threads/processes share this module
# (single token + IP-based secondary limits -> no point in concurrency).
# --------------------------------------------------------------------------- #
_GITHUB_REQUEST_LOCK = threading.Lock()
# Minimum spacing between two GitHub calls (seconds). Keeps the request rate
# low and smooth so the IP never bursts past the secondary-limit threshold.
_MIN_REQUEST_INTERVAL = float(os.getenv("GITHUB_MIN_REQUEST_INTERVAL", "2.0"))
_LAST_REQUEST_AT = 0.0


def _acquire_github_slot() -> None:
    """Serialize every GitHub call: hold a global lock AND pace requests.

    Only returns once it is safe to fire one HTTP request to GitHub.
    """
    global _LAST_REQUEST_AT
    # 1) Strict mutual exclusion: no two GitHub calls in parallel anywhere.
    _GITHUB_REQUEST_LOCK.acquire()
    # 2) Pacing: ensure at least GITHUB_MIN_REQUEST_INTERVAL s between calls.
    with _SECONDARY_LOCK:
        elapsed = time.time() - _LAST_REQUEST_AT
        if elapsed < _MIN_REQUEST_INTERVAL:
            wait = _MIN_REQUEST_INTERVAL - elapsed
            # release lock while sleeping so we don't stall the cooldown gate?
            # No: we keep the lock held to guarantee strict serialization.
        else:
            wait = 0.0
    if wait > 0:
        time.sleep(wait)
    with _SECONDARY_LOCK:
        _LAST_REQUEST_AT = time.time()


def _release_github_slot() -> None:
    _GITHUB_REQUEST_LOCK.release()


def _token_fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:8]


class GitHubCodeSearcher:
    """Execute GitHub Code Search queries via REST API.
    
    This class claims a single exclusive token via file-based locking.
    Each instance locks exactly one token, preventing concurrent use by multiple processes.
    Lock files are created atomically and cleaned up when the instance is released.
    
    A single module-level instance is created and reused for all operations.
    """
    
    API_BASE = os.getenv("GITHUB_API_BASE", "https://api.github.com")
    LOCK_DIR = "/tmp"
    LOCK_PREFIX = "i_use_this_token_"
    LOCK_SUFFIX = ".tmp"
    REQUESTS_PER_MINUTE = int(os.getenv("GITHUB_TOKEN_RPM_LIMIT", "30"))
    REQUEST_WINDOW_SECONDS = 60.0
    _request_history_lock = threading.Lock()
    _request_history_by_token: Dict[str, Deque[float]] = {}

    def __init__(
        self,
        token: Optional[str] = None,
        per_page: int = 100,
        token_file: Optional[str] = None,
        enable_token_lock: bool = True,
    ):
        # Guard: prevent re-initialization on subsequent calls to __init__
        if hasattr(self, '_initialized') and self._initialized:
            logger.debug("GitHubCodeSearcher already initialized, skipping re-init")
            return
        
        self._initialized = True
        self._preferred_token = token.strip() if token and token.strip() else None
        
        self._token_pool = self._load_token_pool(token, token_file)
        
        if not self._token_pool:
            raise ValueError("No GitHub tokens available. Provide tokens in config or environment.")
        
        self._enable_token_lock = enable_token_lock
        self._lock_file_path: Optional[str] = None

        if self._enable_token_lock:
            # Clean stale locks from dead processes on initialization
            self._cleanup_stale_locks()

            # Claim exclusive token via file locking
            self._token_idx = self._claim_token_lock()
            self._claimed_token = self._token_pool[self._token_idx]
            self._lock_file_path = self._get_lock_file_path(self._token_idx)
        else:
            if self._preferred_token and self._preferred_token in self._token_pool:
                self._token_idx = self._token_pool.index(self._preferred_token)
                self._claimed_token = self._preferred_token
            else:
                self._token_idx = 0
                self._claimed_token = self._token_pool[0]
        
        self.per_page = per_page
        logger.info(
            "GitHubCodeSearcher[PID=%d] claimed token #%d (fingerprint=%s, lock: %s)",
            os.getpid(),
            self._token_idx,
            _token_fingerprint(self._claimed_token),
            self._lock_file_path,
        )

    def _load_token_pool(self, explicit_token: Optional[str], token_file: Optional[str]) -> List[str]:
        pool: List[str] = []

        if token_file:
            file_path = Path(token_file)
            if file_path.exists():
                try:
                    with file_path.open("r", encoding="utf-8") as fh:
                        for line in fh:
                            token = line.strip()
                            if not token or token.startswith("#"):
                                continue
                            pool.append(token)
                except Exception as exc:
                    logger.warning("Failed to read token pool file %s: %s", token_file, exc)

        if explicit_token and explicit_token.strip():
            pool.append(explicit_token.strip())

        env_token = os.getenv("GITHUB_TOKEN")
        if env_token:
            for t in env_token.split(","):
                t = t.strip()
                if t:
                    pool.append(t)

        tokens_env = os.getenv("GITHUB_TOKENS")
        if tokens_env:
            for t in tokens_env.split(","):
                t = t.strip()
                if t:
                    pool.append(t)

        # Keep order, remove duplicates.
        deduped = list(dict.fromkeys([t for t in pool if t]))
        if deduped:
            logger.info("Loaded %d GitHub token(s) for API requests", len(deduped))
        return deduped

    @staticmethod
    def _get_lock_file_path(token_idx: int) -> str:
        """Get the lock file path for a given token index."""
        return os.path.join(
            GitHubCodeSearcher.LOCK_DIR,
            f"{GitHubCodeSearcher.LOCK_PREFIX}{token_idx}_pid_{os.getpid()}{GitHubCodeSearcher.LOCK_SUFFIX}"
        )

    @staticmethod
    def _pid_is_alive(pid: int) -> bool:
        """Check if a process with given PID is still running."""
        if pid == os.getpid():
            return True
        try:
            # Send signal 0 (no-op) to check if process exists
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    @staticmethod
    def _cleanup_stale_locks() -> None:
        """Remove lock files from dead processes."""
        try:
            for entry in os.listdir(GitHubCodeSearcher.LOCK_DIR):
                if not entry.startswith(GitHubCodeSearcher.LOCK_PREFIX):
                    continue
                if not entry.endswith(GitHubCodeSearcher.LOCK_SUFFIX):
                    continue
                
                # Extract PID from filename: i_use_this_token_{idx}_pid_{pid}.tmp
                parts = entry.replace(GitHubCodeSearcher.LOCK_PREFIX, "").replace(GitHubCodeSearcher.LOCK_SUFFIX, "").split("_pid_")
                if len(parts) != 2:
                    continue
                
                try:
                    pid = int(parts[1])
                    lock_path = os.path.join(GitHubCodeSearcher.LOCK_DIR, entry)
                    
                    if not GitHubCodeSearcher._pid_is_alive(pid):
                        os.remove(lock_path)
                        logger.debug("Cleaned stale lock file (PID %d): %s", pid, entry)
                except (ValueError, OSError) as e:
                    logger.debug("Could not cleanup lock file %s: %s", entry, e)
        except OSError as e:
            logger.warning("Error cleaning stale locks: %s", e)

    def _claim_token_lock(self, max_attempts: int = 300, wait_per_attempt: float = 0.5) -> int:
        """
        Claim an exclusive token lock via file creation.
        
        Tries token indices 0, 1, 2... until one is available.
        Uses atomic os.open(O_CREAT | O_EXCL) to prevent race conditions.
        Will retry for up to max_attempts * wait_per_attempt seconds.
        
        Args:
            max_attempts: Maximum number of retry attempts
            wait_per_attempt: Seconds to wait between attempts
            
        Returns:
            Token index that was successfully locked
            
        Raises:
            RuntimeError if unable to claim any token within timeout
        """
        start_time = time.time()
        
        for attempt in range(max_attempts):
            for token_idx in range(len(self._token_pool)):
                lock_path = self._get_lock_file_path(token_idx)
                try:
                    # Atomic creation - fails if file already exists
                    fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
                    with os.fdopen(fd, 'w') as f:
                        f.write(f"PID={os.getpid()}\nToken Index={token_idx}\nClaimed at={time.time()}\n")
                    logger.info("Successfully claimed token lock #%d", token_idx)
                    return token_idx
                except FileExistsError:
                    # This token is already locked, try next one
                    continue
                except OSError as e:
                    logger.warning("Error claiming token lock %d: %s", token_idx, e)
                    continue
            
            # All tokens are locked, wait and retry
            elapsed = time.time() - start_time
            logger.debug("All tokens locked, retrying... (attempt %d/%d, elapsed=%.1fs)", 
                        attempt + 1, max_attempts, elapsed)
            time.sleep(wait_per_attempt)
        
        elapsed = time.time() - start_time
        raise RuntimeError(
            f"Unable to claim any token lock after {max_attempts} attempts ({elapsed:.1f}s). "
            f"All {len(self._token_pool)} tokens are in use by other processes."
        )

    def _release_token_lock(self) -> None:
        """Release the claimed token lock by removing the lock file."""
        if not hasattr(self, '_lock_file_path') or self._lock_file_path is None:
            return
        try:
            if os.path.exists(self._lock_file_path):
                os.remove(self._lock_file_path)
                logger.info("Released token lock #%d (PID=%d)", self._token_idx, os.getpid())
        except OSError as e:
            logger.warning("Error releasing token lock: %s", e)

    def __del__(self):
        """Cleanup: release token lock when instance is garbage collected."""
        self._release_token_lock()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit: release token lock."""
        self._release_token_lock()
        return False

    def _headers(self) -> Dict[str, str]:
        """Build request headers with the claimed token."""
        headers = {
            "Accept": "application/vnd.github.v3.text-match+json",
            "User-Agent": "GitHubCodeSearcher/1.0",
        }
        if self._claimed_token:
            headers["Authorization"] = f"token {self._claimed_token}"
        return headers

    def _throttle_token_requests(self, action: str) -> None:
        """Enforce a per-token request cap before hitting GitHub."""
        if not self._claimed_token:
            return

        token_key = _token_fingerprint(self._claimed_token)
        limit = max(1, int(self.REQUESTS_PER_MINUTE))
        window = float(self.REQUEST_WINDOW_SECONDS)

        while True:
            with self._request_history_lock:
                now = time.time()
                history = self._request_history_by_token.setdefault(token_key, deque())

                while history and now - history[0] >= window:
                    history.popleft()

                if len(history) < limit:
                    history.append(now)
                    return

                wait_seconds = max(0.0, window - (now - history[0]) + 1.0)

            logger.info(
                "Token #%d (%s) throttled for %.1fs before %s",
                self._token_idx,
                token_key,
                wait_seconds,
                action,
            )
            logger.warning(
                "Token #%d (%s) RPM limit reached; waiting %.1fs before %s",
                self._token_idx,
                token_key,
                wait_seconds,
                action,
            )
            time.sleep(wait_seconds)

    def _handle_rate_limit(self, resp: requests.Response) -> Optional[int]:
        """
        Check if response indicates rate limiting and extract the exact wait time from GitHub.
        
        Strictly respects GitHub's provided Retry-After or X-RateLimit-Reset headers.
        No guessing or exponential backoff - only use GitHub's precise wait times.
        
        Args:
            resp: GitHub API response
            
        Returns:
            Seconds to wait (from GitHub), or None if not rate-limited
        """
        if resp.status_code == 403:
            remaining = resp.headers.get("X-RateLimit-Remaining")
            reset = resp.headers.get("X-RateLimit-Reset")
            if remaining == "0" and reset:
                try:
                    reset_ts = int(reset)
                    wait = max(0, reset_ts - int(time.time()) + 1)  # +1 second buffer
                    logger.warning("Rate limited (403) - GitHub says wait %d seconds until reset at %d", 
                                  wait, reset_ts)
                    return wait
                except Exception:
                    logger.warning("Rate limited (403) but could not parse X-RateLimit-Reset", exc_info=True)
                    return 60  # Fallback conservative wait
        
        if resp.status_code == 429:
            # 429 Too Many Requests - GitHub is being very explicit about rate limit
            retry_after = resp.headers.get("Retry-After")
            if retry_after:
                try:
                    wait = int(retry_after)
                    logger.warning("Rate limited (429) - GitHub Retry-After: %d seconds", wait)
                    return wait
                except Exception:
                    logger.warning("Rate limited (429) but could not parse Retry-After header", exc_info=True)
            # Fallback if Retry-After is missing
            logger.warning("Rate limited (429) - no Retry-After header, using conservative 60s wait")
            return 60
        
        return None

    def _fetch_file_content(
        self,
        repo_full_name: str,
        file_path: str,
        sha: Optional[str] = None,
    ) -> Optional[str]:
        """Fetch raw file content from GitHub with fallback strategies.
        
        Respects rate limiting with automatic retry after wait.
        """
        # Strategy 1: Try with provided SHA
        # if sha:
        #     url = f"https://raw.githubusercontent.com/{repo_full_name}/{sha}/{file_path}"
        #     try:
        #         resp = requests.get(url, headers=self._headers(), timeout=10)
        #         if resp.status_code == 200:
        #             return resp.text
        #     except Exception:
        #         pass
        
        # Strategy 2: Try with 'main' branch (with rate limit handling)
        for branch in ['main', 'master', 'HEAD']:
            url = f"https://raw.githubusercontent.com/{repo_full_name}/{branch}/{file_path}"
            max_retries = 1
            retry_count = 0
            
            while retry_count <= max_retries:
                try:
                    gate_wait = _secondary_wait()
                    if gate_wait > 0:
                        logger.warning("Global secondary-limit gate: sleeping %.0fs before raw fetch", gate_wait)
                        time.sleep(gate_wait)
                    self._throttle_token_requests(f"raw content fetch for {file_path} ({branch})")
                    _acquire_github_slot()
                    try:
                        resp = requests.get(url, headers=self._headers(), timeout=10)
                    finally:
                        _release_github_slot()
                    if resp.status_code == 200:
                        logger.debug("Fetched from %s branch: %s", branch, file_path)
                        return resp.text
                    
                    # Check for rate limiting
                    wait_seconds = self._handle_rate_limit(resp)
                    if wait_seconds is not None:
                        _secondary_mark_blocked(wait_seconds)
                        logger.warning("Rate limited while fetching %s. Global cooldown n+1=%.0fs...", url, wait_seconds + 1.0)
                        retry_count += 1
                        continue
                    break
                except Exception:
                    break
        
        # Strategy 3: Try GitHub API as last resort (with rate limit handling)
        api_url = f"{self.API_BASE}/repos/{repo_full_name}/contents/{file_path}"
        max_retries = 1
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                gate_wait = _secondary_wait()
                if gate_wait > 0:
                    logger.warning("Global secondary-limit gate: sleeping %.0fs before API fetch", gate_wait)
                    time.sleep(gate_wait)
                self._throttle_token_requests(f"API content fetch for {file_path}")
                _acquire_github_slot()
                try:
                    resp = requests.get(api_url, headers=self._headers(), timeout=10)
                finally:
                    _release_github_slot()
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("content"):
                        import base64
                        content = base64.b64decode(data["content"]).decode('utf-8')
                        logger.debug("Fetched via API: %s", file_path)
                        return content
                
                # Check for rate limiting
                wait_seconds = self._handle_rate_limit(resp)
                if wait_seconds is not None:
                    _secondary_mark_blocked(wait_seconds)
                    logger.warning("Rate limited while fetching API content. Global cooldown n+1=%.0fs...", wait_seconds + 1.0)
                    retry_count += 1
                    continue
                break
            except Exception:
                break
        
        logger.warning("Could not fetch content for %s/%s (tried all strategies)", repo_full_name, file_path)
        return None

    def _fetch_object_url_content(self, object_url: str) -> Optional[str]:
        """Fetch content from GitHub contents API `object_url` and decode base64 content.
        
        Respects rate limiting with automatic retry after wait.
        """
        if not object_url:
            return None

        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                self._throttle_token_requests(f"object content fetch for {object_url}")
                resp = requests.get(object_url, headers=self._headers(), timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    encoded = data.get("content")
                    encoding = data.get("encoding")
                    if encoded and encoding == "base64":
                        cleaned = str(encoded).replace("\n", "")
                        return base64.b64decode(cleaned).decode("utf-8", errors="replace")

                    if isinstance(data.get("download_url"), str) and data["download_url"]:
                        self._throttle_token_requests(f"download fetch for {data['download_url']}")
                        raw_resp = requests.get(data["download_url"], headers=self._headers(), timeout=15)
                        if raw_resp.status_code == 200:
                            return raw_resp.text
                        return None
                    return None
                
                # Check for rate limiting
                wait_seconds = self._handle_rate_limit(resp)
                if wait_seconds is not None:
                    logger.warning("Rate limited while fetching object content. Sleeping for %d seconds...", wait_seconds)
                    time.sleep(wait_seconds)
                    retry_count += 1
                    continue
                if resp.status_code in (500, 502, 503, 504):
                    retry_count += 1
                    if retry_count >= max_retries:
                        logger.warning("Could not fetch object_url %s: status=%s", object_url, resp.status_code)
                        return None
                    backoff = min(2 ** retry_count, 5)
                    logger.warning(
                        "Transient object_url status=%s, retrying (%d/%d) after %ss",
                        resp.status_code,
                        retry_count,
                        max_retries,
                        backoff,
                    )
                    time.sleep(backoff)
                    continue

                logger.warning("Could not fetch object_url %s: status=%s", object_url, resp.status_code)
                return None
                    
            except requests.RequestException as exc:
                retry_count += 1
                if retry_count >= max_retries:
                    logger.warning("Failed to fetch object_url content: %s", exc)
                    return None
                backoff = min(2 ** retry_count, 5)
                logger.warning(
                    "Transient fetch error for object_url (%d/%d): %s",
                    retry_count,
                    max_retries,
                    exc,
                )
                time.sleep(backoff)
                continue
            except Exception as exc:
                logger.warning("Failed to fetch object_url content: %s", exc)
                return None
        
        logger.warning("Retries exhausted for object_url: %s", object_url)
        return None

    def _char_index_to_line_no(self, content: str, char_index: int) -> int:
        """Convert char index to 0-based line number in the full content."""
        idx = max(0, min(char_index, len(content)))
        return content[:idx].count("\n")

    def _merge_line_windows(self, windows: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """Merge overlapping line windows (inclusive intervals)."""
        if not windows:
            return []
        merged: List[Tuple[int, int]] = []
        for start, end in sorted(windows, key=lambda x: x[0]):
            if not merged or start > merged[-1][1] + 1:
                merged.append((start, end))
                continue
            prev_start, prev_end = merged[-1]
            merged[-1] = (prev_start, max(prev_end, end))
        return merged


    def _fallback_snippet_from_text_match(self, text_match: Dict[str, Any]) -> str:
        """Fallback snippet from API text_match fragment when context anchoring fails."""
        if not isinstance(text_match, dict):
            return ""
        return str(text_match.get("fragment", "") or "").strip()

    def _split_fragment_segments(self, fragment: str) -> List[Tuple[str, int, int]]:
        """Split fragment by '\n...\n' while preserving each segment's char range in fragment."""
        text = str(fragment or "")
        delimiter = "\n...\n"
        segments: List[Tuple[str, int, int]] = []

        start = 0
        while True:
            idx = text.find(delimiter, start)
            if idx == -1:
                seg = text[start:]
                if seg.strip():
                    segments.append((seg, start, len(text)))
                break
            seg = text[start:idx]
            if seg.strip():
                segments.append((seg, start, idx))
            start = idx + len(delimiter)

        return segments

    def _segment_for_fragment_index(
        self,
        segments: List[Tuple[str, int, int]],
        fragment_index: int,
    ) -> Optional[Tuple[str, int, int]]:
        for seg_text, seg_start, seg_end in segments:
            if seg_start <= fragment_index < seg_end:
                return (seg_text, seg_start, seg_end)
        return None

    def _file_content_matches(self, text_matches: Any) -> List[Dict[str, Any]]:
        if not isinstance(text_matches, list):
            return []
        return [
            item for item in text_matches
            if isinstance(item, dict) and item.get("object_type") == "FileContent"
        ]

    def _extract_chunks_from_text_matches(
        self,
        content: str,
        text_matches: List[Dict[str, Any]],
        context_lines: int,
    ) -> List[str]:
        chunks: List[str] = []
        seen_chunks = set()

        content_lines = content.split("\n")
        if not content_lines:
            return chunks

        windows: List[Tuple[int, int]] = []
        fallback_chunks: List[str] = []

        for text_match in text_matches:
            fragment = str(text_match.get("fragment", "") or "") if isinstance(text_match, dict) else ""
            segments = self._split_fragment_segments(fragment)
            raw_matches = text_match.get("matches", []) if isinstance(text_match, dict) else []
            if not isinstance(raw_matches, list):
                raw_matches = []

            found_index = False
            for match_item in raw_matches:
                if not isinstance(match_item, dict):
                    continue
                indices = match_item.get("indices")
                if not (
                    isinstance(indices, list)
                    and len(indices) == 2
                    and all(isinstance(x, int) for x in indices)
                ):
                    continue

                start_idx = indices[0]
                if start_idx < 0:
                    continue

                seg_info = self._segment_for_fragment_index(segments, start_idx)
                if not seg_info:
                    continue

                seg_text, seg_start, _ = seg_info
                seg_clean = seg_text.strip("\n")
                if not seg_clean:
                    continue

                seg_pos = content.find(seg_clean)
                if seg_pos == -1:
                    # Fallback to line-level matching within segment when exact segment match fails.
                    local_idx = max(0, min(start_idx - seg_start, len(seg_text)))
                    line_start = seg_text.rfind("\n", 0, local_idx) + 1
                    line_end = seg_text.find("\n", local_idx)
                    if line_end == -1:
                        line_end = len(seg_text)
                    anchor_line = seg_text[line_start:line_end].strip()
                    if not anchor_line:
                        continue
                    anchor_pos = content.find(anchor_line)
                    if anchor_pos == -1:
                        continue
                    target_char = anchor_pos
                else:
                    local_idx = max(0, min(start_idx - seg_start, max(len(seg_text) - 1, 0)))
                    target_char = seg_pos + local_idx

                line_no = self._char_index_to_line_no(content, target_char)
                start_line = max(0, line_no - context_lines)
                end_line = min(len(content_lines) - 1, line_no + context_lines)
                windows.append((start_line, end_line))
                found_index = True

            if not found_index:
                fallback = self._fallback_snippet_from_text_match(text_match)
                if fallback:
                    fallback_chunks.append(fallback)

        if windows:
            for start_line, end_line in self._merge_line_windows(windows):
                chunk = "\n".join(content_lines[start_line:end_line + 1]).strip()
                if chunk and chunk not in seen_chunks:
                    seen_chunks.add(chunk)
                    chunks.append(chunk)
            return chunks

        # If index-based extraction fails, return API matched snippets without context.
        for fallback in fallback_chunks:
            if fallback and fallback not in seen_chunks:
                seen_chunks.add(fallback)
                chunks.append(fallback)

        return chunks

    def search_code(
        self,
        query: str,
        fetch_limit: int = 100,
        max_pages: int = 5,
    ) -> List[Dict]:
        """Search GitHub code with the given query.
        
        Uses the single claimed token for all requests.
        Strictly follows GitHub's rate limit wait times (from Retry-After or X-RateLimit-Reset).
        
        Args:
            query: GitHub search query string
            fetch_limit: Maximum results to fetch from API (before sampling)
            max_pages: Maximum pages to request
            
        Returns:
            List of search results with basic snippets from text_matches
        """
        results: List[Dict] = []
        page = 1
        per_page = min(self.per_page, 100)
        fetched = 0
        session = requests.Session()

        while fetched < fetch_limit and page <= max_pages:
            # Global secondary-limit gate: if any request hit a rate limit, all
            # requests wait out the cooldown before hitting GitHub again.
            gate_wait = _secondary_wait()
            if gate_wait > 0:
                logger.warning("Global secondary-limit gate: sleeping %.0fs before GitHub call", gate_wait)
                time.sleep(gate_wait)

            params = {"q": query, "per_page": per_page, "page": page}
            url = f"{self.API_BASE}/search/code"
            logger.info("GitHub code search [token #%d]: %s params=%s", 
                       self._token_idx, url, params)
            
            try:
                self._throttle_token_requests(f"search request page {page} for {query[:80]}")
                _acquire_github_slot()
                try:
                    resp = session.get(url, headers=self._headers(), params=params, timeout=30)
                finally:
                    _release_github_slot()
            except requests.RequestException as e:
                logger.error("Request error: %s", e)
                break

            if resp.status_code != 200:
                wait_seconds = self._handle_rate_limit(resp)
                if wait_seconds is not None:
                    # Strict secondary-limit backoff: mark the global cooldown
                    # (n+1) and DO NOT retry the request. Immediate retries after
                    # short Retry-After values make GitHub escalate the penalty
                    # (2s -> 1s -> 735s) and hammer the IP pointlessly.
                    _secondary_mark_blocked(wait_seconds)
                    logger.warning(
                        "Rate limited. Global cooldown set to n+1=%.0fs; request NOT retried.",
                        wait_seconds + 1.0,
                    )
                    break
                else:
                    logger.error("GitHub API error %s: %s", resp.status_code, resp.text[:200])
                    break

            _secondary_mark_success()
            try:
                data = resp.json()
            except json.JSONDecodeError as e:
                logger.error("Failed to parse JSON response: %s", e)
                break

            items = data.get("items", [])
            if not items:
                logger.debug("No more items in API response")
                break

            for it in items:
                repo_info = it.get("repository", {})
                # Extract basic snippet from text_matches
                tm = self._file_content_matches(it.get("text_matches"))
                if not tm:
                    continue

                frags = [
                    fragment
                    for match in tm
                    for fragment in [match.get("fragment")]
                    if isinstance(fragment, str) and fragment
                ]
                if frags:
                    snippet = "\n...\n".join(frags)
                else:
                    snippet = f"File: {it.get('path', 'unknown')}"
                
                entry = {
                    "repository": repo_info.get("full_name"),
                    "path": it.get("path"),
                    "name": it.get("name"),
                    "html_url": it.get("html_url"),
                    "object_url": tm[0].get("object_url", "") if tm else "",
                    "score": it.get("score"),
                    "sha": it.get("sha"),
                    "snippet": snippet,
                    "text_matches": tm,  # Preserve for context enrichment later
                }
                results.append(entry)
                fetched += 1
                if fetched >= fetch_limit:
                    break

            page += 1
            time.sleep(0.2)  # Respectful rate limiting between pages

        logger.info("Fetched %d results from API", len(results))
        return results

    def enrich_with_context(
        self,
        results: List[Dict],
        context_lines: int = 20,
    ) -> List[Dict]:
        """Enrich results with full file context.
        
        Args:
            results: List of search results to enrich
            context_lines: Lines of context to include around matches
            
        Returns:
            Results with enriched snippets from full file content
        """
        enriched = []
        success_count = 0
        total = len(results)
        
        for idx, r in enumerate(results, 1):
            repo_name = r.get("repository")
            file_path = r.get("path")
            snippet = r.get("snippet", "")
            
            if not repo_name or not file_path:
                enriched.append(r)
                continue
            
            logger.debug("Enriching %d/%d: %s/%s", idx, total, repo_name, file_path)
            tm = self._file_content_matches(r.get("text_matches"))
            object_url = r.get("object_url")
            object_url_str = object_url if isinstance(object_url, str) else ""
            content = self._fetch_object_url_content(object_url_str)
            
            if content:
                chunks = self._extract_chunks_from_text_matches(content, tm, context_lines)
                if chunks:
                    snippet = "\n...\n".join(chunks)
                    # Update snippet with enriched context
                    r_enriched = r.copy()
                    r_enriched["snippet"] = snippet
                    r_enriched["context_enriched"] = True
                    enriched.append(r_enriched)
                    success_count += 1
                else:
                    # Failed to extract context, keep original snippet
                    r_copy = r.copy()
                    r_copy["context_enriched"] = False
                    enriched.append(r_copy)
            else:
                # Failed to fetch, keep original basic snippet
                r_copy = r.copy()
                r_copy["context_enriched"] = False
                enriched.append(r_copy)
            
            time.sleep(0.1)  # Rate limiting
        
        logger.debug("Context enrichment complete: %d/%d successful (%.1f%%)", 
                   success_count, total, 100.0 * success_count / total if total > 0 else 0)
        return enriched


def _embed_with_codet5p(texts: List[str], batch_size: int = 96) -> Optional[np.ndarray]:
    """Embed texts using local CodeT5p model.
    
    Args:
        texts: List of code snippets to embed
        batch_size: Batch size for embedding (default 96)
        
    Returns:
        Normalized embedding matrix or None if embedding fails
    """
    try:
        import torch
        from transformers import AutoTokenizer, AutoModel
    except ImportError:
        logger.warning("transformers or torch not available for CodeT5p embedding")
        return None
    
    model_name = "Salesforce/codet5p-110m-embedding"
    
    try:
        # Load config first and patch for transformers >= 4.45 compat
        from transformers import AutoConfig
        config = AutoConfig.from_pretrained(model_name, trust_remote_code=True)
        if not hasattr(config, "is_decoder"):
            config.is_decoder = False
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        model = AutoModel.from_pretrained(model_name, trust_remote_code=True, config=config)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model.to(device)
        model.eval()
    except Exception as exc:
        logger.warning("Failed to load CodeT5p model: %s", exc)
        return None
    
    all_vectors: List[np.ndarray] = []
    
    for start_idx in range(0, len(texts), batch_size):
        batch_texts = texts[start_idx : start_idx + batch_size]
        
        try:
            with torch.no_grad():
                inputs = tokenizer(
                    batch_texts,
                    padding=True,
                    truncation=True,
                    max_length=512,
                    return_tensors="pt"
                ).to(device)
                outputs = model(**inputs)
                # Compat: newer transformers return raw tensor (batch, dim),
                # older return dict with last_hidden_state (batch, seq, dim)
                if isinstance(outputs, torch.Tensor):
                    embeddings = outputs
                else:
                    embeddings = outputs.last_hidden_state[:, 0, :]
                batch_vectors = embeddings.detach().cpu().numpy().astype(np.float32)
                all_vectors.append(batch_vectors)
        except Exception as exc:
            logger.warning("CodeT5p embedding batch error: %s", exc)
            return None
    
    if not all_vectors:
        return None
    
    arr = np.vstack(all_vectors).astype(np.float32)
    if arr.shape[0] != len(texts):
        return None
    
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return arr / norms


def _embed_with_qwen(texts: List[str], batch_size: int = 10) -> Optional[np.ndarray]:
    """Embed texts using DashScope Qwen embedding model.

    Uses DASHSCOPE_API_KEY and DASHSCOPE_BASE_URL from environment.
    Qwen API limits batch size to 10.
    """
    api_key = os.getenv("DASHSCOPE_API_KEY", "")
    if not api_key:
        logger.warning("DASHSCOPE_API_KEY not set for Qwen embedding")
        return None

    base_url = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    url = base_url.rstrip("/") + "/embeddings"
    model = os.getenv("EMBED_QWEN_MODEL", "text-embedding-v4")

    all_vectors: List[np.ndarray] = []

    for start_idx in range(0, len(texts), batch_size):
        batch_texts = texts[start_idx : start_idx + batch_size]
        try:
            resp = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "input": batch_texts,
                    "encoding_format": "float",
                },
                timeout=30,
            )
            if resp.status_code != 200:
                logger.warning("Qwen embedding returned status %d: %s", resp.status_code, resp.text[:200])
                return None
            data = resp.json()
            data_list = data.get("data", [])
            if not data_list:
                logger.warning("Qwen embedding returned no data")
                return None
            batch_vectors = np.array(
                [item["embedding"] for item in data_list], dtype=np.float32
            )
            all_vectors.append(batch_vectors)
        except Exception as exc:
            logger.warning("Qwen embedding error: %s", exc)
            return None

    if not all_vectors:
        return None

    arr = np.vstack(all_vectors).astype(np.float32)
    if arr.shape[0] != len(texts):
        logger.warning("Qwen embedding count mismatch: expected=%d got=%d", len(texts), arr.shape[0])
        return None

    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return arr / norms


def _embed(texts: List[str]) -> Optional[np.ndarray]:
    """Embed texts using the configured embedding model.

    Controlled by EMBED_MODEL env var (default: "codet5p").
    - "qwen": DashScope text-embedding-v4
    - "codet5p": local Salesforce/codet5p-110m-embedding
    """
    if _EMBED_MODEL == "qwen":
        return _embed_with_qwen(texts)
    return _embed_with_codet5p(texts)


def _cluster_and_pick_representatives(
    items: List[Dict],
    texts: List[str],
    sim_threshold: float,
) -> List[int]:
    """Cluster items by embedding cosine similarity and return one representative index per cluster.

    Uses greedy clustering: first item forms a cluster, subsequent items are
    assigned to an existing cluster if max similarity > threshold, else form new.
    Within each cluster, the item with highest score is picked as representative.

    Returns list of representative indices (stable order by first occurrence).
    """
    embeddings = _embed(texts)
    if embeddings is None:
        logger.info("Embedding unavailable, falling back to raw ordering")
        return list(range(len(items)))

    sim_matrix = np.dot(embeddings, embeddings.T)

    clusters: List[List[int]] = []

    for i in range(len(items)):
        best_cluster = -1
        best_sim = -1.0
        for ci, cluster in enumerate(clusters):
            sim_to_cluster = max(sim_matrix[i, j] for j in cluster)
            if sim_to_cluster > best_sim:
                best_sim = sim_to_cluster
                best_cluster = ci

        if best_sim >= sim_threshold:
            clusters[best_cluster].append(i)
        else:
            clusters.append([i])

    logger.info(
        "Clustered %d items into %d groups (threshold=%.2f)",
        len(items),
        len(clusters),
        sim_threshold,
    )

    representatives = []
    for cluster in clusters:
        best_idx = max(cluster, key=lambda idx: float(items[idx].get("score", 0)))
        representatives.append(best_idx)

    return representatives


def sample_results(results: List[Dict], target_count: int) -> List[Dict]:
    """Keep diverse results via CodeT5p embedding-based clustering.

    Clusters snippets by embedding similarity and picks the highest-scoring
    representative from each cluster, then returns top target_count by score.

    Falls back to score-sort if embedding is unavailable.
    """
    if not results:
        return []

    max_keep = min(96, len(results))
    if len(results) <= 1:
        return results

    texts = [r.get("snippet", "") for r in results]
    representatives = _cluster_and_pick_representatives(results, texts, _EMBED_SIM_THRESHOLD)

    clustered_results = [results[i] for i in representatives]
    sorted_results = sorted(
        clustered_results,
        key=lambda r: float(r.get("score", 0)),
        reverse=True,
    )
    sampled = sorted_results[:max_keep]

    logger.info(
        "Sampled %d results from %d total (%d clusters) via embedding dedup",
        len(sampled),
        len(results),
        len(representatives),
    )
    return sampled


_github_searcher_by_token: Dict[str, GitHubCodeSearcher] = {}

def _get_searcher(token: Optional[str] = None) -> GitHubCodeSearcher:
    """Get or create the module-level GitHubCodeSearcher instance."""
    global _github_searcher_by_token

    if token:
        key = token.strip()
        if key not in _github_searcher_by_token:
            logger.info("Initializing token-scoped GitHubCodeSearcher instance")
            _github_searcher_by_token[key] = GitHubCodeSearcher(
                token=key,
                token_file=None,
                enable_token_lock=False,
            )
        return _github_searcher_by_token[key]

    logger.info("Initializing pooled GitHubCodeSearcher instance")
    return GitHubCodeSearcher()


def peek(query, token: Optional[str] = None, limit: int = 5):
    """Quick preview of search results using module-level instance.

    limit: number of top snippets to return. limit <= 0 (or None) means
    "all" -> fetch the full first page (up to 100 results) and return them all.
    """
    searcher = _get_searcher(token=token)
    try:
        if limit is not None and limit > 0:
            results = searcher.search_code(query=query, fetch_limit=limit, max_pages=1)
            snippets = [r.get("snippet", "") for r in results][:limit]
        else:
            results = searcher.search_code(query=query, fetch_limit=100, max_pages=1)
            snippets = [r.get("snippet", "") for r in results]
        return snippets
    finally:
        if token is None:
            searcher._release_token_lock()


def run(query, target_results=20, context_lines=5, token: Optional[str] = None):
    """Run full search pipeline using module-level instance."""
    searcher = _get_searcher(token=token)
    try:
        # Setup
        fetch_limit = max(target_results * 10, 100)  # Fetch more than target to allow for filtering and enrichment
        
        # Phase 1: Fetch from API
        logger.debug("Phase 1: Fetching up to %d results from GitHub API", fetch_limit)
        logger.debug("Query: %s", query)
        
        raw_results = searcher.search_code(
            query,
            fetch_limit=fetch_limit,
        )
        
        # Phase 2: Deduplicate by repository (to filter forks) and URL
        logger.debug("Phase 2: Deduplicating results by repository name and URL")
        unique_results = []
        seen_repos = set()
        seen_urls = set()
        
        for r in raw_results:
            repo = r.get('repository')
            url = r.get('html_url')
            
            # Skip if we've seen this repo or URL before (filters forks and duplicates)
            if repo and repo in seen_repos:
                logger.debug("Skipping duplicate repo: %s", repo)
                continue
            if url and url in seen_urls:
                logger.debug("Skipping duplicate URL: %s", url)
                continue
            
            if repo: seen_repos.add(repo)
            if url: seen_urls.add(url)
            unique_results.append(r)
        
        logger.debug("Unique results after deduplication: %d (from %d repos)", 
                    len(unique_results), len(seen_repos))
        
        # Phase 2b: Embedding-based near-duplicate removal
        logger.debug("Phase 2b: Removing near-duplicates via embedding clustering")
        if len(unique_results) > 1:
            texts = [r.get("snippet", "") for r in unique_results]
            representatives = _cluster_and_pick_representatives(unique_results, texts, _EMBED_SIM_THRESHOLD)
            unique_results = [unique_results[i] for i in representatives]
            logger.debug("After embedding dedup: %d results (%d clusters)", len(unique_results), len(representatives))
        
        # Phase 3: Sample to target count
        logger.debug("Phase 3: Sampling to target count of %d", target_results)
        sampled_results = sample_results(unique_results, target_results)
        
        # Phase 4: Enrich with full context only when explicitly enabled.
        if _FETCH_FULL_CONTENT:
            logger.debug("Phase 4: Enriching %d sampled results with full file context", len(sampled_results))
            final_results = searcher.enrich_with_context(sampled_results, context_lines)
        else:
            logger.debug("Phase 4: Skipping full-content fetch by default")
            final_results = sampled_results
        
        # Phase 5: Format output
        output = []
        for r in final_results:
            result = {
                "repo": r.get("repository"),
                "path": r.get("path"),
                "url": r.get("html_url"),
                "snippet": r.get("snippet"),
                "score": r.get("score"),
            }
            # Include enrichment status if context fetching was attempted
            if "context_enriched" in r:
                result["context_enriched"] = r["context_enriched"]
            output.append(result)

        logger.info("Final output: %d results", len(output))
        return output
    finally:
        if token is None:
            searcher._release_token_lock()

if __name__ == "__main__":
    r = run("def quick_sort", target_results=10, context_lines=5)
