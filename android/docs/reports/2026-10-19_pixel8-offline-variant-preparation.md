# Offline Android variant preparation

Date: 2026-10-19.
Status: v4 independent pilot and v5 background gate passed; full v2 is running.

Candidate v5 adds a foreground service only to the isolated benchmark APK.
The owner approved this change after the background LOW_MEMORY interruption.
All ten inference-source files match candidate v4 byte for byte.
The model pack manifest remains unchanged.
Twenty Android tests, three initial host guard tests, and debug lint passed.
Fresh-process default-off, Activity recreation, explicit switch shutdown, and the
observed notification stop action passed on Pixel 8.
The repeated numerical gate passed all 102 checks.
The background gate completed 30 requests and 300 recipe predictions in one process.
All predictions and Top-20 scores match the v4 independent pilot exactly.
All 68 background samples have importance 125. Maximum heat was `MODERATE`.
Full v2 started in a new directory after these gates passed.
Read [the current measurement report](2026-10-19_pixel8-my-failed2-offline-variants.md).

## Scope

The owner selected fully offline Android query processing.
Mobile segmentation replaces runtime SAM3 query masks.
The ten desktop recipe IDs remain frozen.
Do not interpret the desktop table scores as mobile results.
Re-ranking, barcode recognition, OCR, and VLM calls are disabled.
The main application, its defaults, and its model pack remain unchanged.

The benchmark application ID is `com.alolalab.chtozavino.offlinebench`.
The original Android user is `0`.
The connected Pixel 8 serial is `41231FDJH002WZ`.

## Prepared components

| Component | Contract |
| --- | --- |
| Encoder | `google/siglip2-so400m-patch16-naflex`, 512 patches, 1152 dimensions. |
| Revision | `cc24074f717b612951c2dead130904ab9b65a81e`. |
| Runtime | Complete FP16-weight LiteRT graph with explicit pooling log weights. |
| Encoder execution | Explicit GPU FP32 buffers or CPU for numerical comparison. No silent fallback. |
| Query segmentation | Catalogue-trained YOLO11n-seg, independent `bottle` and `label` masks, CPU. |
| Search | Exact FP32 dot products, per-wine Max, Mean-2, or Mean-3. |
| Fusion | Full wine-score arrays, not a shortlist re-ranker. |
| Catalogue | 2274 wines in seven selected reference galleries. |

The reference payload contains 3,953,092,784 bytes including owner arrays.
The frozen device pack contains about 4.82 GB with models and metadata.
This pack supports comparisons. It is not the main production pack.
The benchmark APK does not contain these large reference arrays.

## Segmentation training

The dataset contains 2031 training images and 228 wine-group validation images.
All images come from the catalogue.
The dataset excludes exact-hash matches with 3039 evaluation-image hashes.
No evaluation image, mask, accepted answer, or retrieval result selected the checkpoint.

The original training schedule permits 30 epochs.
The pilot stopping policy fixed ten complete epochs before adapted retrieval inference.
The pilot completed ten epochs in 69.3 minutes.
The selected checkpoint is epoch 8, with validation fitness 1.79737.
Selected mask mAP50-95 is 0.93199. Selected box mAP50-95 is 0.86538.
These are catalogue segmentation metrics. They are not wine-recognition metrics.

The checkpoint SHA-256 is
`8f33d71e63069e9f0d40fdeb1b84b181122e400e293998819d7d6cb7d927ba44`.
The compiled segmenter SHA-256 is
`2d0dc925e6f8962318dbe936a8a21652cefe0f66984c052360c7a71eb64f44a1`.

The compiled segmenter passed three PyTorch/LiteRT CPU raw-output checks.
The largest coordinate error was 0.00455 pixels.
The largest prototype error was 0.0000223.

## Numerical gates

The weighted graph preserves all 448 original external weight buffers.
Zero pooling bias gives zero component error against the original LiteRT graph on
two synthetic fixtures. Padding perturbations do not change those vectors.

The development device gates passed these checks:

