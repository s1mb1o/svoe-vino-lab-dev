# No segmentation, DIS, and SAM3 across SigLIP2 SO400M models

Date: 2026-09-29

## Result

SAM3 improved positive retrieval against no segmentation with all six SigLIP2 models.
The R@1 gain was from 2.73 to 12.33 percentage points.
Each R@1 gain was significant in the exact paired McNemar test.

The best cell was SAM3 with fixed 512.
It reached 81.42% R@1, 96.66% R@5, and 97.51% R@10.

The best DIS R@1 was 74.98% with NaFlex p1024.
The best DIS R@5 was 92.35% with fixed 512.

The best result without segmentation was fixed 512.
It reached 78.69% R@1, 95.75% R@5, and 97.39% R@10.
It was 2.73 pp below the best SAM3 R@1 result.
It was 4.13 pp above the matching DIS R@1 result.

Barcode lookup was disabled.
The result measures segmentation and vector retrieval only.

## Scope

The frozen `my` set had 2,226 queries.
It had 1,647 positive queries and 579 negative queries.
The frozen catalogue had 2,270 image sources for 2,093 wines.

Each cell used the same catalogue manifest and query manifest.
Each input method prepared one shared input set.
All six models of that input method used the same prepared PNG files.

The matrix had these 18 cells:

- No segmentation with NaFlex p256, p512, and p1024.
- No segmentation with fixed 256, 384, and 512.
- DIS with NaFlex p256, p512, and p1024.
- DIS with fixed 256, 384, and 512.
- SAM3 with NaFlex p256, p512, and p1024.
- SAM3 with fixed 256, 384, and 512.

The comparable compute levels were:

| Level | NaFlex patch limit | Fixed input | Approximate patch tokens |
|---|---:|---:|---:|
| Low | 256 | 256 | 256 and 256 |
| Medium | 512 | 384 | 512 and 576 |
| High | 1,024 | 512 | 1,024 and 1,024 |

## Method

The DIS path used `litert-community/DIS-ISNet-LiteRT` revision
`1b966dbe2f33bd5ca1299cf94fbab59265210b6b`.
It used threshold 0.5 and margin 0.04.

The SAM3 catalogue path used the stored package derivative.
The SAM3 query path used the cached main-scene package selection.

The no-segmentation path did not use a mask, crop, or object removal.
It used the full source image.
It composited only an existing alpha channel on white to make an RGB image.
It did not change opaque pixels.

The DIS and SAM3 paths composited the selected object on white.
All three paths kept the aspect ratio.
All three paths limited the long side to 1,024 pixels without upscaling.

The benchmark normalized every returned vector.
The score of a wine was the maximum cosine over its catalogue sources.
The benchmark ranked 2,093 wines.

The benchmark used the exact paired McNemar test.
An error counted as an incorrect result.
The negative rejection metric used the workbench rule.
A negative query was rejected at rank 1 when another slug was first.

## Absolute metrics

| Input method | Model | R@1 | R@5 | R@10 | MRR@10 | Negative rejection | Positive errors |
|---|---|---:|---:|---:|---:|---:|---:|
| None | NaFlex p256 | 62.78% | 86.58% | 90.16% | 72.97% | 82.21% | 0 |
| None | NaFlex p512 | 71.46% | 92.41% | 95.20% | 80.80% | 80.48% | 0 |
| None | NaFlex p1024 | 76.81% | 94.90% | 97.21% | 84.97% | 82.21% | 0 |
| None | Fixed 256 | 58.96% | 84.21% | 89.25% | 69.85% | 81.52% | 0 |
| None | Fixed 384 | 72.92% | 93.38% | 95.75% | 81.93% | 83.42% | 0 |
| None | Fixed 512 | 78.69% | 95.75% | 97.39% | 86.22% | 82.38% | 0 |
| DIS | NaFlex p256 | 65.88% | 88.28% | 91.32% | 75.73% | 82.38% | 5 |
| DIS | NaFlex p512 | 73.59% | 90.89% | 93.38% | 81.39% | 80.48% | 5 |
| DIS | NaFlex p1024 | 74.98% | 92.11% | 94.54% | 82.52% | 82.73% | 5 |
| DIS | Fixed 256 | 62.05% | 85.61% | 89.37% | 72.22% | 83.25% | 5 |
| DIS | Fixed 384 | 71.77% | 90.89% | 93.69% | 80.26% | 83.77% | 5 |
| DIS | Fixed 512 | 74.56% | 92.35% | 94.72% | 82.56% | 82.38% | 5 |
| SAM3 | NaFlex p256 | 75.11% | 94.72% | 96.11% | 83.82% | 83.59% | 0 |
| SAM3 | NaFlex p512 | 78.87% | 95.39% | 97.15% | 86.43% | 81.52% | 0 |
| SAM3 | NaFlex p1024 | 80.02% | 95.93% | 97.02% | 87.14% | 81.69% | 0 |
| SAM3 | Fixed 256 | 70.25% | 91.26% | 94.41% | 79.74% | 81.69% | 0 |
| SAM3 | Fixed 384 | 76.81% | 95.32% | 96.72% | 85.01% | 84.28% | 0 |
| SAM3 | Fixed 512 | **81.42%** | **96.66%** | **97.51%** | **88.22%** | 82.73% | 0 |

