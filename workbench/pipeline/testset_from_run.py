"""A new test set from the misses of one run (plan 44).

The button `New testset…` of `/runs` makes a new test set of the lab database from the R@1
misses or the R@5 misses of the open run. The run names its test set in `options.set` of
`run.json`. The rule is the rule of the set `vlmrerank-8b-failed` of `svoe-vino-testset`:

- A row of `results.jsonl` is selected when its label is `positive` and its true slug is
  not at rank 1 (`r1`), or not in the top 5 (`r5`). A failed request has no rank, so it is
  selected: the metrics count it as a miss too.
- A selected row is copied when the source set still holds the photo of its `image_path`
  with the SHA-256 and the label of the run. Else it stays out with a reason. The owner
  chose this on 2026-09-26T09:12:00+0300.
- The copy keeps each column of the row of `test_photo`. The comments of the copied
  photos and the variant groups of the source set are copies too. No photo file is
  copied: the image store keeps one file for each SHA-256. The comments of a whole wine
  belong to no set, and the exclusion went away (plan 51).

The proposed name is `<base>-<N>`. The base is the name of the source set without a
trailing `-<digits>`, so the set `my-1` gives the base `my` (owner answer of 09:12:00).
`N` is the first number that gives a name that `test_set` does not hold. Read
`docs/plans/44_testset-from-run-misses.md`.
"""
import json
import os
import re

import run_files
import testsets
from testsets import TestsetError

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS_DIR = os.path.join(ROOT, "runs")
# The label of a selected row. The new set holds positive photos alone, as
# `vlmrerank-8b-failed` does.
LABEL = "positive"
# kind -> (the name, the rule, the test of the rank of the true slug). A rank of None is
# a true slug that did not come back.
MISSES = {
    "r1": ("R@1 misses", "the true slug is not at rank 1", lambda rank: rank != 1),
    "r5": ("R@5 misses", "the true slug is not in the top 5",
           lambda rank: rank is None or rank > 5),
}
# The reasons of a selected row that stays out.
REASONS = ("gone", "other bytes", "label changed")
# The CHECK of `test_set.set_name`, and `SET_NAME_RE` of `import_testset.py`.
NAME_RE = re.compile(r"^[0-9a-z_-]+$")
NUMBER_RE = re.compile(r"-[0-9]+$")


def runs_dir_of(server):
    """Return the directory of the runs of the lab server, as `run_routes.respond` does."""
    return getattr(server, "runs_dir", None) or RUNS_DIR


def source_set(conn, runs_dir, run_id):
    """Return the test set that the run `run_id` names. Raise `TestsetError` for an
    unknown run, a run with no test set, a dry run, and a set that the database of `conn`
    does not hold."""
    if not isinstance(run_id, str) or run_id not in run_files.run_dirs(runs_dir):
        raise TestsetError(404, "unknown run %r" % (run_id,))
    meta = run_files.read_json(run_files.run_path(runs_dir, run_id, "run.json")) or {}
    options = meta.get("options") or {}
    set_name = options.get("set")
    if not isinstance(set_name, str) or not set_name:
        raise TestsetError(409, "the run %s names no test set; a run of "
                                "scripts/match_run.py has none" % run_id)
    if options.get("dry_run"):
        raise TestsetError(409, "the run %s is a dry run, so it holds no answer" % run_id)
    if set_name not in testsets.set_names(conn):
        raise TestsetError(404, "the database holds no test set %s, the test set of the "
                                "run" % set_name)
    return set_name


def positive_rows(runs_dir, run_id):
    """Return the rows of `results.jsonl` of the run with the label `positive`, in the
    order of the file. A second row of one `image_path` is left out."""
    path = run_files.run_path(runs_dir, run_id, "results.jsonl")
    if not path or not os.path.isfile(path):
        raise TestsetError(409, "the run %s has no results.jsonl" % run_id)
    rows, seen = [], set()
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("label") != LABEL or rec.get("image_path") in seen:
                continue
            seen.add(rec.get("image_path"))
            rows.append(rec)
    return rows


def select(conn, set_name, rows):
    """Return kind -> the selection of each kind of `MISSES` from the rows of a run:
    `copy` (the place and the file name of each photo to copy), `selected`, `errors` (the
    selected rows whose request failed), and `left_out` (reason -> count)."""
    photos = {(place, name): (digest, label) for place, name, digest, label in conn.execute(
        "SELECT place, file_name, sha256, label FROM test_photo WHERE set_name = ?",
        (set_name,))}
    out = {kind: {"copy": [], "selected": 0, "errors": 0,
                  "left_out": dict.fromkeys(REASONS, 0)} for kind in MISSES}
    for rec in rows:
        # The place is a slug and holds no `/`, so the file name follows the last `/`.
        place, _, name = str(rec.get("image_path") or "").rpartition("/")
        found = photos.get((place, name))
        if found is None:
            reason = "gone"
        elif found[0] != rec.get("image_sha256"):
            reason = "other bytes"
        elif found[1] != rec.get("label"):
            reason = "label changed"
        else:
            reason = None
        for kind, (_, _, missed) in MISSES.items():
            if not missed(rec.get("rank_of_truth")):
                continue
            slot = out[kind]
            slot["selected"] += 1
            if rec.get("error"):
                slot["errors"] += 1
            if reason:
                slot["left_out"][reason] += 1
            else:
                slot["copy"].append((place, name))
    return out


