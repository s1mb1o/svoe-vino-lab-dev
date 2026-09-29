# Change log

## 2026-09-29

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
- Built the 576,503,269-byte `chtozavino_debug.apk`.
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
