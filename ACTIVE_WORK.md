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

- Task 5: explain the failures of run
  `2026-09-27T070800Z-lab-barcode-rerank-siglip2-512-crop-my-1` and give a prioritized
  fix plan. Do not change product code.
- Source: owner message of 2026-09-27T10:13:36+0300.
- Files for task 5: `docs/owner-messages.md` (append), a new report in
  `docs/reports/`, and this section of `ACTIVE_WORK.md`.
- State for task 5: done, not committed. The report separates 67 exact-byte
  alternate-valid results from 153 genuine misses. It explains the ten raw-rank-one
  reranker demotions, eight decoded but unmapped codes, five top-ten retrieval misses,
  index coverage, label-fusion evidence, and the prioritized repair sequence. The run
  artifacts and product code stayed read-only.
- Updated for task 5: 2026-09-27T10:26:13+0300.

## drink-atlas-workspace-c7 [09419d]

- Task: a global key of `config.yaml` that updates the embedding of a pipeline before
  each run of that pipeline, set to true.
- Source: owner messages of 2026-09-27T08:40:19+0300 and 08:40:26, answers of 08:53:00
  (update the changed items; `Run>` and the CLI; a failed build fails the run; separate
  hunks in the files of the stale sections are allowed).
- Files: `docs/owner-messages.md` (append), `docs/plans/59_rebuild-embeddings-on-run.md`
  (new), `pipeline/rebuild_on_run.py` (new), `tests/test_rebuild_on_run.py` (new),
  `config.yaml` (one new top-level key after `embedding_python`), `pipeline/run_job.py`
  (one import, one call before `build`, one docstring paragraph),
  `pipeline/embedding_run.py` (one import, one call in `main`, one docstring sentence),
  and my own hunks in `ChangeLog.md`, `SMOKE_TESTS.md` (section RB after NB10),
  `README.md` (3 hunks). No schema change. No restart: `run_job.py` and the build are
  read from disk for each job.
- State: done, not committed. Waiting: the owner decides the commit. Live since about
  09:00: the key is true in `config.yaml`. Tests: `test_rebuild_on_run.py` 17 OK, the full
  suite 1,164 OK (5 skipped). No live run by this session (it sends requests to gx10).
- Updated: 2026-09-27T19:36:00+0300
- Agreements: 1d [e2bf93] restarted 8168 at about 14:37; c7 checked at 14:38 that the
  server does not call `before_run` (no change of server behavior). 4e [ff960b] asked at
  about 19:34 for separate hunks in `pipeline/embedding_run.py` (plan 64:
  `Catalogue.rank` and `EmbeddingBackend.ask`, `only` -> `first`). c7 answered "ok" with
  conditions: my lines 14 to 16, 60, and 697 stay byte-identical; 4e commits only its own
  hunks through a private index; 4e runs `test_rebuild_on_run.py` (17 OK) after its edit.

## drink-atlas-workspace-a8 [c74148]

- Task: a `Paste image` tile after the tile "Drop photos here or choose files" of
  `Alternative photos` on `/dataset`.
- Source: owner message of 2026-09-27T08:55:08+0300.
- Files: `docs/owner-messages.md` (append); separate hunks in `pipeline/pages/dataset.html`
  (the alternative CSS, the tile in the alternative editor, one click branch, one paste
  listener, one function); my own hunks in `ChangeLog.md`, `SMOKE_TESTS.md`, `README.md`.
  No restart: the page is read from disk.
- State: done, not committed; waiting: the owner decides the commit. The owner chose
  "Click + ⌘V" and "Replace it" at about 08:57; I removed the stale section
  codex-dataset-clipboard. 24 of 24 Playwright checks pass on 8168 with mocked write
  requests; nothing was saved. Smoke tests PI1 to PI7.
- Updated: 2026-09-27T20:21:00+0300
- Agreements: d8 [a08e7a] and 6c [e05b96] got a message about my hunks in
  `dataset.html` at about 09:04. 6c answered "no objection"; it holds no claim on the
  file. My paste listener is a separate listener; the Atlas listener is unchanged.
  1d [e2bf93] told at about 14:35 that it adds separate hunks to `dataset.html` (the
  describe dialog functions, the popstate listener, the init block), none near my
  hunks; it commits its own hunks alone. I have no objection; no answer was needed.
  d8 [a5ab96] told at about 14:54 that it adds separate Atlas "approve" hunks to
  `dataset.html` (`atlasBindingEditor`, a new `approveAtlasBinding`, one branch of the
  `.atlas-binding-editor` click handler, one CSS line); my hunks stay byte-identical; it
  commits its own hunks alone. I have no objection; no answer was needed.
  2f [0e9cfe] asked at about 15:23 for separate hunks of plan 62 in `dataset.html`
  (`similarEditor`, one line of `recordHtml`, 2 functions, a datalist, one click branch,
  one keydown branch, CSS) and a later restart of 8168. I answered "ok" at 15:25: my
  lines stay byte-identical; its click branch stays outside the `.alternative-editor`
  block; one unchanged line at least between its hunks and mine; a restart is fine.
  2f told at about 15:50 that plan 62 is live (8168 restart at 15:47, pid 47252). I
  checked at 15:55: my 6 blocks are byte-identical; the Playwright check passes 24 of 24
  again (the script now waits for the delayed render of the search input).
  1e [7df1e0] asked at about 17:10 for separate hunks of plan 63 (wine tags) in
  `dataset.html` (CSS, `tagEditor`, one card line, new functions, one branch in each of
  the click, input, and keydown listeners of `#list`), schema 029, and a restart of
  8168. I answered "ok" at 17:12 with the conditions of 2f: my lines stay
  byte-identical; its click branch stays outside the `.alternative-editor` block; one
  unchanged line at least between its hunks and mine.
  06 [1b7eb8] asked at about 19:31 to change one line of `dataset.html`: the
  `max-height: 310px` of `.alternative-grid` (owner message of 19:30:17). I answered
  "ok" at 19:32; the line is not mine, and my lines stay byte-identical.
  06 told at about 19:34 that the change is in (310px -> 620px, line 280 alone). My
  lines are unchanged (checked at 19:34). 06 committed d5d46e6 at 20:19; I checked
  at 20:21: it holds none of my lines, and my hunks stay uncommitted in the tree.

## drink-atlas-workspace-d7 [604e28]

- Task: research how the top-k search can use label-space embeddings and fuse them with
  the full-bottle embeddings. Research only; no code change.
