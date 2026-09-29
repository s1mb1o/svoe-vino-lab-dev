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

- Task 6: run `barcode-rerank-siglip2-p512-crop` and
  `barcode-rerank-siglip2-p1024-crop` on every test set through the lab server.
- Source: owner messages of 2026-09-28T01:22:28+0300 and 01:29:05+0300.
- Files for task 6: `docs/owner-messages.md` (append), separate new pipeline entries in
  `config.yaml`, the plan 68 dependency hunks in `pipeline/cluster_rerank.py`,
  `pipeline/embedding_run.py`, `pipeline/pipelines.py`, `tests/test_cluster_rerank.py`,
  `tests/test_barcode_shared.py`, and `tests/test_pipeline_workers.py`,
  `data/embeddings/gx10-siglip2-so400m-patch16-naflex-p512/`
  (`clusters.json`, `cluster-rules.json`) and the corresponding p1024 directory, new run
  directories under `runs/` and the configured test-set run directories,
  `work/run_barcode_rerank_siglip2_all.py`, its log and result ledger, the compatibility
  removal of `rerank.rules` from `work/full-matrix-20260928-0135/config.yaml`, and this
  section of `ACTIVE_WORK.md`.
- State for task 6: active. The owner approved the QwenCloud transmission at 01:34:46.
  The p512 and p1024 cluster builds completed at 01:29 (208 and 229 combined clusters).
  The rule builds completed with 0 description errors and 0 rule errors. The p512
  rulebook has 166 sheet rules and 42 verdict rules. The p1024 rulebook has 184 sheet
  rules and 45 verdict rules. The plan 68 dependency code and the two pipeline entries
  are in the tree. The 46 focused tests pass. Port 8168 restarted with PID 2838, and
  `/api/dataset` answers HTTP 200. The live run API reports both new pipelines as
  runnable. The other task `Прогнать pipelines на датасетах` owns a 270-run serial
  matrix that can take 6 to 12 hours. The resumable serial orchestrator in exec session
  35635 waits for that matrix, then starts the ten requested runs. It writes
  `work/run_barcode_rerank_siglip2_all.log` and records each completed pair in
  `work/run_barcode_rerank_siglip2_all-results.jsonl`.
- Updated for task 6: 2026-09-28T02:33:30+0300.

- Task 7: use GX10 SAM3 to detect barcodes and QR codes in every unique image that a
  test set references. Add the image tags `barcode` and `qr_code` without removing an
  existing tag.
- Source: owner messages received before 2026-09-28T01:42:50+0300 and the scheduled
  continuation at 2026-09-28T06:43:16+0300.
- Files for task 7: `docs/owner-messages.md` (append), `data/lab.sqlite3` (new
  `image_tag` rows), one backup in `data/backups/`,
  `data/cache/sam3/` (the combined-prompt answers), `work/tag_testset_images_sam3.py`,
  `work/tag-testset-images-sam3.jsonl`, my own small hunk in `ChangeLog.md`, and this
  section of `ACTIVE_WORK.md`.
- State for task 7: done, not committed. The run used the canonical `SAM3_ENDPOINT`.
  It sent one serial request per unique image with the nouns `barcode, QR code`.
  It processed 3,474 images in 1,739.5 s with zero request failures. The final rows are
  513 `barcode` tags and 248 `qr_code` tags on 548 images. There are 213 images with
  both tags. The ledger has 3,474 unique successful checkpoints and no errors. Its tag
  pairs exactly equal the database tag pairs. Database integrity, foreign-key, image
  coverage, and tag-scope checks pass. A no-op rerun attempted zero images.
- Updated for task 7: 2026-09-28T07:18:41+0300.

- Task 8: determine whether `scripts/01_search.py` through `scripts/09_apply_moves.py`
  are used. Keep the scripts and product code read-only.
- Source: owner message of 2026-09-28T07:28:16+0300.
- Files for task 8: `docs/owner-messages.md` (append), a new findings section in
  `ResearchLog.md`, and this section of `ACTIVE_WORK.md`.
- State for task 8: done, not committed. The nine scripts are legacy test-set builder
  and review-tool commands. The lab server calls none of them. Current references remain
  in wrappers, documentation, smoke tests, and stage-04 import users. Product code and
  the scripts stayed unchanged.
- Updated for task 8: 2026-09-28T07:34:55+0300.

- Task 9: refactor `svoe-vino-lab` to remove `scripts/01_search.py` through
  `scripts/09_apply_moves.py`.
- Source: owner message of 2026-09-28T07:36:44+0300.
- Files for task 9: `docs/owner-messages.md` (append),
  `docs/plans/70_remove-legacy-testset-stages.md` (new), deletion of
  `scripts/01_search.py` through `scripts/09_apply_moves.py`, deletion of
  `scripts/run_pipeline.py` and `scripts/finalize.sh`, new
  `pipeline/wine_identity_vlm.py`, `scripts/bench_vlm_models.py`,
  `scripts/common.py`, `scripts/review_server.py`, `pipeline/export_testset.py`,
  `tests/test_model_cache.py`, `tests/test_vlm_config.py`, `config.yaml`,
  `config.old.yaml`, `docs/plans/25_model-call-cache.md`, and my own hunks in
  `README.md`, `SMOKE_TESTS.md`, `ResearchLog.md`, and `ChangeLog.md`. This section of
  `ACTIVE_WORK.md` also changes.
- State for task 9: done, not committed. The owner selected focused removal. The eleven
  legacy files are deleted. The reusable VLM logic has a current module. The 69 focused
  tests pass. The complete suite ran 1,298 tests: 1,292 passed, 5 skipped, and one
  unrelated test rejected the shell's port-18082 `SAM3_ENDPOINT`; its nine-test module
  passes with the required port 18081. No schema changed. Port 8168 did not restart.
- Updated for task 9: 2026-09-28T07:53:30+0300.

- Task 10: review only the files and documentation in `matcher/` for hackathon
  submission quality. Ignore that the implementation is a mock. Keep `matcher/`
  read-only.
- Source: owner message of 2026-09-28T08:38:54+0300.
- Files for task 10: `docs/owner-messages.md` (append) and this section of
  `ACTIVE_WORK.md`. The review output stays in the conversation.
- State for task 10: done, not committed. The review found one submission blocker,
  two important reproducibility issues, and several smaller quality gaps. All four
  matcher tests pass. The `matcher/` files stayed read-only.
- Updated for task 10: 2026-09-28T08:41:43+0300.

- Task 11: assess whether a `matcher/Dockerfile` would improve the hackathon
  submission. Do not change `matcher/`.
- Source: owner message of 2026-09-28T09:10:28+0300.
- Files for task 11: `docs/owner-messages.md` (append) and this section of
  `ACTIVE_WORK.md`. The answer stays in the conversation.
- State for task 11: done, not committed. A reproducible one-command container would
  materially improve evaluator usability. The `matcher/` files stayed read-only.
- Updated for task 11: 2026-09-28T09:10:28+0300.

- Task 12: study the current project evidence, README files, presentation audit, and
  benchmark tools. Prepare an evidence-first list of checks and benchmarks for the
  night of 2026-09-28. Do not run the benchmark jobs and do not edit the presentation.
- Source: owner message recorded at 2026-09-28T17:33:00+0300. The owner selected the
  evidence-first approach.
- Files for task 12: `docs/owner-messages.md` (append),
  `docs/reports/2026-09-28_overnight-research-benchmark-plan.md` (new), my own hunk in
  `ChangeLog.md`, and this section of `ACTIVE_WORK.md`.
- State for task 12: done, not committed. The report gives start gates, six prioritized
  benchmarks, acceptance conditions, estimated times, morning outputs, and work that
  should not run. The presentation, product code, data, and run artifacts stayed
  read-only. No model request or benchmark job started. Plan 75 still moves `data/`, and
  port 8168 is down, so the report blocks benchmark starts until that move completes.
- Updated for task 12: 2026-09-28T17:44:32+0300.

- Task 13: scan each uploaded additional wine image with the existing QR/barcode
  service. Store detected GTINs and QR URLs in the wine code fields.
- Source: owner messages of 2026-09-28T18:25:00+0300 and
  2026-09-28T18:33:00+0300.
- Files for task 13: `docs/owner-messages.md` (append),
  `docs/plans/76_scan-additional-image-codes.md` (new),
  `pipeline/qr_barcode.py` (new), separate hunks in `pipeline/lab_server.py`,
  `tests/test_qr_barcode.py` (new), `tests/test_alternative_codes.py` (new), and my own
  hunks in `docs/API.md`, `README.md`, `SMOKE_TESTS.md`, and `ChangeLog.md`. This section
  of `ACTIVE_WORK.md` also changes. A restart of port 8168 follows the tests.
- State for task 13: done, not committed. The upload path scans every valid additional
  image with `POST /scan` and `engine=auto`. It stores new normalized GTINs and QR URLs
  before it builds the response record. A scanner failure keeps the image and returns a
  warning. The 8 new focused tests, 17 code and cache tests, 59 alternative-image tests,
  and 69 lab-server tests pass. A live synthetic EAN-13 probe found and normalized the
  expected code. Port 8168 runs the new code in managed session 33711 (pid 9551) and
  returns HTTP 200.
- Updated for task 13: 2026-09-28T19:01:00+0300.

- Task 14: extend the advanced tag filter of `/testset` with `All`, `No tag`, and the
  tags that exist in the selected test set. The filter applies to wine rows. A wine
  matches `No tag` when at least one of its test photos has no tag.
- Source: owner message and selected option 1 recorded at
  2026-09-28T23:11:34+0300.
- Files for task 14: `docs/owner-messages.md` (append), separate hunks in
  `pipeline/pages/testset.html`, and my own hunks in `SMOKE_TESTS.md`, `ChangeLog.md`,
  and this section of `ACTIVE_WORK.md`.
- State for task 14: done, not committed. `Tag` now lists `All`, `No tag`, and only the
  tags in the selected set. `No tag` keeps a wine row when one or more of its photos is
  untagged. A specific tag keeps a wine row when one or more photos has that tag. The
  live clustered `my` view showed 422 wines for `All`, 321 for `No tag`, and 106 for
  `barcode`. A direct `No tag` address restored the selection and the count. The inline
  script syntax check, 4 page tests, and 52 test-set tests pass. No data changed. Port
  8168 used its existing process and did not restart.
- Updated for task 14: 2026-09-28T23:18:23+0300.

- Task 15: implement incremental end-to-end manual wine creation and embedding-index
  activation. Add one operator CLI and connect the `lab_server.py` Add wine form to the
  same workflow. Test both paths. Then create one wine through each interface.
- Source: owner messages recorded at 2026-09-29T01:06:34+0300. The owner selected the
  operator CLI workflow.
- Files for task 15: `docs/owner-messages.md` (append), this section of
  `ACTIVE_WORK.md`, new `docs/plans/78_incremental-new-wine-index.md`, new
  `pipeline/new_wine_workflow.py`, new `scripts/add_wine.py`, separate hunks in
  `pipeline/lab_server.py` and `pipeline/pages/dataset.html`, new
  `tests/test_new_wine_workflow.py`, focused hunks in `tests/test_manual_wines.py`, and
  my own hunks in `COMMANDS.md`, `README.md`, `SMOKE_TESTS.md`, and `ChangeLog.md`.
  The live trial changes `data/catalog/catalog.sqlite3`, image files, and one selected
  embedding directory. A restart of port 8168 follows the tests.
- State for task 15: done, not committed. The CLI and web route use one workflow. The
  focused suites pass 152 tests. The CLI trial created
  `__cli-index-smoke-20260929`. The browser trial created
  `__web-index-smoke-20260929`. Each trial activated two current index items. Both
  records are now `Disabled`, and the cleanup build pruned their four items. The active
  index has 4,641 items in `vectors-02636f81.npy`. Port 8168 restarted with SIGTERM and
  runs the new code on PID 80244 in managed session 79039.
- Updated for task 15: 2026-09-29T01:23:07+0300.

- Task 16: implement OpenAPI documentation for the lab server on port 8168.
- Source: owner message recorded at 2026-09-29T02:02:20+0300.
- Files for task 16: `docs/owner-messages.md` (append), this section of
  `ACTIVE_WORK.md`, new `docs/plans/80_lab-server-openapi.md`, new
  `docs/lab-openapi.yaml`, new `pipeline/lab_openapi.py`, focused hunks in
  `pipeline/lab_server.py`, new `tests/test_lab_openapi.py`, and my own hunks in
  `COMMANDS.md`, `README.md`, `SMOKE_TESTS.md`, and `ChangeLog.md`. A restart of port
  8168 follows the tests.
- State for task 16: done, not committed. The checked-in OpenAPI 3.1 document covers
  98 operations in 85 paths. The YAML and JSON endpoints return equal documents.
  Swagger UI 5.33.0 loads the document and executed `GET /api/health` with HTTP 200.
  The 11 focused tests and all 225 affected route tests pass. Port 8168 runs the
  verified code on PID 26110 in managed session 81843.
- Updated for task 16: 2026-09-29T07:26:00+0300.

- Task 17: correct the Add wine form so category and color are separate concepts, and
  explain which required fields are missing while Save is disabled.
- Source: owner message of 2026-09-29T12:24:33+0300.
- Files for task 17: `docs/owner-messages.md` (append), this section of
  `ACTIVE_WORK.md`, separate hunks in `pipeline/pages/dataset.html` and
  `pipeline/manual_wines.py`, `scripts/add_wine.py`, focused tests in
  `tests/test_manual_wines.py` and `tests/test_new_wine_workflow.py`, and my own hunks
  in `docs/lab-openapi.yaml`, `docs/plans/20_add-wine.md`,
  `docs/plans/78_incremental-new-wine-index.md`, `COMMANDS.md`, `README.md`,
  `SMOKE_TESTS.md`, and `ChangeLog.md`.
- State for task 17: done, not committed. Category stores `Wine` (`4`) or `Sparkling
  wine` (`44`) in `wine_beverage_type`; Color stores the broad catalogue color; Shade
  is optional. The disabled Save status names and updates all missing requirements.
  Tests: 17 manual-wine, 7 incremental-workflow, 22 import, and 11 OpenAPI tests OK;
  inline JavaScript syntax OK. Live Chromium verified the choices and shrinking status
  with no page error. Port 8168 restarted at 12:38 on PID 75301 and answers HTTP 200.
- Updated for task 17: 2026-09-29T12:40:13+0300.

- Task 18: check five photographed bottles against the dataset. Find a front bottle
  image for each missing wine, and create its card through the lab server.
- Source: owner message of 2026-09-29T13:02:10+0300.
- Files for task 18: `docs/owner-messages.md` (append), this section of
  `ACTIVE_WORK.md`, `data/catalog/catalog.sqlite3`, new files under
  `data/catalog/images/main/`, and the embedding artifacts that the Add wine workflow
  updates. Temporary research images stay outside the repository.
- State for task 18: done, not committed. Exact-product checks found none of the five
  photographed wines in the catalogue. The web form created five active cards with
  front product images: `__rkatsiteli-muskat-oranzh-2025`, `__rozovoe-suhoe-2025`,
  `__kaberne-sovinon-rezerv-2024`, `__massandra-suhoe-krasnoe-2025`, and
  `__green-cape-blaufrankish-malolektik-2024`. The dataset now has 2,113 records
  (2,108 shown with Removed excluded). Each card is visible as `indexed`; their five
  full and five label derivatives occupy rows 4,643 through 4,652 of the active
  4,653-item index. The five source screenshots stayed read-only. Port 8168 used its
  existing process and did not restart.
- Updated for task 18: 2026-09-29T13:18:03+0300.

- Task 19: continue task 18 for five more photographed bottles. Check exact products
  against the dataset, find front bottle images for missing wines, and create their
  cards through the lab server.
- Source: owner message of 2026-09-29T13:20:30+0300.
- Files for task 19: `docs/owner-messages.md` (append), this section of
  `ACTIVE_WORK.md`, `data/catalog/catalog.sqlite3`, new files under
  `data/catalog/images/main/`, and the embedding artifacts that the Add wine workflow
  updates. Temporary research images stay outside the repository.
- State for task 19: done, not committed. `balaklava-pino-nuar` already represented
  the photographed Balaklava Pinot Noir Brut and was not duplicated. The web form
  created four active cards with clean front product images:
  `__vysokiy-bereg-kaberne-sovinon-2024`,
  `__fanagoria-avtorskoe-kaberne-saperavi`, `__balaklava-chardonnay-brut`, and
  `__chateau-tamagne-reserve-extra-brut-2023`. The Chardonnay label is a separate
  current product from the existing Reserve-labelled `balaklava-bryut-rezerv` card.
  The dataset now has 2,117 records. All four new cards are visible as `indexed`; their
  four full and four label derivatives occupy rows 4,653 through 4,660 of the active
  4,661-item index. Database `quick_check` is OK. The five source screenshots stayed
  read-only. Port 8168 used its existing process and did not restart.
- Updated for task 19: 2026-09-29T13:28:23+0300.

- Task 20: continue tasks 18 and 19 for two more photographed bottles shown from the
  front and back. Check the exact products against the dataset, find clean front bottle
  images for missing wines, and create their cards through the lab server.
- Source: owner message of 2026-09-29T13:30:01+0300.
- Files for task 20: `docs/owner-messages.md` (append), this section of
  `ACTIVE_WORK.md`, `data/catalog/catalog.sqlite3`, new files under
  `data/catalog/images/main/`, and the embedding artifacts that the Add wine workflow
  updates. Temporary research images stay outside the repository; the four source
  screenshots stay read-only.
