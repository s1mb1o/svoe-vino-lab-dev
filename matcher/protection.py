"""Bound HTTP uploads and reject unsafe image files before matching."""

import asyncio
from dataclasses import dataclass
from io import BytesIO
import json
import logging
import secrets
from time import perf_counter
import warnings

from PIL import Image, UnidentifiedImageError


LOGGER = logging.getLogger("uvicorn.error")
PREDICT_PATH = "/v1/eval/predict"
MATCH_PATH = "/v1/match"
GROUP_MATCH_PATH = "/v1/group/match"
PROTECTED_PATHS = frozenset({PREDICT_PATH, MATCH_PATH, GROUP_MATCH_PATH})
SUPPORTED_IMAGE_FORMATS = frozenset({"JPEG", "MPO", "PNG", "WEBP"})


@dataclass(frozen=True)
class ImageInfo:
    """Validated image properties."""

    format: str
    width: int
    height: int

    @property
    def pixels(self) -> int:
        return self.width * self.height


class ImageRejected(ValueError):
    """A safe client error for an invalid or unsafe image."""

    def __init__(self, status_code, detail):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class RequestProtectionMiddleware:
    """Protect the image endpoints before FastAPI parses multipart data."""

    def __init__(self, app, *, max_request_bytes, upload_timeout_seconds,
                 max_inflight_requests, max_queued_requests,
                 queue_timeout_seconds, token=None):
        self.app = app
        self.max_request_bytes = max_request_bytes
        self.upload_timeout_seconds = upload_timeout_seconds
        self.queue_timeout_seconds = queue_timeout_seconds
        self.token = token
        self.slots = asyncio.Semaphore(max_inflight_requests)
        self.max_queued_requests = max_queued_requests
        self.queued_requests = 0

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("path") not in PROTECTED_PATHS:
            await self.app(scope, receive, send)
            return

        started_at = perf_counter()
        if not self._authorized(scope):
            await self._reject(scope, send, 401, "invalid or missing bearer token",
                               started_at, [(b"www-authenticate", b"Bearer")])
            return

        content_length = self._content_length(scope)
        if content_length is False:
            await self._reject(scope, send, 400, "invalid Content-Length", started_at)
            return
        if content_length is not None and content_length > self.max_request_bytes:
            await self._reject(scope, send, 413, "request body is too large", started_at)
            return

        if not await self._acquire_slot():
            await self._reject(scope, send, 503, "matcher is busy", started_at,
                               [(b"retry-after", b"1")])
            return

        response_started = False

        async def tracked_send(message):
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        received = 0
        body_complete = asyncio.Event()
        body_too_large = asyncio.Event()

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_request_bytes:
                    body_too_large.set()
                    await asyncio.Future()
                if not message.get("more_body", False):
                    body_complete.set()
            elif message["type"] == "http.disconnect":
                body_complete.set()
            return message

        app_task = asyncio.create_task(
            self.app(scope, limited_receive, tracked_send))
        upload_task = asyncio.create_task(asyncio.wait_for(
            body_complete.wait(), self.upload_timeout_seconds))
        size_task = asyncio.create_task(body_too_large.wait())
        try:
            done, _ = await asyncio.wait(
                (app_task, upload_task, size_task),
                return_when=asyncio.FIRST_COMPLETED,
            )
            if size_task in done and size_task.result():
                await self._cancel(app_task)
                await self._cancel(upload_task)
                if response_started:
                    raise RuntimeError("request body limit fired after response start")
                await self._reject(
                    scope, send, 413, "request body is too large", started_at)
            elif app_task in done:
                await self._cancel(upload_task)
                await self._cancel(size_task)
                await app_task
            else:
                await self._cancel(size_task)
                try:
                    upload_task.result()
                except TimeoutError:
                    await self._cancel(app_task)
                    if response_started:
                        raise RuntimeError("upload timeout fired after response start")
                    await self._reject(
                        scope, send, 408, "request upload timed out", started_at)
                else:
                    await app_task
        finally:
            await self._cancel(app_task)
            await self._cancel(upload_task)
            await self._cancel(size_task)
            self.slots.release()

    async def _acquire_slot(self):
        if not self.slots.locked():
            await self.slots.acquire()
            return True
        if self.queued_requests >= self.max_queued_requests:
            return False
        self.queued_requests += 1
        try:
            await asyncio.wait_for(
                self.slots.acquire(), self.queue_timeout_seconds)
            return True
        except TimeoutError:
            return False
        finally:
            self.queued_requests -= 1

    @staticmethod
    async def _cancel(task):
        if not task.done():
            task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    def _authorized(self, scope):
        if self.token is None:
            return True
        values = [value for name, value in scope.get("headers", ())
                  if name.lower() == b"authorization"]
        if len(values) != 1:
            return False
        scheme, separator, credential = values[0].partition(b" ")
        if not separator or scheme.lower() != b"bearer" or not credential:
            return False
        return secrets.compare_digest(credential, self.token.encode("utf-8"))

    @staticmethod
    def _content_length(scope):
        values = [value for name, value in scope.get("headers", ())
                  if name.lower() == b"content-length"]
        if not values:
            return None
        if len(values) != 1:
            return False
        try:
            value = int(values[0].decode("ascii"))
        except (UnicodeDecodeError, ValueError):
            return False
        return value if value >= 0 else False

    async def _reject(self, scope, send, status_code, detail, started_at,
                      extra_headers=()):
        body = json.dumps({"detail": detail}, separators=(",", ":")).encode("utf-8")
        headers = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode("ascii")),
            (b"connection", b"close"),
            *extra_headers,
        ]
        client = scope.get("client")
        event = {
            "client_ip": client[0] if client else None,
            "status_code": status_code,
            "reason": detail,
            "content_length": self._content_length(scope),
            "duration_ms": round((perf_counter() - started_at) * 1000, 3),
        }
        LOGGER.warning("matcher_rejected %s", json.dumps(
            event, ensure_ascii=False, separators=(",", ":")))
        await send({"type": "http.response.start", "status": status_code,
                    "headers": headers})
        await send({"type": "http.response.body", "body": body})


def validate_image(body, max_pixels):
    """Validate an image header and structure without decoding all pixels."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(body)) as image:
                image_format = (image.format or "").upper()
                width, height = image.size
                if image_format not in SUPPORTED_IMAGE_FORMATS:
                    raise ImageRejected(
                        415,
                        "image format MUST be JPEG (including MPO), PNG, or WEBP",
                    )
                if width <= 0 or height <= 0:
                    raise ImageRejected(422, "image dimensions MUST be positive")
                if width * height > max_pixels:
                    raise ImageRejected(413, "image pixel count exceeds the configured limit")
                image.verify()
    except ImageRejected:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ImageRejected(413, "image pixel count exceeds the configured limit") from exc
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        raise ImageRejected(422, "image file is invalid or damaged") from exc
    return ImageInfo(image_format, width, height)
