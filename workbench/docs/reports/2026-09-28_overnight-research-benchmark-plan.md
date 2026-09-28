# Overnight evidence plan for the presentation and README

Date: 2026-09-28.

## Decision

Do not run another broad model sweep tonight.
The project already has terminal outcomes for 53 internal or local profiles.
It also has complete barcode, crop, cache, and selected HTTP latency studies.

Use the night to close evidence gaps in the submitted system.
The final evidence must distinguish the standalone matcher from the best workbench pipeline.

## Current evidence and gaps

The root `README.md` names `siglip2-p512-as-is` as the standalone matcher.
It reports 74.15% R@1 and 92.94% R@5 for that profile.
The same file has an explicit TODO to describe the benchmark set.

The established research result is 84.67% R@1 and 97.02% R@5.
It uses `barcode-rerank-siglip2-512-crop` on 1,644 positive rows.
Its 584 negative rows are constraints.
They are not confirmed no-match photos.

The new run of `barcode-rerank-siglip2-p1024-crop` reports 85.12% R@1 and 97.81% R@5.
It uses 1,647 positive rows and 579 negative constraints.
It has zero query errors.
It used caches and four workers.
Its latency is not comparable with the sequential evaluator path.

The paired p512 and p1024 comparison on this new snapshot has 81 wins and 60 losses.
The exact McNemar p-value is 0.0918.
The new gain is not strong evidence at a 0.05 threshold.
The p1024 result also does not improve the two smaller checks:

- `official-real-photos`: 90.00% against 91.67% for p512, exact p-value 1.0.
- `vlmrerank-8b-failed`: 44.13% against 44.69% for p512, exact p-value 1.0.

The current deck still contains an unsupported prompt-language claim.
It still contains an isolated 0.2-second barcode measurement.
It has no final benchmark table.
It has no evaluator-path latency result.
It has no no-match result.

## Start gate

Do not start a benchmark while plan 75 moves `data/`.
At 17:37 MSK, the move was active and port 8168 was down.
Wait until the owner section in `ACTIVE_WORK.md` marks stage 1 complete.
Then require all conditions below.

1. `GET /api/dataset` returns HTTP 200.
2. No embedding build, run job, seed job, or data move is active.
3. The GX10 task tracker matches the actual process state.
4. GX10 has the required free memory plus the 20 GiB safety margin.
5. The database passes `PRAGMA integrity_check` and `PRAGMA foreign_key_check`.
6. The selected indexes have zero missing and zero stale full-view items.
7. The matcher bundle validator passes.
8. The workbench and matcher unit tests pass.

Create one immutable benchmark manifest before the first run.
Record these values:

- Git commit and dirty-tree patch hash.
- Effective configuration hash.
- Database backup hash.
- Test-row and image-digest hashes.
- Index, vector, cluster, and rule hashes.
- Bundle manifest and file hashes.
- Model names and served revisions, when the service exposes them.
- Cache policy and worker count.
- Host load and available memory.

Do not compare runs whose manifests differ in a relevant input.

## P0 benchmark 1: clean final-pipeline ablation

Run four profiles on the same frozen `my` snapshot:

1. `siglip2-p1024-as-is`.
2. `siglip2-p1024-crop`.
3. `barcode-siglip2-p1024-crop`.
4. `barcode-rerank-siglip2-p1024-crop`.

Use four workers and the same cache policy for all four runs.
Use the runs for quality only.
Do not use their wall time as evaluator latency.

Run the final p512 and p1024 profiles on `official-real-photos` too.
This set is small, so keep its denominator visible.

Report these measures:

- R@1, R@5, R@10, and MRR.
- Exact R@1 wins and losses for each adjacent pipeline stage.
- Exact McNemar p-values.
- Negative forbidden Top-1 and Top-10 counts.
- Errors and degraded answers.
- Index coverage.
- Rerank trigger count, wins, and losses.

Acceptance condition:

- Every run uses the same frozen queries and catalogue state.
- Every paired row has the same image SHA-256.
- Each claimed gain names the numerator and denominator.
- The report does not call a difference significant when the test does not support it.

Estimated time: 45 to 90 minutes after the indexes are ready.

## P0 benchmark 2: actual evaluator HTTP path

Benchmark the current standalone matcher, `siglip2-p512-as-is`.
Use the real `POST /v1/eval/predict` endpoint.
Send requests sequentially, as the official harness does.

Run one complete quality pass on the frozen positive and negative rows.
Run three latency passes on a fixed wine-disjoint sample of at least 200 images.
Include the public HTTPS edge in one pass if it is the submitted endpoint.
Keep the local or LAN pass separate from the public pass.

Run `POST /v1/match` on the same images to obtain Top-5 and score margins.
Verify that its Top-1 equals the result of `POST /v1/eval/predict`.

Report these measures:

- Top-1 and Top-5 quality.
- Full-response p50, p95, p99, and maximum latency.
- Complete responses within 3 seconds and within 10 seconds.
- HTTP status counts and empty responses.
- First request after model load.
- Later requests in the same process.
- Prediction parity with the equivalent workbench profile.

Acceptance condition:

- The timer includes upload through the complete response body.
- The quality pass has no per-image response-cache hits.
- The report separates model cold start from steady requests.
- The report does not describe four-worker throughput as single-request latency.

Estimated time: 60 to 120 minutes.