| Gate | Result |
| --- | --- |
| Exact-pooling, three images, grouped GPU/CPU/GPU | 60 checks passed. Minimum cosine 0.9999999858. Maximum component error 0.0000192. |
| All ten recipes, one image, grouped GPU/CPU/GPU | 102 checks passed. Minimum cosine 0.9999999990. Maximum component error 0.00000416. |
| Complete bottle-score arrays | Maximum error below 0.000000208. Includes Max, Mean-2, and Mean-3. |
| Legacy mask log weights | Zero numerical error after the BOX rounding correction. |
| Isolated source tests | 16 unit tests and debug lint passed. |

The first all-recipe gate detected incorrect legacy BOX rounding.
Its APK and captures are retained as rejected evidence.
The correction uses the verified BOX endpoints and fixed coefficient rounding.
It does not relax the numerical tolerance.

These checks used held-out catalogue images, not `my-failed-2` test images.

## Frozen-pack interruption

The final frozen-pack gate received two of three planned responses.
GPU and CPU vectors, mask weights, segmenter tensors, and complete bottle scores
passed partial checks on those responses.
The last response was lost during a USB transport reset.
The run remains incomplete. Partial checks do not pass the complete gate.

The original process initially remained PID 26472 after USB returned.
The phone uptime excluded a reboot.
Android later recorded a background `LOW_MEMORY` process exit.
The active Android user was 10. The test package and pack belonged to user 0.
No own native crash was recorded.
The audit does not establish a GPU crash as the cause of the USB reset.

The revised runner saves incomplete status even if cleanup loses the device.
The revised benchmark server survives Activity recreation.
HTTP restarts share one inference worker for ordered model cleanup and creation.
Device tools now reject another active Android user before a device write.
The lifecycle APK was not installed while the other user's session was active.

The owner must restore user 0 or approve switching to user 0 before device work resumes.
The USB transport later became unavailable. Wireless ADB remains listed.
The benchmark did not switch to wireless transport.
No thirty-image quality pilot or complete adapted `my-failed-2` run has started.

## Resumed final gate

The owner restored Android user 0. USB transport returned.
The lifecycle candidate was installed without clearing application data.
The private frozen model pack remained unchanged.
The repeated final gate completed all three GPU/CPU/GPU requests in PID 21034.
All 102 numerical checks passed. Minimum encoder cosine was 0.9999999993.
Maximum encoder component error was 0.00000441.
Maximum complete bottle-score error was 0.000000244.
The segmenter raw tensors matched exactly. Legacy log weights matched exactly.
Exact-coverage log-weight error was below 0.000001.
Maximum thermal status was `LIGHT`. Peak sampled PSS was 3,995.1 MiB.

An explicit Activity recreation retained the HTTP server and loaded model state.
The process remained PID 21034. Both health checks returned the frozen pack identity.
The independent thirty-image pilot started after the complete numerical gate passed.
No complete adapted `my-failed-2` result is available yet.

## Independent pilot interruption

The pilot saved 57 successful responses from 300 planned requests.
The test process remained PID 21034 until the interruption.
At 19:01:12 MSK, the benchmark Activity stopped and the camera became foreground.
At 19:01:26 MSK, Android killed PID 21034 with reason `LOW_MEMORY` and importance 400.
No native crash of the benchmark application was recorded.
The active Android user remained 0. USB transport remained available.
This interruption differs from the earlier profile-change interruption.

Request 58 was variant 8 on query `q-000124`.
That request has no response. The pilot remains incomplete.
Do not use its partial Top-k percentages as complete-cohort accuracy.
Maximum sampled thermal status was `MODERATE`.
Maximum battery temperature was 41.2 C. Peak sampled pilot PSS was 2,146.98 MiB.
The system exit record reported about 1.9 GB RSS for the cached process.

The runner saved the failure and completed cleanup without an error.
The HTTP listener is absent. The test forwarding rule is absent.
The power setting is restored to 15. The private frozen model pack is preserved.
The main application and its data remain unchanged.
The temporary benchmark UI XML was removed.
The next pilot requires a phone dedicated to the visible benchmark application.
The isolated application has no foreground service.
Do not infer background execution support from Activity-recreation support.

## Foreground interruption and memory candidate

The owner dedicated the phone to the benchmark at 19:05 MSK.
The second pilot stopped before its first response.
Android recorded `LOW_MEMORY`, importance 100, and about 2.4 GB RSS for PID 2123.
The benchmark Activity remained foreground. Android user 0 remained active.
This second failure cannot be explained only by the camera transition in the first run.
Both incomplete pilots and their process-exit audits remain unchanged.

