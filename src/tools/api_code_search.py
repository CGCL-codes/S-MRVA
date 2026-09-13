from langchain_core.tools import tool
import os
import sys
import json
import socket
import logging
import subprocess
import time
from typing import List, Dict, Any, Optional

try:
    from .impl_code_search import run as _run_impl, peek as _peek_impl
except ImportError:
    from impl_code_search import run as _run_impl, peek as _peek_impl

logger = logging.getLogger(__name__)

SOCKET_PATH = "/tmp/api_code_search.sock"
STATE_PATH = "/tmp/api_code_search_server_state.json"
STARTUP_LOCK_PATH = "/tmp/api_code_search_startup.lock"
MAX_MESSAGE_SIZE = 100 * 1024 * 1024
HEADER_SIZE = 10

def _get_mode() -> str:
    mode = os.getenv("API_CODE_SEARCH_MODE", "auto").lower()
    if mode not in ("direct", "server", "auto"):
        logger.warning("Invalid API_CODE_SEARCH_MODE=%s, using 'auto'", mode)
        return "auto"
    return mode


def _read_server_state() -> Optional[Dict[str, Any]]:
    try:
        if not os.path.exists(STATE_PATH):
            return None
        with open(STATE_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _pid_is_alive(pid: Optional[int]) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    if pid == os.getpid():
        return True
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _socket_is_ready() -> bool:
    if not os.path.exists(SOCKET_PATH):
        return False
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(1.0)
    try:
        sock.connect(SOCKET_PATH)
        return True
    except OSError:
        return False
    finally:
        try:
            sock.close()
        except Exception:
            pass


def _acquire_startup_lock() -> Optional[int]:
    try:
        return os.open(STARTUP_LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        return None
    except OSError:
        return None


def _release_startup_lock(fd: Optional[int]) -> None:
    if fd is None:
        return
    try:
        os.close(fd)
    except OSError:
        pass


def _server_is_ready() -> bool:
    if _socket_is_ready():
        return True

    state = _read_server_state()
    if not state:
        return False

    return _pid_is_alive(state.get("pid")) and _socket_is_ready()


def _wait_for_server_ready(timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _server_is_ready():
            return True
        time.sleep(0.25)
    return False


def _spawn_server_process() -> None:
    server_module = os.path.join(os.path.dirname(__file__), "api_code_search_server.py")
    if not os.path.exists(server_module):
        raise FileNotFoundError(f"Server module not found: {server_module}")

    subprocess.Popen(
        [sys.executable, "-m", "src.tools.api_code_search_server"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        if os.path.exists(STARTUP_LOCK_PATH):
            os.remove(STARTUP_LOCK_PATH)
    except OSError:
        pass


def init_server(timeout: float = 30.0) -> bool:
    """Ensure the single API code search server is running.

    A filesystem lock serializes startup so multiple worker processes do not
    spawn competing servers.
    """
    if _server_is_ready():
        return True

    lock_fd = _acquire_startup_lock()
    if lock_fd is None:
        return _wait_for_server_ready(timeout)

    try:
        if _server_is_ready():
            return True

        _spawn_server_process()

        if _wait_for_server_ready(timeout):
            return True

        logger.warning("Server did not become ready within %.1f seconds", timeout)
        return False
    except Exception as e:
        logger.warning("Failed to start server: %s", e)
        return False
    finally:
        _release_startup_lock(lock_fd)

def _send_message(conn: socket.socket, data: Dict[str, Any]):
    payload = json.dumps(data).encode('utf-8')
    length = len(payload)
    
    if length > MAX_MESSAGE_SIZE:
        raise ValueError(f"Message too large: {length} bytes")
    
    header = f"{length:010d}\n".encode('ascii')
    conn.sendall(header + payload)

def _recv_message(conn: socket.socket) -> Optional[Dict[str, Any]]:
    header = b''
    while len(header) < HEADER_SIZE + 1:
        chunk = conn.recv(HEADER_SIZE + 1 - len(header))
        if not chunk:
            return None
        header += chunk
    
    try:
        length = int(header[:HEADER_SIZE].decode('ascii'))
    except ValueError:
        logger.error("Invalid length header from server")
        return None
    
    if length > MAX_MESSAGE_SIZE:
        logger.error("Server message too large: %d bytes", length)
        return None
    
    payload = b''
    while len(payload) < length:
        chunk = conn.recv(min(4096, length - len(payload)))
        if not chunk:
            return None
        payload += chunk
    
    return json.loads(payload.decode('utf-8'))

def _try_start_server() -> bool:
    return init_server()


def _query_via_mode(
    mode: str,
    method: str,
    query: str,
    direct_fn,
    **kwargs,
):
    if mode == "direct":
        try:
            return direct_fn(query=query, **kwargs)
        except Exception as e:
            print(f"Error occurred while querying GitHub code: {e}")
            return []

    if mode not in ("server", "auto"):
        return []

    if mode == "server":
        if not _server_is_ready():
            raise RuntimeError(
                "API_CODE_SEARCH_MODE=server but the code-search server is not "
                f"reachable at {SOCKET_PATH}. Start it with: "
                "python3 -m src.tools.api_code_search_server"
            )
    elif not _server_is_ready() and not init_server():
        logger.warning("Server unavailable; falling back to direct mode")
        try:
            return direct_fn(query=query, **kwargs)
        except Exception as e:
            print(f"Error occurred while querying GitHub code: {e}")
            return []

    result = _call_server(method, query, **kwargs)
    if result is not None:
        return result

    logger.warning("Server communication failed; falling back to direct mode")
    try:
        return direct_fn(query=query, **kwargs)
    except Exception as e:
        print(f"Error occurred while querying GitHub code: {e}")
        return []

def _call_server(method: str, query: str, **kwargs) -> Optional[List]:
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        timeout = kwargs.pop('timeout', None)
        if timeout is not None:
            sock.settimeout(timeout)
        
        try:
            sock.connect(SOCKET_PATH)
        except OSError:
            return None
        
        request = {"method": method, "query": query, **kwargs}
        _send_message(sock, request)
        
        response = _recv_message(sock)
        sock.close()
        
        if response is None:
            logger.error("No response from server")
            return None
        
        if response.get("status") == "ok":
            return response.get("data", [])
        else:
            error = response.get("error", "Unknown error")
            logger.error("Server error: %s", error)
            return None
    
    except Exception as e:
        logger.warning("Server communication failed: %s", e)
        return None

def github_code_search(query: str, target_results: int = 10, context_lines: int = 5):
    mode = _get_mode()
    return _query_via_mode(
        mode=mode,
        method="search",
        query=query,
        direct_fn=_run_impl,
        target_results=target_results,
        context_lines=context_lines,
    )

def peek(query: str, limit: int = 5):
    mode = _get_mode()
    return _query_via_mode(mode=mode, method="peek", query=query, direct_fn=_peek_impl, limit=limit)