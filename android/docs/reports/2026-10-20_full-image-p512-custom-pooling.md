# Full-image Base p512 custom pooling on Pixel 8

Date: 2026-10-20.
Status: complete at 16:11:35 MSK. Fresh audit verified at 16:20 MSK.
Both full 668-assignment runs passed. The standard control reproduced every production Top-1 prediction.

## Final comparison

All scores use the same 668 `my-failed-2` assignments and accepted alternative slugs.
Keep segmentation failures in the denominator. Re-ranking and barcode remain disabled.

| Pipeline | Top-1 | Top-5 | Top-10 | Median, ms | P95, ms | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Current default: full-image p512 standard, repeated control | 41.02% | 77.84% | 84.58% | 878 | 1252 | 0 |
| Full-image p512 custom, matched custom references | 38.92% | 77.54% | 84.43% | 1554 | 3002 | 2 |
| Prior cropped/white p512 custom, same custom references | 36.98% | 68.86% | 73.95% | 1769 | 2428 | 2 |

Full-image custom has 260 Top-1 hits. The control has 274. Cropped custom has 247.
Full-image custom gains 1.95 percentage points over cropped custom.
Its Top-5/10 gains over cropped custom are 8.68/10.48 percentage points.
The paired Top-1 comparison has 69 gains and 56 regressions against cropped custom.
Full-image custom loses 2.10 Top-1 percentage points against the default.
The paired Top-1 comparison has 61 gains and 75 regressions against the default.
Its observed median latency is 1.77 times the repeated control latency.
Its P95 is worse than both alternatives. Do not infer a universal latency ratio.

Keep standard p512 without segmentation as the Pixel 8 default.
Full-image custom improves the prior custom pipeline but does not replace the default.
These are whole-pipeline comparisons. Control and custom use different reference indexes.
The new full-image pipeline also repairs source-colour and alpha decoding.
Do not attribute the entire difference from the prior cropped pipeline to cropping alone.
This failure-focused cohort is not the full `my` test set.

Both full runs retained Pixel PID 21332. Maximum sampled thermal status was 1 in both runs.
Peak sampled PSS was 1181936 KiB for control and 1139110 KiB for custom.
Custom retained two no-bottle errors: q-000040 and q-000394.
The experiment did not substitute a full-image fallback for those errors.
No process restart, invalid vector, or unexpected inference error occurred.
Cleanup disabled HTTP and stopped the isolated process. The controller exited.
No production model, setting, pack, or default changed.

Fresh read-only recalculation exactly matches both saved independent audits.
The control-agreement record confirms 668/668 identical production Top-1 predictions.
Evidence under the artifact root:

- `comparison-v2/condition-5-full/production-control-agreement.json`.
- `comparison-v2/condition-5-full/predictions.jsonl`.
- `comparison-v2/condition-6-full/predictions.jsonl`.
- `comparison-v2/comparison.json` and `comparison-v2/status.json`.
- `final-status-audit-20261020-1620.json`.

## Historical repaired device checkpoint at 15:35 MSK

Both five-image GPU/CPU/GPU gates passed without an inference error.
The standard condition passed 165 checks. The custom condition passed 145 checks.
All four previously differing ICC/alpha inputs now reproduce production Top-20 rankings.
All 30 standard production-vector and production-ranking checks passed.
Minimum desktop/device cosine is 0.9999999999515934 for standard and 0.9999999999199387 for custom.
Maximum component error is 0.000002325 for standard and 0.000001878 for custom.
Both raw-RGB preprocessing checks and full-source pixel-preservation checks passed.
This controlled replay confirms that the repaired decoder removes the observed parity failures.
The full 668-query identity check remains required.

Both independent 30-image pilots passed. Each pilot retained all 30 assignments.
Standard median/P95 is 906/1156 ms. Custom median/P95 is 1338/1923 ms.
Do not treat pilot timing or quality as a complete-cohort result.
Full standard has saved 8/668 assignments without errors.
Full custom follows exact standard-control agreement and cooling.
The finite detached controller is PID 42579 with parent PID 1.
Pixel PID remains 21332. The latest battery temperature is 34.0 C. Thermal status is 0.
Allow about 35-50 more minutes for both full runs, audits, and cooling.
Keep the Pixel connected. Do not start a duplicate runner or change the frozen sources.

## Authorized decoder repair and v2 attempt

The owner authorized repair and resumption at 15:26 MSK.
The isolated decoder now matches production source-colour and alpha handling.
The decoder requests source colour space, software allocation, and unpremultiplied RGB.
It discards alpha without compositing. It does not resize the complete source image.
The legacy cropped decoder and production code remain unchanged.
Raw RGB captures replace PNG display conversion as the preprocessing oracle.
The new GPU/CPU/GPU gate includes all four affected inputs and one opaque control.
Require all 668 standard Top-1 predictions to reproduce production before full custom inference.

