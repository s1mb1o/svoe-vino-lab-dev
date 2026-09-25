# Active work of the sessions

This file shows the present work of each agent session of this project. The rules are in
[AGENTS.md](AGENTS.md), section "Work of the sessions". In short:

- Read this file before you change a file.
- Keep one section for your session. Change your own section alone.
- Do not change a file that another section lists. Send that session a message.
- Remove your section when your work is committed.

The form of a section:

```text
## <session name>

- Task: <one line>
- Source: <a plan, or the time of an owner message>
- Files: <the paths or globs that this session changes>
- State: active | waiting: <reason>
- Updated: <local time in ISO 8601>
- Agreements: <the agreements with other sessions, if any>
```

## drink-atlas-workspace-20

- Task: (1) the rules of this file, rules 13 to 21 of `AGENTS.md`: done, not committed.
  (2) plan 12: the test sets and their labels in the database, imported read-only from
  `dataset/<set>/review-labels.json`, and a benchmark runner that writes `runs/<id>/`.
  The first run is `svm-siglip2-448` on the set `my`; it MUST give the metrics of the
  latest JSON-era run of that backend.
- Source: owner messages of 2026-09-25 ("we have plenty time. Run tests and benchmark
  when ready", and the four answers after it).
- Files: `docs/plans/12_testsets-benchmark.md`. After the plan: `pipeline/schema_pending/NNN_testset.sql`, later
  `pipeline/schema/NNN_testset.sql` (the number is fixed only when the file enters `pipeline/schema/`: the next free
  number then; not before the commit of plan 09; proposed to a2 and 9a on 2026-09-25), `pipeline/import_testset.py`, `pipeline/benchmark.py`, `scripts/match_run.py`
  (the scoring code and `embeddings_of` move out), `scripts/match_scoring.py`,
  `scripts/match_backends.py` (gets `embeddings_of`),
  `tests/test_import_testset.py`, `tests/test_benchmark.py`,
  `tests/testset_fixture.py`, `runs/<id>/` of my runs.
  Entries in `README.md`, `SMOKE_TESTS.md`, `ChangeLog.md`, `docs/plans/07_*.md` (steps
  6 and 7), `docs/owner-messages.md`. `AGENTS.md` rules 25 to 28 (schema numbers). Earlier: `AGENTS.md` rules 13 to
  21, this section.
- State: waiting: the code and the tests of plan 12 are done. The schema file enters
  `pipeline/schema/` after the flat image store of drink-atlas-workspace-9a [f028b4];
  then the import of the sets and the parity run. The owner chose this order.
- Updated: 2026-09-25T07:16:02+0300
- Agreements: none.

## drink-atlas-workspace-8b

- Task: the SAM3 noun `box` of plan 09: option A (keep the result, patch the crate of
  `ona-skazala-da` and the tube of `fanagoriya-tochka-saperavi-krasnoe-suhoe-14`) or
  option B (a box wins only when it holds the bottle instance). Plans 08 and 09 are
  committed in `a8e113a`.
- Source: `docs/plans/09_image-processing.md`; owner message of 2026-09-25T00:55:04+0300.
- Files: `pipeline/derive.py`, `tests/test_derive.py`. Option B also writes rows of
  `image_derivative` and `image` in `data/lab.sqlite3`, and entries in `ChangeLog.md`,
  `ResearchLog.md`, and `docs/plans/09_image-processing.md`.
- State: waiting: the owner chooses option A or B.
- Updated: 2026-09-25T13:52:53+0300
- Agreements: all other files of plans 08 and 09 are released (2026-09-25): to
  drink-atlas-workspace-a2, drink-atlas-workspace-9a, and drink-atlas-workspace-7e.
  After the A/B decision, this session hands `pipeline/derive.py` and
  `tests/test_derive.py` over to drink-atlas-workspace-9a. drink-atlas-workspace-9a
  MAY apply its store-path lines (flat store, its own schema file) to both files in its step
  before the A/B change; this session reads both files again before its next change
  (2026-09-25). drink-atlas-workspace-7b MAY change `Sam3Client` of
  `pipeline/derive.py` (a method `instances()`) and add one test at the end of
  `tests/test_derive.py` now, for plan 16 (2026-09-25). drink-atlas-workspace-7b MAY
  also change `derive_all()` and `write_rows()` for the column `kind` of
  `image_derivative` (owner decision of 12:28:04); 7b and 9a agree the order of their
  changes of these two functions (2026-09-25). CACHE MAY add a cache of the SAM3
  answers to `Sam3Client._post` and tests to `Sam3ClientTest` (plan 25); it agrees the
  order with 7b (2026-09-25).

## drink-atlas-workspace-a2

- Task: plan 11: GTIN, barcode, and QR URL in the database (table `wine_code`); one wine
  MAY have more than one value, and one value MAY belong to more than one wine.
- Source: owner messages of 2026-09-25T00:52:48+0300, 2026-09-25T00:58:25+0300, and
  2026-09-25T07:19:46+0300 (approval; GTIN-14; check the check digit of each input);
  `docs/plans/11_wine-codes.md`.
- Files: `pipeline/schema/008_wine_code.sql`, `pipeline/codes.py`, `pipeline/seed_codes.py`,
  `pipeline/lab_server.py`, `pipeline/pages/dataset.html`, `tests/test_codes.py`,
  `tests/test_seed_codes.py`, `tests/test_lab_server.py`, `tests/test_labdb.py`,
  `docs/plans/11_wine-codes.md`, `docs/plans/07_*.md` (rule 5), `data/lab.sqlite3`.
  Entries in `COMMANDS.md`, `README.md` (step 6), `SMOKE_TESTS.md` (S1, S3, S4, S12,
  section WC), `ChangeLog.md`, `ResearchLog.md` (two entries at the top), and
  `docs/owner-messages.md`.
- State: waiting: the owner commits. The code is done and deployed: schema 008 entered,
  `data/lab.sqlite3` is at version 8 with 23 GTINs and 3 QR URLs, and the lab server on
  8168 runs the new code (restarted at 07:35 with SIGTERM). All tests pass except the 5
  old loader errors of the `scripts/review_server.py` tests. After the commit, this
  session sends 9a [f028b4] a message, and `pipeline/lab_server.py` is free.
- Updated: 2026-09-25T07:38:08+0300
- Agreements: with drink-atlas-workspace-8b (2026-09-25): this session changes
  `pipeline/lab_server.py`, `pipeline/pages/dataset.html`, `tests/test_lab_server.py`,
  `tests/test_labdb.py`, and `data/lab.sqlite3` after the commit of plan 09. The commit
  waits for the owner. 8b plans no more changes to the four code files. 8b MAY run
  `seed_images.py` once more on `data/lab.sqlite3` (schema version 7). Done: plan 09 is
  committed in `a8e113a`, and 8b released the five files on 2026-09-25. 8b keeps
  `pipeline/derive.py` and `tests/test_derive.py`, and tells this session before a run of
  option B on `data/lab.sqlite3`.
  With drink-atlas-workspace-9a (2026-09-25): this session changes
  `pipeline/lab_server.py` first, after the commit of plan 09, and sends 9a a message after
  its commit of plan 11. 9a then adds its `/embedding` hook. If 9a is ready first, it asks,
  and this session expects to agree. The schema point of this agreement is replaced by
  the rule below.
  Schema numbers, with drink-atlas-workspace-20 and 9a (2026-09-25): a number is fixed
  only when a file enters `pipeline/schema/`. Just before the entry, read
  `pipeline/schema/` and `ACTIVE_WORK.md`, take the next free number, and state it here.
  Do not renumber or edit a file that is in `pipeline/schema/`.
  With drink-atlas-workspace-9a [f028b4] (2026-09-25): the session that is ready first
  tells the others before its first change to `pipeline/lab_server.py`. Each session
  commits before the next one starts on `pipeline/lab_server.py`. [f028b4] changes the
  image code alone, and its schema file drops `image.folder` alone.
  Later, [f028b4] agreed (2026-09-25, about 07:24) that this session goes first on
  `pipeline/lab_server.py`, `pipeline/pages/dataset.html`, `tests/test_lab_server.py`,
  and `tests/test_labdb.py`, and that `NNN_wine_code.sql` enters `pipeline/schema/`
  before its file. This session sends [f028b4] a message after its commit.
  With drink-atlas-workspace-7e (2026-09-25): by the owner message of
  2026-09-25T06:52:00+0300, 7e changes `pipeline/lab_server.py`, the navigation of
  `pipeline/pages/dataset.html`, and `tests/test_lab_server.py` first. This session
  starts on these files after the message of 7e that its work is committed. The owner
  gave the `/embedding` hook to 7e, so the hook point of the agreement with 9a
  [fb66e9] no longer applies.

## drink-atlas-workspace-9a [f028b4]

The name `drink-atlas-workspace-9a` belongs to two sessions. This section is the session
`[f028b4]`.

- Task: the flat image store `data/images/<sha256>.<extension>` with no type folders.
  The column `image.folder` goes away in a new schema file.
- Source: owner messages of 2026-09-25T00:03:25+0300 and 2026-09-25T00:06:15+0300 (option 1);
  approved 2026-09-25T07:32:59+0300; `docs/plans/13_flat-image-store.md`.
- Files: in a private git worktree first, not in the shared tree: `pipeline/labdb.py`,
  `pipeline/imagestore.py`, `pipeline/seed_images.py`, `pipeline/seed_patched.py`,
  `pipeline/embeddings.py`, `tests/embedding_lab.py`, `tests/test_seed_images.py`,
  `tests/test_seed_patched.py`, a new `pipeline/schema/NNN_flat_image_store.sql`,
  `docs/plans/13_flat-image-store.md`. Later, when free: `pipeline/lab_server.py`,
  `tests/test_lab_server.py` (after a2), `pipeline/derive.py`, `tests/test_derive.py`
  (after 8b). At the end in the shared tree: all of these, `data/images/`,
  `data/lab.sqlite3`, entries in `README.md`, `SMOKE_TESTS.md`, `ChangeLog.md`, a note in plan 08, a server restart on 8168. Entries appended to
  `docs/owner-messages.md` and `ResearchLog.md`.
- State: waiting: the change is ready and tested in the private worktree (18 files).
  The shared tree gets it in one step after (1) the commit of drink-atlas-workspace-a2
  (`pipeline/lab_server.py`, `tests/test_lab_server.py`, `tests/test_labdb.py`), and
  (2) done: drink-atlas-workspace-8b agreed on `pipeline/derive.py` and
  `tests/test_derive.py`, and (3) the commit of drink-atlas-workspace-7b (the patch
  editor; the owner chose at 09:53 that it goes first).
- Updated: 2026-09-25T09:53:53+0300
- Agreements: with drink-atlas-workspace-a2 (2026-09-25): whoever is ready first tells
  the other before the first change to `pipeline/lab_server.py`. Each session commits
  before the next one starts on that file. A schema number is fixed only when a file
  enters `pipeline/schema/`. The owner chooses the order.
  With drink-atlas-workspace-20 (2026-09-25): the schema file of plan 12 enters
  `pipeline/schema/` after the file of this session (owner message 07:09:07). The flat
  store drops `image.folder` with `ALTER TABLE … DROP COLUMN`, not with a rebuild. This
  session sends 20 a message when `pipeline/imagestore.py` is committed. Planned
  interface: `path_of(db_path, sha256, extension)` instead of `folder_of`.
  With drink-atlas-workspace-8b (2026-09-25): this session applies its store-path
  lines to `pipeline/derive.py` and `tests/test_derive.py` in the flat-store step,
  before the A/B change of 8b. 8b changes neither file before that step; if the owner
  decides option B first, 8b sends a message and both agree the order again. Plan 09
  and schema 007 stay as they are; plan 13 describes the change.
  Notice of drink-atlas-workspace-f0 (2026-09-25 about 09:49, owner approval about
  09:50): f0 adds a route hunk to `pipeline/lab_server.py` (`/dataset/<slug>` and
  `/dataset/<slug>/patch` serve `dataset.html`) and one test to
  `tests/test_lab_server.py`. It does not touch the image code. The flat-store step
  applies its lines on top of this hunk.
  With drink-atlas-workspace-7b (2026-09-25): 7b goes first in the shared tree (owner
  choice 09:53). 7b changes `pipeline/seed_patched.py` and `tests/test_seed_patched.py`
  (no delete of a `main_patched` row) in the shared tree; this session merges the
  change into its worktree. In the new `pipeline/patches.py`, 7b keeps the store path,
  the `INSERT INTO image`, and any image URL each in one place. The flat-store step
  changes them too. 7b sends a message after its commit.

## drink-atlas-workspace-f0

- Task: the image preview of `/dataset` puts the wine slug in the page path:
  `/dataset/<slug>` for the catalogue image, `/dataset/<slug>/patch` for the patch image.
  A link opens the same preview.
- Source: owner message of 2026-09-25T09:46:41+0300 and the two answers after it (path
  segment; edit on top of the uncommitted work of a2 now).
- Files: `pipeline/pages/dataset.html`, `pipeline/lab_server.py` (the route of `/dataset`
  alone), `tests/test_lab_server.py` (one new test), `scripts/review_server.py` (the route
  of `/dataset` alone), `pipeline/lab_pages.py` (the shared route pattern). Entries in
  `SMOKE_TESTS.md` (D9f to D9h), `ChangeLog.md`,
  `docs/owner-messages.md`.
- State: waiting: the owner commits. The code, the test, and the docs are done. The lab
  server on 8168 runs the new code (restarted with SIGINT at 09:52:55).
- Updated: 2026-09-25T10:16:54+0300
- Agreements: the owner chose (2026-09-25, about 09:48) that this session adds small
  separate hunks on top of the uncommitted plan 11 hunks of drink-atlas-workspace-a2 in
  `pipeline/pages/dataset.html`, `pipeline/lab_server.py`, and `tests/test_lab_server.py`.
  A commit of this session stages its own hunks alone. a2 was not reachable by
  `SendMessage` at 09:48. drink-atlas-workspace-9a [f028b4] got a message at 09:48.
  With drink-atlas-workspace-7b [d39f66] (2026-09-25, about 09:54): this session's hunks
  in `pipeline/pages/dataset.html` are written; 7b edits after them. The patch line of
  `imagePreviewUrl` belongs to 7b. 7b MAY restart 8168 with this session's code in it.
  With 7b again (2026-09-25, owner messages 10:08 and 10:13:53): 7b adds the preview
  thumbnails on top of this session's hunks: CSS, modal markup, one call at the end of
  `showImagePreview` before the `pushState` lines, new functions after
  `stepImagePreview`. This session plans no more change to `dataset.html`. The hunk in
  `showImagePreview` holds lines of both sessions; before a commit, this session sends
  7b a message, and both agree which commit takes that hunk.
  With drink-atlas-workspace-f1 [222bcf] (2026-09-25, owner choice 10:16:07): f1 adds
  small hunks to `pipeline/pages/dataset.html`, `pipeline/lab_server.py`, and
  `tests/test_lab_server.py` (no `barcode` kind; the GTIN and QR URL editors redraw
  their own card). f1 does not touch the hunks of this session. This session plans no
  more change to these files.

## drink-atlas-workspace-7b

- Task: (1) the patch editor of `/dataset` on the lab database: drop, `Apply`, and
  `Remove` of a `main_patched` image: done, not committed. (2) the image preview of
  `/dataset/<slug>`: the image in the vertical center, and thumbnails below it: the
  original, the patch (with a badge) when it exists, and the processed file. (3) the card
  shows the `main` image in its place and the processed patch in the patch slot, side by
  side; a dropped patch file is applied and processed at once; a `crop` that cuts
  nothing gets no badge; the preview gets four thumbnails. (4) larger thumbnails at the
  bottom of the preview, at a fixed height (owner message of 10:24:00). (5) the patch
  `Remove` button: the size of the `Remove` button of the main image, at the right
  (owner message of 10:24:52; the CSS of `.state-actions` and `.patch-actions`). (6) the
  value `Disabled` of the `State` filter (owner message of 10:25:56; the `#state`
  select, new `inStateView`, one line each in `applyView` and `renderCard`). (7) the
  keys Up and Down step to the previous and the next wine in the preview (owner message
  of 10:26:37; the `keydown` listener and the titles of the arrow buttons). (8) the
  Embeddings page: the failed count in red, an `open` button on the `Directory` row
  that opens the directory in Finder, no `endpoint` in the `Directory` row (owner
  message of 10:29:30). Files: `pipeline/pages/embedding.html` (`showSource`, the
  summary line, one click listener), `pipeline/embedding_routes.py` (`ENTRY_ROUTE`,
  `respond`, new `open_directory`), `tests/test_embedding_routes.py` (new tests at the
  end of `RoutesTest`). (9) alternative images on the lab database: plan
  `docs/plans/16_alternative-images.md` (draft), owner message of 10:52:31 and the four
  answers of 10:58:12; approved by the owner at 11:02:26. Files: new
  `pipeline/alternatives.py`, `tests/test_alternatives.py`,
  `pipeline/schema/010_additional_types.sql` (entered as number 010 at the time of
  this update; 20, 9a [f028b4], and 98 got a message just before), hunks in
  `pipeline/lab_server.py` (docstring, `_alternatives` in `dataset_records`, the
  alternative keys of `dataset_view`, `_write_route`, new `Handler._alternative`),
  `pipeline/pages/dataset.html` (`alternativeEditor` and its handlers, the
  `.alternative-*` CSS), `pipeline/derive.py` (`Sam3Client` alone; asked 8b at 11:03),
  `pipeline/labdb.py` (`IMAGE_FOLDERS`: the new type names; no answer of 9a, told 9a at
  11:15), `tests/test_labdb.py` (`VERSION` 10), the type names in the fixtures of
  `tests/embedding_lab.py`, `tests/test_seed_images.py`, `tests/test_embeddings.py`,
  `tests/test_embedding_routes.py`, `tests/test_lab_server.py`, `tests/test_derive.py`
  (new class `Sam3InstancesTest`; agreed with 8b at 11:06), `data/lab.sqlite3` (migrated
  to version 10 at 11:11:16; backup in the scratchpad of this session), a restart of
  8168 (98 allows it). Entries in `README.md`, `SMOKE_TESTS.md`, `ChangeLog.md`, plan 10.
- Source: owner messages of 2026-09-25T09:46:30+0300 and 2026-09-25T09:48:52+0300, and
  the three answers of 2026-09-25T09:53:00+0300 (the database is the truth; `Apply` runs
  `derive.derive_all`; edit on top now); `docs/plans/14_patch-editor.md`. (2): owner
  messages of 2026-09-25T10:08:37+0300 and 10:10:04, answers of 10:13:53 (three
  thumbnails; edit on top of f0 now). (3): owner messages of 10:20:28 and 10:21:13, and
  the three answers after them.
- Files: new `docs/plans/14_patch-editor.md`, `pipeline/patches.py`, `tests/test_patches.py`.
  Hunks in `pipeline/lab_server.py` (module docstring, `import patches`,
  `dataset_records`, `dataset_view`, the patch functions after `remove_code`,
  `Handler._patch`, `_write_route`, `make_server`), `pipeline/pages/dataset.html`
  (`patchEditorOn`, `patchEditor`, `applyPendingPatch`, the patch line of
  `imagePreviewUrl`, the drag and drop checks of `[data-patch-drop]`),
  `tests/test_lab_server.py` (one line of `test_other_api_routes_are_disabled`),
  `pipeline/seed_patched.py` and `tests/test_seed_patched.py` (the delete rule alone).
  (3): `card_images` of `pipeline/lab_server.py`, `pipeline/patches.py` (`patch_urls`
  goes away), `tests/test_lab_server.py` (`test_api_dataset_sends_the_card_image` and
  `test_api_dataset_sends_the_size_of_the_card_image` alone), `dataset.html`
  (`patchEditor`, `stagePatchFile`, `imagePreviewUrl`, `previewThumbs`).
  (2): `pipeline/pages/dataset.html` (the CSS and the markup of the preview modal,
  `showImagePreview`, new `previewThumbs`), `pipeline/lab_server.py` (`card_images`,
  `CARD_IMAGE_KEYS`: the key `catalog_main_url`), `tests/test_patches.py`, entries in
  `README.md` (section "The Dataset page"), `SMOKE_TESTS.md` (PE11 to PE16),
  `ChangeLog.md`.
  Entries in `README.md` (steps 3 and 5), `SMOKE_TESTS.md` (P4, section PE),
  `docs/plans/07_*.md` (step 5), `ChangeLog.md`, `docs/owner-messages.md`.
- State: waiting: the owner commits. (1) to (14) are done, tested, and deployed (8168 since
  12:45:39; schema 017 entered at 12:35:13). Before: (1) to (11) are done, tested, and deployed; the lab
  server on 8168 runs them since 11:35:26. (10) a barcode gives the back types; (11)
  schema `012_type_names_kind_first.sql` entered at 11:30:03, `data/lab.sqlite3` at
  version 12, names changed in `pipeline/alternatives.py`, `pipeline/labdb.py`,
  `pipeline/embeddings.py` (told 9a), the page, and the fixtures.
  (12) the detection nouns `barcode, bottle, label, bottle neck, can` (owner message of
  11:45:49, answer of 11:47:17; `pipeline/alternatives.py`): done, tested, and live since
  the restart of 8168 by e3 at 11:48:14.
  (13) a review of the unfinished work of all sessions (owner message of 12:01:18):
  done, `docs/reviews/2026-09-25_unfinished-work.md`. The owner chose at 12:28:04: each
  session fixes its own findings (messages sent at about 12:30); one cut for each
  original and kind; a seed refuses a non-empty table unless `--force`; a thumbnail
  switches the preview fully (0b). (14) the fixes of 7b: `pipeline/alternatives.py`,
  `pipeline/patches.py`, `pipeline/lab_server.py` (the patch and alternative routes,
  `card_images`, `alternative_images`, docstrings), `pipeline/pages/dataset.html`
  (`stagePatchFile`, the alternative Cancel and ×), `pipeline/seed_patched.py`
  (`--force`), a new `pipeline/schema/NNN_derivative_kind.sql`, `pipeline/derive.py`
  (`write_rows`, the `done` query; asked 8b at 12:31), `scripts/common.py` and the 5
  review-tool test modules (the load errors; no section lists them), the tests of these
  files, and docs.
- Updated: 2026-09-25T12:49:00+0300
- Agreements: the owner chose (09:53) small separate hunks on top of the uncommitted work
  of a2 and f0. A commit of this session stages its own hunks alone.
  With drink-atlas-workspace-f0 (about 10:00): its hunks in `dataset.html` are written;
  this session changes only the parts named above; f0 allows a restart of 8168 with its
  code in it.
  With drink-atlas-workspace-9a [f028b4] (about 10:00): this session goes first in the
  shared tree, then the flat store. This session changes the delete rule of
  `seed_patched.py` and its test in the shared tree; [f028b4] merges them. In
  `pipeline/patches.py`, the store path, the `INSERT INTO image`, and the image URL are
  each in one place. This session sends [f028b4] a message after its commit.
  With drink-atlas-workspace-f0 (2026-09-25T10:13:53, the owner chose): this session
  edits the preview code on top of the uncommitted hunks of f0. Those hunks are then
  committed together. f0 plans no more change in `dataset.html`; before a commit of f0,
  f0 sends this session a message.
  With drink-atlas-workspace-0b (about 11:25, the owner chose at 11:22): 0b adds the
  preview of the alternative photos on top of the uncommitted hunks of this session in
  `previewThumbs`, `showImagePreview`, `stepImagePreview`, `alternativeEditor` (the `<a>`
  of a lab photo), and the preview listeners. Those hunks are committed together. 0b
  updates `SMOKE_TESTS.md` PE12 to PE14 for its new thumbnail names, or tells this
  session. This session plans no change in these regions.
  With drink-atlas-workspace-e3 (about 11:46, the owner chose at 11:45:00): e3 adds a
  `Log` button to `/embedding` on top of the uncommitted hunks of this session in
  `pipeline/embedding_routes.py` (`ENTRY_ROUTE`, `respond`), `embedding.html`, and
  `tests/test_embedding_routes.py`. This session plans no change there; a restart by e3
  may deploy the code of this session.
  With drink-atlas-workspace-f1 (about 10:17, and 10:28): no overlap of the regions. f1
  is done with its code and allows a restart of 8168; before an Atlas change in
  `dataset_records`, `dataset_view`, or the Atlas editor, f1 sends a message. The line
  `"patch_editor": True, "patches": …` of `dataset_view` stays. The restart of 8168 at
  the end of the work of f1 also deploys `catalog_main_url`; f1 tells this session.

## drink-atlas-workspace-f1

- Task: (1) keep GTIN alone in the lab: remove the kind `barcode` from the lab code, the
  lab API, the seed, and the Dataset page on the lab server; delete the one `barcode`
  row of `data/lab.sqlite3`. No schema file: schema 008 keeps `'barcode'` in its CHECK
  until the flatten. The old review tool keeps its Barcodes editor. (2) the save delay:
  the GTIN and QR URL editors redraw their own card, not all 2,103 cards. (3) the
  Atlas Core product binding on the lab server.
- Source: owner messages of 2026-09-25T09:51:46+0300, 09:52:30, 10:13:54, and the four
  answers of 10:16:07 (code only; lab page only; edit on top now; fix the delay too).
  (3): owner message of 2026-09-25T10:23:51+0300 and the answers of 10:30:50 (the
  database; a remove of a manual binding); `docs/plans/15_atlas-binding.md`.
- Files: hunks in `pipeline/codes.py`, `pipeline/seed_codes.py`, `pipeline/lab_server.py`
  (module docstring, `CODE_ROUTES`, `dataset_view`, `code_counts`),
  `pipeline/pages/dataset.html` (the GTIN, barcode, and QR URL editors: markup,
  open, cancel, save, remove; `renderHead`; the text search), `tests/test_codes.py`,
  `tests/test_seed_codes.py`, `tests/test_lab_server.py` (code route tests alone),
  `data/lab.sqlite3` (one DELETE). Entries in `docs/plans/11_wine-codes.md`, `README.md`,
  `SMOKE_TESTS.md` (S4, S5, section WC), `docs/plans/07_*.md` (rule 5, one line),
  `ChangeLog.md`, `ResearchLog.md`, `docs/owner-messages.md`. (3): new
  `docs/plans/15_atlas-binding.md`, `pipeline/schema/009_atlas_binding.sql` (number 009
  taken at 10:36), `pipeline/atlas_bindings.py`, `pipeline/seed_atlas_bindings.py`,
  `tests/test_atlas_bindings.py`, `tests/test_seed_atlas_bindings.py`; hunks in
  `pipeline/lab_server.py` (the `_atlas_*` lines of `dataset_records`, the `atlas_*` keys
  of `dataset_view`, the new route in `_write_route`, `Handler._atlas_binding`),
  `pipeline/pages/dataset.html` (`atlasBindingEditor`, `saveAtlasBinding`, new
  `removeAtlasBinding`, the Atlas click and keydown handlers), `tests/test_lab_server.py`
  (new Atlas route tests), `tests/test_labdb.py` (the version 9), `data/lab.sqlite3`
  (migration to 9 and the seed). Entries in `README.md`, `SMOKE_TESTS.md` (S4, new
  section AB), `docs/plans/07_*.md` (rule 5), `ChangeLog.md`. A restart of 8168.
- State: waiting: the owner commits. (1) to (3): done and deployed. (4) done and tested: the
  fixes of `docs/reviews/2026-09-25_unfinished-work.md`, sections f1 and a2 (owner answer
  of 2026-09-25T12:28:04+0300, section 4 item 1): the seeds `seed_codes.py` and
  `seed_atlas_bindings.py` refuse a table with rows unless `--force`; the Barcodes editor
  of the review tool on the shared page; the IPv6 host of `codes.clean_qr_url`; the value
  in the seed error of `seed_codes.py`; a test for `barcode_file`; SMOKE_TESTS S1, S3,
  S12, and the line "schema version 2". (4) files: `pipeline/codes.py`,
  `pipeline/seed_codes.py`, `pipeline/seed_atlas_bindings.py`, `tests/test_codes.py`,
  `tests/test_seed_codes.py`, `tests/test_seed_atlas_bindings.py`, hunks in
  `pipeline/pages/dataset.html` (`codeCheck`, `gtinEditor`, `barcodeEditor`,
  `qrUrlEditor`, the `gtinEditor` call of `recordHtml`), `tests/test_lab_server.py` (one
  assertion), entries in `COMMANDS.md`, `README.md` (steps 6 and 7), `SMOKE_TESTS.md`,
  `ChangeLog.md`, plans 11 and 15. No restart: the page is read from disk.
- Updated: 2026-09-25T12:48:02+0300
- Agreements: the owner chose (10:16:07) that this session edits on top of the
  uncommitted plan 11 hunks of drink-atlas-workspace-a2 (not reachable). The removal and
  plan 11 go into one commit. Messages to 7b [d39f66] and f0 [15172d] at 10:17.
  Schema 009 (rule 26, about 10:36): messages to 20, 9a [f028b4], and 8b; 20 agreed.
  With 7b [d39f66] (10:34 to 10:38): its hunks and mine in `lab_server.py`,
  `dataset.html`, and `test_lab_server.py` do not overlap; this session restarted 8168
  with the code of both at 10:37:59.
  With 7b [d39f66] (about 10:48, plan 16): 7b changes the `_alternatives` line of
  `dataset_records`, the alternative keys of `dataset_view`, and the schema version in
  `tests/test_labdb.py`. This session plans no more change to any file.
  With fa (about 11:43, plan 20): fa adds hunks to `lab_server.py` and `dataset.html` on
  top; no overlap with the hunks of this session.
  With 7b [d39f66] (about 12:40, review): 7b takes the shared sentences of plan 07 rule 5,
  README step 3, and the `lab_server.py` docstring whole, with the Atlas and code facts
  of this session. `seed_patched.py` uses the same `--force` form.

## drink-atlas-workspace-98

- Task: (4) the review findings of section "98" of
  `docs/reviews/2026-09-25_unfinished-work.md` (owner answer of 12:28:04: each session
  fixes its own). (3) favorites of `/dataset`: a star toggles a wine; the value `Favorites` of the
  `State` filter shows each favorite, also a removed one (owner message of 11:37:46).
  (2) rule 23 of `AGENTS.md`: stop 8168 with SIGTERM, not SIGINT (owner message
  of 11:29:27). (1) timestamped comments of a wine on `/dataset` (plan 17): a new table
  `wine_comment`, add and remove, the list in time order (the oldest first), a
  multi-line input, the value `with comments` of the filter `Show`.
- Source: owner messages of 2026-09-25T11:04:34+0300, the three answers of 11:07:00
  (oldest first; multi-line; edit on top now), 11:07:59 (the filter), and 11:09:30 (the source `user` or `script`);
  `docs/plans/17_wine-comments.md`.
- Files: (4) `pipeline/comments.py`, `tests/test_comments.py`, `tests/test_lab_server.py`
  (my comment tests), `pipeline/pages/dataset.html` (`removeComment`, my part of
  `beforeunload`), `SMOKE_TESTS.md` (D2, D10, D10a, D12 of the lab database section),
  `docs/plans/07_*.md` (the test count of step 2), `docs/plans/11_wine-codes.md` (the
  SIGINT line), `README.md` (step 3: the `State` values), `ChangeLog.md`.
  (3) new `docs/plans/19_favorites.md`, `pipeline/favorites.py`,
  `tests/test_favorites.py`, `pipeline/schema/013_wine_favorite.sql` (number 013 taken
  at 11:55, rule 26). Hunks in `pipeline/lab_server.py` (docstring, `import
  favorites`, one line of `dataset_records`, the key `favorites` of `dataset_view`, new
  `set_favorite` after `remove_comment`, new `Handler._favorite` after `_comment`, one
  line of `_write_route`), `pipeline/pages/dataset.html` (the `.favorite-star` CSS, one
  `<option>` of `#state`, `BUSY_FAVORITES`, new `favoriteStar` and `toggleFavorite`
  after my comment code, the star in the `.name` line of `recordHtml`, one line of
  `inStateView`, `renderHead`, one click branch, one line of `init`),
  `tests/test_lab_server.py` (new tests after my comment tests), `tests/test_labdb.py`
  (the version and the tables), `data/lab.sqlite3` (the migration), a restart of 8168.
  Entries in `README.md`, `SMOKE_TESTS.md` (new section FV), `ChangeLog.md`,
  `docs/plans/07_*.md` (rule 5), `docs/owner-messages.md`.
  (2) `AGENTS.md` (rule 23 alone), `ResearchLog.md` (the two SIGINT entries).
  (1) new `docs/plans/17_wine-comments.md`, `pipeline/comments.py`,
  `tests/test_comments.py`, `pipeline/schema/011_wine_comment.sql` (number 011 taken at 11:19, rule 26). Hunks in
  `pipeline/lab_server.py` (module docstring, `import comments`, one line of
  `dataset_records`, the key `comments` of `dataset_view`, new `add_comment` and
  `remove_comment` after `remove_atlas_binding`, new `Handler._comment` after
  `_atlas_binding`, one line of `_write_route`), `pipeline/pages/dataset.html` (the
  `.comment-*` CSS, one `<option>` of `#filter`, `DATA` defaults, `DRAFT_COMMENTS` and
  `BUSY_COMMENTS`, new `commentEditor` after `atlasBindingEditor`, one line of
  `recordHtml`, the filter line and the search text of `applyView`, `renderHead`, new
  comment functions after the Atlas functions, the comment branches of the click,
  input, and keydown listeners, one line of `beforeunload`, one line of `init`), `tests/test_lab_server.py` (new
  comment tests after the Atlas tests), `tests/test_labdb.py` (the version and the
  tables), `data/lab.sqlite3` (the migration), a restart of 8168. Entries in
  `README.md`, `SMOKE_TESTS.md` (new section CM), `ChangeLog.md`, `ResearchLog.md` (the
  SIGINT entry), `docs/plans/07_*.md` (rule 5, one sentence), `docs/owner-messages.md`.
- State: waiting: the owner commits (1) to (4). All four are done and live: fix 1 of (4)
  (`comments.py`) since the restart of 7b at 12:45:39, fixes 2 and 3 at once (page).
- Updated: 2026-09-25T13:18:36+0300
- Agreements: the owner chose (11:07:00) small separate hunks on top of the uncommitted
  work of the other sessions.
  With drink-atlas-workspace-7b (about 11:12): no overlap of the regions; the session that
  enters its schema file second sets `VERSION` and the table list of
  `tests/test_labdb.py`. 7b took 010; this session takes 011.
  Rule 26 messages (about 11:19): to 7b, 20, 9a [f028b4], and ff. ff writes comments
  with source `script` through `comments.add`; ff needs no schema file. 20 agreed.
  With drink-atlas-workspace-0b (about 11:24): its preview hunks in `dataset.html` do not
  touch mine; 0b keeps my line of `init`. 0b MAY restart 8168.
  With drink-atlas-workspace-20 (11:30): `AGENTS.md` is in the list of 20; message sent
  before the change of rule 23. The owner approved the change at 11:29:27.
  20 answered (about 11:31): it plans no change of `AGENTS.md`.
  With drink-atlas-workspace-ff (about 11:46): the deploy of (3) waits for the end of its
  `import_website.py` run (about 11:58); ff sends a message then.
  With drink-atlas-workspace-fa (about 11:47, plan 20): no overlap of the regions. fa
  sends a message when its hunks in `lab_server.py` and `dataset.html` are written; this
  session applies the plan 19 hunks after that. fa does not restart 8168 between the
  apply of this session and its message `deploy done`.
  With drink-atlas-workspace-7b (about 11:57): 013 agreed. The `favorites` line and the
  comment sentence of `inStateView` sit in the uncommitted `Disabled` hunk of 7b, so they
  go into the same commit as that hunk.
  20 agreed to 013 (about 11:56). fa: the `dataset.html` change of 11:53:48 is its own and
  went live with the restart of 11:55:50; `deploy done` sent to fa and 7b.
  With drink-atlas-workspace-0b (about 12:00): by the owner message of 11:58:25 to 0b, 0b
  moves the star to the top right of `.info` (its hunks on top of plan 19). This session
  plans no more change to those lines. Done: 0b's move is live; this session updated the
  star position in plan 19, `README.md`, and `SMOKE_TESTS.md` FV2 (about 12:05).
## drink-atlas-workspace-ff

- Task: (1) plan 18: `pipeline/import_website.py` (CLI): done, not committed. (2) plan 21:
  the UI mode of the import with a merge dialog, remembered refusals, the reused HTTPS
  connection, and two change times of a wine (`website_modified_at`, `modified_at`)
  with two sort options on `/dataset`.
- Source: (1) owner message of 2026-09-25T11:06:56+0300 and the answers after it;
  `docs/plans/18_import-website.md`. (2) owner messages of about 12:00 ("can we make 2
  modes", "also introduce last_modified time") and the answers after them;
  `docs/plans/21_website-import-ui.md`.
- Files: `docs/owner-messages.md` (append), `docs/plans/18_import-website.md`, new
  `docs/plans/21_website-import-ui.md`, `pipeline/import_website.py`,
  `tests/test_import_website.py`. After the approval of plan 21:
  `pipeline/schema/015_website_import.sql` (number 015 taken at 12:32:01, rule 26;
  messages to 7b and TESTSET; 20, 9a [f028b4], and e3 were not reachable), new
  `pipeline/website_import_routes.py`, new `pipeline/pages/website_import.js`, new
  `tests/test_website_import_routes.py`, hunks in `pipeline/lab_server.py` (the import,
  the delegation in `do_GET` and `_write_route`, the two times in `dataset_records`) and
  `pipeline/pages/dataset.html` (the button in the bar, one `<script src>` tag, two
  options of `#sort` and the sort code), `tests/test_lab_server.py` and
  `tests/test_labdb.py` (new tests at the end), `data/lab.sqlite3` (the migration),
  `work/website-import/`, a restart of 8168. Entries in `COMMANDS.md`, `README.md`,
  `SMOKE_TESTS.md`, `ChangeLog.md`, `ResearchLog.md`.
- State: waiting: the owner merges the conflicts in the dialog of `/dataset` (run
  `20260925T125132`, prepared 13:02: 12 conflicts, 196 changes), and commits. Plans 18
  and 21 are implemented, tested (397 tests OK), deployed, and documented. Nothing was
  applied to `data/lab.sqlite3`.
- Updated: 2026-09-25T13:04:00+0300
- Agreements: with drink-atlas-workspace-98 (2026-09-25, about 11:20): this session
  calls `comments.add(conn, slug, text, "script")` in its own transaction. It changes
  neither `pipeline/comments.py` nor schema 011.
  To drink-atlas-workspace-9a [f028b4] (about 11:33): a notice that
  `pipeline/import_website.py` writes `image.folder` and a store path in
  `store_path` and `insert_image`; the flat store changes these lines too.
  With drink-atlas-workspace-7b (12:33 to 12:45): no restart by this session while 7b
  changed derive.py; 7b restarted 8168 at 12:45:39 for all. 7b took 017, TESTSET 016.
  With drink-atlas-workspace-f1 and fa (about 12:40): the fixture inserts of
  `tests/test_lab_server.py` (this session) and `tests/test_manual_wines.py` (fa) name
  their columns after schema 015.
  With drink-atlas-workspace-fa (about 11:50): rules 24 to 26 of plan 20 are in
  `import_website.py` and plan 18 (rules 21, 22). The tool checks the prefix `__` itself
  until `pipeline/manual_wines.py` is committed.

## drink-atlas-workspace-0b

- Task: (1) the image preview of `/dataset` for the alternative photos, the same as for
  the `main` and the patch image (the modal, the thumbnails, the page path, the arrows).
  (2) the `main` image of a Disabled wine in grayscale on the card, in the browser
  (owner message of 11:57:30): one class in `imageFigure`, one CSS line after
  `.pictures a { position: relative; }`, entries in `README.md`, `SMOKE_TESTS.md`,
  `ChangeLog.md`. (3) the favorites star at the top right of `.info`, close to the
  alternative photos (owner message of 11:58:25): the star line and the `.info` line of
  `recordHtml`, new CSS after the `.favorite-star` rules of 98; entries in the same docs.
  (4) the review findings of this session (`docs/reviews/2026-09-25_unfinished-work.md`,
  owner answers of 12:28:04): a thumbnail of another kind switches the preview fully;
  the raw link of the patch preview (7b finding 11); SMOKE_TESTS AL numbers, PE18, plan
  14 item 4 (one line, 7b agreed); `.info { align-self: stretch; }` at <= 860 px. Files:
  `showImagePreview`, `previewThumbs`, `showPreviewThumb`, `renderPreviewThumbs`, the
  860 px media query of `dataset.html`; `SMOKE_TESTS.md`, `docs/plans/14_patch-editor.md`,
  `README.md`, `ChangeLog.md`.
- Source: owner message of 2026-09-25T11:19:38+0300, the four answers of 11:22:10 (every
  photo; all wine images; `/alternative/<sha256>`; edit on top now), and the message of
  11:22:21 (the strip: main, main processed, patched, patched processed, alternative,
  alternative processed).
- Files: `docs/owner-messages.md` (append). Hunks in
  `pipeline/pages/dataset.html` (the preview functions and the alternative card link),
  `pipeline/lab_pages.py` (`DATASET_PREVIEW_ROUTE`), `tests/test_lab_server.py` (the
  preview route test). Also the CSS of `.image-preview-thumbs` (one row that scrolls)
  and the scroll to the marked thumbnail at the end of `renderPreviewThumbs`; 7b got a
  message. Entries in `README.md` (section "The Dataset page"), `SMOKE_TESTS.md` (PE12
  to PE15, PE18, new AL15 to AL21), `ChangeLog.md`.
- State: waiting: the owner commits (1) to (4). (2) to (4) are done and live; the page needs no restart. The code, the test, and the docs are done. The
  route went live with a restart of 8168 at 11:26 (SIGTERM); 7b restarted 8168 again at
  about 11:32 for schema 012.
- Updated: 2026-09-25T12:40:00+0300
- Agreements: the owner chose (11:22:10) small separate hunks on top of the uncommitted
  work of 7b, 98, and the others. Messages to 7b and 98 at 11:23 name the regions:
  `previewThumbs`, `showImagePreview`, `stepImagePreview`, `imagePreviewPath`,
  `imagePreviewOfPath`, the `<a>` of a lab photo in `alternativeEditor`, the
  `data-image-preview` branch of the `#list` click listener, `popstate`, the preview line
  of `init`. 7b agreed (about 11:24): its hunks and mine in these regions go into one
  commit. 98 agreed (about 11:24): no overlap; a restart of 8168 needs no question.
  7b asked (about 11:31) for a restart for schema 012; this session answered
  `restart ok`.
  With drink-atlas-workspace-fa (about 11:44, plan 20, owner choice 11:42:50): fa adds
  hunks to `dataset.html` and `lab_server.py` outside the preview regions of this
  session, and it restarts 8168 at the end. This session plans no more code change.
  (2): fa and 7b agreed (about 11:59): no overlap; `imageFigure` holds no uncommitted
  hunk. (3): 98 agreed (about 12:01); it keeps `favoriteStar` and `toggleFavorite`, and it
  updates its own docs of the star place (plan 19, `README.md`, FV2).

## drink-atlas-workspace-fa

- Task: plan 20: a button `Add wine` on `/dataset`: a full manual form, the slug prefix
  `__`, a required `main` image; the imports never remove a `__` wine. No schema file.
- Source: owner messages of 2026-09-25T11:30:05+0300 and 11:41:15, the answers of
  11:40:48 and 11:42:50 (edit on top now); `docs/plans/20_add-wine.md`.
- Files: `docs/owner-messages.md` (append), new `docs/plans/20_add-wine.md`. After the
  approval: new `pipeline/manual_wines.py`, `tests/test_manual_wines.py`;
  `pipeline/import_catalog.py`, `tests/test_import_catalog.py`. Hunks in
  `pipeline/lab_server.py` (module docstring, `import manual_wines`, the key
  `wine_editor` of `dataset_view`, new `add_wine` after `change_state`, new
  `Handler._new_wine` after `_wine_state`, one branch of `_write_route` after
  `/api/wine-state`), `pipeline/pages/dataset.html` (the `.wine-form-*` CSS, the
  `Add wine` button in the bar, the new `#wine-modal` markup, new form functions after
  `openValidation`, the slug line of `recordHtml`, the form listeners after the
  validation listeners, one line of the document `keydown` listener, one line of
  `init`). Entries in `README.md`, `SMOKE_TESTS.md` (new section AW), `ChangeLog.md`,
  `docs/plans/07_*.md` (step 2, one rule). A restart of 8168.
- State: waiting: the owner commits (1) to (4). (4), the fixes of review section fa
  (items 1, 3, 4; item 5 was done at 12:13), is done, tested, and live since the restart
  of 8168 by 7b at 12:45:39 (checked). (1) to (3) are deployed: schema 014 entered at 12:13, `data/lab.sqlite3` is at version 14 (12:13:19),
  8168 runs the code since 12:13:40 (SIGTERM). Full suite: 334 tests, only the 5 old
  loader errors. (2): the slug follows the name until a person types a
  slug (owner message of 12:05:54). (3): `description` is optional (owner message and
  answer of 12:09:52: rebuild the table). Files of (2) and (3): hunks in
  `pipeline/pages/dataset.html` (my form functions, the `input` listener of
  `#wine-form`, the dialog markup), `pipeline/manual_wines.py`,
  `tests/test_manual_wines.py`, `pipeline/labdb.py` (`migrate` alone: foreign keys off
  during a schema file, `PRAGMA foreign_key_check` before COMMIT),
  `tests/test_labdb.py` (the version, one new test), a new
  `pipeline/schema/014_description_optional.sql` (number 014 taken at 12:12, rule 26;
  messages to 20, 9a [f028b4], 7b, and 98), `data/lab.sqlite3` (the migration; a backup first), a restart of 8168.
  Entries in `README.md`, `SMOKE_TESTS.md` (AW), `ChangeLog.md`, `ResearchLog.md`,
  plan 20, plan 07. (1) plan 20 waits for the commit of the owner.
- Updated: 2026-09-25T12:48:12+0300
- Agreements: the owner chose (11:42:50) small separate hunks on top of the uncommitted
  work of the other sessions. Messages at about 11:47 to 7b, 98, 0b, and f1 (the regions of
  `lab_server.py` and `dataset.html` above), to ff (rules 24 to 26 of plan 20 for
  `import_website.py`), and to 9a [f028b4] (the store path of `manual_wines.py`).
  0b, 98, f1, 7b, and ff answered: no overlap. ff added rules 24 to 26 to
  `import_website.py` with its own `MANUAL_PREFIX` until my commit. 98 deployed plan 19
  on top of my hunks. I plan no more edits to `lab_server.py` or `dataset.html`.
  20, 9a [f028b4], 7b, and 98 got the rule 26 message for 014 at 12:12. 7b and 98 agreed;
  98 asked for the checks of the child references and the comment ids (done, sent).
  ff and TESTSET told (after schema 015) that the fixture of `tests/test_manual_wines.py`
  fails; fixed by this session (the column list). 12 tests OK.

## drink-atlas-workspace-e3

- Task: (1) a button on `/embedding` that opens a dialog with the build log
  (`build.log`) of the selected entry: done, not committed. (2) a click on an image of
  `/embedding` opens a preview as on `/dataset`: done, not committed. (3) the label cut of
  each full photo, so the view `label` of `/embedding` gets its images and vectors; a
  badge `vector` on each cell whose item has a vector row (current and stale).
- Source: (1) owner message of 11:42:50, answers of 11:45:00. (2) owner message of
  11:59:27, answers of 12:02:31. (3) owner message of 12:11:50, answers of 12:27:47
  ("New table", "Current and stale"). The owner answer of 12:28:04 to 7b (one cut for
  each original and kind in `image_derivative`) replaces the new table: the label cut of
  a full photo is a row of kind `label` of `image_derivative` (agreed with 7b, about 12:31).
- Files: (1) and (2): hunks in `pipeline/embedding_routes.py` (docstring, `ENTRY_ROUTE`,
  the `/log` branch of `respond`, `build_log`), `pipeline/pages/embedding.html` (the log
  dialog, the preview CSS and markup, `cellHtml`, `columnHtml`, `wineHtml`, one line of
  `render`, the log and preview functions and listeners, the last line),
  `tests/test_embedding_routes.py` (3 tests at the end of `RoutesTest`).
  (3): new `docs/plans/22_label-cut.md`, new `pipeline/seed_label_cuts.py`, new
  `tests/test_seed_label_cuts.py`; hunks in `pipeline/embeddings.py` (`read_inputs`
  alone), `tests/test_embeddings.py` (one new test at the end),
  `pipeline/embedding_routes.py` (`entry_view`, new `_vector_rows`, `import numpy`),
  `pipeline/pages/embedding.html` (`cellHtml`, the `.vector` CSS, the preview file line),
  `tests/test_embedding_routes.py` (one test after `test_entry_view_and_image_route`).
  `data/lab.sqlite3` (rows of `image` and `image_derivative` of kind `label`; a backup
  first), new files in `data/images/cropped/`. Entries in `README.md`, `SMOKE_TESTS.md`,
  `ChangeLog.md`, `ResearchLog.md`, `COMMANDS.md`, plan 10, `docs/owner-messages.md`.
  No schema file.
- Task (4): the job row of `/embedding` shows the phase of a running build: `waiting
  for the model · <time>` and `retry <n>` (owner message of 13:37:14 "make it show
  progress", answer of about 13:40 "Phase text"). Files of (4): hunks in
  `pipeline/build_embeddings.py` (one `request` event in the batch loop of `run`, one
  `retry` event in `OpenAIBackend.embed`), `pipeline/embeddings.py` (`job_state`: the
  keys `phase`, `phase_event`, `phase_t`), `pipeline/pages/embedding.html` (`showJobs`,
  `LOG_HIDDEN` and the label of `#log-hide`), `tests/test_build_embeddings.py` (new tests
  at the end of `BuildTest`), `tests/test_embedding_routes.py` (one test in
  `JobStateTest`). A restart of 8168. Entries in `README.md`, `SMOKE_TESTS.md`,
  `ChangeLog.md`, plan 10.
- State: waiting: the owner commits (1) to (4). All four are done, tested, and live.
  (3): the seed ended at 13:36:59 (2,014 cuts written, 5 before, 4 with no label, no
  error); a `Build` of `gx10-siglip2-so400m-patch16-naflex-p256` at 13:44 left 4 failed
  items of 4,043; each other entry needs a `Build`. (4): 8168 restarted at 13:44:04 and
  at 13:46:33 (SIGTERM; the second start with `start_new_session`, PID 25039).
- Updated: 2026-09-25T13:47:00+0300
- Agreements: the owner chose (11:45:00) small separate hunks on top of the uncommitted
  work of drink-atlas-workspace-7b in the three code files of the Embeddings page. 7b
  agreed (about 11:46). With 7b (about 12:31): 7b enters its schema file (`image_derivative.kind`,
  key (source_sha256, kind)); 7b does not touch `embeddings.py`; this session changes
  `read_inputs` in the same restart as 015, and its seed adds rows of kind `label` for
  full originals through the writer of `alternatives.py`. `pipeline/embeddings.py` is
  also in the list of 9a [f028b4], which has ended (7b); the owner gets told.
  With drink-atlas-workspace-85 (about 13:08, plan 23): 85 adds hunks outside my regions
  (the label of `#emb`, `BACKENDS`, `Embedding.__init__`, `start`, `build_embeddings.main`).
  No overlap.

## TESTSET [0fe970]

- Task: (1) plan 12 step 4 without the flat store: the test set tables and an `image`
  rebuild with the folder `testset` in one schema file; photos in `data/images/testset/`;
  a script that imports the sets `my`, `official-real-photos`, and `vlmrerank-8b-failed`
  of `svoe-vino-testset/dataset/`; migrate, restart 8168, run the import. (2) after (1):
  a plan for the Testset page `/` with label editing on the database.
- Source: owner messages of 2026-09-25T12:13:10+0300 and 12:15:00, and the two answers of
  12:22:00 ("Enter schema now", "Editing on the DB").
- Files: `docs/owner-messages.md` (append). Taken over from drink-atlas-workspace-20 (not
  in `ListAgents`; owner choice 12:22): `pipeline/schema_pending/NNN_testset.sql` (it
  enters as `pipeline/schema/016_testset.sql`: number 016 taken at 12:34, rule 26; 7b and
  ff got a message),
  `pipeline/import_testset.py`, `pipeline/benchmark.py` (the photo path alone),
  `tests/testset_fixture.py`, `tests/test_import_testset.py`, `tests/test_benchmark.py`,
  `docs/plans/12_testsets-benchmark.md`. New `pipeline/import_testsets.py`,
  `tests/test_import_testsets.py`. (2): new `docs/plans/24_testset-page.md`; the code files
  follow its approval. At the entry: `tests/test_labdb.py` (the version and
  the table list), `data/lab.sqlite3` (a backup first), `data/images/testset/`, a restart
  of 8168. Entries in `README.md`, `COMMANDS.md`, `SMOKE_TESTS.md`, `ChangeLog.md`.
- State: (1) done, not committed: 016 entered at 12:34, `data/lab.sqlite3` at 16 (then 17
  by 7b), the three sets imported (4,323 photo rows, 3,449 new files), tests and docs
  done. No restart of 8168 by this session; 7b restarted 8168 at 12:45:39 (version 17). (2) waiting: the owner
  approves `docs/plans/24_testset-page.md` and answers its questions Q1 to Q4. The plan
  holds the box of the main object (owner message of 12:42:00).
- Updated: 2026-09-25T13:03:12+0300
- Agreements: drink-atlas-workspace-20 and 9a [f028b4] are not in `ListAgents`. With
  drink-atlas-workspace-7b (about 12:32): this session reuses `import_testset.py`; the
  file `NNN_derivative_kind.sql` of 7b rebuilds `image_derivative` alone, and either
  order works. ff took 015 at 12:32:01. 7b asked (about 12:34) that this
  session does not restart 8168: 7b restarts once, after its 017; this session agreed.
  7b set `VERSION` 17 in `tests/test_labdb.py` on top of 16. drink-atlas-workspace-85
  (about 12:47) got a notice: plan 24 (Testset) and its Runs page touch the same regions of
  `lab_server.py`; no change of this session there before the approval of plan 24. 85 answered (about 13:01): plan 23 is
  `23_runs-page.md` of 85 (written first, approved 12:52), so this plan is 24. 85 changes
  in `lab_server.py`: the docstring paragraph of the disabled pages, `import run_routes`,
  `"/runs"` out of `DISABLED_PAGES` (`"/"` stays), one `do_GET` branch after the
  `embedding_routes` branch, `Handler._runs` after `_embedding`; in
  `tests/test_lab_server.py` the `/runs` and `/api/runs` entries alone. 85 MAY add the
  optional argument `configuration=None` to `run_benchmark` of `pipeline/benchmark.py`
  (the key `configuration` of `run.json`) and one test at the end of
  `tests/test_benchmark.py`, on top of the photo path change of this session. 85 adds the literal folder
  `testset` to `IMAGE_ROUTE` of `lab_server.py` now, in plan 23 (agreed about 13:03);
  plan 24 drops that hunk.

## drink-atlas-workspace-85

- Task: enable the Runs page `/runs` on the lab server. The runs stay in `runs/`, not
  in SQLite. A filter by configuration (the entry of the `/embedding` selector). (2) The
  configuration `mock` builds like any other entry: random unit vectors (owner message
  of 13:37:14 in the session e3, answer of 13:41:00).
- Source: owner messages of 2026-09-25T12:36:00+0300 and 12:38:00 (the term
  "Configuration").
- Files: `docs/owner-messages.md` (append), new `docs/plans/23_runs-page.md` (approved
  12:52:00). New `pipeline/run_files.py`, `pipeline/run_routes.py`,
  `pipeline/pages/runs.html`, `pipeline/mock_run.py`, `tests/test_run_files.py`,
  `tests/test_run_routes.py`, `tests/test_mock_run.py`. Hunks in `pipeline/lab_server.py`
  (docstring: the disabled-pages paragraph and a new Runs paragraph; `import
  run_routes`; `DISABLED_PAGES` loses `/runs`; one `do_GET` branch after the embedding
  branch; new `Handler._runs` after `_embedding`), `tests/test_lab_server.py` (the
  `/runs` and `/api/runs` lines of the disabled-page tests), `pipeline/pages/embedding.html`
  (the label of `#emb` alone), `pipeline/embeddings.py` (`BACKENDS`, the mock branch of
  `Embedding.__init__`), `pipeline/embedding_routes.py` (`start` alone),
  `pipeline/build_embeddings.py` (`main` alone), `pipeline/benchmark.py` (the argument
  `configuration` of `run_benchmark`), `tests/test_benchmark.py` (one test at the end),
  `config.yaml` (the entry `mock` at the end of `embeddings`), `runs/<id>/` of my mock
  runs. Entries in `README.md`, `COMMANDS.md`, `SMOKE_TESTS.md`, `ChangeLog.md`, plans 07
  and 10. A restart of 8168.
- State: waiting: the owner commits (1) and (2). (2) is live since the restart of 8168
  by e3 at 13:44:04 (the mock files were written at 13:41:35 to 13:41:59). (2) is
  done and tested:(2) is
  done and tested: `pipeline/embeddings.py` (the mock branch of `Embedding.__init__`),
  `pipeline/build_embeddings.py` (new `MockBackend`, one branch of `make_backend`, no
  refusal in `main`), `pipeline/embedding_routes.py` (my refusal in `start` is gone; no
  hunk of this session is left there), `config.yaml` (`views: *views_c_f`),
  `tests/test_mock_run.py`, `tests/test_run_routes.py`, docs.
- Updated: 2026-09-25T13:54:00+0300
- Agreements: with TESTSET [0fe970] (about 12:58): 23 is this plan, TESTSET took 24.
  TESTSET changes neither `lab_server.py` nor `test_lab_server.py` before the approval of
  plan 24, then adds its hunks on top; this session sends it the lines. This session adds
  `configuration=None` to `run_benchmark` itself, and its test after the last test of
  `tests/test_benchmark.py`.
  With ff (about 12:58): the `do_GET` branch of this session stands after the
  `website_import_routes` branch of ff. ff plans no more change of `lab_server.py`.
  With 7b [d39f66] (about 12:59): no collision in `embedding.html`, `embeddings.py`,
  `embedding_routes.py`; `start` is not a region of 7b. EMBEDDINGS [2d4494] is e3; a
  message was sent at about 12:57. e3 answered (about 13:05): no overlap; the `#emb`
  label, `BACKENDS`, `Embedding.__init__`, `start`, and `build_embeddings.main` are outside
  its regions. TESTSET agreed (about 13:02) that this session adds the literal folder
  `testset` to `IMAGE_ROUTE`; plan 24 drops that hunk.

## drink-atlas-workspace-7e

- Task: a one-page A4 description of the structure of `data/lab.sqlite3` (schema
  version 17).
- Source: owner message of 2026-09-25T13:14:45+0300.
- Files: `docs/owner-messages.md` (append), `docs/database-structure.html` and
  `docs/database-structure.pdf` (new), an entry in `ChangeLog.md`.
- State: waiting: the owner reviews the page. Done, not committed. Owner choices at
  13:26: PDF file, one-off page, landscape ER diagram.
- Updated: 2026-09-25T13:53:00+0300

## CACHE [31e42f]

- Task: plan 25: a cache of the model calls (GDINO, SAM3, VLM) in `data/cache/`, one JSON
  file for each call. The key is a hash of the endpoint, the model, the parameters, the
  sha256 of each sent image, and the prompt. Only a success is stored.
- Source: owner message of 2026-09-25T13:45:11+0300, answers of 13:47:30 (JSON files, hash
  only, all four scopes, full URL), message of 13:51:48 (choose the recommended way; test).
- Files: new `docs/plans/25_model-call-cache.md`, `pipeline/model_cache.py`,
  `pipeline/gdino.py`, `tests/test_model_cache.py`, `tests/test_gdino.py`. Hunks in
  `scripts/cluster_rules.py` (`Vlm.ask`), `scripts/04_verify.py` (`Backend.ask`),
  `scripts/bench_vlm_models.py` (`call`). After the agreement of 8b: hunks in
  `pipeline/derive.py` (`Sam3Client._post`, a new `_send`, the import, `SAM3_MODEL`)
  and `tests/test_derive.py` (`setUpModule`, one test at the end of `Sam3ClientTest`).
  New files in `data/cache/`. Entries in `README.md`, `SMOKE_TESTS.md`, `ChangeLog.md`,
  `ResearchLog.md`, `COMMANDS.md`, `docs/owner-messages.md`.
- State: waiting: the owner commits. Code, tests, and docs are done: 445 unit tests and
  12 live cases against gx10 pass. No restart of 8168: the lab server uses the cache
  after its next restart.
- Updated: 2026-09-25T14:04:00+0300
- Agreements: with drink-atlas-workspace-8b (about 13:56): the hunks in `Sam3Client` and in
  `tests/test_derive.py` are allowed; build on the file on disk; the key holds the sent bytes,
  every form field, and the model; a failure is never stored. The test isolation is a
  module-level `setUpModule` before `class Sam3ClientTest` (told 8b). With
  drink-atlas-workspace-7b (about 13:56): 7b plans no more changes in `Sam3Client`,
  `Sam3ClientTest`, or `Sam3InstancesTest`; `_post(data, texts, return_masks)` stays the
  entry point; unit tests do not write into `data/cache/`.

## root

- Task: Perform a detailed Pareto audit of the project. Explain the architecture. List
  improvements with benefits and costs.
- Source: owner messages of 2026-09-25T14:27:40+0300,
  2026-09-25T14:28:00+0300, and 2026-09-25T14:37:47+0300.
- Files: `docs/owner-messages.md` (append),
  `docs/reviews/2026-09-25_pareto-audit.md` (new). Read-only inspection of all other
  files.
- State: waiting: the audit now uses the declared SQLite target architecture.
- Updated: 2026-09-25T14:37:47+0300
- Agreements: the owner authorized the detailed audit after the file conflict was stated.
