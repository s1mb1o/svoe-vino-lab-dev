# Model-pack contract

The application imports one ZIP file.
The ZIP MUST contain these files at its root:

- `manifest.json`
- `dis.tflite`
- `siglip2_base_224_fp16.tflite`
- `vectors.f32`
- `candidates.jsonl`
- `wines.jsonl`
- `codes.jsonl`

`manifest.json` MUST use format `svoe-vino-android-model-pack` and version 1.
The manifest MUST declare pipeline `dis-white-square-v1`.
The manifest MUST declare model `vit_base_patch16_siglip_224.v2_webli`.
The manifest MUST declare vector dimension 768.

`vectors.f32` contains little-endian float32 rows.
Each vector MUST be finite and L2-normalized.

`candidates.jsonl` contains one object per vector relation.
Each object has `vector_row`, `wine_slug`, and `view`.
The application searches rows whose view is `full`.

`wines.jsonl` contains one wine card per line.
The required fields are `wine_slug`, `name`, and `page_url`.

`codes.jsonl` contains local barcode and QR relations.
Each line has `value`, `kind`, and `wine_slug`.
Supported kinds are `gtin`, `barcode`, and `qr_url`.

Use this command to make a pack from a compatible matcher bundle:

```text
python3 tools/build_model_pack.py \
  --bundle /path/to/base-224-dis-bundle \
  --catalog-db ../workbench/data/catalog/catalog.sqlite3 \
  --dis-model /path/to/dis.tflite \
  --siglip-model /path/to/siglip2_base_224_fp16.tflite \
  --confirm-pipeline dis-white-square-v1 \
  --out /path/out/svoe-vino-android-model-pack.zip
```

The script MUST write the pack outside the repository.
