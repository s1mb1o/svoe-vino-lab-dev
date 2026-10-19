# «Что за вино?» for Android

This application recognizes a wine on the device.
It supports Android 9 and later.
The user interface is in Russian.
The application ID is `chtozavino.alolalab.com`.

## Functions

- 18+ confirmation.
- Camera capture and multiple gallery selection for JPEG, PNG, WebP, HEIC, and HEIF.
- Multi-shot recognition with one to three photographs.
- Maximum-score result fusion for each wine across the selected photographs.
- Google Code Scanner with EAN-13, QR, and manual input.
- A settings page through the gear icon.
- A product website link on the settings page.
- Independent `Авто`, `GPU`, and `CPU` settings for DIS and SigLIP2.
- A first-start GPU compatibility check with a saved safe selection.
- A `Без сегментации / DIS / YOLO` setting.
- DIS foreground segmentation.
- YOLO26n-seg bottle segmentation with COCO class `bottle` on CPU.
- White-background crop.
- SigLIP2 Base NaFlex p512 embedding through the verified v0.2.0 complete graph.
- Native aspect ratio, standard attention pooling, and 768-dimensional vectors.
- FP16 model weights with FP32 GPU execution and automatic CPU fallback.
- Optional exact split runtime for `google/siglip2-so400m-patch16-naflex`.
- Desktop-compatible 1,152-dimensional NaFlex vectors.
- Optional exact split runtime for `google/siglip2-base-patch16-naflex`.
- Standard and foreground-aware pooling for 768-dimensional Base NaFlex vectors.
- Local cosine search.
- Debug images for each preprocessing stage.
- A built-in compatible p512 index and one transparent catalogue image for each wine.
- Legacy fixed Base/224 and split-model pack support for experiments.
- Links to the matching page on `vino-svoe.ru`.
- A whole-percent `Сходство` value for image results.
- Local history.
- A light or dark theme that follows the system setting.
- The shared `svoe-vino-lab` product logo as the launcher icon.

`Без сегментации` is the default mode.
The main pipeline encodes the full original image with Base NaFlex p512.
It does not apply the legacy square crop or the 2,048-pixel decode limit.
It uses the released Pillow-compatible preprocessing code.
The application verifies GPU agreement against the same CPU graph on first start.
It selects CPU when cosine is below `0.99999` or maximum error exceeds `0.001`.
All encoder creation, inference, and cleanup run on one dedicated thread.
Use YOLO for photographs that show a complete bottle.
Use DIS only as an explicit alternative.
The catalogue references remain the frozen p512 package-cut references in these modes.
Their accuracy needs a separate device evaluation.

The application processes multi-shot photographs in sequence.
This behavior limits peak LiteRT memory use.
The application keeps the maximum score for each wine across all successful
photographs.
The debug images and the history preview come from the photograph that supplies the
final Top-1 result.
The application continues when one photograph fails.
The application reports an error when all photographs fail.
After each successful photograph, the application checks the merged Top-1 result.
The application stops before the next photograph when Top-1 is at least `0.93` and the
margin over Top-2 is at least `0.08`.
The technical result text reports this early exit.

## Build

Use JDK 17 and Android SDK 36.
Export the format version 6 catalogue pack before you build the APK.
Use the released model directory and its matching frozen index:

```text
python3 tools/build_verified_naflex_pack.py \
  --catalogue-pack /path/to/previous-android-catalogue-pack.zip \
  --model-dir /path/to/android-model-base-p512 \
  --index-dir /path/to/android-index-base-p512 \
  --out /path/out/base-p512-default-pack.zip
cp /path/out/base-p512-default-pack.zip app/src/main/assets/default_model_pack.zip
```

The exporter retains wine cards, transparent display images, codes, DIS, and YOLO.
It replaces the old encoder and every reference vector.
It verifies the model, profile, table, source index, and payload hashes.
It rejects a missing wine instead of silently reducing catalogue coverage.
The current pack contains 2,093 wines and 2,093 p512 reference vectors.
Each wine has one unrotated reference.
The new pack does not contain a 72-angle p512 index.
Do not reuse the fixed Base/224 rotation vectors with this encoder.
Read [the integration validation report](docs/reports/2026-10-19_base-p512-default.md).
Read [the full Pixel 8 my benchmark](docs/reports/2026-10-19_pixel8-base-p512-full-my.md)
for retrieval quality, whole-pipeline latency, negative cases, and sustained heat.

### Legacy catalogue exporter

Use this tool only for fixed Base/224 or experimental split packs:

```text
python3 tools/build_catalog_pack.py \
  --replace \
  --version 20260929-dis-main-alpha
```

The legacy exporter default uses
`../workbench/data/catalog/embeddings/android-siglip2-base-224-dis-white-rot5`.
It writes `app/src/main/assets/default_model_pack.zip`.

The exporter writes only the files that the Android application uses:

- The verified DIS, YOLO26n-seg, and SigLIP2 LiteRT models.
- The selected 768-dimensional SigLIP2 reference vectors.
- Wine metadata and local barcode and QR relations.
- One transparent package cut for each included wine.

