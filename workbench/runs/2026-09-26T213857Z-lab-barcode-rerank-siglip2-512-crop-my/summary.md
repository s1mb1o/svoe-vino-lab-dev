# Run 2026-09-26T213857Z-lab-barcode-rerank-siglip2-512-crop-my

| Field | Value |
|---|---|
| Backend | `barcode-rerank-siglip2-512-crop` — lab pipeline barcode-rerank-siglip2-512-crop: the embedding gx10-siglip2-so400m-patch16-512, then the cluster re-rank, after the code lookup |
| Started | 2026-09-27T00:38:57+0300 |
| Queries | 2217 (positive 1639, negative 578, variant 0, no match 0) |
| Top-k asked | 10 |
| Scores returned | yes |
| Wall time | 2507.1 s |

## Positive photos

| Measure | Value |
|---|---|
| n | 1639 |
| Match share (R@1), target 90-100% | 84.8% |
| F1 top-1 | 0.8475 |
| F1 top-5 | 0.9707 |
| Near-duplicate confusion | 32 |
| R@1 | 84.8% |
| R@5 | 97.1% |
| R@10 | 97.8% |
| MRR | 0.9038 |
| No answer | 0 |
| Errors | 0 |

Rank of the true slug: `{"1": 1389, "2": 148, "3": 39, "4-10": 27, "absent": 36}`

## Negative photos

A negative photo shows a different wine. Only a Top-1 answer with that
slug is a proven error. The other outcomes are not successes.

| Outcome | Count |
|---|---|
| False match at rank 1 | 90 |
| Another slug at rank 1 (unverifiable) | 488 |
| No answer | 0 |
| Errors | 0 |

The slug appeared anywhere in the top-10 for 469 of 578 negative photos.

## Latency

Within the SLA of 3000 ms: 97.7% of the photos.

median 871 ms, p95 2372 ms, max 102367 ms. Comparable to the jury harness: yes.

## Dataset rule

This summary was scored again on 2026-09-29T19:46:20+0300 with the rule of `docs/plans/87_benchmark-dataset-rule.md`. The photos of
a wine outside the dataset left the metrics: disabled wine 1, removed wine 10.
The run asked 2228 photos. `summary.before-dataset-rule.md` holds the old numbers.
