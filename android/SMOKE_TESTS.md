# Smoke tests

## Rebuild checkpoint

The October 19 new-ID rebuild passed 65 main debug, 62 main release,
20 isolated Android, 16 model-pack, and 20 host tests.
No test failed or was skipped. All three lint variants have no errors.
The rebuilt APKs have the expected package IDs, SDK values, ABI, and signature states.
The release contains no NanoHTTPD or debug HTTP endpoints.
The original old-ID release and embedded pack hashes remain unchanged.
The Pixel retains the same frozen benchmark APK and PID. No installation occurred.
Read `docs/releases/2026-10-19-rebuild.md` for archive paths and hashes.

## Isolated offline retrieval benchmark

1. Build `tools/offline_benchmark/device` with `tools/offline_benchmark/build_device.sh`.
2. Require all isolated unit tests and debug lint to pass.
3. Verify package `com.alolalab.chtozavino.offlinebench` and minimum SDK 28.
4. Confirm that the main application's package, data, and installed pack are unchanged.
5. Confirm that the benchmark HTTP switch is off after a fresh process start.
6. Transfer only the verified benchmark pack into app-private `files/bench`.
7. Reject a changed checksum, wrong encoder dimension, or mismatched revision.
8. Enable HTTP through the observed UI switch. Confirm `/healthz` on port 18088.
9. Confirm that every response reports barcode and re-ranking as disabled.
10. Run grouped GPU, CPU, and GPU checks on held-out catalogue images.
11. Require desktop/device cosine of at least 0.99999 and component error at most 0.001.
12. Check complete bottle scores against the same frozen FP32 reference gallery.
13. Run 30 independent images per variant before the complete cohort.
14. Reject a native abort, process restart, silent CPU fallback, or critical thermal state.
15. Keep segmentation failures in predictions and the quality denominator.
16. Distinguish shared-work full-run timings from independent variant latency.
17. Save predictions, raw responses, hashes, traces, and thermal samples.
18. Disable HTTP after saving the final result. Remove only test-created forwarding.
19. Recreate the benchmark Activity. Confirm that enabled HTTP and loaded models remain.
20. Confirm that the device tools reject another active Android user before any write.
21. Disconnect USB during a disposable run. Require saved incomplete status and cleanup
    errors. Do not call this disposable run complete.
22. For the constant-sharing candidate, require FP32 BUFFER execution and disabled
    source quantization. Repeat numerical checks before quality measurement.
23. Verify that fresh process startup has no foreground service, notification, or lock.
24. Enable HTTP. Require a visible Russian notification and a private `specialUse` service.
25. Move the Activity to the background. Require importance at most 125 and continued
    HTTP access. Repeat 30 original images without a PID change or critical heat.
26. Disable HTTP. Require no listener, service, notification, or own wake lock after cleanup.
27. Repeat startup and notification stop-action checks. Require default-off after a kill.
28. Run all host tests in `tools/offline_benchmark`. Inject a binary status prefix and
    a truncated body. Require strict rejection, fresh sockets, and at most two retries.
29. Require a changed PID to prevent a second POST. Do not retry a model error.
30. Continue only into a new directory with the same APK, query, and pack hashes.
    Require an independent source audit and exact response and prediction prefix hashes.
31. Keep saved no-bottle errors. Check the first missing image on the phone before
    continuation. Verify both process segments and every variant prediction count.
32. Make UI cleanup time out in a host test. Require an isolated-app force-stop and
    recorded cleanup failure. Do not stop the main application.

## Automated checks

1. Run `python3 -m unittest tools.test_build_catalog_pack tools.test_build_model_pack
   tools.test_export_siglip2_naflex_split tools.test_build_verified_naflex_pack`.
2. Build the format 6 pack with `tools/build_verified_naflex_pack.py`.
3. Run `./gradlew testDebugUnitTest lintDebug assembleDebug testReleaseUnitTest
   lintRelease assembleRelease`.
4. Confirm that the APK contains the uncompressed asset
   `assets/default_model_pack.zip`.
5. Compare every packaged reference row with the matching released p512 index row.

## Isolated offline retrieval adaptation

1. Verify the frozen `my-failed-2` manifest hash and accepted alternative slugs.
2. Run the current installed application as a separate Base p512 control.
3. Confirm that no answer or query mask enters a device request.
4. Preserve every raw response and append each prediction immediately.
5. Confirm that re-ranking and barcode recognition remain disabled.
6. Check every vector, actual accelerator, and application PID.
7. Record catalogue-uncovered assignments in the complete scoring denominator.
8. Exclude evaluation-image hashes from the mobile segmentation training split.
9. Check source-coordinate cut boxes and catalogue annotation checksums.
10. Freeze exact reference and query pooling, geometry, views, and fusion recipes.
11. Preserve and verify external LiteRT weight buffers after a graph modification.
12. Require zero-bias, native-vector, and padding-exclusion checks before deployment.
13. Require Android CPU/GPU agreement and a short stability run before full variants.
14. Distinguish planned variants from completed device measurements.
15. Disable test HTTP and remove only test-created forwarding after measurement.

