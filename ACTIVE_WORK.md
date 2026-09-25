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
- Updated: 2026-09-25T06:53:37+0300
- Agreements: all other files of plans 08 and 09 are released (2026-09-25): to
  drink-atlas-workspace-a2, drink-atlas-workspace-9a, and drink-atlas-workspace-7e.
  After the A/B decision, this session hands `pipeline/derive.py` and
  `tests/test_derive.py` over to drink-atlas-workspace-9a.

## drink-atlas-workspace-a2

- Task: plan 11: GTIN, barcode, and QR URL in the database (table `wine_code`); one wine
  MAY have more than one value, and one value MAY belong to more than one wine.
- Source: owner messages of 2026-09-25T00:52:48+0300 and 2026-09-25T00:58:25+0300;
  `docs/plans/11_wine-codes.md`.
- Files: `docs/plans/11_wine-codes.md`, entries appended to `docs/owner-messages.md`.
  After the approval of plan 11: `pipeline/schema/NNN_wine_code.sql` (number fixed at entry),
  `pipeline/codes.py`, `pipeline/seed_codes.py`, `tests/test_seed_codes.py`. After the
  commit of plan 09 by drink-atlas-workspace-8b: `pipeline/lab_server.py`,
  `pipeline/pages/dataset.html`, `tests/test_lab_server.py`, `tests/test_labdb.py`,
  `data/lab.sqlite3`. Entries in `COMMANDS.md`, `README.md`, `docs/API.md`,
  `docs/openapi.yaml`, `docs/plans/07_*.md` (rule 5), `SMOKE_TESTS.md`, `ChangeLog.md`.
- State: waiting: the owner reviews plan 11, answers O1 (the stored form of a GTIN), and
  chooses the order of the sessions that change `pipeline/lab_server.py`. Plan 09 is
  committed in `a8e113a`, so the wait for drink-atlas-workspace-8b is over.
- Updated: 2026-09-25T06:53:59+0300
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
- Source: owner messages of 2026-09-25T00:03:25+0300 and 2026-09-25T00:06:15+0300 (option 1).
- Files: `ResearchLog.md` (one entry at the top). Planned: `pipeline/labdb.py`, `pipeline/imagestore.py`,
  `pipeline/derive.py`, `pipeline/seed_images.py`, `pipeline/seed_patched.py`,
  `pipeline/lab_server.py`, `pipeline/embeddings.py`, `tests/embedding_lab.py`, a new `pipeline/schema/NNN_*.sql`,
  their tests, plans 08 and 09, `data/images/`, `data/lab.sqlite3`. Entry appended to
  `docs/owner-messages.md`.
- State: waiting: the other sections list the planned files. The owner chooses the order.
  drink-atlas-workspace-7e changes `pipeline/lab_server.py` now by the owner's order
  (notice of 2026-09-25 about 06:53); this session waits for its commit.
- Updated: 2026-09-25T07:09:40+0300
- Agreements: with drink-atlas-workspace-a2 (2026-09-25): whoever is ready first tells
  the other before the first change to `pipeline/lab_server.py`. Each session commits
  before the next one starts on that file. A schema number is fixed only when a file
  enters `pipeline/schema/`. The owner chooses the order.
  With drink-atlas-workspace-20 (2026-09-25): the schema file of plan 12 enters
  `pipeline/schema/` after the file of this session (owner message 07:09:07). The flat
  store drops `image.folder` with `ALTER TABLE … DROP COLUMN`, not with a rebuild. This
  session sends 20 a message when `pipeline/imagestore.py` is committed. Planned
  interface: `path_of(db_path, sha256, extension)` instead of `folder_of`.

## drink-atlas-workspace-7e

- Task: enable the Embeddings page on the lab server (the hook of plan 10), and the page
  order Dataset, Embeddings, then the other pages.
- Source: owner messages of 2026-09-25T06:49:54+0300, 06:50:29 and 06:52:00 (the owner
  gave the hook of drink-atlas-workspace-9a to this session).
- Files: `pipeline/lab_server.py` (the hook, `NAV`, `DISABLED_PAGES`, the docstring),
  `pipeline/pages/dataset.html` and `pipeline/pages/embedding.html` (the navigation
  alone), `tests/test_lab_server.py`. Entries in `ChangeLog.md`, `SMOKE_TESTS.md`,
  `README.md`, `docs/owner-messages.md`. A restart of the server on port 8168.
- State: active
- Updated: 2026-09-25T06:53:00+0300
- Agreements: this session sends 9a, a2, and 8b a message before the first change, and
  a message when it is done.
