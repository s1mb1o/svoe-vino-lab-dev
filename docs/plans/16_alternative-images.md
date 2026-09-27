# 16 — Alternative images of a wine on the lab database

Date: 2026-09-25.
Status: implemented and deployed on 2026-09-25 by drink-atlas-workspace-7b. Schema files
`010_additional_types.sql`, `012_type_names_kind_first.sql`, and
`017_derivative_kind.sql`; the lab server on 8168 runs the code since 12:45:39. Approved
by the owner on 2026-09-25T11:02:26+0300. The owner answered four questions
on 2026-09-25T10:58:12+0300.
The owner message of 2026-09-25T10:52:31+0300 ("add support for alternative images"),
the earlier message of 2026-09-25T00:51:57+0300 about the type buttons, and the answers
are in [owner-messages.md](../owner-messages.md).

## Goal

1. The editor `Alternative photos` of `/dataset` works on the lab server (port 8168).
2. A person drops one or more photos on a wine. Each photo is stored at once.
3. The server detects whether a photo shows a full package or a label close-up, and a
   front or a back view (a barcode). It sets one of the four types, and it segments the
   photo.
4. Four buttons below each photo, `FF`, `LF`, `FB`, `LB`, change the type at once, as the
   label buttons of the Testset candidates do. A change between a full type and a label
   type segments the photo again.
5. `×` on a photo stages a removal. `Apply` removes the photo; `Cancel` keeps it.

## Present state

- The lab server sends `"alternative_dir": ""` and `"_alternatives": []`. The page reads
  `alternative_dir is not configured`.
- The schema allows the types `front`, `back`, `label_front`, and `label_back`. No row of
  `data/lab.sqlite3` uses them. `alternative_dir` of the old tool
  (`svoe-wino-hackaton/dataset/derived/additional`) holds no photo, so nothing is imported.
- `pipeline/embeddings.py` knows both sets of names (`ROLES`). Plan 10 lists the type
  buttons as not started.
- `pipeline/derive.py` cuts the package alone. Its SAM3 texts are fixed. No code cuts a
  label at import.

## Decisions of the owner

| Question | Answer |
|---|---|
| Adding | Instant, like patches. |
| Type names | Rename in a schema file: `full_front`, `label_front`, `full_back`, `label_back`. |
| Processing | Detect full package or label, set the type, then segment. A change between full and label segments again. |
| Buttons | 2×2 short codes `FF`, `LF`, `FB`, `LB`, with the full name as the tooltip. |

## Rules

### Types and schema

1. A new schema file `NNN_additional_types.sql` builds `wine_image` again with the types
   `main`, `main_patched`, `full_front`, `label_front`, `full_back`, `label_back`. It maps
   the old names to the new names. It keeps each row and the index `wine_image_one_main`.
2. `labdb.IMAGE_FOLDERS` maps the four new types to the folder `additional`, in place
   of the old names. The old names cannot be stored any more. The test fixtures that
   stored an old name use the new name.
3. The number of the schema file is fixed when the file enters `pipeline/schema/`
   (rules 25 to 28 of `AGENTS.md`). The flat image store of drink-atlas-workspace-9a
   [f028b4] also waits for a number. The two sessions agree the order.

### Upload

4. `POST /api/dataset-alternative?slug=<wine_slug>&name=<file name>` with the image bytes
   stores one photo. The body rules are the rules of a patch: JPEG, PNG, or WebP, at most
   20 MiB, the type read from the bytes.
5. The file goes to `images/additional/<sha256>.<extension>`, or reuses a stored file with
   the same SHA-256. `source_name` is the file name, `match_method` is `manual`.
6. The server detects the kind (rule 10) and the side (the last section), writes the
   row with one of the four types, and segments the photo for that kind (rules 12 and
   13). SAM3 runs before
   the write transaction.
7. The same photo on the same wine a second time changes nothing and answers the present
   row.

### Type change and removal

8. `POST /api/dataset-alternative-type` with `{"slug", "sha256", "type"}` changes the type
   of one row. A change between a full type and a label type segments the photo again. A
   change between front and back keeps the processed file.