- Source: owner message of 2026-09-27T10:13:59+0300.
- Files: `docs/owner-messages.md` (append), `docs/reports/2026-09-27_label-fusion.md`
  (new), `docs/reports/2026-09-27_label-fusion/fusion_replay.py` (new, read-only replay of
  saved runs), `ResearchLog.md` (one entry at the top), my own hunk in `ChangeLog.md`.
- State: done, not committed; waiting: the owner chooses option A, B, or C of the report.
- Updated: 2026-09-27T10:21:21+0300

## drink-atlas-workspace-38 [2e502f]

- Task: explain the failures of the run
  `2026-09-27T070800Z-lab-barcode-rerank-siglip2-512-crop-my-1` and propose fixes.
  Research only; no code change without the owner's word.
- Source: owner message of 2026-09-27T10:13:36+0300 (already in
  `docs/owner-messages.md`).
- Files: `docs/owner-messages.md` (append); new
  `docs/reports/2026-09-27_my-1-failure-addendum.md`; new
  `docs/reports/2026-09-27_my-1-failure-addendum/replay.py`; one entry at the top of
  `ResearchLog.md`; one entry in `ChangeLog.md`. I do not change
  `docs/reports/2026-09-27_my-1-failure-analysis.md` (another session wrote it at 10:26).
- State: done, not committed; waiting: the owner chooses the fixes and decides the
  commit. The report, the script, and the two log entries are written. No code change.
- Updated: 2026-09-27T10:48:00+0300

## drink-atlas-workspace-1d [e2bf93]

- Task: a page path that opens the Image description dialog of `/dataset`:
  `/dataset/<wine_slug>/describe/<sha256>`. The address bar follows the dialog; Back
  closes it. No "Copy link" button.
- Source: owner message of 2026-09-27T13:49:11+0300 and the answers after it.
- Files: `docs/owner-messages.md` (append), `pipeline/lab_pages.py`
  (`DATASET_PREVIEW_ROUTE` and its comment), `pipeline/pages/dataset.html` (separate
  hunks: new describe path functions next to `openDescribe`, `openDescribe`,
  `closeDescribe`, the `popstate` listener, the `init` block), `tests/test_lab_server.py`
  (`test_dataset_preview_paths_send_the_page`), and my own hunks in `README.md`,
  `ChangeLog.md`, `SMOKE_TESTS.md`. A restart of 8168 for `lab_pages.py`.
- State: done, not committed. Waiting: the owner decides the commit. 8168 restarted by 1d
  at 14:37:41 (pid 13418); `GET /api/dataset` answers 200. Tests: `test_lab_server.py` 64
  OK, `test_lab_pages.py` 4 OK. 16 of 16 Playwright checks pass on 8168 (write requests
  blocked; nothing saved). Docs: `README.md`, `ChangeLog.md`, `SMOKE_TESTS.md` (ID31 to
  ID34).
- Updated: 2026-09-27T14:45:00+0300
- Agreements: the owner allowed separate hunks in the files of the stale sections 6c
  [c91c62], 41 [501d23], d3, f2, and bc.
  6b [e99257] answered "ok" at about 14:36: it adds one line `loadLabelDescriptions(sha);`
  before `$("#describe-modal").hidden = false;` in `openDescribe`, and other hunks outside
  my lines; it does not change `closeDescribe`, the `popstate` listener, or `init`.
  c7 [09419d] answered at 14:38: the restart loads its `embedding_run.py` and
  `rebuild_on_run.py`, with no change of server behavior. a8 and d8 were told.
  d8 [a5ab96] told at about 14:50 that it adds separate Atlas "approve" hunks in
  `dataset.html` and `tests/test_lab_server.py` (owner message of 14:49:04); 1d has no
  objection: no overlap with my hunks.
  2f [0e9cfe] asked at about 15:15 for separate plan 62 hunks in `dataset.html` and
  `tests/test_lab_server.py`; 1d answered "ok" with one condition: the `popstate`
  listener next to its keydown branch stays byte-identical.
  2f reported at 15:47 that plan 62 is live (8168 pid 47252) and my lines are intact; 16 of
  16 Playwright checks passed again after it.
  1e [7df1e0] asked at about 16:00 for separate plan 63 hunks in `dataset.html` and
  `tests/test_lab_server.py`; 1d answered "ok": my lines stay byte-identical.

## drink-atlas-workspace-6b [e99257]

- Task: plan 61, label descriptions of the images: a history table of the answers of
  `label_rules.DESCRIBE_PROMPT`, stage 3 of the watcher, a key repair and a check, the key
  repair in `label_rules.describe`, and a history view with edit and remove in the image
  description dialog of `/dataset`.
- Source: owner message of 2026-09-27T13:55:59+0300, answers of about 14:15:00; plan
  `docs/plans/61_label-descriptions.md`.
- Files: `docs/owner-messages.md` (append), `docs/plans/61_label-descriptions.md` (new),
  `pipeline/schema/027_image_label_description.sql` (new; 027 taken at 15:16:26), `pipeline/label_descriptions.py` (new),
  `pipeline/label_description_routes.py` (new), `tests/test_label_descriptions.py` (new).
  After the owner allows it (files of stale sections): separate hunks in
  `pipeline/describe_images.py`, `pipeline/image_descriptions.py` (`call_view`,
  `watcher_status`), `pipeline/label_rules.py` (`describe`, one import),
  `pipeline/lab_server.py` (docstring, import, 2 route branches, one handler),
  `pipeline/pages/dataset.html` (CSS, a new dialog section, new functions, one line in
  `openDescribe`, the pill texts), `config.yaml` (one key `labels` in
  `image_description`), `tests/test_describe_images.py`, `tests/test_label_rules.py`,
  `tests/test_labdb.py` (VERSION, table list), and my own hunks in `README.md`,
  `COMMANDS.md`, `docs/API.md`, `SMOKE_TESTS.md`, `ChangeLog.md`, `ResearchLog.md`, one
  dated note at the end of plan 45. Later: a migration of `data/lab.sqlite3`, a restart of
  8168, one row in `/Users/ashmelev/Admin/GPU_TASKS.md`.
- State: done, not committed. The backlog of stage 3 ended at 16:49 (2,162 of 2,166; 2
  failed). Waiting: the owner decides the commit. 027 is live: `data/lab.sqlite3` at version 27 since 15:16:56 (backup
  `data/backups/lab-before-027-image-label-description-20260927T121654Z.sqlite3`). 8168
  restarted by 6b at 15:17:20 (pid 55047, watcher pid 55081, `caffeinate` pid 57284; the
  keeper `work/plan61-caffeinate.sh` pid 79610 holds `caffeinate` across restarts); the
  GPU row is in `GPU_TASKS.md`. Tests: full suite 1,211 OK in the live tree. Docs done:
  README, COMMANDS, docs/API.md, SMOKE_TESTS (LD1 to LD12), ChangeLog, ResearchLog, plan 45
  note, plan 61 result. Scratch copy of the work: session scratchpad `lab61/`.