- State for task 20: done, not committed. Exact-product checks found neither wine in
  the catalogue; the Mont de Fleur GTIN visible on the rear label also had no match.
  The web form created two active cards with clean front product images:
  `__mont-de-fleur-rose-semi-dry` and `__chateau-pinot-belenkoe-2025`. Both are
  visible as `indexed`. Their full and label derivatives occupy rows 4,661 through
  4,664 of the active 4,665-item index. The dataset now has 2,119 records (2,110
  Active, 4 Disabled, 5 Removed), and database `quick_check` is OK. The four source
  screenshots stayed read-only. Port 8168 was restarted because its former process
  stopped; the current server is PID 28433 and `/api/dataset` answers HTTP 200.
- Updated for task 20: 2026-09-29T13:45:17+0300.

- Task 21: identify whether the photographed Malesan Crémant de Bordeaux Brut Rosé
  is Russian wine. Do not change catalogue data.
- Source: owner message of 2026-09-29T14:12:26+0300.
- Files for task 21: `docs/owner-messages.md` (append) and this section of
  `ACTIVE_WORK.md`. The source screenshot stays read-only.
- State for task 21: done, not committed. The front label identifies a French Crémant
  de Bordeaux and says `Produit de France`; it is not Russian wine.
- Updated for task 21: 2026-09-29T14:12:26+0300.

- Task 22: check whether the two photographed Мысхако Игристое 2025 wines (white
  brut and white semi-sweet) already exist in the dataset. Do not change catalogue
  data.
- Source: owner message of 2026-09-29T14:15:50+0300.
- Files for task 22: `docs/owner-messages.md` (append) and this section of
  `ACTIVE_WORK.md`. The source screenshot stays read-only.
- State for task 22: done, not committed. Both exact products already have Active
  cards and main catalogue images: `myshako-igristoe-beloe-bryut` and
  `myshako-igristoe-beloe-polusladkoe`. No catalogue data changed.
- Updated for task 22: 2026-09-29T14:16:41+0300.

- Task 23: check whether the photographed Усадьба Александровская Cabernet
  Sauvignon / Merlot / Cabernet Franc wine already exists in the dataset. Do not
  change catalogue data.
- Source: owner message of 2026-09-29T14:33:59+0300.
- Files for task 23: `docs/owner-messages.md` (append) and this section of
  `ACTIVE_WORK.md`. The source screenshot stays read-only.
- State for task 23: done, not committed. The exact photographed blend is absent.
  The only Active card by the same producer is the different wine `Бубновый Валет`
  (`usadba-aleksandrovskaya-bubnovyy-valet-kaberne-sovinon-krasnoe-polusladkoe-13`).
  No catalogue data changed.
- Updated for task 23: 2026-09-29T14:34:50+0300.

- Task 24: add the absent photographed Усадьба Александровская Cabernet Sauvignon /
  Merlot / Cabernet Franc wine. Find a clean front bottle image and create its card
  through the lab server.
- Source: owner message of 2026-09-29T14:35:35+0300, interpreted as resuming the
  original add-if-missing workflow after task 23 confirmed the exact wine is absent.
- Files for task 24: `docs/owner-messages.md` (append), this section of
  `ACTIVE_WORK.md`, `data/catalog/catalog.sqlite3`, a new file under
  `data/catalog/images/main/`, and the embedding artifacts updated by Add wine.
  Temporary research images stay outside the repository; the source screenshot stays
  read-only.
- State for task 24: done, not committed. The web form created the Active card
  `__usadba-aleksandrovskaya-kaberne-sovinon-merlo-kaberne-fran` with a clean front
  product image. It is visible as `indexed`; its full and label derivatives occupy
  rows 4,665 and 4,666 of the active 4,667-item index. The dataset now has 2,120
  records (2,111 Active), and database `quick_check` is OK. The source screenshot
  stayed read-only. Port 8168 used its existing process and did not restart.
- Updated for task 24: 2026-09-29T14:38:51+0300.

- Task 25: identify the photographed wine and check whether the exact product already
  exists in the dataset. Do not change catalogue data.
- Source: owner message of 2026-09-29T15:14:49+0300.
- Files for task 25: `docs/owner-messages.md` (append) and this section of
  `ACTIVE_WORK.md`. The source screenshot stays read-only.
- State for task 25: done, not committed. The bottle is Inkerman Classic Collection
  `Древний Город`, a Crimean red semi-sweet blend of Saperavi, Cabernet Sauvignon,
  and Merlot. Exact name and slug searches found no catalogue card. No catalogue data
  changed.
- Updated for task 25: 2026-09-29T15:16:35+0300.

- Task 26: add the absent Inkerman Classic Collection `Древний Город` red semi-sweet
  wine. Find a clean front bottle image and create its card through the lab server.
- Source: owner message of 2026-09-29T15:24:42+0300.
- Files for task 26: `docs/owner-messages.md` (append), this section of
  `ACTIVE_WORK.md`, `data/catalog/catalog.sqlite3`, a new file under
  `data/catalog/images/main/`, and the embedding artifacts updated by Add wine.
  Temporary research images stay outside the repository; the source screenshot stays
  read-only.
- State for task 26: done, not committed. The web form created the Active card
  `__inkerman-drevniy-gorod` with a clean front product image. It is visible as
  `indexed`; its full and label derivatives occupy rows 4,667 and 4,668 of the active
  4,669-item index. The dataset now has 2,121 records (2,112 Active), and database
  `quick_check` is OK. The source screenshot stayed read-only. Port 8168 used its
  existing process and did not restart.
- Updated for task 26: 2026-09-29T15:31:04+0300.

- Task 27: rename the imported 58-photo test set to `test-1`, and add a safe rename
  action to the `/testset` page.
- Source: owner messages of 2026-09-29T15:33:57+0300, 15:34:11+0300, and
  15:34:20+0300.
- Files for task 27: `docs/owner-messages.md` (append), this section of
  `ACTIVE_WORK.md`, `data/catalog/catalog.sqlite3` (the live rename), separate hunks in
  `pipeline/testsets.py`, `pipeline/testset_routes.py`, and
  `pipeline/pages/testset.html`, focused hunks in `tests/test_testsets.py`,
  `tests/test_testset_routes.py`, and `tests/test_lab_openapi.py`, the new route in
  `docs/lab-openapi.yaml`, and my own small hunks in `README.md`, `SMOKE_TESTS.md`, and
  `ChangeLog.md`. No schema change. A restart of port 8168 follows the tests.
- Agreements for task 27: `drink-atlas-workspace-c1` lists
  `pipeline/pages/testset.html`, but its two tasks are done and the session is absent
  from the current ListAgents answer. The owner directly requested this page feature;
  any edit will use separate hunks and preserve c1's changes byte-for-byte.
- State for task 27: done, not committed. The live set is now `test-1`; it keeps its 58
  photos, 6 variant rows, 2 photo comments, labels, source provenance, and selector
  position. The previous name is absent, `foreign_key_check` has no row, and
  `quick_check` is OK. `/testset` now has `Rename…`; the shared dialog validates format, unchanged
  names, and occupied names, then calls `POST /api/testset-rename`. The page visibly
  selected `test-1` and kept the counts; its conflict check visibly disabled `Rename`
  for `my`. Tests: 57 testset tests and 11 OpenAPI tests OK; the page script parses in
  Node; `git diff --check` passes. Port 8168 restarted with SIGTERM and answers HTTP 200
  on PID 62346.
- Updated for task 27: 2026-09-29T15:48:20+0300.

- Task 28: check the complete `svoe-vino-lab/*` tree for every case-insensitive trace
  of the legacy pre-rename test-set alias, including file names and SQLite values.
  Report only; do not clean or change product data.
- Source: owner message of 2026-09-29T16:01:32+0300.
- Files for task 28: `docs/owner-messages.md` (append) and this section of
  `ACTIVE_WORK.md`. All other project files stay read-only.
- State for task 28: done, not committed. The zero-trace check failed. The live set name
  was already `test-1`, but its `source_dir` still used the legacy dataset directory.
  Ten filesystem paths used the legacy alias: the source dataset directory, report
  directory/file, one backup filename, and six run directories.
  Nine tracked text files contain references; ignored runtime logs, run metadata,
  SAM3 cache records, barcode-report artifacts, and `catalog.sqlite3` contain more.
  `docs/owner-messages.md` is a required historical log and intentionally includes the
  word. No product/data cleanup was performed.
- Updated for task 28: 2026-09-29T16:10:01+0300.

- Task 29: replace every operational use of the legacy test-set alias across
  `svoe-vino-lab` with `test-1`, including paths, metadata, documentation, cache/log
  artifacts, and the live SQLite source directory. Preserve the mandatory verbatim
  owner-message history.
- Source: owner message of 2026-09-29T16:17:46+0300.
- Files for task 29: `docs/owner-messages.md` (append), this section of
  `ACTIVE_WORK.md`, `dataset/*`, `docs/reports/*`, `runs/*`, `work/*`,
  `data/cache/models/sam3/*`, `data/backups/*`, `data/catalog/catalog.sqlite3`, and
  tracked documentation or metadata files containing the old name. File and directory
  paths containing the old name may be renamed. Git history stays unchanged.
- Agreements for task 29: every other section is absent from the current ListAgents
  answer. The owner directly requested this cross-tree rename; edits preserve unrelated
  hunks and the required verbatim history in `docs/owner-messages.md`.
- State for task 29: done, not committed. All operational paths, tracked documentation,
  dataset metadata, six run directories and their metadata, cached SAM3/barcode records,
  logs, the backup filename, and the live database now use `test-1`. The database
  `source_dir` is `dataset/test-1`; it has 58 photos, `quick_check` is OK, and
  `foreign_key_check` is empty. `VACUUM` removed stale values from free SQLite pages.
  A case-insensitive full-tree text search and a path-name search find no legacy alias
  outside the mandatory verbatim owner-message log; `strings` finds none in the live
  database. Dataset and run JSON parse with `jq`; `git diff --check` passes. Port 8168
  restarted on PID 20435; the `test-1` API and `/api/dataset` both answer HTTP 200.
- Updated for task 29: 2026-09-29T16:46:06+0300.

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
- Source: owner message of 2026-09-27T23:50:37+0300, answers of 23:53:00, 23:59:59, and
  00:32:00. Plan
  `docs/plans/66_testset-image-tags.md`.
- Files: `docs/owner-messages.md` (append), `docs/plans/66_testset-image-tags.md` (new).
  `pipeline/schema/030_image_tag.sql` (new; 030 taken at 00:32:20; 1e, 31, and 49 have no schema work),
  `pipeline/image_tags.py` (new), `tests/test_image_tags.py` (new), `pipeline/testsets.py`,
  `pipeline/testset_routes.py`, `pipeline/pages/testset.html`, `pipeline/export_testset.py`,
  `pipeline/import_testset.py`, `tests/test_testsets.py`, `tests/test_testset_routes.py`,
  `tests/test_export_testset.py`, `tests/test_import_testset.py`, `tests/test_labdb.py`
  (VERSION, one table name), and my own hunks in `docs/API.md`, `README.md`,
  `ChangeLog.md`, `SMOKE_TESTS.md`. A migration of `data/lab.sqlite3` and a restart of 8168.
- State: done, not committed. Waiting: the owner decides the commit. The checkpoint
  115f5b0 (of 19) holds plans 62, 63, and 66 as a document; the plan 66 code is not in
  HEAD. Schema 030 is live: backup
  `data/backups/lab-before-030-image-tag-20260927T213243Z.sqlite3`, migration at
  00:32:43, 8168 restarted by a4 at 00:32:47 (PID 4467); `/api/dataset`, `/testset`,
  `/runs`, `/dataset`, `/health` answer 200. Full suite 1,290 OK (5 skipped); browser 60
  of 60 on the scratch server 8175 (stopped) and 12 of 12 read-only on 8168. Docs: plan
  66 Result, README, API.md, SMOKE_TESTS IT1-IT11, ChangeLog; `PORTS_USED.md` (8175).
- Updated: 2026-09-28T00:38:12+0300
- Agreements: the owner allowed at 23:59:59 the testset files that the stale sections
  ab [539687], 96 [6338a8], 41 [501d23], b4 [aee81a], and 9e [4644ab] list.
  1e [7df1e0] "ok with conditions" at about 00:00: in `tests/test_labdb.py` I MAY change
  `VERSION, 29` to 30; the closing line `"wine_similar", "wine_tag"])` stays
  byte-identical. 1e has no pending schema file. Commit chain: plan 62 (028) -> plan 63
  (029) -> plan 66 (030), never alone. The import of `wine_tags.normal` and
  `wine_tags.TagError` is fine; plan 66 states that the image tags follow those rules.
  The owner allowed at 00:32:00 the change of the 6b [e99257] line of `tests/test_labdb.py`
  (the name `image_tag` after `image_label_description_failure`).

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
  of the stale sections; a restart of 8168 allowed. Run A done (00:09-00:16,
  `runs/2026-09-27T210917Z-lab-barcode-rerank-siglip2-512-crop-my-plan68-a`, R@1 85.55 %).
  512 clusters built 00:10:44 (212 combined), note copied. Rule build of the 512 folder
  runs since 00:16 (pid 56717). The code change is ready in the scratchpad copy of this
  session, not in the tree; it lands after the rule build. The checkpoint commit 115f5b0 (session 19, owner
  "commit all") holds the plan 68 draft and my owner-message entries up to 00:13:52; the
  rest goes in a follow-up commit. Stage 1 done at 00:20 (521 cards, 0 errors); stage 2 runs.
- Updated: 2026-09-28T00:20:28+0300

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
  `ChangeLog.md`, `SMOKE_TESTS.md`, `COMMANDS.md`, `ResearchLog.md`. A restart of 8168 for
  `run_jobs.py`.
- State: done; waiting: the owner decides the commit. The code, the tests, and plan 67
  are in the checkpoint 115f5b0 of session 19. Not committed: the `Selftest` button hunk
  of `pipeline/pages/embedding.html`, and my hunks in `README.md`, `COMMANDS.md`,
  `docs/API.md`, `SMOKE_TESTS.md` (SE1 to SE8), `ChangeLog.md` (2026-09-28),
  `ResearchLog.md` (2026-09-28), and the status line of plan 67. 8168 restarted by 49 at
  00:15:47 (PID 52966); a4 restarted it at 00:32:47 (PID 4467, schema 030),
  and the self-test route answers there. Tests: the full suite 1,277 OK (5 skipped); 12 browser checks.
  Full self-test of `gx10-siglip2-so400m-patch16-512`: 2,401 images, recall@1 0.9713.
  The owner allowed at 00:07:00 separate hunks in the files of the stale sections (f4,
  b4, ab, c7, codex-profile-latency, 41, 64) and a restart of 8168.
- Updated: 2026-09-28T00:38:43+0300

## codex-submission-01

- Task: prepare a small root-ready submission package in `_submission/`.
- Source: owner messages of 2026-09-28T00:40:00+0300.
- Files: `docs/owner-messages.md` (append), `_submission/**`, and my section in
  `ACTIVE_WORK.md`.
- State: done, not committed. The package has three files and is 10.7 KB. A restore of
  `db-export/` and the migration from schema 25 to 30 succeeded. The 8 database-export
  tests and 17 schema tests pass. The example configuration opens the schema-30 database.
  All 10 root-relative links resolve. `git diff --check` passes.
- Updated: 2026-09-28T00:46:17+0300
- Task 2: create brief Russian submission documents for the complete repository.
- Source 2: owner message of 2026-09-28T16:08:00+0300.
- Files 2: `docs/owner-messages.md` (append), `../README.md`, `../ARCHITECTURE.md`,
  `../BENCHMARKS.md`, `../SETUP.md`, and my section in `ACTIVE_WORK.md`.
- State 2: done, not committed. Created four brief Russian documents at the repository
  root. All local Markdown links resolve. Matcher passed 60 tests. Web UI passed typecheck,
  103 tests, and its production build.
- Updated 2: 2026-09-28T16:18:00+0300

## codex-main-scene-ranking

- Task: select the main package in recognition photos with an observable hybrid scene
  score. Prefer a package held in a hand. Select the main bottle when many bottles occur.
  Create an A4 decision diagram.
- Source: owner messages recorded at 2026-09-28T01:16:11+0300 through
  2026-09-28T01:16:13+0300. The owner selected approach 1.
- Files: `docs/owner-messages.md` (append), `docs/plans/69_main-scene-ranking.md` (new),
  `pipeline/main_scene.py` (new), separate hunks in `pipeline/embedding_run.py` and
  `pipeline/run_steps.py`, `tests/test_main_scene.py` (new), separate hunks in
  `tests/test_embedding_run.py` and `tests/test_run_steps.py`,
  `output/pdf/main-scene-selection.pdf` (new), `scripts/draw_main_scene_selection.py`
  (new), and my own small hunks in
  `README.md`, `ResearchLog.md`, `SMOKE_TESTS.md`, and `ChangeLog.md`. A restart of port
  8168 is required.
- State: implemented and verified. Both live recognition requests select `can`. The
  package step exposes the complete audit. A browser check opened the result and showed
  the weights, signals, contributions, and ranked candidates. The full suite has 1,298
  passing tests and 5 skipped tests. Port 8168 was restarted at 01:39 (PID 2431), and
  `/api/dataset` returned HTTP 200. Changes are not committed.
- Updated: 2026-09-28T01:39:14+0300

## codex-rerank-diagnosis

- Task: explain why the 2024 candidate for the specified Aratti photo moved from rank 1
  to rank 2 after cluster re-rank.
