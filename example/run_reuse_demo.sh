#!/bin/bash
# ============================================================================
# S-MRVA — Reusable-badge demo
#
# Exercises everything a reuser needs, in ONE run:
#   1. LLM backend       BACKEND=qwen|deepseek|openai|openrouter|siliconflow|moonshot
#                        (or set LLM_BASE_URL / LLM_API_KEY / LLM_MODEL directly)
#   2. Ablation setting  ABLATION=full|no-code-search|no-refine
#   3. Sensitivity       B_HIGH=<int> (LOGIC_TREE_B_HIGH)   TAU=<0..1> (EMBED_SIM_THRESHOLD)
#   4. Time & cost       ENABLE_COST_TRACKING=1 (on by default here)
#
# Usage (repo root, on the host or inside the image):
#   bash example/run_reuse_demo.sh
#   BACKEND=deepseek ABLATION=no-code-search B_HIGH=3 TAU=0.4 bash example/run_reuse_demo.sh
#   DRY_RUN=1 bash example/run_reuse_demo.sh            # print resolved config only
#
# Override the target with RULE_ID / RULE_LANGUAGE / ANALYZER / BASE_DIR / ARTIFACTS_DIR.
# Any extra arguments are forwarded to src/agents/pipeline_agent.py.
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

# Values passed explicitly by the caller win over .env and over BACKEND presets.
_PRE_LLM_BASE_URL="${LLM_BASE_URL:-}"
_PRE_LLM_API_KEY="${LLM_API_KEY:-}"
_PRE_LLM_MODEL="${LLM_MODEL:-}"

# ---- load .env (if present) ------------------------------------------------
if [ -f .env ]; then
    set -a
    . ./.env
    set +a
fi

# ---- user knobs (all overridable from the environment) ---------------------
BACKEND="${BACKEND:-}"                    # empty -> use .env as-is
ABLATION="${ABLATION:-full}"              # full | no-code-search | no-refine
B_HIGH="${B_HIGH:-}"                      # -> LOGIC_TREE_B_HIGH   (default 5)
TAU="${TAU:-}"                            # -> EMBED_SIM_THRESHOLD (default 0.60)
DRY_RUN="${DRY_RUN:-0}"

RULE_ID="${RULE_ID:-anonymous-ldap-bind}"
RULE_LANGUAGE="${RULE_LANGUAGE:-java}"
ANALYZER="${ANALYZER:-semgrep}"
BASE_DIR="${BASE_DIR:-dataset/semgrep-rules}"
ARTIFACTS_DIR="${ARTIFACTS_DIR:-example/run_output}"

# ---- 1. LLM backend preset -------------------------------------------------
NEEDS_KEY=0
case "$BACKEND" in
    ""|qwen|dashscope)
        # qwen is the default; .env normally sets DASHSCOPE_* already.
        ;;
    deepseek)
        export LLM_BASE_URL="https://api.deepseek.com"
        export LLM_MODEL="deepseek-flash"
        export EMBED_MODEL="${EMBED_MODEL:-codet5p}"
        NEEDS_KEY=1
        ;;
    openai)
        export LLM_BASE_URL="https://api.openai.com/v1"
        export LLM_MODEL="gpt-4o-mini"
        export EMBED_MODEL="${EMBED_MODEL:-codet5p}"
        NEEDS_KEY=1
        ;;
    openrouter)
        export LLM_BASE_URL="https://openrouter.ai/api/v1"
        export LLM_MODEL="deepseek/deepseek-chat"
        export EMBED_MODEL="${EMBED_MODEL:-codet5p}"
        NEEDS_KEY=1
        ;;
    siliconflow)
        export LLM_BASE_URL="https://api.siliconflow.com/v1"
        export LLM_MODEL="deepseek-ai/DeepSeek-V3"
        export EMBED_MODEL="${EMBED_MODEL:-codet5p}"
        NEEDS_KEY=1
        ;;
    moonshot)
        export LLM_BASE_URL="https://api.moonshot.ai/v1"
        export LLM_MODEL="moonshot-v1-8k"
        export EMBED_MODEL="${EMBED_MODEL:-codet5p}"
        NEEDS_KEY=1
        ;;
    *)
        echo "ERROR: unknown BACKEND='$BACKEND'." >&2
        echo "       choose one of: qwen deepseek openai openrouter siliconflow moonshot" >&2
        exit 2
        ;;
