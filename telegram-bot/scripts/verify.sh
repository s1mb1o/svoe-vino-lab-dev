#!/bin/sh
set -eu

uv lock --check
uv sync --frozen --extra dev
uv run ruff check .
uv run pytest -q
uv run chto-za-vino-host-demo
