# 20 — Add a wine by hand on the Dataset page

Date: 2026-09-25.
Status: approved by the owner on 2026-09-25T11:46:09+0300. The owner chose the design on
2026-09-25 (answers of 11:40:48 and 11:42:50). Implemented by drink-atlas-workspace-fa.
The lab server on 8168 runs the code since 11:52:40. `import_website.py` of plan 18 has
rules 24 to 26 since about 11:50 (drink-atlas-workspace-ff). The slug from the name and
the optional description (owner messages of 12:05:54 and 12:09:52) are live since
12:13:40, with schema 014; `data/lab.sqlite3` is at version 14.
The owner messages of 2026-09-25T11:30:05+0300 and 11:41:15, and the answers after them,
are in [owner-messages.md](../owner-messages.md).

## Goal

A button `Add wine` on `/dataset` opens a form. The form creates one new row of
`wine_catalog` and its `main` image. The wine is `Active`.

## Decisions of the owner

| Question | Answer |
|---|---|
| Source of the data | A full manual form with all catalogue fields. |
| The imports and a manual wine | Protect the manual wine. |
| Marker of a manual wine | The slug prefix `__` alone. No schema file. |
| Main image | Required. Its file name becomes `csv_photo_name`. |
| The slug | The name fills it until a person types a slug (12:05:54). |
| Description | Optional (12:09:52). Schema 014 builds `wine_catalog` again with a nullable `description`. |
| Shared files | Small separate hunks on top of the uncommitted work of the other sessions. |

## The marker `__`

1. The slug of a manual wine starts with `__`. The person types the rest of the slug.
   The form shows the prefix as a fixed part.
2. No slug of `data/lab.sqlite3` starts with `_` (a query of 2026-09-25, 2,103 wines).
   So a manual slug cannot be equal to a slug of the catalogue. A wine that later
   appears on vino-svoe.ru gets its own slug with no prefix.
3. The full slug MUST match `^__[a-z0-9][a-z0-9_-]*$` and have at most 200 characters.
   The catalogue slugs use `a-z`, `0-9`, `-`, and `_` alone (a query of 2026-09-25).
4. One function tells a manual slug: `manual_wines.is_manual(slug)`. Each tool that
   needs the rule calls it.

## The form

5. The button `Add wine` stands in the bar of `/dataset`, before `Validate`. The page
   shows the button only when `/api/dataset` sends `"wine_editor": true`. The review
   tool `scripts/review_server.py` shares the page and does not send the key, so its
   page shows no button.
6. The button opens a modal dialog. The dialog uses the classes of the `Validate`
   dialog and the theme variables, so the light and the dark theme both work.
7. The fields, in the order of `wine_catalog`:

   | Field | Input | Required |
   |---|---|---|
   | Slug | text after the fixed `__` | yes |
   | Name | text | yes |
   | Producer | text with a list of the producers of the loaded records | yes |
   | Category | select of the categories of the loaded records | yes |
   | Color | text | yes |
   | Region | text with a list of the regions of the loaded records | yes |
   | Grapes | text | no |
   | Description | multi-line text | no |
   | Main image | drop zone and file picker, with a thumbnail | yes |

7a. The slug follows the name until a person types in the slug field. `slugOfName`
    writes each Cyrillic letter in its most common spelling in the slugs of
    vino-svoe.ru (for example `х` -> `h`, `ц` -> `ts`, `й` and `ы` -> `y`, `ь` and `ъ`
    -> nothing), drops the accents, and puts one `-` for each run of other characters.
    An empty slug field follows the name again. For 325 of the 2,103 catalogue wines
    the name alone gives the website slug; the website adds the producer and the type to
    most other slugs.
8. The drop zone takes one JPEG, PNG, or WebP file of at most 20 MB, as the patch.
   The zone is a portrait column at the left of the fields, because a wine image is a
   portrait image (owner message of 2026-09-25T11:55:02+0300). A screen of at most
   640 px puts the zone above the fields.
9. `Save` is off until each required field holds a value. `Cancel`, `Escape`, and a
   click outside the dialog close it. A closed dialog keeps its values until a save
   succeeds or the page reloads.
10. An error of the server stays in the dialog. The values stay.
11. After a save, the page adds the new record at the end of the catalogue order,
    renders the list, closes the dialog, clears the form, and scrolls to the new card
    when the filters show it.
12. The card of a manual wine shows the slug as plain text. It has no link to
    vino-svoe.ru, because the website has no page for it.

## The route

13. `POST /api/wine` with a JSON body:

    ```json
    {"slug": "__my-wine", "name": "…", "producer": "…", "category": "Белое",
     "color": "…", "region": "…", "grapes": "…", "description": "…",
     "image_name": "IMG_1234.jpg", "image": "<base64 of the file>"}
    ```

    JSON with base64 is used because the form has eight text fields and one file. The
    server has no multipart parser: Python 3.14 has no module `cgi`.
14. The body has at most `manual_wines.MAX_BODY` bytes: the base64 form of 20 MB plus
    64 KiB. A larger body gets HTTP 413, and the server closes the connection.