esac

# Caller-provided LLM_* values take precedence over the preset and .env.
if [ -n "$_PRE_LLM_BASE_URL" ]; then export LLM_BASE_URL="$_PRE_LLM_BASE_URL"; fi
if [ -n "$_PRE_LLM_API_KEY" ]; then export LLM_API_KEY="$_PRE_LLM_API_KEY"; fi
if [ -n "$_PRE_LLM_MODEL" ]; then export LLM_MODEL="$_PRE_LLM_MODEL"; fi

# ---- 2. ablation setting ---------------------------------------------------
case "$ABLATION" in
    full)
        export LLM_DIRECT_MUTATION=0
        export ENABLE_LOGIC_TREE_REFINEMENT=1
        ;;
    no-code-search)
        export LLM_DIRECT_MUTATION=1
        export ENABLE_LOGIC_TREE_REFINEMENT=1
        ;;
    no-refine)
        export LLM_DIRECT_MUTATION=0
        export ENABLE_LOGIC_TREE_REFINEMENT=0
        ;;
    *)
        echo "ERROR: unknown ABLATION='$ABLATION'." >&2
        echo "       choose one of: full no-code-search no-refine" >&2
        exit 2
        ;;
esac

# ---- 3. parameter sensitivity ----------------------------------------------
if [ -n "$B_HIGH" ]; then export LOGIC_TREE_B_HIGH="$B_HIGH"; fi
if [ -n "$TAU" ]; then export EMBED_SIM_THRESHOLD="$TAU"; fi

# ---- 4. time & cost tracking -----------------------------------------------
export ENABLE_COST_TRACKING=1
export SAT_WORK_DIR="${SAT_WORK_DIR:-$PWD}"

# ---- report the resolved configuration -------------------------------------
mask() {
    local v="${1:-}"
    if [ -n "$v" ]; then echo "${v:0:4}****${v: -4}"; else echo "(unset)"; fi
}

if [ "$NEEDS_KEY" = 1 ] && [ -z "${LLM_API_KEY:-}" ]; then
    echo "WARNING: BACKEND=$BACKEND asks for LLM_API_KEY (the qwen embedding fallback" >&2
    echo "         does not apply to the LLM). Set it in .env or the environment." >&2
fi

echo "============================================"
echo " S-MRVA reusable-badge demo"
echo "--------------------------------------------"
echo " backend        : ${BACKEND:-<from .env>}"
echo " LLM_MODEL      : ${LLM_MODEL:-<unset>}"
echo " LLM_BASE_URL   : ${LLM_BASE_URL:-${DASHSCOPE_BASE_URL:-<unset>}}"
echo " LLM_API_KEY    : $(mask "${LLM_API_KEY:-${DASHSCOPE_API_KEY:-}}")"
echo " EMBED_MODEL    : ${EMBED_MODEL:-<unset>}"
echo " ablation       : $ABLATION (LLM_DIRECT_MUTATION=$LLM_DIRECT_MUTATION, ENABLE_LOGIC_TREE_REFINEMENT=$ENABLE_LOGIC_TREE_REFINEMENT)"
echo " sensitivity    : LOGIC_TREE_B_HIGH=${LOGIC_TREE_B_HIGH:-5}, EMBED_SIM_THRESHOLD=${EMBED_SIM_THRESHOLD:-0.60}"
echo " cost tracking  : ENABLE_COST_TRACKING=$ENABLE_COST_TRACKING"
echo " target rule    : $RULE_ID ($RULE_LANGUAGE / $ANALYZER)"
echo " output dir     : $ARTIFACTS_DIR/$RULE_ID/"
echo "============================================"
echo

if [ "$DRY_RUN" = "1" ]; then
    echo "(DRY_RUN=1) configuration resolved; pipeline not executed."
    exit 0
fi

python3 src/agents/pipeline_agent.py \
    --rule_id "$RULE_ID" \
    --language "$RULE_LANGUAGE" \
    --analyzer "$ANALYZER" \
    --base_dir "$BASE_DIR" \
    --artifacts_dir "$ARTIFACTS_DIR" \
    "$@"

echo
echo "Done."
echo "Time / token / cost summary:"
echo "  $ARTIFACTS_DIR/$RULE_ID/pipeline_summary_$RULE_ID.json   -> key \"cost\""
