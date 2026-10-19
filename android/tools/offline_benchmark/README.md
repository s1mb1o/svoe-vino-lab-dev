# Offline Android retrieval benchmark

This directory implements the owner's ten-variant mobile pilot.
Read [the protocol](../../docs/plans/06_android-retrieval-variants.md).
The main application and its model pack remain unchanged.

## Device application

The application ID is `com.alolalab.chtozavino.offlinebench`.
Device tools require the original Android user `0`.
Do not switch a user profile without the owner's explicit approval.
The minimum Android API is 28.
The HTTP switch is off at each fresh application-process start.
The server survives an Activity recreation until the switch is disabled.
The server listens on port 18088 only after the switch is enabled.
The application performs no model download and no upstream inference request.

Enabling HTTP starts an isolated foreground service with a persistent notification.
Allow notifications when Android asks. The service does not start after a fresh process.
The service holds a partial CPU wake lock while HTTP runs and model cleanup finishes.
The switch and the notification's `Остановить` action stop HTTP and release resources.
The Activity MAY move to the background. The service does not restart after a kill.
Foreground-service priority reduces cached-process freezing. It does not guarantee
protection from memory pressure. No main-application service is added.

The application uses these components:

- A catalogue-trained YOLO11n-seg model provides independent bottle and label masks.
  The segmenter uses LiteRT CPU.
- The complete SO400M NaFlex p512 graph produces normalized 1152-dimensional vectors.
  A fourth input provides log weights to attention pooling only.
  The original transformer mask still excludes padded patches.
  GPU checks use FP32 buffer execution without serialization caches.
  The current memory candidate explicitly shares GPU constant tensors.
  It explicitly disables dynamic-range source quantization.
  Candidate v4 passed the numerical gate and all 300 independent pilot requests.
- A NEON dot-product kernel scores FP32 reference vectors in bounded blocks.
  Mean-2 and Mean-3 retain equal scores from distinct reference rows.
- Label fusion combines complete wine-score arrays.
  It does not re-rank a shortlist.

The ten recipe IDs, reference ownership, and fusion weights come from frozen desktop
artifacts. Query segmentation runs on the phone. Do not supply SAM3 query masks.
Barcode recognition, OCR, VLM calls, and re-ranking are disabled.
An absent bottle causes a failed request. There is no full-image fallback.
An absent label disables the label boost and uses bottle-only scores.

## Artifacts and sequence

Generated models, datasets, packs, captures, and runs remain outside Git.
Each Python entry point provides its argument list with `--help`.
Use the source paths from the frozen run manifest. Do not infer a model identity from
a filename alone.

1. `prepare_segmenter_data.py` excludes evaluation-image hashes from catalogue data.
2. `train_segmenter.py` starts the recorded local MPS training schedule.
   `freeze_segmenter.py` stops only that process after the declared pilot epoch.
3. `export_segmenter.py` exports the frozen checkpoint and compares raw CPU outputs.
4. `patch_weighted_pooling.py` preserves the external weights of the complete encoder.
   `validate_pooling.py` checks zero bias, native agreement, and padded positions.
5. `freeze_variants.py`, `fetch_exact_references.py`, and `export_reference_pack.py`
   preserve the selected reference galleries and their ownership.
6. `assemble_device_pack.py` verifies source hashes and writes a separate pack.
   A development pack is not eligible for a quality benchmark.
7. `build_device.sh` requires JDK 17, `ANDROID_HOME`, cached Gradle dependencies,
   and NDK `27.0.12077973`. It runs unit tests, lint, and the debug build.
8. Install the separate APK. Do not uninstall, clear, or replace the main application.
9. `push_device_pack.py` sends regular files with mode `0600` through debug `run-as`.
   The pack uses app-private `files/bench`. Do not make a directory world-writable.
10. Enable the observed HTTP switch in the benchmark application.
11. `run_device.py --mode parity` captures grouped GPU, CPU, and GPU runs.
    Use held-out catalogue images for numerical checks.
    `validate_device_capture.py` compares identical raw encoder inputs on desktop.
12. `run_device.py --mode pilot` sends 30 evenly spaced unique test images through
    each variant independently. The selection does not use prediction correctness.