15. Each text value loses its outer white space, as in `import_catalog.py`. An empty
    `grapes` or `description` becomes NULL. An empty required value gets HTTP 400 that
    names the field.
16. A slug that does not match rule 3 gets HTTP 400. The slug `__null__` is reserved:
    it is the place of the photos that match no wine (`NULL_SLUG` of
    `scripts/match_scoring.py`), and it gets HTTP 400. A slug that `wine_catalog` holds
    already, in any state, gets HTTP 409.
16a. Each text field and `image_name` MUST be a JSON string or absent. Another JSON type,
    or a string with a lone surrogate (JSON admits `\ud800`, UTF-8 does not), gets HTTP
    400. The review of 2026-09-25 found that such a request got no answer.
17. The server does not check the category against a list. The form offers the values
    of the loaded records.
18. `csv_photo_name` is the base name of `image_name`, as `patches.source_name` makes
    it. An upload with no name gets `upload`.
19. The answer is HTTP 200 with `ok`, `slug`, and `record`: the new record in the shape
    of `/api/dataset`. A SAM3 problem adds the key `warning`.

## The store

20. The image follows the rules of `patches.py`: `patches.read_image` checks it, the
    file goes to `images/main/<sha256>.<extension>`, and a SHA-256 that `image` holds
    already reuses the stored file.
21. `derive.derive_all` processes the original before the write transaction. SAM3 does
    not answer: the wine is stored with no processed file, and the answer holds a
    warning.
22. One write transaction (`BEGIN IMMEDIATE`) writes one row of `wine_catalog`
    (`state` = `Active`, `removed_by` = NULL), the row of `image`, one row of
    `wine_image` (type `main`, `source_name` = rule 18, `match_method` = `manual`), and
    the rows of `image_derivative`. The slug check of rule 16 runs again inside the
    transaction.
23. The store path and the `INSERT INTO image` are each in one function of
    `manual_wines.py`, as in `alternatives.py`. The flat image store of plan 13 changes
    both lines.

## The imports

24. `import_catalog.py` never removes a manual wine. A manual wine is not in the list
    `removed`, and the report does not count it.
25. A CSV slug that starts with `__` stops `import_catalog.py`. The error names the
    slug.
26. The same two rules apply to `import_website.py` of plan 18. That file belongs to
    drink-atlas-workspace-ff. This session sends ff a message; ff adds the rules to
    plan 18 and to the tool.
27. `seed_images.py` does not change. A manual wine has a `main` row, so the script
    keeps the row. When no upload name fits its `csv_photo_name`, the script prints one
    `no match` line for the wine.

## Tests

`tests/test_manual_wines.py` uses a temporary database and the fake SAM3 client of
`tests/test_patches.py`:

1. A valid request stores the wine as `Active`, its `main` row, its `image` row, and
   its processed file. `/api/dataset` then sends the record.
2. The trim of the values and NULL for an empty `grapes`.
3. A slug with no prefix, a slug with a wrong character, and a slug of 201 characters
   get HTTP 400.
4. A slug that the database holds gets HTTP 409, and nothing changes.
5. An empty required field, a missing image, and an image that Pillow cannot read get
   HTTP 400, and nothing changes.
6. A body over `MAX_BODY` gets HTTP 413.
7. A SAM3 client that does not answer: the wine is stored with no processed file, and
   the answer holds a warning.
8. `/api/dataset` sends `"wine_editor": true`.

`tests/test_import_catalog.py` gets two tests: a manual wine stays `Active` when the CSV
does not hold it, and a CSV slug with `__` stops the import.

## Files

- New `pipeline/manual_wines.py`, new `tests/test_manual_wines.py`.
- Hunks in `pipeline/lab_server.py`: the module docstring, `import manual_wines`, the
  key `wine_editor` of `dataset_view`, a new `add_wine` after `change_state`, a new
  `Handler._new_wine` after `_wine_state`, one branch of `_write_route`.
- Hunks in `pipeline/pages/dataset.html`: the `.wine-form-*` CSS, the button in the bar,
  the markup of the new modal, new functions of the form after `openValidation`, the
  slug line of `recordHtml`, the listeners of the form, one line of the `keydown`
  listener, one line of `init`.
- `pipeline/import_catalog.py` and `tests/test_import_catalog.py`: rules 24 and 25.
- Entries in `README.md` (section "The Dataset page"), `SMOKE_TESTS.md` (new section
  AW), `ChangeLog.md`, and `docs/plans/07_sqlite-lab-database.md` (step 2, one rule).
- A restart of the lab server on 8168.
- `pipeline/schema/014_description_optional.sql`, the `migrate` function of
  `pipeline/labdb.py` (the foreign keys off during a file, `PRAGMA foreign_key_check`
  before the COMMIT), and `tests/test_labdb.py` (the version 14, 3 new tests).

## Open points

1. A manual wine has no GTIN, no Atlas binding, and no comment at the start. The card
   editors add them as for any wine.
2. The Embeddings page and the benchmark see a manual wine as any other `Active` wine.
