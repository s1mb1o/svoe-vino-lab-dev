# Pixel benchmark recovery

Date: 2026-10-20.
Status at 11:15 MSK: full v4 complete. Pooling comparison waits for cooling.

Full v4 finished at 11:00:08 MSK. The independent audit passed all 668 assignments.
All 536 inherited records remain byte-identical. Both no-bottle failures remain counted.
The continuation retained Pixel PID 9424. Cleanup disabled HTTP and stopped the test app.
Recipes 1 and 3 share the best Top-1 result, 50.15%.
Recipe 3 Top-5 and Top-10 are 80.99% and 83.38%.
Read the frozen full-run report and independent audit in `full-my-failed2-v4/`.

The four-condition workflow started `comparison-v3` at 11:00:22 MSK.
At 11:15 MSK, the comparison waits for cooling before installation.
Battery temperature is 40.4 C. Thermal status is 1.
The start gate requires at most 40 C and thermal status at most 2.
No pooling device measurement has started. No start-time estimate is established.
Re-ranking and barcode recognition remain disabled.

## Historical checkpoint at 10:45 MSK

At this checkpoint, 645 of 668 assignments were saved.
The two no-bottle failures are unchanged. No transport retry or error is recorded.
All host workers are alive. All 536 inherited prediction prefixes remain exact.
The latest 30-request mean is 39.06 seconds. About 15 compute minutes remain.
The updated full-run estimate is about 11:01 MSK.
The pooling comparison remains queued behind audit, cleanup, and cooling.
The latest battery temperature is 44.6 C. Its required start temperature is at most 40 C.

## Preserved evidence

The raw `full-my-failed2-v3` directory is unchanged.
The directory retains 536 response records and 536 records in each prediction file.
The two no-bottle failures remain at `q-000040` and `q-000394`.
No inherited prediction, accepted answer, model, or recipe changed.

Created `full-my-failed2-v3-recovery-v1` as a separate copy.
Derived missing thermal and memory maxima from saved telemetry.
The copy's `finished_at` is its metadata finalization time at 09:28 MSK.
The recovery record states that the actual original host exit time and cause are unknown.
The frozen independent audit passed all 536 assignments.
The frozen resume-prefix function restored all 536 assignments in a dry check.
Every copied prediction prefix remains byte-identical.
All 23 host tests passed.

## Resumed execution

Resumed at assignment 537 into `full-my-failed2-v4` at 09:32:34 MSK.
At 09:35:18 MSK, the continuation has saved 540 of 668 assignments.
All four new assignments completed on their first transport attempt.
The Pixel process remains PID 9424. The model session was not restarted.
The installed APK, private model-pack manifest, queries, and frozen host scripts match.
The encoder uses GPU. The mobile segmenter uses CPU.
Re-ranking and barcode recognition remain disabled.

The finite host workflow uses a separate session and has parent PID 1.
It ignores `SIGHUP`. Its output goes to persistent files.
It has no automatic restart policy and installs no permanent service.
The temporary rejected `launchctl submit` job was removed before device work.

| Process | PID |
| --- | ---: |
| Standalone workflow | 26125 |
| Full-run coordinator | 26171 |
| Full-run HTTP runner | 26172 |
| Android benchmark app | 9424 |

## Next-stage contract recorded at 09:35 MSK

After full v4, require successful completion, independent audit, and cleanup.
The same workflow then starts the frozen four-condition comparison in `comparison-v3`.
The conditions remain p224 standard/custom and p512 standard/custom.
The comparison still requires numerical checks, 30-image pilots, and cooling.
Run full 668-assignment evaluations only for eligible conditions.
Keep the Pixel connected and unlocked for setup.

The full-run completion estimate at that checkpoint was about 10:55 MSK.
The estimate uses the previous 50-request mean of 36.65 seconds.
The pooling comparison starts later, after audit, setup, and cooling.
No fixed comparison start time is guaranteed.

## Artifact paths

Base directory:
`/Volumes/Storage/svoe-vino-final/artifacts/android-offline-retrieval-variants-20261019/`.

- `full-my-failed2-v3/`: unchanged raw interrupted run.
- `full-my-failed2-v3-recovery-v1/recovery-record.json`: inventory and recovery checks.
- `full-my-failed2-v4/variant-NN/predictions.jsonl`: resumed predictions with the full prefix.
- `resume-20261020-v1/workflow.json`: the frozen sequential workflow configuration.
- `resume-20261020-v1/status.json`: the current workflow phase.
- `resume-20261020-v1/workflow.log`: workflow and runner output.
- `resume-20261020-v1/continuation-start-audit.json`: observed new progress and prefix checks.
- `resume-20261020-v1/detached-launch.json`: the actual standalone launcher record.

The configured `job_label` records the rejected temporary submission.
Use `detached-launch.json` and the live PID for execution status.
The comparison output path is
`/Volumes/Storage/svoe-vino-final/artifacts/android-base-p224-pooling-20261020/comparison-v3/`.
