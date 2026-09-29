# Android DIS and SAM3 comparison

Date: 2026-09-29

## Result

SAM3 gives better positive-photo retrieval with the same SigLIP2 Base 224 model.
SAM3 improves R@1 by 6.86 percentage points.
SAM3 improves R@5 by 6.26 percentage points.
The paired R@1 difference is statistically significant.

DIS rejects more negative photos at rank 1.
The difference is 2.07 percentage points.
This negative-photo difference is not statistically significant.

The present Android DIS pipeline is operational.
It is not quality-equivalent to the SAM3 reference pipeline on `my`.

## Scope

The test used the permanent pipelines in `config.yaml`:

- `android-siglip2-base-224-dis-white`
- `android-siglip2-base-224-sam3-white`

Both pipelines used one worker.
Both pipelines used `vit_base_patch16_siglip_224.v2_webli`.
Both pipelines used one `full` view.
Neither pipeline has a `barcode` key.
The commands also used `--no-barcode`.
No barcode decode or barcode lookup ran.

The test set was `my`.
It had 2,226 queries.
It had 1,647 positive queries and 579 negative queries.
The two final runs used the same query file.
Its SHA-256 is
`8ae79b0f77321c6d2501cc07a4189212c2a2b7276d4cec3a66754ff430ab6f69`.

Each final index had 2,270 current items and zero failed items.
Each final index covered 2,093 wines.
Each vector had 768 float32 values.

## Runs

| Pipeline | Run ID | Wall time | Errors |
|---|---|---:|---:|
| DIS | `2026-09-28T211710Z-lab-android-siglip2-base-224-dis-white-my` | 3,690.8 s | 5 |
| SAM3 | `2026-09-28T222600Z-lab-android-siglip2-base-224-sam3-white-my` | 297.4 s | 0 |

The SAM3 wall time uses the existing SAM3 cache.
Do not use this wall-time ratio as an uncached segmentation benchmark.
The DIS run performed real LiteRT segmentation for each query on the Mac.

## Retrieval metrics

| Metric | DIS | SAM3 | SAM3 minus DIS |
|---|---:|---:|---:|
| Positive R@1 | 43.05% (709/1,647) | 49.91% (822/1,647) | +6.86 pp |
| Positive R@5 | 73.10% (1,204/1,647) | 79.36% (1,307/1,647) | +6.26 pp |
| Positive R@10 | 80.15% (1,320/1,647) | 85.55% (1,409/1,647) | +5.40 pp |
| Positive MRR | 0.5575 | 0.6238 | +0.0663 |
| Negative rejection at rank 1 | 84.97% (492/579) | 82.90% (480/579) | -2.07 pp |
| Negative false match at rank 1 | 87/579 | 99/579 | +12 false matches |
| Median query latency | 1,599 ms | 109 ms | Cache conditions differ |
| P95 query latency | 2,162 ms | 377 ms | Cache conditions differ |

The two pipelines returned the same top-1 slug for 1,128 queries.
They returned different top-1 values for 1,098 queries.

## Paired tests

The comparison paired every query by `image_path`.
It verified the same `image_sha256` for each pair.
No pair was removed.
An error or no answer counted as an incorrect answer.

| Test | SAM3 wins | SAM3 losses | Exact McNemar p |
|---|---:|---:|---:|
| Positive R@1 | 249 | 136 | `9.013745e-09` |
| Positive R@5 | 178 | 75 | `7.880679e-11` |
| Positive R@10 | 140 | 51 | `8.768926e-11` |
| Negative rejection at rank 1 | 34 | 46 | `0.218518` |

## DIS segmentation failures

DIS returned `DIS found no main object` for five positive queries.
Two queries share the same image bytes.
The five errors represent four unique images.

| Query image | SHA-256 |
|---|---|
| `abrau-dyurso-imperatorskoe-bryut-shardone-beloe-12/04_manual.png` | `126dc4ec4b4ea825c4c830b803eed005e8187af582eba18c3080af30865de658` |
| `domaine-lipko-blaufrankish-krasnoe-suhoe-126/04_manual.jpg` | `29be9b94b0cdd68acb8b1116057fcf8782e1095b69a4be2f36a3cc82018f2ee0` |
| `grand-jete-blanc-de-blancs/02_manual.jpg` | `beaf11320e8bf3396581b7185bd8865c2d60b5d1229269956bb5ed24a1bde3fa` |
| `imenie-sikory-kaberne-fran-roze-rozovoe-suhoe-13/01_conf095.jpg` | `08953d3d023fae304b5478fb995feadfea72d9ac7c0e83cba8a1ecc64e4fa181` |
| `imenie-sikory-kaberne-fran-sikory-rozovoe-suhoe-13/01_conf095.jpg` | `08953d3d023fae304b5478fb995feadfea72d9ac7c0e83cba8a1ecc64e4fa181` |

## Reproducibility note

The first SAM3 run was
`2026-09-28T221902Z-lab-android-siglip2-base-224-sam3-white-my`.
A concurrent CLI smoke test temporarily added one active catalogue wine during its
index update.
That run had 2,271 items and 2,094 wines.
It is not part of the final comparison.

The final SAM3 run started after the temporary wine became `Disabled`.
Its rebuild removed the temporary item.
The final DIS and SAM3 catalogue counts are equal.

## Artifact hashes

| Artifact | SHA-256 |
|---|---|
| DIS `run.json` | `f9060cbf01af3b282158d97f792a1e26096006b96dc8252fb6ded5bc9be139d0` |
| DIS `metrics.json` | `45ca7bb7d62be30d5bdbd915e77f3c3266aad05036b95924bb9862234a87cade` |
| DIS `results.jsonl` | `84f70e3424bce01dff3f69d55cd1ab961c359e3a19c0513c5756fff41486641d` |
| SAM3 `run.json` | `482ed9d18441147eb53a5a32830c8e84f122edf8ac6e06b548e55a1bd71e409e` |
| SAM3 `metrics.json` | `9ced65dcc3dad08fd7782749aea1e65481562416fe99fc4e9785d19216d0898d` |
| SAM3 `results.jsonl` | `a2a91fa575c5c6a815320f898a5695c68ae006f6a190a9f7ca8c822744c9e507` |

## Repeat the test

Open `/testset?set=my`.
Open `Run>`.
Select each pipeline by its exact name.
Keep one worker.
The barcode checkbox stays disabled because the pipelines have no barcode step.

Use these CLI commands for the same path:

```text
~/.venvs/svoe-vino-lab/bin/python pipeline/run_job.py \
  --name android-siglip2-base-224-dis-white --set my --workers 1 --no-barcode

~/.venvs/svoe-vino-lab/bin/python pipeline/run_job.py \
  --name android-siglip2-base-224-sam3-white --set my --workers 1 --no-barcode
```

Run `scripts/compare_runs.py` with the DIS run first and the SAM3 run second.
