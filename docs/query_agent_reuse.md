# Reusing the QueryAgent

The **QueryAgent** is the retrieval stage of S-MRVA. Given a target predicate and
a logic tree annotated with code, it generates GitHub Code Search queries,
searches real repositories, evaluates the candidates with an LLM, and returns
**real-world code snippets** as *false-negative* (FN) and *false-positive* (FP)
exemplars. These snippets are the raw material the synthesis stage splices into
realistic rule variants.

Module: `src/agents/query_agent_api.py`
Prompt guidance: `src/prompts/code_search_api.md`

You can reuse it on its own — you do **not** need the rest of the pipeline.

---

## 1. Interface

```python
find_code_snippets(
    llm: BaseChatModel,
    language: str,
    target_predicate: str,
    logic_tree_with_code: dict,
    target_cnt: int = 5,
    max_iterations: int = 5,
    callback_handler=None,
    skip_refine_pipeline: bool | None = None,
) -> dict
```

| Argument | Meaning |
|---|---|
| `llm` | Any LangChain chat model (use `agents.model.llm`). |
| `language` | Search language: `java`, `python`, `c`, … |
| `target_predicate` | Short human description of what to retrieve (one predicate). |
| `logic_tree_with_code` | The predicate plus concrete code strings to search for. |
| `target_cnt` | Desired number of snippets **per direction** (FN and FP). |
| `max_iterations` | Max generate→search→evaluate rounds. |
| `callback_handler` | Optional LangChain callbacks (e.g. tracing). |
| `skip_refine_pipeline` | Overrides `QUERY_AGENT_SKIP_REFINE_PIPELINE`. |

`logic_tree_with_code` is intentionally loose, but include the concrete API
tokens you want to find:

```python
logic_tree_with_code = {
    "condition": 'Environment.put(Context.SECURITY_AUTHENTICATION, "none")',
    "patterns": ["Context.SECURITY_AUTHENTICATION", '"none"', "new InitialDirContext"],
}
```

## 2. Return value

```jsonc
{
  "target_predicate": "...",
  "language": "java",
  "logic_tree_with_code": { ... },
  "current_cnt": 6,
  "target_cnt": 10,
  "saved_code_snippets": [ ... ],
  "false_negative_examples": [ ... ],   // snippets that LOOK vulnerable but likely bypass the rule
  "false_positive_examples": [ ... ],   // snippets the rule may wrongly flag
  "search_iterations": 2,
  "max_iterations": 5,
  "last_query": { "false_negative": ["..."], "false_positive": ["..."] }
}
```

Each example carries the snippet code, its repository/URL, and the search
provenance. The synthesis stage consumes `false_negative_examples` and
`false_positive_examples`; for standalone use, those two lists are usually all
you need.

## 3. Configuration

Set these in `.env` (see `.env.example`). Only the GitHub token and the LLM key
are strictly required.