The October 19 Base p512 control passed all 668 requests.
Read `docs/reports/2026-10-19_pixel8-my-failed2-offline-control.md`.
The offline-adaptation dataset isolation and desktop pooling gates passed.
The catalogue-only segmentation pilot completed ten epochs.
The final frozen-pack gate passed all 102 numerical checks on Pixel 8.
Explicit Activity recreation retained HTTP and the loaded model state.
The independent quality pilot stopped after 57 responses when Android killed the
cached process after the camera became foreground. The pilot is incomplete.
Candidate v4 passed all 102 repeated numerical checks and all 300 independent pilot requests.
No request error, process restart, or CPU fallback occurred in that complete pilot.
Maximum thermal status was `SEVERE`. The declared stop threshold is `CRITICAL`.
All ten thirty-record prediction files and metrics passed independent verification.
The first complete-cohort attempt stopped after 29 assignments with background LOW_MEMORY.
Its partial predictions remain separate. Complete adapted quality is not final.
Candidate v5 passed 20 Android tests, seven host tests, and all 102 numerical checks.
Default-off, notification startup, both stop actions, and warm-model cleanup passed.
The background gate completed all 30 requests in PID 20524 with importance 125.
All 300 predictions and Top-20 scores match the independent v4 pilot exactly.
Maximum sampled background-gate heat was MODERATE.
The v2 cohort stopped after 44 responses with a malformed HTTP status line.
The host-only transport and continuation repair passed 20 host tests.
The q-000045 phone smoke passed all ten variants on its first attempt.
Full v3 resumed from assignment 45. The first 47 records pass independent audit.
The 44 inherited records and all source v2 files remain byte-for-byte unchanged.
Both q-000045 runs have identical candidates. Full quality is not final.

## Release archive checks

1. Rebuild release from the committed Android source.
2. Run debug and release unit tests, model-pack Python tests, and release lint.
3. Verify application ID `com.alolalab.chtozavino`, version `0.2.0`, and version code 6.
4. Verify minimum API 28, target API 36, and only the `arm64-v8a` ABI.
5. Confirm that the release is not debuggable.
6. Confirm that NanoHTTPD and the debug HTTP endpoint implementation are absent.
7. Verify the embedded format 6 pack SHA-256 and its 2,093 wine and vector counts.
8. Confirm the unsigned state with `apksigner verify`.
9. Copy the APK to the local archive and compare the source and destination SHA-256.
10. Copy historical APKs without changing the originals.
11. Preserve different APK hashes even when version names are equal.
12. Save archive manifests with byte lengths, hashes, versions, and source paths.

The October 19 local 0.2.0 release checks passed.
That frozen archive predates the ID change and uses `chtozavino.alolalab.com`.
The owner selected unsigned output.
There were no unit-test failures or errors in 64 debug and 61 release tests.
All 16 model-pack Python tests passed.
The new APK contains the same verified pack as the measured p512 application.
The new release was not installed on the phone in this archive task.
Read [the release record](docs/releases/0.2.0.md).

## Main application ID

1. Run debug and release unit tests, lint, and assembly.
2. Confirm that `ApplicationIdentityTest` passes for both build types.
3. Inspect both APK manifests for package `com.alolalab.chtozavino`.
4. Confirm FileProvider authority `com.alolalab.chtozavino.files` in both manifests.
5. Confirm launcher activity `com.alolalab.chtozavino.MainActivity`.
6. Confirm that the launcher label remains `Что за вино?`.
7. Confirm that the Pixel 8 pilot runner targets the new package.
8. Do not overwrite the old-ID archived release or the dual-GPU experiment.

The October 19 rename validation passed for both APKs.
Debug unit tests: 65 passed. Release unit tests: 62 passed.
No unit test failed, produced an error, or was skipped.
Both application-ID tests passed.
Both lint tasks passed with no errors.
Debug lint reported 31 warnings. Release lint reported 32 warnings.
Both APK manifests contain the new package and FileProvider authority.
Both APKs keep version `0.2.0`, version code 6, API 28 minimum, and API 36 target.
Both APKs keep the original Russian launcher label and the verified format 6 pack.
The debug APK signature verifies. The release APK remains unsigned and not debuggable.
The Pixel 8 pilot module imports and targets `com.alolalab.chtozavino`.
The old-ID archive SHA-256 remains
`f6dbfe72e5d2bff1de98cee3ac8948c3b3f9553d1a477575be6425c1feb4ccb6`.

New-ID build outputs:

- `app/build/outputs/apk/friendly/chtozavino-0.2.0-debug.apk`:
  447,547,504 bytes. SHA-256:
  `37db77a393eab210f238431a1dc0613c9161dc1e2be73f6a8819e4885d2b2a14`.
- `app/build/outputs/apk/release/app-release-unsigned.apk`:
  414,916,338 bytes. SHA-256:
  `1575957fd4c4dbfd356d8e21adba9cd6864c44298205512af74fed9614ef3eb8`.

Installation, camera capture, and new-ID first-start device checks need a separate
device installation.
Do not treat the new ID as an update of the old package.

## Complete Base NaFlex p512 default

The following migration check describes the pre-rename package.
Use an old-ID APK to reproduce that update over version 0.1.4.
The new ID starts with separate application data.

