"""A thin asynchronous client of the MAX Bot API.

Reference: https://dev.max.ru/docs-api and https://github.com/max-messenger/api-schema.
The client covers only the methods that the bot uses. It never logs a token, an image URL,
or a message text.
"""

from __future__ import annotations

import asyncio
import json
import logging
import ssl
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable, Mapping, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import certifi
import httpx

LOG = logging.getLogger("chto_za_vino_max_bot.max_api")

DEFAULT_BASE_URL = "https://platform-api2.max.ru"
# platform-api2.max.ru uses a certificate of the Russian Trusted Root CA (Минцифры).
DEFAULT_CA_FILE = Path(__file__).with_name("certs") / "russian_trusted_root_ca.pem"
DEFAULT_CA_SHA256 = (
    "d26d2d0231b7c39f92cc738512ba54103519e4405d68b5bd703e9788ca8ecf31"
)
GLOBAL_REQUESTS_PER_SECOND = 30.0
CHAT_OPERATIONS_PER_SECOND = 2.0
TEXT_LIMIT = 4000
UPDATE_TYPES = ("message_created", "message_callback", "bot_started")
ATTACHMENT_NOT_READY = "attachment.not.ready"
ATTACHMENT_RETRY_DELAYS = (1.0, 2.0, 4.0)
TRANSIENT_RETRY_DELAYS = (1.0, 2.0, 4.0)
REQUEST_TIMEOUT_SECONDS = 30.0
UPLOAD_TIMEOUT_SECONDS = 120.0
MAX_CHAT_LIMITERS = 10_000
MAX_REDIRECTS = 3

Sleep = Callable[[float], Awaitable[None]]


class MaxApiError(RuntimeError):
    """A MAX API call failed. The text never contains the token or a request URL."""

    def __init__(self, status: int, code: str | None, message: str | None) -> None:
        self.status = status
        self.code = code
        self.description = message or ""
        super().__init__(f"MAX API error status={status} code={code or '-'}")

    @property
    def transient(self) -> bool:
        return self.status == 429 or self.status >= 500


class MaxTransportError(MaxApiError):
    """The request did not reach the MAX API or its answer did not arrive."""

    def __init__(self, reason: str) -> None:
        super().__init__(0, "transport", reason)

    @property
    def transient(self) -> bool:
        return True


class MediaUnavailable(RuntimeError):
    """An attachment file cannot be downloaded."""


class MediaTooLarge(MediaUnavailable):
    """An attachment file is larger than the configured limit."""


def create_ssl_context(ca_file: Path | None = DEFAULT_CA_FILE) -> ssl.SSLContext:
    """Return the public trust store plus the Russian Trusted Root CA.

    The extra root is added to the trust store. It does not replace it, so the upload and
    download hosts with ordinary certificates keep working.
    """
    context = ssl.create_default_context(cafile=certifi.where())
    if ca_file is not None:
        context.load_verify_locations(cafile=str(ca_file))
    return context


