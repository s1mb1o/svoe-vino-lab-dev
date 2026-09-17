#!/usr/bin/env bash
# Finish the test set: top-up the short wines, cross-check with the official
# recognizer, then write my/ and the reports.
#
# The cloud backends need QWEN_API_KEY and DASHSCOPE_API_KEY in the environment.
# Read them from the login shell; never put a key on a command line.
set -euo pipefail
cd "$(dirname "$0")/.."

: "${BACKENDS:=local:8,tokenplan:8,dashscope:6}"
export QWEN_API_KEY="${QWEN_API_KEY:-$(zsh -ic 'printf %s "$QWEN_API_KEY"' 2>/dev/null)}"
export DASHSCOPE_API_KEY="${DASHSCOPE_API_KEY:-$(zsh -ic 'printf %s "$DASHSCOPE_API_KEY"' 2>/dev/null)}"

echo "== top-up: reopen wines with fewer than 3 photos =="
python3 scripts/06_topup.py --need 3 --redownload

echo "== deeper download and embedding for the reopened wines =="
python3 scripts/run_pipeline.py --stages 23 --chunk 400 --per-wine 40 --dl-workers 40

echo "== deeper verification for the reopened wines =="
python3 scripts/run_pipeline.py --stages 4 --chunk 400 --top 20 --backends "$BACKENDS"

echo "== cross-check every accepted photo with the official recognizer =="
python3 scripts/07_api_check.py --workers 4

echo "== build my/ and the reports =="
python3 scripts/05_report.py --keep 4

echo "done"