1. Install the debug APK as an update over version 0.1.4.
2. Confirm that the old pack upgrades to format 6.
3. Confirm that history and the 18+ choice remain present.
4. Confirm that `Без сегментации` is selected after this migration.
5. Confirm that settings identify Base NaFlex p512 and 768 dimensions.
6. Confirm that the first-start CPU/GPU check completes.
7. Confirm that an invalid GPU vector causes automatic CPU selection.
8. Confirm that the debug HTTP server remains off unless the owner enabled it.
9. Enable the debug HTTP server and inspect `GET /healthz`.
10. Confirm runtime `naflex-complete`, patch budget `512`, and segmenter `NONE`.
11. Run the deterministic 30-image pilot through `/v1/debug/embedding`.
12. Decode every returned vector and check its size, finite values, and L2 norm.
13. Compare CPU and GPU on the same image.
14. Compare device vectors with the desktop complete graph.
15. Confirm that the process does not restart between HTTP requests.
16. Confirm that UI image recognition requests server shutdown first.
17. Disable HTTP and recognize one gallery image in the UI.
18. Test a transparent PNG, an EXIF-oriented JPEG, and a HEIC image.
19. Switch to DIS and YOLO and confirm that the p512 encoder remains active.
20. Disable the server and remove ADB forwarding after the test.

Read [the integration report](docs/reports/2026-10-19_base-p512-default.md) for the
executed subset and the unperformed checks.

The October 19 complete-graph device check passed pack migration and automatic GPU.
All thirty pilot requests returned HTTP 200 without a process restart.
CPU/GPU parity passed on one transparent reference.
Desktop/device parity passed on fourteen pilot images.
Median warm server latency was 514.8 ms. P95 was 748.8 ms.
Peak sampled PSS was 925.3 MiB. Android thermal status remained `NONE`.
The HTTP server was disabled after the API checks.
The transparent PNG gallery preview and UI GPU recognition passed.
The exact reference returned `Пино Нуар` at 100-percent similarity.
The new history row remained visible after a deliberate cold restart.
The HTTP server remained off after that restart.
The test-created device files and ADB forwarding rule were removed.

## Isolated DIS GPU and p512 GPU experiment

1. Copy the committed Android source into an isolated experiment directory.
2. Set a separate application ID and launcher label before building.
3. Keep the main application source, APKs, installed package, and private data unchanged.
4. Bypass the DIS GPU to p512 CPU override only in the copied source.
5. Disable CPU fallback for explicit debug accelerator requests in the experiment.
6. Include actual accelerator fields in every successful debug response.
7. Run debug unit tests, lint, and assembly in the copied source.
8. Run the frozen thirty-image pilot and verify vectors, accelerators, PID, and logs.
9. Run full `my` only after the stability gate passes.
10. Keep segmentation failures in the scored result set.
11. Stop on native abort, process change, invalid output, or CPU fallback.
12. Stop the experimental process at Android thermal status `CRITICAL` or higher.
13. Compare frozen-query results with the complete p512 no-segmentation baseline.
14. After the full run, compare p512 CPU/GPU vectors with DIS still on GPU.
15. Disable HTTP, remove forwarding, restore power settings, and verify main APK hashes.

The October 19 experiment passed 64 debug unit tests and debug lint.
All 30 pilot requests returned HTTP 200 with GPU + GPU.
All 3,409 full assignments completed in one process.
There were 3,404 HTTP 200 responses and five explicit DIS no-object errors.
No native abort, process restart, or model-level CPU fallback occurred.
Positive Top-1 was 72.29%, Top-5 was 88.18%, and Top-10 was 90.34%.
Client median was 1,319 ms. P95 was 2,343 ms.
Full-run peak sampled PSS was 1,434.2 MiB. Maximum thermal status was `MODERATE`.
All three post-run p512 GPU/CPU vector comparisons passed.
Closing both GPU models left the experimental process alive.
HTTP shutdown, forwarding removal, power restoration, and main APK preservation passed.
The main application source and guard were not changed.
Read [the full experiment report](docs/reports/2026-10-19_pixel8-p512-dis-dual-gpu-my.md).

## Full my device matching benchmark

1. Freeze `my` assignments with the current Workbench query builder.
2. Verify the input hashes and compare the saved query file with the baseline.
3. Select complete Base NaFlex p512, GPU, and no segmentation.
4. Run one uncached worker through `/v1/match?k=20` without barcode recognition.
5. Keep every positive, negative, no-match, and duplicate assignment.
6. Save predictions, scored results, telemetry, application logs, and source hashes.
7. Check Top-1, Top-5, and Top-10 against every accepted slug.
8. Report unavailable catalogue wines separately without changing the main denominator.
9. Check the application PID, HTTP status, accelerator, and thermal status.
10. Disable HTTP, remove forwarding, and restore the power setting after the run.

