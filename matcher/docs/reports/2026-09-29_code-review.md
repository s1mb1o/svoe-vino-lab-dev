# Matcher code review

Date: 2026-09-29

## Scope

The review read every Python module of `matcher/`: `app.py`, `service.py`,
`protection.py`, `siglip2.py`, `group.py`, `main_scene.py`, `bundle.py`, `catalog.py`,
and `audit.py`.
The review compared the code with `README.md`, `Dockerfile`, and
`<workspace>/deploy/gx10/matcher-prod.md`.
The review did not change code.

Baseline: all 113 tests passed with `~/.venvs/svoe-vino-lab/bin/python -W
error::ResourceWarning -m unittest discover matcher/tests`.
The system `python3` (3.14.7) cannot import `fastapi`, because its `pydantic` install is
broken (`typing_inspection.introspection` is missing).

Each finding has a status.
"Confirmed" means that a local probe reproduced the finding.
"Code reading" means that no probe was made.
"Unverified" means that the finding depends on a system that the review did not read.

## Follow-up

On 2026-09-29 the owner selected these actions:

- Item 1: fixed with option A. `model_input` maps a decode error to HTTP 422.
- Item 2: recorded in [../KNOWN_ISSUES.md](../KNOWN_ISSUES.md) for a later fix.
- Item 5: fixed. `validate_image` does not change the warnings filters. A pixel limit
  above the Pillow limit stops the start.
- Item 7: fixed later on 2026-09-29 (owner answer of 21:07:52). `_read_cards` checks the
  type of each card field.
- Item 4: the deploy document names `GET /readyz` since the same fix. The model requests
  of the health check are intended: `docs/cascade.md`, section "Limits", states them.
- The other items have no decision.

The entry of 2026-09-29 in `ChangeLog.md` describes the fixes.

## Findings

### 1. A truncated JPEG gives HTTP 500

Status: confirmed with a local uvicorn server, a fixture bundle, and a fake SigLIP2
endpoint.

- `validate_image` calls `image.verify()` (`protection.py:243`). Pillow does not decode
  JPEG pixel data in `verify()`. A JPEG that is cut in half passes the check.
- `model_input` (`siglip2.py:41-46`) decodes the image and raises
  `OSError: image file is truncated`.
- `process_image` (`app.py:298`) maps only `HTTPException`, `GroupMatchError`, and
  `Siglip2Error`. Every other exception gives HTTP 500 and a stack trace in the log.

Result: `POST /v1/eval/predict` and `POST /v1/match` answer HTTP 500 for this file.
`README.md` promises HTTP 422 for a damaged image.
The same file gives HTTP 400 on `POST /v1/group/match` and with `hand_selection: true`,
because `_normalize_image` (`group.py:132`) maps `OSError` to `GroupMatchError(400)`.
A truncated WEBP gets HTTP 422 from `validate_image`, as documented.

### 2. Stalled uploads block every other client

Status: confirmed with the mock configuration `matcher/tests/config.yaml`.

- The middleware takes an in-flight slot before it reads the request body
  (`protection.py:79`).
- A client keeps the slot until its upload is complete or until the upload timeout
  (default 30 s).

Probe: 8 clients sent the headers and 100 bytes of the body, then stopped.
A normal client then got `HTTP 503 {"detail":"matcher is busy"}` after 0.25 s.
A client can repeat the stall every 30 s.
The prod LAN port `192.168.86.14:28000` has no authorization.
The review did not check whether the public edge buffers request bodies.

### 3. `/readyz` has no limit and no authorization

Status: code reading.

- `/readyz` is not in `PROTECTED_PATHS` (`protection.py:19`).
- Each call sends one SigLIP2 embedding request. With `hand_selection: true`, each call
  also sends one SAM3 request (`service.py:136-148`).
- The call runs in `asyncio.to_thread` (`app.py:238`). The matching work uses the same
  default thread pool (`app.py:260`, `app.py:268`, `app.py:294`).

Result: a burst of `/readyz` calls sends model requests with no limit. The burst can also
fill the thread pool, so that the matching work waits.

### 4. The Docker healthcheck sends a model request every 30 s

Status: unverified. The review did not read the llama-swap configuration of gx10.

- The Dockerfile `HEALTHCHECK` calls `/readyz` every 30 s. Each call sends one SigLIP2
  embedding request.
- If llama-swap unloads an idle model or swaps models in a group, the probe loads the
  SigLIP2 model again every 30 s. The load can remove another model from the GPU.
- `<workspace>/deploy/gx10/matcher-prod.md:46` says that the image health check uses
  `GET /healthz`. The Dockerfile now uses `/readyz`. The document is out of date.

### 5. `validate_image` changes the global warnings filter in worker threads

Status: code reading. The finding has no effect with the default pixel limit.

- `warnings.catch_warnings()` (`protection.py:229`) changes the filter list of the whole
  process. Python 3.11 does not make this change thread-local.
  `validate_image` runs in several threads at the same time.
- Two parallel requests can leave the `error` filter installed for the process. They can
  also remove the filter while a third request is in its check.
- The explicit pixel check at `protection.py:241` still rejects each image above the
  default limit of 40,000,000 pixels.
- A value of `SVOE_VINO_MATCHER_MAX_IMAGE_PIXELS` above `Image.MAX_IMAGE_PIXELS`
  (89,478,485) has no effect. Pillow warns at that size, and the filter changes the
  warning into HTTP 413.

### 6. `predict` and rank 1 of `match` can differ

Status: code reading. The current bundles do not have this problem.

- `Siglip2Matcher.predict` ranks all slugs of the bundle (`service.py:134`,
  `bundle.py:59-68`).
- `Siglip2Matcher.match` removes each slug that has no card (`service.py:165-169`).
- If `wines.jsonl` of a version 2 bundle has no record for a slug, the two endpoints can
  give different answers. `README.md` states both "rank 1 always equals predict" and
  "a wine without a card is skipped". These two statements conflict in this case.
- Check on 2026-09-29: both local bundles have a card for each of the 2,094 slugs of the
  view `full`.

### 7. Card fields are not type-checked when the bundle loads

Status: code reading.

- `_read_cards` (`bundle.py:188-193`) checks the types of `wine_slug`, `name`,
  `page_url`, and `qr_urls`.
- It does not check `producer`, `category`, `region`, `color`, `grapes`, `image_url`, or
  the items of `qr_urls`.
- A value with a wrong type passes the load. `WineCard` then fails in each response that
  contains this wine, and the client gets HTTP 500.
- `workbench/scripts/validate_matcher_bundle.py` checks the full contract before a
  deploy. The review did not read that script.

### 8. Efficiency

Status: measured with one test photo.

- A group crop is a JPEG of about 200 KB. `model_input` encodes it again as a PNG of
  about 930 KB. An embedding request with 64 crops then has a body of about 77 MB.
  The PNG step can be intentional, to keep the steps of the lab pipeline. The review did
  not check this intent.
- `segment_group` prepares each bottle before the duplicate check (`group.py:88-93`).
  Each duplicate costs one mask decode, one PNG encode, and one JPEG encode.

### 9. Housekeeping

- `matcher/1.txt` is an empty file. It is not in the Docker image. The review did not
  identify its origin.
