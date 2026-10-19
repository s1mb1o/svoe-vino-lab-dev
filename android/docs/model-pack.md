# Model-pack contract

The application reads one ZIP file.
The application supports format versions 1, 2, 3, 4, and 5.
The application uses the built-in format version 3 pack on the first start.
The production user interface does not expose pack installation or replacement.

## Root payloads

All supported format versions MUST contain these common files at the ZIP root:

- `manifest.json`
- `dis.tflite`
- `vectors.f32`
- `candidates.jsonl`
- `wines.jsonl`
- `codes.jsonl`

Format version 2 MUST also contain `images.zip` at the ZIP root.
Format version 3 MUST also contain these files at the ZIP root:

- `images.zip`
- `yolo26n-seg_w8a32.tflite`

Format versions 1 through 3 MUST contain `siglip2_base_224_fp16.tflite`.
Format versions 4 and 5 MUST contain these files instead:

- `siglip2_naflex_backbone.tflite`
- `siglip2_naflex_pooling.tflite`
- `siglip2_naflex_position_embeddings.f32`
- `images.zip`
- `yolo26n-seg_w8a32.tflite`

The application rejects an unknown root payload.
The application rejects a duplicate root payload.

`manifest.json` MUST use format `svoe-vino-android-model-pack`.
Formats 1 through 3 MUST declare pipeline `dis-white-square-timm-crop090-v2`.
Formats 1 through 3 MUST declare model `vit_base_patch16_siglip_224.v2_webli`.
Formats 1 through 3 MUST declare vector dimension 768.
Format 4 MUST declare pipeline `foreground-white-native-naflex-v1`.
Format 4 MUST declare model `google/siglip2-so400m-patch16-naflex`.
Format 4 MUST declare runtime `naflex-exact-split`.
Format 4 MUST declare vector dimension 1,152.
Format 4 MUST declare patch size 16.
Format 4 MUST declare a patch limit of 256, 512, or 1,024.
Format 4 MUST declare a 16 by 16 source position grid.
Format 5 MUST declare pipeline `foreground-white-native-naflex-v1`.
Format 5 MUST declare model `google/siglip2-base-patch16-naflex`.
Format 5 MUST declare runtime `naflex-exact-split`.
Format 5 MUST declare vector dimension 768.
Format 5 MUST declare patch size 16.
Format 5 MUST declare a patch limit of 256, 512, or 1,024.
Format 5 MUST declare a 16 by 16 source position grid.
Format 5 MAY declare pooling mode `foreground-1.0-background-0.1`.
The default pooling mode is `standard`.
All formats MAY declare reference aggregation `max` or `top2-mean`.
The default reference aggregation is `max`.
Formats 4 and 5 MAY declare `gpu_compatible: true` only after a device parity test
passes.
The pack builders MUST write `gpu_compatible: false` by default.
The SHA-256 of `dis.tflite` MUST be
`0c3c93b6a2a65e7c69137ec82596944e6bfb97d982c75bab03acb0738dbaa087`.
The SHA-256 of `siglip2_base_224_fp16.tflite` MUST be
`a30ebb7b3ee15eaa68a18f9ab6a2ed740c15c343d25d898dc482317473320854`.
The SHA-256 of `yolo26n-seg_w8a32.tflite` MUST be
`3a9d800e59071e32516511bd788bf73a229e8b62c09eed96d6789894bc238acf`.

The manifest `files` object MUST record the byte length and SHA-256 of each root
payload except `manifest.json`.
The application verifies these values before it activates a pack.
The application limits the extracted root payloads to 2 GiB.

## NaFlex split

This contract describes this repository's experimental split runtime.
It does not describe the separate `siglip2-naflex-litert` v0.2.0 model package.
Read [the implementation comparison](naflex-implementations.md) for the verified
complete-graph GPU library.

The NaFlex backbone accepts normalized patches, resized position vectors, and one
additive attention mask.
It returns patch tokens before the final vision LayerNorm.
The pooling model applies the original vision LayerNorm, attention pooling, pooling
LayerNorm, and MLP residual.
It returns one vector.
Format 4 returns 1,152 dimensions.
Format 5 returns 768 dimensions.
The application L2-normalizes this vector.

The foreground-aware pooling mode MUST reuse the DIS or YOLO mask.
It MUST calculate each patch foreground mean.
It MUST calculate each valid patch weight as `0.1 + 0.9 * foreground`.
It MUST add `log(weight)` to the attention logit.
It MUST keep padding logits masked.

The current Android runtime runs the backbone on LiteRT CPU/XNNPACK.
The pooling model always uses LiteRT CPU/XNNPACK.
The Pixel 8 GPU delegate returned incompatible vectors for the tested SO400M p512,
Base p256, and Base p512 backbones.
The application disables NaFlex GPU unless the pack declares completed compatibility.
The Android preprocessor preserves the segmented crop aspect ratio.
It implements the SigLIP2 maximum-patch resize rule.
It uses RGB values in patch-row, patch-column, pixel-row, pixel-column, channel order.

## Catalogue payloads

`vectors.f32` contains little-endian float32 rows.
Each vector MUST be finite and L2-normalized.