13. `run_device.py --mode full` sends every frozen assignment with `variant=all`.
    This mode shares identical work inside one request. It never shares embeddings
    between query images. Its timings are not independent per-variant timings.
14. Disable the HTTP switch after the final saved result. Remove only test-created
    forwarding and temporary device files.

For the foreground-service candidate, repeat the numerical gate first.
Then use `--mode background-pilot` for the same 30 selected images with `variant=all`.
Move the Activity to the background before that gate. Keep original query bytes.
This checks background execution. It does not replace the independent latency pilot.
The runner requires active service protection and records process importance.
Use `run_full_benchmark.py` with the runner's `--serial`, `--queries`,
`--pack-manifest`, and `--out` arguments for a finite full run.
This coordinator audits the saved predictions and writes `report.md`.
It disables HTTP and stops only the isolated application after the audit.
`coordinator-cleanup.json` records cleanup success or failure.
The audit accepts every frozen alternative slug. An incomplete run has no final accuracy.

### USB HTTP recovery and continuation

The host client uses a new plain HTTP socket for each ADB loopback request.
It does not use proxy settings, TLS, or a connection pool.
It rejects an invalid status line or response body. It does not remove invalid bytes.
It retries a transport failure at most twice. `transport-attempts.jsonl` records attempts.
Before each attempt, it checks the PID, active Android user, and service protection.
It waits for active inference to finish before a retry. A changed PID stops the run.
Model errors are not transport retries. No-bottle errors remain failed predictions.

To continue an incomplete full run, use a new `--out` directory.
Add `--resume-from <old-run>` and `--expected-apk-sha256 <frozen-apk-hash>` to
`run_full_benchmark.py`. Keep the same query and pack manifests.
The runner independently audits the source run before it copies predictions.
It copies every saved response and all ten prediction prefixes without changing bytes.
It records prefix hashes, the inherited run manifest, and separate process segments.
The runner starts with the first missing assignment. It does not retry saved model errors.
The original run directory remains unchanged. Each prediction file contains both segments.
Client latency includes retry time. Telemetry maxima describe the current segment only.
Read the inherited run for the earlier segment telemetry.
Run host regression tests with `python3 -m unittest discover -s
android/tools/offline_benchmark -p 'test_*.py' -v` from the repository root.

The runner sends original image bytes. It does not send masks or accepted slugs.
The runner stops if the active Android user changes.
Each variant gets incremental `predictions.jsonl` records, including explicit errors.
The run directory also holds raw responses, process checks, logs, and thermal samples.
Keep failures in the full quality denominator. A stopped run is not complete.
Partial tensor diagnostics do not pass the complete numerical gate.
An interrupted pilot does not pass the thirty-image stability gate.

## HTTP contract

`GET /healthz` returns process identity, pack readiness, and disabled optional features.
It also returns `foreground_service`, `wake_lock_held`, and `process_importance`.

`POST /v1/match`, `/v1/eval/predict`, and `/v1/debug/embedding` require one multipart
`image` file. The maximum body is 20 MiB plus multipart overhead.
The maximum decoded image is 24 megapixels.
Parameters are `variant=1..10|all`, `k=1..20`, and `accelerator=GPU|CPU`.
The response includes a `variants` array, actual accelerators, stage traces, rotation,
encoder-pass count, and independent or shared timing mode.
The debug endpoint also writes model-input captures to app-private storage.
Do not use debug capture timings as an application-latency measurement.

The application verifies every pack file before creating a model.
CPU/GPU selection is explicit. A failed GPU request does not silently use CPU.
GPU creation, execution, and cleanup use one worker thread.
HTTP restarts share that worker. Old cleanup finishes before new model creation.

## Measurement limits

This pilot replaces desktop SAM3 query masks with mobile masks.
It uses a 160 by 160 prototype grid, Android bilinear RGB rendering, and bilinear
float mask sampling. The original unrotated crop has a four-percent edge margin.
Tight and rotated crops have no edge margin.
Prepared RGB has a maximum long edge of 1024 pixels.
These are declared mobile adaptations, not exact desktop preprocessing.

The installed Base p512 control uses 768-dimensional vectors and a smaller catalogue.
A difference from that control is not a segmentation-only effect.
Catalogue validation mask mAP is not wine-recognition accuracy.
Desktop numerical agreement is not a substitute for Android GPU validation.
