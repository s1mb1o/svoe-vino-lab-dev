"""Copy the catalogue directory for the matcher (plan 75, stage 2).

The copy holds `catalog.sqlite3`, and for each selected embedding `embeddings/<name>/`
with `index.json`, the vector file that the index names, and the cluster files. Unless
`images` is false, it also holds `images/` and `cuts/`. It holds no prepared PNG file, no
log, and no lock. `copy.json` records the counts. The matcher reads the copy with
`matcher/catalog.py`; the copy replaces the bundle build of plan 72.

A plain file copy of the live directory is not safe: the journal mode of the database is
`delete`, so a copy during a write can hold a part of a transaction, and a copy during a
build can take an `index.json` that names a deleted vector file. So the script copies the
database with the SQLite backup API, refuses a copy during a build, and reads the index
again after the copy of its vector file.
"""

import collections
from contextlib import closing
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import time

import embeddings


REPO = Path(__file__).resolve().parents[2]
DATABASE = "catalog.sqlite3"
MANIFEST = "copy.json"
CLUSTER_FILES = ("clusters.json", "cluster-rules.json", "cluster-notes.json")
# The directories of the catalogue with image files. The files never change: the name of
# a file is the SHA-256 of its bytes. So a hard link is a safe copy.
IMAGE_DIRS = ("images", "cuts")


class CopyError(ValueError):
    """The lab data do not allow a copy."""


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def selected_names(settings, names):
    """Return the names to copy: `names`, or each valid embedding that has an index."""
    if names:
        return list(dict.fromkeys(names))
    return [name for name, embedding, _ in settings.entries if embedding is not None
            and embeddings.read_index(embeddings.entry_dir(settings.db_path, name))]


def check(settings, names):
    """Return name -> counts of each selected embedding. Raise CopyError.

    Each item of the index MUST be a current item: the matcher uses each item of the
    index, so a stale item would reach it with an old vector. Missing and failed items
    only lower the counts.
    """
    with closing(embeddings.open_database(settings.db_path)) as conn:
        _, sources = embeddings.read_inputs(conn, settings.db_path)
    report = {}
    for name in names:
        try:
            embedding = settings.find(name)
        except KeyError as exc:
            raise CopyError("unknown embedding: %s" % name) from exc
        except embeddings.ConfigError as exc:
            raise CopyError("the embedding %s is not valid: %s" % (name, exc)) from exc
        directory = embeddings.entry_dir(settings.db_path, name)
        if embeddings.running_pid(directory):
            raise CopyError("a build of %s runs; copy after it" % name)
        try:
            index = embeddings.read_index(directory)
        except ValueError as exc:
            raise CopyError("the index of %s cannot be read: %s" % (name, exc)) from exc
        if index is None:
            raise CopyError("the embedding %s has no index" % name)
        items = embeddings.plan_items(embedding, sources)
        status = embeddings.item_status(items, index, embeddings.image_names(directory))
        counts = collections.Counter(state for state, _ in status.values())
        current = {key for key, (state, _) in status.items() if state == "current"}
        other = sum((record.get("source_sha256"), record.get("view")) not in current
                    for record in index.get("items", []))
        if other:
            raise CopyError("the index of %s holds %d items that are not current (%d stale); "
                            "build the embedding again, then copy" % (name, other,
                                                                      counts["stale"]))
        report[name] = {"items": len(index.get("items", [])), "current": counts["current"],
                        "missing": counts["missing"], "failed": counts["failed"]}
    return report


def _link_or_copy(source, target):
    try:
        os.link(source, target)
    except OSError:
        shutil.copy2(source, target)


def _copy_embedding(source, target, name):
    target.mkdir(parents=True)
    before = (source / embeddings.INDEX).read_bytes()
    vectors = json.loads(before).get("vectors_file")
    if not isinstance(vectors, str) or not embeddings.VECTORS_RE.match(vectors):
        raise CopyError("the index of %s names no valid vector file" % name)
    try:
        shutil.copy2(source / vectors, target / vectors)
    except FileNotFoundError as exc:
        raise CopyError("the vector file of %s changed during the copy; copy again"
                        % name) from exc
    if (source / embeddings.INDEX).read_bytes() != before:
        raise CopyError("the index of %s changed during the copy; copy again" % name)
    (target / embeddings.INDEX).write_bytes(before)
    for file_name in CLUSTER_FILES:
        if (source / file_name).is_file():
            shutil.copy2(source / file_name, target / file_name)


def _copy_images(catalog, target):
    count = 0
    for relative in IMAGE_DIRS:
        for directory, _, file_names in os.walk(catalog / relative):
            for file_name in sorted(file_names):
                if file_name.startswith("."):
                    continue
                source = Path(directory) / file_name
                destination = target / source.relative_to(catalog)
                destination.parent.mkdir(parents=True, exist_ok=True)
                _link_or_copy(source, destination)
                count += 1
    return count


def _load_with_matcher(directory, name):
    """Load one embedding of the copy with the reader of the matcher. Raise CopyError."""
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from matcher.catalog import CatalogError, load_catalog

    try:
        return load_catalog(directory, name)
    except CatalogError as exc:
        raise CopyError("the matcher cannot read the copy of %s: %s" % (name, exc)) from exc


def copy_catalog(config_path, out, names=None, images=True):
    """Check the lab data, write the copy into the new directory `out`, and return the
    content of `copy.json` with the path. Raise CopyError."""
    out = Path(out).absolute()
    if out.exists() or out.is_symlink():
        raise CopyError("the output path exists: %s" % out)
    settings = embeddings.load_settings(config_path)
    names = selected_names(settings, names)
    if not names:
        raise CopyError("no embedding to copy")
    report = check(settings, names)
    database = Path(settings.db_path).absolute()
    catalog = database.parent
    out.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".%s." % out.name, dir=out.parent))
    try:
        with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as source, \
                closing(sqlite3.connect(temporary / DATABASE)) as target:
            source.backup(target)
            version = target.execute("PRAGMA user_version").fetchone()[0]
        for name in names:
            _copy_embedding(Path(embeddings.entry_dir(settings.db_path, name)),
                            temporary / "embeddings" / name, name)
        image_files = _copy_images(catalog, temporary) if images else 0
        for name in names:
            bundle = _load_with_matcher(temporary, name)
            report[name].update(wines=len(bundle.slugs),
                                rows={view: int(len(pair[1]))
                                      for view, pair in sorted(bundle.views.items())})
        manifest = {"created_at": now(), "database": str(database),
                    "schema_version": version, "images": bool(images),
                    "image_files": image_files, "embeddings": report}
        (temporary / MANIFEST).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
            encoding="utf-8")
        if out.exists() or out.is_symlink():
            raise CopyError("the output path appeared during the copy: %s" % out)
        temporary.rename(out)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return dict(manifest, path=str(out))
