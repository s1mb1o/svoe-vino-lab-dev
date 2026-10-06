"""Reuse watcher counts while committed SQLite data stays equal."""

import json
import os
from pathlib import Path
import sqlite3

from dataset_payload_cache import SqlitePayloadCache


class WatcherCountCache(SqlitePayloadCache):
    """Keep one bounded count snapshot and one read-only SQLite connection."""

    def __init__(self, max_bytes=64 * 1024):
        super().__init__(max_bytes)

    @staticmethod
    def _read(conn, max_attempts, readers):
        answer = {}
        for reader in readers:
            answer.update(reader(conn, max_attempts))
        return answer

    def get(self, conn, max_attempts, readers):
        """Reuse committed counts. Preserve transactions and memory databases."""
        if conn.in_transaction:
            return self._read(conn, max_attempts, readers)
        try:
            db_path = next(path for _, name, path in conn.execute("PRAGMA database_list")
                           if name == "main")
        except (StopIteration, sqlite3.Error):
            return self._read(conn, max_attempts, readers)
        if not db_path:
            return self._read(conn, max_attempts, readers)
        db_path = os.path.abspath(db_path)
        with self._lock:
            try:
                identity = self._file(db_path)[:2]
                key = (db_path, identity, max_attempts, readers)
                if self._key != key:
                    self._close()
                    self._connection = sqlite3.connect(
                        Path(db_path).as_uri() + "?mode=ro", uri=True,
                        check_same_thread=False)
                    self._key = key
                signature = self._signature(db_path, None)
            except (OSError, sqlite3.Error):
                self._close()
                return self._read(conn, max_attempts, readers)
            if self._cached is not None and self._cached[0] == signature:
                return json.loads(self._cached[1])
            self._cached = None
            answer = self._read(self._connection, max_attempts, readers)
            body = json.dumps(answer, ensure_ascii=False).encode("utf-8")
            try:
                after = self._signature(db_path, None)
            except (OSError, sqlite3.Error):
                self._close()
            else:
                if after == signature and len(body) <= self.max_bytes:
                    self._cached = (after, body)
            return answer


WATCHER_COUNT_CACHE = WatcherCountCache()
