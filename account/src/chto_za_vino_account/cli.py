"""Command line entry points.

  chto-za-vino-account                 run the service
  chto-za-vino-account max-key         read the MAX bot token from stdin and print MAX_WEBAPP_KEY
  chto-za-vino-account backup <file>   write a consistent copy of ACCOUNT_DATABASE to <file>
  chto-za-vino-account merge --keep <username> --remove <username>
                                       move the login methods of one account to another account
                                       and delete the first account (operator action)
"""

from __future__ import annotations

import contextlib
import logging
import os
import sqlite3
import sys
import tempfile
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
    if len(args) == 5 and args[0] == "merge" and args[1] == "--keep" and args[3] == "--remove":
        return merge(os.environ.get("ACCOUNT_DATABASE", "data/account.sqlite3"), args[2], args[4])
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


BACKUP_TEMP_PREFIX = ".backup-"


def backup(database: str, target: str) -> int:
    """Copy the live database with the SQLite online backup API.

    The copy goes to a unique temporary file (mode 0600) in the target directory. A hard link
    publishes it: the link fails when the target exists, so a backup never overwrites a file,
    also when two backups run at the same time. The temporary file is removed in every case.
    """
    source_path = Path(database)
    target_path = Path(target)
    if not source_path.is_file():
        print(f"No database at {source_path}", file=sys.stderr)
        return 1
    if target_path.exists():
        print(f"{target_path} exists; choose a new file name", file=sys.stderr)
        return 1
    target_path.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(
        prefix=BACKUP_TEMP_PREFIX, suffix=".tmp", dir=target_path.parent
    )
    os.close(handle)
    temp_path = Path(temp_name)
    try:
        source = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True)
        try:
            copy = sqlite3.connect(temp_path)
            try:
                source.backup(copy)
            finally:
                copy.close()
        finally:
            source.close()
        try:
            os.link(temp_path, target_path)
        except FileExistsError:
            print(f"{target_path} exists; choose a new file name", file=sys.stderr)
            return 1
    except sqlite3.Error as error:
        print(f"Backup failed: {type(error).__name__}", file=sys.stderr)
        return 1
    finally:
        with contextlib.suppress(FileNotFoundError):
            temp_path.unlink()
    print(target_path)
    return 0



def merge(database: str, keep: str, remove: str) -> int:
    """Join two accounts of one person: an operator action for accounts made before the email rule.

    The login methods (identities) of `remove` move to `keep`, then `remove` is deleted with its
    sessions and pending records. The command stops without a change when `keep` already has a
    login method of the same provider: an account has at most one identity for each provider.
    Back up the database first. Diary data does not exist yet; move it here when it does.
    """
    path = Path(database)
    if not path.is_file():
        print(f"No database at {path}", file=sys.stderr)
        return 1
    db = sqlite3.connect(path, isolation_level=None)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("BEGIN IMMEDIATE")
        users = {
            row["username"]: row["id"]
            for row in db.execute(
                "SELECT id, username FROM users WHERE username IN (?, ?)", (keep, remove)
            )
        }
        if keep == remove or keep not in users or remove not in users:
            db.execute("ROLLBACK")
            print("Give two different existing usernames", file=sys.stderr)
            return 1
        keep_id, remove_id = users[keep], users[remove]
        kept = {row["provider"] for row in db.execute(
            "SELECT provider FROM identities WHERE user_id = ?", (keep_id,))}
        moving = [row["provider"] for row in db.execute(
            "SELECT provider FROM identities WHERE user_id = ?", (remove_id,))]
        clash = sorted(kept.intersection(moving))
        if clash:
            db.execute("ROLLBACK")
            print(f"{keep} already has: {', '.join(clash)}; nothing changed", file=sys.stderr)
            return 1
        db.execute("UPDATE identities SET user_id = ? WHERE user_id = ?", (keep_id, remove_id))
        db.execute("DELETE FROM users WHERE id = ?", (remove_id,))
        db.execute("COMMIT")
    except sqlite3.Error as error:
        if db.in_transaction:
            db.execute("ROLLBACK")
        print(f"Merge failed: {type(error).__name__}", file=sys.stderr)
        return 1
    finally:
        db.close()
    print(f"Merged {remove} into {keep}: moved {', '.join(sorted(moving)) or 'nothing'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
