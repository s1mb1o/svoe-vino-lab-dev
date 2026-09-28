"""FastAPI entry point for the official evaluation matcher contract."""

import asyncio
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
from time import perf_counter
from typing import Literal
import uuid

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, ConfigDict, Field

from .audit import RequestArchive, safe_headers
from .protection import ImageRejected, RequestProtectionMiddleware, validate_image
from .service import load_matcher


ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = ROOT / "config.yaml"
DEFAULT_MAX_IMAGE_BYTES = 20 * 1024 * 1024
DEFAULT_MAX_IMAGE_PIXELS = 40_000_000
DEFAULT_UPLOAD_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_INFLIGHT_REQUESTS = 8
DEFAULT_MAX_QUEUED_REQUESTS = 16
DEFAULT_QUEUE_TIMEOUT_SECONDS = 0.25
MULTIPART_OVERHEAD_BYTES = 64 * 1024
LOGGER = logging.getLogger("uvicorn.error")


class Prediction(BaseModel):
    """Top-1 catalogue match returned by the API."""

    model_config = ConfigDict(extra="forbid")

    slug: str = Field(
        description="Catalogue slug of the Top-1 match, or an empty string if no match exists.",
        examples=["massandra-muskatel-belyy-belye-sorta-vinograda-beloe-sladkoe-16"],
    )