def proposed_name(conn, set_name):
    """Return the first free name `<base>-<N>` for a set made from the set `set_name`."""
    base = NUMBER_RE.sub("", set_name) or set_name
    taken = set(testsets.set_names(conn))
    number = 1
    while "%s-%d" % (base, number) in taken:
        number += 1
    return "%s-%d" % (base, number)


def dialog_view(conn, runs_dir, run_id):
    """Return the answer of `GET /api/testset-from-run`: the set of the run, the proposed
    name, and the counts of each kind of misses."""
    set_name = source_set(conn, runs_dir, run_id)
    chosen = select(conn, set_name, positive_rows(runs_dir, run_id))
    return {"run": run_id, "set": set_name, "name": proposed_name(conn, set_name),
            "misses": {kind: {"title": MISSES[kind][0], "rule": MISSES[kind][1],
                              "selected": slot["selected"], "copied": len(slot["copy"]),
                              "errors": slot["errors"], "left_out": slot["left_out"]}
                       for kind, slot in chosen.items()}}


def _columns(conn, table):
    """Return the columns of `table` other than `set_name`, in the order of the table."""
    return [row[1] for row in conn.execute("PRAGMA table_info(%s)" % table)
            if row[1] != "set_name"]


def _copy_rows(conn, table, new, source, slugs=None):
    """Copy the rows of `table` of the set `source` to the set `new`: each row, or the
    rows of `slugs` alone. Return the count of the copied rows."""
    columns = ", ".join(_columns(conn, table))
    sql = ("INSERT INTO %s (set_name, %s) SELECT ?, %s FROM %s WHERE set_name = ?"
           % (table, columns, columns, table))
    if slugs is None:
        return conn.execute(sql, (new, source)).rowcount
    return sum(conn.execute(sql + " AND wine_slug = ?", (new, source, slug)).rowcount
               for slug in slugs)


def origin_note(name, source, run_id, misses, slot, now, source_note):
    """Return `test_set.label_note` of the new set: the origin, then the note of the
    source set."""
    left = ", ".join("%s %d" % item for item in slot["left_out"].items())
    title, rule, _ = MISSES[misses]
    note = ("The set %s was built on %s from the %s of the run %s of the test set %s "
            "(plan 44). Rule: a photo is selected when its label in the run is positive and "
            "%s. A selected photo is copied when the set %s holds it with the same SHA-256 "
            "and the same label. Selected: %d, %d of them with a failed request. Copied: "
            "%d. Left out: %s. The label entries, the comments of the photos, and the "
            "variant groups are copies without a change."
            % (name, now, title, run_id, source, rule, source, slot["selected"],
               slot["errors"], len(slot["copy"]), left))
    return note + ("\n\n" + source_note if source_note else "")


def build(conn, runs_dir, run_id, misses, name):
    """Write the new test set `name` from the misses `misses` (`r1` or `r5`) of the run
    `run_id`, in the transaction of the caller. Return the answer of
    `POST /api/testset-from-run`."""
    if misses not in MISSES:
        raise TestsetError(400, "`misses` MUST be one of %s" % ", ".join(MISSES))
    if not isinstance(name, str) or not NAME_RE.match(name):
        raise TestsetError(400, "the name MUST hold the characters a-z, 0-9, `_`, and `-` "
                                "alone")
    source = source_set(conn, runs_dir, run_id)
    if name in testsets.set_names(conn):
        raise TestsetError(409, "the test set %s exists already" % name)
    slot = select(conn, source, positive_rows(runs_dir, run_id))[misses]
    if not slot["copy"]:
        raise TestsetError(409, "the %s of the run %s give no photo to copy"
                           % (MISSES[misses][0], run_id))
    now = testsets.now_local()
    (source_note,) = conn.execute("SELECT label_note FROM test_set WHERE set_name = ?",
                                  (source,)).fetchone()
    # `edited_at` is set, so an import of a directory with this name needs `--force` to
    # replace the rows.
    conn.execute("INSERT INTO test_set (set_name, source_dir, edited_at, label_note) "
                 "VALUES (?, ?, ?, ?)",
                 (name, os.path.join(os.path.realpath(runs_dir), run_id), now,
                  origin_note(name, source, run_id, misses, slot, now, source_note)))
    columns = ", ".join(_columns(conn, "test_photo"))
    notes = 0
    for place, file_name in slot["copy"]:
        conn.execute("INSERT INTO test_photo (set_name, %s) SELECT ?, %s FROM test_photo "
                     "WHERE set_name = ? AND place = ? AND file_name = ?"
                     % (columns, columns), (name, source, place, file_name))
        # The comments of the photo keep their time and their source (plan 51).
        notes += conn.execute(
            "INSERT INTO test_photo_comment (set_name, place, file_name, created_at, source, "
            "text) SELECT ?, place, file_name, created_at, source, text FROM "
            "test_photo_comment WHERE set_name = ? AND place = ? AND file_name = ? "
            "ORDER BY created_at, id", (name, source, place, file_name)).rowcount
    return {"ok": True, "set": name, "source": source, "run": run_id, "misses": misses,
            "photos": len(slot["copy"]), "selected": slot["selected"],
            "errors": slot["errors"], "left_out": slot["left_out"],
            "photo_comments": notes,
            "variant_slugs": _copy_rows(conn, "test_variant", name, source)}
