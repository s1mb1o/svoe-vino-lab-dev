"""Reuse an Embedding view after its data, files, jobs, and queue are checked."""

import json
import hashlib
import marshal
import os
from pathlib import Path
import sqlite3

from dataset_payload_cache import SqlitePayloadCache
import embeddings
import labdb
import summary_cache

_SOURCE_ROOT = Path(__file__).parent
_SOURCE_FILES = sorted(_SOURCE_ROOT.glob("*.py")) + sorted((_SOURCE_ROOT / "schema").glob("*.sql"))
_SOURCE_REVISION = hashlib.sha256(b"".join(
    str(path.relative_to(_SOURCE_ROOT)).encode() + b"\0" + hashlib.sha256(path.read_bytes()).digest()
    for path in _SOURCE_FILES)).hexdigest()


class EmbeddingViewCache(SqlitePayloadCache):
    """Keep one bounded JSON snapshot. Return an independent view to each caller."""

    def __init__(self, max_bytes=16 * 1024 * 1024, *, disk_kind=None, cache_directory=None):
        super().__init__(max_bytes)
        self.disk_kind = disk_kind
        self.cache_directory = cache_directory

    def _disk_identity(self, settings, name, settings_key, signature, readers):
        if self.disk_kind is None:
            return None
        codes = []
        for reader in readers:
            code = getattr(reader, "__code__", None)
            if code is None:
                return None
            codes.append(hashlib.sha256(marshal.dumps(code)).hexdigest())
        # A connection-local data_version cannot identify a saved snapshot.
        # Database and WAL file identities check commits across connections.
        try:
            wal = self._optional_file(settings.db_path + "-wal")
        except OSError:
            return None
        return (settings.db_path, name, settings_key, self._disk_inputs(signature),
                wal, _SOURCE_REVISION,
                sqlite3.sqlite_version, codes)

    def _disk_inputs(self, signature):
        return signature[0][:2], signature[1:]

    def _disk_directory(self, settings):
        return self.cache_directory or os.path.join(
            labdb.data_root(settings.db_path), "cache", "embedding-views")

    def _optional_file(self, path):
        try:
            return self._file(path)
        except FileNotFoundError:
            return None

    def _inputs(self, settings, name, job, queue):
        names = ([name] if name is not None else
                 [label for label, entry, _ in settings.entries if entry is not None])
        files = []
        jobs = []
        for label in names:
            directory = embeddings.entry_dir(settings.db_path, label)
            files.append((label, self._optional_file(directory),
                          self._optional_file(os.path.join(directory, embeddings.INDEX)),
                          self._optional_file(os.path.join(directory, embeddings.IMAGES))))
            if name is not None:
                try:
                    with os.scandir(directory) as entries:
                        vectors = sorted(entry.name for entry in entries
                                         if embeddings.VECTORS_RE.match(entry.name))
                except FileNotFoundError:
                    vectors = []
                files.append(tuple((item, self._file(os.path.join(directory, item)))
                                   for item in vectors))
            jobs.append(job(directory))
        state = {"jobs": jobs, "queue": queue() if name is None else None}
        return (self._signature(settings.db_path, settings.config_path), tuple(files),
                json.dumps(state, ensure_ascii=False))

    @staticmethod
    def _errors(view):
        entries = view.get("embeddings", [])
        if "embedding" in view:
            entries = [view["embedding"]]
        return any(entry.get("index_error") for entry in entries)

    def get(self, settings, name, read_view, job, queue, *, encode_json=False):
        """Check every input. Rebuild the snapshot after an input changes."""
        db_path = os.path.abspath(settings.db_path)
        with self._lock:
            settings_key = json.dumps(
                [(label, entry.summary() if entry is not None else None, error)
                 for label, entry, error in settings.entries],
                ensure_ascii=False, sort_keys=True)
            try:
                identity = self._file(db_path)[:2]
                key = (db_path, settings.config_path, settings_key, identity, name,
                       read_view, job, queue)
                if self._key != key:
                    self._close()
                    self._connection = sqlite3.connect(
                        Path(db_path).as_uri() + "?mode=ro", uri=True,
                        check_same_thread=False)
                    self._key = key
                signature = self._inputs(settings, name, job, queue)
            except (OSError, sqlite3.Error):
                self._close()
                view = read_view(settings) if name is None else read_view(settings, name)
                return json.dumps(view, ensure_ascii=False).encode("utf-8") if encode_json else view
            if self._cached is not None and self._cached[0] == signature:
                return self._cached[1] if encode_json else json.loads(self._cached[1])
            self._cached = None
            disk_identity = self._disk_identity(settings, name, settings_key, signature,
                                                 (read_view, job, queue))
            if disk_identity is not None:
                saved = summary_cache.load(self._disk_directory(settings), self.disk_kind,
                                           name, disk_identity)
                if isinstance(saved, str):
                    body = saved.encode("utf-8")
                    try:
                        after = self._inputs(settings, name, job, queue)
                    except (OSError, sqlite3.Error):
                        after, after_disk = None, None
                    else:
                        after_disk = self._disk_identity(settings, name, settings_key, after,
                                                         (read_view, job, queue))
                    if (len(body) <= self.max_bytes and after == signature
                            and after_disk == disk_identity):
                        self._cached = (after, body)
                        return body if encode_json else json.loads(body)
            view = read_view(settings) if name is None else read_view(settings, name)
            body = json.dumps(view, ensure_ascii=False).encode("utf-8")
            try:
                after = self._inputs(settings, name, job, queue)
            except (OSError, sqlite3.Error):
                self._close()
            else:
                if after == signature and len(body) <= self.max_bytes and not self._errors(view):
                    self._cached = (after, body)
                    after_disk = self._disk_identity(settings, name, settings_key, after,
                                                     (read_view, job, queue))
                    if disk_identity is not None and after_disk == disk_identity:
                        summary_cache.store(self._disk_directory(settings), self.disk_kind,
                                            name, disk_identity, body.decode("utf-8"))
            return body if encode_json else view


LIST_VIEW_CACHE = EmbeddingViewCache(max_bytes=1024 * 1024, disk_kind="embedding-list-v1")
ENTRY_VIEW_CACHE = EmbeddingViewCache(disk_kind="embedding-entry-v1")
