# Compact retrieval benchmark results

[Full algorithm reference](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md) · [Raw reported counts](metrics.csv) · [Exact configurations](configurations.json)

Hardware: GX10. No re-ranking.
Each testset has 353,188 unique configurations. The p512/p512 subset has 345,796.
These are development-set results. The two testsets share 619 images.
Top-10 ties use Top-5, then Top-1, then MRR@10 and the variant ID.

| Testset | Baseline R@1 | Baseline R@5 | Baseline R@10 |
| --- | --- | --- | --- |
| my-failed-2 | 44.01% (294/668) | 96.56% (645/668) | 99.70% (666/668) |
| my | 86.94% (2582/2970) | 99.19% (2946/2970) | 99.93% (2968/2970) |

## my-failed-2: all_budgets Top-1

| Rank | Recipe | R@1 / delta | R@5 / delta | R@10 / delta |
| --- | --- | --- | --- | --- |
| 1 | [R001](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r001) | 67.37% / +23.35 pp | 98.35% / +1.80 pp | 99.85% / +0.15 pp |
| 2 | [R002](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r002) | 67.37% / +23.35 pp | 98.35% / +1.80 pp | 99.85% / +0.15 pp |
| 3 | [R003](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r003) | 67.22% / +23.20 pp | 98.50% / +1.95 pp | 100.00% / +0.30 pp |
| 4 | [R004](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r004) | 67.07% / +23.05 pp | 98.50% / +1.95 pp | 100.00% / +0.30 pp |
| 5 | [R005](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r005) | 67.07% / +23.05 pp | 98.35% / +1.80 pp | 99.85% / +0.15 pp |

## my-failed-2: all_budgets Top-5

| Rank | Recipe | R@1 / delta | R@5 / delta | R@10 / delta |
| --- | --- | --- | --- | --- |
| 1 | [R006](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r006) | 60.48% / +16.47 pp | 100.00% / +3.44 pp | 100.00% / +0.30 pp |
| 2 | [R007](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r007) | 63.02% / +19.01 pp | 99.85% / +3.29 pp | 100.00% / +0.30 pp |
| 3 | [R008](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r008) | 60.78% / +16.77 pp | 99.85% / +3.29 pp | 100.00% / +0.30 pp |
| 4 | [R009](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r009) | 60.63% / +16.62 pp | 99.85% / +3.29 pp | 100.00% / +0.30 pp |
| 5 | [R010](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r010) | 60.18% / +16.17 pp | 99.85% / +3.29 pp | 100.00% / +0.30 pp |

## my-failed-2: all_budgets Top-10

| Rank | Recipe | R@1 / delta | R@5 / delta | R@10 / delta |
| --- | --- | --- | --- | --- |
| 1 | [R006](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r006) | 60.48% / +16.47 pp | 100.00% / +3.44 pp | 100.00% / +0.30 pp |
| 2 | [R007](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r007) | 63.02% / +19.01 pp | 99.85% / +3.29 pp | 100.00% / +0.30 pp |
| 3 | [R008](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r008) | 60.78% / +16.77 pp | 99.85% / +3.29 pp | 100.00% / +0.30 pp |
| 4 | [R009](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r009) | 60.63% / +16.62 pp | 99.85% / +3.29 pp | 100.00% / +0.30 pp |
| 5 | [R010](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r010) | 60.18% / +16.17 pp | 99.85% / +3.29 pp | 100.00% / +0.30 pp |

## my-failed-2: p512 Top-1

| Rank | Recipe | R@1 / delta | R@5 / delta | R@10 / delta |
| --- | --- | --- | --- | --- |
| 1 | [R018](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r018) | 66.17% / +22.16 pp | 98.80% / +2.25 pp | 99.55% / -0.15 pp |
| 2 | [R019](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r019) | 66.17% / +22.16 pp | 98.80% / +2.25 pp | 99.55% / -0.15 pp |
| 3 | [R020](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r020) | 66.02% / +22.01 pp | 98.95% / +2.40 pp | 100.00% / +0.30 pp |
| 4 | [R021](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r021) | 66.02% / +22.01 pp | 98.95% / +2.40 pp | 99.55% / -0.15 pp |
| 5 | [R022](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r022) | 65.87% / +21.86 pp | 99.25% / +2.69 pp | 100.00% / +0.30 pp |

