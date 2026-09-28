# 18 — Import the catalogue from the website

Date: 2026-09-25.
Status: approved by the owner on 2026-09-25T11:27:46+0300. The owner chose the design on 2026-09-25 (answers of about 11:13 and
11:20). Implementation by drink-atlas-workspace-ff after the approval of this plan.
The owner message of 2026-09-25T11:06:56+0300 and the seven answers after it are in
[owner-messages.md](../owner-messages.md).

Plan 21 ([21_website-import-ui.md](21_website-import-ui.md)) extends this plan: the UI
mode with the merge dialog, the refusals, the reused connection, and the two change times.

## Goal

A new tool compares the table `wine_catalog` with the live catalogue of vino-svoe.ru
and changes the database to match:

```bash
python3 pipeline/import_website.py --db data/lab.sqlite3
```

1. A wine that is not on the website becomes `Removed`. This applies to an `Active`
   wine and to a `Disabled` wine. The wine gets a comment.
2. A wine that is on the website and not in the database is created as `Active`. The
   wine gets a comment.
3. A wine that is on the website and `Removed` in the database becomes `Active`. The
   wine gets a comment.
4. A changed main image stops the import. The tool compares the website image with the
   original `main` image of the database.
5. The comments are short.

## Decisions of the owner

| Question | Answer |
|---|---|
| Source | The JSON API `https://api.vino-svoe.ru/v1`. |
| Image check | Download the original of each website wine, and compare the bytes. |
| `csv_photo_name` of a new wine | The upload file name of the website image. No schema change. |
| Restore | Each `Removed` wine that is on the website, also a wine that a person removed. |
| Changed text of a wine | Stop, as in `import_catalog.py`. The fields of the list pages. |
| Wine with no `main` row | Store the website image as `main`, and add a comment. |
| After a stop | No extra option. The owner fixes the case by hand before the next run. |

The `robots.txt` of `api.vino-svoe.ru` disallows everything except `*/img/*` and
`*/file-proxy/str-api-file-name/*`. The owner chose the API with this knowledge.

## Findings

Probes from this Mac on 2026-09-25, from about 11:08 to 11:25. No proxy is necessary.

- `GET /v1/wines?page=N&perPage=30`: 30 is the maximum page size. The answer holds
  `currentPage`, `itemsPerPage`, `totalItems`, `totalPages`, and `items`. There are
  2,105 wines on 71 pages, with no duplicate slug.
- A list item holds `slug`, `title`, `manufacturer`, `category`, `color`, `region`,
  `image.url`, `image.altText`, and `publicRating`. It holds no description and no
  grapes.
- `GET /v1/wines/<slug>` holds also `description`, `grapes[].name`, `alcohol`,
  `temperature`, and `dishes`. In the card, `manufacturer`, `category`, and `region` are
  objects with `name`.
- `GET /v1/file-proxy/str-api-file-name/uploads/<name>` returns the original upload.
  For `aligote-barrel-2024`, its SHA-256 equals the stored `main` image. The resize
  proxy `/v1/img/...` does not give the original.
- The slug set of the API equals the slug set of `wines-sitemap.xml`. The image name of
  each API item equals the image name of the sitemap.
- The API `category` holds the colour and the sweetness, for example `Белое сухое`.
  There are 19 values. The first word is one of `Белое`, `Красное`, `Розовое`, and
  `Оранжевое`. These are the four values of `wine_catalog.category`.
- The grape names of a card, joined with `, `, equal `wine_catalog.grapes` for 3 of 3
  sampled wines. The trimmed `description` is equal for the same 3 wines.
- A `title` can have a leading space, for example ` Алиготе Баррель, 2024`.

State of 2026-09-25, about 11:20. The database holds 2,103 wines, all `Active`.

