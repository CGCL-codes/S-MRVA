#!/usr/bin/env python3
"""Verify that the configured LLM and embedding backend are usable.

Usage (from the repository root):

    python3 src/agents/check_env.py

Reads `.env` if present, then:
  1. prints the resolved LLM configuration (API key masked) and sends one tiny
     request;
  2. runs the configured embedding on one tiny input (`codet5p` local model, or
     the `qwen` DashScope embedding API).

Exit code is 0 only if both checks pass, so it is safe to use in a shell `&&`
chain. In the published image the `codet5p` model is baked in (no download);
running outside the image downloads it once (~0.5 GB).
"""
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

try:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
except Exception:
    pass

# A sane default so importing the tools never fails on a missing work dir.
os.environ.setdefault("SAT_WORK_DIR", str(REPO_ROOT))


def _mask(secret: str | None) -> str:
    return f"{secret[:6]}..." if secret else "(unset)"


def check_llm() -> None:
    from agents.model import llm  # constructs ChatOpenAI from the env

    base_url = getattr(llm, "openai_api_base", None) or os.getenv("LLM_BASE_URL") \
        or os.getenv("DASHSCOPE_BASE_URL", "(default)")
    key = os.getenv("LLM_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
    print(f"[LLM] model={getattr(llm, 'model_name', '?')}  base_url={base_url}  "
          f"api_key={_mask(key)}")

    t = time.time()
    reply = llm.invoke("Reply with exactly one word: OK")
    text = getattr(reply, "content", str(reply))
    print(f"[LLM] OK in {time.time() - t:.1f}s -> {text!r}")


def check_embed() -> None:
    mode = os.getenv("EMBED_MODEL", "codet5p").lower()
    extra = ""
    if mode == "qwen":
        extra = (f"  base_url={os.getenv('DASHSCOPE_BASE_URL', '(default)')}  "
                 f"model={os.getenv('EMBED_QWEN_MODEL', 'text-embedding-v4')}")
    print(f"[EMB] EMBED_MODEL={mode}{extra}")

    from tools.impl_code_search import _embed

    t = time.time()
    vec = _embed(["def f(x):\n    return x"])
    if vec is None:
        raise RuntimeError(
            f"embedding '{mode}' returned None (check the DASHSCOPE_* key/endpoint)"
        )
    print(f"[EMB] OK in {time.time() - t:.1f}s -> shape={getattr(vec, 'shape', None)}")


def main() -> int:
    ok = True
    for name, fn in (("LLM", check_llm), ("EMBED", check_embed)):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 - report and continue
            ok = False
            print(f"[{name}] FAIL: {type(exc).__name__}: {exc}")
    print(f"\nRESULT: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
