# Base NaFlex p224 and p512 custom pooling on Android

Date: 2026-10-20.
Status: complete. All four full runs passed independent audits.

## Pixel 8 default recommendation

Recommendation recorded on 2026-10-20 after comparison with the existing application control.
Keep complete Base NaFlex p512, standard pooling, no query segmentation, and GPU as the default.
This is a recommendation. No application code, model pack, or device setting changed.

The [existing no-segmentation control](2026-10-19_pixel8-my-failed2-offline-control.md)
uses the same 668 assignments and accepted alternatives.
Its query manifest is byte-identical to the four-condition query manifest.
A fresh read-only calculation reproduces 274, 520, and 565 Top-1/5/10 hits.

| Pixel 8 pipeline | Top-1 | Top-5 | Top-10 | Client median | Client P95 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Existing p512 standard, no segmentation | 41.02% | 77.84% | 84.58% | 662 ms | 956 ms |
| Experimental p512 custom, mobile bottle crop | 36.98% | 68.86% | 73.95% | 1769 ms | 2428 ms |

The no-segmentation control adds 27 Top-1 hits, or 4.04 percentage points.
Its measured median is about 2.7 times shorter. It has zero segmentation errors.
These results compare complete pipelines. They do not isolate the pooling operation.
The query preparation, model integration, and reference preparation differ.
Do not infer that custom pooling alone causes the lower quality.

The p512 custom condition remains the quality leader only among the four segmented conditions.
Retain that condition as an experiment. Do not promote it to the application default.
The optional dual-GPU DIS study improves full `my` Top-1 but adds latency and memory.
It is not a direct test of the new custom-pooling pipeline.

## Final comparison

The comparison finished at 13:08:34 MSK on 2026-10-20.
All four conditions passed 60 numerical checks and their 30-image smoothness pilots.
All four full runs passed independent audits of 668 assignments each.
A fresh read-only audit at 13:33 MSK matches every saved full-run audit.
All 2,672 prediction records remain saved in separate condition directories.
All conditions use the same 2,093-wine catalogue and accepted alternative slugs.
All scores use `my-failed-2`. These scores are not full `my` scores.
Each run counts the same two no-bottle failures in its denominator.

| Full run | Top-1 | Top-5 | Top-10 | Client median | Client P95 | Top-1 hits |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| p224 standard | 27.84% | 57.78% | 63.92% | 1383 ms | 1748 ms | 186 |
| p224 fractional-bg010 | 28.44% | 57.78% | 66.17% | 1366 ms | 2073 ms | 190 |
| p512 standard | 33.83% | 66.32% | 70.51% | 2283 ms | 3215 ms | 226 |
| p512 fractional-bg010 | 36.98% | 68.86% | 73.95% | 1769 ms | 2428 ms | 247 |

Custom pooling uses fractional bottle coverage with whitespace weight 0.1 and bottle weight 1.0.
It changes only the attention-pooling log weights. It uses one query encoder pass.

At p224, custom pooling adds 0.60 percentage points Top-1 and 2.25 points Top-10.
Top-5 is unchanged. The paired Top-1 comparison has 30 gains and 26 regressions.
Its median is similar to standard, but its P95 is higher.

At p512, custom pooling adds 3.14 percentage points Top-1 and 3.44 points Top-10.
Top-5 increases by 2.54 points. The paired Top-1 comparison has 37 gains and 16 regressions.
Compared with p224 custom, p512 custom adds 8.53 points Top-1.
Its measured median is about 30% longer than the p224 custom median.

The measured p512 custom median is 22.5% shorter than the p512 standard median.
The measured P95 is 24.5% shorter.
Do not interpret this difference as an isolated pooling speed improvement.
The runs were sequential. The p512 standard run reached thermal status 3.
The p512 custom run reached thermal status 1. Cooling conditions differed.
The 30-image pilot medians were 1310 ms for p512 standard and 1395 ms for p512 custom.
An interleaved repeat under matched thermal conditions is required for a causal speed claim.

| Full run | Maximum thermal status | Peak sampled PSS, KiB |
| --- | ---: | ---: |
| p224 standard | 1 | 946508 |
| p224 fractional-bg010 | 1 | 776563 |
| p512 standard | 3 | 944996 |
| p512 fractional-bg010 | 1 | 931832 |

