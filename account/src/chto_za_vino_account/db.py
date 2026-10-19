"""SQLite storage with numbered schema files.

One connection serves the process. A lock serializes access, because FastAPI runs sync
handlers in a thread pool.
"""

from __future__ import annotations

import re
import sqlite3
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from importlib import resources
from pathlib import Path

SCHEMA_PACKAGE = "chto_za_vino_account.schema"
SCHEMA_FILE = re.compile(r"(\d{3})_[a-z0-9_]+\.sql")


class Database:
    def __init__(self, path: str) -> None:
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._connection.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        for pragma in (
            "PRAGMA journal_mode=WAL",
            "PRAGMA foreign_keys=ON",
            "PRAGMA secure_delete=ON",
            "PRAGMA busy_timeout=5000",
        ):
            self._connection.execute(pragma)
        self._migrate()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                yield self._connection
            except BaseException:
                self._connection.execute("ROLLBACK")
                raise
            self._connection.execute("COMMIT")

    def ping(self) -> bool:
        with self._lock:
            return self._connection.execute("SELECT 1").fetchone()[0] == 1

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def _migrate(self) -> None:
        with self.transaction() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(version INTEGER PRIMARY KEY, applied_at INTEGER NOT NULL)"
            )
            applied = {row[0] for row in db.execute("SELECT version FROM schema_migrations")}
            files = sorted(
                (int(match.group(1)), item)
                for item in resources.files(SCHEMA_PACKAGE).iterdir()
                if (match := SCHEMA_FILE.fullmatch(item.name))
            )
            expected = list(range(1, len(files) + 1))
            if [number for number, _ in files] != expected:
                raise RuntimeError("Schema files must be numbered without gaps")
            for number, item in files:
                if number in applied:
                    continue
                for statement in _statements(item.read_text(encoding="utf-8")):
                    db.execute(statement)
                db.execute(
                    "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                    (number, int(time.time())),
                )


def _statements(script: str) -> Iterator[str]:
    lines = [line for line in script.splitlines() if not line.lstrip().startswith("--")]
    for statement in "\n".join(lines).split(";"):
        if statement.strip():
            yield statement
