# Plan 50: a text export of the lab database for the git history

Date: 2026-09-26

Source: owner message of 2026-09-26T17:26:06+0300, and the answers of 17:28:00 (session
drink-atlas-workspace-96 [0fa3f4]). This plan answers open question 3 of
[plan 07](07_sqlite-lab-database.md).

## 1. The problem

`data/lab.sqlite3` holds data that the sources cannot rebuild: the wine states, the
comments, the favorites, the manual wines, the alternative photos, the edits of the
Testset page, and the image descriptions. git
ignores `/data/` since 2026-09-24. The copies in `data/backups/` are binary files with no
history. So no tool shows when a row changed, or what it held before.

## 2. The decisions of the owner

| question | options | the choice of the owner |
|---|---|---|
| The format | one `sqlite3 .dump` file; one JSON-lines file for each table | JSON lines for each table |
| The place | a new directory `db-export/`; an exception for one file in `/data/` | `db-export/` |
| The commit | the skill exports and commits; the skill exports, and a person commits | the skill exports and commits |
| The restore | into a new file; no restore in the skill | into a new file |

Reasons for JSON lines: each table has its own file, and the rows stay in primary key
order. A `.dump` file keeps the rows in `rowid` order, and one file holds all 17 tables.
The cost of JSON lines: a Python tool is necessary for the export and for the restore.

## 3. The tool `pipeline/db_export.py`

`export` writes three kinds of files into `db-export/`:

| file | content |
|---|---|
| `schema.sql` | The `CREATE TABLE` statements, in the order of `sqlite_schema`. |
| `rows/<table>.jsonl` | One JSON object for each row, in primary key order. The keys are the columns, in the order of the table. |
| `after-rows.sql` | The indexes, the views, the triggers, and `PRAGMA user_version`. |

Rules of the export:

1. The export reads the database into memory with the SQLite backup API, in one step. So
   the export sees one state of the database. A running lab server waits for the copy
   alone: 0.03 s on 2026-09-26.
2. Each row keeps its `rowid` as the first key. About 15 queries of the lab code sort or
   join by `rowid` to keep the import order, for example in `lab_server.py` and
   `import_catalog.py`.
   The schema files 004 and 014 keep each `rowid` for the same reason.
3. A table whose primary key is one column of the type `INTEGER` has no key `rowid`. The
   column is the `rowid` itself. Today this is `wine_comment.id`.
4. A table with a column `rowid`, `oid`, or `_rowid_` stops the export. The column hides
   the `rowid`.
5. A BLOB value stops the export. The lab schema has no BLOB column today. A new BLOB
   column needs a change of the tool.
6. The tables `sqlite_*` are internal. The export skips them. The automatic indexes have
   no SQL. SQLite makes them again with their tables.
7. Each file goes to `<file>.tmp` first and then to its name. `.gitignore` ignores
   `*.tmp`.
8. The export removes the file of a table that the database no longer holds.
9. The JSON keeps the Cyrillic letters (`ensure_ascii=False`). A line break in a value is
   `\n`, so each row stays on one line.

`restore` builds a new database from an export directory:

1. The target file MUST NOT exist. The restore never replaces a file.
2. The restore runs `schema.sql`, loads the rows in one transaction with the foreign keys
   off, and runs `PRAGMA foreign_key_check`. A broken link stops the restore.
3. Then it runs `after-rows.sql`. The triggers come after the rows, because the trigger
   `wine_catalog_insert_time` sets `modified_at` of a new row when the value is NULL.
4. The work file is `<target>.restoring`. A failed restore removes it. The restore
   renames it to the target at the end.

## 4. The skill `backup-lab-db`

[`.claude/skills/backup-lab-db/SKILL.md`](../../.claude/skills/backup-lab-db/SKILL.md)
holds the steps: the export, a round trip check, the commit, the history commands, and
the restore.

1. The round trip check restores the export into a temporary file and exports the file
   again. `diff -r` MUST find no difference.
2. The commit uses a private git index (`GIT_INDEX_FILE`) that holds `HEAD` plus
   `db-export/`. Other sessions work in the same working tree and use the same shared
   index. On 2026-09-26 a shared index put the work of one session into the commit of
   another session. `git update-ref <branch> <new> <old>` fails when `HEAD` moved. Then
   `git reset -q -- db-export` makes the shared index agree with the new commit.
3. An export with no change makes no commit.
4. The skill does not push.
5. The skill takes `db-export/*` in `ACTIVE_WORK.md` for the time of the run, so that two
   sessions do not export at the same time.

## 5. Measurements of 2026-09-26

On `data/lab.sqlite3` with schema 21: 17 tables, 26,792 rows, 12 MB of text. The export
took 0.4 s. The restore took 0.5 s. The restored database gave the same rows with the
same `rowid` in each table. A second export of it was byte for byte equal to the first.
`labdb.connect` opened it. In a scratch clone of the repository, one changed GTIN gave a
commit of one file with 1 added and 1 removed line.

## 6. Risks and limits

- The commit holds the images of `data/images/main/` and `data/images/patched/` alone
  (section 8). The alternative photos of `data/images/additional/` cannot be rebuilt
  either, but they stay out of git until the owner asks for them.
- Each commit that changes a large table adds a new object of 1 to 3 MB. `git gc` packs
  the objects with deltas. The size of the repository grows with the number of backups.
- The export holds all text of the database, for example the image descriptions and the
  comments. A push sends it to the remote.
- An `INTEGER PRIMARY KEY DESC` column is not the `rowid` in SQLite. The tool counts it
  as the `rowid`. The lab schema has no such column.

## 7. Tests

`tests/test_db_export.py`, 8 tests: the key order and the `rowid`, an exact round trip,
the trigger after the rows, the refusal of an existing target, no file after a failed
restore, the removal of the file of a dropped table, the refusal of a BLOB, and a round
trip of the full lab schema through `labdb.connect`.

## 8. The main photos and the patches in git

Source: owner message of 2026-09-26T17:51:32+0300, and the answers of 17:54:00.

| question | options | the choice of the owner |
|---|---|---|
| The scope | the skill commits the images on each run; one commit now | the skill commits them on each run |
| The storage | plain git; Git LFS | plain git |

1. `.gitignore` ignores the content of `data/` and of `data/images/`, not the
   directories, and takes back `data/images/main/` and `data/images/patched/`. git cannot
   take back a file of an ignored directory.
2. `data/cache/` stays out of git, as the owner asked. So do the database file,
   `data/backups/`, `data/embeddings/`, and the image folders `cropped/`, `testset/`, and
   `additional/`.
3. On 2026-09-26, `data/images/main/` held 2,019 files (135 MB), and
   `data/images/patched/` held 18 files (7 MB). The largest file had 1.8 MB.
4. Each file name is the sha256 of the file. A file never changes. So the history of the
   folders holds added files and removed files alone, and each image is in git one time.
5. Step 3 of the skill adds the two folders to the same private index as `db-export/`.
   One commit then holds rows and images of the same moment. The commit message counts
   the added and the removed files of each folder.
6. In a scratch clone, the first run committed the 2,037 files, the second run made no
   commit, and one new patch with one removed main photo gave a commit of 2 files.
