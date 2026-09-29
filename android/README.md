# «Что за вино?» for Android

This application recognizes a wine on the device.
It supports Android 9 and later.
The user interface is in Russian.
The application ID is `chtozavino.alolalab.com`.

## Functions

- 18+ confirmation.
- Camera capture and gallery selection.
- Google Code Scanner with EAN-13, QR, and manual input.
- A settings page through the gear icon.
- A product website link on the settings page.
- Independent `Авто`, `GPU`, and `CPU` settings for DIS and SigLIP2.
- A first-start GPU compatibility check with a saved safe selection.
- DIS foreground segmentation.
- White-background crop.
- SigLIP2 Base/16 224 embedding.
- Local cosine search.
- Debug images for each preprocessing stage.
- Built-in DIS catalogue embeddings and one catalogue image for each included wine.
- Links to the matching page on `vino-svoe.ru`.
- A whole-percent `Сходство` value for image results.
- Local history.
- A light or dark theme that follows the system setting.
- The shared `svoe-vino-lab` product logo as the launcher icon.

## Build

Use JDK 17 and Android SDK 36.
Export the generated catalogue pack from the workbench before you build the APK:

```text
python3 tools/build_catalog_pack.py \
  --replace \
  --version 20260929-dis-main-alpha
```

The default pack uses
`../workbench/data/catalog/embeddings/android-siglip2-base-224-dis-white`.
It writes `app/src/main/assets/default_model_pack.zip`.

The exporter writes only the files that the Android application uses:

- The verified DIS and SigLIP2 LiteRT models.
- The selected 768-dimensional SigLIP2 vectors.
- Wine metadata and local barcode and QR relations.
- One transparent package cut for each included wine.

The exporter selects `main_patched` before `main` to find the correct indexed vector.
It does not put either source image into the Android pack.
It reads the related `image_derivative` row with `kind=package`.
It crops the transparent border and limits the long side to 1,024 pixels.
It writes the display image as transparent WebP at quality 80.
The display image is not an input to image matching.
The application uses the saved vector for image matching.

The exporter verifies model hashes, vector shape, vector normalization, source cut
hashes, image transparency, image dimensions, archive paths, and all generated payload
hashes.
It writes a temporary pack first.
It replaces the target only after validation succeeds.
It reports each omitted wine in its JSON result.

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

The APK installs the built-in pack on the first start.
The application uses this pack without a replacement action in the user interface.
Model files, catalogue images, vectors, and generated packs stay outside Git.
Reserve at least 1.5 GB of free device storage for the APK and the installed pack.

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
The server uses the installed model pack and the saved DIS and SigLIP2 accelerator
settings.
It serializes inference because one LiteRT model pipeline processes one image at a time.

- `GET /healthz` reports the pack version and wine count.
- `POST /v1/eval/predict` accepts multipart field `image` and returns one `slug`.
- `POST /v1/match?k=20` accepts multipart field `image` and returns ranked candidates.
- The image limit is 20 MiB.
- `k` MUST be from 1 through 20.

Use the Wi-Fi IPv4 address of the phone in the Workbench New Run dialog.
Use ADB forwarding when the Wi-Fi network blocks incoming device connections:

```text
adb -s <serial> forward tcp:18088 tcp:18088
curl http://127.0.0.1:18088/healthz
```

The two Workbench pipelines are `android-device-eval-predict` and
`android-device-match-k20`.
Both pipelines disable barcode recognition.

To start a bulk test in the Workbench UI:

1. Install and open the debug APK on the device.
2. Confirm that the built-in model pack is ready.
3. Open the application settings.
4. Enable `HTTP-сервер для тестов`.
5. Open the Workbench test-set page.
6. Select `android-device-eval-predict` or `android-device-match-k20` in New Run.
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
The `my` test set contained 2,232 queries during the 2026-09-29 check.
A complete run can take multiple hours on one phone.
Workbench writes the run files to `../workbench/runs/` and shows the result on the Runs
page.
Read [plan 86](../workbench/docs/plans/86_android-device-http-evaluation.md).

Read [the model and vector verification results](VERIFICATION_RESULTS.md),
[the verified Android 0.1.4 screenshot set](docs/screenshots/android-0.1.4/README.md),
[the specification](docs/specification.md), and
[the model-pack contract](docs/model-pack.md).