- Source: owner message recorded at 2026-09-28T01:43:17+0300.
- Files: `docs/owner-messages.md` (append), this section of `ACTIVE_WORK.md`, and a small
  findings entry in `ResearchLog.md` if the diagnosis is material.
- State: diagnosis complete. The base embedding rank was correct. A one-sided verdict
  rule treated absent `ПОЛУСУХОЕ` text as proof of the other card. The test photo is a
  2024 package variant that omits this text. No code changed.
- Updated: 2026-09-28T01:48:00+0300

## codex-rerank-scores

- Task: replace direct VLM re-rank decisions with VLM evidence scores and deterministic
  code decisions.
- Source: owner message recorded at 2026-09-28T01:55:32+0300.
- Files: `docs/owner-messages.md` (append), this section of `ACTIVE_WORK.md`, a new plan,
  `pipeline/cluster_rerank.py`, its focused tests, and the relevant project documents.
- State: waiting for the owner to select the score contract.
- Updated: 2026-09-28T01:55:32+0300

## codex-side-matcher-api

- Task: add a standalone FastAPI matcher subproject with `POST /v1/eval/predict`, an
  explicit pipeline configuration, three mock answers, and the official evaluation
  directory as its test harness.
- Source: owner messages recorded at 2026-09-28T08:07:45+0300 and the selected option 1.
- Files: `docs/owner-messages.md` (append),
  `docs/plans/71_eval-matcher-service.md` (new), `matcher/**` (new), my own small hunks
  in `ChangeLog.md` and `SMOKE_TESTS.md`, and this section of `ACTIVE_WORK.md`.
- State: done, not committed. The FastAPI service, configuration, README, and tests are
  complete. The official participant_test.sh received all three configured slugs. An
  unknown image received an empty slug. All 4 matcher tests pass with ResourceWarning
  treated as an error. No database schema change. No lab-server restart. No fixed port.
- Updated: 2026-09-28T08:15:34+0300
- Task 2: rewrite `matcher/README.md` in Russian for a human reader. Keep technical
  identifiers and commands unchanged.
- Source 2: owner message of 2026-09-28T08:23:11+0300.
- State 2: done, not committed. The complete README is in Russian. Commands, paths,
  configuration keys, environment variables, and API identifiers are unchanged.
- Updated for task 2: 2026-09-28T08:23:11+0300
- Task 3: use `SVOE_VINO_MATCHER_PORT` for the matcher port in the documented start
  command. Keep the host fixed at `127.0.0.1`.
- Source 3: owner message and answer of 2026-09-28T08:27:14+0300.
- State 3: done, not committed. The README uses `SVOE_VINO_MATCHER_PORT` in the start,
  curl, and official-harness commands. The host stays `127.0.0.1`.
- Updated for task 3: 2026-09-28T08:27:14+0300
- Task 4: use the project Python environment `~/.venvs/svoe-vino-lab` in the matcher
  README.
- Source 4: owner message of 2026-09-28T08:28:51+0300.
- State 4: done, not committed. Setup, startup, and test commands use the project
  environment `~/.venvs/svoe-vino-lab`.
- Updated for task 4: 2026-09-28T08:28:51+0300
- Task 5: replace the three-line matcher port prompt with one command that keeps an
  existing `SVOE_VINO_MATCHER_PORT` value and prompts when the value is absent.
- Source 5: owner message of 2026-09-28T08:32:45+0300.
- Files 5: `docs/owner-messages.md` (append), `matcher/README.md`, my own matcher hunk
  in `ChangeLog.md`, and this section of `ACTIVE_WORK.md`.
- State 5: done, not committed. The one-line command preserves a non-empty value,
  prompts for an empty value, and exports the result. Both paths pass a shell check.
- Updated for task 5: 2026-09-28T08:32:45+0300
- Task 6: put the three matcher sample images in `matcher/tests/data` and use those
  local files in the README and tests.
- Source 6: owner message of 2026-09-28T08:34:42+0300.
- Files 6: `docs/owner-messages.md` (append), `matcher/tests/data/*`,
  `matcher/tests/test_service.py`, `matcher/tests/test_official_harness.py`,
  `matcher/README.md`, `docs/plans/71_eval-matcher-service.md`, my own matcher hunk in
  `ChangeLog.md`, and this section of `ACTIVE_WORK.md`.
- State 6: done, not committed. The three local files have the official SHA-256 values.
  The README, unit test, and official-harness test use `matcher/tests/data`. All 4
  matcher tests pass. `git diff --check` passes.
- Updated for task 6: 2026-09-28T08:34:42+0300
- Task 7: put the official `participant_test.sh` in `matcher/tests` and use the local
  script in the README and integration test.
- Source 7: owner message of 2026-09-28T08:39:22+0300.
- Files 7: `docs/owner-messages.md` (append), `matcher/tests/participant_test.sh`,
  `matcher/tests/test_official_harness.py`, `matcher/README.md`,
  `docs/plans/71_eval-matcher-service.md`, my own matcher hunk in `ChangeLog.md`, and
  this section of `ACTIVE_WORK.md`.
- State 7: done, not committed. The local script is executable and has the official
  SHA-256 value. The README and integration test use it. All 4 matcher tests pass.
  `git diff --check` passes.
- Updated for task 7: 2026-09-28T08:39:22+0300
- Task 8: reserve `matcher/config.yaml` for the future real configuration. Move the
  current mock configuration to `matcher/tests/config.yaml` and select it explicitly
  for API tests.
- Source 8: owner message of 2026-09-28T08:41:12+0300.
- Files 8: `docs/owner-messages.md` (append), `matcher/config.yaml` (move),
  `matcher/tests/config.yaml`, `matcher/tests/test_service.py`,
  `matcher/tests/test_official_harness.py`, `matcher/README.md`,
  `docs/plans/71_eval-matcher-service.md`, my own matcher hunks in `ChangeLog.md` and
  `SMOKE_TESTS.md`, and this section of `ACTIVE_WORK.md`.
- State 8: done, not committed. `matcher/config.yaml` is free for the future real
  configuration. The mock is in `matcher/tests/config.yaml`. Unit tests load it by
  path. The API integration test sets `SVOE_VINO_MATCHER_CONFIG` explicitly. All 4
  matcher tests pass. `git diff --check` passes.
- Updated for task 8: 2026-09-28T08:41:12+0300
- Task 9: add OpenAPI documentation for the matcher API.
- Source 9: owner message of 2026-09-28T08:55:30+0300.
- Files 9: `docs/owner-messages.md` (append), `matcher/openapi.yaml`, `matcher/app.py`,
  `matcher/tests/test_service.py`, `matcher/tests/test_official_harness.py`,
  `matcher/README.md`,
  `docs/plans/71_eval-matcher-service.md`, my own matcher hunks in `ChangeLog.md` and
  `SMOKE_TESTS.md`, and this section of `ACTIVE_WORK.md`.
- State 9: done, not committed. `matcher/openapi.yaml` documents the request, success,
  and validation error. FastAPI publishes Swagger UI, ReDoc, and `/openapi.json` with
  the typed `Prediction` response. The static and live core contracts match. All 5
  matcher tests pass. `git diff --check` passes.
- Updated for task 9: 2026-09-28T08:55:30+0300
- Task 10: add an integration test that verifies the JSONL record written by
  `matcher/tests/participant_test.sh` against the documented example.
- Source 10: owner message of 2026-09-28T08:59:53+0300.
- Files 10: `docs/owner-messages.md` (append),
  `matcher/tests/test_official_harness.py`, `matcher/README.md`,
  `docs/plans/71_eval-matcher-service.md`, my own matcher hunks in `ChangeLog.md` and
  `SMOKE_TESTS.md`, and this section of `ACTIVE_WORK.md`.
- State 10: done, not committed. The test runs the local shell client and parses the
  produced file. It checks the exact five-field order, query id, image path, full
  SHA-256, predicted slug, and integer nonnegative latency. All 6 matcher tests pass.
  `git diff --check` passes.
- Updated for task 10: 2026-09-28T08:59:53+0300
- Task 11: log matcher requests and archive every submitted image with request headers,
  client IP, result, and processing duration in a required output directory.
- Source 11: owner message of 2026-09-28T09:07:32+0300.
- Files 11: `docs/owner-messages.md` (append), `matcher/audit.py` (new),
  `matcher/app.py`, `matcher/tests/test_official_harness.py`, `matcher/README.md`,
  `docs/plans/71_eval-matcher-service.md`, my own matcher hunks in `ChangeLog.md` and
  `SMOKE_TESTS.md`, and this section of `ACTIVE_WORK.md`.
- State 11: done, not committed. The required output directory gets one private request
  directory with the exact image and JSON metadata. Metadata holds the direct client
  IP, all header names, redacted secret values, image properties, timestamps, duration,
  status, and result. Uvicorn gets a structured completion or error event. All 7 matcher
  tests pass with ResourceWarning treated as an error. `git diff --check` passes.
- Updated for task 11: 2026-09-28T09:07:32+0300
- Task 12: add `GET /health`, local queries.tsv, pinned direct dependencies, bounded
  non-empty image input, negative tests, and exact static/live OpenAPI verification.
- Source 12: owner message of 2026-09-28T09:16:48+0300.
- Files 12: `docs/owner-messages.md` (append), `matcher/tests/queries.tsv` (new),
  `matcher/requirements.txt`, `matcher/app.py`, `matcher/openapi.yaml`,
  `matcher/tests/test_service.py`, `matcher/tests/test_official_harness.py`,
  `matcher/README.md`, `docs/plans/71_eval-matcher-service.md`, my own matcher hunks in
  `ChangeLog.md` and `SMOKE_TESTS.md`, and this section of `ACTIVE_WORK.md`.
- State 12: done, not committed. GET /health reports readiness and the selected
  pipeline. The service rejects empty and oversized files with HTTP 400 and 413; a
  missing image gets HTTP 422. The official manifest is local and has the source
  SHA-256. Direct dependencies have exact versions and include pydantic. The five
  negative configuration cases pass. The complete parsed static and live OpenAPI
  documents are equal. All 16 matcher tests pass with ResourceWarning treated as an
  error. `pip check` and `git diff --check` pass. No schema change or lab-server
  restart.
- Updated for task 12: 2026-09-28T09:24:26+0300
- Task 13: test the matcher against decompression bombs, oversized and slow uploads,
  and request overload. Add stable countermeasures and a repeatable resilience harness.
- Source 13: owner message of 2026-09-28T09:26:10+0300.
- Files 13: `docs/owner-messages.md` (append), `matcher/protection.py` (new),
  `matcher/app.py`, `matcher/requirements.txt`, `matcher/openapi.yaml`,
  `matcher/tests/test_resilience.py` (new), `matcher/tests/test_official_harness.py`,
  `matcher/README.md`, `docs/plans/71_eval-matcher-service.md`, my own matcher hunks
  in `ChangeLog.md` and `SMOKE_TESTS.md`, and this section of `ACTIVE_WORK.md`.
- State 13: done, not committed. The middleware limits the complete body, image bytes,
  pixels, upload time, active requests, queued requests, and queue time. Pillow verifies
  JPEG, PNG, and WEBP. Seven adversarial tests cover a JPEG dimension bomb, a 1 GiB
  sparse upload, a chunked oversized body, a slow upload, a full queue, a damaged image,
  and an unsupported format. The service stays usable after every test.
- Updated for task 13: 2026-09-28T09:57:38+0300
- Task 14: add optional token authentication to matcher requests. Add positive and
  negative tests for configurations with and without authentication. Document the
  purpose of each test configuration in YAML comments.
- Source 14: owner message of 2026-09-28T09:27:29+0300.
- Files 14: `docs/owner-messages.md` (append), `matcher/service.py`, `matcher/app.py`,
  `matcher/tests/config.yaml`, `matcher/tests/config.token.yaml` (new),
  `matcher/tests/test_service.py`, `matcher/tests/test_auth.py` (new),
  `matcher/openapi.yaml`, `matcher/README.md`, `docs/plans/71_eval-matcher-service.md`,
  my own matcher hunks in `ChangeLog.md` and `SMOKE_TESTS.md`, and this section of
  `ACTIVE_WORK.md`.
- State 14: done, not committed. `Authorization: Bearer <token>` protects predict when
  `matcher.token_env` is configured. YAML stores only the environment-variable name.
  Missing, malformed, and invalid credentials return HTTP 401. `/healthz` and OpenAPI
  stay public. Both test configs explain their purpose in comments.
- Updated for task 14: 2026-09-28T09:57:38+0300
- Task 15: add production-quality Docker support for `matcher/`. Use Python 3.11 slim,
  a non-root user, port 8080, a `.dockerignore`, README commands, and an automated
  build-and-run test with local evaluation data.
- Source 15: owner message of 2026-09-28T09:28:56+0300.
- Files 15 before the container-contract choice: `docs/owner-messages.md` (append) and
  this section of `ACTIVE_WORK.md`. Product files will be listed after the owner selects
  the default container configuration.
- State 15: waiting: the owner selects the container configuration contract.
- Updated for task 15: 2026-09-28T09:28:56+0300
- Task 16: configure the matcher output directory in `config.yaml`. Support the
  existing project notation `{env:NAME}` for `SVOE_VINO_MATCHER_OUTPUT_DIR`.
- Source 16: owner message of 2026-09-28T09:29:46+0300.
- Files 16: `docs/owner-messages.md` (append), `matcher/service.py`, `matcher/app.py`,
  `matcher/tests/config.yaml`, `matcher/tests/test_service.py`, `matcher/README.md`,
  `docs/plans/71_eval-matcher-service.md`, my own matcher hunks in `ChangeLog.md` and
  `SMOKE_TESTS.md`, and this section of `ACTIVE_WORK.md`.
- State 16: done, not committed. `matcher.output_dir` accepts a literal path or an
  exact `"{env:NAME}"` reference. The API test config resolves
  `SVOE_VINO_MATCHER_OUTPUT_DIR` through this field. A config without the field keeps
  the legacy direct environment fallback. Tests cover literal, resolved, absent,
  missing, empty, and malformed values. All 23 matcher tests pass with ResourceWarning
  treated as an error. `pip check` and `git diff --check` pass. No schema change or
  lab-server restart.
- Updated for task 16: 2026-09-28T09:39:35+0300
- Task 17: use the more common infrastructure probe path `/healthz` instead of
  `/health`.
- Source 17: owner message of 2026-09-28T09:40:52+0300.
- Files 17: `docs/owner-messages.md` (append), `matcher/app.py`,
  `matcher/openapi.yaml`, `matcher/tests/test_service.py`,
  `matcher/tests/test_official_harness.py`, `matcher/README.md`,
  `docs/plans/71_eval-matcher-service.md`, my own matcher hunks in `ChangeLog.md` and
  `SMOKE_TESTS.md`, and this section of `ACTIVE_WORK.md`.
- State 17: done, not committed. The app, OpenAPI, tests, README, plan, change log, and
  smoke tests use `/healthz`. The full matcher suite has 37 passing tests.
- Updated for task 17: 2026-09-28T09:57:38+0300
- Task 18: commit the completed matcher implementation without the unrelated work of
  other sessions.
- Source 18: owner message of 2026-09-28T10:03:35+0300.
- Files 18: `docs/owner-messages.md` (append), `matcher/**`,
  `docs/plans/71_eval-matcher-service.md`, my matcher hunks in `ChangeLog.md` and
  `SMOKE_TESTS.md`, and this section of `ACTIVE_WORK.md`.
- State 18: done. Commit `43244f7` contains tasks 1 through 14 and 16 through 18. The
  isolated Git index contained only matcher files and matcher hunks. Task 15 remains
  waiting and is not part of this commit.
- Updated for task 18: 2026-09-28T10:09:19+0300
- Task 19: add a GitLab CI job for the complete matcher test harness, push the matcher
  commits to GitLab, and verify that the remote pipeline passes.
- Source 19: owner message of 2026-09-28T10:09:59+0300.
- Files 19: `docs/owner-messages.md` (append), `.gitlab-ci.yml` (new), my matcher hunks
  in `ChangeLog.md` and `SMOKE_TESTS.md`, and this section of `ACTIVE_WORK.md`.
- State 19: done. Commit `06a947a` adds the `matcher-tests` GitLab CI job. Commits
  `43244f7` and `06a947a` are on `origin/main`. Pipeline `325`, job `1060`, passed on
  the Docker runner with `python:3.11-slim`: `pip check` passed and all 37 matcher tests
  passed with no skips. The local and remote `main` refs are equal. No unrelated hunk
  was staged or committed. Task 15 remains waiting.
- Updated for task 19: 2026-09-28T10:20:57+0300
- Task 20: add `matcher/TESTING.md` and move all code-testing guidance out of
  `matcher/README.md`.
- Source 20: owner message of 2026-09-28T10:21:41+0300.
- Files 20: `docs/owner-messages.md` (append), `matcher/README.md`,
  `matcher/TESTING.md` (new), and this section of `ACTIVE_WORK.md`.
- State 20: done, not committed. `matcher/README.md` now contains only runtime and API
  guidance plus one link to testing. `matcher/TESTING.md` contains the test
  prerequisites, configurations, data, full unittest command, coverage description,
  manual official harness, and GitLab CI contract. All 37 matcher tests pass with no
  skips. No product code changed.
- Updated for task 20: 2026-09-28T10:25:00+0300
- Task 21: require the exact `"{env:NAME}"` notation for `matcher.token_env` instead of
  a bare environment-variable name.
