# Svoe Vino Workbench

Test data for the Svoe Vino wine scanner.

- `eval/` is the official evaluation set from the organizers. It holds 3 photos.
- `my/` is a larger set built by this project. It holds real-world photos found on the web.
- `scripts/` holds the five pipeline stages and the driver.
- `work/` holds the state database, the downloaded candidates, and the logs. It is disposable.
- `config.yaml` holds the paths that point out of this project.
- `backends.yaml` defines the match backends.
- `runs/` holds one directory per match run. It is the history of the measurements.
- `excluded-slugs.json` names the slugs that are out of the benchmark.
- `manual-groups.json` names the variant pairs that a reviewer made by hand.
- `pipeline/` holds the lab database tools. `data/` holds the lab data (plan 75):
  - `data/catalog/` is the catalogue: the lab database `catalog.sqlite3`, the images
    of the wines in `images/main/`, `images/patched/`, and `images/additional/`, the
    processed files in `cuts/`, and the embeddings in `embeddings/<name>/`.
    `scripts/copy_catalog.py` makes a consistent copy of it for the matcher (plan 75,
    stage 2).
  - `data/testsets/images/` holds the photos of the test sets.
  - `data/cache/models/` holds the model call cache.
  - `data/backups/` holds the copies of the database.
  Git ignores `data/`, except `data/catalog/images/main/`,
  `data/catalog/images/patched/`, and `data/catalog/images/additional/`.
- `db-export/` holds the text export of `data/catalog/catalog.sqlite3`, one JSON-lines
  file for each table. It keeps the history of the database in git. The skill
  `backup-lab-db` writes and commits it, together with `data/catalog/images/main/`,
  `patched/`, and `additional/`. Read [plan 50](docs/plans/50_lab-db-text-export.md).

## The lab database

One SQLite database holds the lab state of one catalogue delivery. The database is filled
one step at a time. Read [plan 07](docs/plans/07_sqlite-lab-database.md) for the steps,
the tables, and the rules. Read [decision record 01](docs/decisions/01_sqlite-lab-database.md)
for the reasons.

```bash
# step 1: create the database and its tables
python3 pipeline/labdb.py data/catalog/catalog.sqlite3

# step 2: import the Strapi CSV into wine_catalog; the first import adds every wine
python3 pipeline/import_catalog.py --db data/catalog/catalog.sqlite3 \
    ../../svoe-wino-hackaton/dataset/official-2026-09-17/strapi_output0709.csv
```

The database MUST be on a local disk. The import never writes to the delivery directory.
A later import adds the new wines and marks the missing wines `Removed`. A wine that
the import removed is `Active` again when it comes back. A wine that a person removed
stays `Removed`. A changed field of a wine stops the import with an error. A wine that
a person added (slug prefix `__`) is never removed, and a CSV slug with this prefix
stops the import.
`tests/data/` holds fake variants of the CSV to test this.

```bash
# step 3: the lab server, the Dataset page on the database
python3 pipeline/lab_server.py            # http://127.0.0.1:8168/dataset
```

`config.yaml` holds two keys: `rootdir` and `database_file`. A relative
`database_file` is resolved against `rootdir`, so the value is
`svoe-vino-lab/workbench/data/catalog/catalog.sqlite3`. The lab server opens the database
read-only. The Dataset, Embeddings, Clusters, Testset (`/testset`), and Runs pages work.
`/` redirects to `/dataset`. The navigation order is `Dataset`, `Embeddings`, `Clusters`,
`Testset`, `Runs`. Each card of the Dataset page holds
the buttons `Disable` / `Enable`, `Remove`, and `Restore` below the catalogue image. The
`main` image of a `Disabled` wine is gray on the card. The browser draws it with a CSS
filter; the file does not change. The patch and the alternative photos keep their
colours. The filter `State` shows `All (except Removed)`, `Disabled`, `Removed`, or `Favorites`
(each favorite wine, also a removed one; the lab server alone). The lab server writes
these data alone: the state of a wine; its GTINs and QR URLs (`wine_code`, plan 11); its
manual Atlas Core binding (`wine_atlas_binding`, plan 15); its comments (`wine_comment`,
plan 17); the favorite mark (`wine_favorite`, plan 19); the wine type
(`wine_beverage_type`, plan 52); a wine added by hand, with a slug
that starts with `__` (plan 20); its patch (the `main_patched` row, plan 14) and its
alternative photos (the types `full_front`, `label_front`, `full_back`, `label_back`,
plan 16), each with its files and their rows of `image` and `image_derivative`; and the
data of the website import of plan 21. The card images come from the table
`wine_image`: the `main` image at the left and the patch in the patch slot next to it,
side by side. Each slot shows the processed file with its badge `crop` or `seg`. A
`crop` whose box is the whole image cut nothing: the slot shows the original and no
badge. The server sends the image files (`labdb.image_dir`, plan 75) at
`/images/<folder>/<sha256>.<extension>`. `Sort` can order the cards by the pixel count
of the image. The slug of a card links to the page of the wine on vino-svoe.ru. The lab
server uses port 8168.
The review tool of `svoe-vino-testset` keeps port 8154, so both can run.

```bash
# step 4: find the main image of each wine in the Strapi uploads folder, offline
python3 pipeline/seed_images.py --db data/catalog/catalog.sqlite3 \
    ../../svoe-wino-hackaton/dataset/official-2026-09-17/prod-svoe-vino-strapi/prod-svoe-vino/strapi/uploads
```

The table `wine_image` holds the images of a wine and the type of each image: `main`,
`main_patched`, `full_front`, `label_front`, `full_back`, and `label_back` (the names of
schema 012). A reader such as the Embeddings page uses a `main_patched` image in place of
the `main` image of the same wine; the card of the Dataset page shows the two side by
side. `image_derivative` holds one processed file for each original and kind of cut
(`package` or `label`, schema 017). The files are in `data/catalog/images/`:
`main/`, `patched/`, and `additional/`, each file as `<sha256>.<extension>`. The
processed files (folder `cropped`) are in `data/catalog/cuts/`. The photos of the test
sets (folder `testset`, schema 016, see "later: the test sets" below) are in
`data/testsets/images/`.
`seed_images.py` fills `main`. It matches `csv_photo_name` with the upload file names
by the rule of `build_catalog.py`, and it reads no internet resource. A wine with no
match gets a console message. Read [plan 08](docs/plans/08_seed-images.md).

The table `image` holds one row for each stored file. Each import also processes each
image it stores, with `pipeline/derive.py`: an image with a transparent background loses
its border (`crop`), and SAM3 on gx10 segments the bottle of an image with no
transparent background (`seg`). The processed file is a PNG in `data/catalog/cuts/`.
The table `image_derivative` links it to its original by the sha256. The Dataset page
shows the processed image with the badge `crop` or `seg`. When SAM3 does not answer,
the image stays unprocessed, and the next import asks again. The key `sam3.endpoint`
of `config.yaml` names the SAM3 service of each SAM3 call of `pipeline/`; without the
key, the service of gx10 stays. The option `--sam3 <URL>` names another SAM3 service
for one import. Read [plan 09](docs/plans/09_image-processing.md).

```bash
# step 5: store the patched main images; the file name is the wine slug
python3 pipeline/seed_patched.py --db data/catalog/catalog.sqlite3 \
    ../../svoe-wino-hackaton/dataset/patched-official-2026-09-17
```

`seed_patched.py` fills `main_patched` from the patch folder. The database is the truth
for the patches, and the folder is one source of them: a new file adds or replaces the
row of its wine. A row whose wine has no file in the folder stays, because the patch
editor of the Dataset page also writes rows. It processes each patch as
`seed_images.py` does. Read step 5 of [plan 07](docs/plans/07_sqlite-lab-database.md)
and [plan 14](docs/plans/14_patch-editor.md).

The patch editor of the Dataset page on the lab server stands next to the card image.
Drop a JPEG, PNG, or WebP file of at most 20 MiB on it, or press it to choose a file.
The page sends the file at once; there is no `Apply` step. The editor shows
`Processing…` while the server stores the file in `data/catalog/images/patched/`, writes the
`main_patched` row, and creates its package cut and label cut. SAM3 can take up to about
two minutes. When SAM3 does not answer, the patch stays stored. The page shows a warning
for each missing cut. A patch applied by mistake is removed with the red `Clear` button.
The page clears the patch at once; there is no `Apply` step. The editor
shows `Clearing…` while the server works. This deletes the row; the file stays in the
store. The patch `Clear` button has the size of the `Remove` button of the main image
and stands at the right.
The editor does not write the patch folder.

```bash
# step 6: the GTINs and the QR URLs of the code map of the matcher
python3 pipeline/seed_codes.py --db data/catalog/catalog.sqlite3 \
    ../../svoe-vino-matcher/dataset/code-map.json
```

The table `wine_code` holds the codes of a wine: `gtin` and `qr_url`. One
wine MAY have more than one value of each kind, and one value MAY belong to more than
one wine. A GTIN is a GS1 number of 8, 12, 13, or 14 digits with a valid check digit.
The table stores it in its GTIN-14 form, with leading zeros: the printed
`4631168664979` is `04631168664979`. The lab keeps GTINs alone: it has no kind
`barcode` (owner choice of 2026-09-25). Each `barcode` value of the code map MUST be a
GTIN. A QR URL gets the normal form of the matcher: no `URL:` prefix, a lower-case host, and no
fragment. `pipeline/codes.py` holds the checks. `seed_codes.py` adds rows alone, and a
wrong check digit stops it with no write; the error names the record, the field, and the
value. It refuses a table `wine_code` that already holds rows, because a second run adds
back the values that a person removed on the page; `--force` adds the missing rows anyway. The Dataset page of the lab has the editors
`GTINs` and `QR URLs`. They write the table through `POST` and `DELETE` of
`/api/dataset-gtin` and `/api/dataset-qr-url`. A save redraws its own card, and the cards
of the other wines of the same code. A GTIN or a QR URL of 2 or more Active wines shows the
badge `N wines` at its right; the tooltip names the other wines
([plan 58](docs/plans/58_shared-codes.md)). The
page checks the check digit while you type, and the server checks it again. The GTIN
input accepts at most 14 characters (owner message of 2026-09-25T22:47:19+0300). The editor
`Barcodes` shows only on the review tool, which sends `barcode_file`. `svoe-vino-matcher`
still reads `code-map.json`; it does not see the codes of the table. Read
[plan 11](docs/plans/11_wine-codes.md).
The column `modified_at` of `wine_code` holds the UTC insert time of each row, in the form
`2026-09-27T05:46:17Z` (schema 026, owner message of 2026-09-27T08:30:51+0300). A trigger
sets it. The writers of the table do not change. A row is never updated, so the insert time
is the time of the last change. A row that is older than schema 026 has NULL. `GET /api/dataset` sends the
times of each wine in `_code_times`: `{"gtin": {value: time}, "qr_url": {value: time}}`.
A code route also sends `modified_at`: `{value: time}` for the values of its kind. On the
Dataset page, the tooltip of a GTIN or of a QR URL reads `added YYYY-MM-DD HH:MM` in local
time, or `added: unknown` for NULL.

```bash
# step 7: the Atlas Core product of each wine, from the files of svoe-wino-hackaton
D=../../svoe-wino-hackaton/dataset/derived/official-2026-09-17
python3 pipeline/seed_atlas_bindings.py --db data/catalog/catalog.sqlite3 \
    --matches $D/atlas-matches.jsonl --manual $D/atlas-bindings.manual.jsonl
```

The table `wine_atlas_binding` (schema 009) links a wine to a Drink Atlas Core product
UUID. A wine has at most one `automatic` row, from `match_atlas.py`, and one `manual`
row, from a person. The manual row wins. One product MAY belong to more than one wine.
The seed adds rows alone. A file row whose UUID differs from the stored row prints
`differs: <slug> <source>` and is not applied. Like `seed_codes.py`, the seed refuses a
table that already holds rows unless `--force` is given. On 2026-09-25 the seed added 364
automatic rows and 3 manual rows. The editor `Atlas Core product` of the Dataset page
sets a manual binding with `POST /api/dataset-atlas-binding`. The red `×` removes the
shown binding, manual or automatic, with `DELETE`. After the remove of a manual row, the
wine shows its automatic binding, or `not bound`. The remove of an automatic row deletes
a wrong match of `match_atlas.py`; the seed does not add it back without `--force`. The lab does not write the JSONL files, so the review tool does not see a lab
binding. Read [plan 15](docs/plans/15_atlas-binding.md).

Schema 025 (plan 54, 2026-09-26) replaces the one-row rules of the paragraph above. A
wine MAY have 2 or more Atlas Core products. The key of `wine_atlas_binding` is
`(wine_slug, product_uuid)`. Each row keeps its source, `automatic` or `manual`, as a
label. The rule "the manual row wins" goes away. The migration kept the effective row of
each wine and dropped the one automatic row that a manual row hid. The editor lists each
UUID with its source, a red `×`, `copy`, and `open`. A UUID of 2 or more Active wines
shows the badge `N wines` after `open`, as a shared GTIN of plan 58; the tooltip names
the other wines (owner message of 2026-09-27T20:08:45+0300). The `+` button adds one manual UUID
with `POST /api/dataset-atlas-binding`. A UUID that the wine already has answers HTTP
409. `DELETE /api/dataset-atlas-binding?slug=…&product_uuid=…` removes one UUID of either
source. `GET /api/dataset` sends `_atlas_products`, a list of `{product_uuid, source}`,
and the header counts the rows. The seed accepts 2 or more UUIDs of one slug in one file.
It no longer prints `differs`. The old review tool keeps one UUID per slug. Read
[plan 54](docs/plans/54_atlas-binding-list.md).

An automatic UUID has a green `approve` button after its source label (owner message of
2026-09-27T14:49:04+0300). The button tells that a person confirmed the match of
`match_atlas.py`. It sends `POST /api/dataset-atlas-binding-approve`, which changes the
source of the row from `automatic` to `manual`. The row keeps its rowid, so the UUID keeps
its place in the list. The row count does not change; the manual count grows by 1. A
manual UUID has no `approve` button. The button needs no confirm, because it removes
nothing. No route changes a manual row back to automatic.

The table `wine_comment` (schema 011) holds the timestamped comments of a wine. One wine
MAY have more than one comment. Each row has the UTC time of the write (`created_at`),
a source, and the text with its line breaks, at most 4,000 characters. The source is
`user` for a person on the Dataset page and `script` for a script. The editor
`Comments` of the Dataset page lists the comments of a wine in time order, the oldest
first, with the local time and the source. The `+` button opens a multi-line field:
Enter adds a line break, Cmd+Enter or Ctrl+Enter saves, and Esc cancels. The red `×`
removes one comment after a confirmation. A comment has no edit. The editor writes
through `POST` and `DELETE` of `/api/dataset-comment`. A script calls
`comments.add(conn, slug, text, "script")` in its own transaction, or sends
`"source": "script"` in the body of the POST. The value `with comments` of the filter
`Show` shows the wines with at least one comment. The text search finds the text of a
comment. Read [plan 17](docs/plans/17_wine-comments.md).

The table `wine_favorite` (schema 013) holds the favorite wines. A wine is a favorite
while it has a row. The star at the top right of the text column of each card of the
Dataset page, next to the alternative photos, toggles the mark with one click and saves
it at once: `☆` is not a favorite, and an amber `★` is
a favorite. The page writes through `POST /api/dataset-favorite` with
`{"slug": …, "favorite": true|false}`. The value `Favorites` of the filter `State` shows
each favorite wine in each state, also a `Removed` one. The header counts the favorites.
Read [plan 19](docs/plans/19_favorites.md).

The table `wine_similar` (schema 028) holds the manual pairs of two hard cases (owner
message of 2026-09-27T15:12:00+0300). The pair has no direction: one row holds the two
slugs in sorted order, and the pair shows on the card of each wine. The editor
`Hard cases` of each card, after `Atlas Core product`, lists the partners with their
names. A click on a partner goes to its card. When the filters hide that card, it goes in
just below the card of the click; the next full render of the list takes it out again
(owner message of 2026-09-27T20:22:30+0300).
The `+` button opens an input with a list of the slugs and the names of the page; Enter
or the save button adds the pair, and Esc cancels. The red `×` removes the pair after a
confirmation. The page writes through `POST` and `DELETE` of `/api/dataset-similar`. The
cluster build of `/clusters` uses each pair as one more link of the views `full`,
`label`, and `combined`, with the signal `manual`: the other wine joins the cluster of the
first wine, two clusters become one, and a pair of two wines with no other link makes a
cluster of the kind `manual`. A pair counts only when both wines are Active and have an
image. A change of a pair makes the stored clusters stale; build them again on
`/clusters`. Read [plan 62](docs/plans/62_similar-wines.md).
A hard case is a wine that is hard to distinguish from the other wine of the pair (owner
message of 2026-09-27T23:11:41+0300). The page says `Hard cases`; the table, the route,
and the keys keep the name `similar`.

The table `wine_tag` (schema 029) holds the free-form text tags of a wine (owner messages
of 2026-09-27T17:04:20+0300 and 17:05:11). One wine MAY have more than one tag. The first
use is to mark the variants of one wine with more than one slug, for example `generic` on
`shato-pino-shiraz-krasnoe-suhoe-135` and `vintage:2017` on
`shato-pino-shiraz-krasnoe-suhoe-14`. The editor `Tags` of each card, after `Hard cases`,
lists the tags. The `+` button opens an input that suggests the tags of the page; Enter or
the save button adds the tag, and Esc cancels. The red `×` removes a tag after a
confirmation. A tag is stored in lower case, with 1 to 64 letters, digits, `_`, `-`, `:`,
or `.`, and no white space. The page writes through `POST` and `DELETE` of
`/api/dataset-tag`. The pipeline does not read the tags yet. Read
[plan 63](docs/plans/63_wine-tags.md).

The table `wine_beverage_type` (schema 023) holds the wine type of a wine. The column
`beverage_type_code` has the name of the column of Drink Atlas Core: `4` is a wine, `44`
is a sparkling wine. The two values are prefixes of the EGAIS product type codes, not
dictionary codes. A wine with no row has no type, and that is the default. The select
`Type` at the end of the category line of each card of the Dataset page sets the type at
once: `not set`, `Wine`, or `Sparkling wine`. The page writes through
`POST /api/dataset-beverage-type` with `{"slug": …, "beverage_type_code": "4"|"44"|null}`.
The filter `Type` in the row of `Advanced Filters:` shows `All`, `Wines`,
`Sparkling Wines`, or `Not set`. A change of the type does not change the lab change time
of the wine. Read [plan 52](docs/plans/52_wine-beverage-type.md).

The button `Add wine` of the Dataset page adds a wine by hand. The
dialog asks the slug, the name, the producer, the category, the color, the region, the
grapes (optional), the description (optional), and the main image (JPEG, PNG, or WebP,
at most 20 MB). The slug follows the name (`Южный Лес` -> `yuzhnyy-les`) until you type
a slug; an empty slug field follows the name again. The image zone is a portrait column at the left of the fields. The slug gets
the fixed prefix `__`; the rest holds `a-z`, `0-9`, `-`, and `_`,
and starts with a letter or a digit. No slug of vino-svoe.ru starts with `_`, so a
manual slug cannot collide with a website wine. The category is a select of the values
of the loaded records; the producer and the region suggest the values of the loaded
records. `Save` stays off until each required field and the image are there. The page
sends `POST /api/wine` with JSON and the image in base64. The server stores the wine as
`Active`, the image as `main` (`match_method` = `manual`, its file name as
`csv_photo_name`), and processes the image as a patch. A slug that the database holds
already gets HTTP 409, and the dialog shows the error. The card of a manual wine shows
the slug with no link to vino-svoe.ru. `import_catalog.py` and `import_website.py` never
remove a manual wine. The review tool shows no button. Read
[plan 20](docs/plans/20_add-wine.md).

