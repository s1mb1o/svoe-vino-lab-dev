"""Authenticated standalone FastAPI surface for the complete Dinner Lens pipeline."""
from __future__ import annotations

import asyncio
import base64
import binascii
import hmac
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from . import __version__
from .data import Knowledge
from .embeddings import EmbeddingIndex
from .engine import Engine, PipelineError
from .provider import QwenRecognizer
from .configuration import Configuration, LimitSettings, asset_path, load_config, secret


class RecommendRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    confirmed_dish: str | None = Field(default=None, max_length=500)
    node_id: str | None = Field(default=None, max_length=100)
    user_constraints: dict[str, Any] = Field(default_factory=dict)
    confirmed_attributes: dict[str, Any] = Field(default_factory=dict)
    limit: int = Field(default=3, ge=1, le=10)


class MoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    cursor: str = Field(min_length=1, max_length=1_500_000)
    user_constraints: dict[str, Any] | None = None
    confirmed_attributes: dict[str, Any] | None = None


class PhotoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    image_base64: str = Field(min_length=1, max_length=7_000_000)
    user_constraints: dict[str, Any] = Field(default_factory=dict)
    confirmed_attributes: dict[str, Any] = Field(default_factory=dict)
    limit: int = Field(default=3, ge=1, le=10)


class BoundedBody:
    """Bound request bytes before JSON parsing, even without Content-Length."""
    def __init__(self, app, max_bytes=8 * 1024 * 1024):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH"}:
            return await self.app(scope, receive, send)
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > self.max_bytes:
                return await JSONResponse({"detail": "Request body exceeds the configured limit"}, status_code=413)(scope, receive, send)
            if not message.get("more_body"):
                break
        first = True

        async def replay():
            nonlocal first
            if first:
                first = False
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()
        return await self.app(scope, replay, send)


def create_app(engine: Engine, recognizer: QwenRecognizer, *, api_token: str, limits: LimitSettings | None = None) -> FastAPI:
    if type(api_token) is not str or len(api_token) < 24 or not re.fullmatch(r"[A-Za-z0-9._~-]+", api_token):
        raise ValueError("A safe API token of at least 24 characters is required")
    app = FastAPI(title="Dinner Lens", version=__version__)
    limits = limits or LimitSettings()
    app.add_middleware(BoundedBody, max_bytes=limits.max_request_bytes)
    semaphore = asyncio.Semaphore(limits.recognition_concurrency)

    @app.middleware("http")
    async def authorize(request: Request, call_next):
        if request.url.path not in {"/health", "/readyz"}:
            provided = request.headers.get("authorization", "").encode()
            if not hmac.compare_digest(provided, ("Bearer " + api_token).encode()):
                return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(PipelineError)
    async def pipeline_error(_request, exc):
        return JSONResponse({"code": exc.code, "detail": str(exc)}, status_code=422)

    @app.get("/readyz")
    @app.get("/health")
    def health():
        return {"status": "ok", "bundle_version": engine.version,
                "catalog_wines": len(engine.knowledge.wines), "embedding_model": engine.index.model,
                "recognition_model": getattr(recognizer, "model", "qwen3.8-flash"),
                "recognition_fallback_model": getattr(recognizer, "fallback_model", None), "instruction_language": "en"}

    @app.post("/v1/recommendations")
    def recommend(body: RecommendRequest):
        return engine.recommend(confirmed_dish=body.confirmed_dish, node_id=body.node_id,
                                filters=body.user_constraints, confirmed_attributes=body.confirmed_attributes,
                                limit=body.limit)

    @app.post("/v1/recommendations/more")
    def more(body: MoreRequest):
        return engine.more(body.cursor, filters=body.user_constraints,
                           confirmed_attributes=body.confirmed_attributes)

    @app.post("/v1/recognize-and-recommend")
    async def recognize_and_recommend(body: PhotoRequest):
        # Validate filters before incurring a paid model call.
        from .engine import validate_attributes, validate_filters
        validate_filters(body.user_constraints)
        validate_attributes(body.confirmed_attributes)
        encoded = body.image_base64
        if encoded.startswith("data:"):
            if not re.match(r"^data:image/(?:jpeg|png|webp|heic|heif);base64,", encoded):
                raise PipelineError("invalid_image", "Only inline JPEG, PNG, HEIC/HEIF and WebP data URLs are supported")
            encoded = encoded.split(",", 1)[1]
        try:
            image = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error):
            raise PipelineError("invalid_image", "Invalid base64 image") from None
        try:
            await asyncio.wait_for(semaphore.acquire(), timeout=limits.recognition_queue_seconds)
        except TimeoutError:
            raise HTTPException(status_code=503, detail="Recognition capacity is busy; retry shortly") from None
        try:
            try:
                recognition, meta = await run_in_threadpool(recognizer.recognize, image)
            except RuntimeError as exc:
                raise HTTPException(status_code=503, detail=str(exc)) from None
        finally:
            semaphore.release()
        result = await run_in_threadpool(engine.recommend_from_recognition, recognition,
                                        filters=body.user_constraints,
                                        confirmed_attributes=body.confirmed_attributes, limit=body.limit)
        result["recognition"] = recognition
        result["llm"] = meta
        return result

    return app


def app_from_config(config: Configuration, config_path: Path) -> FastAPI:
    token = secret(config.auth.api_token_env)
    cursor_secret = secret(config.auth.cursor_secret_env)
    if config.recognition.api_key_env:
        secret(config.recognition.api_key_env)
    if config.recognition.fallback and config.recognition.fallback.api_key_env:
        secret(config.recognition.fallback.api_key_env)
    knowledge = Knowledge(asset_path(config.assets.dataset, config_path), asset_path(config.assets.style, config_path))
    index = EmbeddingIndex(knowledge, asset_path(config.assets.index, config_path), settings=config.embeddings)
    engine = Engine(knowledge, index, cursor_secret=cursor_secret.encode(),
                    cursor_ttl_seconds=config.limits.cursor_ttl_seconds)
    recognizer = QwenRecognizer(knowledge, asset_path(config.recognition.prompt, config_path),
                                settings=config.recognition)
    app = create_app(engine, recognizer, api_token=token, limits=config.limits)
    app.state.configuration = config
    return app


def app_from_environment() -> FastAPI:
    """ASGI factory. Only the configuration selector and secrets use the environment."""
    return app_from_config(*load_config())
