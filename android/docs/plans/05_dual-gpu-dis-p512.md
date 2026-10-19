# Isolated DIS and complete p512 dual-GPU experiment

Date: 2026-10-19

## Authority and isolation

The owner approved this experiment and its conditional full run.
Copy the committed Android source from `e14c541e` into the experiment artifact folder.
Do not modify the main Android application source or its build outputs.
Use application ID `chtozavino.alolalab.com.dualgpu`.
Give the experimental launcher a distinct Russian label.
Install the experiment beside the main application.
Do not replace, uninstall, or clear data from the main application.
Temporarily stop the main process to prevent competing GPU sessions.
Reopen the main application after cleanup.

The artifact folder is
`/Volumes/Storage/svoe-vino-final/artifacts/android-p512-dis-dual-gpu-20261019/`.
Keep the full source snapshot, exact experimental patch, APK, and hashes there.
Keep model weights and generated APKs outside Git.

## Experimental changes

Use the same format 6 pack and its 2,093 frozen reference vectors.
Keep full-resolution decode, native crop preparation, and complete Base p512 inference.
Bypass only the inherited DIS GPU to SigLIP2 CPU override in the copied source.
Keep model reuse and the dedicated inference worker.
Keep GPU FP32 execution, BUFFER storage, and disabled GPU program caching.
Disable CPU fallback for explicit debug accelerator requests in the experiment.
Add actual segmentation and embedding accelerators to every successful debug response.
Identify the experimental application and guard bypass in health responses.
Keep HTTP off by default and enable it explicitly for the test.

## Pilot gate

Use the exact existing thirty-image selection and verify every input SHA-256.
Request DIS GPU and SigLIP2 GPU through the debug embedding endpoint.
Use one worker, maximum reference aggregation, and no barcode decoding.
Save every response, timing, PID, telemetry sample, and application-only log.
Check every successful embedding for 768 finite values and unit norm.
Require both actual accelerators to be GPU.
Stop after a native abort, process restart, non-finite vector, or CPU fallback.
Do not silently restart the application and combine separate processes.
An explicit DIS no-object error is a segmentation coverage result, not a native crash.
Record that error and include its query in the quality denominator.
Require all thirty requests to finish without a runtime stability failure.
Report latency, sampled PSS, and thermal status separately from this stability gate.

## Full run

Start full `my` only after the pilot stability gate passes.
Reuse the previous full-run frozen `queries.jsonl` without changing accepted slugs.
Verify all 3,031 distinct input hashes.
Run all 3,409 assignments with one uncached worker and barcode disabled.
Use `/v1/match?k=20` with explicit GPU requests for both models.
Save Workbench `predictions.jsonl`, scored results, and raw device responses.
Record actual accelerators for every successful request.
Stop on native abort, process restart, invalid vector, or CPU fallback.
Stop at Android thermal status `CRITICAL` or higher.
Do not override Android thermal protection.
Preserve completed rows when a safety stop occurs.

## Comparison and cleanup

Compare full positive Top-1, Top-5, Top-10, MRR, and paired gains and losses.
Compare negative forbidden matches and no-match false accepts.
Compare the catalogue-covered subset without changing the primary denominator.
Compare client latency with the previous full p512 no-segmentation run.
State that the baseline and experiment occurred at different times.
Report heat and memory without treating sampled PSS as the complete GPU peak.
Disable the experimental HTTP server and remove only the created ADB forward.
Restore any temporary screen-awake setting.
Force-stop the experimental application after the test.
Verify that the main installed APK and main application source remain unchanged.
Record results in a separate report. Preserve existing frozen reports.

## Completion

The isolated APK passed 64 debug unit tests and debug lint.
All thirty pilot requests passed stability and vector validation.
The full run completed all 3,409 assignments in PID `19651`.
No native abort, process restart, or CPU fallback occurred.
Five positive assignments failed DIS main-object detection.
Full Top-1 increased from 69.09% to 72.29%.
Client median latency increased from 924 ms to 1,319 ms.
Three explicit post-run p512 GPU/CPU vector comparisons passed.
The HTTP setting is disabled, forwarding is removed, and power settings are restored.
The main application source and installed/build APK hashes are unchanged.
Read [the completed report](../reports/2026-10-19_pixel8-p512-dis-dual-gpu-my.md).