The October 19 run completed all 3,409 requests in PID `24675` with HTTP 200.
Positive Top-1 was 69.09%. Top-5 was 87.10%. Top-10 was 90.03%.
Client median latency was 924 ms. P95 was 1,479 ms.
No process restart, fatal application error, or CPU fallback was observed.
The post-run embedding probe confirmed GPU.
Peak sampled PSS was 955.2 MiB.
The thermal check failed the short-pilot gate: the long run reached `SEVERE` (`3`).
Negative forbidden Top-1 matches increased from 42 to 73 of 430.
All 9 no-match queries remained false accepts.
HTTP shutdown, forwarding removal, temporary UI dump removal, and power restoration
passed.
Read [the full report](docs/reports/2026-10-19_pixel8-base-p512-full-my.md).

## SigLIP2 NaFlex exact split checks

1. Export the p512 split with `tools/export_siglip2_naflex_split.py`.
2. Confirm that PyTorch split cosine is `1.0`.
3. Confirm that LiteRT end-to-end cosine is at least `0.99999`.
4. Build a format version 4 pack with the matching 1,152-dimensional index.
5. Install the debug APK on the Pixel 8.
6. Install the external format version 4 pack.
7. Confirm that `GET /healthz` reports runtime `naflex-exact-split`.
8. Confirm that `GET /healthz` reports vector dimension `1152`.
9. Confirm that `GET /healthz` reports patch limit `512`.
10. Select explicit GPU for SigLIP2.
11. Send one image to `POST /v1/match?k=3`.
12. Confirm that the request reports the NaFlex GPU compatibility error.
13. Select `Auto` for SigLIP2.
14. Confirm that the saved automatic SigLIP2 accelerator is CPU.
15. Send the known `chin-chin-vermentino` catalogue image to `POST /v1/match?k=3`.
16. Confirm that Top-1 is `chin-chin-vermentino`.
17. Confirm that its score is close to `0.977004`.
18. Confirm that the returned vector search uses the p512 split pipeline.

## Focused SigLIP2 Base pilot checks

1. Export Base NaFlex p256 standard.
2. Export Base NaFlex p256 5a.
3. Export Base NaFlex p512 standard.
4. Confirm that each output has 768 dimensions.
5. Confirm that each generated model stays outside Git.
6. Run CPU/GPU vector parity on one Pixel 8 image.
7. Reject an accelerator when cosine is below `0.99999`.
8. Reject an accelerator when maximum error is above `0.001`.
9. Run the same deterministic 30-image selection for each encoder.
10. Record latency, PSS, RSS, battery temperature, thermal status, PID, and logcat.
11. Confirm that every vector is finite and has 768 dimensions.
12. Confirm that no process restarted.
13. Run full `my` only for a variant that passes every gate.
14. Confirm that an unverified NaFlex pack has `gpu_compatible: false`.
15. Read
    `docs/reports/2026-10-19_pixel8-siglip2-base-pilot/report.md`.

The 2026-10-19 Pixel 8 pilot passed all execution and stability checks.
It rejected all variants on the combined vector and latency gates.
The final validation passed `lintDebug`, `testDebugUnitTest`, `assembleDebug`, eight
Python tests, and sixteen Workbench tests.

## SigLIP2 NaFlex verification on 2026-10-19

- The Python split and pack-builder tests passed.
- `testDebugUnitTest`, `lintDebug`, and `assembleDebug` passed.
- The debug APK installed on Pixel 8 serial `41231FDJH002WZ`.
- `GET /healthz` reported format version 4 runtime values.
- Explicit GPU returned HTTP 502 before it could return a false match.
- The automatic accelerator check saved CPU for SigLIP2 NaFlex.
- The final `Auto` request used pipeline
  `android-dis-siglip2-so400m-naflex-p512-split`.
- The final request returned `chin-chin-vermentino` at `0.977004`.
- The final request latency was `256081.709` ms.
- The final debug APK installed on the Pixel 8.
- The debug HTTP server was off after the test.
- The ADB port forward and temporary device pack archives were removed.

## HEIC and HEIF checks

1. Put one valid HEIC image and one valid HEIF image in the device gallery.
2. Open the gallery from the application.
3. Confirm that the picker shows both files.
4. Select the HEIC image.
5. Confirm that the application shows its preview.
6. Start recognition.
7. Confirm that the application shows a ranked result.
8. Open the history page.
9. Confirm that the new history row shows its preview.
10. Restart the application.
11. Confirm that the history preview remains visible.
12. Repeat steps 4 through 11 with the HEIF image.

## Verification on 2026-10-19

- The gallery MIME-type unit test passed in debug and release variants.
- All 35 debug unit tests passed.
- All 32 release unit tests passed.
- `lintDebug`, `lintRelease`, `assembleDebug`, and `assembleRelease` passed.
- The Pixel 8 MediaStore reported `image/heic` for the HEIC test file.
- The Pixel 8 MediaStore reported `image/heif` for the HEIF test file.
- The system picker showed both test files.
- The application decoded and showed the HEIC preview.
- The HEIC test image produced `Каберне Фран 1890` at 81 percent similarity.
- The history row showed its preview.
- The row and preview stayed visible after a cold application restart.
- TalkBack opened the system picker without an application error.
- The accessibility tree exposed the gallery action, both file names, the selected
  preview, and the history preview.
