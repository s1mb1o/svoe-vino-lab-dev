"""The answer cache of the model proxy.

The key function and the eligibility rules are the rules of the gx10 cache
(`/Users/ashmelev/Admin/gx10/scripts/inference/vlm_response_cache/server.py`), so that a
later import of gx10 entries stays possible. The differences of the store are in
docs/plans/01_multi-host-model-proxy.md, section "Cache".
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import sqlite3
import threading
import time
from collections.abc import AsyncIterator, Mapping, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode

from starlette.datastructures import UploadFile
from starlette.requests import Request


@dataclass(frozen=True)
class MultipartPart:
    name: str
    kind: str
    value: bytes
    content_type: str = ""


@dataclass(frozen=True)
class CacheEntry:
    status: int
    content_type: str
    body: bytes
    created_at: float
    host: str


def canonical_json(value: Any) -> bytes:
    """Return stable JSON bytes for semantically identical JSON input."""
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_query(raw_query: str) -> str:
    """Normalize the query order and keep repeated values."""
    return urlencode(sorted(parse_qsl(raw_query, keep_blank_values=True)), doseq=True)


def canonical_multipart(parts: Sequence[MultipartPart]) -> bytes:
    """Return a boundary-independent form of multipart fields."""
    rows: list[dict[str, Any]] = []
    for part in parts:
        row: dict[str, Any] = {
            "name": part.name,
            "kind": part.kind,
            "size": len(part.value),
            "sha256": hashlib.sha256(part.value).hexdigest(),
        }
        if part.kind == "file":
            row["content_type"] = part.content_type
        rows.append(row)
    rows.sort(
        key=lambda row: (
            row["name"],
            row["kind"],
            row.get("content_type", ""),
            row["sha256"],
            row["size"],
        )
    )
    return canonical_json(rows)


def build_cache_key(
    *,
    namespace: str,
    method: str,
    path: str,
    query: str,
    semantic_body: bytes,
) -> str:
    digest = hashlib.sha256()
    for item in (
        namespace.encode("utf-8"),
        method.upper().encode("ascii"),
        path.encode("utf-8"),
        canonical_query(query).encode("utf-8"),
        semantic_body,
    ):
        digest.update(len(item).to_bytes(8, "big"))
        digest.update(item)
    return digest.hexdigest()


def request_bypasses_cache(headers: Mapping[str, str]) -> bool:
    cache_control = headers.get("cache-control", "").casefold()
    explicit = headers.get("x-gx10-cache", "").casefold()
    return "no-cache" in {item.strip() for item in cache_control.split(",")} or explicit == "bypass"


def response_is_cacheable(route: str, status: int, content_type: str, body: bytes) -> bool:
    """Reject errors, non-JSON answers, and answers without the expected list."""
    if status != 200 or content_type.split(";", 1)[0].strip().casefold() != "application/json":
        return False
    try:
        payload = json.loads(body)
    except (UnicodeError, json.JSONDecodeError):
        return False
    if not isinstance(payload, dict):
        return False
    if route == "visual-embeddings":
        return isinstance(payload.get("data"), list)
    if route in {"sam3", "grounding-dino"}:
        return isinstance(payload.get("instances"), list)
    return False


async def multipart_semantic_body(request: Request) -> bytes:
    form = await request.form()
    parts: list[MultipartPart] = []
    try:
        for name, value in form.multi_items():
            if isinstance(value, UploadFile):
                data = await value.read()
                parts.append(
                    MultipartPart(
                        name=name,
                        kind="file",
                        value=data,
                        content_type=value.content_type or "application/octet-stream",
                    )
                )
            else:
                parts.append(
                    MultipartPart(name=name, kind="field", value=str(value).encode("utf-8"))
                )
    finally:
        await form.close()
    return canonical_multipart(parts)


async def semantic_body(request: Request, body: bytes) -> bytes | None:
    """Return the semantic body of a JSON or multipart request, or None when the body
    cannot be read. A request with None is forwarded without the cache."""
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().casefold()
    if content_type == "application/json":
        try:
            return canonical_json(json.loads(body))
        except (UnicodeError, ValueError, TypeError):
            return None
    if content_type == "multipart/form-data":
        try:
            return await multipart_semantic_body(request)
        except Exception:
            return None
    return None


class CacheStore:
    """SQLite store of the answers with a TTL and an LRU size limit. It never stores a
    request body."""

    PRUNE_INTERVAL = 60.0

    def __init__(self, path: Path, *, ttl_seconds: int, max_bytes: int) -> None:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = path
        self.ttl_seconds = ttl_seconds
        self.max_bytes = max_bytes
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, timeout=30, check_same_thread=False)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA synchronous=NORMAL")
        self._db.execute("PRAGMA temp_store=MEMORY")
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS entries (
                cache_key TEXT PRIMARY KEY,
                route TEXT NOT NULL,
                model TEXT NOT NULL,
                host TEXT NOT NULL,
                status INTEGER NOT NULL,
                content_type TEXT NOT NULL,
                body BLOB NOT NULL,
                body_size INTEGER NOT NULL,
                created_at REAL NOT NULL,
                last_accessed_at REAL NOT NULL,
                hits INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        self._db.execute("CREATE INDEX IF NOT EXISTS entries_lru ON entries(last_accessed_at)")
        self._db.execute("CREATE INDEX IF NOT EXISTS entries_created ON entries(created_at)")
        self._db.commit()
        self._total = int(
            self._db.execute("SELECT COALESCE(SUM(body_size), 0) FROM entries").fetchone()[0]
        )
        self._pruned_at = 0.0
        self.prune()

    def get(self, cache_key: str, *, now: float | None = None) -> CacheEntry | None:
        current = time.time() if now is None else now
        with self._lock:
            row = self._db.execute(
                """
                SELECT status, content_type, body, created_at, host, body_size
                FROM entries WHERE cache_key = ?
                """,
                (cache_key,),
            ).fetchone()
            if row is None:
                return None
            if float(row[3]) < current - self.ttl_seconds:
                self._db.execute("DELETE FROM entries WHERE cache_key = ?", (cache_key,))
                self._total -= int(row[5])
                self._db.commit()
                return None
            self._db.execute(
                "UPDATE entries SET last_accessed_at = ?, hits = hits + 1 WHERE cache_key = ?",
                (current, cache_key),
            )
            self._db.commit()
        return CacheEntry(int(row[0]), str(row[1]), bytes(row[2]), float(row[3]), str(row[4]))

    def put(
        self,
        cache_key: str,
        *,
        route: str,
        model: str,
        host: str,
        status: int,
        content_type: str,
        body: bytes,
        now: float | None = None,
    ) -> None:
        current = time.time() if now is None else now
        with self._lock:
            old = self._db.execute(
                "SELECT body_size FROM entries WHERE cache_key = ?", (cache_key,)
            ).fetchone()
            self._db.execute(
                """
                INSERT OR REPLACE INTO entries
                    (cache_key, route, model, host, status, content_type, body, body_size,
                     created_at, last_accessed_at, hits)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    cache_key,
                    route,
                    model,
                    host,
                    status,
                    content_type,
                    sqlite3.Binary(body),
                    len(body),
                    current,
                    current,
                ),
            )
            self._total += len(body) - (int(old[0]) if old else 0)
            self._prune_locked(current, force=False)
            self._db.commit()

    def prune(self, *, now: float | None = None) -> None:
        current = time.time() if now is None else now
        with self._lock:
            self._prune_locked(current, force=True)
            self._db.commit()

    def _prune_locked(self, current: float, *, force: bool) -> None:
        if force or current - self._pruned_at >= self.PRUNE_INTERVAL:
            self._pruned_at = current
            cutoff = current - self.ttl_seconds
            expired = int(
                self._db.execute(
                    "SELECT COALESCE(SUM(body_size), 0) FROM entries WHERE created_at < ?",
                    (cutoff,),
                ).fetchone()[0]
            )
            if expired:
                self._db.execute("DELETE FROM entries WHERE created_at < ?", (cutoff,))
                self._total -= expired
        while self._total > self.max_bytes:
            victims = self._db.execute(
                "SELECT cache_key, body_size FROM entries ORDER BY last_accessed_at ASC LIMIT 128"
            ).fetchall()
            if not victims:
                self._total = 0
                break
            for cache_key, body_size in victims:
                self._db.execute("DELETE FROM entries WHERE cache_key = ?", (cache_key,))
                self._total -= int(body_size)
                if self._total <= self.max_bytes:
                    break

    def stats(self) -> dict[str, Any]:
        with self._lock:
            count, body_bytes, hits = self._db.execute(
                "SELECT COUNT(*), COALESCE(SUM(body_size), 0), COALESCE(SUM(hits), 0) FROM entries"
            ).fetchone()
            rows = self._db.execute(
                """
                SELECT route, model, host, COUNT(*), COALESCE(SUM(body_size), 0),
                       COALESCE(SUM(hits), 0)
                FROM entries GROUP BY route, model, host ORDER BY route, model, host
                """
            ).fetchall()
        return {
            "entries": int(count),
            "body_bytes": int(body_bytes),
            "stored_hits": int(hits),
            "by_target": [
                {
                    "route": str(row[0]),
                    "model": str(row[1]),
                    "host": str(row[2]),
                    "entries": int(row[3]),
                    "body_bytes": int(row[4]),
                    "hits": int(row[5]),
                }
                for row in rows
            ],
        }

    def purge(self) -> int:
        with self._lock:
            count = int(self._db.execute("SELECT COUNT(*) FROM entries").fetchone()[0])
            self._db.execute("DELETE FROM entries")
            self._db.commit()
            self._total = 0
        return count

    def close(self) -> None:
        with self._lock:
            self._db.close()


class KeyedLocks:
    """Reference-counted locks for each key, for the merge of identical requests."""

    def __init__(self) -> None:
        self._guard = asyncio.Lock()
        self._locks: dict[str, tuple[asyncio.Lock, int]] = {}

    @asynccontextmanager
    async def hold(self, key: str) -> AsyncIterator[None]:
        async with self._guard:
            lock, refs = self._locks.get(key, (asyncio.Lock(), 0))
            self._locks[key] = (lock, refs + 1)
        try:
            await lock.acquire()
            try:
                yield
            finally:
                lock.release()
        finally:
            # A waiter that is cancelled in acquire() also gives back its reference.
            async with self._guard:
                current_lock, refs = self._locks[key]
                if current_lock is lock and refs == 1:
                    del self._locks[key]
                else:
                    self._locks[key] = (current_lock, refs - 1)

    @property
    def size(self) -> int:
        return len(self._locks)
