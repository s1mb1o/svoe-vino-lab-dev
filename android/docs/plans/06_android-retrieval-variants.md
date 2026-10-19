# Android retrieval variant evaluation

Date: 2026-10-19
State: The owner selected the complete offline adaptation.

## Request

Measure the current application on `my-failed-2` first.
Then evaluate the ten variants in the owner's table on Pixel 8.
Disable re-ranking for every measurement.
Keep the existing application, release archive, and completed benchmarks recoverable.

## Verified preflight

The connected device is Pixel 8 with serial `41231FDJH002WZ`.
ADB reports state `device`.
The installed main application still uses `chtozavino.alolalab.com`.
The new `com.alolalab.chtozavino` APK has not been installed.

The source report is in this directory:
`/Volumes/T7_2TB/Projects-T7_2TB/drink-atlas-workspace/svoe-vino-lab/internal/my-failed2-six-variants-20261017/`.
Read `protocol.json` and `retrieval-extensions-20261018/protocol.json` there.

The desktop campaign uses `google/siglip2-so400m-patch16-naflex`.
The checkpoint revision is `cc24074f717b612951c2dead130904ab9b65a81e`.
The requested configurations use a 512-patch budget.
The frozen cohort contains 668 assignments on 627 distinct images.
The query manifest SHA-256 is
`1b8fb97a08b08fe8d9c7a422c142e316e5f853cd827219236ca5504840cce93a`.
The campaign uses saved package and label masks in source coordinates.
Its prerequisite evidence identifies SAM3 label segmentation.
The protocol already excludes local re-ranking.

The main Android pipeline instead uses complete Base p512 with 768 dimensions.
DIS and YOLO do not provide a separate label mask in the application.
Do not reuse Base catalogue vectors with the SO400M encoder.
Do not call frozen desktop masks an on-device segmentation result.

## Measurement-boundary options

1. Exact retrieval reproduction in an isolated debug application.
   Use the SO400M checkpoint and frozen SAM3 masks.
   Run the encoder, weighted pooling, and catalogue search on Pixel 8.
   Report mask preparation as an external prerequisite.
   Exclude segmentation from the measured Android latency.
2. A fully offline Android adaptation.
   Define a mobile bottle and label segmentation path first.
   Record each deviation from the desktop configurations.
   Do not attribute the desktop table scores to the adapted pipeline.

The first option preserves the requested retrieval conditions.
The second option measures a complete mobile pipeline but changes those conditions.
The owner selected option 2 on 2026-10-19.
Use mobile query segmentation throughout the adapted device pipeline.
Do not supply frozen SAM3 query masks to the application.

## Offline adaptation

The installed COCO YOLO model provides bottle masks only.
No verified mobile label model was found in the inspected application or model cache.
Prepare a small two-class `bottle` and `label` segmentation model from catalogue masks.
Use catalogue images only for training and validation.
Exclude exact-hash matches with the evaluation images from segmentation training.
Do not use evaluation masks, labels, accepted slugs, or results to train the segmenter.
Freeze the training split and hyperparameters before the device evaluation.
The original training schedule permits 30 epochs.
For this pilot, stop after the first 10 complete epochs.
Select the highest catalogue-validation fitness within those epochs.
This stopping policy is fixed before the first `my-failed-2` adapted query.
Do not use retrieval results to select a checkpoint.
Validate the exported mobile segmenter numerically before a complete device run.
Retain failed detections in the scoring denominator.

Keep SO400M p512 and the desktop reference index when their identities agree.
Add explicit pooling log weights to the verified complete graph.
Require agreement with zero log weights before weighted tests.
Keep segmentation, preprocessing, pooling, fusion, and ranking on the device.
Use the host only for input transport, reference-pack preparation, and result scoring.
Run a separate benchmark application. Do not replace the main application defaults.
Benchmark the current installed Base p512 pipeline as a separate control.
Record its old application ID instead of claiming that the new ID is installed.

