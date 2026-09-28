# 72 — Standalone matcher bundle

Date: 2026-09-28.
Status: complete. The owner selected the flat bundle with optional prepared images.

## Goal

Export one embedding index and its catalogue metadata into a versioned directory. A
matcher MUST read the directory without `lab.sqlite3` and without an import from the lab
code. Add a separate validator for the directory.

## Bundle contract

The bundle format is `svoe-vino-matcher-bundle`, version 1. It contains these required
files:

- `manifest.json`: the format version, embedding contract, counts, and payload hashes.
- `vectors.npy`: a compact C-order `float32` matrix with one L2-normalized vector per
  item.
- `items.jsonl`: one record per vector row.
- `candidates.jsonl`: one record per vector-row and wine relation.
- `wines.jsonl`: one record per active wine that owns an exported item.
- `omissions.jsonl`: one record per planned item that is not current in the source
  index.

With `--include-images`, the bundle also contains `images/` and `images.jsonl`. The image
manifest records the SHA-256 and byte size of each prepared image.

One source image MAY belong to more than one wine. In that case, `candidates.jsonl`
contains more than one record for the same vector row. The vector matrix does not repeat
the vector.

## Builder

1. `scripts/build_matcher_bundle.py` accepts `--embedding`, `--out`, `--config`, and
   `--include-images`.
2. The builder reads the configured database and embedding index through
   `pipeline/embeddings.py`.
3. The builder exports current items only. It compacts their vector rows.
4. The builder records failed, stale, and missing planned items in `omissions.jsonl`.
5. The builder writes a temporary sibling directory and renames it only after local
   validation succeeds.
6. The builder refuses an output path that exists.
7. The bundle contains no secret.

## Validator

1. `scripts/validate_matcher_bundle.py BUNDLE` validates a bundle without the lab
   database and without the source embedding directory.
2. It verifies the format and version.
3. It verifies each declared payload SHA-256 and byte size.
4. It loads `vectors.npy` with `allow_pickle=False`.
5. It verifies the shape, `float32` type, finite values, and L2 normalization.
6. It verifies contiguous vector rows and unique item keys.
7. It verifies every candidate row, wine slug, and view relation.
8. It verifies that every vector row has at least one candidate.
9. With images, it verifies each image path, SHA-256, byte size, and item relation.
10. It rejects absolute paths, parent traversal, and symbolic-link payloads.

## Verification

1. Nine unit tests build fixture bundles with and without images.
2. The tests verify a shared image that belongs to two wine slugs.
3. The tests validate a bundle after the source database and embedding directory move.
4. The tests reject changed payloads, invalid relations, Fortran-order vectors, and a
   symbolic-link image directory.
5. A CLI test runs both scripts.
6. A real bundle without images passed validation. It contains 4,642 items, 4,674
   candidate relations, 2,094 wines, 3 omissions, and vectors of dimension 768.
7. A real bundle with 4,642 images passed validation. Its size is 1.4 GB.
8. The 17 embedding-build tests and 38 embedding-run tests pass.
9. `git diff --check` passes.
