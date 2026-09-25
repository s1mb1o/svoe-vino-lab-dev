# svoe-vino-testset

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
- `pipeline/` holds the lab database tools. `data/lab.sqlite3` is the lab database.
  `data/images/` holds the images of the wines. Git ignores `data/`.

## The lab database

One SQLite database holds the lab state of one catalogue delivery. The database is filled
one step at a time. Read [plan 07](docs/plans/07_sqlite-lab-database.md) for the steps,
the tables, and the rules. Read [decision record 01](docs/decisions/01_sqlite-lab-database.md)
for the reasons.

```bash
# step 1: create the database and its tables
python3 pipeline/labdb.py data/lab.sqlite3

# step 2: import the Strapi CSV into wine_catalog; the first import adds every wine
python3 pipeline/import_catalog.py --db data/lab.sqlite3 \
    ../svoe-wino-hackaton/dataset/official-2026-09-17/strapi_output0709.csv
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
`svoe-vino-lab/data/lab.sqlite3`. The lab server opens the database
read-only. The Dataset, Embeddings, Testset (`/testset`), and Runs pages work. `/`
redirects to `/dataset`. Clusters is disabled for now: it answers a notice page. The
navigation order is `Dataset`, `Embeddings`, `Clusters`, `Testset`, `Runs`. Each card of the Dataset page holds
the buttons `Disable` / `Enable`, `Remove`, and `Restore` below the catalogue image. The
`main` image of a `Disabled` wine is gray on the card. The browser draws it with a CSS
filter; the file does not change. The patch and the alternative photos keep their
colours. The filter `State` shows `All (except Removed)`, `Disabled`, `Removed`, or `Favorites`
(each favorite wine, also a removed one; the lab server alone). The lab server writes
these data alone: the state of a wine; its GTINs and QR URLs (`wine_code`, plan 11); its
manual Atlas Core binding (`wine_atlas_binding`, plan 15); its comments (`wine_comment`,
plan 17); the favorite mark (`wine_favorite`, plan 19); a wine added by hand, with a slug
that starts with `__` (plan 20); its patch (the `main_patched` row, plan 14) and its
alternative photos (the types `full_front`, `label_front`, `full_back`, `label_back`,
plan 16), each with its files and their rows of `image` and `image_derivative`; and the
data of the website import of plan 21. The card images come from the table
`wine_image`: the `main` image at the left and the patch in the patch slot next to it,
side by side. Each slot shows the processed file with its badge `crop` or `seg`. A
`crop` whose box is the whole image cut nothing: the slot shows the original and no
badge. The server sends the files of `data/images/` at
`/images/<folder>/<sha256>.<extension>`. `Sort` can order the cards by the pixel count
of the image. The slug of a card links to the page of the wine on vino-svoe.ru. The lab
server uses port 8168.
The review tool of `svoe-vino-testset` keeps port 8154, so both can run.

```bash
# step 4: find the main image of each wine in the Strapi uploads folder, offline
python3 pipeline/seed_images.py --db data/lab.sqlite3 \
    ../svoe-wino-hackaton/dataset/official-2026-09-17/prod-svoe-vino-strapi/prod-svoe-vino/strapi/uploads
```

The table `wine_image` holds the images of a wine and the type of each image: `main`,
`main_patched`, `full_front`, `label_front`, `full_back`, and `label_back` (the names of
schema 012). A reader such as the Embeddings page uses a `main_patched` image in place of
the `main` image of the same wine; the card of the Dataset page shows the two side by
side. `image_derivative` holds one processed file for each original and kind of cut
(`package` or `label`, schema 017). The files are in `data/images/`:
`main/`, `patched/`, and `additional/`, each file as `<sha256>.<extension>`. The folder
`testset/` holds the photos of the test sets (schema 016, see "later: the test sets"
below).
`seed_images.py` fills `main`. It matches `csv_photo_name` with the upload file names
by the rule of `build_catalog.py`, and it reads no internet resource. A wine with no
match gets a console message. Read [plan 08](docs/plans/08_seed-images.md).

The table `image` holds one row for each stored file. Each import also processes each
image it stores, with `pipeline/derive.py`: an image with a transparent background loses
its border (`crop`), and SAM3 on gx10 segments the bottle of an image with no
transparent background (`seg`). The processed file is a PNG in `data/images/cropped/`.
The table `image_derivative` links it to its original by the sha256. The Dataset page
shows the processed image with the badge `crop` or `seg`. When SAM3 does not answer,
the image stays unprocessed, and the next import asks again. The option `--sam3 <URL>`
names another SAM3 service. Read [plan 09](docs/plans/09_image-processing.md).

```bash
# step 5: store the patched main images; the file name is the wine slug
python3 pipeline/seed_patched.py --db data/lab.sqlite3 \
    ../svoe-wino-hackaton/dataset/patched-official-2026-09-17
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
`Processing…` while the server stores the file in `data/images/patched/`, writes the
`main_patched` row, and processes the file as `seed_patched.py` does. SAM3 can take up
to about two minutes. When SAM3 does not answer, the patch is stored with no processed
file, and the page shows a warning. A patch applied by mistake is removed with `Remove`
and `Apply`: this deletes the row; the file stays in the store. The patch `Remove`
button has the size of the `Remove` button of the main image and stands at the right.
The editor does not write the patch folder.

