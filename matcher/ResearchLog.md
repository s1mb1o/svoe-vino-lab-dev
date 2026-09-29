# Research log

## Conditional model readiness, 2026-09-29

Three options were considered.
The first option made `/healthz` call each model dependency.
The second option kept `/healthz` as liveness and added `/readyz` for dependency checks.
The third option checked only a lightweight model-list endpoint.

The matcher uses the second option.
Docker uses `/readyz` for its healthcheck.
The mock pipeline makes no external request.
The SigLIP2 pipeline sends one small embedding request.
A pipeline with `hand_selection: true` also sends one small SAM3 request.

This decision keeps liveness available during a model outage.
It also validates the configured model and embedding dimension.
Each dependency probe has an eight-second timeout.
The Docker healthcheck has a 20-second timeout because a hand-selection probe can use
both dependencies in sequence.

## Reproducible container dependencies, 2026-09-29

The dependency input has exact direct versions in `requirements.txt`.
This file does not lock transitive versions or distribution hashes.

Three options were considered.
The first option keeps the direct requirements and adds a generated lock file.
The second option replaces the direct requirements with one large locked file.
The third option adds `pyproject.toml` and `uv.lock`.

The matcher uses the first option.
`requirements.txt` stays the editable dependency input.
`requirements.lock` contains the complete Python 3.11 Linux graph and distribution hashes.
Docker and `matcher/tests/run_ci.sh` use pip with `--require-hashes`.
The Docker base image uses an OCI digest.

This decision keeps dependency updates explicit.
An update MUST regenerate the lock file and validate the Docker build.
The lock file targets the Python 3.11 Linux container and CI environment.
Local environments with a different Python version use `requirements.txt`.

## Group photo matching, 2026-09-28

The existing Web UI shelf implementation established the SAM3 request contract.
The request uses `wine bottle`, detection threshold 0.4, mask threshold 0.5, and full-frame PNG masks.

SAM3 detector boxes can extend outside the image.
SAM3 masks can contain disconnected fragments outside a detector box.
The matcher clamps each detector box and removes mask pixels outside that box.

A shelf can contain many bottles.
Sequential embedding requests increase network latency for every bottle.
The OpenAI-compatible embedding contract accepts an input array.
The SigLIP2 backend now sends all bottle crops in one request and validates one indexed vector per crop.

The production SigLIP2 service accepts at most 64 inputs in one request.
A shelf photo produced 93 bottle crops and caused an HTTP 400 response from SigLIP2.
The matcher now splits larger logical batches into transport requests of at most 64 inputs.
The matcher preserves the input order across these requests.

The response returns a normalized preview.
This preview makes the coordinates and masks independent of browser EXIF behavior.
The response returns cropped transparent masks instead of full-frame masks.
This choice reduces response size and supports direct UI overlays.

The detailed contract is in `docs/group-match.md`.