- TalkBack was restored to its original off state after the check.
- Logcat contained no application warning, fatal exception, or native abort.
- The two temporary gallery files were removed after the test.
- `testDebugUnitTest`, `lintDebug`, and `assembleDebug` passed.
- The version 0.1.4 debug APK installed on Pixel 8 serial `41231FDJH002WZ`.
- The device ran Android 17 at API level 37.
- The installed pack reported version `20261003-dis-yolo26n-seg` and 2,093 wines.
- The settings page showed DIS GPU and SigLIP2 CPU.
- The main screen accepted three gallery photographs.
- One multi-shot run processed all three photographs.
- One multi-shot run stopped after the first photograph at the configured thresholds.
- The early-exit technical text reported `Обработано фото: 1 из 3`.
- The early-exit technical text reported `Ранний выход: высокое сходство`.
- The `/v1/match?k=20` run completed all 3,409 eligible `my` queries.
- The run used one application process and one HTTP worker.
- The run had five HTTP 502 results from four unique DIS failures.
- The run had no native abort and no application process restart.
- Positive R@1 was 0.3327.
- Positive R@5 was 0.5646.
- Positive R@10 was 0.6441.
- Median latency was 1,699 ms.
- P95 latency was 2,156 ms.
- The debug HTTP server was off after the test.
- The ADB port forward was absent after the test.
- The temporary device images were removed after the test.

## Multi-shot checks

1. Add one photograph from the camera.
2. Add two photographs from the gallery.
3. Confirm that the screen shows three selected photographs.
4. Confirm that the camera and gallery actions are disabled at three photographs.
5. Remove one photograph.
6. Confirm that the camera and gallery actions become available.
7. Start recognition with two or three photographs.
8. Confirm that the progress text shows each photograph in sequence.
9. Confirm that the result list contains no duplicate `wine.slug` value.
10. Confirm that each wine uses its maximum score across successful photographs.
11. Confirm that one failed photograph does not stop the other photographs.
12. Confirm that all failed photographs produce an error.
13. Confirm that the debug images come from the photograph that supplies Top-1.
14. Confirm that the action creates one history row.
15. Confirm that the history preview comes from the photograph that supplies Top-1.
16. Use a first photograph with Top-1 `0.93` or more and a Top-2 margin `0.08` or more.
17. Confirm that the application does not process the remaining photographs.
18. Confirm that the technical text reports `Ранний выход: высокое сходство`.
19. Use a result below either early-exit threshold.
20. Confirm that the application processes the next photograph.

## Verification on 2026-10-18

- Four multi-shot result-fusion unit tests passed.
- Four multi-shot early-exit unit tests passed.
- All 34 debug unit tests passed.
- All 31 release unit tests passed.
- `lintDebug` and `lintRelease` passed.
- `assembleDebug` and `assembleRelease` passed.
- The multi-shot device checks completed on 2026-10-19.

## Verification on 2026-10-03

- Four catalogue exporter tests passed for 72 reference rows per wine.
- Seven Python pack-builder tests passed in total.
- The test pack contained angles `0, 5, …, 355` for each included wine.
- The test pack validator rejected any vector count that did not equal 72 times the wine
  count.
- The Workbench rotation suite passed 26 tests.
- The Workbench configuration loaded the Android rot5 entry with 72 angles.
- Full-index generation and an APK device test are pending.
- Six Python pack-builder tests passed for model-pack format version 3.
- Android debug unit tests passed after the segmentation-mode change.
- `lintDebug` and `assembleDebug` passed with JDK 21 after the final source change.
- The built-in format version 3 pack contains 2,093 vectors, wines, and images.
- The pack contains the verified 3,234,566-byte YOLO26n-seg w8a32 file.
- The debug APK installed over version 0.1.4 without data removal.
- The application upgraded the installed format version 2 pack to format version 3.
- `GET /healthz` reported pack `20261003-dis-yolo26n-seg`, 2,093 wines, and the
  selected segmentation mode.
- The YOLO smoke test returned a result for five of the first 10 queries.
- The controlled DIS run completed 100 requests in one process.
- The controlled YOLO run completed 100 requests in one process.
- No native abort occurred during either run.
- DIS with SigLIP2 CPU accepted 38 of 100 queries.
- YOLO with SigLIP2 CPU found a bottle in 70 queries and accepted 23 of 100 queries.
- The debug HTTP server and ADB port forward were off after the tests.
- The final 576,503,447-byte debug APK installed on Pixel 8 serial
  `41231FDJH002WZ`.
- The final APK SHA-256 is
  `18800aadae4646a9f06f4605b965f3fe4a1e764d6f7f7f1289c0e38942b47964`.
- The installed model pack reports format version 3 and contains
  `yolo26n-seg_w8a32.tflite`.
- The debug HTTP server setting remained off after the final installation.

## Earlier verification on 2026-10-03

