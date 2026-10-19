# Pixel 8 my-failed-2 control

Date: 2026-10-19
State: Complete control. The ten offline adaptations remain unmeasured.

## Scope

Use the currently installed main application as the control.
Its application ID is `chtozavino.alolalab.com`.
The new-ID APK was not installed during this run.
The application version is `0.2.0`, version code 6.
The device is Pixel 8, serial `41231FDJH002WZ`.
The built-in pack is `20261019-base-naflex-p512-complete`.
It contains 2,093 wines and one reference for each wine.
The encoder is complete Base NaFlex p512 with 768 dimensions.
The query pipeline uses no segmentation and standard pooling.
Reference aggregation is `max`.

The test sent original image bytes to `/v1/debug/embedding?k=20&aggregation=max`.
The endpoint returns the vector, ranked candidates, actual accelerator, and stage times.
Barcode recognition and re-ranking were not used.
No answer slug or query mask was sent to the application.
The host did not cache or replace device predictions.

## Frozen cohort

The cohort is `my-failed-2`.
It contains 668 positive assignments on 627 distinct images.
The query manifest SHA-256 is
`1b8fb97a08b08fe8d9c7a422c142e316e5f853cd827219236ca5504840cce93a`.
Scoring accepts each slug in the frozen `truth` list.
All 668 assignments remain in the denominator.

## Results

| Metric | Value |
| --- | --- |
| Top-1 | 274 / 668 = 41.02% |
| Top-5 | 520 / 668 = 77.84% |
| Top-10 | 565 / 668 = 84.58% |
| HTTP errors | 0 |
| Process restart | 0 |
| Actual embedding accelerator | GPU for all 668 requests |
| Client median | 662.2 ms |
| Client P95 | 956.0 ms |
| Median encoder stage | 460 ms |
| Median search stage | 97 ms |
| Median segmentation stage | 0 ms |
| Bulk wall time | 554.9 s |
| Peak sampled PSS | 952.5 MiB |
| Maximum sampled thermal status | LIGHT |
| Maximum sampled battery temperature | 38.8 C |

Every returned vector had 768 finite values and a valid unit norm.
PID `2961` remained unchanged.
The client timer includes HTTP and vector serialization.
The bulk wall time also includes host checks and telemetry.
PSS samples do not measure every short allocation or all GPU allocations.

## Coverage and comparison limits

The installed catalogue covers 626 of the 668 assignments.
The other 42 assignments cannot match an accepted slug in this pack.
Do not remove those assignments from the primary accuracy denominator.

There are 660 assignments on 619 images shared with the earlier full `my` control.
All 660 retain the same Top-1 prediction.
The remaining eight images were not present in that earlier frozen `my` run.

The requested desktop table uses SO400M p512 and a different reference gallery.
The table also uses SAM3 query segmentation.
These control scores do not isolate the effect of encoder size alone.
Do not describe a later improvement as a segmentation-only gain.
Do not compare this HTTP timing directly with cached desktop score timings.

## Evidence

Artifact directory:
`/Volumes/Storage/svoe-vino-final/artifacts/android-offline-retrieval-variants-20261019/control-base-p512-no-seg/`.

- `run.json`: device, model pack, complete status, counters, and aggregate telemetry.
- `queries.json`: frozen assignment identities and accepted slugs.
- `predictions.jsonl`: 668 evaluator-compatible device predictions.
- `responses.jsonl`: 668 raw responses with vectors and stage times.
- `telemetry.jsonl`: sampled memory, thermal state, and battery temperature.
- `logcat.txt`: application and native error evidence.

Runner: `tools/offline_benchmark/run_control.py`.
The debug HTTP switch was disabled through the application UI after the run.
The test-created ADB forward was removed.
The original power setting was restored.
The temporary UI dump was removed.
The run did not install an APK, change model settings, or clear application data.
