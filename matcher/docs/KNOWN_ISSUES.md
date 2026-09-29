# Matcher known issues

This file lists the known defects of the matcher that are not fixed yet.
Each entry states the effect, the cause, and the possible corrections.
When a fix is merged, remove its entry and record the fix in [../ChangeLog.md](../ChangeLog.md).

## 1. Stalled uploads hold the in-flight slots

- Found: 2026-09-29, item 2 of the code review
  [reports/2026-09-29_code-review.md](reports/2026-09-29_code-review.md).
- Status: open. The owner decided to fix it later.
- Effect: with the default limits, 8 clients can fill all in-flight slots. Each client
  sends the headers and a few bytes of the body, and then stops. Every other client gets
  `HTTP 503 {"detail":"matcher is busy"}` after the queue timeout of 0.25 s. One stall
  lasts up to the upload timeout of 30 s. A client can repeat it. The prod LAN port
  `192.168.86.14:28000` has no authorization.
- Cause: `RequestProtectionMiddleware` takes an in-flight slot before the application
  reads the request body (`protection.py`, `_acquire_slot` in `__call__`). The slot stays
  taken until the upload is complete or until the upload timeout fires.
- Reproduction: start the matcher with `matcher/tests/config.yaml`. Open 8 connections.
  Each connection sends the headers and 100 bytes of a `POST /v1/eval/predict` body.
  Then send a normal request.
- Possible corrections. The owner did not select one.
  - Take the slot after the body is complete. Use a separate, larger limit for parallel
    uploads.
  - Make the upload timeout shorter.
  - Buffer the request body in the reverse proxy. This protects only the clients of that
    proxy.
- Open question: the review did not check whether the public edge buffers request bodies.

## 2. Hand selection gives HTTP 400 for a damaged image

- Found: 2026-09-29, during the fix of item 1 of the code review.
- Status: open. The owner did not decide on it.
- Effect: with `hand_selection: true`, a damaged JPEG, MPO, or WEBP can pass the
  admission check. `POST /v1/eval/predict` and `POST /v1/match` then answer HTTP 400
  `image cannot be decoded`. Without hand selection, the same file gets HTTP 422
  `image file is invalid or damaged`. `README.md` documents HTTP 422 for a damaged image.
- Cause: hand selection decodes the image in `group._normalize_image` before
  `siglip2.model_input`. `_normalize_image` maps a decode error to `GroupMatchError(400)`.
  `POST /v1/group/match` documents this HTTP 400.
- Prod effect: none at present. The prod configuration has `hand_selection: false`.