`candidates.jsonl` contains one object for each vector relation.
Each generated built-in object has `vector_row`, `wine_slug`, `view`, and `angle`.
The application searches rows whose view is `full`.
The built-in pack MUST contain the angles `0, 5, …, 355` for each included wine.
The built-in pack MUST contain 72 reference vectors for each included wine.
The application uses the maximum cosine similarity across the rows of one wine.

The manifest MUST set `reference_rotation_step_degrees` to `5`.
The manifest MUST set `reference_frames_per_image` to `72`.

`wines.jsonl` contains one wine card on each line.
The required fields are `wine_slug`, `name`, and `page_url`.
A format version 2 or 3 row also contains `image_path`, `image_type`, and
`image_sha256`.
The generated built-in row also contains `image_source_type`, `image_source_sha256`,
and `image_cut_sha256` for provenance.

`codes.jsonl` contains local barcode and QR relations.
Each line has `value`, `kind`, and `wine_slug`.
Supported kinds are `gtin`, `barcode`, and `qr_url`.

## Catalogue images

Format version 2, 3, 4, or 5 uses one catalogue image for each included wine.
`images.zip` MUST contain each image at
`images/<wine_slug>.<extension>`.
The `image_path` value in `wines.jsonl` MUST identify this path.
The `image_count` value MUST equal the wine count.

The application extracts the image archive only after it verifies the root archive
hash.
The application rejects an unsafe path, a duplicate path, more than 5,000 images, or
more than 512 MiB of extracted image data.

The generated built-in pack MUST use transparent WebP package cuts.
Each package cut MUST come from an `image_derivative` row with `kind=package`.
The long side of each image MUST be 1,024 pixels or less.
The exporter MUST verify that each image has a transparent pixel.
The pack MUST NOT contain the large `main` or `main_patched` source image.
Those source images identify the matching vector and package cut only.

## Built-in pack

Use this command from the Android project to build the application pack from the
workbench catalogue:

```text
python3 tools/build_catalog_pack.py \
  --replace \
  --version <version>
```

The command reads these sources by default:

- `../workbench/data/catalog/catalog.sqlite3`
- `../workbench/data/catalog/embeddings/android-siglip2-base-224-dis-white-rot5/`
- the verified DIS and SigLIP2 LiteRT files in the shared Hugging Face cache
- the verified YOLO26n-seg LiteRT file in the shared Ultralytics cache

The YOLO file path is
`~/.config/Ultralytics/yolo26n-seg_w8a32.tflite` by default.
The official source is the Ultralytics YOLO Flutter release `v0.6.6`.
The model metadata declares task `segment`, image size 640, COCO classes, and the
AGPL-3.0 license.

The command selects active wines only.
The command selects `main_patched` before `main` to find the indexed vector.
The command writes 72 vectors, 72 candidate relations, and one transparent package cut
for each included wine.
The candidate relations use the angles `0, 5, …, 355`.
The exporter rejects an incomplete or differently ordered angle sequence.
The command converts each cut to transparent WebP at quality 80.
The command limits the long side to 1,024 pixels.
The command does not copy `main` or `main_patched` source images.
The command reports each omitted wine.

The default output is
`app/src/main/assets/default_model_pack.zip`.
Git ignores this generated file.
The file MUST exist before an APK is built for distribution.

## NaFlex pack

Export the two verified LiteRT models outside the repository:

```text
python3 tools/export_siglip2_naflex_split.py \
  --max-num-patches 512 \
  --out-dir /path/out/android-siglip2-so400m-naflex-p512-split
```

The exporter reads `google/siglip2-so400m-patch16-naflex` from the local Hugging Face
cache.
The exporter compares the original PyTorch output, the split PyTorch output, and both
LiteRT outputs.
The exporter writes `metadata.json` with shapes, hashes, versions, and parity values.

Build a format version 4 pack with the matching workbench index:

```text
python3 tools/build_catalog_pack.py \
  --catalog /path/to/workbench/data/catalog \
  --embedding gx10-siglip2-so400m-patch16-naflex-p512-rot5 \
  --siglip-runtime naflex-exact-split \
  --naflex-model-dir /path/out/android-siglip2-so400m-naflex-p512-split \
  --out /path/out/android-naflex-p512-pack-v4.zip
```

Write generated models and packs outside Git.

Use `--model-id google/siglip2-base-patch16-naflex` for format version 5.
Use `--pooling foreground-1.0-background-0.1` to export the 5a pooling head.
Use `--reference-aggregation top2-mean` to make that aggregation the pack default.

The Pixel 8 Base pilot report is in
`reports/2026-10-19_pixel8-siglip2-base-pilot/report.md`.

## Legacy pack tool

Use this command to make a format version 1 pack from a compatible matcher bundle:

```text
python3 tools/build_model_pack.py \
  --bundle /path/to/base-224-dis-bundle \
  --catalog-db ../workbench/data/catalog/catalog.sqlite3 \
  --dis-model /path/to/dis.tflite \
  --siglip-model /path/to/siglip2_base_224_fp16.tflite \
  --confirm-pipeline dis-white-square-timm-crop090-v2 \
  --out /path/out/svoe-vino-android-model-pack.zip
```

Write a legacy pack outside the repository.
The production user interface does not expose this pack.
