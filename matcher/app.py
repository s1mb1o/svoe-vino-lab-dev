"""FastAPI entry point for the official evaluation contract and the ranked match API."""

import asyncio
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
from time import perf_counter
from typing import Literal
import uuid

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, ConfigDict, Field

from .audit import RequestArchive, safe_headers
from .group import GroupMatchError, segment_group
from .protection import ImageRejected, RequestProtectionMiddleware, validate_image
from .service import load_matcher
from .siglip2 import Siglip2Error


ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = ROOT / "config.yaml"
DEFAULT_MAX_IMAGE_BYTES = 20 * 1024 * 1024
DEFAULT_MAX_IMAGE_PIXELS = 40_000_000
DEFAULT_UPLOAD_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_INFLIGHT_REQUESTS = 8
DEFAULT_MAX_QUEUED_REQUESTS = 16
DEFAULT_QUEUE_TIMEOUT_SECONDS = 0.25
MULTIPART_OVERHEAD_BYTES = 64 * 1024
DEFAULT_MATCH_K = 20
MAX_MATCH_K = 20
LOGGER = logging.getLogger("uvicorn.error")


class Prediction(BaseModel):
    """Top-1 catalogue match returned by the API."""

    model_config = ConfigDict(extra="forbid")

    slug: str = Field(
        description="Catalogue slug of the Top-1 match, or an empty string if no match exists.",
        examples=["massandra-muskatel-belyy-belye-sorta-vinograda-beloe-sladkoe-16"],
    )


class WineCard(BaseModel):
    """The catalogue card of one wine from the matcher bundle."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Wine name.")
    page_url: str = Field(description="Catalogue page of the wine.")
    producer: str | None = Field(description="Producer.")
    category: str | None = Field(description="Catalogue category.")
    region: str | None = Field(description="Region.")
    color: str | None = Field(description="Colour.")
    grapes: str | None = Field(description="Grape varieties.")
    sugar: str | None = Field(
        description="Sugar class that the slug or the name states, or null.")
    image_url: str | None = Field(description="Official catalogue image, or null.")
    qr_urls: list[str] = Field(description="Normalized QR code URLs of the wine.")


class MatchCandidate(BaseModel):
    """One ranked catalogue candidate."""

    model_config = ConfigDict(extra="forbid")

    rank: int = Field(description="Rank of the candidate. Rank 1 is the best match.")
    slug: str = Field(description="Catalogue slug of the wine.")
    score: float = Field(
        description="Pipeline score. The score does not increase from one rank to the next.")
    wine: WineCard


class MatchResult(BaseModel):
    """Ranked catalogue candidates of one image."""

    model_config = ConfigDict(extra="forbid")

    pipeline: str = Field(description="Name of the selected pipeline.")
    latency_ms: float = Field(description="Processing time of the request in milliseconds.")
    candidates: list[MatchCandidate] = Field(
        description="Up to k candidates, the best first. An empty list means no match.")


class GroupImage(BaseModel):
    """The normalized shelf image used for bottle coordinates."""

    model_config = ConfigDict(extra="forbid")

    width: int = Field(gt=0, description="Normalized image width in pixels.")
    height: int = Field(gt=0, description="Normalized image height in pixels.")
    preview: str = Field(description="Normalized JPEG image as a data URL.")


class GroupBottle(BaseModel):
    """One segmented bottle and its best catalogue match."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="Stable response-local bottle identifier.")
    segmentation_score: float = Field(
        ge=0, le=1, description="SAM3 confidence score for the bottle.")
    box: list[float] = Field(
        min_length=4, max_length=4,
        description=("Normalized [left, top, right, bottom] coordinates in the "
                     "returned image."),
    )
    mask: str = Field(
        description="Transparent PNG mask cropped to the bottle box as a data URL.")
    match: MatchCandidate | None = Field(
        description="Best catalogue match, or null when no match exists.")


class GroupMatchResult(BaseModel):
    """Bottle segments and catalogue matches for one shelf image."""

    model_config = ConfigDict(extra="forbid")

    pipeline: str = Field(description="Name of the selected pipeline.")
    latency_ms: float = Field(description="Processing time of the request in milliseconds.")
    image: GroupImage
    detected_count: int = Field(
        ge=0, description="Valid SAM3 detections before deduplication and response limits.")
    truncated: bool = Field(
        description="True when a response limit excluded a valid non-duplicate bottle.")
    bottles: list[GroupBottle] = Field(
        description="Segmented bottles in shelf order and their best matches.")


