"""Command line entry points.

  chto-za-vino-account                 run the service
  chto-za-vino-account max-key         read the MAX bot token from stdin and print MAX_WEBAPP_KEY
  chto-za-vino-account backup <file>   write a consistent copy of ACCOUNT_DATABASE to <file>
"""

from __future__ import annotations

import logging
import os
import sqlite3
import sys
from pathlib import Path

import uvicorn

from .api import create_app
from .config import Settings
from .max_launch import derive_key


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args == ["max-key"]:
        token = sys.stdin.readline().strip()
        if not token:
            print("Send the MAX bot token on stdin", file=sys.stderr)
            return 2
        print(derive_key(token).hex())
        return 0
    if len(args) == 2 and args[0] == "backup":
        return backup(os.environ.get("ACCOUNT_DATABASE", "data/account.sqlite3"), args[1])
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    settings = Settings.from_env()
    uvicorn.run(
        create_app(settings),
        host=settings.host,
        port=settings.port,
        access_log=False,
        proxy_headers=False,
        server_header=False,
        log_level="info",
    )
    return 0


def backup(database: str, target: str) -> int:
    """Copy the live database with the SQLite online backup API. Never overwrite a file."""
    source_path = Path(database)
    target_path = Path(target)
    if not source_path.is_file():
        print(f"No database at {source_path}", file=sys.stderr)
        return 1
    if target_path.exists():
        print(f"{target_path} exists; choose a new file name", file=sys.stderr)
        return 1
    target_path.parent.mkdir(parents=True, exist_ok=True)
    partial = target_path.with_name(target_path.name + ".partial")
    source = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True)
    try:
        copy = sqlite3.connect(partial)
        try:
            source.backup(copy)
        finally:
            copy.close()
    finally:
        source.close()
    partial.chmod(0o600)
    partial.rename(target_path)
    print(target_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
