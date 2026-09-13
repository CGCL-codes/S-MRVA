#!/bin/bash
# ============================================================================
# Example: Run the pipeline on a single Semgrep Java rule
# Usage: bash example/run_semgrep_example.sh
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

if [ -f .env ]; then
    set -a && source .env && set +a
fi

export SAT_WORK_DIR="${SAT_WORK_DIR:-$PWD}"

RULE_ID="${1:-anonymous-ldap-bind}"
LANGUAGE="${2:-java}"
ANALYZER="${3:-semgrep}"
BASE_DIR="dataset/semgrep-rules"
ARTIFACTS_DIR="example/run_output"

echo "============================================"
echo " Running Pipeline Agent for: $RULE_ID"
echo " Language: $LANGUAGE | Analyzer: $ANALYZER"
echo " Base Dir: $BASE_DIR"
echo " Output:   $ARTIFACTS_DIR/$RULE_ID/"
echo "============================================"
echo

python3 src/agents/pipeline_agent.py \
  --rule_id "$RULE_ID" \
  --language "$LANGUAGE" \
  --analyzer "$ANALYZER" \
  --base_dir "$BASE_DIR" \
  --artifacts_dir "$ARTIFACTS_DIR"

echo
echo "============================================"
echo " Pipeline complete!"
echo " Report:  $ARTIFACTS_DIR/$RULE_ID/pipeline_report_$RULE_ID.md"
echo " Summary: $ARTIFACTS_DIR/$RULE_ID/pipeline_summary_$RULE_ID.json"
echo "============================================"
