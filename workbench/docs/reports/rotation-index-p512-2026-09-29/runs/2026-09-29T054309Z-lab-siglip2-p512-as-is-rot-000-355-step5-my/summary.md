# Run 2026-09-29T054309Z-lab-siglip2-p512-as-is-rot-000-355-step5-my

| Field | Value |
|---|---|
| Backend | `siglip2-p512-as-is-rot-000-355-step5` — siglip2-p512-as-is, catalogue rotated 0:355:5 |
| Started | 2026-09-29T08:43:10+0300 |
| Queries | 2226 (positive 1647, negative 579, variant 0, no match 0) |
| Top-k asked | 10 |
| Scores returned | yes |
| Wall time | 49.8 s |

## Positive photos

| Measure | Value |
|---|---|
| n | 1647 |
| Match share (R@1), target 90-100% | 77.2% |
| F1 top-1 | 0.7723 |
| F1 top-5 | 0.9545 |
| Near-duplicate confusion | 34 |
| R@1 | 77.2% |
| R@5 | 95.5% |
| R@10 | 96.7% |
| MRR | 0.8538 |
| No answer | 0 |
| Errors | 0 |

Rank of the true slug: `{"1": 1272, "2": 214, "3": 45, "4-10": 61, "absent": 55}`

## Negative photos

A negative photo shows a different wine. Only a Top-1 answer with that
slug is a proven error. The other outcomes are not successes.

| Outcome | Count |
|---|---|
| False match at rank 1 | 116 |
| Another slug at rank 1 (unverifiable) | 463 |
| No answer | 0 |
| Errors | 0 |

The slug appeared anywhere in the top-10 for 476 of 579 negative photos.

## Latency

Within the SLA of 3000 ms: 100.0% of the photos.

median 22 ms, p95 26 ms, max 59 ms. Comparable to the jury harness: yes.