The same Pixel PID 16862 completed all four full runs without a process restart.
The final cleanup disabled HTTP and stopped only the isolated test application.
Re-ranking and barcode recognition remained disabled.
The production application and its p512 no-segmentation default remain unchanged.

p512 custom is the quality leader in this four-condition experiment.
This result supports further testing. It does not establish a win over the production pipeline.
Read the frozen `comparison-v3/report.md` and `comparison-v3/comparison.json` under the artifact root.
Read `comparison-v3/condition-N-full/predictions.jsonl` for each condition's predictions.

## Historical checkpoint at 12:58 MSK

The p512 standard full run is complete. Its independent audit passed all 668 assignments.
The p512 custom full run has saved 403 of 668 assignments. Its final results are pending.
The same Pixel process, PID 16862, remains active. Both host controllers are alive.
No model, settings, production application, or measurement script changed during this check.

| Audited full run | Top-1 | Top-5 | Top-10 | Client median | Client P95 |
| --- | ---: | ---: | ---: | ---: | ---: |
| p224 standard | 27.84% | 57.78% | 63.92% | 1383 ms | 1748 ms |
| p224 fractional-bg010 | 28.44% | 57.78% | 66.17% | 1366 ms | 2073 ms |
| p512 standard | 33.83% | 66.32% | 70.51% | 2283 ms | 3215 ms |

All results use `my-failed-2`, not full `my`.
All completed full runs count the same two no-bottle failures in the 668-assignment denominator.
Re-ranking and barcode recognition remain disabled.

The p512 standard Top-1 exceeds p224 standard by 5.99 percentage points, or 40 hits.
The measured p512 standard median is 65% longer than the p224 standard median.
The p512 standard maximum thermal status is 3. Both p224 maximum thermal statuses are 1.
These are observed sequential-run latencies. Do not attribute all latency changes to pooling.
The custom p224 Top-1 gain is 0.60 percentage points, with 30 gains and 26 regressions.
Its median is similar to standard. Its P95 is higher, 2073 versus 1748 ms.
Do not select a final four-condition winner before p512 custom completes and passes audit.

The p512 custom recent 50-request mean is 1758 ms.
Its latest sampled temperature is 38.8 C and thermal status is 1.
The current estimate is 9-12 more minutes, including observed request overhead and audit.
Allow more time if request latency or thermal conditions change.

## Historical checkpoint at 12:32 MSK

All four conditions passed 60 numerical checks each.
All four conditions passed their independent 30-image smoothness pilots.
Both p224 full runs passed independent audits of all 668 assignments.
The full p512 standard run has saved 617 of 668 assignments.
The p512 custom full run is queued after p512 standard and cooling.
The host workflow and comparison controller remain alive. Pixel PID remains 16862.
Re-ranking and barcode recognition remain disabled. The production default is unchanged.

| Completed full run | Top-1 | Top-5 | Top-10 | Client median | Client P95 | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| p224 standard | 27.84% | 57.78% | 63.92% | 1383 ms | 1748 ms | 2 |
| p224 fractional-bg010 | 28.44% | 57.78% | 66.17% | 1366 ms | 2073 ms | 2 |

Custom p224 pooling adds 4 Top-1 hits and 15 Top-10 hits.
The changes are +0.60 and +2.25 percentage points. Top-5 is unchanged.
These are `my-failed-2` scores. They are not full `my` scores.
The two no-bottle failures remain in each full denominator at q-000040 and q-000394.
Do not select the final production pipeline before both p512 runs finish.

The p512 standard pilot median is 1310 ms. Its P95 is 1636 ms.
The p512 custom pilot median is 1395 ms. Its P95 is 1787 ms.
These pilot timings are not sustained full-run timings.
The latest 50 p512 standard requests average 2848 ms.
The latest sampled battery temperature is 44.7 C. Thermal status is 3.
The critical stop threshold is 4. The next run requires cooling to at most 40 C.
Allow about 30-40 more active test minutes, plus cooling and audit.
Cooling duration is not established. Do not guarantee a wall-clock completion time.

## Historical checkpoint at 11:21 MSK

