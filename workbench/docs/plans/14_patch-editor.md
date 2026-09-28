# 14 — The patch editor of the Dataset page on the lab database

Date: 2026-09-25.
Status: implemented and deployed on 2026-09-25 by drink-atlas-workspace-7b. The owner
chose the approach on 2026-09-25T09:53:00+0300. The last section and the review of
2026-09-25 (`docs/reviews/2026-09-25_unfinished-work.md`) change some rules.
The owner messages of 2026-09-25T09:46:30+0300 and 2026-09-25T09:48:52+0300 and the
three answers are in [owner-messages.md](../owner-messages.md).

## Goal

1. The patch editor of `/dataset` works on the lab server (port 8168).
2. A person drops an image on a wine. The image becomes the `main_patched` image of the
   wine at once (changed on 2026-09-25: no `Apply` step for a new patch).
3. A person presses `Remove` and `Apply`. The wine goes back to its `main` image.

## Present state

- `pipeline/lab_server.py` sends `"patch_dir": ""` and `"_patched": false` for every
  wine. The page shows `patch_dir is not configured`.
- `pipeline/seed_patched.py` stores the files of the patch folder
  `svoe-wino-hackaton/dataset/patched-official-2026-09-17` as `main_patched` rows. The
  folder is the truth: a row whose wine has no file in the folder is deleted (owner
  answer of 2026-09-24T23:37:09+0300).
- The old tool `scripts/review_server.py` wrote the file into `patch_dir` and moved the
  old file to `patch_dir/.trash`.

## Decisions of the owner (2026-09-25T09:53:00+0300)

1. The database is the truth for the patches. The editor writes the image store and the
   rows. It does not write the patch folder.
2. `Apply` makes the processed file in the same request, with `derive.derive_all`.
3. The change enters the shared tree now, on top of the uncommitted work of the sessions
   a2 and f0, before the flat image store of session 9a [f028b4].

## Rules

1. `POST /api/dataset-patch?slug=<wine_slug>&name=<file name>` with the image bytes as
   the body stores the patch of one wine.
2. The body MUST be a JPEG, PNG, or WebP image of at most 20 MiB. Pillow reads the type
   from the bytes. The `Content-Type` header does not count. These are the types of the
   patch folder (`seed_patched.IMAGE_EXTENSIONS`).
3. A wine of each state MAY get a patch, as in `seed_patched.py`.
4. The file goes to the image store under its SHA-256. A SHA-256 that `image` holds
   already reuses the stored file. The editor writes no second copy.
5. The upload creates the `package` derivative and the `label` derivative for the new
   file. SAM3 can take up to about two minutes. The processing runs before the write
   transaction, so it does not hold the write lock.
6. SAM3 does not answer, or SAM3 finds no label: the patch stays stored. The answer holds
   a `warning` for each missing derivative. To process it later, drop the same file
   again. A derivative with the current settings is reused. The row does not change.
7. The write transaction replaces the `main_patched` row of the wine. The same SHA-256
   changes nothing. `source_name` is the file name of the upload, or `upload` when the
   request holds none. `match_method` is `manual`.
8. `DELETE /api/dataset-patch?slug=<wine_slug>` deletes the `main_patched` row. The file
   and its processed file stay in the store, because the store is content-addressed and
   another row can use the file. No `.trash` is necessary.
9. The answer of both routes holds `patched`, the count `patches`, and `record`: the new
   record of the wine, as `/api/dataset` sends it. The page replaces its record with it,
   so the card shows the new card image at once.
10. The errors are 400 (a bad body or a bad type), 404 (an unknown wine, or no patch to
    remove), 413 (a body larger than 20 MiB), and 503 (no database).
11. `/api/dataset` sends `_patched` and `_patch_url` for each wine. `_patch_url` is the
    store URL of the patch original, not of its processed file. The key `patch_dir` is
    gone. The new key `patch_editor` is `true`. `patches` is the count of
    `main_patched` rows.
12. `scripts/review_server.py` serves the same `dataset.html`. That server sends
    `patch_dir` and serves `/img/patch`. The page turns the editor on when `patch_dir` or
    `patch_editor` is set. It uses `_patch_url` when a record holds it, and `/img/patch`
    when not. So the page keeps its work on the old server.
13. The page keeps its accepted types (JPEG, PNG, WebP, GIF, BMP), because the old server
    accepts all five. The lab server refuses GIF and BMP with HTTP 400.
14. `seed_patched.py` no longer deletes a `main_patched` row whose wine has no file in the
    patch folder. It adds and replaces rows alone. So a patch of the editor stays after
    a seed run. A file of the folder still replaces an editor patch of the same wine.

## Code

- New `pipeline/patches.py`: `store_patch` and `remove_patch`. The store path, the
  `INSERT INTO image`, and the image URL are each in one function, so the flat image
  store of plan 13 changes one line in each.
- `pipeline/lab_server.py`: the routes of `/api/dataset-patch`, `_patched` and
  `_patch_url` in `dataset_records`, the count in `dataset_view`. `make_server` takes a
  `segmenter`; None means `derive.Sam3Client()`.
- `pipeline/pages/dataset.html`: rules 12 and 13. `Apply` sends the file name and takes
  `record` from the answer.
- `pipeline/seed_patched.py`: rule 14.

## Out of scope

- The patch folder in `svoe-wino-hackaton` does not change. Its README table can differ
  from the database after an edit.
- The left figure of a card shows the card image. For a patched wine this is the
  processed patch, so the page shows no `main` image of such a wine. This is the
  present behaviour of `card_images`, and this plan does not change it. Point 2 of
  the last section changes it later.
- A new patch has a new SHA-256, so the Embeddings page shows its items as `missing`
  until a build. This plan starts no build.

## Changes of 2026-09-25 after the first version

The owner asked for these changes on 2026-09-25 (messages of 10:08:37 to 10:24:52, and
the answers of 10:13:53 and 10:23:52 in [owner-messages.md](../owner-messages.md)).

1. A dropped or chosen file goes to the server at once. There is no `Apply` step for a
   new patch. A patch applied by mistake is removed with `Remove` and `Apply`. `Remove`
   keeps its two steps. The old review tool keeps the `Apply` step.
2. The card shows the `main` image at the left and the processed patch in the patch
   slot, side by side. The patch does not replace the `main` image on the card any more.
   `/api/dataset` sends the `main` image in `main_image_*`, and the patch in
   `_patch_url` (the original), `_patch_image_url` (the file of the slot), and
   `_patch_derivation`. Readers such as the embeddings keep the rule of schema file 005:
   `main_patched` replaces `main`.
3. A `crop` whose box is the whole image cut nothing (`lab_server.cut_nothing`). The slot
   shows the original with no badge. On 2026-09-25, 563 of the 1,875 `crop` files of
   `data/lab.sqlite3` cut nothing. A `seg` file keeps its badge, because it removes the
   background.
4. The image preview shows thumbnails at its bottom: `main`, `main · processed`, for a
   patched wine `patched` and `patched · processed`, and two for each alternative photo.
5. The patch `Remove` button has the size of the `Remove` button of the main image and
   stands at the right.
6. A patch upload creates its `package` and `label` derivatives. A missing label cut does
   not cancel the upload. The answer holds a label-specific warning.

Rule 11 changes with point 2: the keys `_patch_image_url` and `_patch_derivation` are new.
Rule 5 still processes the file in the request. It now creates both derivative kinds.