## my-failed-2: p512 Top-5

| Rank | Recipe | R@1 / delta | R@5 / delta | R@10 / delta |
| --- | --- | --- | --- | --- |
| 1 | [R006](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r006) | 60.48% / +16.47 pp | 100.00% / +3.44 pp | 100.00% / +0.30 pp |
| 2 | [R007](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r007) | 63.02% / +19.01 pp | 99.85% / +3.29 pp | 100.00% / +0.30 pp |
| 3 | [R008](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r008) | 60.78% / +16.77 pp | 99.85% / +3.29 pp | 100.00% / +0.30 pp |
| 4 | [R009](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r009) | 60.63% / +16.62 pp | 99.85% / +3.29 pp | 100.00% / +0.30 pp |
| 5 | [R010](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r010) | 60.18% / +16.17 pp | 99.85% / +3.29 pp | 100.00% / +0.30 pp |

## my-failed-2: p512 Top-10

| Rank | Recipe | R@1 / delta | R@5 / delta | R@10 / delta |
| --- | --- | --- | --- | --- |
| 1 | [R006](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r006) | 60.48% / +16.47 pp | 100.00% / +3.44 pp | 100.00% / +0.30 pp |
| 2 | [R007](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r007) | 63.02% / +19.01 pp | 99.85% / +3.29 pp | 100.00% / +0.30 pp |
| 3 | [R008](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r008) | 60.78% / +16.77 pp | 99.85% / +3.29 pp | 100.00% / +0.30 pp |
| 4 | [R009](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r009) | 60.63% / +16.62 pp | 99.85% / +3.29 pp | 100.00% / +0.30 pp |
| 5 | [R010](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r010) | 60.18% / +16.17 pp | 99.85% / +3.29 pp | 100.00% / +0.30 pp |

## my: all_budgets Top-1

| Rank | Recipe | R@1 / delta | R@5 / delta | R@10 / delta |
| --- | --- | --- | --- | --- |
| 1 | [R011](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r011) | 90.77% / +3.84 pp | 99.83% / +0.64 pp | 100.00% / +0.07 pp |
| 2 | [R012](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r012) | 90.77% / +3.84 pp | 99.80% / +0.61 pp | 100.00% / +0.07 pp |
| 3 | [R013](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r013) | 90.74% / +3.80 pp | 99.80% / +0.61 pp | 100.00% / +0.07 pp |
| 4 | [R014](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r014) | 90.74% / +3.80 pp | 99.73% / +0.54 pp | 99.90% / -0.03 pp |
| 5 | [R015](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r015) | 90.74% / +3.80 pp | 99.73% / +0.54 pp | 99.90% / -0.03 pp |

## my: all_budgets Top-5

| Rank | Recipe | R@1 / delta | R@5 / delta | R@10 / delta |
| --- | --- | --- | --- | --- |
| 1 | [R006](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r006) | 89.36% / +2.42 pp | 99.93% / +0.74 pp | 100.00% / +0.07 pp |
| 2 | [R016](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r016) | 89.33% / +2.39 pp | 99.93% / +0.74 pp | 100.00% / +0.07 pp |
| 3 | [R017](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r017) | 89.26% / +2.32 pp | 99.93% / +0.74 pp | 100.00% / +0.07 pp |
| 4 | [R009](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r009) | 89.53% / +2.59 pp | 99.90% / +0.71 pp | 100.00% / +0.07 pp |
| 5 | [R008](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r008) | 89.46% / +2.53 pp | 99.90% / +0.71 pp | 100.00% / +0.07 pp |

## my: all_budgets Top-10

