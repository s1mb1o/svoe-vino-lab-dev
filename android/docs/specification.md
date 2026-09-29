# Android application specification

Date: 2026-09-29

## Purpose

The application identifies one wine from a bottle photograph.
The application runs recognition on the Android device.
The application opens the matching page on `vino-svoe.ru`.

## Platform

- The minimum Android version MUST be Android 9.
- `minSdk` MUST be 28.
- `targetSdk` MUST be 36.
- The application ID MUST be `chtozavino.alolalab.com`.
- The user interface MUST be in Russian.

## User flow

1. The application MUST request an 18+ confirmation before it shows the main content.
2. The user MAY take a photograph.
3. The user MAY select an image from the gallery.
4. The user MAY scan a barcode or QR code with Google Code Scanner.
5. The user starts image recognition with the button `Начать распознавание`.
6. The application shows ranked results and one catalogue image for each result.
7. The application shows the DIS mask, the crop, and the white-background image in the
   debug section.
8. The user MAY open a result on `vino-svoe.ru`.
9. The application MUST store local result history.
10. The top application bar MUST contain a settings gear icon.
11. The camera and gallery actions MUST use compact icons and short labels.
12. The top application bar MUST show `Не требует интернета`.
13. The bottom navigation MUST use clear recognition and history icons.
14. The settings page MUST show the application version.
15. The settings page MUST show a link to `https://vino-svoe.ru` below the version.
16. The application theme MUST follow the system light or dark setting.

## Image recognition

The application MUST use this image pipeline:

1. Decode the image and limit its long side to 2,048 pixels.
2. Run DIS at 1,024 by 1,024 pixels.
3. Calculate the foreground box from mask values of 0.5 or more.
4. Add a four-percent margin to the foreground box.
5. Crop the source image and the alpha mask to this box.
6. Composite the crop on white with the soft alpha mask.
7. Put the crop in the center of a square white image.
8. Resize the square image to 224 by 224 pixels.
9. Resize the 224 by 224 image to 248 by 248 pixels.
10. Take the centered 224 by 224 crop.
11. Normalize RGB values to `[-1, 1]` in NCHW order.
12. Run `vit_base_patch16_siglip_224.v2_webli` through LiteRT.
13. Compare the 768-dimensional normalized vector with catalogue vectors.
14. Use dot product as cosine similarity.
15. Use the maximum image score as the wine score.

The user interface MUST show the image score as `Сходство: <whole percent>%`.
The user interface MUST NOT describe the cosine score as confidence.

Steps 9 and 10 reproduce the timm image processor with `crop_pct=0.9`.

The desktop catalogue pipeline MUST use the same steps.
The application MUST reject vectors from a different model or pipeline.
The application MUST reject an output that has a wrong size or a non-finite value.
The application MUST test GPU inference for DIS and SigLIP2 on the first start.
The application MUST validate the output of each GPU test.
The application MUST save one automatic accelerator selection for each model.
The settings page MUST provide `Авто`, `GPU`, and `CPU` for each model.
The `Авто` mode MUST use the saved automatic selection.
The `Авто` mode MUST retry a failed GPU inference on CPU.
The application MUST save CPU as the automatic selection after this fallback.
The explicit `GPU` mode MUST report an invalid GPU result.
The explicit `CPU` mode MUST not load the model on GPU.

## Barcode and QR recognition

Google Code Scanner MUST perform camera scanning.
The scanner MUST request EAN-8, EAN-13, UPC-A, UPC-E, Code 128, Data Matrix, and QR
formats.
The scanner MUST enable auto-zoom and manual input.
The application MUST report a scanner error, an empty value, or cancellation.
The application MUST normalize a 13-digit EAN value to the stored 14-digit GTIN key.
The application MUST resolve the returned value in the local model pack.
The application MUST not upload a scanned value.

## Model pack

The APK MUST contain a built-in format version 2 model pack.
The built-in pack MUST use the completed
`android-siglip2-base-224-dis-white` embedding index.
The built-in pack MUST contain one `main_patched` or `main` image for each included
wine.
The application MUST install the built-in pack on the first start.
The application MUST show progress during this operation.

The user interface MUST NOT show a model-pack installation or replacement action.
The settings page MUST show the built-in pack version and counts.
The application MUST verify every root payload with SHA-256 and byte length.
The application MUST reject unsafe ZIP paths and unknown payloads.
Recognition MUST work without a network connection after installation of the model pack
and the Google Code Scanner module.

## History

The application MUST store at most 50 history rows.
Each row MUST contain the time, recognition source, best result, score, page URL, and a
local preview when one exists.
History data MUST stay on the device.
The history page MUST show a clear empty-state message before the first saved result.

## Debug APK

The debug build MUST create a distribution copy named `chtozavino_debug.apk`.

## Product icon

The launcher icon MUST use `../assets/product-logo-640x640.png` as its artwork source.
The application MUST provide an adaptive launcher icon.