9. `DELETE /api/dataset-alternative?slug=<wine_slug>&sha256=<sha256>` deletes one row. The
   file and its processed file stay in the store.

### Detection

10. SAM3 gets the texts `barcode, bottle, label, bottle neck, can`, threshold 0.35, long
    side 1536 px. The owner chose the first four for a quick classification and kept
    `can` for the can rule (2026-09-25T11:45:49 and 11:47:17). The photo is a full package when one of these holds:
    - a real bottle neck: its box lies inside the box of the largest bottle, its top is
      below 2 % of the height, its bottom is above 50 % of the height, and it is not
      wider than 0.7 of that bottle;
    - a can whose box covers at least 90 % of the height, and the photo is at least two
      times as tall as it is wide.
    Else the photo is a label close-up.
11. SAM3 does not answer: the type is `full_front`, the photo has no processed file, and
    the answer holds a warning. Each later request for the photo (the same file again, or
    a type change) processes it when it has no current cut of its kind.

### Segmentation

12. A full type: the processing of `derive.py`, unchanged (alpha crop, SAM3 package, or
    white crop).
13. A label type: the largest label instance that is not the package itself, with the
    rules of `svoe-wino-hackaton/scripts/build_labels.py` (`is_package`, the duplicate
    rule, the area before the score). In a close-up the label can fill the frame and equal
    the bottle box; then the largest label instance counts. The mask is smoothed as in
    `derive.py` and becomes the alpha channel (`seg`). No label instance: no processed
    file.
14. `image_derivative` keeps one processed file for each original and kind of cut
    (`package`, `label`; schema 017, owner answer of 2026-09-25T12:28:04). A full type
    shows the package cut, a label type the label cut. A file that is a patch and a label
    photo keeps both cuts, and a change back to a kind reuses its cut. Before schema 017
    one cut stood for each original, and the last writer won.

### Page and API

15. `/api/dataset` sends `_alternatives` for each wine: a list of `{sha256, type, url,
    image_url, derivation}` in the order of the upload. `alternative_editor` is `true`,
    and `alternatives` is the count of rows. The key `alternative_dir` is gone.
16. The page shows the photos in the grid of the editor (64 px cells), each with the badge of
    its processing (the rule `cut_nothing` of plan 14 applies) and the 2×2 buttons below
    it. The button of the present type is filled.
17. The page keeps its work on `scripts/review_server.py`: that server sends
    `alternative_dir` and file names, and the page keeps the old path for it.

## Code

- `pipeline/derive.py`: `Sam3Client` takes the SAM3 texts as an argument, and a new
  method answers all instances. The present behaviour stays the default. This file is
  held by drink-atlas-workspace-8b (the A/B decision) and 9a [f028b4] (store paths); the
  change needs their agreement.
- New `pipeline/alternatives.py`: store, detect, segment, change the type, remove.
- `pipeline/lab_server.py`: the three routes, `_alternatives` in `dataset_records`, the
  keys in `dataset_view`.
- `pipeline/pages/dataset.html`: `alternativeEditor` and its handlers.
- Tests: new `tests/test_alternatives.py`; `tests/test_labdb.py` for the schema version.

## Evidence for rule 10 (probe of 2026-09-25, 17 images, read-only SAM3 calls)

| Images | Expected | First probe: the neck rule alone |
|---|---|---|
| 12 catalogue `main` images (11 bottles, 1 can) | full | 11 of 12. The can has no neck. |
| 4 label crops of catalogue images | label | 4 of 4 |
| The patch photo of `avtohtonnoe-vino-kryma-beloe-suhoe` (upper half of a bottle, other bottles behind it) | label | full: the necks of the bottles behind it counted |

Rule 10 adds the can test and the test "inside the largest bottle" for these two
failures. "Inside" allows 2 % of the width and of the height. A second probe of rule 10
as written gave 17 of 17: 12 of 12 full, 4 of 4 crops, and the patch photo as a label.
The rule was fitted to these same 17 images, so this result does not measure its
accuracy. The accuracy on real alternative photos is not known: the probe set is small,
and 16 of the 17 photos are catalogue studio pictures or crops of them. A wrong type
costs one click.

