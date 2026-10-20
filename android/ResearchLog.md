# Research log

## 2026-10-20

### Production promotion

- The owner selected both complete pipelines, with DIS-768 cropped custom as the default.
  The alternative retains the original standard graph and original reference bytes.
  Format 7 shares catalogue images and position data. It keeps separate candidate mappings.
- The measured crop permits margins outside the original frame and caps the rendered long side at 1024 pixels.
  The previous production crop clamps source bounds. Reusing that path would change the measured pipeline.
- The new custom path uses fractional mask coverage on the actual NaFlex grid.
  It does not identify whitespace from RGB values. White bottle labels remain foreground.
- The owner selected omission of optional YOLO weights for public distribution.
  Barcode and QR functionality does not require those weights.
- The DIS-512 campaign finished at 21:16 MSK with 668 assignments and zero errors.
  Its saved audit passes: Top-1/5/10 46.56/82.34/87.72%, median/P95 1324/1665 ms.
  The DIS-768 default has the same Top-1 and higher Top-5/10 on this cohort.
- Device validation and website publication remain pending. Do not attribute benchmark results to the new APK before parity checks pass.

### DIS resolution specialization

- DIS 768 completed all 668 assignments at 20:47 MSK with zero inference errors.
  The saved audit, fresh audit, and direct accepted-alternative calculations agree.
  Top-1/5/10 is 46.56/84.58/89.67%. Request median/P95 is 1637/2052 ms.
  Against DIS 1024, paired Top-1 gains/losses are 36/39: net -3 hits (-0.45 points).
  Request median decreases 37.22%; P95 decreases 40.15%. Reference bytes are unchanged.
  Peak sampled PSS is 1647703 KiB. Maximum thermal status is 2; battery temperature is 42.6 C.
  Pixel PID 7960 stayed stable. No transport error, process restart, fallback, or cleanup error occurred.
  The DIS 1024 baseline required USB continuation. Its peak PSS is 1751076 KiB and battery maximum is 43.8 C.
  Different start temperatures limit a strictly causal speed comparison. Full `my` quality remains unmeasured.
  All 105 frozen source files remain unchanged. Re-ranking remains disabled.
  DIS 512 continues through its cooling gate. The production default remains unchanged.

- DIS 768 passed all 115 device checks and its 30-image pilot at 20:25 MSK.
  Maximum raw/normalized mask errors are 0.000001550/0.000006735.
  Maximum encoder component error is 0.000002906. No threshold changed.
  Pilot median/P95 is 1358/1468 ms, zero errors, maximum thermal status 0.
  The full 668-assignment run started. Do not compare pilot quality with full baseline quality.

- The pinned DIS export has 247 operators and fixed bilinear-resize sizes.
  A smaller input bitmap alone does not reduce the graph's internal spatial sizes.
- Specialize spatial activation shapes and shape constants for 768 and 512.
  Preserve every learned-weight buffer, channel dimension, interpolation flag, and operator option.
  Preserve explicit padding in pixels. Do not scale the 1026 padded activation as a whole.
- The identity 1024 export matches source CPU output exactly.
  Both smaller candidates pass finite-output and complete static-shape checks.
  These checks do not establish retrieval quality or device speed.
- Use separate disresbench packs with the same p512 graph and reference bytes.
  Compare each candidate mask with its own CPU graph, not with the 1024 mask.
  Keep the same strict parity thresholds and independent 30-image pilots.
- All 54 host and 33 Android tests pass. The finite Pixel workflow started at 20:21 MSK.
  Read `docs/reports/2026-10-20_dis-input-resolution.md` for identities and pending measurements.

### Cropped DIS speedup assessment

- Derived an additive timing budget from all 668 saved cropped DIS responses.
  Mean client time is 2608 ms. Mean device time is 2218 ms.
  Do not add stage medians to explain the whole-request median.
- Mean DIS inference/readback is 575 ms. Mean encoder inference/readback is 483 ms.
  Mean DIS post-processing is 412 ms. Other uninstrumented device work is 494 ms.
  DIS preprocessing, encoder preprocessing, and search add 254 ms on average.
  Outside-device benchmark work adds 390 ms. This is not pure network time.
- The source repeatedly validates and scans the 1024-square mask.
  The zero-angle crop computes a general convex hull before it calculates bounds.
  The source allocates image and float arrays per request.
  These are optimization candidates, not measured speedups.
- First preserve the 1024 DIS graph, p512 encoder, FP32 policies, and reference bytes.
  Add detailed crop/decode/normalization timers. Reuse scratch buffers.
  Test fused mask loops, an exact zero-angle bounding-box path, and native image loops.
  Require unchanged masks, patch weights, vectors, and rankings within existing numerical gates.
- A second option is a separate DIS export at 768 or 512 input pixels.
  The current graph has fixed 1024 input tensors. Resizing the source alone does not change that graph.
  Reduced input changes masks and needs a fresh numerical and retrieval-quality experiment.
- Reduced GPU precision is higher risk. The earlier default-precision DIS run failed mask parity.
  Do not restore that policy or lower the existing numerical threshold to obtain a speedup.
  Models already remain compiled between requests. Cosine search averages only 21 ms.
