# Change log

## 2026-10-19

### Debug HTTP and repeatable device benchmarks

- Added `/v1/debug/embedding` to the debug HTTP server.
- Added per-request accelerator overrides for debug HTTP tests.
- Added runtime, vector dimension, patch limit, pooling mode, and aggregation to health.
- Added deterministic 30-image selection and Pixel 8 measurement tools.
- Added CPU/GPU vector parity measurement.
- Added the `android-device-match-k20-top2-mean` Workbench configuration.
- Kept Base pilot packs separate from compatible retrieval catalogue packs.

### SigLIP2 NaFlex split runtimes and model packs

- Added model-pack format version 4 for `google/siglip2-so400m-patch16-naflex`.
- Added model-pack format version 5 for `google/siglip2-base-patch16-naflex`.
- Added 768-dimensional Base NaFlex p256 and p512 support.
- Added a LiteRT backbone that returns NaFlex patch tokens.
- Added a separate LiteRT pooling model with the original `post_layernorm`, attention
  pooling, pooling LayerNorm, and MLP residual.
- Added Android NaFlex preprocessing with native aspect ratio, 16 by 16 patches, exact
  patch-limit selection, resized position vectors, and padding masks.
- Added support for 256, 512, and 1,024 patch limits.
- Added 1,152-dimensional catalogue vectors and dynamic catalogue validation.
- Added foreground-aware 5a attention pooling.
- Added `max` and `top2-mean` reference aggregation.
- Added an export tool with PyTorch split parity and LiteRT parity checks.
- Added format version 4 support to the catalogue pack builder.
- Added focused Kotlin and Python tests for preprocessing, pack validation, and the
  model split.
- Added a `gpu_compatible` model-pack gate.
- Made all pack builders disable NaFlex GPU by default.
- Made `Auto` select LiteRT CPU/XNNPACK for an unverified split runtime.
- Made explicit GPU selection report a clear error before it can return a false match.
- Keyed the saved accelerator check to the installed model files and patch limit.

### HEIC and HEIF gallery input

- Added `image/heic` and `image/heif` to the gallery picker allowlist.
- Kept `ImageDecoder` as the Android 9 and later decode path.
- Kept the history preview as a local JPEG after recognition.
- Added a unit test for all supported gallery MIME types.
- Updated the application and format documentation.
- Passed debug and release unit tests, lint, and APK assembly.
- Verified the HEIC picker, preview, recognition, and persistent history on a Pixel 8.
- Verified that the Pixel 8 picker shows files with MIME types `image/heic` and
  `image/heif`.
- Verified the gallery and preview accessibility labels with TalkBack enabled.

### Pixel 8 current-patch validation

- Built the version 0.1.4 debug APK from commit `f8b15c2`.
- Passed `testDebugUnitTest`, `lintDebug`, and `assembleDebug`.
- Installed the APK on a Google Pixel 8 with Android 17.
- Verified the model pack, settings, main screen, and debug HTTP server.
- Verified selection and recognition of three photographs.
- Verified the multi-shot early exit after one of three photographs.
- Ran all 3,409 eligible queries of the Workbench `my` test set.
- Completed the run in one application process without `SIGABRT` or another crash.
- Measured positive R@1 0.3327, R@5 0.5646, R@10 0.6441, and MRR 0.4402.
- Measured 1,699 ms median latency and 2,156 ms P95 latency.
- Recorded five HTTP 502 results for four unique images where DIS found no main object.
- Disabled the debug HTTP server after the run.
- Removed the ADB port forward and the temporary device images after the run.

## 2026-10-18

### Multi-shot recognition

- Added selection of one through three photographs.
- Added camera and gallery accumulation for selected photographs.
- Added removal of one selected photograph or all selected photographs.
- Processed the selected photographs in sequence.
- Merged results with the maximum score for each wine.
- Continued recognition when at least one photograph succeeded.
- Used the Top-1 source photograph for debug images and the history preview.
- Added deterministic unit tests for result fusion.
- Added a multi-shot early exit at Top-1 `0.93` and Top-1 to Top-2 margin `0.08`.
- Added unit tests for the early-exit score, margin, and candidate-count rules.

- Listed downloadable model packs as a possible future feature.
- Kept model-pack download and replacement outside the current project scope.

## 2026-10-17

### Realme USB smoke test

- Verified cold start on a Realme RMX3890 with Android 14.
- Verified the installed 0.1.5 debug application and model pack.
- Ran 10 queries through `/v1/eval/predict` with zero request errors.
- Ran 10 queries through `/v1/match?k=20` with zero request errors.
- Measured recall@1 0.5 for both endpoints.
- Measured recall@5 0.7 for `/v1/match?k=20`.
- Confirmed that Logcat contained no `FATAL EXCEPTION` or `SIGABRT`.
- Disabled the debug HTTP server after the test.
- Removed the ADB port forward after the test.

