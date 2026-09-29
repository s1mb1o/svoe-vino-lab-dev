# Plan 82: max-over-rotation matching (rotated reference embeddings)

Date: 2026-09-29. Project: `svoe-vino-lab` — lab `workbench/` (W) and production `matcher/`
(M). Session: drink-atlas-workspace-b6. On approval, this file is copied to
`W/docs/plans/82_rotated-reference-embeddings.md` (81 is `81_android-built-in-pack.md`
of another session).

## Context

The rotation tests of 2026-09-29 (`W/docs/reports/rotation-similarity-2026-09-29.md`,
`rotation-dinov3-2026-09-29.md`) showed: a rotated bottle loses much similarity to its one
index vector (NaFlex p512: mean 0.79 over the angles, minimum 0.70); reference vectors of the
rotated catalogue image over the full circle bring it back to 0.96–0.99. The owner asks for
the method in the product (owner messages in plan mode, 2026-09-29):

1. Offline: for each catalogue image, embeddings every 5–10°; an option defines the angle.
2. All rotated embeddings keep the same `wine_slug` / `image_sha256`.
3. Online: one embedding of the detected bottle crop.
4. Search against the rotated reference embeddings.
5. Collapse by wine / image with the maximum: S(q, x) = max_θ cos(E(q), E(R_θ(x))).
6. Store the angle of each rotated vector; a later feature MAY use it to detect the angle
   of the candidate bottle.

Owner answers: lab and matcher; NaFlex p512 entries with 5° and 10°; the lab builder with
parallel requests builds the indexes; the matcher query input is a config choice; the
matcher gets both the catalogue-copy path and bundle format 3. This replaces the task 7
constraint "no change of lab code or config.yaml" (answer of 07:06:38).

Evidence on the real test set `my` (2,226 queries, 1,647 positive): the offline baselines
repeat the official runs exactly — `siglip2-p512-crop` R@1 79.48 %, R@5 96.11 %;
`siglip2-p512-as-is` R@1 74.26 %, R@5 94.11 %. The offline 5° vectors
(`W/work/rotation-index/`) finish at about 08:40 (gate G0).

## Existing code that already does most of the work

- `embedding_run.Catalogue.rank` (`W/pipeline/embedding_run.py:360-403`) and the matcher
  `Bundle.top1/ranked` (`M/bundle.py:59-82`) take `np.maximum.at` over all rows of a wine.
- `M/bundle.load_bundle` (`M/bundle.py:114-177`) reads `candidates.jsonl` + `vectors.npy`.
- The matcher query choice exists: pipeline key `hand_selection` (`M/service.py:126, 160-163,
  233-237`; `M/config.yaml:25`): `true` = SAM3 main package, masked crop on white (lab twin
  `crop-seg`); `false` = the photo as it is (lab `as-is`). One query vector. No new query
  code. (Known: `M/docs/known-issues.md` item 2, HTTP 400 for a damaged image.)
- The rotation method: `W/scripts/rotation_similarity.py` `rotated()`/`scale_of()`;
  `W/scripts/rotation_index_build.py` (0° = the index PNG, checked on 2,270 images).
- Fixtures: `W/tests/embedding_lab.py` (`Lab`, `add_entry(**values)`, `FakeGateway` records
  each request and returns mean RGB + width + height), `quiet_backend`
  (`W/tests/test_build_embeddings.py:20-22`).

## Design

### 1. Config

- New entry key `rotation_step` (int degrees, 1–180) in `embeddings` of `W/config.yaml`.
  Angles 0°, step, … < 360° for the view `full` (counter-clockwise, white fill, the canvas
  grows, the 0° scale of `resize`). Label view, close-ups, and queries stay unrotated.
  Entry-level key: a view spec allows only `steps` (`embeddings.py:131-132`) and
  `&views_c_f` is shared by 12 entries.
- `Embedding.__init__` (`embeddings.py:202`; `ENTRY_KEYS` line 52): int, not bool, 1–180;
  the view `full` exists; no `square_on_white`, no `segment_dis`; a `resize` step is last
  with `aspect: keep`; `batch_size` ≥ 2. `summary()` adds the key only when set.