| Case | Count |
|---|---|
| On the website, not in the database (new) | 73 |
| In the database, not on the website (missing) | 71 |
| On both, and the upload name of the image differs | 13 |
| … of these, the bytes are equal | 10 |
| … of these, the bytes differ | 3: `vintazh-premium`, `muskat-premium`, `shardone-rezerv` |
| On both, and the database has no `main` row | 52 |
| On both, and a list field differs | 7 wines, 9 fields |

The 9 field differences: 4 `name`, 4 `producer`, and 1 `category`
(`igristoe-vino-endemy-bianka-bryut-beloe`: `Розовое` -> `Белое`).
So the first run stops on 10 wines. It changes nothing until the owner fixes them.

A renamed slug is not detected. The old slug becomes `Removed` and the new slug is a
new wine. The new wine does not get the GTIN, the patch, or the Atlas binding of the old
slug.

## Field mapping of a new wine

| Column | Source |
|---|---|
| `wine_slug` | `slug` of the list item |
| `name` | `title`, trimmed |
| `producer` | `manufacturer` of the list item, trimmed |
| `category` | the first word of `category` of the list item |
| `color` | `color`, trimmed |
| `region` | `region` of the list item, trimmed |
| `grapes` | `grapes[].name` of the card, each trimmed, joined with `, `; NULL for an empty list |
| `description` | `description` of the card, trimmed |
| `csv_photo_name` | the base name of `image.url`, for example `DSC_09173_4a9ff95cc2.webp` |

An empty required value of a new wine stops the import.

## Rules of the import

### Compare

1. The tool reads all list pages. The number of distinct slugs MUST equal
   `totalItems`. Two different items with the same slug stop the import. A list with
   no wine stops the import.
2. For each website wine that the database holds, the tool compares `name`,
   `producer`, `category`, `color`, and `region` with the list item after the mapping
   of the table above. A difference stops the import. The error names the slug, the
   state, the field, the old value, and the new value. This applies to each state.
   `grapes` and `description` are not compared.
3. For each website wine, the tool downloads the original image. A website wine with no
   `image.url` stops the import.
4. A website wine with a `main` row: the SHA-256 of the download MUST equal the
   `sha256` of the row. A difference stops the import. The error names the slug, the
   stored `source_name` and SHA-256, and the website file name and SHA-256. The same
   bytes under a new upload name are no change. The tool compares with `main`, never
   with `main_patched`.
5. The tool collects all problems of rules 1 to 4 and of the new wines, and reports all
   of them in one error. Then it stops. The database and the image store do not change.
6. A network error or an HTTP error after the retries stops the import.

### Change

7. A new wine: the tool reads its card, inserts the row as `Active`, and stores the
   image as `main`. Comment: `New on vino-svoe.ru.`
8. A `Removed` wine on the website: `state` = `Active`, `removed_by` = NULL. This
   applies to `removed_by` = `import` and to `removed_by` = `person`. Comment:
   `Back on vino-svoe.ru.`
9. An `Active` or a `Disabled` wine that is not on the website: `state` = `Removed`,
   `removed_by` = `import`. Comment: `Missing on vino-svoe.ru.`
10. A `Removed` wine that is not on the website: no change, no comment.
11. A `Disabled` wine on the website stays `Disabled`.
12. A website wine that the database holds with no `main` row: the tool stores the
    image as `main`. Comment: `Main image from vino-svoe.ru.` A new wine gets only the
    comment of rule 7.
13. Each comment has the source `script`. The tool writes it with
    `comments.add(conn, slug, text, "script")` of plan 17.

### Store

14. A stored image follows the rules of `seed_images.py`: the file
    `images/main/<sha256>.<extension>`, the extension of the upload name in lower case,
    one row of `image`, one row of `wine_image` with the type `main`. `source_name` is
    the upload name. `match_method` is `website`. Pillow reads `width` and `height`
    from the header.
15. The tool writes a file only after the compare finds no problem. A file that the
    store holds already is not written again.
16. The tool processes each new original with `derive.derive_all` before the write
    transaction, as in `patches.py`. If SAM3 does not answer, the original stays with
    no processed file, and the report states this.
