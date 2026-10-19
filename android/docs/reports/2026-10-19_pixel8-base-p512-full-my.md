# Pixel 8 complete Base p512 full my benchmark

Date: 2026-10-19

## Status

The full run is complete.
All 3,409 requests returned HTTP 200 in one application process.
The new pipeline improves positive retrieval and median latency over the fixed
Base/224 plus DIS baseline.
The negative-case result is worse.
The sustained workload also fails the short-pilot thermal gate.
Do not describe this run as an all-gates pass.

Read [the machine-readable results](2026-10-19_pixel8-base-p512-full-my.json).

## Results

Top-k means that at least one accepted wine occurs in the first k candidates.
The denominator is all 2,970 positive assignments, including unavailable catalogue
wines and any request errors.

| Measurement | Fixed Base/224 + DIS baseline | Complete Base NaFlex p512, no segmentation |
| --- | ---: | ---: |
| Top-1 | 988 / 2,970 (33.27%) | 2,052 / 2,970 (69.09%) |
| Top-5 | 1,677 / 2,970 (56.46%) | 2,587 / 2,970 (87.10%) |
| Top-10 | 1,913 / 2,970 (64.41%) | 2,674 / 2,970 (90.03%) |
| Top-20 | 2,107 / 2,970 (70.94%) | 2,714 / 2,970 (91.38%) |
| MRR | 0.4402 | 0.7707 |
| Client median latency | 1,699 ms | 924 ms |
| Client P95 latency | 2,156 ms | 1,479 ms |
| Client maximum latency | 4,684 ms | 5,837 ms |
| Requests within 3 seconds | 3,404 / 3,409 | 3,406 / 3,409 |
| HTTP errors | 5 | 0 |
| Whole-run wall time | 5,986.9 s | 3,300.0 s |

Top-1 increases by 35.82 percentage points.
Top-5 increases by 30.64 percentage points.
Top-10 increases by 25.62 percentage points.
The paired Top-1 comparison has 1,213 gains and 149 losses.
Median client latency decreases by 45.62 percent, or a factor of 1.84.
P95 client latency decreases by 31.40 percent.
The recorded 90-percent Top-1 target is not met.

For the 2,800 catalogue-covered positives, Top-1 is 73.29 percent.
Top-5 is 92.39 percent. Top-10 is 95.50 percent.
The 170 unavailable positives limit full-set recall to 94.28 percent with this pack.
The 2,808-distinct-positive-image view has Top-1 of 68.45 percent, Top-5 of 86.65
percent, and Top-10 of 89.60 percent.
This secondary view keeps the first positive assignment for each image hash.
The main result retains all assignments.

### Negative and no-match cases

The forbidden wine occurs at Top-1 in 73 of 430 negative assignments.
The baseline count is 42 of 430.
This is a regression of 31 cases.
A negative assignment means only that the assigned wine is incorrect.
Another returned wine is not proof of a correct answer.

All 9 no-match queries return a wine instead of rejection.
The baseline also falsely accepted all 9.
This is the unchanged limitation of the current nearest-wine response policy.
The run does not validate an unknown-wine rejection threshold.

## Device and pipeline

- Device: Google Pixel 8, serial `41231FDJH002WZ`.
- Android: 17, SDK 37.
- Application: `chtozavino.alolalab.com`, version `0.2.0`, version code `6`.
- Model pack: `20261019-base-naflex-p512-complete`, format 6.
- Encoder: complete `google/siglip2-base-patch16-naflex`, 512 patches, 768 dimensions.
- Query input: original full image without segmentation.
- Encoder request: GPU, FP32 execution, BUFFER storage, no GPU program cache.
- Matching: maximum cosine across the available catalogue references.
- Catalogue: 2,093 wines and 2,093 reference vectors.
- Barcode: disabled. The debug match endpoint does not run barcode decoding.
- Request endpoint: `/v1/match?k=20&siglip2_accelerator=gpu` through USB forwarding.
- Workers: one. Response caches are disabled.

The model and pack hashes are in
[the integration report](2026-10-19_base-p512-default.md).
The thirty-image pilot and vector parity passed before this full run.
The full run includes the first request with a new model session.

## Frozen query set

The saved query set contains 3,409 assignments and 3,031 distinct image hashes.
It contains 2,970 positive assignments, 430 negative assignments, and 9 no-match queries.
The positive assignments contain 2,808 distinct image hashes.
Keep duplicate assignments. Do not silently deduplicate the benchmark.

The current Workbench accepts every eligible positive wine assignment for the same
image hash as an alternative answer.
There are 152 assignments with more than one accepted slug.
The frozen `queries.jsonl` is identical to the previous fixed Base/224 baseline.
Both files have SHA-256
`9c2c4591e02f3e597dbbd75db2e8565d2dd90fc5cc282f7664eb9f6cf6eefd40`.
The comparison can therefore use all 3,409 assignments directly.
An initial preflight used the older query builder in the Android checkout.
That builder omitted the multi-positive truth expansion.
The apparent 152-record difference was a harness difference, not a dataset change.
The actual run uses the current Workbench query builder and scorer.

