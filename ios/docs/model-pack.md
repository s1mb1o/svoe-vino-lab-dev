# iPhone resource-pack contract

Date: 2026-10-03

## Format

The application reads one generated resource directory.
The manifest format MUST be `svoe-vino-ios-resource-pack`.
The format version MUST be 1.

## Root payloads

The resource root MUST contain these files and directories:

- `manifest.json`
- `wines.jsonl`
- `codes.jsonl`
- `images/`
- `siglip2/candidates.jsonl`
- `siglip2/vectors.f32`
- `siglip2-base-naflex-p512/candidates.jsonl`
- `siglip2-base-naflex-p512/vectors.f32`
- `mobileclip2-s2/candidates.jsonl`
- `mobileclip2-s2/vectors.f32`

The application MUST reject an unknown root payload.
The manifest `files` object MUST record the byte length and SHA-256 of each payload
except `manifest.json`.

## Encoder indexes

The `siglip2` index MUST declare model `vit_base_patch16_siglip_224.v2_webli`.
The `siglip2` index MUST declare pipeline `dis-white-square-timm-crop090-v2`.
The `siglip2` index MUST have vector dimension 768.

The `siglip2-base-naflex-p512` index MUST declare model `google/siglip2-base-patch16-naflex`.
The index MUST declare pipeline `dis-white-square-siglip2-base-naflex-p512-v1`.
The index MUST have vector dimension 768.

The `mobileclip2-s2` index MUST declare model `apple/MobileCLIP2-S2`.
The `mobileclip2-s2` index MUST declare pipeline `dis-white-square-mobileclip2-s2-v1`.
The `mobileclip2-s2` index MUST have vector dimension 512.

Each `vectors.f32` file contains little-endian float32 rows.
Each vector MUST be finite and L2-normalized.
Each `candidates.jsonl` row MUST contain `vector_row`, `wine_slug`, and `view`.
The application MUST search rows whose `view` is `full`.

## Shared catalogue

Each `wines.jsonl` row MUST contain `wine_slug`, `name`, `page_url`, `image_path`, and
`image_sha256`.
Each `codes.jsonl` row MUST contain `value`, `kind`, and `wine_slug`.
The `images` directory MUST contain each image at `images/<wine_slug>.<extension>`.

The Xcode target stores the generated directory as `BuiltinPack`.
The application copies this directory to Application Support on the first start.
The application writes a validation receipt only after it verifies all payloads and images.
The receipt is next to the installed pack. It is not a pack payload.
The receipt records the pack version and the SHA-256 of `manifest.json`.
The application reuses the receipt only when both values match.
The generated directory stays outside Git.

## Core ML models

The model source directory MUST contain these generated model packages:

- `DIS.mlpackage`
- `YOLO26nSeg.mlpackage`
- `SigLIP2ImageEncoder.mlpackage`
- `SigLIP2BaseNaFlexP512ImageEncoder.mlpackage`
- `MobileCLIP2S2ImageEncoder.mlpackage`

The generated models stay outside Git.
The build scripts MUST verify their model identifiers, input shapes, output shapes, and
SHA-256 values before a distribution build.
The `tools/compile_models.py` script MUST compile the packages before Xcode project
generation.
The Xcode target MUST contain the five generated `.mlmodelc` directories.