```bash
# step 6: the GTINs and the QR URLs of the code map of the matcher
python3 pipeline/seed_codes.py --db data/lab.sqlite3 \
    ../svoe-vino-matcher/dataset/code-map.json
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
`/api/dataset-gtin` and `/api/dataset-qr-url`. A save redraws its own card alone. The
page checks the check digit while you type, and the server checks it again. The editor
`Barcodes` shows only on the review tool, which sends `barcode_file`. `svoe-vino-matcher`
still reads `code-map.json`; it does not see the codes of the table. Read
[plan 11](docs/plans/11_wine-codes.md).

```bash
# step 7: the Atlas Core product of each wine, from the files of svoe-wino-hackaton
D=../svoe-wino-hackaton/dataset/derived/official-2026-09-17
python3 pipeline/seed_atlas_bindings.py --db data/lab.sqlite3 \
    --matches $D/atlas-matches.jsonl --manual $D/atlas-bindings.manual.jsonl
```

The table `wine_atlas_binding` (schema 009) links a wine to a Drink Atlas Core product
UUID. A wine has at most one `automatic` row, from `match_atlas.py`, and one `manual`
row, from a person. The manual row wins. One product MAY belong to more than one wine.
The seed adds rows alone. A file row whose UUID differs from the stored row prints
`differs: <slug> <source>` and is not applied. Like `seed_codes.py`, the seed refuses a
table that already holds rows unless `--force` is given. On 2026-09-25 the seed added 364
automatic rows and 3 manual rows. The editor `Atlas Core product` of the Dataset page
sets a manual binding with `POST /api/dataset-atlas-binding`. The red `×` of a manual
binding removes it with `DELETE`; the wine then shows its automatic binding, or `not
bound`. The lab does not write the JSONL files, so the review tool does not see a lab
binding. Read [plan 15](docs/plans/15_atlas-binding.md).

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

The button `Add wine` of the Dataset page, before `Validate`, adds a wine by hand. The
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
python3 pipeline/import_website.py --db data/lab.sqlite3
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
needs a choice for each conflict, and it runs `import_website.py --apply` on the same run
directory. A choice `website` writes the website value, or replaces the `main` image; the
old file stays in the store. A choice `database` and a cleared checkbox are refusals in
the table `website_refusal` (schema 015). A later run, also of the CLI, skips a refusal
while the website keeps the refused value. Each choice writes a short comment of the
source `script`. The compare reuses one HTTPS connection; a full run takes about 10
minutes. Each write also sets `wine_catalog.website_modified_at`, the `lastmod` of
`wines-sitemap.xml`. `wine_catalog.modified_at` is the time of the last change of a field
or of the state of the row; two triggers of schema 015 set it. The sort of the Dataset page
offers `changed in the lab, newest first` and `changed on vino-svoe.ru, newest first`. Read
[plan 21](docs/plans/21_website-import-ui.md).

```bash
# later: the test sets my, official-real-photos, and vlmrerank-8b-failed
python3 pipeline/import_testsets.py --db data/lab.sqlite3
```

`import_testsets.py` imports the three test sets of `../svoe-vino-testset/dataset/` into
the tables `test_set`, `test_photo`, `test_wine_note`, `test_excluded`, and
`test_variant`. The set name is the name of the directory. The import keeps each field of
a label entry of `review-labels.json`, the notes of a whole wine, and the text `note`
(schema 019, plan 24). Since plan 24 the database is the source of the labels: the
Testset page writes to the rows. So the import refuses a set that holds a page edit;
`--force` replaces the page edits with the files. A photo is stored as
`data/images/testset/<sha256>.<extension>`, one time for the same bytes. A photo whose
bytes the lab holds already, for example as a patch, keeps that file. `--source` names
another directory of the sets. `import_testset.py --set <name> <dir>` imports one set.
Read [plan 12](docs/plans/12_testsets-benchmark.md).

```bash
# seed or restore: build the whole lab database again from its sources
python3 pipeline/seed_from_testset.py --db data/lab.sqlite3
```

`seed_from_testset.py` runs the steps of this section in one command: the tables, the
catalogue, the main images, the patches, the GTINs and QR URLs, the Atlas Core bindings,
the three test sets, and the label cuts (SAM3 on gx10 through `data/cache/sam3/`). It
builds the new database at `<db>.seeding`, next to `--db`, with the same image store. A
failed step stops the script, and `--db` does not change; the next run deletes the
partial file. After the last step, the old database goes to
`data/backups/lab-<UTC time>.sqlite3`, and the new one is copied into `--db` with the
SQLite backup API. The lab server needs no restart. The new database holds the data of
the sources alone: a wine state, a comment, a favorite, a manual wine, an alternative
photo, an edit of the Testset page, and an image description are in the backup only. It
copies no configuration, no run, and no cluster. Read
[plan 28](docs/plans/28_seed-from-testset.md).
Git ignores the whole `data/` directory.

## The Testset page of the lab

The Testset page of the lab server (`/testset`) shows one test set of the database and
writes the labels of its photos. Each click writes to `data/lab.sqlite3` at once. The page
is a port of the Testset page of the review tool, with a smaller scope. Read
[plan 24](docs/plans/24_testset-page.md).

- The combobox in the title (`Test set [my (4043 photos) ▾]`) chooses the set: `my`,
  `official-real-photos`, or `vlmrerank-8b-failed`. The address keeps the set, the
  controls, and the open photo: `/testset?set=<set>#<slug>/<file name>`. The line after
  the combobox counts the wines and each photo of the set, the sidebar too. The stats
  line ends with the time of the last edit of the set.
- One row for each `Active` and `Disabled` wine, and one row for each place that holds a
  photo of the set, also when its wine is `Removed` or is not in `wine_catalog`. The NULL
  place (`__null__`) is the right sidebar, not a row. A `Removed` wine keeps its photos and its labels and gets
  the badge `Removed`, so a restore finds it again; the benchmark leaves its photos out
  ("removed wine") until the restore.
