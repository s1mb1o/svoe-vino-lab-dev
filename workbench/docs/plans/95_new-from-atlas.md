# Plan 95: New from Atlas, and photo moves between roles

Date: 2026-09-30

Source: owner message of 2026-09-30T22:05:00+0300 and the answers of 22:22:00
(`docs/owner-messages.md`).

## Owner decisions

- Approach B: "Prepare, then Create". The lab server keeps no job. The dialog drives the
  steps with an idempotent request.
- "All largest photos" means the largest photo of each group of similar photos.
- A move to `main` or to `patched` swaps: the old photo of the role becomes an
  additional photo.
- The fields come from the form `Add wine`, prefilled from Atlas. The owner confirms them.
- The new wine has no main photo. The owner selects the main photo later.

## Part 1: New from Atlas

### Flow

1. The button `New from Atlas` of the Dataset page opens a dialog. The dialog asks for a
   Drink Atlas product URL, for example
   `http://127.0.0.1:8157/products/a3b3d69b-71e5-4f38-9a76-411c6203c873`.
2. `Prepare` sends `POST /api/atlas-import/advance`. The dialog sends it again every 3 s
   until each step is terminal.
3. When each step is terminal, the dialog sends `POST /api/atlas-import/photos` and shows
   the selected photos. `Create` is then enabled.
4. `Create now` is enabled at each moment. It takes the photos that exist at that moment.
5. `Create` and `Create now` open the form `Add wine` in the Atlas mode. The form is
   prefilled. It shows the selected photos in place of the main image. It needs no main
   image.
   - Name: `display_name`. Producer: the first `producers[].name`, else `brand`.
   - Category (`beverage_type_code`): the rule of `display_names._base_style` of Atlas
     Core. A code that starts with `44` or `45` gives `44` (sparkling wine). A code that
     starts with `40` to `43` gives `4` (wine).
   - Color (`category`): `wine_profile.wine_color_code` `white`, `red`, `rose`, `orange`
     gives `Белое`, `Красное`, `Розовое`, `Оранжевое`. A select that has no option for
     the value gets the option.
   - Region: `origin_region`. Grapes: `grapes_and_harvest`. Shade stays empty.
6. `Save` sends `POST /api/atlas-import/create`. The answer has the shape of the answer of
   `POST /api/wine`. The page adds the card as `saveWine` does.

### The Atlas steps

The steps are the same as the three buttons of the Atlas product page
(`drink-atlas-webui/src/enrichment.tsx`):

| Button | Profile | Media |
|---|---|---|
| `Удалить белые поля и полосы` | `image-auto-clean-v1` | each image that has no `pdf_sources` |
| `Извлечь изображения из PDF` | `pdf-embedded-images-v7` | each asset with `content_type` `application/pdf` |
| `Распознать штрихкоды` | `image-barcode-v3` | each image, and each `crop.derived_media_id` |

- Stage 1 is the clean step and the PDF step. Stage 2 is the barcode step.
- Stage 2 starts when each stage 1 step is terminal. The product is read again, so the
  barcode step also covers the new PDF images and the new derived crops.
- The request goes to the Atlas web UI proxy:
  `POST <atlas>/api/enrichment/requests` with the body
  `{"product_uuids": [<uuid>], "profile": <profile>, "queue_class": "interactive",
  "params": {"media_id": <id>}}`. The proxy needs `Origin: <atlas>` and
  `X-Atlas-Action: enrichment`. The proxy adds the coordinator token. The lab keeps no
  Atlas token.
- `advance` reads the tasks of each media with
  `GET <atlas>/api/enrichment/tasks?product_uuid=<uuid>&media_id=<id>&limit=200`. The
  newest task of the profile is the task of the step. A step with no task gets a new
  request. A step with a task gets no new request, also when the task failed. So a
  repeated `advance` sends no duplicate request.
- Terminal task states: `succeeded`, `failed`, `stale`, `blocked`.
- `<atlas>` is the origin of the URL of the owner. The host MUST be `127.0.0.1`,
  `localhost`, or `::1`. The Atlas proxy answers a loopback host only. The lab server does
  not fetch other hosts.