- Source 21: owner message of 2026-09-28T11:10:38+0300.
- Files 21: `docs/owner-messages.md` (append), `matcher/service.py`,
  `matcher/tests/config.token.yaml`, `matcher/tests/test_service.py`,
  `matcher/README.md`, `matcher/TESTING.md`, `docs/plans/71_eval-matcher-service.md`,
  my own matcher hunks in `ChangeLog.md` and `SMOKE_TESTS.md`, and this section of
  `ACTIVE_WORK.md`.
- State 21: done, not committed. `matcher.token_env` accepts only an exact
  `"{env:NAME}"` reference. The loader rejects bare names and malformed references.
  Startup resolves only the referenced variable and rejects a missing or empty value.
  Configs, README, TESTING, plan, change log, and smoke tests use the same notation.
  All 20 config tests and all 37 matcher tests pass with no skips.
- Updated for task 21: 2026-09-28T11:12:36+0300
- Task 22: rename the matcher configuration key `token_env` to `token`.
- Source 22: owner answer `ok, rename` at 2026-09-28T11:19:20+0300 after the question
  `token_env -> token_key ?` and the recommendation to use `token`.
- Files 22: `docs/owner-messages.md` (append), `matcher/service.py`, `matcher/app.py`,
  `matcher/openapi.yaml`, `matcher/tests/config.yaml`,
  `matcher/tests/config.token.yaml`, `matcher/tests/test_service.py`,
  `matcher/README.md`, `matcher/TESTING.md`, `docs/plans/71_eval-matcher-service.md`,
  my own matcher hunks in `ChangeLog.md` and `SMOKE_TESTS.md`, and this section of
  `ACTIVE_WORK.md`.
- State 22: done, not committed. The config, runtime model, OpenAPI, README, TESTING,
  plan, change log, and smoke tests use `matcher.token: "{env:NAME}"`. The loader
  explicitly rejects `matcher.token_env`, bare names, malformed references, and missing
  or empty referenced variables. All 20 config tests and all 37 matcher tests pass with
  no skips. `git diff --check` passes for the changed matcher files.
- Updated for task 22: 2026-09-28T11:21:32+0300
- Task 23: add GitHub Actions testing for all matcher tests, push to the `github` remote,
  and verify the remote run.
- Source 23: owner messages of 2026-09-28T11:49:38+0300 and 11:52:12+0300.
- Files 23: `workbench/docs/owner-messages.md` (append),
  `.github/workflows/matcher-tests.yml` (new), `matcher/tests/run_ci.sh` (new),
  `matcher/TESTING.md`, my own matcher hunk in `workbench/ChangeLog.md`, and this
  section of `workbench/ACTIVE_WORK.md`.
- State 23: done. GitHub reports two online self-hosted runners. The workflow uses
  `ct112-svoe-vino-lab-docker-1`. Commit `191f77b` replaced the false-positive nested
  heredoc with `matcher/tests/run_ci.sh`. Commits `191f77b` and `dcae4e4` are on
  `github/main`. GitHub Actions run `36401705134` passed on the current HEAD:
  `pip check` passed, and all 37 discovered tests ran with zero skips. The ordinary
  runner `ct111-svoe-vino-lab-1` stays available for jobs that do not need Docker. No
  unrelated file was committed.
- Updated for task 23: 2026-09-28T12:10:21+0300

## codex-side-commands-rules

- Task: add the project rules for `COMMANDS.md` and component test commands to
  `AGENTS.md`.
- Source: owner message of 2026-09-28T08:13:27+0300.
- Files: `docs/owner-messages.md` (append), `AGENTS.md`, my own small hunk in
  `ChangeLog.md`, and this section of `ACTIVE_WORK.md`.
- State: done, not committed. Rules 29 to 38 define the use and structure of
  `COMMANDS.md`, detailed testing documents, executable targets, and test scripts.
- Updated: 2026-09-28T08:15:00+0300.

## drink-atlas-workspace-61 [081a48]

- Task: compare the gx10 service `qr-scanner` with the barcode step of the lab, and
  propose an explicit choice of the barcode decoder in the key `barcode` of a pipeline.
- Source: owner messages of 2026-09-28 (about 08:18 and 08:20).
- Files: `docs/owner-messages.md` (append), `ResearchLog.md` (one entry at the top),
  this section.
- State: waiting: the owner selects an approach. No code change.
- Updated: 2026-09-28T08:22:55+0300

## codex-deployment-advice

- Task: configure two restricted reverse-SSH tunnels from gx10 port 28000 to the
  loopback interface of Avalon and Princess. Document the installed configuration.
- Source: owner messages of 2026-09-28T09:56:48+0300 and
  2026-09-28T11:23:21+0300, 2026-09-28T13:17:25+0300, and
  2026-09-28T13:44:29+0300.
- Files: `docs/owner-messages.md` (append),
  `docs/deployment/01_gx10-public-failover-options.md` (new),
  `../deploy/INFRASRUCTURE.md`, `../deploy/gx10/matcher-prod.md`,
  `../deploy/gx10/reverse-ssh.md` (new),
  `/Users/ashmelev/Admin/infra/servers/{avalon,princess}/`,
  `/Users/ashmelev/Admin/infra/servers/{INDEX.md,ChangeLog.md}`, the removal of the
  mistaken local `deploy/gx10/` copies, my own hunk in `ChangeLog.md`, and this section
  of `ACTIVE_WORK.md`. Live files: two keys and two systemd user units on gx10, and the
  `matcher-gx10` account and SSH drop-in on each VDS.
- State: done, not committed. Both units are enabled and active. Both loopback listeners
  return the matcher health response after a control restart. Public port 28000 is not
  reachable on either VDS. The active session 7c lists `../deploy/ChangeLog.md`, so this
  session did not change that file.
- Updated: 2026-09-28T14:02:58+0300
- Task 2: enable HTTPS for `chtozavino.ru` on Princess and publish the matcher through
  the private reverse SSH listener with an edge security policy.
- Source 2: owner message of 2026-09-28T16:05:26+0300.
- Files 2: `docs/owner-messages.md` (append), `../deploy/INFRASRUCTURE.md`,
  `../deploy/princess/matcher-edge.md` (new), `../deploy/gx10/matcher-prod.md`,
  `/Users/ashmelev/Admin/infra/servers/princess/{README.md,access.md,services.md,ChangeLog.md}`,
  `/Users/ashmelev/Admin/infra/servers/ChangeLog.md`, my own hunk in `ChangeLog.md`,
  `/Users/ashmelev/Admin/infra/websites/chtozavino.ru/**`,
  `/Users/ashmelev/Admin/infra/websites/{INDEX.md,ChangeLog.md}`,
  `/Users/ashmelev/Admin/infra/services/svoe-vino-matcher/**`,
  `/Users/ashmelev/Admin/infra/services/{INDEX.md,ChangeLog.md}`, this section, and live
  Princess files `/etc/caddy/{Caddyfile,matcher.env}`,
  `/etc/systemd/system/caddy.service.d/10-matcher-token.conf`, and the Caddy service.
- State 2: done, not committed. Caddy is enabled and active. HTTP redirects to HTTPS.
  Both certificates pass client validation. The health route is public. Both POST routes
  require the Bearer token from Keychain. A request without the token returns HTTP 401.
  An authorized request without an image reaches the matcher and returns HTTP 422.
  Unlisted paths return HTTP 404. Public port 28000 stays closed. The first token was
  rotated. The current token is absent from the Caddy journal. The public health route
  still reports `official-eval-mock`. Session e9 owns the pending matcher pipeline switch.
  No full image prediction was sent through the public domain because that data transfer
  was not authorized.
- Updated for task 2: 2026-09-28T16:21:39+0300

## codex-side-matcher-bundle

- Task: export a standalone matcher bundle with optional prepared images. Add a
  separate bundle validator and automated tests.
- Source: owner message of 2026-09-28T10:01:26+0300. The owner selected the flat bundle
  approach in the preceding side conversation.
- Files: `docs/owner-messages.md` (append), `docs/plans/72_matcher-bundle.md` (new),
  `pipeline/matcher_bundle.py` (new), `scripts/build_matcher_bundle.py` (new),
  `scripts/validate_matcher_bundle.py` (new), `tests/test_matcher_bundle.py` (new),
  `docs/testing/matcher-bundle.md` (new), my own hunks in `COMMANDS.md`,
  `ChangeLog.md`, and `SMOKE_TESTS.md`, and this section of `ACTIVE_WORK.md`.
- State: done, not committed. Waiting: the owner decides the next integration step.
  Nine bundle tests, 17 embedding-build tests, and 38 embedding-run tests pass. Real
  bundles with zero and 4,642 copied images pass standalone validation. Both contain
  4,642 items, 4,674 candidate relations, 2,094 wines, 3 omissions, and vectors of
  dimension 768. No database schema change. No lab-server restart.
- Updated: 2026-09-28T10:14:00+0300

## drink-atlas-workspace-66 [64fd47]

- Task: plan 75, stage 2a: the matcher reads a copy of `data/catalog/` (fixed SQL views,
  `index.json`, the vector file); `scripts/copy_catalog.py` replaces the bundle build.
  Stage 1 is committed: `86face6`.
- Source: owner messages of 2026-09-28T16:21:20+0300 and 18:57:07+0300 (`do 1 and 3`).
- Files: `docs/owner-messages.md` (append), `docs/plans/75_data-layout.md`,
  `pipeline/schema/031_matcher_views.sql` (new, schema 031 taken at 19:14:08),
  `tests/test_labdb.py` (VERSION 31), `tests/test_matcher_views.py` (new),
  `pipeline/catalog_copy.py` (new), `scripts/copy_catalog.py` (new),
  `tests/test_catalog_copy.py` (new), `../matcher/catalog.py` (new),
  `../matcher/service.py`, `../matcher/app.py` (two 503 messages),
  `../matcher/tests/test_catalog.py` (new), `../matcher/README.md`, `../matcher/TESTING.md`,
  `COMMANDS.md`, and my own hunks in `README.md` (one line), `SMOKE_TESTS.md` (section CC),
  and `ChangeLog.md`.
- State: stage 2a done, not committed. `data/catalog/catalog.sqlite3` is at schema 31 since
  19:14; 8168 runs since 19:14 (pid 10583, started by 66). Waiting: the owner decides the
  commit of 2a, the prod switch (2b), and the removal of the bundle code (2c).
- Updated: 2026-09-28T19:23:26+0300

## codex-android-embeddings

- Task: add and build two Android-compatible SigLIP2 Base 224 embeddings. One entry
  uses DIS. One entry uses the present SAM3 package derivative.
- Source: owner messages of 2026-09-28T21:41:25+0300,
  2026-09-28T21:46:16+0300, and 2026-09-28T23:10:10+0300. The owner selected
  approaches 1 and 2, and asked for a separate Android verification-results document
  after the builds complete.
- Files: `docs/owner-messages.md` (append), `docs/plans/77_android-embeddings.md`
  (new), `config.yaml` (two separate embedding entries), `pipeline/embeddings.py`,
  `pipeline/build_embeddings.py`, a new DIS helper under `pipeline/`, focused tests,
  `requirements-local.txt`, and my own hunks in `COMMANDS.md`, `README.md`,
  `ResearchLog.md`, `SMOKE_TESTS.md`, and `ChangeLog.md`. Runtime output goes to
  `data/catalog/embeddings/android-*`. The task also adds one active row to
  `/Users/ashmelev/Admin/GPU_TASKS.md` before a GPU build. The build uses the isolated
  GX10 endpoint on port 5997. It does not reload the shared gateway while another
  project uses SAM3. The live probe also fixed the missing reference DIS min-max
  normalization in `../android/app/src/main/java/com/alolalab/chtozavino/` and its tests.
  The final files also include `../android/VERIFICATION_RESULTS.md`, its README link,
  `../android/tools/verify_model_vectors.py`, the timm preprocessing correction, and
  exact DIS and SigLIP2 SHA-256 checks in the model-pack builder and Android importer.
- State: done, not committed. Both indices contain 2,271 finite normalized vectors of
  dimension 768 and zero failures. The SAM3 build took 282.1 seconds. The corrected DIS
  build took 3,832.6 seconds. A deterministic 32-image LiteRT comparison passed for
  both indices. The minimum cosine was 0.99999851. The comparison found and corrected
  the missing timm `crop_pct=0.9` preprocessing in Android. All 75 focused workbench
  tests pass. Android lint, debug and release unit tests, the debug APK build, and three
  model-pack builder tests pass. The isolated GX10 endpoint stopped. Port 5997 is
  closed. The shared gateway and SAM3 process did not restart.
- Updated: 2026-09-28T23:53:30+0300

## root

- Task: read the `svoe-vino-lab/workbench` project and report its structure, current
  state, architecture, and developer workflow.
- Source: owner message of 2026-09-28T23:00:51+0300.
- Files: `docs/owner-messages.md` (append) and this section of `ACTIVE_WORK.md`.
- State: done, not committed. The project read was read-only apart from the required
  owner-message and active-work records. No test, model call, server restart, or data
  write ran. The existing Android DIS embedding build stayed untouched.
- Updated: 2026-09-28T23:03:57+0300
- Task 3: verify whether barcode checking happens when an additional image is added.
- Source: owner message of 2026-09-28T23:06:00+0300.
- Files: `docs/owner-messages.md` (append) and this section of `ACTIVE_WORK.md`.
- State: done, not committed. The implementation and commit history were inspected; 5
  QR/barcode client tests and 3 additional-upload integration tests pass. The running
  server log says `QR/barcode scanner: not configured`, so an upload currently keeps the
  photo and reports a warning instead of filling code fields. No product code or data
  changed.
- Updated: 2026-09-28T23:07:00+0300
- Task 2: add an advanced tag filter to `/testset`. The dropdown shows only tags that
  exist in the selected test set.
- Source: owner message of 2026-09-28T23:05:46+0300.
- Files for task 2: `docs/owner-messages.md` (append) and this section of
  `ACTIVE_WORK.md`.
- State for task 2: done, not committed. Commit `65a429a3` already contains the filter.
  The live page lists only `barcode (571)` and `qr_code (245)` for `my`. Selecting
  `barcode` adds `tag=barcode` to the address and reduces the clustered view from 422
  to 106 wines. No product file or data changed. No server restart was necessary.
- Updated for task 2: 2026-09-28T23:07:00+0300
- Task 4: verify whether `lab_server.py` uses `zxing-cpp` directly for additional-image
  barcode checks.
- Source: owner message of 2026-09-28T23:13:17+0300.
- Files: `docs/owner-messages.md` (append) and this section of `ACTIVE_WORK.md`.
- State: done, not committed. The path was inspected; the upload uses the remote scanner
  through `qr_barcode.Client`, while `zxing-cpp` belongs to the separate recognition
  pipeline in `barcode.py`. No product code or data changed.
- Updated: 2026-09-28T23:13:17+0300
- Task 5: run the two Android SigLIP2 Base 224 indices on test set `my` with barcode
  disabled. Compare the results.
- Source: owner message of 2026-09-28T23:59:58+0300.
- Files: `docs/owner-messages.md` (append), this section of `ACTIVE_WORK.md`, two
  permanent pipeline entries in `config.yaml`, DIS query support in
  `pipeline/build_embeddings.py`, `pipeline/embedding_run.py`, and
  `pipeline/run_steps.py`, focused hunks in `tests/test_embedding_run.py` and
  `tests/test_pipelines.py`, two new run directories under `runs/`, and one comparison
  report under `docs/reports/`. The task also updates `../android/VERIFICATION_RESULTS.md`
  and my own hunks in `README.md`, `ChangeLog.md`, and `SMOKE_TESTS.md`.
- State: done, not committed. Both permanent pipelines are valid and have no barcode
  step. The 110 focused tests pass. The controlled final runs have 2,226 identical
  queries, 2,270 current catalogue items, and 2,093 wines. SAM3 positive R@1 is 49.91%.
  DIS positive R@1 is 43.05%. The paired gain is 6.86 percentage points with exact
  McNemar `p=9.01e-09`. DIS has five `no main object` rows. SAM3 has zero errors. The
  isolated GX10 endpoint is stopped.
- Updated: 2026-09-29T01:34:00+0300
- Task 6: restore dragging an image from the linked Yandex Images result into
  `/testset?set=my&q=vibes`.
- Source: owner message of 2026-09-29T00:03:42+0300.
- Files for task 6: `docs/owner-messages.md` (append), this section of
  `ACTIVE_WORK.md`, a separate drop-handling hunk in `pipeline/pages/testset.html`,
  `pipeline/testset_routes.py`, new `pipeline/remote_images.py`, focused hunks in
  `tests/test_testset_routes.py`, new `tests/test_remote_images.py`, and my own hunks
  in `docs/API.md`, `README.md`, `ChangeLog.md`, and `SMOKE_TESTS.md`.
- State for task 6: done, not committed. The page accepts the URL/HTML data types of a
  browser-image drag and unwraps a Yandex Images viewer URL. The new server route fetches
  public HTTP(S) images before its database transaction and refuses local/private
  addresses on every redirect. The exact reported 1000 x 1500 image downloaded as an
  82,872-byte WebP. Tests: 53 Testset, 4 remote-fetch, the lab page/server checks, Python
  compilation, and inline JavaScript syntax pass. The live page has no console error;
  its route fetched the exact image against a deliberately missing set and wrote no data.
  Port 8168 restarted with SIGTERM and answers `/api/dataset` 200 on PID 11528; the
  invalid local fetch probe answers 400. The restart also loaded the current separate
  task 7 barcode/config hunks already present in the shared worktree.
- Updated for task 6: 2026-09-29T00:17:49+0300
- Agreements for task 6: `drink-atlas-workspace-a4 [34c1c5]` is absent from the
  current `ListAgents` answer and stale. The owner directly requested this separate
  drop fix; plan 66 image-tag behavior stays unchanged.