The exporter selects `main_patched` before `main` to find the correct indexed vector.
It exports 72 reference vectors for each selected image.
The reference angles are `0°, 5°, …, 355°`.
The application calculates one query vector.
It uses the maximum cosine similarity across the 72 reference vectors of each wine.
It does not put either source image into the Android pack.
It reads the related `image_derivative` row with `kind=package`.
It crops the transparent border and limits the long side to 1,024 pixels.
It writes the display image as transparent WebP at quality 80.
The display image is not an input to image matching.
The application uses the saved vector for image matching.

The YOLO model is the official Ultralytics `yolo26n-seg` w8a32 LiteRT asset.
Its embedded metadata declares the AGPL-3.0 license.
Do not publish an APK that contains this model until the distribution license is
approved for the product.
Use a compatible commercial license when the product license is not compatible with
AGPL-3.0.

The exporter verifies model hashes, vector shape, vector normalization, source cut
hashes, image transparency, image dimensions, archive paths, and all generated payload
hashes.
It writes a temporary pack first.
It replaces the target only after validation succeeds.
It reports each omitted wine in its JSON result.

### Optional SigLIP2 NaFlex split pack

This section describes the experimental split exports in this repository.
The separate `siglip2-naflex-litert` v0.2.0 library has verified GPU exports and its
own Android benchmark app.
Read [the implementation comparison](docs/naflex-implementations.md) before selecting
a runtime or interpreting the split-export measurements.

The application accepts model-pack formats 4 and 5.
This format uses a LiteRT backbone and a separate LiteRT pooling model.
The pooling model contains the original SigLIP2 attention pooling, LayerNorm, and MLP.
The Android preprocessor supplies patches, resized position vectors, and the attention
mask.
The pooling model runs on CPU.
Format 4 uses `google/siglip2-so400m-patch16-naflex` and 1,152 dimensions.
Format 5 uses `google/siglip2-base-patch16-naflex` and 768 dimensions.
Format 5 supports standard pooling and foreground-aware 5a pooling.
The 5a pooling adds `log(0.1 + 0.9 * foreground)` to each patch attention logit.

The split runtime runs an unverified NaFlex backbone on LiteRT CPU/XNNPACK.
`Auto` selects CPU when the pack does not declare GPU compatibility.
Explicit GPU selection reports a compatibility error in this case.
The pack builders write `gpu_compatible: false` by default.

Export the p512 split outside the repository:

```text
python3 tools/export_siglip2_naflex_split.py \
  --max-num-patches 512 \
  --out-dir /path/out/android-siglip2-so400m-naflex-p512-split
```

Build the matching external pack:

```text
python3 tools/build_catalog_pack.py \
  --catalog /path/to/workbench/data/catalog \
  --embedding gx10-siglip2-so400m-patch16-naflex-p512-rot5 \
  --siglip-runtime naflex-exact-split \
  --naflex-model-dir /path/out/android-siglip2-so400m-naflex-p512-split \
  --out /path/out/android-naflex-p512-pack-v4.zip
```

The generated p512 backbone is approximately 788 MiB.
The complete tested pack is approximately 1.72 GiB.
Keep these generated files outside Git and outside the APK.
The Pixel 8 CPU reference run took approximately 256 seconds for one image.
The Pixel 8 GPU delegate compiled the full backbone but returned an incompatible vector.
The application therefore disables GPU for this NaFlex runtime.
Treat this runtime as an accuracy baseline until a smaller or more strongly quantized
model meets the latency target.

The focused Base NaFlex pilot tested fixed p224, p256 standard, p256 5a, and p512
standard on one Pixel 8.
Each variant completed 30 requests without a process restart.
No variant passed both the exact-vector and latency gates.
Read [the Pixel 8 Base pilot report](docs/reports/2026-10-19_pixel8-siglip2-base-pilot/report.md).

```text
./gradlew test assembleDebug
```

The build writes the distribution copy to
`app/build/outputs/apk/friendly/chtozavino-<version>-debug.apk`.

Use this command to verify and build the optimized release variant:

```text
./gradlew testReleaseUnitTest lintRelease assembleRelease
```

The project does not contain a release signing key.
Gradle writes an unsigned APK to
`app/build/outputs/apk/release/app-release-unsigned.apk`.
Sign this APK with an owner-controlled release key before installation or publication.

The local release archive is
`/Volumes/Storage/svoe-vino-final/releases/android/`.
The current release file is `chtozavino-0.2.0-release-unsigned.apk`.
Its adjacent JSON file records the source commit, SHA-256, tests, and embedded pack.
Historical local APKs are in `historical/`.
Published 0.1.4 assets are in `github/android-v0.1.4/`.
The archive preserves different builds with the same version name.
Read [the 0.2.0 release record](docs/releases/0.2.0.md) before distribution.