### The photo selection

- The candidates are the product assets of the kind `image`, one for each `media_id`.
  These include the PDF images.
- The groups use the rule of the Atlas button `Сгруппировать похожие`
  (`drink-atlas-webui/src/similar-images.ts`, `main.tsx` `imageFingerprint`). The lab
  ports the rule to Python:
  - The fingerprint is a 32 x 32 RGB image of the thumbnail
    `/api/v1/assets/<id>/thumbnail`. The id is `display_media_id` when it differs from
    `media_id`, else `crop.derived_media_id`, else `media_id`.
  - An image that has no `pdf_sources` loses its outer white fields before the resize.
  - Two photos are similar when the fingerprint distance is at most 0.07 and the aspect
    ratios differ by at most 4 %. An original and a PDF image are also similar when one
    is a crop of the other (the directional crop match).
  - The groups are the connected components.
- The selected photo of a group is the first photo by the Atlas quality rule
  (`compareAssetQuality`): the most pixels (the crop size when a crop exists), then the
  most bytes, then the lowest `media_id`.
- Difference to Atlas: Pillow resizes the fingerprint with `LANCZOS`. The browser uses
  its own high-quality filter. A distance near the limit can differ.
- A photo whose thumbnail cannot be read forms its own group.

### The download

The file of a selected photo follows `downloadImage` of
`drink-atlas-webui/src/asset-download.ts`:

- With `crop.derived_media_id`: `/api/v1/assets/<derived>/content`.
- With a crop and no derived media: `/api/v1/assets/<id>/crop` (PNG).
- Else: `/api/v1/assets/<display or oriented id>/content`.
- A confirmed orientation with a crop, or with no derived media, gets the rotation and
  the reflection of `orientation`, as `rotateCrop` does.
- A file that is not JPEG, PNG, or WebP becomes PNG. A file of more than 20 MB is
  skipped with a warning.
- Each file is downloaded before the first write. An Atlas error stops the create with no
  write.

### The create

`POST /api/atlas-import/create` takes the fields of the form `Add wine`, `url`, and
`media_ids` (the photos that the dialog showed).

1. The server checks the fields with the rules of `manual_wines.py`. The main image is not
   required.
2. The server checks that each `media_id` is an image of the product. It runs the
   preflight of the new-wine index (plan 84), as `POST /api/wine` does.
3. The server downloads the files.
4. One transaction writes `wine_catalog` (state `Active`, `csv_photo_name` =
   `atlas-<product uuid>`), `wine_beverage_type`, and the manual Atlas binding
   (`wine_atlas_binding`, source `manual`).
5. Each file becomes an additional photo through `alternatives.store_alternative`: SAM3
   selects the type and makes the cuts. The QR/barcode scanner of the lab adds its codes
   to `wine_code`, as an upload of the card does. The source name is
   `atlas-<media_id>.<extension>`.
6. The index job of plan 84 starts.

A photo that fails in step 5 gives a warning. The wine stays with the other photos.

## Part 2: photo moves

`POST /api/dataset-photo-move` with `{slug, sha256, from, to}`. One of `from` and `to` is
`additional`. The other is `main` or `patched`.

- Additional to main (or patched): the additional row of the photo is removed. The photo
  becomes the `main` (or `main_patched`) row. The old photo of the role becomes an
  additional photo of the type `full_front`. It is the last additional photo.
- Main (or patched) to additional: the photo becomes an additional photo of the type
  `full_front`. The role is then empty.
- A photo that is an additional photo already, and also holds the role, only loses the
  role row.
- A photo in the role `main` or `main_patched` needs the cuts of a full photo: the package
  cut and the label cut of a full photo. The move makes a missing cut before its write
  transaction (`alternatives._cuts_of` with the kind `full`). A label close-up that moves
  to main thus gets a new label cut, as a type change from a label type to a full type.
- The file stays in its folder. The table `image` does not change.
- `csv_photo_name` does not change.
- A move does not start an index job. The note of the card states that a change enters
  the matcher index after an index rebuild. This is the rule of the other photo edits.
