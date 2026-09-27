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

## drink-atlas-workspace-f4 [b39b7b]

- Task: a filter `Testset` on `/runs` (owner message of 2026-09-26T07:03:17+0300).
- Source: owner message of 2026-09-26T07:03:17+0300.
- Files: `docs/owner-messages.md` (append), `pipeline/run_files.py` (`run_head`),
  `pipeline/pages/runs.html` (the header, the run filter, the header state),
  `tests/test_run_routes.py`, and my own hunks in `ChangeLog.md`, `SMOKE_TESTS.md`,
  `README.md`. A restart of 8168 for `run_files.py`.
- State: done, not committed. The owner chose "Combo + column" at 07:06:00. 8168
  restarted by f4 at 07:08:32 (pid 40768). 7 run route tests OK; 24 Playwright checks pass.
- Updated: 2026-09-26T07:51:00+0300
- Task 2: plan 41, a step popup for the query photo of `/runs` (owner message of
  2026-09-26T07:14:42+0300, answers of 07:22:00). State: done, not committed; waiting: the owner decides the commit. 8168 serves it (restart by 5d at 07:42:25; the first request of the route came after the last edit of `run_steps.py`).
  Files: `docs/plans/41_run-step-popup.md` (new), `pipeline/run_steps.py` (new),
  `pipeline/embedding_run.py` (the step trace in `ask`, `query_inputs`, `cuts_of`,
  `Catalogue.rank`), `pipeline/benchmark.py` (`one`: an optional trace of `ask`),
  `pipeline/derive.py` (`Sam3Client._post`: a thread-local cache-hit flag),
  `pipeline/run_routes.py` (the route `/api/run-steps`; `run_view` drops `trace`),
  `pipeline/pages/runs.html` (the step popup; the query photo click),
  `tests/test_embedding_run.py`, `tests/test_run_steps.py` (new), `tests/test_benchmark.py`,
  `docs/API.md`, and my own hunks in `README.md`, `ChangeLog.md`, `SMOKE_TESTS.md`.
  A restart of 8168 for the route.
- Agreements: 39 [fb59ad] agreed to the key `set` in `saveHeader` and `restoreHeader` of
  `runs.html` (the URL wins; `renderSets` drops a stored value that is not an option).
  f4 agreed to separate hunks of 39 in `ChangeLog.md` and `SMOKE_TESTS.md`.
  f4 agreed (07:30) to hunks of 1c [800d92] in `embedding_run.py` (`build_pipeline_backend`,
  `model_inputs`, `candidate_items`) and `run_routes.py` (the embedded branch of the
  run-inputs view); 1c adds the trace step `barcode` in its `pipeline/barcode.py`.
  2a [693b64]: f4 removed the reads of `dataset/catalog-cluster*.json` from `run_steps.py`
  (owner message of 07:32:51); 2a changes `/api/run-clusters` and the cluster frames.
  5d [dab707] re-seeds `data/lab.sqlite3` (owner request); f4 answered "ok" to its start
  of 8168 with this code. f4 made the safety copy
  `data/backups/lab-rescue-20260926T0735-from-s3-viewer.sqlite3` of the old database,
  which went to `s3-viewer/~lab.sqlite3` at 07:33.

## drink-atlas-workspace-5d [dab707]

- Task: the full seed of the lab database with `pipeline/seed_from_testset.py`, then a
  start of 8168 and a check of `GET /api/dataset`. Fresh start: the lab-only data of the
  old database are not carried over.
- Source: owner message of 2026-09-26T07:31:00+0300, answers of 07:36:00, message of
  07:38:00 (the commands to repeat the import).
- Files: `docs/owner-messages.md` (append), `data/lab.sqlite3` (the swap of the seed),
  `data/lab.sqlite3.seeding`, `data/backups/`, `work/seed/`, one bullet in `ChangeLog.md`.
  A start of 8168 (it does not listen now).
- State: done, not committed. The seed ended at 07:42 (8 steps, exit status 0).
  8168 started at 07:42:25 (pid 5297); `GET /api/dataset` answers 200. Waiting for the
  owner: the old database moved to `../s3-viewer/` at 07:33, not by this session.
- Updated: 2026-09-26T07:46:00+0300

## codex-side-sam3-fix

- Task: make patch upload create the `package` and `label` derivatives. Keep the patch
  upload successful when SAM3 is unavailable or finds no label. Return a clear warning.
- Source: owner messages after 2026-09-26T07:53:41+0300. The owner selected approach 1.
- Files: `docs/owner-messages.md` (append), `pipeline/patches.py`,
  `pipeline/alternatives.py`, `tests/test_patches.py`, `docs/plans/14_patch-editor.md`,
  and my own small hunks in `ChangeLog.md`, `SMOKE_TESTS.md`, and `README.md`.
- State: done, not committed. Tests: `test_patches.py` 15 and
  `test_alternatives.py` 40 OK. The exact patch `00bae0ae…` got its missing label
  derivative. Its next embedding build built 1 item and left the 4 unrelated failures.
  Port 8168 restarted and answers HTTP 200 (PID 33223). Waiting: the owner decides on a
  commit.
- Updated: 2026-09-26T08:57:00+0300
- Task 2: mark the label derivative as not applicable when SAM3 finds no label and the
  package classifier finds a `packet` or `box`. Do not create a duplicate label vector.
- Source: owner answer of 2026-09-26T09:24:34+0300.
- Files: `pipeline/schema/021_derivative_absence.sql`, `pipeline/alternatives.py`,
  `pipeline/patches.py`, `pipeline/seed_label_cuts.py`, `pipeline/embeddings.py`,
  `pipeline/embedding_routes.py`, `tests/test_alternatives.py`,
  `tests/test_seed_label_cuts.py`, `tests/test_embeddings.py`, `tests/test_patches.py`,
  `tests/test_build_embeddings.py`, `tests/test_embedding_routes.py`, `tests/test_labdb.py`,
  `docs/plans/22_label-cut.md`, and my own hunks in `README.md`, `SMOKE_TESTS.md`, and
  `ChangeLog.md`. Schema number 021 is free. A migration and a restart of 8168 belong to
  the change.
- State: done, not committed. Schema 021 is live. The label seed recorded the Gloriya
  de Luna packet and the Izabella box as not applicable. The rebuilt SigLIP 2 index has
  4,060 items: 4,058 current and 2 failed bottle labels. The API reports 2 additional
  not-applicable label cells and keeps both full vectors. Port 8168 answers on PID 7765.
  Tests: the full suite has 783 tests OK and 5 skipped. Waiting: the owner decides on a
  commit.
- Updated: 2026-09-26T09:42:00+0300

## drink-atlas-workspace-9e [4644ab]

- Task: a button on `/runs` that builds a new test set from the R@1 misses or the R@5
  misses of the open run. A dialog selects the misses and the name `<set>-<N>` (the
  first free N).
- Source: owner message of 2026-09-26T09:05:00+0300, answers of 09:12:00; plan 44
  (`docs/plans/44_testset-from-run-misses.md`).
- Files: `docs/owner-messages.md` (append), `docs/plans/44_testset-from-run-misses.md`
  (new), `pipeline/testset_from_run.py` (new), `pipeline/testset_routes.py` (the route
  `/api/testset-from-run`), `tests/test_testset_from_run.py` (new),
  `pipeline/pages/runs.html` (5 separate hunks: a CSS block after `#more`, the button
  `New testset…` beside `#det-h`, the dialog `#nts-dlg` after `#lb`, one line
  `ntsButton()` in `loadRun`, and a script block before `the large view`),
  `docs/API.md` (one entry after `GET /api/run-clusters`). My own hunks in `README.md`
  (a bullet before `The routes are in pipeline/run_routes.py`, and the set combobox
  bullet of the Testset page), `ChangeLog.md` (the first bullet of `## 2026-09-26`), and
  `SMOKE_TESTS.md` (the section NT1 to NT12 after CI9). No schema change. No restart by
  this session: 8168 serves the route since the restart of 09:38:53 by another session.
- State: done, not committed. Waiting: the owner decides the commit. Tests: 6 of plan 44
  OK, the route tests OK, 32 browser checks OK. No set was made in `data/lab.sqlite3`.
- Updated: 2026-09-26T09:43:30+0300
- Agreements: the owner allowed at 09:24:00 separate hunks in `runs.html` and
  `docs/API.md`; the section of f4 [b39b7b] is stale (f4 is not in `ListAgents`).
  CLUSTERS [fb59ad] (39) agreed at about 09:27 to the plan 44 hunks in `runs.html`, with
  no condition: `HEADER_KEY`, `saveHeader`, `restoreHeader`, the two header listeners,
  and `evenCards` stay as they are. 39 takes plan number 45 for its next plan.
  drink-atlas-workspace-cc [d62b09] adds one link `Health` at the end of the
  `<nav class="nav">` line of `runs.html` (owner message of 10:35:48, answer of
  11:02:57); 9e agreed. cc does not touch the plan 44 hunks and commits its hunk alone.
  drink-atlas-workspace-ab [539687] asked at about 18:10 to change plan 44 files for its
  owner task of 17:55:00 (answers of 18:08:34): `test_photo_comment`; `test_wine_note`,
  `test_excluded`, and `test_photo.comment` go away. 9e answered "ok with conditions" at
  18:12. ab MAY change: `testset_from_run.py` (the copies of the notes and the excluded
  slugs, the docstring, the text at line 181; the selection logic stays),
  `tests/test_testset_from_run.py`, the other routes of `testset_routes.py` (the route
  `/api/testset-from-run` stays), 2 texts of `#nts-dlg` in `runs.html`, the testset write
  entries of `docs/API.md`, my `New testset…` bullet of `README.md`, row NT12 of
  `SMOKE_TESTS.md`, and one dated note at the end of plan 44 (no change of the plan
  text). Conditions: `test_testset_from_run.py` and `test_testset_routes.py` pass. The
  hunks inside the plan 44 files go into git only with plan 44, and only when the owner
  says so. ab accepted the 4 conditions at 18:12 and records the agreement in its section.
  drink-atlas-workspace-b4 [aee81a] adds 2 separate hunks to `runs.html` (owner message
  of 19:43:40, answers of 19:47:40): the CSS line `.tag.nobarcode` after `.tag.nocache`,
  and a `no barcode` tag line after the `no cache` tag line of `#runs-body`. 9e answered
  "ok" at 19:50. No plan 44 hunk changes.
  drink-atlas-workspace-41 [501d23] adds separate hunks for plan 55 (owner message of
  22:32:00, answers of 22:37:00): in `runs.html` the nav link `Recognize`, and the move
  of the plan 41 CSS block and step functions to the marks `STEPS_CSS` / `STEPS_JS`; in
  `docs/API.md` one new section at the end. 9e answered "ok with 1 condition" at 22:43:
  the dialog `New testset…` still opens with its two counts (NT5). No plan 44 hunk
  changes; plan 44 calls none of the moved functions. 41 reported at about 23:10 that
  plan 55 is live (8168 restart 23:07:24) and NT5 passes; 9e found the plan 44 parts in
  place at 23:15.
  drink-atlas-workspace-96 [6338a8] adds a hunk to `testset_routes.py` for plan 57
  (owner message of about 23:04): one docstring line, `NEW = "/api/testset-new"`, and one
  `WRITES` entry. 9e answered "ok" at 23:16. The `WRITES` entry goes after the `UPLOAD`
  entry and before the comment of `FROM_RUN`. The plan 44 code and `respond` stay as
  they are. `tests/test_testset_routes.py` is ab's file, so 96 asks ab too.
  drink-atlas-workspace-86 [92610a] adds one `docs/API.md` entry for
  `POST /api/dataset-alternative-recut` next to the `/api/dataset-alternative-cut` entry
  (owner message of 2026-09-27T00:51:44+0300). 9e has no objection (01:03). The entry is
  far from the plan 44 entry.
