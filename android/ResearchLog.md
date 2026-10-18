# Research log

## 2026-10-19

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
