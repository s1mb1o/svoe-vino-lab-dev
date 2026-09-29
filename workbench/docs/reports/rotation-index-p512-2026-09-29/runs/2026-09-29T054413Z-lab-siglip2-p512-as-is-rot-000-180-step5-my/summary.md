# Run 2026-09-29T054413Z-lab-siglip2-p512-as-is-rot-000-180-step5-my

| Field | Value |
|---|---|
| Backend | `siglip2-p512-as-is-rot-000-180-step5` — siglip2-p512-as-is, catalogue rotated 0:180:5 |
| Started | 2026-09-29T08:44:13+0300 |
| Queries | 2226 (positive 1647, negative 579, variant 0, no match 0) |
| Top-k asked | 10 |
| Scores returned | yes |
| Wall time | 27.4 s |

## Positive photos

| Measure | Value |
|---|---|
| n | 1647 |
| Match share (R@1), target 90-100% | 76.9% |
| F1 top-1 | 0.7693 |
| F1 top-5 | 0.9539 |
| Near-duplicate confusion | 34 |
| R@1 | 76.9% |
| R@5 | 95.4% |
| R@10 | 96.7% |
| MRR | 0.8523 |
| No answer | 0 |
| Errors | 0 |

Rank of the true slug: `{"1": 1267, "2": 216, "3": 51, "4-10": 58, "absent": 55}`

## Negative photos

A negative photo shows a different wine. Only a Top-1 answer with that
slug is a proven error. The other outcomes are not successes.

| Outcome | Count |
|---|---|
| False match at rank 1 | 110 |
| Another slug at rank 1 (unverifiable) | 469 |
| No answer | 0 |
| Errors | 0 |

The slug appeared anywhere in the top-10 for 473 of 579 negative photos.

## Latency

Within the SLA of 3000 ms: 100.0% of the photos.

median 12 ms, p95 15 ms, max 40 ms. Comparable to the jury harness: yes.