p224 standard passed all 60 numerical checks.
Its 30-image pilot has saved 21 responses without errors.
The observed client mean is 1329 ms. The observed client median is 1276 ms.
These partial pilot timings are not the final audit or a measured p512 estimate.
Conditions 2-4 remain queued. Re-ranking and barcode remain disabled.

Historical checkpoint at 11:20 MSK: the isolated Base device comparison has started.
Condition 1, p224 standard, started device execution at 11:18:05 MSK.
All 9 GPU/CPU/GPU parity requests completed without request errors.
The host numerical validator is active. Numerical agreement remains unconfirmed.
Conditions 2-4 are queued. No 30-image pilot or full Base run has started.
The device PID is 16862. Last sampled temperature is 39.4 C and thermal status is 1.
Re-ranking and barcode remain disabled. The production application remains unchanged.

A measured completion estimate requires the independent 30-image pilots.
At an assumed mean of 2-3 seconds per image, four full runs need 89-134 compute minutes.
Allow additional time for numerical validation, pilots, audit, and cooling.
This estimate is conditional. The p512 device latency is not measured yet.
Do not use parity capture timings as production latency.

Historical checkpoint at 11:15 MSK: full v4 completed all 668 assignments at 11:00:08 MSK.
The independent audit and cleanup passed. Both no-bottle failures remain counted.
The detached workflow started `comparison-v3` at 11:00:22 MSK.
The comparison waits for cooling before installation. Battery temperature is 40.4 C.
Thermal status is 1. The start gate requires at most 40 C and thermal status at most 2.
No pooling device measurement has started. Re-ranking and barcode recognition remain off.
Read the [recovery record](2026-10-20_pixel-benchmark-recovery.md).

## Runtime status at 08:58 MSK

The preceding full-v3 run stopped saving responses at 04:34 MSK.
It saved 536 of 668 assignments in each of its ten prediction files.
Two assignments have no-bottle failures. No transport retry is recorded.
The host runner and both host coordinators are absent.
The cause of host termination is not established.
The Pixel app remains alive with PID 9424. Its HTTP health is OK and idle.
The four-condition comparison has not started. Its saved waiting state is stale.

The remaining 132 assignments need about 81 compute minutes at the last measured rate.
The rate is 36.65 seconds per assignment over the last 50 saved responses.
The new comparison must then wait for an audit, setup, and cooling to at most 40 C.
No restart occurred during this status check.
Preserve the raw interrupted files. Prepare and audit a recovery copy before a continuation.
The normal audit needs missing final metadata because the host cleanup did not run.

## Owner decisions

- Use `max_num_patches=224`. Preserve image proportions.
- Compare standard and custom pooling at both p224 and p512 budgets.
- Use a separate experiment. Do not interrupt the existing Pixel full-v3 benchmark.
- Keep the production p512 default until device results support a change.

Read the [implementation plan](../plans/07_base-naflex-p224-custom-pooling.md)
and the [tool instructions](../../tools/base_p224_experiment/README.md).

## Selected candidate

