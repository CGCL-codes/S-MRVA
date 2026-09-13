"""LLM cost/time tracking via a LangChain callback handler.

Enabled by ENABLE_COST_TRACKING=1 (default off). Attach a CostTracker to the
LLM's callbacks; it accumulates per-call latency and token usage and computes
an estimated USD cost from a provider pricing table.
"""

import os
import time

from langchain_core.callbacks import BaseCallbackHandler

# ---------------------------------------------------------------------------
# Pricing table
# ---------------------------------------------------------------------------
# USD per 1M tokens as (input, output) unless marked CNY.
# For CNY providers the raw price is stored and converted with CNY_PER_USD at
# cost-computation time.
PRICING: dict[str, tuple[float, float, str]] = {
    # DeepSeek (USD)
    "deepseek-flash": (0.22, 0.66, "USD"),
    "deepseek-v4-flash": (0.22, 0.66, "USD"),  # legacy alias
    "deepseek-v4-pro": (0.66, 1.98, "USD"),
    "deepseek-chat": (0.27, 1.10, "USD"),
    "deepseek-reasoner": (0.55, 2.19, "USD"),
    # OpenAI (USD)
    "gpt-4o": (2.50, 10.00, "USD"),
    "gpt-4o-mini": (0.15, 0.60, "USD"),
    "gpt-4.1": (2.00, 8.00, "USD"),
    "gpt-4.1-mini": (0.40, 1.60, "USD"),
    "gpt-4.1-nano": (0.10, 0.40, "USD"),
    # DashScope Qwen (CNY, converted to USD)
    "qwen3.5-plus": (0.8, 4.8, "CNY"),
    "qwen3.5-flash": (0.2, 2.0, "CNY"),
    "qwen3.7-plus": (2, 8, "CNY"),
    "qwen3.7-flash": (0.2, 0.8, "CNY"),
    "qwen3.8-flash": (0.8, 2.7, "CNY"),
    "qwen3.8-max": (12, 36, "CNY"),
    # MiniMax (CNY, converted to USD)
    "minimax-m3": (2.10, 8.40, "CNY"),
    "minimax-m2.5": (2.1, 8.4, "CNY"),
}

# CNY → USD conversion factor (default 0.14 ≈ 7.14 CNY/USD).
CNY_PER_USD = float(os.getenv("CNY_PER_USD", "0.14"))


def compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate USD cost for *input_tokens* / *output_tokens* at 1M-token rates.

    Returns 0.0 if the model is not present in the pricing table.
    """
    entry = PRICING.get((model or "").lower())
    if entry is None:
        return 0.0
    in_p, out_p, currency = entry
    if currency == "CNY":
        in_p *= CNY_PER_USD
        out_p *= CNY_PER_USD
    return input_tokens / 1e6 * in_p + output_tokens / 1e6 * out_p


def _tokens_from_message(msg) -> tuple[int, int]:
    """(input, output) token counts from an AIMessage-like object, else (0, 0)."""
    usage = getattr(msg, "usage_metadata", None)
    if isinstance(usage, dict):
        i = int(usage.get("input_tokens") or 0)
        o = int(usage.get("output_tokens") or 0)
        if i or o:
            return i, o
    meta = getattr(msg, "response_metadata", None) or {}
    if isinstance(meta, dict):
        for key in ("token_usage", "usage"):
            tu = meta.get(key)
            if isinstance(tu, dict):
                i = int(tu.get("prompt_tokens") or tu.get("input_tokens") or 0)
                o = int(tu.get("completion_tokens") or tu.get("output_tokens") or 0)
                if i or o:
                    return i, o
    return 0, 0


def _tokens_from_llm_result(response) -> tuple[int, int]:
    """Sum token usage across an LLMResult's generations.

    ``on_llm_end`` receives an ``LLMResult``; the usage metadata lives on the
    ``AIMessage`` inside ``response.generations`` (or, for some providers, at the
    top level in ``response.llm_output["token_usage"]``).
    """
    total_in = total_out = 0
    for gen_list in getattr(response, "generations", None) or []:
        for gen in gen_list or []:
            msg = getattr(gen, "message", None)
            if msg is None:
                continue
            i, o = _tokens_from_message(msg)
            total_in += i
            total_out += o
    if not (total_in or total_out):
        llm_output = getattr(response, "llm_output", None) or {}
        tu = llm_output.get("token_usage") if isinstance(llm_output, dict) else None
        if isinstance(tu, dict):
            total_in = int(tu.get("prompt_tokens") or tu.get("input_tokens") or 0)
            total_out = int(tu.get("completion_tokens") or tu.get("output_tokens") or 0)
    return total_in, total_out


class CostTracker(BaseCallbackHandler):
    """LangChain callback handler that accumulates LLM call time and tokens."""

    def __init__(self, model: str = "") -> None:
        super().__init__()
        self.model: str = model or os.getenv("LLM_MODEL", "")
        self.num_calls: int = 0
        self.input_tokens: int = 0
        self.output_tokens: int = 0
        self.total_time_s: float = 0.0
        # run_id -> start timestamp
        self.start_times: dict = {}

    def on_llm_start(self, serialized, prompts, **kwargs) -> None:
        """Record the wall-clock start time for the call identified by run_id."""
        run_id = kwargs.get("run_id")
        if run_id is not None:
            self.start_times[run_id] = time.time()

    def on_llm_end(self, response, **kwargs) -> None:
        """Accumulate latency and token usage for a completed LLM call."""
        run_id = kwargs.get("run_id")
        start = self.start_times.pop(run_id, None)
        if start is not None:
            self.total_time_s += time.time() - start
        self.num_calls += 1

        input_tokens, output_tokens = _tokens_from_llm_result(response)
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens

    def compute_cost(self, input_tokens: int, output_tokens: int) -> float:
        """USD cost estimate for the given token counts for ``self.model``."""
        return compute_cost(self.model, input_tokens, output_tokens)

    def summary(self) -> dict:
        """Return a snapshot dict of accumulated call/token/time/cost stats.

        Never raises even if usage metadata was missing (defaults to 0).
        """
        total_tokens = self.input_tokens + self.output_tokens
        return {
            "model": self.model,
            "num_llm_calls": self.num_calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": total_tokens,
            "total_time_seconds": round(self.total_time_s, 2),
            "estimated_cost_usd": round(
                self.compute_cost(self.input_tokens, self.output_tokens), 4
            ),
        }


# ---------------------------------------------------------------------------
# Active-tracker registry
# ---------------------------------------------------------------------------
# The pipeline builds more than one ChatOpenAI instance (the main model and the
# direct-mutation model). They are separate objects, so we register the single
# CostTracker here and let each construction pick it up via active_callbacks().
_ACTIVE_TRACKER: "CostTracker | None" = None


def set_active_tracker(tracker: "CostTracker | None") -> None:
    """Register the tracker so separately-constructed LLMs can share it."""
    global _ACTIVE_TRACKER
    _ACTIVE_TRACKER = tracker


def active_callbacks() -> list:
    """Callback list for a newly-constructed LLM (empty when tracking is off)."""
    return [_ACTIVE_TRACKER] if _ACTIVE_TRACKER is not None else []
