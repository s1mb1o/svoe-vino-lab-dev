# Final profile comparison

Date: 2026-09-27. Status: **terminal_with_failures**.
All 53 authorized internal or local profiles have terminal outcomes.
There are **48 validated successful runs, one run with eight retained errors, and four unavailable local profiles**.
The external recognizer is the 54th configured profile. It remains excluded pending photo-transfer approval.
This report does not claim 53 successful measurements.

Each of the 49 measured runs retains 2228 query rows and 1851 unique image digests.
Quality uses 1644 positive rows and 584 negative constraints.
A negative row forbids its named wine. Another prediction is not a confirmed identification.
The 48 successful runs have zero query errors, zero degraded results, and no per-run input drift.
The failed run retains all eight errors and all original rows and scores.

The remote runs use four query workers and caches. The local policy specifies one worker.
The queue requests `use_barcode=true`. Only profiles with a configured barcode stage scan codes.
The queue runs one profile at a time through the existing run-job API. Results appear on Runs.
No profile attempt was duplicated. No production behavior changed during these comparisons.

## Recommended settings and measured leaders

For full-set bulk reruns, retain `barcode-rerank-siglip2-512-crop`, caches, and four query workers.
It has the highest positive R@1 among the 48 validated successful profiles.
For fresh sequential demo requests, the measured candidate is persistent `photo4` with
`barcode-siglip2-512-as-is`. Its separate HTTP pilot has a latency/quality tradeoff and no hard timeout.
The sections below preserve those two distinct measurement scopes.

| Profile | Correct R@1 /1644 | R@5 | Forbidden top-1 /584 | Cached runner wall, s |
|---|---:|---:|---:|---:|
| `barcode-rerank-siglip2-512-crop` | 1392 (84.67%) | 97.02% | 90 | 133.8 |
| `barcode-siglip2-p1024-crop` | 1370 (83.33%) | 97.99% | 98 | 110.3 |
| `rerank-siglip2-512-crop` | 1368 (83.21%) | 95.74% | 90 | 129.2 |
| `barcode-rerank-siglip2-512-crop-label` | 1363 (82.91%) | 96.47% | 94 | 895.2 |
| `barcode-siglip2-512-crop` | 1351 (82.18%) | 97.02% | 100 | 97.5 |

`barcode-siglip2-p1024-crop` has the highest measured R@5: 1611/1644 (97.99%).
Its index covers more catalogue items. The cross-model ranking does not isolate model quality.
The new label tower has lower R@1 and R@5 than the reference. Do not replace the reference on this evidence.

Successful cached runner walls range from 67.0 to 895.2 seconds.
The fastest observed runner is `barcode-dinov3-vitb16-as-is`, with 35.95% R@1.
These walls include different cold starts, cache states, and host conditions.
They do not form a controlled model-speed ranking or a fresh-image latency test.
Per-run intent-to-final intervals, throughput, worker settings, and coverage are in
[final-profile-metrics.json](final-profile-metrics.json).

## All 54 configured profiles

Every row remains visible. `done` means validated success. `invalid_completion` retains errors.
Metrics marked `raw` belong to the failed run and are excluded from the successful ranking.
A dash means no measured value. It does not mean zero.
All measured rows use four workers and caches. The four unavailable local rows specify one worker.
The Barcode column describes the configured stage, not the queue option.

Coverage A: 4054 current items, 127 missing items, two failed items, zero stale items;
2051 full-view wines and 2047 label-view wines.
Coverage B: 4181 current items, zero missing items, two failed label items, zero stale items;
2096 full-view wines and 2092 label-view wines.
B is the prepared NaFlex-1024 index. The two not-applicable label items are outside its build plan.
Local current index coverage was not validated for a launch after the capacity refusal.

