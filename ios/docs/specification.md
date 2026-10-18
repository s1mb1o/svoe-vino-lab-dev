# iPhone application specification

Date: 2026-10-03

## Purpose

The application identifies one wine from a bottle photograph.
The application runs recognition on the iPhone.
The application opens the matching page on `vino-svoe.ru`.

## Platform

- The minimum version MUST be iOS 17.2.
- The application MUST use SwiftUI.
- The bundle identifier MUST be `chtozavino.alolalab.com`.
- The user interface MUST be in Russian.
- The application theme MUST follow the system light or dark setting.

## Accessibility

- The application MUST support VoiceOver on every user flow.
- Every interactive control MUST have a clear Russian accessibility name.
- An icon-only control MUST have an accessibility label.
- A control whose result is not clear from its name MUST have an accessibility hint.
- The application MUST use accessibility headings for the screen title and result groups.
- The application MUST move VoiceOver focus to the recognition action after image selection.
- The application MUST move VoiceOver focus to the result group after recognition.
- The application MUST announce long-running operation status changes to VoiceOver.
- Each interactive control MUST have a hit region of at least 44 by 44 points.
- The interface MUST support all Dynamic Type sizes.
- The interface MUST keep all text and controls available at accessibility text sizes.
- Horizontal content groups MUST use a vertical layout when accessibility text sizes need more space.
- A state MUST NOT use color as its only indicator.
- The application MUST follow Reduce Motion.
- The application MUST follow Reduce Transparency.
- The application MUST remain usable with Increase Contrast.
- Decorative images MUST be hidden from assistive technologies.
- An informative image MUST have an accessibility label or an adjacent text description.
- The scanner MUST provide manual code input.
- VoiceOver MUST report a detected scanner value in the manual input field.
- The application MUST use standard controls for Voice Control and Switch Control compatibility.
- The UI test target MUST audit the age gate, recognition screen, history screen, settings screen, code scanner, and unavailable-camera screen.
- The recognition test MUST start at the largest accessibility text size.
- The recognition test MUST verify that each main control is at least 44 by 44 points.

## User flow

1. The application MUST request an 18+ confirmation before it shows the main content.
2. The user MAY take a photograph.
3. The user MAY select an image from the photo library.
4. The user MAY scan EAN, UPC, Code 128, Data Matrix, or QR codes.
5. The user MAY enter a code manually when a camera is not available.
6. The user starts image recognition with the button `Начать распознавание`.
7. The application shows ranked results and one catalogue image for each result.
8. The application shows the selected segmenter mask, the crop, and the white-background image in the
debug section.
9. The user MAY open a result on `vino-svoe.ru`.
10. The application MUST store local result history.
11. The top application bar MUST contain a settings gear icon.
12. The recognition screen MUST show `Не требует интернета`.
13. The bottom navigation MUST provide recognition and history tabs.
14. The settings page MUST show the application version.
15. The settings page MUST show a link to `https://vino-svoe.ru`.

## Encoders

The settings page MUST let the user select `SigLIP2 Base NaFlex p512`, `SigLIP2 Base 224`, or `MobileCLIP2-S2`.
The application MUST save the selection.
The default selection MUST be `SigLIP2 Base NaFlex p512`.
The application MUST use only the vector index for the selected encoder.

## Image recognition

The settings page MUST let the user select `DIS` or `YOLO`.
The application MUST save the selection.
The default selection MUST be `DIS`.

The DIS pipeline MUST perform these steps:

1. Decode the image and correct its orientation.
2. Limit the long side to 2,048 pixels.
3. Run DIS at 1,024 by 1,024 pixels.
4. Calculate the foreground box from mask values of 0.5 or more.
5. Add a four-percent margin to the foreground box.
6. Crop the source image and the alpha mask to this box.
7. Composite the crop on white with the soft alpha mask.
8. Put the crop in the center of a square white image.

The YOLO pipeline MUST perform these steps:

1. Resize the image into a 640 by 640 letterbox.
2. Fill the letterbox with RGB value 114.
3. Run the Core ML export of the official `yolo26n-seg` checkpoint on CPU.
4. Read the raw 116 by 8,400 detection tensor.
5. Read the 32 by 160 by 160 mask prototype tensor.
6. Select class 39, which is the COCO `bottle` class.
7. Reject a bottle score below 0.25.
8. Select the largest central bottle.
9. Build the instance mask from its 32 mask coefficients.
10. Remove the letterbox area from the mask.
11. Use the same threshold, margin, crop, white composite, and square operations as DIS.

