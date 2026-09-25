# 09 — Process each image at import: crop and segment

Date: 2026-09-25.
Status: implemented on 2026-09-25. The owner answered the open questions on 2026-09-25.
The owner messages of 2026-09-24 and 2026-09-25 in
[owner-messages.md](../owner-messages.md) hold the request and the answers.

## Goal

1. Each import processes each image that it stores: `main`, `main_patched`, and the
   additional types.
2. An image with a transparent background loses its transparent border. The badge is
   `crop`.
3. An image with no transparent background goes to SAM3. SAM3 finds the bottle. The
   badge is `seg`.
4. The originals stay in the store. A processed file is a second file next to it.
5. The sha256 of the original is the key of the processing. A file that several wines
   share is processed one time.
6. The Dataset page shows the processed image with its badge.

## Decisions of the owner

| Question | Decision |
|---|---|
| Keep the originals | Yes. The processed files are stored next to them (option A of 2026-09-24). |
| The storage of the link | Option C: a table `image` with one row for each stored file. `wine_image` and the new table `image_derivative` refer to it. |
| The processing | Cut white and transparent borders. Use SAM3 for an image with no transparent background. |
| The badges | `crop` and `seg` on the image of the card. |
| What `seg` makes | A segmentation of the bottle, the can, or the packet. The mask is smoothed and grown a little. |
| Several instances | The main image holds one package. The largest instance wins. |
| The size of the size sort | The size of the processed file. |
| `seed_patched.py` | This session changes it. The owner agreed; drink-atlas-workspace-20 agreed too. |
| A change of the settings | The default of open question 5: the row is replaced, with no history. |

## Measurement on 2026-09-25

The 2,018 files of `data/images/main/`:

| Background | Files | Processing |
|---|---|---|
| transparent pixels in the alpha channel | 1,875 | `crop` |
| RGB, no alpha channel | 143 | `seg` |

The SAM3 service of gx10 had an empty queue: `queued 0`, `running 0`.

## Schema file 007

The schema file builds the image tables again. Rules 9 to 12 of `AGENTS.md` allow it.

```sql
-- One row for each stored file: an original or a processed file.
CREATE TABLE image (
    sha256    TEXT PRIMARY KEY,  -- 64 lower-case hex characters
    folder    TEXT NOT NULL,     -- main, patched, additional, or cropped
    extension TEXT NOT NULL,     -- a-z0-9, lower case
    width     INTEGER,           -- pixels; NULL when not measured
    height    INTEGER
) STRICT;

-- One row for each wine, image type, and original file.
CREATE TABLE wine_image (
    wine_slug    TEXT NOT NULL REFERENCES wine_catalog (wine_slug),
    image_type   TEXT NOT NULL,  -- the six types of schema file 005
    sha256       TEXT NOT NULL REFERENCES image (sha256),
    source_name  TEXT NOT NULL,
    match_method TEXT NOT NULL,
    PRIMARY KEY (wine_slug, image_type, sha256)
) STRICT;

-- The processed file of one original.
CREATE TABLE image_derivative (
    source_sha256 TEXT PRIMARY KEY REFERENCES image (sha256),
    method        TEXT NOT NULL CHECK (method IN ('crop', 'seg')),
    settings      TEXT NOT NULL,  -- the rule and its values, for example 'alpha 32, open 5'
    sha256        TEXT NOT NULL REFERENCES image (sha256),
    box_left      INTEGER NOT NULL,  -- the box in the pixels of the original
    box_top       INTEGER NOT NULL,
    box_right     INTEGER NOT NULL,
    box_bottom    INTEGER NOT NULL
) STRICT;
```

- The file of an image is `images/<folder>/<sha256>.<extension>`.
- The folder of an original is the folder of the image type that stored it first. A
  file that is `main` of one wine and `front` of another wine stays in one folder.
- The processed files are in `images/cropped/`. Their format is PNG.
- The columns `extension`, `width`, and `height` move from `wine_image` to `image`.
  So the table `wine_image` is in BCNF now.
- The unique index for one `main` and one `main_patched` of each wine stays.
- The migration keeps each row. It fills `image` from the distinct files of
  `wine_image`.
- The link: `wine_image.sha256` = `image_derivative.source_sha256`, and
  `image_derivative.sha256` names the processed file. Each link is a foreign key.

## The processing

A new module `pipeline/derive.py` processes one original. `seed_images.py` and
`seed_patched.py` call it for each file that they store or keep.

1. An original with a row in `image_derivative` is not processed again.
2. An original with transparent pixels gets `crop`. The rule is the alpha rule of
   `svoe-wino-hackaton/scripts/build_cropped.py`:
   - a pixel is content when its alpha value is above 32;
   - a morphological opening of 5 pixels removes thin lines;
   - the box is the bounding box of the rest, with no margin;
   - the crop keeps the pixels and the alpha channel, as RGBA PNG.
3. An original with no transparent pixels goes to SAM3:
   - `POST /segment_multi` with the texts `wine bottle, can, packet`, `threshold` 0.35,
     `mask_threshold` 0.5, and `return_masks` true, as `build_labels.py`;
   - the image is flattened on white and scaled to a long side of 1,536 pixels at
     most; the mask is scaled back to the size of the original;
   - the largest instance wins, because the main image holds one package;
   - the mask is smoothed and grown: a Gaussian blur with a sigma of 0.5 % of the long
     side, then a cut at 64 of 255. The mask grows by about 0.67 sigma. A blur of 1
     pixel makes the edge soft;
   - the mask becomes the alpha channel. The crop is the box of the mask;
   - the result gets the badge `seg`.
