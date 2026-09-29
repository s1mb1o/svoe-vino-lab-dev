# Internal profile queue snapshot

Status: partial.
Complete authorized profiles: 1 of 53. Total queue profiles: 54.
Expected coverage: 2228 query rows and 1851 unique images.
External recognizer approval: pending.

| Profile | State | Attempts | Workers | Cache requested | Barcode configured | Run ID |
|---|---|---:|---:|---|---|---|
| vino-svoe-search-by-photo | awaiting_user_approval | 0 | 4 | yes | unknown | — |
| siglip2-p256-as-is | pending | 0 | 4 | yes | unknown | — |
| siglip2-p256-crop | pending | 0 | 4 | yes | unknown | — |
| siglip2-p256-crop-seg | pending | 0 | 4 | yes | unknown | — |
| siglip2-p512-as-is | pending | 0 | 4 | yes | unknown | — |
| siglip2-p512-crop | pending | 0 | 4 | yes | unknown | — |
| siglip2-p1024-as-is | waiting_for_index | 0 | 4 | yes | unknown | — |
| siglip2-p1024-crop | waiting_for_index | 0 | 4 | yes | unknown | — |
| siglip2-p14-384-as-is | pending | 0 | 4 | yes | unknown | — |
| siglip2-p14-384-crop | pending | 0 | 4 | yes | unknown | — |
| siglip2-256-as-is | pending | 0 | 4 | yes | unknown | — |
| siglip2-256-crop | pending | 0 | 4 | yes | unknown | — |
| siglip2-384-as-is | pending | 0 | 4 | yes | unknown | — |
| siglip2-384-crop | pending | 0 | 4 | yes | unknown | — |
| siglip2-512-as-is | done | 1 | 4 | yes | no | 2026-09-27T005701Z-lab-siglip2-512-as-is-my |
| siglip2-512-crop | running | 1 | 4 | yes | no | 2026-09-27T010430Z-lab-siglip2-512-crop-my |
| naflexvit-p256-as-is | pending | 0 | 4 | yes | unknown | — |
| naflexvit-p256-crop | pending | 0 | 4 | yes | unknown | — |
| pe-core-l14-336-as-is | pending | 0 | 4 | yes | unknown | — |
| pe-core-l14-336-crop | pending | 0 | 4 | yes | unknown | — |
| dinov3-vitb16-as-is | pending | 0 | 4 | yes | unknown | — |
| dinov3-vitb16-crop | pending | 0 | 4 | yes | unknown | — |
| dinov3-vitl16-as-is | pending | 0 | 4 | yes | unknown | — |
| dinov3-vitl16-crop | pending | 0 | 4 | yes | unknown | — |
| local-siglip2-p256-as-is | pending | 0 | 1 | yes | unknown | — |
| local-siglip2-p256-crop | pending | 0 | 1 | yes | unknown | — |
| barcode-siglip2-p256-as-is | pending | 0 | 4 | yes | unknown | — |
| barcode-siglip2-p256-crop | pending | 0 | 4 | yes | unknown | — |
| barcode-siglip2-p256-crop-seg | pending | 0 | 4 | yes | unknown | — |
| barcode-siglip2-p512-as-is | pending | 0 | 4 | yes | unknown | — |
| barcode-siglip2-p512-crop | pending | 0 | 4 | yes | unknown | — |
| barcode-siglip2-p1024-as-is | waiting_for_index | 0 | 4 | yes | unknown | — |
| barcode-siglip2-p1024-crop | waiting_for_index | 0 | 4 | yes | unknown | — |
| barcode-siglip2-p14-384-as-is | pending | 0 | 4 | yes | unknown | — |
| barcode-siglip2-p14-384-crop | pending | 0 | 4 | yes | unknown | — |
| barcode-siglip2-256-as-is | pending | 0 | 4 | yes | unknown | — |
| barcode-siglip2-256-crop | pending | 0 | 4 | yes | unknown | — |
| barcode-siglip2-384-as-is | pending | 0 | 4 | yes | unknown | — |
| barcode-siglip2-384-crop | pending | 0 | 4 | yes | unknown | — |
| barcode-siglip2-512-as-is | pending | 0 | 4 | yes | unknown | — |
| barcode-siglip2-512-crop | pending | 0 | 4 | yes | unknown | — |
| barcode-naflexvit-p256-as-is | pending | 0 | 4 | yes | unknown | — |
| barcode-naflexvit-p256-crop | pending | 0 | 4 | yes | unknown | — |
| barcode-pe-core-l14-336-as-is | pending | 0 | 4 | yes | unknown | — |
| barcode-pe-core-l14-336-crop | pending | 0 | 4 | yes | unknown | — |
| barcode-dinov3-vitb16-as-is | pending | 0 | 4 | yes | unknown | — |
| barcode-dinov3-vitb16-crop | pending | 0 | 4 | yes | unknown | — |
| barcode-dinov3-vitl16-as-is | pending | 0 | 4 | yes | unknown | — |
| barcode-dinov3-vitl16-crop | pending | 0 | 4 | yes | unknown | — |
| barcode-local-siglip2-p256-as-is | pending | 0 | 1 | yes | unknown | — |
| barcode-local-siglip2-p256-crop | pending | 0 | 1 | yes | unknown | — |
| rerank-siglip2-512-crop | pending | 0 | 4 | yes | unknown | — |
| barcode-rerank-siglip2-512-crop | pending | 0 | 4 | yes | unknown | — |
| barcode-rerank-siglip2-512-crop-label | pending | 0 | 4 | yes | unknown | — |

