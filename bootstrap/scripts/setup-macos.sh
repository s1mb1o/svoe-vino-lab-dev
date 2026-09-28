#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

if [ "$(uname -m)" != "arm64" ]; then
    echo "This setup script requires Apple Silicon." >&2
    exit 1
fi
if ! command -v python3.12 >/dev/null 2>&1; then
    echo "Install Python 3.12 first. Homebrew command: brew install python@3.12" >&2
    exit 1
fi

python3.12 -m venv .venv
PIP_CACHE_DIR="$ROOT/.cache/pip" .venv/bin/python -m pip install --upgrade pip
PIP_CACHE_DIR="$ROOT/.cache/pip" .venv/bin/python -m pip install -r requirements-macos.txt
.venv/bin/python -m unittest discover -s tests -v

