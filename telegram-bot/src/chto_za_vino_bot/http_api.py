from __future__ import annotations

import ipaddress
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from email import policy
from email.message import Message
from email.parser import BytesParser

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response

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
    recognize: RecognitionCallback,
) -> FastAPI:
    networks = tuple(ipaddress.ip_network(item, strict=False) for item in allowed_networks)
    app = FastAPI(
        title="Что за вино? Recognition API",
        version="1.1.0",
        description=(
            "Internal synchronous API. It uses the same queue and recognition pipeline "
            "as the Telegram bot."
        ),
    )

    @app.middleware("http")
    async def network_middleware(request: Request, call_next):
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
                response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/healthz", response_class=PlainTextResponse, include_in_schema=False)
    @app.get("/api/v1/healthz", response_class=PlainTextResponse)
    async def health() -> str:
        return "ok"

    @app.post(
        "/api/v1/recognize",
        response_class=JSONResponse,
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