| Rank | Recipe | R@1 / delta | R@5 / delta | R@10 / delta |
| --- | --- | --- | --- | --- |
| 1 | [R006](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r006) | 89.36% / +2.42 pp | 99.93% / +0.74 pp | 100.00% / +0.07 pp |
| 2 | [R016](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r016) | 89.33% / +2.39 pp | 99.93% / +0.74 pp | 100.00% / +0.07 pp |
| 3 | [R017](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r017) | 89.26% / +2.32 pp | 99.93% / +0.74 pp | 100.00% / +0.07 pp |
| 4 | [R009](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r009) | 89.53% / +2.59 pp | 99.90% / +0.71 pp | 100.00% / +0.07 pp |
| 5 | [R008](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r008) | 89.46% / +2.53 pp | 99.90% / +0.71 pp | 100.00% / +0.07 pp |

## my: p512 Top-1

| Rank | Recipe | R@1 / delta | R@5 / delta | R@10 / delta |
| --- | --- | --- | --- | --- |
| 1 | [R011](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r011) | 90.77% / +3.84 pp | 99.83% / +0.64 pp | 100.00% / +0.07 pp |
| 2 | [R012](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r012) | 90.77% / +3.84 pp | 99.80% / +0.61 pp | 100.00% / +0.07 pp |
| 3 | [R013](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r013) | 90.74% / +3.80 pp | 99.80% / +0.61 pp | 100.00% / +0.07 pp |
| 4 | [R014](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r014) | 90.74% / +3.80 pp | 99.73% / +0.54 pp | 99.90% / -0.03 pp |
| 5 | [R015](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r015) | 90.74% / +3.80 pp | 99.73% / +0.54 pp | 99.90% / -0.03 pp |

## my: p512 Top-5

| Rank | Recipe | R@1 / delta | R@5 / delta | R@10 / delta |
| --- | --- | --- | --- | --- |
| 1 | [R006](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r006) | 89.36% / +2.42 pp | 99.93% / +0.74 pp | 100.00% / +0.07 pp |
| 2 | [R016](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r016) | 89.33% / +2.39 pp | 99.93% / +0.74 pp | 100.00% / +0.07 pp |
| 3 | [R017](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r017) | 89.26% / +2.32 pp | 99.93% / +0.74 pp | 100.00% / +0.07 pp |
| 4 | [R009](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r009) | 89.53% / +2.59 pp | 99.90% / +0.71 pp | 100.00% / +0.07 pp |
| 5 | [R008](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r008) | 89.46% / +2.53 pp | 99.90% / +0.71 pp | 100.00% / +0.07 pp |

## my: p512 Top-10

| Rank | Recipe | R@1 / delta | R@5 / delta | R@10 / delta |
| --- | --- | --- | --- | --- |
| 1 | [R006](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r006) | 89.36% / +2.42 pp | 99.93% / +0.74 pp | 100.00% / +0.07 pp |
| 2 | [R016](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r016) | 89.33% / +2.39 pp | 99.93% / +0.74 pp | 100.00% / +0.07 pp |
| 3 | [R017](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r017) | 89.26% / +2.32 pp | 99.93% / +0.74 pp | 100.00% / +0.07 pp |
| 4 | [R009](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r009) | 89.53% / +2.59 pp | 99.90% / +0.71 pp | 100.00% / +0.07 pp |
| 5 | [R008](../../../RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r008) | 89.46% / +2.53 pp | 99.90% / +0.71 pp | 100.00% / +0.07 pp |

## Evidence boundaries

The CSV includes every exact result recipe on both testsets, controlled pooling and query comparisons, baselines, and historical named results.
The JSON table export preserves every numeric table in Sections 1–16 of the full report.
The compact data does not contain every measured variant or per-image prediction.
The [dataset inventory](dataset-inventory.json) records the source database identities.
The incomplete RTX4090 replay remains a separate report snapshot. Its scores do not enter these GX10 leaderboards.
