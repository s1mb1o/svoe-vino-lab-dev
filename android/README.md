# «Что за вино?» for Android

This application recognizes a wine on the device.
It supports Android 9 and later.
The user interface is in Russian.

## Functions

- 18+ confirmation.
- Camera capture and gallery selection.
- Google Code Scanner for barcode and QR input.
- DIS foreground segmentation.
- White-background crop.
- SigLIP2 Base/16 224 embedding.
- Local cosine search.
- Debug images for each preprocessing stage.
- Links to the matching page on `vino-svoe.ru`.
- Local history.

## Build

Use JDK 17 and Android SDK 36.

```text
./gradlew test assembleDebug
```

The application has no model weights in Git.
Build a pack with `tools/build_model_pack.py`.
Install the pack through `Установить пакет моделей` in the application.

Read [the specification](docs/specification.md) and
[the model-pack contract](docs/model-pack.md).