## P0 benchmark 3: metric and annotation audit

Run this analysis offline from the frozen run artifacts.
Do not send model requests.

Report five views of quality:

1. Row-weighted canonical R@1 and R@5.
2. Unique-image-digest R@1 and R@5.
3. Macro recall by wine.
4. Group-aware R@1 for approved aliases or variants.
5. Canonical R@1 after same-byte truth conflicts are excluded as a sensitivity check.

Use an exact paired McNemar test for pipeline comparisons.
Use a cluster bootstrap by image digest and by wine for 95% confidence intervals.
Do not use a naive row bootstrap because the set repeats image bytes and wines.

Regenerate the annotation audit on the final snapshot.
Report exact-byte conflicts, catalogue leakage, missing catalogue images, and weak references.

Acceptance condition:

- The report states the snapshot date.
- It states positive rows, negative constraints, no-match rows, unique digests, and unique wines.
- It keeps raw and sensitivity metrics separate.

Estimated time: 30 to 60 minutes on CPU.

## P0 benchmark 4: no-match and confidence behavior

The current benchmark has zero confirmed no-match rows.
The 579 negative rows do not solve this gap.
Each negative row forbids one slug, but another returned slug can still be correct.

Create a small, reviewed no-match set before this benchmark.
Use at least 150 unique images.
Include non-catalogue wines and irrelevant package photos.
Keep source provenance and manual review decisions.
Keep this set outside the catalogue and outside model-selection work.

Run the standalone matcher and the final research pipeline.
Use ranked scores to test score and score-margin thresholds.

Report these measures:

- False accept rate on no-match images.
- Coverage and selective accuracy on positive images.
- False reject rate on positive images.
- Accuracy versus coverage curve.
- Threshold selected before the final test pass.
- Results on the held-out part alone.

Acceptance condition:

- Threshold selection and threshold evaluation use different images.
- The report does not call a negative constraint a no-match truth.
- The README states that the released matcher always answers if abstention remains unimplemented.

Estimated time: two to three hours, including review.
If the reviewed set is not ready, do not invent a no-match number.

## P1 benchmark 5: pipeline strata

Use the frozen results and traces.
Do not rerun inference unless one required trace field is absent.

Report quality and latency for these strata:

- Unique code answer and visual fallback.
- Barcode-tagged, QR-tagged, and untagged images.
- SAM3 package success and fallback.
- Rerank triggered and not triggered.
- Near-duplicate conflict and ordinary case.
- Expected wine present and absent from the index.
- `official-real-photos`, the main set, and the hard set.

Show both the row count and the unique-image count for every stratum.
Use the strata to explain where each pipeline stage helps.

Estimated time: 30 to 60 minutes on CPU.

## P1 benchmark 6: reranker repeatability

Use only the rows that trigger the VLM reranker.
Run three isolated no-cache repeats with the same rules and model.
Do not change the rules between repeats.

Report the Top-1 flip rate, answer agreement, R@1 variance, and request failures.
Record the served model revision when possible.
Stop if another GX10 task creates sustained contention.

This benchmark tests repeatability.
It does not tune the reranker.

Estimated time: 60 to 120 minutes.

## Checks that should run once

Run these checks after the data move and before the evidence freeze:

- The complete workbench unit-test suite.
- The 69 matcher tests with `ResourceWarning` treated as an error.
- Bundle validation.
- Embedding self-test as an index-integrity check.
- The official three-image harness as a contract smoke test.
- OpenAPI parity.
- Web UI build and smoke tests.
- Database and file-store referential checks.
- A test-to-catalogue exact-byte leakage check.
- A check that README metric values match saved JSON artifacts.

Do not present the embedding self-test as external recognition accuracy.
Do not present the three public evaluator images as an accuracy benchmark.

## Work that should not run tonight

Do not restart the 54-profile by 5-test-set matrix.
It has low presentation value and the earlier queue stopped after 57 of 270 runs.

Do not repeat these completed studies:

- The broad embedding-model sweep.
- The barcode decoder variant sweep.
- The cached bulk worker sweep.
- The raw label-tower mean fusion.
- DINOv3 profiles.
- Local profiles that failed the memory gate.

Do not tune reranker rules before the annotation audit.
The current hard-set analysis shows that conflicting labels and duplicate catalogue cards can dominate the apparent result.

## Morning outputs

Store raw JSONL, manifests, logs, and generated tables under one new report directory.
Keep failed observations in all applicable denominators.

Use the results in the presentation as follows:

- Slide 8: the four-stage ablation on one frozen snapshot.
- Slide 9: reranker wins, losses, and the hard-set limitation.
- Slide 10: code-path gain and coverage. Remove the isolated 0.2-second claim unless the final HTTP test supports it.
- Metrics slide: final R@1, R@5, confidence interval, independent-set result, and exact denominator.
- Latency slide: sequential HTTP p50 and p95, first-request latency, and the share within 3 seconds.

Update the root README with these sections:

- Benchmark dataset and snapshot.
- Released matcher result.
- Best research pipeline result.
- Controlled ablation.
- Evaluator-path latency.
- No-match behavior.
- Reproducibility and limitations.

Keep the released matcher and the research pipeline in separate rows.
Do not replace the README headline with 85.12% until the final snapshot, paired analysis, and independent-set caveat are complete.