| Profile | Outcome | Barcode | R@1, % | R@5, % | Forbidden top-1 / top-10 | Runner wall, s | Coverage |
|---|---|---|---:|---:|---:|---:|---|
| `vino-svoe-search-by-photo` | awaiting_user_approval | — | — | — | — | — | — |
| `siglip2-p256-as-is` | done | no | 65.33 | 86.92 | 98 / 422 | 81.1 | A |
| `siglip2-p256-crop` | done | no | 74.94 | 92.15 | 97 / 472 | 95.5 | A |
| `siglip2-p256-crop-seg` | done | no | 73.97 | 92.03 | 96 / 475 | 93.4 | A |
| `siglip2-p512-as-is` | done | no | 74.15 | 92.94 | 111 / 468 | 86.5 | A |
| `siglip2-p512-crop` | done | no | 79.50 | 94.77 | 108 / 480 | 98.4 | A |
| `siglip2-p1024-as-is` | done | no | 79.08 | 95.68 | 103 / 489 | 110.0 | B |
| `siglip2-p1024-crop` | done | no | 81.93 | 96.90 | 98 / 502 | 113.1 | B |
| `siglip2-p14-384-as-is` | invalid_completion | no | 76.76 raw | 93.19 raw | 97 / 465 | 169.9 | A |
| `siglip2-p14-384-crop` | done | no | 78.65 | 94.83 | 94 / 475 | 97.7 | A |
| `siglip2-256-as-is` | done | no | 61.13 | 84.37 | 106 / 397 | 111.4 | A |
| `siglip2-256-crop` | done | no | 69.34 | 89.48 | 108 / 433 | 95.6 | A |
| `siglip2-384-as-is` | done | no | 74.45 | 92.52 | 97 / 451 | 117.0 | A |
| `siglip2-384-crop` | done | no | 76.64 | 94.10 | 99 / 472 | 97.8 | A |
| `siglip2-512-as-is` | done | no | 79.93 | 95.44 | 94 / 467 | 80.0 | A |
| `siglip2-512-crop` | done | no | 80.72 | 95.74 | 100 / 474 | 98.8 | A |
| `naflexvit-p256-as-is` | done | no | 66.00 | 86.74 | 96 / 426 | 94.3 | A |
| `naflexvit-p256-crop` | done | no | 74.27 | 93.19 | 100 / 473 | 90.8 | A |
| `pe-core-l14-336-as-is` | done | no | 70.74 | 91.55 | 93 / 439 | 98.1 | A |
| `pe-core-l14-336-crop` | done | no | 75.00 | 93.37 | 101 / 465 | 97.6 | A |
| `dinov3-vitb16-as-is` | done | no | 34.61 | 62.96 | 65 / 255 | 73.6 | A |
| `dinov3-vitb16-crop` | done | no | 42.82 | 73.24 | 80 / 320 | 87.8 | A |
| `dinov3-vitl16-as-is` | done | no | 29.81 | 57.36 | 46 / 212 | 91.1 | A |
| `dinov3-vitl16-crop` | done | no | 43.37 | 73.48 | 65 / 304 | 96.6 | A |
| `local-siglip2-p256-as-is` | unavailable | — | — | — | — | — | — |
| `local-siglip2-p256-crop` | unavailable | — | — | — | — | — | — |
| `barcode-siglip2-p256-as-is` | done | yes | 66.67 | 88.20 | 98 / 422 | 82.3 | A |
| `barcode-siglip2-p256-crop` | done | yes | 76.28 | 93.43 | 97 / 472 | 93.6 | A |
| `barcode-siglip2-p256-crop-seg` | done | yes | 75.30 | 93.25 | 96 / 475 | 92.2 | A |
| `barcode-siglip2-p512-as-is` | done | yes | 75.61 | 94.22 | 111 / 468 | 85.9 | A |
| `barcode-siglip2-p512-crop` | done | yes | 80.90 | 96.05 | 108 / 480 | 97.0 | A |
| `barcode-siglip2-p1024-as-is` | done | yes | 80.54 | 96.96 | 103 / 489 | 108.7 | B |
| `barcode-siglip2-p1024-crop` | done | yes | 83.33 | 97.99 | 98 / 502 | 110.3 | B |
| `barcode-siglip2-p14-384-as-is` | done | yes | 78.53 | 95.01 | 97 / 465 | 81.5 | A |
| `barcode-siglip2-p14-384-crop` | done | yes | 80.11 | 96.05 | 94 / 475 | 96.9 | A |
| `barcode-siglip2-256-as-is` | done | yes | 62.59 | 85.77 | 106 / 397 | 79.7 | A |
| `barcode-siglip2-256-crop` | done | yes | 70.80 | 90.88 | 108 / 433 | 95.2 | A |
| `barcode-siglip2-384-as-is` | done | yes | 75.85 | 93.86 | 97 / 451 | 79.6 | A |
| `barcode-siglip2-384-crop` | done | yes | 78.10 | 95.44 | 99 / 472 | 94.0 | A |
| `barcode-siglip2-512-as-is` | done | yes | 81.39 | 96.78 | 94 / 467 | 168.4 | A |
| `barcode-siglip2-512-crop` | done | yes | 82.18 | 97.02 | 100 / 474 | 97.5 | A |
| `barcode-naflexvit-p256-as-is` | done | yes | 67.34 | 88.02 | 96 / 426 | 75.7 | A |
| `barcode-naflexvit-p256-crop` | done | yes | 75.61 | 94.40 | 100 / 473 | 91.1 | A |
| `barcode-pe-core-l14-336-as-is` | done | yes | 72.14 | 92.76 | 93 / 439 | 82.5 | A |
| `barcode-pe-core-l14-336-crop` | done | yes | 76.34 | 94.59 | 101 / 465 | 96.9 | A |
| `barcode-dinov3-vitb16-as-is` | done | yes | 35.95 | 64.23 | 65 / 255 | 67.0 | A |
| `barcode-dinov3-vitb16-crop` | done | yes | 44.16 | 74.51 | 80 / 320 | 84.8 | A |
| `barcode-dinov3-vitl16-as-is` | done | yes | 31.20 | 58.64 | 46 / 212 | 78.4 | A |
| `barcode-dinov3-vitl16-crop` | done | yes | 44.77 | 74.76 | 65 / 304 | 91.4 | A |
| `barcode-local-siglip2-p256-as-is` | unavailable | — | — | — | — | — | — |
| `barcode-local-siglip2-p256-crop` | unavailable | — | — | — | — | — | — |
| `rerank-siglip2-512-crop` | done | no | 83.21 | 95.74 | 90 / 474 | 129.2 | A |
| `barcode-rerank-siglip2-512-crop` | done | yes | 84.67 | 97.02 | 90 / 474 | 133.8 | A |
| `barcode-rerank-siglip2-512-crop-label` | done | yes | 82.91 | 96.47 | 94 / 476 | 895.2 | A |