- Task 7: refactor `pipeline/barcode.py` to decode through HTTP `POST /scan`, and read
  the scanner endpoint from `config.yaml` with `{env: QR_SCANNER_ENDPOINT}` support.
- Source: owner message of 2026-09-29T00:05:01+0300.
- Files for task 7: `docs/owner-messages.md` (append), this section of
  `ACTIVE_WORK.md`, `pipeline/barcode.py`, `pipeline/qr_barcode.py`, configuration
  loading code and focused tests as required, barcode benchmark utilities and their
  focused tests, `docs/plans/41_run-step-popup.md`, `docs/plans/42_barcode-step.md`,
  `docs/plans/55_recognize-page.md`, `docs/plans/76_scan-additional-image-codes.md`,
  separate `config.yaml` hunks, and my own hunks in `README.md`, `docs/API.md`,
  `ChangeLog.md`, `SMOKE_TESTS.md`, and `COMMANDS.md` if commands change.
  `requirements-local.txt` only if `zxing-cpp` ceases to be a workbench runtime
  dependency.
- State for task 7: done, not committed. Barcode recognition and additional-image
  uploads use the shared HTTP scanner configured by `qr_scanner` in `config.yaml`; an
  exact `{env:NAME}` endpoint is resolved when the client is built. The workbench no
  longer imports or requires `zxing-cpp`. Focused tests pass: 114 barcode, 17 bulk
  benchmark, 40 recognition benchmark, 40 embedding-run, 69 lab-server, 32 pipeline,
  11 run-step, and 3 additional-code tests. A live config-driven synthetic EAN-13 scan
  returned the expected code. Port 8168 restarted with SIGTERM and `/api/dataset`
  answers 200 on PID 22522.
- Updated for task 7: 2026-09-29T00:30:08+0300
- Agreements for task 7: the sections that name `barcode.py`, `config.yaml`, and focused
  barcode tests are absent from the current `ListAgents` answer and stale. The owner
  directly requested this refactor of those exact areas; their unrelated lines remain
  untouched.
- Task 8: check whether the configured QR scanner engine `auto` matches the previous
  local `zxing-cpp` barcode behavior.
- Source: owner message of 2026-09-29T00:40:16+0300.
- Files for task 8: `docs/owner-messages.md` (append) and this section of
  `ACTIVE_WORK.md`; product code and documentation stay read-only unless the comparison
  finds a mismatch that requires a correction.
- State for task 8: done, not committed. `auto` does not match the former runtime
  behavior: it runs ZXing 3.0.0, zxing-cpp-sr, BoofCV, QR unwarping, and SAM3 +
  qwen3.5-9b, while the old path used local zxing-cpp 2.3.0 with two binarizers and up
  to 34 tiles. It did return the same decoded values as the old path on four generated
  cases (EAN-13, QR, valid-GTIN Code 128, and a small-code composite), but took about
  2.1--5.7 seconds versus 0.1--0.3 seconds locally; the named service `zxing-cpp`
  engine took about 0.03--0.08 seconds round trip on those cases. No catalogue photo
  was sent and no product/configuration file changed.
- Updated for task 8: 2026-09-29T00:44:18+0300
- Task 9: test the official participant harness against `matcher` with the R@1 hits from
  test set `my` and the same pipeline as the matcher. Compare every prediction with the
  expected slug.
- Source: owner message of 2026-09-29T00:48:14+0300.
- Files for task 9: `docs/owner-messages.md` (append), this section of
  `ACTIVE_WORK.md`, and derived test artifacts under
  `../../svoe-wino-hackaton/dataset/derived/matcher-pipeline-test-2026-09-29/`.
  The official dataset, the `my` test set, the selected workbench run, the matcher
  bundle, and matcher code stay read-only.
- State for task 9: done, not committed. The selected source run is
  `2026-09-28T011622Z-lab-siglip2-p512-as-is-my`. It contains 1,223 positive R@1 hits.
  The unchanged official harness wrote 1,223 valid JSONL rows. The matcher returned the
  expected slug for 1,222 photos. Query `q-000932` returned `null`. Its `.jpg` file is
  an `MPO` with two frames. The matcher validator returned 415 because it accepts only
  `JPEG`, `PNG`, and `WEBP`. The temporary matcher stopped. No product code changed.
- Updated for task 9: 2026-09-29T00:58:30+0300
- Task 10: recommend how to prevent the MPO rejection that the matcher pipeline test
  found.
- Source: owner message of 2026-09-29T01:51:38+0300.
- Files for task 10: `docs/owner-messages.md` (append) and this section of
  `ACTIVE_WORK.md`. Product code stays read-only.
- State for task 10: done, not committed. The recommended permanent correction is to
  accept `MPO` as a JPEG-family upload and process frame 0. A regression test must
  compare an MPO result with the first-frame JPEG result. Filtering MPO from the test
  set is not recommended because it hides a production input incompatibility.
- Updated for task 10: 2026-09-29T01:51:38+0300
- Task 11: accept `MPO` as a JPEG-family matcher upload, process frame 0, add regression
  tests, and rerun the 1,223-query official harness.
- Source: owner message of 2026-09-29T01:53:04+0300.
- Files for task 11: `docs/owner-messages.md` (append), this section of
  `ACTIVE_WORK.md`, `../matcher/protection.py`, `../matcher/siglip2.py`,
  `../matcher/group.py`, focused hunks in `../matcher/tests/test_resilience.py`,
  `../matcher/tests/test_siglip2.py`, and `../matcher/tests/test_group.py`, the
  existing derived artifacts under
  `../../svoe-wino-hackaton/dataset/derived/matcher-pipeline-test-2026-09-29/`, and my
  own matcher test-result hunk in `ChangeLog.md` if the file is available.
- State for task 11: done, not committed. The matcher accepts `MPO`, records the source
  format in the request audit, and processes frame 0 explicitly in single-image and
  group paths. All 108 matcher tests pass. The unchanged official harness wrote 1,223
  valid rows, and all 1,223 predictions match the prior R@1 expected slug. Query
  `q-000932` now returns `shato-pino-pino-nuar-krasnoe-suhoe-135`. The failed artifacts
  are preserved under `before-mpo-fix/`. The temporary matcher stopped. Existing
  unrelated matcher changes stay intact.
- Agreements for task 11: `codex-side-matcher-api` is absent from the current
  `ListAgents` result. The owner directly requested this correction after the pipeline
  test found it. This task changes only the MPO-specific hunks in its listed files.
- Updated for task 11: 2026-09-29T02:01:40+0300
- Task 10: change the shared QR scanner engine from `auto` to `zxing-cpp` for behavior
  and performance closer to the former local decoder.
- Source: owner message of 2026-09-29T00:51:28+0300.
- Files for task 10: `docs/owner-messages.md` (append), this section of
  `ACTIVE_WORK.md`, a separate hunk in `config.yaml`, focused scanner configuration
  tests, current scanner documentation, and my own hunk in `ChangeLog.md`. A restart of
  port 8168 belongs to the change.
- State for task 10: done, not committed. `config.yaml` now selects `engine: zxing-cpp`;
  the generic client still accepts all four service engines. The 27 barcode, 32
  pipeline, and 9 scanner-client tests pass. A config-driven live request decoded the
  expected synthetic EAN-13 and sent `zxing-cpp`. Port 8168 restarted with SIGTERM;
  its startup report names `engine zxing-cpp`, and `/api/dataset` answers 200 on PID
  50773.
- Updated for task 10: 2026-09-29T00:54:04+0300
- Task 11: import the 54 archived test-1 shop photos as a new test set. Map each
  photo to `wine_slug` only after a visible-label and catalogue check. Keep unresolved
  photos outside scored ground truth. Run the current matching pipelines on the
  confirmed subset and compare Top-1, Top-5, latency, and failure groups.
- Source: owner message recorded at 2026-09-29T00:55:59+0300. The owner did not select
  one of the three proposed labelling modes and added a comparison task. Continue with
  the recommended model-assisted, independently verified mode.
- Files for task 11: `docs/owner-messages.md` (append), this section of
  `ACTIVE_WORK.md`, new `dataset/test-1/**`, new rows and images of the test set in
  ignored `data/catalog/catalog.sqlite3` and `data/testsets/images/`, a new report under
  `docs/reports/`, and my own hunks in `README.md`, `ResearchLog.md`, and `ChangeLog.md`.
  Existing pipeline code and configuration stay read-only.
- State for task 11: done, not committed. The source is the 54-photo historical commit
  `55cfe4c1aaf51b0f491f851bcb5f22dbc6e337f5`; current upstream removed the photos and
  published no ground-truth labels. Independent review mapped 35 photos to catalogue
  slugs, 13 to confirmed no-match, and 6 multi-product scenes to the unscored Drawer.
  The set is imported in the lab database. Three profiles completed 162 requests with
  no error. `rerank-siglip2-512-crop` gives family-aware Top-1 71.4% and Top-5 80.0% on
  the 35 catalogue matches, but all 13 no-match photos get a false card. The database
  backup is `data/backups/catalog-before-test-1-20260929T0121+0300.sqlite3`. The
  58 focused test-set unit tests pass. Export restored all 48 labels and extra accepted
  slugs.
- Updated for task 11: 2026-09-29T01:26:17+0300
- Task 12: compare the three WineHack catalogue representations
  (`catalog.csv`, `catalog_enriched.csv`, and `seed_wines.sql`) with the current lab
  catalogue. Report record and slug coverage, field completeness, transformations,
  duplicates, and useful enrichment that we do not hold.
- Source: owner message of 2026-09-29T00:55:59+0300.
- Files for task 12: `docs/owner-messages.md` (append), this section of
  `ACTIVE_WORK.md`, a new report under `docs/reports/`, and my own hunks in
  `ResearchLog.md` and `ChangeLog.md`. WineHack sources and our catalogue stay
  read-only.
- State for task 12: done, not committed. `origin/main` of `WineHackathon/backend` is
  current at `642cb396f5c6bcd600937dce24c0e29c0b783d0d`; the separately referenced `infra`
  and `catalog-service` repositories are not public. Its 2,103 official slugs and eight
  base fields equal ours. The source has 2,044 exact duplicate rows. The enrichment has
  58 shared image-file groups across 207 slugs. The SQL has 4,533 generated pairings,
  NULL prices, and an artificial `roskachestvo_score`. The separate Markdown and JSON
  reports record the checks and the Pareto recommendation.
- Updated for task 12: 2026-09-29T01:26:17+0300

- Task 13: compare DIS and SAM3 across six SigLIP2 SO400M image towers on all 2,226
  queries of `my`. Test NaFlex p256/p512/p1024 and fixed 256/384/512. Treat fixed
  256/384/512 as the comparable 256/576/1024 patch-token levels. Disable barcode.
  Reuse each prepared image across models. Report paired retrieval and negative-rejection
  metrics.
- Source: owner messages recorded at 2026-09-29T01:56:07+0300 and
  2026-09-29T01:56:08+0300. The owner selected the complete matrix with shared prepared
  images.
- Files for task 13: `docs/owner-messages.md` (append), this section of
  `ACTIVE_WORK.md`, new `docs/plans/79_segmentation-model-matrix.md`, a new benchmark
  utility under `scripts/`, focused tests under `tests/`, generated artifacts under
  `runs/segmentation-model-matrix-2026-09-29/`, a new report under `docs/reports/`, and
  my own hunks in `ResearchLog.md`, `ChangeLog.md`, `SMOKE_TESTS.md`, and `COMMANDS.md`.
- State for task 13: done, not committed. The complete 12-cell run used 2,270 catalogue
  sources, 2,226 queries, and 53,922 vectors. SAM3 improved R@1 in all six models. The
  best cell was SAM3 fixed 512 at 81.42% R@1 and 96.66% R@5. DIS had five segmentation
  failures. SAM3 had none. Seven tests, compilation, and final vector verification pass.
  Existing catalogue indices and the test-set database stayed read-only. No GX10 service
  restarted or changed configuration. The report and generated artifacts are complete.
- Updated for task 13: 2026-09-29T03:55:18+0300

- Task 14: extend the frozen plan 79 matrix with a path that uses the original image
  without segmentation. Keep barcode disabled. Compare the new path with DIS and SAM3.
- Source: owner message of 2026-09-29T03:56:56+0300 and answer of
  2026-09-29T07:08:03+0300. The owner selected the complete six-model extension.
- Files for task 14: the task 13 benchmark utility, tests, generated matrix artifacts,
  report, and my own hunks in the same documentation files.
- State for task 14: done, not committed. The complete 18-cell run used the frozen
  2,270-source catalogue and the frozen 2,226-query set. It produced 80,898 vectors.
  No segmentation with fixed 512 reached 78.69% R@1 and 95.75% R@5. It was 2.73 pp
  below SAM3 fixed 512 at R@1, but it was 4.13 pp above DIS fixed 512. SAM3 improved
  R@1 against no segmentation for every model. All six gains were significant. The
  eight focused tests, compilation, scoring, and vector verification pass. One transient
  HTTP 429 was repeated successfully. No embedding was lost. No GX10 service restarted
  or changed configuration.
- Updated for task 14: 2026-09-29T08:01:00+0300

- Task 15: create a script that prepares an Android catalogue bundle from
  `data/catalog/`. Include one catalogue image for each wine. Use `main_patched` when it
  exists. Otherwise, use `main`.
- Source: owner message of 2026-09-29T08:06:31+0300.
- Files for task 15: `docs/owner-messages.md` (append) and this section of
  `ACTIVE_WORK.md`. Add implementation, tests, and documentation after the owner selects
  the output contract.
- State for task 15: done as part of task 17. The implemented contract is the Android
  model-pack format version 2 contract.
- Updated for task 15: 2026-09-29T08:39:42+0300

- Task 16: record the known DIS failure on a close-up label in `KNOWN_ISSUES.md`.
- Source: owner messages of 2026-09-29T08:09:35+0300 and 08:09:47+0300.
- Files for task 16: `docs/owner-messages.md` (append), this section of
  `ACTIVE_WORK.md`, and one new entry in `../matcher/docs/KNOWN_ISSUES.md`.
- State for task 16: done, not committed. The entry records the effect, cause, evidence,
  risk, and possible corrections. No code or runtime data changed.
- Updated for task 16: 2026-09-29T08:09:47+0300

- Task 17: finish the Android application with a built-in offline model pack. Include
  the `android-siglip2-base-224-dis-white` catalogue vectors. Include one catalogue
  image per wine. Prefer `main_patched` over `main`. Keep manual model-pack updates.
- Source: owner message of 2026-09-29T08:11:27+0300.
- Files for task 17: `docs/owner-messages.md` (append), this section of
  `ACTIVE_WORK.md`, new `docs/plans/81_android-built-in-pack.md`, Android application
  code and tests under `../android/app/`, Android pack tools and tests under
  `../android/tools/`, `../android/docs/model-pack.md`, `../android/README.md`,
  `../android/docs/specification.md`, `../android/ChangeLog.md`,
  `../android/ResearchLog.md`, `../android/SMOKE_TESTS.md`, and
  `../android/VERIFICATION_RESULTS.md`. Generated packs and model files stay ignored by
  Git.
- State for task 17: done, not committed. The built-in format version 2 pack contains
  2,093 wines, 2,093 DIS-preprocessed SigLIP2 vectors, 2,093 catalogue images, and 135
  local code relations. The selection contains 23 `main_patched` images and 2,070
  `main` images. Five active wines have no eligible image and were omitted. The pack
  SHA-256 is
  `da8a079c5e599c663e3a844d743af5103a9b8b896aa15f1660f07c1cdea56684`.
  The debug APK contains the pack as an uncompressed asset. Five Python tests, Android
  debug and release unit tests, `lintDebug`, and `assembleDebug` pass. A fresh APK
  installation and first-start pack installation passed on an arm64 Android 14 phone.
  The installed manifest and all 2,093 image files were verified. Interactive UI and
  inference checks are pending because the phone was locked.
- Updated for task 17: 2026-09-29T08:39:42+0300
- Agreement for task 17: `codex-android-embeddings` is not a live session. Its section
  is done. The owner directly requested this follow-up. Preserve its existing changes.

- Task 18: fix the Android SigLIP2 empty-vector error on a physical phone. Add an
  automatic CPU retry when GPU inference returns an invalid vector. Add a settings page
  through a gear icon. Remove the manual model-pack replacement action. Replace the
  long camera and gallery button labels with compact icon buttons.
- Source: owner messages of 2026-09-29T10:03:54+0300 and 10:07:17+0300.
- Files for task 18: `docs/owner-messages.md` (append), this section of
  `ACTIVE_WORK.md`, Android inference code and tests under `../android/app/`, and my own
  hunks in the Android verification documents.
- State for task 18: done, not committed. Output validation found a non-finite SigLIP2
  GPU result on the Realme Android 14 phone. The automatic CPU path matched `Пино Нуар`
  at cosine 0.910. The settings page, compact image actions, and removal of the pack
  replacement action passed physical UI checks.
- Updated for task 18: 2026-09-29T10:56:00+0300

- Task 19: fix EAN-13 scanning through Google Code Scanner. Keep Google Code Scanner.
  Add explicit scan lifecycle feedback and a manual-input fallback.
- Source: owner message of 2026-09-29T10:07:17+0300.
- Files for task 19: this root section, `docs/owner-messages.md` (append), Android scanner
  code and UI under `../android/app/`, and my own hunks in the Android documentation.
- State for task 19: done, not committed. The scanner requests supported formats,
  auto-zoom, and manual input. The application reports scanner start, cancellation,
  empty output, and failure. Google Code Scanner opened and showed its manual input.
  A physical camera scan of a printed EAN-13 remains a smoke-test item.
