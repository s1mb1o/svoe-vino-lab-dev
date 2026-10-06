"""Reuse one Testset response while its SQLite data stays equal."""

from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3

from dataset_payload_cache import SqlitePayloadCache
import testsets


class TestsetPayloadCache(SqlitePayloadCache):
    """Keep one bounded JSON payload and one read-only SQLite connection."""

    @staticmethod
    def _read(db_path, set_name, open_database, card_images):
        with closing(open_database(db_path)) as conn:
            view = testsets.set_view(conn, set_name, card_images)
        return json.dumps(view, ensure_ascii=False).encode("utf-8")

    def get(self, db_path, set_name, open_database, card_images):
        """Return exact JSON bytes. Check database commits on every request."""
        db_path = os.path.abspath(db_path)
        with self._lock:
            try:
                identity = self._file(db_path)[:2]
                key = (db_path, identity, set_name, open_database, card_images,
                       testsets.set_view)
                if self._key != key:
                    self._close()
                    self._connection = sqlite3.connect(
                        Path(db_path).as_uri() + "?mode=ro", uri=True,
                        check_same_thread=False)
                    self._key = key
                signature = self._signature(db_path, None)
            except (OSError, sqlite3.Error):
                self._close()
                return self._read(db_path, set_name, open_database, card_images)
            if self._cached is not None and self._cached[0] == signature:
                return self._cached[1]
            self._cached = None
            body = self._read(db_path, set_name, open_database, card_images)
            try:
                after = self._signature(db_path, None)
            except (OSError, sqlite3.Error):
                self._close()
            else:
                if after == signature and len(body) <= self.max_bytes:
                    self._cached = (after, body)
            return body


TESTSET_PAYLOAD_CACHE = TestsetPayloadCache()