- The page shows the buttons `→M` and `→P` for each additional photo, and a button
  `→ additional` for the main photo and for the patch.

## Part 3: `load photos` of an existing wine

Source: owner message of 2026-09-30T23:01:00+0300 and the answers of 23:04 ("A: Card
button", "Skip barcodes"). Changed by the owner message of 23:20:00 and the answers of
23:22 ("`load photos` only", "Show photos, then Import"): the button runs no Atlas step.

- Each Atlas product row of a card (`atlasBindingEditor`) has the button `load photos`.
  The rows hold the manual and the automatic bindings.
- The button opens the dialog of part 1 in the add mode. The URL is
  `http://127.0.0.1:8157/products/<uuid>`, the address of the link `open` of the row.
- The add mode runs no Atlas step and sends no `advance`. It reads
  `GET /api/atlas-import/photos` at once: the photos that Atlas has now, with the rule of
  part 1. The answer also holds the product name. `Reload` reads the photos again.
  `New from Atlas` keeps its three steps.
- `Import` sends `POST /api/atlas-import/add` with `{slug, url, media_ids}`. Each photo
  becomes an additional photo of the wine through
  `alternatives.store_alternative`, as in part 1. A photo with the same SHA-256 on the wine
  is not added again. The main photo, the patch, and the Atlas bindings do not change. No
  index job starts: the rule of the other photo edits.
- The answer holds the new record and `added`. The dialog states the count.

## Files

- New: `pipeline/atlas_import.py`, `pipeline/atlas_import_routes.py`,
  `pipeline/photo_moves.py`, `pipeline/pages/atlas_import.js`,
  `tests/test_atlas_import.py`, `tests/test_photo_moves.py`.
- Own hunks: `pipeline/lab_server.py`, `pipeline/pages/dataset.html`,
  `docs/lab-openapi.yaml`, `tests/test_lab_openapi.py`, `README.md`, `ChangeLog.md`,
  `SMOKE_TESTS.md`, `COMMANDS.md`.
- No schema change.
- A restart of 8168 for the new routes (rules 22 to 24).

## Known limits

- On 2026-09-30 at 22:10, no enrichment worker for these profiles was online. Only the
  `frame-gx10-*` workers ran. The tasks stay `queued` until a general worker runs, for
  example `drink-atlas-enrichment/scripts/run_worker_local.py --id mbp2023-worker-a`.
  The owner starts the workers. `Create now` works without them.
- The barcode step of Atlas does not confirm a GTIN. The lab does not copy
  `confirmed_gtins` of Atlas. The lab scanner scans each imported photo.
- A field with no Atlas value stays empty, often Region and Shade. The owner fills it.

## Results

2026-09-30:

- Tests: `test_atlas_import.py` 14 OK, `test_photo_moves.py` 7 OK. The related suites
  stay green: `test_lab_openapi.py` 11, `test_manual_wines.py` 17, `test_patches.py` 16,
  `test_alternatives.py` 59, `test_lab_server.py` 69, `test_new_wine_jobs.py` 10.
- A Playwright run of a scratch server (temporary database, fake SAM3, fake Atlas) passed
  the whole flow in light and dark theme: the two stages, the photos, the prefilled
  form, the save, `→M`, `→P`, and `→ additional`. The page had no error.
- The live product `ffd04eec-572b-42fe-b06f-83e29f86c329` gave 3 groups. Each group held
  2 originals and 1 PDF image. The selected photo of each group was the cleaned original.
  The selection took 0.7 s.
- The live product `a3b3d69b-71e5-4f38-9a76-411c6203c873` gave 3 single photos: the
  three JPEG files show different pictures.
- Part 3: `test_atlas_import.py` 15 OK. A Playwright run of a scratch server with scratch
  pages and a fake Atlas: `load photos` sent no Atlas request, showed 2 photos at once,
  and `Import` added them to the card. 8168 restarted at 23:07:24 (pid 81464) and, for
  the change of 23:20, at 23:22:50 (pid 24051).
