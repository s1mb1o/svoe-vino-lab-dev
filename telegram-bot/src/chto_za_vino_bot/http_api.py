from __future__ import annotations

import asyncio
import ipaddress
import math
import secrets
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from email import policy
from email.message import Message
from email.parser import BytesParser

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from fastapi.security import HTTPBearer

MAX_MULTIPART_OVERHEAD = 64 * 1024


class HttpQueueFull(RuntimeError):
    pass


class HttpQueueUnavailable(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class HttpRecognitionResult:
    status_code: int
    body: dict[str, object]


RecognitionCallback = Callable[[bytes], Awaitable[HttpRecognitionResult]]


async def read_multipart_image(request: Request, max_image_bytes: int) -> bytes:
    content_type = request.headers.get("content-type", "")
    if not content_type or len(content_type) > 512 or "\r" in content_type or "\n" in content_type:
        raise HTTPException(status_code=415, detail="Expected multipart/form-data")
    header = Message()
    header["content-type"] = content_type
    if header.get_content_type() != "multipart/form-data" or not header.get_boundary():
        raise HTTPException(status_code=415, detail="Expected multipart/form-data")

    request_limit = max_image_bytes + MAX_MULTIPART_OVERHEAD
    raw_length = request.headers.get("content-length")
    if raw_length:
        try:
            content_length = int(raw_length)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid Content-Length") from exc
        if content_length < 0:
            raise HTTPException(status_code=400, detail="Invalid Content-Length")
        if content_length > request_limit:
            raise HTTPException(status_code=413, detail="Image is too large")

    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > request_limit:
            raise HTTPException(status_code=413, detail="Image is too large")
        body.extend(chunk)
    try:
        encoded_content_type = content_type.encode("ascii")
    except UnicodeEncodeError as exc:
        raise HTTPException(status_code=415, detail="Invalid multipart content type") from exc
    message = BytesParser(policy=policy.default).parsebytes(
        b"Content-Type: "
        + encoded_content_type
        + b"\r\nMIME-Version: 1.0\r\n\r\n"
        + bytes(body)
    )
    if not message.is_multipart() or message.defects:
        raise HTTPException(status_code=400, detail="Invalid multipart body")

    images: list[bytes] = []
    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        if part.get_param("name", header="content-disposition") != "image":
            continue
        payload = part.get_payload(decode=True)
        if not isinstance(payload, bytes) or not payload:
            raise HTTPException(status_code=400, detail="Image field is empty")
        images.append(payload)
    if len(images) != 1:
        raise HTTPException(status_code=400, detail="One image field is required")
    if len(images[0]) > max_image_bytes:
        raise HTTPException(status_code=413, detail="Image is too large")
    return images[0]


def create_http_api_app(
    *,
    allowed_networks: tuple[str, ...],
    max_image_bytes: int,
    api_token: str,
    rate_limit: int,
    rate_window_seconds: int,
    max_in_flight: int,
    recognize: RecognitionCallback,
    readiness: Callable[[], Awaitable[dict[str, bool]]] | None = None,
) -> FastAPI:
    if len(api_token) < 32:
        raise ValueError("API token must contain at least 32 characters")
    if rate_limit <= 0 or rate_window_seconds <= 0 or max_in_flight <= 0:
        raise ValueError("API request limits must be positive")
    networks = tuple(ipaddress.ip_network(item, strict=False) for item in allowed_networks)
    requests_by_address: dict[str, deque[float]] = {}
    state_lock = asyncio.Lock()
    in_flight = 0
    app = FastAPI(
        title="Что за вино? Recognition API",
        version="1.1.0",
        description=(
            "Internal synchronous API. It uses the same queue and recognition pipeline "
            "as the Telegram bot."
        ),
    )
    bearer_scheme = HTTPBearer(description="BOT_HTTP_API_TOKEN")

    @app.middleware("http")
    async def network_middleware(request: Request, call_next):
        nonlocal in_flight
        host = request.client.host if request.client else ""
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            response: Response = JSONResponse(
                {"error": "forbidden", "detail": "Client network is not allowed"},
                status_code=403,
            )
        else:
            if not any(address in network for network in networks):
                response = JSONResponse(
                    {"error": "forbidden", "detail": "Client network is not allowed"},
                    status_code=403,
                )
            else:
                protected = request.method == "POST" and request.url.path == "/api/v1/recognize"
                if protected:
                    authorization = request.headers.get("authorization", "")
                    scheme, separator, supplied = authorization.partition(" ")
                    valid_token = (
                        separator == " "
                        and scheme.casefold() == "bearer"
                        and secrets.compare_digest(
                            supplied.encode("utf-8"), api_token.encode("utf-8")
                        )
                    )
                    if not valid_token:
                        response = JSONResponse(
                            {"error": "unauthorized", "detail": "Bearer token is required"},
                            status_code=401,
                            headers={"WWW-Authenticate": "Bearer"},
                        )
                    else:
                        now = time.monotonic()
                        async with state_lock:
                            timestamps = requests_by_address.setdefault(host, deque())
                            cutoff = now - rate_window_seconds
                            while timestamps and timestamps[0] <= cutoff:
                                timestamps.popleft()
                            if len(timestamps) >= rate_limit:
                                retry_after = max(
                                    1,
                                    math.ceil(timestamps[0] + rate_window_seconds - now),
                                )
                                response = JSONResponse(
                                    {
                                        "error": "rate_limited",
                                        "detail": "API request limit exceeded",
                                    },
                                    status_code=429,
                                    headers={"Retry-After": str(retry_after)},
                                )
                            elif in_flight >= max_in_flight:
                                response = JSONResponse(
                                    {
                                        "error": "too_many_requests",
                                        "detail": "Too many API requests are in progress",
                                    },
                                    status_code=503,
                                    headers={"Retry-After": "20"},
                                )
                            else:
                                timestamps.append(now)
                                in_flight += 1
                                response = None
                        if response is None:
                            try:
                                response = await call_next(request)
                            finally:
                                async with state_lock:
                                    in_flight -= 1
                else:
                    response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/healthz", response_class=PlainTextResponse, include_in_schema=False)
    @app.get("/api/v1/healthz", response_class=PlainTextResponse)
    async def health() -> str:
        return "ok"

    @app.get("/readyz", include_in_schema=False)
    @app.get("/api/v1/readyz")
    async def ready() -> JSONResponse:
        checks = await readiness() if readiness is not None else {"application": True}
        ready_now = bool(checks) and all(checks.values())
        return JSONResponse(
            {"ready": ready_now, "checks": checks},
            status_code=200 if ready_now else 503,
        )

    @app.post(
        "/api/v1/recognize",
        response_class=JSONResponse,
        dependencies=[Depends(bearer_scheme)],
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {
                    "multipart/form-data": {
                        "schema": {
                            "type": "object",
                            "required": ["image"],
                            "properties": {
                                "image": {"type": "string", "format": "binary"}
                            },
                        }
                    }
                },
            }
        },
    )
    async def recognize_image(request: Request) -> JSONResponse:
        image = await read_multipart_image(request, max_image_bytes)
        try:
            result = await recognize(image)
        except HttpQueueFull as exc:
            return JSONResponse(
                {"error": "queue_full", "detail": str(exc)},
                status_code=503,
                headers={"Retry-After": "20"},
            )
        except HttpQueueUnavailable as exc:
            return JSONResponse(
                {"error": "queue_unavailable", "detail": str(exc)},
                status_code=503,
            )
        return JSONResponse(result.body, status_code=result.status_code)

    return app
