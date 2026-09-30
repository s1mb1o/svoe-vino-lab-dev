# Plan 94: the checkbox `generate label` of an image

Date: 2026-09-30

Source: the owner message of 2026-09-30T20:38:00+0300 and the answers of about 20:46 and
21:59 (`docs/owner-messages.md`).

## Request

```text
in wine image properties add checkbox [x] generate label (by default - generate), if not defined -> generate, but if explicitly unchecked - do not generatae
```

The owner selected these answers:

- "generate label" is the SAM3 label cut: the row of `image_derivative` with the kind
  `label`. It is not the VLM label description of plan 61.
- The value is a column of `image_description`.
- An uncheck removes the automatic label cut. A manual cut of plan 56 stays.

## Values

1. The new column `image_description.generate_label` holds NULL, 1, or 0.
2. NULL means "not set". The label cut is made as before.
3. 1 means "checked". The label cut is made as before.
4. 0 means "unchecked". The label cut is turned off for this image.
5. The value belongs to one image file (its `sha256`), as each value of
   `image_description`. Each wine that links the file gets the same value.

## Schema

6. The new file `pipeline/schema/NNN_generate_label.sql` adds the column:
   `generate_label INTEGER CHECK (generate_label IN (0, 1))`. The number is fixed at the
   entry (rules 25 and 26).
7. The file changes no row. Each present image keeps NULL, so each image keeps its label
   cut.
8. The views `matcher_wine` and `matcher_wine_image` do not change.

## The dialog `Image description` of `/dataset`

9. The form gets the checkbox `generate label` after `presentation_mode`.
10. The box is checked when the value is NULL or 1. The box is clear when the value is 0.
11. `Save` sends `generate_label` only when the owner changed the box. So a value that
    is not set stays NULL after a save of the other fields.
12. The title of the box states the effect: "Unchecked: no SAM3 label cut for this image.
    A save removes the automatic label cut. A manual cut stays."

## The route `POST /api/image-description`

13. `values` MAY hold `generate_label`: `true`, `false`, or `null`. Another value gives
    HTTP 400.
14. `true` stores 1. `false` stores 0. `null` stores NULL.
15. With `false`, the same transaction deletes the automatic label cut of the image: the
    row of `image_derivative` with the kind `label` and settings that do not start with
    `derive.MANUAL_PREFIX`. The processed file stays in the image store.
16. The answer holds `label_cut_removed` (true or false). When it is true, the answer
    also holds `records`: the new record of each wine that links the image. The page
    merges each record, as the recut route does.
17. A save of `true` or `null` makes no SAM3 call. The next writer of rule 19 makes the
    cut again.

## The writers of a label cut

18. `alternatives.process_image` with the kind `label` returns at once when the value is
    0. It sends no SAM3 request and writes no row. The result has `turned_off = True`.
    `write_processed_rows` then keeps the not-applicable marker of schema 021 as it is.
19. This rule covers each writer, because each writer calls `process_image`: the upload
    and the type change of an alternative photo, the recut, the reset of a manual cut, a
    patch upload (`patches.py`), a manual wine (`manual_wines.py`), the website import
    (`import_website.py`), `pipeline/seed_label_cuts.py`, and
    `scripts/prepare_rerun_label_inputs.py`.
20. A turned-off result gives no warning `NO_LABEL_CUT` and no warning
    `NO_PROCESSED_FILE`: the absence is the wish of the owner. `alternatives._warn`,
    `alternatives.full_label_cut`, and `patches.py` check `turned_off`.
21. `alternatives.has_current_cuts` counts a turned-off label cut as present. So a
    request does not process the photo again only for its label cut.
22. `seed_label_cuts.py` leaves each turned-off original out of the to-do list. The log
    and the report state the count: `label cut turned off: N`.

## The readers of a label cut

23. `embeddings.read_inputs` marks the label view of a turned-off full original as not
    applicable, with the reason "the owner turned off the label cut". The embedding
    build then makes no label item for it and does not count it as missing. The matcher
    bundle, the clusters, the catalogue copy, and the index of a new wine read the same
    function.
24. A turned-off original with a manual label cut keeps its label item: the manual cut
    is the work of the owner.
25. `read_inputs` still works on a database with no column `generate_label`. It then
    sees no turned-off image.
26. The card, `image_details.py`, `clusters.py`, and `scripts/normalize_glass.py` need no
    change. After rule 15, they find no automatic label cut.

## Limits

27. An uncheck changes no present embedding index. The label vector of the image stays
    in each index until the next build of that index.
28. A label close-up (`label_front`, `label_back`) that is turned off has no processed
    file. Its card shows the original. Its embedding does not change: a close-up uses
    the original with no cut.
29. The label cut of a query photo during a run (`embedding_run.py`) does not read the
    value. A query photo is not a catalogue image.

## Tests

30. The new file `tests/test_generate_label.py` checks: the schema column and its CHECK;
    the route values `true`, `false`, `null`, and a bad value; the removal of an automatic
    cut and the stay of a manual cut; `process_image` with no SAM3 call; no warnings;
    `has_current_cuts`; `seed_label_cuts.py`; and `read_inputs`.
31. The suites `test_alternatives.py`, `test_alternative_recut.py`, `test_patches.py`,
    `test_seed_label_cuts.py`, `test_embeddings.py`, `test_image_descriptions.py`, and
    `test_lab_openapi.py` still pass.
32. A browser check of the dialog: the box, a save of each state, and the card of a
    label close-up.

## Rollout

33. Order: the schema file, the migration of `data/catalog/catalog.sqlite3` with
    `pipeline/labdb.py`, the code, and a restart of 8168 (rule 27). A backup of the
    database comes first.