- Task 2: a read-only check. Is `data/lab.sqlite3` equal to the test set data of
  `svoe-vino-testset` and `svoe-wino-hackaton/dataset/derived`?
  Source: owner message of 2026-09-26T17:28:03+0300. Files: `docs/owner-messages.md`
  (append), `ResearchLog.md` (one new entry at the top). The database and the test set
  stay read-only. State: done, not committed. Waiting: the owner decides the commit.
  Updated: 2026-09-26T17:40:00+0300

## drink-atlas-workspace-d1 [0feb34]

- Task: the image preview of `/clusters`: no scroll bar; ←/→ inside one cluster; ↑/↓
  between clusters.
- Source: owner messages of 2026-09-26T09:29:30+0300 and 09:30:30.
- Files: `docs/owner-messages.md` (append), `pipeline/pages/clusters.html` (the CSS of
  `#preview`, the preview script: `previewItems`, `showPreview`, the click binding in
  `bindDynamic`, the preview buttons and the key listener), and my own hunks in
  `ChangeLog.md`, `SMOKE_TESTS.md`, and `README.md` (one paragraph of the embedding
  clusters). No server change, no restart.
- State: done, not committed. Waiting: the owner decides on a commit. Owner answers of
  09:32:30: ←/→ wraps inside the cluster; ↑/↓ opens image 1 of the adjacent cluster,
  skips clusters with no image, wraps at the ends. Live on 8168 with no restart (pages
  are read from disk). 19 Playwright checks pass.
- Updated: 2026-09-26T09:55:00+0300
- Agreements: CLUSTERS [fb59ad] (39) answered "ok" at about 09:32 for the preview hunks
  in `clusters.html`; 39 has no pending change there and asks first if it needs `ruleHtml`.
  d1 answered "ok" at about 09:54 to two hunks of 39 in `clusters.html` (owner message of
  09:51:00: `imageHtml` uses `image.cut_url`; no fill in `.member img, .member .nobottle`).
  Condition of 39: `.preview-body img` keeps no background fill. d1 does not change the
  file again.
  d1 answered "ok" at about 11:03 to one hunk of drink-atlas-workspace-cc [d62b09] in
  `clusters.html`: the link `Health` after `Runs` in the nav line (owner message of
  10:35:48, answer of 11:02:57). cc commits only that hunk through a private index.
  d1 answered "ok" at about 11:13 to a hunk of 39 [fb59ad] in `clusters.html`: the body
  of the `[data-save-note]` click handler in `bindDynamic` and one new function next to
  it (owner answer of 11:11:00: a background rebuild of the rule after a note save).
  d1 answered "ok" at about 22:42 to one hunk of drink-atlas-workspace-41 [501d23] in
  `clusters.html`: the link `Recognize` between `Runs` and `Health` in the nav line
  (plan 55; owner message of 22:32:00, answers of 22:37:00). 41 commits only that hunk.
- Task 2: show the wine comments on `/testset` as the Dataset page shows them.
  Source: owner message of 2026-09-26T17:37:45+0300. Files: `docs/owner-messages.md`
  (append) alone. State: covered by ab [539687] (owner answer of 18:08:34 to ab: ab
  changes the `/testset` row). d1 made no edit in the files of ab. Updated:
  2026-09-26T19:01:00+0300

## codex-hackathon-audit

- Task: audit `svoe-vino-lab` for hackathon readiness. Review the code, architecture,
  tests, documentation, repository presentation, and the first-pass LLM experience.
  Make a Pareto-ranked improvement list. Make a commented TODO that fits one A4 page.
  Create a reusable project skill for the same audit.
- Source: owner message recorded at 2026-09-26T11:35:32+0300 and the selected sequence
  `1, затем 2`.
- Files: `docs/owner-messages.md` (append),
  `docs/reviews/2026-09-26_hackathon-readiness-audit.md` (new),
  `HACKATHON_TODO.md` (new), and
  `../.claude/skills/audit-hackathon-project/**` (new).
- State: done, not committed. Product code stayed read-only. The audit, the A4 TODO,
  and the reusable skill are complete. The skill validator passed. Existing
  uncommitted changes belong to other sessions and stayed unchanged.
- Updated: 2026-09-26T11:48:21+0300

## codex-hackathon-infographic

- Task: create a Russian A4 infographic that combines the audit result and the
  Pareto-ranked hackathon TODO.
- Source: owner message recorded at 2026-09-26T12:39:00+0300.
- Files: `docs/owner-messages.md` (append),
  `docs/reviews/2026-09-26_hackathon-todo-infographic.png` (new), and
  `ACTIVE_WORK.md` (update).
- State: done, not committed. The infographic is complete. Product code stayed
  read-only.
- Updated: 2026-09-26T12:42:00+0300

## codex-svoe-atlas-match

- Task: match the `svoe-vino-lab` main, patched, and additional photos to Drink Atlas
  with `drink-atlas-matcher`. Verify image candidates against the available descriptions.
  Create a sortable HTML report and a reusable project skill. Keep both databases read-only.
- Source: owner message recorded at 2026-09-26T13:33:30+0300.
- Files: `docs/owner-messages.md` (append),
  `docs/plans/47_drink-atlas-read-only-match.md` (new),
  `docs/reports/2026-09-26_drink-atlas-match/**` (new),
  `../drink-atlas-matcher/scripts/match_svoe_vino_lab.py` (new),
  `../drink-atlas-matcher/src/drink_atlas_matcher/svoe_vino_match.py` (new),
  `../drink-atlas-matcher/tests/test_svoe_vino_match.py` (new), separate task hunks in
  `../drink-atlas-matcher/README.md`, `COMMANDS.md`, `ChangeLog.md`, `ResearchLog.md`,
  and `SMOKE_TESTS.md`, and
  `../.claude/skills/match-svoe-vino-to-drink-atlas/**` (new).
- State: done, not committed. The report contains 51 matches, 1,893 review rows, and
  159 unmatched rows. The source database SHA-256 stayed unchanged. All 140 matcher
  tests pass. The reusable skill passes validation.
- Updated: 2026-09-26T14:04:00+0300

## drink-atlas-workspace-ab [539687]

- Task: comment tables of the Testset. A new table `test_photo_comment`. Move
  `test_photo.comment` into it. Move `test_wine_note` and `test_excluded.reason` into
  `wine_comment`. Drop `test_wine_note`, `test_excluded`, `test_photo.comment`, and the
  exclusion of the benchmark. The photo popup and the wine rows of `/testset` show the
  comments as the Dataset page does.
- Source: owner message of 2026-09-26T17:55:00+0300; answers of 18:08:34 (one step;
  wine notes to `wine_comment`; drop the exclusion; this session also does the row).
  Plan `docs/plans/51_testset-comments.md`.
- Files: `docs/owner-messages.md` (append), `docs/plans/51_testset-comments.md` (new),
  `pipeline/schema/022_testset_comments.sql` (new; entered at 18:50:37),
  `pipeline/testsets.py`, `pipeline/pages/testset.html`, `pipeline/import_testset.py`,
  `pipeline/export_testset.py`, `pipeline/seed_from_testset.py` (docstring),
  `tests/test_testsets.py`, `tests/test_import_testset.py`, `tests/test_export_testset.py`,
  `tests/test_testset_routes.py`, `tests/test_testset_retention.py`,
  `tests/testset_fixture.py` (no change was needed), and
  my own hunks in `README.md`, `ChangeLog.md`, `SMOKE_TESTS.md`. By agreement with 9e:
  `pipeline/testset_from_run.py`, `tests/test_testset_from_run.py`,
  `pipeline/testset_routes.py`, `pipeline/pages/runs.html` (2 texts of `#nts-dlg`),
  `docs/API.md` (the testset write routes), 9e's README bullet `New testset…`, 9e's
  SMOKE row NT12, one dated note at the end of `docs/plans/44_testset-from-run-misses.md`.
  Allowed by the owner at 2026-09-26T18:17:31+0300 (stale or unreachable sections):
  `pipeline/benchmark.py` and `tests/test_benchmark.py` (f4), `tests/test_labdb.py`
  (codex-side-sam3-fix; a separate hunk), `data/lab.sqlite3` (5d; a copy goes to
  `data/backups/` first). A restart of 8168 (also deploys the `config.yaml` hunk of 16:01).
- State: done, not committed. Waiting: the owner decides the commit. Docs done:
  `README.md`, `ChangeLog.md`, `SMOKE_TESTS.md` (TS2, TS8, TP6, TP10, TP11, TP23, TP29,
  NT12, new PC1-PC11), `docs/API.md` (the entry of plan 44), plan 44 (a dated note),
  plan 51 (the result). Not changed: `docs/openapi.yaml` (the old review tool),
  `docs/database-structure.html` (schema 001-017; it needs a new layout). The commit
  order: 021 of codex-side-sam3-fix first (else a gap), then 022 with plan 44 whole
  (condition of 9e), then 023 of d3. `tests/test_labdb.py` holds the hunks of all
  three on the same lines.
