# 71 — Evaluation matcher service

Date: 2026-09-28.
Status: implemented and verified. The owner selected the standalone FastAPI subproject.

## Goal

Add a standalone matcher service to `svoe-vino-lab/matcher/`. Make the service
compatible with the official evaluation harness.

## API contract

1. The service MUST provide `POST /v1/eval/predict`.
2. The request MUST hold one image in the multipart field `image`.
3. A successful response MUST be a JSON object with one string field:
   `{"slug":"..."}`.
4. The mock backend MUST identify the three official example images by SHA-256.
5. The mock backend MUST return these exact slugs:
   - `019c68d0.jpg`: `tabia_pino_nuar`;
   - `02eef911.webp`:
     `massandra-muskatel-belyy-belye-sorta-vinograda-beloe-sladkoe-16`;
   - `096ca74e.jpg`: `donum_xxiv`.
6. The mock backend MUST return `{"slug":""}` for another image.
7. The service MUST provide `GET /healthz`.
8. `GET /healthz` MUST return `status` and the selected pipeline name.
9. The service MUST reject an empty image with HTTP 400.
10. The service MUST reject an image above the configured limit with HTTP 413.
11. FastAPI MUST reject a request without the `image` field with HTTP 422.
12. The service MUST accept only JPEG, PNG, and WEBP images.
13. The service MUST reject a damaged image with HTTP 422.
14. The service MUST reject an unsupported image format with HTTP 415.
15. The service MUST reject a timed-out upload with HTTP 408.
16. The service MUST reject a request when the bounded queue is unavailable with HTTP
    503.

## Configuration

1. `matcher/tests/config.yaml` MUST have a top-level `pipeline` list for API tests.
2. Each pipeline entry MUST use the `name` and `backend` keys of
   `svoe-vino-lab/config.yaml`.
3. `matcher.pipeline` MUST explicitly select one pipeline entry by name.
4. The first implementation MUST support `backend: mock`.
5. The selected mock pipeline MUST hold the SHA-256-to-slug answer map.
6. `matcher/config.yaml` MUST stay available for the future real configuration.
7. `SVOE_VINO_MATCHER_MAX_IMAGE_BYTES` MAY set a positive image-size limit in bytes.
8. The default image-size limit MUST be 20 MiB.
9. `matcher/requirements.txt` MUST pin each direct dependency to an exact version.
10. `pydantic` MUST be a direct dependency because the application imports it.
11. `matcher.output_dir` MAY be a non-empty literal path.
12. `matcher.output_dir` MAY be an exact `"{env:NAME}"` reference.
13. The service MUST reject a malformed environment reference.
14. The service MUST reject a missing or empty referenced environment variable.
15. A configuration without `matcher.output_dir` MUST keep the legacy
    `SVOE_VINO_MATCHER_OUTPUT_DIR` fallback.
16. `matcher.token` MAY hold one exact `"{env:NAME}"` reference to an environment
    variable that holds a Bearer token.
17. A YAML file MUST NOT hold the token value.
18. The service MUST reject a bare variable name or a malformed environment reference.
19. The service MUST fail at startup when the referenced token variable is missing or
    empty.
20. The service MUST reject the retired key `matcher.token_env`.
21. `matcher/tests/config.yaml` MUST test the API without authentication.
22. `matcher/tests/config.token.yaml` MUST test the API with authentication.
23. Each test configuration MUST start with comments that state its purpose.

## Authentication

1. `POST /v1/eval/predict` MUST require `Authorization: Bearer <token>` when
   `matcher.token` is configured.
2. The token comparison MUST use a constant-time comparison.
3. A missing or invalid token MUST return HTTP 401 and `WWW-Authenticate: Bearer`.
4. `GET /healthz`, `/docs`, `/redoc`, and `/openapi.json` MUST stay public.
5. A configuration without `matcher.token` MUST keep predict public.

## Request protection

1. The middleware MUST limit the complete HTTP body before multipart parsing.
2. The complete-body limit MUST also work for chunked uploads without Content-Length.
3. The service MUST limit the image byte count and the declared pixel count.
4. Pillow MUST verify the image structure before the matcher runs.
5. The service MUST limit the upload time.
6. The service MUST limit active predict requests.
7. The service MUST limit queued predict requests.
8. The service MUST limit the time that a request can stay in the queue.
9. The protection MUST apply only to predict. It MUST NOT block `GET /healthz`.
10. A rejection MUST write a structured `matcher_rejected` log event.

## Request audit

1. `matcher.output_dir` MUST specify the output directory. A configuration without the
   field MAY use the legacy `SVOE_VINO_MATCHER_OUTPUT_DIR` fallback.
2. The service MUST save every submitted image before matching starts.
3. The service MUST save one JSON record beside the image.
4. The record MUST contain the request id, timestamps, duration, direct client IP,
   headers, image properties, HTTP status, and slug or error type.