## 2026-10-03

### Five-degree Android reference rotation

- Added the Workbench entry `android-siglip2-base-224-dis-white-rot5`.
- Added 72 reference angles from 0 degrees through 355 degrees for each catalogue image.
- Rotated the DIS result before `square_on_white` and the 224 by 224 resize.
- Kept the 0-degree frame equal to the existing Android model input.
- Kept one SigLIP2 query vector on the Android device.
- Kept maximum cosine scoring across all reference rows of one wine.
- Changed the catalogue exporter default to the rotated index.
- Added an `angle` value to each generated candidate relation.
- Added strict validation for the 5-degree sequence and 72 rows per wine.
- Passed four Android catalogue exporter tests and 26 Workbench rotation tests.
- Did not generate the full catalogue index or APK in this change.

### DIS and YOLO segmentation modes

- Added the `DIS / YOLO` segmentation setting.
- Added the official `yolo26n-seg` w8a32 LiteRT model at 640 by 640 pixels.
- Kept only COCO class 39, `bottle`.
- Selected the largest central bottle mask.
- Removed letterbox padding before the white-background crop.
- Kept YOLO inference on CPU.
- Added model-pack format version 3 and a verified YOLO payload.
- Kept format versions 1 and 2 readable.
- Reused one LiteRT environment, compiled model, and buffer set across requests.
- Prevented two live GPU models in the DIS pipeline.
- Added unit tests for YOLO bottle selection, normalized boxes, mask generation, and
  settings fallback.
- Ran controlled DIS and YOLO evaluations on 100 images on a Google Pixel 8.
- DIS with SigLIP2 CPU accepted 38 of 100 images.
- YOLO with SigLIP2 CPU accepted 23 of 100 images.
- YOLO did not find a complete bottle in 30 images.
- Both 100-request runs completed without `SIGABRT`.
- Passed six Python pack-builder tests, Android debug unit tests, `lintDebug`, and
  `assembleDebug`.
- Installed the final debug APK on a Google Pixel 8.
- Kept the debug HTTP server off after the test.

## 2026-09-29

### GitHub Android pre-release

- Created the private GitHub pre-release `android-v0.1.4`.
- Attached the optimized test-signed release APK and the debug APK.
- Attached a SHA-256 checksum file for both APK files.
- Marked the release as a pre-release because both APK files use the Android debug
  certificate.
- Verified the uploaded asset states, byte sizes, and GitHub SHA-256 digests.
- Kept the unsigned APK out of the installable release assets.

### Debug device evaluation API

- Added a labelled collage of the 10 Pixel 8 smoke-test photographs.
- Recorded why the unbalanced 10-query sample reached only 30 percent recall@1.
- Kept the debug HTTP server off by default.
- Added the debug-only `HTTP-сервер для тестов` settings switch.
- Started and stopped the server immediately when the switch changed.
- Saved the switch value between application starts.
- Passed 21 debug unit tests, `lintDebug`, `compileReleaseKotlin`, and `assembleDebug`.
- Verified the default, enabled, persisted, and disabled states on a Google Pixel 8.
- Added a debug-only NanoHTTPD server on port 18088.
- Added matcher-compatible `POST /v1/eval/predict` and `POST /v1/match` operations.
- Added `GET /healthz` with the installed pack state.
- Used the installed model pack and the saved DIS and SigLIP2 accelerator settings.
- Limited uploads to 20 MiB and serialized model inference.
- Kept the server and NanoHTTPD dependency out of the release runtime.
- Added unit tests for `k` validation and both response shapes.
- Passed `lintDebug`, `testDebugUnitTest`, `assembleDebug`, and `compileReleaseKotlin`.
- Built and installed `chtozavino-0.1.4-debug.apk` on a Google Pixel 8.
- Ran 10 images from Workbench through each endpoint with zero request errors.
- `/v1/eval/predict` gave recall@1 0.3 with 4,349 ms median latency.
- `/v1/match?k=20` gave recall@1 0.3, recall@5 0.6, and recall@10 0.9 with
  4,597 ms median latency.

### Optimized release build

- Ran release unit tests and `lintRelease`.
- Ran R8 code optimization and resource shrinking.
- Built the unsigned release APK for version 0.1.4.
- Added the versioned output copy
  `chtozavino-0.1.4-release-unsigned.apk`.
