#!/usr/bin/env python3
"""Merge the imported competitor test sets into one flat set, then remove them.

Usage (from `workbench/`):
    python3 scripts/merge_competitor_testsets.py --dry-run
    python3 scripts/merge_competitor_testsets.py

The owner asked for this merge on 2026-09-30T18:45:00+0300 and selected the rules at
18:58 (`docs/owner-messages.md`):
- One photo is one source photo. Rows with the same SHA-256 or the same source file
  stem are one photo, as in `competitors-scored-common`. The largest copy stays.
- A photo goes to every place that a source set gave it: each wine slug, `__null__`,
  and `__drawer__`.
- The script removes the source sets from the database. Their directories below
  `data/competitor-testsets/` stay, so `import_competitor_testsets.py` can make them
  again.

A source set is a set whose directory below the snapshot root holds `manifest.jsonl`.
The manifest gives the source image path of each row. The database rows give the place,
the label, and the image. Before the write, the script copies the database to
`data/backups/`.
"""

import argparse
import datetime
import json
import os
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKBENCH = HERE.parent
sys.path.insert(0, str(WORKBENCH / "pipeline"))
import labdb  # noqa: E402
import testsets  # noqa: E402

TARGET = "competitors"
NOTE = ("Flat merge of the competitor test sets (owner message of "
        "2026-09-30T18:45:00+0300). The set mixes the evidence tiers scored and "
        "provisional. A photo goes to every place that a source set gave it. "
        "extra.merged_from holds the source rows.")


class MergeError(Exception):
    pass


def source_sets(snapshot):
    """Return set name -> {(place, file_name): manifest row} for each snapshot set."""
    sets = {}
    for manifest in sorted(Path(snapshot).glob("*/manifest.jsonl")):
        rows = {}
        for line in manifest.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                rows[(row["place"], row["file_name"])] = row
        sets[manifest.parent.name] = rows
    return sets


def load_rows(conn, manifests):
    """Return the database rows of the source sets that the database holds."""
    names = sorted(name for name in manifests if conn.execute(
        "SELECT 1 FROM test_set WHERE set_name = ?", (name,)).fetchone())
    rows = []
    for name in names:
        for place, file_name, digest, label, delete, extra, width, height in conn.execute(
                "SELECT p.place, p.file_name, p.sha256, p.label, p.marked_delete, p.extra, "
                "i.width, i.height FROM test_photo p JOIN image i ON i.sha256 = p.sha256 "
                "WHERE p.set_name = ? ORDER BY p.place, p.file_name", (name,)):
            manifest = manifests[name].get((place, file_name))
            rows.append({
                "set_name": name, "place": place, "file_name": file_name,
                "sha256": digest, "label": label, "marked_delete": delete,
                "extra": json.loads(extra) if extra else None,
                "area": (width or 0) * (height or 0),
                # A row that the Testset page added has no manifest row; its SHA-256
                # alone groups it.
                "stem": (Path(manifest["source_image_path"]).stem if manifest else None),
            })
    return names, rows


def group_photos(rows):
    """Return the lists of rows that show one source photo (same SHA-256 or stem)."""
    parent = {}

    def find(key):
        parent.setdefault(key, key)
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    for row in rows:
        find("sha:" + row["sha256"])
        if row["stem"]:
            parent[find("sha:" + row["sha256"])] = find("stem:" + row["stem"])
    groups = defaultdict(list)
    for row in rows:
        groups[find("sha:" + row["sha256"])].append(row)
    return sorted(groups.values(), key=lambda g: min(r["sha256"] for r in g))


def merge(rows):
    """Return the rows of the flat set: one row per photo and place."""
    out = []
    for group in group_photos(rows):
        best = max(group, key=lambda r: (r["area"], r["sha256"]))
        file_name = min(r["file_name"] for r in group if r["sha256"] == best["sha256"])
        places = defaultdict(list)
        for row in group:
            places[row["place"]].append(row)
        for place, sources in sorted(places.items()):
            labels = {r["label"] for r in sources}
            if len(labels) != 1:
                raise MergeError("the photo %s holds the labels %s at the place %s"
                                 % (file_name, sorted(labels, key=str), place))
            out.append({
                "place": place, "file_name": file_name, "sha256": best["sha256"],
                "label": labels.pop(),
                "marked_delete": max(r["marked_delete"] for r in sources),
                "extra": {"merged_from": [
                    {key: r[key] for key in ("set_name", "place", "file_name", "sha256",
                                             "label", "extra")}
                    for r in sorted(sources, key=lambda r: (r["set_name"], r["file_name"]))
                ]},
            })
    return out


def backup(conn, db_path):
    folder = labdb.backups_dir(db_path)
    os.makedirs(folder, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(folder, "catalog-before-competitor-merge-%s.sqlite3" % stamp)
    target = sqlite3.connect(path)
    try:
        conn.backup(target)
    finally:
        target.close()
    return path


def write(conn, names, merged, target=TARGET):
    """Make the set `target` and remove the source sets in one transaction."""
    with conn:
        testsets.create_set(conn, target)
        conn.execute("UPDATE test_set SET label_note = ? WHERE set_name = ?", (NOTE, target))
        conn.executemany(
            "INSERT INTO test_photo (set_name, place, file_name, sha256, label, "
            "marked_delete, extra) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(target, r["place"], r["file_name"], r["sha256"], r["label"],
              r["marked_delete"], json.dumps(r["extra"], ensure_ascii=False, sort_keys=True))
             for r in merged])
        for name in names:
            # `test_photo_comment` follows `test_photo` with ON DELETE CASCADE.
            conn.execute("DELETE FROM test_photo WHERE set_name = ?", (name,))
            conn.execute("DELETE FROM test_variant WHERE set_name = ?", (name,))
            conn.execute("DELETE FROM test_set WHERE set_name = ?", (name,))


def summary(names, rows, merged):
    return {
        "source_sets": names,
        "source_rows": len(rows),
        "photos": len({r["sha256"] for r in merged}),
        "rows": len(merged),
        "labels": dict(sorted(Counter(r["label"] for r in merged).items())),
        "photos_in_more_than_one_place": sum(
            1 for count in Counter(r["sha256"] for r in merged).values() if count > 1),
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", default=str(WORKBENCH / "data/catalog/catalog.sqlite3"))
    parser.add_argument("--snapshot", default=str(WORKBENCH / "data/competitor-testsets"))
    parser.add_argument("--dry-run", action="store_true",
                        help="print the result and write nothing")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    conn = labdb.connect(args.db)
    try:
        if conn.execute("SELECT 1 FROM test_set WHERE set_name = ?", (TARGET,)).fetchone():
            raise MergeError("the test set %s exists already" % TARGET)
        names, rows = load_rows(conn, source_sets(args.snapshot))
        if not names:
            raise MergeError("the database holds no set of %s" % args.snapshot)
        merged = merge(rows)
        report = summary(names, rows, merged)
        if not args.dry_run:
            report["backup"] = backup(conn, args.db)
            write(conn, names, merged)
        report["dry_run"] = args.dry_run
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except MergeError as exc:
        sys.exit("merge_competitor_testsets: %s" % exc)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