- Updated: 2026-09-27T17:13:34+0300
- Agreements: 1d [e2bf93] changes `openDescribe`, `closeDescribe`, the `popstate`
  listener, and the `init` block of `dataset.html` (its hunks are on disk). I add one line
  in `openDescribe` before `$("#describe-modal").hidden = false;` and no line in
  `closeDescribe` (agreed at about 14:30). I send 1d a message before a restart of 8168.
  2f [0e9cfe] (plan 62, schema 028 `wine_similar`) asked at about 15:25 for separate hunks
  in `lab_server.py`, `dataset.html`, `tests/test_labdb.py` (VERSION 28, one table name),
  and a later restart of 8168. 6b answered "ok": my lines stay byte-identical; 2f sends
  me the new watcher pid after its restart (not needed since the keeper runs; 2f was told).
  2f restarted 8168 at 15:47 for schema 028 (pid 47252, watcher pid 47284); 6b checked at
  15:55: stage 3 goes on (697 of 2,163 done), the plan 61 lines are byte-identical, and
  the plan 61 tests pass with VERSION 28.
  00 [8866fa] asked at about 16:53 for separate hunks in `pipeline/lab_server.py`
  (`import model_cache`, `forget_scans`, one call each in `add_code` and `remove_code`,
  `OSError` in `_code`) and `docs/API.md` (the code routes), then a restart of 8168
  (owner message of 16:08). 6b answered "ok": my lines stay byte-identical; the stage 3
  watcher resumes by itself after the restart.
  1e [7df1e0] (plan 63, wine tags, schema 029 `wine_tag`) asked at about 17:12 for separate
  hunks in `lab_server.py`, `dataset.html`, `tests/test_labdb.py` (VERSION 29, one table
  name), `docs/API.md`, and a restart of 8168. 6b answered "ok": no place is next to my
  lines; I have no more schema work.
  00 restarted 8168 at 17:09:02 (pid 7024, watcher pid 7068, `labels on`); 6b checked at
  17:13: the watcher described the last pending image and is idle (2,173 of 2,175 done,
  2 failed); the plan 61 files are byte-identical.

## drink-atlas-workspace-64 [a6a2b4]

- Task: a button `Build All` on `/embedding` that starts the build of each embedding.
- Source: owner message of 2026-09-27T14:33:25+0300. Plan `docs/plans/60_build-all-embeddings.md`.
- Files: `docs/owner-messages.md` (append), `docs/plans/60_build-all-embeddings.md` (new),
  separate hunks in `pipeline/embedding_routes.py` (docstring, one route branch, the queue
  functions, the queue in the list and jobs answers, `pop` in `_reap`) and
  `pipeline/pages/embedding.html` (the button, its message, the poll), one new class at
  the end of `tests/test_embedding_routes.py`, and my own hunks in `ChangeLog.md`,
  `SMOKE_TESTS.md` (EB48 to EB54), `README.md`. A restart of 8168 for `embedding_routes.py`.
- State: done, not committed. Waiting: the owner decides the commit. The owner chose
  "One at a time, server" and "Yes, separate hunks" at about 14:40. The stale claims of
  41 and codex-side-sam3-fix on these files are committed in c863231; my hunks leave
  their lines as they are. 8168 restarted by 64 at 14:44:31 (pid 38527); the restart
  deployed only `embedding_routes.py` (each other pending server file is older than the
  server of 1d of 14:37:41). Tests: `test_embedding_routes.py` 23 OK; full suite 1,169 OK
  (5 skipped). 39 of 40 Playwright checks on 8168 with each POST mocked or blocked; the
  failed check is an old horizontal scroll at 390 px from the `Configuration` select.
  No live `Build All` by this session (it sends requests to gx10).
- Updated: 2026-09-27T14:54:50+0300
- Agreements: d8 [a5ab96] asked at about 14:54 whether a restart of 8168 may load my
  `embedding_routes.py`. I answered (a): safe to load; no Build All queue runs.

## drink-atlas-workspace-d8 [a5ab96]

- Task: a button `approve` on an automatic Atlas Core product of a Dataset card. It changes
  the source of the row from `automatic` to `manual`.
- Source: owner message of 2026-09-27T14:49:04+0300, answers of 14:54:07 (a new approve
  route; separate hunks in the files of the stale section bc).
- Files: `docs/owner-messages.md` (append), separate hunks in `pipeline/atlas_bindings.py`
  (`approve`), `pipeline/lab_server.py` (docstring, `approve_atlas_binding`,
  `_atlas_binding`, one route branch), `pipeline/pages/dataset.html` (one CSS line,
  `atlasBindingEditor`, `approveAtlasBinding`, the Atlas click handler),
  `tests/test_atlas_bindings.py`, `tests/test_lab_server.py` (`approve_atlas`,
  `test_approve_makes_an_automatic_product_manual`), and my own hunks in `README.md`,
  `ChangeLog.md`, `SMOKE_TESTS.md` (AA1 to AA7), `docs/API.md`.
- State: done, not committed. Waiting: the owner decides the commit. No schema change.
  8168 restarted by me at 14:57:17 (pid 88971); `GET /api/dataset` answers 200. Tests:
  `test_atlas_bindings.py` 9 OK, `test_lab_server.py` 65 OK, `test_dataset_atlas_bindings.py`,
  `test_seed_atlas_bindings.py`, `test_labdb.py` OK. Playwright on 8168 in dark and light
  mode: 20 of 20 checks pass (the approve POST mocked; nothing saved).
