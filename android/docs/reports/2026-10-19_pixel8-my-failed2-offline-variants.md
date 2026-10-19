# Pixel 8 offline retrieval variants

Date: 2026-10-19.
Status: v5 numerical and background gates passed. Full v3 resumed from the audited
44-record v2 prefix at 23:26 MSK. Complete-cohort quality remains pending.

## Scope

The owner requested ten mobile adaptations of frozen desktop retrieval recipes.
The cohort contains 668 positive assignments on 627 distinct images.
The evaluator accepts every slug in each frozen `truth` array.
Re-ranking, barcode recognition, OCR, and VLM inference are disabled.
Original image bytes enter each device request. Answers and query masks do not.
The main application and its model pack remain unchanged.

The device is Google Pixel 8 with Tensor G3, Android 17, and API 37.
The USB serial is `41231FDJH002WZ`. The active Android user is 0.
The isolated package is `com.alolalab.chtozavino.offlinebench`.
The encoder is `google/siglip2-so400m-patch16-naflex` at revision
`cc24074f717b612951c2dead130904ab9b65a81e`.
It uses 512 patches and 1152 dimensions.
The catalogue has 2274 wines in seven FP32 reference galleries.

YOLO11n-seg supplies bottle and label masks on CPU.
The segmenter uses the catalogue-validation-selected epoch-8 checkpoint.
The checkpoint was selected after ten complete training epochs.
Evaluation-image hashes were excluded from segmentation training.
The encoder uses GPU FP32 BUFFER execution with constant-tensor sharing.
GPU source quantization and serialization caches are disabled.
There is no silent CPU fallback.

This pipeline replaces desktop SAM3 query masks with mobile masks.
RGB rendering, soft-mask sampling, prototype-grid geometry, and crop margins also differ.
Do not treat the desktop table scores as measured Android scores.
Read [the preparation report](2026-10-19_pixel8-offline-variant-preparation.md).

## Gates

Candidate v4 passed 18 unit tests and debug lint.
Lint reported zero errors and ten warnings.
The complete GPU/CPU/GPU gate passed 102 numerical checks in PID 13687.
Minimum cosine was 0.9999999993. Maximum encoder component error was 0.00000425.
The gate checks identical captured inputs, pooling weights, and complete bottle scores.

The independent pilot completed 300 requests in 46.38 minutes.
Each recipe processed the same 30 distinct, evenly spaced images.
All 300 requests returned HTTP 200 in PID 13687.
No process restart, invalid vector, or CPU fallback occurred.
Independent verification confirmed every prediction file and every Top-k count.
Each of the ten prediction files contains 30 records.
All 57 requests shared with the interrupted original candidate retained the same Top-1.

Peak sampled pilot PSS was 2173.36 MiB.
Maximum sampled battery temperature was 44.3 C.
Maximum thermal status was `SEVERE`, not `CRITICAL`.
This passes the declared process and critical-heat stopping gate.
It does not establish acceptable production latency or sustained heat.
The phone cooled to `MODERATE` before the complete-cohort run started.
The loaded model process remained unchanged during cooldown.

## Independent latency

These times include query preparation, mobile segmentation, encoding, and matching.
They come from the 30-image mixed-recipe pilot with warm models.
They are not encoder-only times or shared-request incremental times.
The memory and heat measurements cover the shared pilot process.
They are not isolated per-recipe memory measurements.
PSS is sampled process memory. Accelerator memory is not measured separately.

| Recipe | Short description | Encoder passes | Median, seconds | P95, seconds |
| --- | --- | --- | --- | --- |
| 1 | Compact bottle and label fusion; 13 views; Mean-3 | 1-2 | 8.95 | 9.89 |
| 2 | IoU rotation and label fusion; 84 views; Mean-2 | 1-2 | 10.38 | 11.38 |
| 3 | Original and guarded rotation mean; 84 views; label fusion | 2-3 | 13.65 | 15.08 |
| 4 | Original and unrestricted rotation mean; 84 views; label fusion | 2-3 | 13.74 | 14.92 |
| 5 | Compact weighted bottle; guarded rotation; 13 views; Mean-3 | 1 | 4.26 | 5.09 |
| 6 | Original and guarded rotation mean; 84 views; no label fusion | 2 | 9.09 | 10.83 |
| 7 | Asymmetric weights; 72 views; Max; label fusion | 1-2 | 10.10 | 11.51 |
| 8 | Standard pooling; guarded rotation; 13 views; Mean-2 | 1 | 4.09 | 4.76 |
| 9 | Cardinal gallery; 16 views; Mean-3; label fusion | 1-2 | 8.83 | 10.09 |
| 10 | Exact coverage; label weight 3; 16 views; 50/50 fusion | 1-2 | 8.72 | 9.68 |