The pack contains at least one accepted wine for 2,800 positive assignments.
The other 170 positive assignments have no accepted wine in this pack.
Report the full-set metric and the catalogue-covered subset separately.
Do not change the catalogue or the accepted answers during the run.
No positive query image hash equals a selected reference-cut hash or its frozen
original-source hash.
This byte-hash check does not replace a visual near-duplicate audit.

## Harness and records

The current catalogue database has schema version 36.
The dedicated Android checkout contains the older schema version 32 harness.
The run uses the current shared Workbench harness to read the database without a
migration or another database write.
It saves all run files in the dedicated Android checkout.
The exact harness source and SHA-256 records are saved with the technical artifacts.

Run directory:
`/Volumes/Storage/svoe-vino-final/code/svoe-vino-lab-android/workbench/runs/2026-10-19T084128Z-lab-android-device-match-k20-my-pixel8-p512-complete-no-seg-20261019/`.

Technical artifacts:
`/Volumes/Storage/svoe-vino-final/artifacts/android-full-my-p512-20261019/`.

The run saved `queries.jsonl`, `predictions.jsonl`, and `results.jsonl` incrementally.
The Workbench wrote `metrics.json`, `run.json`, and `summary.md` after completion.
Read [predictions.jsonl](../../../workbench/runs/2026-10-19T084128Z-lab-android-device-match-k20-my-pixel8-p512-complete-no-seg-20261019/predictions.jsonl)
and [the scored results](../../../workbench/runs/2026-10-19T084128Z-lab-android-device-match-k20-my-pixel8-p512-complete-no-seg-20261019/results.jsonl).
All 3,031 distinct input files passed SHA-256 verification.
Every result has the expected query identity and twenty finite candidate scores.
Every candidate slug occurs in the installed pack.
The baseline ranks were independently checked against the same frozen truth.
The JSON report records hashes for the final run files and the exact harness source.
The technical artifacts also contain `paired-changes.jsonl` and `analysis.json`.
The technical records include device metadata, health, app PID, sampled PSS and RSS,
thermal status, and battery temperature.
App logs are restricted to the measured application PID.
The test does not clear system logs or export application history.
The test temporarily kept the USB-powered screen awake.
It restored the original power setting after the run.

## Timing scope

The Workbench measures client wall time for each HTTP call.
The value includes USB transport, device image decoding, preprocessing, inference,
catalogue search, and the response.
Multipart request construction on the host is outside that per-request timer.
The whole-run wall time includes runner overhead.
The run uses one worker so per-request latency is comparable with the previous run.
Sampled process PSS does not measure the complete GPU allocation peak.
The first request, `q-000001`, took 5,837 ms with a new model session.
It was the slowest request.
The other requests above 3 seconds were `q-000188` at 3,327 ms and `q-000813` at
3,271 ms.
The run did not use an unmeasured warm-up request.
The cold-session conditions were not controlled between the two full runs.

## Runtime, memory, and heat

The application PID remained `24675` for all 3,409 requests.
No process restart, native abort, fatal application exception, or CPU fallback was
observed.
A post-run embedding probe confirmed GPU, segmenter `NONE`, and 768 dimensions.
Its normalized vector had norm `0.9999999877900376`.

The test saved 194 telemetry samples at approximately 15-second intervals.
Peak sampled process PSS was 978,120 KiB, or 955.2 MiB.
Battery temperature started at 35.5 degrees Celsius and ended at 43.6 degrees Celsius.
The maximum sampled battery temperature was 45.2 degrees Celsius.
Android thermal status first reached `LIGHT` after 98.7 seconds, `MODERATE` after
665.7 seconds, and `SEVERE` after 1,264.3 seconds.
These times are relative to the first telemetry sample.
The maximum status was `SEVERE` (`3`).
Read [the Android thermal status definitions](https://developer.android.com/ndk/reference/group/thermal).
The long run fails the pilot gate that requires thermal status below `3`.
The thirty-image pilot remained at `NONE`; it did not establish sustained thermal
behavior.
Do not report the short pilot latency as full-run sustained latency.

An independent watcher would stop only the owned coordinator with SIGINT at
`CRITICAL` (`4`) or higher.
The stop condition did not occur.
The watcher did not change thermal limits or disable Android protection.

## Cleanup

The test disabled `HTTP-сервер для тестов` through the application settings.
The health endpoint then stopped accepting connections.
The test removed the ADB port 18088 forwarding rule and its temporary UI dump.
The original `stay_on_while_plugged_in` value `15` was restored and checked.
The application remained in the same process after cleanup.
The test did not export private application preferences or history.
Debug HTTP requests did not create history records.

## Baseline

Previous run:
`2026-10-18T193540Z-lab-android-device-match-k20-my-pixel8-usb-current-patches-20261018`.

The previous run used DIS and fixed Base/224 with the same 2,093 wine cards.
Its positive R@1 was `0.3327`, R@5 was `0.5646`, and R@10 was `0.6441`.
Its positive MRR was `0.4402`.
Its client median latency was 1,699 ms. P95 was 2,156 ms.
Its five HTTP errors came from DIS main-object failures.
The new run changes the encoder and removes query segmentation.
Do not attribute a difference to the encoder alone.
