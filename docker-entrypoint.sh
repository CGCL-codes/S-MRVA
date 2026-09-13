#!/bin/bash
set -e

# Start the code search server in the background if GitHub tokens are available
if [ -n "$GITHUB_TOKENS" ] || [ -n "$GITHUB_TOKEN" ]; then
    echo "[entrypoint] Starting code search server..."
    python3 -m src.tools.api_code_search_server &
    SERVER_PID=$!
    sleep 5
    if kill -0 $SERVER_PID 2>/dev/null; then
        echo "[entrypoint] Code search server started (PID $SERVER_PID)."
    else
        echo "[entrypoint] Code search server failed to start (invalid tokens?)."
    fi
else
    echo "[entrypoint] Skipping code search server (no GitHub tokens set)."
fi

# Exec the requested command (default: bash)
exec "$@"