The segmenter found a bottle in all 30 pilot images.
It found a usable label in 27 images.
An absent label disables label fusion and label boosting.
An absent bottle causes an explicit error. There is no full-image fallback.
Nominal gallery view counts describe the desktop recipes.
Actual reference rows and ownership remain in the frozen pack manifest.

## Foreground-service candidate

The owner approved a separate service candidate after the first full interruption.
Candidate v5 changes the isolated HTTP lifetime only.
All ten encoder, segmentation, geometry, pooling, and native-search source hashes
match candidate v4. Model and reference bytes remain unchanged.
The main application's installed version and update time remain unchanged.

Twenty Android unit tests and seven host tests passed. Lint has no errors.
Device checks passed for default-off startup, Activity recreation, switch shutdown,
the observed notification stop action, and default-off after a test-process stop.
Shutdown after actual GPU/CPU inference also completed model cleanup on its worker.
The service and held wake lock were absent after cleanup.

The repeated GPU/CPU/GPU gate completed all three requests in PID 20524.
All 102 independent numerical checks passed.
Minimum encoder cosine remains 0.9999999993.
Maximum encoder component error remains 0.00000425.
The Activity then moved to the background. `/healthz` reported importance 125.
The thirty-image background gate completed with `variant=all` in 18.49 minutes.
All 30 requests returned HTTP 200. All 300 recipe predictions passed independent audit.
All 68 telemetry samples report the same PID, active protection, and importance 125.
Every Top-1, Top-20 order, and shared candidate score matches the v4 independent pilot.
Maximum sampled thermal status was `MODERATE`. Maximum battery temperature was 43.4 C.
Peak sampled PSS was 2451.03 MiB. This includes model startup.
Its shared timings must not replace the independent v4 latency table above.
No complete v5 hard-set result is available yet.

## Complete cohort

The first full run started at 20:09 MSK on 2026-10-19.
It sends all 668 assignments in frozen order with `variant=all`.
Identical query work is shared only inside one request.
No query embedding is reused between requests.
Full-request latency is not independent per-recipe latency.
The host uses a temporary idle-sleep assertion while the runner is active.
The assertion ends when the runner exits. It does not change persistent power settings.

This attempt stopped after 29 successful requests. Request 30 has no response.
All ten prediction files contain 29 records. This is not a complete accuracy result.
The Activity stopped at 20:24:11 MSK. Android then cached and froze PID 13687.
Android recorded LOW_MEMORY at importance 400 at 20:26:37 MSK.
The last completed request took 97.54 seconds during cached-process compaction.
No application native crash was recorded. The active user remained 0.
Cleanup restored power setting 15 and removed test-created forwarding.
The owner approved a foreground service in the isolated APK before the repeat.
The main application, model pack, and retrieval recipes remain unchanged.
Historical predictions remain immutable.

The repeat started at approximately 21:06 MSK with the same warm v5 process.
It writes a new `full-my-failed2-v2/` directory and sends all 668 assignments again.
It does not reuse the first attempt's predictions.
The observed pilot rate gives an initial estimate of about six to seven hours.
This estimate is not a completion guarantee.
The finite coordinator audits each saved prediction against accepted slugs.
It writes `independent-audit.json` and `report.md` after the run.
It then disables HTTP and stops only the isolated test application.
`coordinator-cleanup.json` records cleanup success or failure.
The coordinator returns failure if cleanup fails.

The repeat stopped at 21:34 MSK after 27.64 minutes.
It saved 43 HTTP 200 responses and one no-bottle error at `q-000040`.
The client raised `BadStatusLine` while reading the response for `q-000045`.
The received status line contains a binary prefix before `HTTP/1.1 200 OK`.
The transport root cause is not established. No fix or restart was made during the
owner's status check.
PID 20524 remained unchanged until explicit cleanup. No own native crash was recorded.
This interruption is not the earlier cached-process LOW_MEMORY exit.
Each of the ten prediction files contains 44 records. Independent partial audit passed.
Maximum sampled thermal status was SEVERE. Maximum battery temperature was 44.6 C.
The coordinator disabled HTTP and stopped only the isolated application.
The status check confirmed no service, no test PID, no forwarding, and power setting 15.
At the status check, the v2 runner was no longer active.
Its earlier completion estimate no longer applies.

Complete-cohort Top-1, Top-5, Top-10, failures, and paired control differences are pending.
Do not substitute the 30-image pilot accuracy for complete-cohort accuracy.
The separate Base p512 control scored 41.02 / 77.84 / 84.58 percent.
That control has a different encoder, smaller catalogue, and different references.
Do not attribute a future difference to segmentation alone.