The positive denominator was 1,647.
The negative denominator was 579.

## Effect of segmentation against no segmentation

The table shows `segmentation - no segmentation`.
The wins and losses refer to the positive R@1 result.

| Model | Method | R@1 delta | R@1 wins/losses | R@1 p | R@5 delta | R@5 p | Negative rejection delta | Negative p |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| NaFlex p256 | DIS | +3.10 pp | 244 / 193 | 0.0167 | +1.70 pp | 0.0572 | +0.17 pp | 1.000 |
| NaFlex p256 | SAM3 | +12.33 pp | 299 / 96 | 2.30e-25 | +8.14 pp | 3.33e-27 | +1.38 pp | 0.451 |
| NaFlex p512 | DIS | +2.13 pp | 198 / 163 | 0.0734 | -1.52 pp | 0.0444 | 0.00 pp | 1.000 |
| NaFlex p512 | SAM3 | +7.41 pp | 214 / 92 | 2.37e-12 | +2.98 pp | 8.41e-8 | +1.04 pp | 0.581 |
| NaFlex p1024 | DIS | -1.82 pp | 132 / 162 | 0.0906 | -2.79 pp | 1.64e-5 | +0.52 pp | 0.830 |
| NaFlex p1024 | SAM3 | +3.22 pp | 151 / 98 | 0.000945 | +1.03 pp | 0.0300 | -0.52 pp | 0.826 |
| Fixed 256 | DIS | +3.10 pp | 265 / 214 | 0.0222 | +1.40 pp | 0.139 | +1.73 pp | 0.382 |
| Fixed 256 | SAM3 | +11.29 pp | 285 / 99 | 5.50e-22 | +7.04 pp | 5.10e-17 | +0.17 pp | 1.000 |
| Fixed 384 | DIS | -1.15 pp | 151 / 170 | 0.315 | -2.49 pp | 0.000244 | +0.35 pp | 0.904 |
| Fixed 384 | SAM3 | +3.89 pp | 167 / 103 | 0.000118 | +1.94 pp | 0.000535 | +0.86 pp | 0.609 |
| Fixed 512 | DIS | -4.13 pp | 96 / 164 | 2.95e-5 | -3.40 pp | 8.31e-8 | 0.00 pp | 1.000 |
| Fixed 512 | SAM3 | +2.73 pp | 140 / 95 | 0.00401 | +0.91 pp | 0.0627 | +0.35 pp | 0.892 |

No segmentation was not uniformly worse than DIS.
It had higher R@1 than DIS with fixed 384, fixed 512, and NaFlex p1024.
The fixed-512 advantage over DIS was significant.
The fixed-384 and NaFlex-p1024 R@1 differences were not significant.

SAM3 had higher R@1 than no segmentation with every model.
Each SAM3 R@1 advantage was significant.
The difference decreased as model capacity increased.
For fixed 512, the R@5 and R@10 differences were not significant.

No segmentation did not have a significant negative-rejection difference against DIS or
SAM3 with any model.

## Effect of SAM3 against DIS

The table shows `SAM3 - DIS`.

