# Run 2026-09-29T054122Z-lab-siglip2-p512-crop-rot-000-355-step5-my

| Field | Value |
|---|---|
| Backend | `siglip2-p512-crop-rot-000-355-step5` — siglip2-p512-crop, catalogue rotated 0:355:5 |
| Started | 2026-09-29T08:41:22+0300 |
| Queries | 2226 (positive 1647, negative 579, variant 0, no match 0) |
| Top-k asked | 10 |
| Scores returned | yes |
| Wall time | 50.5 s |

## Positive photos

| Measure | Value |
|---|---|
| n | 1647 |
| Match share (R@1), target 90-100% | 79.7% |
| F1 top-1 | 0.7966 |
| F1 top-5 | 0.9617 |
| Near-duplicate confusion | 29 |
| R@1 | 79.7% |
| R@5 | 96.2% |
| R@10 | 97.3% |
| MRR | 0.8704 |
| No answer | 0 |
| Errors | 0 |

Rank of the true slug: `{"1": 1312, "2": 191, "3": 45, "4-10": 54, "absent": 45}`

## Negative photos

A negative photo shows a different wine. Only a Top-1 answer with that
slug is a proven error. The other outcomes are not successes.

| Outcome | Count |
|---|---|
| False match at rank 1 | 102 |
| Another slug at rank 1 (unverifiable) | 477 |
| No answer | 0 |
| Errors | 0 |

The slug appeared anywhere in the top-10 for 483 of 579 negative photos.

## Latency

Within the SLA of 3000 ms: 100.0% of the photos.

median 22 ms, p95 26 ms, max 89 ms. Comparable to the jury harness: yes.
