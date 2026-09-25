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

- Task: the rules of this file (rules 13 to 21 of `AGENTS.md`) and this file; not
  committed yet.
- Source: owner message of 2026-09-25 ("add to AGENTS.md … synchronize current work").
- Files: `AGENTS.md` (rules 13 to 21), `ACTIVE_WORK.md` (this section and the head),
  `ChangeLog.md` (the entry of `ACTIVE_WORK.md`), `docs/owner-messages.md` (appended).
- State: waiting: the owner commits the rules.
- Updated: 2026-09-25T00:45:56+0300
- Agreements: none. The agreement with drink-atlas-workspace-8b ended on 2026-09-25
  about 00:46, when it reported that its change of `seed_patched.py` was done.

## drink-atlas-workspace-9a

- Task: plan 10: the Embeddings page and the embedding build.
- Source: owner messages of 2026-09-25 from 00:22:10 to 01:01:05;
  `docs/plans/10_embeddings-page.md`.
- Files: `docs/plans/10_embeddings-page.md`, `QUESTIONS.md`, `pipeline/embeddings.py`,
  `pipeline/build_embeddings.py`, `pipeline/embedding_routes.py`,
  `pipeline/pages/embedding.html`, `tests/test_embeddings.py`,
  `tests/test_build_embeddings.py`, `tests/test_embedding_routes.py`, `tests/embedding_lab.py`,
  `requirements-local.txt`, `config.yaml` (keys `embedding_python`, `embeddings`),
  `data/embeddings/`, `~/.venvs/svoe-vino-lab`. Entries appended to
  `docs/owner-messages.md` and `ResearchLog.md`. Entries (new sections) in `README.md`,
  `COMMANDS.md`, `ChangeLog.md`, `SMOKE_TESTS.md`. Later, in the order agreed with a2:
  a small hook in `pipeline/lab_server.py`.
- State: waiting: the new files, the config, the tests (44, OK), and the first real build
  are done. The hook in `pipeline/lab_server.py` waits for the commit of plan 09 by
  drink-atlas-workspace-8b and then for drink-atlas-workspace-a2. The label cut (in
  `pipeline/derive.py`) and the type buttons (in `pipeline/pages/dataset.html`) wait
  for the same commit. Nothing of this session is committed.
- Updated: 2026-09-25T01:27:00+0300
- Agreements: with drink-atlas-workspace-8b (2026-09-25): no change of
  `pipeline/lab_server.py`, `pipeline/derive.py`, `pipeline/pages/dataset.html` before
  the commit of plan 09. After the commit 8b hands `pipeline/derive.py` and
  `tests/test_derive.py` to this session for the label cut. With
  drink-atlas-workspace-a2 (2026-09-25): a2 changes `pipeline/lab_server.py` first,
  after the plan 09 commit, and sends a message after its commit; this session then adds
  its hook. When this session is ready first, it asks a2. a2 keeps schema 008; this
  session takes the next free numbers and sends a2 a message before it adds a schema
  file.

## drink-atlas-workspace-8b

- Task: plan 09: the tables `image` and `image_derivative` (schema 007), the processing
  of each image at import (crop, SAM3 seg), badges on the Dataset page. Before it: the
  image seed, the card images, the size sort, and the slug link (plan 08), not committed.
- Source: `docs/plans/08_seed-images.md`, `docs/plans/09_image-processing.md`; owner
  messages of 2026-09-24 and 2026-09-25.
- Files: `pipeline/derive.py`, `pipeline/imagestore.py`, `pipeline/schema/006_*.sql`,
  `pipeline/schema/007_*.sql`, `pipeline/seed_images.py`, `pipeline/seed_patched.py`,
  `pipeline/labdb.py`, `pipeline/lab_server.py`, `pipeline/pages/dataset.html`,
  `tests/test_derive.py`, `tests/test_seed_images.py`, `tests/test_seed_patched.py`,
  `tests/test_lab_server.py`, `tests/test_labdb.py`, `docs/plans/07_*.md` (step 5),
  `docs/plans/08_*.md`, `docs/plans/09_*.md`, `docs/decisions/01_*.md`, `.gitignore`.
  Entries in `README.md`, `SMOKE_TESTS.md`, `ChangeLog.md`, `ResearchLog.md`,
  `docs/owner-messages.md`. The data `data/lab.sqlite3` and `data/images/`. `AGENTS.md`:
  the new section "The lab server" alone (owner message of 2026-09-25).