The [final saved-evidence snapshot](final-snapshot/queue-summary.md) and its
[JSON ledger](final-snapshot/queue-summary.json) retain run IDs, attempts, PID evidence, and artifact hashes.
Its queue-time missing-index notes are historical. NaFlex-1024 preparation finished before its four runs.
The integrated metrics file also retains the failed run's raw metrics from the reviewed archive.

## Failed and unavailable outcomes

`siglip2-p14-384-as-is` completed 2228 rows with eight embedding errors.
The failures are positive queries `q-000001` through `q-000008`.
The gateway reported HTTP 500 with `upstream command exited prematurely`.
The stored result status is null for those rows. The raw R@1/R@5 remain 1262/1644 and 1532/1644.
The original log contains 24 built-in client retry events. No profile POST was repeated.
Saved gateway evidence records eight premature process exits, then a health-check pass.
The model subsequently served the other three profiles without query errors.
The original startup cause is unestablished. The available log does not prove an OOM.
Read the [reviewed failure archive](g9-failed-run-evidence.md) and [review record](g9-failed-run-review.json).

All four local profiles are unavailable under the unchanged memory gate.
The fresh Mac observation has 32 GiB RAM, pressure code 2, 35.35 GiB swap used, and 0.65 GiB swap free.
The conservative 16 GiB total additional allowance plus the queue's 20 GiB reserve requires 36 GiB.
This exceeds the physical upper bound. The allowance is not a measured peak.
This is a policy-scoped refusal, not proof that the model can never run on the Mac.
Each local row retains authorization, an empty attempt list, and null PID/run ID.
No model was loaded, and no application was stopped.
Read [final G10 evidence](g10-readiness-final.md) and the [capacity decision](g10-capacity-decision.json).

## Fast bulk reruns

Use the barcode cache and four query workers for remote embedding profiles.
The separate completed bulk comparison retains the full barcode scan and the reference crop/rerank profile.
All four settings preserve baseline predictions, candidate order, ranks, and outcomes.

| Barcode cache | Query workers | Process wall, s | Harness wall, s |
|---|---:|---:|---:|
| Cold | 1 | 855.785 | 854.498 |
| Warm | 1 | 462.249 | 460.973 |
| Cold | 4 | 232.358 | 231.029 |
| Warm | 4 | 129.634 | 128.303 |

The observed four-worker speed ratios are 3.68 for cold cache and 3.57 for warm cache.
Warm barcode caches remove native decoding in this instrumented comparison.
Cached SAM3 and VLM responses still require image preparation and response processing.
Remote query embeddings still require requests.
The cold one-worker run retains its initial 42.054 s embedding request.
This startup-associated request includes other work. It is not an isolated model-load timer.
Startup, host load, and model residency differ between runs.
Use one query worker for local profiles under the queue policy.

Source: [completed barcode recommendations](../2026-09-27_barcode-variants/final-recommendations.md).

## Fresh sequential demo requests

Persistent execution with per-image `photo4` decoding is the measured implementation candidate.
It retains all 24 known barcode hits. It can overlap up to four tile tasks inside one image.
Do not multiply four internal decode threads by four bulk query workers.

The HTTP pilot has 64 rows, 61 image digests, 54 positive rows, and ten negative constraints.
It includes all 24 known barcode-hit rows. Its deadline rate is not a full-corpus estimate.
Requests are sequential and bypass prior per-image response caches.
The HTTP timer covers upload through the complete response body, including response reconstruction.
This loopback timer excludes browser rendering and phone/network transit latency.

The main eight-cell HTTP pilot retains all 512 observations: 511 successful responses and one failure.
In the process/full cold-Qwen case, `q-000078` returns HTTP 503 after 300.701 s.
The watchdog expires during the first conditional rerank after an unloaded-Qwen preflight.
The retained failure does not isolate model-load time. It remains in all raw denominators.

