# Run 2026-09-29T041353Z-lab-siglip2-p512-crop-my-baseline

| Field | Value |
|---|---|
| Backend | `siglip2-p512-crop` — lab pipeline siglip2-p512-crop: the embedding gx10-siglip2-so400m-patch16-naflex-p512 |
| Started | 2026-09-29T07:13:53+0300 |
| Queries | 2226 (positive 1647, negative 579, variant 0, no match 0) |
| Top-k asked | 10 |
| Scores returned | yes |
| Wall time | 531.2 s |

## Positive photos

| Measure | Value |
|---|---|
| n | 1647 |
| Match share (R@1), target 90-100% | 79.5% |
| F1 top-1 | 0.7948 |
| F1 top-5 | 0.9611 |
| Near-duplicate confusion | 29 |
| R@1 | 79.5% |
| R@5 | 96.1% |
| R@10 | 97.3% |
| MRR | 0.8694 |
| No answer | 0 |
| Errors | 0 |

Rank of the true slug: `{"1": 1309, "2": 193, "3": 46, "4-10": 54, "absent": 45}`

## Negative photos

A negative photo shows a different wine. Only a Top-1 answer with that
slug is a proven error. The other outcomes are not successes.

| Outcome | Count |
|---|---|
| False match at rank 1 | 111 |
| Another slug at rank 1 (unverifiable) | 468 |
| No answer | 0 |
| Errors | 0 |

The slug appeared anywhere in the top-10 for 485 of 579 negative photos.

## Latency

Within the SLA of 3000 ms: 99.9% of the photos.

median 950 ms, p95 1638 ms, max 3989 ms. Comparable to the jury harness: no, the run used several workers.
