# Android application specification

Date: 2026-10-18

## Purpose

The application identifies one wine from one to three bottle photographs.
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
2. The user MAY take one or more photographs.
3. The user MAY select one or more images from the gallery.
4. The application MUST keep from one through three selected photographs.
5. The user MAY remove one selected photograph or all selected photographs.
6. The user MAY scan a barcode or QR code with Google Code Scanner.
7. The user starts image recognition with the recognition button.
8. The application shows ranked results and one catalogue image for each result.
9. The application shows the selected segmentation mask, the crop, and the
   white-background image in the debug section.
10. The user MAY open a result on `vino-svoe.ru`.
11. The application MUST store local result history.
12. The top application bar MUST contain a settings gear icon.
13. The camera and gallery actions MUST use compact icons and short labels.
14. The top application bar MUST show `Не требует интернета`.
15. The bottom navigation MUST use clear recognition and history icons.
16. The settings page MUST show the application version.
17. The settings page MUST show a link to `https://vino-svoe.ru` below the version.
18. The application theme MUST follow the system light or dark setting.

## Image recognition

The settings page MUST provide a `DIS / YOLO` segmentation setting.
The default segmentation mode MUST be `DIS`.
The application MUST use this image pipeline:

1. Decode the image and limit its long side to 2,048 pixels.
2. Run the selected segmentation model.
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
15. Use the maximum score across all reference angles and images as the wine score.

The application MUST process selected photographs in sequence.
The application MUST NOT run multiple LiteRT image pipelines at the same time.
The application MUST create a ranked result for each successfully processed photograph.
The application MUST keep the maximum score for each `wine.slug` across these results.
The application MUST sort the merged results by score in descending order.
The application MUST use `wine.slug` in ascending order to resolve equal scores.
The application MUST continue when one selected photograph fails.
The application MUST report an error when all selected photographs fail.
The application MUST use the photograph that supplies the final Top-1 score for debug images.
The application MUST use this photograph for the history preview.
The application MUST write one history row for one multi-shot recognition action.
After each successful photograph, the application MUST check the merged Top-1 result.
The application MUST stop before the next photograph when Top-1 is `0.93` or more and
the margin over Top-2 is `0.08` or more.
The application MUST NOT stop early when fewer than two candidates exist.
The technical result text MUST report an early exit.
The technical result text MUST show the number of processed photographs.

The user interface MUST show the image score as `Сходство: <whole percent>%`.
The user interface MUST NOT describe the cosine score as confidence.

Steps 9 and 10 reproduce the timm image processor with `crop_pct=0.9`.

DIS MUST use a 1,024 by 1,024 input.
YOLO MUST use the official `yolo26n-seg` w8a32 LiteRT model.
YOLO MUST use a 640 by 640 letterbox input.
YOLO MUST keep only COCO class 39, `bottle`.
YOLO MUST select the largest central bottle.
YOLO MUST remove letterbox padding from the output mask.
YOLO MUST use CPU in this implementation.
YOLO MUST report an error when it does not find a bottle.
YOLO MUST NOT fall back to DIS when YOLO is selected.

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
The explicit `GPU` mode MUST report an invalid GPU result when the dual-GPU safety
rule does not select CPU.
The explicit `CPU` mode MUST not load the model on GPU.
The recognition engine MUST reuse the LiteRT environment, compiled models, and tensor
buffers across requests.
The recognition engine MUST not keep two GPU compiled models open at the same time.
When DIS and SigLIP2 both resolve to GPU, the engine MUST keep DIS on GPU and use
SigLIP2 on CPU.

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

The APK MUST contain a built-in format version 3 model pack.
The built-in pack MUST use the completed
`android-siglip2-base-224-dis-white-rot5` embedding index.
The index MUST contain one reference vector at each angle from 0 degrees through 355
degrees in 5-degree intervals.
Each selected catalogue image MUST have 72 reference vectors.
The query image MUST produce one vector.
The application MUST use the maximum score across the 72 reference vectors of each wine.
The built-in pack MUST contain one transparent package cut for each included wine.
The built-in pack MUST contain the verified YOLO26n-seg LiteRT file.
The package cut MUST be WebP with a long side of 1,024 pixels or less.
The built-in pack MUST NOT contain the large `main_patched` or `main` source image.
The source image MUST identify the selected vector and package cut only.
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

The debug build MUST create a distribution copy named
`chtozavino-<version>-debug.apk`.
The debug build MUST keep its HTTP server off by default.
The debug settings page MUST provide an `HTTP-сервер для тестов` switch.
The switch MUST start or stop the server immediately.
The application MUST save the switch value between starts.
The server MUST use port `18088` when the switch is on.
The server MUST listen on all device interfaces.
The server MUST provide `GET /healthz`.
The server MUST provide `POST /v1/eval/predict` with the matcher `slug-object` response.
The server MUST provide `POST /v1/match` with the matcher `candidates` response.
Both POST operations MUST read the image from multipart field `image`.
The server MUST reject an image above 20 MiB.
The optional `k` value of `/v1/match` MUST be an integer from 1 through 20.
The default `k` value MUST be 20.
The server MUST use the installed model pack.
The server MUST use the saved `DIS / YOLO` setting.
The server MUST use the saved DIS and SigLIP2 accelerator settings.
The server MUST serialize model inference.
The debug endpoints MUST not run barcode recognition.
The debug endpoints MUST not add a history row.
The release settings page MUST NOT show the HTTP server switch.
The release build MUST NOT contain the HTTP server or its NanoHTTPD dependency.

## Product icon

The launcher icon MUST use `../assets/product-logo-640x640.png` as its artwork source.
The application MUST provide an adaptive launcher icon.

## Out of scope

The current project does not download a model pack after application installation.
The current project does not update or replace the built-in model pack through the user interface.
Downloadable model packs are a possible future feature.
