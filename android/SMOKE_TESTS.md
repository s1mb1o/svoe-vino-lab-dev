# Smoke tests

## Automated checks

1. Run `python3 -m unittest tools.test_build_catalog_pack tools.test_build_model_pack`.
2. Run `python3 tools/build_catalog_pack.py --replace --version <version>`.
3. Run `./gradlew lintDebug test assembleDebug`.
4. Confirm that the APK contains the uncompressed asset
   `assets/default_model_pack.zip`.
5. Run `tools/verify_model_vectors.py` against a completed 768-dimensional workbench
   index and the Android SigLIP2 LiteRT file.

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