Candidate v4 explicitly enables GPU constant-tensor sharing.
It explicitly disables dynamic-range source quantization.
It keeps FP32 arithmetic, BUFFER storage, and disabled serialization caches.
Model files, reference files, masks, pooling formulas, and recipes remain unchanged.
The candidate passed 18 unit tests and lint with zero errors and ten warnings.

The complete repeated GPU/CPU/GPU gate passed 102 numerical checks in PID 13687.
Minimum encoder cosine was 0.9999999993. Maximum component error was 0.00000425.
The gate completed in 255.1 seconds without a process restart or request error.
Peak sampled PSS was 2,961.25 MiB. Maximum thermal status was `LIGHT`.
This is not a controlled memory A/B comparison. The device state differed between runs.
The third independent pilot completed 300 requests with zero errors in PID 13687.
Every recipe has 30 verified prediction records. No CPU fallback occurred.
Peak sampled PSS was 2173.36 MiB. Maximum thermal status was `SEVERE`.
Independent medians ranged from 4.09 through 13.74 seconds.
The phone cooled to `MODERATE` before the complete cohort started in the same process.
Read [the current measurement report](2026-10-19_pixel8-my-failed2-offline-variants.md).

## Existing quality control

The installed Base p512 control completed all 668 `my-failed-2` assignments.
Top-1/5/10 were 41.02 / 77.84 / 84.58 percent.
Read [the control report](2026-10-19_pixel8-my-failed2-offline-control.md).
Its 768-dimensional encoder and smaller catalogue differ from this experiment.
Do not attribute a future difference to segmentation alone.

## Artifact location

All generated evidence is under this directory:

`/Volumes/Storage/svoe-vino-final/artifacts/android-offline-retrieval-variants-20261019/`.

- `variants-v1.json`: exact desktop recipe mapping.
- `reference-pack-v1/`: seven FP32 galleries and owner arrays.
- `models/weighted-v2-validation.json`: graph adaptation gate.
- `segmenter-pilot-frozen-v1/`: checkpoint selection and training history.
- `segmenter-export-pilot-v1/`: compiled model and export checks.
- `device-pack-frozen-v1/`: final device pack.
- `device-development-parity-v2/`: complete exact-pooling numerical gate.
- `device-development-all-parity-v1/`: rejected legacy-rounding gate and APK.
- `device-development-all-parity-v2/`: complete repaired numerical gate.
- `device-frozen-all-parity-v1/`: interrupted final gate, partial checks, and exit audit.
- `device-frozen-all-parity-v2/`: passed final gate and Activity lifecycle check.
- `pilot-30-v1/`: interrupted independent pilot, partial predictions, exit audit, and cleanup.
- `pilot-30-v2/`: zero-response foreground memory failure and diagnostic audit.
- `device-frozen-shared-constants-parity-v1/`: passed candidate-v4 numerical gate.
- `pilot-30-v3/`: complete independently verified pilot with candidate v4.
- `full-my-failed2-v1/`: active complete-cohort run and incremental per-recipe predictions.
- `build-candidate-v3/`: exact source archive, local test evidence, and the next APK.
- `build-candidate-v4/`: constant-sharing APK, source, eighteen tests, and installation hashes.

The lifecycle candidate v3 APK is `chtozavino-offlinebench-0.1.0-debug.apk`.
Its size is 19,745,497 bytes.
Its SHA-256 is
`03a7340be0cc313716275a2de494ce0f84bcbfecca235d9c90c5ceaca8dc13f6`.
Its build passed 16 unit tests and lint with zero errors and ten warnings.
Candidate v3 was installed in user 0. Its Activity lifecycle check passed.

The current candidate v4 APK has 19,746,453 bytes.
Its SHA-256 is
`41ee5fdc26686f4c3306748d1419671da18f459e438b90e87e0e597b18691353`.
The installed APK hash matches this saved file.
Its complete numerical and process-stability gates passed.
Its complete-cohort quality run is not complete.

The frozen pack manifest SHA-256 is
`806593b1e0634275237142814c07c39427d658b8b23064bb896ededa7a1d45b1`.
Read [the tool documentation](../../tools/offline_benchmark/README.md) before resuming.
