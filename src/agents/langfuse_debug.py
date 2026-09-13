"""
Langfuse observability integration (optional, enabled via --debug flag).

Requires environment variables:
    LANGFUSE_SECRET_KEY
    LANGFUSE_PUBLIC_KEY
    LANGFUSE_BASE_URL
"""

import os
import sys

secret = os.getenv("LANGFUSE_SECRET_KEY")
public = os.getenv("LANGFUSE_PUBLIC_KEY")
base_url = os.getenv("LANGFUSE_BASE_URL")

if not all([secret, public, base_url]):
    print(
        "[langfuse_debug] skipping: set LANGFUSE_SECRET_KEY, LANGFUSE_PUBLIC_KEY, "
        "and LANGFUSE_BASE_URL to enable tracing.",
        file=sys.stderr,
    )

langfuse_client = None

if secret and public and base_url:
    os.environ["LANGFUSE_SECRET_KEY"] = secret
    os.environ["LANGFUSE_PUBLIC_KEY"] = public
    os.environ["LANGFUSE_BASE_URL"] = base_url

    from langfuse import get_client

    langfuse_client = get_client()
    if langfuse_client.auth_check():
        print("[langfuse_debug] tracing enabled", file=sys.stderr)
    else:
        print("[langfuse_debug] auth check failed", file=sys.stderr)


def get_callback_handler():
    """Return a Langfuse LangChain CallbackHandler, or None when tracing is off.

    Safe to call unconditionally: returns None (and the pipeline runs exactly as
    before) unless LANGFUSE_SECRET_KEY / LANGFUSE_PUBLIC_KEY / LANGFUSE_BASE_URL
    are all set.
    """
    if not (secret and public and base_url):
        return None
    try:
        from langfuse.langchain import CallbackHandler

        return CallbackHandler()
    except Exception as exc:  # pragma: no cover - defensive
        print(f"[langfuse_debug] callback handler init failed: {exc}", file=sys.stderr)
        return None