Do not add full-image fallback merely because the owner asked whether it exists.
Report any proposed fallback as a separate policy change.

## Required protocol after selection

1. Resolve each table row to exact frozen configuration identifiers.
2. Preserve checkpoint, pooling weights, mask coverage, geometry, reference views,
   score aggregation, and label-fusion weights for exact reproduction.
3. Keep barcode recognition, OCR, VLM calls, cluster re-ranking, and shortlist
   re-ranking outside the benchmark.
4. Freeze the query identities and accepted alternative slugs.
5. Install a separate debug application when required by the selected workflow.
6. Validate CPU/GPU and desktop/device vector agreement before a complete run.
7. Run a short stability check before all 668 assignments.
8. Save predictions incrementally in `predictions.jsonl`.
9. Save raw responses, artifact hashes, model identities, and actual accelerators.
10. Measure Top-1, Top-5, Top-10, latency, memory, thermal state, and process stability.
11. Keep failures in the cohort denominator.
12. Distinguish encoder-only, retrieval, and complete-pipeline timings.
13. Disable debug HTTP and remove only test-created forwarding after measurement.

## Frozen mobile preparation policy

Use two independent instance masks. Do not use an overlap map for nested targets.
Run the mobile segmenter on CPU. Run SO400M p512 on GPU when numerical checks pass.
Use soft prototype masks with a 0.5 core threshold for geometry.
Use source-coordinate letterbox mapping for the 160 by 160 prototype grid.
Choose the large central bottle. Choose a contained label on that bottle.
Use a four-percent margin on each edge for the unrotated original view.
Use zero margin for tight and rotated views.
Limit prepared RGB to a 1024-pixel long edge, as in the desktop campaign.
Use Android bilinear RGB rendering and bilinear float mask sampling.
These rules are mobile adaptations. They are not exact PIL/SAM3 reproduction.

For independent latency, run one variant in each request.
For complete-cohort quality, the `all` selector MAY share segmentation and identical
embeddings inside one request. It MUST NOT cache query embeddings across requests.
Label fusion MUST score the complete catalogue. It is not shortlist re-ranking.
Report shared-request timings separately from independent variant latency.

The Base p512 control is complete. See the control report.
The SO400M desktop numerical gate and the development segmenter export gate passed.
The first two adapted pilots are incomplete and retained as evidence.
Android killed the first cached process after the camera became foreground.
Android killed the second foreground process under memory pressure.
Candidate v4 passed the repeated numerical gate and the complete independent pilot.
The first full run stopped after 29 assignments. No complete hard-set result exists yet.
Development numerical gates passed. The interrupted frozen-pack gate is retained.
The repeated frozen-pack gate passed all 102 numerical checks in one device process.
The process and HTTP server survived explicit Activity recreation.
Read `docs/reports/2026-10-19_pixel8-offline-variant-preparation.md` before resuming.
Require the original Android user 0 and an available USB transport.
Do not switch a user profile without the owner's explicit approval.

## Foreground memory gate

The repeated cold-start pilot also stopped with `LOW_MEMORY` at importance 100.
The benchmark Activity remained foreground. No first response completed.
This evidence excludes a background-only explanation for that second interruption.
Retain the original APK, both pilot attempts, and both process-exit audits.

Test explicit GPU constant-tensor sharing in a new isolated candidate.
Keep FP32 arithmetic, BUFFER storage, model bytes, pooling, and all recipes unchanged.
Explicitly disable dynamic-range source quantization.
The memory benefit is not established until a device measurement completes.
Require the complete GPU/CPU/GPU numerical gate again after this runtime option change.
Then repeat the same thirty-image-per-recipe pilot in a new output directory.
Candidate v4 passed this repeated numerical gate and all 300 independent requests.
Its pilot reached SEVERE heat. Do not call this a production heat acceptance.
Keep the process warm and let the phone cool to MODERATE before the full cohort.
Do not stop other applications, stop another Android user, or reboot the phone.
Such device changes require a separate owner decision.