| Persistent `photo4` profile | Correct top-1 /54 | Correct within 3 s /54 | Complete response within 3 s /64 | Forbidden top-1 /10 |
|---|---:|---:|---:|---:|
| Reference crop/rerank | 45 | 38 | 50 | 0 |
| Crop without rerank | 44 | 40 | 58 | 0 |
| As-is without crop/rerank | 43 | 43 | 64 | 1 |

The as-is profile gives the best measured deadline fraction in this selected comparison.
It trades two correct top-1 answers for more timely answers versus the reference.
Its HTTP p50 / p95 / maximum are 305.4 / 1634.4 / 2158.0 ms.
All three profiles have R@5 of 54/54.
The reviewed source also preserves the separate 52-positive sensitivity analysis.
Persistent execution and `photo4` remain experimental harness behavior.
No enforced three-second timeout, cancellation policy, or hard deadline guarantee was implemented or validated.

Source: [sequential HTTP evidence and limits](../2026-09-27_barcode-variants/final-recommendations.md).

## New label embedding tower

The reference and new label profile use the same frozen queries, catalogue, model, and index.
The new profile searches label vectors as a second tower.
It produces 29 fewer correct top-1 answers and nine fewer correct top-5 answers.

| Metric | Reference | Label profile | Paired changes |
|---|---:|---:|---|
| R@1 /1644 | 1392 | 1363 | 51 gained; 80 lost |
| R@5 /1644 | 1595 | 1586 | 10 gained; 19 lost |
| Forbidden top-1 /584 | 90 | 94 | 18 introduced; 14 removed |
| Forbidden top-10 /584 | 474 | 476 | 21 introduced; 19 removed |

These results do not support replacing the reference with this label profile.
Two missing-label rows correctly use the full tower alone.
Changed retrieval order and rerank selection also affect quality.
Do not attribute every loss to segmentation.

The run walls are 133.8 s and 895.2 s, with unequal cache warmth.
The label run has 1457 retrieval-label SAM3 misses and 50 rerank VLM misses.
The reference has no retrieval-label step and zero rerank VLM misses.
These walls do not measure equal-cache steady performance or demo latency.

Source: [reviewed paired label comparison](label-comparison-final.md).

## Coverage and other reviewed comparisons

The rebuilt NaFlex-1024 index has 4181 current items and no missing items.
The compared NaFlex-256/512 indexes have 4054 current items and 127 missing items.
NaFlex-1024 has 45 more wines in each view. All three retain two failed items.
Thus, cross-budget comparisons do not isolate the patch budget.
Matched crop/as-is and plain/barcode pairs use the same index.

The reviewed G2 and G3–G5 comparisons show crop gains with negative-constraint tradeoffs.
Barcode resolves the same 24 correct rows and preserves the matching pipeline on 2204 fallback rows.
A scan-cache hit is not a resolved wine answer.
Native-call totals are absent from these ordinary profile traces.

Sources: [G2 plain](g2-plain-comparison.md), [G2 barcode](g2-barcode-comparison.md),
and [G3–G5 comparison](g3-g5-comparison.md).

## Annotation constraints

The frozen audit finds 67 identical-digest groups with incompatible exact-slug positive constraints.
They contain 136 positive rows. No same-digest positive truth conflicts with a negative forbidden slug.
If identical bytes always produce the same deterministic answer without row-specific metadata,
the optimistic top-1 ceiling is 1576/1644, or 95.8637%. At least 68 positive rows must miss.
This is a conditional metadata bound, not an achieved result or an annotation correction.
It does not bound top-5. All raw labels, weights, and denominators remain unchanged.

Source: [reviewed annotation audit](annotation-audit.md).

## Evidence and external authorization

The [final source/control audit](final-production-source-check.md) checks all 49 frozen attempts.
Their 57-file production-source maps match each other and the current source files.
Their frozen configuration hashes and query identities also match.
The audit records two deliberate catalogue snapshots and 11 embedding indexes.
It does not inspect source-photo bytes, live database/configuration state, or remote dependencies.
The failed attempt remains an invalid completion. This audit does not promote it to success.

The final accounting is 48 successful, one invalid completion, and four unavailable profiles among 53 authorized profiles.
The final snapshot reports `terminal_with_failures`. No authorized profile is pending or active.
Technical evidence remains in this directory. The barcode comparison artifacts remain in the sibling report directory.

The external `vino-svoe-search-by-photo` profile retains `authorized_to_start:false` and `awaiting_user_approval`.
No photo was sent to `api.vino-svoe.ru` by this execution.
Automatic approval review requires separate explicit authorization for that external photo transfer.
This pending request is not included among the 53 authorized outcomes.
