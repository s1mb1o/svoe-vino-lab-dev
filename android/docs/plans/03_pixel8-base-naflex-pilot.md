# Pixel 8 SigLIP2 Base pilot

Date: 2026-10-19

## Objective

Compare four SigLIP2 Base encoder variants on one Pixel 8.
Reject a variant before the full `my` test if its vectors, runtime, or stability do not pass the pilot gates.

## Encoder variants

The pilot MUST test these encoder variants:

1. `base-fixed-p224-control`: the current fixed SigLIP2 Base/224 encoder.
2. `base-naflex-p256-standard`: SigLIP2 Base NaFlex with 256 patches and standard attention pooling.
3. `base-naflex-p256-5a`: SigLIP2 Base NaFlex with 256 patches and foreground-aware attention pooling.
4. `base-naflex-p512-standard`: SigLIP2 Base NaFlex with 512 patches and standard attention pooling.

The NaFlex variants MUST use `google/siglip2-base-patch16-naflex`.
The NaFlex output MUST have 768 dimensions.

## Foreground-aware pooling

The 5a variant MUST reuse the DIS or YOLO foreground mask.
The application MUST resize the mask with the same geometry as the image patches.
For each patch, it MUST calculate the mean soft foreground value `m`.
It MUST calculate the patch weight as `0.1 + 0.9 * m`.
It MUST add `log(weight)` to the standard attention logits.
It MUST keep padding logits masked.
It MUST keep the original post-LayerNorm, attention projection, pooling LayerNorm, and MLP.

Transparent catalogue reference images MUST use the alpha channel as the foreground mask.

## Reference aggregation

The control scoring rule is the maximum cosine score for one wine.
The pilot MUST also calculate `top2-mean`.
`top2-mean` is the arithmetic mean of the two highest reference cosine scores for one wine.
If a wine has one reference, `top2-mean` MUST use that score.

## Export and parity

The exporter MUST create two Base NaFlex backbone models.
The models MUST have static limits of 256 and 512 patches.
The exporter MUST create standard and 5a pooling models.
The exporter MUST write model metadata and SHA-256 values.
Generated model files MUST stay outside Git.

The desktop split output MUST match the original PyTorch output for standard pooling.
The exported LiteRT output MUST match its PyTorch split output.
The Android CPU output MUST have cosine agreement of at least `0.99999` with the desktop LiteRT output.
The maximum absolute component error MUST be at most `0.001`.
The Android GPU output MUST meet the same gates before the pilot uses the GPU.
A failed accelerator MUST not cause the whole encoder variant to fail if CPU passes.

## Representative set

The pilot MUST use 30 deterministic and segmentable images from `my`.
The set MUST contain successful baseline matches, baseline misses, and negative queries.
The set MUST cover portrait, landscape, small-object, low-light, glare, and close-label cases when these labels are available.
The selection manifest MUST record the source query ID and the selection reason.

## Device measurements

The pilot MUST record these values for each request:

- inference latency and total request latency;
- process PSS and RSS;
- battery temperature and reported thermal sensors;
- Android thermal status;
- process ID before and after the request;
- HTTP result, vector validity, and selected accelerator.

The pilot MUST retain `logcat` evidence for native crashes.
The pilot MUST record the model pack ID, application version, device model, Android version, and build fingerprint.

## Pilot gates

An encoder variant passes when all these conditions are true:

- vector parity passes on the selected accelerator;
- all 30 requests complete without an application restart or native abort;
- all produced vectors are finite and have 768 dimensions;
- no request exceeds 10 seconds;
- median total latency is at most 3 seconds;
- p95 total latency is at most 5 seconds;
- peak application PSS is at most 2.5 GiB;
- Android does not report `SEVERE`, `CRITICAL`, `EMERGENCY`, or `SHUTDOWN` thermal status.

A segmentation rejection is not an encoder failure.
The 30-image set excludes baseline segmentation rejections so that each request measures the encoder.

## Full test

The pilot MUST run the full `my` set only for encoder variants that pass all pilot gates.
For each passing encoder, the full test MUST calculate the maximum-score and `top2-mean` results.
The report MUST use `expected.jsonl` and accepted alternative slugs.
The report MUST include Top-1, error count, latency percentiles, process stability, peak memory, and thermal observations.

## Artifacts

The implementation MUST create these tracked artifacts:

- this plan;
- a 30-image selection manifest;
- a pilot summary report;
- a full-test summary for each passing variant;
- documentation updates in `README.md`, `ResearchLog.md`, `ChangeLog.md`, and `SMOKE_TESTS.md`.

Raw vectors, model files, catalogue packs, images, and large logs MUST stay outside Git.

## State

The owner selected this pilot on 2026-10-19.
Implementation is complete.
No encoder variant passed all pilot gates.
No new full `my` run was started.
See `../reports/2026-10-19_pixel8-siglip2-base-pilot/report.md`.
