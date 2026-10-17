"""Update delivery: the durable inbox, long polling, and the webhook receiver.

Both delivery modes write each update to the SQLite inbox before the bot handles it.
One dispatcher task handles the inbox rows in arrival order.
"""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
import time
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from .max_api import UPDATE_TYPES, MaxApiError
from .storage import Repository
from .updates import Update, parse_update, update_key, update_user_id

LOG = logging.getLogger("chto_za_vino_max_bot.delivery")

MARKER_KEY = "polling_marker"
POLLING_MIN_INTERVAL_SECONDS = 0.3
POLLING_MAX_BACKOFF_SECONDS = 30.0
WEBHOOK_MAX_BODY_BYTES = 1024 * 1024
INBOX_BATCH = 100

UpdateHandler = Callable[[Update], Awaitable[None]]


class UpdateDispatcher:
    """Admit updates to the inbox and handle them one by one in arrival order."""

    def __init__(
        self,
        repository: Repository,
        handler: UpdateHandler,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._repository = repository
        self._handler = handler
        self._clock = clock
        self._wakeup = asyncio.Event()

    def admit(self, raw_updates: list[dict[str, Any]], *, marker: int | None = None) -> int:
        """Write the updates to the inbox. The polling marker is stored in the same transaction."""
        rows = []
        for raw in raw_updates:
            update_type = raw.get("update_type")
            if update_type not in UPDATE_TYPES:
                continue
            key = update_key(raw)
            if key is None:
                LOG.warning("MAX update without an identity was dropped type=%s", update_type)
                continue
            rows.append((key, str(update_type), update_user_id(raw), raw))
        admitted = self._repository.admit_updates(rows, now=int(self._clock()), marker=marker)
        if admitted:
            self._wakeup.set()
        return admitted

    async def run_once(self) -> int:
        """Handle the pending inbox rows. Return the number of handled rows."""
        handled = 0
        while True:
            batch = self._repository.pending_updates(limit=INBOX_BATCH)
            if not batch:
                return handled
            for item in batch:
                update = parse_update(item.payload)
                if update is not None:
                    try:
                        await self._handler(update)
                    except asyncio.CancelledError:
                        raise
                    except Exception:
                        # One failed update MUST NOT stop the delivery of the next updates.
                        LOG.exception(
                            "MAX update handling failed type=%s",
                            item.payload.get("update_type"),
                        )
                self._repository.mark_update_processed(item.inbox_id, int(self._clock()))
                handled += 1

    async def run(self) -> None:
        while True:
            # Clear before the check, so an admission during the check is not lost.
            self._wakeup.clear()
            if await self.run_once():
                continue
            await self._wakeup.wait()


def stored_marker(repository: Repository) -> int | None:
    value = repository.state(MARKER_KEY)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        LOG.warning("Stored MAX polling marker is invalid; polling starts without a marker")
        return None


class Poller:
    """Long polling of `GET /updates` with a persistent marker."""

    def __init__(
        self,
        api: Any,
        dispatcher: UpdateDispatcher,
        repository: Repository,
        *,
        timeout_seconds: int = 30,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._api = api
        self._dispatcher = dispatcher
        self._repository = repository
        self._timeout = timeout_seconds
        self._sleep = sleep
        self._clock = clock

    async def check_no_webhook(self) -> None:
        """MAX does not deliver long polling events while a webhook subscription is active."""
        subscriptions = await self._api.get_subscriptions()
        if subscriptions:
            raise RuntimeError(
                "A MAX webhook subscription is active, so long polling gets no updates. "
                "Delete the subscription or set updates.mode: webhook in config.yaml."
            )

    async def poll_once(self, marker: int | None) -> int | None:
        updates, next_marker = await self._api.get_updates(
            marker=marker,
            timeout=self._timeout,
            types=UPDATE_TYPES,
        )
        self._dispatcher.admit(updates, marker=next_marker)
        return next_marker if next_marker is not None else marker

    async def run(self) -> None:
        marker = stored_marker(self._repository)
        backoff = 1.0
        last_call = -POLLING_MIN_INTERVAL_SECONDS
        while True:
            wait = POLLING_MIN_INTERVAL_SECONDS - (self._clock() - last_call)
            if wait > 0:
                await self._sleep(wait)
            last_call = self._clock()
            try:
                marker = await self.poll_once(marker)
            except MaxApiError as exc:
                if exc.status in {401, 403}:
                    raise
                LOG.warning(
                    "MAX long polling failed status=%s code=%s retry_in=%s",
                    exc.status,
                    exc.code,
                    backoff,
                )
                await self._sleep(backoff)
                backoff = min(POLLING_MAX_BACKOFF_SECONDS, backoff * 2)
                continue
            backoff = 1.0


def create_webhook_app(
    *,
    path: str,
    secret: str,
    dispatcher: UpdateDispatcher,
) -> FastAPI:
    """Return the webhook receiver. A TLS proxy MUST publish it on HTTPS port 443."""
    expected = secret.encode("utf-8")
    app = FastAPI(
        title="Что за вино? MAX webhook",
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
    )

    @app.get("/healthz", response_class=PlainTextResponse)
    async def health() -> str:
        return "ok"

    @app.post(path)
    async def receive(request: Request) -> JSONResponse:
        supplied = request.headers.get("x-max-bot-api-secret", "").encode("utf-8")
        if not secrets.compare_digest(supplied, expected):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        raw_length = request.headers.get("content-length")
        if raw_length and raw_length.isdigit() and int(raw_length) > WEBHOOK_MAX_BODY_BYTES:
            return JSONResponse({"error": "too_large"}, status_code=413)
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > WEBHOOK_MAX_BODY_BYTES:
                return JSONResponse({"error": "too_large"}, status_code=413)
        try:
            payload = json.loads(bytes(body))
        except ValueError:
            return JSONResponse({"error": "invalid_json"}, status_code=400)
        if not isinstance(payload, dict):
            return JSONResponse({"error": "invalid_update"}, status_code=400)
        try:
            dispatcher.admit([payload])
        except Exception:
            # A non-200 answer makes MAX repeat the delivery later.
            LOG.exception("MAX webhook update was not stored")
            return JSONResponse({"error": "unavailable"}, status_code=503)
        return JSONResponse({"ok": True})

    return app