5. Secret header values MUST be replaced with `<redacted>`.
6. The service MUST write one structured completion or failure event to the Uvicorn log.

## Files

- `matcher/app.py`: the FastAPI application.
- `matcher/audit.py`: private image storage, metadata storage, and header redaction.
- `matcher/protection.py`: authentication, upload bounds, admission control, and image
  validation.
- `matcher/service.py`: configuration validation and mock matching.
- `matcher/openapi.yaml`: the version-controlled OpenAPI 3.1 contract.
- `matcher/tests/config.yaml`: the selected mock pipeline and test answers.
- `matcher/tests/config.token.yaml`: the authenticated test configuration.
- `matcher/requirements.txt`: the runtime dependencies.
- `matcher/README.md`: setup, API, configuration, and official-harness instructions.
- `matcher/tests/participant_test.sh`: a local copy of the official evaluation client.
- `matcher/tests/queries.tsv`: a local copy of the official evaluation manifest.
- `matcher/tests/data/`: local copies of the three official sample images.
- `matcher/tests/test_auth.py`: live positive and negative authentication tests.
- `matcher/tests/test_resilience.py`: bounded local-socket adversarial tests.
- `matcher/tests/`: unit tests and official-harness integration tests.

## Verification

1. Unit tests MUST cover configuration selection, the three known images, and the
   unknown-image fallback.
2. An integration test MUST run the local copy of the official `participant_test.sh`
   against the live FastAPI service.
3. The integration test MUST use `matcher/tests/queries.tsv` and the local sample
   images in `matcher/tests/data/`.
4. The three output rows MUST contain the configured slugs.
5. A test MUST verify the five JSONL fields and values of the first official query.
6. The live `/openapi.json` document MUST be equal to the parsed
   `matcher/openapi.yaml` document.
7. The version-controlled OpenAPI document MUST describe GET /healthz, the image
   request, the slug response, BearerAuth, and responses 400, 401, 408, 413, 415, 422,
   and 503.
8. An integration test MUST verify the archived image, headers, client IP, SHA-256,
   response, and duration.
9. `git diff --check` MUST pass.
10. This work MUST NOT change the lab database or restart the lab server.
11. Tests MUST cover a request without `image`, an empty file, and an oversized file.
12. Tests MUST reject broken YAML, an unknown pipeline, a duplicate pipeline name, an
    invalid SHA-256, and an unsupported backend.
13. Tests MUST cover a literal output directory, an environment reference, a config
    without the field, a missing variable, an empty variable, and malformed references.
14. Tests MUST cover predict with authentication disabled and enabled.
15. Tests MUST cover missing, malformed, and invalid Bearer credentials.
16. Tests MUST prove that health and OpenAPI stay public.
17. Tests MUST send a JPEG dimension bomb and a damaged image.
18. Tests MUST send an unsupported image format.
19. Tests MUST send an oversized chunked body.
20. Tests MUST attempt a 1 GiB sparse upload and verify an early HTTP 413 response.
21. Tests MUST send a slow upload and verify HTTP 408.
22. Tests MUST fill the active request slots and the bounded queue and verify HTTP 503.
23. Each adversarial test MUST verify that the service can still process a normal
    request.

## Result

The service implements the contract. The test configuration selects official-eval-mock.
The mock answers identify the images by SHA-256. The local copy of the official shell
harness uses the local manifest and receives the three configured slugs. A fourth
request with an unknown image receives an empty slug. Tests select
`matcher/tests/config.yaml` explicitly. The JSONL test verifies the first official query
record, including its complete SHA-256 and latency type. Each accepted request archives
its image and JSON metadata in the required output directory. The audit test verifies
the direct client IP, headers, redaction, image data, response, duration, and Uvicorn
log. The API reports readiness at GET /healthz. The health endpoint and OpenAPI stay
public. Predict supports optional Bearer authentication. The YAML file stores only the
token environment-variable name. The test config uses
`output_dir: "{env:SVOE_VINO_MATCHER_OUTPUT_DIR}"`. A literal path and a config without
the field stay supported. Negative tests reject invalid or unresolved references.

The request middleware rejects an oversized declared or streamed body before matcher
work starts. It enforces the upload timeout. It bounds active requests, queued requests,
and queue time. Pillow accepts only JPEG, PNG, and WEBP. It rejects damaged images and
images above the pixel limit. The adversarial harness covers a JPEG dimension bomb, a
1 GiB sparse file, a large chunked body, a slow upload, an unsupported format, a
damaged image, and a full queue. The health endpoint and a normal request work after
each case.

All 37 matcher tests pass with ResourceWarning treated as an error. The parsed
checked-in OpenAPI 3.1 document equals the live OpenAPI document. Runtime requirements
have exact versions. They name pydantic and Pillow directly.

The tests use an ephemeral port. The project reserves no new port. The lab database did
not change. The lab server did not restart. git diff --check passes.