- The debug APK installed over release version 0.1.4 without data removal.
- `GET /healthz` reported pack `20260929-dis-main-alpha` and 2,093 wines.
- The Pixel 8 used DIS GPU and SigLIP2 GPU.
- Queries 1 through 56 completed in one process.
- Query 57 caused a native abort in the LiteRT GPU accelerator.
- Three fresh processes completed the remaining queries in batches of 20, 20, and 4.
- The final file contains 100 ordered and unique query rows.
- Every row has the required five fields.
- Every image SHA-256 matches the actual query image.
- No prediction is null.
- The median request latency is 4,669 ms.
- The primary and accepted alternative slugs accepted 38 of 100 predictions.
- The release APK replaced the debug APK after the test.
- The debug HTTP server and the ADB port forward were off after the test.

## Verification on 2026-09-29

- GitHub release `android-v0.1.4` exists and is not a draft.
- The GitHub release is marked as a pre-release.
- The release tag resolves to the source commit that contains the Android 0.1.4 code.
- GitHub reports `chtozavino-0.1.4-release-test-signed.apk` as uploaded with size
  441,392,911 bytes.
- Its GitHub SHA-256 digest matches
  `1a846cf82f06fc24f495bb6008b6bc775ef4aae25df175b5c93a6a7a46f1dfd0`.
- GitHub reports `chtozavino-0.1.4-debug.apk` as uploaded with size 576,503,447 bytes.
- Its GitHub SHA-256 digest matches
  `fc4cf0f44b8fefcff5286b04746efb7fa44b9742ec6df282aa0cc959f6777ea2`.
- `SHA256SUMS-android-v0.1.4.txt` is uploaded.
- The unsigned release APK is not an installable release asset.

- All 21 debug unit tests passed after the server-switch change.
- `lintDebug`, `compileReleaseKotlin`, and `assembleDebug` passed.
- Release dependency inspection found no NanoHTTPD dependency.
- The updated debug APK installed on the Google Pixel 8.
- The debug HTTP server was off after the update because no saved setting existed.
- Port 18088 did not listen while the switch was off.
- The debug settings page showed the switch in its off state.
- Enabling the switch opened port 18088 immediately.
- `GET /healthz` returned HTTP 200 with 2,093 wines.
- The enabled state and HTTP server stayed active after an application restart.
- Disabling the switch closed port 18088 immediately.
- The switch and server were left off after the test.
- The debug APK is 576,503,447 bytes.
- Its SHA-256 is
  `fc4cf0f44b8fefcff5286b04746efb7fa44b9742ec6df282aa0cc959f6777ea2`.

- `lintDebug`, `testDebugUnitTest`, `assembleDebug`, and `compileReleaseKotlin` passed
  after the debug HTTP server change.
- The debug server unit tests passed for `k` validation and both response shapes.
- The earlier server-API debug APK was 576,503,447 bytes.
- Its SHA-256 was
  `9066ff9c377305d8eef2880d0c127a276d841bfd52d50af31c16740b53503279`.
- The APK installed on the Google Pixel 8 with serial `41231FDJH002WZ`.
- `GET /healthz` returned HTTP 200, pack `20260929-dis-main`, and 2,093 wines.
- A 10-query Workbench run through `/v1/eval/predict` had zero errors and recall@1 0.3.
- Its median latency was 4,349 ms.
- A 10-query Workbench run through `/v1/match?k=20` had zero errors.
- It had recall@1 0.3, recall@5 0.6, and recall@10 0.9.
- Its median latency was 4,597 ms.
- NanoHTTPD 2.3.1 was present in `debugRuntimeClasspath`.
- NanoHTTPD was absent from `releaseRuntimeClasspath`.

- `testReleaseUnitTest`, `lintRelease`, and `assembleRelease` passed.
- All 18 release unit tests passed.
- R8 code optimization and resource shrinking passed.
- ZIP alignment verification passed.
- The release APK has package ID `chtozavino.alolalab.com`.
- It has version code 5 and version name 0.1.4.
- It has `minSdkVersion` 28 and `targetSdkVersion` 36.
- The versioned file is `chtozavino-0.1.4-release-unsigned.apk`.
- The release APK is 441,352,932 bytes.
- Its SHA-256 is
  `a5cf1ce4a42715c521579a899c5dc9bbeddb32b5ae55c9ad54c82dbd19d765e4`.
- The embedded pack is 429,200,870 bytes.
- The embedded pack SHA-256 is
  `cb181ce8f5583d92c800014c083eb75cc0458fa205407aa24bc032a80b050ec3`.
- Signature verification correctly reports that the release APK is unsigned.
- Installation is pending a production signing configuration.

- Six focused Python pack-builder tests passed after the transparent image change.
- The exporter produced 2,093 vectors, wines, and transparent WebP images.
- The exporter produced 1,939 `package_crop` and 154 `package_seg` images.
- The exporter verified each image hash, format, dimension, and alpha channel.
- Each image has a long side of 1,024 pixels or less.
- The pack contains no large `main` or `main_patched` source image.
- The generated `images.zip` is 59,205,972 bytes.
- The generated pack is 429,200,870 bytes.
- The pack SHA-256 is
  `cb181ce8f5583d92c800014c083eb75cc0458fa205407aa24bc032a80b050ec3`.
- The pack is 102,749,791 bytes and 19.3 percent smaller than the previous pack.
- A visual check passed for one `package_crop` image and one `package_seg` image.
- An Android Gradle build did not run for this change because this host has no JDK.

