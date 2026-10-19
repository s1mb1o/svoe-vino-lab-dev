# Verified Base NaFlex p512 default

Date: 2026-10-19

## Objective

Make `google/siglip2-base-patch16-naflex` with 512 patches the main Android encoder.
Use the verified complete graph from `siglip2-naflex-litert` v0.2.0.
Keep Russian UI text and Android API 28 support.

## Runtime

Pin the released AAR and its SHA-256 in the application build.
Use the released preprocessor and complete encoder graph.
Request FP32 GPU execution with BUFFER storage and no GPU program cache.
Keep CPU and GPU accelerator settings.
Use CPU after a failed automatic GPU check or failed automatic GPU inference.
Create, execute, and close GPU resources on one dedicated worker thread.
Keep the existing split runtimes readable for external experimental packs.

## Pack contract

Add format version 6 with runtime `naflex-complete`.
Pin the Base p512 model, revision, profile, and source position table hashes.
Keep 768-dimensional normalized float32 vectors.
Reject a fixed Base/224 index and a split-runtime index.
Use matching reference vectors from the verified model package.
Keep barcode relations and transparent display images in the built-in pack.
Keep generated model files and catalogue packs outside Git.

The main query pipeline preserves the full image and its aspect ratio.
It does not segment the query by default.
Keep DIS and YOLO as explicit optional query modes.
Keep the legacy 72-angle exporters available without reusing their old vectors.
Use the verified single-reference p512 index for this default-pack change.
Do not claim p512 72-angle coverage until the matching vectors are calculated.
Record the actual reference count of the built-in pack.

## Installation

Upgrade the built-in pack when an installed pack has an older runtime.
Preserve the 18+ choice, history, and unrelated settings.
Select no segmentation when the old built-in pack is upgraded.
Reset the saved accelerator check when the model identity changes.
Keep debug HTTP off by default.

## Validation

Test format validation, tensor contracts, index identity, and upgrade selection.
Test model-pack export with deterministic small fixtures.
Run Android unit tests, lint, and debug assembly.
Check the final APK version and embedded pack hashes.
Run device parity and a bounded Eval subset when a USB phone is available.
Record a missing device as an unperformed device check.

## Readiness

The owner requested Base NaFlex p512 as the main pipeline.
The selected graph and library already have two-phone measurements.
No USB Android device was visible during the first integration preflight.
Implementation and host validation are complete.
The debug APK installed on Pixel 8 as an update.
The owner confirmed no segmentation and unlocked Pixel 8.
The thirty-image GPU runtime pilot passed.
CPU/GPU parity passed on one transparent reference.
Desktop/device parity passed on fourteen pilot images.
UI recognition and history persistence passed after a cold restart.
The debug HTTP server is disabled. Temporary device files and forwarding are removed.
The subsequent full `my` run completed 3,409 requests without an HTTP error or restart.
Positive Top-1 was 69.09%. Client median latency was 924 ms.
The full run reached `SEVERE` and failed the short-pilot thermal gate.
HEIC, EXIF orientation, and optional segmentation were not retested.
Read `../reports/2026-10-19_pixel8-base-p512-full-my.md` for full-run results and limits.
Read `../reports/2026-10-19_base-p512-default.md` for the exact scope.
