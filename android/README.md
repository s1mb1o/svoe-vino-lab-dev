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
Build the generated catalogue pack before you build the APK:

```text
python3 tools/build_catalog_pack.py --replace --version 20260929-dis-main
```

The default pack uses
`../workbench/data/catalog/embeddings/android-siglip2-base-224-dis-white`.
It selects `main_patched` before `main`.
It writes `app/src/main/assets/default_model_pack.zip`.

```text
./gradlew test assembleDebug
```

The build writes the distribution copy to
`app/build/outputs/apk/friendly/chtozavino_debug.apk`.

The APK installs the built-in pack on the first start.
The application uses this pack without a replacement action in the user interface.
Model files, catalogue images, vectors, and generated packs stay outside Git.
Reserve at least 1.5 GB of free device storage for the APK and the installed pack.

Read [the model and vector verification results](VERIFICATION_RESULTS.md),
[the specification](docs/specification.md), and
[the model-pack contract](docs/model-pack.md).
