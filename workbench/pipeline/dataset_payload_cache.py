"""Reuse dataset JSON while SQLite data and configuration stay equal."""

import json
import os
from pathlib import Path
import sqlite3
import threading


class SqlitePayloadCache:
    """Keep one bounded JSON payload and one read-only SQLite connection."""

    def __init__(self, max_bytes=16 * 1024 * 1024):
        self.max_bytes = max_bytes
        self._key = None
        self._connection = None
        self._cached = None
        self._lock = threading.Lock()

    @staticmethod
    def _file(path):
        if path is None:
            return None
        value = os.stat(path)
        return (value.st_dev, value.st_ino, value.st_size,
                value.st_mtime_ns, value.st_ctime_ns)

    def _close(self):
        if self._connection is not None:
            self._connection.close()
        self._connection = None
        self._key = None
        self._cached = None

    def close(self):
        with self._lock:
            self._close()

    def _signature(self, db_path, config_path):
        return (self._file(db_path), self._file(config_path),
                self._connection.execute("PRAGMA data_version").fetchone()[0])


class DatasetPayloadCache(SqlitePayloadCache):
    """Reuse catalogue JSON. Read new-wine job states on every request."""

    def get(self, db_path, config_path, read_view, job_states):
        """Return JSON bytes. Read job state on every request."""
        db_path = os.path.abspath(db_path)
        config_path = None if config_path is None else os.path.abspath(config_path)
        with self._lock:
            try:
                identity = self._file(db_path)[:2]
                key = (db_path, config_path, identity, read_view)
                if self._key != key:
                    self._close()
                    self._connection = sqlite3.connect(
                        Path(db_path).as_uri() + "?mode=ro", uri=True, check_same_thread=False)
                    self._key = key
                signature = self._signature(db_path, config_path)
            except (OSError, sqlite3.Error):
                self._close()
                view = read_view(db_path, config_path)
                view["new_wine_index"] = job_states()
                return json.dumps(view, ensure_ascii=False).encode("utf-8")
            if self._cached is not None and self._cached[0] == signature:
                body = self._cached[1]
            else:
                self._cached = None
                view = read_view(db_path, config_path)
                # The live field follows all catalogue fields in the existing response.
                if "new_wine_index" in view:
                    view["new_wine_index"] = job_states()
                    return json.dumps(view, ensure_ascii=False).encode("utf-8")
                body = json.dumps(view, ensure_ascii=False).encode("utf-8")
                try:
                    after = self._signature(db_path, config_path)
                except (OSError, sqlite3.Error):
                    self._close()
                else:
                    if after == signature and len(body) <= self.max_bytes:
                        self._cached = (after, body)
            jobs = json.dumps(job_states(), ensure_ascii=False).encode("utf-8")
            separator = b"" if body == b"{}" else b", "
            return body[:-1] + separator + b'"new_wine_index": ' + jobs + b'}'


DATASET_PAYLOAD_CACHE = DatasetPayloadCache()