- Updated for task 19: 2026-09-29T10:56:00+0300

- Task 20: use the shared product logo from `../assets/` for the Android application
  launcher icon. Convert the asset to Android resource formats when required.
- Source: owner message recorded at 2026-09-29T10:35:30+0300.
- Files for task 20: this root section, `docs/owner-messages.md` (append), Android
  launcher resources and manifest under `../android/app/`, and my own hunks in the
  Android documentation.
- State for task 20: done, not committed. The shared source is
  `../assets/product-logo-640x640.png`. The APK contains adaptive, round, and fallback
  launcher resources. The manifest uses the new resources.
- Updated for task 20: 2026-09-29T10:56:00+0300

- Task 21: test DIS and SigLIP2 on the connected Google Pixel 8. Add the model
  accelerator setting `Авто`, `GPU`, and `CPU`. On the first launch, validate GPU output
  and save a safe automatic selection. Keep CPU fallback for invalid GPU output.
- Source: owner messages recorded at 2026-09-29T10:35:30+0300.
- Files for task 21: this root section, `docs/owner-messages.md` (append), Android
  inference code, settings UI, preferences, tests, and my own hunks in the Android
  documentation.
- State for task 21: done, not committed. The application has separate `Авто`, `GPU`, and `CPU`
  settings for DIS and SigLIP2. It tests both GPU outputs on the first start and saves
  the safe selections. The Realme automatic check selected DIS GPU and SigLIP2 CPU.
  A complete recognition in this mode matched `Пино Нуар` at cosine 0.910. The Pixel 8
  automatic check selected DIS GPU and SigLIP2 GPU. A complete Pixel 8 recognition
  matched `Пино Нуар` at cosine 0.909. The Pixel used a compact one-wine pack because the
  production APK did not fit in 1.2 GB of free storage. The compact pack kept the exact
  production model files, vector, and image. The temporary application and image were
  removed after the test.
- Updated for task 21: 2026-09-29T11:28:43+0300

- Task 22: show the image score as `Сходство: 91%`. Replace the bottom navigation
  glyphs with clear icons. Name the debug APK `chtozavino_debug.apk`. Add the product
  website below the application version. Show `Не требует интернета`. Diagnose the
  empty history on the first phone. Verify the system-controlled dark theme.
- Source: owner messages recorded at 2026-09-29T11:51:48+0300. The owner selected
  `Сходство: 91%`.
- Files for task 22: this root section, `docs/owner-messages.md` (append), Android UI,
  icon resources, build configuration, tests, and my own hunks in the Android
  documentation.
- State for task 22: done, not committed. Version 0.1.3 shows `Сходство: 91%`,
  uses clear 30 dp tab icons, shows the product site link, and builds
  `chtozavino_debug.apk`. The history was empty because the earlier device-test rows
  were cleared. A new `Пино Нуар` row survived an application restart. The Realme
  followed the system dark setting. Its original light setting was restored. Gradle
  lint, debug and release unit tests, and assembly passed.
- Updated for task 22: 2026-09-29T12:07:00+0300

- Task 23: change the application ID to `chtozavino.alolalab.com`. Remove the old
  `Chtozavino.alolalab.com` installation. Install and test the full application on the
  connected Pixel 8.
- Source: owner message recorded at 2026-09-29T12:45:14+0300.
- Files for task 23: this root section, `docs/owner-messages.md` (append), Android build
  configuration, specification, change log, research log, smoke tests, verification
  results, and README.
- State for task 23: done, not committed. Version 0.1.4 uses
  `chtozavino.alolalab.com`. The old package was absent from the Pixel 8 and was
  removed from the Realme with its local data. The full APK installed on the Pixel 8.
  The installed pack has 2,093 images, wines, and vectors. The automatic check selected
  GPU for DIS and SigLIP2. The process stayed active with no crash. The Pixel lock
  screen prevented direct UI interaction. Gradle lint, debug and release unit tests,
  and assembly passed.
- Updated for task 23: 2026-09-29T12:55:00+0300
- Continuation of task 23: the owner unlocked the Pixel 8. Direct UI and full
  recognition checks passed. The main page shows the automatic GPU selections for DIS
  and SigLIP2. The full run matched `Пино Нуар` at 91%. DIS GPU used 2,463 ms.
  SigLIP2 GPU used 2,134 ms. Search used 100 ms. The DIS mask opened. The history row
  stayed after an application restart.
- Updated for task 23 continuation: 2026-09-29T13:18:00+0300
- Task 24: verify the wine-result and product-site links from the Pixel 8 application.
  Verify all settings-page values and controls on the Pixel 8.
- Source: owner message recorded at 2026-09-29T13:12:38+0300.
- Files for task 24: this root section, `docs/owner-messages.md` (append), and my own
  Android verification, research, change-log, and smoke-test hunks.
- State for task 24: done, not committed. The wine result opened its exact
  `vino-svoe.ru/wines/...` URL in Chrome. The settings link opened
  `https://vino-svoe.ru`. The settings page correctly showed pack version
  `20260929-dis-main`, both 2,093 counts, selected `Авто` controls, the saved GPU/GPU
  automatic selection, the GPU recheck action, version 0.1.4, and the product-site
  link. The complete page rendered correctly in the Pixel 8 dark system theme.
- Updated for task 24: 2026-09-29T13:18:00+0300
- Task 25: create the selected eight-image marketing screenshot set on the Pixel 8.
  Include a bottle image on the main page in light and dark themes. Use only verified
  working examples. Create source PNG files, website WebP files, and one presentation
  contact sheet.
- Source: owner messages recorded at 2026-09-29T13:35:00+0300. The owner selected
  option 1.
- Files for task 25: this root section, `docs/owner-messages.md` (append), new files
  under `../android/docs/screenshots/android-0.1.4/`, one link in `../android/README.md`,
  and my own Android change-log, research-log, and smoke-test hunks.
- State for task 25: done, not committed. The set has eight primary screenshots and
  three detail screenshots. Every screenshot comes from a verified working state on
  the Pixel 8. The photo flow matched `Пино Нуар` at 91%. The history row persisted.
  Google Code Scanner read physical EAN-13 `4630037250909`. The local catalogue
  matched it to `Шато Тамань. Каберне Совиньон` at 100%. The set contains full PNG
  files, cropped WebP files, and PNG and WebP contact sheets. The Pixel 8 dark theme
  was restored. System UI demo mode was disabled. The temporary image was removed.
- Updated for task 25: 2026-09-29T13:48:43+0300
- Task 26: add the application version to each distribution APK file name and build
  the versioned APK.
- Source: owner message recorded at 2026-09-29T13:50:52+0300.
- Files for task 26: this root section, `docs/owner-messages.md` (append),
  `../android/app/build.gradle.kts`, and my own Android documentation hunks.
- State for task 26: done, not committed. The version 0.1.4 distribution file is
  `chtozavino-0.1.4-debug.apk`. The output directory contains no obsolete unversioned
  APK. `lintDebug`, debug and release unit tests, and `assembleDebug` passed. The APK
  has application ID `chtozavino.alolalab.com`, version code 5, version name 0.1.4,
  `minSdkVersion` 28, and `targetSdkVersion` 36. Its size is 576,503,269 bytes. Its
  SHA-256 is `e22d166c8922936dd75acb63ec0b860334ef982caf5bbde36c5bb5c079227c26`.
- Updated for task 26: 2026-09-29T13:55:00+0300
- Task 27: create the selected full Android application landing page in `../webui`.
  Add a versioned APK download link. Use verified Pixel 8 screenshots. Explain offline
  recognition, image search, QR and barcode search, on-device processing, the local
  catalogue, automatic acceleration, history, themes, and Android 9 support.
- Source: owner messages recorded at 2026-09-29T14:00:21+0300. The owner selected
  option 1.
- Files for task 27: this root section, `docs/owner-messages.md` (append), and files
  only in `../webui/` for implementation and Web UI documentation.
- State for task 27: done, not committed. The implementation specification is
  `../webui/docs/android-landing.md`. The `/android` page includes the configured
  versioned APK download, verified Pixel 8 screenshots, product benefits, search
  metadata, and navigation. Type checks passed. All 169 tests passed in 14 files. The
  production build passed. The local APK route returned the expected HTTP 200 headers.
  An invalid file name returned HTTP 404. Desktop light and mobile light and dark
  layouts passed a visual check.
- Updated for task 27: 2026-09-29T14:11:50+0300
- Task 28: export the Android model pack from the workbench with transparent segmented
  package images instead of the large `main` or `main_patched` files. Resize the display
  images for Android. Document the command in `../android/README.md`.
- Source: owner message recorded at 2026-09-29T14:46:36+0300. The owner selected
  option 1.
- Files for task 28: this root section, `docs/owner-messages.md` (append),
  `../android/tools/build_catalog_pack.py`, its tests, and my own Android specification,
  model-pack, README, change-log, research-log, and smoke-test hunks.
- State for task 28: done, not committed. The exporter now packages the related
  transparent `image_derivative(kind=package)` cut instead of the large `main` or
  `main_patched` source image. It writes WebP at quality 80 and limits the long side to
  1,024 pixels. The verified pack contains 2,093 vectors, wines, and images. It is
  429,200,870 bytes. Its SHA-256 is
  `cb181ce8f5583d92c800014c083eb75cc0458fa205407aa24bc032a80b050ec3`.
  Six focused Python tests passed. The Android documentation records the exporter
  contract and measured result. The Android Gradle build was deferred to task 29.
- Updated for task 28: 2026-09-29T15:00:52+0300
- Task 29: build and verify the Android release variant with the current transparent
  catalogue pack. Keep the application version in the copied APK file name.
- Source: owner message recorded at 2026-09-29T15:20:00+0300.
- Files for task 29: this root section, `docs/owner-messages.md` (append), and my own
  Android README, change-log, research-log, and smoke-test hunks.
- State for task 29: done, not committed. Release unit tests, `lintRelease`, R8,
  resource shrinking, `assembleRelease`, and ZIP alignment verification passed. The
  versioned file is `chtozavino-0.1.4-release-unsigned.apk`. It is 441,352,932 bytes.
  Its SHA-256 is
  `a5cf1ce4a42715c521579a899c5dc9bbeddb32b5ae55c9ad54c82dbd19d765e4`.
  The embedded model pack matches the verified transparent catalogue pack. The APK is
  unsigned because the project has no production signing configuration.
- Updated for task 29: 2026-09-29T15:20:00+0300
- Task 30: add debug-only Android HTTP endpoints compatible with `/v1/match` and
  `/v1/eval/predict`. Add two workbench run configurations. Add a device IP parameter
  to New Run. Run the test set against the Pixel 8.
- Source: owner message recorded at 2026-09-29T15:41:59+0300.
- Files for task 30: this root section, `docs/owner-messages.md` (append), Android debug
  server code, Android build configuration, manifest, tests, Android documentation,
  workbench `config.yaml`, New Run server and page code, focused tests, and workbench
  documentation. The external port registry file is
  `/Users/ashmelev/Admin/mbp2023/PORTS_USED.md`.
- State for task 30: done, not committed. The debug APK serves `/healthz`,
  `/v1/eval/predict`, and `/v1/match` on port 18088. NanoHTTPD is absent from the
  release runtime. Workbench has two permanent device pipelines and a checked New Run
  IPv4 field. Focused Workbench tests passed: 32, 16, 27, and 11 tests. Android
  `lintDebug`, `testDebugUnitTest`, `assembleDebug`, and `compileReleaseKotlin` passed.
  The APK installed on Pixel 8. Both clean 10-query runs had zero errors. Eval gave
  recall@1 0.3 and median 4,349 ms. Match gave recall@1 0.3, recall@5 0.6, recall@10
  0.9, and median 4,597 ms. A live run through `POST /api/run-jobs` also completed.
  Port 8168 restarted and answers HTTP 200. The implementation plan is
  `docs/plans/86_android-device-http-evaluation.md`.
- Updated for task 30: 2026-09-29T16:56:52+0300
- Task 31: document the debug Android bulk-test mechanism in the Android README.
- Source: owner message recorded at 2026-09-29T16:58:49+0300.
- Files for task 31: this root section, `docs/owner-messages.md` (append), and
  `../android/README.md`.
- State for task 31: done, not committed. The Android README now explains the
  debug-only bulk-test server, both permanent Workbench pipelines, the UI procedure,
  CLI commands, Wi-Fi and ADB connection options, the output location, and the
  full-run duration warning. `git diff --check` passed for the changed documentation.
- Updated for task 31: 2026-09-29T17:02:00+0300
- Task 32: keep the debug Android HTTP server off by default. Add a debug-only settings
  switch that starts or stops the server immediately.
- Source: owner message recorded at 2026-09-29T17:01:58+0300.
- Files for task 32: this root section, `docs/owner-messages.md` (append), Android debug
  application and server settings code, main application state and settings UI, focused
  Android tests, `../android/README.md`, `../android/docs/specification.md`,
  `../android/ChangeLog.md`, and `../android/SMOKE_TESTS.md`.
- State for task 32: done, not committed. A fresh debug installation keeps the server
  off. The debug settings page has a saved switch that starts and stops port 18088
  immediately. The release UI hides the switch. The release runtime still has no
  server implementation or NanoHTTPD dependency. All 21 debug unit tests passed.
  `lintDebug`, `compileReleaseKotlin`, and `assembleDebug` passed. The updated APK
  installed on Pixel 8. The off, on, saved-on-after-restart, and off-again states passed.
  `GET /healthz` returned HTTP 200 while the server was enabled. The Pixel 8 server and
  switch were left off.
- Updated for task 32: 2026-09-29T17:13:00+0300
- Task 33: inspect every unusable photo in test set `official-real-photos` with origin
  `manual`, and verify whether the catalogue really has no matching wine.
- Source: owner message recorded at 2026-09-29T17:18:42+0300.
- Files for task 33: this root section, `docs/owner-messages.md` (append), and
  `data/catalog/catalog.sqlite3` for the approved test-photo move. The catalogue wine
  rows and application stay read-only.
- State for task 33: done, not committed. All 15 unusable photos were inspected.
  Two photos have a clear catalogue target, and one ambiguous two-wine photo contains
  one catalogue target. Twelve photos have no exact local card and image match. The
  owner clarified that `variant` means skip and is not implemented yet. The Pinot Noir
  photo can use `positive`. The `Winery Series Red Blend` photo must not move to the
  regular Red Blend slug. The catalogue and test-set data stayed read-only. The browser
  remains open on the complete unusable-photo view.
- Follow-up for task 33: verify the Red Blend slug against the two supplied product
  images. The black `Noble Selection` bottle is a different product. The regular Red
  Blend card is also not an exact image match: its front label names Cabernet Sauvignon,
  Merlot, `Red Blend`, and 2021. The test bottle says `Winery Series Red Blend` and has
  no grape text on the front label. The exact `Winery Series` card and image are absent.
- Online verification for task 33: done. Current RBC Wine listings distinguish
  `Winery Series. Red Blend` 2023 (Cabernet Sauvignon 46%, Merlot 34%, Cabernet Franc
  20%) from the regular `Red Blend` 2022/2021 (Cabernet Sauvignon and Merlot). The
  producer describes Winery Series as a separate limited experimental collection.
  Therefore the test photo must not move to the regular Red Blend slug; the exact
  Winery Series product is absent from the local catalogue.
- Owner-policy discussion for task 33: waiting. The owner asks whether a Winery Series
  blend with no dedicated catalogue slug may use the sole Golubitskoe Estate Red Blend
  slug. No move has been made; `variant` remains unused.
- Repeat review for task 33: done, not committed. The Winery Series Red Blend photo is
  already `positive` under the regular Red Blend slug (timestamp 19:00:34). Twelve
  photos remain unusable. Eleven have no suitable catalogue family slug: two Aristov
  Donum XXIV, Mogzauri Alazanskaya Dolina, AYA Purity in Balance, four Alveus Orange
  Brut, one multi-product Fanagoria photo, Inkerman Cabernet, and Litavshchuk Cabernet
  Sauvignon. One two-product Inkerman photo contains the catalogued Shato Ruzh but is
  ambiguous because Busso is equally prominent. No test-set data changed in this
  repeat review; `variant` was not used.
- Updated for task 33: 2026-09-29T19:08:23+0300
- Task 34: diagnose why the 10-query Pixel 8 Android smoke run reached only 30 percent
  recall@1.
- Source: owner message recorded at 2026-09-29T17:24:16+0300.
- Files for task 34: this root section, `docs/owner-messages.md` (append), and my own
  findings in `../android/ResearchLog.md`. Add the labelled query collage under
  `../android/docs/test-results/` and one entry in `../android/ChangeLog.md`. Run files
  and catalogue data stay read-only.
- State for task 34: done, not committed. The 10-row limit selected 10 photographs of
  only four wine SKUs. Six photographs cover two near-identical Abrau-Durso Reserve
  bottles. Three errors are rank-2 near-ties with gaps from 0.0017 through 0.0042. Two
  Pinot Noir queries chose another Pinot Noir SKU. One Syrah query chose another Syrah
  SKU. One query missed the correct wine in the first 20. The same desktop pipeline
  also produced exactly three rank-1 matches for these 10 photographs. The complete
  desktop benchmark reached 43.05 percent recall@1 across 1,647 positive queries. A
  labelled 2,560 by 1,710 pixel collage records all 10 queries and their Android result.
- Updated for task 34: 2026-09-29T17:29:49+0300

