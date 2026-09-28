# Android application specification

Date: 2026-09-28

## Purpose

The application identifies one wine from a bottle photograph.
The application runs recognition on the Android device.
The application opens the matching page on `vino-svoe.ru`.

## Platform

- The minimum Android version MUST be Android 9.
- `minSdk` MUST be 28.
- `targetSdk` MUST be 36.
- The application ID MUST be `Chtozavino.alolalab.com`.
- The user interface MUST be in Russian.

## User flow

1. The application MUST request an 18+ confirmation before it shows the main content.
2. The user MAY take a photograph.
3. The user MAY select an image from the gallery.
4. The user MAY scan a barcode or QR code with Google Code Scanner.
5. The user starts image recognition with the button `Начать распознавание`.
6. The application shows ranked results.
7. The application shows the DIS mask, the crop, and the white-background image in the
   debug section.
8. The user MAY open a result on `vino-svoe.ru`.
9. The application MUST store local result history.

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
9. Normalize RGB values to `[-1, 1]` in NCHW order.
10. Run `vit_base_patch16_siglip_224.v2_webli` through LiteRT.
11. Compare the 768-dimensional normalized vector with catalogue vectors.
12. Use dot product as cosine similarity.
13. Use the maximum image score as the wine score.

The desktop catalogue pipeline MUST use the same steps.
The application MUST reject vectors from a different model or pipeline.

## Barcode and QR recognition

Google Code Scanner MUST perform camera scanning.
The scanner MUST request EAN-8, EAN-13, UPC-A, UPC-E, Code 128, Data Matrix, and QR
formats.
The application MUST resolve the returned value in the local model pack.
The application MUST not upload a scanned value.

## Model pack

The application MUST import one ZIP model pack through the Android document picker.
The application MUST verify every payload with SHA-256 and byte length.
The application MUST reject unsafe ZIP paths and unknown payloads.
Recognition MUST work without a network connection after installation of the model pack
and the Google Code Scanner module.

## History

The application MUST store at most 50 history rows.
Each row MUST contain the time, recognition source, best result, score, page URL, and a
local preview when one exists.
History data MUST stay on the device.
