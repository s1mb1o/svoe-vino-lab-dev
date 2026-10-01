# Run 2026-09-27T020325Z-lab-siglip2-p512-as-is-my

| Field | Value |
|---|---|
| Backend | `siglip2-p512-as-is` — lab pipeline siglip2-p512-as-is: the embedding gx10-siglip2-so400m-patch16-naflex-p512 |
| Started | 2026-09-27T05:03:25+0300 |
| Queries | 2217 (positive 1639, negative 578, variant 0, no match 0) |
| Top-k asked | 10 |
| Scores returned | yes |
| Wall time | 86.5 s |

## Positive photos

| Measure | Value |
|---|---|
| n | 1639 |
| Match share (R@1), target 90-100% | 74.3% |
| F1 top-1 | 0.7431 |
| F1 top-5 | 0.9317 |
| Near-duplicate confusion | 36 |
| R@1 | 74.3% |
| R@5 | 93.2% |
| R@10 | 95.3% |
| MRR | 0.8271 |
| No answer | 0 |
| Errors | 0 |

Rank of the true slug: `{"1": 1218, "2": 207, "3": 56, "4-10": 81, "absent": 77}`

## Negative photos

A negative photo shows a different wine. Only a Top-1 answer with that
slug is a proven error. The other outcomes are not successes.

| Outcome | Count |
|---|---|
| False match at rank 1 | 111 |
| Another slug at rank 1 (unverifiable) | 467 |
| No answer | 0 |
| Errors | 0 |

The slug appeared anywhere in the top-10 for 464 of 578 negative photos.

## Latency

Within the SLA of 3000 ms: 100.0% of the photos.

median 150 ms, p95 235 ms, max 796 ms. Comparable to the jury harness: no, the run used several workers.

## Dataset rule

This summary was scored again on 2026-09-29T19:46:23+0300 with the rule of `docs/plans/87_benchmark-dataset-rule.md`. The photos of
a wine outside the dataset left the metrics: disabled wine 1, removed wine 10.
The run asked 2228 photos. `summary.before-dataset-rule.md` holds the old numbers.