- The buttons `V`, `N`, `x`, and `D` set `positive`, `negative`, `unusable`, and
  `variant`; the same button again clears the label. A photo of `__null__` takes
  `positive` or `unusable` alone. The right-click menu marks a photo for deletion; the
  mark moves no file. The field below a wine holds its note. `Exclude` takes a slug out of
  the benchmark and asks for a reason.
- The sidebar holds the photos that wait for a wine, also after a restart. A drag of a
  photo card onto the sidebar moves the photo to `__null__`; a drag of a sidebar card
  onto a wine row moves it to that wine; the key `0` of the large view moves it to the
  sidebar (`POST /api/testset-move`). A move clears the label and keeps the comment, the
  box, the delete mark, and the proposal; `moved_from` gets the old place; a file name
  that the target holds gets `_moved<N>`. No file moves. A sidebar card has `V`
  (confirmed: no card of the catalogue shows this wine) and `×` (unusable). The
  benchmark takes a NULL photo only with `V` (`positive`).
- The large view shows the catalogue image and the photo side by side, with the comment
  panel. The keys: `Left` and `Right` the photos of the wine, `Up` and `Down` the wines,
  `1` to `4` the labels, `b` the box, `Esc` close.
- The box of the main object is optional, for a scene with several items. `b` or `Box`,
  then a drag on the photo, draws it; `Clear box` removes it. The box is in the pixels of
  the photo after its EXIF orientation. A card with a box gets the badge `box`. The IoU
  of the box against the box of the matcher comes with plan 27.
- The filters of the old page, and `marked for deletion`, `holds a box`, and `removed
  from the catalogue`. The 13 sort orders of the old page. `Find` matches each word in
  the slug, the name, the producer, the region, or the grapes, in any order, with the case
  and the accents folded.
- A drop of image files from the Finder onto the sidebar (the NULL place) or onto a wine
  row stores each file in that place with no label (`POST /api/testset-upload`). A new
  image keeps its file name; a clash with another image of the place gets `_upload<N>`.
  An image that the set holds already keeps the file name of the set. The same place
  refuses it (HTTP 409); another place takes it, for example for `negative`. The page
  takes JPEG, PNG, WebP, GIF, and BMP of at most 20 MB. HEIC is refused: Pillow here
  cannot read it.
- Not on this page yet: the copy of a photo, the upload by a file button and by URL, the
  checks (`validate`), the group editor, and the CSV export.

```bash
# write the JSON files of one set from the database (the database is the source)
python3 pipeline/export_testset.py --db data/lab.sqlite3 --set my --out <directory>
```

The export writes `review-labels.json` and `excluded-slugs.json` into `--out`, in the
form of the review tool. The import of a set, then its export, gives the same `labels`,
`wines`, excluded slugs, and `note` as the source files: checked on the three sets on
2026-09-25.

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

- A build writes `data/embeddings/<name>/`: `index.json` with the settings and the
  items, `vectors-<8 hex>.npy` with one float32 row for each item, and
  `images/<source_sha256>_<view>.png`. The PNG is the exact model input. The database
  does not change.
- The inputs are the images of the Active wines. `main_patched` replaces `main`. A file
  that several wines share is one item.
