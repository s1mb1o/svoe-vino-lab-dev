# 22 — The label cut of a full photo, and the vector badge

Date: 2026-09-25.
Status: the owner chose the design on 2026-09-25T12:27:47+0300. The storage follows the
owner answer of 12:28:04 to drink-atlas-workspace-7b: `image_derivative` keeps one cut
for each original and kind. Implemented by drink-atlas-workspace-e3 on 2026-09-25. The
seed ran from 12:46:36 to 13:36:59: 2,019 of 2,023 full originals have a label cut; SAM3
found no label on 4. A `Build` of `gx10-siglip2-so400m-patch16-naflex-p256` at 13:44
left 4 failed items of 4,043. The owner message of
2026-09-25T12:11:50+0300 and the answers are in [owner-messages.md](../owner-messages.md).

## Goal

1. Each item of the view `label` of the Embeddings page gets its model input and its
   vector. Before this plan, each of them failed with `no label cut yet`.
2. Each image cell of the Embeddings page shows the badge `vector` when the vectors file
   holds the row of its item.

## The cause of the failure

- The view `label` starts with `segment target: label`. `embeddings.prepare` needs the
  label cut of the source for this step.
- `embeddings.read_inputs` set `cuts["label"]` to `None` for each source. Plan 10 lists
  the label cut at import under "Work outside this plan", as not started.
- `image_derivative` had the primary key `source_sha256`: one processed file for each
  original. It had no place for a second cut.

## Decisions of the owner

- The label cut of a full photo is stored in the database, not at build time (12:27:47).
  The answer of 12:28:04 puts it in `image_derivative` as a row of the kind `label`, next
  to the row of the kind `package`. Schema file `017_derivative_kind.sql` of 7b adds the column `kind` and the
  key (`source_sha256`, `kind`). This plan has no schema file of its own.
- The badge `vector` shows on a `current` item and on a `stale` item (12:27:47). A stale
  item keeps the vector of its old hash; the status badge tells which.

## The label cut

1. A full original is a file of `wine_image` of the type `main`, `main_patched`,
   `full_front`, or `full_back`. The database holds 2,023 of them on 2026-09-25.
2. `pipeline/seed_label_cuts.py --db data/lab.sqlite3` asks SAM3 for each full original
   that has no label cut of the present settings (`alternatives.SETTINGS_LABEL`).
3. The label rule is the rule of an alternative label photo (plan 16): the nouns
   `alternatives.DETECT_TEXTS`, then `alternatives.label_instance` (the rule of
   `build_labels.py`). `alternatives.label_derivatives` stores the PNG in
   `images/cropped/` and gives the rows. `derive.write_rows` writes them with the kind
   `label`.
4. SAM3 runs outside the write transaction. Each original gets its own short transaction.
   A second run continues the first one.
5. An original with no label gets no row. The next run asks SAM3 again.

Note of 2026-09-25 (drink-atlas-workspace-cb [48de03]; owner messages of 19:10:14 and
19:10:30, answers of 19:16:44 and 20:24:14): a photo with a second body label gets the
box of the labels, not the segment of the largest label. A second label counts when its
centre lies on the largest bottle, when less than 80 % of it lies inside the main label,
and when it has at least 25 % of the area and 60 % of the width of the main label
(`alternatives.body_labels`). The cut is then the crop of the photo to the box around the
counted labels, with no mask (method `crop`, kind `label`). A neck label, a capsule, and a
part of the main label do not count. The new `SETTINGS_LABEL` names the rule, so each
label cut was made again with `seed_label_cuts.py` on 2026-09-25 from 20:30:00 to 20:53:39
(1,419 s): 2,017 cuts, 4 originals with no label; 111 cuts are now `crop`, and the 1,910
`seg` cuts have the same file as before. A label
close-up of `wine_image` (`label_front`, `label_back`) gets the new rule at its next
request, as before. The rule of the measurement is in `ResearchLog.md`.
6. The run stops at the first time that SAM3 does not answer.
7. `embeddings.read_inputs` reads the row of the kind `package` into `cuts["package"]` and
   the row of the kind `label` into `cuts["label"]`. The hash of each label item changes,
   so the next `Build` of an entry makes each label item.

## The vector badge

1. `embedding_routes.entry_view` maps the vectors file that `index.json` names
   (`numpy.load` with `mmap_mode`). A cell gets `vector: true` when its index record
   (current or stale) has a `row` below the number of rows of the file.
2. The page shows the badge `vector` at the bottom left of the cell. The preview names
   `vector` in its second line.

## Tests

- `tests/test_seed_label_cuts.py`: a label cut for each full original, no request for a
  close-up, a second run, a package row that does not count, no label, SAM3 down, the
  limit, and `read_inputs` and `prepare` on the cut.
- `tests/test_embedding_routes.py`: `test_a_cell_with_a_vector_row_gets_vector`.

## Risks

- About 2,023 × 0.6 s ≈ 20 min of SAM3 on gx10 for the first run.
- The flat image store (plan 13) changes the store path. The seed uses
  `alternatives.file_path` and `alternatives.label_derivatives`, so the store code stays in
  one place.