## Recorded metrics

Partial and unverified attempts remain labelled in the State column.

| Profile | State | Rows / expected | Errors / degraded | R@1 | R@5 | Forbidden top-1 / negative | Bulk p50 / p95 ms | Run / attempt s | Rows/s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| vino-svoe-search-by-photo | awaiting_user_approval | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| siglip2-p256-as-is | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| siglip2-p256-crop | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| siglip2-p256-crop-seg | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| siglip2-p512-as-is | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| siglip2-p512-crop | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| siglip2-p1024-as-is | waiting_for_index | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| siglip2-p1024-crop | waiting_for_index | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| siglip2-p14-384-as-is | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| siglip2-p14-384-crop | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| siglip2-256-as-is | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| siglip2-256-crop | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| siglip2-384-as-is | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| siglip2-384-crop | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| siglip2-512-as-is | done | 2228 / 2228 | 0 / 0 | 79.93% (n=1644) | 95.44% (n=1644) | 94 / 584 | 137.00 / 228.00 | 80.00 / 80.88 | 27.85 |
| siglip2-512-crop | running | 405 / 2228 | 0 / — | — | — | — / — | — / — | — / — | — |
| naflexvit-p256-as-is | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| naflexvit-p256-crop | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| pe-core-l14-336-as-is | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| pe-core-l14-336-crop | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| dinov3-vitb16-as-is | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| dinov3-vitb16-crop | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| dinov3-vitl16-as-is | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| dinov3-vitl16-crop | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| local-siglip2-p256-as-is | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| local-siglip2-p256-crop | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| barcode-siglip2-p256-as-is | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| barcode-siglip2-p256-crop | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| barcode-siglip2-p256-crop-seg | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| barcode-siglip2-p512-as-is | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| barcode-siglip2-p512-crop | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| barcode-siglip2-p1024-as-is | waiting_for_index | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| barcode-siglip2-p1024-crop | waiting_for_index | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| barcode-siglip2-p14-384-as-is | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| barcode-siglip2-p14-384-crop | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| barcode-siglip2-256-as-is | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| barcode-siglip2-256-crop | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| barcode-siglip2-384-as-is | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| barcode-siglip2-384-crop | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| barcode-siglip2-512-as-is | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| barcode-siglip2-512-crop | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| barcode-naflexvit-p256-as-is | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| barcode-naflexvit-p256-crop | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| barcode-pe-core-l14-336-as-is | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| barcode-pe-core-l14-336-crop | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| barcode-dinov3-vitb16-as-is | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| barcode-dinov3-vitb16-crop | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| barcode-dinov3-vitl16-as-is | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| barcode-dinov3-vitl16-crop | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| barcode-local-siglip2-p256-as-is | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| barcode-local-siglip2-p256-crop | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| rerank-siglip2-512-crop | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| barcode-rerank-siglip2-512-crop | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |
| barcode-rerank-siglip2-512-crop-label | pending | — / 2228 | — / — | — | — | — / — | — / — | — / — | — |

## Attempt notes

- `siglip2-p1024-as-is`: no index: build it on /embedding
- `siglip2-p1024-crop`: no index: build it on /embedding
- `barcode-siglip2-p1024-as-is`: no index: build it on /embedding
- `barcode-siglip2-p1024-crop`: no index: build it on /embedding

## Label profile comparison

State: pending.
Aggregate recorded bulk metrics. This is not a paired prediction comparison.
Both profiles need a verified complete recorded attempt.

## Measurement limits

- All queue profiles remain visible. A missing metric means unknown, not zero.
- Completion uses saved runner-exit evidence and artifact validation. This reader does not rehash run files or verify current PIDs.
- An archive mismatch can occur during reconciliation. Repeat the snapshot after reconciliation.
- Metrics from failed, active, or unverified attempts are partial. Do not rank these attempts as complete runs.
- Latency describes cached bulk requests. It does not establish new-image demo latency or a three-second response guarantee.
- Run wall excludes work outside the benchmark. Attempt elapsed is the recorded intent-to-final interval. It is not isolated startup time.
- Barcode requested does not mean barcode configured. Profiles without a barcode stage do not add one.
- Negative labels exclude a named wine. A different prediction does not prove correct identification.
- Index coverage and model cache state can differ. Compare these records before interpreting timing or quality differences.

Automatic approval review requires explicit permission to send all my test photos to this external API.
