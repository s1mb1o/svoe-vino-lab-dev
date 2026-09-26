# 21 — The website import in the UI, the merge dialog, and the change times

Date: 2026-09-25.
Status: approved by the owner on 2026-09-25T12:27:00+0300. Implementation by
drink-atlas-workspace-ff.
The owner messages of 2026-09-25 from about 12:00 ("can we make 2 modes", "also
introduce last_modified time") and the answers after them are in
[owner-messages.md](../owner-messages.md). This plan extends
[plan 18](18_import-website.md).

## Goal

1. `import_website.py` has two modes. The CLI stops on a conflict, as in plan 18. The
   UI shows a dialog, and a person merges each conflict.
2. Each wine has two change times. The Dataset page can sort by each of them.

A conflict is a changed text field or a changed main image. A plain change is a new
wine, a missing wine, a restored wine, or a stored main image (plan 18, rules 7 to 12).

## Decisions of the owner

| Question | Answer |
|---|---|
| UI mode | A background job. A button on `/dataset` starts the tool as a subprocess, as `Build` on the Embeddings page does. The merge dialog opens after the compare. |
| Dialog | The conflicts and all plain changes. Each plain change has a checkbox. |
| A conflict with the choice `database` | Remember the refusal. A later run skips it while the website value stays the same. The CLI obeys it. |
| A cleared checkbox of a plain change | Remember it in the same way. Changed on 2026-09-26 (owner messages of 19:58:00 and 20:05:00): skip it this time, with no refusal and no comment. |
| An image conflict with the choice `website` | The website image replaces `main` and gets `derive.py`. The old file stays in the store. `main_patched` stays. |
| Comments | A comment for each choice. |
| Image check | A full download and a byte compare of each image, over one reused HTTPS connection. |
| Change times | Two columns: `website_modified_at` (the sitemap `lastmod`) and `modified_at` (the lab change time). |
| Lab change | A change of a field or of the state of the row of `wine_catalog`. |
| Shared files | Small separate hunks on top of the uncommitted work of the other sessions. |

## Findings

Probes of 2026-09-25, about 12:05, with 20 and 30 images:

| Request | New connection | Reused connection |
|---|---|---|
| `HEAD` of an original | 0.45 s | 0.16 s |
| `GET` of an original (52 KB mean) | 0.53 s | 0.16 s |

A reused connection makes the 0.25 s pause the limit. A full run then needs about 2,250
requests at 0.25 s: about 10 minutes, not 22. A `HEAD` request costs the same as a
`GET`, so a size check saves no time. The server keeps the connection open.

## Schema file `NNN_website_import.sql`

The number is fixed at the entry (rules 25 to 28 of `AGENTS.md`).

```sql
ALTER TABLE wine_catalog ADD COLUMN website_modified_at TEXT
    CHECK (website_modified_at <> '');
ALTER TABLE wine_catalog ADD COLUMN modified_at TEXT
    CHECK (modified_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z');

-- One trigger for an insert, one for an update of a field or of the state.
CREATE TRIGGER wine_catalog_insert_time AFTER INSERT ON wine_catalog
BEGIN
    UPDATE wine_catalog SET modified_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
    WHERE rowid = NEW.rowid;
END;
CREATE TRIGGER wine_catalog_update_time AFTER UPDATE OF
    name, producer, category, color, region, grapes, description, csv_photo_name,
    state, removed_by ON wine_catalog
WHEN OLD.name IS NOT NEW.name OR OLD.producer IS NOT NEW.producer OR … (each column)
BEGIN
    UPDATE wine_catalog SET modified_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
    WHERE rowid = NEW.rowid;
END;

CREATE TABLE website_refusal (
    wine_slug     TEXT NOT NULL CHECK (wine_slug <> ''),
    kind          TEXT NOT NULL
                  CHECK (kind IN ('text', 'image', 'new', 'missing', 'back', 'main')),
    field         TEXT NOT NULL DEFAULT '',
    website_value TEXT,
    created_at    TEXT NOT NULL,
    PRIMARY KEY (wine_slug, kind, field),
    CHECK ((kind = 'text') = (field <> ''))
) STRICT;
```

- `website_modified_at` is the `lastmod` of the wine in `wines-sitemap.xml`, as the
  sitemap writes it, for example `2026-09-22T15:36:48.000Z`. NULL: no import saw the
  wine yet.
- `modified_at` is the UTC time of the last change of the row. The triggers set it, so
  no writer changes its code. `website_modified_at` and `modified_at` themselves do not
  count as a change. An existing row keeps NULL: its change time is not known.
- A schema file that builds `wine_catalog` again (as 004 and 014 did) drops both
  triggers. Such a file MUST create them again. A column that a later schema file adds
  MUST get a line in the trigger of the update too. The review of 7b (2026-09-25) asked
  for this rule.
- The trigger of the insert runs only when `modified_at` is NULL, so a copy of a row can
  keep its time.
- `website_refusal` has no foreign key: a refused new wine is not in `wine_catalog`.
- `website_value`: for `text`, the website value; for `image` and `main`, the SHA-256 of
  the website file; for `new`, `missing`, and `back`, NULL.

## Changes of `import_website.py`

### Requests

1. The client reuses one HTTPS connection to `api.vino-svoe.ru`. It opens a new one
   after an error or after `Connection: close`. The pause of 0.25 s stays.
2. The tool reads `https://vino-svoe.ru/wines-sitemap.xml` once, for the `lastmod` of
   each slug. A slug that the sitemap does not hold gets NULL.

### Refusals

3. A refusal matches while its situation stays:
   - `text`: the website value of the field equals `website_value`.
   - `image`: the SHA-256 of the website image equals `website_value`.
4. A matching refusal removes its conflict from the run. The report counts it as
   `refused`.
5. A write of an import deletes each refusal that did not match in this run.
- Change of 2026-09-26 (owner messages of 19:58:00 and 20:05:00): only a conflict with
  the choice `database` gets a refusal. A plain change never gets one. The compare reads
  no refusal of the kinds `new`, `missing`, `back`, and `main`. So a row of these kinds
  does not match, and the next write deletes it (rule 5). The schema keeps the four
  kinds, because rule 28 of `AGENTS.md` forbids an edit of `015_website_import.sql`.

### Modes

6. No mode flag (the CLI): as plan 18. A conflict stops the import. Rule 3 applies.
7. `--prepare DIR`: the tool compares, and it never writes the database. It writes
   `DIR/diff.json` and `DIR/images/<sha256>.<extension>` for each website image that
   the apply can need. Exit 0 also with conflicts. The problems that are not conflicts
   still stop the run with exit 1: a list problem, a `__` slug, a website wine with no
   image, a new wine with an empty required value, a network error.
8. `--apply DIR`: the tool reads `DIR/diff.json` and `DIR/choices.json`. It refuses a
   choice file that misses a conflict. It reads the database again. If the database
   changed after the prepare, it stops with no change and asks for a new compare. Else
   it writes everything in one transaction and writes `DIR/result.json`.
9. Each mode writes `website_modified_at` of each website wine at its write.

### `diff.json` and `choices.json`

```json
{"created_at": "…", "database": "data/lab.sqlite3", "snapshot": "<sha256 of the rows>",
 "conflicts": [
   {"id": "text:muskat-premium:name", "slug": "muskat-premium", "kind": "text",
    "field": "name", "database": "Мускат. Премиум", "website": "Мускат Премиум"},
   {"id": "image:muskat-premium", "slug": "muskat-premium", "kind": "image",
    "database": {"sha256": "…", "source_name": "Screenshot_25_e7771a3f2d.webp"},
    "website": {"sha256": "…", "name": "MAX_02198_7f3ccea6d6.webp", "file": "images/….webp"}}],
 "changes": [
   {"id": "new:<slug>", "slug": "…", "kind": "new", "name": "…", "producer": "…",
    "image": "images/….webp"},
   {"id": "missing:<slug>", "slug": "…", "kind": "missing", "name": "…", "state": "Active"}],
 "refused": 0, "website": 2105}
```

```json
{"conflicts": {"text:muskat-premium:name": "website", "image:muskat-premium": "database"},
 "changes": {"new:<slug>": true, "missing:<slug>": false}}
```

### The apply of the choices

| Choice | Write | Comment (source `script`) |
|---|---|---|
| Text, `website` | The field gets the website value. | `<field> from vino-svoe.ru; was '<old>'.` |
| Text, `database` | A `text` refusal. | `kept <field>; vino-svoe.ru has '<new>'.` |
| Image, `website` | The website file replaces the `main` row, with `derive.py`. | `main image from vino-svoe.ru; was <old source_name>.` |
| Image, `database` | An `image` refusal. | `kept main image; vino-svoe.ru has <name>.` |
| Plain change, checked | As plan 18. | As plan 18. |
| Plain change, cleared | None: skipped this time. The next compare shows it again. | None. |
| Conflict, no choice | None: skipped this time. The next compare shows it again. | None. |

Until 2026-09-26 19:58, a cleared `missing`, `back`, `main`, or `new` row wrote a refusal,
and the first three wrote a comment (`kept <state>; missing on vino-svoe.ru.`, `kept
Removed; back on vino-svoe.ru.`, `main image of vino-svoe.ru not taken.`). The result and
`result.json` list the cleared change ids in `skipped` (`cleared changes, not written`).

## The lab server

A new module `pipeline/website_import_routes.py`, like `embedding_routes.py`.
`lab_server.py` gets small hunks: the import, and the delegation in `do_GET` and in
`_write_route`.

| Route | Answer |
|---|---|
| `POST /api/website-import/start` | Starts `import_website.py --db <db> --prepare work/website-import/<run>/` with its log in `run.log`. HTTP 409 while a job runs. |
| `GET /api/website-import` | The newest run: the phase (`prepare` or `apply`), the state (`running`, `done`, `failed`), the last progress line, the error, and the counts. |
| `GET /api/website-import/<run>/diff` | `diff.json`. |
| `GET /website-import/<run>/images/<sha256>.<extension>` | A website image of the run. |
| `POST /api/website-import/<run>/apply` | Writes `choices.json`, and starts `--apply`. |
| `POST /api/website-import/stop` | Stops the job with SIGTERM. |

- One job runs at a time. A lock file with the PID in `work/website-import/` tells it,
  so a restart of the server does not lose the job. Git ignores `work/`.
- The run directories stay. One run holds about 10 MB of images.

## The Dataset page

- `dataset.html` gets small hunks: a button `Import from website` in the bar, one
  `<script src="/website-import.js">` tag, two options of `#sort`, and the two times in
  the data of a record (a hunk in `dataset_records` of `lab_server.py`).
- The new file `pipeline/pages/website_import.js` builds the dialog with the `.modal`
  classes of the page and its colour variables, so the dark theme works.
- A click on the button starts a compare. The button then shows the progress, for
  example `Website: images 300/2105`. At the end the dialog opens. A click on the button
  opens the dialog of a finished compare again.
- The dialog has sections: conflicts (the two values, or the two images side by side,
  and the radio buttons `database` and `website`), new wines, missing wines, restored
  wines, and main images. A checkbox of a plain change is set at the start. A conflict
  has no choice at the start. `Apply` is disabled until each conflict has a choice.
- Changes of 2026-09-25, about 16:00 (owner messages of about 15:40 and the answers of
  15:55): one card holds all conflicts of one wine. Each wine slug is a link to
  `https://vino-svoe.ru/wines/<slug>`, except in `Missing on the website`. A click on an
  image shows a large view with the file name; the click changes no choice. The section
  titles are `New wines on website` and `Missing main images, taken from website`.
- `Apply` starts the apply job. At the end the page reads the data again and shows the
  result.
- Change of 2026-09-26 (owner message of 08:00:00, answer of 08:07:00): the path of the
  page is `/dataset/website-import` while the dialog is open. The open pushes a history
  entry; a close and Back give `/dataset`; Forward opens the dialog again. A link to the
  path, or a reload of it, opens the dialog with the newest run. The server already sends
  the page for `/dataset/<one segment>`; the page does not read `website-import` as a wine
  slug. `Reload the page` in the result loads `/dataset`.
- Change of 2026-09-26 (owner message of 19:11:01): `Apply` stays enabled while a
  conflict has no choice. The apply skips such a conflict: no field change, no image
  change, no refusal, and no comment. The next compare shows it again. The status line
  states `N conflicts have no choice. Apply skips them.` The result and `result.json` list
  the skipped conflict ids (`unresolved`). The CLI still stops on each conflict.
- Change of 2026-09-26 (owner messages of 19:16:31 to 19:23:19, answers of 19:22:30): a
  section `Possible renames` after `Conflicts`. A rename always pairs a slug that left
  the website (a `missing` change) with a slug that appeared on it (a `new` change). A
  pair matches when the stored main image equals the website image, when the slug
  distance (Levenshtein) is at most 3 edits or at most 20 % of the longer slug, or when
  the name and the producer are equal after the normalization (lower case, `ё` -> `е`, no
  punctuation). Each row shows the missing wine, an arrow, the new wine, and the matched
  rules. The section is display only: the checkboxes of `New wines on website` and
  `Missing on the website` decide the write. The diff route computes the pairs from
  `diff.json` with `import_website.renames`, so an older run shows them too.
- `#sort` gets `changed in the lab, newest first` (`modified_at`) and `changed on
  vino-svoe.ru, newest first` (`website_modified_at`). A NULL time sorts last.

## Tests

- `tests/test_import_website.py`: the reused connection (a fake), the sitemap times, each
  refusal kind, `--prepare` (no write, the files), `--apply` (each row of the choice
  table, a missing choice, a database change after the prepare), the deletion of a stale
  refusal.
- `tests/test_website_import_routes.py`: start, 409, state, diff, image, apply, stop,
  with a fake command.
- `tests/test_labdb.py` and a trigger test: an insert and a field change set
  `modified_at`; a write of `website_modified_at` alone does not.
- `tests/test_lab_server.py`: the two times in `/api/dataset`, the delegation.

## Deploy

The schema file, the migration of `data/lab.sqlite3`, and a restart of 8168 with
SIGTERM belong together (rules 22 to 28). The owner gets a message about the restart.

## Deploy log

- 2026-09-25 12:32: `015_website_import.sql` entered (rule 26: messages to 7b and
  TESTSET; 20, 9a [f028b4], and e3 were not reachable). 12:33: `data/lab.sqlite3`
  migrated to 15. `tests/test_labdb.py`: `VERSION` 15 and the table `website_refusal`.
  The fixture insert of `tests/test_lab_server.py` names its columns now; f1 found the
  break. fa fixed the same insert in `tests/test_manual_wines.py`.
- 12:45:39: 7b restarted 8168 for all sessions. 12:50:39: this session restarted 8168
  with SIGTERM for the routes of the website import.
- Tests: `test_import_website.py` 31, `test_website_import_routes.py` 6,
  `test_lab_server.py` 50, the full suite 397, all `OK`. Headless Chromium on the live
  server: the button, the start dialog, Esc, and the two sort options in the light and
  the dark theme.
- 12:51:32 to 13:02:57: the first compare through the UI route (run
  `20260925T125132`) took 11.5 minutes: 2,255 requests, 150 MB, 127 staged images. It
  found 12 conflicts (the 9 text fields and the 3 images of plan 18) and 196 plain
  changes (73 new, 71 missing, 52 main images). The database did not change. The dialog
  showed all of them in headless Chromium, in both themes. Nothing was applied: the
  choices belong to the owner.

## Open points for the owner

1. A conflict has no choice at the start, so `Apply` needs a choice for each conflict.
   The alternative: `database` at the start. Changed on 2026-09-26 (owner message of
   19:11:01): `Apply` skips a conflict with no choice.
2. The comments of a cleared plain change (the last four rows of the table) are my
   proposal. Removed on 2026-09-26: a cleared plain change gets no comment.
3. An existing row keeps `modified_at` NULL. The alternative: the time of the migration
   for each row.
4. No page lists or forgets a refusal in this plan. A refusal ends when its situation
   ends (rule 5), or a person deletes its row.
