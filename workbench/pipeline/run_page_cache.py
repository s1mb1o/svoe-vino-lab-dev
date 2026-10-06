"""Cache one checked run-page response per run, with bounded in-memory storage."""
from collections import OrderedDict
import hashlib
import json
import os
from pathlib import Path
from threading import Lock

import run_files
import summary_cache

_LOCK = Lock()
_CACHE = OrderedDict()
_MAX_PAGES = 3
_MAX_BYTES = 6 * 1024 * 1024
_MAX_PAGE_BYTES = 2 * 1024 * 1024


def _code_revision():
    root = Path(__file__).resolve().parent
    try:
        sources = [root / name for name in (
            "run_page_cache.py", "run_routes.py", "run_files.py", "lab_server.py")]
        # Include the optional image-tag adapter when this checkout has it.
        tags = root / "image_tags.py"
        if tags.exists():
            sources.append(tags)
        return hashlib.sha256(b"".join(path.read_bytes() for path in sources)).hexdigest()
    except OSError:
        return None


_CODE_REVISION = _code_revision()


def _signature(path):
    if path is None:
        return None
    try:
        return run_files._file_key(path, os.stat(path))
    except OSError:
        return None


def token(runs_dir, run_id, db_path, card_images, options):
    """Identify inputs for the standard SQLite-backed card renderer."""
    if (_CODE_REVISION is None or not db_path
            or getattr(card_images, "__module__", None) != "lab_server"
            or getattr(card_images, "__name__", None) != "card_images"):
        return None
    source = run_files.run_path(runs_dir, run_id, "results.jsonl")
    if source is None:
        return None
    database = os.path.abspath(db_path)
    db = _signature(database)
    if db is None:
        return None
    identity = (_CODE_REVISION, tuple(options), db, _signature(database + "-wal"),
                tuple(_signature(run_files.run_path(runs_dir, run_id, name))
                      for name in ("results.jsonl", "run.json", "metrics.json")))
    return source, identity


def _remember(key, body):
    size = len(body)
    if size > _MAX_PAGE_BYTES:
        return
    source, identity = key
    with _LOCK:
        _CACHE[source] = (identity, body, size)
        _CACHE.move_to_end(source)
        while (len(_CACHE) > _MAX_PAGES or
               sum(record[2] for record in _CACHE.values()) > _MAX_BYTES):
            _CACHE.popitem(last=False)


def load(key):
    if key is None:
        return None
    source, identity = key
    with _LOCK:
        hit = _CACHE.get(source)
        if hit is not None and hit[0] == identity:
            _CACHE.move_to_end(source)
            return hit[1]
    value = summary_cache.load(run_files._cache_directory(source), "pages-v1",
                               source, identity)
    if not isinstance(value, str):
        return None
    body = value.encode("utf-8")
    _remember(key, body)
    return body


def store(key, value):
    """Retain successful image lookups only. Oversized pages stay uncached."""
    if key is None or value.get("images_error") is not None:
        return
    text = json.dumps(value, ensure_ascii=False)
    body = text.encode("utf-8")
    if len(body) > _MAX_PAGE_BYTES:
        return body
    _remember(key, body)
    source, identity = key
    summary_cache.store(run_files._cache_directory(source), "pages-v1", source,
                        identity, text)
    return body