The SigLIP2 path MUST perform these additional steps:

1. Resize the square image to 224 by 224 pixels.
2. Resize the image to 248 by 248 pixels.
3. Take the centered 224 by 224 crop.
4. Normalize RGB values to `[-1, 1]` in NCHW order.
5. Run the Core ML export of `vit_base_patch16_siglip_224.v2_webli`.
6. Compare the normalized 768-dimensional vector with the SigLIP2 index.

The SigLIP2 Base NaFlex p512 path MUST perform these additional steps:

1. Resize the square image to 352 by 352 pixels.
2. Normalize RGB values to `[-1, 1]`.
3. Split the image into a row-major 22 by 22 grid of 16-pixel patches.
4. Flatten each patch in pixel and RGB channel order.
5. Run the Core ML export of `google/siglip2-base-patch16-naflex`.
6. Compare the normalized 768-dimensional vector with the p512 index.

The MobileCLIP2 path MUST perform these additional steps:

1. Resize the square image to 256 by 256 pixels.
2. Use RGB float values in the range required by the exported model.
3. Run the Core ML export of `MobileCLIP2-S2`.
4. Compare the normalized 512-dimensional vector with the MobileCLIP2-S2 index.

The application MUST use dot product as cosine similarity.
The application MUST use the maximum image score as the wine score.
The user interface MUST show `Сходство: <whole percent>%`.
The user interface MUST NOT describe the cosine score as confidence.
The application MUST reject a wrong output size or a non-finite value.

## Compute units

The settings page MUST provide `Авто`, `ANE`, and `CPU` for DIS and the image encoder.
`Авто` MUST use all compute units available to Core ML.
`ANE` MUST use CPU and Neural Engine compute units.
`CPU` MUST use the CPU only.
The application MUST save both selections.
The iOS simulator MUST use CPU because it does not provide iPhone ANE execution.
The application MUST test CPU and Neural Engine model compatibility on the first start.
The settings page MUST let the user repeat this test.
The compatibility text MUST not claim that Core ML used ANE because Core ML does not
report the selected execution unit.

## Barcode and QR recognition

The application MUST use VisionKit `DataScannerViewController` on a physical iPhone.
The scanner MUST request EAN-8, EAN-13, UPC-E, Code 128, Data Matrix, and QR formats.
The application MUST report an unavailable scanner, an empty value, or cancellation.
The application MUST normalize a 13-digit EAN value to the stored 14-digit GTIN key.
The application MUST resolve the returned value in the local resource pack.
The application MUST not upload a scanned value.
The simulator MUST provide manual code input because camera scanning is unavailable.

## Resource pack

The application MUST contain a built-in iOS resource pack.
The pack MUST contain wine metadata, local code relations, and one catalogue image for
each included wine.
The pack MUST contain one compatible vector index for each encoder.
The application MUST install the built-in pack on the first start.
The application MUST show progress during this operation.
The settings page MUST show the pack version and counts.
The application MUST verify SHA-256 and byte length for every root payload.
The application MUST complete the full integrity check before it writes a validation receipt.
The application MAY reuse the validation receipt when the pack version and manifest SHA-256 match.
The application MUST reject unsafe relative paths and unknown payloads.
Recognition MUST work without a network connection after installation.

## History

The application MUST store at most 50 history rows.
Each row MUST contain the time, recognition source, encoder, best result, score, page
URL, and a local preview when one exists.
History data MUST stay on the device.
The history page MUST show a clear empty-state message before the first saved result.

## Debug build

The debug settings page MUST provide an `HTTP-сервер для тестов` switch.
The server MUST use port `18088`.
The server MUST listen on all device interfaces.
The server MUST provide `GET /healthz`.
The server MUST provide `POST /v1/eval/predict`.
The server MUST provide `POST /v1/match`.
Both POST operations MUST read multipart field `image`.
The server MUST reject an image above 20 MiB.
The optional `k` value MUST be from 1 through 20.
The default `k` value MUST be 20.
The server MUST serialize inference.
The endpoints MUST not add a history row.
The match response MUST identify the selected segmenter and encoder in `pipeline`.
The release build MUST not start the debug server.

## Product icon

The application icon MUST use `../assets/product-logo-640x640.png` as its artwork source.