All 29 host tests and 25 Android tests passed. Debug build and lint passed.
API 28 signature verification and 16-KiB ZIP alignment passed.
Isolated test version: `0.1.3-full-image-p512-pooling`.
APK SHA-256: `6effa272d90c4ab6e2b0214b22472566ac42f7108d471433da603b1efc44083a`.
All models, indexes, pack, queries, and accepted alternatives remain byte-identical.
The production pack still has SHA-256 `4307a92be20fc53bec18f922ae80b60d92fc219c2a8e22f981f8c8778117a128`.
The workflow verified the exact installed v1 APK and every private pack file before updating.
No application data was cleared. All stopped v1 artifacts remain unchanged.

New frozen sources: `source-snapshot-v2/` in the same artifact root.
Workflow: `comparison-workflow-v2/workflow.json`. Progress: `comparison-v2/status.json`.
Build evidence: `build-record-v2.json` and `artifact-verification-v2.json`.
Re-ranking and barcode stay disabled. The production default remains unchanged.

## Historical stopped v1 checkpoint at 15:06 MSK

The first attempt stopped at the full-control identity gate at 14:17:49 MSK.
Its full custom run did not start.

## Control identity failure

The repeated standard control completed all 668 requests without an HTTP error.
Its independent accuracy audit passed. A fresh read-only audit matches the saved audit.
Its Top-1 is 272/668, or 40.72%, versus 274/668, or 41.02%, in the production control.
Top-5 remains 77.84%. Top-10 remains 84.58%.
Its median/P95 is 951/1482 ms. These values are not a validated default replacement.
Four Top-1 predictions differ: q-000029, q-000171, q-000380, and q-000567.
The last two differences are regressions. The first two remain incorrect in both runs.
Top-20 order differs on 36 assignments. The exact-control safeguard correctly stopped the campaign.

Source inspection identifies two decoder differences.
The test forces sRGB. The production full-resolution loader retains the source colour space.
The test uses ordinary alpha decoding and copies the bitmap.
The production loader requests unpremultiplied RGB and discards alpha without compositing.
All four Top-1 mismatches have embedded colour profiles. Three are RGBA PNG files.
All 601 unprofiled RGB assignments retain Top-1 and have score error below 0.000002244.
Source and metadata evidence points to colour and alpha preparation, not GPU instability.
A controlled device replay of the affected inputs is still required to confirm the fix.
The three parity inputs did not cover these colour and alpha cases.

No process restart or native abort occurred. Pixel PID 24041 remained stable during control.
Cleanup switched HTTP off and stopped the isolated process. The controller has exited.
Re-ranking remained disabled. The production application and all saved artifacts remain unchanged.

The recommended next step is to match the production loader in the test application.
Add the affected colour and alpha inputs to parity checks before another full run.
Preserve this attempt. Rebuild and rerun only into new source and result directories.
Do not weaken the control-agreement gate or publish a final custom quality value.
No test source or device setting changed during this status request.
Evidence: `status-audit-20261020-1506.json` and `comparison-v1/status.json` in the artifact root.

## Historical checkpoint at 14:11 MSK

The full control had saved 384 of 668 assignments with zero errors.
The full custom run had not started. Both numerical gates and pilots passed.
The isolated device workflow started at 13:59 MSK.
Complete-cohort quality and latency remain pending.

The detached controller is alive. Pixel PID remains 24041.
The latest temperature is 38.7 C. Thermal status is 1.
The latest 50 control requests average 1041 ms before additional host telemetry overhead.
Allow about 25-35 more minutes for the remaining control, custom run, cooling, and audit.
The full-image custom pilot median/P95 remains 1321/2164 ms.
Do not present these pilot timings as full-cohort results.

## Initial device checkpoint at 14:04 MSK

The standard condition passed 99 numerical checks. The custom condition passed 87 checks.
Both checks preserve full-source dimensions and pixel hashes before NaFlex preprocessing.
Both use the same complete source image, not the bottle crop or a white-background image.
Standard minimum desktop/device cosine is 0.9999999999651046.
Custom minimum desktop/device cosine is 0.9999999999258525.
Maximum component errors are 0.000001997 and 0.000001907, respectively.
The standard capture checks reproduce the original production vector and Top-20 order.