- Verified the package ID, version, SDK levels, ZIP alignment, and embedded model pack.
- Recorded that production signing is not configured.

### Transparent Android catalogue export

- Changed the workbench exporter to package transparent package cuts.
- Stopped packaging the large `main` and `main_patched` source images.
- Kept source image selection only for vector and cut provenance.
- Converted display images to transparent WebP at quality 80.
- Limited the display image long side to 1,024 pixels.
- Added image hash, format, dimension, and transparency validation.
- Added parallel image conversion and atomic pack replacement.
- Added tests for transparent export, resize, provenance, and opaque-cut rejection.
- Exported 2,093 vectors, wines, and images.
- Reduced the generated pack from 531,950,661 bytes to 429,200,870 bytes.

### Versioned APK file name

- Added the application version to the distribution APK file name.
- The version 0.1.4 distribution file is `chtozavino-0.1.4-debug.apk`.
- Kept `versionName` as the single value that supplies the APK file name.
- Changed the distribution task to `Sync` so that an obsolete APK does not stay in
  the output directory.
- Passed `lintDebug`, debug and release unit tests, and `assembleDebug`.
- Verified version code 5, version name 0.1.4, `minSdkVersion` 28, and
  `targetSdkVersion` 36 in the versioned APK.

### Verified marketing screenshots

- Added eight primary screenshots from the installed version 0.1.4 application on a
  Google Pixel 8.
- Added full PNG source files and cropped WebP website files.
- Added a high-resolution contact sheet for presentations.
- Added separate detail views for the crop, white-background, and settings-about
  sections.
- Verified the photo example through DIS, SigLIP2, local search, and persistent
  history.
- Verified the photo result as `Пино Нуар` at `Сходство: 91%`.
- Verified a physical EAN-13 camera scan through Google Code Scanner.
- The code `4630037250909` matched `Шато Тамань. Каберне Совиньон` at
  `Сходство: 100%`.
- Restored the Pixel 8 dark system theme after capture.
- Disabled System UI demo mode and removed the temporary image after capture.

### Lowercase application ID

- Changed the application ID to `chtozavino.alolalab.com`.
- Changed the version to `0.1.4` with version code 5.
- Removed the old `Chtozavino.alolalab.com` installation from the Realme test phone.
- Kept the unrelated `com.alolalab.storagetracker*` applications unchanged.
- Installed the full APK on the Google Pixel 8.
- Installed the built-in pack with 2,093 wines, vectors, and images on the Pixel 8.
- Verified that the Pixel 8 automatic check selected GPU for DIS and SigLIP2.
- Completed one full Pixel 8 recognition with the production pack.
- The source wine matched `Пино Нуар` at `Сходство: 91%`.
- Verified the DIS mask debug view and persistent history on the Pixel 8.
- Verified the result link to the exact `vino-svoe.ru/wines/...` page.
- Verified the settings link to `https://vino-svoe.ru`.
- Verified all settings values and controls in the Pixel 8 dark system theme.
- Built the 576,503,269-byte `chtozavino-0.1.4-debug.apk`.
- The APK SHA-256 is
  `e22d166c8922936dd75acb63ec0b860334ef982caf5bbde36c5bb5c079227c26`.

### Result wording and interface polish

- Changed the version to `0.1.3` with version code 4.
- Replaced the raw cosine label with `Сходство` and a whole-percent value.
- Added two similarity-format unit tests for each build variant.
- Replaced the bottom navigation glyphs with clear 30 dp vector icons.
- Changed the main subtitle to `Не требует интернета`.
- Added the `Сайт «Что за вино?»` link below the application version.
- Added a clear history empty-state message.
- Added the friendly build artifact `chtozavino_debug.apk`.
- Verified the system-controlled light and dark themes on the Realme Android 14 phone.
- Verified that a successful recognition creates a persistent history row.
- Built the 576,503,277-byte `chtozavino_debug.apk`.
- The APK SHA-256 is
  `be7a24ca7db3d182a87c931b6c7d154f69892e28735e7f211a45e4650f55a828`.

### Per-model accelerators and product icon

- Changed the version to `0.1.2` with version code 3.
- Added a first-start GPU compatibility check for DIS and SigLIP2.
- Added a saved automatic accelerator selection for each model.
- Added independent `Авто`, `GPU`, and `CPU` controls for DIS and SigLIP2.
- Kept a CPU retry for a failed GPU result in `Авто` mode.
- Added four accelerator-selection unit tests for each build variant.
- Added an extra DIS output-size test for each build variant.
- Converted `assets/product-logo-640x640.png` to adaptive and fallback launcher
  resources.
