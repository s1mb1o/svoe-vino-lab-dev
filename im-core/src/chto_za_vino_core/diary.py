"""History records of «Винный дневник» from a bot (plan `../docs/plans/07_diary-history-and-saved.md`).

When a person links the messenger to the diary, the bot records each wine that it shows to the
person. The account service records a wine only for a linked identity and only when the switch
«Записывать найденные вина» is on. The consumer token of the bot gives the messenger.

Each call runs in the background with one attempt and a 2-second timeout. A failure changes
nothing in the chat. The log contains no user ID, no wine slug, and no token.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import Coroutine
from typing import Any

import httpx

from .wine import Wine, unknown_wine

LOG = logging.getLogger("chto_za_vino_core.diary")

RECORD_PATH = "/v1/bot/history"
UNDO_PATH = "/v1/bot/history/undo"
TIMEOUT_SECONDS = 2.0
# History calls that run at the same time. They share the HTTP pool with the photo pipeline.
MAX_TASKS = 8
MAX_RESPONSE_BYTES = 16 * 1024
# The slug rule of the account service.
WINE_SLUG = re.compile(r"[a-z0-9](?:[a-z0-9_-]{0,198}[a-z0-9])?")
# The snapshot limits of the account service. It refuses a larger snapshot with HTTP 422.
SNAPSHOT_TEXT_LIMIT = 200
SNAPSHOT_GRAPE_LIMIT = 80
SNAPSHOT_GRAPES = 12
SNAPSHOT_BYTES = 2048
# The keys that the bot removes first when the snapshot is too large.
SNAPSHOT_DROP_ORDER = ("grapes", "region", "sugar", "color", "producer", "name")
GRAPE_SEPARATOR = re.compile(r"[,;]")
# An error code or a status of the account service. Any other value does not go to the log.
SERVICE_CODE = re.compile(r"[a-z_]{1,40}")


def _text(value: str | None, limit: int) -> str | None:
    if not value:
        return None
    text = " ".join(value.split())[:limit].rstrip()
    return text or None


def _json_bytes(value: dict[str, object]) -> int:
    return len(json.dumps(value, ensure_ascii=False).encode("utf-8"))


def wine_snapshot(wine: Wine) -> dict[str, object] | None:
    """Return the diary snapshot of a shown wine, or None when the card has no data.

    The account service accepts `name`, `producer`, `color`, `sugar`, and `region` (strings of
    1 to 200 characters) and `grapes` (at most 12 strings of 1 to 80 characters), at most
    2,048 bytes of JSON.

    The diary color is the wine color of the site («Красное», «Белое»). In a matcher card that
    value is `category`; `color` is the tint («Рубиновый»). The tint is the fallback.
    """
    if wine == unknown_wine(wine.slug):
        # A request of an old version has no card, and its name is the slug. A newer snapshot
        # replaces an older one, so this card must not replace the snapshot of the site.
        return None
    snapshot: dict[str, object] = {}
    for key, value in (
        ("name", wine.name),
        ("producer", wine.producer),
        ("color", wine.category or wine.color),
        ("sugar", wine.sugar),
        ("region", wine.region),
    ):
        text = _text(value, SNAPSHOT_TEXT_LIMIT)
        if text is not None:
            snapshot[key] = text
    grapes: list[str] = []
    for item in GRAPE_SEPARATOR.split(wine.grapes or ""):
        grape = _text(item, SNAPSHOT_GRAPE_LIMIT)
        if grape is not None and grape not in grapes:
            grapes.append(grape)
    if grapes:
        snapshot["grapes"] = grapes[:SNAPSHOT_GRAPES]
    for key in SNAPSHOT_DROP_ORDER:
        if _json_bytes(snapshot) <= SNAPSHOT_BYTES:
            break
        snapshot.pop(key, None)
    return snapshot or None


def _person(user_id: object) -> bool:
    return isinstance(user_id, int) and not isinstance(user_id, bool) and user_id > 0


def _slug(value: object) -> bool:
    return isinstance(value, str) and WINE_SLUG.fullmatch(value) is not None


class DiaryUnavailable(Exception):
    """The account service did not accept the call. The text contains no personal data."""


class DiaryHistory:
    """Sends the history calls of one bot to the account service in the background.

    `record` and `undo` return at once and never raise. The status `not_linked` is a normal
    answer: most people do not link the messenger.
    """

    def __init__(
        self,
        endpoint: str,
        token: str,
        client: httpx.AsyncClient,
        *,
        timeout_seconds: float = TIMEOUT_SECONDS,
        max_tasks: int = MAX_TASKS,
    ) -> None:
        self._base = endpoint.rstrip("/")
        self._headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        self._client = client
        self._timeout = timeout_seconds
        self._tasks: set[asyncio.Task[None]] = set()
        self._slots = asyncio.Semaphore(max_tasks)

    def __repr__(self) -> str:
        return f"DiaryHistory(endpoint={self._base!r})"

    def record(self, user_id: int, wine: Wine, *, replaces: str | None = None) -> None:
        """Record a shown wine for today.

        `replaces` is the wine that the person rejected before they selected this wine. The
        service removes the date of today of that wine.
        """
        self._spawn("record", self._record(user_id, wine, replaces))

    def undo(self, user_id: int, slug: str) -> None:
        """Remove the date of today of a wine that the person rejected."""
        self._spawn("undo", self._undo(user_id, slug))

    async def join(self) -> None:
        """Wait for the calls that run now."""
        while self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _record(self, user_id: int, wine: Wine, replaces: str | None) -> str | None:
        if not _person(user_id) or not _slug(wine.slug):
            return None
        body: dict[str, object] = {"user_id": user_id, "slug": wine.slug}
        snapshot = wine_snapshot(wine)
        if snapshot is not None:
            body["wine_snapshot"] = snapshot
        if replaces != wine.slug and _slug(replaces):
            body["replaces"] = replaces
        return await self._post(RECORD_PATH, body)

    async def _undo(self, user_id: int, slug: str) -> str | None:
        if not _person(user_id) or not _slug(slug):
            return None
        return await self._post(UNDO_PATH, {"user_id": user_id, "slug": slug})

    def _spawn(self, operation: str, work: Coroutine[Any, Any, str | None]) -> None:
        guarded = self._guarded(operation, work)
        try:
            task = asyncio.create_task(guarded)
        except RuntimeError as exc:
            # No running event loop. The caller continues without the record.
            guarded.close()
            work.close()
            LOG.warning("Diary history %s failed: %s", operation, type(exc).__name__)
            return
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _guarded(self, operation: str, work: Coroutine[Any, Any, str | None]) -> None:
        try:
            async with self._slots:
                async with asyncio.timeout(self._timeout):
                    status = await work
        except DiaryUnavailable as exc:
            LOG.warning("Diary history %s failed: %s", operation, exc)
            return
        except Exception as exc:  # noqa: BLE001 - a history call never stops the bot
            # The type only: the text of an exception can contain the request body.
            LOG.warning("Diary history %s failed: %s", operation, type(exc).__name__)
            return
        finally:
            work.close()
        if status is not None:
            LOG.info("Diary history %s answered status=%s", operation, status)

    async def _post(self, path: str, body: dict[str, object]) -> str:
        response = await self._client.post(
            f"{self._base}{path}",
            json=body,
            headers=self._headers,
            timeout=self._timeout,
            follow_redirects=False,
        )
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise DiaryUnavailable("response too large")
        try:
            data = response.json()
        except ValueError:
            raise DiaryUnavailable(f"HTTP {response.status_code}") from None
        if not isinstance(data, dict):
            raise DiaryUnavailable(f"HTTP {response.status_code}")
        if response.status_code != 200:
            code = data.get("error")
            known = code if isinstance(code, str) and SERVICE_CODE.fullmatch(code) else ""
            raise DiaryUnavailable(f"HTTP {response.status_code} {known}".strip())
        status = data.get("status")
        if not isinstance(status, str) or not SERVICE_CODE.fullmatch(status):
            raise DiaryUnavailable("answer without a status")
        return status