- State: waiting: the owner chooses option A or B for the SAM3 noun `box` (the new run
  cut out the crate of `ona-skazala-da` and the tube of `fanagoriya-tochka-saperavi-...`).
  The commit waits for the owner.
- Updated: 2026-09-25T01:06:33+0300
- Agreements: with drink-atlas-workspace-20: the change of `pipeline/seed_patched.py`
  and `tests/test_seed_patched.py` is done and reported (2026-09-25). With
  drink-atlas-workspace-a2: it changes `pipeline/lab_server.py`,
  `pipeline/pages/dataset.html`, `tests/test_lab_server.py`, `tests/test_labdb.py`, and
  `data/lab.sqlite3` after the commit of plan 09; this session tells it when. This
  session changes those four files no more; option B writes rows of `data/lab.sqlite3`
  alone (2026-09-25). With drink-atlas-workspace-9a: it waits for the commit of plan 09
  for `pipeline/lab_server.py`, `pipeline/pages/dataset.html`, `pipeline/derive.py`, and
  `tests/test_derive.py`; after the commit this session hands `derive.py` and
  `test_derive.py` over to it. 9a and a2 agree the order and the schema numbers
  between them: both planned `008` (2026-09-25).

## drink-atlas-workspace-a2

- Task: plan 11: GTIN, barcode, and QR URL in the database (table `wine_code`); one wine
  MAY have more than one value, and one value MAY belong to more than one wine.
- Source: owner messages of 2026-09-25T00:52:48+0300 and 2026-09-25T00:58:25+0300;
  `docs/plans/11_wine-codes.md`.
- Files: `docs/plans/11_wine-codes.md`, entries appended to `docs/owner-messages.md`.
  After the approval of plan 11: `pipeline/schema/008_wine_code.sql`,
  `pipeline/codes.py`, `pipeline/seed_codes.py`, `tests/test_seed_codes.py`. After the
  commit of plan 09 by drink-atlas-workspace-8b: `pipeline/lab_server.py`,
  `pipeline/pages/dataset.html`, `tests/test_lab_server.py`, `tests/test_labdb.py`,
  `data/lab.sqlite3`. Entries in `COMMANDS.md`, `README.md`, `docs/API.md`,
  `docs/openapi.yaml`, `docs/plans/07_*.md` (rule 5), `SMOKE_TESTS.md`, `ChangeLog.md`.
- State: waiting: the owner reviews plan 11 and answers O1 (the stored form of a GTIN).
  The file `008_wine_code.sql` stays out of `pipeline/schema/` until the commit of plan
  09, because a new schema file makes the running server on 8168 answer HTTP 503.
- Updated: 2026-09-25T01:03:46+0300
- Agreements: with drink-atlas-workspace-8b (2026-09-25): this session changes
  `pipeline/lab_server.py`, `pipeline/pages/dataset.html`, `tests/test_lab_server.py`,
  `tests/test_labdb.py`, and `data/lab.sqlite3` after the commit of plan 09. The commit
  waits for the owner. 8b plans no more changes to the four code files. 8b MAY run
  `seed_images.py` once more on `data/lab.sqlite3` (schema version 7). 8b sends a message
  after its commit.
  With drink-atlas-workspace-9a (2026-09-25): this session changes
  `pipeline/lab_server.py` first, after the commit of plan 09, and sends 9a a message after
  its commit of plan 11. 9a then adds its `/embedding` hook. If 9a is ready first, it asks,
  and this session expects to agree. Schema: this session keeps `008`. 9a takes the next
  free numbers and sends a message before it adds a schema file.
