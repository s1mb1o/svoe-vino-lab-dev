# 47 — Read-only Drink Atlas match

Date: 2026-09-26.
Status: completed on 2026-09-26.

## Goal

Match each available `svoe-vino-lab` catalogue photo to the active Drink Atlas image
index. Use `drink-atlas-matcher` for image embedding and search. Verify each image
candidate against the catalogue fields and the saved VLM image detail. Write an offline,
sortable HTML report. Do not change either database.

## Input snapshot

The runner MUST open `data/lab.sqlite3` with SQLite URI parameters `mode=ro` and
`immutable=1`. It MUST record the database SHA-256 in the report manifest.

The runner MUST read these `wine_image.image_type` values:

- `main`
- `main_patched`
- `full_front`
- `label_front`
- `full_back`
- `label_back`

These are the names of schema 012. The first version of the runner used the names of
schema 010 (`front_full`, `front_label`, `back_full`, `back_label`). The database refuses
those names since schema 012, so that runner read no additional photo. The names were
changed on 2026-09-26 (owner message of 2026-09-26T19:37:57+0300).

The current database has 2,046 `main` links and 16 `main_patched` links. It has no
additional-photo links. The report MUST show this absence. The code MUST still support
all four additional-photo types.

The runner MUST verify that each image file exists at
`data/images/<folder>/<sha256>.<extension>`. It MUST verify the file SHA-256 before it
uses the file.

## Image candidate stage

The image candidate stage MUST use the active `drink-atlas-matcher` full-image index.
It MUST use the exact embedding pipeline of that index. It MUST generate candidates from
image embeddings only. Text, GTIN, and description evidence MUST NOT change the image
ranking.

The runner MUST use the score and margin thresholds from the completed GTIN control run.
The current selection is score `0.81` and margin `0.10`. It has 34 accepted and 34 correct
control pairs. The report MUST record the threshold file SHA-256 and the active index ID.

The runner MUST keep a pipeline-bound embedding checkpoint outside both databases. A
later run MAY reuse a vector only when the image SHA-256 and pipeline digest are equal.

## Description verification stage

The runner MUST build source properties from `wine_catalog`. It MUST use the wine name,
producer, category, colour, region, grapes, and description. It MUST read GTIN values
from `wine_code` when they exist.

The runner MUST use `image_detail.answer` as independent label evidence when the answer
exists. It MUST compare readable label text, the vintage, and the visual description
with the current Drink Atlas candidate metadata. Missing VLM detail MUST be explicit.

The verification stage MUST run after image ranking. It MUST NOT replace the top image
candidate with a text-selected candidate. A hard property conflict or a vintage conflict
MUST move the result to review.

## Wine decision

The wine decision MUST prefer `main_patched` over `main`. The `main` row MUST remain in
the evidence table when a patch exists. Additional photos MAY support the preferred
candidate. They MUST NOT silently override a conflicting patched image.

A wine is `matched` only when the effective primary image passes the image threshold and
the property verification. A weak image, a missing candidate, a conflict, or disagreement
between relevant photo roles produces `review` or `unmatched` with a reason code.

## Report

Write the report to `docs/reports/2026-09-26_drink-atlas-match/`.

The report MUST contain:

- `report.html` with sortable and filterable wine and image tables.
- Side-by-side local thumbnails for the source photo and the top Drink Atlas photo.
- `wine-decisions.jsonl` and `image-decisions.jsonl`.
- CSV files for matched, review, and unmatched wine decisions.
- `problems.jsonl` with every detected input or processing problem.
- `manifest.json` with input hashes, thresholds, index identity, counts, and timestamps.

The HTML MUST work without a server. The report MUST not embed credentials, complete Core
responses, or original image bodies.

## Verification

1. Unit tests MUST cover the read-only SQLite connection, image-role loading, patch
   precedence, description evidence, and HTML escaping and sorting controls.
2. The runner MUST verify the source database SHA-256 again after the run.
3. The complete matcher test suite MUST pass.
4. The report manifest MUST state that both databases stayed read-only.

## Result

The run processed 2,103 wines and 2,062 eligible image links.
It produced 51 matches, 1,893 review rows, and 159 unmatched rows.
The active index was stale relative to the current Core view.
The report records 2,114 unavailable candidate UUIDs and 87 wines without a current
Core candidate in the embedding top 10.
The source database SHA-256 did not change.
The run wrote zero database rows.
All 140 matcher tests passed.