- Five Python pack-builder tests passed.
- Four catalogue index tests, four DIS mask tests, four SigLIP2 vector tests, and four
  accelerator-selection tests passed
  for the debug variant.
- Two similarity-format tests passed for the debug variant.
- Four catalogue index tests, four DIS mask tests, four SigLIP2 vector tests, and four
  accelerator-selection tests passed
  for the release variant.
- Two similarity-format tests passed for the release variant.
- `./gradlew lintDebug test assembleDebug` passed with JDK 17.
- The built-in pack has 2,093 vectors, wines, and images.
- The pack has 23 `main_patched` images and 2,070 `main` images.
- Five active wines were omitted because they have no selected image.
- The pack has 135 local barcode and QR relations.
- The pack SHA-256 is
  `da8a079c5e599c663e3a844d743af5103a9b8b896aa15f1660f07c1cdea56684`.
- The debug APK contains the 531,950,661-byte pack as the uncompressed asset
  `assets/default_model_pack.zip`.
- The debug APK has `minSdkVersion` 28, `targetSdkVersion` 36, and application ID
  `Chtozavino.alolalab.com`.
- A fresh APK installation passed on an arm64 Android 14 phone.
- The first-start installation produced a format version 2 pack with 2,093 vectors,
  wines, and images.
- The installed image directory contained 2,093 files.
- The application process stayed active and had no `AndroidRuntime` crash.
- The settings gear, compact camera and gallery buttons, and settings page passed on the
  phone.
- GPU SigLIP2 returned a non-finite output on the phone.
- The automatic CPU retry completed and matched the source wine at cosine 0.910.
- A repeated recognition used SigLIP2 CPU directly for 2,920 ms.
- The first-start accelerator check selected DIS GPU and SigLIP2 CPU on the Realme.
- The settings page showed independent `Авто`, `GPU`, and `CPU` controls for both
  models.
- The DIS control changed to CPU and saved the selection.
- The DIS control changed back to `Авто` and saved the selection.
- A complete run in `Авто` mode used DIS GPU for 6,454 ms and SigLIP2 CPU for
  3,027 ms.
- The run matched `Пино Нуар` at cosine 0.910.
- The application used the shared product logo as the adaptive launcher icon.
- The Pixel 8 ran Android 17 at API level 37.
- The full production APK did not install with only 1.2 GB of free storage.
- A compact valid pack kept the production DIS and SigLIP2 files and one catalogue
  vector and image.
- The Pixel 8 first-start check selected DIS GPU and SigLIP2 GPU.
- The Pixel 8 saved both automatic selections across an application restart.
- The Pixel 8 matched `Пино Нуар` at cosine 0.909.
- The Pixel 8 run used DIS GPU for 2,546 ms and SigLIP2 GPU for 2,287 ms.
- The Pixel 8 showed the DIS mask, crop, and white-background debug images.
- Google Code Scanner opened and showed the manual-input action.
- Google Code Scanner read the physical EAN-13 code `4630037250909` through the
  Pixel 8 camera.
- The local catalogue matched this code to `Шато Тамань. Каберне Совиньон` at
  `Сходство: 100%`.
- Version 0.1.3 installed over version 0.1.2 without clearing application data.
- The main subtitle showed `Не требует интернета`.
- The recognition and history tabs showed clear 30 dp vector icons.
- The settings page showed version 0.1.3 and the `Сайт «Что за вино?»` link.
- The application followed the Realme system light and dark settings.
- The original light system setting was restored after the test.
- The test image showed `Сходство: 91%` for `Пино Нуар`.
- The history page showed the new `Пино Нуар` row as `Фото · сходство 91%`.
- The history page contained the same row after an application restart.
- `chtozavino_debug.apk` has version code 4, version name 0.1.3, `minSdkVersion` 28,
  and `targetSdkVersion` 36.
- `chtozavino_debug.apk` is 576,503,277 bytes.
- Its SHA-256 is
  `be7a24ca7db3d182a87c931b6c7d154f69892e28735e7f211a45e4650f55a828`.
- Version 0.1.4 has application ID `chtozavino.alolalab.com` and version code 5.
- The version 0.1.4 distribution file is `chtozavino-0.1.4-debug.apk`.
- The version 0.1.4 APK has `minSdkVersion` 28 and `targetSdkVersion` 36.
- The version 0.1.4 APK is 576,503,269 bytes.
- Its SHA-256 is
  `e22d166c8922936dd75acb63ec0b860334ef982caf5bbde36c5bb5c079227c26`.
- The friendly output directory contains no obsolete unversioned APK.
- `lintDebug`, debug and release unit tests, and `assembleDebug` passed after the file
  name change.
- The old `Chtozavino.alolalab.com` package is absent from the Pixel 8 and Realme.
- The full version 0.1.4 APK installed on the Pixel 8 with 6.1 GB free before the
  installation.
