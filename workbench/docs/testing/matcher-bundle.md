# Matcher bundle

The matcher bundle is a versioned directory. It contains the vectors and catalogue
metadata that a matcher needs at run time. The matcher does not need `lab.sqlite3`, the
source embedding index, or a lab module.

## Contents

Every bundle contains these files:

- `manifest.json` defines the format, vector contract, counts, and payload hashes.
- `vectors.npy` contains a compact C-order `float32` matrix.
- `items.jsonl` maps each vector row to one prepared source item.
- `candidates.jsonl` maps each vector row to one or more wine slugs.
- `wines.jsonl` contains the exported wine metadata.
- `omissions.jsonl` identifies planned items that were not current during the export.

The option `--include-images` also copies the prepared images. The option adds
`images.jsonl`. This file contains one SHA-256 value and byte size for each image.

## Format versions

The builder writes format version 2. The validator accepts version 1 and version 2.
The two versions differ only in `wines.jsonl`.

A version 1 wine record has `wine_slug`, `name`, `producer`, `category`, and `region`.

A version 2 wine record also has the wine card fields of the matcher endpoint
`/v1/match` (plan 74):

| Field | Source | Value |
|---|---|---|
| `color` | `wine_catalog.color` | string or `null` |
| `grapes` | `wine_catalog.grapes` | string or `null` |
| `page_url` | the slug | `https://vino-svoe.ru/wines/<slug>` |
| `image_url` | `wine_image.source_name` of the image type `main` | `https://api.vino-svoe.ru/v1/img/str-api/1920/1920/resize/uploads/<name>`, or `null` without a `main` image |
| `qr_urls` | `wine_code.value` with `kind = 'qr_url'` | a sorted list of unique normalized URLs |

`image_url` uses `main` because `main` is the official catalogue image.
`main_patched` is a lab image that the catalogue site does not serve.
The QR URL normalization uses the rules of `telegram-bot`: a lowercase scheme and host,
no default port, no fragment, and no user information.

## Build a bundle

Run the builder from the workbench root. The configured database and the embedding index
MUST exist. The output path MUST not exist.

```bash
python3 scripts/build_matcher_bundle.py \
    --embedding gx10-dinov3-vitb16 \
    --out work/matcher-bundles/gx10-dinov3-vitb16
```

Add the prepared images when the consumer needs them:

```bash
python3 scripts/build_matcher_bundle.py \
    --embedding gx10-dinov3-vitb16 \
    --out work/matcher-bundles/gx10-dinov3-vitb16-with-images \
    --include-images
```

The builder writes a temporary sibling directory. It validates the temporary bundle.
It then renames the directory to the requested output path. A failed build does not
publish a partial bundle.

The builder does not call an external service. It reads `config.yaml` by default. Use
`--config <path>` to select another configuration.

## Validate a bundle

The validator is read-only. It does not read the lab database or the source embedding
directory.

```bash
python3 scripts/validate_matcher_bundle.py \
    work/matcher-bundles/gx10-dinov3-vitb16
```

Exit code `0` means that the bundle satisfies the supported contract. Exit code `2`
means that validation failed. The error identifies the first failed check.

The validator checks these properties:

- The format name and version are supported.
- Every payload has the declared SHA-256 value and byte size.
- The vector matrix has the declared shape and `float32` type.
- The matrix is C-contiguous, finite, and L2-normalized.
- Vector rows are contiguous and have catalogue candidates.
- Candidate rows name exported wines and the correct views.
- A version 2 wine record has all card fields, an HTTPS `page_url`, an HTTPS or `null`
  `image_url`, and unique normalized `qr_urls`.
- Optional image paths are safe and identify regular files.
- Optional image hashes and sizes match the image manifest.

## Run the tests

The tests use a temporary database, a local fake embedding gateway, and temporary
bundle directories. They do not call an external service.

```bash
python3 -m unittest discover -s tests -p 'test_matcher_bundle.py'
```

## Interpret the summary

`items` is the number of exported vector rows. `candidates` can be greater than
`items`, because one source image can belong to more than one wine. `omissions` is the
number of planned items that were failed, missing, or stale at export time. The bundle
contains only current items.

## Troubleshooting

- Build the selected embedding before an export if its index or vector file is absent.
- Use a new output path if the builder reports that the path exists.
- Inspect `omissions.jsonl` if the export has fewer items than the embedding plan.
- Build a new bundle after a source database or embedding change. Do not edit a bundle
  in place.