## Direct USB HTTP repair and continuation

The owner selected a minimal host-only repair on October 19 at 23:17 MSK.
The client now opens a new direct plain HTTP connection for each ADB loopback request.
It does not use proxy configuration, TLS, or pooled connections.
It rejects malformed framing. It never removes a binary status prefix.
It retries transport failures at most twice and logs every physical POST attempt.
Before each attempt, it checks the same PID, user 0, and foreground-service protection.
It waits for the inference worker to become idle before a retry.
It does not retry an HTTP model error or enable a recognition fallback.
The origin of the original binary prefix remains unknown.

All 20 host tests passed. Fault injection checks the binary prefix, truncated bodies,
bounded retries, process changes, model errors, and proxy isolation.
A real-prefix dry audit validated all 44 saved assignments and all ten prediction files.
The source run inventory remained byte-for-byte unchanged.
The installed APK and private pack manifest match the frozen checksums below.
The q-000045 smoke returned HTTP 200 on its first attempt in Pixel PID 9424.
Independent audit passed all ten recipe predictions. This is a one-image smoke only.
The cold shared request took 64.11 seconds, including model initialization.

Full v3 started at approximately 23:26 MSK with the same warm PID 9424.
It copies the original 44 responses and prediction prefixes without byte changes.
It starts new computation at q-000045. The smoke result is not inserted into the cohort.
Q-000040 remains an explicit no-bottle failure. The denominator remains 668 assignments.
`inherited-run.json` preserves the raw source manifest. Prefix hashes bind every file.
Explicit process segments distinguish old PID 20524 from new PID 9424.
All ten recipes, model bytes, references, accelerators, and disabled re-ranking remain fixed.
The main application remains unchanged.

The initial remaining-time estimate is about six hours. Heat can change this estimate.
The finite coordinator audits results and disables isolated HTTP when the runner ends.
It stops only the isolated test application, including when UI cleanup times out.
The source run remains in `full-my-failed2-v2/`. New results use `full-my-failed2-v3/`.
Each new prediction file contains inherited and newly appended assignments.
The consistent start snapshot independently verified 47 assignments.
It contains 44 unchanged inherited records and three successful new records.
Q-000045 smoke and cohort candidates match exactly for all ten recipes.
No transport retry occurred in those first three new requests.
Current-segment memory and thermal maxima do not include the earlier segment.
Combined client times include earlier requests and any new transport retries.
Complete-cohort Top-1, Top-5, and Top-10 remain pending.

## Evidence

Artifact root:
`/Volumes/Storage/svoe-vino-final/artifacts/android-offline-retrieval-variants-20261019/`.

- `build-candidate-v4/`: APK, source, local tests, and installed hashes.
- `build-candidate-v5/`: foreground APK, unchanged inference hashes, lifecycle checks,
  and separately frozen host coordinator and audit tools.
- `device-frozen-foreground-parity-v1/`: complete v5 numerical gate.
- `background-pilot-30-v1/`: v5 background-execution gate.
- `device-pack-frozen-v1/manifest.json`: exact models, recipes, owners, and payload hashes.
- `device-frozen-shared-constants-parity-v1/`: complete numerical gate and raw captures.
- `pilot-30-v3/`: complete independent pilot, predictions, stage traces, and telemetry.
- `pilot-30-v3/stability-gate.json`: independent pilot verification and latency summary.
- `full-my-failed2-v1/`: interrupted full attempt and 29 incremental predictions per recipe.
- `full-my-failed2-v2/`: interrupted v5 repeat, 44 records per recipe, and cleanup evidence.
- `http-repair-v1/`: host source archive, 20-test log, real-prefix dry audit, and
  source inventory preservation checks.
- `http-repair-smoke-v1/`: q-000045 original-byte smoke and all ten audited predictions.
- `full-my-failed2-v3/`: active audited continuation from assignment 45.
- `full-my-failed2-v3/variant-01/predictions.jsonl`: current recipe 1 predictions.
  Recipes 2 through 10 use the corresponding `variant-02` through `variant-10` directory.
- `control-base-p512-no-seg/`: complete installed-application control.

Candidate-v4 APK SHA-256:
`41ee5fdc26686f4c3306748d1419671da18f459e438b90e87e0e597b18691353`.
Candidate-v5 APK SHA-256:
`5802b58299ea2474717061e6701f0c7d47fc226983715817b8e1f7bb75bff12e`.
Frozen pack manifest SHA-256:
`806593b1e0634275237142814c07c39427d658b8b23064bb896ededa7a1d45b1`.
Full query manifest SHA-256:
`1b8fb97a08b08fe8d9c7a422c142e316e5f853cd827219236ca5504840cce93a`.