- The Pixel 8 installed 2,093 catalogue images, 2,093 wines, and 2,093 vectors.
- The Pixel 8 automatic check selected GPU for DIS and SigLIP2.
- The full Pixel 8 run matched `Пино Нуар` at `Сходство: 91%`.
- The run used DIS GPU for 2,463 ms, SigLIP2 GPU for 2,134 ms, and search for 100 ms.
- The Pixel 8 showed the DIS mask debug view.
- The Pixel 8 kept the `Пино Нуар` history row after an application restart.
- The history result opened the exact wine page in Chrome.
- The settings product link opened `https://vino-svoe.ru` in Chrome.
- The settings page showed pack version `20260929-dis-main` and both 2,093 counts.
- The settings page showed selected `Авто` controls for DIS and SigLIP2.
- The settings page showed the automatic DIS GPU and SigLIP2 GPU selections.
- The settings page showed version 0.1.4 and the product-site link.
- The complete settings page rendered correctly in the Pixel 8 dark system theme.
- No application crash was present after the checks.
- The eight primary marketing screenshots show verified working states.
- The screenshot set contains light and dark main screens with the same selected
  bottle.
- The screenshot set contains the real DIS mask, crop, and white-background images.
- The screenshot set contains the persistent history row and the physical EAN-13
  result.
- The Pixel 8 dark system theme was restored after capture.
- System UI demo mode was disabled after capture.
- The temporary source image was removed after capture.

## Verification on 2026-09-28

- `./gradlew lintDebug test assembleDebug` passed with JDK 17.
- Three catalogue index tests passed for the debug and release variants.
- Three model-pack builder tests passed.
- The debug APK has `minSdkVersion` 28 and `targetSdkVersion` 36.
- The debug APK has the application ID `Chtozavino.alolalab.com`.
- A physical device was not connected. The device checks are pending.
- A compatible 768-dimensional model pack was not available. The inference checks are pending.
- Three DIS mask-normalization tests pass. They cover the measured LiteRT output range,
  a flat mask, and a non-finite mask.
- The model-vector test passed on 32 evenly spaced catalogue rows of each index.
  The DIS-index cosine values were 0.9999985 minimum, 0.9999995 mean, and 0.9999999
  maximum. The SAM3-index values were 0.9999990 minimum, 0.9999996 mean, and 0.9999999
  maximum.

## Device checks

1. Install the debug APK on an Android 9 arm64 device.
2. Confirm that the 18+ window blocks the application content.
3. Select `Мне есть 18 лет`.
4. Confirm that the application remembers the answer after a restart.
5. Confirm that the application shows `Готовим встроенный каталог…`.
6. Confirm that the built-in pack installs without a document-picker action.
7. Confirm that the application shows 2,093 images and 2,093 wines.
8. Confirm that the main screen does not show a model-pack replacement action.
9. Open the settings gear.
10. Confirm that settings show the pack version and the 2,093 counts.
11. Take one bottle photograph.
12. Select one bottle photograph from the gallery.
13. Start recognition for each image.
14. Confirm that the first start checks DIS and SigLIP2 on GPU.
15. Confirm that the settings page shows the saved automatic selection for each model.
16. Select `CPU` for DIS and confirm that recognition reports `DIS: CPU`.
17. Select `GPU` for DIS and confirm that recognition reports `DIS: GPU` or a clear
    invalid-result error.
18. Restore `Авто` for DIS.
19. Repeat steps 16 to 18 for SigLIP2.
20. Confirm that an invalid GPU result in `Авто` mode causes one CPU retry.
21. Confirm that the application saves CPU as the automatic selection after this retry.
22. Confirm that the result contains ranked wines, scores, and catalogue images.
23. Open the debug section.
24. Confirm that the DIS mask, crop, and white-background image are visible.
25. Open the best result on `vino-svoe.ru`.
26. Disable the network connection.
27. Repeat image recognition.
28. Confirm that image recognition still works.
29. Scan one known EAN-13 code and one known QR code.
30. Confirm that each code resolves without an image embedding.
31. Confirm that Google Code Scanner shows its manual-input action.
32. Cancel Google Code Scanner.
33. Confirm that the application reports the cancellation.
34. Open history.
35. Confirm that image and code results appear in newest-first order.
36. Confirm that image results use `Сходство` and a whole-percent value.
37. Confirm that a new successful result remains in history after an application restart.
38. Change the system theme to dark.
39. Confirm that all application pages use the dark color scheme.
40. Restore the original system theme.
41. Confirm that the installed package ID is `chtozavino.alolalab.com`.
42. Confirm that the old `Chtozavino.alolalab.com` package is absent.
43. Open a wine result and confirm that Chrome receives the exact wine page URL.
44. Open the settings product link and confirm that Chrome receives
    `https://vino-svoe.ru`.
45. Confirm that the settings page shows the pack version and counts.
46. Confirm that `Авто` is selected for DIS and SigLIP2.
47. Confirm that the settings page shows each saved automatic accelerator selection.
48. Confirm that the settings page shows the application version and product link.
49. Install the debug APK with clean application data.
50. Confirm that `HTTP-сервер для тестов` is off.
51. Confirm that port 18088 does not answer while the switch is off.
52. Enable the switch and confirm that `GET /healthz` answers on port 18088.
53. Restart the application and confirm that the enabled setting stays active.
54. Disable the switch and confirm that port 18088 stops answering.
55. Confirm that the release settings page does not show the switch.