```bash
# later: compare wine_catalog with the live catalogue of vino-svoe.ru
python3 pipeline/import_website.py --db data/catalog/catalog.sqlite3
```

`import_website.py` reads the JSON API `https://api.vino-svoe.ru/v1`: the list pages,
the card of each new wine, and the original image of each wine through
`/v1/file-proxy/`. A website wine that the database does not hold is added as `Active`
with its image as `main`. An `Active` or `Disabled` wine that the website does not hold
becomes `Removed`. A `Removed` wine on the website becomes `Active`, also when a person
removed it. A website wine with no `main` row gets the website image. Each change gets a
comment of the source `script`: `New on vino-svoe.ru.`, `Missing on vino-svoe.ru.`,
`Back on vino-svoe.ru.`, or `Main image from vino-svoe.ru.` A new wine gets the first
word of the website category (`Белое сухое` -> `Белое`), and its `csv_photo_name` is
the upload file name. The tool compares `name`, `producer`, `category`, `color`, and
`region` of each known wine, and the SHA-256 of its original image with the `main` row.
A difference stops the import. The error lists all problems, and nothing changes. The
same bytes under a new upload name are no change. The tool does not detect a renamed
slug: the old slug becomes `Removed`, and the new slug is a new wine. A manual wine
(slug prefix `__`, plan 20) is never removed, and a website slug with this prefix stops
the import. Read [plan 18](docs/plans/18_import-website.md).

The button `Import from website` of the Dataset page runs the same compare as a job of the
lab server: `import_website.py --prepare work/website-import/<run>/`. The button shows the
progress. After the compare, a dialog lists each conflict with the choice `database` or
`website`, and each plain change (new, missing, back, main image) with a checkbox. `Apply`
runs `import_website.py --apply` on the same run directory. A conflict with no choice does
not block `Apply`: the apply skips it, writes nothing for it, and the next compare shows it
again. The section `Possible renames` pairs a slug that left the website with a slug that
appeared on it: the same main image, a slug distance of at most 3 edits or 20 %, or the same
name and producer. It is display only. A choice `website` writes the website value, or replaces the `main` image; the
old file stays in the store. A choice `database` and a cleared checkbox are refusals in
the table `website_refusal` (schema 015). A later run, also of the CLI, skips a refusal
while the website keeps the refused value. Each choice writes a short comment of the
source `script`. The compare reuses one HTTPS connection; a full run takes about 10
minutes. Each write also sets `wine_catalog.website_modified_at`, the `lastmod` of
`wines-sitemap.xml`. `wine_catalog.modified_at` is the time of the last change of a field
or of the state of the row; two triggers of schema 015 set it. The sort of the Dataset page
offers `changed in the lab, newest first` and `changed on vino-svoe.ru, newest first`. Read
[plan 21](docs/plans/21_website-import-ui.md).

While the dialog is open, the path of the page is `/dataset/website-import`. A link to
`http://127.0.0.1:8168/dataset/website-import` opens the dialog with the newest run. A
close and Back give `/dataset`.

```bash
# later: the test sets my, official-real-photos, and vlmrerank-8b-failed
python3 pipeline/import_testsets.py --db data/catalog/catalog.sqlite3
```

`import_testsets.py` imports the three test sets of `../../svoe-vino-testset/dataset/` into
the tables `test_set`, `test_photo`, `test_photo_comment`, and `test_variant`. The set
name is the name of the directory. The import keeps each field of a label entry of
`review-labels.json` and the text `note` (schema 019, plan 24). The comments of a photo
(the list `comments`, or the old field `comment`) go into `test_photo_comment`. The old
map `wines` and the old `excluded-slugs.json` become rows of `wine_comment`; a second
import adds no text again (schema 022, plan 51). Since plan 24 the database is the source of the labels: the
Testset page writes to the rows. So the import refuses a set that holds a page edit;
`--force` replaces the page edits with the files. A photo is stored as
`data/testsets/images/<sha256>.<extension>`, one time for the same bytes. A photo whose
bytes the lab holds already, for example as a patch, keeps that file. `--source` names
another directory of the sets. `import_testset.py --set <name> <dir>` imports one set.
Read [plan 12](docs/plans/12_testsets-benchmark.md).

```bash
# seed or restore: build the whole lab database again from its sources
python3 pipeline/seed_from_testset.py --db data/catalog/catalog.sqlite3
```

`seed_from_testset.py` runs the steps of this section in one command: the tables, the
catalogue, the main images, the patches, the GTINs and QR URLs, the Atlas Core bindings,
the three test sets, and the label cuts (SAM3 on gx10 through `data/cache/models/sam3/`). It
builds the new database at `<db>.seeding`, next to `--db`, with the same image store. A
failed step stops the script, and `--db` does not change; the next run deletes the
partial file. After the last step, the old database goes to
`data/backups/lab-<UTC time>.sqlite3`, and the new one is copied into `--db` with the
SQLite backup API. The lab server needs no restart. The new database holds the data of
the sources alone: a wine state, a comment, a favorite, a manual wine, an alternative
photo, an edit of the Testset page, and an image description are in the backup only. It
copies no configuration, no run, and no cluster. Read
[plan 28](docs/plans/28_seed-from-testset.md).
Git ignores the whole `data/` directory, except `data/catalog/images/main/`,
`data/catalog/images/patched/`, and `data/catalog/images/additional/` (plan 50).

## The Testset page of the lab

The Testset page of the lab server (`/testset`) shows one test set of the database and
writes the labels of its photos. Each click writes to `data/catalog/catalog.sqlite3` at once. The page
is a port of the Testset page of the review tool, with a smaller scope. Read
[plan 24](docs/plans/24_testset-page.md).

- The combobox in the title (`Test set [my (4043 photos) ▾]`) chooses the set: `my`,
  `official-real-photos`, `vlmrerank-8b-failed`, or a set that the button `New testset…`
  of `/runs` made (plan 44). The address keeps the set, the
  controls, and the open photo: `/testset?set=<set>#<slug>/<file name>`. The line after
  the combobox counts the wines and each photo of the set, the Drawer too. The stats
  line ends with the time of the last edit of the set.
- The last option of the combobox, `Add new testset …`, opens a small dialog (plan 57).
  It makes a new empty set with the typed name (`POST /api/testset-new`). A name holds
  0-9, a-z, `_`, and `-` alone, and MUST be free; `Create` is enabled only for such a
  name. Enter creates the set, Escape or a click outside closes the dialog. After
  `Create`, the page shows the new set; it is the last set of the combobox. The row of
  `test_set` has `source_dir` `the page /testset` and an `edited_at`, so
  `import_testset.py` does not overwrite it without `--force`. No route deletes a set.
- One row for each `Active` and `Disabled` wine, and one row for each place that holds a
  photo of the set, also when its wine is `Removed` or is not in `wine_catalog`. The first
  row is `No Match` (the place `__null__`), and no filter, sort, or search takes it away.
  The Drawer (the place `__drawer__`) is the right sidebar, not a row. A `Removed` wine keeps its photos and its labels and gets
  the badge `Removed`, so a restore finds it again; the benchmark leaves its photos out
  ("removed wine") until the restore.
- The buttons `V`, `N`, `x`, and `D` set `positive`, `negative`, `unusable`, and
  `variant`; the same button again clears the label. A photo of `__null__` takes
  `positive` or `unusable` alone. The right-click menu marks a photo for deletion; the
  mark moves no file.
- A wine row shows the comments of the wine as the Dataset page does (`wine_comment`,
  the route `/api/dataset-comment`): the list with the time, the source, and `×`, and
  `+` for a new comment (Cmd+Enter or Ctrl+Enter saves, Esc cancels). A wine comment
  belongs to no set, so it is not an edit of the set. The row `No Match`, the Drawer,
  and a place that `wine_catalog` does not hold have no wine comments. The old field of
  the wine note and the button `Exclude` went away (owner answers of
  2026-09-26T18:08:34+0300, [plan 51](docs/plans/51_testset-comments.md)): the old notes
  and the reasons of the old exclusions are wine comments now, and the benchmark
  excludes no slug.
- Two special places (plan 36, owner answer of 2026-09-26T00:29:00+0300):
  - The row `No Match` holds the photos that must give no match. A run uses each of them
    as a `no_match` query, also with no label; `×` (unusable) or the delete mark takes a
    photo out of the run. Its cards have `V` (confirmed: no card of the catalogue shows
    this wine) and `×`.
  - The Drawer, the right sidebar, holds the photos that wait for a wine, also after a
    restart. No run uses them. Its cards have no label buttons; the comments, the box, and
    the delete mark stay.
- A drag of a photo card onto the sidebar moves the photo to the Drawer; a drag onto the
  row `No Match` or onto a wine row moves it there; the key `0` of the large view moves
  it to the Drawer; the right-click menu holds `Move to the Drawer`, `Move to No Match`,
  and, on a card of a special place, `Move to a wine…` (`POST /api/testset-move`). A move
  clears the label and keeps the comments, the box, the delete mark, and the proposal;
  `moved_from` gets the old place; a file name that the target holds gets `_moved<N>`.
  No file moves.
- The large view shows the catalogue image and the photo side by side, with the panel
  `Comments on this photo` (plan 51). A photo MAY have more than one comment
  (`test_photo_comment`). The panel lists them, the oldest first, with the time, the
  source, and `×` (remove, after a confirm). `Add`, Cmd+Enter, or Ctrl+Enter adds the
  text of the field as a new comment (`POST /api/testset-photo-comment`); a text that is
  not added yet is added at a step to another photo, at the close of the view, at a
  change of the set, at a move of the photo, and at a reload. The badge of a card lists
  the comments. The keys: `Left` and `Right` the photos of the wine, `Up` and `Down` the
  wines, `1` to `4` the labels, `b` the box, `Esc` close.
- The box of the main object is optional, for a scene with several items. `b` or `Box`,
  then a drag on the photo, draws it; `Clear box` removes it. The box is in the pixels of
  the photo after its EXIF orientation. A card with a box gets the badge `box`. The IoU
  of the box against the box of the matcher comes with plan 27.
- The tags of an image (plan 66, schema 030 `image_tag`). A tag belongs to the image
  bytes (`sha256`), so each copy of the image, in each wine row and in each set, shows it.
  The large view has the section `Tags of this image`: the tags as chips with `×`, and an
  input that suggests each tag of the database; Enter or `Add` adds a tag
  (`POST /api/testset-photo-tag`, `POST /api/testset-photo-tag-remove`). A tag has the
  form of a wine tag of plan 63. A card with a tag gets a badge at the lower right of the
  image; its title lists the tags. The row counts get `N tagged`, `Marks` gets
  `a tag`, and `Additional settings` gets the select `Tag` (the address keeps it as
  `tag=`). The export writes the field `tags`; the import adds it back and never removes
  a tag. The pipeline does not read the tags.
- Three filter axes take the place of the single select `Show` of the old page (owner
  answers of 2026-09-26 00:26:58). `Progress`: `all`, `not fully labelled`, `no label
  yet`, `partly labelled`, `fully labelled`, `no candidate photos`. `Verdict` (a photo of
  the wine holds this label): `positive`, `no positive`, `negative`, `unusable`,
  `different design`. `Marks` (a photo of the wine holds this mark): `a comment`, `an
  agent proposal`, `a deletion mark`, `a box`. A wine passes when it passes every axis.
  A wine with no photo in the set shows only when `Verdict` and `Marks` stand on `any`.
  An old address with `?filter=<value>` still opens: the value goes to its axis, and
  the address changes to the key of that axis (`verdict` or `marks`).
- `Clusters` ([plan 37](docs/plans/37_testset-cluster-grouping.md)) groups the table
  by the clusters of one embedding: `No`, or each embedding with a `clusters.json`, as
  `<embedding> (<N> clusters)` (`, stale` when the inputs changed after the build). The
  page uses the view `combined`. The table then lists only the wines in a cluster that
  pass the other filters; a cluster can show in part. A cluster stands at the place of
  its first row in the sort order. A header row stands above it: `<id> · <shown> of
  <size> wines shown · <signals>` and `open on /clusters` (a new tab, the cluster
  marked). The row `No Match` stays first. The address key is `cluster`. `Clusters`
  took the place of the select `Wine` and its values `in a variant group` and `removed
  from the catalogue`; the tag `variant group of N`, the sort `variant group first`, and
  the badge `Removed` stay. The page has no
  filter of the benchmark scope (owner message of 2026-09-26T00:39:13+0300): the select
  `Slugs` and the old values `excluded` and `included` are gone, and an old address
  with them opens the full list. The 13 sort orders of
  the old page, and `cluster size, largest first` (owner answer of 2026-09-26
  01:08:49): with an embedding in `Clusters`, the largest cluster stands first (a tie
  goes by the cluster id), and inside a cluster the rows go by slug. With `Clusters` on
  `No`, the option is disabled, and a stored or linked `sort=cluster_size` gives
  `slug A-Z`. `Marks` and `Clusters` stand in a second row that the button
  `Additional settings` shows or hides; the button shows `· N` when N of the two are not
  at their default, and localStorage (`svl.testset.more`) keeps the open state.
  `Find` matches each word in
  the slug, the name, the producer, the region, or the grapes, in any order, with the case
  and the accents folded.
- A drop of image files from the Finder onto the sidebar (the Drawer) or onto a row
  stores each file in that place with no label (`POST /api/testset-upload`). A new
  image keeps its file name; a clash with another image of the place gets `_upload<N>`.
  An image that the set holds already keeps the file name of the set. The same place
  refuses it (HTTP 409); another place takes it, for example for `negative`. The page
  takes JPEG, PNG, WebP, GIF, and BMP of at most 20 MB. HEIC is refused: Pillow here
  cannot read it.
- Not on this page yet: the copy of a photo, the upload by a file button and by URL, the
  checks (`validate`), the group editor, and the CSV export.
- The button `Run>` after the selector of the set opens a dialog. The dialog lists every
  pipeline of `config.yaml` (the key `pipeline`, plan 34) and the count of the queries of
  the set. It does not list the entries of `embeddings`. A pipeline with an error is
  disabled with the note `configuration error`. A pipeline of the backend `embedding`
  whose `embeddings` entry has no index is disabled with the note `no index: build it on
  /embedding`; its job runs with `embedding_python`.
  `first N queries` (empty: all) and `workers` (empty: the value of the entry) are
  optional. The checkbox `Use caches` is on at each page load: a model call that repeats
  an earlier call reads its answer from `data/cache/models/` (SAM3, GDINO, VLM, LLM). Barcode
  scans also use this setting. Off, the
  job reads no record, each model call goes to its service, and the latency is real
  time; the fresh answers are still stored (`run_job.py --no-cache`; owner answers of
  2026-09-26T01:32:00+0300, [plan 39](docs/plans/39_use-caches-checkbox.md)). `run.json`
  records the state in `use_cache`. The embedding request and the request to the API of
  vino-svoe.ru have no cache, so they are real time in both modes.
  The checkbox `Disable barcode fast path` is off at each page load. It is enabled for a
  pipeline with the key `barcode` alone; for another pipeline it is greyed. On, the run
  skips the barcode step: no decode and no lookup in `wine_code`, and the embedding
  answers each photo, as in the twin pipeline with no key `barcode`
  (`run_job.py --no-barcode`; owner answers of 2026-09-26T19:47:40+0300,
  [plan 53](docs/plans/53_disable-barcode-checkbox.md)). `run.json` records the state in
  `use_barcode`.
  `Start` runs `pipeline/run_job.py` as a separate process, and the run goes
  to `runs/` as a CLI run. With `rebuild_embeddings_on_run: true`, the job first updates
  the index of the embedding, and the job row shows `starting` until the build ends
  ([plan 59](docs/plans/59_rebuild-embeddings-on-run.md)). A job row under the header shows the pipeline and the
  set, the state, a bar, done / total, the errors, and the elapsed time; the icon button
  `×` at the start of the row stops the run and keeps the files of the answered photos.
  The row stays 60 s after the end, with the link `open run`. One pipeline runs one job at a time. The job files are in
  `work/run-jobs/<configuration>/` (`job.log`, `job.lock`), so a reload of the page or a
  restart of the server finds a running job again. Read
  [plan 32](docs/plans/32_testset-run-button.md).

```bash
# write the JSON files of one set from the database (the database is the source)
python3 pipeline/export_testset.py --db data/catalog/catalog.sqlite3 --set my --out <directory>
```

The export writes `review-labels.json` into `--out`, in the form of the review tool. The
import of a set, then its export, gave the same `labels`, `wines`, excluded slugs, and
`note` as the source files: checked on the three sets on 2026-09-25. Since plan 51 each
entry holds its comments as the list `comments` (`{created_at, source, text}`, the
oldest first), and the export writes no `wines` and no `excluded-slugs.json`: the notes
of a wine are wine comments, and the exclusion went away. An old `excluded-slugs.json`
in `--out` stays as it is; the scripts of `scripts/` still read it.

## The embeddings of the lab

The key `embeddings` of `config.yaml` holds one entry for each embedding: a name, an
endpoint, options, and the steps of each view. The entries are the image embedding
models of gx10 and one local model. Read [plan 10](docs/plans/10_embeddings-page.md).

```bash
# create the venv of the build once; the local backend needs torch
python3 -m venv ~/.venvs/svoe-vino-lab
~/.venvs/svoe-vino-lab/bin/pip install -r requirements-local.txt

# build one entry; a second run continues a stopped build
~/.venvs/svoe-vino-lab/bin/python pipeline/build_embeddings.py \
    --name gx10-siglip2-so400m-patch16-naflex-p256
```

- A build writes `data/catalog/embeddings/<name>/`: `index.json` with the settings and the
  items, `vectors-<8 hex>.npy` with one float32 row for each item, and
  `images/<source_sha256>_<view>.png`. The PNG is the exact model input. The database
  does not change.
- The inputs are the images of the Active wines. `main_patched` replaces `main`. A file
  that several wines share is one item.
- The view `full` is variant C: the package cut of plan 09 (`segment`,
  `remove_background`), on white (`white_background`), and `resize`. The view `label`
  is variant F: the same with the label cut. The label cut of a full original is the
  row of the kind `label` of `image_derivative` (plan 22). A patch, a full alternative
  photo, a manual wine, and a new main image of the website import get it when they are
  stored. `python3 pipeline/seed_label_cuts.py --db data/catalog/catalog.sqlite3` makes each missing
  one with SAM3 and the label rule of plan 16. If SAM3 finds no label and identifies a printed `packet` or
  `box`, schema 021 records that the label cut is not applicable. The label item is
  omitted, and the full-package vector stays. A bottle or can with no label cut fails
  with `no label cut yet`. A label close-up (`label_front`, `label_back`) goes to the
  view `label` as it is.
- The gateway drops the alpha channel. So the configuration check rejects
  `remove_background` with no `white_background` after it, and a build fails each item
  whose model input has a transparent pixel. The page shows the error.
- The `embedding_hash` of an item covers the source file, the view, the model, the
  options, the steps, and the processed file. A build does nothing for an item whose
  hash did not change and whose prepared image exists. A change of the model or of the
  steps makes each item stale.
- The build writes one JSON line for each event to stdout. SIGTERM or Ctrl+C stops it
  after the present batch, and the finished items stay. A checkpoint writes the files
  every 30 s.
