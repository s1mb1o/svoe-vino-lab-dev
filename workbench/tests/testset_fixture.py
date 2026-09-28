"""The fixture of the tests of plan 12: a database with the test set tables, and a set.

The tests use a schema directory of their own with every file of `pipeline/schema/`.
The tables of the test sets are in `pipeline/schema/016_testset.sql`.
"""
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(1, str(ROOT / "scripts"))
import labdb  # noqa: E402


def schema_dir(root):
    """Return a schema directory with the files of the database of plan 12."""
    target = Path(root) / "schema"
    target.mkdir()
    for _, path in labdb.schema_files():
        shutil.copy(path, target / os.path.basename(path))
    return str(target)


def make_database(root, slugs=("wine-a", "wine-b", "wine-c")):
    """Create the database at `<root>/data/lab.sqlite3` with the wines `slugs`."""
    db = Path(root) / "data" / "lab.sqlite3"
    db.parent.mkdir(parents=True)
    directory = schema_dir(root)
    conn = labdb.connect(str(db), create=True, directory=directory)
    with conn:
        conn.executemany(
            "INSERT INTO wine_catalog (wine_slug, name, producer, category, color, region, "
            "description, csv_photo_name) VALUES (?, 'n', 'p', 'c', 'co', 'r', 'd', 'x.webp')",
            [(slug,) for slug in slugs])
    conn.close()
    return str(db), directory


def write_set(root, photos, labels, excluded=None, groups=None, name="set"):
    """Write a set directory. `photos` maps "place/file" to bytes; "file" is a loose file."""
    set_dir = Path(root) / name
    for relative, data in photos.items():
        path = set_dir / "photo" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    (set_dir / "photo").mkdir(parents=True, exist_ok=True)
    (set_dir / "review-labels.json").write_text(
        json.dumps({"version": 2, "labels": labels}), encoding="utf-8")
    if excluded is not None:
        (set_dir / "excluded-slugs.json").write_text(
            json.dumps({"excluded": excluded}), encoding="utf-8")
    if groups is not None:
        (set_dir / "variant-groups.json").write_text(
            json.dumps({"groups": [{"slugs": g} for g in groups]}), encoding="utf-8")
    return str(set_dir)
