# Run 2026-09-27T023118Z-lab-barcode-siglip2-p1024-crop-my

| Field | Value |
|---|---|
| Backend | `barcode-siglip2-p1024-crop` — lab pipeline barcode-siglip2-p1024-crop: the embedding gx10-siglip2-so400m-patch16-naflex-p1024, after the code lookup |
| Started | 2026-09-27T05:31:18+0300 |
| Queries | 2217 (positive 1639, negative 578, variant 0, no match 0) |
| Top-k asked | 10 |
| Scores returned | yes |
| Wall time | 110.3 s |

## Positive photos

| Measure | Value |
|---|---|
| n | 1639 |
| Match share (R@1), target 90-100% | 83.3% |
| F1 top-1 | 0.8328 |
| F1 top-5 | 0.9799 |
| Near-duplicate confusion | 30 |
| R@1 | 83.3% |
| R@5 | 98.0% |
| R@10 | 99.6% |
| MRR | 0.8998 |
| No answer | 0 |
| Errors | 0 |

Rank of the true slug: `{"1": 1365, "2": 172, "3": 39, "4-10": 57, "absent": 6}`

## Negative photos

A negative photo shows a different wine. Only a Top-1 answer with that
slug is a proven error. The other outcomes are not successes.

| Outcome | Count |
|---|---|
| False match at rank 1 | 97 |
| Another slug at rank 1 (unverifiable) | 481 |
| No answer | 0 |
| Errors | 0 |

The slug appeared anywhere in the top-10 for 497 of 578 negative photos.

## Latency

Within the SLA of 3000 ms: 100.0% of the photos.

median 171 ms, p95 398 ms, max 1329 ms. Comparable to the jury harness: no, the run used several workers.

## Dataset rule

This summary was scored again on 2026-09-29T19:46:24+0300 with the rule of `docs/plans/87_benchmark-dataset-rule.md`. The photos of
a wine outside the dataset left the metrics: disabled wine 1, removed wine 10.
The run asked 2228 photos. `summary.before-dataset-rule.md` holds the old numbers.