- Updated: 2026-09-27T14:59:06+0300
- Agreements: 6b [e99257] "no objection" (its plan 61 code is in a scratch copy; my restart
  deploys nothing of it). 64 [a6a2b4] said embedding_routes.py is safe to load and no
  Build All queue ran. 1d [e2bf93] "ok, no objection". a8 [c74148] was told.
  6b told me at about 15:05 that it enters schema 027, migrates, and restarts 8168; my
  Atlas lines stay byte-identical. Checked after its restart (pid 55047): `/api/dataset`
  200, the approve route answers (404 for an unknown wine), the page has the button.
  2f [0e9cfe] (plan 62, a manual `similar` pair; owner message of 15:12:00): I answered
  "ok with 3 conditions" at 15:24 to separate hunks after my approve blocks in
  `lab_server.py`, `dataset.html`, and a new class in `tests/test_lab_server.py`: my
  approve lines stay byte-identical; each session commits only its own lines (private
  index, hand-built patch where hunks touch); after its restart, `test_atlas_bindings.py`
  and `test_lab_server.py` pass and the approve route still answers.
  2f reported plan 62 live at 15:47 (8168 pid 47252, schema 028). I checked: my approve
  lines are in place, the route answers 404 for an unknown wine, `test_atlas_bindings.py`
  9 OK, `test_lab_server.py` 67 OK. Conditions met.
  00 [8866fa] (owner message of 16:08, a GTIN or QR URL change deletes the barcode scan
  records of the wine): I answered "ok with 2 conditions" at 16:53 to separate hunks
  in `lab_server.py` (import, `forget_scans`, `add_code`, `remove_code`, `_code`) and in
  the code-route section of `docs/API.md`: my approve lines stay byte-identical, each
  session commits only its own lines; after its restart, `test_atlas_bindings.py` and
  `test_lab_server.py` pass and the approve route still answers.
  1e [7df1e0] (plan 63, wine tags, schema 029): I answered "ok with 2 conditions" at 17:11
  to separate hunks in `lab_server.py`, `dataset.html`, `tests/test_lab_server.py`, and
  `docs/API.md`, with the same 2 conditions as 00.
  00 reported its restart at 17:09:02 (pid 7024). I checked: my approve lines are in
  place, the route answers 404 for an unknown wine, `test_atlas_bindings.py` 9 OK,
  `test_lab_server.py` 67 OK. The conditions of 00 are met.
  06 [1b7eb8] (owner message of 20:08:45, a badge for an Atlas UUID of 2 or more wines):
  I answered "ok with 3 conditions" at 20:10 to its change of the `open` line of
  `atlasBindingEditor` (2 lines below my hunk) and the kind `atlas` in `codeUsers` and
  `codePeers`: my approve lines stay byte-identical; it commits its line alone by a
  hand-built patch (git shows one merged hunk); it tells me when its hunks are on disk,
  and I re-run my browser check of the approve button.
  06 reported its hunks on disk. I re-ran the check: 20 of 20 approve checks pass in dark
  and light mode; on `nebbiolo` the order is source, approve, copy, open, `2 wines`, and
  the badge stays after an approve (POST mocked; nothing saved). The conditions of 06 are met.
  06 committed d5d46e6 at 20:19:55. I checked: no approve line of mine is in it; my 9
  approve lines of `dataset.html` stay uncommitted in the tree. Its ChangeLog text and
  smoke row AS3 name the approve button, which enters HEAD with my commit.

## drink-atlas-workspace-2f [0e9cfe]

- Task: paste of an image from the clipboard (Ctrl+V / Cmd+V) on `/recognize`.
- Source: owner message of 2026-09-27T15:04:13+0300.
- Files: `docs/owner-messages.md` (append), `pipeline/pages/recognize.html` (the drop
  hint, one `paste` listener), and my own hunks in `ChangeLog.md` and `SMOKE_TESTS.md`.
  The stale section 41 [501d23] lists `recognize.html`; its work is committed in c863231.
  The owner asked for this change of the page directly.
- State: done, not committed. Waiting: the owner decides the commit. No restart: the
  server reads the page from disk for each request. Checks: 9 of 9 browser checks on the
  live page (synthetic paste, text paste, real ControlOrMeta+V from the clipboard; POST
  mocked, no pipeline ran); 390 px light and dark with no horizontal scroll; RC1 tests OK.
- Updated: 2026-09-27T15:09:00+0300
- Task 2: a manual two-way relation `similar` between two wines on `/dataset`; the
  cluster build adds the other wine of a pair to the cluster of the first wine.
- Source 2: owner message of 2026-09-27T15:12:00+0300.
- Files 2: `docs/owner-messages.md` (append), `docs/plans/62_similar-wines.md` (new),
  `pipeline/schema/028_wine_similar.sql` (new; 028 taken at 15:46:57; 6b has no second schema file),
  `pipeline/similar_wines.py` (new), `tests/test_similar_wines.py` (new),
  `pipeline/clusters.py` (`context`, `build`, `components`, one new function),
  `tests/test_clusters.py` (new tests). Separate hunks after agreement:
  `pipeline/lab_server.py` (docstring paragraph, import, `dataset_records`,
  `dataset_view`, 2 new functions, one handler, one route branch),
  `pipeline/pages/dataset.html` (new CSS lines, `similarEditor`, one line in
  `recordHtml`, 2 new functions, a datalist, one click branch, one keydown branch),
  `pipeline/pages/clusters.html` (one CSS line `.badge.manual`), `tests/test_labdb.py`
  (VERSION, table list), `tests/test_lab_server.py` (a new class at the end), and my own
  hunks in `docs/API.md`, `README.md`, `ChangeLog.md`, `SMOKE_TESTS.md`. A migration of
  `data/lab.sqlite3` and a restart of 8168.
- State 2: done, not committed. Waiting: the owner decides the commit. Schema 028
  entered and migrated at 15:46:57 (backup
  `data/backups/lab-before-028-wine-similar-20260927T124657Z.sqlite3`). 8168 restarted by
  2f at 15:47 (pid 47252, watcher pid 47284); only plan 62 was pending. Tests: full suite
  1,223 OK (5 skipped); d8 checks pass (`test_atlas_bindings.py`, `test_lab_server.py`,
  the approve POST with `no-such-wine` answers 404). Browser: 19 of 19 on a scratch
  server, 5 of 5 on 8168 with the writes mocked; 0 pairs in the real table. My hunks went
  in by `patch -F0`; the lines of the other sessions are byte-identical.
