---
name: backup-lab-db
description: Back up the svoe-vino-lab database data/lab.sqlite3 as a text export in db-export/ and commit it together with the image folders data/images/main/ and data/images/patched/, so that git keeps the history of each row and each main photo and patch. Also restores an export from the working tree or from any commit into a new database file. Use when asked to back up, snapshot, export, or commit the lab database, to show the history of lab data, or to restore the lab database from git.
---

# Back up the lab database to git

`data/lab.sqlite3` is a binary file, and git ignores it. So git cannot keep its history. `pipeline/db_export.py` writes the database as text files into `db-export/`.
Each row is one line, so `git diff` shows each added, changed, and removed row. Read
[plan 50](../../../docs/plans/50_lab-db-text-export.md) for the reasons.

The export directory:

| file | content |
|---|---|
| `db-export/schema.sql` | The `CREATE TABLE` statements. |
| `db-export/rows/<table>.jsonl` | One JSON object for each row, in primary key order. |
| `db-export/after-rows.sql` | The indexes, the views, the triggers, and `PRAGMA user_version`. |

Each row keeps its `rowid`. The lab code sorts by `rowid` to keep the import order, so a
restore without the `rowid` is not the same database. A changed row is one removed line
and one added line in `git diff`.

The same commit holds the image files of `data/images/main/` and `data/images/patched/`.
The owner asked for this on 2026-09-26. Each file name is the sha256 of the file, so a
file never changes: git adds a new file or records a removed file. `.gitignore` keeps the
rest of `data/` out of git: the database file, `data/cache/`, `data/backups/`,
`data/embeddings/`, and the image folders `cropped/`, `testset/`, and `additional/`.

Run every command in the project root:

```bash
cd /Volumes/T7_2TB/Projects-T7_2TB/drink-atlas-workspace/svoe-vino-lab
```

## 0. Before you start

1. Read `ACTIVE_WORK.md`. If another section lists `db-export/*`, stop: another session
   runs this skill. Wait, or ask the owner.
2. Put `db-export/*` in the files of your own section of `ACTIVE_WORK.md`. Make the
   section if you do not have one. Read the rules in `AGENTS.md`, section "Work of the
   sessions".

## 1. Export

```bash
python3 pipeline/db_export.py export
```

The expected output: `export: db-export (schema 21, 17 tables, 26792 rows)`. The numbers
change with the data. The export reads the database with the SQLite backup API in one
step. A running lab server (port 8168) does not need a stop.

The export stops with `error: …` in these cases. Do not commit a partial export: report
the error to the owner.

- A column holds a BLOB. The export keeps text and numbers alone. A new BLOB column needs
  a change of `pipeline/db_export.py`.
- A table name is not safe as a file name.
- `data/lab.sqlite3` does not exist.

## 2. Check the export with a round trip

```bash
T=$(mktemp -d)
python3 pipeline/db_export.py restore --from db-export --db "$T/lab.sqlite3"
python3 pipeline/db_export.py export --db "$T/lab.sqlite3" --out "$T/again"
diff -r db-export "$T/again" && echo "round trip: identical"
rm -rf "$T"
```

The restore MUST give the same row counts as step 1. `diff -r` MUST print no line. Any
difference is an error of the tool: do not commit, and report it to the owner.

## 3. Commit the export

Other sessions work in the same working tree and use the same git index. So the commit
uses a private index. It holds `HEAD` plus `db-export/` and the two image folders alone.
Do not use `git add` or `git commit` with the shared index.