- Updated: 2026-09-26T23:16:07+0300
- Agreements: d1 [0feb34] was told at about 18:10 that its Task 2 is covered by this
  task. d1 confirmed at about 19:02: its Task 2 is "covered by ab", and it has no
  pending edit in the files of ab. The owner answered d1 at 19:00:28 "Same editor,
  shared": the Comments block of the Dataset page on each wine row, through
  `wine_comment` and `/api/dataset-comment`. The deployed row editor is that block.
  b4 [aee81a] (owner message of 19:43:40, answers of 19:47:40: a checkbox "Disable
  barcode fast path" in `Run>`), agreed at 19:49 with conditions: 3 separate hunks,
  in the `Run>` dialog of `testset.html` (a CSS rule, the label `#run-barcode`,
  `runSyncFields`, `startRun`), one CSS line and the tag `no barcode` in the runs table
  of `runs.html`, and `use_barcode` in `run_benchmark` of `benchmark.py`. b4 does not
  move the hunks of ab, checks the page script with `node --check` and a load of
  `/testset`, asks 9e (runs.html) and the owner (the stale f4 listing of benchmark.py),
  and commits its own hunks alone.
  6c [c91c62] (owner task of 19:46, schema 024 `image_description.presentation_mode`),
  agreed at 20:04: in `tests/test_labdb.py`, VERSION 23 -> 24 by patch; the table
  list of ab stays. 6c asks d3 (the VERSION value of 023) and the owner (the listing of
  codex-side-sam3-fix). The `use_barcode` hunk of b4 in `benchmark.py` came in; the
  hunks of ab there are intact, and `test_benchmark.py` passes.
  bc [2d545a] (plan 54, schema 025 `atlas_binding_list`, a rebuild of
  `wine_atlas_binding`), agreed at 22:04: ab has no more schema work, so 025 is
  free from the side of ab; in `tests/test_labdb.py`, VERSION 24 -> 25 by patch, and
  the table list of ab stays. bc asks 6c (the VERSION value of 024) and the owner (the
  listing of codex-side-sam3-fix). 025 went live at 22:25 (restart by bc, pid 98664); ab checked
  /testset and its tests after it: OK.
  41 [501d23] (plan 55, the page `/recognize`), agreed at 22:42 with conditions: the
  nav link in `testset.html` and `runs.html`, the move of the plan 41 step renderer of
  `runs.html` to the marks `/* STEPS_CSS */` and `/* STEPS_JS */`, and a new last section
  of `docs/API.md`; separate hunks; the `runs.html` marks go on disk only in the same step
  as the restart that loads the new `lab_pages.py`; a check of /runs, the step popup, and
  /testset after the deploy; 41 asks 9e (runs.html, API.md) and the owner (f4 stale). Plan 55
  went live at 23:07:24 (restart by 41, pid 94543); ab checked its hunks and /testset
  after it (read-only browser check): OK.
  96 [6338a8] (plan 57, "Add new testset …"), agreed at 23:16 with conditions:
  separate hunks in `testsets.py` (`create_set`, `NEW_SOURCE`), `testset_routes.py`
  (`/api/testset-new`), `testset.html` (the option, 2 lines of the `#set` handler, a
  dialog), and new test classes; each path that loads another set calls `flushComment()`
  first; the page hunk goes on disk with the restart that loads the route; 96 asks 9e
  (`testset_routes.py`); the tests of the testset pass after the deploy. 9e [4644ab] answered "ok with conditions" at 18:12 (the text is in the section of
  9e). ab accepted the 4 conditions at 18:12.
  d3 [4920ce] (plan 52, table `wine_beverage_type`), agreed at 18:25: the
  session that enters its schema file first takes 022, the other takes 023 and
  migrates after it; each messages the other before its entry. d3 adds 3 hunks to
  `docs/database-structure.html` first; ab edits the file after d3 says it is done.
  `tests/test_labdb.py`: each session adds its own table name; the second entry
  sets VERSION.
- Note: this section was added at 17:55 and went away at 18:12 with the tail of the
  file, when another session removed its own section. It is added again here.

## drink-atlas-workspace-d3 [4920ce]

- Task: a wine type for each wine, `beverage_type_code` as in Drink Atlas Core: unset
  (default), `4` wine, or `44` sparkling wine. A control on each card of the Dataset page
  sets it. A filter of the Dataset page shows All, Wines, Sparkling Wines, or Not set.
- Source: owner messages of 2026-09-26T17:53:16+0300 and 18:10:45, answers of 18:21:29.
  Plan `docs/plans/52_wine-beverage-type.md` (number 51 belongs to ab).
- Files: `docs/owner-messages.md` (append), `docs/plans/52_wine-beverage-type.md` (new),
  `pipeline/schema/023_wine_beverage_type.sql` (new; number 023 taken at 18:53:56 after
  a message to ab, the only session with schema work), `pipeline/beverage_types.py`
  (new), `pipeline/lab_server.py` (the docstring, `dataset_records`, `dataset_view`, one
  POST route), `pipeline/pages/dataset.html` (the card select, the filter `Type` of the
  advanced row, `HEADER_IDS`), `tests/test_beverage_types.py` (new),
  `tests/test_lab_server.py`, `tests/test_labdb.py` (one table name and VERSION; the
  owner allowed it at 18:46:25), `data/lab.sqlite3` (a backup, then the migration; the
  owner allowed it at 18:46:25), a restart of 8168, and my own hunks in `README.md`,
  `ChangeLog.md`, and `SMOKE_TESTS.md`.
- State: done, not committed. Waiting: the owner decides the commit. 023 is live:
  `data/lab.sqlite3` at version 23 since 18:54:25 (backup
  `data/backups/lab-before-023-wine-beverage-type-20260926T155424Z.sqlite3`); 8168
  restarted by d3 at 18:54:37 (pid 38611, watcher pid 38616); `/api/dataset`, `/testset`,
  `/runs`, `/clusters`, and `/health` answer 200. Tests in the shared tree: 7 test files
  OK. The live page shows the select on 2,103 cards and the filter; no page error. Docs:
  `README.md`, `ChangeLog.md`, `SMOKE_TESTS.md` (WT1 to WT11), plan 52 status.
- Updated: 2026-09-26T18:57:19+0300
- Agreements: ab [539687] agreed at about 18:25: the session that enters its schema file
  first takes 022, the other takes 023 and migrates after it; each messages the other
  before its entry. ab confirmed before 18:46 that it enters 022 and deploys first, and
  sends d3 one line after its migration and restart; d3 restarts nothing on 8168 before
  that. `tests/test_labdb.py`: each session adds its own table name; the session of the
  second entry sets VERSION.
  `docs/database-structure.html`: d3 added no hunk. The box of the new table does not
  fit the one-page layout (diagram overflow 91 px). d3 told ab that the file is free; ab
  does not change the file either and reports to the owner that the page needs a new
  layout for schema 018 and later.
  f2 [120a07]: d3 agreed at 18:49 to the hunks of f2 in `pipeline/lab_server.py`,
  `pipeline/pages/dataset.html`, and `tests/test_lab_server.py` (the Atlas binding
  remove; made at about 18:45). They do not touch plan 52. d3 merges its hunks on top by
  patch (a dry run applies at zero fuzz) and copies no whole file. f2 does not change the
  3 files again. d3 told f2 that the restart of ab puts the server hunks of f2 live.
  6c [c91c62]: d3 agreed at 20:04 to separate hunks of 6c (owner task of 19:46, the
  field `presentation_mode`, schema 024) in `pipeline/pages/dataset.html` (the describe
  dialog, `DESCRIBE_FIELDS`, the field lists of `openDescribe` and `saveDescribe`),
  `pipeline/lab_server.py` (`set_image_description`: docstring and "1 to 5 fields"), and
  `tests/test_labdb.py` (VERSION 23 -> 24). 6c applies them by patch; the blocks of plan
  52 stay unchanged. Each session commits only its own hunks. At 20:11 d3 also agreed to
  one hunk of 6c in `tests/test_lab_server.py`: the key `presentation_mode` in the
  `record_vlm` dict of `test_the_raw_reply_route` (line 924 ff., far from the plan 52
  tests at lines 651 to 703).
  bc [2d545a]: d3 agreed at 22:04 to separate Atlas hunks of bc (plan 54, schema 025,
  the rebuild of `wine_atlas_binding`) in `pipeline/lab_server.py`,
  `pipeline/pages/dataset.html`, `tests/test_lab_server.py` (the Atlas tests), and
  `tests/test_labdb.py` (VERSION 24 -> 25). d3 has no schema work planned. Condition:
  bc builds its patches against the present files and keeps the plan 52 lines unchanged
  and in place; some stand within 3 lines of the Atlas lines (`lab_server.py` 373, 389,
  403, 417; `dataset.html` 2014 to 2022 and 2043). bc deployed 025 at 22:25:16 and kept
  the plan 52 lines; d3 checked the live API and the plan 52 tests after it (OK).
  41 [501d23]: d3 agreed at 22:41 to separate hunks of 41 (plan 55, the page
  `/recognize`): 6 in `pipeline/lab_server.py` (the import after `run_routes`, the NAV
  entry, one docstring paragraph after the Health paragraph, `_recognize` after
  `_health`, one branch in `do_GET` and one in `_write_route` after the health branches)
  and 1 in `pipeline/pages/dataset.html` (the nav link). None is near the plan 52 lines.
  96 [6338a8]: d3 agreed at 22:45 to separate hunks of 96 (plan 56, a manual polygon cut
  of an alternative photo) in `pipeline/lab_server.py` (`alternative_images`, two
  functions after `remove_alternative`, the route `/api/dataset-alternative-cut`, one
  docstring paragraph after the alternative paragraph), `pipeline/pages/dataset.html`
  (preview CSS, buttons, overlay, functions, the badge `manual`), and
  `tests/test_lab_server.py` (a new class at the end). Condition: the plan 52 branch of
  `_write_route` (8 lines below `/api/dataset-alternative-type`) stays unchanged and in
  place.
  df [46e479] (FYI, owner allowed at 2026-09-26T23:59:00+0300): hunks of plan 58 (shared
  code badges) in `pipeline/pages/dataset.html`, among them the body of
  `renderCodeCard`. d3 checked at 2026-09-27T00:14: `renderCodeCard` still calls the
  plan 52 `renderCard` first, and `codePeers` cannot throw on missing data, so the save
  of the wine type works as before.
  86 [92610a] (FYI, owner message of 2026-09-27T00:39:59): the filter `Alternatives` in
  the advanced row of `pipeline/pages/dataset.html`. d3 answered at 00:42: ok; keep and
  extend the plan 52 lines in the same spots (`typeFilterActive()` in the `active`
  expression of `changeAdvancedFilter` and in the `restoreHeader` condition, the first
  block of `initAdvancedFilters`, `inTypeView` in `applyView`, `"type-filter"` in
  `HEADER_IDS`, the label `type-filter-label`). 86 merged at 00:42:34. d3 checked at
  00:44: the 12 plan 52 markers of the page are present, and the live page loads with no
  page error; the filter `Sparkling Wines` shows the 2 wines of the database.
  86 [92610a] (FYI, owner message of 2026-09-27T00:51:44): the re-segment button of an
  alternative photo, hunks in `pipeline/lab_server.py` and `pipeline/pages/dataset.html`
  outside the plan 52 lines, and a restart of 8168 that the owner allowed. d3 has no
  objection (plan 52 has no pending code) and checks the plan 52 lines after the change.

## drink-atlas-workspace-f2 [120a07]

- Task: the red `×` of `Atlas Core product` also removes an automatic binding. A DELETE
  removes the effective row: the manual row, else the automatic row.
- Source: owner message of about 2026-09-26T18:40:00+0300, answers of about 18:45:00.
- Files: `docs/owner-messages.md` (append), `pipeline/atlas_bindings.py`
  (`remove_manual` -> `remove_effective`, docstring), `pipeline/lab_server.py` (the
  docstring paragraph of `/api/dataset-atlas-binding`, `remove_atlas_binding`),
  `pipeline/pages/dataset.html` (`atlasBindingEditor`: `removable` and the `×` label;
  `removeAtlasBinding`), `tests/test_atlas_bindings.py`, `tests/test_lab_server.py`
  (2 Atlas tests), `docs/plans/15_atlas-binding.md` (a dated change note), and my own
  hunks in `README.md`, `ChangeLog.md`, and `SMOKE_TESTS.md`. No restart by f2.
- State: done, not committed. Live: ab restarted 8168 at 18:50:38 (pid 29949). The live
  DELETE on a wine with no row answers 404 `… has no Atlas binding` (new code). A remove
  of an automatic row passed on a scratch copy of `data/lab.sqlite3`. Waiting: the owner
  decides the commit.
  Tests: `test_atlas_bindings.py` 6 OK, `test_lab_server.py` 61 OK. Docs done. The code
  hunks were made at about 18:45, before this section and before an agreement with d3
  [4920ce], which lists 3 of the files.
- Updated: 2026-09-27T01:03:00+0300
- Agreements: d3 [4920ce] was messaged at about 18:51 with the exact hunks in
  `lab_server.py`, `dataset.html`, and `test_lab_server.py`; f2 asked d3 to merge, not to
  copy whole files, at its deploy. d3 agreed at about 18:58: the hunks do not touch plan
  52, and d3 applies its deploy patches on top of them (patch -F0), never whole files.
  f2 does not change the 3 files again.
  ab [539687] asked at about 18:53 to restart 8168 with the f2 server hunks; f2 answered
  "ok".
  6c [c91c62] asked at about 19:48 for separate hunks in `pipeline/pages/dataset.html`
  (the description dialog, `DESCRIBE_FIELDS`, `openDescribe`, `saveDescribe`) and
  `pipeline/lab_server.py` (`set_image_description`: docstring, error text), by patch
  -F0. f2 answered "ok"; condition: the f2 Atlas hunks stay as they are.
  6c asked at about 19:55 for one hunk in `tests/test_lab_server.py`: the key
  `presentation_mode` in the `record_vlm` dict of `test_the_raw_reply_route`. f2
  answered "ok"; the 2 Atlas tests stay as they are.
  bc [2d545a] asked at about 22:05 to rewrite the f2 Atlas blocks for plan 54 (a list
  of UUIDs per wine) by patch -F0. f2 answered "ok". Condition: f2 commits first, when
  the owner says so; bc does not put f2 hunks into its commit. The f2 hunks alone are in
  `work/f2-atlas-remove-automatic.patch` (10 files, +116/-33); `git apply --cached` on
  a private index read from HEAD succeeds.
  bc said at about 22:30: plan 54 is live (schema 025 at 22:25:01, 8168 restart at
  22:25:16, pid 98664), on top of the f2 hunks. The f2 `×` code is replaced by plan 54 in
  the shared tree; the f2 patch stays the f2 commit. f2 answered "ok" to one dated line
  of bc at the end of plan 15, after the f2 change note.
  41 [501d23] asked at about 22:41 for separate hunks for plan 55 (page `/recognize`):
  6 in `pipeline/lab_server.py` (import, NAV, one docstring paragraph, `_recognize`, two
  route branches) and 1 nav link in `pipeline/pages/dataset.html`, by patch -F0. f2
  answered "ok"; condition: the Atlas blocks stay as they are; 41 also asks bc.
  96 [6338a8] asked at about 22:45 for separate hunks for plan 56 (a manual polygon cut
  of an alternative photo) in `pipeline/lab_server.py`, `pipeline/pages/dataset.html`,
  and `tests/test_lab_server.py` (a new class at the end). f2 answered "ok"; condition:
  the Atlas code stays as it is; 96 also asks bc.
  df [46e479] told f2 at about 00:14 (FYI, no answer asked): plan 58 added separate hunks
  in `pipeline/pages/dataset.html`, allowed by the owner at 2026-09-26T23:59:00+0300;
  the Atlas blocks are unchanged. The f2 patch still applies to HEAD `f2f13ac`.
  86 [92610a] told f2 at about 00:41 (FYI, no answer asked): separate hunks in
  `pipeline/pages/dataset.html` for the filter `Alternatives` (owner message of
  2026-09-27T00:39:59); the f2 hunks are not touched.
  86 told f2 at about 01:03: separate hunks for a re-segment button (owner message of
  2026-09-27T00:51:44) in `pipeline/lab_server.py` and `pipeline/pages/dataset.html`,
  and a restart of 8168. f2 has no objection and did not answer (none was asked).

## drink-atlas-workspace-c6 [bb1fb1]

- Task: the Drink Atlas match runner uses the old additional image types `front_full`,
  `front_label`, `back_full`, `back_label`. Schema 012 renamed them to `full_front`,
  `label_front`, `full_back`, `label_back`. Change the runner, its test, and plan 47.
- Source: owner message of 2026-09-26T19:37:57+0300.
- Files: `docs/owner-messages.md` (append). After the owner permission (the section
  `codex-svoe-atlas-match` lists these files; that session is not in `ListAgents`):
  `docs/plans/47_drink-atlas-read-only-match.md`,
  `../drink-atlas-matcher/src/drink_atlas_matcher/svoe_vino_match.py`,
  `../drink-atlas-matcher/tests/test_svoe_vino_match.py`, and my own hunks in
  `ChangeLog.md` and `../drink-atlas-matcher/ChangeLog.md`.
- State: done, not committed. Waiting: the owner decides the commit. The owner allowed
  the edit of the 3 files of `codex-svoe-atlas-match` at 2026-09-26T19:39:33+0300. No
  rerun of the match (owner answer). Matcher tests: 140 OK. The live snapshot gives
  1 `full_back` and 2 `label_back` photos.
- Updated: 2026-09-26T22:04:38+0300
- Agreements: drink-atlas-workspace-bc [2d545a] (plan 54, a list of Atlas bindings)
  asked at about 22:04 to change the prior-binding lines of `svoe_vino_match.py`, the
  fixtures of `test_svoe_vino_match.py`, and its own hunk in the matcher `ChangeLog.md`.
  c6 answered "ok with conditions": the image-type hunks of c6 stay byte-identical;
  bc adds its own ChangeLog section; the full matcher suite passes. The 3 matcher
  files are untracked, so a commit takes both sets of hunks; the owner decides.
  bc reported its hunks in at about 22:30. c6 checked: its hunks are unchanged; the
  full matcher suite gives 142 OK.

## drink-atlas-workspace-4f [0fa826]

- Task: the label cut of a close-up keeps a small label (a QR sticker) and drops the
  real label, because the box of the real label is close to the box of the bottle.
  Photo `d9f847bd…` of `vysokij-bereg-risling-zelenaya-seriya`.
- Source: owner message of 2026-09-26T19:38:53+0300, answers of 19:47:16 ("Close-ups:
  largest"; separate hunks in the files of `codex-side-sam3-fix`).
- Files: `docs/owner-messages.md` (append), `pipeline/alternatives.py` (a flag
  `close_up` in the label rule, `SETTINGS_LABEL_CLOSE_UP`), `tests/test_alternatives.py`,
  `docs/plans/16_alternative-images.md` (a dated change note), `data/lab.sqlite3` (the
  new cut of the 2 `label_back` photos), a restart of 8168, and my own hunks in
  `ChangeLog.md`, `ResearchLog.md`, `SMOKE_TESTS.md`, and `README.md`.
- State: done, not committed. Waiting: the owner decides the commit. No restart by
  this session: the restart of 19:50:15 by another session loaded the new
  `alternatives.py` (last edit 19:50:02). The 3 `label_back` cuts were made again
  through the live route. Tests: `test_alternatives.py` 44 OK; the full suite passes
  except `test_barcode.py` (it counts 23 pipelines in the uncommitted `config.yaml`
  hunk of another session; not this change).
- Updated: 2026-09-27T01:03:00+0300
- Agreements: the owner allowed at 19:47:16 separate hunks in `pipeline/alternatives.py`
  and `tests/test_alternatives.py`, which the stale section `codex-side-sam3-fix` lists.
  drink-atlas-workspace-96 [6338a8] (plan 56, a manual polygon cut) asked at about 22:45
  for separate hunks in the same 2 files. 4f answered "ok with conditions" at 22:47:
  the `MANUAL_PREFIX` check goes after `if row is None` and before the label branch of
  `has_current_cut`; the `close_up` parameter, branch, docstring, and call-site
  arguments stay; my 3 tests and `STICKER_CLOSE_UP` stay; `test_alternatives.py`
  passes; 96 commits only when the owner says so, and a commit of one task alone splits
  `has_current_cut` by hand. The stale section `codex-side-sam3-fix` needs the owner.
  drink-atlas-workspace-86 [92610a] (a re-segment button, owner message of
  2026-09-27T00:51:44) adds `recut_alternative` after `remove_alternative` and
  `tests/test_alternative_recut.py`. 4f has no objection, with one condition: a label
  type is cut with `close_up=kind == "label"`, as `_process_again` does.

## drink-atlas-workspace-b4 [aee81a]

- Task: a checkbox `Disable barcode fast path` in the dialog `Run>` of `/testset`. On: the
  run of a pipeline with the key `barcode` skips the code lookup (`barcode.CodeFirst`).
- Source: owner message of 2026-09-26T19:43:40+0300, answers of 19:47:40 (skip the step;
  `run.json` and a tag on `/runs`; the box is disabled for a pipeline with no `barcode`;
  separate hunks in the files of the stale section f4 are allowed).
  Plan `docs/plans/53_disable-barcode-checkbox.md`.
- Files: `docs/owner-messages.md` (append), `docs/plans/53_disable-barcode-checkbox.md`
  (new), `pipeline/run_jobs.py` (`has_barcode`, `configurations_view`, `start`,
  docstring), `pipeline/run_job.py` (`--no-barcode`, docstring), `pipeline/run_files.py`
  (`run_head`: one field), `pipeline/benchmark.py` (`run_benchmark`: the keyword
  `use_barcode`), `pipeline/pages/testset.html` (the Run> dialog: one CSS rule, the
  label `#run-barcode-label`, `RUN_BARCODE_TITLE`, 3 lines of `runSyncFields`, one line
  of `startRun`), `pipeline/pages/runs.html` (one CSS line, one tag line),
  `tests/test_run_jobs.py` (class `UseBarcodeTest`), `tests/test_run_files.py`, and my
  own hunks in `README.md` (2), `ChangeLog.md` (1 bullet), `SMOKE_TESTS.md` (NB1-NB10).
- State: done, not committed. Waiting: the owner decides the commit. Live: the restart
  of 19:50:15 by another session loaded `run_jobs.py` and `run_files.py`; the pages,
  `run_job.py`, and `benchmark.py` are read from disk. No restart by this session.
  Tests: `test_run_jobs.py` 21 OK, `test_run_files.py` 8 OK; the full suite 910 tests,
  1 failure: `test_barcode.py` counts 23 plain pipelines in the uncommitted `config.yaml`
  of another session (not this change). 22 browser checks pass (light and dark).
- Updated: 2026-09-26T23:18:00+0300
- Agreements: ab [539687] answered "ok with conditions" at about 19:52 for
  `testset.html`, `runs.html`, and `benchmark.py`: separate hunks; ab's hunks stay as they
  are; `node --check` and a /testset load with the Comments block (done); commit my
  hunks alone through a private index, and tell ab. 9e [4644ab] answered "ok" at about
  19:53 for the 2 hunks in `runs.html`; note: my tag line is 2 lines above the
  uncommitted `r.set` cell of f4, so check the hunk split at the commit. The files of the
  stale f4 section: owner answer of 19:47:40.
  41 [501d23] asked at about 22:40 for separate hunks in `testset.html` (a nav link
  `Recognize`) and `runs.html` (the nav link; the plan 41 step CSS/JS moves to the marks
  `STEPS_CSS` / `STEPS_JS`), plan 55. b4 answered "ok with conditions" at 22:43: my
  plan 53 hunks stay byte-identical; the hunks stay apart from my tag line and the f4
  `r.set` cell; `node --check` and my browser check after the patch; 41 commits its own
  hunks alone through a private index and tells b4.
  41 reported at about 23:14: plan 55 live since the restart of 23:07:24. b4 checked at
  23:15: my hunks unchanged; `check_barcode_box.py` 22 of 22 PASS, no page error.
  96 [6338a8] asked at about 23:15 for separate hunks in `testset.html` (plan 57: an
  option of `#set`, 2 lines of its change handler, a new dialog after `#run-dlg`, its JS
  after the Run> listeners, a keydown guard). b4 answered "ok with conditions" at 23:17:
  my hunks and the `#run-dlg` keydown guard stay as they are; the new markup goes after
  the close of `#run-dlg`, at least 7 unchanged lines after my label; `node --check` and
  my browser check after the patch; 96 commits its own hunks alone and tells b4.

## drink-atlas-workspace-6c [c91c62]

- Task: a 5th description field `presentation_mode` (`on_package`, `flat_surface`,
  `other`, `unknown`): the table, the dialog of `/dataset`, the VLM prompt and schema. The
  migration put the old rows back in the VLM queue; COALESCE keeps their 4 old values.
  The 4-gon cut is dropped (owner, 20:01).
- Source: owner messages of 2026-09-26T19:46:00+0300 to 20:01:00, answers of 19:55:00,
  20:10:00, and 20:18:54.
- Files: `docs/owner-messages.md` (append), `pipeline/schema/024_presentation_mode.sql`
  (new; entered at 20:19:30), `pipeline/image_descriptions.py`,
  `pipeline/describe_images.py`, `tests/test_image_descriptions.py`,
  `tests/test_describe_images.py`, `docs/plans/26_image-description.md` (a dated note,
  the prompt, the schema), `config.yaml` (the comment of `image_description`), my own
  hunks in `README.md`, `ChangeLog.md`, `SMOKE_TESTS.md`. By agreement:
  `pipeline/pages/dataset.html` (the description dialog alone), `pipeline/lab_server.py`
  (`set_image_description` alone), `tests/test_labdb.py` (VERSION 24 alone),
  `tests/test_lab_server.py` (one dict of `test_the_raw_reply_route`). Also
  `/Users/ashmelev/Admin/GPU_TASKS.md` (one row).
- State: done, not committed; live. Waiting: the owner decides the commit. 024 is live:
  `data/lab.sqlite3` at version 24 since 20:19:30 (backup
  `data/backups/lab-before-024-presentation-mode-20260926T171930Z.sqlite3`); 8168
  restarted by 6c at 20:19:39 (pid 22550, watcher pid 22583, `caffeinate` pid 22804);
  `/api/dataset` answers 200. The re-queue ended at 22:29: 2,092 of 2,092 rows filled
  (2,091 `on_package`, 1 `flat_surface`); `caffeinate` stopped; the GPU row is completed.
  Tests: 6 test files OK in the live tree; the full suite has 1 failure of another session
  (`test_barcode.py`). Also `ResearchLog.md` (one entry at the top). At 22:10 the 024 test
  of `test_image_descriptions.py` got `len(labdb.schema_files())` (a finding of bc).
- Updated: 2026-09-27T01:03:00+0300
- Agreements: f2 [120a07], ab [539687], and d3 [4920ce] answered "ok" at about 20:05 to
  the hunks above, and f2 and d3 at about 20:11 to the `test_lab_server.py` hunk: by patch
  (-F0) on the present files, never whole files. Their blocks stay unchanged (f2: the
  Atlas docstring, `remove_atlas_binding`, `atlasBindingEditor`, `removeAtlasBinding`, the
  2 Atlas tests; d3: `beverageTypeSelect`, `set_beverage_type`, the plan 52 tests; ab: the
  table list of `test_labdb.py`). The owner allowed the `test_labdb.py` part of the stale
  section codex-side-sam3-fix at 20:18:54. fb [3998cb] said "ok" to the restart.
  bc [2d545a] (plan 54, schema 025, a rebuild of `wine_atlas_binding`) asked at about
  22:03; 6c answered "ok" with conditions: Atlas hunks alone by patch -F0 in
  `lab_server.py`, `dataset.html`, `test_lab_server.py`, VERSION 24 -> 25 in
  `test_labdb.py` (the owner decides the part of codex-side-sam3-fix); a restart during
  the re-queue is OK; bc sends 6c the new pids of 8168 and of the watcher, so that 6c
  holds `caffeinate` on the new watcher. 6c has no schema work that needs 025.
  41 [501d23] (plan 55, the page /recognize) asked at about 22:41; 6c answered "ok": 6
  hunks in `lab_server.py` (import, NAV, docstring, `_recognize`, 2 route branches) and
  the nav link in `dataset.html`, by patch -F0; the blocks of 6c stay unchanged; a
  restart of 8168 is fine.
  96 [6338a8] (plan 56, a manual polygon cut of an alternative photo) asked at about
  22:45; 6c answered "ok": hunks in `lab_server.py`, `dataset.html`, and
  `test_lab_server.py` outside the blocks of 6c, by patch; a restart of 8168 is fine.
  1b [55fb13] (a pipeline `siglip2-p256-crop-seg`) asked at about 23:25; 6c answered
  "ok": one `pipeline` entry (and a `barcode-` twin) in `config.yaml`; the comment of
  `image_description` stays byte-identical.
  df [46e479] (plan 58, shared-code badges; the owner allowed it at 23:59:00) told 6c
  that it added separate hunks to `dataset.html` outside the description dialog. At
  a commit, 6c stages only its own hunks.
  86 [92610a] (the filter `Alternatives`, owner message of 2026-09-27T00:39:59) told 6c
  that it adds separate hunks to `dataset.html` (`#advanced-bar`, the advanced filter
  functions) outside the description dialog.
  86 [92610a] (a re-segment button, owner message of 2026-09-27T00:51:44) told 6c that it
  adds separate hunks to `lab_server.py` (`recut_alternative`, the route
  `/api/dataset-alternative-recut`, one docstring paragraph) and `dataset.html`, and
  restarts 8168. 6c has no objection; a restart does not affect its work.

## drink-atlas-workspace-bc [2d545a]

- Task: a wine MAY have 2 or more Drink Atlas Core product UUIDs. One list per wine; each
  row keeps its source (`automatic` or `manual`) as a label. The rule "manual replaces
  automatic" goes away. The migration keeps the present effective row of each wine.
- Source: owner message of about 2026-09-26T21:50:00+0300, answers of about 21:58:00.
  Plan `docs/plans/54_atlas-binding-list.md`.
- Files: `docs/owner-messages.md` (append), `docs/plans/54_atlas-binding-list.md` (new),
  `pipeline/schema/025_atlas_binding_list.sql` (new; entered at 22:25:01),
  `pipeline/seed_atlas_bindings.py`, `tests/test_seed_atlas_bindings.py`.
  After agreement: `pipeline/atlas_bindings.py`, `tests/test_atlas_bindings.py` (f2);
  `pipeline/lab_server.py` (Atlas docstring, `dataset_records` Atlas lines,
  `dataset_view` Atlas lines, `_atlas_answer`, `set_atlas_binding`,
  `remove_atlas_binding`, `_atlas_binding`), `pipeline/pages/dataset.html`
  (`atlasBindingEditor`, `saveAtlasBinding`, `removeAtlasBinding`, the Atlas click
  handler, `hasIdentifier` atlas line, the search text atlas line),
  `tests/test_lab_server.py` (the Atlas tests), `tests/test_labdb.py` (VERSION alone)
  (f2, d3, 6c); `../drink-atlas-matcher/src/drink_atlas_matcher/svoe_vino_match.py`,
  `../drink-atlas-matcher/tests/test_svoe_vino_match.py`,
  `../drink-atlas-matcher/scripts/match_svoe_vino_lab.py` (the prior-binding lines alone)
  (c6). `data/lab.sqlite3` (a backup, then the migration), a restart of 8168, and my own
  hunks in `README.md` (one new paragraph after the Atlas paragraph), `ChangeLog.md`,
  `SMOKE_TESTS.md` (new section AL1 to AL11), `../drink-atlas-matcher/ChangeLog.md` (my
  own section). `docs/plans/15_atlas-binding.md` (one dated note at the end; f2 agreed).
- Also: `pipeline/pages/dataset.html` CSS (2 new lines after
  `.atlas-binding-editor .barcode-value code`).
- State: done, not committed. Waiting: the owner decides the commit; f2 commits first.
  025 is live: `data/lab.sqlite3` at version 25 since 22:25 (backup
  `data/backups/lab-before-025-atlas-binding-list-20260926T192501Z.sqlite3`); 363
  automatic and 5 manual rows. 8168 restarted by bc at 22:25:16 (pid 98664, watcher pid
  98702). `/api/dataset`, `/dataset`, `/testset`, `/runs`, `/clusters`, `/health` answer
  200. The owner allowed the stale-section files at about 22:23. Tests in the shared
  tree: the full lab suite 918, 1 failure (`test_barcode.py`, the uncommitted
  `config.yaml` of another session); matcher 142 OK. Live page: 368 UUIDs, the filter
  `has Drink Atlas` 368 cards, no page error in light and dark mode. Docs done.
- Updated: 2026-09-26T22:31:36+03:00
- Agreements: f2 [120a07] "ok" between 22:05 and 22:10: build on top of its Atlas hunks by patch
  -F0; f2 commits first; my commit goes only after its commit is in HEAD, or after the
  owner says otherwise; its hunks are in `work/f2-atlas-remove-automatic.patch`.
  d3 [4920ce] "ok" at about 22:04: the plan 52 lines stay unchanged and in place.
  6c [c91c62] "ok" at about 22:03: its blocks stay unchanged; a restart during its
  re-queue is OK; 6c changed `tests/test_image_descriptions.py` line 196 itself for 025.
  ab [539687] "ok" at about 22:04: its table list in `test_labdb.py` stays.
  c6 [bb1fb1] "ok" at about 22:03 for the matcher: its image-type lines stay
  byte-identical; my own ChangeLog section; the full matcher suite passes. c6 confirmed
  at about 22:31 that the conditions are met.
  f2 agreed at about 22:30 to one dated note at the end of plan 15, after its section.
  41 [501d23]: bc answered "ok" at 22:42 to 7 separate hunks of plan 55 (/recognize) in
  `pipeline/lab_server.py` (import, NAV, docstring, `_recognize`, 2 route branches)
  and `pipeline/pages/dataset.html` (the nav link), by patch -F0. My Atlas lines stay
  byte-identical. A restart by 41 deploys nothing new from bc.
  96 [6338a8]: bc answered "ok" at 22:45 to separate hunks of plan 56 (manual polygon
  cut) in `pipeline/lab_server.py`, `pipeline/pages/dataset.html`, and
  `tests/test_lab_server.py`, by patch -F0. My Atlas lines stay byte-identical; its
  new functions go above `_atlas_products` and its route branch above the Atlas
  branch of `_write_route`, with no change to them.
  Schema: 025 is free (ab, d3, 6c have no schema work planned). Entered at 22:25:01.
  The owner allowed at about 22:23 the files of the stale sections codex-side-sam3-fix
  (`tests/test_labdb.py` VERSION) and codex-svoe-atlas-match (the 3 matcher files).

## drink-atlas-workspace-0f [b65dd3]

- Task: show the slug in the step popup of one photo on `/runs` (plan 41 popup).
- Source: owner message of 2026-09-26T22:16:00+0300.
- Files: `docs/owner-messages.md` (append). After agreement: `pipeline/pages/runs.html`
  (`renderSteps` alone, maybe one CSS line near `.sp-sub`), and my own hunks in
  `ChangeLog.md` and `SMOKE_TESTS.md`. No server change, no restart.
- State: done, not committed. Waiting: the owner decides the commit. Owner answers of
  22:20:00: "Own line in header"; "Yes, separate hunk" in `runs.html` (the listings of
  f4, 9e, b4, ab). My hunks in `runs.html`: one CSS line after `.sp-title .tag`, the
  function `slugLine` before `renderSteps`, and `${slugLine(row)}` at the end of the
  `#sp-title` line. Live with no restart (the page is read from disk). 10 Playwright
  checks pass (light, dark, 390 px). ChangeLog bullet and smoke test RN27 added.
- Task 2: the URL of `/runs` holds the photo of the open step popup:
  `#<run>/<slug>/<file>`. A load of the URL opens the popup; the arrow keys update the
  URL; close returns to `#<run>`. Source: owner message of 23:12:00, answers of 23:58:00
  ("#run/slug/file"; "Yes, separate hunks"). Files: `pipeline/pages/runs.html`
  (`openSteps`, `closeSteps`, the hash line of `loadRun`, `init`), my own hunks in
  `ChangeLog.md` and `SMOKE_TESTS.md`. No server change, no restart. Also `runHash`,
  `openPhoto` (new, next to `openSteps`). State: done, not committed. Waiting: the owner
  decides the commit. Applied by patch -F0 at about 00:00 on 2026-09-27; live with no
  restart. Checks: 14 URL checks, RN23, RN25, RN27 pass; `/recognize` answers 200; no
  page error. ChangeLog entry (2026-09-27) and RN28, RN29 added.
- Updated: 2026-09-27T00:02:00+0300
- Agreements: drink-atlas-workspace-41 [501d23] (plan 55, a page `/recognize`) asked at
  about 22:39 for separate hunks in `runs.html`: the nav link `Recognize`, and the plan 41
  renderer moves to `pipeline/pages/steps.css` and `steps.js`. 0f answered "ok with
  conditions": my 3 hunks stay byte-identical and in `runs.html` (the CSS line after
  `.sp-title .tag`, `slugLine` before `renderSteps`, `${slugLine(row)}` in the
  `#sp-title` line); 41 applies by patch -F0 and commits only its own hunks; 41 checks
  RN27 after its change. The agreement covers only the hunks of 0f; the renderer of the
  stale f4 and the hunks of 9e, b4, ab need their own agreement or the owner.
  41 reported at about 23:08: plan 55 is live (8168 restart 23:07:24, pid 94543), my 3
  hunks are in place. 0f checked again at 23:10: the 3 hunks are byte-identical; RN27
  passes (light, dark, 390 px, no page error).
  41 answered "ok" at about 23:59 to the 5 hunks of Task 2 (by patch -F0). Condition:
  its plan 55 hunks stay byte-identical (the nav line, `/* STEPS_CSS */` and its
  comment, the media query with `#sp` and `.sp-body`, the popup JS comment, `SP`,
  `SP_OPEN`, `/* STEPS_JS */`, the `Steps.html` line of `renderSteps`, `toggleStep`);
  check a row click and `/recognize` after (done).

## drink-atlas-workspace-41 [501d23]

- Task: plan 55, the page `/recognize`: a pipeline select, a drop area for one photo, and
  the steps of the photo as in the step popup of `/runs` (plan 41).
- Source: owner message of 2026-09-26T22:32:00+0300, answers of 22:37:00 (subprocess for
  each photo; embedding pipelines; a nav link on every page; shared steps.js + css).
  Plan `docs/plans/55_recognize-page.md`.
- Files: `docs/owner-messages.md` (append), `docs/plans/55_recognize-page.md` (new),
  `pipeline/recognize.py` (new), `pipeline/recognize_routes.py` (new),
  `pipeline/pages/recognize.html` (new), `pipeline/pages/steps.js` (new),
  `pipeline/pages/steps.css` (new), `pipeline/lab_pages.py` (2 optional marks),
  `tests/test_recognize.py`, `tests/test_recognize_routes.py`, `tests/test_lab_pages.py`
  (new), `pipeline/pages/embedding.html` and `pipeline/pages/health.html` (the nav line),
  and my own hunks in `README.md`, `ChangeLog.md`, `SMOKE_TESTS.md`.
  After agreement: `pipeline/lab_server.py` (import, `NAV`, one docstring paragraph,
  `_recognize`, one branch in `do_GET` and in `_write_route`); the nav line of
  `dataset.html`, `testset.html`, `clusters.html`; `runs.html` (the nav line; the plan 41
  CSS block and the step render functions move to `steps.css`/`steps.js`; `renderSteps`
  and `toggleStep` call `Steps`); `docs/API.md` (one new section at the end).
  A restart of 8168 for the new routes.
- State: done, not committed. Waiting: the owner decides the commit. One restart of 8168
  by this session at 23:07:24 deployed plan 55 and plan 56 (new pid 94543, watcher pid
  94574); the same step wrote `runs.html` and the nav hunks. Checks: 20 new tests OK; full
  suite 949, 1 failure of another session (`test_barcode.py`); 41 browser checks on
  `/recognize`; the `/runs` popup equal before and after; RN27, NT5, b4's 22 checks,
  `node --check` of each page. No page error.
- Updated: 2026-09-26T23:14:00+0300
- Agreements (all by patch -F0 on the present files; each session commits only its own
  hunks): d3, f2, 6c, bc "ok" for the 6 hunks of `lab_server.py` and the nav hunk of
  `dataset.html`; their blocks stay byte-identical (d3: plan 52; f2 and bc: the Atlas
  blocks; 6c: the describe dialog, `set_image_description`). d1 "ok" for the nav hunk of
  `clusters.html`. 0f "ok with conditions": `.sp-title .sp-slug` CSS line, `slugLine`,
  and `${slugLine(row)}` stay byte-identical in `runs.html`; check RN27 after. b4 "ok with
  conditions": its `testset.html` and `runs.html` hunks stay byte-identical; keep my hunks
  away from its tag line and the f4 `r.set` cell; `node --check`; its script
  `check_barcode_box.py`; tell b4 at a commit of either file. ab "ok with conditions":
  its hunks stay; the `runs.html` marks go on disk in the same step as the restart that
  loads the new `lab_pages.py`; old pages of `review_server.py` still render; check
  `/runs`, the popup, `/testset`; tell ab at a commit. 9e "ok": check NT5 (the dialog
  `New testset…`) after.
  96 [6338a8] (plan 56) "ok" at about 22:50 to my hunks; I answered "ok" to its hunks in
  `lab_server.py`, `dataset.html`, `docs/API.md` (my plan 55 hunks stay byte-identical).
  96 agreed at about 22:58: this session makes the one restart for both plans after 96
  says plan 56 is complete; I send 96 the new pid.
  96 [6338a8] (plan 57) asked at about 23:15 for separate hunks in `testset.html`; I
  answered "ok": my nav line stays byte-identical; a restart of 8168 is fine (plan 55 is
  live); `lab_pages.py` stays as it is.
  0f [b65dd3] asked at about 23:59 for 5 hunks in `runs.html` (the popup photo in the URL:
  `openSteps`, `closeSteps`, `stepSteps`, `init`, one new function); I answered "ok": my
  plan 55 hunks (nav line, STEPS marks, `SP`/`SP_OPEN`, the `Steps.html` line of
  `renderSteps`, `toggleStep`) stay byte-identical.
## drink-atlas-workspace-96 [6338a8]

- Task: a manual polygon cut for an alternative photo. A manual cut overrides the SAM3
  cut of the kind of the current type.
- Source: owner message of 2026-09-26T22:39:58+0300 and the answers after it; plan 56
  (`docs/plans/56_manual-alternative-cut.md`).
- Files: `docs/owner-messages.md` (append), `docs/plans/56_manual-alternative-cut.md`
  (new). After agreement, separate hunks in: `pipeline/alternatives.py` (manual cut
  functions, `has_current_cut`), `pipeline/derive.py` (`MANUAL_PREFIX`, one line in
  `derive_all`), `pipeline/seed_label_cuts.py` (the query of present cuts),
  `pipeline/lab_server.py` (`alternative_images`, two request functions, the route
  `/api/dataset-alternative-cut`, one docstring paragraph), `pipeline/pages/dataset.html`
  (the preview modal: a CSS block, the polygon editor, a badge `manual`),
  `tests/test_alternatives.py`, `tests/test_lab_server.py`, `tests/test_seed_label_cuts.py`,
  `docs/API.md` (one entry), and my own hunks in `ChangeLog.md`, `SMOKE_TESTS.md` (the
  section MC at the end), `README.md` (one paragraph after the preview thumbnails). A restart of 8168. No schema change.
- State: done, not committed. Waiting: the joint restart of 8168 by 41 (agreed at
  22:58), and the owner decides the commit. Tests: `test_alternatives.py` 54 OK,
  `test_seed_label_cuts.py` 9 OK, 35 Playwright checks. Docs done.
- Updated: 2026-09-26T23:07:01+0300
- Agreements: the owner allowed separate hunks in the files of the stale sections f4
  and `codex-side-sam3-fix` (answer of 2026-09-26T22:51:46+0300). f2, 6c, d3, bc, 41, and
  4f [0fa826] agreed to separate hunks by patch on the present files. Conditions: the
  Atlas code (f2, bc: 2 blank lines before `_atlas_products`, the Atlas branch of
  `_write_route`), the describe code (6c), the beverage branch (d3), and the plan 55
  hunks of 41 stay byte-identical. 4f: the manual check in `has_current_cut` goes after
  `if row is None` and before `if kind == "label"`; the `close_up` code stays; 44
  tests of `test_alternatives.py` pass; commit only when the owner says so. 41: tell
  41 before a restart of 8168.
- Task 2: plan 57, the option `Add new testset …` of the select `Test set` of
  `/testset`: a dialog makes an empty set (owner message of 2026-09-26T23:03:00+0300,
  answers of 23:13:58).
  Files: `docs/plans/57_testset-new.md` (new). After agreement, separate hunks in:
  `pipeline/testsets.py` (`create_set`, `NEW_SOURCE`), `pipeline/testset_routes.py`
  (docstring line, `NEW`, one `WRITES` entry), `pipeline/pages/testset.html` (one
  option in `load`, the `#set` change handler, a dialog after `#run-dlg`, its JS),
  `tests/test_testsets.py`, `tests/test_testset_routes.py`, my own hunks in the docs.
  A restart of 8168. No schema change.
  State: done, not committed. Waiting: the owner decides the commit. Live: 8168
  restarted by this session at 23:18:58 (pid 21149) for the route; the page came on
  disk after the restart. Tests: `test_testsets.py` 27, `test_testset_routes.py` 10,
  `test_testset_from_run.py` 6 OK; 42 Playwright checks; b4's check 22 PASS. Docs done.
  Updated: 2026-09-26T23:26:06+0300
  Agreements: ab (separate hunks; `flushComment()` before each load; `(new)` never
  reaches the URL or the header; tell ab at a commit), 9e (the `WRITES` entry after
  `UPLOAD`; stage against HEAD alone), b4 (its Run> hunks byte-identical; the dialog
  after `</div>` of `#run-dlg` with 7 unchanged lines between; tell b4 at a commit),
  41 (its nav line byte-identical).

## drink-atlas-workspace-1b [55fb13]

- Task: the pipelines `siglip2-p256-crop-seg` and `barcode-siglip2-p256-crop-seg`: the
  steps of `siglip2-p256-crop` with `remove_background` after `segment`, so the
  background of the package cut becomes white.
- Source: owner message of 2026-09-26T23:24:00+0300, answers of 23:27:00 (the name
  `siglip2-p256-crop-seg`; add the barcode twin and update the count of the test).
- Files: `docs/owner-messages.md` (append), `config.yaml` (after agreement with 6c: one
  entry after `siglip2-p256-crop`, one after `barcode-siglip2-p256-crop`),
  `tests/test_barcode.py` (the count 22 -> 26), and my own hunks in `ChangeLog.md`,
  `SMOKE_TESTS.md` (the section CS at the end), `README.md` (one bullet). No code change,
  no schema change, no restart.
- State: done, not committed. Waiting: the owner decides the commit. Live on 8168 with no
  restart. Tests: `test_barcode.py` 28 OK, `test_pipelines.py` 29 OK, `test_recogni*.py`
  16 OK; one live photo on 3 pipelines, HTTP 200. The count 26 includes the 2
  uncommitted p1024 pipelines of another session: commit this test line after or with
  that hunk.
- Updated: 2026-09-27T00:05:00+0300
- Agreements: 6c [c91c62] "ok" at about 23:27 to my `config.yaml` hunks; condition: the
  comment of `image_description` stays byte-identical (it did not change).
  df [46e479] (plan 58) added separate hunks to `tests/test_barcode.py` with the owner
  permission of 2026-09-26T23:59:00+0300. My count line (26) is unchanged. At a
  commit I stage only my count hunk; the df hunks go with plan 58.

## drink-atlas-workspace-df [46e479]

- Task: a badge beside a GTIN and beside a QR URL that 2 or more wines share (the Dataset
  page). The barcode step: a shared GTIN limits the match to the wines of the GTIN; a
  shared QR URL gives the normal match.
- Source: owner message of 2026-09-26T23:54:53+0300.
- Plan: `docs/plans/58_shared-codes.md` (new). Owner answers of 23:59:00: rank only the
  code wines; badge = count + tooltip; a unique code wins over a shared GTIN; separate
  hunks in the files of other sessions are allowed.
- Files: `docs/owner-messages.md` (append), `docs/plans/58_shared-codes.md` (new),
  `pipeline/barcode.py`, `tests/test_barcode_shared.py` (new). Separate hunks (owner
  answer of 23:59:00): `pipeline/embedding_run.py` (`Catalogue.rank`,
  `EmbeddingBackend.ask`), `pipeline/cluster_rerank.py` (`ClusterRerank.ask`),
  `pipeline/pages/dataset.html` (one CSS line after `.barcode-value .open-product`;
  `codeUsers`, `sharedCodeBadge`, `codePeers` before `gtinEditor`; the badge in
  `gtinEditor` and `qrUrlEditor`; `CODE_USERS = null` in `render`; `renderCodeCard`; one
  line in the `finally` of the state action), `tests/test_barcode.py` (`HIT`, the lookup
  of `CodeFirstTest`, 2 assertions, the shared QR test), `docs/plans/42_barcode-step.md`
  (section 10), and my own hunks in `ChangeLog.md` (first bullet of 2026-09-27),
  `SMOKE_TESTS.md` (section SC at the end), `README.md` (2 sentences in the `wine_code`
  paragraph, the `barcode` bullet of the pipelines).
- State: done, not committed. Waiting: the owner decides the commit. No restart: the
  pages and the run scripts are read from disk. Tests: `test_barcode_shared.py` 15 OK,
  `test_barcode.py` 28 OK, the full suite 968 OK (5 skipped); 22 Playwright checks; one
  real photo on `barcode-siglip2-p256-crop` (mode `limit`, 122 first).
- Updated: 2026-09-27T00:14:00+0300
- Agreements: the owner allowed the separate hunks at 2026-09-26T23:59:00+0300. At
  00:14 df told 1b (`test_barcode.py`) and d3, f2, 6c, bc, 41, 96 (`dataset.html`) about
  the hunks; no answer is needed.
  drink-atlas-workspace-86 [92610a] said at about 00:40 that it adds separate hunks to
  `dataset.html` (the select `Alternatives`, `initAdvancedFilters`, `changeAdvancedFilter`,
  one line of `applyView`, one listener) and does not touch the hunks of df. No overlap:
  the df hunk near it is in `render`, not in `applyView`.

## codex-dataset-clipboard

- Task: add a clipboard image button to Alternative photos on `/dataset`.
- Source: owner message of 2026-09-27T00:15:16+0300.
- Files: `docs/owner-messages.md` (append); proposed separate hunks in
  `pipeline/pages/dataset.html` (alternative controls and clipboard function),
  `README.md` (alternative upload paragraph), `SMOKE_TESTS.md` (append),
  and `ChangeLog.md` (one bullet).
- State: waiting: owner approval for separate edits under rule 17. The prepared patch
  `/private/tmp/dataset-clipboard-full.patch` passes `git apply --check`. The browser
  checks pass with mock clipboard and upload APIs. The live page is unchanged.
- Updated: 2026-09-27T00:18:33+0300

## drink-atlas-workspace-86 [92610a]

- Task: the SAM3 package cut prefers a wine bottle over a box, a can, or a packet
  (q-000117 of run 2026-09-26T173050Z-lab-barcode-siglip2-512-crop-my).
- Source: owner message of 2026-09-27T00:05:00+0300.
- Files: `docs/owner-messages.md` (append). After the owner choice and the agreement
  with 96: separate hunks in `pipeline/derive.py` (`Sam3Client.segment`,
  `SETTINGS_SEG`, the module docstring), `tests/test_derive.py`, and my own hunks in
  `ChangeLog.md`, `ResearchLog.md`.
- State: done, not committed. The owner chose rule D and a new `SETTINGS_SEG` at
  00:20:00. Waiting: the owner decides the commit, the re-cut of the catalogue, and the
  embedding rebuild. 8168 serves the new rule since the restart of task 3.
  Tests: `test_derive.py` 25 OK, full suite 975 OK.
- Updated: 2026-09-27T00:31:41+0300
- Agreements: 96 [6338a8] got a message about the separate hunks in `derive.py` at
  00:22; no answer is needed.
- Task 2: an advanced filter on `/dataset` that shows the wines with alternative photos
  (owner message of 2026-09-27T00:39:59+0300).
  Files: `docs/owner-messages.md` (append); separate hunks in `pipeline/pages/dataset.html`
  (the advanced bar: a select `Alternatives`, the id of the Package label;
  `initAdvancedFilters`, `changeAdvancedFilter`, one line in `applyView`, one listener),
  and my own hunks in `ChangeLog.md`, `SMOKE_TESTS.md` (section AF), `README.md` (one
  bullet of the advanced filters). No restart: the page is read from disk. State: done,
  not committed; waiting: the owner decides the commit. 48 of 48 Playwright checks pass.
  Updated: 2026-09-27T00:44:14+0300.
  Agreements: I told 41, 6c, 96, bc, d3, df, f2 about the hunks in
  `dataset.html`; no answer is needed. d3 agreed and asked to keep the plan 52
  lines; they stay unchanged.
- Task 3: a button ↻ at the bottom left of each alternative photo of the lab page. It asks
  SAM3 again with no cache read, stores the fresh answers in the cache, and cuts the
  photo again from them. The button is disabled on a manual cut.
  Source: owner message of 2026-09-27T00:51:44+0300, answers of 00:56:00.
  Files: `docs/owner-messages.md` (append); separate hunks in `pipeline/derive.py`
  (`Sam3Client.__init__` and `_post`: the flag `refresh`), `pipeline/alternatives.py`
  (a new function `recut_alternative` after `remove_alternative`), `pipeline/lab_server.py`
  (a wrapper after `reset_manual_cut`, the route `/api/dataset-alternative-recut`, one
  docstring paragraph), `pipeline/pages/dataset.html` (the button, its CSS, one click
  branch, one function), `docs/API.md` (one entry), `tests/test_alternative_recut.py`
  (new), `tests/test_derive.py`, and my own hunks in `README.md`, `ChangeLog.md`,
  `SMOKE_TESTS.md`. A restart of 8168 (the owner allowed it at 00:56:00).
  State: done, not committed; waiting: the owner decides the commit. 8168 restarted by
  86 at 01:13 (pid 15146). Tests: `test_alternative_recut.py` 7 OK, full suite 1,001
  OK, 32 Playwright checks. Live: d9f847bd… keeps the label box 102, 61, 1247, 1553
  (the check of 4f); b6e13a6d… of Aratti now cuts the bottle. Updated: 2026-09-27T01:15:23+0300.

## codex-profile-latency

- Task: cache barcode scans and set four workers for `barcode-rerank-siglip2-512-crop`.
- Source: owner request of 2026-09-27T01:01:41+03:00: `add barcode scan cache also. And support a few workers (4).`
- Files: `pipeline/barcode.py`; new `tests/test_barcode_cache.py`; `docs/reports/2026-09-27_profile-latency.md`; separate additions in `docs/owner-messages.md`, `README.md`, `ChangeLog.md`, and `SMOKE_TESTS.md`.
- Delegated files: agent `trace_profile` owns `pipeline/pipelines.py`, `pipeline/embedding_run.py` (worker spec), `pipeline/run_jobs.py` (worker default), `config.yaml` (profile worker count), `tests/test_pipelines.py`, and new `tests/test_pipeline_workers.py`.
- State: done, not committed. 162 relevant tests pass. The 14-photo barcode control preserves all answers (8.4754 s first scan; 0.0767 s cached with four workers). Port 8168 restarted to PID 96402; dataset HTTP 200; profile default 4. Active benchmark PID 11418 continues with one worker. No database change.
- Updated: 2026-09-27T01:09:35+03:00
- Agreements: the owner requested these implementation changes after the diagnosis. This task changes only the cache and worker behavior. Existing unrelated edits remain intact. The delegated agent does not edit parent-owned files.

- Task 2: assess faster ZXing scans, crop choices, pass limits, and per-image parallelism.
- Files for task 2: new `docs/reports/2026-09-27_zxing-speed-options.md`; `docs/owner-messages.md` (append). Temporary benchmark files use `/tmp`.
- State for task 2: done. The report records pinned upstream sources, 42-photo pass limits, and three per-image parallel controls. No production configuration change.
- Updated for task 2: 2026-09-27T01:10:40+03:00

- Task 3: wait for the current run, then benchmark bulk reruns and sequential recognition with a 3-second total deadline.
- Files for task 3: new `docs/reports/2026-09-27_barcode-benchmark-plan.md`; `docs/reports/2026-09-27_barcode-variants/**`; `scripts/benchmark_barcode_variants.py` and `tests/test_barcode_variants.py` (agent `trace_profile`); `docs/owner-messages.md` (append); own documentation hunks. New preparation files: `scripts/benchmark_barcode_crops.py` and `tests/test_barcode_crops.py` (agent `trace_profile`); `scripts/benchmark_recognition_latency.py` and `tests/test_recognition_latency.py` (agent `review_demo_benchmark`). Parent owns new `scripts/benchmark_bulk_cache.py` and `tests/test_bulk_cache_benchmark.py`. Agent `review_demo_benchmark` also owns new `scripts/benchmark_recognition_http.py` and `tests/test_recognition_http.py` for isolated HTTP measurements.
- State for task 3: complete. All scan, crop, bulk, and sequential HTTP comparisons have terminal validated artifacts. The final recommendations were delivered in the parent turn at 04:09. No repeated measurement is required.
- Updated for task 3: 2026-09-27T01:30:00+03:00
- Offline HTTP reporting: agent `review_demo_benchmark` owns new `scripts/summarize_recognition_http.py`, new `tests/test_summarize_recognition_http.py`, and one separate `ChangeLog.md` entry. The helper reads frozen selections and saved HTTP records only. It does not load images or call services. State: done, not committed; eight fixture tests and bounded independent review pass. Delegated by the parent on 2026-09-27. Correction: the parent authorizes missing-child timing exclusion, focused fixture tests, and new `docs/reports/2026-09-27_barcode-variants/http-pilot-report-final-v2/**`. Keep old report artifacts. State for correction: complete; ten fixture tests and independent review pass. The new report keeps all eight sessions and unchanged latency, quality, and reliability denominators. Only unavailable child timing fields are excluded. Offline only.
- Preliminary process-mode analysis: agent `review_demo_benchmark` owns new `docs/reports/2026-09-27_barcode-variants/http-process-preliminary.json` and `http-process-preliminary.md`. Compare the four completed process sessions only. Preserve the cold HTTP 503 and report paired-success and annotation-conflict sensitivity separately. State: complete; delegated at 2026-09-27T03:33+03:00. The report validates fixed input hashes, all selected rows, cache isolation, and paired deadline sets. No code changes, model requests, or image processing.
- Fresh crop diagnostic analysis: agent `review_demo_benchmark` owns new `docs/reports/2026-09-27_barcode-variants/http-crop-hits-report-final/**`, `http-crop-hits-observation.md`, and `http-crop-hits-observation.json`. Read the completed 72 observations and frozen 24-hit selection. Report geometry availability, barcode unique returns, pipeline fallback, quality, and HTTP latency. State: complete; delegated after completion at 2026-09-27T03:43:34+03:00. The report validates all 72 records, frozen selection identity, fixed source hashes, cache isolation, and barcode-return paths. Offline analysis only. No model calls, image processing, or production edits.

- Task 4: add a profile with a segmented query label and a second top-k search in the catalogue label vectors.
- Source for task 4: owner message of 2026-09-27T01:35:09+03:00.
- Files for task 4: `config.yaml` (new profile only); `docs/owner-messages.md` (append); own hunks in `README.md`, `ChangeLog.md`, and `SMOKE_TESTS.md`.
- State for task 4: done, not committed. `barcode-rerank-siglip2-512-crop-label` is runnable in both live selectors without a restart. Both towers use the existing SigLIP2-512 index. The full steps match the original profile; label steps match the catalogue label view. Validation: 136 existing tests pass after rerunning 10 environment-blocked tests with the system Python and local socket permission. Synthetic photos confirm separate full/label searches and the missing-label fallback. No model inference or full run was started. The barcode benchmark continues.
- Updated for task 4: 2026-09-27T01:39:00+03:00

- Task 5: rerun every configured profile after the current benchmark comparisons.
- Source for task 5: owner message of 2026-09-27T01:40:18+03:00. The test set stays `my`.
- Files for task 5: `docs/owner-messages.md` (append); new `docs/reports/2026-09-27_all-profile-rerun.md`; new `docs/reports/2026-09-27_all-profile-rerun/**`; the existing benchmark plan and own ChangeLog hunk. Update the existing heartbeat rather than create a second scheduler. Agent `trace_profile` owns new `scripts/prepare_rerun_label_inputs.py` and `tests/test_prepare_rerun_label_inputs.py` for the restricted NaFlex-1024 derivative prerequisite. Execution waits for completed benchmark comparisons and fresh GPU checks. Agent `review_bulk_harness` owns new `scripts/summarize_barcode_bulk.py` and its fixture tests for offline result aggregation.
- State for task 5: active. The serial 53-profile internal/local queue is running. Read the latest checkpoint and queue.json. The external recognizer remains excluded pending explicit transfer approval. The NaFlex-1024 index build is complete and validated with two documented missing-label inputs.
- Updated for task 5: 2026-09-27T01:44:00+03:00

- Benchmark preparation checkpoint: 2026-09-27T07:02:43.686181+03:00. Done, not committed. All barcode comparisons and final recommendations are delivered. All 53 authorized profile outcomes are terminal: 48 validated successes, one retained eight-error invalid completion, and four local unavailable outcomes under the current memory policy. Final-profile-comparison.md and final-review.json are delivered. The source/control audit passed. The heartbeat is PAUSED. No further inference or queue work remains. The external recognizer remains unauthorized pending separate explicit photo-transfer approval. No unrelated service changed.


- Delegated queue preparation: agent `trace_profile` owns new `scripts/run_internal_profile_queue.py` and `tests/test_run_internal_profile_queue.py`. Default inspection is read-only. Explicit execution can launch at most one approved internal/local queue profile through the existing run-job API. This preparation uses fixtures only. Parent owns real queue writes and launch gates. Preparation is complete: 23 fixture tests and independent review pass. A real read-only inspection preserves the queue hash. Actual execution stays gated on all benchmark comparisons.

- Current offline analysis: agent `trace_profile` owns new `docs/reports/2026-09-27_barcode-variants/profile-comparison-observation.md`. It compares the prepared as-is diagnostic with the current crop/rerank profile. The work sends no requests and changes no production file.

- Agent `trace_profile` also owns new `docs/reports/2026-09-27_barcode-variants/http-persistent-photo4-offline-rerank.json` and `.md`. These files reconstruct pre-rerank quality from saved traces only. They make no measured HTTP deadline claim.

- Agent `trace_profile` owns new `docs/reports/2026-09-27_barcode-variants/final-recommendations.md`. Integrate the completed bulk and sequential demo comparisons. No inference or launch. Parent owns final validation and the rerun queue.

- Agent `review_bulk_harness` owns new `scripts/summarize_internal_profile_queue.py` and `tests/test_summarize_internal_profile_queue.py`. The helper reads saved queue and attempt evidence only. It reports all profiles and explicit partial outcomes. It does not launch jobs or modify the queue. Parent owns its shared documentation hunks.

- Queue reconciliation fix: parent owns the `pid_state` hunk in `scripts/run_internal_profile_queue.py` and focused tests in `tests/test_run_internal_profile_queue.py`. A completed lab-server child remains a macOS zombie. Treat confirmed `Z` process status as terminated, then require the existing final-event and artifact checks. Do not retry the launch or change the server.

- G2 offline validation preparation: agent `trace_profile` owns new `docs/reports/2026-09-27_all-profile-rerun/validate_naflex_index.py`. It reads index metadata and vector arrays only. It performs no inference, image processing, source mutation, or launch. The parent reviews and executes it after the index build.

- Terminal G1 label analysis: agent `review_bulk_harness` owns new `docs/reports/2026-09-27_all-profile-rerun/label-comparison-final.md` and `.json`. Compare only the saved, validated G1 run artifacts and frozen attempt identities. No inference or source-image decoding. Parent owns G2 prerequisite execution and queue state.

- Later remote group preparation: agent `trace_profile` owns new `docs/reports/2026-09-27_all-profile-rerun/remote-group-launch-template.txt`. Adapt the reviewed one-profile G2 gate for G3 through G9. Keep model registry and residency checks, both memory thresholds, source verification, strict serial order, durable dispatcher intent, and no duplicate attempt. Prepare only; the parent reviews before execution.

- G2 plain-profile analysis: agent `review_demo_benchmark` owns new `docs/reports/2026-09-27_all-profile-rerun/g2-plain-comparison.md` and `.json`. Read the seven completed plain NaFlex profiles and frozen artifacts only. Compare paired crop and background-removal changes. Preserve catalogue coverage and cached-bulk timing limits. No inference, network requests, image decoding, or production edits.

- G2 barcode-pair analysis: agent `review_demo_benchmark` owns new `docs/reports/2026-09-27_all-profile-rerun/g2-barcode-comparison.md` and `.json`. Compare all seven completed barcode profiles with the matched plain profiles. Use saved artifacts only. Validate changed query IDs, barcode returns, cache flags, and fixed denominators. No inference, network requests, image decoding, or production edits.

- Full-set annotation audit: agent `review_demo_benchmark` owns new `docs/reports/2026-09-27_all-profile-rerun/annotation-audit.md` and `.json`. Read the frozen baseline query metadata only. Check repeated-digest positive truth conflicts and negative constraints. Do not change labels, decode images, rerun inference, or alter raw result denominators.

## /root

- Task: review `svoe-wino-hackaton/presentation/ЛЦТ2026 Моя презентация.pptx`
  against the hackathon rules and the current `svoe-vino-lab` evidence. Give a
  slide-by-slide list of content, evidence, and visual additions. Do not edit the deck.
- Source: owner messages of 2026-09-27T01:15:00+0300 and 2026-09-27T01:16:00+0300.
- Files: `docs/owner-messages.md` (append) and
  `../svoe-wino-hackaton/presentation/REQUESTS.md` (append), and
  `../svoe-wino-hackaton/presentation/content-audit-2026-09-27.md` (new), and
  `../svoe-wino-hackaton/ChangeLog.md` (one entry).
- State: done, not committed. The deck stayed unchanged. The review document, request
  logs, and the hackathon ChangeLog entry are complete.
- Updated: 2026-09-27T01:27:05+0300.

- Task 2: create a prioritized implementation backlog from the presentation audit and
  the current project state. Do not change the deck or the product code.
- Source: owner message of 2026-09-27T01:29:32+0300.
- Files for task 2: `docs/owner-messages.md` (append) and
  `../svoe-wino-hackaton/presentation/REQUESTS.md` (append).
- State for task 2: done, not committed. The backlog separates submission blockers,
  recognition quality work, evidence work, and optional roadmap items. It includes
  acceptance criteria for the official API, the real web flow, the useful function,
  the final benchmark, and the public release package.
- Updated for task 2: 2026-09-27T01:34:00+0300.

- Task 3: explain every failure in run
  `2026-09-26T213857Z-lab-barcode-rerank-siglip2-512-crop-my` and rank validated
  matching-pipeline fixes by the Pareto rule. Do not change product code.
- Source: owner messages of 2026-09-27T01:35:00+0300 and
  2026-09-27T01:36:00+0300.
- Files for task 3: `docs/owner-messages.md` (append), a new report in
  `docs/reports/`, and my own small hunk in `ChangeLog.md`.
- State for task 3: done, not committed. The report explains all 49 `after_5` rows.
  Twenty-nine rows are structurally unretrievable because 13 expected wines have no
  full or label row in the run index. Thirteen expected wines are at ranks 6 to 9.
  Seven indexed expected wines are absent from the top ten. The report also records
  the exact reranker gates, duplicate labels, wrong product labels, rear-view cases,
  the preprocessing skew, offline counterfactual checks, and the Pareto implementation
  order. No product code or inference job changed. Validation: all 49 expected query
  ids occur once in the item tables; Markdown diff whitespace check passes.
- Updated for task 3: 2026-09-27T01:55:44+0300.

- Task 4: create a derived test set from the R@1 misses of run
  `2026-09-27T011711Z-lab-barcode-rerank-siglip2-512-crop-my`.
- Source: owner message of 2026-09-27T08:16:43+0300.
- Files for task 4: `docs/owner-messages.md` (append), `data/lab.sqlite3` (the new test
  set), one small hunk in `ChangeLog.md`, and this section of `ACTIVE_WORK.md`.
- State for task 4: done, not committed. The set `my-1` has 252 positive photos in 156
  places. No selected photo was left out. The set also has 43 photo comments and all 63
  variant-group slugs of `my`. The source set still has 4,043 photos.
- Updated for task 4: 2026-09-27T08:18:19+0300.

## drink-atlas-workspace-d8 [a08e7a]

- Task: a column `modified_at` in `wine_code` (the insert time of each row), in the API and
  on the Dataset page.
- Source: owner message of 2026-09-27T08:30:51+0300 and owner answers of about 08:32 and 08:35.
- Files: `docs/owner-messages.md` (append), `pipeline/schema/026_wine_code_time.sql` (new;
  number 026 taken at 08:44:52 after messages to c7 and cb; f4 and 6c have no schema work), `pipeline/lab_server.py` (`wine_codes`,
  `dataset_records`, `_code_answer`), `pipeline/pages/dataset.html` (the GTIN and QR URL
  editors), `tests/test_labdb.py`, `tests/test_lab_server.py`,
  `tests/test_seed_codes.py` (one positional INSERT), `docs/API.md`,
  `docs/database-structure.html`, and my own hunks in `ChangeLog.md`, `SMOKE_TESTS.md`,
  `README.md`. A migration of `data/lab.sqlite3` and a restart of 8168.
- State: active. f4 [8de48d] committed at about 08:35 and plans no schema work.
  The owner allowed at about 08:35 separate hunks in the files of the stale sections, a
  backup of `data/lab.sqlite3`, the migration, and a restart of 8168. The owner chose a
  map `_code_times` and a tooltip on the Dataset page.
- Updated: 2026-09-27T08:44:52+0300
- Agreements: 6c [e05b96] told at about 08:40 that it adds separate hunks in
  `dataset.html` (`atlasProductFromUrl`, a "paste" listener). They do not touch my GTIN
  and QR URL editor hunks.

## drink-atlas-workspace-6c [e05b96]

- Task: a paste of a product URL `…/products/<uuid>` into the input of `Atlas Core
  product` inserts the UUID alone.
- Source: owner message of about 2026-09-27T08:37:00+0300, answers of 08:40.
- Files: `docs/owner-messages.md` (append), `pipeline/pages/dataset.html` (a new
  function `atlasProductFromUrl` after `atlasProducts`, and a new `paste` listener after
  the `input` listener of `#list`), and my own hunks in `ChangeLog.md`,
  `SMOKE_TESTS.md` (AB14, AB15), and `README.md` (one new line after the Atlas paragraph
  of the Dataset page). No restart: the page is read from disk.
- State: done, not committed. Waiting: the owner decides the commit. The owner allowed at
  08:40 separate hunks in `dataset.html`. The lines of d8 [a08e7a] (the GTIN and QR URL
  editors) and of f2 and bc (stale) stay unchanged. A Playwright check on 8168 passed 8
  of 8 cases, with no POST, no DELETE, and no page error. No restart.
- Updated: 2026-09-27T08:43:00+0300
- Agreements: d8 [a08e7a] was told at about 08:41; d8 recorded it in its section.