- Follow the official LiteRT guidance to profile application work and remove redundant copies.
  Sources: [performance guidance](https://developers.google.com/edge/litert/conversion/tensorflow/build/best_practices)
  and [GPU precision API](https://developers.google.com/edge/api/litert/kotlin/com/google/ai/edge/litert/CompiledModel.GpuOptions.Precision).
- Saved evidence: `android-dis-p512-pooling-20261020/cropped-speedup-analysis-20261020.json`.
  No implementation, model export, device request, or new benchmark occurred.
  Recommend the exact-output CPU path before a lower-resolution or lower-precision model.

### DIS p512 comparison design

- All three DIS comparison conditions are complete. Cropped DIS finished at 19:33 MSK.
  Fresh audits match all five saved cohorts. Direct metric calculations also match.
- Cropped DIS has 314/668 Top-1 hits and Top-1/5/10 of 47.01/84.58/89.82%.
  It gains 5.99 points over default and 3.29 over full-image DIS.
  Paired gains/regressions are 115/75 against default and 73/51 against full-image DIS.
- Cropped DIS median/P95 is 2607/3429 ms. Maximum is 5323 ms.
  The request-latency targets pass. USB continuation prevents an uninterrupted-stability claim.
  Both measured segments used Pixel PID 22646. All inherited records remain byte-identical.
- All custom conditions use the same reference vectors. No re-ranking or fallback was enabled.
  The default is fastest. Keep whole-pipeline, thermal, and decoder differences explicit.
  The failure-cohort result does not establish quality on the full `my` dataset.
- Final HTTP-off and isolated-process-stop cleanup passed. The USB forward is absent.
  The production default remains unchanged. No device state changed in the final read-only audit.

- USB disconnected during cropped DIS after 190 saved assignments. The host controller exited.
  Pixel PID 22646 survived. Exact APK/pack hashes and all saved records passed recovery checks.
  No received but unsaved assignment existed. Do not classify this USB loss as a native crash.
- The host-only continuation preserves the raw attempt and exact response/prediction prefixes.
  It requires the same process. It excludes the disconnected interval from request latency.
  It records the original cleanup failures and does not claim uninterrupted stability.
  All 46 host tests pass. The new finite workflow resumed at 19:08 MSK.

- Full-image DIS completed 668 assignments at 18:27 MSK with zero errors.
  Fresh audits match saved results. Top-1/5/10 is 43.71/83.23/88.92%.
  The fresh standard control reproduces all 668 production Top-1 predictions at 41.02%.
- Full-image DIS gains 2.69 Top-1 points over default and 4.79 over full-image YOLO.
  Paired gains/regressions are 81/63 against default and 53/21 against full-image YOLO.
- Full-image DIS median/P95 is 2283/5351 ms. Maximum is 15784 ms.
  It fails the full-cohort latency targets despite passing numerical and accuracy audits.
  Maximum thermal status is 3 versus 1 for control. The same Pixel PID remained stable.
- Cropped DIS has not started at 18:28 MSK. The phone is cooling from 43.4 C.
  Keep the 40 C gate and re-ranking disabled. The complete comparison remains pending.

- V3 FP32 arithmetic with automatic storage passed all mask and vector checks.
  Full-image maximum raw/normalized mask errors are 0.000001789/0.000007749.
  The first DIS inference was 536 ms. Forced BUFFER was 2877 ms; default precision was 263 ms.
  Keep these model-specific runtime choices separate from the encoder's FP32/BUFFER policy.
- All 440 numerical checks and three 30-image pilots pass without errors.
  DIS full-image median/P95 is 2025/3351 ms. DIS cropped median/P95 is 1949/2204 ms.
  The standard pilot is 872/1091 ms. These are pilot values, not full-cohort results.
- The full standard control is running at 17:33 MSK. Full DIS quality remains pending.
  Keep re-ranking off and the production default unchanged.

- V2 production-default DIS GPU options reduced first replay inference to 263 ms.
  Strict experimental CPU/GPU mask errors reached 0.007584095 raw and 0.032568038 normalized.
  Same-input encoder agreement passed. No invalid output or native failure occurred.
  The unchanged mask gate stopped the workflow before full tests.
  Test FP32 arithmetic with automatic storage next. Do not weaken thresholds to bypass this result.
- V1 passed 165 control and 160 DIS numerical checks, including raw masks and source projection.
  Its first 21 DIS pilot requests had median latency 4179 ms with no inference error.
  The test incorrectly applied encoder-only FP32/BUFFER settings to DIS.
  Production DIS uses default GPU options. Keep those model-specific policies separate.
  Preserve v1. Repeat unchanged gates with the production-equivalent DIS configuration.
- The owner selected full-image custom and cropped/white custom with DIS plus a fresh control.
- Keep the previous matched custom reference vectors unchanged for both custom queries.
  This comparison tests query preparation. It does not test a rebuilt DIS reference index.
- Reuse the production DIS graph and its per-image min-max output normalization.
  DIS predicts salient foreground, not a bottle or label class.
- Use GPU DIS and GPU p512 in an isolated package, with no CPU or no-mask fallback.
  Prior dual-GPU testing supports this policy. New numerical and stability gates remain required.
- YOLO used CPU segmentation. Compare end-to-end quality and latency, not segmenter-only latency.
- All 36 host and 30 Android tests pass. Encoder and reference bytes remain unchanged.
  The new workflow started at 17:04 MSK. Full quality remains pending.
  Read `docs/reports/2026-10-20_dis-p512-pooling.md` for progress and artifact identities.

### Completed full-image p512 custom comparison

- Both repaired full runs completed at 16:11 MSK. Fresh audits match both saved audits.
- Standard control reproduces all 668 production Top-1 predictions. The decoder repair passes.
- Full-image custom has 260/668 Top-1 hits. Cropped custom has 247. Standard has 274.
  Full-image custom improves cropped custom by 1.95 points but loses 2.10 points to standard.
- Full-image custom improves cropped Top-5/10 by 8.68/10.48 points.
  Custom remains below standard Top-5/10 by 0.30/0.15 points.
- Standard median/P95 is 878/1252 ms. Full-image custom is 1554/3002 ms.
  Both full runs have maximum thermal status 1 and the same stable Pixel PID.
- Keep standard no-segmentation p512 as the Pixel 8 default.
  These are whole-pipeline results. Index differences and the decoder repair limit causal attribution.
- Both no-bottle errors remain counted. HTTP-off and process-stop cleanup passed.
  Read `docs/reports/2026-10-20_full-image-p512-custom-pooling.md` for full evidence.

### Full-image control agreement failure

- The owner authorized a test-only decoder repair and a preserved v2 attempt.
  The repaired decoder follows production source-colour and alpha handling.
  Raw RGB captures avoid a second colour conversion during host validation.
  The new parity cohort includes all four affected images and one opaque control.
  All 29 host and 25 Android regression tests pass.
  Controlled device replay confirms restored production Top-20 on all four affected images.
  All 30 production-vector/ranking checks pass across GPU/CPU/GPU recreations.
  Both variants pass raw-RGB preprocessing, numerical checks, and independent pilots.
  The new full control is running. Complete-cohort custom quality remains pending.
- The full-image workflow stopped at 14:17 MSK after the standard control audit.
  All 668 requests completed without errors. Four Top-1 predictions differ from production.
  Top-1 fell from 274 to 272 hits. Full custom inference was not started.
- The test forces sRGB and uses ordinary alpha decoding.
  Production retains the source colour space and unpremultiplied RGB, then discards alpha.
- All four changed Top-1 inputs have embedded colour profiles. Three use RGBA PNG.
  All 601 unprofiled RGB assignments retain Top-1 and agree within 0.000002244 in scores.
- The original three parity inputs missed this decoder boundary.
  Match production decoding and add the affected inputs before another full comparison.
  Confirm the cause with a controlled device replay. Do not weaken the identity gate.
- The workflow performed successful HTTP-off and process-stop cleanup.
  All raw records remain preserved. No runtime repair or restart occurred during the status check.

### Full-image custom-pooling isolation

- The earlier four-condition test changed query crop and background treatment.
  Its custom weights therefore did not isolate a full-image pooling policy.
- The owner selected the previous matched custom reference index unchanged.
  The new query keeps source RGB and uses the bottle mask only for attention weights.
- The control reuses the exact production standard reference bytes.
  It must reproduce all previous control Top-1 predictions before comparison succeeds.
- Pixel capture checks compare source and frame pixel hashes, native dimensions,
  released NaFlex preprocessing, mask coverage, CPU/GPU vectors, and reference scores.
- Do not infer a pooling-only effect when the control and custom reference indexes differ.
  Read `docs/reports/2026-10-20_full-image-p512-custom-pooling.md` for new measurements.

### Pixel 8 default recommendation

- Compared the four-condition result with the existing no-segmentation control.
  The query manifests and all 668 accepted-answer assignments are identical.
- Fresh scoring reproduces no-segmentation Top-1/5/10 at 41.02/77.84/84.58%.
  The recorded median/P95 is 662/956 ms, with zero request errors.
- Experimental segmented p512 custom is lower at 36.98/68.86/73.95% and 1769/2428 ms.
- Recommend the existing p512 standard, no-segmentation GPU pipeline as the default.
  This compares whole pipelines. It does not isolate a pooling effect.
  No code or device setting changed for this recommendation.
- Read `docs/reports/2026-10-20_base-naflex-p224-custom-pooling.md` for the evidence.

### Final Pixel Base pooling results

- All four conditions passed their numerical gates, pilots, and 668-assignment audits.
- Standard/custom p224 Top-1 is 27.84/28.44%. Standard/custom p512 Top-1 is 33.83/36.98%.
- The p512 custom paired comparison has 37 Top-1 gains and 16 regressions over p512 standard.
- Custom p512 has the best quality in this experiment. Its median/P95 is 1769/2428 ms.
- Do not attribute its shorter measured latency to pooling alone.
  Standard p512 reached thermal status 3. Custom p512 reached thermal status 1.
  The independent pilot medians were 1310/1395 ms, in standard/custom order.
- The study uses one segmented bottle view and a matched 2,093-wine catalogue.
  It does not establish a win over the unchanged production no-segmentation pipeline.
- Read `docs/reports/2026-10-20_base-naflex-p224-custom-pooling.md` for the final comparison.

### Recovery-copy and host lifecycle decisions

- Finalized only a separate copy of the interrupted 536-assignment run.
  Derived thermal and memory maxima from saved telemetry. Preserved every raw source file.
- Recorded the copy's metadata finalization time explicitly.
  The original worker exit time and cause remain unknown.
- The frozen audit and dry resume-prefix check pass all 536 assignments.
  The continuation retains both no-bottle failures and all accepted alternative slugs.
- `launchctl submit` keeps failed jobs alive. A test submission exited with `EX_CONFIG`
  before it created the workflow logs or sent a device request. Removed that submission.
- Selected a double-fork standalone process with a separate session and ignored `SIGHUP`.
  The workflow's parent PID is 1. No permanent service or automatic restart was installed.
- Transferred the abandoned ADB forward to the new runner.
  The new runner owns forward removal before the comparison starts.

### Overnight host-worker interruption

- At 08:58 MSK, the full-v3 host runner and both coordinators are absent.
- The last response was saved at 04:34 MSK. All ten prediction files retain 536 rows.
- The Pixel app still has PID 9424. HTTP health is OK and idle. No native process restart
  is indicated by these observations. The host termination cause is not established.
- The saved waiting JSON does not prove that the comparison coordinator is alive.
- Abrupt termination bypassed final metadata and cleanup. The normal partial audit
  raises `KeyError: maximum_thermal_status`. Preserve the raw run and use a separate
  audited recovery copy if the owner requests continuation. Do not edit frozen tools.

### Base p224 fractional bottle coverage

- The owner extended the experiment to p512 custom pooling.
  Use the same coverage formula and the same fixed catalogue for all four conditions.
  A p512 standard/custom pair separates the pooling effect from the patch-budget effect.
  Preserve the original three reference indexes byte-for-byte in the v2 comparison.
- The modified p512 graph has zero error with zero log bias on four synthetic cases.
  Its independent attention oracle differs by less than 0.000000019.
  Added padding bias has zero output effect. Original FP16 payload bytes stay unchanged.

- The existing NaFlex library contains a complete Base model with a 224-patch budget.
  This is not the fixed 224 by 224 model. The model preserves image proportions.
- The report's `5a` profile assigns 0.1 to whitespace and 1.0 to bottle coverage.
  The report uses SO400M and desktop masks. Do not transfer its accuracy to Android.
- Selected one mobile bottle mask and one encoder pass as the Android-fit candidate.
  Label fusion and augmented reference views need separate latency and memory budgets.
- Added log weights only to the original attention-pooling logits.
  Original FP16 weight bytes remain unchanged. Zero bias reproduces the original output
  exactly on four synthetic inputs. The independent attention oracle differs by less
  than 0.00000004. Modified padding bias does not change the output.
- Use matching indexes for standard p224, custom p224, and standard p512.
  The same 2,093 original catalogue cuts prevent a catalogue-coverage confound.
- Keep the production p512 no-segmentation result as context only.
  A different segmentation policy cannot measure a pooling-only effect.
- Pixel CPU/GPU agreement and retrieval measurements passed in the final comparison.
  Read `docs/reports/2026-10-20_base-naflex-p224-custom-pooling.md`.

## 2026-10-19

### Rebuild verification boundary

- The rebuilt benchmark has a different APK container checksum.
  All 89 uncompressed ZIP entry payloads match the frozen v5 APK exactly.
  Keep device results bound to the installed APK checksum. Do not infer a new
  device validation from payload agreement alone.
- Release DEX retains the shared callback name `setDebugHttpServerEnabled`.
  This name is not a server class. Exact class and endpoint checks confirm that the
  release has no NanoHTTPD implementation or debug HTTP endpoints.

### Mobile segmentation and isolated benchmark implementation

- A host-only repair rejects the observed malformed status line and opens a fresh
  plain HTTP socket for a bounded retry. It never removes bytes from a response.
  Fault injection reproduces `BadStatusLine` and verifies exact request-byte recovery.
  Twenty host tests pass. Tests also reject a changed process and changed pack.
  The host has no current proxy entries. The original binary-prefix source remains
  unknown. Do not claim that a proxy caused the interruption.
  Continuation audits and copies the saved prefix into a new directory.
  Explicit process segments allow the original and new PIDs without hiding restarts.
  The source no-bottle error remains a failure. Re-ranking stays disabled.
  The q-000045 original-byte smoke passed all ten recipes in PID 9424 without a retry.
  Full v3 resumed at assignment 45. Its first three new records passed independent audit.
  The 44 inherited records pass exact prefix hashes. Source v2 files remain unchanged.
  Q-000045 smoke and cohort candidates match exactly. Complete quality remains pending.
- The v5 full repeat stopped at 44 of 668 responses with `BadStatusLine` on q-000045.
  The client received a binary prefix before an HTTP 200 status line.
  The transport root cause is not established. Do not attribute it to model failure.
  PID 20524 remained unchanged until explicit cleanup. No own native crash was recorded.
  Q-000040 returned an expected no-bottle error. The other 43 saved responses succeeded.
  All ten 44-row prediction files passed partial audit. Complete accuracy is unavailable.
  The finite coordinator successfully disabled HTTP and stopped only the isolated app.
  The owner's status check made no model, application, or transport change.
- The first full cohort stopped after 29 of 668 requests.
  Android cached and froze PID 13687 after the Activity stopped at 20:24:11 MSK.
  The LOW_MEMORY record has importance 400. No own native crash was recorded.
  A foreground service is appropriate for the owner-started, visible bulk computation.
  [Android service types](https://developer.android.com/develop/background-work/services/fgs/service-types#special-use)
  document `specialUse` and its manifest explanation.
  [Service startup](https://developer.android.com/develop/background-work/services/fgs/launch)
  requires prompt foreground promotion and a notification.
  [Wake locks](https://developer.android.com/develop/background-work/background-tasks/awake/wakelock/)
  support explicit CPU-awake lifetime. Release the lock when HTTP shutdown completes.
  These mechanisms do not guarantee protection from OOM.
- Candidate v5 passed all 102 repeated numerical checks.
  Its 30-image background gate completed in 18.49 minutes without errors or restart.
  All 300 recipe predictions and complete Top-20 scores match the v4 pilot exactly.
  All 68 background telemetry samples have importance 125 and active service protection.
  Maximum sampled heat is MODERATE. Peak sampled PSS is 2451.03 MiB, including startup.
  This gate uses shared query work. Do not compare its timings directly with the
  independent v4 per-recipe latency table.
- The repeated pilot stopped during its first cold request with `LOW_MEMORY`.
  Android recorded foreground importance 100 and about 2.4 GB RSS for PID 2123.
  The owner kept the benchmark visible. This is not the earlier background-only case.
  Before a new device run, test constant-tensor sharing with FP32 and no source
  quantization. The model bytes and recipes remain fixed.
  [LiteRT 2.2.0 GPU options](https://github.com/google-ai-edge/LiteRT/blob/v2.2.0/litert/c/options/litert_gpu_options.h)
  define constant sharing across subgraphs. The memory benefit is not yet measured.
- Candidate v4 completed the repeated numerical gate in one process without errors.
  All 102 checks passed. Minimum cosine was 0.9999999993.
  Maximum encoder component error was 0.00000425. Peak sampled PSS was 2,961.25 MiB.
  Do not interpret this as a controlled memory A/B result. Device state differed.
  Independent pilot `pilot-30-v3/` uses this candidate and the unchanged frozen pack.
- The independent pilot completed all 300 requests in one process with zero errors.
  Every GPU trace reports constant sharing and disabled source quantization.
  All ten prediction files contain exactly 30 distinct query records.
  The 57 requests shared with the original candidate retain identical Top-1 slugs.
  The largest shared Top-1 score difference is 0.00000138.
  Median complete-pipeline latency ranges from 4.09 to 13.74 seconds.
  Peak sampled PSS is 2173.36 MiB. Sustained thermal status reached `SEVERE`.
  Separate process stability from production latency and heat acceptance.
- The original v3 independent pilot stopped after 57 successful responses.
  The camera became foreground at 19:01:12 MSK. Android killed the cached benchmark
  process at 19:01:26 with `LOW_MEMORY` and importance 400.
  The active user remained 0. No own native crash was recorded.
  Activity-recreation support does not protect a background process from memory pressure.
  That original candidate had no foreground service.
  The later v5 candidate adds owner-approved foreground execution.
  Preserve the incomplete pilot instead of calculating a complete quality result.
- The repeated frozen-pack gate passed all 102 checks in PID 21034.
  Minimum encoder cosine was 0.9999999993. Maximum component error was 0.00000441.
  Complete bottle-score error stayed below 0.000000244.
  Segmenter raw tensors and legacy log weights matched exactly.
  Explicit Activity recreation preserved the same process and the loaded HTTP server.
  Evidence: `device-frozen-all-parity-v2/` in the isolated artifact root.
- The repaired all-recipe gate passed 102 numerical checks.
  Minimum encoder cosine was 0.9999999990.
  Maximum component error was 0.00000416.
  Legacy log weights matched without numerical error on the held-out control image.
  The final ten-epoch pilot selected epoch 8 by combined validation fitness 1.79737.
  Its catalogue-validation mask mAP50-95 was 0.93199.
  This is not wine-retrieval Top-1.
- The final frozen-pack gate received GPU and CPU responses before USB transport reset.
  The third response was not received. The run is incomplete.
  The original PID initially survived. The phone did not reboot.
  A later exit record identifies `LOW_MEMORY` with background importance 400.
  The active Android user was then 10, not the original user 0.
  No native crash of the benchmark application was recorded.
  Do not attribute an unrelated application's crash-buffer entry to this benchmark.
- The benchmark server originally belonged to the Activity lifetime.
  Keep the server at process lifetime. Order HTTP cleanup and model creation on one
  shared worker. Keep HTTP off at each fresh process start.
- The runner's first cleanup exception could prevent the final failure record.
  Catch cleanup errors individually. Always save the incomplete-run metadata.
  Reject a changed Android user before any new query or UI action.
  Do not switch a user profile without explicit owner approval.

- The three-image device exact-pooling gate passed all captured calculations.
  Minimum encoder cosine was 0.9999999858. Maximum component error was 0.0000192.
  Complete bottle-score error stayed below 0.000000208.
  The nine requests used grouped GPU, CPU, and GPU execution in one process.
- The all-recipe gate detected a legacy mask-weight mismatch before quality testing.
  The cause was BOX endpoint inclusion and coefficient rounding.
  [Pillow 11.3 source](https://github.com/python-pillow/Pillow/blob/11.3.0/src/libImaging/Resample.c)
  uses an open lower endpoint, a closed upper endpoint, and 22-bit integer coefficients
  for L-image resizing. Plain double averages do not reproduce that rounding.
  Added two fixed fixtures before repeating the device gate.
- Removed the unused 4.82 GB external device-pack copy after the private pack loaded.
  The complete host copy and the working private pack remain available.

- Independent instance masks are required for nested bottle and label targets.
  The Ultralytics overlap-map target removes label pixels from the bottle target.
  Training v2 was stopped and rejected after its first epoch.
  Training v3 uses `overlap_mask=False` and preserves both targets.
- The development epoch-zero mobile export passed three held-out catalogue checks.
  The largest detection-coordinate error was 0.00290 pixels.
  The largest prototype error was 0.0000263.
  These checks compare PyTorch and desktop LiteRT CPU raw outputs.
  They do not establish device agreement or retrieval quality.
- Seven exact FP32 reference galleries require 3,953,092,784 bytes including owners.
  The development device pack requires about 4.82 GB with models and metadata.
  This is an isolated measurement pack. It is not the main application's pack.
- Fourteen isolated unit tests cover score aggregation, full-score fusion, mask
  coverage, padding policy, source mapping, cardinal guards, and neck direction.
- The first device preflight sent zero images because the application could not
  access an ADB-created external pack directory.
  Use app-private storage through debug `run-as`. Do not use world-writable modes.
- The pilot checkpoint policy uses the best catalogue-validation fitness within the
  first ten complete epochs. The original cosine schedule remains a 30-epoch schedule.
  The stopping policy was fixed before adapted `my-failed-2` inference.
  No evaluation image, mask, accepted answer, or retrieval result selects the model.
- Runtime masks use CPU YOLO11n-seg with bottle and label classes.
  RGB rendering, float mask sampling, prototype-grid geometry, and the original-view
  margin are declared mobile adaptations. The exact desktop scores do not transfer.

### Retrieval table and Android measurement boundary

- Located the supplied table's desktop campaign under
  `svoe-vino-lab/internal/my-failed2-six-variants-20261017/` in the T7 workspace.
- Its extension protocol pins `google/siglip2-so400m-patch16-naflex` at revision
  `cc24074f717b612951c2dead130904ab9b65a81e`.
- Its masks come from saved package and label segmentation, including SAM3 labels.
- Its frozen `my-failed-2` set has 668 assignments on 627 distinct images.
- The current main application instead uses Base p512 and has no separate label
  segmenter. Reusing its vectors would not reproduce the requested configurations.
- Exact retrieval reproduction can use frozen masks, but that measurement excludes
  on-device segmentation. A complete offline adaptation needs a different segmentation
  path and must report that change.
- Pixel 8 remains connected and authorized. The new main ID is not installed.
- No benchmark inference, APK installation, or export ran during this preflight.
- Plan `docs/plans/06_android-retrieval-variants.md` waits for the measurement choice.

### Offline selection and initial measured control

- The owner selected the complete offline adaptation after the initial preflight.
- The current installed Base p512 control completed 668 `my-failed-2` assignments.
  Top-1/5/10 were 41.02 / 77.84 / 84.58 percent. All vectors came from GPU.
- The default catalogue lacks every accepted slug for 42 assignments.
  Encoder, catalogue coverage, reference gallery, and segmentation all differ from the
  requested desktop variants. A future delta is not a segmentation-only result.
- All 660 assignment predictions on shared images equal the previous full control.
- Main-reference catalogue masks provide 2,259 valid bottle/label training examples.
  The wine-group split has 2,031 training images and 228 validation images.
  Excluding the union of both evaluation cohorts removes six catalogue sources.
  The verified training overlap with 3,039 evaluation-image hashes is empty.
- Ultralytics 8.4.40 treats the literal run name `model` as a special value.
  It replaced that name with a source-model path. Setup v1 stopped before training.
  Use the explicit name `bottle-label` and check output-directory containment.
- The released SO400M LiteRT file stores 448 buffers after its FlatBuffer header.
  `ModelT.Pack` alone omits that external payload. Candidate v1 was rejected.
  Candidate v2 relocates external offsets and preserves the full payload SHA-256.
- Candidate v2 adds one log-weight input to the 16 pooling softmax heads only.
  It does not change the transformer valid-patch mask.
  Zero log weights give zero component error against the original LiteRT graph on two
  synthetic fixtures. Native checkpoint cosine exceeds 0.9999997.
  Perturbing padded-position logits by 100 does not change either checked vector.
- Variants 1 through 4, 7, and 9 use `always-mean75`: bottle weight 0.75 and label
  weight 0.25. Variant 10 uses `always-mean50`.
  All label-space variants use `l-7f-rot5`, with aligned reference labels and no query
  bottle or query label rotation in label space.
- These are preparation and control results. Android GPU validation and the ten
  adapted retrieval runs remain required.

### Measured complete p512 and DIS dual-GPU combination

- The separate `chtozavino.alolalab.com.dualgpu` debug APK completed the thirty-image
  pilot and all 3,409 full `my` assignments on Pixel 8.
- Both model accelerators were GPU for every successful request.
  CPU fallback was disabled for explicit debug requests.
- PID `19651` remained unchanged through the pilot, full run, post-run probes, and
  closure of both GPU models.
- No native abort or fatal application exception was observed.
- Five positive assignments failed because DIS found no main object.
  These failures are not GPU crashes and remain in the positive quality denominator.
- DIS improved Top-1 by 95 hits, from 2,052 to 2,147 of 2,970 positives.
  This is a 3.20-percentage-point increase, with 262 gains and 167 losses.
- Top-5 increased from 87.10% to 88.18%. Top-10 increased from 90.03% to 90.34%.
- Catalogue-covered Top-1 is 76.68%. The pack still cannot answer 170 positives.
- Negative forbidden Top-1 matches decreased from 73 to 69 of 430.
  Another predicted slug does not establish correct recognition for a negative query.
- All 9 no-match queries still returned a nearest wine.
- Client median latency increased from 924 to 1,319 ms.
  P95 increased from 1,479 to 2,343 ms.
  These are HTTP pipeline times, not isolated encoder times.
- Full-run sampled PSS peaked at 1,434.2 MiB. The cold pilot peak was 1,565.0 MiB.
  PSS does not measure the complete GPU allocation peak.
- The full run reached `MODERATE`, not `SEVERE` or `CRITICAL`.
  Per-request ADB checks increased idle intervals outside the HTTP timer.
  This timing difference prevents a controlled power or thermal comparison.
- The 97.04-minute bulk wall time contains 858.781 seconds outside HTTP call timers.
  The baseline contains only 13.178 seconds of that host overhead.
- Three explicit post-run p512 GPU/CPU comparisons passed while DIS remained on GPU.
  Minimum cosine was `0.9999999999044907`.
  Maximum component error was `0.000003159046173095703`.
  These explicit CPU requests were not fallback or part of the full-run metrics.
- All 271 repeated-image groups kept a consistent Top-1 prediction.
- The result establishes measured stability for this Pixel 8, graph, and worker runtime.
  It does not establish dual-GPU compatibility for another phone or a legacy graph.
  It does not isolate the cause of the historical model-creation abort.
- The main source and APK hashes are unchanged. The main guard remains active.
- Read `docs/reports/2026-10-19_pixel8-p512-dis-dual-gpu-my.md` for the exact scope.

### Scope of the inherited dual-GPU guard

- The owner asked why the application moves SigLIP2 to CPU when DIS uses GPU.
- `ImageRecognition.kt` applies this decision unconditionally when both requested
  accelerators are GPU and DIS actually runs on GPU.
- This decision is application code, not a detected Android hardware restriction.
- The historical query-57 crash occurred in `libLiteRtClGlAccelerator.so` during GPU
  `CompiledModel` creation with the fixed Base/224 pipeline.
- The old code created and closed DIS before creating and closing SigLIP2 on each
  request. The code did not retain both GPU models together in that path.
- Commit `9fe721dc` introduced model reuse and the conservative dual-GPU guard together.
- Later stable runs therefore do not isolate which change prevented the native abort.
- The crash evidence does not establish that simultaneous GPU model residency caused
  the old failure or is impossible for the complete p512 graph.
- The complete p512 runtime now keeps GPU lifecycle operations on one dedicated thread.
  Its GPU verification used no query segmentation.
- Complete p512 plus DIS with both models on GPU remains unverified.
- A DIS CPU plus p512 GPU benchmark can use the current application without bypassing
  the guard. The guard must not be presented as a proven platform limitation.
- This investigation did not change the application or start a benchmark.

### Complete Base p512 full my findings

- The full run used the same 3,409 frozen assignments as the fixed Base/224 plus DIS
  baseline. All 3,031 distinct input files passed SHA-256 verification.
- The current scorer accepts alternative positive slugs for the same image hash.
  The older local query builder omitted this expansion for 152 assignments.
  The actual full runs used identical queries, not the older preflight query file.
- Positive Top-1 improved from 33.27% to 69.09%.
  Top-5 improved from 56.46% to 87.10%. Top-10 improved from 64.41% to 90.03%.
- Paired Top-1 results had 1,213 gains and 149 losses.
  The comparison changes the encoder and removes segmentation together.
  It cannot isolate the encoder effect.
- The pack covers accepted wines for 2,800 of 2,970 positive assignments.
  Covered-only Top-1 is 73.29%. Covered-only Top-10 is 95.50%.
- Negative forbidden Top-1 matches increased from 42 to 73 of 430.
  Returning another slug does not prove correct recognition on a negative assignment.
- All 9 no-match queries still return a nearest wine.
  This run does not validate unknown-wine rejection.
- Full client median latency was 924 ms. P95 was 1,479 ms.
  The slowest request took 5,837 ms and included a new model session.
- All 3,409 calls returned HTTP 200 in PID `24675` without an observed CPU fallback.
  A post-run probe still used GPU.
- Peak sampled PSS was 955.2 MiB. This value does not include every GPU allocation.
- The 55-minute workload reached thermal status `SEVERE` after 1,264.3 seconds.
  The maximum sampled battery temperature was 45.2 degrees Celsius.
  The short pilot did not predict this sustained thermal behavior.
  The full run fails the short-pilot thermal gate but never reached `CRITICAL`.
- HTTP was disabled after the test. The original power setting was restored.
- Read `docs/reports/2026-10-19_pixel8-base-p512-full-my.md` for the complete result.

### Verified complete p512 integration

- The complete v0.2.0 graph is distinct from the rejected split GPU exports.
- The frozen complete-graph index contains 2,193 rows with 768 dimensions.
- Every one of the current 2,093 catalogue wines occurs in this index.
- The new exporter selects rows by slug without changing their float32 values.
- The maximum packaged vector norm error is `1.7881393432617188e-7`.
- The new built-in pack contains one unrotated reference for each wine.
- The old generated built-in pack also contained one reference for each wine.
- Older documentation described a 72-angle pack that was not actually bundled.
- A p512 72-angle index needs a separate calculation with this exact encoder.
- The current integration does not make that calculation or claim its coverage.
- The new pack is 402,692,669 bytes.
- Its SHA-256 is `4307a92be20fc53bec18f922ae80b60d92fc219c2a8e22f981f8c8778117a128`.
- The Pixel 8 became visible after host validation.
- The version 0.2.0 debug APK installed as an update over version 0.1.4.
- The phone was locked before the device test could enable the HTTP setting.
- No settings or history backup was exported from the phone.
- The owner then unlocked the phone and confirmed no query segmentation.
- The first-start check selected GPU for complete Base NaFlex p512.
- CPU/GPU reference cosine was `0.9999999999384342` with maximum error `0.0000039041`.
- Fourteen device vectors agreed with cached desktop vectors at cosine of at least
  `0.9999999999289232` and maximum error of at most `0.0000015004`.
- All thirty GPU pilot requests succeeded in one process.
- Warm server latency was 514.8 ms median and 748.8 ms P95.
- Peak sampled PSS was 925.3 MiB. Android thermal status remained `NONE`.
- The stratified pilot returned 17 of 24 positive Top-1 hits and 21 of 24 Top-5 hits.
- These pilot counts do not estimate full `my` accuracy.
- UI recognition of the transparent reference returned `Пино Нуар` at 100 percent.
- The first UI embedding stage took 3,319 ms with a new GPU session.
- The new history row remained visible after a deliberate cold restart.
- HTTP stayed off after the restart. Test device files and forwarding were removed.
- Read `docs/reports/2026-10-19_base-p512-default.md` for measured integration results.

### Scope of NaFlex measurements

- The October 19 measurements used the split exports in this repository.
- The separate `siglip2-naflex-litert` repository contains a verified v0.2.0 GPU library.
- Its October 5 and 6 tests covered sixteen profiles on Pixel 8 and realme RMX3890.
- Its Base p512 Pixel encoder P95 was `401.5` ms in the profile sweep.
- Its Base p512 Eval run accepted `85/99` known wines at rank 1.
- Its Eval encode and search median was `533.7` ms.
- These measurements use a different graph and test method from the split pilot.
- The split pilot does not invalidate the separate library measurements.
- Before the main-pipeline change, the separate library was not integrated into this application.
- Read `docs/naflex-implementations.md` for source paths and measurement scope.

### Focused Pixel 8 SigLIP2 Base pilot

- The device was a Google Pixel 8 with serial `41231FDJH002WZ`.
- The device ran Android 17.
- The application version was `0.1.4`.
- The NaFlex source was `google/siglip2-base-patch16-naflex`.
- The source revision was `b53b807d3a2d5e2b3911292f2d69e5341cdc064c`.
- The pilot used one deterministic 30-image set for all variants.
- The fixed p224 CPU run completed 30 of 30 requests.
- Its median latency was `9274.397` ms.
- Its p95 latency was `10525.581` ms.
- Its peak PSS was 1,469,292 KiB.
- The p256 standard CPU run completed 30 of 30 requests.
- Its median latency was `11781.540` ms.
- Its p95 latency was `13530.799` ms.
- Its peak PSS was 1,477,980 KiB.
- The p256 5a CPU run completed 30 of 30 requests.
- Its median latency was `11800.106` ms.
- Its p95 latency was `13806.638` ms.
- Its peak PSS was 1,480,138 KiB.
- The p512 standard CPU run completed 30 of 30 requests.
- Its median latency was `22219.217` ms.
- Its p95 latency was `24148.602` ms.
- Its peak PSS was 1,514,782 KiB.
- All 120 measured requests returned HTTP 200.
- Every returned vector was finite and had 768 dimensions.
- No application process restarted.
- Android thermal status stayed at `NONE`.
- Fixed p224 CPU/GPU cosine was `0.99913565`.
- Fixed p224 CPU/GPU maximum error was `0.00458609`.
- Base NaFlex p256 CPU/GPU cosine was `0.95890638`.
- Base NaFlex p256 CPU/GPU maximum error was `0.03201315`.
- Base NaFlex p512 CPU/GPU cosine was `0.92733709`.
- Base NaFlex p512 CPU/GPU maximum error was `0.06663840`.
- The p256 5a variant used the same rejected p256 backbone.
- The p256 standard LiteRT maximum export error was `0.00129485`.
- The p256 5a LiteRT maximum export error was `0.00089574`.
- The p512 standard LiteRT maximum export error was `0.00113583`.
- No encoder passed all pilot gates.
- No new full `my` run started.
- The current pack has one reference for each wine.
- `top2-mean` therefore equals `max` for the current pack.
- The report is
  `docs/reports/2026-10-19_pixel8-siglip2-base-pilot/report.md`.
- The final debug APK SHA-256 was
  `49c57470bfe03dabab7278ab29b4da8e2e442305f5cf128f1b877247664f260b`.
- The final debug APK installed on the Pixel 8.
- The fixed-224 control pack was active after the test.
- The debug HTTP server was off after the test.
- The ADB forwarding rule was removed.
- Approximately 2.6 GiB of temporary device packs and backups were removed.
- `lintDebug`, `testDebugUnitTest`, and `assembleDebug` passed.
- Eight Python exporter and pack-builder tests passed.
- Sixteen Workbench remote-run tests passed.

### SigLIP2 SO400M NaFlex exact split on Pixel 8

- The source model was `google/siglip2-so400m-patch16-naflex`.
- The source revision was `cc24074f717b612951c2dead130904ab9b65a81e`.
- The selected patch limit was 512.
- The first LiteRT model applied patch projection and the vision transformer.
- The first LiteRT model returned 512 by 1,152 patch tokens.
- The second LiteRT model applied the original pooling path.
- The second LiteRT model returned one 1,152-dimensional vector.
- PyTorch split cosine was `1.0`.
- PyTorch split maximum absolute error was `0.0`.
- LiteRT end-to-end cosine against PyTorch was `0.99999994`.
- The backbone file size was 825,851,536 bytes.
- The pooling file size was 27,870,656 bytes.
- The source position table size was 1,179,648 bytes.
- The external pack used version `naflex-p512-mask-v2-20261019`.
- The external pack contained 2,201 wines and 158,472 vectors.
- The pack contained 72 reference vectors for each included wine.
- The pack size was 1,846,711,927 bytes.
- The pack SHA-256 was
  `963b33daaa4b6a52eddeda5e1929c7cdd246f409dd8d03bdb4e1764921bf6d11`.
- The device was a Google Pixel 8 with serial `41231FDJH002WZ`.
- The device ran Android 17.
- The LiteRT GPU delegate compiled all 1,515 backbone operations.
- The GPU request completed in 225.768 seconds.
- The GPU vector produced the false Top-1 result `shardone-premium` at `0.811958`.
- A finite-value check did not detect this compatibility failure.
- The CPU request completed in 263.963 seconds before the safety change.
- The CPU vector produced the expected Top-1 result `chin-chin-vermentino` at
  `0.977004`.
- The application now disables GPU for the NaFlex runtime.
- `Auto` now selects LiteRT CPU/XNNPACK for the NaFlex runtime.
- Explicit GPU selection now returns HTTP 502 with a clear compatibility error.
- The accelerator check key now includes the runtime, patch limit, DIS hash, and
  SigLIP2 backbone hash.
- The final `Auto` request completed in 256.082 seconds.
- The final request returned `chin-chin-vermentino` at `0.977004`.
- The debug APK size was 478,043,213 bytes.
- The debug APK SHA-256 was
  `5862b0e138c0026764d652ded052ae8e9544a041928e7a5fb3df8037839dfbae`.
- The final debug APK installed on the Pixel 8.
- The final device settings used DIS `Auto` and SigLIP2 `Auto`.
- The final automatic SigLIP2 accelerator was CPU.
- The debug HTTP server was off after the test.
- The ADB port forward and temporary device pack archives were removed.
- Python split and pack-builder tests passed.
- `testDebugUnitTest`, `lintDebug`, and `assembleDebug` passed.

### HEIC and HEIF Android input validation

- The code change added `image/heic` and `image/heif` to the gallery picker allowlist.
- The recognition path already used `ImageDecoder` on Android 9 and later.
- The history path saved the processed white-background bitmap as JPEG.
- The test used a Google Pixel 8 with serial `41231FDJH002WZ`.
- The device ran Android 17 at API level 37.
- The test converted query `q-000004` to a real HEVC HEIF image.
- MediaStore identified the `.heic` file as `image/heic`.
- MediaStore identified the `.heif` file as `image/heif`.
- The system picker showed both files.
- The application decoded and showed the HEIC image.
- Recognition returned `Каберне Фран 1890` at 81 percent similarity.
- The history page showed the new row and its preview.
- The row and preview stayed visible after a cold application restart.
- TalkBack opened the system picker without an application error.
- The accessibility tree exposed the gallery action, both file names, the selected
  preview, and the history preview.
- TalkBack was restored to its original off state after the check.
- The application process log contained no application warning, fatal exception, or
  native abort.
- The two temporary gallery files were removed after the test.
- All 35 debug unit tests and all 32 release unit tests passed.
- Debug and release lint passed.
- Debug and release APK assembly passed.

### Pixel 8 full `my` validation

- The source commit was `f8b15c210f82f9dd970493dad995c13690b421c8`.
- The test used a Google Pixel 8 with serial `41231FDJH002WZ`.
- The device ran Android 17 at API level 37.
- The installed application had version 0.1.4 and version code 5.
- The package ID was `chtozavino.alolalab.com`.
- The APK size was 477,573,550 bytes.
- The APK SHA-256 was
  `41ea00bd1baa8d4235f276579dca8a86db16570f5bdd3635b9eeb54e25793154`.
- The model pack version was `20261003-dis-yolo26n-seg`.
- The model pack contained 2,093 wines, 2,093 images, and 2,093 vectors.
- The model pack used one vector for each wine.
- This APK did not contain the 72-angle reference index.
- The model pack size was 432,436,177 bytes.
- The model pack SHA-256 was
  `c55203fdaa2b2f1abb034eb22793714465ae265298ce8b4a3ef9a6dfe8cd1616`.
- The saved settings selected DIS GPU and SigLIP2 CPU.
- `GET /healthz` reported the correct pack version, wine count, and DIS mode.
- One three-photo check processed all three photographs.
- Its technical text reported DIS GPU and SigLIP2 CPU.
- A second three-photo check stopped after its first photograph.
- Its technical text reported `Обработано фото: 1 из 3`.
- Its technical text reported `Ранний выход: высокое сходство`.
- The first photograph had Top-1 0.9425 and a Top-1 to Top-2 margin of 0.0919.
- These values exceeded the configured score 0.93 and margin 0.08 thresholds.
- The full run called `POST /v1/match?k=20` through an ADB port forward.
- The run used one worker and one Android application process.
- The run evaluated 3,409 queries in 5,986.9 seconds.
- The query set had 2,970 positive queries, 430 negative queries, and 9 no-match
  queries.
- Positive R@1 was 0.3327.
- Positive R@5 was 0.5646.
- Positive R@10 was 0.6441.
- Positive MRR was 0.4402.
- Median latency was 1,699 ms.
- P95 latency was 2,156 ms.
- Maximum latency was 4,684 ms.
- 99.85 percent of queries completed within 3,000 ms.
- Five positive queries returned HTTP 502.
- These five queries represented four unique image files.
- Each repeated check reported `DIS не нашёл главный объект`.
- The errors were segmentation refusals and not process failures.
- The negative set had 42 target-slug false matches at rank 1.
- The no-match set had zero correct rejections and nine rank-1 false matches.
- The application PID stayed `30129` through the full run.
- The Android crash buffer was empty after the run.
- Logcat contained no `FATAL EXCEPTION`, `Fatal signal`, `SIGABRT`, or
  `libLiteRtClGlAccelerator` error.
- The debug HTTP server was off after the run.
- The ADB port forward was absent after the run.

## 2026-10-03

### Five-degree Android reference rotation

- The Android search already keeps the maximum score for each `wine_slug`.
- The runtime needs no additional query embedding for rotation support.
- The offline index now provides 72 rows per catalogue image.
- Rotation occurs after DIS and `white_background`.
- Rotation occurs before `square_on_white` and the 224 by 224 resize.
- This order keeps the 0-degree frame equal to the existing Android input.
- For 2,093 wines, float32 vectors need 462,938,112 bytes.
- The old one-vector index needs 6,429,696 bytes.
- The rotation sequence adds 456,508,416 bytes before ZIP overhead.
- The generated index and APK were not built during this implementation step.

- The official Ultralytics YOLO Flutter release `v0.6.6` supplied
  `yolo26n-seg_w8a32.tflite`.
- The YOLO file is 3,234,566 bytes.
- Its SHA-256 is
  `3a9d800e59071e32516511bd788bf73a229e8b62c09eed96d6789894bc238acf`.
- The embedded metadata identifies Ultralytics version 8.4.104, task `segment`, image
  size 640, and COCO class 39 as `bottle`.
- The embedded metadata declares the AGPL-3.0 license.
- Model-pack format version 3 adds the YOLO file and keeps the same 2,093 catalogue
  vectors, wines, and images as the earlier DIS test.
- The version 3 pack is 432,436,177 bytes.
- Its SHA-256 is
  `c55203fdaa2b2f1abb034eb22793714465ae265298ce8b4a3ef9a6dfe8cd1616`.
- The Pixel 8 test used YOLO on CPU.
- The controlled comparison used SigLIP2 on CPU for DIS and YOLO.
- DIS returned 100 predictions and accepted 38 of 100.
- DIS median latency was 2,024.5 ms and mean latency was 1,981.25 ms.
- YOLO found a bottle in 70 of 100 images.
- YOLO returned 70 predictions and accepted 23 of 100.
- YOLO median latency was 1,234 ms and mean latency was 1,312.99 ms.
- Both segmentation modes were correct for 20 queries.
- DIS alone was correct for 18 queries.
- YOLO alone was correct for 3 queries.
- Neither mode was correct for 59 queries.
- The 30 YOLO failures mainly contain label close-ups or images without a complete
  bottle.
- Both 100-request runs completed in one application process.
- Neither run caused `SIGABRT` or another native abort.
- The DIS result file SHA-256 is
  `e44ea3ff502b3ee09f87bbd2e52680f7b8d8e9082d845852c612933deba172f8`.
- The controlled YOLO result file SHA-256 is
  `c15984953177af732a2aa9e87d9755d36cb60fec013e666337e8a76006a3e232`.
- The debug HTTP server and ADB port forward were disabled after the tests.
- Six Python pack-builder tests passed.
- `testDebugUnitTest`, `lintDebug`, and `assembleDebug` passed with JDK 21.
- The final debug APK is 576,503,447 bytes.
- Its SHA-256 is
  `18800aadae4646a9f06f4605b965f3fe4a1e764d6f7f7f1289c0e38942b47964`.
- The final debug APK installed on the Pixel 8 with serial `41231FDJH002WZ`.
- The installed manifest reports format version 3, 2,093 vectors, and the verified
  YOLO model.
- The saved device settings select YOLO and SigLIP2 CPU.
- The debug HTTP server setting is off.

- The Pixel 8 evaluation used Android application version 0.1.4.
- The debug server reported model pack `20260929-dis-main-alpha` and 2,093 wines.
- ADB forwarded host port 18088 to device port 18088.
- The run used the saved DIS GPU and SigLIP2 GPU selections.
- The attached evaluation set contained 100 WebP query images.
- The ZIP structure and CRC values were valid.
- The supplied `checksums.sha256` file did not match 42 query images.
- The expected-answer file matched the actual SHA-256 value of all 100 query images.
- The first continuous run completed queries 1 through 56.
- Query 57 caused a native `SIGABRT` in `libLiteRtClGlAccelerator.so`.
- The stack trace shows the failure during GPU `CompiledModel` creation.
- The process uptime was 392 seconds when the failure occurred.
- Three application restarts completed queries 57 through 100 in batches of 20, 20,
  and 4 queries.
- The final `predictions.jsonl` contains 100 unique queries and no null prediction.
- The minimum latency was 3,923 ms.
- The median latency was 4,669 ms.
- The mean latency was 4,826.68 ms.
- The maximum latency was 6,948 ms.
- The accepted-answer check used the primary slug, `alternative_slug_1`, and
  `alternative_slug_2`.
- The result had 38 accepted predictions from 100 queries.
- All 38 accepted predictions matched the primary slug.
- The alternative slugs did not add an accepted prediction.
- The legacy `alternative_slug` field did not change the result.
- The final file SHA-256 is
  `3842219ad3130c4403ce3c81bb35394046da3c6e21f3d7fea2f019c23611796d`.
- The release application replaced the debug application after the run.
- The debug HTTP server setting and ADB port forward were disabled after the run.

## 2026-09-29

- GitHub repository `s1mb1o/svoe-vino-lab-dev` is private.
- The Android GitHub release URL is
  `https://github.com/s1mb1o/svoe-vino-lab-dev/releases/tag/android-v0.1.4`.
- The release is a pre-release.
- `chtozavino-0.1.4-release-test-signed.apk` is 441,392,911 bytes.
- Its SHA-256 is
  `1a846cf82f06fc24f495bb6008b6bc775ef4aae25df175b5c93a6a7a46f1dfd0`.
- `chtozavino-0.1.4-debug.apk` is 576,503,447 bytes.
- Its SHA-256 is
  `fc4cf0f44b8fefcff5286b04746efb7fa44b9742ec6df282aa0cc959f6777ea2`.
- GitHub reported both APK assets as `uploaded`.
- GitHub reported the same SHA-256 values as the local files.
- Both APK files use the Android debug certificate.
- The test-signed release APK has no debug HTTP server.
- The debug APK has the bulk-test server, which is off by default.
- A future APK that uses a permanent production certificate can require removal of
  this test version before installation.

- The 10-query Pixel 8 smoke run contains 10 photographs of only four wine SKUs.
- The run uses the first 10 positive rows of the sorted `my` test set.
- It is not a balanced or representative sample.
- Six photographs belong to two visually similar Abrau-Durso Reserve bottles.
- The Pixel 8 result has three matches at rank 1, three at rank 2, three at ranks 6 or
  9, and one result outside the first 20 candidates.
- Three rank-2 errors have score gaps of 0.0017, 0.0019, and 0.0042.
- The catalogue vectors of the two Abrau-Durso Reserve bottles have cosine 0.975512.
- Their 224 by 224 DIS-preprocessed catalogue images have a mean absolute pixel
  difference of 2.73 on the 0 through 255 scale.
- SigLIP2-base at 224 pixels does not reliably separate these two catalogue references.
- Two Pinot Noir photographs selected another Pinot Noir SKU at rank 1.
- The correct Pinot Noir SKU was at rank 6 for both Android queries.
- One label close-up of `Сира Нуво` selected another Syrah SKU at rank 1.
- The correct `Сира Нуво` SKU was at rank 9.
- The index holds one `full` catalogue vector for each of these wines.
- Label close-ups and scene photographs therefore compare against one full-bottle
  reference.
- The desktop run of the same `android-siglip2-base-224-dis-white` pipeline also had
  exactly three rank-1 matches for these same 10 photographs.
- The low smoke result is not specific to Android GPU or LiteRT execution.
- The complete desktop benchmark of this pipeline had 43.05 percent recall@1, 73.10
  percent recall@5, and 80.15 percent recall@10 across 1,647 positive queries.
- The 30 percent result MUST NOT be used as the final Android accuracy estimate.
- The labelled collage is
  [android-pixel8-smoke-10-collage.png](docs/test-results/android-pixel8-smoke-10-collage.png).

- The debug application server listens on `*:18088` on the Pixel 8.
- `GET /healthz` reported pack `20260929-dis-main` and 2,093 wines.
- The Pixel 8 Wi-Fi address was `192.168.86.51` during the test.
- The host could not open the Wi-Fi address because the network blocked the incoming
  connection.
- ADB forwarding from host port 18088 to device port 18088 worked.
- Workbench used `device_ip=127.0.0.1` through this forwarding path.
- The clean `/v1/eval/predict` run answered 10 of 10 requests with no error.
- It gave recall@1 0.3 and median latency 4,349 ms.
- The clean `/v1/match?k=20` run answered 10 of 10 requests with no error.
- It gave recall@1 0.3, recall@5 0.6, recall@10 0.9, and median latency 4,597 ms.
- Both runs used the same installed DIS and SigLIP2 pipeline.
- The new debug APK is 576,503,447 bytes.
- Its SHA-256 is
  `9066ff9c377305d8eef2880d0c127a276d841bfd52d50af31c16740b53503279`.
- Gradle confirmed NanoHTTPD 2.3.1 in `debugRuntimeClasspath`.
- Gradle found no NanoHTTPD dependency in `releaseRuntimeClasspath`.

- The project has no release signing configuration.
- `assembleRelease` creates `app-release-unsigned.apk`.
- The unsigned APK cannot be installed or published before signing.
- The optimized release APK is 441,352,932 bytes.
- Its SHA-256 is
  `a5cf1ce4a42715c521579a899c5dc9bbeddb32b5ae55c9ad54c82dbd19d765e4`.
- R8 and resource shrinking reduced the APK after the transparent image export.
- The APK contains the 429,200,870-byte model pack without compression.
- The embedded pack SHA-256 matches the exported pack SHA-256.

- Android cosine search does not read the catalogue display image.
- It reads `vectors.f32`, `candidates.jsonl`, and `wines.jsonl`.
- The application uses the catalogue display image only in the user interface.
- The Android pack does not need the image that produced an embedding.
- The Android pack does not need a large non-segmented `main` or `main_patched` image.
- The exporter uses the selected source image digest to find the compatible vector.
- It uses the related `image_derivative(kind=package)` file as the display image.
- The exporter converted 1,939 `crop` cuts and 154 `seg` cuts.
- All 2,093 exported files are transparent WebP images.
- Each exported image has a long side of 1,024 pixels or less.
- The generated `images.zip` is 59,205,972 bytes.
- The generated model pack is 429,200,870 bytes.
- Its SHA-256 is
  `cb181ce8f5583d92c800014c083eb75cc0458fa205407aa24bc032a80b050ec3`.
- The previous model pack was 531,950,661 bytes.
- The new pack is 102,749,791 bytes smaller.
- This change reduced the pack by 19.3 percent.
- Thirteen active workbench rows use a private slug that starts with `__`.
- The exporter omitted these private rows because they do not have a public page URL.
- Five public active wines have no selected source image.
- The exporter omitted these five wines as before.

- The version 0.1.4 screenshot set uses real states from the installed Pixel 8
  application.
- The source screenshots are 1,080 by 2,400 pixel PNG files.
- The website files are 1,080 by 2,199 pixel WebP files without Android system bars.
- The photo example matched `Пино Нуар` at score 0.91.
- The debug views show the real DIS mask, crop, and white-background square from this
  run.
- The history page shows the saved `Пино Нуар` row at 91%.
- Google Code Scanner read physical EAN-13 `4630037250909` through the Pixel 8 camera.
- The local code index matched this code to `Шато Тамань. Каберне Совиньон` at 100%.
- The scanner displayed its manual-input fallback before it read the physical code.
- The capture restored the original Pixel 8 dark theme and disabled System UI demo
  mode.

- Android treats `Chtozavino.alolalab.com` and `chtozavino.alolalab.com` as different
  application IDs.
- The Google Pixel 8 did not contain the old application ID before installation.
- The Realme contained the old application ID.
- Removing the old Realme package also removed its local settings, model pack, and
  history.
- The Pixel 8 had 6.1 GB of free data storage before installation.
- The full 576,503,269-byte APK installed successfully on the Pixel 8.
- The installed application uses `chtozavino.alolalab.com` at version 0.1.4.
- The first start installed 2,093 catalogue images, 2,093 wines, and 2,093 vectors.
- The installed private files use approximately 667 MiB.
- The first-start accelerator check selected GPU for DIS and SigLIP2.
- A full Pixel 8 run matched the source `Пино Нуар` wine at score 0.91.
- The run used DIS GPU for 2,463 ms, SigLIP2 GPU for 2,134 ms, and local search for
  100 ms.
- The DIS mask debug view opened after the run.
- The history row stayed after an application restart.
- The result link opened the exact wine page in Chrome.
- The settings product link opened `https://vino-svoe.ru` in Chrome.
- The Pixel 8 used its dark system theme during this check.
- The settings page showed the complete pack information, both accelerator controls,
  the automatic GPU selections, version 0.1.4, and the product-site link.
- Both `Авто` filter chips were selected.
- No settings value or control was clipped after the system back animation completed.

- The Realme history preferences file existed before the version 0.1.3 update.
- The file contained an empty map.
- Its modification time matched the cleanup of the earlier four device-test rows.
- The application writes history after a successful image or code recognition.
- A version 0.1.3 recognition added one persistent `Пино Нуар` row at score
  0.9097248.
- The result page showed `Сходство: 91%`.
- The history page showed `Фото · сходство 91%`.
- The empty history was caused by the earlier test cleanup.
- The version update did not clear application data.
- The system theme was light before the theme test.
- The application changed to its dark color scheme after the system changed to dark mode.
- The application changed back to its light color scheme after the system setting was
  restored.
- The bottom navigation icons rendered at 30 dp in both themes.
- A similarity value describes cosine more accurately than a confidence value.
- A cosine score is not a calibrated probability.

- One accelerator setting for both models is not sufficient.
- The Realme test phone runs DIS correctly on GPU but returns an invalid SigLIP2 GPU
  output.
- The application now detects and saves the accelerator for each model separately.
- The first automatic check on the Realme selected DIS GPU and SigLIP2 CPU.
- A complete run after the automatic check matched `Пино Нуар` at cosine 0.910.
- This run used 6,454 ms for DIS GPU, 3,027 ms for SigLIP2 CPU, and 201 ms for local
  search.
- The launcher artwork source is `assets/product-logo-640x640.png`.
- The source has a 640 by 640 canvas and uses RGB pixels without alpha.
- The adaptive foreground keeps the full source artwork inside a 432 by 432 transparent
  canvas.
- A Google Pixel 8 was connected with serial `41231FDJH002WZ`.
- The Pixel 8 runs Android 17 at API level 37.
- The full production APK could not install with 1.2 GB of free storage.
- Standard and incremental installation both returned
  `INSTALL_FAILED_INSUFFICIENT_STORAGE`.
- A valid test pack kept the same DIS and SigLIP2 files and one production catalogue
  vector and image.
- The test pack size was 361,695,609 bytes.
- The test APK size was 406,246,869 bytes.
- The Pixel 8 automatic check selected GPU for DIS and GPU for SigLIP2.
- Both automatic selections persisted after an application restart.
- A complete Pixel 8 run matched `Пино Нуар` at cosine 0.909.
- This run used 2,546 ms for DIS GPU, 2,287 ms for SigLIP2 GPU, and 2 ms for the
  one-vector local search.
- The Pixel 8 showed the DIS mask, crop, and white-background debug images.
- The temporary test application and image were removed from the Pixel 8 after the
  verification.

- The catalogue has 2,098 active wines.
- A total of 2,093 active wines have a `main_patched` or `main` image and a current
  `full` vector in `android-siglip2-base-224-dis-white`.
- Five active wines have neither a `main_patched` image nor a `main` image.
- The built-in pack uses 23 `main_patched` images and 2,070 `main` images.
- The built-in pack uses 2,093 DIS-preprocessed SigLIP2 vectors of dimension 768.
- The vectors are finite and L2-normalized.
- The vector norm range is 0.99999988 to 1.00000012.
- The pack contains 135 local barcode and QR relations.
- The format version 2 pack size is 531,950,661 bytes.
- The pack SHA-256 is
  `da8a079c5e599c663e3a844d743af5103a9b8b896aa15f1660f07c1cdea56684`.
- The final debug APK size is 576,832,975 bytes.
- The final APK SHA-256 is
  `173ee058ad5681242d275a9fb0bb6a28035fd0f261df30323ff44ca269d2f980`.
- The APK stores the pack without ZIP compression.
- The application needs sufficient free internal storage to extract the models and the
  catalogue images on the first start.
- A fresh installation succeeded on an arm64 Android 14 phone.
- The installed private model directory used approximately 667 MiB.
- The installed manifest reported 2,093 vectors, wines, and images.
- The installed image directory contained 2,093 files.
- No `AndroidRuntime` crash was present after the first-start installation.
- LiteRT GPU SigLIP2 returned a non-finite output on the arm64 Android 14 test phone.
- The same model returned a valid vector through the LiteRT CPU accelerator.
- The first corrected run included the failed GPU attempt and used 11,780 ms for
  SigLIP2.
- A repeated run selected CPU directly and used 2,920 ms for SigLIP2.
- The test image matched its source wine at cosine 0.910.
- Google Code Scanner supports EAN-13 and manual input.
- The scanner now exposes its manual-input action as an EAN-13 fallback.
- The catalogue test confirms that EAN-13 `4631168664979` matches stored GTIN-14
  `04631168664979`.
- The Google Code Scanner camera could not be tested against a physical printed code
  through ADB.
- Google documents the scanner API at
  `https://developers.google.com/ml-kit/vision/barcode-scanning/code-scanner`.

## 2026-09-28

- Google Code Scanner 16.1.0 supports Android API 23 and later.
- Google Code Scanner performs processing on the device through Google Play services.
- LiteRT 2.2.0 provides `CompiledModel` with GPU and CPU accelerators.
- `litert-community/DIS-ISNet-LiteRT` uses a 1 by 3 by 1,024 by 1,024 float input.
- DIS normalization is `x / 255 - 0.5`.
- DIS returns a 1 by 1 by 1,024 by 1,024 soft alpha mask.
- The measured `dis.tflite` output uses the interval 0.5 to 0.731 on a catalogue image.
  The reference DIS inference code applies per-image min-max normalization. The
  application MUST apply the same normalization before threshold and alpha use.
- `litert-community/SigLIP2-base-patch16-224` uses a 1 by 3 by 224 by 224 float input.
- SigLIP2 normalization maps RGB values to `[-1, 1]`.
- SigLIP2 returns one L2-normalized 768-dimensional vector.
- The timm checkpoint uses `crop_pct=0.9`. For a 224 by 224 input, the processor
  resizes the image to 248 by 248 pixels and takes the centered 224 by 224 crop.
- A direct LiteRT input without this crop does not match the GX10 catalogue vectors.
  The 32-image control test had cosine values from 0.8103079 to 0.9761065.
- The tests of both completed indices with the timm crop had cosine values from
  0.9999985 to 0.9999999.
- The current workspace catalogue has 4,642 vectors of dimension 1,152.
- The current vectors use a different SigLIP2 model and cannot be used by the Android
  image encoder.