- Updated 2: 2026-09-27T15:55:00+0300
- Agreements 2: the owner allowed separate hunks in the files of the stale sections
  (15:31). 6b "ok": 028 is mine; its plan 61 lines stay byte-identical; `wine_similar`
  in its alphabetical place in `test_labdb.py`; a restart is fine. a8 "ok": its Paste
  image lines stay byte-identical; my click branch outside the `.alternative-editor`
  block; one unchanged line between our hunks. 1d "ok": its `popstate` listener and its
  test lines stay byte-identical; my patch against the present file. d8 [a5ab96] "ok":
  its approve lines stay byte-identical; each session commits its own lines (private
  GIT_INDEX_FILE); after the restart `test_atlas_bindings.py` and `test_lab_server.py`
  pass and the approve POST with `no-such-wine` answers 404. d8 [a08e7a] "ok".
  00 [8866fa] asked at about 16:10 for separate hunks in `pipeline/lab_server.py`
  (`import model_cache`, `forget_scans`, calls in `add_code`/`remove_code`, `OSError` in
  `_code`) and `docs/API.md` (the code routes section); I answered "ok" with conditions:
  my plan 62 lines stay byte-identical, `_code_write` does not change, one unchanged line
  between our hunks, each session stages its own hunks; its restart of 8168 is fine.
  1e [7df1e0] (plan 63, wine tags, schema 029) asked at about 16:15 for hunks next to my
  plan 62 hunks in `lab_server.py`, `dataset.html`, `test_labdb.py`, `test_lab_server.py`,
  `docs/API.md`. I answered "ok" with conditions: my lines stay byte-identical, except
  `VERSION, 28` and the closing line `"wine_similar"])` of `test_labdb.py`; each session
  commits its own lines (private GIT_INDEX_FILE, a hand-built patch where hunks touch);
  plan 62 (028) is committed before 029 or in the same commit; its restart is fine, then
  it checks `similar_pairs`, `test_similar_wines.py`, and `test_clusters.py`.
  4e [ff960b] (plan 64, a shared GTIN as a forced link) asked at about 19:30 for hunks
  next to my plan 62 lines in `clusters.py`, `clusters.html`, `test_clusters.py`. I
  answered "ok", option A: it adds `by=MANUAL` to `manual_links` (the `def` line, the 2
  uses of `MANUAL`, and its docstring change); every other plan 62 line stays
  byte-identical; `ManualPairTest` passes unchanged; with no GTIN pair the hash stays;
  its commit comes after my plan 62 commit or in the same commit.
  4e asked at about 20:13 for one more hunk in `clusters.html` (`cardImage` before
  `memberHtml`, one line in `memberHtml`); I answered "ok": my `.badge.manual` lines stay.
  06 [1b7eb8] (owner bug report of 20:22:30: a hidden partner opened a new tab that
  restores the same search) asked at about 20:25 to change the `[data-similar-open]`
  branch of my `.similar-editor` click block in `dataset.html` (4 lines), add
  `openSimilarCard` after `scrollToCard`, and change SW6. I answered "ok" with
  conditions: no second card with the same id; it also changes the new-tab sentence of my
  README paragraph; it commits after my plan 62 commit; each session stages its own lines.
  06 reported the fix on disk at about 20:40 (30 of 30 browser checks). At my plan 62
  commit: send one line to 06, 4e, and 1e (they commit after it). My commit uses my own
  lines; the 06 lines of the similar-open branch, README line 241, and SW6 go in the 06
  commit.
  1c [b72be3] (plan 65, Build all clusters) asked at about 22:10 for hunks in
  `clusters.html` (a `#build-all` button and a `#queue` span, one line in `loadList`, new
  queue functions); I answered "ok": my `.badge.manual` lines stay.
  e3 [c13919] (owner answers of 23:15:34: visible text only, "Hard cases") asked at about
  23:20 to change the visible texts of plan 62 in `dataset.html` (9 text lines),
  README.md (2 lines + 1 sentence), SMOKE_TESTS.md (heading, SW2, SW5), docs/API.md
  (heading, first sentence), and a note at the end of plan 62. I answered "ok": text only,
  every identifier and server text and the 06 lines stay; `node --check` and the route
  tests pass; it commits after my plan 62 commit. Notify e3 at my commit too.

## drink-atlas-workspace-00 [8866fa]

- Task: an add or a remove of a GTIN or a QR URL of a wine deletes the barcode scan
  records (`data/cache/barcode/`) of the test photos of that wine (`test_photo.place`).
- Source: owner message of 2026-09-27T16:08:37+0300, answers of 16:49:57.
- Files: `docs/owner-messages.md` (append); `pipeline/model_cache.py` (a new function
  `forget`); `tests/test_model_cache.py` (a new class at the end); new
  `tests/test_code_cache_forget.py`; separate new hunks in `pipeline/lab_server.py`
  (`import model_cache`, a new helper `forget_scans`, one call in `add_code` and in
  `remove_code`, `OSError` in the except of `_code`) and in `docs/API.md` (the code
  routes); my own hunks in `ChangeLog.md`, `SMOKE_TESTS.md`. A restart of 8168.
- State: done, not committed; waiting: the owner decides the commit. 8168 restarted by 00
  at 17:09:02 (pid 7024, watcher pid 7068); `GET /api/dataset` answers 200. Live check
  WC22 passed. Tests: 1,229 OK (5 skipped).
- Updated: 2026-09-27T17:13:30+0300
- Agreements: 6b "ok" (keep `import model_cache` a separate hunk from its import). d8
  [a5ab96] "ok": its approve lines byte-identical; after the restart
  `test_atlas_bindings.py` and `test_lab_server.py` pass and the approve route answers
  404 for `no-such-wine`. 2f "ok": its plan 62 lines byte-identical, `_code_write`
  unchanged, one unchanged line between hunks. The owner at 17:02:48 allowed separate hunks
  in the files of the stale sections. Commit through a private GIT_INDEX_FILE. 1e [7df1e0] asked at about 17:13 for
  separate hunks of plan 63 in `lab_server.py` and `docs/API.md`; 00 answered "ok": my
  lines byte-identical, one unchanged line between hunks; 1e restarts 8168 after 00.

## drink-atlas-workspace-1e [7df1e0]

- Task: plan 63, the tags of a wine: table `wine_tag`, module, routes
  `/api/dataset-tag`, the editor `Tags` on `/dataset`. No pipeline change (owner answer).
- Source: owner messages of 2026-09-27T17:04:20+0300 and 17:05:11+0300, answers of
  17:07:53. Plan `docs/plans/63_wine-tags.md`.
- Files: `docs/owner-messages.md` (append), `docs/plans/63_wine-tags.md` (new),
  `pipeline/schema/029_wine_tag.sql` (new; 029 taken at 17:20:28; 6b and 2f have no
  pending schema file), `pipeline/wine_tags.py` (new), `tests/test_wine_tags.py` (new); separate new
  hunks in `pipeline/lab_server.py` (docstring paragraph, import, `dataset_records`,
  `dataset_view`, new tag functions, one handler, one route branch),
  `pipeline/pages/dataset.html` (new CSS lines, `tagEditor`, one line in the card, new
  functions, one branch in each of the click, input, and keydown listeners),
  `tests/test_lab_server.py` (a new class at the end), `tests/test_labdb.py` (VERSION,
  one table name), and my own hunks in `docs/API.md`, `README.md`, `ChangeLog.md`,
  `SMOKE_TESTS.md`. A migration of `data/lab.sqlite3` and a restart of 8168.