class RateLimiter:
    """Keep operations at least `1 / rate` seconds apart. It has no background task.

    A strict interval keeps every one-second window within the limit. MAX permits two message
    operations per second in one chat and 30 requests per second in total.
    """

    def __init__(
        self,
        rate: float,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        if rate <= 0:
            raise ValueError("rate must be positive")
        self.interval = 1.0 / rate
        self._clock = clock
        self._sleep = sleep
        self._next_at = float("-inf")

    def wait_time(self, now: float) -> float:
        return max(0.0, self._next_at - now)

    def mark(self, now: float) -> None:
        """Record an operation at the actual time `now`."""
        self._next_at = now + self.interval

    async def acquire(self) -> None:
        await acquire_all((self,), clock=self._clock, sleep=self._sleep)


async def acquire_all(
    limiters: Sequence[RateLimiter],
    *,
    clock: Callable[[], float],
    sleep: Sleep,
) -> None:
    """Wait until every limiter permits an operation, then mark all of them at the same time.

    The check and the mark have no await between them, so they are atomic in the event loop.
    A late wakeup marks the actual time, so a deadline never comes from a stale estimate.
    """
    while True:
        now = clock()
        wait = max(limiter.wait_time(now) for limiter in limiters)
        if wait <= 0:
            for limiter in limiters:
                limiter.mark(now)
            return
        await sleep(wait)


def callback_button(text: str, payload: str) -> dict[str, object]:
    return {"type": "callback", "text": text[:128], "payload": payload}


def link_button(text: str, url: str) -> dict[str, object]:
    return {"type": "link", "text": text[:128], "url": url}


def inline_keyboard(rows: Sequence[Sequence[Mapping[str, object]]]) -> dict[str, object]:
    return {
        "type": "inline_keyboard",
        "payload": {"buttons": [[dict(button) for button in row] for row in rows]},
    }


def image_attachment(payload: Mapping[str, object]) -> dict[str, object]:
    return {"type": "image", "payload": dict(payload)}


def _error_from_response(response: httpx.Response) -> MaxApiError:
    code: str | None = None
    message: str | None = None
    try:
        body = response.json()
    except ValueError:
        body = None
    if isinstance(body, dict):
        raw_code = body.get("code") or body.get("error")
        code = raw_code if isinstance(raw_code, str) else None
        raw_message = body.get("message")
        message = raw_message if isinstance(raw_message, str) else None
    return MaxApiError(response.status_code, code, message)


class MaxApi:
    """MAX Bot API methods. One instance serves the whole process."""

    def __init__(
        self,
        token: str,
        client: httpx.AsyncClient,
        *,
        base_url: str = DEFAULT_BASE_URL,
        media_client: httpx.AsyncClient | None = None,
        media_allowed_hosts: tuple[str, ...] = (),
        global_rate: float = GLOBAL_REQUESTS_PER_SECOND,
        chat_rate: float = CHAT_OPERATIONS_PER_SECOND,
        sleep: Sleep = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not token:
            raise ValueError("the MAX bot token is required")
        parts = urlsplit(base_url)
        if parts.scheme != "https" or not parts.hostname:
            raise ValueError("the MAX API base URL must be an HTTPS URL")
        self._token = token
        self._client = client
        self._media_client = media_client or client
        self._base_url = base_url.rstrip("/")
        self._media_allowed_hosts = tuple(
            host.strip().lower().lstrip(".") for host in media_allowed_hosts if host.strip()
        )
        self._sleep = sleep
        self._clock = clock
        self._global_limiter = RateLimiter(global_rate, clock=clock, sleep=sleep)
        self._chat_rate = chat_rate
        self._chat_limiters: OrderedDict[int, RateLimiter] = OrderedDict()

    # Transport

    def _chat_limiter(self, chat_id: int) -> RateLimiter:
        limiter = self._chat_limiters.get(chat_id)
        if limiter is None:
            limiter = RateLimiter(self._chat_rate, clock=self._clock, sleep=self._sleep)
            self._chat_limiters[chat_id] = limiter
            while len(self._chat_limiters) > MAX_CHAT_LIMITERS:
                self._chat_limiters.popitem(last=False)
        else:
            self._chat_limiters.move_to_end(chat_id)
        return limiter

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, object] | None = None,
        body: object | None = None,
        chat_id: int | None = None,
        retry: bool = False,
        timeout: float = REQUEST_TIMEOUT_SECONDS,
    ) -> Any:
        """Call one method. Retry 429 always, other transient errors only when `retry`."""
        delays = iter(TRANSIENT_RETRY_DELAYS)
        while True:
            try:
                return await self._request_once(
                    method,
                    path,
                    params=params,
                    body=body,
                    chat_id=chat_id,
                    timeout=timeout,
                )
            except MaxApiError as exc:
                # A 429 answer means that MAX did not run the method, so a repeat is safe.
                if not (exc.status == 429 or (retry and exc.transient)):
                    raise
                delay = next(delays, None)
                if delay is None:
                    raise
                LOG.warning(
                    "MAX API call will be repeated method=%s path=%s status=%s delay=%s",
                    method,
                    path,
                    exc.status,
                    delay,
                )
                await self._sleep(delay)

    async def _request_once(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, object] | None,
        body: object | None,
        chat_id: int | None,
        timeout: float,
    ) -> Any:
        # Both limits are checked and marked together at the send time. A request that waits
        # for one limit cannot use a stale slot of the other limit.
        limiters = (
            (self._chat_limiter(chat_id), self._global_limiter)
            if chat_id is not None
            else (self._global_limiter,)
        )
        await acquire_all(limiters, clock=self._clock, sleep=self._sleep)
        query = {
            key: _query_value(value) for key, value in (params or {}).items() if value is not None
        }
        try:
            response = await self._client.request(
                method,
                f"{self._base_url}{path}",
                params=query,
                content=None if body is None else json.dumps(body, ensure_ascii=False),
                headers={
                    "Authorization": self._token,
                    "Accept": "application/json",
                    **({"Content-Type": "application/json"} if body is not None else {}),
                },
                timeout=timeout,
            )
        except httpx.HTTPError as exc:
            raise MaxTransportError(type(exc).__name__) from None
        if response.status_code >= 400:
            raise _error_from_response(response)
        try:
            value = response.json()
        except ValueError:
            raise MaxApiError(response.status_code, "invalid_json", None) from None
        if isinstance(value, dict) and value.get("success") is False:
            raw_message = value.get("message")
            raise MaxApiError(
                response.status_code,
                "unsuccessful",
                raw_message if isinstance(raw_message, str) else None,
            )
        return value

    # Bot information

    async def get_me(self) -> dict[str, Any]:
        return _object(await self._request("GET", "/me", retry=True))

    async def set_commands(self, commands: Sequence[Mapping[str, str]]) -> dict[str, Any]:
        return _object(
            await self._request(
                "PATCH",
                "/me/commands",
                body={"commands": [dict(item) for item in commands]},
                retry=True,
            )
        )

    # Updates

    async def get_updates(
        self,
        *,
        marker: int | None,
        timeout: int,
        limit: int = 100,
        types: Sequence[str] = UPDATE_TYPES,
    ) -> tuple[list[dict[str, Any]], int | None]:
        value = _object(
            await self._request(
                "GET",
                "/updates",
                params={
                    "marker": marker,
                    "timeout": timeout,
                    "limit": limit,
                    "types": ",".join(types),
                },
                retry=True,
                timeout=timeout + REQUEST_TIMEOUT_SECONDS,
            )
        )
        updates = value.get("updates")
        if not isinstance(updates, list):
            raise MaxApiError(200, "invalid_updates", None)
        raw_marker = value.get("marker")
        next_marker = (
            raw_marker
            if isinstance(raw_marker, int) and not isinstance(raw_marker, bool)
            else None
        )
        return [item for item in updates if isinstance(item, dict)], next_marker

    async def get_subscriptions(self) -> list[dict[str, Any]]:
        value = _object(await self._request("GET", "/subscriptions", retry=True))
        subscriptions = value.get("subscriptions")
        if not isinstance(subscriptions, list):
            raise MaxApiError(200, "invalid_subscriptions", None)
        return [item for item in subscriptions if isinstance(item, dict)]

    async def subscribe(self, url: str, *, secret: str, update_types: Sequence[str]) -> None:
        await self._request(
            "POST",
            "/subscriptions",
            body={"url": url, "secret": secret, "update_types": list(update_types)},
            retry=True,
        )

    async def unsubscribe(self, url: str) -> None:
        await self._request("DELETE", "/subscriptions", params={"url": url}, retry=True)

    # Messages

    async def send_message(
        self,
        chat_id: int,
        *,
        text: str | None,
        attachments: Sequence[Mapping[str, object]] | None = None,
        reply_to: str | None = None,
        text_format: str | None = "html",
        disable_link_preview: bool = False,
    ) -> dict[str, Any]:
        """Send one message and return the `Message` object.

        A failed reply is sent again without the reply link. This copies the Telegram option
        `allow_sending_without_reply=True`.
        """
        body = _message_body(text, attachments, text_format)
        if reply_to:
            body["link"] = {"type": "reply", "mid": reply_to}
        params = {"chat_id": chat_id, "disable_link_preview": disable_link_preview or None}
        try:
            value = await self._send_with_attachment_retry(chat_id, params, body)
        except MaxApiError as exc:
            # MAX rejected the request, so no message exists. Other errors can hide a sent message.
            if not reply_to or exc.status not in {400, 404} or exc.code == ATTACHMENT_NOT_READY:
                raise
            LOG.warning("MAX reply failed; the message is sent without the reply link")
            body.pop("link", None)
            value = await self._send_with_attachment_retry(chat_id, params, body)
        message = value.get("message") if isinstance(value, dict) else None
        if not isinstance(message, dict):
            raise MaxApiError(200, "invalid_message", None)
        return message

    async def _send_with_attachment_retry(
        self,
        chat_id: int,
        params: Mapping[str, object],
        body: Mapping[str, object],
    ) -> Any:
        delays = iter(ATTACHMENT_RETRY_DELAYS)
        while True:
            try:
                return await self._request(
                    "POST", "/messages", params=params, body=body, chat_id=chat_id
                )
            except MaxApiError as exc:
                delay = next(delays, None)
                if exc.code != ATTACHMENT_NOT_READY or delay is None:
                    raise
                await self._sleep(delay)

    async def edit_message(
        self,
        chat_id: int,
        message_id: str,
        *,
        text: str | None,
        attachments: Sequence[Mapping[str, object]] | None,
        text_format: str | None = "html",
    ) -> None:
        """Replace the text and the complete attachment list of one bot message.

        An empty `attachments` list removes all attachments, including a keyboard.
        """
        await self._request(
            "PUT",
            "/messages",
            params={"message_id": message_id},
            body=_message_body(text, attachments, text_format),
            chat_id=chat_id,
        )

    async def delete_message(self, chat_id: int, message_id: str) -> None:
        await self._request(
            "DELETE", "/messages", params={"message_id": message_id}, chat_id=chat_id
        )

    async def get_message(self, message_id: str) -> dict[str, Any]:
        return _object(
            await self._request("GET", f"/messages/{_path_segment(message_id)}", retry=True)
        )

    async def answer_callback(
        self,
        chat_id: int | None,
        callback_id: str,
        *,
        notification: str | None = None,
        message: Mapping[str, object] | None = None,
        disable_link_preview: bool = False,
    ) -> None:
        """Answer a button press. `message` replaces the message of the button."""
        body: dict[str, object] = {}
        if notification:
            body["notification"] = notification
        if message is not None:
            body["message"] = dict(message)
        await self._request(
            "POST",
            "/answers",
            params={
                "callback_id": callback_id,
                "disable_link_preview": disable_link_preview or None,
            },
            body=body,
            chat_id=chat_id,
        )

    # Media

    async def upload_image(
        self,
        body: bytes,
        *,
        filename: str,
        content_type: str,
    ) -> tuple[dict[str, object], str | None]:
        """Upload one image. Return the `image` attachment payload and its reusable token."""
        endpoint = _object(
            await self._request("POST", "/uploads", params={"type": "image"}, retry=True)
        )
        upload_url = endpoint.get("url")
        if not isinstance(upload_url, str) or urlsplit(upload_url).scheme != "https":
            raise MaxApiError(200, "invalid_upload_url", None)
        try:
            response = await self._media_client.post(
                upload_url,
                files={"data": (filename, body, content_type)},
                timeout=UPLOAD_TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as exc:
            raise MaxTransportError(type(exc).__name__) from None
        if response.status_code >= 400:
            raise _error_from_response(response)
        try:
            value = response.json()
        except ValueError:
            raise MaxApiError(response.status_code, "invalid_upload_answer", None) from None
        photos = value.get("photos") if isinstance(value, dict) else None
        if isinstance(photos, dict) and photos:
            tokens = [
                item.get("token")
                for item in photos.values()
                if isinstance(item, dict) and isinstance(item.get("token"), str)
            ]
            if tokens:
                return {"photos": photos}, tokens[0]
        token = value.get("token") if isinstance(value, dict) else None
        if isinstance(token, str) and token:
            return {"token": token}, token
        raise MaxApiError(response.status_code, "invalid_upload_answer", None)

    def _check_media_url(self, url: str) -> None:
        try:
            parts = urlsplit(url)
        except ValueError:
            raise MediaUnavailable("attachment URL is invalid") from None
        host = (parts.hostname or "").lower()
        if parts.scheme != "https" or not host:
            raise MediaUnavailable("attachment URL must use HTTPS")
        if self._media_allowed_hosts and not any(
            host == allowed or host.endswith(f".{allowed}")
            for allowed in self._media_allowed_hosts
        ):
            raise MediaUnavailable("attachment host is not allowed")

    async def download(self, url: str, *, max_bytes: int) -> bytes:
        """Download one attachment file. The bot token is not sent to the media host.

        A redirect is followed only to another allowed HTTPS URL, at most MAX_REDIRECTS times.
        """
        for _ in range(MAX_REDIRECTS + 1):
            self._check_media_url(url)
            chunks: list[bytes] = []
            size = 0
            try:
                async with self._media_client.stream("GET", url, timeout=60) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise MediaUnavailable("attachment redirect has no location")
                        url = str(response.url.join(location))
                        continue
                    if response.status_code >= 300:
                        raise MediaUnavailable(
                            f"attachment download status {response.status_code}"
                        )
                    content_length = response.headers.get("content-length")
                    if content_length and int(content_length) > max_bytes:
                        raise MediaTooLarge("attachment is too large")
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > max_bytes:
                            raise MediaTooLarge("attachment is too large")
                        chunks.append(chunk)
            except MediaUnavailable:
                raise
            except (httpx.HTTPError, ValueError) as exc:
                raise MediaUnavailable(
                    f"attachment download failed: {type(exc).__name__}"
                ) from None
            return b"".join(chunks)
        raise MediaUnavailable("attachment download has too many redirects")


def _object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MaxApiError(200, "invalid_answer", None)
    return value


def _query_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _path_segment(value: str) -> str:
    if not value or "/" in value or "?" in value or "#" in value:
        raise ValueError("message ID is invalid")
    return value


def _message_body(
    text: str | None,
    attachments: Sequence[Mapping[str, object]] | None,
    text_format: str | None,
) -> dict[str, object]:
    if text is not None and len(text) > TEXT_LIMIT:
        raise ValueError(f"message text exceeds {TEXT_LIMIT} characters")
    body: dict[str, object] = {"text": text}
    if attachments is not None:
        body["attachments"] = [dict(item) for item in attachments]
    if text_format and text:
        body["format"] = text_format
    return body
