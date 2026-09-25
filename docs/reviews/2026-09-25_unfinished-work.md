# Review of the unfinished work, 2026-09-25

Date: 2026-09-25, about 12:25 local time.
Author: drink-atlas-workspace-7b, with five read-only reviewers.
Source: the owner messages of 2026-09-25T12:01:18+0300 ("what sessions have unfinished
work?", "review them and implement what is missing").
State of the tree: nothing is committed after `b5ba133` (07:32). `data/lab.sqlite3` is at
schema version 14. The full suite runs 334 tests; only the 5 load errors of the review-tool
tests fail.

Severity words: **bug**, **missing** (a feature or a rule), **test** (a missing test),
**doc** (a missing or stale document).

## 1. Findings by session

### drink-atlas-workspace-7b (plans 14 and 16, preview, Embeddings)

1. **bug, high.** `image_derivative` holds one processed file for each original, but the
   kind (package cut or label cut) belongs to each row. One file that is a patch (or a
   `main`, or a full type) and also a label type gets one shared cut. The last writer wins.
   The Embeddings page reads the same row as the package cut. Reproduced.
2. **bug, high.** `alternatives.store_alternative` writes the size of the SAM3 copy into
   `image` (`width`, `height` are overwritten). A photo with a long side above 1,536 px gets
   a wrong size, and `cut_nothing` then fails. Reproduced (3000 × 4000 became 1152 × 1536).
3. **bug, medium.** A change between full and label keeps the old cut when SAM3 is down or
   finds no label. The card shows the cut of the other kind; the warning text is wrong.
4. **bug, medium.** A patch file chosen while the previous patch of the same wine is
   processing is lost with no message.
5. **missing, medium.** No way to process a photo again: the same file again changes
   nothing, and a front/back change does no processing, also with no processed file.
   Plan 14 rule 6 promises a later run that no tool does.
6. **missing, medium.** `seed_patched.py` still overrides the editor for the 15 wines of
   the patch folder: a folder file replaces an editor patch, and a seed run undoes an editor
   `Remove`. This conflicts with "the database is the truth".
7. **risk, medium.** `alternatives.py` has its own `insert_image` with the column `folder`
   and uses `imagestore.folder_of`; the flat image store drops `image.folder`.
8. **bug, low.** `Cancel` during alternative uploads also drops the queued uploads.
9. **bug, low.** `×` stays enabled while a type change runs (the server answers 409).
10. **bug, low.** An unexpected exception in the patch and alternative routes closes the
    connection with no HTTP answer. Uploads have no pixel limit (a 27 KB PNG of
    15000 × 15000 px was processed).
11. **bug, low** (with drink-atlas-workspace-0b). `open raw image` in the patch preview opens
    the processed file, not the original.
12. **test.** No fake SAM3 with a scale below 1; no test of a file shared by a patch and an
    alternative; no test of `set_type` with SAM3 down or with no label; no route test of
    413 and 503; no migration test of a version 9 database with rows through 010 and 012;
    missing `detect` cases.
13. **doc.** Stale: README (types `front`, `back`, "main_patched replaces main" for the
    card), SMOKE_TESTS P5, AL13/AL14 twice, PE18, plan 07 rule 5, plan 10 (old names),
    plan 16 (status, goal 3, rule 6, the list order 1-3-2), plan 14 (status, `Apply` for a
    new patch), the `lab_server.py` docstrings, one comment in `dataset.html`.

No finding: the write lock during SAM3, the 409 guard, the seed delete rule, the preview
layout, the `Disabled` filter, the Embeddings page, the type names and the nouns.

### drink-atlas-workspace-a2 (plan 11; the session is not running)

1. **bug, latent.** The review tool (`scripts/review_server.py`) can no longer add a normal
   barcode: the shared page refuses every EAN-13 as "a GTIN", and the GTIN editor posts to a
   route that the review tool does not have. ChangeLog and plan 11 say "the review tool is
   not changed".
2. **bug, low.** `codes.clean_qr_url` drops the brackets of an IPv6 host.
3. **missing, low.** The seed error does not name the bad value (plan 11 seed rule 4).
4. **test.** No test that the lab answer holds no `barcode_file`.

### drink-atlas-workspace-f1 (barcode removal, save delay, plan 15)

1. **bug, needs an owner decision.** `seed_codes.py` and `seed_atlas_bindings.py` add every
   file row that is not in the table. A value that a person removed comes back on the next
   run. `COMMANDS.md` says a second run is safe. Reproduced.
2. **doc.** Plan 07 rule 5, README step 3, and the `lab_server.py` docstring still say the
   Atlas bindings are not in the database, or leave `wine_atlas_binding` out.
3. **doc.** SMOKE_TESTS S1, S3 (version 8), the "schema version 2" line, S12 (33 tests).

No finding: the barcode removal, the redraw of one card, the rules of plan 15.

### drink-atlas-workspace-98 (plans 17 and 19, rule 23)

1. **bug, low.** A comment with a lone surrogate character gets no HTTP answer.
2. **cosmetic.** In the view `with comments` a card stays after its last comment goes; in
   `Favorites` a card leaves. The two filters differ.
3. **cosmetic.** An empty comment draft triggers the leave-page prompt.
4. **doc.** SMOKE_TESTS D2, D10, D10a (version 7), D12 and plan 07 (9 tests of
   `test_labdb.py`); plan 11 still says SIGINT; README step 3 lists no `Favorites`.

No finding: the rules of plans 17 and 19.

### drink-atlas-workspace-fa (plan 20, `Add wine`)

1. **bug, low.** A non-string `image_name`, or a lone surrogate in a text field, gets no
   HTTP answer.
2. **missing.** Plan 20 rule 4: `import_website.py` keeps its own copy of `is_manual`.
3. **test.** Rule 16 (a slug that exists in any state) is tested for an `Active` wine alone.
4. **risk.** The slug `__null__` passes the manual slug rule; it is the no-match place of
   `scripts/match_scoring.py`.
5. **in progress.** The optional description (schema 014) is in; plan 20 and SMOKE_TESTS AW
   still name it required; the slug from the name is not in the page yet.

No finding: "the imports never remove a `__` wine", the portrait image column.

### drink-atlas-workspace-0b (the preview of the alternative photos, the grey `Disabled` image)

1. **missing, needs an owner decision.** A click on a thumbnail of another kind changes the
   image alone. The title, the page path, and the arrows stay on the kind that was opened,
   so a copied link opens another image.
2. **doc.** SMOKE_TESTS AL13/AL14 twice; PE18; plan 14 item 4 (thumbnail names).
3. **cosmetic.** At 860 px or less the favorites star is not at the right edge.

No finding: the preview of the alternative photos, the page paths, the grey image.

### drink-atlas-workspace-e3 (`Log` on `/embedding`)

No finding.

### drink-atlas-workspace-f0 (the preview path; the session is not running)

No finding.

### drink-atlas-workspace-ff (plans 18 and 21, the website import)

1. **blocked.** Plan 21 (a UI for the import, the merge dialog, a reused connection, two
   times, a schema file) waits for the owner.
2. **missing.** No route can fix the 10 stop problems of the first run (`name`, `producer`,
   `category`, a changed `main`). Plan 21 covers this.
3. **risk.** The store code uses `image.folder`; the next run fails after the flat store.
4. **risk.** Plan 21 adds triggers on `wine_catalog`; each later rebuild of that table (as
   014) MUST create them again.

### drink-atlas-workspace-8b (plan 09, the SAM3 noun `box`)

1. **blocked.** The owner chooses option A (patch two wines, no code) or B (a box wins only
   when it holds the bottle). 8b recommends B. B changes every caller of `derive_all` and
   needs one SAM3 run over about 143 images.

### drink-atlas-workspace-9a [f028b4] (plan 13, the flat image store)

1. **blocked, large.** The worktree change is from 07:42. On the present tree 7 hunks fail
   in 5 files, and 61 tests fail. The merge MUST now also cover `patches.py`,
   `alternatives.py`, `manual_wines.py`, `import_website.py`, the new routes of
   `lab_server.py`, their tests, and docs: about 25 to 28 files. 4,054 files move.
2. **risk.** `labdb.migrate` checks the numbers alone. A file with a number that the database
   has applied already is skipped with no message. Check `PRAGMA table_info(image)` after
   the migration.
3. It waits for the commit of the other sessions.

### drink-atlas-workspace-20 (plan 12, the test sets)

1. **blocked.** The code needs the flat store (`imagestore.path_of`, no `image.folder`). The
   pending schema file fits the present schema.
2. **overlap.** The owner asked at 12:15:00 for a script that imports the test sets of
   `svoe-vino-testset/dataset/`. `pipeline/import_testset.py` already is that script. The
   session TESTSET [0fe970] SHOULD reuse it and agree with 20.

## 2. Findings that no session owns

1. **test.** The 5 review-tool test modules do not load: `scripts/common.py` stops when
   `config.yaml` holds no `dataset`. With `config.old.yaml` all 25 tests pass. Proposed fix
   (about 11 lines): an environment variable for the config path of `scripts/common.py`,
   set to `config.old.yaml` by the 5 test modules.
2. **data.** Test values in the live database: the manual wine `__wqeqwe` (Active, junk
   text), the GTINs `00123123332138` and `00343324234332`, and the QR URL
   `http://127.0.0.1:8168/dataset` on two wines.

## 3. Decisions for the owner

1. The model of the processed files (7b finding 1): one cut for each original and kind (a
   schema change), or a guard that keeps one cut for each original.
2. `seed_patched.py` against the editor (7b finding 6).
3. The seeds of codes and Atlas bindings against removals (f1 finding 1).
4. The thumbnail click of another kind (0b finding 1).
5. The test values in the live database (section 2, item 2).
6. Is `scripts/review_server.py` still supported? It decides the urgency of a2 finding 1.
7. Option A or B of 8b; plan 21 of ff; an empty description in the imports after 014.
8. The commit of the shared tree. The flat store (9a) and the test sets (20) wait for it.

## 4. The answers of the owner (2026-09-25T12:28:04+0300)

1. Each running session fixes its own findings. 7b fixes its own findings, the findings
   of the stopped sessions in shared files, and the 5 load errors. The findings of a2 in
   `codes.py`, `seed_codes.py`, and the barcode editor go to f1, because f1 changes the
   same code.
2. `image_derivative` keeps one cut for each original and kind (`package` or `label`), in a
   new schema file (7b).
3. A seed refuses to run when its table already holds rows, unless `--force` is given:
   `seed_patched.py` (7b), `seed_codes.py` and `seed_atlas_bindings.py` (f1).
4. A click on a thumbnail of another kind switches the preview fully: the title, the page
   path, and the arrows follow (0b). The raw link of the patch preview (7b finding 11)
   goes to 0b, because 0b changes the same function.

Open: decisions 5 to 8 of section 3.

## 5. State of the fixes (about 12:50)

| Section | State |
|---|---|
| 7b | Done: findings 1 to 10 and 12, 13 (finding 11 went to 0b). Deployed at 12:45:39. |
| a2 | Done by f1 (findings 1 to 4). |
| f1 | Done by f1 (findings 1 to 3). |
| 98 | Done by 98 (findings 1 to 4). 98 also found a lone surrogate in the slug of each JSON route; 7b fixed it in `_json_body`. |
| fa | Done by fa (findings 1, 3, 4, 5); finding 2 done by ff. |
| 0b | Done by 0b (findings 1 to 3, and 7b finding 11). |
| ff | Finding 1 done (it uses `manual_wines.is_manual`); the rest is plan 21, which waits for the owner. |
| 8b | Waits for the owner (option A or B). |
| 9a [f028b4], 20 | These sessions ended. The flat store is in a private worktree and must be merged again (section 1). TESTSET entered the test sets as schema 016 without the flat store (owner choice of 12:22). |
| Section 2, item 1 | Done by 7b: the 5 load errors. |
| Section 2, item 2 | Open for the owner: the test values in the live database. |