## Foreground service readiness

The owner approved this approach at 20:30:39 MSK on 2026-10-19.
The full v1 process became cached after its Activity stopped.
Android froze that process and then recorded LOW_MEMORY at importance 400.
Preserve all v1 partial predictions. Do not combine these records with a new run.

Add a foreground service only to the isolated benchmark application.
The main application MUST remain unchanged.
The HTTP switch MUST stay off after each fresh process start.
Only an explicit UI action MAY start the service.
The service MUST post a persistent Russian notification before starting HTTP.
Use the `specialUse` service type on API 34 and later.
Declare the owner-started offline bulk-inference use case in the manifest.
Do not classify this six-hour computation as `dataSync` or `shortService`.
The service MUST hold a partial CPU wake lock only while HTTP or ordered shutdown runs.
The HTTP switch and notification stop action MUST stop HTTP and the service.
Shutdown MUST enqueue model cleanup on the existing inference worker.
Shutdown MUST remove the notification and release the wake lock.
Activity recreation MUST NOT stop the service.
Use `START_NOT_STICKY`. Do not add boot receivers or automatic restart.
Record service state, wake-lock state, and process importance in `/healthz`.
The runner MUST require foreground-service protection before sending a query.
The service reduces cached-process freezing. It does not guarantee OOM immunity.

Preserve candidate v4 and its complete independent latency pilot as historical evidence.
Freeze a new v5 APK and source archive. Keep every inference-source hash unchanged.
Repeat the GPU/CPU/GPU numerical gate after installation.
Then run 30 original images with `variant=all` while the Activity is in the background.
Require one PID, explicit GPU, no cached importance, and no critical heat.
Check HTTP-off cleanup and fresh-process default-off behavior before this background gate.
Do not reattribute v4 independent latency measurements to v5.
After these checks pass, repeat all 668 assignments in `full-my-failed2-v2/`.

Candidate v5 passed 20 Android tests, seven host tests, and all 102 numerical checks.
The original 30 selected images completed in the background without errors or restart.
All 300 recipe predictions and every Top-20 score match the v4 independent pilot.
All 68 background samples have importance 125. Maximum thermal status is MODERATE.
Full v2 started at approximately 21:06 MSK in the same warm process.
The finite coordinator audits results, writes a report, and stops only the isolated app.
The complete 668-assignment quality result remains pending.

## Direct USB HTTP repair and continuation

The owner selected the minimal repair and continuation on 2026-10-19 at 23:17 MSK.
The v2 client received a binary prefix before an HTTP 200 status line on q-000045.
The v2 process remained alive. The exact source of the prefix is not established.
Use a direct `http.client.HTTPConnection` to the existing ADB loopback endpoint.
Do not use ambient proxy configuration or a shared connection.
Close each HTTP connection. Reject malformed framing instead of removing prefix bytes.
Retry transport failures at most twice. Log every physical request attempt.
Before a retry, require the same PID, Android user 0, and foreground-service protection.
Wait for the previous inference to finish before sending the same image again.
Do not retry a model error as a transport failure. Preserve no-bottle errors.
Stop on a PID change, unexpected model error, or critical heat.

Add fault-injection tests for the observed binary prefix, truncated responses,
bounded retries, process changes, and proxy isolation.
Validate the complete 44-record source prefix with the independent auditor.
Require identical query and pack hashes and the same installed v5 APK checksum.
Copy source response and prediction bytes into a new output directory.
Record source paths, prefix lengths, prefix hashes, and explicit process segments.
Do not modify the original source directory.
Resume from the first missing assignment, q-000045. Retain q-000040 as a failure.
Keep all 668 assignments in the quality denominator.
Record retry time in the current client request time. Do not call a retry-free latency.
Check q-000045 on the phone before the continuation.
Keep re-ranking and barcode recognition disabled throughout the continuation.
