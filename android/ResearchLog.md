# Research log

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