4. SAM3 answers, and it finds no bottle: the white rule of `build_cropped.py` makes the
   crop (a pixel is content when a colour channel is below 245). The badge is `crop`.
   The `settings` value states the fallback.
5. SAM3 does not answer: the original gets no processed file, and a console message.
   The import goes on. A second import asks SAM3 again. After the first failure, the run
   sends no more requests, so a run with no service does not wait for each image.
6. An image with no content keeps the whole canvas as its box.
7. The endpoint is `http://192.168.86.14:18081/upstream/sam3`. The option
   `--sam3 <URL>` of each importer changes it. An answer HTTP 429 or 5xx makes the
   client wait and ask again, as `build_labels.py` does.
8. A full run adds one row to `/Users/ashmelev/Admin/GPU_TASKS.md` first.

## The lab server and the page

1. `/api/dataset` sends the processed file of the card image in `main_image_url`, and
   the original in `main_image_original_url`. A card image with no processed file
   sends the original in both keys.
2. `main_image_derivation` holds `crop`, `seg`, or null. `main_image_width` and
   `main_image_height` hold the size of the file that the card shows.
3. The card shows the badge `crop` or `seg` on the image. The caption stays
   `main · name-unique`.
4. The link `open raw image` of the large view opens the original.
5. The route `/images/` accepts the folder `cropped` too.

## Tests

1. `tests/test_derive.py`: the alpha rule, the thin-line opening, the SAM3 path with a
   fake service, the fallback to the white rule, a service that does not answer, and a
   second call that does nothing.
2. `tests/test_seed_images.py`, `tests/test_seed_patched.py`, `tests/test_lab_server.py`:
   the new tables and the new keys.
3. `tests/test_labdb.py`: schema version 7, and the migration keeps each row.
4. The tests never call the real SAM3 service.

## Open questions

The owner answered questions 1 to 4 on 2026-09-25. See "Decisions of the owner".
Question 5 uses its default.

| # | Question | Default | Other answer |
|---|---|---|---|
| 1 | What does `seg` write? | The SAM3 mask becomes the alpha channel, so the background is transparent. The crop is the box of the mask. | A crop to the box of the bottle alone. The background stays. |
| 2 | SAM3 finds several instances of `wine bottle`. | The union of all instances above the threshold. A card with two bottles keeps both. | The largest instance alone. |
| 3 | The sort by image size uses which size? | The size of the image on the card: the processed file. | The size of the original. |
| 4 | Who changes `seed_patched.py`? | This session. Option C needs the change. The file is unchanged since 2026-09-24 23:37. | The other session. |
| 5 | A change of the settings. | The row of `image_derivative` is replaced. No history. | Keep one row for each settings value. |

## Result on 2026-09-25

The run of `seed_images.py` on `data/lab.sqlite3` (schema 6 before the run):

| Count | Value |
|---|---|
| originals processed | 2,018 in 4 min 25 s |
| `crop` by the alpha rule | 1,875 |
| `crop` by the white rule (SAM3 found no package) | 1 |
| `seg` | 142 |
| SAM3 did not answer | 0 |
| processed files | 2,018 PNG files, 1.2 GB |

- `PRAGMA foreign_key_check` answered no row.
- The Dataset page showed 2,046 processed card images: 1,903 cards with `crop`, 143 with
  `seg`. A file that several wines share counts for each wine.
- A run of `seed_patched.py` on a copy of the database processed the 15 patches:
  `crop` 15. The real database holds no patch yet.

Weak results of `seg`, found with the sort `image size, smallest first`:

| Wine | Result |
|---|---|
| `soyuz-vino-soyuz-vino-muskat-beg-in-boks-beloe-polusladkoe-11`, the `izabella` and the `shardone` bag-in-box of Союз-Вино | SAM3 cuts out the bottle that is printed on the box. The box is the package. |
| `fanagoriya-ice-wine-merlo-rozovoe-sladkoe-10` | The image holds a bottle and its tube. The largest instance is the tube. |
| `ona-skazala-da`, `rozovoe-polusladkoe-2` | A photo of a scene. SAM3 cuts out the bottle; the edge of the second mask is rough. |

The white rule made the crop of the three `soyuz-vino-...-beg-in-boks-...-11/12` wines
that share one image: SAM3 found no package there.

## Code

- `pipeline/imagestore.py`: the store functions of each writer (`sha256_of`,
  `pixel_size`, `store_file`, `store_bytes`).
- `pipeline/derive.py`: the processing, the SAM3 client, `derive_all`, and `write_rows`.
- `pipeline/schema/007_image_table.sql`: the tables.
- `pipeline/seed_images.py` and `pipeline/seed_patched.py`: the option `--sam3 <URL>`,
  and the report lines `processed`, `processed already`,
  `no processing, SAM3 did not answer`, `no processing, not an image`, and
  `processed files written`.
- `pipeline/lab_server.py` and `pipeline/pages/dataset.html`: the processed card image,
  the badge, and the link to the original.

## Gotchas

1. Pillow reads a transparent PNG with the mode `RGBA`, and a transparent WebP too. A
   test picture of the mode `RGB` goes to SAM3. The tests replace `derive.Sam3Client`
   with a fake class, so no test calls the real service.
2. A test that adds a row to `wine_image` MUST add the row of `image` first. The
   foreign key needs it when the connection turns on `PRAGMA foreign_keys`.

