#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

if [ "$(uname -m)" != "x86_64" ]; then
    echo "This setup script requires x86_64 Linux." >&2
    exit 1
fi
if ! command -v nvidia-smi >/dev/null 2>&1; then
    echo "nvidia-smi is required." >&2
    exit 1
fi
if ! command -v python3.12 >/dev/null 2>&1; then
    echo "Python 3.12 is required." >&2
    exit 1
fi

python3.12 -m venv .venv
PIP_CACHE_DIR="$ROOT/.cache/pip" .venv/bin/python -m pip install --upgrade pip
PIP_CACHE_DIR="$ROOT/.cache/pip" .venv/bin/python -m pip install -r requirements-common.txt
PIP_CACHE_DIR="$ROOT/.cache/pip" .venv/bin/python -m pip install \
    --index-url https://download.pytorch.org/whl/cu130 \
    torch==2.11.0 torchvision==0.26.0
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -c 'import torch; assert torch.cuda.is_available(); print(torch.cuda.get_device_name(0))'

