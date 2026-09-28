# Plan 57: the option `Add new testset …` of `/testset`

Date: 2026-09-26. Session: drink-atlas-workspace-96 [6338a8].
Status: approved by the owner on 2026-09-26T23:13:58+0300. Done, not committed. Live on 8168 since 23:18:58.

Source: owner message of 2026-09-26T23:03:00+0300 and the answers of 23:13:58. The text
is in [../owner-messages.md](../owner-messages.md). The page is the subject of
[plan 24](24_testset-page.md).

## 1. Goal

1. The select `Test set` of `/testset` gets a last option `Add new testset …`.
2. The option opens a small dialog. The dialog makes a new empty test set with the name
   that the owner types.
3. After the creation, the page shows the new set. The owner fills it with photos by a
   drop on a wine row, as before.

## 2. Decisions of the owner

| Question | Options | Answer |
|---|---|---|
| What does the option create? | an empty set; a copy of the current set; a choice in the dialog | an empty set |
| How is the name entered? | a small dialog; the browser `prompt()` | a small dialog |

## 3. The design

### 3.1 The server

1. `testsets.create_set(conn, name)` inserts one row of `test_set`:
   - `set_name` is `name`. The rule is the `CHECK` of schema 016: `^[0-9a-z_-]+$`.
     Another value gives HTTP 400.
   - A name that exists gives HTTP 409.
   - `source_dir` is `NEW_SOURCE` (`the page /testset`). The column MUST NOT be empty.
     No code reads `source_dir` as a path.
   - `edited_at` is the local time. So `import_testset.py` refuses to overwrite the set
     without `--force`, as for each set with a page edit.
2. The answer is `{"ok": true, "set": "<name>"}`.
3. The route is `POST /api/testset-new` with the JSON body `{"name": "<name>"}`. It is
   one entry of `testset_routes.WRITES`, so it runs in one write transaction.
4. `set_names` orders the sets by `rowid`, so the new set is the last in the select.
   The first set stays the default of the page.
5. No schema change. No route deletes or renames a set; this plan adds none.

### 3.2 The page

1. `load()` fills `#set` with the sets and appends the option `Add new testset …`. Its
   value `(new)` cannot be a set name, because a name has no parentheses.
2. The change handler of `#set` sees `(new)`: it selects the current set again and opens
   the dialog. The page does not load another set.
3. The dialog reuses the classes of the `Run>` dialog (`.run-dlg`, `.run-panel`,
   `.run-btn`). It holds a name field, the name rule, an error line, `Cancel`, and
   `Create`.
4. The live check: `Create` is enabled only for a name that matches the rule and is not
   the name of a present set. The error line states the reason.
5. Enter in the field presses `Create`. Escape and a click outside the panel close the
   dialog. While the dialog is open, the keys of the page do not act.
6. `Create` sends the POST. An error of the server shows on the error line. After a
   success the dialog closes and the page loads the new set (`load(name, false)`).

## 4. Files

- `pipeline/testsets.py`: `NEW_SOURCE`, `SET_NAME_RE`, `create_set`.
- `pipeline/testset_routes.py`: the docstring, `NEW`, one entry of `WRITES`.
- `pipeline/pages/testset.html`: the option, the change handler, the dialog, its JS.
- Tests: `tests/test_testsets.py`, `tests/test_testset_routes.py`.
- Docs: `README.md`, `SMOKE_TESTS.md`, `ChangeLog.md`.

## 5. Risks

1. A set with a wrong name stays: no route deletes a set. The owner removes it with
   SQLite. A delete route is a separate task.