- New entries at the END of `embeddings:` (Build All runs in config order,
  `embedding_routes.py:10-12`), with the view `full` only (new anchor with the `full` steps
  of `*views_c_f`) and `batch_size: 36`: `gx10-siglip2-so400m-patch16-naflex-p512-rot5` (`rotation_step: 5`,
  72 angles) and `…-p512-rot10` (`rotation_step: 10`, 36 angles).
- New pipelines (no barcode, no rerank, own `views`, one `full` query vector):
  `siglip2-p512-rot{5,10}-as-is` (`*as-is-views`), `siglip2-p512-rot{5,10}-crop`
  (`*crop-views`), `siglip2-p512-rot{5,10}-crop-seg` (`*crop-seg-views`), and the unrotated
  `siglip2-p512-crop-seg` (the lab twin of `hand_selection: true`).

### 2. Rotated model inputs (one function)

Models: SAM3 runs one time on the original catalogue image, at import (the stored package
cut, plan 09); it does not run on the rotated images. The rotation is geometric (PIL, no
model). The only model on each rotated image is the embedding model of the entry (SigLIP2
so400m NaFlex, `max_num_patches` 512). The 0° source is already cropped and segmented: the
view `full` steps are `segment` (crop to the SAM3 box), `remove_background` (the SAM3 mask),
`white_background`, then `resize`; the rotation takes the image after `white_background`.
Evidence: the offline build checked 1,747 of 2,270 images so far — 0° pixels equal to the
index PNG of `…-naflex-p512` in all of them, cosine to the index vector 1.0.

`embeddings.rotated_inputs(item, source_path, angles)`: the steps before `resize` through
`apply_steps` (unchanged, shared with the query side); per angle
`Image.rotate(angle, BICUBIC, expand=True, fillcolor=(255, 255, 255))`, then the fixed 0°
scale of `resize` (`round(w·s), round(h·s)`, LANCZOS) and the transparency check. At 0° it
MUST equal `prepare()` pixel for pixel. `scripts/rotation_similarity.py` imports it.

### 3. Index record: one record per image and view, several rows, one angle per row