class Health(BaseModel):
    """Service state and selected matcher pipeline."""

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
        description="Identify wines in one package, label, or shelf image.",
        version="1.1.0",
        openapi_tags=[{
            "name": "evaluation",
            "description": "Official matcher evaluation contract.",
        }, {
            "name": "match",
            "description": "Ranked wine candidates with catalogue cards.",
        }, {
            "name": "group",
            "description": "Segment and match all wine bottles in one shelf image.",
        }, {
            "name": "service",
            "description": "Service liveness and readiness.",
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
        response_description="The service process is live.",
        summary="Check service liveness",
        operation_id="healthz",
        tags=["service"],
    )
    async def healthz() -> Health:
        """Return liveness and the selected pipeline."""
        return Health(pipeline=matcher.pipeline)

    @application.get(
        "/readyz",
        response_model=Health,
        response_description="The selected pipeline is ready.",
        summary="Check pipeline readiness",
        operation_id="readyz",
        tags=["service"],
        responses={
            503: {"description": "A dependency of the selected pipeline is unavailable."},
        },
    )
    async def readyz() -> Health:
        """Check only the dependencies required by the selected pipeline."""
        try:
            await asyncio.to_thread(matcher.check_ready)
        except (GroupMatchError, Siglip2Error) as exc:
            LOGGER.warning(
                "matcher readiness failed pipeline=%s error_type=%s",
                matcher.pipeline,
                type(exc).__name__,
            )
            raise HTTPException(status_code=503, detail=exc.detail) from exc
        return Health(pipeline=matcher.pipeline)

    async def process_image(request, image, operation):
        """Validate, archive, and process one image.

        `operation(body)` returns the result and the response fields of the audit
        record. Return the result and the duration in milliseconds.
        """
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
            result, response_data = await asyncio.to_thread(operation, body)
        except Exception as exc:
            completed_at = datetime.now(timezone.utc)
            duration_ms = round((perf_counter() - started_at) * 1000, 3)
            expected = isinstance(exc, (HTTPException, GroupMatchError, Siglip2Error))
            status_code = exc.status_code if expected else 500
            record = _record(
                request_id, received_at, completed_at, duration_ms, client_ip,
                request_data, image_data,
                {"status_code": status_code, "error_type": type(exc).__name__},
            )
            try:
                await asyncio.to_thread(archive.save_record, saved, record)
            except Exception:
                LOGGER.exception("cannot save matcher audit request_id=%s", request_id)
            if expected:
                LOGGER.warning("matcher_request %s", _log_event(record))
            else:
                LOGGER.exception("matcher_request %s", _log_event(record))
            if isinstance(exc, (GroupMatchError, Siglip2Error)):
                raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
            raise

        completed_at = datetime.now(timezone.utc)
        duration_ms = round((perf_counter() - started_at) * 1000, 3)
        record = _record(
            request_id, received_at, completed_at, duration_ms, client_ip,
            request_data, image_data, dict({"status_code": 200}, **response_data),
        )
        metadata_path = await asyncio.to_thread(archive.save_record, saved, record)
        LOGGER.info("matcher_request %s", _log_event(record, metadata_path))
        return result, duration_ms

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
            502: {"description": "SigLIP2 or SAM3 failed or returned invalid data."},
            503: {"description": "The matcher request queue is full, or hand selection "
                                 "requires SAM3 configuration."},
            504: {"description": "A SigLIP2 or SAM3 request exceeded its time limit."},
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
        def operation(body):
            slug = matcher.predict(body)
            return slug, {"slug": slug}

        slug, _ = await process_image(request, image, operation)
        return Prediction(slug=slug)

    @application.post(
        "/v1/match",
        response_model=MatchResult,
        response_description="The ranked catalogue candidates.",
        summary="Match one wine",
        description=(
            "Upload one JPEG, PNG, or WEBP image in the multipart field `image`. "
            "The answer holds up to `k` ranked candidates with their catalogue cards. "
            "The endpoint requires `Authorization: Bearer <token>` when "
            "`matcher.token` is configured."
        ),
        operation_id="match_image",
        tags=["match"],
        responses={
            400: {"description": "The uploaded image is empty."},
            413: {"description": "The uploaded image exceeds the configured size limit."},
            401: {"description": "The bearer token is missing or invalid."},
            408: {"description": "The request upload exceeded its time limit."},
            415: {"description": "The uploaded image format is not supported."},
            502: {"description": "SigLIP2 or SAM3 failed or returned invalid data."},
            503: {"description": "The matcher request queue is full, the selected "
                                 "pipeline has no wine cards, or hand selection "
                                 "requires SAM3 configuration."},
            504: {"description": "A SigLIP2 or SAM3 request exceeded its time limit."},
        },
    )
    async def match(
        request: Request,
        image: UploadFile = File(
            ...,
            description="Wine package or label image.",
        ),
        k: int = Query(
            DEFAULT_MATCH_K, ge=1, le=MAX_MATCH_K,
            description="Maximum number of candidates.",
        ),
    ) -> MatchResult:
        """Return up to `k` ranked candidates for one multipart image."""
        cards = matcher.cards
        if cards is None:
            detail = ("the selected pipeline has no wine cards; it needs a bundle of "
                      "format version 2 or a catalog")
            _log_rejection(uuid.uuid4().hex, request.client.host if request.client else None,
                           503, detail, perf_counter())
            raise HTTPException(status_code=503, detail=detail)

        def operation(body):
            ranked = matcher.match(body, k)
            return ranked, {"candidates": [slug for slug, _ in ranked]}

        ranked, duration_ms = await process_image(request, image, operation)
        return MatchResult(
            pipeline=matcher.pipeline,
            latency_ms=duration_ms,
            candidates=[
                MatchCandidate(rank=rank, slug=slug, score=score, wine=WineCard(**cards[slug]))
                for rank, (slug, score) in enumerate(ranked, 1)
            ],
        )

    @application.post(
        "/v1/group/match",
        response_model=GroupMatchResult,
        response_description="The segmented bottles and their best catalogue matches.",
        summary="Match all bottles in one shelf image",
        description=(
            "Upload one JPEG, PNG, or WEBP shelf image in the multipart field `image`. "
            "The service segments wine bottles with SAM3 and matches every returned "
            "bottle against the selected catalogue bundle. The endpoint requires "
            "`Authorization: Bearer <token>` when `matcher.token` is configured."
        ),
        operation_id="match_group_image",
        tags=["group"],
        responses={
            400: {"description": "The uploaded image is empty or cannot be decoded."},
            413: {"description": "The uploaded image exceeds the configured size limit."},
            401: {"description": "The bearer token is missing or invalid."},
            408: {"description": "The request upload exceeded its time limit."},
            415: {"description": "The uploaded image format is not supported."},
            502: {"description": "SigLIP2 or SAM3 failed or returned invalid data."},
            503: {"description": "The request queue is full, SAM3 is not configured, "
                                 "or the selected pipeline has no wine cards."},
            504: {"description": "A SigLIP2 or SAM3 request exceeded its time limit."},
        },
    )
    async def group_match(
        request: Request,
        image: UploadFile = File(
            ...,
            description="Shelf image that can contain multiple wine bottles.",
        ),
    ) -> GroupMatchResult:
        """Segment and match all returned bottles in one multipart image."""
        cards = matcher.cards
        if cards is None:
            detail = ("the selected pipeline has no wine cards; it needs a bundle of "
                      "format version 2 or a catalog")
            _log_rejection(uuid.uuid4().hex, request.client.host if request.client else None,
                           503, detail, perf_counter())
            raise HTTPException(status_code=503, detail=detail)

        def operation(body):
            try:
                segmented = segment_group(body, os.environ.get("SAM3_ENDPOINT"))
            except GroupMatchError as exc:
                raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
            ranked_groups = matcher.match_many(
                [bottle.crop for bottle in segmented.bottles], 1)
            if len(ranked_groups) != len(segmented.bottles):
                raise RuntimeError("matcher returned a wrong number of group results")
            audit_bottles = [
                {"id": bottle.id,
                 "slug": ranked[0][0] if ranked else None}
                for bottle, ranked in zip(segmented.bottles, ranked_groups)
            ]
            return (segmented, ranked_groups), {
                "detected_count": segmented.detected_count,
                "truncated": segmented.truncated,
                "bottles": audit_bottles,
            }

        (segmented, ranked_groups), duration_ms = await process_image(
            request, image, operation)
        bottles = []
        for bottle, ranked in zip(segmented.bottles, ranked_groups):
            candidate = None
            if ranked:
                slug, score = ranked[0]
                candidate = MatchCandidate(
                    rank=1, slug=slug, score=score, wine=WineCard(**cards[slug]))
            bottles.append(GroupBottle(
                id=bottle.id,
                segmentation_score=bottle.segmentation_score,
                box=list(bottle.box),
                mask=bottle.mask,
                match=candidate,
            ))
        return GroupMatchResult(
            pipeline=matcher.pipeline,
            latency_ms=duration_ms,
            image=GroupImage(
                width=segmented.width,
                height=segmented.height,
                preview=segmented.preview,
            ),
            detected_count=segmented.detected_count,
            truncated=segmented.truncated,
            bottles=bottles,
        )

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
    if "candidates" in record["response"]:
        event["candidates"] = record["response"]["candidates"]
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
        for path in ("/v1/eval/predict", "/v1/match", "/v1/group/match"):
            schema["paths"][path]["post"]["security"] = [
                {},
                {"BearerAuth": []},
            ]
        return schema

    application.openapi = matcher_openapi


app = create_app()
