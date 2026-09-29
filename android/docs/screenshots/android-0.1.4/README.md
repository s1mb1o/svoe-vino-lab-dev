# Android 0.1.4 screenshot set

This set shows the installed Android application on a Google Pixel 8.
The phone ran Android 17 at API level 37.
The application ID was `chtozavino.alolalab.com`.
The application used the built-in `20260929-dis-main` pack.

The `raw/` directory contains full 1,080 by 2,400 pixel PNG screenshots.
The `web/` directory contains cropped 1,080 by 2,199 pixel WebP files.
The WebP files exclude the Android status bar and navigation bar.

## Primary screenshots

1. `01_age_consent_light` shows the 18+ consent window.
2. `02_bottle_selected_light` shows a selected bottle in the light theme.
3. `03_bottle_selected_dark` shows the same bottle in the dark theme.
4. `04_recognition_result_dark` shows the verified `Пино Нуар` result at
   `Сходство: 91%`.
5. `05_processing_pipeline_dark` shows the DIS mask and the start of the crop stage.
6. `06_history_dark` shows the saved `Пино Нуар` history row.
7. `07_settings_dark` shows the built-in pack and the DIS and SigLIP2 accelerator
   controls.
8. `08_barcode_result_dark` shows the EAN-13 result for `4630037250909`.

## Detail screenshots

- `05b_cropped_image_dark` shows the crop stage.
- `05c_white_background_dark` shows the white-background square stage.
- `07b_settings_about_dark` shows the saved GPU selections, application version, and
  product-site link.

## Presentation files

- `android-0.1.4-contact-sheet.png` is a lossless contact sheet for presentations.
- `android-0.1.4-contact-sheet.webp` is the smaller website version.

## Functional verification

The photo example ran through DIS, SigLIP2, and local vector search on the Pixel 8.
DIS used the GPU.
SigLIP2 used the GPU.
The result was `Пино Нуар` at `Сходство: 91%`.
The application saved this result in history.

Google Code Scanner read the physical EAN-13 code `4630037250909` through the camera.
The local catalogue resolved the code to `Шато Тамань. Каберне Совиньон` at
`Сходство: 100%`.
The scanner also displayed its manual-input fallback before it read the code.

The result link and the settings link were tested before this capture session.
The result link opened the exact wine page on `vino-svoe.ru`.
The settings link opened `https://vino-svoe.ru`.

The capture used Android System UI demo mode only to make the time and battery value
stable.
The test restored the original dark system theme after capture.
The test disabled System UI demo mode after capture.
The test removed the temporary source image from the phone after capture.