The APK installs the built-in pack on the first start.
An update replaces an old format 1 through 5 pack with the built-in format 6 pack.
The update preserves history, the 18+ choice, and accelerator preferences.
It selects `Без сегментации` and repeats accelerator detection for the new model.
The application uses this pack without a replacement action in the user interface.
Model files, catalogue images, vectors, and generated packs stay outside Git.
The format 6 pack is approximately 384 MiB with one reference per wine.
Keep sufficient free storage for the APK, the extracted pack, and the temporary upgrade.
The old pack remains recoverable until the new pack passes validation.

## Debug device bulk evaluation

The debug APK can start an HTTP server on port `18088`.
The release APK does not contain this server or the NanoHTTPD dependency.
This server lets Workbench run a complete test set against the models on a real Android
device.
The server is off by default.
Open the application settings and enable `HTTP-сервер для тестов` before a
test.
Disable the setting after the test.
The application saves the setting between starts.
It restores a saved enabled setting only after pack migration and accelerator checks.
HTTP bulk testing and UI image recognition are mutually exclusive.
The UI releases its encoder when the server starts.
Disable the server before UI recognition or a manual accelerator check.
This rule prevents two GPU models from remaining open in one process.
The server uses the installed model pack, the saved segmentation setting, and the saved
DIS and SigLIP2 accelerator settings.
It serializes inference because one LiteRT model pipeline processes one image at a time.
It reuses the LiteRT environment, compiled models, and tensor buffers across requests.

- `GET /healthz` reports the pack version, wine count, SigLIP2 runtime, vector
  dimension, and patch limit.
- `POST /v1/eval/predict` accepts multipart field `image` and returns one `slug`.
- `POST /v1/match?k=20` accepts multipart field `image` and returns ranked candidates.
- `POST /v1/debug/embedding?k=20` also returns the normalized vector and stage latency.
- `aggregation=max` selects the maximum reference score.
- `aggregation=top2-mean` selects the mean of the two best reference scores.
- `dis_accelerator=cpu|gpu` and `siglip2_accelerator=cpu|gpu` override saved settings
  for one debug request.
- The image limit is 20 MiB.
- `k` MUST be from 1 through 20.

Use the Wi-Fi IPv4 address of the phone in the Workbench New Run dialog.
Use ADB forwarding when the Wi-Fi network blocks incoming device connections:

```text
adb -s <serial> forward tcp:18088 tcp:18088
curl http://127.0.0.1:18088/healthz
```

The Workbench pipelines are `android-device-eval-predict`,
`android-device-match-k20`, and `android-device-match-k20-top2-mean`.
These pipelines disable barcode recognition.

To start a bulk test in the Workbench UI:

1. Install and open the debug APK on the device.
2. Confirm that the built-in model pack is ready.
3. Open the application settings.
4. Enable `HTTP-сервер для тестов`.
5. Open the Workbench test-set page.
6. Select one Android device pipeline in New Run.
7. Enter the device IPv4 address.
8. Set the query limit for a smoke test, or leave the limit empty for a complete run.
9. Start the run.
10. Disable the HTTP server in the application settings after the run.

Use `127.0.0.1` as the device address when ADB forwarding is active.
Use the phone Wi-Fi IPv4 address when the phone accepts incoming connections.
Keep one worker because the Android server serializes inference.

You can also start the same bulk tests from the Workbench directory:

```text
python3 pipeline/remote_run.py --name android-device-eval-predict \
  --set my --device-ip 127.0.0.1 --limit 10 --label pixel8-smoke
python3 pipeline/remote_run.py --name android-device-match-k20 \
  --set my --device-ip 127.0.0.1 --limit 10 --label pixel8-smoke
```

Remove `--limit 10` only when you want a complete bulk run.
The `my` test set contained 3,409 queries during the 2026-10-19 check.
A complete run can take multiple hours on one phone.
Workbench writes the run files to `../workbench/runs/` and shows the result on the Runs
page.
Read [plan 86](../workbench/docs/plans/86_android-device-http-evaluation.md).

Read [the model and vector verification results](VERIFICATION_RESULTS.md),
[the verified Android 0.1.4 screenshot set](docs/screenshots/android-0.1.4/README.md),
[the Pixel 8 Base pilot](docs/reports/2026-10-19_pixel8-siglip2-base-pilot/report.md),
[the specification](docs/specification.md), and
[the model-pack contract](docs/model-pack.md).

## Pixel 8 segmentation comparison

The controlled 100-image test used the same catalogue, vectors, queries, and SigLIP2
CPU accelerator for both segmentation modes.

- DIS found a result for 100 images and accepted 38 results.
- YOLO found a bottle for 70 images and accepted 23 results.
- DIS median latency was 2,024.5 ms.
- YOLO median latency was 1,234 ms.
- Both runs completed 100 requests in one process without `SIGABRT`.

Keep DIS as the default for this test set.
YOLO is faster, but it has lower coverage and lower accepted Top-1 accuracy on these
queries.

The YOLO result is worse for this test set because 30 images do not show a complete
bottle that the COCO `bottle` class can detect.
The generated result files are in
`../output/android-pixel8-dis-reuse-eval-20261003/` and
`../output/android-pixel8-yolo26n-siglip-cpu-eval-20261003/`.
