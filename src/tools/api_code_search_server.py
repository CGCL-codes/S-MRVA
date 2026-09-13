#!/usr/bin/env python3
"""
GitHub Code Search Request Serialization Server

This server serializes all GitHub API requests from multiple processes through
a single process to avoid rate limit conflicts. Uses Unix domain socket for IPC.

Architecture:
- Single server instance enforced via file-based locking (atomic O_CREAT|O_EXCL)
- Unix domain socket at /tmp/api_code_search.sock for client communication
- Strictly serial request processing (one GitHub API call at a time)
- Reuses GitHubCodeSearcher from impl_code_search for actual GitHub interaction
- Graceful shutdown on SIGTERM/SIGINT with cleanup

Usage:
    python -m tools.api_code_search_server
    
    Or auto-started by client when needed.
"""

import os
import sys
import json
import time
import signal
import socket
import logging
import threading
import hashlib
from collections import deque
from pathlib import Path
from typing import Optional, Dict, Any, List

# Import the actual GitHub searcher implementation
try:
    from .impl_code_search import run as _run_impl, peek as _peek_impl, GitHubCodeSearcher
except ImportError:
    from impl_code_search import run as _run_impl, peek as _peek_impl, GitHubCodeSearcher

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


class CodeSearchServer:
    """
    Request serialization server for GitHub code search.
    
    Enforces single instance via file locking and processes all requests serially
    to avoid GitHub API rate limit conflicts across multiple processes.
    """
    
    LOCK_DIR = "/tmp"
    LOCK_PREFIX = "api_code_search_server_pid_"
    LOCK_SUFFIX = ".lock"
    SOCKET_PATH = "/tmp/api_code_search.sock"
    STATE_PATH = "/tmp/api_code_search_server_state.json"
    
    MAX_MESSAGE_SIZE = 100 * 1024 * 1024
    HEADER_SIZE = 10
    
    def __init__(self):
        self.pid = os.getpid()
        self.lock_file_path: Optional[str] = None
        self.socket: Optional[socket.socket] = None
        self.running = False
        self._shutdown_event = threading.Event()
        self._request_count = 0
        self._start_time = time.time()
        self._token_pool = self._load_token_pool()
        self._available_tokens: List[str] = []
        self._token_queue: deque[str] = deque()
        self._token_lock = threading.Lock()
        
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _load_token_pool(self) -> List[str]:
        pool: List[str] = []

        token_file = os.getenv("GITHUB_TOKEN_FILE")
        if token_file:
            file_path = Path(token_file)
            if file_path.exists():
                try:
                    with file_path.open("r", encoding="utf-8") as handle:
                        for line in handle:
                            token = line.strip()
                            if not token or token.startswith("#"):
                                continue
                            pool.append(token)
                except OSError as e:
                    logger.warning("Failed to read token file %s: %s", token_file, e)

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

        deduped = list(dict.fromkeys([t for t in pool if t]))
        # The GitHub search limit is per-IP (secondary rate limit), not per-token,
        # so extra tokens do not help. We use ONE token and serialize every
        # request (see impl_code_search._acquire_github_slot). The cap is applied
        # AFTER availability filtering in _initialize_available_tokens so a dead
        # token early in the file cannot starve the pool.
        max_tokens = int(os.getenv("GITHUB_MAX_TOKENS", "1"))
        self._max_tokens = max_tokens
        if deduped:
            logger.info("Loaded %d GitHub token(s) from pool (will cap at %d after availability check)",
                        len(deduped), max_tokens)
        return deduped

    @staticmethod
    def _is_token_available(token: str) -> bool:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHubCodeSearchServer/1.0",
            "Authorization": f"token {token}",
        }
        try:
            import requests

            rate_limit_url = f"{os.getenv('GITHUB_API_BASE', 'https://api.github.com')}/rate_limit"
            resp = requests.get(rate_limit_url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return False
            data = resp.json()
            core = data.get("resources", {}).get("core", {})
            remaining = core.get("remaining")
            return isinstance(remaining, int) and remaining > 0
        except Exception:
            return False

    def _initialize_available_tokens(self) -> bool:
        if not self._token_pool:
            logger.error("No tokens found in token pool")
            return False

        # Filter to tokens that are actually usable FIRST, then cap. This way a
        # dead token earlier in the file (e.g. token #0) is skipped instead of
        # starving the pool.
        available: List[str] = []
        for idx, token in enumerate(self._token_pool):
            ok = self._is_token_available(token)
            logger.info("Token #%d availability: %s", idx, "OK" if ok else "UNAVAILABLE")
            if ok:
                available.append(token)

        max_tokens = getattr(self, "_max_tokens", 1)
        if max_tokens > 0:
            available = available[:max_tokens]

        if not available:
            logger.error("All tokens are unavailable at startup")
            return False

        self._available_tokens = available
        self._token_queue = deque(available)
        logger.info("Initialized token pool with %d available token(s) (capped at %d)",
                    len(available), max_tokens)
        return True

    def _next_token(self) -> Optional[str]:
        with self._token_lock:
            if not self._token_queue:
                return None
            token = self._token_queue[0]
            self._token_queue.rotate(-1)
            token_fingerprint = hashlib.sha256(token.encode("utf-8")).hexdigest()[:8]
            logger.info("Rotating to token (fingerprint=%s)", token_fingerprint)
            return token
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info("Received signal %d, initiating graceful shutdown...", signum)
        self.running = False
        self._shutdown_event.set()
    
    @staticmethod
    def _pid_is_alive(pid: int) -> bool:
        """Check if a process with given PID is still running."""
        if pid == os.getpid():
            return True
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    
    @staticmethod
    def _cleanup_stale_resources():
        """Remove stale lock files and socket files from dead processes."""
        logger.debug("Cleaning up stale resources...")
        
        # Clean stale lock files
        try:
            for entry in os.listdir(CodeSearchServer.LOCK_DIR):
                if not entry.startswith(CodeSearchServer.LOCK_PREFIX):
                    continue
                if not entry.endswith(CodeSearchServer.LOCK_SUFFIX):
                    continue
                
                # Extract PID from filename: api_code_search_server_pid_{pid}.lock
                try:
                    pid_str = entry.replace(CodeSearchServer.LOCK_PREFIX, "").replace(CodeSearchServer.LOCK_SUFFIX, "")
                    pid = int(pid_str)
                    lock_path = os.path.join(CodeSearchServer.LOCK_DIR, entry)
                    
                    if not CodeSearchServer._pid_is_alive(pid):
                        os.remove(lock_path)
                        logger.info("Removed stale lock file (dead PID %d): %s", pid, entry)
                except (ValueError, OSError) as e:
                    logger.debug("Could not cleanup lock file %s: %s", entry, e)
        except OSError as e:
            logger.warning("Error listing lock directory: %s", e)
        
        # Clean stale socket file
        if os.path.exists(CodeSearchServer.SOCKET_PATH):
            # Try to connect to see if server is actually running
            try:
                test_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                test_sock.settimeout(1.0)
                test_sock.connect(CodeSearchServer.SOCKET_PATH)
                test_sock.close()
                logger.debug("Socket file exists and server is responsive")
            except (socket.error, OSError):
                # Socket exists but no server listening - remove it
                try:
                    os.remove(CodeSearchServer.SOCKET_PATH)
                    logger.info("Removed stale socket file: %s", CodeSearchServer.SOCKET_PATH)
                except OSError as e:
                    logger.warning("Could not remove stale socket: %s", e)
    
    def _claim_lock(self) -> bool:
        """
        Claim exclusive server lock via atomic file creation.
        
        Returns:
            True if lock claimed successfully, False if another server is running
        """
        self.lock_file_path = os.path.join(
            self.LOCK_DIR,
            f"{self.LOCK_PREFIX}{self.pid}{self.LOCK_SUFFIX}"
        )
        
        try:
            # Atomic creation - fails if file already exists
            fd = os.open(self.lock_file_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            with os.fdopen(fd, 'w') as f:
                lock_data = {
                    "pid": self.pid,
                    "socket": self.SOCKET_PATH,
                    "started": time.time()
                }
                json.dump(lock_data, f)
            logger.info("Successfully claimed server lock (PID=%d): %s", self.pid, self.lock_file_path)
            return True
        except FileExistsError:
            logger.error("Lock file already exists - another server may be running")
            return False
        except OSError as e:
            logger.error("Error claiming lock: %s", e)
            return False
    
    def _release_lock(self):
        """Release the server lock by removing the lock file."""
        if self.lock_file_path and os.path.exists(self.lock_file_path):
            try:
                os.remove(self.lock_file_path)
                logger.info("Released server lock (PID=%d)", self.pid)
            except OSError as e:
                logger.warning("Error releasing lock: %s", e)

    def _write_state_file(self):
        """Persist server state so clients can detect and reuse the single server."""
        try:
            state = {
                "pid": self.pid,
                "socket": self.SOCKET_PATH,
                "lock_file": self.lock_file_path,
                "started": time.time(),
            }
            with open(self.STATE_PATH, "w", encoding="utf-8") as handle:
                json.dump(state, handle)
            logger.info("Wrote server state file: %s", self.STATE_PATH)
        except OSError as e:
            logger.warning("Error writing state file: %s", e)

    def _remove_state_file(self):
        """Remove the persisted server state file."""
        if os.path.exists(self.STATE_PATH):
            try:
                os.remove(self.STATE_PATH)
                logger.info("Removed state file: %s", self.STATE_PATH)
            except OSError as e:
                logger.warning("Error removing state file: %s", e)
    
    def _create_socket(self) -> bool:
        """
        Create and bind Unix domain socket.
        
        Returns:
            True if socket created successfully, False otherwise
        """
        try:
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.socket.bind(self.SOCKET_PATH)
            self.socket.listen(128)  # absorb the pipeline's concurrent search burst
            logger.info("Server listening on: %s", self.SOCKET_PATH)
            return True
        except OSError as e:
            logger.error("Failed to create socket: %s", e)
            return False
    
    def _close_socket(self):
        """Close socket and remove socket file."""
        if self.socket:
            try:
                self.socket.close()
            except OSError as e:
                logger.warning("Error closing socket: %s", e)
        
        if os.path.exists(self.SOCKET_PATH):
            try:
                os.remove(self.SOCKET_PATH)
                logger.info("Removed socket file: %s", self.SOCKET_PATH)
            except OSError as e:
                logger.warning("Error removing socket file: %s", e)
    
    def _send_message(self, conn: socket.socket, data: Dict[str, Any]):
        """Send a JSON message with length prefix."""
        try:
            payload = json.dumps(data).encode('utf-8')
            length = len(payload)
            
            if length > self.MAX_MESSAGE_SIZE:
                raise ValueError(f"Message too large: {length} bytes")
            
            # Send length header: "{length:10}\n"
            header = f"{length:010d}\n".encode('ascii')
            conn.sendall(header + payload)
        except BrokenPipeError:
            # Client disconnected (normal occurrence after timeout or network issue)
            logger.debug("Client disconnected - broken pipe while sending response")
        except ConnectionResetError:
            # Client forcefully closed connection
            logger.debug("Connection reset by client")
        except Exception as e:
            logger.warning("Error sending message: %s", e)
    
    def _recv_message(self, conn: socket.socket) -> Optional[Dict[str, Any]]:
        """Receive a JSON message with length prefix."""
        try:
            # Read length header (10 digits + newline)
            header = b''
            while len(header) < self.HEADER_SIZE + 1:
                chunk = conn.recv(self.HEADER_SIZE + 1 - len(header))
                if not chunk:
                    return None
                header += chunk
            
            # Parse length
            try:
                length = int(header[:self.HEADER_SIZE].decode('ascii'))
            except ValueError:
                logger.error("Invalid length header: %s", header)
                return None
            
            if length > self.MAX_MESSAGE_SIZE:
                logger.error("Message too large: %d bytes", length)
                return None
            
            # Read payload
            payload = b''
            while len(payload) < length:
                chunk = conn.recv(min(4096, length - len(payload)))
                if not chunk:
                    return None
                payload += chunk
            
            # Parse JSON
            return json.loads(payload.decode('utf-8'))
        except Exception as e:
            logger.error("Error receiving message: %s", e)
            return None
    
    def _handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single search request.
        
        Args:
            request: Request dict with 'method', 'query', etc.
            
        Returns:
            Response dict with 'status' and 'data' or 'error'
        """
        self._request_count += 1
        request_id = self._request_count
        
        try:
            method = request.get('method')
            query = request.get('query')
            
            if not method or not query:
                return {
                    "status": "error",
                    "error": "Missing 'method' or 'query' in request"
                }
            
            logger.info("[Req #%d] %s: %s", request_id, method, query[:100])
            start = time.time()
            token = self._next_token()
            if not token:
                return {
                    "status": "error",
                    "error": "No available tokens in pool"
                }
            if method == 'search':
                target_results = request.get('target_results', 20)
                context_lines = request.get('context_lines', 5)
                
                results = _run_impl(
                    query=query,
                    target_results=target_results,
                    context_lines=context_lines,
                    token=token,
                )
                
                elapsed = time.time() - start
                logger.info("[Req #%d] Completed in %.2fs, returned %d results", 
                           request_id, elapsed, len(results))
                
                return {
                    "status": "ok",
                    "data": results
                }
            
            elif method == 'peek':
                limit = request.get('limit', 5)
                results = _peek_impl(query=query, token=token, limit=limit)
                
                elapsed = time.time() - start
                logger.info("[Req #%d] Peek completed in %.2fs, returned %d results", 
                           request_id, elapsed, len(results))
                
                return {
                    "status": "ok",
                    "data": results
                }
            
            else:
                return {
                    "status": "error",
                    "error": f"Unknown method: {method}"
                }
        
        except Exception as e:
            logger.error("Error processing request: %s", e, exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _handle_connection(self, conn: socket.socket, _addr):
        """Handle a single client connection."""
        try:
            logger.debug("Accepted connection from client")
            
            # Receive request
            request = self._recv_message(conn)
            if request is None:
                # Normal when a client disconnects without sending a request.
                logger.debug("Client disconnected without sending a request")
                return
            
            # Process request (this is where serialization happens)
            response = self._handle_request(request)
            
            # Send response
            self._send_message(conn, response)
            logger.debug("Sent response to client")
        
        except socket.timeout:
            # Socket timeout - client didn't respond in time
            logger.debug("Socket timeout - client request took too long")
        except (BrokenPipeError, ConnectionResetError):
            # Client disconnected - normal, don't log as error
            logger.debug("Client connection lost during request handling")
        except Exception as e:
            logger.error("Error handling connection: %s", e, exc_info=True)
            try:
                error_response = {"status": "error", "error": str(e)}
                self._send_message(conn, error_response)
            except (BrokenPipeError, ConnectionResetError, socket.timeout):
                logger.debug("Could not send error response - client already disconnected")
            except Exception:
                pass
        finally:
            try:
                conn.close()
            except Exception:
                pass
    
    def serve(self):
        """Main server loop - accept connections and process requests serially."""
        if self.socket is None:
            logger.error("Cannot serve: socket not initialized")
            return
        
        self.running = True
        logger.info("Server started (PID=%d)", self.pid)
        
        self.socket.settimeout(1.0)
        
        while self.running:
            try:
                conn, addr = self.socket.accept()
                self._handle_connection(conn, addr)
            except socket.timeout:
                if self._shutdown_event.is_set():
                    break
                
                if self._request_count > 0 and self._request_count % 100 == 0:
                    uptime = time.time() - self._start_time
                    logger.info("Stats: %d requests processed, uptime: %.1fs", 
                               self._request_count, uptime)
                continue
            except Exception as e:
                if self.running:
                    logger.error("Error accepting connection: %s", e)
                break
        
        uptime = time.time() - self._start_time
        logger.info("Server shutting down... (processed %d requests in %.1fs)", 
                   self._request_count, uptime)
    
    def start(self) -> bool:
        """
        Start the server.
        
        Returns:
            True if server started successfully, False otherwise
        """
        # Cleanup stale resources
        self._cleanup_stale_resources()
        
        # Claim lock
        if not self._claim_lock():
            return False
        
        # Create socket
        if not self._create_socket():
            self._release_lock()
            return False

        if not self._initialize_available_tokens():
            self._close_socket()
            self._release_lock()
            return False

        self._write_state_file()
        
        return True
    
    def stop(self):
        """Stop the server and cleanup resources."""
        self.running = False
        self._close_socket()
        self._remove_state_file()
        self._release_lock()


def main():
    """Main entry point for server process."""
    server = CodeSearchServer()
    
    try:
        if not server.start():
            logger.error("Failed to start server")
            sys.exit(1)
        
        # Run server loop
        server.serve()
    
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        sys.exit(1)
    finally:
        server.stop()
        logger.info("Server stopped")


if __name__ == "__main__":
    main()
