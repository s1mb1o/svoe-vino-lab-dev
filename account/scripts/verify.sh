#!/bin/sh
set -eu

cd "$(dirname "$0")/.."
uv lock --check
uv sync --frozen --extra dev
uv run ruff check .
uv run pytest -q