| Model | R@1 delta | R@1 wins/losses | R@1 p | R@5 delta | R@5 p | Negative rejection delta | Negative p |
|---|---:|---:|---:|---:|---:|---:|---:|
| NaFlex p256 | +9.23 pp | 248 / 96 | 1.23e-16 | +6.44 pp | 4.33e-19 | +1.21 pp | 0.483 |
| NaFlex p512 | +5.28 pp | 182 / 95 | 1.90e-7 | +4.49 pp | 6.75e-13 | +1.04 pp | 0.567 |
| NaFlex p1024 | +5.04 pp | 175 / 92 | 4.25e-7 | +3.83 pp | 1.01e-10 | -1.04 pp | 0.519 |
| Fixed 256 | +8.20 pp | 265 / 130 | 9.88e-12 | +5.65 pp | 3.51e-12 | -1.55 pp | 0.356 |
| Fixed 384 | +5.04 pp | 191 / 108 | 1.83e-6 | +4.43 pp | 1.93e-12 | +0.52 pp | 0.801 |
| Fixed 512 | +6.86 pp | 180 / 67 | 3.99e-13 | +4.31 pp | 6.93e-14 | +0.35 pp | 0.894 |

SAM3 did not give a significant negative-rejection change for any model.
The negative result did not have one direction.

## Effect of model size

### NaFlex

Without segmentation, R@1 increased from 62.78% to 71.46% to 76.81%.
The p256 to p512 gain was 8.68 pp (`p=9.28e-16`).
The p512 to p1024 gain was 5.34 pp (`p=4.01e-8`).

With DIS, R@1 increased from 65.88% to 73.59% to 74.98%.
The p256 to p512 gain was 7.71 pp (`p=9.76e-16`).
The p512 to p1024 gain was 1.40 pp (`p=0.0998`).
The last R@1 gain was not significant.
The last R@5 gain was 1.21 pp (`p=0.00907`).

With SAM3, R@1 increased from 75.11% to 78.87% to 80.02%.
The p256 to p512 gain was 3.76 pp (`p=4.48e-5`).
The p512 to p1024 gain was 1.15 pp (`p=0.161`).
The last R@1 gain was not significant.
The last R@5 gain was 0.55 pp (`p=0.150`).

DIS and SAM3 had clear diminishing returns after p512 on this set.
No segmentation continued to get a significant gain from p512 to p1024.

### Fixed resolution

Without segmentation, R@1 increased from 58.96% to 72.92% to 78.69%.
The 256 to 384 gain was 13.96 pp (`p=1.09e-32`).
The 384 to 512 gain was 5.77 pp (`p=2.28e-11`).

With DIS, R@1 increased from 62.05% to 71.77% to 74.56%.
The 256 to 384 gain was 9.71 pp (`p=1.89e-18`).
The 384 to 512 gain was 2.79 pp (`p=0.00111`).

With SAM3, R@1 increased from 70.25% to 76.81% to 81.42%.
The 256 to 384 gain was 6.56 pp (`p=1.08e-9`).
The 384 to 512 gain was 4.61 pp (`p=1.40e-8`).

Fixed 512 still gave a significant R@1 gain over fixed 384.
The gain was largest without segmentation.

## NaFlex against fixed resolution

The comparison uses the three compute levels in the scope section.

Without segmentation, NaFlex p256 was 3.83 pp better than fixed 256
(`p=0.00104`).
Fixed 384 was 1.46 pp better than NaFlex p512 (`p=0.178`).
Fixed 512 was 1.88 pp better than NaFlex p1024 (`p=0.0396`).

At the low level, NaFlex p256 was better than fixed 256.
Its R@1 advantage was 3.83 pp with DIS (`p=0.00118`).
Its R@1 advantage was 4.86 pp with SAM3 (`p=1.33e-5`).

At the medium level, NaFlex p512 was better than fixed 384 at R@1.
Its advantage was 1.82 pp with DIS (`p=0.0664`).
Its advantage was 2.06 pp with SAM3 (`p=0.0279`).
The R@5 values were equal with DIS and differed by only 0.06 pp with SAM3.

At the high level, NaFlex p1024 and fixed 512 had similar R@1.
Fixed 512 was 0.43 pp lower with DIS (`p=0.675`).
Fixed 512 was 1.40 pp higher with SAM3 (`p=0.102`).
Fixed 512 had a 0.73 pp R@5 gain with SAM3 (`p=0.0290`).

NaFlex was more effective at the low and medium levels.
The two families converged at the high level.

## Segmentation failures

DIS did not find a main object in five positive queries.
SAM3 prepared all 2,226 queries.

The five DIS failures were:

