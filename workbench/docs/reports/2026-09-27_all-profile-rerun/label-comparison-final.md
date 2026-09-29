# Completed label-profile comparison

Date: 2026-09-27. Both G1 runs are complete and validated.
This report reads saved run artifacts and frozen attempt identities only.

The label profile returns 29 fewer correct top-1 answers and nine fewer correct top-5 answers.
It fixes 51 top-1 cases and loses 80. This result does not support replacing the reference profile.

## Coverage and quality

Both runs contain 2228 query rows and 1851 unique image digests.
The frozen labels contain 1644 positive rows and 584 negative constraints.
Both runs have zero top-level errors and zero degraded trace steps.
Each row uses the same query ID, path, image digest, label, and truth in both runs.

| Metric | Reference | Label profile | Label minus reference | Paired changes |
|---|---:|---:|---:|---|
| Positive R@1 | 1392/1644 (84.6715%) | 1363/1644 (82.9075%) | -29; -1.7640 percentage points | 51 gained; 80 lost |
| Positive R@5 | 1595/1644 (97.0195%) | 1586/1644 (96.4720%) | -9; -0.5474 percentage points | 10 gained; 19 lost |
| Forbidden negative top-1 | 90/584 | 94/584 | +4 | 18 introduced; 14 removed |
| Forbidden negative in top-10 | 474/584 | 476/584 | +2 | 21 introduced; 19 removed |

Top-1 predictions change on 288 rows, including 114 negative rows.
An allowed negative prediction is not a confirmed correct identification.
The [JSON evidence](label-comparison-final.json) lists every gained, lost, introduced, and removed query ID.
Its changed-row records retain the paired candidates, truth ranks, geometry fields, and rerank outputs.

## Comparable inputs

All frozen identity fields match except the profile name. This includes the query set,
catalogue identity, config hash, model, index metadata and vectors, lookup table,
rerank rule files, production source hashes, endpoints, and four-worker setting.
The saved index has 2051 full-view wines and 2047 label-view wines.
It records 4054 current items, 127 missing items, two failed items, and zero stale items.
The full tower uses identical recorded prepared-image hashes for all 2204 retrieval rows.
No current catalogue state was read after G2 preparation started.

## Cache and tower observations

| Step | Reference cache hits / misses | Label cache hits / misses | Other paths |
|---|---:|---:|---|
| Barcode | 2228 / 0 | 2228 / 0 | 24 unique wine answers in each run |
| Package SAM3 | 2144 / 0 | 2144 / 0 | 60 alpha paths in each run; no SAM3 request |
| Retrieval label SAM3 | No step | 747 / 1457 | 2204 observations |
| Rerank VLM | 585 / 0 | 540 / 50 | Internal label-SAM3 cache state is not recorded |

All 24 barcode answers are unchanged and bypass both retrieval towers.
The reference embeds and searches the full view on the other 2204 rows.
The label profile embeds both views on 2202 rows and only the full view on two rows.
Its full search has 2204 observations. Its label search has 2202 observations.
One embed step batches the available views. It has no embedding-cache flag.
Do not infer embedding cache hits or divide the batched duration between towers.

Retrieval label geometry is available on 2202/2204 rows: 1963 use method `seg`,
and 239 use method `crop`. SAM3 finds no label for `q-000345` and `q-000357`.
Both rows record a skipped label view, use the full view, and remain correct at rank 1.
Geometry availability does not measure segmentation correctness. No images were inspected.

Rerank runs on 585 reference rows and 590 label rows. The mode counts are
518 sheet / 67 verdict and 531 sheet / 59 verdict, respectively.
The added label scores can change candidate order and rerank selection.
Do not attribute all quality loss to segmentation alone.

## Observed bulk costs

| Cost | Reference | Label profile |
|---|---:|---:|
| Run wall, s | 133.8 | 895.2 |
| Intent-to-final interval, s | 135.166 | 896.483 |
| Per-row median / p95, ms | 186 / 552 | 1800 / 3030 |

| Trace step | Reference summed s | Label summed s |
|---|---:|---:|
| `barcode` | 4.093 | 5.461 |
| `input` | 19.348 | 18.416 |
| `sam3-package` | 193.890 | 170.752 |
| `view:full` | 61.496 | 54.438 |
| `embed` | 124.160 | 364.603 |
| `search:full` | 3.346 | 3.354 |
| `score` | 2.641 | 2.301 |
| `cluster_rules` | 125.388 | 235.391 |
| `sam3-label` | — | 2689.017 |
| `view:label` | — | 31.713 |
| `search:label` | — | 2.859 |

The 1457 retrieval label cache misses account for 2630.396 summed step seconds.
The 747 label cache hits account for 58.621 seconds. Rerank VLM miss paths account
for 134.591 seconds; the label profile has 50 such paths and the reference has zero.
These step durations include preparation and waiting. They are not isolated model inference timers.

The 895.2 s and 133.8 s run walls do not compare equal cache conditions.
Both runs use four workers. Summed step times overlap across workers.
All costs above use `trace.steps[].ms`. Cached `candidate.explain.ms` is excluded.
Both saved per-row latency records set `comparable=false`.
These runs do not measure sequential HTTP recognition or establish a three-second demo response.

## Frozen sources

- Reference: [2026-09-27T011711Z-lab-barcode-rerank-siglip2-512-crop-my](../../../runs/2026-09-27T011711Z-lab-barcode-rerank-siglip2-512-crop-my/run.json).
- Label: [2026-09-27T011951Z-lab-barcode-rerank-siglip2-512-crop-label-my](../../../runs/2026-09-27T011951Z-lab-barcode-rerank-siglip2-512-crop-label-my/run.json).
- Reference attempt: [saved record](attempts/barcode-rerank-siglip2-512-crop-a255248824054b1d8f0da492a5737fc4/attempt.json).
- Label attempt: [saved record](attempts/barcode-rerank-siglip2-512-crop-label-296c73e93ac74b0ab3aee1bdc46ee5da/attempt.json).
- [JSON evidence](label-comparison-final.json) contains verified file hashes and complete paired query-ID lists.