- State: done, not committed. Waiting: the owner decides the commit. 029 goes with or after
  the plan 62 commit of 2f (condition 3 of 2f). 8168 restarted by 1e at 17:21 (pid 46259);
  1c restarted it again at 22:39 (pid 53022). Checks by 23:47: `test_wine_tags.py` 5,
  `test_lab_server.py` 69, `test_labdb.py` 17, `test_atlas_bindings.py` 9,
  `test_similar_wines.py` 5, `test_clusters.py` 27, `test_code_cache_forget.py` 4 OK; full
  suite 1,262 OK (5 skipped); the approve route answers 404 for `no-such-wine`;
  `similar_pairs` is sent. Browser 58 of 60 (the 2 failures: the old header overflow at
  390 px, not plan 63). Docs: plan 63 Result, README, API.md, SMOKE_TESTS WT1-WT10,
  ChangeLog.
- Updated: 2026-09-27T23:57:08+0300
- Agreements (all "ok", separate new hunks, their lines byte-identical, each session
  stages only its own hunks through a private GIT_INDEX_FILE):
  1d [e2bf93]: keep the describe block, `popstate`, `init`, and 3 path lines of
  `test_dataset_preview_paths_send_the_page`. d8 [a5ab96]: keep the approve lines; after
  my restart `test_atlas_bindings.py` and `test_lab_server.py` pass, and the approve route
  answers 404 for `no-such-wine`. a8 [c74148]: keep the Paste image lines; my click branch
  stays outside `.alternative-editor`; one unchanged line between hunks. 2f [0e9cfe]: keep
  every plan 62 line except `VERSION, 28` and the closing `"wine_similar"])` of
  `test_labdb.py`; 029 is committed with or after plan 62, never alone; after my restart
  `similar_pairs`, `test_similar_wines.py`, and `test_clusters.py` pass. 6b [e99257]: no
  condition; 029 is mine; keep the 2 `image_label_description*` names. 00 [8866fa]: keep
  `import model_cache`, the last 3 lines of `add_code`/`remove_code`, `forget_scans`, the
  `OSError` except, and the API.md entry of the barcode scans; one unchanged line between
  hunks; after my restart `test_code_cache_forget.py` passes (4 OK). 00 restarted 8168 at
  17:09:02. The owner allowed the files of the stale sections at 17:15:09.
  a4 [34c1c5] (plan 66, image tags, schema 030) asked at about 23:57 for my line
  `VERSION, 29` of `test_labdb.py`: I answered "ok" with conditions: "wine_tag" stays in
  the list; I have no pending schema file; commit chain 62 -> 63 -> 66, each with or after
  the one before; its `image_tags.py` imports `wine_tags.normal` and `TagError`.

## drink-atlas-workspace-4e [ff960b]

- Task: plan 64, a shared GTIN gives a soft re-rank: the GTIN wines go first, the other
  wines stay below them, and the GTIN wines become the window of the VLM re-rank. The
  cluster build links the wines of each shared GTIN.
- Source: owner message of 2026-09-27T17:12:18+0300, answer "3" of 17:16:05, answers of
  19:28:52 ("Auto cluster link", "Yes, separate hunks").
- Files: `docs/owner-messages.md` (append), `docs/plans/64_shared-gtin-rerank.md` (new).
  Separate hunks (owner answer of 19:28:52): `pipeline/barcode.py` (`CodeFirst`, the
  docstring), `pipeline/cluster_rerank.py` (`RuleBook.trigger`, `ClusterRerank.rerank`,
  `ClusterRerank.ask`), `pipeline/embedding_run.py` (`Catalogue.rank`,
  `EmbeddingBackend.ask`), `tests/test_barcode_shared.py`. After agreement with 2f:
  `pipeline/clusters.py` (a new helper, new lines in `context`, `build`, `components`),
  `pipeline/pages/clusters.html` (one CSS line), `tests/test_clusters.py` (a new class).
  My own hunks in `README.md`, `ChangeLog.md`, `SMOKE_TESTS.md`.
- State: done, not committed. Waiting: the owner says "commit" (owner answer "Leave it"
  of 20:09:06). The rollout is done: `clusters.json` of
  `gx10-siglip2-so400m-patch16-naflex-p256` rebuilt at 20:10:14, 19 rules built by 20:20:47
  (backups in `data/backups/*-before-plan64-*`), 8168 restarted by 4e at 20:21:54 (pid
  3472). The commit of `clusters.py` comes after the plan 62 commit of 2f, or with it.
- Updated: 2026-09-27T20:30:00+0300
- Agreements: 2f [0e9cfe] "ok", option A: I add a keyword `by=MANUAL` to `manual_links`
  and may change its `def` line, the two uses of `MANUAL` in its body, and its docstring.
  Every other plan 62 line in `clusters.py`, `clusters.html`, and `test_clusters.py` stays
  byte-identical; `ManualPairTest` passes unchanged; with no GTIN pair the input hash stays
  the same; I commit after the plan 62 commit or in the same commit, and each session
  stages its own lines; the restart after the owner's word is fine. c7 [09419d] "ok" for
  `Catalogue.rank` and `EmbeddingBackend.ask`: its plan 59 lines (14 to 16, 60, 697 at
  19:34) stay byte-identical; I stage only my hunks (private GIT_INDEX_FILE); after my edit
  `test_rebuild_on_run.py` gives 17 OK.
- Task 2: the cards of `/clusters` show the main image (`main_patched`, else `main`).
  Source: owner message of 2026-09-27T20:11:15+0300, answer of 20:16:16. Files:
  `pipeline/pages/clusters.html` (a new function `cardImage`, one line in `memberHtml`),
  my own hunks in `ChangeLog.md`, `SMOKE_TESTS.md`. State: done, not committed; browser
  check passed (420 cards, light and dark, 1,600 and 390 px). Agreements: 2f "ok",
  no other condition; the owner allowed separate hunks in `clusters.html` (stale d1
  [0feb34] and 41 [501d23]) at 20:16:16, also for my `.badge.gtin` line.

## codex-side-dataset-navigation

- Task: in the Dataset image preview, use Left and Right for the images of the current
  wine, and use Up and Down for the previous and next visible wine.