Use `google/siglip2-base-patch16-naflex` at revision
`b53b807d3a2d5e2b3911292f2d69e5341cdc064c`.
Use patch size 16, at most 224 patches, and 768 output dimensions.
Use one mobile bottle mask and one encoder pass.
Use the fractional `5a` profile from the
[source report](http://127.0.0.1:59998/complete-report-20261018/report.html).

Calculate bottle coverage `f` for each actual image patch.
Set `weight = 0.1 * (1 - f) + f`.
Add `log(weight)` to the original attention-pooling logits.
Preserve valid-patch masking, the transformer, LayerNorm, MLP, and output normalization.
Do not treat padding or a white label as background.

This candidate limits Android work to one query embedding.
The nonzero background weight retains some context when the mobile mask is imperfect.
This is an engineering selection for measurement, not a measured quality winner.
The source report uses SO400M and desktop masks. Its accuracy is not an Android result.

## Paired conditions

| Condition | Budget | Pooling | Query encoder passes |
| --- | ---: | --- | ---: |
| `base-p224-standard` | 224 | Standard attention | 1 |
| `base-p224-fractional-bg010` | 224 | Fractional whitespace 0.1; bottle 1.0 | 1 |
| `base-p512-standard` | 512 | Standard attention | 1 |
| `base-p512-fractional-bg010` | 512 | Fractional whitespace 0.1; bottle 1.0 | 1 |

The owner added the fourth condition at 01:25 MSK.
The fourth condition uses its own p512 complete graph and its own matching index.
The other three index files remain byte-identical to v1.

All conditions use the same 2,093 wines and the same original catalogue alpha cuts.
Each condition has one unrotated reference per wine and a separate matching index.
The original reference alpha supplies reference bottle coverage.
The on-device catalogue-trained YOLO11n segmenter supplies query bottle coverage on CPU.
The query crop uses zero rotation and margin 0.04.
No label boost, label fusion, rotation, reference augmentation, or re-ranking runs.
Barcode, OCR, and VLM inference remain disabled.
No query mask or accepted answer goes to Android.
Segmentation failures do not use a full-image fallback.

The production p512 no-segmentation baseline has a different query preparation policy.
Use that baseline only as context. Do not attribute its difference to pooling alone.

## Completed initial v1 host gates

- The original p224 graph and the modified graph use identical FP16 weight payloads.
- Four synthetic inputs have zero output error with zero log bias.
- The independent NumPy attention oracle has maximum error below `0.00000004`.
- Modified padding bias has zero output effect on all four synthetic inputs.
- All 6,279 reference vectors are finite and normalized.
- All nine captured-input CPU/Metal reference checks pass the fixed numerical gates.
- The 16 Python tests pass. They cover mask weights, profile identity, accepted alternatives,
  failure denominators, partial-run rejection, paired comparisons, and prerequisite cleanup.
- The 17 Android unit tests pass. They cover coverage, accelerator options, foreground-service
  declarations, condition budgets, custom-pooling identity, and empty-mask rejection.

| Condition | References | Minimum CPU/Metal cosine | Maximum component error |
| --- | ---: | ---: | ---: |
| p224 standard | 2,093 | 0.999999999622 | 0.000003228 |
| p224 custom | 2,093 | 0.999999999834 | 0.000002557 |
| p512 standard | 2,093 | 0.999999999894 | 0.000002146 |

These checks compare the same deployed FP16 weights.
They do not measure FP32-source-to-FP16 quantization loss.
Metal timings are host preparation times. They are not Pixel latency measurements.

## Four-condition v2 extension

The p512 custom graph preserves all original FP16 weight payload bytes.
All four synthetic p512 cases have zero error for zero bias and for excluded padding.
The independent p512 attention oracle has maximum error below `0.000000019`.
The 19 Python tests and 19 Android tests pass. Debug lint has no errors.
The tests cover both budgets, all four identities, and all six paired comparisons.

The new p512 custom index uses the same 2,093 reference cuts.
The three v1 indexes remain unchanged. Do not rebuild or replace them to improve a score.
All 8,372 vectors are finite and normalized. All 12 CPU/Metal checks pass.
The three new p512 custom checks have minimum cosine `0.999999999906`.
Their maximum component error is `0.000002414`.
Each of the four conditions must pass its own device numerical and 30-image pilot gates.
The final report must compare standard with custom pooling at each budget.
The final report must also compare p224 with p512 for each pooling type.

## Device protocol and pending results

The separate application ID is `com.alolalab.chtozavino.basepoolbench`.
The HTTP switch is off on first launch.
The test application uses a private foreground service while HTTP runs.
The production application and the installed full-v3 benchmark remain unchanged.

The initial v1 comparison entered `waiting-for-existing-full-benchmark` at 01:24 MSK.
The owner extended the scope at 01:25 MSK.
Only waiting host coordinator 31107 was stopped. No device request or installation occurred.
The v1 APK, pack, indexes, source snapshot, and status remain preserved.
The four-condition v2 coordinator must use a new frozen source snapshot.
The v2 coordinator started at 01:32 MSK with `source-snapshot-v2/`.
Its host PID is 51249. Its exec session is 55599.
Its state is `waiting-for-existing-full-benchmark`.
At this checkpoint, full v3 has 243 saved assignments and one retained segmentation error.
The old PID remains 9424. All inherited prefixes remain byte-identical.
No new APK is installed.
At this checkpoint, full v3 has 228 saved assignments and one retained segmentation error.
All inherited 44-row prefixes remain byte-identical. No new APK was installed.

Wait for full v3 to finish and pass its independent audit and cleanup.
Stop the new comparison if that prerequisite fails.
Then require thermal status at most MODERATE and battery temperature at most 40 C.
Run three images in GPU, CPU, and GPU blocks for each condition.
Check captured tensors, fractional mask coverage, vector agreement, and all reference scores.
Require cosine at least 0.99999 and maximum component error at most 0.001.

Run 30 frozen distinct images after the numerical gate.
Select the images by evenly spaced source identities, not by correctness.
Measure each condition independently after one untimed warmup.
Require client median at most 3 seconds, P95 at most 5 seconds, and maximum at most 10 seconds.
Record PSS, thermal status, logcat, process identity, and every transport attempt.
Run all 668 `my-failed-2` assignments only for conditions that pass.
Count every segmentation failure in the quality denominator.
Accept every frozen alternative slug.

Top-1, Top-5, Top-10, Pixel latency, Pixel PSS, and heat remain pending.
Do not select a production winner from the completed host checks.

## Evidence

Artifact root:
`/Volumes/Storage/svoe-vino-final/artifacts/android-base-p224-pooling-20261020/`.

- `report-source/`: the source HTML, JSON, selected legend, and source checksums.
- `inputs/inputs.json`: verified reference inputs and frozen host-only query identity.
- `models/validation.json`: graph-rewrite and independent attention checks.
- `references-v1/references.json`: all three index identities and CPU/Metal checks.
- `references-v2/references.json`: all four index identities and the v1 reuse checks.
- `device-pack-v1/manifest.json`: the model pack and every payload checksum.
- `device-pack-v2/manifest.json`: the four-condition pack with both numerical reports.
- `models/validation-p512.json`: the p512 graph-rewrite and attention-oracle checks.
- `android-build-v*.log`: preserved build attempts and fixes.
- `host-tests-v1.log`: the 16 host test results.
- `host-tests-final.log`: the final 16 host test results.
- `build-record.json`: the frozen APK, source, pack, AAR, and test identities.
- `build-record-v2.json`: the four-condition APK, source, pack, AAR, and test identities.
- `old-benchmark-preservation.json`: the original benchmark preservation check.
- `comparison-v1/status.json`: the preserved superseded queue state. No device predictions exist.
- `comparison-v1/superseded.json`: the owner-authorized queue replacement reason.
- `comparison-v2/status.json`: the replacement four-condition comparison state.
- `comparison-v2/condition-N-full/predictions.jsonl`: future four-condition predictions.
- `comparison-v2/comparison.json` and `report.md`: future audited four-condition results.

The preserved v1 pack has 401,979,292 payload bytes before its root manifest.
The four-condition v2 pack has 593,548,758 payload bytes before its root manifest.
These packs contain experiment controls. Neither pack is a new production bundle.

Key SHA-256 identities:

| Artifact | SHA-256 |
| --- | --- |
| Frozen Base experiment APK | `21231c8467869aa9294678989c3696fb1b742c1aadf9ef94f06262cfa50cc566` |
| Frozen four-condition APK v2 | `7ed834e5022de84af472e88d2985d8220fc708a81a707d9402b8582694893ad5` |
| Source p224 graph | `9e59bae912daa597dcce9830cdc966cd1b18455d6e8034d46cb9e84ad0b18441` |
| Modified p224 graph | `c0371d2c6825642a6f2e1d782e7d3c202d72c0908cbb7320045aeb2fa31fd097` |
| Standard p512 graph | `9cd7a00df9818bebe9e505e7a84647334587f88101300dd14b4bce1e39165005` |
| Modified p512 graph | `6d626149ec6460ef3c57efd671d75691a7f98628f0d1eddefc8c203f818d5ab7` |
| New comparison pack manifest | `b13a8a3505d88a932b9bc4e056d8411642185163b2484ce0a79522b7f5501e16` |
| Four-condition pack manifest v2 | `8d6e9aee47e2c5ff64595a8d35c268379c2e032d19a92c8cc4d6dc1d1f965c41` |
| Frozen 668-assignment query file | `1b8fb97a08b08fe8d9c7a422c142e316e5f853cd827219236ca5504840cce93a` |
| Source report data | `0674d507b26c1ca9c11d3120df32dd31bf7ed4b7a168d08c1d17618c295006dc` |
