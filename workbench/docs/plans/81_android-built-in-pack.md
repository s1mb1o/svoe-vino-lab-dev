# Android built-in DIS catalogue pack

Date: 2026-09-29

## Goal

Finish the Android application with a built-in offline model pack.
The application MUST work after installation without a manual model-pack import.

Use the catalogue vectors from `android-siglip2-base-224-dis-white`.
Use one catalogue image for each active wine.
Use `main_patched` when it exists.
Otherwise, use `main`.

## Source

Use `workbench/data/catalog/catalog.sqlite3` as the catalogue source.
Use the selected image bytes from `workbench/data/catalog/images/` or
`workbench/data/catalog/cuts/`.
Use the completed DIS embedding index from
`workbench/data/catalog/embeddings/android-siglip2-base-224-dis-white/`.

Use the pinned LiteRT model files from the shared Hugging Face cache.
Verify both model SHA-256 values before the pack is written.

## Catalogue selection

Select active wines only.
Select at most one image for each wine.
Select `main_patched` before `main`.
Do not select `full_front`, `full_back`, `label_front`, or `label_back`.

The selected source SHA-256 MUST have one current `full` vector in the DIS index.
Omit a wine when it has no selected image or no current vector.
Report every omitted wine.

Write one vector row and one candidate row for each included wine.
Duplicate a vector when two wines use the same source image.
This keeps the Android relation one-to-one and makes the pack easy to audit.

## Pack format

Add format version 2 of `svoe-vino-android-model-pack`.
Keep format version 1 readable for a manual legacy update.

Version 2 MUST add `images.zip` as a verified root payload.
`images.zip` MUST contain one path `images/<wine_slug>.<extension>` for each included
wine.
Each `wines.jsonl` row MUST contain its `image_path`.

The application MUST verify the byte length and SHA-256 of `images.zip` before it
extracts an image.
The application MUST reject unsafe inner ZIP paths, duplicate paths, and an oversized
image payload.

Generated model packs and model files MUST stay outside Git.
The generated built-in pack path is
`android/app/src/main/assets/default_model_pack.zip`.
Git MUST ignore this file.

## Application behavior

On the first start, install `default_model_pack.zip` from Android assets.
Do the copy and verification on an IO dispatcher.
Show progress while the first-start installation runs.

Do not replace an installed pack on each start.
A pack that the user selects through the document picker MUST replace the built-in pack.
Keep the document-picker update action in the user interface.

Show the selected catalogue image in each recognition result.
Continue to show the local result when the network is unavailable.

## Tool

Add `android/tools/build_catalog_pack.py`.
The command MUST read `data/catalog/` directly.
The command MUST be deterministic except for the explicit pack version and creation
time.
The command MUST write atomically.
The command MUST validate the completed pack before publication.

## Checks

1. Unit tests MUST verify `main_patched` precedence.
2. Unit tests MUST verify the one-image and one-vector rule.
3. Unit tests MUST verify the image archive and hashes.
4. Android tests MUST verify the optional `image_path` field.
5. `lintDebug`, unit tests, and `assembleDebug` MUST pass.
6. The APK MUST contain `assets/default_model_pack.zip`.
7. The installed pack MUST contain only the selected `main_patched` or `main` image for
   each included wine.
8. The pack vector dimension MUST be 768.
9. Each vector MUST be finite and L2-normalized.

## Safety

Do not change the workbench database or an embedding index.
Do not call a model service.
Do not restart a service.

## Completion

Completed on 2026-09-29.

The generated pack contains 2,093 wines, 2,093 vectors, and 2,093 images.
The selection contains 23 `main_patched` images and 2,070 `main` images.
Five active wines were omitted because they have no eligible image.
The pack contains 135 local code relations.
The pack SHA-256 is
`da8a079c5e599c663e3a844d743af5103a9b8b896aa15f1660f07c1cdea56684`.

Five Python pack tests passed.
The Android debug and release unit tests passed.
`lintDebug` and `assembleDebug` passed.
The APK contains the pack as an uncompressed asset.
A fresh installation and first-start pack installation passed on an arm64 Android 14
phone.
Interactive UI and inference checks are still pending because the phone was locked.