- The Embeddings page of the lab server (`/embedding`) shows the prepared images of one
  entry, with a combobox, the buttons `Build` and `Stop`, and the progress of each
  running build. Each running job row starts with an icon button `×`: it stops the build
  of that row (`POST /api/embeddings/<name>/stop`), also when the combobox selects another
  entry. A `stopping` row keeps a disabled `×`. `Build` continues a stopped build.
  The header has two rows. The first row holds the title, the
  `Configuration` combobox, the buttons, the message of the last build, and the
  navigation. The second row holds `Show` and `Search`. The header shows no counts; the
  row `Items` of the source panel shows them. The lab server starts a build with `embedding_python` of
  `config.yaml`. The routes are in `pipeline/embedding_routes.py`. `lab_server.py`
  sends each route of the page to that module. The old routes `/api/embedding` and
  `/img/embedding` of the review tool stay HTTP 503. The count of failed items is red
  when it is above zero. The `open` button of the row `Directory` opens the directory of
  the entry in Finder (`POST /api/embeddings/<name>/open` runs `open` on the Mac of the
  lab server; the route opens no other path). The row `Directory` does not repeat the
  endpoint of the first row. The `Log` button after `Stop` opens a dialog with
  `build.log` of the last build of the entry (`GET /api/embeddings/<name>/log`). Each
  JSON line shows as `time · event · fields`. A line that is not JSON, for example a
  traceback, shows as it is, in red. The checkbox `Show progress and request` is on at the
  start. When it is off, the `progress` and `request` lines are hidden. An `item_failed`
  line always shows. It names the wine of the failed file: `wine` (the slug), `name`,
  `image_type`, and `other_wines` when more wines use the same file. `Refresh` reads the
  file again. `Log` is disabled while the entry has no
  build yet.
  The button `Build All` (plan 60) builds each configuration with no configuration
  error, one at a time, in the order of `config.yaml`
  (`POST /api/embeddings/build-all`). A thread of the lab server runs the queue, so a
  closed tab does not stop it; a restart of the server ends it. A failed build does not
  stop the queue. `Stop`, or the `×` of the job row, stops the build and the queue. The
  message after the button shows the position (`Build All 3 / 12`) or the result, and its
  title lists the result of each configuration.
- The button `Selftest` (plan 67) checks that each dataset image is in the index of the
  selected configuration. Each image of an Active wine is one query: `main`,
  `main_patched` (the original `main` of a patched wine too), `full_front`, `full_back`,
  `label_front`, and `label_back`. A full image gets the SAM3 package cut and the steps of
  the view `full`, as a test photo; a label close-up goes in as it is. Each query searches
  the `full` vectors alone, with no barcode step. The truth is the wine of the image, so
  a file of two wines is a miss of one of them. The result is a run of the set `dataset`
  and the configuration `selftest-<name>` on `/runs`; the line after the button shows the
  job and `open run`. The button needs a current item and no running build. The same
  work is `pipeline/selftest.py --embedding <name>`. Read
  [plan 67](docs/plans/67_embedding-selftest.md).
- A click on a prepared image of `/embedding` opens the image preview of `/dataset`: the
  image in the center, the title (view and wine), the slug, the column, the image type,
  the status, `<position> / <count>`, the size, and `open raw image` (the original).
  The arrows, Left, Right, Up, and Down step to the image of the same view of the
  previous or the next column, over the wines of the filtered list. The thumbnails show
  each column of the wine: `original` and each view, with its status. The URL key
  `preview=<sha256>_<view>` names the open preview. Back closes it, and a link with the
  key opens it again. Esc or a click on the backdrop closes it. A click with Cmd, Ctrl,
  Shift, or Alt opens the prepared image in a new tab, as before.
- The job row of a running build shows its phase after `done / todo`:
  `waiting for the model · <time>` while a model request takes 3 s or more (a cold start
  of a gateway model takes up to about 48 s), and `retry <n> in <s> s: <error>` while the
  build waits to try a request again. The build writes the line `request` before each
  model request and the line `retry` before each wait; `embeddings.job_state` gives the
  keys `phase`, `phase_event`, and `phase_t`.
- The badge `vector` at the bottom left of an image cell tells that the vectors file of
  the entry holds the vector of the item. A `stale` item keeps the vector of its old
  hash, so it has the badge too. The preview names `vector` in its second line.
- The owner calls an entry a "configuration", because it holds more than the embedding
  model: the endpoint, the options, and the steps of each view. The selector of
  `/embedding` has the label `Configuration`. The route and the page name stay.
- The key `embeddings` holds the embedding models alone: the backends `openai` and
  `local`. The entry `vino-svoe-search-by-photo` moved to the key `pipeline` on
  2026-09-26 (owner message of 2026-09-25T23:37:48+0300, plan 34), so `/embedding` and
  `/clusters` do not show it. The owner removed the entry `mock`, its code, and
  `data/catalog/embeddings/mock/` on 2026-09-26 (owner messages of 00:26:27 and 00:29:55). An
  entry of `embeddings` with another backend gets an error that names the key
  `pipeline`.