```bash
D=$(mktemp -d); IDX="$D/index"
P=(db-export data/images/main data/images/patched)
OLD=$(git rev-parse HEAD); BRANCH=$(git symbolic-ref HEAD)
GIT_INDEX_FILE="$IDX" git read-tree "$OLD"
GIT_INDEX_FILE="$IDX" git add -A -- "${P[@]}"
if GIT_INDEX_FILE="$IDX" git diff --cached --quiet "$OLD"; then
  echo "no change since the last export"
else
  V=$(sed -n 's/^PRAGMA user_version = \([0-9]*\);$/\1/p' db-export/after-rows.sql)
  K=$(ls db-export/rows | wc -l | tr -d ' ')
  N=$(cat db-export/rows/*.jsonl | wc -l | tr -d ' ')
  { echo "Lab database export (schema $V, $K tables, $N rows)"; echo
    echo "The skill backup-lab-db exported data/lab.sqlite3 at $(date +%Y-%m-%dT%H:%M:%S%z)."
    echo "Lines added and removed in each file (a changed row counts in both columns):"
    GIT_INDEX_FILE="$IDX" git diff --cached --numstat "$OLD" -- db-export | grep . \
      || echo "no change"
    echo "Image files (A added, D removed):"
    GIT_INDEX_FILE="$IDX" git diff --cached --name-status "$OLD" -- data/images \
      | awk '{split($2, p, "/"); n[$1 " " p[1] "/" p[2] "/" p[3]]++}
             END {for (k in n) print n[k], k}' | sort -k2 | grep . || echo "no change"
  } > "$D/message"
  TREE=$(GIT_INDEX_FILE="$IDX" git write-tree)
  NEW=$(git commit-tree "$TREE" -p "$OLD" -F "$D/message")
  git update-ref "$BRANCH" "$NEW" "$OLD" && git reset -q -- "${P[@]}" \
    && git log -1 --format='%h %s' "$NEW" && git show --stat=100 --format= "$NEW" | tail -1
fi
rm -rf "$D"
git diff --cached --name-only -- "${P[@]}"
```

- `no change since the last export` is a correct result. Make no commit.
- `git update-ref` fails when `HEAD` moved during the step: another session made a commit.
  Run step 3 again. The new `HEAD` is the parent then.
- `git reset -q -- "${P[@]}"` makes the shared index agree with the new commit for the
  three paths alone. The staged files of other sessions stay.
- The last command MUST print no line.
- The first commit of `db-export/` added about 12 MB, and the first commit of the images
  about 142 MB (2,037 files). A later commit adds each changed export file as a new
  object, and each new image. `git gc` packs the objects and keeps the differences of the
  text files alone.
- Do not push. Push only when the owner asks.

## 4. Finish

1. Remove `db-export/*` from your section of `ACTIVE_WORK.md`. Remove the section if it
   holds nothing else.
2. Tell the owner the commit hash, the title line, and the tables with changed rows. Or
   tell the owner that nothing changed.

## Show the history

```bash
git log --stat --format='%h %ad %s' --date=iso -- db-export     # each backup
git log -p -- db-export/rows/wine_catalog.jsonl                 # the rows of one table
git log -S '"wine_slug":"<slug>"' --oneline -- db-export        # the commits that touch one wine
git diff <commit-1> <commit-2> -- db-export/rows/               # two backups
```

## Restore

A restore writes a NEW database file. It never replaces a file:
`pipeline/db_export.py restore` refuses a `--db` that exists. Put the new file in
`data/backups/`.

From the working tree:

```bash
python3 pipeline/db_export.py restore --from db-export \
    --db data/backups/lab-restored-$(date -u +%Y%m%dT%H%M%SZ).sqlite3
```

From a commit:

```bash
C=<commit>
T=$(mktemp -d)
git archive "$C" db-export | tar -x -C "$T"
python3 pipeline/db_export.py restore --from "$T/db-export" \
    --db data/backups/lab-restored-$(git rev-parse --short "$C").sqlite3
rm -rf "$T"
```

The restore creates the tables, loads the rows with the foreign keys off, and runs
`PRAGMA foreign_key_check`. Then it creates the indexes, the views, and the triggers, so
a trigger does not change a restored row. At the end it sets `PRAGMA user_version`. A
failed restore leaves no file.

To open a restored file, use `labdb.connect`. It applies the newer schema files of
`pipeline/schema/` when the export is older.

The image files need no restore step while they are in the working tree. A removed main
photo or patch comes back from a commit that holds it:
`git checkout <commit> -- data/images/patched/<sha256>.<extension>`.

Do not put a restored file in the place of `data/lab.sqlite3` unless the owner asks for
it. The swap needs a stop of the lab server and a start again. Follow the rules 22 to 24
of `AGENTS.md`. Before the swap, copy the present `data/lab.sqlite3` to
`data/backups/lab-before-restore-<UTC time>.sqlite3`.
