# 80 — OpenAPI for the lab server

Date: 2026-09-29.
Status: implemented and verified.

The owner selected a checked-in OpenAPI 3.1 document on 2026-09-29.
The messages are in [owner-messages.md](../owner-messages.md).

## Goal

1. The lab server on port 8168 MUST publish its HTTP contract.
2. `GET /openapi.yaml` MUST return the checked-in YAML document.
3. `GET /openapi.json` MUST return the same document as JSON.
4. `GET /docs` MUST show the document with Swagger UI.
5. The document MUST cover every current lab API operation.
6. The document MUST cover the UI, specification, and image routes that a client can
   open directly.

## Document

1. The file is `docs/lab-openapi.yaml`.
2. The document uses OpenAPI 3.1.0.
3. The server URL is `http://127.0.0.1:8168`.
4. The document states that the server has no authentication.
5. The document states that the server MUST stay on a trusted local host.
6. Each operation MUST have a unique `operationId`.
7. Each operation MUST state its parameters, request body, success response, and common
   error responses.
8. A large or variable response MAY use an open object schema.
9. Request schemas MUST state the fields that the route validates.

## Routes

The document covers these groups:

1. Dataset reads and writes.
2. Manual wine creation and state changes.
3. Image descriptions and label descriptions.
4. Embedding indexes and build jobs.
5. Embedding clusters and cluster notes.
6. Test sets and test-set photo edits.
7. Run files, run details, and run jobs.
8. Website catalogue import jobs.
9. Interactive recognition.
10. Health status and endpoint checks.
11. UI pages, the OpenAPI files, Swagger UI, and image files.

## Server integration

1. `pipeline/lab_openapi.py` reads and converts the document.
2. The module owns the Swagger UI page.
3. Swagger UI uses the pinned version 5.33.0.
4. The page follows the operating-system light or dark theme.
5. The lab server sends the module output through its existing response helper.
6. The old disabled `/docs` branch is removed.
7. An unknown `/api/` route stays HTTP 503 for compatibility.
8. An unknown `/openapi.*` route stays HTTP 503 for compatibility.

## Failure behavior

1. A missing YAML file returns HTTP 404 from both specification routes.
2. `GET /openapi.yaml` returns the file bytes without parsing them.
3. Invalid YAML returns HTTP 500 from `GET /openapi.json`.
4. Swagger UI does not prevent the server from starting when its CDN is unavailable.
5. The YAML and JSON routes use `Cache-Control: no-store`.

## Tests

1. Parse the YAML document.
2. Verify OpenAPI 3.1.0, the title, and the server URL.
3. Verify every expected route and HTTP method.
4. Verify unique operation IDs.
5. Verify that each local `$ref` resolves.
6. Compare the complete parsed YAML and live JSON documents.
7. Verify the raw YAML media type and content.
8. Verify the Swagger UI page and its pinned version.
9. Verify missing and invalid document errors with a temporary file.
10. Restart port 8168 and test the three live endpoints.

## Files

- `docs/lab-openapi.yaml`
- `pipeline/lab_openapi.py`
- `pipeline/lab_server.py`
- `tests/test_lab_openapi.py`
- `COMMANDS.md`
- `README.md`
- `SMOKE_TESTS.md`
- `ChangeLog.md`

## Result

1. The checked-in document contains 98 operations in 85 paths.
2. The focused OpenAPI suite has 11 passing tests.
3. The OpenAPI suite and the 10 affected route suites have 225 passing tests.
4. The live YAML body equals the checked-in file byte for byte.
5. The live JSON document equals the parsed YAML document.
6. Swagger UI loaded the OpenAPI 3.1 document in the in-app browser.
7. Swagger UI executed `GET /api/health` and showed HTTP 200.
8. Port 8168 runs the verified code on PID 26110.