17. The store path and the `INSERT INTO image` are each in one function of the tool.
    The flat image store of plan 13 changes both lines.

### Transaction

18. The compare runs on a read of the database with no lock, because the downloads take
    minutes.
19. The write takes `BEGIN IMMEDIATE`. Then the tool reads the rows again. If a state, a
    `removed_by`, a compared field, or a `main` row changed after the first read, the
    tool stops with no change. The message asks for a new run.
20. The tool writes all rows of one run in one transaction: `wine_catalog`, `image`,
    `wine_image`, `image_derivative`, and `wine_comment`.

### Manual wines

Rules 24 to 26 of [plan 20](20_add-wine.md), approved by the owner on
2026-09-25T11:46:09+0300. A wine that a person adds by hand has a slug that starts with
`__`.

21. The import never removes a manual wine. A manual wine is not in the list `removed`
    and gets no comment.
22. A website slug that starts with `__` stops the import. The error names the slug.

## Requests

- One run sends about 71 list requests, one card request for each new wine, and one
  image request for each website wine. Now this is about 2,250 requests and about
  200 MB.
- The requests are sequential. The pause between two requests is 0.25 s, as in
  `wine-sites-crawler`. A retry follows an HTTP 408, 425, 429, 500, 502, 503, or 504,
  or a network error, at most 5 times.
- The `User-Agent` names the tool: `svoe-vino-lab import_website.py`.
- The first real run (2026-09-25, 11:31:25 to 11:53:57) took 22.5 minutes: about 1 minute
  for the 71 list pages, about 21 minutes for the 2,105 images, and less than 1 minute for
  the 73 cards.
- The tool keeps only the images of new wines and of wines with no `main` row in memory.
  It computes the SHA-256 of each other download and drops the bytes.

## Report

The output follows `import_catalog.py`:

```text
source: https://api.vino-svoe.ru/v1/wines
wines on the website: 2105
images downloaded: 2105
added: 73: …
restored: 0
removed: 71: …
main images stored: 52: …
unchanged: …
processed: crop N, seg N, no SAM3 N
database: data/lab.sqlite3
states: Active N, Disabled N, Removed N
result: imported
```

A stop prints `error:` with all problems and returns the exit status 1. A second run
with no change on the website prints `result: no change`.

## Tests

`tests/test_import_website.py` uses a fake HTTP client and a fake SAM3 client. It sends
no request to the internet. The cases:

1. A new wine, a missing `Active` wine, a missing `Disabled` wine, and a returned wine
   (`removed_by` = `import` and `person`). The states and the comments are correct.
2. A missing wine that is `Removed` already gets no second comment.
3. A changed text field stops the import. The database does not change.
4. Changed image bytes stop the import. A new upload name with the same bytes is no
   change.
5. A wine with no `main` row gets the image and the comment.
6. A list with a duplicate slug, a count that differs from `totalItems`, or no wine
   stops the import.
7. A change of the database between the compare and the write stops the import.
8. A second run prints `result: no change`.

## Files

- New `pipeline/import_website.py`, new `tests/test_import_website.py`.
- Entries in `COMMANDS.md`, `README.md`, `SMOKE_TESTS.md`, `ChangeLog.md`, and
  `ResearchLog.md`.
- No schema file. Plan 17 adds `wine_comment` (schema 011).

## First run

2026-09-25, 11:31 to 11:54, against `data/lab.sqlite3`. Exit 1, as expected. The error
lists 10 problems: the 7 wines with a changed text and the 3 changed images of the
findings. The database did not change: 2,103 wines, all `Active`, no `script` comment, no
`website` image row.

## Open points

1. The first run stops on 10 wines: 3 images and 7 wines with a changed text. The
   owner fixes them by hand. The tool gives no option for this.
2. Plan 13 (the flat image store) changes the store path and `image.folder`. The session
   of plan 13 gets a message about the new file.