> **LLM vs embedding credentials are separate.** The LLM is configured with
> `LLM_MODEL` / `LLM_API_KEY` / `LLM_BASE_URL` (falling back to `DASHSCOPE_*`),
> but the `qwen` embedding path reads `DASHSCOPE_API_KEY` / `DASHSCOPE_BASE_URL`
> **directly**. To use a non-DashScope LLM (e.g. DeepSeek) set
> `EMBED_MODEL=codet5p` so embeddings stay local; to keep DashScope embeddings
> from outside mainland China, use the Singapore endpoint
> `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` with a
> Singapore-region key (keys are region-bound). See the README's
> [R1. Use a different LLM backend](../README.md#r1-use-a-different-llm-backend) section.

| Variable | Default | Purpose |
|---|---|---|
| `GITHUB_TOKENS` | — | Comma-separated GitHub tokens (or `GITHUB_TOKEN`, or `GITHUB_TOKEN_FILE`). |
| `GITHUB_API_BASE` | `https://api.github.com` | API endpoint (GitHub Enterprise). |
| `GITHUB_MAX_TOKENS` | `1` | How many tokens to rotate over per run. |
| `GITHUB_MIN_REQUEST_INTERVAL` | `2.0` | Min seconds between requests. |
| `GITHUB_TOKEN_RPM_LIMIT` | `30` | Per-token request budget. |
| `API_CODE_SEARCH_MODE` | `auto` | `direct` \| `server` \| `auto` (see §4). |
| `EMBED_MODEL` | `codet5p` | `codet5p` (local) or `qwen` (DashScope API) for snippet dedup. |
| `EMBED_QWEN_MODEL` | `text-embedding-v4` | DashScope embedding model. |
| `EMBED_SIM_THRESHOLD` | `0.60` | Cluster/merge threshold for deduplication. |
| `QUERY_AGENT_SKIP_REFINE_PIPELINE` | `1` | `1` = single search pass (faster). |
| `QUERY_REFINE_MAX_TURNS` | `0` | Extra query-refinement turns. |
| `API_CODE_SEARCH_FETCH_FULL_CONTENT` | `0` | Fetch full file contents (slower, more context). |
| `DASHSCOPE_API_KEY` / `LLM_API_KEY` | — | LLM key (`LLM_API_KEY` overrides). |
| `LLM_MODEL` / `LLM_BASE_URL` | `qwen3.5-plus` / DashScope | Any OpenAI-compatible provider. |
| `SAT_WORK_DIR` | — | Project root (must be set; used to resolve resources). |

## 4. The code-search server (why you should run it)

All GitHub search goes through `src/tools/api_code_search.py`, which routes by
`API_CODE_SEARCH_MODE`:

- `direct` — call the GitHub API in-process.
- `server` — talk to the rate-limit/token-pool server over a Unix socket
  `/tmp/api_code_search.sock`; **raises if the server is not running**.
- `auto` (default) — use the server if reachable, otherwise fall back to direct.

The server multiplexes tokens and enforces rate limits across concurrent jobs,
which is what keeps long runs from being blocked. Start it manually:

```bash
python3 -m src.tools.api_code_search_server &     # listens on /tmp/api_code_search.sock
```

In Docker it is started **automatically** by `docker-entrypoint.sh` whenever
`GITHUB_TOKENS`/`GITHUB_TOKEN` is set.

## 5. Running it standalone

You only need `src/` on `PYTHONPATH` and the server running. Verify your
LLM/embedding configuration first with `python3 src/agents/check_env.py`.

```bash
# from the repository root
PYTHONPATH=src python3 - <<'PY'
import json
from agents.model import llm
from agents.query_agent_api import find_code_snippets

result = find_code_snippets(
    llm=llm,
    language="java",
    target_predicate="anonymous LDAP bind (authentication set to none)",
    logic_tree_with_code={
        "condition": 'Environment.put(Context.SECURITY_AUTHENTICATION, "none")',
        "patterns": ["Context.SECURITY_AUTHENTICATION", '"none"', "new InitialDirContext"],
    },
    target_cnt=3,
    max_iterations=1,
)

print(json.dumps({
    "fn": len(result.get("false_negative_examples", [])),
    "fp": len(result.get("false_positive_examples", [])),
    "search_iterations": result.get("search_iterations"),
    "last_query": result.get("last_query"),
}, indent=2))
PY
```

> `python3 src/agents/query_agent_api.py` also works, but its demo block imports
> `langfuse`, which is **not** in `requirements.txt`; prefer the script above.

## 6. Notes and limitations

- **Non-deterministic.** LLM query generation + live GitHub search mean repeated
  runs return different snippets.
- **Rate limits.** The GitHub Code Search API has a low secondary rate limit; on
  a hit the pipeline **blocks and waits** (often ~2 h+ for one case). The server
  helps by rotating tokens.
- **No tokens?** The synthesis stage can bypass search entirely
  (`LLM_DIRECT_MUTATION=1`), but this QueryAgent itself needs GitHub access.
