# Benchmark results

Summary updated: 2026-10-20.

This file indexes recorded measurements.
Each row identifies its cohort, model or pipeline, and source.
The documentation review does not run a new inference benchmark.
The dated reports retain their original scores and test counts.

## Latest retrieval research

The completed GX10 campaign uses `google/siglip2-so400m-patch16-naflex`.
It evaluates 353,188 unique retrieval configurations per frozen testset.
It uses no re-ranking.
The rows below keep all recall values from one exact recipe together.

| Cohort | Exact recipe | R@1 | R@5 | R@10 | Source |
|---|---|---:|---:|---:|---|
| `my`: 2,970 positive assignments | R011; p512; custom pooling, axial views, bottle–label fusion | **90.77% (2,696/2,970)** | 99.83% (2,965/2,970) | 100.00% (2,970/2,970) | [R011 recipe](RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r011) |
| `my-failed-2`: 668 positive assignments | R001; p1024; custom pooling and axial views | **67.37% (450/668)** | 98.35% (657/668) | 99.85% (667/668) | [R001 recipe](RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r001) |
| `my-failed-2`: 668 positive assignments | R018; best p512 Top-1 recipe | **66.17% (442/668)** | 98.80% (660/668) | 99.55% (665/668) | [R018 recipe](RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md#r018) |

The standard bottle baseline has 2,582/2,970 Top-1 hits on `my`.
R011 adds 114 hits, or 3.84 percentage points, within that frozen cohort.
The hard-cohort baseline has 294/668 Top-1 hits.
R001 adds 156 hits, or 23.35 percentage points, within that frozen cohort.
R018 adds 148 hits, or 22.16 percentage points.

The full `my` snapshot has 3,409 assignments: 2,970 positive, 430 negative, and 9 no-match.
The hard cohort has 668 positive assignments and 627 distinct images.
The two testsets share 619 image identities.
Both testsets were used for development selection.
These results do not establish independent validation, a production matcher score, or an official jury score.
No HTTP latency measurement is attached to these recipe rows.
Read [the full research reference](RETRIEVAL-ALGORITHMS-AND-RESULTS-20261020.md)
and [the compact metric export](research/retrieval-20261020/summaries/metrics.csv).

## Recorded matcher API results

| Pipeline or artifact | Cohort and contract | Quality | Recorded latency | Source |
|---|---|---|---|---|
| Frozen submission `predictions.jsonl` | 100 organizers' photos; team reference; `POST /v1/eval/predict` | 95/100 accepted results | Median 1,316.5 ms; maximum 2,906 ms | [Predictions](predictions.jsonl), [README](README.md) |
| `cascade-p512-rot5` ranked API | 63 positive and 21 negative organizers' photos; `POST /v1/match`; no time budget | R@1 90.48%; R@5 100% | No timing value is asserted here | [Recorded summary](README.md) |
| `cascade-p512-rot5` with a local FP8 VLM on RTX 4090 | `official-real-photos`; 84 requests; 63 positive; evaluator time budget | R@1 93.65% (59/63); zero request errors | Median 1,353 ms; P90 1,929 ms; maximum 2,905 ms | [2026-10-01 measurement](workbench/ResearchLog.md) |

The 95/100 value is the team's internal check.
The team created the reference answers and accepted alternatives.
The diagnostic 97/100 run used corrections after the answers were known.
It remains excluded from the frozen submission result.
The ranked API and evaluator time budget are different request settings.
The committed default remains `siglip2-p512-as-is` in [matcher/config.yaml](matcher/config.yaml).
Do not assign a cascade or research result to that default.

## Android measurements

Android uses SigLIP2 Base NaFlex p512 with 768-dimensional vectors.
The server research above uses SO400M with 1,152-dimensional vectors.
The two model families have different reference indexes and preparation pipelines.

### Full `my`: matched comparison from 2026-10-19

Both rows use 2,970 positive assignments from 3,409 total assignments.
The query files and accepted alternatives are identical.

| Complete phone pipeline | Top-1 | Top-5 | Top-10 | Client median / P95 | Source |
|---|---:|---:|---:|---|---|
| Full photo; standard pooling; Pixel 8 GPU | 69.09% (2,052/2,970) | 87.10% (2,587/2,970) | 90.03% (2,674/2,970) | 924 / 1,479 ms | [Full-photo report](android/docs/reports/2026-10-19_pixel8-base-p512-full-my.md) |
| Separate DIS GPU + encoder GPU experiment | **72.29% (2,147/2,970)** | 88.18% (2,619/2,970) | 90.34% (2,683/2,970) | 1,319 / 2,343 ms | [Dual-GPU report](android/docs/reports/2026-10-19_pixel8-p512-dis-dual-gpu-my.md) |

The experiment adds 95 Top-1 hits, or 3.20 percentage points.
It also increases latency and sampled memory use.
Its five DIS no-object errors remain in the positive denominator.
Both pipelines return a wine for all nine no-match queries.
The experiment uses a separate application.
It does not establish the result of the later custom-pooling release.

### Android 0.3.0: selected hard cohort

The later release is recorded on `origin/main` at `6bd4abed`.
The source of that release can differ from an older local checkout.
The links below identify the exact committed evidence.

| Pipeline and run | Cohort | Top-1 | Top-5 | Top-10 | Complete request median / P95 | Source |
|---|---|---:|---:|---:|---|---|
| Fresh standard full-photo control | 668 `my-failed-2` assignments | 41.02% (274/668) | 77.84% (520/668) | 84.58% (565/668) | 966 / 1,700 ms | [DIS comparison](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/6bd4abed8009296dec8cdde4e418103f610a74ba/android/docs/reports/2026-10-20_dis-p512-pooling.md) |
| DIS-1024 cropped custom experiment | Same 668 assignments | **47.01% (314/668)** | 84.58% (565/668) | 89.82% (600/668) | 2,607 / 3,429 ms | [DIS comparison](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/6bd4abed8009296dec8cdde4e418103f610a74ba/android/docs/reports/2026-10-20_dis-p512-pooling.md) |
| Android 0.3.0 `DIS768_CUSTOM` replay | Same 668 assignments | **46.56% (311/668)** | 84.58% (565/668) | 89.67% (599/668) | 1,372 / 1,832 ms | [Release record](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/6bd4abed8009296dec8cdde4e418103f610a74ba/android/docs/releases/0.3.0.md) |

The release replay completes all 668 requests with zero errors.
Its Top-1 count exceeds the standard control by 37 hits, or 5.54 percentage points.
The release replay preserves every Top-1 decision of the frozen DIS-768 experiment.
The DIS-1024 experiment has three more Top-1 hits, with greater measured latency.
It requires USB continuation after assignment 190.
It is not an uninterrupted transport-stability pass.
These comparisons concern complete pipelines.
They do not isolate custom pooling or remove differences in thermal conditions.
The release request times include debug embedding serialization.
They are not camera-to-result UI times.
No full-`my` quality result is recorded for Android 0.3.0 in these sources.

The same release record reports 86 accepted results from the original 100-image Eval.zip.
That consists of 81 exact results and five accepted alternatives.
It has 14 mismatches and no empty or missing predictions.
Its comparison status is `FAIL` because that checker requires 100 accepted results.
This phone result does not replace the separate server submission result of 95/100.

## Historical 2026-09-27 snapshot

This section preserves the earlier comparison.
It is no longer a list of the best results across all later experiments.

- 2,228 query rows: 1,644 positive rows and 584 negative constraints.
- 1,851 distinct image digests.
- 53 permitted profiles have a final status.
- 48 profiles have valid results with no query errors.
- One profile has errors. Four profiles are unavailable because of memory limits.

A negative constraint forbids one wine.
It does not identify a correct alternative.

| Pipeline | Role in this snapshot | R@1 | R@5 | Forbidden Top-1 | Cached bulk P50 / P95 |
|---|---|---:|---:|---:|---|
| `siglip2-p512-as-is` | Committed standalone default | 74.15% | 92.94% | 111/584 | 150 / 235 ms |
| `barcode-rerank-siglip2-512-crop` | Highest R@1 in the September comparison | **84.67%** | 97.02% | 90/584 | 186 / 552 ms |
| `barcode-siglip2-p1024-crop` | Highest R@5 in the September comparison | 83.33% | **97.99%** | 98/584 | 171 / 397 ms |

Bulk latency uses caches and four workers.
It is not a cold public HTTP request measurement.
The newer research `my` cohort has 2,970 positive assignments.
The change from 84.67% to 90.77% is not a controlled gain on one fixed cohort.

### Standalone transfer checks for that snapshot

- The bundle contains 2,094 wines and 4,642 vectors of 1,152 dimensions.
- Matcher and workbench model inputs agree in 400/400 checks.
- Matcher and workbench Top-1 results agree in 100/100 checks.
- The three harness photos receive answers in 334–455 ms after model loading.
- Bundle version 2 preserves the older bundle's Top-1 result in 300/300 vector checks.

These checks verify the pipeline transfer.
They do not establish three correct recognitions or replace a complete quality benchmark.
The earlier annotation audit finds 67 groups with incompatible positive labels for identical bytes.
Its optimistic ceiling is 1,576/1,644, or 95.86%.
Catalogue coverage differs between indexes.
Read [the September profile comparison](workbench/docs/reports/2026-09-27_all-profile-rerun/final-profile-comparison.md)
and [the annotation audit](workbench/docs/reports/2026-09-27_all-profile-rerun/annotation-audit.md).

## Recorded verification results

These counts describe software checks. They are not recognition-accuracy measurements.
The [assessment](ASSESSMENT.md) records source revisions and test limits.

| Check recorded on 2026-10-20 | Result |
|---|---|
| Account verification at `121c7f08` | Lockfile and Ruff checks pass; 159 tests pass; no skips |
| Web UI unit suite in the assessment review | 616 tests pass; 26 tests skip |
| MCP unit and protocol suite in the assessment review | 51 tests pass; no skips |
| Focused workbench export and production-error tests | 24 tests pass |

During this documentation review, the portable research checker passes again.
The review also independently recalculates the Android 0.3.0 replay counts from its saved
queries, responses, and predictions: 311/565/599 hits from 668 assignments.
The recalculated median is 1,372.026 ms and the inclusive P95 is 1,831.934 ms.
The complete replay files remain in the external artifact directory named by the release record.
No phone, model service, or training job starts for this review.
