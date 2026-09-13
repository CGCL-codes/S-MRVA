#!/bin/bash

set -u

BASE_DIR="${BASE_DIR:-dataset/semgrep-rules}"
RULE_LANGUAGE="${RULE_LANGUAGE:-java}"
ANALYZER="${ANALYZER:-semgrep}"
OUTPUT_DIR="${OUTPUT_DIR:-output/semgrep-rules}"
DRY_RUN=0
NUM_WORKERS=5
INTERVAL_SECONDS="${INTERVAL_SECONDS:-300}"  # worker stagger in seconds (default 5 min)

while [[ $# -gt 0 ]]; do
	case "$1" in
		-n|--dry-run)
			DRY_RUN=1
			shift
			;;
		-w|--workers)
			NUM_WORKERS="$2"
			shift 2
			;;
		-h|--help)
			echo "Usage: $0 [-n|--dry-run] [-w|--workers NUM]"
			echo "  -n, --dry-run      Print commands only, do not execute"
			echo "  -w, --workers NUM  Number of parallel workers (default: 5)"
			exit 0
			;;
		*)
			echo "Unknown argument: $1"
			echo "Usage: $0 [-n|--dry-run] [-w|--workers NUM]"
			exit 1
			;;
	esac
done

if [[ ! -d "$BASE_DIR" ]]; then
	echo "Error: base directory not found: $BASE_DIR"
	exit 1
fi

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

TOTAL=0
PASSED=0
FAILED=0
SKIPPED=0

echo "Running semgrep with $NUM_WORKERS parallel workers from: $BASE_DIR"
echo "Each worker will start with a ${INTERVAL_SECONDS}s interval"
if [[ $DRY_RUN -eq 1 ]]; then
	echo "Dry-run mode enabled: commands will be printed, not executed"
fi

# Collect all rules into an array
declare -a rules
for rule_path in "$BASE_DIR"/*/; do
	[[ -d "$rule_path" ]] || continue
	rule_id="$(basename "$rule_path")"
	rules+=("$rule_id")
done

TOTAL=${#rules[@]}
echo "Found $TOTAL rules to process"

# Function to process rules for a specific worker
process_worker() {
	local worker_id=$1
	local start_index=$2
	local worker_passed=0
	local worker_failed=0
	local worker_skipped=0

	# Sleep for staggered start
	if [[ $worker_id -gt 0 ]]; then
		local sleep_time=$((worker_id * INTERVAL_SECONDS))
		echo "[Worker $worker_id] Waiting ${sleep_time}s before starting..."
		if [[ $DRY_RUN -eq 0 ]]; then
			sleep "$sleep_time"
		fi
	fi

	echo "[Worker $worker_id] Starting at $(date '+%Y-%m-%d %H:%M:%S')"

	# Process every NUM_WORKERS-th rule starting from start_index
	for ((idx = start_index; idx < ${#rules[@]}; idx += NUM_WORKERS)); do
		rule_id="${rules[$idx]}"
		rule_output_dir="$OUTPUT_DIR/$rule_id"
		local rule_num=$((idx + 1))

		# Skip if output directory already exists for this rule
		if [[ -d "$rule_output_dir" ]]; then
			echo "[Worker $worker_id] [$rule_num/$TOTAL] SKIP: $rule_id"
			((worker_skipped++))
			continue
		fi

		echo "[Worker $worker_id] [$rule_num/$TOTAL] Testing rule: $rule_id"

		if [[ $DRY_RUN -eq 1 ]]; then
			echo "[Worker $worker_id] [$rule_num/$TOTAL] DRY-RUN: would execute python3 src/agents/pipeline_agent.py --rule_id=$rule_id --language=$RULE_LANGUAGE --analyzer=$ANALYZER --base_dir=$BASE_DIR --artifacts_dir=$OUTPUT_DIR"
		else
			if python3 src/agents/pipeline_agent.py \
				--rule_id "$rule_id" \
				--language="$RULE_LANGUAGE" \
				--analyzer="$ANALYZER" \
				--base_dir="$BASE_DIR" \
				--artifacts_dir="$OUTPUT_DIR"; then
				((worker_passed++))
				echo "[Worker $worker_id] [$rule_num/$TOTAL] PASS: $rule_id"
			else
				((worker_failed++))
				echo "[Worker $worker_id] [$rule_num/$TOTAL] FAIL: $rule_id"
			fi
		fi
	done

	echo "[Worker $worker_id] Completed at $(date '+%Y-%m-%d %H:%M:%S'): Passed=$worker_passed Failed=$worker_failed Skipped=$worker_skipped"
}

if [[ $DRY_RUN -eq 1 ]]; then
	echo "DRY-RUN MODE: Showing what would happen without waiting or executing..."
	echo ""
	# Run workers sequentially in dry-run mode to show plan
	for ((w = 0; w < NUM_WORKERS; w++)); do
		process_worker "$w" "$w"
		echo ""
	done
	exit 0
fi

# Start workers in background
declare -a pids
for ((w = 0; w < NUM_WORKERS; w++)); do
	process_worker "$w" "$w" &
	pids+=($!)
done

echo "Started $NUM_WORKERS workers: ${pids[*]}"
echo ""

# Wait for all workers to complete
failed_workers=0
for ((w = 0; w < ${#pids[@]}; w++)); do
	pid=${pids[$w]}
	if wait "$pid"; then
		echo "Worker $w (PID $pid) completed successfully"
	else
		echo "Worker $w (PID $pid) exited with error"
		((failed_workers++))
	fi
done

echo ""
echo "All workers completed at $(date '+%Y-%m-%d %H:%M:%S')"
echo "Total rules: $TOTAL"

if [[ $failed_workers -gt 0 ]]; then
	echo "Warning: $failed_workers workers exited with errors"
	exit 1
fi
