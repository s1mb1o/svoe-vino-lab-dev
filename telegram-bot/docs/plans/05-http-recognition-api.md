# HTTP recognition API

Date: 2026-09-27

Status: Deployed

## Goal

Add a synchronous HTTP API for internal recognition tests.
The API MUST use the same processing queue as Telegram requests.
The API MUST use the same moderation, quality, recognition, storage, artifact, and timing steps.

## Interface

The bot process MUST listen on a separate configurable HTTP port.
The default port MUST be `8180`.
The production listener MUST be available on the home LAN.

`POST /api/v1/recognize` MUST accept `multipart/form-data`.
The form MUST contain one `image` field.
The endpoint MUST wait for queue processing to finish.
The endpoint MUST return a JSON result.

The JSON result MUST contain:

- The request ID and terminal status.
- Moderation metadata.
- Advisory quality metadata.
- Recognition confidence and the selected wine.
- Four ranked candidates when recognition ran.
- Wine color, sugar class, grape varieties, and catalogue URL.
- Each stored step timing.
- The active matcher pipeline.

The endpoint MUST return a successful HTTP response for `recognized`, `abstained`, and
`quarantined` terminal statuses.
The response MUST not contain an unsafe image or its storage path.

## Queue behavior

The HTTP endpoint MUST submit work to the existing `WorkQueue` instance.
The API request MUST be exempt from the Telegram per-user rate limit.
The configured queue capacity MUST apply.
The endpoint MUST return HTTP 503 when the queue is full.

An interrupted API request cannot be restored because its image exists only in memory.
The service MUST mark an interrupted API request as failed.
The service MUST not restore an API request as a Telegram request after a restart.

## Image safety

The endpoint MUST enforce `BOT_MAX_IMAGE_BYTES` before processing.
The endpoint MUST parse the multipart body in memory.
The endpoint MUST not use a temporary upload file.
The pipeline MUST moderate the image before persistent image storage.
The pipeline MUST fail closed when moderation is unavailable.
The response MUST not expose quarantine files.

## Network access

The API does not require an API key for this test deployment.
The API MUST restrict clients to `BOT_HTTP_API_ALLOWED_NETWORKS`.
The default networks MUST be localhost and `192.168.86.0/24`.
The service MUST not trust proxy headers.

FastAPI MUST publish OpenAPI at `/openapi.json`.
FastAPI MUST publish Swagger UI at `/docs`.

## Configuration

Add these variables:

- `BOT_HTTP_API_HOST`, with default `127.0.0.1`.
- `BOT_HTTP_API_PORT`, with default `8180`.
- `BOT_HTTP_API_ALLOWED_NETWORKS`, with the same default LAN list as the administration UI.

Production MUST set `BOT_HTTP_API_HOST=0.0.0.0`.

## Verification

Tests MUST cover LAN filtering, multipart validation, upload size enforcement, queue submission,
unsafe results, recognized results, API source persistence, and restart filtering.

Run:

```bash
uv run ruff check .
uv run pytest -q
```

Run one production smoke request with a safe wine image.
Confirm that the request appears in the administration interface.
Confirm that the response contains four candidates and step timings.

## Result

The production service listens on `0.0.0.0:8180` on `gx10`.
The API health endpoint and OpenAPI endpoint return HTTP 200 from the home LAN.
The cached control image returned HTTP 200 in 9.811 seconds.
The response used status `abstained` because the correct Top-1 margin was below the configured
confidence threshold.
The response contained the correct `Фантом 30/70` Top-1 result, four candidates, wine parameters,
moderation metadata, quality metadata, and all step timings.
The administration interface showed the request with source `HTTP API`.

One uncached control request reached the matcher but timed out after 180 seconds while the shared
VLM was busy with another workload.
The API returned HTTP 502 with status `recognition_failed` and complete timing evidence.
The failure did not stop the service or its queue worker.
