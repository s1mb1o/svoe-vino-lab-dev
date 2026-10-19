# scene-v1 photo failures

[All cases](README.md) · [Tracking issue](https://github.com/s1mb1o/svoe-vino-lab-dev/issues/34)

Failures are listed by case and detection mode. Expected-label loss uses the saved <98% threshold; target misses use the saved `correct` field. Rows with both are listed once. These are development checks across several cohorts, not a combined accuracy estimate. Geometry fixtures are excluded because their new contract does not score legacy scene-v1.

| Case | Cohort | Mode | Failure | Expected subject | Selected subject | Expected-label retention |
|---|---|---|---|---|---|---|
| [hc-005](cases/hc-005.md) | `passive_intent` | controlled | **WRONG TARGET** | `1` | `None` | 100.00% |
| [hc-006](cases/hc-006.md) | `passive_intent` | controlled | **WRONG TARGET** | `1` | `None` | 100.00% |
| [hc-007](cases/hc-007.md) | `passive_intent` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `101` | 0.00% |
| [hc-008](cases/hc-008.md) | `passive_intent` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `101` | 0.00% |
| [hc-010](cases/hc-010.md) | `interaction` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-012](cases/hc-012.md) | `interaction` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-012](cases/hc-012.md) | `interaction` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-020](cases/hc-020.md) | `passive_intent` | live | **EXPECTED LABEL LOSS** | `1` | `1` | 97.98% |
| [hc-022](cases/hc-022.md) | `passive_intent` | live | **EXPECTED LABEL LOSS** | `1` | `1` | 97.86% |
| [hc-023](cases/hc-023.md) | `passive_intent` | live | **EXPECTED LABEL LOSS** | `1` | `1` | 97.76% |
| [hc-025](cases/hc-025.md) | `policy_targets` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-025](cases/hc-025.md) | `policy_targets` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-026](cases/hc-026.md) | `policy_targets` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `2` | `1` | 0.00% |
| [hc-030](cases/hc-030.md) | `passive_intent` | live | **EXPECTED LABEL LOSS** | `1` | `1` | 97.78% |
| [hc-031](cases/hc-031.md) | `passive_intent` | live | **WRONG TARGET** | `200` | `None` | not scored |
| [hc-034](cases/hc-034.md) | `passive_intent` | live | **EXPECTED LABEL LOSS** | `1` | `1` | 95.49% |
| [hc-035](cases/hc-035.md) | `policy_targets` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-035](cases/hc-035.md) | `policy_targets` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-036](cases/hc-036.md) | `passive_intent` | live | **EXPECTED LABEL LOSS** | `1` | `1` | 96.32% |
| [hc-037](cases/hc-037.md) | `passive_intent` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-039](cases/hc-039.md) | `policy_targets` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-040](cases/hc-040.md) | `passive_intent` | live | **EXPECTED LABEL LOSS** | `1` | `1` | 95.56% |
| [hc-044](cases/hc-044.md) | `passive_intent` | live | **WRONG TARGET** | `200` | `None` | 100.00% |
| [hc-046](cases/hc-046.md) | `passive_intent` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `200` | 0.00% |
| [hc-046](cases/hc-046.md) | `passive_intent` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `200` | 0.00% |
| [hc-048](cases/hc-048.md) | `policy_targets` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-049](cases/hc-049.md) | `passive_intent` | controlled | **EXPECTED LABEL LOSS** | `1` | `1` | 57.86% |
| [hc-049](cases/hc-049.md) | `passive_intent` | live | **EXPECTED LABEL LOSS** | `1` | `1` | 58.06% |
| [hc-050](cases/hc-050.md) | `passive_intent` | controlled | **EXPECTED LABEL LOSS** | `1` | `1` | 48.88% |
| [hc-051](cases/hc-051.md) | `passive_intent` | live | **EXPECTED LABEL LOSS** | `1` | `1` | 58.00% |
| [hc-052](cases/hc-052.md) | `passive_intent` | live | **EXPECTED LABEL LOSS** | `1` | `1` | 50.66% |
| [hc-054](cases/hc-054.md) | `passive_intent` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-054](cases/hc-054.md) | `passive_intent` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-055](cases/hc-055.md) | `passive_intent` | live | **EXPECTED LABEL LOSS** | `1` | `1` | 58.07% |
| [hc-056](cases/hc-056.md) | `policy_targets` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-056](cases/hc-056.md) | `policy_targets` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-057](cases/hc-057.md) | `policy_targets` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-057](cases/hc-057.md) | `policy_targets` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-058](cases/hc-058.md) | `policy_targets` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-058](cases/hc-058.md) | `policy_targets` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-059](cases/hc-059.md) | `interaction` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `2` | `1` | 0.00% |
| [hc-059](cases/hc-059.md) | `interaction` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `2` | `1` | 0.00% |
| [hc-060](cases/hc-060.md) | `interaction` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-060](cases/hc-060.md) | `interaction` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-065](cases/hc-065.md) | `policy_targets` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `2` | `1` | 0.00% |
| [hc-065](cases/hc-065.md) | `policy_targets` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `2` | `1` | 0.00% |
| [hc-066](cases/hc-066.md) | `interaction` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `2` | `1` | 0.00% |
| [hc-066](cases/hc-066.md) | `interaction` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `2` | `1` | 0.00% |
| [hc-067](cases/hc-067.md) | `passive_intent` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-067](cases/hc-067.md) | `passive_intent` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-068](cases/hc-068.md) | `passive_intent` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-068](cases/hc-068.md) | `passive_intent` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-073](cases/hc-073.md) | `passive_intent` | controlled | **EXPECTED LABEL LOSS** | `1` | `1` | 96.24% |
| [hc-074](cases/hc-074.md) | `passive_intent` | controlled | **WRONG TARGET** | `1` | `None` | 100.00% |
| [hc-075](cases/hc-075.md) | `passive_intent` | controlled | **WRONG TARGET** | `1` | `None` | 100.00% |
| [hc-076](cases/hc-076.md) | `passive_intent` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `101` | 0.00% |
| [hc-077](cases/hc-077.md) | `passive_intent` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `103` | 0.00% |
| [hc-081](cases/hc-081.md) | `interaction` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-081](cases/hc-081.md) | `interaction` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-083](cases/hc-083.md) | `passive_intent` | live | **EXPECTED LABEL LOSS** | `1` | `1` | 97.57% |
| [hc-091](cases/hc-091.md) | `passive_intent` | live | **EXPECTED LABEL LOSS** | `1` | `1` | 97.61% |
| [hc-092](cases/hc-092.md) | `passive_intent` | live | **EXPECTED LABEL LOSS** | `1` | `1` | 97.36% |
| [hc-096](cases/hc-096.md) | `policy_targets` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-097](cases/hc-097.md) | `policy_targets` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `3` | `2` | 0.00% |
| [hc-097](cases/hc-097.md) | `policy_targets` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `3` | `2` | 0.00% |
| [hc-099](cases/hc-099.md) | `passive_intent` | live | **EXPECTED LABEL LOSS** | `1` | `1` | 97.93% |
| [hc-100](cases/hc-100.md) | `passive_intent` | live | **WRONG TARGET** | `200` | `None` | not scored |
| [hc-103](cases/hc-103.md) | `passive_intent` | live | **EXPECTED LABEL LOSS** | `1` | `1` | 95.45% |
| [hc-104](cases/hc-104.md) | `policy_targets` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-104](cases/hc-104.md) | `policy_targets` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-105](cases/hc-105.md) | `passive_intent` | live | **EXPECTED LABEL LOSS** | `1` | `1` | 95.70% |
| [hc-108](cases/hc-108.md) | `policy_targets` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-109](cases/hc-109.md) | `passive_intent` | live | **EXPECTED LABEL LOSS** | `1` | `1` | 95.70% |
| [hc-113](cases/hc-113.md) | `passive_intent` | live | **WRONG TARGET** | `200` | `None` | 100.00% |
| [hc-117](cases/hc-117.md) | `policy_targets` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `2` | `1` | 0.00% |
| [hc-117](cases/hc-117.md) | `policy_targets` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `2` | `1` | 0.00% |
| [hc-118](cases/hc-118.md) | `passive_intent` | controlled | **EXPECTED LABEL LOSS** | `1` | `1` | 57.36% |
| [hc-118](cases/hc-118.md) | `passive_intent` | live | **EXPECTED LABEL LOSS** | `1` | `1` | 57.74% |
| [hc-119](cases/hc-119.md) | `passive_intent` | controlled | **EXPECTED LABEL LOSS** | `1` | `1` | 48.82% |
| [hc-120](cases/hc-120.md) | `passive_intent` | live | **EXPECTED LABEL LOSS** | `1` | `1` | 57.60% |
| [hc-121](cases/hc-121.md) | `passive_intent` | live | **EXPECTED LABEL LOSS** | `1` | `1` | 51.04% |
| [hc-123](cases/hc-123.md) | `passive_intent` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-123](cases/hc-123.md) | `passive_intent` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-124](cases/hc-124.md) | `passive_intent` | live | **EXPECTED LABEL LOSS** | `1` | `1` | 57.73% |
| [hc-125](cases/hc-125.md) | `policy_targets` | live | **EXPECTED LABEL LOSS** | `2` | `2` | 97.40% |
| [hc-126](cases/hc-126.md) | `policy_targets` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-126](cases/hc-126.md) | `policy_targets` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-128](cases/hc-128.md) | `interaction` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `2` | `1` | 0.00% |
| [hc-128](cases/hc-128.md) | `interaction` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `2` | `1` | 0.00% |
| [hc-129](cases/hc-129.md) | `interaction` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-129](cases/hc-129.md) | `interaction` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-132](cases/hc-132.md) | `passive_intent` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `3` | 0.00% |
| [hc-132](cases/hc-132.md) | `passive_intent` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `3` | 0.00% |
| [hc-134](cases/hc-134.md) | `policy_targets` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `2` | `3` | 0.00% |
| [hc-134](cases/hc-134.md) | `policy_targets` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `2` | `3` | 0.00% |
| [hc-135](cases/hc-135.md) | `interaction` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `2` | `1` | 0.00% |
| [hc-135](cases/hc-135.md) | `interaction` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `2` | `1` | 0.00% |
| [hc-136](cases/hc-136.md) | `passive_intent` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-136](cases/hc-136.md) | `passive_intent` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-141](cases/hc-141.md) | `passive_intent` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-141](cases/hc-141.md) | `passive_intent` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [hc-143](cases/hc-143.md) | `policy_targets` | controlled | **WRONG TARGET, EXPECTED LABEL LOSS** | `2` | `1` | 0.00% |
| [hc-143](cases/hc-143.md) | `policy_targets` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `2` | `1` | 0.00% |
| [hc-147](cases/hc-147.md) | `passive_intent` | live | **WRONG TARGET, EXPECTED LABEL LOSS** | `1` | `2` | 0.00% |
| [real-520871](cases/real-520871.md) | `passive_intent` | live | **WRONG TARGET** | `1864895` | `None` | not scored |
| [real-166918](cases/real-166918.md) | `policy_targets` | live | **WRONG TARGET** | `1865335` | `1482938` | not scored |
| [real-117719](cases/real-117719.md) | `policy_targets` | live | **WRONG TARGET** | `1492244` | `1494627` | not scored |