| Query | Wine | Image |
|---|---|---|
| `q-000090` | `abrau-dyurso-imperatorskoe-bryut-shardone-beloe-12` | `04_manual.png` |
| `q-000800` | `domaine-lipko-blaufrankish-krasnoe-suhoe-126` | `04_manual.jpg` |
| `q-001133` | `grand-jete-blanc-de-blancs` | `02_manual.jpg` |
| `q-001157` | `imenie-sikory-kaberne-fran-roze-rozovoe-suhoe-13` | `01_conf095.jpg` |
| `q-001158` | `imenie-sikory-kaberne-fran-sikory-rozovoe-suhoe-13` | `01_conf095.jpg` |

With SAM3 and fixed 512, three of these five queries were R@1 hits.
One was at rank 3.
One was outside R@10.
The three recovered R@1 hits explain only 0.18 pp of the 6.86 pp R@1 gain.
Most of the SAM3 gain came from different crops for queries that both methods processed.

## Decision

Use SAM3 with fixed 512 when the primary goal is maximum retrieval accuracy on GX10.

Use no segmentation with fixed 512 when pipeline simplicity is more important than the
2.73 pp R@1 difference.
This path removes the segmentation service and its failure mode.
It reached 78.69% R@1 and 95.75% R@5.
Its R@5 difference from SAM3 fixed 512 was 0.91 pp and was not significant
(`p=0.0627`).

Do not assume that DIS improves a large SigLIP2 model.
DIS fixed 512 was 4.13 pp below no segmentation at R@1.

Use SAM3 with NaFlex p512 as an accuracy alternative when the p1024 or fixed-512 cost is
not acceptable.
It reached 78.87% R@1 and 95.39% R@5.
This benchmark did not measure isolated latency or energy use.

Do not select a larger model to improve negative rejection.
The negative-rejection rate was from 80.48% to 84.28%.
It did not increase consistently with model size.

## Reproduction

Run from the workbench root.
The command calls the existing GX10 embedding gateway.
It uses the canonical shared SAM3 endpoint for cache identity.

```bash
SAM3_ENDPOINT=http://192.168.86.14:18081/upstream/sam3 \
~/.venvs/svoe-vino-lab/bin/python scripts/segmentation_model_matrix.py \
    --phase all --batch-size 8
```

The phases `prepare`, `embed`, `score`, and `verify` can run separately.
The vector arrays are resumable.

The generated directory is
`runs/segmentation-model-matrix-2026-09-29/`.
It has a size of approximately 4.4 GiB.
It contains 36 vector arrays and 18 query-result files.
The run produced 80,898 vectors.

## Frozen evidence

| File | SHA-256 |
|---|---|
| `manifest.json` | `a39a9ebc6f41e838d782011bce426c8e78534fbc3ab6c5f62144b9c5836a2419` |
| `prepared.jsonl` | `7aac5910828217cb78b0ef3c87398e55004e744a3587e71d894cb394ef6c040d` |
| `embedding.json` | `9de9a6fef4a6cfda0d8523813727337229c7542bc01ea5ba65059218d953c282` |
| `metrics.json` | `901a6c119e4fef6c8688c5104e9868e9b4b2863d852e1edd001b8b07c2216d30` |

The frozen `config.yaml` SHA-256 was
`0d9e25bb1f649b8e56d48fd8faa8e275a737930e66b15c45613c1610b280db1c`.

The verification checked every vector-array row count.
It checked finite vectors.
It checked unit L2 norms with float32 tolerance.
It passed after the final scoring run.

## Execution notes

The first embedding invocation calculated DIS NaFlex p256 and then failed while it wrote
the metadata JSON.
The failure was an integer serialization error.
The vector arrays were complete.
The corrected invocation reused all 4,491 valid p256 vectors.

An early SAM3 preparation attempt used a stale endpoint value in the shell.
The cache client found no matching entries and sent no network request.
The final preparation used `SAM3_ENDPOINT=http://192.168.86.14:18081/upstream/sam3`.
It produced all 2,226 SAM3 query inputs with zero errors.

The no-segmentation extension prepared 2,270 catalogue images and 2,226 query images.
It had no preparation error.
One NaFlex p256 embedding request received HTTP 429.
The client repeated the request after two seconds.
The repeated request succeeded, and no vector was lost.

The benchmark did not restart or reconfigure a GX10 service.
It did not change a production catalogue index.
It did not change the database.