## Changes of 2026-09-25 after the first version

1. A barcode gives the back types (owner message of 11:26:11). SAM3 gets the noun
   `barcode` too. A barcode counts when its score is at least 0.7, its width is at least
   10 % of the largest bottle or can, and its centre lies on that package (`side`). A
   photo with no package counts each barcode of that score. The type is `full_back` or
   `label_back`. A probe of 16 random FRAP photos gave the side that a person would give
   for 13 or 14 of them: a barcode on a hanging tag gave `back`, and the back of a
   decanter without a barcode gave `front`. The two limits came from two errors of that
   probe, so the probe does not measure their accuracy. 15 lab photos with no back view
   (12 catalogue images, 3 owner photos) gave no back type.
2. The names put the kind first (owner message of 11:27:30, answer of 11:28:52): schema
   file `012_type_names_kind_first.sql` renames `front_full`, `front_label`,
   `back_full`, `back_label` to `full_front`, `label_front`, `full_back`, `label_back`.
   The buttons read `FF`, `LF`, `FB`, `LB`. `pipeline/embeddings.py` knows the six names
   of the schema alone.
3. The nouns (owner message of 11:45:49, answer of 11:47:17): `barcode, bottle, label,
   bottle neck, can`. The noun `wine bottle label` is gone, so the label cut uses
   `label` alone. On 7 test images the five nouns took 4.4 s, the six nouns before 5.2 s,
   the four nouns alone 3.9 s; the four alone gave a can `label_front`.

## Out of scope

- The embeddings: a new alternative photo appears on the Embeddings page as a `missing`
  item until a build. A label close-up enters the view `label` as it is (plan 10).
- The preview of the alternative photos. drink-atlas-workspace-0b adds it (owner message
  of 2026-09-25T11:19:38).

## Changes of the review of 2026-09-25

The review (`docs/reviews/2026-09-25_unfinished-work.md`, section 7b) found these defects;
they are fixed:

1. One cut for each original and kind (rule 14).
2. The row of `image` holds the size of the file, not the size of the SAM3 copy.
3. A photo with no current cut of its kind is processed again on the next request (rule
   11); the warning of a type change names the missing cut of the new kind.
4. The page: a patch dropped while the last one of the wine is processing is refused with
   a message; `Cancel` takes back the marked removals alone and lets the uploads go on;
   `×` is disabled while a type change of the photo runs.
5. An unexpected error of the patch and alternative routes answers HTTP 500 with a JSON
   error. An upload of more than 100,000,000 pixels answers HTTP 413. A JSON body with a
   lone surrogate character answers HTTP 400 on every route.
6. `seed_patched.py` refuses a table with `main_patched` rows unless `--force` (owner
   answer of 12:28:04).

## Change of 2026-09-26: the largest label in a label close-up

Owner message of 2026-09-26T19:38:53+0300, answer of 19:47:16 ("Close-ups: largest").
This change replaces the bottle test of rule 13 for a label type.

1. In a label close-up (`label_front`, `label_back`), the largest label instance is the
   main label. The bottle test of `build_labels.py` does not apply.
2. Reason: in a close-up the bottle fills the frame. The box of the real label is then
   close to the box of the bottle. On the photo `d9f847bd…` of
   `vysokij-bereg-risling-zelenaya-seriya`, the IoU was 0.84, above `BOTTLE_IOU` 0.80. The
   bottle test dropped the real label (1,353,980 px) and kept a QR sticker (176,368 px).
3. A full photo (`main`, `main_patched`, `full_front`, `full_back`) keeps the bottle
   test. The embedding runner keeps it for a test photo, because a test photo has no type.
4. The cut of a close-up has the settings `alternatives.SETTINGS_LABEL_CLOSE_UP`. The text
   of `SETTINGS_LABEL` did not change, so the label cuts of the full photos stay current.
   A close-up cut with `SETTINGS_LABEL` is processed again on the next request.