- Verified that the automatic check selected DIS GPU and SigLIP2 CPU on the Realme
  Android 14 phone.
- Repeated the full recognition on that phone.
- The test image matched `Пино Нуар` at cosine 0.910.
- The run used DIS GPU for 6,454 ms, SigLIP2 CPU for 3,027 ms, and local search for
  201 ms.
- Tested the same DIS and SigLIP2 files on a Google Pixel 8 with Android 17.
- The Pixel 8 automatic check selected GPU for DIS and GPU for SigLIP2.
- The Pixel 8 saved both selections across an application restart.
- The Pixel 8 matched `Пино Нуар` at cosine 0.909.
- The Pixel 8 run used DIS GPU for 2,546 ms and SigLIP2 GPU for 2,287 ms.
- Verified the DIS mask, crop, and white-background debug images on the Pixel 8.
- Built the 576,832,975-byte debug APK.
- The APK SHA-256 is
  `173ee058ad5681242d275a9fb0bb6a28035fd0f261df30323ff44ca269d2f980`.

### Built-in DIS catalogue

- Added model-pack format version 2 with a verified `images.zip` payload.
- Added a catalogue pack builder for
  `android-siglip2-base-224-dis-white`.
- Added one vector, one candidate relation, and one catalogue image for each included
  wine.
- Selected `main_patched` before `main`.
- Added first-start installation of the pack from the APK.
- Kept format version 1 parsing for development tools.
- Added the catalogue image to each recognition result.
- Added sampled preview decoding to limit memory use for large catalogue images.
- Built a pack with 2,093 wines, 2,093 vectors, 2,093 images, and 135 local code
  relations.
- Omitted five active wines that have no `main_patched` or `main` image.
- Verified 23 `main_patched` selections and 2,070 `main` selections.
- Verified that all 768-dimensional vectors are finite and L2-normalized.
- Built the debug APK with the 531,950,661-byte pack stored in
  `assets/default_model_pack.zip`.
- Passed Python tests, Android debug and release unit tests, `lintDebug`, and
  `assembleDebug`.
- Installed the APK on an arm64 Android 14 phone.
- Verified the first-start installation of all 2,093 images and the format version 2
  manifest on the phone.

### Device inference and interface corrections

- Changed the version to `0.1.1` with version code 2.
- Added validation for the SigLIP2 output size, finite values, and vector norm.
- Added an automatic CPU retry when GPU SigLIP2 returns an invalid output.
- Disabled later SigLIP2 GPU attempts in the same process after this failure.
- Added four SigLIP2 vector-normalization tests for each build variant.
- Added a settings page through a gear icon.
- Removed the model-pack replacement action from the user interface.
- Replaced the long camera and gallery labels with compact icon buttons.
- Enabled Google Code Scanner manual input as a fallback for EAN-13.
- Added scanner cancellation, empty-result, and failure feedback.
- Verified the CPU fallback on an arm64 Android 14 phone.
- The test catalogue image matched its own wine at cosine 0.910.
- A repeated run used DIS on GPU for 6,307 ms, SigLIP2 on CPU for 2,920 ms, and local
  search for 236 ms.

## 2026-09-28

### Initial Android application

- Added an Android 9 application project with the ID `Chtozavino.alolalab.com`.
- Added the offline DIS and SigLIP2 recognition contract.
- Added the verified external model-pack contract.
- Added the Russian user-flow specification and smoke tests.
- Added the model-pack builder with strict model, dimension, pipeline, and hash checks.
- Added local cosine-search and barcode normalization tests.
- Added a model-pack builder test that rejects the current 1,152-dimensional GX10 vectors.
- Verified lint, unit tests, and the debug APK build with JDK 17.
- Verified `minSdkVersion` 28, `targetSdkVersion` 36, and the application ID in the APK.
- Kept model files and catalogue vectors outside Git.

### DIS mask normalization

- Added the per-image min-max normalization of the reference DIS inference code.
- Fixed full-frame selection from the raw LiteRT output range of 0.5 to 0.731.
- Added unit tests for the measured range, a flat mask, and a non-finite mask.

### SigLIP2 vector compatibility

- Added the timm `crop_pct=0.9` preprocessing to the Android SigLIP2 encoder.
- Changed the model-pack pipeline ID to `dis-white-square-timm-crop090-v2`.
- Added a reproducible LiteRT-to-GX10 vector comparison tool.
- Pinned the accepted DIS and SigLIP2 model files by SHA-256 in the pack builder and
  the Android pack importer.
- Verified the SigLIP2 model on 32 catalogue images.
- The minimum cosine value was 0.9999985 across both indices after matching the
  preprocessing.