class Health(BaseModel):
    """Service readiness and selected matcher pipeline."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"] = "ok"
    pipeline: str


def create_app(config_path=None, output_dir=None, max_image_bytes=None,
               max_image_pixels=None, upload_timeout_seconds=None,
               max_inflight_requests=None, max_queued_requests=None,
               queue_timeout_seconds=None):
    """Create the API and load its selected pipeline."""
    path = config_path or os.environ.get("SVOE_VINO_MATCHER_CONFIG") or DEFAULT_CONFIG
    matcher = load_matcher(path)
    if output_dir is not None:
        output = output_dir
    elif matcher.output_dir is not None:
        output = matcher.resolved_output_dir()
    else:
        output = os.environ.get("SVOE_VINO_MATCHER_OUTPUT_DIR")
    if not output:
        raise RuntimeError(
            "matcher.output_dir or SVOE_VINO_MATCHER_OUTPUT_DIR MUST specify "
            "an output directory")
    limit = _positive_int_setting(
        max_image_bytes, "SVOE_VINO_MATCHER_MAX_IMAGE_BYTES", DEFAULT_MAX_IMAGE_BYTES)
    pixel_limit = _positive_int_setting(
        max_image_pixels, "SVOE_VINO_MATCHER_MAX_IMAGE_PIXELS", DEFAULT_MAX_IMAGE_PIXELS)
    upload_timeout = _positive_float_setting(
        upload_timeout_seconds, "SVOE_VINO_MATCHER_UPLOAD_TIMEOUT_SECONDS",
        DEFAULT_UPLOAD_TIMEOUT_SECONDS)
    inflight_limit = _positive_int_setting(
        max_inflight_requests, "SVOE_VINO_MATCHER_MAX_INFLIGHT_REQUESTS",
        DEFAULT_MAX_INFLIGHT_REQUESTS)
    queue_limit = _positive_int_setting(
        max_queued_requests, "SVOE_VINO_MATCHER_MAX_QUEUED_REQUESTS",
        DEFAULT_MAX_QUEUED_REQUESTS)
    queue_timeout = _positive_float_setting(
        queue_timeout_seconds, "SVOE_VINO_MATCHER_QUEUE_TIMEOUT_SECONDS",
        DEFAULT_QUEUE_TIMEOUT_SECONDS)
    token = matcher.resolved_token()
    archive = RequestArchive(output)
    application = FastAPI(
        title="Svoe Vino Matcher API",
        description="Identify one wine from one uploaded package or label image.",
        version="1.0.0",
        openapi_tags=[{
            "name": "evaluation",
            "description": "Official matcher evaluation contract.",
        }, {
            "name": "service",
            "description": "Service readiness.",
        }],
    )
    application.state.matcher = matcher
    application.state.request_archive = archive
    application.state.max_image_bytes = limit
    application.state.max_image_pixels = pixel_limit
    application.state.auth_required = token is not None
    application.state.max_queued_requests = queue_limit
    application.add_middleware(
        RequestProtectionMiddleware,
        max_request_bytes=limit + MULTIPART_OVERHEAD_BYTES,
        upload_timeout_seconds=upload_timeout,
        max_inflight_requests=inflight_limit,
        max_queued_requests=queue_limit,
        queue_timeout_seconds=queue_timeout,
        token=token,
    )

    @application.get(
        "/healthz",
        response_model=Health,
        response_description="The service is ready.",
        summary="Check service readiness",
        operation_id="healthz",
        tags=["service"],
    )
    async def healthz() -> Health:
        """Return readiness and the selected pipeline."""
        return Health(pipeline=matcher.pipeline)

    @application.post(
        "/v1/eval/predict",
        response_model=Prediction,
        response_description="The Top-1 catalogue match.",
        summary="Predict one wine",
        description=(
            "Upload one JPEG, PNG, or WEBP image in the multipart field `image`. "
            "The endpoint requires `Authorization: Bearer <token>` when "
            "`matcher.token` is configured."
        ),
        operation_id="predict_image",
        tags=["evaluation"],
        responses={
            400: {"description": "The uploaded image is empty."},
            413: {"description": "The uploaded image exceeds the configured size limit."},
            401: {"description": "The bearer token is missing or invalid."},
            408: {"description": "The request upload exceeded its time limit."},
            415: {"description": "The uploaded image format is not supported."},
            503: {"description": "The matcher request queue is full."},
        },
    )
    async def predict(
        request: Request,
        image: UploadFile = File(
            ...,
            description="Wine package or label image.",
        ),
    ) -> Prediction:
        """Return the Top-1 slug for one multipart image."""
        request_id = uuid.uuid4().hex
        received_at = datetime.now(timezone.utc)
        started_at = perf_counter()
        client_ip = request.client.host if request.client else None
        try:
            body = await _read_image(image, limit)
            image_info = await asyncio.to_thread(validate_image, body, pixel_limit)
        except HTTPException as exc:
            _log_rejection(request_id, client_ip, exc.status_code, exc.detail, started_at)
            raise
        except ImageRejected as exc:
            _log_rejection(request_id, client_ip, exc.status_code, exc.detail, started_at)
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
        try:
            saved = await asyncio.to_thread(
                archive.save_image, request_id, received_at, image.filename, body)
        except Exception:
            LOGGER.exception("cannot archive matcher image request_id=%s client_ip=%s",
                             request_id, client_ip)
            raise

        request_data = {
            "method": request.method,
            "path": request.url.path,
            "query": request.url.query,
            "http_version": request.scope.get("http_version"),
            "headers": safe_headers(request.headers.raw),
        }
        image_data = {
            "original_filename": image.filename,
            "content_type": image.content_type,
            "size_bytes": saved.size_bytes,
            "sha256": saved.sha256,
            "saved_path": saved.relative_path,
            "format": image_info.format,
            "width": image_info.width,
            "height": image_info.height,
            "pixels": image_info.pixels,
        }
        try:
            slug = await asyncio.to_thread(matcher.predict, body)
        except Exception as exc:
            completed_at = datetime.now(timezone.utc)
            duration_ms = round((perf_counter() - started_at) * 1000, 3)
            record = _record(
                request_id, received_at, completed_at, duration_ms, client_ip,
                request_data, image_data,
                {"status_code": 500, "error_type": type(exc).__name__},
            )
            try:
                await asyncio.to_thread(archive.save_record, saved, record)
            except Exception:
                LOGGER.exception("cannot save matcher audit request_id=%s", request_id)
            LOGGER.exception("matcher_request %s", _log_event(record))
            raise

        completed_at = datetime.now(timezone.utc)
        duration_ms = round((perf_counter() - started_at) * 1000, 3)
        record = _record(
            request_id, received_at, completed_at, duration_ms, client_ip,
            request_data, image_data, {"status_code": 200, "slug": slug},
        )
        metadata_path = await asyncio.to_thread(archive.save_record, saved, record)
        LOGGER.info("matcher_request %s", _log_event(record, metadata_path))
        return Prediction(slug=slug)

    _configure_openapi(application)
    return application


def _positive_int_setting(explicit, environment_name, default):
    raw = explicit if explicit is not None else os.environ.get(environment_name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("%s MUST be a positive integer" % environment_name) from exc
    if value <= 0:
        raise RuntimeError("%s MUST be a positive integer" % environment_name)
    return value


def _positive_float_setting(explicit, environment_name, default):
    raw = explicit if explicit is not None else os.environ.get(environment_name)
    if raw is None or raw == "":
        return default
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("%s MUST be a positive number" % environment_name) from exc
    if value <= 0:
        raise RuntimeError("%s MUST be a positive number" % environment_name)
    return value


async def _read_image(image, limit):
    body = await image.read(limit + 1)
    if not body:
        raise HTTPException(status_code=400, detail="image MUST not be empty")
    if len(body) > limit:
        raise HTTPException(
            status_code=413,
            detail="image exceeds SVOE_VINO_MATCHER_MAX_IMAGE_BYTES",
        )
    return body


def _record(request_id, received_at, completed_at, duration_ms, client_ip,
            request_data, image_data, response_data):
    return {
        "request_id": request_id,
        "received_at": received_at.isoformat().replace("+00:00", "Z"),
        "completed_at": completed_at.isoformat().replace("+00:00", "Z"),
        "duration_ms": duration_ms,
        "client_ip": client_ip,
        "request": request_data,
        "image": image_data,
        "response": response_data,
    }


def _log_event(record, metadata_path=None):
    event = {
        "request_id": record["request_id"],
        "client_ip": record["client_ip"],
        "image_sha256": record["image"]["sha256"],
        "size_bytes": record["image"]["size_bytes"],
        "duration_ms": record["duration_ms"],
        "status_code": record["response"]["status_code"],
        "slug": record["response"].get("slug"),
        "saved_image": record["image"]["saved_path"],
        "metadata_path": str(metadata_path) if metadata_path else None,
    }
    return json.dumps(event, ensure_ascii=False, separators=(",", ":"))


def _log_rejection(request_id, client_ip, status_code, detail, started_at):
    event = {
        "request_id": request_id,
        "client_ip": client_ip,
        "status_code": status_code,
        "reason": detail,
        "duration_ms": round((perf_counter() - started_at) * 1000, 3),
    }
    LOGGER.warning("matcher_rejected %s", json.dumps(
        event, ensure_ascii=False, separators=(",", ":")))


def _configure_openapi(application):
    default_openapi = application.openapi

    def matcher_openapi():
        schema = default_openapi()
        security_schemes = schema.setdefault("components", {}).setdefault(
            "securitySchemes", {})
        security_schemes["BearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "description": "Required only when matcher.token is configured.",
        }
        schema["paths"]["/v1/eval/predict"]["post"]["security"] = [
            {},
            {"BearerAuth": []},
        ]
        return schema

    application.openapi = matcher_openapi


app = create_app()
