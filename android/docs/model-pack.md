# Model-pack contract

The application reads one ZIP file.
The application supports format versions 1 and 2.
The application uses the built-in format version 2 pack on the first start.
The production user interface does not expose pack installation or replacement.

## Root payloads

Both format versions MUST contain these files at the ZIP root:

- `manifest.json`
- `dis.tflite`
- `siglip2_base_224_fp16.tflite`
- `vectors.f32`
- `candidates.jsonl`
- `wines.jsonl`
- `codes.jsonl`

Format version 2 MUST also contain `images.zip` at the ZIP root.
The application rejects an unknown root payload.
The application rejects a duplicate root payload.

`manifest.json` MUST use format `svoe-vino-android-model-pack`.
The manifest MUST declare pipeline `dis-white-square-timm-crop090-v2`.
The manifest MUST declare model `vit_base_patch16_siglip_224.v2_webli`.
The manifest MUST declare vector dimension 768.
The SHA-256 of `dis.tflite` MUST be
`0c3c93b6a2a65e7c69137ec82596944e6bfb97d982c75bab03acb0738dbaa087`.
The SHA-256 of `siglip2_base_224_fp16.tflite` MUST be
`a30ebb7b3ee15eaa68a18f9ab6a2ed740c15c343d25d898dc482317473320854`.

The manifest `files` object MUST record the byte length and SHA-256 of each root
payload except `manifest.json`.
The application verifies these values before it activates a pack.

## Catalogue payloads

`vectors.f32` contains little-endian float32 rows.
Each vector MUST be finite and L2-normalized.

`candidates.jsonl` contains one object for each vector relation.
Each object has `vector_row`, `wine_slug`, and `view`.
The application searches rows whose view is `full`.

`wines.jsonl` contains one wine card on each line.
The required fields are `wine_slug`, `name`, and `page_url`.
A format version 2 row also contains `image_path`, `image_type`, and `image_sha256`.

`codes.jsonl` contains local barcode and QR relations.
Each line has `value`, `kind`, and `wine_slug`.
Supported kinds are `gtin`, `barcode`, and `qr_url`.

## Catalogue images

Format version 2 uses one catalogue image for each included wine.
`images.zip` MUST contain each image at
`images/<wine_slug>.<extension>`.
The `image_path` value in `wines.jsonl` MUST identify this path.
The `image_count` value MUST equal the wine count.

The application extracts the image archive only after it verifies the root archive
hash.
The application rejects an unsafe path, a duplicate path, more than 5,000 images, or
more than 512 MiB of extracted image data.

## Built-in pack

Use this command from the Android project to build the application pack from the
workbench catalogue:

```text
python3 tools/build_catalog_pack.py --replace --version 20260929-dis-main
```

The command reads these sources by default:

- `../workbench/data/catalog/catalog.sqlite3`
- `../workbench/data/catalog/embeddings/android-siglip2-base-224-dis-white/`
- the verified DIS and SigLIP2 LiteRT files in the shared Hugging Face cache

The command selects active wines only.
The command selects `main_patched` before `main`.
The command writes one vector, one candidate relation, and one image for each included
wine.
The command reports each omitted wine.

The default output is
`app/src/main/assets/default_model_pack.zip`.
Git ignores this generated file.
The file MUST exist before an APK is built for distribution.

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