- A pipeline of the backend `embedding` names an entry of the backend `openai` or `local`
  with an index. `pipeline/embedding_run.py` makes its runs of a test set (section "The
  runs of the lab"). Read [plan 33](docs/plans/33_embedding-run.md).
- A pipeline of the backend `embedding` MAY hold the key `barcode` (plan 42). The run
  decodes the photo with zxing-cpp before the views (`pipeline/barcode.py`, a copy of the
  decoder of svoe-vino-matcher). A GTIN or a QR URL that `wine_code` holds for one Active
  wine answers the photo: the wine at score 1.0, and the embedding does not run. A GTIN of
  2 or more Active wines puts its wines first: the embedding ranks every wine, and the
  other wines stay below them. With the key `rerank`, the VLM then compares only the wines
  of the GTIN ([plan 64](docs/plans/64_shared-gtin-rerank.md)). A QR URL of 2 or more
  wines decides nothing, and the normal match runs. A code of one wine wins over a shared
  GTIN ([plan 58](docs/plans/58_shared-codes.md)). A miss runs the views and the
  embedding. Each pipeline of the backend `embedding`
  has a twin `barcode-<pipeline>`. zxing-cpp 2.3.0 MUST be in `embedding_python`; it
  builds from the source (`requirements-local.txt`). Read
  [plan 42](docs/plans/42_barcode-step.md).
- A pipeline of the backend `embedding` MAY hold the key `rerank` (plan 48): the cluster
  re-rank of the section "The cluster re-rank". It runs inside the barcode step.

## The embedding clusters of the lab

The Clusters page (`/clusters`) reads one artifact from the directory of one embedding
configuration. Read [plan 30](docs/plans/30_embedding-clusters.md).

```bash
~/.venvs/svoe-vino-lab/bin/python pipeline/build_clusters.py \
    --name gx10-siglip2-so400m-patch16-naflex-p256
```

The command writes `data/catalog/embeddings/<name>/clusters.json`. The button `Build clusters` of
the page does the same for the selected configuration. The button `Build all clusters`
(plan 65, `POST /api/clusters/build-all`) builds each configuration with no configuration
error, one at a time, in the order of `config.yaml`. A thread of the lab server runs the
queue, so a closed tab does not stop it; a restart of the server ends it. A configuration
whose embedding build runs is waited for. A configuration with no vectors is skipped. The
text after the button shows the position (`Build all clusters 3 / 12: <name>`) or the
result, and its title lists the result of each configuration. Reviewer notes go to
`cluster-notes.json` in the same directory. A future offline difference-rule build will
write `cluster-rules.json` there. A cluster rebuild changes `clusters.json` alone.

These files are the only cluster data of the lab (plan 43). The Runs page shows the
clusters of the embedding of each run. The one note of the retired
`dataset/catalog-cluster-notes.json` is in `cluster-notes.json` of
`gx10-siglip2-so400m-patch16-naflex-p256`, under the key `a29e59138ed4`.

- `main_patched` replaces `main`.
- `full_front` and `full_back` contribute to the `full` and `label` spaces.
- `label_front` and `label_back` contribute to the `label` space alone.
- The builder compares vectors in one space only. It never compares a `full` vector
  with a `label` vector.
- One edge uses the highest cosine of all applicable image pairs of two wines. The
  artifact records the two images that gave this cosine.
- The `combined` view is the union of the `full` and `label` edges.
- Each two Active wines of one GTIN of `wine_code` are one more link of each view, with
  `gtin` in its list `by` and the signal `gtin` ([plan 64](docs/plans/64_shared-gtin-rerank.md)).
  A cluster of these links alone has the kind `gtin`. A QR URL gives no link.
- The initial threshold is `0.95` in each space. The page can build with other values.

The page shows the status of the embedding inputs, the exact evidence of each edge,
all current images in the selected space, and one note editor per cluster. The artifact
is stale after an embedding item or a wine-to-image assignment changes.

A card image is the segmented cut of the view: the `package` cut in `full`, the `label`
cut in `label` (`image_derivative`). The cut keeps its transparent background, and a
checkerboard shows the transparency, as on `/embedding` (owner message of
2026-09-26T09:51:00+0300). The API gives it as `cut_url` of each image of
`GET /api/clusters/<name>`. The prepared image (`prepared_url`) is the model input: the
same cut on white after the step `white_background`. The links of an edge row still open
the two prepared images. An image with no `segment` step, such as a close-up, has no cut
and shows its prepared image.

A click on a card image opens the image preview. The preview fits the window and has no
scroll bar. The Left and Right keys and the arrow buttons move through the images of one
cluster and wrap at its ends. The Up and Down keys open the first image of the previous
or the next cluster. A cluster with no image is skipped. The last cluster wraps to the
first. The title states the image position and the cluster, for example
`1/8 · cluster c001 (1/168)`. The count covers the clusters that the search shows.

The page does not create VLM difference rules. The offline command of the next section
creates them for the `label` space. The current matcher uses a query label crop, so it
can use only a `label` rule. At query time the VLM will receive closed questions with the
allowed answers, plus `other` and `not visible`. It will not discover new differences for
each query. The re-rank at query time is not in the lab yet (plan 45).

## The label rules of the clusters

A label rule tells the cards of one cluster apart. `pipeline/build_label_rules.py`
builds the rules of the clusters of the view `combined` of one embedding. Read
[plan 45](docs/plans/45_cluster-label-rules.md). The prompts and the check are a port
of `svoe-vino-testset/scripts/cluster_rules.py`.

```bash
python3 pipeline/build_label_rules.py --name gx10-siglip2-so400m-patch16-naflex-p256
python3 pipeline/build_label_rules.py --name <embedding> --stage describe
python3 pipeline/build_label_rules.py --name <embedding> --cluster <slug>
python3 pipeline/build_label_rules.py --name <embedding> --dry-run
python3 pipeline/build_label_rules.py --name <embedding> --force
```

| Stage | One VLM call for | Input | Answer |
|---|---|---|---|
| 1, `describe` | each card of a cluster | the `package` cut of the effective main image (`main_patched`, else `main`), on white, scaled UP or down to a long side of 2048 pixels; no card data | the label description: the texts and the numbers with their place, the vintage, the colours, the design, the marks, the bottle |
| 2, `rules` | each cluster | one image for each card: its `label` cut on white, scaled UP or down to 768 pixels (a card with no label cut sends its package cut); the card data; the descriptions without the key `bottle`; the note of the reviewer | the difference sheet (questions with the expected answer of each card), the rule text, and the groups that no feature separates |

The block `label_rules` of `config.yaml` holds the settings, with a comment for each key.
Stage 1 uses `qwen3.5-9b-nvfp4` with thinking off. Stage 2 uses `qwencloud-qwen3.8-max`
with thinking, 4 calls at the same time, since the owner message of
2026-09-26T16:01:00+0300: about 70 s for one rule. The key comes from the shell variable of
that `vlm` entry. The rules of `qwen3.5-9b-nvfp4` (thinking off; with thinking it gave no
answer in 12,000 tokens) are kept as `cluster-rules.qwen3.5-9b-nvfp4.2026-09-26T1116.json`.
The two rule sets give the same benchmark within the noise (plan 48). The service of
`qwen3.5-9b-nvfp4` accepts at most 20 images in one prompt (`rules_max_images`, the vLLM
option `--limit-mm-per-prompt`). A cluster with more cards gets an error record and no call.
When the service refuses the number of images, the command stops with a message that
names the limit of the service.

The code checks the sheet, as in `svoe-vino-testset`: a question about a bottle number
or about a feature outside the label is never valid; a vintage year counts only when the
name or the slug of the card states it (with the vintage variants of plan 06 of
`svoe-vino-testset`); a question about the alcohol value counts only when no other
question is valid. The mode is `sheet` when a question is valid, else `verdict` when the
rule text is not empty and names no feature outside the label, else `none`. Each question
holds `evidence`: the SHA-256 of the picture that stage 2 sent for each card.

`data/catalog/embeddings/<name>/cluster-rules.json` holds the descriptions under `cards` (by slug)
and the rules under `spaces.label` (by cluster key). A rule is current while its inputs
stay the same: the members, the card data, the pictures, the descriptions, the note, and
the settings of the prompt. A cluster build that keeps the members keeps the rule; the
next run writes the new `input_hash` of `clusters.json` into it with no call. The command
does only the work that is not current, so a stopped run resumes. Each answer goes
through the model cache.

The page `/clusters` shows the `label` rule in the views `combined` and `label` (the
block `VLM difference rule`). The rule is `stale` when `clusters.json` has a new input
hash, or when the note of the cluster changed after the build. The Runs page reads the
questions of the rule (plan 43).

`Save note` also starts the rebuild of the rule of that cluster (owner answer of
2026-09-26T11:11:00+0300): the route runs `build_label_rules.py --cluster <slug> --wait`
as a separate process, and its output goes to `data/catalog/embeddings/<name>/label-rules.log`.
The rebuild waits for a running rule build. The page shows `Saved · rebuilding the rule…`,
asks for the rule every 3 s, and replaces the rule block when the rule is current
(`Rule rebuilt`), usually after 10 to 20 s. After 5 minutes it stops and names the log.
The prompt tells the model that the note is a correct fact, so a note can name a feature,
for example the colour of a mark.

## The cluster re-rank

The key `rerank` of a pipeline uses the label rules at query time. Read
[plan 48](docs/plans/48_cluster-rerank.md). `pipeline/cluster_rerank.py` is a port of the
kind `cluster_rules` of `svoe-vino-matcher`, with its prompts verbatim.

1. The base answer of the pipeline comes first. A code hit of the barcode step answers the
   photo, and the re-rank does not run.
2. The step acts when the rank-1 card is in a cluster with a rule of mode `sheet` or
   `verdict`, and another card of that cluster stands in the first `window` (5) positions.
   The clusters and the rules come from the embedding directory that `rerank.rules`
   names, for every pipeline.
3. The VLM (`rerank.vlm`, `qwen3.5-9b-nvfp4`, thinking off) gets the SAM3 label cut of the
   photo on white at 1,536 pixels, and the questions of the rule (`sheet`) or its rule text
   (`verdict`).
4. Only the cards of the cluster inside the window change their order. A failure of the VLM
   keeps the base order.
5. A photo with a GTIN of 2 or more wines puts the wines of the GTIN first (the barcode
   step). Then the step acts only when the rank-1 card is a wine of the GTIN, and the
   window holds only the wines of the GTIN of its cluster. Another card does not move
   ([plan 64](docs/plans/64_shared-gtin-rerank.md)).

Each card that the step touched holds `explain` with `kind: cluster_rules`; the VLM box of
`/runs` shows it. The trace of the photo holds the step `cluster_rules`. The pipelines
`rerank-siglip2-512-crop` and `barcode-rerank-siglip2-512-crop` use the rules of
`gx10-siglip2-so400m-patch16-naflex-p256`.

## The VLM inferences

The key `vlm` holds one entry for each named VLM inference. `config.yaml` and
`config.old.yaml` hold the same section; `tests/test_vlm_config.py` checks that the two
files agree. `pipeline/vlm_config.py` reads the key. An entry holds the first five keys,
MAY hold `key` and `max_tokens`, and holds no other key:

| Key | Meaning |
|---|---|
| `name` | The name that a client uses. The names differ. |
| `protocol` | `openai`: `POST <endpoint>/chat/completions`. |
| `thinking_field` | Where the switch `enable_thinking` goes: `chat_template_kwargs` (the gx10 gateway) or `top_level` (QwenCloud and DashScope). In `scripts/cluster_rules.py` it also selects the JSON mode rule and the second attempt of an answer that reached `max_tokens`. |
| `endpoint` | The base URL, for example `http://192.168.86.14:18081/v1`. |
| `model` | The model name that the service knows. |
| `key` | Absent or `null` when the service needs no key, or `{env:NAME}`: the key is read from the shell variable `NAME` at run time. A key value in the file is refused. |
| `max_tokens` | Absent (8192) or a positive integer: the `max_tokens` of a detail request of `pipeline/describe_images.py` (owner answer of 2026-09-25). A class request keeps 300. `scripts/cluster_rules.py` and `pipeline/wine_identity_vlm.py` keep their own limits. |

| Entry | Service | Key |
|---|---|---|
| `qwen3.5-9b-nvfp4` | gx10 gateway; the image descriptions of plan 26 | none |
| `qwen3.5-9b` | gx10 gateway; stage 1 of the cluster rules | none |
| `qwen3-vl-32b` | gx10 gateway; pairwise wine-identity checks | none |
| `qwencloud-qwen3.8-max` | QwenCloud Token Plan; stage 2 of the cluster rules | `{env:QWENCLOUD_TOKEN_PLAN_API_KEY}` |
| `qwencloud-qwen3.8-flash` | QwenCloud Token Plan | `{env:QWENCLOUD_TOKEN_PLAN_API_KEY}` |
| `dashscope-qwen3.7-flash` | DashScope, pay-as-you-go | `{env:QWENCLOUD_PAYGO_API_KEY}` |

`pipeline/wine_identity_vlm.py` builds pairwise wine-identity backends from a supplied
configuration map. It ignores an entry whose key variable is not set.
`scripts/cluster_rules.py` imports `scripts/common.py`, which needs the key `dataset`, so
it runs with `SVOE_VINO_REVIEW_CONFIG=config.old.yaml`. It refuses a call whose key
variable is not set. `scripts/bench_vlm_models.py` keeps its own endpoint and does not
read the key `vlm`.

## The image descriptions

The table `image_description` describes each image that `wine_image` links to a wine
(`main`, `main_patched`, and the additional types): `package_type`, `subject_scope`,
`package_view`, `content_roles`, and `presentation_mode`. Read
[plan 26](docs/plans/26_image-description.md).

| Field | Values |
|---|---|
| `package_type` | `bottle`, `can`, `keg`, `bag`, `bag_in_box`, `tetra_pak`, `barrel`, `decanter`, `box`, `other`, `unknown` |
| `subject_scope` | `full_package`, `label_closeup`, `multiple_packages`, `unknown` |
| `package_view` | `front`, `back`, `unknown` |
| `content_roles` | a list of 1 to 2 of `front_label`, `back_label`, `unknown`; `unknown` stands alone |
| `presentation_mode` | `on_package`, `flat_surface`, `other`, `unknown`: the surface that carries the label |

- Schema 024 (2026-09-26) added `presentation_mode` and put each row that the VLM had
  filled back in the queue of the watcher. The four old values stay and go into the
  prompt as fixed facts, so the next answer fills `presentation_mode` alone. The fixed
  facts start with "These values are already set."

- A button `✎` in the bottom right corner of each image of `/dataset` opens the editor
  of that image. A value set by hand stays. `— not set —` clears a value.
- The page path names the open editor: `/dataset/<wine_slug>/describe/<sha256>`. A link
  to this path opens the same editor over the card of the wine. Back closes the editor.
  An image that no card holds gives the plain page at `/dataset` (owner message of
  2026-09-27T13:49:11+0300).
- `created_by` tells who made the row: `manual` (the owner, before the VLM) or `vlm`.
  `vlm_at` is empty until the VLM filled the row.
- The watcher `pipeline/describe_images.py` sends each image with no VLM fill to the
  `vlm` entry of `image_description.vlm` (`qwen3.5-9b-nvfp4`). The prompt holds the
  values that are set as fixed facts. The code checks the answer against the JSON Schema
  `ANSWER_SCHEMA` and fills only the values that are not set (`COALESCE`). `vlm_answer`
  keeps the full answer. An answer that fails the schema writes nothing and counts as a
  failure; an image stops after `max_attempts` (3) failures. A failure of the service (an
  HTTP 429 or 5xx answer, no connection) does not count; the watcher waits and tries again.
- A request that times out (300 s) gets a probe: a chat request of 1 token with no image
  to the same model, with a timeout of 30 s ([plan 49](docs/plans/49_vlm-timeout-probe.md)).
  When the probe answers, the model serves, so the timeout counts against the image and
  starts no backoff. When the probe fails too, the timeout is a failure of the service.
  So one image that makes the model write for more than 300 s stops after 3 attempts and
  does not stop the queue.
- The watcher sends up to `image_description.workers` requests at the same time (8 in
  `config.yaml`, 1 when absent; [plan 35](docs/plans/35_vlm-workers.md)). Each request
  runs in a thread of a pool and holds one image; two requests never hold the same image.
  A failure of the service stops the new requests for the backoff time (30 s, doubled up
  to 600 s); the requests that run finish, and their results are stored. The speed on the
  pill is the wall time per image of the last 20 images, so with 8 workers it is the rate
  of the backlog, not the time of one request.
- The lab server starts the watcher when `image_description.watch` is true. The commands
  are in `COMMANDS.md`, section "Описания изображений".
- The pill at the left of `Add wine` shows the watcher: `VLM 895 / 2,022 · 2.6 s`
  (working, a green dot that pulses), `VLM all … described` or `VLM idle · … pending`
  (idle), `VLM waiting: <error>` (amber: the service or the database cannot be used now),
  or `VLM watcher not running` (stopped). The pill shows the full error with the full
  endpoint; a long error wraps and is never cut. `· N failed` in red counts the images
  that reached `max_attempts`. Its title names the pid, the wine of the image that the VLM
  reads now, the counts, the speed of the last 20 images, and the time of the last step.
  The page asks `GET /api/image-description-status` every 5 s while its tab is visible.
- A click on the text of the pill opens the dialog `VLM watcher` (plan 49): the state,
  the endpoint, the full error, the counts; in the state `waiting` the time of the first
  failure, the backoff, the next try, and the image of the failed request; each request
  that runs with its thumbnail, its age against the timeout, and its attempts; and the
  last 30 lines of `work/describe_images.log`. While it is open, each poll asks
  `?log=30` and draws it again. A click on a thumbnail opens the file in the preview.
  The watcher writes its state into `work/describe_images.status.json` at each step; the
  route reads it, checks that the pid lives, and adds the counts of the database. The
  cards do not change while the page is open; a reload shows the new descriptions.
- The dialog holds a closed block `Raw VLM reply` for a row that the VLM filled. It
  loads `GET /api/image-description-reply?sha256=<sha256>` when it opens: the record of
  the call in `data/cache/models/`, with the model, `finish_reason`, the tokens, the reply text,
  the prompt, the full response body, and the request fields. The route builds the key of
  the call again from the image, `max_side`, the `vlm` entry, and the prompt; a change of
  one of them makes an old record unfindable (`found: false`).
- The button `Advanced Filters:` in the bar shows a second row of filters. Its first
  filter is `Package`: `All`, each `package_type`, and `not described`. The
  `package_type` of the patched image decides when the wine has one, else the main
  image. A wine with no image is `not described`. The button is marked while a filter is
  active. A save in the dialog draws the card again but does not apply the filter again,
  as for `Show`; choose the value again to apply it.
- The second filter of the row is `Identifier`: `All`, `has GTIN`, `has QR URL`, and
  `has Drink Atlas`. It keeps the wines with at least one value of the chosen kind.
  `has Drink Atlas` counts a manual and an automatic Atlas Core binding. The filters of
  the row apply together. A change in a code editor does not apply the filter again, as
  for `Show`.
- The filter `Alternatives` of the row shows `All` or `has alternative photos`. It keeps
  the wines with at least one active alternative photo. It needs no service, so the
  button `Advanced Filters:` shows on each page. `Package` shows only when the image
  descriptions are on. An upload or a removal of an alternative photo does not apply the
  filter again, as for `Show`.

## The image details

Stage 2 of the watcher (plan 29, [docs/plans/29_image-details.md](docs/plans/29_image-details.md))
describes the label of each image, so that a person can tell the wine apart from similar
wines of the same producer. The answers are in the table `image_detail`, one row for each
original.

- An image gets a detail when `wine_image` links it, its `subject_scope` is
  `full_package` or `label_closeup`, and its `package_type` is not `other` or `unknown`.
  `multiple_packages` and `unknown` scopes get no detail.
- A `full_package` image gets the package prompt of the owner with its `package` cut. The
  word `bottle` becomes the name of the `package_type` (`can`, `Tetra Pak carton`, …),
  also in the last key (`"can"`, `"tetra_pak"`). A `label_closeup` image gets the label
  prompt with its `label` cut, else its `package` cut. With no cut, the VLM gets the
  original.
- The watcher runs stage 2 only when no image waits for a class, and only with
  `image_description.details: true`. The request sends the JSON Schema of the answer in
  `response_format` (`json_schema`, strict), a long side of `detail_max_side` (1,536), and
  `max_tokens` of the `vlm` entry (8,192 when absent; 4,096 from `detail_max_tokens` until
  2026-09-25). The code checks the answer against the same
  schema. An answer that `max_tokens` cut off, or that fails the schema, is a failure;
  3 failures stop the image.
- A row stores its inputs: `prompt_kind`, `package_type`, and `input_sha256` (the file
  that the VLM got). A change of one of them, for example a new `package_type` from the
  editor or a new label cut, makes the row stale, and the watcher sends the image again.
- The pill reads `VLM details <done> / <eligible> · <seconds> s` while stage 2 works, and
  `VLM all <n> described · details <done> / <eligible>` when it is idle. Its title holds
  the line `Details …`. `N details failed` in red counts the failed details.
- A click on `N details failed` opens the dialog `Failed details`. It reads
  `GET /api/image-detail-failures` at each opening. The route sends each image whose
  detail failed `max_attempts` times with its present inputs, the newest failure first:
  the wine slug, the file that the VLM got (a thumbnail: a click shows the file alone in
  the image preview, with no arrows; a click with Cmd, Ctrl, or Shift opens it), the prompt
  kind, the `package_type`, the attempts, the time, the last error (`vlm_error`, at most
  1,000 characters), and the last 20 entries of `work/describe_images.log` that name the
  image. An entry keeps the lines that follow it, for example the text of a cut answer.
  `max_attempts` is the value of the running watcher, else 3. The watcher sends such an
  image again when its inputs change, or after a start with `--retry-failed`.
- The details are not shown on `/dataset` yet (owner answer "Later" to Q1 of plan 29).
  Read them with `sqlite3` (`COMMANDS.md`, section "Описания изображений").
- The 9B model misreads small text, for example «ПИСАДКОЕ» for «ПОЛУСЛАДКОЕ». A detail is
  not a verified transcription.

## The label descriptions

Stage 3 of the watcher (plan 61, [docs/plans/61_label-descriptions.md](docs/plans/61_label-descriptions.md))
gives each linked image a label description: the answer of `DESCRIBE_PROMPT` of the
cluster rules (`pipeline/label_rules.py`). The rows are in the table
`image_label_description` (schema 027). One image can have many rows; the latest row (the
newest `created_at`, then the higher `id`) is the effective description.

- The request is the request of stage 1 of the cluster rules: the `package` cut of the
  image, else the original, as PNG at a long side of `label_rules.describe_side` (2,048),
  `max_tokens` `label_rules.describe_max_tokens` (1,500), thinking off, `json_object`, and
  the VLM entry `label_rules.vlm`. An answer that `max_tokens` cut off is sent once more
  with `repetition_penalty` 1.15 and 3,000 tokens (the loop guard). Stage 3 and the
  cluster rules share the records of `data/cache/models/`.
- It is a separate request. It does not change the class request of stage 1.
- The code repairs obvious key drift: `text` becomes `texts`, `number` becomes `numbers`,
  `colors` becomes `colours`, and so on (`label_descriptions.repair`). Then
  `describe_images.LABEL_SCHEMA` checks the answer. A failure counts; 3 failures stop the
  image (`image_label_description_failure`). `label_rules.describe` repairs the same drift
  in each new cluster description; the stored cluster descriptions keep their keys.
- Each VLM row records `vlm_name`, `vlm_endpoint`, `vlm_model`, `vlm_served_model`,
  `max_tokens`, `thinking`, `input_sha256`, `created_at`, the other settings in
  `vlm_request`, and `finish_reason`, `usage`, the time, the cache hit, the renames, and
  the raw answer in `vlm_reply`.
- The watcher sends no request for an image that has a row. It runs stage 3 only when no
  image waits for a class or a detail, and only with `image_description.labels: true`.
- The dialog `Image description` of `/dataset` shows the section `Label description`: one
  block for each row, the latest first and open. `Edit as new` opens a JSON text area with
  the row; `Save as new` adds a manual row, which becomes the latest. `Add manual` starts
  from an empty object of the seven keys. `Remove` deletes one row after a confirmation.
  When the last row goes, the watcher describes the image again.
- The pill reads `VLM labels <done> / <linked> · <seconds> s` while stage 3 works. Its
  title and its dialog hold the line `Labels …`.

## The runs of the lab

The Runs page of the lab server (`/runs`) shows the run directories of `runs/`. The runs
stay files; the lab database does not hold them. The page is the Runs page of the
review tool: the table of the runs, the metric cards, the histograms, the photo rows
with `Show`, `Sort`, and `Find`, the candidate images with the cluster frames and the
VLM box, and the large view with the arrow keys and the model inputs. Read
[plan 23](docs/plans/23_runs-page.md).

```bash
# a run of a remote pipeline (backend svoe-vino-ru): each photo goes to the API as it is
python3 pipeline/remote_run.py --name vino-svoe-search-by-photo --set my \
    [--workers N] [--limit N] [--label TEXT]

# a run of a pipeline of the backend embedding: each photo gets the SAM3 cuts and the
# steps of its embedding entry, and its vectors rank the catalogue vectors of that entry
python3 pipeline/embedding_run.py --name siglip2-p256-crop --set my \
    [--workers N] [--limit N] [--label TEXT] [--top-k N]

# the runner of the button Run> of /testset: one JSON event on each line
python3 pipeline/run_job.py --name <pipeline> --set <set> [--limit N] [--workers N] \
    [--no-cache]
```

- `remote_run.py` builds the HTTP backend of `scripts/match_backends.py` from the
  pipeline and calls `benchmark.run_benchmark`. The run id is `<stamp>-lab-<name>-<set>`.
  `run.json` holds `configuration: <name>`, and its `backend` holds `kind: remote`. The
  default of `--workers` is `workers` of the entry (8). A full run of the set `my` sends
  about 2,200 photos to an external API.
- `embedding_run.py` makes a run of a pipeline of the backend `embedding` (plan 33; owner
  answers of 2026-09-25T23:24:20+0300, 23:35:19, and 2026-09-26T00:12:24). The key
  `embedding` of the pipeline names an entry of `embeddings:`, and that entry needs its
  index: build it on `/embedding` first. Each photo counts as a full photo and gets the
  cuts of a catalogue image in memory: the package cut of `derive.derive_image` and the
  label cut of `alternatives.label_cut_of`, then the steps of each view with
  `embeddings.apply_steps`. A pipeline MAY hold `views`, the steps of the test photo in
  place of the steps of the entry (owner answers of 2026-09-26T00:52:41); a view with no
  `segment` takes the photo as it is and sends no SAM3 request.
  One request to the endpoint of the entry gives the vector of each view. The score of a
  wine is the mean of its best cosine in each view of the photo, over the current items
  of the index; a stale item stays out. When SAM3 finds no label, the photo has the view
  `full` alone. The SAM3 answers go to `data/cache/models/sam3/`, so a second run of a set sends
  no SAM3 request. When SAM3 does not answer, the run asks it no more, and each photo
  gets an error. `run.json` holds `configuration: <pipeline>`, and its `backend` holds
  `kind: embedding`, `embedding: <entry>`, the steps of each view, and the SAM3 settings;
  its `embeddings` holds `built_at`, `index_file`, and the count of each item state. The
  default of `--workers` is the optional `workers` value of the pipeline, or 1 when the
  value is absent. `barcode-rerank-siglip2-512-crop` sets `workers: 4`. The Run dialog
  shows this default. An explicit `--workers` or dialog value overrides the default.
  The worker count of an active run does not change. An entry of the backend `local` needs `torch`: run it with
  `~/.venvs/svoe-vino-lab/bin/python`. The dialog `Run>` starts such a pipeline with
  `embedding_python` (plan 34); a pipeline whose entry has no index is disabled with the
  note `no index: build it on /embedding`. `config.yaml` holds two such pipelines,
  `siglip2-p256-as-is` and `siglip2-p256-crop`, of the entry
  `gx10-siglip2-so400m-patch16-naflex-p256` (next bullet). The first pipeline of that
  entry (owner answer of 2026-09-26T00:15:17) had the name of the entry; the owner removed
  it at about 01:07, and its 2 runs count as `no pipeline` (owner answer of 01:19:00).
  Read [plan 33](docs/plans/33_embedding-run.md).
- With `rebuild_embeddings_on_run: true` (the lab `config.yaml` sets it; owner messages
  of 2026-09-27T08:40:19+0300 and 08:40:26), `run_job.py` and `embedding_run.py` update
  the index of the embedding of the pipeline before the run. `pipeline/rebuild_on_run.py`
  starts `build_embeddings.py`, as the button `Build` of `/embedding` does, and waits for
  its end. The build does only the stale, missing, and failed items: with no change it
  takes a few seconds. Its output goes to the end of `build.log`, so `/embedding` shows
  its progress. The run waits for a build of the same embedding that runs already. A
  build that fails or stops makes the run fail; a failed item does not. An embedding with
  no index gets no build: build it on `/embedding` first. A stop of the run sends SIGTERM
  to the build, and the finished items stay. `/recognize` and the scripts
  `scripts/benchmark_*.py` do not update the index. Read
  [plan 59](docs/plans/59_rebuild-embeddings-on-run.md).

- `barcode-rerank-siglip2-512-crop-label` adds a second retrieval tower to
  `barcode-rerank-siglip2-512-crop`. The first tower keeps the package rectangle and
  searches the `full` vectors. The second tower uses the existing SAM3 label rule,
  applies the catalogue label steps, and searches only the `label` vectors of
  `gx10-siglip2-so400m-patch16-512`. Both inputs use one embedding request. The trace
  shows a separate top-k list for each tower. The final rank uses the existing mean
  of each wine's best available cosine in each view. It does not merge two truncated
  top-k lists. A missing query label uses the first tower alone. Barcode lookup,
  cluster reranking, and the default of four workers stay enabled. The profile uses
  the existing index and needs no embedding build. SAM3 selects labels on the original
  photo. This profile adds no association between a label and the package selected by
  the first tower in a photo with multiple bottles. The existing label rule uses a
  mask for one label and an enclosing rectangle for multiple body labels.

- A pipeline of the backend `embedding` MAY hold the key `views`: the steps of the test
  photo in each view, in the step language of `embeddings`. The first step MAY be another
  step than `segment`. Without the key, the photo gets the steps of the embedding entry.
  The catalogue side stays the index of the entry; a view of the photo is compared with
  the vectors of the same view of the index. Two basic pipelines of
  `gx10-siglip2-so400m-patch16-naflex-p256` use it (owner message of
  2026-09-26T00:45:33+0300): `siglip2-p256-as-is` (the photo as it is:
  `white_background`, `resize` 1024) and `siglip2-p256-crop` (`segment` of the package
  with the background of its box, `white_background`, `resize` 1024). `white_background`
  does not change an opaque photo; 60 queries of `my` have transparent pixels.
- `siglip2-p256-crop-seg` (owner message of 2026-09-26T23:24:00+0300, answers of
  23:27:00) is `siglip2-p256-crop` with `remove_background` after `segment`: the SAM3
  mask of the package makes the background inside the box white. These are the steps of
  the view `full` of the index. Its barcode twin is `barcode-siglip2-p256-crop-seg`.
- Plan 40 adds the same two pipelines for each other entry of `embeddings`:
  `<short>-as-is` and `<short>-crop`, for example `siglip2-512-crop` of
  `gx10-siglip2-so400m-patch16-512` (20 pipelines; YAML anchors hold the steps one time).
  The benchmark of the 22 pipelines is
  [docs/reports/2026-09-26_embedding-benchmark.md](docs/reports/2026-09-26_embedding-benchmark.md).
- The key `configuration` of `run.json` names the pipeline of a run: one entry of the
  key `pipeline` in `config.yaml` (plan 34; the key keeps its old name).
  `pipeline/benchmark.py` writes it when `run_benchmark` gets the argument
  `configuration`. A run with no such key has no pipeline; all runs before 2026-09-25
  are such runs.
- The filter `Pipeline` in the header, after the title `Match runs`, offers `All` (every
  run; owner answer of 2026-09-26T01:19:00+0300), each pipeline of `config.yaml` with
  the count of its runs, and `no pipeline`: the runs whose key `configuration` is absent
  or names no pipeline, for example the runs of a pipeline that the owner removed. The
  filter lists the items of the key `pipeline` alone (owner message of
  2026-09-26T00:10:18+0300). The page
  address keeps the value (`?configuration=<name>`); the hash keeps the open run. When
  the open run leaves the table, the first run of the table with metrics opens.
- The table of the runs has pages: `prev`, `next`, and `per page` (25, 50, 100, or
  `all`). The browser keeps the page size. A sort goes back to page 1; the hash of a run
  opens the page that holds it.
- The filter `Testset` stands after the filter `Pipeline` (owner message of
  2026-09-26T07:03:17+0300). It offers `All`, each test set that a run names with the
  count of its runs, and `no test set`: the runs whose `run.json` has no key
  `options.set`, which are the runs of `scripts/match_run.py`. `pipeline/benchmark.py`
  writes the key for every lab run. The two filters work together. The page address keeps
  the value (`?set=<name>`), and `localStorage` keeps it in `svl.runs.header`.
- The table has the column `pipeline`: the key `configuration` of `run.json`, and the
  column `testset`: the key `options.set` of `run.json` (`set` in `/api/runs`).
- A run whose `run.json` holds `use_cache: false` has the tag `no cache` after its id:
  the checkbox `Use caches` of the dialog `Run>` was off, so the run read no cached
  model answer, and its latency is real time (plan 39). A run with no key gets no tag.
- A run whose `run.json` holds `use_barcode: false` has the tag `no barcode` after its id:
  the checkbox `Disable barcode fast path` of the dialog `Run>` was on, so the run skipped
  the barcode step of its pipeline (plan 53). A run with no key gets no tag.
- The photo of a row comes from the image store of the lab database by its
  `image_sha256`, in the folder of its `image` row (mostly `testset`). A photo whose
  bytes are not in the store shows `not in the lab image store`. The catalogue image of
  a slug is its processed patch when the wine has a `main_patched` image (with the mark
  `patched`), else its processed `main` image, as on the card of `/dataset`.
- The cluster frames and the VLM box read the clusters of the embedding of the open run
  (plan 43): the view `combined` of `data/catalog/embeddings/<name>/clusters.json`, and the
  `label` rule of a cluster from `cluster-rules.json` of the same directory. The route is
  `/api/run-clusters?id=<run id>`. A pipeline run names its embedding in
  `backend.embedding` of `run.json`. An older run of an embedding configuration names it
  in `backend.id`. A run of another backend shows no frame. The link `cluster details`
  opens `/clusters?name=<embedding>&space=combined#<slug>`. The tooltip of a frame adds
  `stale` when the inputs of the embedding changed after the cluster build.
- The model inputs of the large view use `scripts/run_model_inputs.py` and the code of
  `svoe-vino-matcher`, as in the review tool. A run with no backend URL, for example an
  old run of the removed pipeline `mock`, states that it has no model input. A run of a
  remote pipeline states that the photo went to the remote matcher as it is. A run of an embedding configuration
  shows the model input of each view: the route makes it again from the steps of
  `run.json` and the SAM3 answers of `data/cache/models/sam3/`, and sends no request.
- A click on a candidate image of an embedding run opens the large view with the
  catalogue inputs of that wine in the strip (plan 38, owner message of
  2026-09-26T01:23:11+0300). Each item is the PNG of the index that went to the model,
  with its view, its image type, and the cosine that the run recorded. A note states the
  score: the mean of the best cosine of each view. The badge `best` marks the best item of
  each view. An item of a view that the query does not have is dim and reads
  `not compared`. When the index changed after the run, the item keeps its cosine and has
  no image. A run from before plan 38 recorded no cosine of an item: the strip shows the
  items of the present index and reads `no cosine`. The route is `/api/run-candidate`.
- A click on the query photo of a row opens the step popup (plan 41, owner message of
  2026-09-26T07:14:42+0300). It shows the way of the photo through the pipeline as the
  step view of `drink-atlas-recognize` on port 8162: rounds with a clock (the elapsed
  time and the sum of the step times), and one card for each step with its number, its
  name, the service and the model, its time, and its state. A card opens with a click and
  shows what the step made: the photo with the SAM3 box, the cut, the model input of each
  view with a check against the run (`same as the run` or `changed since the run`), the
  top list of each embedding space (`full`, `label`), the answer, and the sections `Step
  settings` and `Result`. A matcher run shows its model inputs, the order before the
  re-rank, the difference step, and the VLM rule step with its questions and answers. A
  click on an image of the popup opens the large view above it. `Esc` closes the large
  view first, then the popup; the arrow keys up and down move the popup to the next row.
  Only an embedding run made after plan 41 has step times: `embedding_run.py` writes the
  key `trace` into each row. An older run shows the same steps with no time. The route is
  `/api/run-steps`.
- The candidate cards of one photo row have one height: the height of the tallest card
  of the row (owner message of 2026-09-26T00:12:24+0300). In a row with a cluster frame, a
  card outside a frame starts where the cards of the frame start. A card has a fixed
  width, so a long slug makes its whole row taller and is not cut.
- The owner removed the pipeline `mock` and `pipeline/mock_run.py` on 2026-09-26 (owner
  message of 00:26:27). Its 2 runs of 2026-09-25 stay in `runs/`; the filter shows them
  under `no pipeline`.
- The button `New testset…` after the heading `Metrics of <run>` makes a new test set of
  the lab database from the misses of the open run (plan 44, owner message of
  2026-09-26T09:05:00+0300). The dialog selects the R@1 misses (the true slug is not at
  rank 1) or the R@5 misses (the true slug is not in the top 5), with the count of each.
  The misses come from the whole run: `Show` and `Find` do not change them. A positive
  photo of the run enters when the set of the run still holds it with the same place, file
  name, SHA-256, and label. The dialog counts the other photos by reason (`gone`, `other
  bytes`, `label changed`) and states the photos with a failed request. The field `Name`
  holds `<set>-<N>`: the name of the set of the run without a trailing `-<digits>`, and
  the first free number (`my` gives `my-1`, `my-1` gives `my-2`). `Create` copies the rows
  of the photos, the comments of the photos, and the variant groups of the source set
  (plan 51: the wine comments belong to no set, and the exclusion went away). No photo
  file is copied. The note of the new set (`label_note`) states
  the origin, and `source_dir` is the run directory. The new set stands on `/testset`, and
  the dialog `Run>` runs it. The button is off for a run that names no test set and for a
  dry run. The routes are `GET /api/testset-from-run?id=<run id>` and
  `POST /api/testset-from-run` of `pipeline/testset_routes.py`; the rule is in
  `pipeline/testset_from_run.py`. A new seed of the database (`seed_from_testset.py`)
  builds the three source sets alone: a set made from a run stays in the backup of the
  old database only.
- The routes are in `pipeline/run_routes.py`; `pipeline/run_files.py` reads the files.
  `lab_server.py` sends each route of the page to `run_routes.py`. The review tool keeps
  its own copy of the run functions.

## The Recognize page of the lab

The Recognize page of the lab server (`/recognize`) recognizes one photo that the user
gives. Read [plan 55](docs/plans/55_recognize-page.md).

- The select `Pipeline` at the top holds each pipeline of the backend `embedding` of
  `config.yaml`. A pipeline whose embedding has no index is disabled, and its title states
  the reason. The page keeps the choice; the address `?pipeline=<name>` wins.
- Drop a photo on the page, or click the drop area to open a file. The photo goes to the
  selected pipeline at once. The button `Recognize` sends the present photo again, for
  example after a change of the pipeline. A change of the pipeline alone sends nothing.
- The server writes the photo to `work/recognize/<sha256>.<ext>` and keeps it. It runs
  `pipeline/recognize.py` in a new process of `embedding_python` for each photo. The script
  builds the backend of the pipeline as a run does, and asks it one time. So a pipeline of
  gx10 sends one SAM3 request and one embedding request, and llama-swap loads the
  embedding model when it does not run. A pipeline of the backend `local` loads its model
  in each process: 20 to 26 s on this Mac (measured on 2026-09-26).
- Configured embedding pipelines use the hybrid main-scene selector of
  `pipeline/main_scene.py` for the package cut (plan 69). One SAM3 request finds
  `wine bottle`, `can`, `packet`, `box`, and `hand`. The selector ranks each package by
  hand contact, relative area, center position, sharpness, detector confidence, mask fill,
  shelf isolation, and edge visibility. It gives no package class a fixed priority. The
  package step records each signal, each contribution, the candidate order, and the
  selected package in `Result`. The catalogue-image processor keeps its bottle-first rule.
- Below the drop area the page shows the steps of the photo as the step popup of `/runs`
  shows them: the rounds, the cards, the times, and the total of the photo. The head line
  shows the first candidate and the time of the process: the start of Python, the build of
  the backend, and the recognition.
- The step view is shared: `pipeline/pages/steps.css` and `pipeline/pages/steps.js`.
  `lab_pages.page` puts them in place of the lines `/* STEPS_CSS */` and `/* STEPS_JS */`
  of `runs.html` and `recognize.html`.
- The routes are in `pipeline/recognize_routes.py` (`docs/API.md`, section "The Recognize
  page").

## The Health page of the lab

The Health page of the lab server (`/health`) shows the state of the server and checks
each endpoint of `config.yaml`. Read [plan 46](docs/plans/46_health-page.md).

The status part loads when the page opens and again after each check. It shows:

- the server: the process id, the start time, the uptime, the Python version, and the
  path of `config.yaml`;
- the database: the schema version of the file and of the code, the wines of each state,
  the size, and the free disk space (`warn` below 5 GB);
- the image description watcher: its state, its counts, and the failures of the last
  hour in `work/describe_images.log`;
- the embedding builds and the run jobs that run now;
- the models that run on each llama-swap gateway now (`GET <root>/running`). A mark
  shows each model that `config.yaml` names.

The button `Check` sends `POST /api/health/check` for each endpoint, 4 at the same time,
and fills one row for each answer. The endpoints are the entries of `vlm` and
`embeddings`, SAM3 (`sam3.endpoint`), and the vino-svoe.ru API. A row has the status
`ok`, `idle`, `warn`, or `error`, a summary line, and the details: each request with its
HTTP code and its time.

The check loads no model on gx10:

- An endpoint with no key reads `GET <root>/running` and `GET <root>/v1/models` of its
  llama-swap gateway. A model that runs gets one real call. A model that does not run
  gets `idle` and no call, because a call would start it. A model that the gateway does
  not list gets `error` with the close names.
- A cloud entry reads `GET <endpoint>/models` with its key, then gets one real call. A
  key variable that is not set gives `error`, and the check sends no request.
- The real call of a VLM is a chat request of 1 token with thinking off. The real call of
  an embedding entry sends one grey PNG of 64 x 64 px. SAM3 gets `GET <endpoint>/health`.
  The vino-svoe.ru API gets `GET /v1/wines?page=1&perPage=1`; the check sends no photo.
- The entry of the backend `local` imports torch and transformers in `embedding_python`,
  and looks for the model in the Hugging Face cache. It loads no model.
- The check does not read `data/cache/models/`: a health check MUST reach the service.

Two pitfalls of the gx10 gateway:

- A request under `/upstream/<model>/` of llama-swap starts the model. Read `/running`
  first.
- Do not send a byte-identical chat prompt twice to the llama.cpp model `qwen3.5-9b` (a
  hybrid model). On 2026-09-26 a repeat stopped its server in `ggml_abort`, and
  llama-swap answered HTTP 502. So each chat request of the check holds a new random
  token. Read `ResearchLog.md`, entry of 2026-09-26 "health checks".

## The cache of the model calls

A call to SAM3, to Grounding DINO, or to a VLM that repeats an earlier successful call
reads the answer from `data/cache/models/` and sends no request. Read
[plan 25](docs/plans/25_model-call-cache.md).

```bash
# one Grounding DINO call; the output states "cache": "miss" or "hit"
python3 pipeline/gdino.py <image> --texts "wine bottle, label" [--model mm-gdino-base]
```

- The key is the sha256 of the request fields: the full endpoint URL, the served model
  name, the parameters (for example `threshold`, `max_tokens`, `temperature`), the prompt
  (the nouns, or the VLM messages), and the sha256 of each sent image. The hash is the
  hash of the sent copy, after the resize. The timeout, the retries, the headers, and
  the API key are not in the key.
- One record is one JSON file `data/cache/models/<model>/<key[0:2]>/<key>.json`. It holds the
  request fields, `created`, `ms`, and the answer as the service sent it. It holds no
  image.
- A success alone is stored: HTTP 200 with a JSON body, and for a VLM at least one entry
  in `choices`. An answer with no instance is a success. A failure asks again next time.
- The clients: `derive.Sam3Client` (each SAM3 call of `pipeline/`), `gdino.GdinoClient`,
  `Vlm.ask` of `scripts/cluster_rules.py`, `Backend.ask` of
  `pipeline/wine_identity_vlm.py`, and `call` of `scripts/bench_vlm_models.py`. A VLM
  request with an image URL that is not a data URL is not cached.
- To send a request again, delete its record, or the directory of its model. Do this
  also after the gateway serves a new checkpoint under the same name: the served name is
  in the key, the checkpoint is not.
- Unit tests set `model_cache.ROOT` to a temporary directory.

Barcode scans use the same cache store in `data/cache/models/barcode/`. The key includes the
source file SHA-256, all decoder options, the zxing-cpp version, the Pillow version,
and the scan revision. The record holds decoded codes for the whole image and each
completed tile. A scan with no code is cached too. Decoder failures are not cached.
Each run checks the decoded codes against its current wine lookup. The record holds
no wine match. If a stored unique code no longer identifies one wine, the decoder
continues with the remaining tiles. A complete cache hit does not open the image or
run the decoder. The barcode trace records `cached: true` or `cached: false`.
`Use caches` off and `--no-cache` bypass reads and store the fresh scan results.
Cache writes are atomic, including when four workers scan the same file.

The isolated speed experiments are described in
[the barcode benchmark plan](docs/reports/2026-09-27_barcode-benchmark-plan.md).
Their scripts compare scan passes, cached crop geometry, complete bulk runs, and
sequential recognition with response-cache reads disabled. The HTTP experiment
includes upload and step-view work. Run one measurement at a time and complete the
documented GPU checks before inference. Cached bulk throughput is separate from
the 3-second new-photo demo target. The experiments do not change production profiles.

Read the [final barcode recommendations](docs/reports/2026-09-27_barcode-variants/final-recommendations.md)
and the [final profile comparison](docs/reports/2026-09-27_all-profile-rerun/final-profile-comparison.md).
The authorized queue has 48 successful runs, one run with eight retained errors,
and four local profiles unavailable under the current memory policy.
The external recognizer remains excluded pending separate photo-transfer approval.
The reports keep cached bulk throughput separate from fresh sequential HTTP latency.

The sections below describe the tools of `scripts/`. They read JSON files through
`scripts/common.py`, and they do not start with the present `config.yaml`.

## Configuration

`config.yaml` in the workbench root holds the configuration. `scripts/common.py` reads it.

The file holds two parts. The keys at the top are the same for every dataset. The key
`dataset` holds one entry per photo set.

### The generic keys

| Key | Constant in `common.py` | Meaning |
|---|---|---|
| `rootdir` | `ROOTDIR` | Root directory of the workspace. Every relative path of the configuration is resolved against it. |
| `catalog_file` | `CATALOG_FILE` | Catalogue of the vino-svoe.ru wines, one JSON record per line. Every dataset reads the same catalogue. |
| `patch_dir` | `PATCH_DIR` | Corrected catalogue photos, one file per wine slug. Optional. Every dataset reads the same directory. See [Patched catalogue photos](#patched-catalogue-photos). |
| `alternative_dir` | `ALTERNATIVE_DIR` | Extra catalogue views, zero or more files per wine slug. Optional. Every dataset and the matcher read the same directory. |
| `alternative_label_dir` | `ALTERNATIVE_LABEL_DIR` | Segmented label crops of the extra views. The layout is `<wine_slug>/<source-file-stem>.png`. Optional. |
| `embedding_ignore_file` | `EMBEDDING_IGNORE_FILE` | Images that the reviewer removed from future embedding index builds. Optional. The Embedding page and the matcher share this JSON file. |
| `barcode_file` | `BARCODE_FILE` | Exact product barcodes grouped by wine slug. Optional. The Dataset page and the matcher share this file. |
| `atlas_matches_file` | `ATLAS_MATCHES_FILE` | Automatic Svoe Vino to Drink Atlas Core product matches. Optional. The Dataset page reads this JSONL file. |
| `atlas_bindings_file` | `ATLAS_BINDINGS_FILE` | Manual Svoe Vino to Drink Atlas Core product bindings. Optional. The Dataset page writes this JSONL overlay. |
| `bottle_cropped_dir` | `BOTTLE_CROPPED_DIR` | Catalogue photos without their empty border, one file per wine slug. Optional. Every view shows the crop in place of the catalogue photo. See [Cropped catalogue photos](#cropped-catalogue-photos). |
| `bottle_label_dir` | `BOTTLE_LABEL_DIR` | Label crops of the catalogue photos, one file per wine slug. Optional. See [The picture selector](#the-picture-selector). |
| `bottle_label_box_dir` | `BOTTLE_LABEL_BOX_DIR` | Box crops of the same labels, one file per wine slug. Optional. See [The picture selector](#the-picture-selector). |
| `backends_file` | `BACKENDS_FILE` | The match backends of `scripts/match_run.py`. |
| `pipeline` | `pipelines.load` | The pipelines of the lab: the dialog `Run>` of `/testset` and the filter `Pipeline` of `/runs` show them. The backends are `svoe-vino-ru` and `embedding`; a pipeline of the backend `embedding` names one entry of `embeddings`, and its optional key `views` holds the steps of the test photo. See [The runs of the lab](#the-runs-of-the-lab) and [plan 34](docs/plans/34_pipeline-section.md). |
| `rebuild_embeddings_on_run` | `rebuild_on_run.enabled` | true: before each run of a pipeline of the backend `embedding`, the run updates the index of its embedding (the stale, missing, and failed items). A missing key is false. The lab `config.yaml` sets true. See [The runs of the lab](#the-runs-of-the-lab) and [plan 59](docs/plans/59_rebuild-embeddings-on-run.md). |
| `clusters` | `clusters.config_values` | The thresholds and the limits of the cluster build of an embedding (plan 30). See [The embedding clusters of the lab](#the-embedding-clusters-of-the-lab). |
| `label_rules` | `label_rules.config_values` | The VLM entries, the thinking switches, the picture sizes, the image limit, the token limits, the workers, and the timeouts of `pipeline/build_label_rules.py` (plan 45). See [The label rules of the clusters](#the-label-rules-of-the-clusters). |
| `cluster_rules` | `cluster_rules.CFG` | Not set in the lab `config.yaml`. The VLM entries of the two stages (`vlm`, `rules_vlm`), the picture sizes, the rules file, and the notes file of `scripts/cluster_rules.py`. Plan 43 retired its command `scripts/11_cluster_rules.py`. See [Catalogue clusters (retired)](#catalogue-clusters-retired). |
| `vlm` | `cluster_rules.VLM`, `cluster_rules.RULES_VLM` | The named VLM inferences. See [The VLM inferences](#the-vlm-inferences). |
| `image_description` | `describe_images.settings` | The watcher of the image descriptions: `watch`, `vlm`, `max_side`, `poll_seconds`, `max_attempts`, `workers`; stage 2: `details`, `detail_max_side`; `max_tokens` of the `vlm` entry. See [The image descriptions](#the-image-descriptions) and [The image details](#the-image-details). |

### The keys of one dataset

| Key | Constant in `common.py` | Meaning |
|---|---|---|
| `name` | `DATASET` | The name of the dataset. It MUST be present, and the names MUST differ. |
| `photo_dir` | `PHOTO_DIR` | Photo set. One directory per wine slug. |
| `trash_dir` | `TRASH_DIR` | A deleted photo is moved here, not unlinked. |
| `label_file` | `LABEL_FILE` | Labels of the review tool. |
| `variant_groups_file` | `VARIANT_GROUPS_FILE` | Generated variant groups that the review tool reads. |
| `manual_groups_file` | `MANUAL_GROUPS_FILE` | Variant pairs made by hand in the review tool. |
| `excluded_slugs_file` | `EXCLUDED_SLUGS_FILE` | Excluded slugs. The photos of an excluded slug are not used for benchmarking. |
| `runs_dir` | `RUNS_DIR` | One directory per match run. The runs of one dataset stand apart from the runs of another. |

```yaml
rootdir: /Volumes/T7_2TB/Projects-T7_2TB/drink-atlas-workspace
catalog_file: svoe-wino-hackaton/dataset/derived/official-2026-09-17/catalog.jsonl
patch_dir: svoe-wino-hackaton/dataset/patched-official-2026-09-17
alternative_dir: svoe-wino-hackaton/dataset/derived/additional
alternative_label_dir: svoe-wino-hackaton/dataset/derived/additional-labels
embedding_ignore_file: svoe-vino-matcher/dataset/embedding-ignore.json
barcode_file: svoe-vino-matcher/dataset/code-map.json
atlas_matches_file: svoe-wino-hackaton/dataset/derived/official-2026-09-17/atlas-matches.jsonl
atlas_bindings_file: svoe-wino-hackaton/dataset/derived/official-2026-09-17/atlas-bindings.manual.jsonl
backends_file: svoe-vino-testset/backends.yaml

dataset:
  - name: default
    photo_dir: svoe-vino-testset/dataset/my/photo
    trash_dir: svoe-vino-testset/dataset/my/trash
    label_file: svoe-vino-testset/dataset/my/review-labels.json
    variant_groups_file: svoe-vino-testset/dataset/my/variant-groups.json
    manual_groups_file: svoe-vino-testset/dataset/my/manual-groups.json
    excluded_slugs_file: svoe-vino-testset/dataset/my/excluded-slugs.json
    runs_dir: svoe-vino-testset/runs
```

An absolute value stays as it is. An absent key gives the earlier default path.
`common.rootpath(path)` resolves any other relative path against `rootdir`.

### Choosing a dataset

One entry MUST carry the name `default`. A script that runs with no option uses that
dataset.

```bash
python3 scripts/review_server.py                    # the dataset `default`
python3 scripts/review_server.py --dataset second
python3 scripts/match_run.py --backend official-api --dataset second
```

`scripts/review_server.py` and `scripts/match_run.py` take `--dataset NAME`. Every
other script uses `default`, so a second dataset is reviewed and benchmarked, and it
is not built by the pipeline. `run.json` of every run records the dataset it used.

### The datasets of this project

| Name | Photos | State |
|---|---|---|
| `default` | the photo set that the pipeline built | 2,435 labels of a reviewer |
| `official-real-photos` | 100 official test photos, real-world shots | no label yet |
| `vlmrerank-8b-failed` | 180 positive photos of `default` that `svm-vlmrerank-8b-siglip2-448` missed at rank 1 | frozen copy of the labels of 2026-09-24 |

`official-real-photos` holds the 100 photos of the official test set. They carry **no
ground truth**. Each photo lies in the directory of the wine that the recognizer
answered at rank 1 in the run `2026-09-21T114905Z-svm-siglip2-448-dir-realphoto`, with
the pipeline `svm-siglip2-448`. The scores of those answers run from 0.653 to 0.852,
and the 100 photos fall on 65 wines.

**A place is not a label.** Every photo holds a comment that names the run, the rank
and the score, and holds no label. The filter `holds a comment` lists them all. A
reviewer MUST judge each photo: the key `1` keeps it, and a photo of another wine is
moved with the `move` button or with the sideboard.

`scripts/match_run.py --dataset official-real-photos` answers `the query set is empty`
until the photos hold labels. The query set is built from labels, and a machine
placement is not one.

`vlmrerank-8b-failed` holds the failures of the run
`2026-09-18T195710Z-svm-vlmrerank-8b-siglip2-448-bench`. A photo is in the set when its
label in that run is `positive` and its true slug is not at rank 1. The run holds 184
such photos. 180 photos of 108 wines are in the set. The other 4 photos carry the label
`negative` in `default` now, so they stay out.

The set is a frozen copy. The photo files and their label entries were copied from
`default` on 2026-09-24, without a change. A later label change in `default` does not
reach this set, and a change in this set does not reach `default`. `excluded-slugs.json`,
`variant-groups.json`, and `manual-groups.json` are copies of the files of `default` of
the same day. 9 photos lie on excluded slugs, so a run takes 171 photos.

`selection.json` in the directory of the set records the rule, the source run, and each
of the 184 photos: the query id and the rank of the true slug in the source run, the
answer at rank 1, and the reason when a photo stays out. The review tool and the match
runner do not read this file.

Every photo of the set failed at rank 1 in the source run. R@1 of a run of this set is
therefore the share of those failures that the backend answers correctly now. It is not
the R@1 of `default`.

```bash
python3 scripts/match_run.py --dataset vlmrerank-8b-failed --backend svm-vlmrerank-8b-siglip2-448
python3 scripts/review_server.py --dataset vlmrerank-8b-failed --port 8167 --no-browser
```

The runs of the set stand in `dataset/vlmrerank-8b-failed/runs/`. The review tool on
port 8154 shows the runs of `default` alone. The second command shows the runs of this
set at `http://127.0.0.1:8167/runs`. A run of this set gives new query ids, so join it
with the source run on `image_path`.

`--from-run` of the source run is not the same set. It reads the live labels of
`default`, and it repeats a photo that was `negative` in the source run as well. Read
the ResearchLog entry of 2026-09-24.

An unknown name stops the script and names every dataset of the file.

`common.select_dataset(name)` binds the paths of one dataset. A script that reads a
path at call time needs no more than this call. A script that binds a path of `common`
at import time MUST bind it again after the call; `scripts/review_server.py` does that
in `bind_paths()`.

The file MUST hold the key `dataset`. A file with the paths at the top level is the
old flat shape. Such a file is refused, and the error names the keys that belong in a
dataset entry now.

Every script prints the configuration and the work directory at start:

```
configuration: .../svoe-vino-testset/config.yaml
  dataset             : default
  rootdir             : /Volumes/T7_2TB/Projects-T7_2TB/drink-atlas-workspace
  catalog_file        : .../svoe-wino-hackaton/dataset/derived/official-2026-09-17/catalog.jsonl
  photo_dir           : .../svoe-vino-testset/dataset/my/photo
  ...
work directory: /Volumes/T7_2TB/Projects-T7_2TB/drink-atlas-workspace
```

A path that does not exist gets the mark `(absent)`. The line `dataset` names every
dataset of the file when the file holds more than one.

## Result

| Measure | Value |
|---|---|
| Wines in the catalogue | 2,018 |
| Wines with at least 1 photo | 844 (42%) |
| Wines with 3 or more photos | 386 (19%) |
| Wines with no photo | 1,174 (58%) |
| Photos in `my/` | 2,016 |
| Vision checks made | 25,172 |
| Acceptance rate | 8.6% |

These measures describe the historical test-set build. The canonical test set and its
builder belong to the sibling project `svoe-vino-testset`.

## The `my/` set

The set covers the 2,018 wines in `wines.jsonl` of the `vino-svoe.ru` dump.
Each wine has its own directory `my/<slug>/`.
A file name is `<rank>_conf<NNN>.<ext>`. `NNN` is the model confidence in percent.

The set contains real-world photos only. A studio catalogue render is excluded.
Two filters remove studio renders: a border-whiteness measure, and a vision model judgement.

A wine has fewer than 3 photos when the web holds fewer than 3 usable photos of it.
`REPORT.md`, `report.html`, and `report.csv` list every wine and every gap.

## Manual labelling tool

`scripts/review_server.py` is a browser tool for manual labelling.
It answers one question for each candidate photo: what is this photo for this slug?

```bash
python3 scripts/review_server.py            # opens http://127.0.0.1:8154/
python3 scripts/review_server.py --no-browser --port 8154
```

### The Dataset page

Open `http://127.0.0.1:8154/dataset`. The page shows every record of the configured
`catalog.jsonl`. The unmodified catalogue image stands at the left. The image from
`patch_dir` stands next to it. A record with no patch is a drop target. Drop an image
there, or press the target to choose a file. The page shows the file as a candidate.
It writes no file until you press `Apply`. Press `Cancel` to discard the candidate.

The page shows all records that pass the current filter. It has no pagination. Search
and sort apply to the full list. Images outside the viewport keep native lazy loading.
Click a catalogue image, a patch image, or an alternative photo of the lab server to
open a modal preview over the Dataset page. The page stays at the same scroll position.
The preview puts the image on a checkerboard and draws its boundary. It also shows the
natural pixel dimensions. The arrow buttons and the Left and Right keys move through
images of the same kind in the current filtered and sorted list. For the alternative
photos, each photo is one step, so a wine with three photos takes three steps. The
`open raw image` link opens the image bytes without the preview. The page path names
the open preview: `/dataset/<slug>` for the catalogue image, `/dataset/<slug>/patch` for
the patch image, and `/dataset/<slug>/alternative/<sha256>` for an alternative photo.
The review tool opens an alternative photo in a new tab, with no preview.

On the lab server (port 8168), the image stands in the vertical center of the preview.
Thumbnails of 120 px stand at the bottom of the preview. Each preview of a wine shows
the same thumbnails: `main` (the `main` image of the delivery) and `main · processed`
(its processed file, with the badge `crop` or `seg`). A wine with a patch also gets
`patched` with the badge `PATCH`, and `patched · processed`. Each alternative photo gets
two thumbnails in the order of the upload, for example `alternative LF` and
`alternative LF · processed`. The label holds the button code of the type. A wine with
more than one photo gets the number of the photo in the label, for example
`alternative 2 FF`. A thumbnail with no file reads `none`. The thumbnails keep their
place when the image changes. Click a thumbnail to show that image in the preview. A
thumbnail of another kind, or of another alternative photo, switches the preview fully:
the title, the page path, the position, and the arrows follow that image. The page path
names the kind and the photo, not the choice of the original or the processed file, so
a copied link opens the processed file. The mark on a thumbnail shows the image in view.
For a processed file, `open raw image` opens its original; this includes the processed
patch. The Up and Down keys step to the previous and the next item, as
Left and Right do. The thumbnails stand in one row. A row that is wider than the
preview scrolls sideways, and the marked thumbnail is scrolled into view. At a width of
at most 440 px the thumbnails are 72 px high.

The manual cut of an alternative photo (plan 56, lab server alone): the preview of an
alternative photo has the button `Manual cut`. It opens the editor on the original. A
click adds a point of a polygon, a drag moves a point, and a right-click removes a point.
`Undo` (or Backspace) removes the last point, `Clear` removes all points, and `Cancel`
(or Escape) closes the editor with no change. `Save cut` needs 3 points. The server cuts
the photo along the polygon on a transparent background. The cut replaces the SAM3 cut
of the kind of the current type, and no automatic run replaces it. The card and the
thumbnail show the badge `manual`. `Manual cut` on a photo with a manual cut loads its
polygon for a change. `Remove manual cut` removes it, and SAM3 cuts the photo again. A
type change to the other kind shows the cut of that kind; a change back shows the manual
cut again. The next index build embeds the new cut.

The button `↻` in the bottom left corner of each alternative photo (lab server alone)
segments the photo again. SAM3 gets the photo with no read of the model cache, the fresh
answers replace the cache records, and the server cuts the photo again from them, for the
kind of its current type. Use it to replace a cached SAM3 answer. The button is disabled
on a photo with a manual cut: remove the manual cut in the preview first. When SAM3 does
not answer, the old cut stays. The next index build embeds the new cut.

A record with a patch has a red `Clear` button. On this tool the button stages the
removal; the lab server clears the patch at once. Press
`Apply` to remove the patch, or press `Cancel` to keep it. You can drop a new image on
an existing patch to stage a replacement. An applied replacement or removal moves the
old file into `patch_dir/.trash`, so the old file can be recovered. The page accepts
JPEG, PNG, WebP, GIF, and BMP files up to 20 MB. Apply also moves the old derived crop
and label images into `.trash` directories beside those files. This prevents another
page from showing pixels that came from the old patch.

The right side of each row holds `Alternative photos`. Drop one or more files there,
or press the drop target to choose files. The page shows local candidates. It writes
no file until you press `Apply`. You can mark an active alternative for removal. The
removal also waits for `Apply`. `Cancel` discards all pending changes of that row.

An addition writes `alternative_dir/<slug>/NN_manual.<extension>`. A removal moves the
file to `alternative_dir/.trash/<slug>/`, so the file can be recovered. These pictures
add views of the slug to every photo index. They do not replace the catalogue picture
or its patch. Rebuild the matcher index after a change.

On the lab server (port 8168) the editor works on the database (plan 16). A dropped or
chosen JPEG, PNG, or WebP photo goes to the server at once; the card shows `processing`
until the answer. SAM3 tells a full package from a label close-up: a real bottle neck
inside the largest bottle, or a tall can, is a full package. A clear barcode on the
package (score 0.7 or more, at least 10 % of its width) makes the photo a back view. The
photo gets one of `full_front`, `label_front`, `full_back`, `label_back`, and the
processed file of its kind: the package cut of `derive.py`, or the label cut (the
largest label; the bottle test of `build_labels.py` does not apply in a label
close-up). A full type also gets the label cut of a full photo, for the view `label` of
the Embeddings page; with no label cut, the answer holds a warning. The badge shows
`crop` or `seg`. The buttons
`FF`, `LF`, `FB`, `LB` below each photo change the type at once; the filled button is
the present type. A change between a full type and a label type cuts the photo again; a
change between front and back keeps the cut. `×` and `Apply` delete the row; the file
stays in `data/catalog/images/additional/`. When SAM3 does not answer, the photo gets
`full_front`, no processed file, and a warning. The detection rules were fitted to small
probe sets; their accuracy on real photos is not known, so check the type.

Each additional-photo upload also goes to the existing QR and barcode service at
`QR_SCANNER_ENDPOINT` (plan 76). The request uses `POST /scan` with `engine=auto`.
A detected valid product barcode fills `GTINs` in GTIN-14 form. A detected QR code that
contains an HTTP or HTTPS URL fills `QR URLs`. The response updates both editors on the
same card. An existing value stays once. A non-GTIN barcode and a non-URL QR code are
ignored. If the scanner is not configured or does not answer, the photo stays stored and
the page shows a warning.

The tile `Paste image` follows the drop target. A click on it reads an image from the
clipboard. Chrome asks for the clipboard permission one time; Safari shows its own
`Paste` button. ⌘V on the focused tile works with no permission. The pasted image takes
the same path as a dropped file. With no permission, the tile reads `press ⌘V`.

The information area of each row holds `Barcodes` and a `+` button. Press `+` to add
an input row. Enter one barcode and press the checkmark icon to save it. Press the
cross icon to cancel the new
row. A wine MAY have more than one barcode. The page writes a confirmed value to
`barcode_file`. The barcode matcher reads the same file. The server removes spaces
from the value and refuses a value that already belongs to another slug. Each saved
barcode has a small red `×`. Press it and confirm to remove only that barcode. The
write keeps the QR code and every other field of the wine record.

The `QR URLs` area works in the same way. Press `+`, enter the web page URL encoded
in the QR code, and press the checkmark icon. Each saved URL has `×`, `copy`, and
`open` controls.
The page writes it to the `qr_code` field of `barcode_file`. The matcher normalizes a
scanned QR URL and uses this field for an exact wine identification before visual
matching. One wine MAY have more than one QR URL. One normalized URL cannot belong to
two wines.

Each row also shows `Atlas Core product`. The value is the permanent product UUID.
The `open` link after `copy` opens that product at `http://127.0.0.1:8157/products/`.
The page reads automatic values from `atlas_matches_file`. Press `+` to add a missing
binding. Press `edit` to replace an automatic or manual value. The input has a save
checkmark icon and a cancel cross icon. The checkmark writes the value to
`atlas_bindings_file`. The cross writes nothing. A
manual value replaces the automatic value for the same slug. The automatic file does
not change. Several Svoe Vino slugs MAY bind to one Atlas product UUID.
A paste of a product URL `http(s)://<host>/products/<uuid>` into the input inserts the UUID alone.

The row shows the name, the producer, the category, the region, the colour, the grapes,
the slug, the image match, and the source links. It does not show the wine description.
Open `full catalog.jsonl record` to read the description and every other field. Search
reads every
source field, every saved barcode, every QR URL, and every Atlas product UUID. The
filter can show the 15 patched records alone.

Press `Validate` to open the validation dialog. The dialog describes three read-only
checks. The slug check compares the catalogue with the public wine sitemap. The image
check downloads each source image and compares its SHA-256 with the local file. This
is an exact byte check. A resize URL can re-encode the same visible image. The page
check compares the source image file name with `og:image` on each `wine_slug` page.
The server runs the selected checks in the background. The dialog shows progress and
the problem records. Closing the dialog does not stop the job. Open it again to read
the current progress or the last result.

The review tool alone has `Validate`. The Dataset page of the lab server (8168) hides it,
because the website import covers the checks (owner answer of 2026-09-25T22:54:00+0300).
The page tells the two servers apart by `database_file` of `GET /api/dataset`.

### The Embedding page

Open `http://127.0.0.1:8154/embedding`. The page shows every image prepared for an
embedding build. The left column identifies the wine. The right side is a matrix. The
first column holds the cropped main package image and its segmented label. Each next
column holds one full additional image and its segmented label. Every image cell has a
checkerboard background. A missing prepared image or label is shown as missing. It is
not replaced with another image.

Press `Ignore` to remove one image from future index builds. Press `Use` to restore it.
The page writes the decision to `embedding_ignore_file`. `svoe-vino-matcher` filters
the main photo, main label, additional photo, and additional label independently. The
ignore fingerprint is part of the index file name, so a changed decision cannot reuse
an old index.

### The four labels

| Label | Key | Meaning | Stays in the set |
|---|---|---|---|
| `positive` | `1` | The photo shows the wine of this slug. | Yes, as a positive sample |
| `negative` | `2` | The photo shows a different wine. | Yes, as a negative sample of this slug |
| `unusable` | `3` | No bottle, unreadable, or a duplicate. | No |
| `variant` | `4` | This wine in another bottle: another vintage, another alcohol value, or another package design. | Yes, as a variant sample |

A `variant` label answers the case that `positive` and `negative` both fit badly:
the photo holds the same wine, but the bottle on it is not the bottle of this slug.
Read the section "Variant groups" for the reason that such a case is common.

A `negative` label is a wanted result, not waste. The set needs negative samples,
so a `negative` photo is kept and is marked with its own colour. `unusable` is the
only label that takes a photo out of the set. A photo with no label is not
reviewed yet.

### The NULL wine: a photo that matches no card

A photo can show a wine that no card of the catalogue holds. The label `negative`
does not state this: it states "not this wine" and states nothing about the rest
of the catalogue.

The first row of the table is the NULL wine. It is a virtual wine. It carries a
dashed `NULL` placeholder in place of a bottle photo, and it holds the photos that
match no card of the catalogue. The row stands first, and no filter and no search
take it away, so the drop target is always there.

A photo goes there in four ways:

- drag the card of the photo to the NULL row, as to any other wine row;
- press `0` in the large view;
- right-click the card and press `No match in the catalogue (NULL)`;
- open the move dialog and choose the last entry, `NULL`.

Each way records a move. The file is moved when `apply` runs, exactly as for a move
to another wine. The photo then lies in `<photo_dir>/__null__/`.

**The place is the statement.** A photo under `__null__` needs no label: the
directory already says that no card of the catalogue shows this wine. The card
still takes two labels. `positive` confirms the statement. `unusable` takes the
photo out of the set, as everywhere else. The server refuses `negative` and
`variant` there, because both judge a photo against a wine and NULL is not a wine.
A copy to NULL is refused for the same reason; a photo that matches nothing is
moved, not copied.

These photos are out of the labelling progress of the header. They are counted
apart, as `no match`.

`scripts/match_run.py` reads them as rejection cases. Read
"The photos with no match" in the section "Benchmark".

### The table

The table is built from the catalogue. The filter `all wines` holds one row per
catalogue card, and a wine with no candidate photo is a row with no candidate photo.
The header states that count: `2103 wines, 100 candidate photos`. A directory of the
photo set whose slug the catalogue does not hold is a row as well.

Every other filter asks about photos or about labels. A wine with no photo holds
neither, so it stays out of those lists and the work lists hold the wines that carry
photos alone. The filters that ask about the catalogue itself show every card:
`no candidate photos (catalogue gap)`, the `catalogue photo:` filters,
`failed a check`, `excluded from the benchmark`, and `included in the benchmark`.

The page holds one table row per wine.
Column 1 holds the catalogue bottle photo of the wine from the strapi dump.
The next column holds the candidate photos of `my/<slug>/`.
Each candidate photo has four buttons: `V`, `N`, `x`, and `D`.
The buttons stand in the order of the keys `1`, `2`, `3`, `4`.
The same button again clears the label.
A `copy` button next to the slug puts the slug on the clipboard.
A `move` button under a photo sends the photo to another wine slug.
A `copy` button under a photo gives the photo to another wine slug as well,
and leaves the photo where it is.

The page has thirteen sort orders, twenty-four filters, and a text search.
Sort by `unlabelled first` to continue an unfinished pass.
Sort by `confidence, lowest first` to check the weakest evidence first.
Filter by `has no positive photo` to find the wines that still need a good photo.

The button `export CSV` downloads the current table view in its current order.
The export uses the selected filter, slug scope, search text, sort order, and variant
group scope. One CSV record describes one candidate photo. A wine with no candidate
photo has one record with empty photo fields. The file contains UTF-8 text and protects
text values from spreadsheet formula execution.

#### The text search

The search reads the slug, the name, the producer, the region, and the grapes. It
takes the query apart into words and asks for each word on its own, so the order of
the words does not matter. Four rules make a word meet the text:

1. A word of the text holds the word of the query. `vivandie` finds `Vivandiere`.
2. The accents are folded on both sides. `cotes` finds `Côtes du Don`.
3. A word of four letters or more also meets a word of the text that stands one
   letter away from it. `chardonay` finds `Chardonnay`.
4. A word in Cyrillic is looked for in its Latin form as well, because the slug is
   Latin. The canonical form puts the spellings of the slugs together, so
   `cimlyanskiy`, `tsimlyanskiy`, and `czimlyanskoe` find each other.

The transliteration was checked against the catalogue on 2026-09-17. Of the Cyrillic
words of the wine names, 96.0 percent stand in the slug exactly as the table writes
them, and the rules above reach 1.6 percent more. The rest do not match, because the
slugs do not follow one rule; `b-yu-rne` for `Бюрнье` is an example.

The search does NOT open a scope of its own. It searches the wines that the selected
filter holds. The filter `all wines` holds every catalogue card, so a search there
reaches every wine. A card with no candidate photo stays out of the filters that ask
about photos or about labels, also when it meets the query.

### The note about a wine

The wine column holds a text field under the data of the wine. The field takes a note
about the **whole wine**, not about one photo: what this wine is, how it differs from
its variants, what a later reviewer MUST watch for.

The field is one line high until it holds a text. It opens to a larger box while it
holds a text or while the cursor is in it. The text is saved after a pause of 700 ms
and again when the cursor leaves the field. The table is not drawn again while the
note is saved, so the cursor stays where it is. An empty field removes the note.

A note about a wine is at most 4000 characters. It is stored in the top level map
`wines` of `review-labels.json`, keyed by the slug, apart from the labels:

```json
"wines": {
  "vysokij-bereg-risling-zelenaya-seriya-1": {
    "comment": "Зеленая серия: три варианта, различать по цвету колпачка",
    "ts": "2026-09-15T22:17:41+0300"
  }
}
```

The count `wine_notes` states how many wines hold a note. A note of a wine that `my/`
no longer holds is dropped at start, as a label is.

The comment panel of the large view is a different thing: it belongs to one photo and
one slug. Use the field of the wine column for a statement about the wine itself.

### Variant groups

The catalogue holds one slug per bottle, not one slug per wine. The same wine of
another vintage, or of another alcohol value, gets its own slug and its own
catalogue photo. The two photos then hold the same label design in two colours, so
a reviewer can mix them up. Example:

```
https://vino-svoe.ru/wines/abrau-dyurso-pino-nuar-krasnoe-suhoe-12
https://vino-svoe.ru/wines/abrau-dyurso-pino-nuar-krasnoe-suhoe-125
```

The file that `variant_groups_file` names holds generated groups. The lab reads this file
as an input and does not regenerate it. The groups were built in two ways:

1. Metadata. The same `producer` and the same `name` in `catalog.jsonl`.
   This step is exact and costs nothing. It gives 28 groups over 63 wines of `my/`.
2. Image. A high cosine similarity of the SigLIP2 embeddings of two catalogue bottle
   photos finds pairs that the metadata rule misses.

The review tool reads the variant groups at start. The rows of one group
stand next to each other, whatever the sort, and share one background colour. The
filter `has a similar wine (variant group)` shows only the wines of a group.
A wine with no group keeps the normal background.

#### Grouping two wines by hand

The generated groups miss a pair whose producer or name differs in the catalogue.
The `Group` button under the bottle photo joins the wine to another wine. The
button states the size of the group that the wine is in now.

The tool writes one pair to the file that `manual_groups_file` names. A group is a
connected component over the generated groups and these pairs, so:

- Two wines that are in no group make a new group. Its id starts with `m`.
- A wine that is in no group joins the group of the wine you name. The generated id
  of that group is kept.
- Two wines that are **each already in a group** are refused, with the two group ids
  in the message. A merge of two groups is a larger decision, and one pair cannot
  undo it. Take one wine out of its group first, by hand in the file.
- A pair that names two wines of one group changes nothing and says so.

The generated file and `manual_groups_file` stay separate. A manual pair does not change
the generated file.

A perceptual hash was tried first and was dropped: a bottle photo is mostly bottle,
so the hash of the silhouette hides the label. Read `ResearchLog.md` for the numbers.

### Catalogue clusters (retired)

Plan 43 retired the catalogue clusters on 2026-09-26. The lab reads cluster data only
from `data/catalog/embeddings/<name>/`. See
[The embedding clusters of the lab](#the-embedding-clusters-of-the-lab) and
[plan 43](docs/plans/43_embedding-clusters-only.md).

The files `dataset/catalog-clusters.json`, `dataset/catalog-cluster-rules.json`,
`dataset/catalog-cluster-notes.json`, `scripts/10_clusters.py`,
`scripts/11_cluster_rules.py`, and `scripts/cluster_rules_report.py` are in
`../.attick/svoe-vino-lab/`. The README there keeps the former text of the sections
"Catalogue clusters" and "Label rules of the clusters". Plans 04, 05, and 06 keep the
decisions and the measurements.

`scripts/cluster_rules.py` stays in the lab. The later rule builder of plan 30 can use its
VLM client, its prompts, and its checks. Today only tests import it.

### Moving a photo to another wine slug

A search result often shows the right wine in the wrong bottle, so the photo belongs
to another slug. The `move` button under the photo, and the `m` key in the large
view, open the move dialog.

The dialog offers the five wines that the photo most likely belongs to, each with its
catalogue bottle photo, its name, and its producer. The order is:

1. a member of the variant group of this wine,
2. the same producer,
3. a wine whose name shares words with this wine, then the same grape and the same
   category.

The last entry of the dialog is always `NULL`. It states that no card of the
catalogue shows this wine. Read the section "The NULL wine".

A click on a row records the move. A field below takes any of the 2,103 catalogue
slugs, with completion. `clear the move` removes a recorded move. `Esc` and `cancel`
close the dialog and change nothing.

#### The sideboard

The panel at the right of the page is the sideboard. It is a second way to move a
photo, for the case where the target wine is not yet known.

1. Drag the card of a photo to the panel. The photo leaves the row of its wine and
   waits in the panel. Nothing is sent to the server.
2. Scroll to another wine and drag the card to its row. The tool records the move,
   exactly as the `move` button does.
3. A drop on the row of the wine that the photo comes from puts the photo back.
   The button `put back` on the card does the same.

A card that stands in a wine row may also be dragged straight to another wine row.
The rule is the same for every card.

**Hide it or show it.** The button `sideboard` at the right of the header hides the
panel and shows it again, and so does the key `s` and the `×` in the head of the
panel. The button always states how many photos the panel holds, so a photo is not
forgotten while the panel is hidden. The choice is kept in the browser and holds
over a reload. A drag of a photo card shows the panel again by itself, because the
photo needs a target on the screen.

While the panel is shown, the header and the table keep the room free at the right
edge. While it is hidden, the page uses the whole width.

The sideboard lives in the browser tab. A reload empties it, a second tab does not
see it, and the server never learns about it. A photo in the sideboard keeps its
label until a target is chosen and `apply` runs. `apply` carries out the recorded
moves and states nothing about a photo that still waits in the sideboard.

#### The inbox: a photo that belongs to no wine yet

An image file that lies directly in `my/`, and not in the directory of a wine,
belongs to no wine yet. Put a new photo there when the wine is not known, or when
several photos arrive at one time. The tool lists these files at the start and shows
them in the sideboard with a dashed frame. The file name stands under the picture.

You can also drag image files from the desktop to the sideboard. You can drag an
image from another browser page too. The server copies each picture directly into
`my/` and shows it in the inbox at once. The picture stays unassigned until you drag
its card to a wine row and press `apply`. A reload does not remove an inbox picture.
The server reads the image type from the bytes. It removes path parts and unsafe
characters from the source name. A name that is already in the inbox gets the suffix
`_inbox2`, `_inbox3`, and so on.

1. Drag such a card to the row of the wine that the photo shows. The card then
   states `→ <the slug>` and the header counts one more pending move.
2. The button `clear` on the card, and a drop back on the sideboard, take the target
   away. The photo stays in the inbox.
3. `apply` moves every file that holds a wine into `my/<slug>/`.

The file keeps its name. A name that is already taken in the target directory gets
the suffix `_moved2`, as any other move does. The photo carries **no label**: no
reviewer has judged it against this wine yet, so it must be reviewed. Its comment
states that the photo comes from the inbox.

The target lives in the browser tab, exactly as the rest of the sideboard does. A
reload before `apply` forgets it, and the file stays in the inbox. The label file is
written only when the file lands in the directory of a wine.

A file of the inbox that is not an image, and a directory, are not shown. A move is
refused when the target is not a slug of the catalogue, when a name holds a path
separator, or when the file is gone. The answer of `apply` names every refusal.

#### The move is recorded, not performed

The tool does NOT move the file when the move is recorded. The target is written to
the label file as `reassign_to`, and the card gets a dashed outline. The header then
states `N moves pending` with an `apply` button.

The files move when the reviewer presses `apply` and confirms the operation.

#### What a move does to the annotation

A moved photo loses its **label**. The label judged the photo against the old wine,
so it says nothing about the new wine. The photo MUST be reviewed again.

The **comment** is kept, and one line is put in front of it:

```
до переноса в <new slug> был в <old slug> с таким комментарием:
<the earlier comment>
```

A photo with no comment gets the first line alone. The entry also gets the field
`moved_from`, and `reassign_to` is dropped, so a second run moves nothing.
A file name that is taken in the target directory gets a `_moved2` suffix.

### Copying a photo to a second wine slug

One picture sometimes shows two wines. The same label stands on two bottles of a
variant group, and the photo is a true photo of both. A move is then wrong, because
a move takes the photo away from the first wine. The `copy` button under the photo,
and the `c` key in the large view, open the same dialog in copy mode.

The dialog is the dialog of the move, with the same five suggestions and the same
field for any slug. `clear the copy` removes a recorded copy.

#### The copy is recorded, not performed

The tool does NOT copy the file when the copy is recorded. The target is written to
the label file as `copy_to`, and the card gets a dotted outline. The header then
states `N copies pending` with an `apply` button. The same `apply` button carries out
the copies, the moves, and the deletions.

The copies run before the moves, because a move takes the source file away.

#### What a copy does to the annotation

The source photo does NOT change. It keeps its slug, its label, and its comment.
The field `copy_to` is dropped when the copy is written, so a second run copies
nothing.

The copy is a new candidate photo of the target wine. It carries **no label**,
because a label judges one photo against one wine, and the wine is another one now.
The copy MUST be reviewed against its new wine. Its comment is one line:

```
копия фотографии из <source slug>
```

The entry of the copy also gets the field `copied_from`. The copy keeps the file
name of the source, which holds the confidence value of the source wine. That value
says nothing about the target wine. A file name that is taken in the target
directory gets a `_copy2` suffix.

A photo that carries both a copy and a `delete` mark is deleted and is not copied.

### Validating the photo set

The button `validate` in the header opens a dialog with one line per check. Choose
the checks and press `run`. A check only reads. It writes no file and no label.

The table then shows only the wines that fail at least one check, and it holds that
view until you change the filter. The count line states how many findings were made
and how long the run took. Every photo that a check reports carries a red outline and
a pill at the top left; the pill states how many wines share the picture, and its
tooltip names the other wine and the other file.

`catalog_photo_twin` reports the CATALOGUE photo of a wine and not a candidate photo,
so its finding marks no card. It draws a badge under the bottle photo in the first
column instead. The badge states the tag and the size of the cluster, for example
`same pic ×2`, and its tooltip states the measured distance and names the other wines of
the cluster.

The result lives in the browser tab. A reload empties it, and the filter
`failed a check` then shows nothing until a new run.

#### The checks

| id | What it reports |
|---|---|
| `shared_positive` | One picture that carries the label `positive` under two or more slugs. |
| `photo_too_small` | One photo whose long side is under 256 pixels. |
| `photo_below_model_input` | One photo whose long side is 256 to 447 pixels. |
| `candidate_is_catalog_photo` | One candidate photo that is the catalogue bottle photo of the same wine. |
| `catalog_photo_twin` | Two wines whose CATALOGUE bottle photo is the same picture, or nearly the same. |

`shared_positive` reads every candidate photo and compares the bytes. One picture
cannot show two wines, so such a pair is a defect of the set: either one label is
wrong, or the two catalogue cards are one wine. A pair of wines that are in one
variant group is reported too, and the pill states `same group`, because a variant
group is the same wine in two bottles and the group itself may be wrong.

A re-encoded copy or a resized copy of the same picture has other bytes, and this
check does not find it.

`photo_too_small` and `photo_below_model_input` read the size of every photo that is
not marked `unusable` and not marked for deletion. The matcher runs SigLIP2 with an
input of 448 by 448 pixels, and the preprocessor stretches the whole picture into that
square; it does not keep the aspect ratio and it does not crop.

The two checks read the LONG side of the photo. A photo of a bottle is tall and narrow,
so its short side is small even when the photo is correct: the bottle itself is narrow,
and a wider frame would only hold more background. The long side measures how much of
the picture belongs to the bottle. The short side reported 65 photos of the set of
today against 0 for the long side, and 52 of them were tall product shots such as 142
by 600 pixels.

A photo with a long side under 448 is stretched up and holds no more detail than it
had. A photo with a long side under 256 holds less than the half of the input, and the
text of the label is then too small for the text step and for the OCR step. The pill of
such a photo states its size, for example `280x280`. The two checks never report the
same photo: the band under 256 belongs to the first check alone.

One run reads the 2,543 candidate photos, about 510 MB, and takes about 2.5 seconds.
The result is not cached. The lock is held only long enough to take the rows and the labels, so
a label of the reviewer is not blocked while a check runs.

`candidate_is_catalog_photo` finds a studio render that leaked into the candidate set.
The set holds real-world photos only. The catalogue bottle photo of a wine is a studio
render, and a candidate photo that is that render makes the benchmark easier than
reality: the matcher reads its own catalogue picture back.

The check compares every candidate photo with the bottle photo of the SAME wine. It
never compares across wines. A wine with no catalogue bottle photo is not checked. A
photo marked `unusable` and a photo marked for deletion stay out.

Two pictures count as duplicates when the bytes are equal, and also when the content is
equal and the size differs. The second case reduces each picture to one signature: the
check composites the picture on white, converts it to grey, crops it to the bounding box
of the bottle, and resizes that box to 32 by 32. The measure is the mean absolute
difference of the 1,024 values, on the scale 0 to 255, and the threshold is 10.0.

The crop is the step that finds a copy with another white margin. Without it the same
picture measures as much as 119, because the catalogue render and the copy on a shop page
are cut differently. The crop variant put 304 of the 4,112 pairs of the set of
2026-09-18 under the threshold, against 143 for the plain variant. The check itself
reports 282 photos in 241 wines, because it leaves out the photos that are already
marked `unusable` or marked for deletion.

A made copy of one bottle photo measured as follows: half size as JPEG 0.28, quarter
size as PNG 0.35, the same size at JPEG quality 70 0.18, and a wider white margin 0.12.

`catalog_photo_twin` compares the CATALOGUE bottle photo of every wine with the
catalogue bottle photo of every other wine. It reads no candidate photo of `my/`, so a
label and a candidate photo do not change its result. Two wines that carry one picture
are a defect of the catalogue: the matcher cannot separate them by the image, and one of
the two cards names the wrong bottle.

The check reads the whole catalogue, including a card that has no directory in `my/`.
The filter `failed a check` shows such a card, so both halves of a cluster reach the
table. On the catalogue of 2026-09-17 the check reads 2,093 cards, which is 2,189,278
pairs.

The compare runs in two stages. Stage one reads the grey 32 by 32 signature of
`candidate_is_catalog_photo` for every picture and measures every pair with numpy in
about 3 seconds; it names the pairs under 3.0 of 255. Stage two reads a COLOUR 128 by
128 signature of the named pictures alone and measures again in about 8 seconds. The
whole run takes about 43 seconds.

Stage two is needed. The grey 32 by 32 signature holds no colour and no text of the
label, so two DIFFERENT wines of one producer line measure as little as 0.09 of 255
under it, which is the band of a true duplicate. Under the colour 128 by 128 signature a
true duplicate measures 0.00 and the nearest different picture measures 0.18. The
measurement is in `ResearchLog.md`.

A finding reports the whole cluster and not the pair. Three wines that carry one picture
give one finding of three slugs. A finding carries one of two tags:

| tag | distance | What it means |
|---|---|---|
| `same pic` | under 0.05 | The two cards carry one picture. This is a defect. |
| `twin` | 0.05 to 1.0 | The two pictures are different photographs of a bottle that looks nearly the same. This is not a defect by itself. |

A `twin` cluster is a producer line: 8 wines of `fanagoriya-primum-alveus`, 6 of
`chteau-le-grand-vostock ... reserve`. The reviewer judges such a cluster, and the pair
is a candidate for a variant group. The badge of `same pic` takes the colour of a defect
and the badge of `twin` takes the colour of a variant.

On the catalogue of 2026-09-17 the check reports 70 findings over 162 wines: 27 clusters
with the tag `same pic` over 55 wines, and 43 clusters with the tag `twin`.

The check needs numpy. Without it one finding states that numpy is not installed, and
the server does not fail.

The check has two limits. The measure has no sharp edge between the two classes, so a
copy over the threshold is not reported and the check misses it. The check also
composites a transparent picture on WHITE, so a render that was flattened on another
colour measures far over the threshold and is not found. A shop page nearly always uses
white. `ResearchLog.md` holds the measurement and the choice of the threshold.

The run reads the pixels of about 6,000 files and takes about 50 seconds. The older
checks take about 3 seconds. The check decodes in 8 threads.

#### Adding a check

The checks live in `scripts/review_server.py`, above `plan_deletes`. Write a function
`check_<name>(rows, labels, groups, catalog)` that answers a list of findings, and name
it in `CHECKS` with an `id`, a `title`, and a `help` text. A finding MUST hold `check`
and `why`, and it SHOULD hold `photos` (a list of `{slug, file}`) or `slugs`. It MAY
hold `tag`, the text of the pill. The dialog reads `GET /api/checks`, so a new check
reaches the page with no change of the page.

### Adding a photo by drag and drop

Drag an image file from the file manager onto the row of a wine, and the tool adds
the file to `my/<slug>/`. The row is outlined while the file is over it. Several
files at a time are accepted, and a file that is not an image is refused.

A hint at the bottom of the window states the two ways to drop while a file is over
the page:

- **On the row of a wine.** The file goes to that wine at once.
- **Anywhere beside the table.** A dialog asks for the wine. Type a part of a slug, a
  name, or a producer, and the dialog offers five wines with their bottle photo. A
  click on one adds the files and scrolls the table to that wine. The field also
  completes from the slugs of `my/`.

The table is NOT drawn again after a drop. Only the row of the wine is brought up to
date: its cards, its photo count, and its mark. A row therefore stays where it is,
also when it no longer matches the selected filter. Under the filter `no candidate
photos (catalogue gap)` the wine would leave the table as soon as its first photo
lands, and the next row would jump under the pointer. Reload the page to filter
again.

A drop on a row works for every wine of the table, also for a wine with no candidate
photo. Such a wine is a card of the catalogue with no directory in `my/`. The write
makes the directory, and the wine becomes a wine of the review set: it leaves the
filter `no candidate photos (catalogue gap)` and enters the counters.

The dialog for a drop beside the table names only the wines that already have a
directory in `my/`. To give a first photo to a wine of the catalogue, drop the file
on its row.

#### From another browser tab

A picture dragged from another browser tab, such as a shop page or an image search,
is accepted the same way, on a row or beside the table.

Such a drag carries no file. It carries the address of the picture, as
`text/uri-list`, as an `<img>` element in `text/html`, or as plain text. The browser
may not read the bytes of another site, so the **server** fetches the address through
`POST /api/fetch-image`. A `data:` address is decoded without a request.

The media type comes from the first bytes of the file, not from the answer of the
host. Several picture hosts send no `Content-Type` or a wrong one; the first bytes
are the only reliable statement. An address that does not answer with a picture is
refused, and the reason names what the host sent.

The server refuses an address that is not `http` or `https`, and an address whose
host resolves to a loopback, private, link-local, reserved, or multicast address. A
dragged link MUST NOT reach a service of this machine or of the local network.

The request carries a browser user agent string, because many picture hosts refuse a
plain Python agent. A host can still refuse the request; the tool then states the
error and adds nothing.

The new file is named `<next number>_manual.<extension>`, so it sorts after the
photos that the pipeline found and is easy to tell apart. It carries no `conf`
value. A file is at most 20 MB, and the type MUST be JPEG, PNG, WebP, GIF, or BMP.

### The large view

A click on a candidate photo opens the large view. The large view shows two images
side by side: the catalogue bottle at the left, the candidate photo at the right.
The two images stay next to each other in the middle, also on a wide monitor.
A click on the catalogue bottle in the table opens the same view at the first photo.
A click on a large image does not close the view.

A wine with no candidate photo opens too. The view then shows the catalogue bottle
alone, the candidate side stays empty, and the badge states `no candidate photo for
this wine`. This is the state of every wine of the filter `no candidate photos
(catalogue gap)`. The keys `1` to `4` and `m` do nothing there, because there is no
photo to label and no photo to move. The comment field is closed for the same
reason: a comment belongs to a photo. A wine with neither a candidate photo nor a
catalogue bottle does not open, and `Down` and `Up` step over it.
A click on the background closes the view. `Esc` also closes it.

The large view holds the keyboard. The keys are:

| Key | Work |
|---|---|
| `Right` / `Left` | Go to the next or the previous photo of this wine. The keys stop at the ends. |
| `Down` / `Up` | Go to the next or the previous wine, at its first photo. |
| `1` | Label `positive`. `1` again clears the label. |
| `2` | Label `negative`. `2` again clears the label. |
| `3` | Label `unusable`. `3` again clears the label. |
| `4` | Label `variant`, this wine in another design. `4` again clears the label. |
| `m` | Move this photo to another wine slug. |
| `Esc` | Close the large view. |

The `Up` and `Down` keys follow the order that the table shows, so the sort and the
filter also control the keyboard pass. Sort by `unlabelled first`, open the first
photo, then work with `1`, `2`, `3`, `Right`, and `Down` only.
A badge at the top of the large view states the label of the photo on screen.
The caption under the candidate photo states the place in the wine and the label
progress of the wine.
The table row behind the large view scrolls with the keys, so the place is held when
the view closes.

### The comment panel

The large view holds a panel at the right. The panel takes a free text comment about
one photo and one wine slug: what is wrong, what is unclear, what the next reviewer
MUST check. The text belongs to the pair, not to the wine, so every photo has its own
comment.

The text is saved as it is typed, after a pause of 600 ms. A move to another photo,
a close of the view, and a close of the page flush the pending text first. The state
line under the field states `typing...`, `saving...`, `saved`, or the error.
The `clear` button empties the field and removes the comment.

A photo with a comment carries a round badge in the top right corner of its card in
the table. Hold the pointer over the badge to read the whole text; the panel that
opens keeps the line breaks and scrolls when the text is long. The row states
`N noted`.
The filter `holds a comment` lists the wines that hold a comment.

While the cursor is in the field, the keys `1` to `4`, the arrows, and `m` do not
act. Press `Esc` once to leave the field, and `Esc` again to close the large view.

A comment is at most 4000 characters. The tool refuses a longer text and writes
nothing.

### The address of one photo

The large view writes its place into the address of the page:

```
http://127.0.0.1:8154/#<slug>/<photo file name>
http://127.0.0.1:8154/#agora-saperavi/02_conf095.jpg
```

Copy the address to point another person at one photo. Open such an address and the
tool opens the large view at that photo. The filter and the search are cleared when
the wine is not in the current view, so a pasted address always opens.
The address is written with `replaceState`, so the arrow keys do not fill the history.

### The label file

Every click is written to `review-labels.json` at once. The format is:

```json
{
  "version": 2,
  "updated": "2026-09-15T14:14:12+0300",
  "counts": { "positive": 1, "negative": 1, "unusable": 0, "variant": 0,
              "labelled": 2, "reassigned": 1, "commented": 1, "wine_notes": 1 },
  "wines": { "<slug>": { "comment": "a note about the whole wine", "ts": "..." } },
  "labels": {
    "<slug>": {
      "<photo file name>": { "label": "positive", "ts": "..." },
      "<other photo>": { "label": "negative", "reassign_to": "<other slug>",
                         "comment": "same label, but the capsule differs",
                         "ts": "..." }
    }
  }
}
```

The tool reads the file again at the next start, so a pass can stop and continue.
A label whose photo is no longer in `my/` is dropped at start.

The tool reads the slug-to-bottle-photo map from the file that `catalog_file` names in
`config.yaml`. The default value is
`svoe-wino-hackaton/dataset/derived/official-2026-09-17/catalog.jsonl`.
4 of the 814 wines have no catalogue bottle photo. The row states the reason.
`patch_dir` corrects that map; see [Patched catalogue photos](#patched-catalogue-photos).

The tool uses the Python standard library and `PyYAML`. `PyYAML` reads `config.yaml`.

## Patched catalogue photos

Some cards of the `vino-svoe.ru` catalogue carry a poor photo, and some carry the photo
of a DIFFERENT wine. `patch_dir` of `config.yaml` names a directory of corrected
photos. The directory holds one file per wine slug:

```
svoe-wino-hackaton/dataset/patched-official-2026-09-17/
  README.md                       not a patch; the extension is not an image type
  bukovinka.webp                  the corrected photo of the card `bukovinka`
  czitronnyj-magaracha.png        a `.png` may replace a `.webp`
  kaberne-sovinon-2.webp
  oleg.webp
  risling-1.webp
  rubin-golodrigi.webp
  vinodelnya-vedernikov-...-125.webp
```

The name before the extension is the slug. The extension states the file type alone: a
`.png` patch replaces a `.webp` photo, because the match is made on the slug. A file
whose extension is not an image type is not a patch, so a `README.md` beside the patches
is ignored.

A patch REPLACES the catalogue photo of that slug. It does not stand beside it, because a wrong photo is not a second view of the
wine. The catalogue file is never rewritten; the patch is a layer above it.

What the tool does with a patch:

- `GET /img/bottle` serves the patch, and never the photo of the catalogue record.
- Every record that carries a bottle also carries the field `patched`.
- `GET /api/patched` lists the slugs that take a patch.
- Every view that shows a catalogue bottle draws the mark `patched` in the top right
  corner of the image. The pickers show a 34 px thumbnail, where the mark is a dot of
  the same colour and the tooltip states the meaning.
- The tool reads the directory again at every `GET /api/reload`, so a new patch file
  needs no restart.
- The Dataset page can add, replace, and remove these files. It stages one change in
  the browser and writes the change only when the reviewer presses `Apply`. A replaced
  or removed patch moves to `.trash/` in this directory. Existing derived crop and
  label files for the slug move to `.trash/` in their directories. Rebuild these files
  after the patch change.

`svoe-vino-matcher/config.yaml` read the same directory under the same key until
2026-09-23. It now indexes the cropped pictures of `dataset.image_dir`, and those
pictures hold the patches. A new or edited patch therefore needs a new run of
`svoe-wino-hackaton/scripts/build_cropped.py`. See
[Cropped catalogue photos](#cropped-catalogue-photos).

An absent `patch_dir` gives no patch. A configured directory that is not on disk makes
the review tool print a warning and start with no patch: a typo in the path MUST NOT
pass without a word, and it MUST NOT stop the work of the reviewer either. The matcher
is stricter and refuses to load such a configuration, because it writes an index.

## Cropped catalogue photos

Many catalogue photos have an empty border around the package. The border is
transparent on most photos, and white on a photo with no alpha channel.
`svoe-wino-hackaton/scripts/build_cropped.py` cuts the border away and writes one file
per wine slug, `<slug>.png`. It cuts the patch when the wine has one. The crop holds
the pixels of the source and nothing else. `bottle_cropped_dir` of `config.yaml` names
the directory.

The crop is the picture that the tool shows:

- `GET /img/bottle` serves the crop. The field `bottle_path` of the agent API names it.
- The pixel checks `candidate_is_catalog_photo` and `catalog_photo_twin` still read the
  catalogue photo of the delivery. They look for a copy of that photo, and a copy
  carries the border.

`common.catalogue_picture` states the order: the crop, then the patch, then the photo
of the catalogue record. A wine with no crop keeps its patch or its photo.

The mark `patched` does not change. It states that the picture comes from a patch,
and a crop of a patch is still that patch.

A patch that changed after its crop wins over the crop, because such a crop was cut
from the picture before the correction. The review tool prints a warning at start
for each such patch. Run `svoe-wino-hackaton/scripts/build_cropped.py` again to crop
the new patch.

An absent `bottle_cropped_dir` shows the photos with their border. A configured
directory that is not on disk makes the review tool print a warning and start without
crops. `svoe-vino-matcher/config.yaml` indexes the same directory as
`dataset.image_dir`.

## The picture selector

Column 1 of the table shows the catalogue picture of the wine. The control `Image` in
the tool bar states WHICH picture:

| Value | Picture | Directory |
| --- | --- | --- |
| `package` | the crop of the catalogue photo, or the patch, or the catalogue photo | `bottle_cropped_dir`, `patch_dir`, `catalog_file` |
| `label` | the label cut out of that photo, as RGBA with the mask in the alpha channel | `bottle_label_dir` |
| `label box` | the bounding box of the label alone, as RGB | `bottle_label_box_dir` |

`svoe-wino-hackaton/scripts/build_labels.py` writes the two crop directories. It reads
the same patch directory, so the label of a patched wine is cut out of the patch.

A label crop does NOT replace the catalogue photo. A patch replaces a wrong photo; a
crop is a second view of the SAME photo. This is why the tool holds a selector for the
crops and no selector for the patches.

What the tool does with the crops:

- `GET /img/bottle?slug=<slug>&kind=label` serves the label crop, and `kind=labelbox`
  serves the box crop. No `kind`, or an unknown `kind`, serves the package picture.
- A wine with no crop of the asked kind answers with its package picture. The page draws
  the mark `no label` in the BOTTOM right corner of such a picture, so the mark stands
  beside the `patched` mark and not over it.
- Every record carries `has_label` and `has_label_box`. The wine record also carries
  `label_path` and `label_box_path`. An agent SHOULD read the path and open the file.
- The control travels in the query string as `img`, beside `filter`, `sort` and `slugs`.
  `/?img=label` opens the table on the label crops.
- The control is hidden when no wine has a crop. Without the two directories every wine
  would fall back to its package picture, and the choice would say nothing.
- A label crop is RGBA. The page puts it on white, so a white label edge stays visible in
  the dark theme. A reader that drops the alpha channel sees the label on white as well,
  because the colour under the transparent part is white.
- The tool reads both directories again at every `GET /api/reload`, so a new build of the
  crops needs no restart.

A configured directory that is not on disk makes the tool print a warning and start with
no crop of that kind.

## Excluded slugs

Some slugs of the `vino-svoe.ru` catalogue hold an error. The most frequent error is a
wrong bottle photo: the card shows a different wine. The bottle photo is the reference
of the benchmark, so a wrong reference shifts the metrics of the whole test set.

Such a slug is excluded. `excluded-slugs.json` names every excluded slug and states the
error. The photos of an excluded slug stay on the disk, but they MUST NOT be used for
benchmarking.

The review tool holds an `Exclude` button under the bottle photo of each row. An
excluded row is red. The control `Slugs` filters the table to `all`, `included`, or
`excluded`. The control `Show` holds the same scope in its list, as
`excluded from the benchmark` and `included in the benchmark`. The two controls
state the same thing, and one of them is enough. A contradiction between them, such
as `Show` on `excluded` with `Slugs` on `included`, gives an empty table, and the
count line states the reason.

Read `docs/excluded-slugs.md` for the format of the file and for the rule of a consumer.

## The match runner

`scripts/match_run.py` sends every annotated photo to one recognizer and writes the
answer into `runs/<UTC time>-<backend>/`. One directory is one run, so two backends or
two versions of one backend are compared side by side.

```bash
python3 scripts/match_run.py --list-backends
python3 scripts/match_run.py --backend official-api
python3 scripts/match_run.py --backend organizers --limit 50 --label smoke
python3 scripts/match_run.py --dry-run          # build the manifests, call nothing

# repeat only what failed in an earlier run
python3 scripts/match_run.py --backend my-service --from-run runs/<run id>
python3 scripts/match_run.py --backend my-service --from-run runs/<run id> --rerun-depth 10

# a plain directory of photos, with no ground truth
python3 scripts/match_run.py --backend svm-siglip2-448 --photos-dir ~/Downloads/photos
```

`--photos-dir DIR` replaces the query set with the image files of one directory. The walk
is recursive. Such a directory holds no ground truth, so every photo carries the label
`unlabelled`, the run states no correctness, and every share of `metrics.json` is empty.
The run records the candidates, the scores, the latency, and the errors. The page `/runs`
shows the photos and the answers, and it names the counts that need no truth. Use the
mode to see what a backend answers for photos that the project holds no label for.
`--photos-dir` MUST NOT be used with `--from-run`, `--only`, or `--variants`.

`--from-run` asks the backend only about the photos that failed before, so the answer to
"did the change help?" costs one request per failure instead of one per photo.
`--rerun-depth K` states how many candidates count as an answer: 1 repeats every photo
that was not correct at rank 1, and 10 repeats every photo whose true slug was not in the
first 10. The shares of such a run cover the repeated photos only, and every file of the
run states it.

The query set holds 979 `positive` photos and 364 `negative` photos. A `positive` photo
is correct when the recognizer answers with its slug. A `negative` photo shows a
different wine, so the recognizer is wrong when that slug stands at rank 1. `variant`
photos stay out unless `--variants` asks for them. A photo of an excluded slug never
enters the set.

### The photos with no match

A photo of `<photo_dir>/__null__/` matches no card of the catalogue. The review tool
writes it there; read the section "The NULL wine". Such a photo enters the query set
with the label `no_match`, with no truth, and it needs no label of its own.

A `no_match` photo is a rejection case. No answer is the only correct outcome, and
every card that comes back at rank 1 is a false match. `metrics.json` holds the block
`no_match` with `n`, `rejected`, `false_match_at_1`, `rejection_rate`, and the score
that a false match reached. `summary.md` holds the same numbers under "Photos with no
match in the catalogue". The score is the useful number for a threshold: a backend
that MUST refuse such a photo needs a threshold above that value.

`--only no_match` runs these photos alone. `--only positive` and `--only negative`
leave them out. The slug `__null__` in `excluded-slugs.json` takes every one of them
out of the benchmark.

The page `/runs` holds two filters for them: `no match: every photo that matches no
card` and `no match: the backend answered a card anyway`.

The run directory holds `predictions.jsonl` in the exact format of the organizers, so
the same run serves as the submission. It also holds `results.jsonl` with every
candidate and its score, `metrics.json` with R@1, R@5, R@10, the rank histogram, and the
negative outcomes, and `summary.md` for a human.

`backends.yaml` defines a backend. A token MUST NOT stand in that file: a header value
`env:NAME` is read from the environment.

The navigation at the top right of the header holds `Review` for `/` and `Runs` for
`/runs`. Both pages hold it.

The metrics follow the specification of the task: the share of the matches against its
target of 90 to 100 percent, the F1 of the top-1 and of the top-5 cards, the share of
the answers inside the SLA of 3 seconds, the gap between the first and the second
candidate, and the near-duplicate errors, which the specification names as the main
source of the mistakes.

The review tool shows the runs at `http://127.0.0.1:8154/runs`: the table of the runs,
the metrics of the selected run, and one row per photo with the candidates that came
back. A click on a column sorts the runs; the control `Sort` orders the photos, for
example the most wrong first. The expected wine carries a green border, and the wine that a negative photo MUST
NOT match carries a red one. A dashed green border marks the true wine of a negative
photo, which the server reads from a byte-equal `positive` photo of the same run. The
review tool shows no cluster frame: plan 43 retired the catalogue clusters and the page
`/clusters` of the review tool. The
filter `negative_above_positive` selects the negative photos whose forbidden wine stands
above that true wine, and the filter `twin_conflict` selects the photos that a defect of
the set marks.

A click on the matched photo opens the large view and reads its model inputs. A strip
under the large image shows each derived image that the matcher passed to an embedding
model. It also shows each query image that the matcher passed to a VLM. A `VLM` badge
marks these images. A click on a strip image shows it as the large image. The page reads
the inputs only after the user opens the matched photo. A barcode or QR answer states
that no embedding model ran.

A run of the backend `svm-label-gw-cluster-rules` holds the answer of the VLM rule step
in the `explain` record of each card that the step touched. When the step acted on a
photo, a box `VLM` stands under the frame of the top cluster: the mode, the cluster id,
the time of the call or `from the cache`, each question with the answer of the VLM (or
the verdict), the score of each card of the window, and whether the answer moved a card
to rank 1. A run that did not record the questions takes their text from the current
rule of the cluster, and the box states that. The filters `rule step: the VLM answered
for the top cluster` and `rule step: the VLM answer changed the order` select these
rows. Read `docs/plans/05_cluster-label-rules.md`.

Read `docs/match-runner.md` for every file, every field, and every option.

## The agent API

`scripts/review_server.py` answers an HTTP API under `/api/v1/` for an agent, such as
Claude Code. Read `docs/API.md` for every route and every field.

`docs/openapi.yaml` holds the same contract in machine-readable form, for every route
of the server. Open `http://127.0.0.1:8154/docs` in a browser to read it, or fetch
`/openapi.yaml` or `/openapi.json` to feed a client generator.

The idea: an agent walks the wines that hold no confirmed photo, searches the web for
a real-world photo, checks it against the catalogue bottle, and writes a **proposal**.
The reviewer confirms the proposals later, in the same page.

```bash
curl -s "http://127.0.0.1:8154/api/v1/wines?filter=needs_positive&limit=1"
curl -s "http://127.0.0.1:8154/api/v1/wine/<slug>"
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"slug":"<slug>","url":"<picture>","proposed":"positive","confidence":0.9,
       "source_url":"<page>","comment":"the label and the capsule match"}' \
  http://127.0.0.1:8154/api/v1/propose
```

An agent MUST NOT write a label. A proposal is not counted in `labelled`. The card of
a proposed photo has a dashed border and a tag with the confidence, and the filter
`holds a photo proposed by an agent` lists them. The reviewer answers with the keys
`1` to `4`, and only then the photo holds a label.

The skill `wine-hunt` in `.claude/skills/wine-hunt/` holds the working instructions
for the agent: which queries to use, what to compare, and when NOT to propose.

## Reports

- `report.html` — thumbnails for visual review. Open it in a browser.
- `REPORT.md` — the same table in Markdown.
- `report.csv` — machine-readable form.

Rows are sorted with the weakest evidence first: wines with fewer than 3 photos,
then the lowest confidence, then the average confidence.

## Search engines

Yandex Images is the primary engine. It answers about 30 results per query.
Three queries run per wine: `site:irecommend.ru`, `site:otzovik.com`, and a plain review query.
DuckDuckGo is secondary. It rate-limits this host quickly and disables itself for 15 minutes.

Search results are noisy. A query for one wine often returns a different wine of the same
grape or the same producer. Stage 4 is the filter that removes them.

## Working data location

`work/raw` and `work/thumbs` are symbolic links to `/Volumes/Storage/svoe-vino-testset-work/`.
The volume `/Volumes/T7_2TB` was full when the set was built.
The database keeps absolute paths, so the links MUST stay in place.

## The `api_rank` column

`report.csv` carries `imgN_api_rank` for each photo. It is the rank of the expected slug
in the answer of the official recognizer, and `0` means the recognizer missed the wine.
Use it to split easy photos from hard photos. It is not a correctness label:
the recognizer misses many photos that are correct but hard.
