# Segmentation and SigLIP2 model matrix

Date: 2026-09-29

## Goal

Measure how no segmentation, DIS, and SAM3 affect retrieval with six SigLIP2 SO400M
image towers.

Run the complete `my` test set.
Disable barcode lookup.
Use the same catalogue snapshot and query snapshot in each matrix cell.

## Matrix

Test these NaFlex models:

- `gx10-siglip2-so400m-patch16-naflex-p256`
- `gx10-siglip2-so400m-patch16-naflex-p512`
- `gx10-siglip2-so400m-patch16-naflex-p1024`

Test these fixed-resolution models:

- `gx10-siglip2-so400m-patch16-256`
- `gx10-siglip2-so400m-patch16-384`
- `gx10-siglip2-so400m-patch16-512`

Compare these compute levels:

| Level | NaFlex | Fixed | Patch tokens |
|---|---|---|---:|
| 1 | p256 | 256 | 256 and 256 |
| 2 | p512 | 384 | 512 and 576 |
| 3 | p1024 | 512 | 1,024 and 1,024 |

Run each model without segmentation, with DIS, and with SAM3.
The matrix has 18 cells.

## Prepared images

Create one prepared catalogue image and one prepared query image for each input method.
Reuse each prepared image for all six models.

The no-segmentation path MUST use the full source image.
It MUST NOT use a mask, crop, or object removal.
It MUST composite an existing alpha channel on white to make an RGB image.
It MUST resize the long side to at most 1,024 pixels and keep the aspect ratio.
It MUST NOT upscale an image.

The DIS path MUST use the pinned `litert-community/DIS-ISNet-LiteRT` revision from
`config.yaml`.
It MUST use threshold `0.5` and margin `0.04`.
It MUST composite the soft mask on white.
It MUST resize the long side to at most 1,024 pixels and keep the aspect ratio.

The SAM3 catalogue path MUST use the stored package derivative of the catalogue source.
The SAM3 query path MUST use the cached main-scene package selection.
It MUST remove the background, composite on white, and resize the long side to at most
1,024 pixels while it keeps the aspect ratio.

Record each prepared PNG SHA-256.
Record each source image SHA-256.
Do not send a new SAM3 request when a cached answer is absent.
Record the missing input as an error.

## Vectors and ranking

Send prepared PNG files to the existing embedding gateway.
Use batches of at most eight images.
Normalize each returned vector to unit length.
Store the vectors as float32 arrays.

Use the same catalogue source-to-wine mapping for every cell.
The score of a wine is the maximum cosine over its catalogue images.
Rank wines by descending score and then by slug.

## Metrics

Record these metrics for each cell:

- positive R@1, R@5, and R@10;
- positive MRR@10;
- negative rejection at rank 1;
- negative false matches at rank 1;
- preprocessing errors;
- embedding errors;
- elapsed preprocessing and embedding time.

For each model, compare no segmentation, DIS, and SAM3 with the exact paired McNemar
test.
For each segmentation method, compare the three compute levels.
Report win and loss counts.

## Artifacts

Write generated artifacts under
`runs/segmentation-model-matrix-2026-09-29/`.
Make each phase resumable.
Do not change a production catalogue index.
Do not change the database.
Do not restart or reconfigure a GX10 service.

Write the result to
`docs/reports/2026-09-29_segmentation-model-matrix.md`.

## Completion

The complete matrix and the no-segmentation extension finished on 2026-09-29.
All 18 cells used the frozen 2,270-source catalogue and the frozen 2,226-query set.
The run produced 80,898 vectors.
SAM3 improved R@1 against no segmentation for all six models.
The best cell was SAM3 with fixed 512 at 81.42% R@1 and 96.66% R@5.
The best no-segmentation cell was fixed 512 at 78.69% R@1 and 95.75% R@5.
No segmentation fixed 512 was 4.13 pp better than DIS fixed 512 at R@1.
The verification passed.
The report contains the full metrics, paired tests, evidence hashes, and failure list.
