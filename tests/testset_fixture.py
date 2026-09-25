"""The fixture of the tests of plan 12: a database with the test set tables, and a set.

The file `pipeline/schema_pending/NNN_testset.sql` enters `pipeline/schema/` only after
the flat image store of drink-atlas-workspace-9a [f028b4] (rules 25 to 28 of AGENTS.md).
Until then the tests build a schema directory of their own:

1. every file of `pipeline/schema/`;
2. when those files do not drop the column `image.folder` yet, one file that does it,
   as the flat store will;
3. the pending file of the test sets.

When `pipeline/imagestore.py` has no `path_of` yet, the fixture adds the function of the
planned interface: `<directory of the database>/images/<sha256>.<extension>`.
"""
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(1, str(ROOT / "scripts"))
import imagestore  # noqa: E402
import labdb  # noqa: E402

PENDING = ROOT / "pipeline" / "schema_pending" / "NNN_testset.sql"


def _path_of(db_path, sha256, extension):
    return os.path.join(os.path.dirname(os.path.abspath(db_path)), "images",
                        "%s.%s" % (sha256, extension))


if not hasattr(imagestore, "path_of"):
    imagestore.path_of = _path_of


def schema_dir(root):
    """Return a schema directory with the files of the database of plan 12."""
    target = Path(root) / "schema"
    target.mkdir()
    files = labdb.schema_files()
    for _, path in files:
        shutil.copy(path, target / os.path.basename(path))
    number = len(files)
    text = "".join(Path(path).read_text(encoding="utf-8") for _, path in files)
    if "DROP COLUMN folder" not in text:
        number += 1
        (target / ("%03d_flat_store_emulation.sql" % number)).write_text(
            "ALTER TABLE image DROP COLUMN folder;\n", encoding="utf-8")
    number += 1
    shutil.copy(PENDING, target / ("%03d_testset.sql" % number))
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