Both independent 30-image smoothness pilots passed without request errors.
Standard median/P95 is 888/1302 ms. Custom median/P95 is 1321/2164 ms.
These pilot values are not full-run latency or complete-cohort quality.
At 14:04 MSK, the full standard run has saved 69 of 668 assignments with zero errors.
The full custom run follows the standard audit and cooling.
Both use Pixel PID 24041. The finite detached controller is PID 11338, with parent PID 1.
Allow about 30-40 more minutes, subject to latency, cooling, and audit.
Do not restart the worker or edit the frozen runtime snapshot.

## Owner-selected experiment

Keep the original full query image. Do not crop, whiten, rotate, or remove its background.
Use the mobile bottle mask only for fractional attention-pooling weights.
Use whitespace weight 0.1 and bottle weight 1.0.
Keep the matched custom reference index from the previous experiment unchanged.
The owner selected this reference policy at 13:50 MSK.
The current production standard index remains the control.
Read [the plan](../plans/09_full-image-p512-custom-pooling.md).

Condition 5 is full-image standard pooling without segmentation.
Condition 6 is full-image custom pooling with the CPU mobile bottle mask.
Both conditions use the complete Base p512 encoder on GPU for quality measurement.
Both use the same frozen 668 `my-failed-2` assignments and accepted alternative slugs.
Keep detection errors in the denominator. Do not add a fallback in this experiment.
Re-ranking, barcode, label fusion, and response caches remain disabled.
The production app and its default pipeline remain unchanged.

## Verified preparation

- 27 host tests passed.
- 23 Android tests passed. No failure, error, or skipped test was recorded.
- Debug build and lint passed. Lint retains warnings, not errors.
- API 28 signature verification and 16-KiB ZIP alignment passed.
- The new application ID is `com.alolalab.chtozavino.fullpoolbench`.
- The version is `0.1.2-full-image-p512-pooling`.
- The new pack contains 395,549,549 payload bytes.
- Production reference vector bytes are unchanged.
- Previous custom reference vector bytes are unchanged.
- The frozen runtime snapshot contains 91 source files.

| Artifact | SHA-256 |
| --- | --- |
| Isolated APK | `32250ff7354d6fdb71b336117abd1847ce9abbf632d18cf36257ff5e55ed1327` |
| Pack manifest | `9bf4a3baa655cc77d6873cf8a49aa6e5295a745ea36f33784dff98e0dbeb1157` |
| Original production pack | `4307a92be20fc53bec18f922ae80b60d92fc219c2a8e22f981f8c8778117a128` |
| Frozen query manifest | `1b8fb97a08b08fe8d9c7a422c142e316e5f853cd827219236ca5504840cce93a` |

## Device gates

The finite workflow verifies the new package's default-off HTTP state.
It requires user 0, unlocked setup, and cooling before each block.
It runs three original images in GPU, CPU, and GPU blocks for each condition.
The host checks full-source dimensions and pixel preservation.
It checks captured patch pixels against the released NaFlex preprocessor.
It checks fractional mask coverage, identical-input vectors, and all reference scores.
The control must reproduce the original production vectors and candidate ordering.
Both conditions must pass 30-image smoothness pilots before their full runs.
The new full control must reproduce all 668 original Top-1 predictions.
The workflow must disable HTTP and stop only the isolated app during cleanup.

## Comparison limits

The new custom condition retains a custom reference index.
The standard control retains the production standard reference index.
This is a complete-pipeline comparison. It is not a query-pooling-only comparison.
The repeated control runs in the isolated test runtime with the same model and reference bytes.
It is not a second execution of the production APK itself.
Shared full-image frame staging can change overhead relative to the earlier production timing.
Compare the full-image custom result with the previous cropped custom result separately.
The two custom conditions use the same reference-vector bytes.
Report thermal conditions with latency. Do not infer a causal speed gain from run order.
Do not select a new application default before complete results pass their audits.

## Evidence

Artifact root:
`/Volumes/Storage/svoe-vino-final/artifacts/android-full-image-p512-pooling-20261020/`.

- `build-record-v1.json`: APK, source, pack, production pack, and test identities.
- `source-snapshot-v1/`: frozen host and device sources.
- `apk-v1/`: preserved isolated APK.
- `device-pack-v1/`: verified p512 model pack and reference indexes.
- `android-build-v1.log`: successful build, tests, and lint.
- `host-tests-final.log`: the 27 host test results.
- `comparison-workflow-v1/workflow.json`: finite comparison configuration.
- `comparison-workflow-v1/detached-launch.json`: standalone process identity and command.
- `comparison-workflow-v1/workflow.log`: workflow output.
- `comparison-workflow-v1/workflow-errors.log`: diagnostic output.
- `comparison-v1/status.json`: current device-test state.
- `comparison-v1/condition-N-full/predictions.jsonl`: per-condition predictions when present.
- `comparison-v1/comparison.json` and `report.md`: final audited results when present.
