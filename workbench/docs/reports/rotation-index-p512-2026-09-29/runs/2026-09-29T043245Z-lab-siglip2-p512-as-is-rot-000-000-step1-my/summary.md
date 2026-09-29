# Run 2026-09-29T043245Z-lab-siglip2-p512-as-is-rot-000-000-step1-my

| Field | Value |
|---|---|
| Backend | `siglip2-p512-as-is-rot-000-000-step1` — siglip2-p512-as-is, catalogue rotated 0:0:1 |
| Started | 2026-09-29T07:32:45+0300 |
| Queries | 2226 (positive 1647, negative 579, variant 0, no match 0) |
| Top-k asked | 10 |
| Scores returned | yes |
| Wall time | 3.7 s |

## Positive photos

| Measure | Value |
|---|---|
| n | 1647 |
| Match share (R@1), target 90-100% | 74.3% |
| F1 top-1 | 0.7426 |
| F1 top-5 | 0.9411 |
| Near-duplicate confusion | 39 |
| R@1 | 74.3% |
| R@5 | 94.1% |
| R@10 | 96.3% |
| MRR | 0.8309 |
| No answer | 0 |
| Errors | 0 |

Rank of the true slug: `{"1": 1223, "2": 219, "3": 58, "4-10": 86, "absent": 61}`

## Negative photos

A negative photo shows a different wine. Only a Top-1 answer with that
slug is a proven error. The other outcomes are not successes.

| Outcome | Count |
|---|---|
| False match at rank 1 | 115 |
| Another slug at rank 1 (unverifiable) | 464 |
| No answer | 0 |
| Errors | 0 |

The slug appeared anywhere in the top-10 for 468 of 579 negative photos.

## Latency

Within the SLA of 3000 ms: 100.0% of the photos.

median 1 ms, p95 2 ms, max 39 ms. Comparable to the jury harness: yes.