- The view `full` is variant C: the package cut of plan 09 (`segment`,
  `remove_background`), on white (`white_background`), and `resize`. The view `label`
  is variant F: the same with the label cut. The label cut of a full original is the
  row of the kind `label` of `image_derivative` (plan 22).
  `python3 pipeline/seed_label_cuts.py --db data/lab.sqlite3` makes it with SAM3 and the
  label rule of plan 16. A full image with no label cut fails with `no label cut yet`. A
  label close-up (`label_front`, `label_back`) goes to the view `label` as it is.
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
  running build. Each running job row ends with a button `(x)`: it stops the build of
  that row (`POST /api/embeddings/<name>/stop`), also when the combobox selects another
  entry. A `stopping` row keeps a disabled `(x)`. `Build` continues a stopped build.
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
  traceback, shows as it is, in red. The checkbox `hide item_failed, progress, and request` is on
  at the start. `Refresh` reads the file again. `Log` is disabled while the entry has no
  build yet.
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
- The last entry is `name: mock`, `backend: mock`, with the views of the other entries.
  It builds as any entry (owner message of 2026-09-25T13:37:14+0300: "mock should run as
  any other config"): the build prepares the images, then `MockBackend` of
  `build_embeddings.py` gives each image a random unit vector of 256 values. It sends no
  request. The seed is the SHA-256 of the prepared PNG, so a model input always gets the
  same vector. The entry takes no `base_url`, `model`, or `extra_body`; its model name
  is `random-unit-vectors`. `pipeline/mock_run.py` makes its runs (section "The runs of
  the lab").

## The VLM inferences

The key `vlm` holds one entry for each named VLM inference. `config.yaml` and
`config.old.yaml` hold the same section; `tests/test_vlm_config.py` checks that the two
files agree. `pipeline/vlm_config.py` reads the key. An entry holds the first five keys,
MAY hold `key`, and holds no other key:

| Key | Meaning |
|---|---|
| `name` | The name that a script uses. The names differ. |
| `protocol` | `openai`: `POST <endpoint>/chat/completions`. |
| `thinking_field` | Where the switch `enable_thinking` goes: `chat_template_kwargs` (the gx10 gateway) or `top_level` (QwenCloud and DashScope). In `scripts/cluster_rules.py` it also selects the JSON mode rule and the second attempt of an answer that reached `max_tokens`. |
| `endpoint` | The base URL, for example `http://192.168.86.14:18081/v1`. |
| `model` | The model name that the service knows. |
| `key` | Absent or `null` when the service needs no key, or `{env:NAME}`: the key is read from the shell variable `NAME` at run time. A key value in the file is refused. |

| Entry | Service | Key |
|---|---|---|
| `qwen3.5-9b-nvfp4` | gx10 gateway; the image descriptions of plan 26 | none |
| `qwen3.5-9b` | gx10 gateway; stage 1 of the cluster rules | none |
| `qwen3-vl-32b` | gx10 gateway; the default of `04_verify.py` | none |
| `qwencloud-qwen3.8-max` | QwenCloud Token Plan; stage 2 of the cluster rules | `{env:QWENCLOUD_TOKEN_PLAN_API_KEY}` |
| `qwencloud-qwen3.8-flash` | QwenCloud Token Plan | `{env:QWENCLOUD_TOKEN_PLAN_API_KEY}` |
| `dashscope-qwen3.7-flash` | DashScope, pay-as-you-go | `{env:QWENCLOUD_PAYGO_API_KEY}` |

```bash
# 04_verify.py names the entries in --backends, as name:workers
SVOE_VINO_REVIEW_CONFIG=config.old.yaml python3 scripts/04_verify.py \
    --backends qwen3-vl-32b:12,qwencloud-qwen3.8-flash:8
```

`scripts/04_verify.py` and `scripts/cluster_rules.py` import `scripts/common.py`, which
needs the key `dataset`. `config.yaml` has no such key, so both scripts run with
`SVOE_VINO_REVIEW_CONFIG=config.old.yaml`. An entry whose key variable is not set is
ignored by `04_verify.py`; `cluster_rules.py` refuses the call. `scripts/bench_vlm_models.py`
keeps its own endpoint and does not read the key `vlm`.

## The image descriptions

The table `image_description` describes each image that `wine_image` links to a wine
(`main`, `main_patched`, and the additional types): `package_type`, `subject_scope`,
`package_view`, and `content_roles`. Read [plan 26](docs/plans/26_image-description.md).

| Field | Values |
|---|---|
| `package_type` | `bottle`, `can`, `keg`, `bag`, `bag_in_box`, `tetra_pak`, `barrel`, `decanter`, `box`, `other`, `unknown` |
| `subject_scope` | `full_package`, `label_closeup`, `multiple_packages`, `unknown` |
| `package_view` | `front`, `back`, `unknown` |
| `content_roles` | a list of 1 to 2 of `front_label`, `back_label`, `unknown`; `unknown` stands alone |

- A button `✎` in the bottom right corner of each image of `/dataset` opens the editor
  of that image. A value set by hand stays. `— not set —` clears a value.
- `created_by` tells who made the row: `manual` (the owner, before the VLM) or `vlm`.
  `vlm_at` is empty until the VLM filled the row.
- The watcher `pipeline/describe_images.py` sends each image with no VLM fill to the
  `vlm` entry of `image_description.vlm` (`qwen3.5-9b-nvfp4`). The prompt holds the
  values that are set as fixed facts. The code checks the answer against the JSON Schema
  `ANSWER_SCHEMA` and fills only the values that are not set (`COALESCE`). `vlm_answer`
  keeps the full answer. An answer that fails the schema writes nothing and counts as a
  failure; an image stops after `max_attempts` (3) failures. A failure of the service (an
  HTTP 429 or 5xx answer, no connection) does not count; the watcher waits and tries again.
- The lab server starts the watcher when `image_description.watch` is true. The commands
  are in `COMMANDS.md`, section "Описания изображений".
- The pill at the left of `Add wine` shows the watcher: `VLM 895 / 2,022 · 2.6 s`
  (working, a green dot that pulses), `VLM all … described` or `VLM idle · … pending`
  (idle), `VLM waiting: <error>` (amber: the service or the database cannot be used now),
  or `VLM watcher not running` (stopped). `· N failed` in red counts the images that
  reached `max_attempts`. Its title names the pid, the wine of the image that the VLM
  reads now, the counts, the speed of the last 20 images, and the time of the last step.
  The page asks `GET /api/image-description-status` every 5 s while its tab is visible.
  The watcher writes its state into `work/describe_images.status.json` at each step; the
  route reads it, checks that the pid lives, and adds the counts of the database. The
  cards do not change while the page is open; a reload shows the new descriptions.
- The dialog holds a closed block `Raw VLM reply` for a row that the VLM filled. It
  loads `GET /api/image-description-reply?sha256=<sha256>` when it opens: the record of
  the call in `data/cache/`, with the model, `finish_reason`, the tokens, the reply text,
  the prompt, the full response body, and the request fields. The route builds the key of
  the call again from the image, `max_side`, the `vlm` entry, and the prompt; a change of
  one of them makes an old record unfindable (`found: false`).
- The button `Advanced Filters:` in the bar shows a second row of filters. Its first
  filter is `Package`: `All`, each `package_type`, and `not described`. The
  `package_type` of the patched image decides when the wine has one, else the main
  image. A wine with no image is `not described`. The button is marked while a filter is
  active. A save in the dialog draws the card again but does not apply the filter again,
  as for `Show`; choose the value again to apply it.

## The runs of the lab

The Runs page of the lab server (`/runs`) shows the run directories of `runs/`. The runs
stay files; the lab database does not hold them. The page is the Runs page of the
review tool: the table of the runs, the metric cards, the histograms, the photo rows
with `Show`, `Sort`, and `Find`, the candidate images with the cluster frames and the
VLM box, and the large view with the arrow keys and the model inputs. Read
[plan 23](docs/plans/23_runs-page.md).

```bash
# a run of the configuration mock: random top-k candidates for each photo of a test set
python3 pipeline/mock_run.py --set my [--top-k 10] [--seed N] [--limit N]
```

- The key `configuration` of `run.json` names the lab configuration of a run: one entry
  of `embeddings` in `config.yaml`. `pipeline/benchmark.py` writes it when
  `run_benchmark` gets the argument `configuration`. A run with no such key has no
  configuration; all runs before 2026-09-25 are such runs.
- The filter `Configuration` in the header, after the title `Match runs`, offers `every run`, each configuration of
  `config.yaml` with the count of its runs, a name that a run holds and `config.yaml`
  does not (`not in config.yaml`), and `no configuration`. The page address keeps the
  value (`?configuration=<name>`); the hash keeps the open run. When the open run
  leaves the table, the first run of the table with metrics opens.
- The table of the runs has pages: `prev`, `next`, and `per page` (25, 50, 100, or
  `all`). The browser keeps the page size. A sort goes back to page 1; the hash of a run
  opens the page that holds it.
- The table has the column `configuration`.
- The photo of a row comes from the image store of the lab database by its
  `image_sha256`, in the folder of its `image` row (mostly `testset`). A photo whose
  bytes are not in the store shows `not in the lab image store`. The catalogue image of
  a slug is its processed patch when the wine has a `main_patched` image (with the mark
  `patched`), else its processed `main` image, as on the card of `/dataset`.
- The cluster frames and the VLM box read `dataset/catalog-clusters.json` and
  `dataset/catalog-cluster-rules.json`. The link `cluster details` opens `/clusters`,
  which is disabled for now.
- The model inputs of the large view use `scripts/run_model_inputs.py` and the code of
  `svoe-vino-matcher`, as in the review tool. A run with no backend URL, for example a
  mock run, states that it has no model input.
- The mock backend answers `top_k` distinct Active slugs with random scores from high to
  low, and a random latency from 50 to 4,000 ms. Each place slug of a photo (of its
  positive or its negative row) gets a random rank from 1 to `top_k`, or no rank. So a
  mock run shows every state of the page: rank 1, a deeper rank, absent, a false match,
  and a negative above a positive. The same seed gives the same answers. The run id is
  `<stamp>-lab-mock-<set>`.
- The routes are in `pipeline/run_routes.py`; `pipeline/run_files.py` reads the files.
  `lab_server.py` sends each route of the page to `run_routes.py`. The review tool keeps
  its own copy of the run functions.

## The cache of the model calls

A call to SAM3, to Grounding DINO, or to a VLM that repeats an earlier successful call
reads the answer from `data/cache/` and sends no request. Read
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
- One record is one JSON file `data/cache/<model>/<key[0:2]>/<key>.json`. It holds the
  request fields, `created`, `ms`, and the answer as the service sent it. It holds no
  image.
- A success alone is stored: HTTP 200 with a JSON body, and for a VLM at least one entry
  in `choices`. An answer with no instance is a success. A failure asks again next time.
- The clients: `derive.Sam3Client` (each SAM3 call of `pipeline/`), `gdino.GdinoClient`,
  `Vlm.ask` of `scripts/cluster_rules.py`, `Backend.ask` of `scripts/04_verify.py`, and
  `call` of `scripts/bench_vlm_models.py`. A VLM request with an image URL that is not a
  data URL is not cached.
- To send a request again, delete its record, or the directory of its model. Do this
  also after the gateway serves a new checkpoint under the same name: the served name is
  in the key, the checkpoint is not.
- Unit tests set `model_cache.ROOT` to a temporary directory.

The sections below describe the tools of `scripts/`. They read JSON files through
`scripts/common.py`, and they do not start with the present `config.yaml`.

## Configuration

`config.yaml` in the project root holds the configuration. `scripts/common.py` reads it.

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
| `clusters` | `CLUSTERS`, `CLUSTERS_FILE` | The settings of `scripts/10_clusters.py` and the path of the cluster file. See [Catalogue clusters](#catalogue-clusters). |
| `cluster_rules` | `cluster_rules.CFG` | The VLM entries of the two stages (`vlm`, `rules_vlm`), the picture sizes, the rules file, and the notes file of `scripts/11_cluster_rules.py`. See [Label rules of the clusters](#label-rules-of-the-clusters). |
| `vlm` | `cluster_rules.VLM`, `cluster_rules.RULES_VLM` | The named VLM inferences. See [The VLM inferences](#the-vlm-inferences). |
| `image_description` | `describe_images.settings` | The watcher of the image descriptions: `watch`, `vlm`, `max_side`, `poll_seconds`, `max_attempts`. See [The image descriptions](#the-image-descriptions). |

### The keys of one dataset

| Key | Constant in `common.py` | Meaning |
|---|---|---|
| `name` | `DATASET` | The name of the dataset. It MUST be present, and the names MUST differ. |
| `photo_dir` | `PHOTO_DIR` | Photo set. One directory per wine slug. |
| `trash_dir` | `TRASH_DIR` | A deleted photo is moved here, not unlinked. |
| `label_file` | `LABEL_FILE` | Labels of the review tool. |
| `variant_groups_file` | `VARIANT_GROUPS_FILE` | Variant groups. `scripts/08_variants.py` writes this file. |
| `manual_groups_file` | `MANUAL_GROUPS_FILE` | Variant pairs made by hand in the review tool. `scripts/08_variants.py` never writes this file. |
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

`my/` is written by stage 5. Re-run `python3 scripts/05_report.py --keep 4`
after any later pass, or the directory keeps the content of the previous run.

## The `my/` set

The set covers the 2,018 wines in `wines.jsonl` of the `vino-svoe.ru` dump.
Each wine has its own directory `my/<slug>/`.
A file name is `<rank>_conf<NNN>.<ext>`. `NNN` is the model confidence in percent.

The set contains real-world photos only. A studio catalogue render is excluded.
Two filters remove studio renders: a border-whiteness measure, and a vision model judgement.

A wine has fewer than 3 photos when the web holds fewer than 3 usable photos of it.
`REPORT.md`, `report.html`, and `report.csv` list every wine and every gap.

## Pipeline

| Stage | Script | Work |
|---|---|---|
| 1 | `01_search.py` | Collect candidate image URLs from Yandex Images and DuckDuckGo |
| 2 | `02_download.py` | Rank candidates by text relevance, then download the best ones |
| 3 | `03_embed.py` | SigLIP2 embedding, cosine similarity against the catalogue photo |
| 4 | `04_verify.py` | `qwen3-vl-32b` pairwise check: same wine, and studio or not |
| 5 | `05_report.py` | Copy accepted photos to `my/`, write the report |
| 6 | `06_topup.py` | Reopen wines that have fewer than 3 photos for a deeper pass |
| 7 | `07_api_check.py` | Ask the official recognizer about each accepted photo |

Run every stage through the driver:

```bash
python3 scripts/run_pipeline.py --chunk 150 --per-wine 20 --top 8 --vlm-workers 6
python3 scripts/05_report.py
```

Finish the set with one command:

```bash
scripts/finalize.sh
```

Stage 1 runs on its own because it is slow and independent:

```bash
python3 scripts/01_search.py --workers 4
```

Every stage is resumable. State lives in `work/state.db`.
Stages 3 and 4 use the llama-swap service on gx10 (`http://192.168.86.14:18081`).

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

A record with a patch has a `Remove` button. The button stages the removal. Press
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
largest label that is not the package). The badge shows `crop` or `seg`. The buttons
`FF`, `LF`, `FB`, `LB` below each photo change the type at once; the filled button is
the present type. A change between a full type and a label type cuts the photo again; a
change between front and back keeps the cut. `×` and `Apply` delete the row; the file
stays in `data/images/additional/`. When SAM3 does not answer, the photo gets
`full_front`, no processed file, and a warning. The detection rules were fitted to small
probe sets; their accuracy on real photos is not known, so check the type.

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

`scripts/08_variants.py` finds such slugs and writes the file that `variant_groups_file` names in `config.yaml`:

```bash
python3 scripts/08_variants.py --no-image      # metadata step only, runs at once
python3 scripts/08_variants.py                 # metadata step and image step
python3 scripts/08_variants.py --threshold 0.93
```

The script joins two slugs in two ways:

1. Metadata. The same `producer` and the same `name` in `catalog.jsonl`.
   This step is exact and costs nothing. It gives 28 groups over 63 wines of `my/`.
2. Image. The cosine similarity of the SigLIP2 embeddings of the two catalogue
   bottle photos, at or above `--threshold`. This step needs the llama-swap service
   on gx10. It finds the pairs that step 1 misses. Every run embeds the bottle photos
   again, because the script keeps no embedding cache. Use `--no-image` to skip the
   step.

The image step MUST NOT run while stage 4 of the pipeline runs. Both use the same
llama-swap service, and a request for `siglip2` makes the service drop
`qwen3-vl-32b` and load `siglip2`. The pipeline then stalls.

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

`scripts/08_variants.py` never writes `manual_groups_file`, so a new run of the
script keeps every pair made by hand.

A perceptual hash was tried first and was dropped: a bottle photo is mostly bottle,
so the hash of the silhouette hides the label. Read `ResearchLog.md` for the numbers.

### Catalogue clusters

A variant group joins wines of `my/`. A catalogue cluster joins cards of the WHOLE
catalogue that the matcher confuses, or can confuse. A later re-rank step reads the
clusters. The two are separate: `scripts/08_variants.py` and the review table do not
read the cluster file, and the page `/clusters` does not read the variant groups.
Read `docs/plans/04_catalog-clusters.md` for the rules and the decisions.

`scripts/10_clusters.py` writes the file that the key `clusters.file` of `config.yaml`
names:

```bash
python3 scripts/10_clusters.py
python3 scripts/10_clusters.py --show abrau-dyurso-pino-nuar-krasnoe-suhoe-12
python3 scripts/10_clusters.py --no-confusion --photo-threshold 0.93 --out work/clusters-test.json
```

Four signals join two cards. A link records every signal that passed.

| Signal | Rule | Default in `config.yaml` |
|---|---|---|
| `name` | The same producer, the same name, and the same category after normalisation. The words of the producer are removed from the name. The grapes of one card MUST be a subset of the grapes of the other card, or one field MUST be empty. | |
| `photo` | The SigLIP 2 cosine of the two catalogue photos. | `photo_threshold: 0.95` |
| `label` | The SigLIP 2 cosine of the two label crops. | `label_threshold: 0.95` |
| `confusion` | The positive photos of one card that a run of `runs` answered as the other card at rank 1, over both directions. | `min_confusions: 2` |

The vectors come from the two index files of `svoe-vino-matcher` that `photo_index`
and `label_index` name. The script calls no service, so it can run while the pipeline
uses gx10. The name of an index file holds a digest. After a rebuild of an index, set
the new file name in `config.yaml`.

A confusion counts only when the current label file still marks the photo `positive`
in the folder of that card. An old run can hold a label that a reviewer changed later.

A cluster is a connected component over the links, so a card is in at most one
cluster. `kind` states how the cluster holds together:

| `kind` | Meaning |
|---|---|
| `same-wine` | The `name` links alone join every card. The cards differ by vintage, alcohol value, or package. |
| `mixed` | The cluster holds `name` links and other links. |
| `look-alike` | The cluster holds no `name` link. The cards share one label design, or the matcher confused them. |

Measured on 2026-09-22 with the defaults: 255 clusters over 630 of the 2,103 cards, the
largest of 10 cards; 53 `same-wine`, 22 `mixed`, 180 `look-alike`. With
`--min-confusions 1` the largest cluster holds 38 cards, because single confusions
chain whole product lines together. Read `ResearchLog.md`.

The page `http://127.0.0.1:8154/clusters` shows the file. It holds one block for each
cluster: the catalogue photos side by side, the card fields, the label counts of the
test photos, and a table of the links with their evidence. The value of a signal that
passed is bold. `confused photos` shows the test photos that a run answered as the
other card. The controls filter by kind, signal, size, and text, and sort the
clusters. `Image` switches between the package and the label crop.

A click on an image opens the large view. The caption names the card, or the photo and
the card that a run answered for it, and states the place: `image 3 of 18 · c013 ·
cluster 2 of 255`. The keys and the buttons of the large view move as follows:

| Key | Move |
|---|---|
| `Left`, `Right` | the previous or the next image of the cluster: the cards first, then the confused photos, in the order of the page |
| `Up`, `Down` | the same place in the previous or the next cluster of the view. A place after the end of that cluster holds at its last image. The page scrolls to that cluster. |
| `Esc` | close. A click on the dark ground also closes. |

The first and the last image hold: a move does not turn around at an end. The image
that the large view showed last keeps an outline in the page. A click with a modifier
key, such as `Cmd`, opens the image in a new tab instead.

`/clusters#<slug>` opens the cluster of that card. The cluster id, such as `c013`, is
not stable between two builds, so the address names a card and not an id. The page
reads the file at each load, so a new build needs no restart. The page writes only the
note of a cluster and the rule of a cluster. See the next section.

### Label rules of the clusters

A label rule tells the cards of one cluster apart. The re-rank kind `cluster_rules` of
`svoe-vino-matcher` reads the rules: when the rank-1 card and another card of its
cluster stand in the first 5 positions, the VLM reads the label of the query photo
with the rule of that cluster. Read `docs/plans/05_cluster-label-rules.md` for the
decisions and the measurements, and `docs/plans/06_label-only-cluster-rules.md` for
the label-only rules of 2026-09-24.

`scripts/11_cluster_rules.py` builds the rules in two stages:

```bash
python3 scripts/11_cluster_rules.py
python3 scripts/11_cluster_rules.py --stage describe
python3 scripts/11_cluster_rules.py --cluster vinodelnya-vedernikov-fantom-3070-krasnostop-zolotovskiy-krasnoe-suhoe-145
python3 scripts/11_cluster_rules.py --dry-run
```

| Stage | One VLM call for | Input | Answer |
|---|---|---|---|
| 1, `describe` | each card of a cluster | the catalogue picture of the review tool, scaled to a long side of 2048 pixels; no card data | the label description: the texts and the numbers with their place, the vintage, the colours, the design, the marks, the bottle |
| 2, `rules` | each cluster | the label crop of each card from `bottle_label_dir`, on white, scaled to a long side of 768 pixels, UP or down (a card with no label crop sends its catalogue picture); the card data; the label descriptions without the key `bottle`; and the note of the reviewer | the difference sheet (questions with the expected answer of each card), the rule text, and the groups that no feature separates |

Stage 1 uses `qwen3.5-9b` on the gx10 gateway, with thinking off; one description
takes about 15 seconds. Stage 2 runs once, so it uses the more capable `qwen3.8-max` of
the QwenCloud Token Plan, with thinking, 4 requests at a time; one rule takes about 40
to 70 seconds. `cluster_rules.vlm` and `cluster_rules.rules_vlm` of `config.old.yaml`
name the two `vlm` entries: `qwen3.5-9b` and `qwencloud-qwen3.8-max`. The key comes from
the environment variable `QWENCLOUD_TOKEN_PLAN_API_KEY` (the `key` of the entry
`qwencloud-qwen3.8-max`); a shell that runs stage 2, or the review tool that builds a
rule, MUST hold it. The old keys `url`, `model`, `rules_url`, `rules_model`, `rules_api`,
and `rules_key_env` are refused. The prompt of stage 2 keeps only major differences: the
grapes, a kosher mark, the wine name or the line name, the colour of the wine as the
label states it, the sugar level, a blend ratio, a reserve or edition mark, the volume,
and the vintage year. The prompt allows only features that are printed on the label:
some catalogue pictures are drawings, and a drawing shows only the label correctly.
The re-rank also sends only the label crop of the query. The vintage year is used only
when the catalogue names of at least two cards state two different years: a year that
only the picture shows changes from bottle to bottle. An expected text is written as the
label prints it, in its own alphabet, so the query VLM can find it among the options: a
first build wrote «Krasnostop» for the printed «КРАСНОСТОП». The catalogue reuses the
picture of one card for another card (43 cards of 21 clusters on 2026-09-24). The caption
of such a card names the other card, and the catalogue data wins where the picture
contradicts it. The script does only the work that is not current, so a stopped run
resumes. A small catalogue photo is scaled UP for stage 1: at 312 x 1000 pixels the
model read «урож. 2024» as 2021.

The code checks the sheet and sets the mode of the rule:

| Mode | Meaning |
|---|---|
| `sheet` | At least one question separates two cards. The re-rank asks the questions about the query photo. |
| `verdict` | No question separates two cards, the rule text is not empty, and the rule text names no feature outside the label. The VLM reads the rule text and names the card. |
| `none` | No usable difference was found. The re-rank does not act. |

The vintage variants. When cards differ only by the vintage year, and one card states
no year, that card is the card of every vintage that no other card states. A card
states a year in its name, in its slug, or on its label (the key `vintage` of its
label description). Only a mixed cluster, which holds cards with a year and cards
without one, gets the note of the vintage variants in its prompt: 43 clusters on
2026-09-24. The model gives a card with no year the answer `other` in the vintage
question. The re-rank of `svoe-vino-matcher` counts a year that no card lists as
`other`.

The code enforces five rules of the prompt, because the model does not always keep
them:

- A question about a bottle number, such as «Бут. №» or «Тираж», is never used: the
  number changes from bottle to bottle. Its kind is `serial`.
- A question about a feature outside the label, such as the glass, the colour of the
  liquid, the capsule, the cork, or the shape of the bottle, is never used. Its kind is
  `bottle`. A rule text that names such a feature gives mode `none`, not `verdict`.
- A vintage question keeps the expected year of a card only when the name or the slug
  of the card states that year. Its kind is `vintage`. The question is used when two
  cards keep two different years.
- The mark `other` of a vintage question stays only for a card that states no year,
  and only when no other question separates that card from every card with a year.
  Then the vintage question also keeps the year on the label of a card.
- A question about the alcohol value is used only when no other question separates the
  cards: the value changes between vintages. Its kind is `alcohol`.

Two files hold the results:

| File | Writer | Content |
|---|---|---|
| `dataset/catalog-cluster-rules.json` | `scripts/11_cluster_rules.py` and the review tool | the label descriptions by slug, and the cluster rules by cluster key |
| `dataset/catalog-cluster-notes.json` | the review tool only | the notes of the reviewer |

The cluster key is the SHA-1 of the sorted slugs of a cluster, 12 hex digits. A note
keeps the slugs of its cluster. It belongs to the current cluster that shares the most
slugs with it, so a note survives a new build of the clusters. A rule is `current`
while its slugs, its card data, its descriptions, the paths of its label crops, its
note, and its prompt stay the same; else it is `stale`. A label crop that is cut again
under the same path does not make a rule stale. A lock file keeps two writers of the
rules file apart.

The post hoc score of `scripts/cluster_rules_report.py` reads the questions of a rules
file: the current file, or the file that `--rules` names. A report of an older run
MUST name the rules file of that run. The rules of 2026-09-23 (`qwen3.8-max`, whole
pictures) are kept as `work/catalog-cluster-rules.2026-09-24T082150.json`. That copy is
the only record of them, because `dataset/catalog-cluster-rules.json` is not in git. The
report also gives the paired numbers for each half of the wines; the half of a wine is
the SHA-1 of its slug, modulo 2.

The page `/clusters` shows a `Label rule` block in each cluster: the mode, the status,
the text about the differences, the sheet as a table with one column for each card,
and the rule text. A struck question is not used; its tooltip gives the reason. Each
card holds its `label description`.

Press `Edit rule` to edit the rule text and the functional difference sheet. You can
add or remove questions. Each question has one expected answer for each card. A blank
answer means that the label does not show the feature. `Save rule` applies the same
checks as a VLM build. It recomputes the valid questions and the mode. The edit keeps
the build identity, so it stays current until an input changes. `Rebuild rule` replaces
the manual edit with a new VLM result.

Stage 2 shows the VLM the cards as «Card A», «Card B», and so on, and the rule text
uses these letters. The rule keeps the map `letters`, from the letter to the slug. The
letters follow the sorted slugs, so A is card #1 of the page. The page writes the letter
beside the number of each card and in the head of the sheet, and `the cards of the
letters` under the rule text names the card and the slug of each letter. The sheet is
stored by slug, so the re-rank never reads a letter in mode `sheet`. In mode `verdict`
the query prompt shows the same letters with the card names and descriptions, and the
code turns the answered letter back into a slug with the same map. A slug is not put
into a prompt: it is long, so the model can answer it with a typo, and it holds hints
such as a year or the alcohol value that the label can contradict. The filter `Rule` selects a mode, a status, or the
clusters with a note.

The note editor stands under the rule. `Save note` stores the note. The note does not
change the rule by itself: `Rebuild rule` saves the note, describes the cards that
have no current description, and asks the VLM for the rule again. It takes about 5 to
30 seconds, and one build runs at a time. The prompt tells the VLM that the note is a
correct fact. Example for the «Фантом» cluster: the note «pay attention to numbers in
bottom left corner of bottle (30/70), (50/50), (70/30)» gave the question about the
bottom left corner with the answers 30/70, 50/50, and 70/30.

`scripts/cluster_rules_report.py <run>` reports one run of the backend
`svm-label-gw-cluster-rules` against its base run. It also replays the run over the
clusters that exist without the `confusion` signal, because that signal comes from
match runs over the same test photos.

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

The files move when `apply` is pressed, or when the script is run:

```bash
python3 scripts/09_apply_moves.py            # report only
python3 scripts/09_apply_moves.py --apply    # move the files
```

Both use the same functions of `review_server.py`, so both act the same way.

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
states `N copies pending` with an `apply` button. The same `apply` button, and the
same script, carry out the copies, the moves, and the deletions:

```bash
python3 scripts/09_apply_moves.py            # report only
python3 scripts/09_apply_moves.py --apply    # move and copy the files
```

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

The crop is the picture that the tool shows and embeds:

- `GET /img/bottle` serves the crop. The field `bottle_path` of the agent API names it.
- `scripts/08_variants.py` embeds the crop to find variant groups.
- `scripts/03_embed.py` embeds the crop as the reference of a wine. The stage scores
  only the candidates that have no `sim` yet, so a score of an earlier run stays as it
  is.
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
photo, which the server reads from a byte-equal `positive` photo of the same run. Two or
more candidates that stand next to each other and belong to one catalogue cluster share
one frame in the accent colour. The link in the frame opens that cluster on
`/clusters` and scrolls to its details. The
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