- The record keeps `row` = the 0° row and gets `angles: [0, 5, …]`; rows are
  `row … row + len(angles) − 1`; row `row + i` is the vector of `angles[i]`. No `angles` =
  one row at 0° (today's format), so a mixed index stays valid.
- `embeddings.record_rows(record, count)` → a `slice` (a view, not a copy);
  `record_angles(record)`. Validation: `angles` is a list of distinct ints 0 ≤ a < 360 with
  `angles[0] == 0`; `row + len(angles) ≤ count`. `angles` always comes from the stored
  record, never from the current `rotation_step`.
- `read_vectors` (`embeddings.py:647-650`) and `M/catalog._read_vectors` (`M/catalog.py:96-101`):
  the records sorted by `row` cover `[0, N)` with no gap and no overlap; errors raise
  `ValueError` / `CatalogError` (never `TypeError`). The bounds checks at
  `embedding_run.py:292`, `matcher_bundle.py:268-270`, `M/catalog.py:185` use the range.
- Readers that keep the 0° row by design: `clusters` (`clusters.py:194, 305`),
  `embedding_routes.entry_view` (253-255), `new_wine_workflow.verify` (98-99), `selftest`
  (through `Catalogue`), `run_steps._index_state`, `candidate_items`.
- `view_config_hash` (`embeddings.py:261-271`) adds `{"rotation_step": s,
  "rotation_version": 1}` only when set, for view `full` and role `full`. Present hashes do
  not change; `STEPS_VERSION` stays.
- Only the 0° prepared PNG is written (`images/<sha>_full.png`). Known: `FIX_LATER.md`
  item 1 — each new entry keeps its own copy of the PNG files (about 0.46 GB each); no fix.
- Not for Android (`android/tools/verify_model_vectors.py:78-102` assumes one row).

### 4. Build (`W/pipeline/build_embeddings.py:187` `run`)

- `kept[key]` is always 2-D: old records `vectors[record_rows(r)]` (a bad record is dropped
  alone and its item rebuilt; the index is not discarded), a new plain vector `v[None, :]`.
- `checkpoint()` (247-265): filter `block.shape[1] == dim`; `row` = running offset; `angles`
  written for multi-row blocks and removed for one-row blocks; assert
  `block.shape[0] == len(angles or [0])`.
- Items without rotation (every present entry) keep today's batched loop unchanged.
  Rotated items: `--workers N` items in parallel (new CLI flag, default 1). Each item runs
  in a worker thread: its rotated PNGs come from a process pool of N (the rotation and the
  PNG encoding hold the GIL; threads gave about 1.6 cores in the offline probe), then its
  ceil(n / `batch_size`) near-equal chunks go to the model one after the other (no request
  of one image; one backend per thread). The item is kept only when all its rows come back;
  any failure fails the whole item. Owner message of about 08:19: gx10 has free capacity,
  so the rotated entries use `batch_size: 36` (2 requests per image at 5°, 1 at 10°) and the
  builds run with `--workers 6`.
- Worker threads return results and exceptions; only the main thread calls `fail()`,
  `emit()`, and `checkpoint()`. `Stop` is checked before each new item; on stop, the pools
  shut down with `cancel_futures=True`; a partial item never enters `kept`.
- The request PNGs use the default level (`compress_level=1` gains little).
- Checkpoint interval: max(`checkpoint_seconds`, 20 × the last checkpoint duration).
  `write_checkpoint` (`embeddings.py:654-671`) skips the vector write when the
  content-hash file name already exists and uses `buffer.getbuffer()` (no extra copy), so
  a no-op build before each run (`rebuild_embeddings_on_run`) does not rewrite 0.76 GB.
- `emit("progress")` keeps its fields (items) and adds `vectors`.

### 5. Lab search (`W/pipeline/embedding_run.py`)

- `Catalogue.__init__` (291-300): each current record gives its rows (a slice) for each
  owner wine; one item dict per (image, wine) is shared by its rows plus a per-row angle
  array; `angle` appears only for records with `angles` (the key sets of
  `tests/test_embedding_run.py:250,258,662` stay). `state` adds `rotation_step` and the
  row count. `rank` stays.
- `items_of` (328-343): one item per image (the best row) with its `angle`; `view_top`
  (345-358) adds the `angle` of the best row. `results.jsonl` stays at about the baseline
  size; `/runs` shows one button per image.
- Each candidate of a rotated entry gets `angle` = the angle of its best `full` row (argmax θ
  of S(q, x)) — the value a later angle detection reads.

### 6. Matcher: catalogue copy and bundle v3

- `M/catalog.py`: `_read_vectors` validates the coverage (§3); `load_catalog` (181-195)
  appends every row of a record for each owner and fills a new optional `Bundle` field
  `angles` (view → int array aligned with the rows; None when no record has `angles`).
  `W/pipeline/catalog_copy.py` `_load_with_matcher` then sees the rotated rows. Known
  effect (doc note): `copy_catalog` without `--embedding` copies every entry (+1.15 GB).
- Export (`W/pipeline/matcher_bundle.py` `_build_in` 255-310): a rotated entry writes format
  version 3: one `items.jsonl` row per vector row with `angle` (0 for an unrotated row) and
  `source_vector_row` of that angle; one candidate per (vector row, owner wine); with
  `include_images`, the 0° PNG one time per image. Counts: `items` = item rows,
  `planned_items` = planned (source, view) pairs; the v3 check is `planned_items` = distinct
  (source, view) of the items + omissions. `scoring` stays. Unrotated entries write v2
  exactly as today. `_validate_records` v3: the unique key (source, view, angle), `image`
  may repeat for the same source; `_validate_vectors` stays (one item row per vector row).
- `M/bundle.py`: `FORMAT_VERSIONS = (1, 2, 3)`; v3 also checks and reads `items.jsonl` for
  `Bundle.angles`; the ranking stays. `M/tests/test_siglip2.py:321`: the "unsupported"
  example 3 → 4.
- The API answer keeps its schema (`MatchCandidate` `extra="forbid"`, `openapi.yaml`); the
  stored angles let a later feature return the bottle angle. Production stays on the v2
  bundle (`M/config.yaml:17`); an old matcher refuses v3 (safe).

### 7. Out of scope

Label view and close-up rotation; a partial range; the 1° sets; an angle in the matcher API;
a UI field for `rotation_step` on `/embedding`; any change of the gx10 production deployment;
the known problems of `FIX_LATER.md` and `M/docs/known-issues.md` (rule 41).

## Order of work

0. Record the owner messages and answers (`W/docs/owner-messages.md`). Update my section of
   `W/ACTIVE_WORK.md` (task 8 = this plan, the files below). Send session e3 (alive; its
   section lists `M/tests/test_siglip2.py`, `test_match.py`, `README.md`, `TESTING.md`,
   `ChangeLog.md`) a message: my hunks there are small and separate (one line in
   `test_siglip2.py`; new matcher tests go to a new file `M/tests/test_rotation.py`).
   The stale sections `66`, `codex-side-matcher-bundle`, `codex-android-embeddings`, `31`,
   `codex-main-scene-ranking`, and `root` list W/M files of this plan; git shows no pending
   change in those code files; the approval of this plan is the owner permission (rule 21).
   `W/config.yaml` has a pending `new_wine_embedding` hunk of `/root`: my hunks are separate.
   Copy this plan to `W/docs/plans/82_rotated-reference-embeddings.md`.
1. G0 (about 08:40): `python3 scripts/rotation_index_eval.py --replay-only --sets 0:355:5
   0:180:5` → R@1/R@5/false match against the baselines, to the owner. If R@1 falls for
   both query sides, wait for the owner; else continue.
2. Lab code §2–§5 + tests; the full W suite passes; the hash check (Verification) passes.
3. Ask the owner for an 8168 restart (rules 22-24; it also deploys the pending code of
   other sessions: `pipeline/lab_server.py`, `lab_openapi.py`, `new_wine_workflow.py`,
   `pages/dataset.html`). Without it, the Embeddings page shows the new entries with
   "unknown key" and the CLI still works.
4. `config.yaml` hunks: the two entries at the end of `embeddings:`, the 7 pipelines.
5. GPU_TASKS row; build `…-rot10`, then `…-rot5`:
   `caffeinate -ims ~/.venvs/svoe-vino-lab/bin/python pipeline/build_embeddings.py
   --name <entry> --workers 6` (81,720 + 163,440 vectors; estimate 1–2 h).
6. Runs on `my` (a `--limit 3` smoke run first): `python3 pipeline/embedding_run.py --name
   <p> --set my --workers 8 --label plan82` for the 7 new pipelines.
7. Matcher §6 + tests; a scratch v3 bundle of `…-rot5` (`scripts/build_matcher_bundle.py
   --embedding … --out <scratch>/bundle-rot5`, `scripts/validate_matcher_bundle.py`); load
   it and the scratch catalogue copy with M; rank 20 photos of `my` as it is.
8. Report `W/docs/reports/rotation-index-p512-2026-09-29.md` and the docs. No commit
   without the owner.

Rules during the work: the lab server spawns the build and run scripts from disk, so each
code edit is live for other sessions (the present entries MUST behave the same; the suite
runs before the code lands). One GPU job of this session at a time; the builder retries
HTTP 429. `rebuild_embeddings_on_run` builds a rotated entry before its runs, and waits for
a build in progress (`rebuild_on_run.py:130-136`) — in the docs.

## Files

- W code: `pipeline/embeddings.py` (also the docstring line 10), `pipeline/build_embeddings.py`,
  `pipeline/embedding_run.py`, `pipeline/matcher_bundle.py`, `config.yaml` (separate hunks),
  `scripts/rotation_similarity.py`.
- W tests: `tests/test_embeddings.py`, `tests/test_build_embeddings.py`,
  `tests/test_embedding_run.py`, `tests/test_matcher_bundle.py`, `tests/test_catalog_copy.py`,
  `tests/test_pipelines.py`.
- M: `bundle.py`, `catalog.py`, `tests/test_rotation.py` (new), `tests/test_siglip2.py` (one
  line), `tests/test_catalog.py`.
- Docs: `W/ChangeLog.md`, `W/ResearchLog.md`, `W/SMOKE_TESTS.md`, `W/COMMANDS.md`,
  `W/README.md`, `W/docs/API.md` (item keys near line 474, the trace `top`),
  `W/docs/testing/matcher-bundle.md` (v3), `W/docs/plans/10_…` and `72_matcher-bundle.md`
  (one note each), `M/ChangeLog.md`, `M/README.md`, `M/TESTING.md` (bundle v3, the test count).

## Verification

- W unit tests (system `python3 -m unittest discover -s tests -p 'test_x.py'`; compare
  `Ran N` with the `def test_` count):
  - `rotation_step` parsing: 5 and 10 valid; bool, 0, 181, a string, `square_on_white`,
    `segment_dis`, no `full`, `aspect: ignore`, `batch_size: 1` rejected;
  - `rotated_inputs(…)[0]` equals `prepare()`; 90° gives the transposed size; 45° the
    expanded canvas; the 0° scale is kept;
  - build with `FakeGateway`: `rotation_step: 90` → `angles == [0, 90, 180, 270]`, row
    `row + i` = the vector of `angles[i]` (90° and 0° rows differ), one PNG per item, every
    request ≥ 2 images; label items still batched; `--workers 3` gives the same index as 1;
    a second build builds nothing and keeps the vector file name; a stop mid-build resumes
    with consistent records; a changed step makes the items stale; a mixed and a malformed
    index are handled (a bad record rebuilt alone);
  - `read_vectors` coverage errors (gap, overlap, bad `angles`) raise `ValueError`;
  - `Catalogue.rank` = max over rows; `items_of` one item per image with `angle`; a query from
    the 90° input of a catalogue image gets its wine first with the candidate `angle == 90`;
    present key-set tests unchanged;
  - bundle: a rotated entry exports and validates as v3 (counts, angles), a plain entry is
    byte-identical v2; `catalog_copy` copies and loads a rotated entry;
  - `ProjectConfigTest`: the two entries and the 7 pipelines are valid.
- M tests (`~/.venvs/svoe-vino-lab/bin/python -W error::ResourceWarning -m unittest discover
  -s matcher/tests -v`, from `M/TESTING.md`): v3 `load_bundle` with `Bundle.angles`; v1/v2
  `angles` None; `load_catalog` multi-row with angles; a bad `angles` → `CatalogError`; a
  rotated query ranks its wine first; version 4 rejected; all 118 + new tests pass.
- The full W suite (about 105 s) passes.
- Hash check (read-only, before the code lands): for each present entry with an index,
  `index["view_config_hash"][v] == view_config_hash(v)`, `index["config"] == summary()`,
  and the `item_status` counts equal those of the old code.
- Live: 0 build failures; 2,270 × 72 (36) rows; every rot5 row matches the offline
  `work/rotation-index/…/<sha>.npz` row of the same angle (cosine ≥ 0.9999; Pillow 12.3.0 in
  the venv vs 12.2.0 offline); the 0° PNG has the sha256 of the p512 PNG; the lab run metrics
  of `rot5-crop`/`rot5-as-is` match the G0 replay within 1–2 queries; `results.jsonl` about
  the baseline size; the scratch v3 bundle ranks a stored 0° row's own wine first.
- Report table: R@1/R@5/R@10/MRR/false match at 1 for as-is, crop, crop-seg × {1 vector,
  10°, 5°}; plus the share and the precision of confident answers at the Telegram bot
  thresholds (`BOT_MATCH_MIN_SCORE` 0.70, `BOT_MATCH_MIN_MARGIN` 0.015), because
  max-over-rotation raises the top and the competing scores.

## Deviations during the work

- The experiment scripts (`scripts/rotation_similarity.py` and the scripts that import it)
  keep their own copy of the rotation code. The math is the same; the canonical code is
  `embeddings.rotate_fixed_scale` and `embeddings.rotated_inputs`.
- The builder reads an index with rotated records leniently (`read_vectors(strict=False)`)
  and builds a bad, overlapping, or mismatched record again alone (review finding 4).
- The plan number is 82: the number 81 was taken by `81_android-built-in-pack.md`.
- The new tests went into two new files: `tests/test_rotated_embeddings.py` (24 tests) and
  `../matcher/tests/test_rotation.py` (6 tests). The present test files did not change.
  The check of the new config entries and pipelines was a live load of `config.yaml`
  (0 entry errors, 0 pipeline errors), not a new `ProjectConfigTest` case.
- The owner stopped the 10° work at 10:17:26 ("no 10° runs when the 5° runs exist"): the
  entry `…-rot10` holds 767 of 2,270 images and has no run.