- Task 35: build the current optimized Android release variant. Sign a separate test
  copy with the local Android debug key. Install that copy on the Pixel 8. Verify the
  release application, the embedded catalogue, the release settings, and one complete
  image-recognition flow.
- Source: owner message recorded at 2026-09-29T19:07:37+0300.
- Files for task 35: this root section, `docs/owner-messages.md` (append), and my own
  Android entries in `../android/ChangeLog.md`, `../android/ResearchLog.md`, and
  `../android/SMOKE_TESTS.md`. Generated APK files stay outside Git.
- State for task 35: waiting for the owner to reconnect the Pixel 8 over USB. The
  release tests, lint, R8, resource shrinking, assembly, APK signing, signature check,
  and ZIP alignment check passed. The non-incremental install succeeded. The release
  application started. The first-run consent, main page, built-in catalogue with 2,093
  images and wines, and automatic GPU/GPU selection passed. The device disconnected
  during the settings check. A complete release recognition still needs verification.
- Updated for task 35: 2026-09-29T19:16:30+0300

- Task 36: deploy the production Android APK at
  `https://vino-svoe.ru/downloads/chtozavino-0.1.4-release.apk`. Use a permanent release
  signature. Update the Web UI release contract and deployment configuration. Verify
  the public download body, headers, size, and SHA-256.
- Source: owner message recorded at 2026-09-29T19:50:22+0300.
- Files for task 36: this root section, `docs/owner-messages.md` (append), required
  files under `../webui/`, my own Android release documentation entries, and the
  applicable website deployment record under `/Users/ashmelev/Admin/infra/` or
  `<workspace>/deploy/`. Generated APK files stay outside Git.
- State for task 36: waiting for the owner. The requested host is the separate official
  `Свое Вино от РСХБ` Nuxt site behind QRATOR at `178.248.236.248`. The requested path
  returns HTTP 404. The workspace and the infrastructure repository contain no
  deployment record or credential for this host. The controlled Android landing page
  is on `chtozavino.ru`. The Android project also has no permanent release key. Only
  the local Android debug key exists. No public file or service changed.
- Updated for task 36: 2026-09-29T19:53:41+0300

- Task 37: publish the Android 0.1.4 artifacts through GitHub Releases in
  `s1mb1o/svoe-vino-lab-dev`. Reuse an existing suitable release when present. Do not
  publish an unsigned APK as an installable release. Verify every uploaded asset with
  the GitHub API.
- Source: owner message recorded at 2026-09-29T19:57:44+0300.
- Files for task 37: this root section, `docs/owner-messages.md` (append), and my own
  Android release documentation entries. GitHub release metadata and assets are
  external writes. Generated APK files stay outside Git.
- State for task 37: done, not committed. Created private pre-release
  `android-v0.1.4` at source commit `9bea7d8`. Uploaded the optimized test-signed APK,
  the debug APK, and their SHA-256 file. GitHub reports all three assets as uploaded.
  Both GitHub APK digests match the local files. The unsigned APK is not published.
- Updated for task 37: 2026-09-29T20:03:35+0300

## drink-atlas-workspace-b6 [088a3a]

- Task: a rotation test of one catalogue main image: cosine similarity to the indexed
  `full` vector per angle (5° steps) for the NaFlex p256/p512/p1024 and the fixed
  256/384/512 embeddings, on a white and on a black background. Read-only for the
  catalogue and the indexes.
- Source: owner message of 2026-09-29T01:10:49+0300.
- Files: `docs/owner-messages.md` (append), `scripts/rotation_similarity.py` (new),
  `scripts/rotation_similarity_plots.py` (new),
  `scripts/rotation_multiref.py` (new),
  `scripts/rotation_refsets.py` (new),
  `docs/reports/rotation-similarity-2026-09-29.md` (new) and its artifact folder, and my
  own hunks in `ResearchLog.md`, `ChangeLog.md`.
- Task 2: Russian charts with bottle thumbnails and a collage of the rotation steps with
  a black image border (owner message of 2026-09-29T01:23:58+0300).
- Task 3: the reference side gets 10 vectors (the index image on white, rotated 0° to 45°
  in steps of 5°); the query rotates 0° to 355° as before; the score is the maximum
  cosine. The vectors are saved in the report folder, not in the catalogue index (owner
  message of 2026-09-29T01:34:10+0300).
- Task 4: five more reference sets (0°–355°/5°, 0°–359°/1°, 0°–45°/1°, 0°–90°/5°,
  0°–90°/1°), each saved in its own folder (owner message of 2026-09-29T01:44:56+0300).
- Task 5: full-circle reference sets with the steps 3°, 8°, 9°, 12°, computed from the
  saved 0°–359° vectors, no new embedding (owner message of 2026-09-29T01:56:01+0300).
- Task 6: the rotation tests of tasks 1 to 5 with the DINOv3 entries, in a separate folder
  `docs/reports/rotation-dinov3-2026-09-29/` and the report `docs/reports/rotation-dinov3-2026-09-29.md` (owner message of 2026-09-29T02:02:13+0300). The plot scripts get
  a layout for any set of entries.
- Task 7: rotation-augmented catalogue vectors for NaFlex p512 (0-360/1, 0-360/5, 0-180/1,
  0-180/5) and a run on the test set `my` without barcode and rerank, against
  `siglip2-p512-crop` and `siglip2-p512-as-is`. Owner answers of 2026-09-29T07:06:38+0300: separate scripts, no
  change of lab code or config.yaml; stage 1 = the 5° sets, stage 2 (1°) after the owner
  decides. Files: `scripts/rotation_index_build.py` (new), `scripts/rotation_index_eval.py`
  (new), `work/rotation-index/` (vectors), `docs/reports/rotation-index-p512-2026-09-29.md`
  (new) and its folder.
- Task 8: plan 82, max-over-rotation matching in the lab and the matcher
  (`docs/plans/82_rotated-reference-embeddings.md`; owner message of about 07:18 and the
  answers recorded at 2026-09-29T08:17:50+0300; plan approved about 08:12).
- Files 8: `docs/plans/82_rotated-reference-embeddings.md` (new), `pipeline/embeddings.py`,
  `pipeline/build_embeddings.py`, `pipeline/embedding_run.py`, `pipeline/matcher_bundle.py`,
  `config.yaml` (separate hunks: two entries at the end of `embeddings:`, seven pipelines),
  `scripts/rotation_index_eval.py`, `tests/test_rotated_embeddings.py` (new; the plan
  named the six present test files, but the new tests went into this one file, and the
  present test files did not change), `../matcher/bundle.py`, `../matcher/catalog.py`,
  `../matcher/tests/test_rotation.py` (new), one line of `../matcher/tests/test_siglip2.py`,
  one line of `tests/test_barcode.py` (the count 26 → 33; the seven barcode twins of the
  plan 82 pipelines are in `config.yaml` after `barcode-siglip2-p512-crop`),
  `docs/reports/rotation-index-p512-2026-09-29.md` (new), runtime output in
  `data/catalog/embeddings/gx10-siglip2-so400m-patch16-naflex-p512-rot{5,10}/`, and my own
  hunks in `ChangeLog.md`, `ResearchLog.md`, `SMOKE_TESTS.md`, `COMMANDS.md`, `README.md`,
  `docs/API.md`, `docs/testing/matcher-bundle.md`, `docs/plans/10_*.md`,
  `docs/plans/72_matcher-bundle.md`, `../matcher/ChangeLog.md`, `../matcher/README.md`,
  `../matcher/TESTING.md`.
- Agreements 8: the owner approval of plan 82 is the permission for the files that the
  stale sections `drink-atlas-workspace-66`, `codex-side-matcher-bundle`,
  `codex-android-embeddings`, `drink-atlas-workspace-31`, `codex-main-scene-ranking`, and
  `root` list (git shows no pending change in those code files). Session e3 answered at
  about 08:22: its matcher hunks are committed (babef66, 16b059d), its section is removed,
  the matcher files are free. The owner chose the 8168 restart at 09:59:38.
- Agreement with c4 (11:45 to 11:47): c4 (this owner conversation, resumed in a new
  process) and b6 had both started the three rot5 runs at 11:43; both stopped their chains;
  b6 restarted them at 11:46:41 as the only chain (logs `work/rotation-index/run-<p>-b6.out`)
  and keeps the runs, their GPU_TASKS row, and the report section; c4 does not edit the report.
- Agreement with 62 (2026-09-29T12:03:41+0300): b6 agreed that session 62 (plan 83) adds separate hunks in
  `config.yaml` (3 `pipeline:` entries after `vino-svoe-search-by-photo`) and in
  `../matcher/README.md` and `../matcher/ChangeLog.md`; my hunks stay unchanged.
- Committed for task 8: the matcher hunks are in HEAD 0657f46 (session b3, owner request
  "git commit matcher" at 10:41:37); the workbench files of task 8 stay uncommitted.
- Also changed for task 8: `scripts/rotation_index_eval.py` (Catalogue attribute
  `angles`), `tests/test_rotated_embeddings.py` (new).
- State: task 8 done, not committed (the matcher part is in HEAD 0657f46); waiting: the owner decides the commit of the workbench files. Tasks 1 to 7 done, not committed.
- Updated: 2026-09-29T12:31:11+0300

## drink-atlas-workspace-11 [5d8e76]

- Task: a read-only review of the storage of `data/catalog/embeddings/` and of the use of
  the prepared images; the new list `FIX_LATER.md`; rules 39 to 42 ("Known problems").
- Source: owner messages of 2026-09-29T07:44:57+0300, 07:50:13 (cache or catalogue data),
  07:54:44 (add the item to a fix-later list; the owner chose `FIX_LATER.md`), and
  08:00:44 (a rule: a problem in `FIX_LATER.md` or a known-issues file is not a problem now).
- Files: `docs/owner-messages.md` (append), `ResearchLog.md` (one new entry at the top),
  `FIX_LATER.md` (new, owner answer of 07:55), my own hunk in `ChangeLog.md`, and a new
  last section of `AGENTS.md` (rules 39 and later). No code, no data file.
- State: done, not committed. e3 renamed the matcher list to
  `../matcher/docs/KNOWN_ISSUES.md` (owner answer "use KNOWN_ISSUES.md", 08:05:15). Rule 39
  of `AGENTS.md` names `FIX_LATER.md` and each file `KNOWN_ISSUES.md`, and links the matcher list.
- Updated: 2026-09-29T08:08:00+0300
- Agreements: the section `codex-side-commands-rules` lists `AGENTS.md`. Its rules 29 to 38
  are committed; git shows no pending change in `AGENTS.md`. The owner asked for the new
  rule directly (08:00:44). I add a new section at the end and change no other line.
  e3 owns `../matcher/docs/known-issues.md` and its links. I asked e3 at 08:06 for the
  rename and the link updates. I change none of its files. e3 confirmed the rename and
  the link updates at 08:07; I checked that no link to the old name is left in `../matcher/`.

## drink-atlas-workspace-a8 [eaf131]

- Task: one model proxy on this Mac (`127.0.0.1:18092`) for SAM3, Grounding DINO, and
  SigLIP2 (NaFlex and fixed). It keeps the API of the gx10 gateway
  `http://192.168.86.14:18082`, sends each request to the first host with a free slot
  (gx10 and RTX 4090 hosts), retries a failed request on another host, runs the SSH
  tunnels to the RTX hosts, and keeps an SQLite cache on the Mac. GDINO goes to gx10
  alone. gx10 is reached through `:18082`; the Mac cache starts empty.
- Source: owner messages of 2026-09-29T08:17:32+0300 and the owner answers of
  2026-09-29T10:02:42+0300 (options A, proxy-run SSH tunnels, GDINO on gx10 alone,
  gx10 through 18082 with an empty cache).
- Files: `docs/owner-messages.md` (append), `../proxies/**` (new project),
  `<workspace>/deploy/mbp2023/model-proxy.md` (new), my own row in the table
  "Deployments" of `<workspace>/deploy/README.md`, my own entry in
  `<workspace>/deploy/ChangeLog.md`, and my own rows (18092, 18191-18199) in
  `/Users/ashmelev/Admin/mbp2023/PORTS_USED.md`. No other lab file.
- State: done, not committed; waiting: the owner decides the commit and the next steps
  (an RTX host, a component row in `../README.md`). 63 unit tests pass. The live tests
  through scratch proxies on ports 18093 and 18094 passed; both proxies stopped. No
  proxy runs on port 18092.
- Updated: 2026-09-29T10:36:00+0300
- Agreements: `codex-submission-01` lists `../README.md` (done; git shows no pending
  change). I do not change it; I ask the owner about a component row for `proxies/`.

## drink-atlas-workspace-b3 [45a3fc]

- Task: a read-only side-by-side comparison of the matcher pipeline and the best lab pipeline.
- Source: owner message of 2026-09-29T08:04:13+0300.
- Task 2: commit the pending `../matcher/` changes as one scope commit. The commit uses a
  private git index. It changes no file in the working tree.
- Source 2: owner message of 2026-09-29T10:41:37+0300.
- Files: `docs/owner-messages.md` (append), `ResearchLog.md` (one new entry at the top, tasks
  3 and 4), and this section of `ACTIVE_WORK.md`.
- State: done, not committed. Task 4: the answer and a follow-up in my `ResearchLog.md`
  entry. Task 3: the answer and a `ResearchLog.md` entry. Task 2 is commit `0657f46` (8 matcher files of b6 and the Codex entry 3 of
  `../matcher/docs/KNOWN_ISSUES.md`; 124 matcher tests pass on the tree alone). The empty
  untracked `../matcher/1.txt` stays out. b6 got a message. My own appends in
  `docs/owner-messages.md` are not committed.
- Agreements: b6 confirmed at 10:44:40 that it recorded `0657f46` in its section. It plans no
  more matcher edits for task 8. A later matcher change is a new commit on top of `0657f46`.
  c4 lists its own hunks in `ResearchLog.md`. At 11:32:02 I told c4 about my entry at the
  top of that file, so that c4 reads the file again before it writes.
- Task 3: explain how the lab step `segment` with `target: package` selects one package
  when a photo shows several bottles, and whether a hand detection takes part. Read-only.
- Source 3: owner message of 2026-09-29T11:28:17+0300.
- Task 4: assess the risk of the hand-aware selection (`main_scene.py`, matcher
  `hand_selection`): the photos that it breaks, and the SAM3 time with the text `hand`.
  Read-only.
- Source 4: owner message of 2026-09-29T11:35:25+0300.
- Updated: 2026-09-29T11:37:54+0300

## drink-atlas-workspace-c4 [e3b3f5]

- Task: the alpha-channel and background test of the SigLIP 2 models of the gx10 gateway
  (the test of the ResearchLog entry of 2026-09-25 was made with `dinov3-vitb16` alone),
  with a report.
- Source: owner message of 2026-09-29T11:14:13+0300.
- Files: `docs/owner-messages.md` (append), `scripts/alpha_background_probe.py` (new),
  `docs/reports/siglip2-alpha-background-2026-09-29.md` (new) and its artifact folder,
  my own hunks in `ResearchLog.md` (a new entry, and one pointer line in the entry of
  2026-09-25) and `ChangeLog.md`. No change of lab code or config.yaml.
- Agreements: this is the same conversation as the section `drink-atlas-workspace-b6
  [088a3a]` (resumed in a new process). That section keeps task 8 (plan 82); its build of
  `...-p512-rot5` runs (pid 63208). I change no file of that section.
- Task 2: continue task 8 of the section b6 (plan 82): the rot5 build ended at 11:41 (0 failures); the runs of the three `siglip2-p512-rot5-*` pipelines on `my` (new run directories in `runs/`) and the rot5 part of `docs/reports/rotation-index-p512-2026-09-29.md`.
- Agreements 2: the section b6 (the old process of this conversation) edited the rot5 report at 11:44; c4 sent b6 a message at 11:45: c4 runs the three rot5 runs and adds only their section to that report.
- State: task 1 done, not committed (report `docs/reports/siglip2-alpha-background-2026-09-29.md`). Task 2 dropped at 11:46: b6 started the same three rot5 runs at 11:43:38; c4 stopped its own duplicate chain and removed its partial run directory `runs/2026-09-29T084311Z-lab-siglip2-p512-rot5-as-is-my-plan82`. b6 keeps the rot5 runs and the report section. b6 also stopped its chain at 11:45:48 (messages crossed), removed its partial directory, and restarted one chain at 11:47 with its own logs `work/rotation-index/run-<pipeline>-b6.out`; c4 agreed to start none.
- Updated: 2026-09-29T11:46:57+0300

## drink-atlas-workspace-c1 [b51d69]

- Task: add the entry `Copy Image` to the right-click menu of a photo on `/testset`. The
  entry copies the picture to the clipboard. The code follows `copyImage` of
  `scripts/review_server.py`.
- Source: owner message of 2026-09-29T12:15:11+0300.
- Files: `docs/owner-messages.md` (append), `pipeline/pages/testset.html` (separate hunks:
  the helper `photoAsPng`, the helper `copyImage`, one menu line, one click branch), and
  my own hunks in `ChangeLog.md` and `SMOKE_TESTS.md`.
- State: done, not committed. Waiting: the owner decides the commit. No restart of 8168:
  the page is read from disk. Headless Chromium on 8168: `copied`, a 721 x 1280 PNG, no
  page errors. Docs: `ChangeLog.md`, `SMOKE_TESTS.md` NM9-NM10.
- Updated: 2026-09-29T12:17:09+0300
- Agreements: the owner asked for this change directly. The sections that list
  `pipeline/pages/testset.html` (ab, b4, 41, 96, a4, `/root`, `root`) are stale or done,
  and the file is clean in git. I change only my separate hunks.
