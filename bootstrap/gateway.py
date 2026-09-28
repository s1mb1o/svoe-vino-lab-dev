"""Compatibility gateway for the portable model services."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request, Response


app = FastAPI(title="Model service bootstrap gateway", version="1.0.0")
targets: dict[str, str] = {}


def configure(values: dict[str, str]) -> None:
    """Set the active model ID to loopback URL mapping."""
    targets.clear()
    targets.update({key: value.rstrip("/") for key, value in values.items()})


def configure_from_environment() -> None:
    raw = os.environ.get("BOOTSTRAP_TARGETS", "{}")
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise RuntimeError("BOOTSTRAP_TARGETS must be a JSON object")
    configure({str(key): str(value) for key, value in parsed.items()})


@app.on_event("startup")
def startup() -> None:
    if not targets:
        configure_from_environment()


def _model_target(model_id: str) -> str:
    target = targets.get(model_id)
    if target is None:
        raise HTTPException(status_code=404, detail=f"model {model_id!r} is not active")
    return target


async def _forward(request: Request, url: str) -> Response:
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in {"host", "content-length", "connection"}
    }
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(900.0)) as client:
            upstream = await client.request(
                request.method,
                url,
                params=request.query_params,
                headers=headers,
                content=await request.body(),
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"model service request failed: {exc}") from exc
    response_headers = {
        key: value
        for key, value in upstream.headers.items()
        if key.lower()
        not in {"content-length", "content-encoding", "transfer-encoding", "connection"}
    }
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type"),
    )


async def _readiness_failures() -> dict[str, str]:
    """Return one diagnostic for each active model that is not ready."""

    async with httpx.AsyncClient(timeout=httpx.Timeout(3.0)) as client:
        async def probe(model_id: str, target: str) -> tuple[str, str | None]:
            try:
                upstream = await client.get(f"{target}/health")
                if upstream.status_code == 200:
                    return model_id, None
                return model_id, f"health returned HTTP {upstream.status_code}"
            except httpx.HTTPError as exc:
                return model_id, str(exc)

        results = await asyncio.gather(
            *(probe(model_id, target) for model_id, target in targets.items())
        )
    return {model_id: error for model_id, error in results if error is not None}


@app.get("/health")
async def health(response: Response) -> dict[str, Any]:
    failures = await _readiness_failures()
    if failures:
        response.status_code = 503
        return {
            "status": "not-ready",
            "active_models": sorted(targets),
            "failures": failures,
        }
    return {"status": "ok", "active_models": sorted(targets), "failures": {}}


@app.api_route(
    "/upstream/{model_id}/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def upstream(model_id: str, path: str, request: Request) -> Response:
    return await _forward(request, f"{_model_target(model_id)}/{path}")


@app.post("/v1/embeddings")
async def embeddings(request: Request) -> Response:
    body = await request.body()
    try:
        parsed = json.loads(body)
        model_id = parsed["model"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="request body must contain a model string") from exc
    if not isinstance(model_id, str) or not model_id:
        raise HTTPException(status_code=400, detail="request body must contain a model string")
    return await _forward(request, f"{_model_target(model_id)}/v1/embeddings")
