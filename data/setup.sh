#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"

clone_at() {
  local repo="$1"
  local commit="$2"
  local dir="$3"
  if [ -d "$dir" ]; then
    echo "[skip] $dir already exists"
  else
    echo "[clone] $repo => $dir @ $commit"
    git clone "$repo" "$dir"
    git -C "$dir" checkout "$commit"
  fi
  # Never ship VCS metadata inside the image (also shrinks it a lot).
  rm -rf "$dir/.git"
}

clone_at "https://github.com/PyCQA/bandit.git" \
  "b46fa3a2723635aa29cc012538df4867ac2ac006" \
  "$BASE_DIR/bandit"

clone_at "https://github.com/github/codeql.git" \
  "9a4bc69843e21dbe28949d91a06881f09e90f5f0" \
  "$BASE_DIR/codeql"

clone_at "https://github.com/semgrep/semgrep-rules.git" \
  "9d73d08e70fee9fc1fd940d1378ca6c601312883" \
  "$BASE_DIR/semgrep-rules"

clone_at "https://github.com/0xdea/semgrep-rules.git" \
  "7691e35b73d1233a27e96cae5cd628c8cbc663c5" \
  "$BASE_DIR/semgrep-rules-0xdea"

clone_at "https://github.com/spotbugs/spotbugs.git" \
  "e463e395154932a4827ba43204336c35870763cc" \
  "$BASE_DIR/spotbugs"

echo "[done] all repositories cloned"
