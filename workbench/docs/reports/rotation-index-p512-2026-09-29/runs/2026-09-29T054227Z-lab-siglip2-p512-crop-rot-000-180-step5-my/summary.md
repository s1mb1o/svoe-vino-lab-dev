# Run 2026-09-29T054227Z-lab-siglip2-p512-crop-rot-000-180-step5-my

| Field | Value |
|---|---|
| Backend | `siglip2-p512-crop-rot-000-180-step5` — siglip2-p512-crop, catalogue rotated 0:180:5 |
| Started | 2026-09-29T08:42:27+0300 |
| Queries | 2226 (positive 1647, negative 579, variant 0, no match 0) |
| Top-k asked | 10 |
| Scores returned | yes |
| Wall time | 27.4 s |

## Positive photos

| Measure | Value |
|---|---|
| n | 1647 |
| Match share (R@1), target 90-100% | 79.6% |
| F1 top-1 | 0.7960 |
| F1 top-5 | 0.9611 |
| Near-duplicate confusion | 29 |
| R@1 | 79.6% |
| R@5 | 96.1% |
| R@10 | 97.2% |
| MRR | 0.8702 |
| No answer | 0 |
| Errors | 0 |

Rank of the true slug: `{"1": 1311, "2": 193, "3": 46, "4-10": 51, "absent": 46}`

## Negative photos

A negative photo shows a different wine. Only a Top-1 answer with that
slug is a proven error. The other outcomes are not successes.

| Outcome | Count |
|---|---|
| False match at rank 1 | 105 |
| Another slug at rank 1 (unverifiable) | 474 |
| No answer | 0 |
| Errors | 0 |

The slug appeared anywhere in the top-10 for 484 of 579 negative photos.

## Latency

Within the SLA of 3000 ms: 100.0% of the photos.

median 12 ms, p95 14 ms, max 43 ms. Comparable to the jury harness: yes.