- Task 2: an advanced filter `Origin` on `/testset` that shows the wines added by hand
  (manual wines: the slug starts with `__`; `__null__` and `__drawer__` are not wines).
- Source for task 2: owner message of 2026-09-29T12:48:14+0300.
- Files for task 2: `docs/owner-messages.md` (append), `pipeline/pages/testset.html`
  (separate hunks: one select in `#more`, the `#more-btn` title, `FILTER_AXES`,
  `CATALOG_SCOPE_FILTERS`, one `matchAxis` case, the `#more-n` count, `VIEW_PARAMS`), and my
  own hunks in `ChangeLog.md` and `SMOKE_TESTS.md`.
- State for task 2: done, not committed. Waiting: the owner decides the commit. No
  restart of 8168. Headless Chromium on 8168: 3 wines added by hand, no page errors.
  Docs: `ChangeLog.md`, `SMOKE_TESTS.md` TP24, TP36, TP42-TP43.
- Updated for task 2: 2026-09-29T12:53:55+0300
- Task 3: read-only check of the F1@1 and F1@5 calculation for test photos with no match
  in the dataset, and of the effect of `Disable` on the photos of a manual wine.
- Source for task 3: owner messages of 2026-09-29T19:04:22+0300, 19:10:09+0300,
  19:16:27+0300, and 19:22:30+0300.
- Files for task 3: `docs/owner-messages.md` (append), `pipeline/benchmark.py`
  (`build_queries` and the module docstring), `tests/test_benchmark.py` (new tests),
  `docs/plans/87_benchmark-dataset-rule.md` (new), `scripts/rescore_runs.py` (new),
  the files `metrics.json` and `summary.md` of the saved lab runs in `runs/` (the old
  files are kept as `*.before-dataset-rule.*`), and my own entries in `ChangeLog.md`,
  `ResearchLog.md`, and `COMMANDS.md` (a new last section). With the owner answer of
  2026-09-29T19:38:55+0300: `work/fixed512-rot5/compare.py` (pair by `image_path`) and
  the count text of `work/fixed512-rot5/finalize_report.py` (files of task 7 of
  `codex-preset-segment-check`; a Codex session gets no message).
- State for task 3: done, not committed. Waiting: the owner decides the commit. 165 saved
  runs re-scored (0 mismatches). The rot5 trial scripts pair by `image_path`; a scratch
  test paired 2,231 photos. The owner allowed the edits of `benchmark.py` and
  `test_benchmark.py` (listed by the stale sections f4 and b4) and the re-score at
  2026-09-29T19:25:36+0300, and the patch of the trial scripts at 19:38:55.
- Task 3b: a manual wine in the state `Active` counts as any other `Active` wine
  (owner message of 2026-09-29T19:42:59+0300). Same files as task 3. State: done, not
  committed. 158 runs re-scored; the 7 runs of `test-1` got their old files back.
- Updated for task 3: 2026-09-29T19:47:37+0300

## drink-atlas-workspace-d7 [685702]

- Task: find why `Save` of the `Add wine` dialog on `/dataset` takes a long time, and
  propose fixes. Done: a cold start of `siglip2-so400m-patch16-512` on gx10 (37.3 s).
- Source: owner message of 2026-09-29T12:28:00+0300.
- Task 2: plan 84, the index build of a new wine in the background; the card tag
  `indexing…`, `indexed`, `not indexed`.
- Source 2: owner answer of 2026-09-29T12:41:02+0300.
- Files: `docs/owner-messages.md` (append), my own entry in `ResearchLog.md`,
  `docs/plans/84_background-new-wine-index.md` (new). After the approval of plan 84:
  `pipeline/new_wine_jobs.py` (new), `tests/test_new_wine_jobs.py` (new), and separate
  hunks in `pipeline/new_wine_workflow.py`, `pipeline/lab_server.py`,
  `pipeline/pages/dataset.html`, `tests/test_new_wine_workflow.py`,
  `docs/lab-openapi.yaml`, `docs/plans/78_incremental-new-wine-index.md`,
  `tests/test_manual_wines.py`, `tests/test_lab_openapi.py`, and my own hunks in
  `README.md`, `SMOKE_TESTS.md`, `ChangeLog.md`. A restart of 8168. The live trial
  writes `data/catalog/catalog.sqlite3`, one image, and the embedding directory.
- State: done, not committed. Waiting: the owner decides the commit. 8168 restarted at
  12:59 (PID 24435). Live trial wine `__web-bg-index-smoke-20260929` is `Disabled`.
- Updated: 2026-09-29T13:04:00+0300
- Agreements: the owner allowed at 12:45:37 separate hunks in the files of the section
  `/root` (a Codex session; no message can reach it). The `/root` lines stay
  byte-identical. The owner approved the live trial `__web-bg-index-smoke-20260929`.
  At 2026-09-29T12:49:53+0300 the owner allowed edits of the `/root` lines that state the replaced plan 78
  behavior: the busy text in `dataset.html` and its assertion in
  `tests/test_new_wine_workflow.py`, `test_a_server_with_a_config_uses_the_index_workflow`
  in `tests/test_manual_wines.py`, the `createWine` summary in `docs/lab-openapi.yaml`,
  `README.md` lines 314-315, `SMOKE_TESTS.md` AW17 and AW19, and 2 new lines in the
  route list of `tests/test_lab_openapi.py`.

## codex-belbek-photo-01

- Task: find a clean high-resolution photo of Belbek Petit Verdot and store it as the wine patch.
- Source: owner messages recorded at 2026-09-29T15:28:23+0300.
- Files: `docs/owner-messages.md` (new entries only), `work/belbek-photo/**` (new), one new entry in `ChangeLog.md`; the API writes the patch and cuts for `belbek-belbek-pti-verdo-krasnoe-suhoe-121` in `data/catalog/`.
- State: done, not committed. The live patch is 999 x 3460 pixels. Source bytes and the package and label derivatives are verified. No API warning. No server restart.
- Updated: 2026-09-29T15:31:40+0300

## codex-wine-identity-check

- Task: compare the two attached bottle photos and answer whether they show the same wine.
- Source: owner message of 2026-09-29T16:17:55+0300.
- Files: `docs/owner-messages.md` (append only).
- State: done, not committed. The bottles share a producer and grape blend, but differ
  in named line and vintage, so they are not the same exact wine/SKU.
- Updated: 2026-09-29T16:19:00+0300
- Task 2: check whether the second photographed wine is present in the local dataset.
- Source: owner message of 2026-09-29T16:21:34+0300.
- Files: `docs/owner-messages.md` (append only); dataset files and databases stay read-only.
- State: done, not committed. The exact 2024 `Мерло & Каберне Совиньон` is absent;
  the catalog contains only the related `Каберне Совиньон & Мерло 1890` entry.
- Updated: 2026-09-29T16:24:30+0300
- Task 3: create a separate dataset entry for the photographed `Усадьба Перовских`
  `Мерло & Каберне Совиньон 2024`; find and use a clean frontal product image from
  the Internet, not the supplied shop photo.
- Source: owner messages of 2026-09-29T16:34:50+0300 and 16:35:53+0300.
- Files: `docs/owner-messages.md` (append only), `data/catalog/catalog.sqlite3`, and
  API-created files under `data/catalog/images/**` and `data/catalog/cuts/**`;
  `data/catalog/embeddings/gx10-siglip2-so400m-patch16-512/**` (incremental index),
  `work/perovskih-merlo-cabernet-2024/**` (downloaded candidate and evidence).
- State: done, not committed. Created `__merlo-kaberne-sovinon-2024` as Active with
  the clean 479×1500 official winery image. The package and label cuts are present;
  both new items are current in `gx10-siglip2-so400m-patch16-512`.
- Updated: 2026-09-29T16:42:30+0300
- Task 4: answer how to start the workbench lab server.
- Source: owner message of 2026-09-29T16:46:16+0300.
- Files: `docs/owner-messages.md` (append only); project files stay read-only.
- State: done, not committed. Confirmed the foreground and no-browser commands from
  `COMMANDS.md`; no server process was started by this task.
- Updated: 2026-09-29T16:47:00+0300

## codex-preset-segment-check

- Task: check whether the four barcode rerank crop presets include segmentation.
- Source: owner message recorded at 2026-09-29T17:28:00+0300.
- Files: `docs/owner-messages.md` (this message append only), this section of `ACTIVE_WORK.md`.
- State: done, not committed. All four presets include package segmentation. The
  crop variants retain the crop background; crop-label also segments the label and
  removes its background. No code or configuration change.
- Updated: 2026-09-29T17:28:18+0300

- Task 2: compare barcode-siglip2-p512-crop, barcode-siglip2-p512-crop-seg, and barcode-rerank-siglip2-p512-crop.
- Source 2: owner message recorded at 2026-09-29T17:31:41+0300.
- Files for task 2: `docs/owner-messages.md` (this message append only), this section.
- State for task 2: done, not committed. Compared the package crop, mask-based
  background removal, and conditional cluster VLM rerank. The same barcode lookup
  and SigLIP2 NaFlex p512 index apply to all three. No code change.
- Updated for task 2: 2026-09-29T17:31:53+0300

- Task 3: rename pipeline presets. Remove `-as-is`; replace `-crop-seg` with `-seg`; keep `-crop`.
- Source 3: owner message recorded at 2026-09-29T17:38:42+0300.
- Files for task 3: `docs/owner-messages.md` (this message append only), this section. `config.yaml` (preset names and related comments only), `tests/test_pipelines.py` (the renamed preset reference), `scripts/rotation_index_eval.py` (resolve current config names), `COMMANDS.md`, `README.md`, `SMOKE_TESTS.md` (current names only), and one new entry in `ChangeLog.md`.
- State for task 3: done, not committed. Renamed 36 presets; 75 focused tests pass.
  All 77 entries load. Parsed settings are unchanged except for names. Both live
  selector APIs return the new names. No restart. Saved run records stay unchanged.
- Scope for task 3: the owner directly requested the preset rename. Existing sections list these shared files; only the requested names and their references change. Other sessions' implementation hunks stay unchanged. Saved reports, run records, and other sessions' sections stay unchanged.
- Updated for task 3: 2026-09-29T17:42:12+0300

- Task 4: audit all configuration names against their effective image-processing steps and correct mismatches.
- Source 4: owner message recorded at 2026-09-29T17:42:45+0300.
- Files for task 4: `docs/owner-messages.md` (this message append only), this section. `config.yaml` (three pipeline names only), `tests/test_pipelines.py` (Android pipeline references), `README.md` and `SMOKE_TESTS.md` (current pipeline names), and one entry in `ChangeLog.md`.
- State for task 4: done, not committed. Corrected the two Android pipeline names to `-dis-seg` and `-sam3-seg`, and the two-view name to `-crop-label-seg`. All 77 names pass the semantic audit; 75 tests pass. Both live selector APIs show the corrected names. Embedding index names and all processing settings stay unchanged. No restart.
- Updated for task 4: 2026-09-29T17:45:24+0300

- Task 5: confirm whether a preset combines barcode, rerank, and package segmentation on white.
- Source 5: owner message recorded at 2026-09-29T17:46:31+0300.
- Files for task 5: `docs/owner-messages.md` (this message append only), this section.
- State for task 5: done, not committed. No preset combines barcode, rerank, and package background removal. The crop-label-seg preset removes the label background only. No configuration change.
- Updated for task 5: 2026-09-29T17:46:40+0300

- Task 6: add barcode-rerank segmentation presets for fixed 512, NaFlex p512, and NaFlex p1024; run each on `my`.
- Source 6: owner message recorded at 2026-09-29T17:48:09+0300.
- Files for task 6: `docs/owner-messages.md` (this message append only), this section, `config.yaml` (three new presets), `tests/test_pipeline_workers.py` (preset references), `README.md`, `COMMANDS.md`, `SMOKE_TESTS.md`, one new entry in `ChangeLog.md`, `work/barcode-rerank-seg/**`, new run directories in `runs/`, and one row in `/Users/ashmelev/Admin/GPU_TASKS.md`. Standard run jobs may update their embedding indexes, model caches, and dependency artifacts.
- State for task 6: done, not committed. All three presets are live. Each final run completed 2,232 photos with zero query and trace-step errors. Initial attempts and malformed SAM3 cache records are preserved in `work/barcode-rerank-seg/`. One package response was refreshed; three package and two label responses were quarantined. No inference code change or server restart. All 75 focused tests pass.
- Updated for task 6: 2026-09-29T18:09:42+0300

- Task 6 results: fixed-512 R@1 84.69%, R@5 97.64%; p512 R@1 82.70%, R@5 96.43%; p1024 R@1 83.79%, R@5 97.04%. Same query manifests; caches enabled. Summary: `work/barcode-rerank-seg/summary.md` and `results.json`.


- Task 7: add `barcode-rerank-siglip2-512-rot5-seg`, build fixed-512 reference embeddings at 5-degree steps, and evaluate on `my` against the completed fixed-512 baseline.
- Source 7: two owner messages recorded at 2026-09-29T18:17:06+0300; the first turn was interrupted before work.
- Files for task 7: `docs/owner-messages.md` (these two message appends only), this section. `config.yaml` (one new embedding and pipeline), `tests/test_pipeline_workers.py` (new preset), `README.md`, `COMMANDS.md`, `SMOKE_TESTS.md`, one new entry in `ChangeLog.md`, `work/fixed512-rot5/**`, `docs/reports/2026-09-29_fixed512-rot5.md`, `data/catalog/embeddings/gx10-siglip2-so400m-patch16-512-rot5/**`, new run directories, relevant model-cache records, and one row in `/Users/ashmelev/Admin/GPU_TASKS.md`.
- State for task 7: active. Index build PID 87306 (6 workers) started at 18:22:58. The coordinator in `work/fixed512-rot5/finish_trial.py` waits for it, validates the index, builds clusters and rules, and runs all of `my`. The ledger is `work/fixed512-rot5/trial.json`. All 87 focused tests pass. No inference code change or restart.
- Updated for task 7: 2026-09-29T18:26:54+0300

## codex-catalog-metrics-explanation

- Task: explain recognition metrics for test wines absent from the catalogue.
- Source: owner message of 2026-09-29T18:06:29+0300.
- Files: this section and `docs/owner-messages.md` (this message append only).
- State: done, not committed. Read the local scorer and supplied evaluation rules. No code or data change.
- Updated: 2026-09-29T18:06:29+0300

- Follow-up: explain R@1, R@5, and F1 formulas for the 60 positive photos.
- Follow-up state: done, not committed. No code or data change.
- Follow-up updated: 2026-09-29T18:07:52+0300

## codex-side-services-01

- Task: launch Drink Atlas Core, Web UI, and Matcher, then verify their health.
- Source: owner message recorded at 2026-09-29T18:11:00+0300.
- Files: `docs/owner-messages.md` (append) and this section. Runtime logs and PID files
  MAY be written only in each service's existing runtime or work directory.
- State: done, not committed. Started the project-owned PostgreSQL cluster and all
  three documented local launchers. Core is healthy on `127.0.0.1:8156`, Web UI
  serves `/products` and `/image-search` on `127.0.0.1:8157`, and Matcher is healthy
  on its generated port `127.0.0.1:54402` with the active SigLIP2 index.
- Updated: 2026-09-29T18:14:00+0300

- Follow-up task: start the Drink Atlas enrichment service and documented worker pools,
  then verify their health while preserving the running Core, Web UI, and Matcher.
- Follow-up source: owner message recorded at 2026-09-29T18:17:41+0300.
- Follow-up files: `docs/owner-messages.md` (append) and this section. Runtime files
  MAY be written only in the enrichment project's existing runtime directories.
- Follow-up state: done, not committed. The catalog coordinator is healthy on
  `127.0.0.1:50175`; two general workers and eight frame-only workers are online.
  The detached frame supervisor has PID 80131. The saved queue remains `running`,
  with 40,180 of 40,180 tasks complete and no current worker task.
- Follow-up updated: 2026-09-29T18:21:12+0300

## drink-atlas-workspace-ad [139787]

- Task: add the pipeline `barcode-rerank-siglip2-p512-rot5-seg` (NaFlex p512, rot5 index),
  add an unrotated `label` view to `gx10-siglip2-so400m-patch16-naflex-p512-rot5`, build
  its label vectors, clusters, and label rules, and run the pipeline on `my` after the
  fixed-512 rot5 build of `codex-preset-segment-check` ends.
- Source: owner message recorded at 2026-09-29T19:57:26+0300; owner answers recorded at
  2026-09-29T20:05:38+0300 ("Add label view", "Run on my after build").
- Files: `docs/owner-messages.md` (append), this section, `config.yaml` (separate hunks:
  the views of the entry `gx10-siglip2-so400m-patch16-naflex-p512-rot5`, the anchor
  `views_full_rotated` moves to the rot10 entry, one new pipeline after
  `barcode-rerank-siglip2-p512-seg`), `tests/test_pipeline_workers.py` (one name in the
  four-worker set), my own hunks in `README.md`, `COMMANDS.md`, `SMOKE_TESTS.md`,
  `ChangeLog.md`, runtime output in
  `data/catalog/embeddings/gx10-siglip2-so400m-patch16-naflex-p512-rot5/`, a new run
  directory in `runs/`, `work/p512-rot5-rerank/**` (new), one row in
  `/Users/ashmelev/Admin/GPU_TASKS.md`.
- Agreements: the rot5 entry is a plan 82 entry (b6). The owner chose this change at
  20:05:38 with that fact in the question; that answer is the permission. I do not change
  the fixed-512 entries or files of `codex-preset-segment-check`.
- State: active.
- Updated: 2026-09-29T20:07:31+0300