- Source: owner message and answer `1` of 2026-09-27T17:36:35+0300.
- Files: `docs/owner-messages.md` (append); separate preview-navigation hunks in
  `pipeline/pages/dataset.html`; and my own hunks in `ChangeLog.md` and
  `SMOKE_TESTS.md`.
- State: done, not committed. Left and Right move among the available files of one wine.
  Up and Down move among visible wines. The live 8168 page passed the button and key
  checks on the requested slug and its next wine. The browser log has no warning or
  error. JavaScript syntax, `test_lab_pages.py` (4), and `test_lab_server.py` (69) pass.
  `git diff --check` passes for the changed code and non-verbatim documents. No restart
  was needed because the server reads the page from disk.
- Updated: 2026-09-27T17:43:31+0300
- Agreements: The owner selected option 1. Keep the active wine-tag changes
  byte-identical. Add only separate preview-navigation hunks.

## drink-atlas-workspace-06 [1b7eb8]

- Task: a click on a similar wine goes to its card. A card in the list: scroll to it. A
  card that the filters hide: show it just below the card of the click, then scroll.
- Source: owner message of 2026-09-27T20:22:30+0300 and the answer after it.
- Files: `docs/owner-messages.md` (append); separate hunks in
  `pipeline/pages/dataset.html` (a new function `openSimilarCard` after `scrollToCard`;
  the `[data-similar-open]` branch of the `.similar-editor` click block of plan 62); my
  own hunks in `ChangeLog.md`; one sentence of SW6 in `SMOKE_TESTS.md` and one sentence of
  the plan 62 paragraph in `README.md` (2f lines, agreed). No restart.
- State: done, not committed; waiting: the plan 62 commit of 2f (condition 3), then the
  owner decides my commit. Browser check on 8168 (writes blocked): 30 of 30, dark and
  light, 1440 px and 390 px. Docs: ChangeLog, README (2f sentence), SW6 (2f row).
- Updated: 2026-09-27T20:44:00+0300
- Agreements: 2f [0e9cfe] answered "ok" at about 20:36 with 3 conditions: (1)
  `openSimilarCard` makes no second card with the same id; (2) I change its README
  sentence "A click on a partner goes to its card; a card out of the list opens in a new
  tab." and SW6 in the same step; (3) I commit my lines after its plan 62 commit, not in
  it, through a private GIT_INDEX_FILE; every other plan 62 line stays byte-identical.

## drink-atlas-workspace-1c [b72be3]

- Task: (1) run `seed_label_cuts.py` for the 98 full photos with no label cut, then
  build the embeddings; (2) each runtime path that adds a full photo also makes its
  label cut: alternative uploads, manual wines, and the website import.
- Source: owner message of about 2026-09-27T20:35:00+0300 ("Implement"), answers of
  2026-09-27T21:26:58+0300 ("Every path").
- Files: `docs/owner-messages.md` (append), `data/lab.sqlite3` (label cuts through
  `seed_label_cuts.py`), `data/images/cropped/` (new cut files), `pipeline/alternatives.py`,
  `pipeline/manual_wines.py`, `pipeline/import_website.py`, `tests/test_alternatives.py`,
  `tests/test_manual_wines.py`, `tests/test_import_website.py`, `docs/plans/22_label-cut.md`
  (a note), and my own hunks in `ChangeLog.md`, `SMOKE_TESTS.md`, `README.md`,
  `ResearchLog.md`. A restart
  of 8168 for the three server modules.
- State: done, not committed. Waiting: the owner decides the commit. Seeds 1 and 2
  made 124 cuts; Build All of `/embedding` left 3 failed items for each entry (the 3
  photos with no label). 8168 restarted by 1c at 22:05:59 (pid 45770).
- Updated: 2026-09-27T22:45:55+0300
- Agreements: the owner allowed at 21:26:58 changes of `pipeline/alternatives.py` and
  `tests/test_alternatives.py`, which the stale sections codex-side-sam3-fix, 4f
  [0fa826], 96 [6338a8], and 86 [92610a] list (their work is in `c863231`).
- Task 2: plan 65, the button `Build all clusters` of `/clusters`: a server queue, as
  `Build All` of `/embedding` (plan 60).
- Source 2: owner message of 2026-09-27T21:44:04+0300 ("add \"Build all clusters\""),
  answers of 2026-09-27T22:05:44+0300 ("Server queue"; "Yes, separate hunks").
- Files 2: `docs/plans/65_build-all-clusters.md` (new), `pipeline/cluster_routes.py`,
  `tests/test_cluster_routes.py`; separate new hunks in `pipeline/pages/clusters.html`
  (one button and one status span after `#build`, one line in `loadList`, new functions
  and one click listener after the `#build` listener); my own hunks in `docs/API.md`,
  `README.md`, `ChangeLog.md`, `SMOKE_TESTS.md`. A restart of 8168 after the Build All
  queue of `/embedding` ends.
- State 2: done, not committed. Waiting: the owner decides the commit. 8168
  restarted by 1c at 22:39:33 (pid 53022). Full suite 1,262 OK (5 skipped); browser
  check 56 of 56.
- Agreements 2: the owner allowed separate hunks in `clusters.html`, which the stale
  sections d1 [0feb34] and 41 [501d23] list (22:05:44), and 4e [ff960b], stale with
  uncommitted hunks (22:39:01). 2f [0e9cfe] answered "ok" with no condition: its
  lines are the comment line and `.badge.manual`.

## drink-atlas-workspace-e3 [c13919]

- Task: rerun `barcode-rerank-siglip2-512-crop` on `my-1` after all embeddings of
  `gx10-siglip2-so400m-patch16-512` are built, with an empty barcode scan cache.
- Source: owner message of 2026-09-27T22:06:44+0300; answer "Clear barcode cache".
- Files: `docs/owner-messages.md` (append), `data/cache/barcode/` (backup to
  `work/barcode-cache.before-e3-2026-09-27/`, then delete), one new run in `runs/`, and
  my own hunk in `ChangeLog.md`. No code change. No 8168 restart.
- State: done, not committed; waiting: the owner decides the commit. Run
  `2026-09-27T191826Z-lab-barcode-rerank-siglip2-512-crop-my-1` done, 0 errors.
- Updated: 2026-09-27T23:23:41+0300
- Task 2: rename the visible text "Similar wines" of plan 62 to "Hard cases": wines that
  are hard to distinguish. Identifiers stay (`wine_similar`, `/api/dataset-similar`,
  `_similar`, CSS classes). No restart, no schema file, no cluster rebuild.
