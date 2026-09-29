# Run 2026-09-27T011711Z-lab-barcode-rerank-siglip2-512-crop-my

| Field | Value |
|---|---|
| Backend | `barcode-rerank-siglip2-512-crop` — lab pipeline barcode-rerank-siglip2-512-crop: the embedding gx10-siglip2-so400m-patch16-512, then the cluster re-rank, after the code lookup |
| Started | 2026-09-27T04:17:11+0300 |
| Queries | 2228 (positive 1644, negative 584, variant 0, no match 0) |
| Top-k asked | 10 |
| Scores returned | yes |
| Wall time | 133.8 s |

## Positive photos

| Measure | Value |
|---|---|
| n | 1644 |
| Match share (R@1), target 90-100% | 84.7% |
| F1 top-1 | 0.8467 |
| F1 top-5 | 0.9702 |
| Near-duplicate confusion | 32 |
| R@1 | 84.7% |
| R@5 | 97.0% |
| R@10 | 97.8% |
| MRR | 0.9030 |
| No answer | 0 |
| Errors | 0 |

Rank of the true slug: `{"1": 1392, "2": 148, "3": 39, "4-10": 29, "absent": 36}`

## Negative photos

A negative photo shows a different wine. Only a Top-1 answer with that
slug is a proven error. The other outcomes are not successes.

| Outcome | Count |
|---|---|
| False match at rank 1 | 90 |
| Another slug at rank 1 (unverifiable) | 494 |
| No answer | 0 |
| Errors | 0 |

The slug appeared anywhere in the top-10 for 474 of 584 negative photos.

## Latency

Within the SLA of 3000 ms: 100.0% of the photos.

median 186 ms, p95 552 ms, max 2493 ms. Comparable to the jury harness: no, the run used several workers.
