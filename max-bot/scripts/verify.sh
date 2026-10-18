#!/bin/sh
set -eu

uv lock --check
uv sync --frozen --extra dev
uv run ruff check .
# The shared modules must match telegram-bot when the sibling directory is present.
if [ -d ../telegram-bot ]; then
    uv run python scripts/sync_shared.py --check
fi
uv run pytest -q
uv run chto-za-vino-max-host-demo
# The shared core of both bots.
if [ -d ../im-core ]; then
    (cd ../im-core && uv lock --check && uv sync --frozen --extra dev \
        && uv run ruff check . && uv run pytest -q)
fi