- Source 2: owner message of 2026-09-27T23:11:41+0300; answers of 23:15:34 ("Visible text
  only", "Hard cases").
- Files 2: `docs/owner-messages.md` (append); separate hunks in 2f's plan 62 lines:
  `pipeline/pages/dataset.html` (9 text lines of `similarEditor`, `saveSimilar`,
  `removeSimilar`), `README.md` (the plan 62 paragraph, not the line of 06),
  `SMOKE_TESTS.md` (the heading, SW2, SW5), `docs/API.md` (the plan 62 heading and first
  sentence), `docs/plans/62_similar-wines.md` (a note at the end); my own hunk in
  `ChangeLog.md`.
- State 2: done, not committed; waiting: the plan 62 commit of 2f, then the owner decides
  the commit. Hunks in by `patch -p1 -F0` at 23:18. node --check OK; test_lab_server.py 69
  and test_similar_wines.py 5 OK; browser check on 8168, writes blocked: 48 of 48.
- Agreements 2: 2f [0e9cfe] "ok" at about 23:17, with conditions: text only (each code
  token, identifier, class, data attribute, and server text byte-identical, and the 06
  lines too); `node --check` of the page script and `test_lab_server.py`,
  `test_similar_wines.py` pass; my commit comes after the plan 62 commit, through a
  private GIT_INDEX_FILE. 2f sends one line when plan 62 is in HEAD.


## drink-atlas-workspace-a4 [34c1c5]

- Task: plan 66, the tags of a test image (by `sha256`) on `/testset`.
- Source: owner message of 2026-09-27T23:50:37+0300, answers of 23:53:00 and 23:59:59. Plan
  `docs/plans/66_testset-image-tags.md`.
- Files: `docs/owner-messages.md` (append), `docs/plans/66_testset-image-tags.md` (new).
  `pipeline/schema/NNN_image_tag.sql` (new),
  `pipeline/image_tags.py` (new), `tests/test_image_tags.py` (new), `pipeline/testsets.py`,
  `pipeline/testset_routes.py`, `pipeline/pages/testset.html`, `pipeline/export_testset.py`,
  `pipeline/import_testset.py`, `tests/test_testsets.py`, `tests/test_testset_routes.py`,
  `tests/test_export_testset.py`, `tests/test_import_testset.py`, `tests/test_labdb.py`
  (VERSION, one table name), and my own hunks in `docs/API.md`, `README.md`,
  `ChangeLog.md`, `SMOKE_TESTS.md`. A migration of `data/lab.sqlite3` and a restart of 8168.
- State: active. The owner approved plan 66 at 23:59:59.
- Updated: 2026-09-28T00:01:00+0300
- Agreements: the owner allowed at 23:59:59 the testset files that the stale sections
  ab [539687], 96 [6338a8], 41 [501d23], b4 [aee81a], and 9e [4644ab] list.
  1e [7df1e0] "ok with conditions" at about 00:00: in `tests/test_labdb.py` I MAY change
  `VERSION, 29` to 30; the closing line `"wine_similar", "wine_tag"])` stays
  byte-identical. 1e has no pending schema file. Commit chain: plan 62 (028) -> plan 63
  (029) -> plan 66 (030), never alone. The import of `wine_tags.normal` and
  `wine_tags.TagError` is fine; plan 66 states that the image tags follow those rules.

## drink-atlas-workspace-31 [e1f2c7]

- Task: plan 68, the re-rank reads the clusters and rules of the pipeline embedding; the
  key `rerank.rules` goes. Build the clusters and rules of
  `gx10-siglip2-so400m-patch16-512`; runs A and B of `barcode-rerank-siglip2-512-crop` on `my`.
- Source: owner message of 2026-09-28T00:04:51+0300, answers of 00:06:31. Plan
  `docs/plans/68_rerank-own-embedding.md`.
- Files: `docs/owner-messages.md` (append), `docs/plans/68_rerank-own-embedding.md` (new),
  `data/embeddings/gx10-siglip2-so400m-patch16-512/` (`clusters.json`, `cluster-rules.json`,
  maybe `cluster-notes.json`), `tests/test_cluster_rerank.py`. After the owner answer (stale
  sections list them), separate hunks: `pipeline/cluster_rerank.py` (`OPTION_KEYS`,
  `check_options`, `ClusterRerank.__init__`, the module docstring),
  `pipeline/embedding_run.py` (`build_pipeline_backend`), `pipeline/pipelines.py` (the
  `rerank.rules` check), `config.yaml` (`&rerank-options` and its comment),
  `docs/plans/48_cluster-rerank.md` (a note at the end). Owner answer of 00:13:52: one line each in
  `tests/test_barcode_shared.py` (`check_options`, `ClusterRerank`) and
  `tests/test_pipeline_workers.py` (the `rerank` config). My own hunks in `README.md`,
  `ChangeLog.md`, `SMOKE_TESTS.md`, `ResearchLog.md`. A restart of 8168.
- State: active. Owner answers of 00:10:21: copy the note; separate hunks allowed in the files
  of the stale sections; a restart of 8168 allowed. Run A started 00:09 (pid 31115).
- Updated: 2026-09-28T00:13:52+0300

## drink-atlas-workspace-49 [549156]

- Task: plan 67, the self-test of one embedding: each dataset image (main, main_patched,
  additional images) is a query in the `full` space; the output is a run on `/runs` with
  the set `dataset`; no barcode step. A button `Selftest` on `/embedding` and a script.
- Source: owner messages of 2026-09-27T23:58:00+0300 and 2026-09-28T00:00:00+0300,
  answers of 00:04:00. Plan `docs/plans/67_embedding-selftest.md`.
- Files: `docs/owner-messages.md` (append), `docs/plans/67_embedding-selftest.md` (new),
  `pipeline/selftest.py` (new), `tests/test_selftest.py` (new). After the owner answer
  (stale sections list them): `pipeline/benchmark.py` (`run_benchmark`: the keyword
  `queries`), `pipeline/run_job.py` (`--selftest`), `pipeline/run_jobs.py` (the body key
  `selftest`), `pipeline/pages/embedding.html` (the button and its job line),
  `tests/test_run_jobs.py`, separate hunks. My own hunks in `docs/API.md`, `README.md`,
  `ChangeLog.md`, `SMOKE_TESTS.md`, `COMMANDS.md`. A restart of 8168 for `run_jobs.py`.
- State: active. The owner allowed at 00:07:00 separate hunks in the files of the stale
  sections (f4, b4, ab, c7, codex-profile-latency, 41, 64) and a restart of 8168.
- Updated: 2026-09-28T00:07:15+0300
