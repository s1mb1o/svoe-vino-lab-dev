"""The lab server: the Dataset page on the lab database.

The server reads two keys of `config.yaml`: `rootdir` and `database_file`. It opens
the database for each request and checks the schema version. It serves the Dataset
page and `GET /api/dataset` from the tables `wine_catalog` and `wine_image`. A GET
opens the database read-only. `POST /api/wine-state` changes the state of one wine; it
writes the columns `state` and `removed_by` alone. `GET /images/<folder>/<sha256>.<ext>`
sends one file of the image store `images/` next to the database file.

`POST /api/wine` adds one wine by hand, with a slug that starts with `__`, and its `main`
image, with `manual_wines.py`. Read `docs/plans/20_add-wine.md`.

The routes `/api/dataset-gtin` and `/api/dataset-qr-url` add (POST) and remove (DELETE)
one row of the table `wine_code`. The lab keeps GTINs alone: it has no barcode route.
Read `docs/plans/11_wine-codes.md`.

The route `/api/dataset-atlas-binding` sets (POST) and removes (DELETE) the manual
Atlas Core product of one wine in the table `wine_atlas_binding` with
`atlas_bindings.py`. Read `docs/plans/15_atlas-binding.md`.

The route `/api/dataset-comment` adds (POST) and removes (DELETE) one timestamped
comment of a wine in the table `wine_comment` with `comments.py`. Read
`docs/plans/17_wine-comments.md`.

The route `/api/dataset-favorite` marks (POST `"favorite": true`) or unmarks (POST
`"favorite": false`) one wine as a favorite in the table `wine_favorite` with
`favorites.py`. Read `docs/plans/19_favorites.md`.

The route `/api/dataset-patch` stores (POST, the image bytes as the body) and removes
(DELETE) the `main_patched` image of one wine with `patches.py`. Read
`docs/plans/14_patch-editor.md`.

The route `/api/dataset-alternative` stores (POST, the image bytes as the body) and removes
(DELETE) one alternative photo of a wine; `POST /api/dataset-alternative-type` changes its
type. `alternatives.py` does the work. Read `docs/plans/16_alternative-images.md`.

The route `/api/image-description` sets (POST) the values of one image in the table
`image_description` by hand, with `image_descriptions.py`; `GET /api/dataset` sends the
key `image_descriptions`. `GET /api/image-description-status` sends the state of the
watcher and the counts for the indicator of the page. `GET
/api/image-description-reply?sha256=` sends the raw VLM reply of one image from
`data/cache/`, with `describe_images.cached_reply`. `GET /api/image-detail-failures`
sends the images whose detail failed, each with its entries of the watcher log
(`image_descriptions.detail_failures`). When `image_description.watch` of
`config.yaml` is true,
`main` starts the watcher `describe_images.py --watch` and stops it at the exit; a SIGTERM
leads to that exit. Read `docs/plans/26_image-description.md`.

The Embeddings page is on: `embedding_routes.py` answers each of its routes. Read
`docs/plans/10_embeddings-page.md`.

The Clusters page is on: `cluster_routes.py` answers each of its routes. Each cluster
artifact depends on one embedding build and stays in that embedding directory. Read
`docs/plans/30_embedding-clusters.md`.

The website import is on: `website_import_routes.py` answers each of its routes. Read
`docs/plans/21_website-import-ui.md`.

The Runs page is on: `run_routes.py` answers each of its routes. It reads the run
directories of `runs/`; the database does not hold the runs. Read
`docs/plans/23_runs-page.md`.

The Testset page is on at `/testset`: `testset_routes.py` answers each of its routes.
It shows the test sets of the database and writes the labels of their photos; the
database is the source of the labels. `GET /` redirects to `/dataset`. Read
`docs/plans/24_testset-page.md`.

The button `Run>` of `/testset` starts a run of one configuration on the set of the page:
`run_jobs.py` answers `/api/run-configurations` and `/api/run-jobs`, and starts
`run_job.py` as a separate process. Read `docs/plans/32_testset-run-button.md`.

The Health page is on at `/health`: `health.py` answers each of its routes. It shows the
state of the server and checks each endpoint of `config.yaml`. A model that does not run
on its llama-swap gateway gets no call. Read `docs/plans/46_health-page.md`.

Each API route that this text does not name answers HTTP 503 with a JSON error. The
navigation of every page stays as it is. Read `docs/plans/07_sqlite-lab-database.md`.

Usage:
    python3 pipeline/lab_server.py              # http://127.0.0.1:8168/dataset
    python3 pipeline/lab_server.py --no-browser
"""
import argparse
import json
import os
import re
import signal
import sqlite3
import subprocess
import sys
import threading
import time
import traceback
import urllib.parse
import webbrowser
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alternatives  # noqa: E402
import atlas_bindings  # noqa: E402
import cluster_routes  # noqa: E402
import codes  # noqa: E402
import comments  # noqa: E402
import describe_images  # noqa: E402
import embedding_routes  # noqa: E402
import favorites  # noqa: E402
import health  # noqa: E402
import image_descriptions  # noqa: E402
import lab_pages  # noqa: E402
import labdb  # noqa: E402
import manual_wines  # noqa: E402
import patches  # noqa: E402
import run_jobs  # noqa: E402
import run_routes  # noqa: E402
import testset_routes  # noqa: E402
import vlm_config  # noqa: E402
import website_import_routes  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT, "config.yaml")
# Port 8168 is recorded in `/Users/ashmelev/Admin/mbp2023/PORTS_USED.md`. It is apart
# from 8154 of `svoe-vino-testset/scripts/review_server.py`, so both can run.
DEFAULT_PORT = 8168

# The columns of `wine_catalog` that `/api/dataset` sends, in table order.
CATALOG_COLUMNS = ("wine_slug", "name", "producer", "category", "color", "region",
                   "grapes", "description", "csv_photo_name", "state", "removed_by")
# The states of a wine, in the order of the start report.
STATES = ("Active", "Disabled", "Removed")
# The Dataset page reads the key `slug`. The API sends `wine_slug` under that key.
PAGE_KEYS = {"wine_slug": "slug"}

# The pages of the navigation, in the order of the navigation. The owner put `Health`
# last on 2026-09-26T11:02:57+0300.
NAV = (("/dataset", "Dataset"), ("/embedding", "Embeddings"),
       ("/clusters", "Clusters"), ("/testset", "Testset"), ("/runs", "Runs"),
       ("/health", "Health"))
# The disabled pages. `/docs` is the API page of the review tool.
DISABLED_PAGES = {"/docs": "API docs"}
# `GET /` goes to the Dataset page. The owner moved the Testset page to `/testset` on
# 2026-09-25T17:01:44+0300.
HOME = "/dataset"
DISABLED_ERROR = ("disabled for now: the lab database does not hold the data of "
                  "this route yet")
# action -> (the states that allow it, the new state). A removal by a person sets
# `removed_by` = `person`, so the import does not restore the wine.
ACTIONS = {
    "disable": (("Active",), "Disabled"),
    "enable": (("Disabled",), "Active"),
    "remove": (("Active", "Disabled"), "Removed"),
    "restore": (("Removed",), "Active"),
}
# The largest body of `POST /api/wine-state`, in bytes.
MAX_BODY = 4096
# The largest body of a POST of a code, in bytes. A QR URL has at most 4096 characters.
MAX_CODE_BODY = 16384
# The largest body of a POST of a comment, in bytes. The JSON form of a comment of
# 4,000 characters MAY need 6 bytes for each character.
MAX_COMMENT_BODY = 32768
# route -> (the kind of `wine_code`, the key of the value in the body and in the query,
# the key of the list of the wine in a record and in an answer).
CODE_ROUTES = {
    "/api/dataset-gtin": ("gtin", "gtin", "gtins"),
    "/api/dataset-qr-url": ("qr_url", "url", "qr_urls"),
}
# kind -> the key of the list of the wine in a record of `/api/dataset`.
CODE_RECORD_KEYS = {kind: "_" + list_key for kind, _key, list_key in CODE_ROUTES.values()}
# The image types of the card: the `main` image and the patch, side by side.
CARD_IMAGE_TYPES = ("main", "main_patched")
# A file of the image store: `/images/<folder>/<sha256>.<extension>`. The name admits no
# other path, so a request cannot read a file outside the store. The folder `testset`
# holds the test photos (schema 016, `import_testset.FOLDER`); the Runs page shows them.
IMAGE_ROUTE = re.compile(r"^/images/(%s)/([0-9a-f]{64}\.([0-9a-z]+))$" % "|".join(
    sorted(set(labdb.IMAGE_FOLDERS.values()) | {labdb.DERIVED_FOLDER, "testset"})))
IMAGE_CONTENT_TYPES = {"webp": "image/webp", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                       "png": "image/png", "gif": "image/gif", "avif": "image/avif",
                       "heic": "image/heic", "tif": "image/tiff", "tiff": "image/tiff"}
# The name of a stored file is the SHA-256 of its bytes, so the file never changes.
IMAGE_CACHE = "public, max-age=31536000, immutable"


class ConfigError(Exception):
    """The configuration or the database does not allow the server to start."""


def load_config(path=CONFIG_PATH):
    """Return the absolute path of the database that `config.yaml` names."""
    try:
        with open(path, encoding="utf-8") as fh:
            config = yaml.safe_load(fh) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError("cannot read %s: %s" % (path, exc))
    database = config.get("database_file")
    if not database:
        raise ConfigError("%s holds no key `database_file`" % path)
    rootdir = config.get("rootdir") or os.path.dirname(ROOT)
    return os.path.abspath(os.path.join(rootdir, database))


def open_database(path, write=False):
    """Open the database, read-only unless `write`. Check the schema version.

    Raise `ConfigError` on a missing file or on a wrong schema version.
    """
    if not os.path.isfile(path):
        raise ConfigError("no database at %s; create it with "
                          "`python3 pipeline/labdb.py %s`" % (path, path))
    conn = sqlite3.connect(Path(path).as_uri() + ("?mode=rw" if write else "?mode=ro"),
                           uri=True)
    try:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        expected = len(labdb.schema_files())
    except Exception:
        conn.close()
        raise
    if version != expected:
        conn.close()
        if version < expected:
            raise ConfigError("the database has schema version %d and this code needs "
                              "version %d; run `python3 pipeline/labdb.py %s`"
                              % (version, expected, path))
        raise ConfigError("the database has schema version %d; this code knows "
                          "version %d" % (version, expected))
    return conn


def state_counts(conn):
    """Return the number of wines of each state, in the order of `STATES`."""
    counts = dict(conn.execute("SELECT state, count(*) FROM wine_catalog GROUP BY state"))
    return {state: counts.get(state, 0) for state in STATES}


def cut_nothing(method, box, width, height):
    """Tell whether a `crop` kept the whole image. Such a file cut nothing away, so the
    card shows the original and no badge. The box is in the pixels of the original after
    its EXIF orientation, so a turned image has width and height the other way round."""
    return (method == "crop" and width is not None and box[:2] == (0, 0)
            and box[2:] in ((width, height), (height, width)))


def card_images(conn):
    """Return wine slug -> the images of the card, as a dict of `CARD_IMAGE_KEYS`.

    The keys `main_image_*` describe the `main` image. The keys `_patch_url`,
    `_patch_image_url`, and `_patch_derivation` describe the `main_patched` image: its
    original, the file that the patch slot shows, and its processing. The owner asked on
    2026-09-25 to see the two side by side, so the patch does not replace the `main`
    image on the card. Each slot shows the processed file of its image when
    `image_derivative` holds one, else the original. A `crop` that cut nothing counts as
    no processing (`cut_nothing`). The size is the size of the file that the card shows.
    A wine with neither image has no key.
    """
    images = {}
    for (slug, image_type, match, digest, folder, extension, width, height, derivation,
         p_digest, p_folder, p_extension, p_width, p_height, *box) in conn.execute(
            "SELECT w.wine_slug, w.image_type, w.match_method, o.sha256, o.folder, "
            "o.extension, o.width, o.height, d.method, p.sha256, p.folder, p.extension, "
            "p.width, p.height, d.box_left, d.box_top, d.box_right, d.box_bottom "
            "FROM wine_image w "
            "JOIN image o ON o.sha256 = w.sha256 "
            "LEFT JOIN image_derivative d ON d.source_sha256 = w.sha256 "
            "AND d.kind = 'package' "
            "LEFT JOIN image p ON p.sha256 = d.sha256 "
            "WHERE w.image_type IN (%s)" % ", ".join("?" for _ in CARD_IMAGE_TYPES),
            CARD_IMAGE_TYPES):
        original = "/images/%s/%s.%s" % (folder, digest, extension)
        shown, method = original, None
        if p_digest is not None and not cut_nothing(derivation, tuple(box), width, height):
            shown = "/images/%s/%s.%s" % (p_folder, p_digest, p_extension)
            width, height, method = p_width, p_height, derivation
        image = images.setdefault(slug, dict.fromkeys(CARD_IMAGE_KEYS))
        if image_type == "main":
            image.update({
                "main_image_url": shown, "main_image_original_url": original,
                "main_image_derivation": method, "main_image_type": image_type,
                "main_image_match_method": match,
                "main_image_width": width, "main_image_height": height})
        else:
            image.update({"_patch_url": original, "_patch_image_url": shown,
                          "_patch_derivation": method})
    return images


# The keys of the card images in each record of `/api/dataset`.
CARD_IMAGE_KEYS = ("main_image_url", "main_image_original_url", "main_image_derivation",
                   "main_image_type", "main_image_match_method", "main_image_width",
                   "main_image_height", "_patch_url", "_patch_image_url",
                   "_patch_derivation")


def alternative_images(conn):
    """Return wine slug -> the alternative photos of the wine, in the order of the
    uploads. Each photo is a dict: `sha256`, `type`, `url` (the original), `image_url`
    (the processed file, or the original), and `derivation` (`crop`, `seg`, or None). A
    full type shows its package cut, a label type its label cut (`image_derivative.kind`).
    A `crop` that cut nothing counts as no processing (`cut_nothing`)."""
    photos = {}
    for (wine, image_type, digest, folder, extension, width, height, derivation,
         p_digest, p_folder, p_extension, *box) in conn.execute(
            "SELECT w.wine_slug, w.image_type, o.sha256, o.folder, o.extension, o.width, "
            "o.height, d.method, p.sha256, p.folder, p.extension, d.box_left, d.box_top, "
            "d.box_right, d.box_bottom FROM wine_image w "
            "JOIN image o ON o.sha256 = w.sha256 "
            "LEFT JOIN image_derivative d ON d.source_sha256 = w.sha256 "
            "AND d.kind = CASE WHEN w.image_type LIKE 'label_%%' THEN 'label' "
            "ELSE 'package' END "
            "LEFT JOIN image p ON p.sha256 = d.sha256 "
            "WHERE w.image_type IN (%s) ORDER BY w.rowid"
            % ", ".join("?" for _ in alternatives.TYPES), alternatives.TYPES):
        original = "/images/%s/%s.%s" % (folder, digest, extension)
        shown, method = original, None
        if p_digest is not None and not cut_nothing(derivation, tuple(box), width, height):
            shown = "/images/%s/%s.%s" % (p_folder, p_digest, p_extension)
            method = derivation
        photos.setdefault(wine, []).append({"sha256": digest, "type": image_type,
                                            "url": original, "image_url": shown,
                                            "derivation": method})
    return photos


def wine_codes(conn, slug=None):
    """Return wine slug -> kind -> the values of `wine_code`, in the order of the writes.

    With `slug`, the answer holds that wine alone.
    """
    out = {}
    query = "SELECT wine_slug, kind, value FROM wine_code"
    rows = (conn.execute(query + " WHERE wine_slug = ? ORDER BY rowid", (slug,))
            if slug is not None else conn.execute(query + " ORDER BY rowid"))
    for wine, kind, value in rows:
        out.setdefault(wine, {}).setdefault(kind, []).append(value)
    return out


def code_counts(conn):
    """Return the number of rows of `wine_code` of each kind."""
    counts = dict(conn.execute("SELECT kind, count(*) FROM wine_code GROUP BY kind"))
    return {kind: counts.get(kind, 0) for kind in codes.KINDS}


def dataset_records(conn):
    """Return every wine in import order, in the record shape of the Dataset page.

    The records hold each state. The key `state` tells a removed wine apart. The keys
    of `CARD_IMAGE_KEYS` describe the card image. Each is None for a wine with no card
    image. The size is None for an image that no tool measured. The keys `_gtins` and
    `_qr_urls` hold the values of `wine_code`. `_patched` tells
    whether the wine has a `main_patched` image. `_alternatives` lists the alternative
    photos (`alternative_images`). `_atlas_product_uuid` and
    `_atlas_binding_source` give the effective row of `wine_atlas_binding`, or None.
    `_comments` lists the comments of the wine in time order (`comments.py`).
    `_favorite` tells whether the wine is a favorite (`favorites.py`).
    `_modified_at` and `_website_modified_at` are the two change times of schema 015.
    """
    images = card_images(conn)
    times = {slug: (changed, website) for slug, changed, website in conn.execute(
        "SELECT wine_slug, modified_at, website_modified_at FROM wine_catalog")}
    values = wine_codes(conn)
    atlas = atlas_bindings.bindings(conn)
    notes = comments.comments(conn)
    starred = favorites.favorites(conn)
    photos = alternative_images(conn)
    records = []
    for row in conn.execute("SELECT %s FROM wine_catalog ORDER BY rowid"
                            % ", ".join(CATALOG_COLUMNS)):
        record = {PAGE_KEYS.get(column, column): value
                  for column, value in zip(CATALOG_COLUMNS, row)}
        record.update(images.get(record["slug"]) or dict.fromkeys(CARD_IMAGE_KEYS))
        of_wine = values.get(record["slug"], {})
        record.update({key: of_wine.get(kind, []) for kind, key in CODE_RECORD_KEYS.items()})
        record["_patched"] = record["_patch_url"] is not None
        record["_alternatives"] = photos.get(record["slug"], [])
        product, source = atlas.get(record["slug"], (None, None))
        record.update({"_atlas_product_uuid": product, "_atlas_binding_source": source})
        record["_comments"] = notes.get(record["slug"], [])
        record["_favorite"] = record["slug"] in starred
        record["_modified_at"], record["_website_modified_at"] = times[record["slug"]]
        records.append(record)
    return records


def dataset_view(db_path):
    """Return the answer of `GET /api/dataset`."""
    with closing(open_database(db_path)) as conn:
        records = dataset_records(conn)
        counts = code_counts(conn)
        atlas_total, atlas_manual = atlas_bindings.counts(conn)
        comment_total = comments.count(conn)
        favorite_total = favorites.count(conn)
        descriptions = image_descriptions.descriptions(conn)
    return {
        "database_file": db_path,
        "wine_editor": True,
        "patch_editor": True, "patches": sum(1 for r in records if r["_patched"]),
        "alternative_editor": True,
        "alternatives": sum(len(r["_alternatives"]) for r in records),
        "gtins": counts["gtin"], "qr_urls": counts["qr_url"],
        "atlas_matches_file": "", "atlas_bindings_file": "",
        "atlas_binding_editor": True,
        "atlas_bindings": atlas_total, "atlas_manual_bindings": atlas_manual,
        "comments": comment_total,
        "favorites": favorite_total,
        "image_description_editor": True,
        "image_description_values": image_descriptions.VALUES,
        "image_descriptions": descriptions,
        "records": records,
    }


class StateError(Exception):
    """A state change or a code change is not allowed. `code` is the HTTP status of the
    answer."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def change_state(db_path, slug, action):
    """Apply one action to one wine. Return the new state and `removed_by`."""
    if action not in ACTIONS:
        raise StateError(400, "unknown action %r; use one of: %s"
                         % (action, ", ".join(ACTIONS)))
    if not isinstance(slug, str) or not slug:
        raise StateError(400, "the request holds no wine slug")
    allowed, target = ACTIONS[action]
    with closing(open_database(db_path, write=True)) as conn:
        conn.isolation_level = None
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute("SELECT state FROM wine_catalog WHERE wine_slug = ?",
                               (slug,)).fetchone()
            if row is None:
                raise StateError(404, "no wine with the slug %s" % slug)
            if row[0] not in allowed:
                raise StateError(409, "the wine %s is %s; %s needs %s"
                                 % (slug, row[0], action, " or ".join(allowed)))
            removed_by = "person" if target == "Removed" else None
            conn.execute("UPDATE wine_catalog SET state = ?, removed_by = ? "
                         "WHERE wine_slug = ?", (target, removed_by, slug))
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
    return {"slug": slug, "state": target, "removed_by": removed_by}


def add_wine(db_path, body, segmenter=None):
    """Add the wine of the request `body` by hand. Return the answer of the POST: the new
    record of the wine."""
    with closing(open_database(db_path, write=True)) as conn:
        conn.isolation_level = None
        conn.execute("PRAGMA foreign_keys = ON")
        result = manual_wines.add_wine(conn, db_path, body, segmenter)
        slug = result["slug"]
        record = next(r for r in dataset_records(conn) if r["slug"] == slug)
    answer = {"ok": True, "slug": slug, "record": record}
    if result["warnings"]:
        answer["warning"] = " ".join(result["warnings"])
    return answer


def _code_request(route, slug, value):
    """Check the slug and the value of a code route. Return the kind and the keys."""
    kind, key, list_key = CODE_ROUTES[route]
    if not isinstance(slug, str) or not slug:
        raise StateError(400, "the request holds no wine slug")
    if not isinstance(value, str) or not value.strip():
        raise StateError(400, "the request holds no `%s`" % key)
    return kind, key, list_key


def _code_answer(conn, kind, slug, list_key, **fields):
    """Return the answer of a code route: the values of the wine and the total."""
    answer = {"ok": True, "slug": slug}
    answer.update(fields)
    answer[list_key] = wine_codes(conn, slug).get(slug, {}).get(kind, [])
    answer["total"] = code_counts(conn)[kind]
    return answer


def _code_write(db_path, slug, write):
    """Run `write(conn)` in one write transaction, after the check that the wine exists."""
    with closing(open_database(db_path, write=True)) as conn:
        conn.isolation_level = None
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("BEGIN IMMEDIATE")
        try:
            if conn.execute("SELECT 1 FROM wine_catalog WHERE wine_slug = ?",
                            (slug,)).fetchone() is None:
                raise StateError(404, "no wine with the slug %s" % slug)
            answer = write(conn)
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
    return answer


def add_code(db_path, route, slug, value):
    """Add one value of the kind of `route` to one wine. Return the answer of the POST.

    The value gets the normal form of `codes.py`. A wine of each state allows it.
    """
    kind, key, list_key = _code_request(route, slug, value)
    try:
        clean = codes.clean(kind, value)
    except codes.CodeError as exc:
        raise StateError(400, str(exc))

    def write(conn):
        if conn.execute("SELECT 1 FROM wine_code WHERE wine_slug = ? AND kind = ? "
                        "AND value = ?", (slug, kind, clean)).fetchone():
            raise StateError(409, "the wine %s already has the %s %s" % (slug, key, clean))
        conn.execute("INSERT INTO wine_code (wine_slug, kind, value) VALUES (?, ?, ?)",
                     (slug, kind, clean))
        return _code_answer(conn, kind, slug, list_key, **{key: clean})

    return _code_write(db_path, slug, write)


def remove_code(db_path, route, slug, value):
    """Remove one stored value of the kind of `route` from one wine. Return the answer.

    The value MUST be the stored form, as `/api/dataset` sends it.
    """
    kind, key, list_key = _code_request(route, slug, value)

    def write(conn):
        if not conn.execute("DELETE FROM wine_code WHERE wine_slug = ? AND kind = ? "
                            "AND value = ?", (slug, kind, value)).rowcount:
            raise StateError(404, "the wine %s has no %s %s" % (slug, key, value))
        return _code_answer(conn, kind, slug, list_key, removed=value)

    return _code_write(db_path, slug, write)


def _patch_answer(conn, slug, **fields):
    """Return the answer of a patch route: the new record of the wine and the count."""
    records = dataset_records(conn)
    record = next(r for r in records if r["slug"] == slug)
    answer = {"ok": True, "slug": slug, "patched": record["_patched"],
              "patches": sum(1 for r in records if r["_patched"]), "record": record}
    answer.update(fields)
    return answer


def store_patch(db_path, slug, data, name=None, segmenter=None):
    """Store `data` as the patch of one wine. Return the answer of the POST."""
    with closing(open_database(db_path, write=True)) as conn:
        conn.isolation_level = None
        conn.execute("PRAGMA foreign_keys = ON")
        result = patches.store_patch(conn, db_path, slug, data, name, segmenter)
        answer = _patch_answer(conn, slug, changed=result["changed"])
        if result["warnings"]:
            answer["warning"] = " ".join(result["warnings"])
    return answer


def remove_patch(db_path, slug):
    """Remove the patch of one wine. Return the answer of the DELETE."""
    with closing(open_database(db_path, write=True)) as conn:
        conn.isolation_level = None
        conn.execute("PRAGMA foreign_keys = ON")
        result = patches.remove_patch(conn, slug)
        return _patch_answer(conn, slug, removed=result["sha256"])


def _alternative_request(db_path, slug, work):
    """Run `work(conn)` on a write connection. Return the answer of an alternative
    route: the fields of `work`, the new record of the wine, and the count."""
    with closing(open_database(db_path, write=True)) as conn:
        conn.isolation_level = None
        conn.execute("PRAGMA foreign_keys = ON")
        result = work(conn)
        records = dataset_records(conn)
    answer = {"ok": True, "slug": slug,
              "record": next(r for r in records if r["slug"] == slug),
              "alternatives": sum(len(r["_alternatives"]) for r in records)}
    warnings = result.pop("warnings", None)
    answer.update(result)
    if warnings:
        answer["warning"] = " ".join(warnings)
    return answer


def store_alternative(db_path, slug, data, name=None, segmenter=None):
    """Store `data` as an alternative photo of one wine. Return the answer of the POST."""
    return _alternative_request(db_path, slug, lambda conn: alternatives.store_alternative(
        conn, db_path, slug, data, name, segmenter))


def set_alternative_type(db_path, slug, digest, image_type, segmenter=None):
    """Change the type of one alternative photo. Return the answer of the POST."""
    return _alternative_request(db_path, slug, lambda conn: alternatives.set_type(
        conn, db_path, slug, digest, image_type, segmenter))


def remove_alternative(db_path, slug, digest):
    """Remove one alternative photo. Return the answer of the DELETE."""
    return _alternative_request(db_path, slug, lambda conn: alternatives.remove_alternative(
        conn, slug, digest))


def _atlas_answer(conn, slug, **fields):
    """Return the answer of the Atlas route: the effective binding and the counts."""
    product, source = atlas_bindings.bindings(conn, slug).get(slug, (None, None))
    total, manual = atlas_bindings.counts(conn)
    answer = {"ok": True, "slug": slug}
    answer.update(fields)
    answer.update({"product_uuid": product, "source": source, "total": total,
                   "manual": manual})
    return answer


def set_atlas_binding(db_path, slug, product_uuid):
    """Set the manual Atlas Core product of one wine. Return the answer of the POST."""
    if not isinstance(slug, str) or not slug:
        raise StateError(400, "the request holds no wine slug")
    try:
        clean = atlas_bindings.clean_uuid(product_uuid)
    except atlas_bindings.BindingError as exc:
        raise StateError(400, str(exc))

    def write(conn):
        atlas_bindings.set_manual(conn, slug, clean)
        return _atlas_answer(conn, slug)

    return _code_write(db_path, slug, write)


def remove_atlas_binding(db_path, slug):
    """Remove the manual Atlas Core product of one wine. Return the answer of the DELETE.

    The answer gives the binding after the remove: the automatic row, or None.
    """
    if not isinstance(slug, str) or not slug:
        raise StateError(400, "the request holds no wine slug")

    def write(conn):
        removed = atlas_bindings.remove_manual(conn, slug)
        if removed is None:
            raise StateError(404, "the wine %s has no manual Atlas binding" % slug)
        return _atlas_answer(conn, slug, removed=removed)

    return _code_write(db_path, slug, write)


def _comment_answer(conn, slug, **fields):
    """Return the answer of the comment route: the comments of the wine and the total."""
    answer = {"ok": True, "slug": slug}
    answer.update(fields)
    answer.update({"comments": comments.comments(conn, slug).get(slug, []),
                   "total": comments.count(conn)})
    return answer


def add_comment(db_path, slug, text, source="user"):
    """Add one comment to one wine. Return the answer of the POST.

    The Dataset page sends no source, so its comments get `user`. A script sends
    `script`. A wine of each state allows a comment.
    """
    if not isinstance(slug, str) or not slug:
        raise StateError(400, "the request holds no wine slug")
    try:
        comments.check_source(source)
        clean = comments.clean_text(text)
    except comments.CommentError as exc:
        raise StateError(400, str(exc))

    def write(conn):
        return _comment_answer(conn, slug, comment=comments.add(conn, slug, clean, source))

    return _code_write(db_path, slug, write)


def remove_comment(db_path, slug, comment_id):
    """Remove one comment of one wine. Return the answer of the DELETE.

    `comment_id` is the text of the query parameter `id`.
    """
    if not isinstance(slug, str) or not slug:
        raise StateError(400, "the request holds no wine slug")
    if not (isinstance(comment_id, str) and comment_id.isascii() and comment_id.isdigit()
            and len(comment_id) <= 18):
        raise StateError(400, "the request holds no valid comment `id`")
    number = int(comment_id)

    def write(conn):
        if comments.remove(conn, slug, number) is None:
            raise StateError(404, "the wine %s has no comment %d" % (slug, number))
        return _comment_answer(conn, slug, removed=number)

    return _code_write(db_path, slug, write)


def set_favorite(db_path, slug, on):
    """Mark one wine as a favorite, or remove the mark. Return the answer of the POST.

    `on` MUST be a JSON boolean. A wine of each state allows it.
    """
    if not isinstance(slug, str) or not slug:
        raise StateError(400, "the request holds no wine slug")
    if not isinstance(on, bool):
        raise StateError(400, "`favorite` MUST be true or false")

    def write(conn):
        favorites.set_favorite(conn, slug, on)
        return {"ok": True, "slug": slug, "favorite": on, "total": favorites.count(conn)}

    return _code_write(db_path, slug, write)


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def set_image_description(db_path, sha256, values):
    """Set values of one image by hand. Return the answer of the POST.

    `values` holds 1 to 4 fields of `image_descriptions.FIELDS`. A value is a value of its
    field, or null to clear it. A field that `values` does not hold stays as it is. The
    image MUST be linked to a wine (`image_descriptions.is_linked`).
    """
    if not isinstance(sha256, str) or not SHA256_RE.match(sha256):
        raise StateError(400, "`sha256` MUST be 64 lower-case hex digits")
    if not isinstance(values, dict) or not values:
        raise StateError(400, "`values` MUST hold 1 to 4 fields")
    try:
        checked = {field: image_descriptions.check_value(field, value)
                   for field, value in values.items()}
    except image_descriptions.DescriptionError as exc:
        raise StateError(400, str(exc))
    with closing(open_database(db_path, write=True)) as conn:
        conn.isolation_level = None
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("BEGIN IMMEDIATE")
        try:
            if not image_descriptions.is_linked(conn, sha256):
                raise StateError(404, "no wine image with the sha256 %s" % sha256)
            row = image_descriptions.set_values(conn, sha256, checked)
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
    return {"ok": True, "sha256": sha256, "description": row}


def image_description_status(db_path):
    """Return the answer of `GET /api/image-description-status`: the state of the watcher
    (`image_descriptions.watcher_status`) and the counts of the linked images."""
    with closing(open_database(db_path)) as conn:
        return image_descriptions.watcher_status(conn)


def image_description_reply(db_path, config_path, sha256):
    """Return the answer of `GET /api/image-description-reply`: the `model_cache` record
    of the VLM call that described one image (`describe_images.cached_reply`), with the
    request fields and the reply as the service sent it. `found` is False when the VLM
    has not filled the row, or when no record matches."""
    if not isinstance(sha256, str) or not SHA256_RE.match(sha256):
        raise StateError(400, "`sha256` MUST be 64 lower-case hex digits")
    with closing(open_database(db_path)) as conn:
        image = conn.execute("SELECT folder, extension FROM image WHERE sha256 = ?",
                             (sha256,)).fetchone()
        row = image_descriptions.description(conn, sha256)
    if image is None:
        raise StateError(404, "no image with the sha256 %s" % sha256)
    answer = {"ok": True, "sha256": sha256, "found": False}
    if not row or not row["vlm_at"]:
        return dict(answer, reason="the VLM has not filled this image")
    try:
        with open(config_path or CONFIG_PATH, encoding="utf-8") as fh:
            config = yaml.safe_load(fh) or {}
        cfg = describe_images.settings(config)
        entry = vlm_config.entry(config, row["vlm_name"] or cfg["vlm"])
    except (OSError, ValueError, yaml.YAMLError, vlm_config.VlmConfigError) as exc:
        raise ConfigError("cannot read the vlm entry: %s" % exc)
    path = os.path.join(labdb.image_store(db_path), image[0], "%s.%s" % (sha256, image[1]))
    try:
        record = describe_images.cached_reply(entry, path, row, cfg["max_side"])
    except OSError as exc:
        return dict(answer, reason="cannot read the image file: %s" % exc)
    if record is None:
        return dict(answer, reason="no record in data/cache/ matches this image")
    return dict(answer, found=True, key=record.get("key"), created=record.get("created"),
                ms=record.get("ms"), request=record.get("request"), reply=record["answer"])


def image_detail_failures(db_path):
    """Return the answer of `GET /api/image-detail-failures`: the failed details and
    their entries of WATCHER_LOG (`image_descriptions.detail_failures`)."""
    with closing(open_database(db_path)) as conn:
        return image_descriptions.detail_failures(conn, WATCHER_LOG)


def disabled_page(route):
    """Return the notice page of a disabled route."""
    name = DISABLED_PAGES[route]
    nav = "".join('<a%s href="%s">%s</a>' % (' class="on"' if href == route else "",
                                              href, label) for href, label in NAV)
    return (lab_pages.page("disabled.html")
            .replace("__PAGE__", name).replace("__NAV__", nav))


class Handler(BaseHTTPRequestHandler):
    server_version = "svoe-vino-lab/1"

    def log_message(self, fmt, *args):
        if self.path.startswith("/api/"):
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, code, body, ctype, cache="no-store"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", cache)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def _json(self, code, value):
        self._send(code, json.dumps(value, ensure_ascii=False),
                   "application/json; charset=utf-8")

    def _embedding(self):
        """Send the answer of `embedding_routes.respond`."""
        code, body, ctype, cache = embedding_routes.respond(self.server, self.command,
                                                            self.path)
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False)
        self._send(code, body, ctype, cache)

    def _clusters(self):
        """Send the answer of `cluster_routes.respond`."""
        def read_body(limit):
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                return None
            return self.rfile.read(length) if 0 < length <= limit else None

        code, body, ctype, cache = cluster_routes.respond(
            self.server, self.command, self.path, read_body)
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False)
        self._send(code, body, ctype, cache)

    def _website_import(self):
        """Send the answer of `website_import_routes.respond`."""
        def read_body(limit):
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                return None
            return self.rfile.read(length) if 0 < length <= limit else None

        code, body, ctype, cache = website_import_routes.respond(
            self.server, self.command, self.path, read_body)
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False)
        self._send(code, body, ctype, cache)

    def _runs(self):
        """Send the answer of `run_routes.respond`. The catalogue image of a slug follows
        the rule of `card_images`."""
        code, body, ctype, cache = run_routes.respond(self.server, self.command, self.path,
                                                      card_images)
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False)
        self._send(code, body, ctype, cache)

    def _run_jobs(self):
        """Send the answer of `run_jobs.respond` (plan 32)."""
        def read_body(limit):
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                return None
            return self.rfile.read(length) if 0 < length <= limit else None

        try:
            code, body, ctype, cache = run_jobs.respond(self.server, self.command,
                                                        self.path, read_body)
        except (ConfigError, sqlite3.Error) as exc:
            code, body, ctype, cache = 503, {"error": str(exc)}, run_jobs.JSON, "no-store"
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False)
        self._send(code, body, ctype, cache)

    def _testset(self):
        """Send the answer of `testset_routes.respond`. The catalogue image of a slug
        follows the rule of `card_images`."""
        def read_body(limit):
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                return None
            return self.rfile.read(length) if 0 < length <= limit else None

        try:
            code, body, ctype, cache = testset_routes.respond(
                self.server, self.command, self.path, read_body, open_database, card_images)
        except (ConfigError, sqlite3.Error) as exc:
            code, body, ctype, cache = 503, {"error": str(exc)}, testset_routes.JSON_TYPE, \
                "no-store"
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False)
        self._send(code, body, ctype, cache)

    def _health(self):
        """Send the answer of `health.respond` (plan 46)."""
        def read_body(limit):
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                return None
            return self.rfile.read(length) if 0 < length <= limit else None

        try:
            code, body, ctype, cache = health.respond(self.server, self.command, self.path,
                                                      read_body, WATCHER_LOG)
        except Exception as exc:  # noqa: BLE001 - the page needs an answer for each error
            traceback.print_exc()
            code, body, ctype, cache = (500, {"error": "internal error: %s" % exc},
                                        health.JSON_TYPE, "no-store")
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False)
        self._send(code, body, ctype, cache)

    def _redirect(self, location):
        self.send_response(302)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def do_GET(self):
        route = urllib.parse.urlsplit(self.path).path
        if embedding_routes.handles(route):
            self._embedding()
        elif cluster_routes.handles(route):
            self._clusters()
        elif website_import_routes.handles(route):
            self._website_import()
        elif run_routes.handles(route):
            self._runs()
        elif run_jobs.handles(route):
            self._run_jobs()
        elif testset_routes.handles(route):
            self._testset()
        elif health.handles(route):
            self._health()
        elif route == "/":
            self._redirect(HOME)
        elif route == "/dataset" or lab_pages.DATASET_PREVIEW_ROUTE.match(route):
            self._send(200, lab_pages.page("dataset.html"), "text/html; charset=utf-8")
        elif route == "/api/dataset":
            try:
                self._json(200, dataset_view(self.server.db_path))
            except (ConfigError, sqlite3.Error) as exc:
                self._json(503, {"error": str(exc)})
        elif route in DISABLED_PAGES:
            self._send(503, disabled_page(route), "text/html; charset=utf-8")
        elif route == "/api/image-description-status":
            try:
                self._json(200, image_description_status(self.server.db_path))
            except (ConfigError, sqlite3.Error) as exc:
                self._json(503, {"error": str(exc)})
        elif route == "/api/image-detail-failures":
            try:
                self._json(200, image_detail_failures(self.server.db_path))
            except (ConfigError, sqlite3.Error) as exc:
                self._json(503, {"error": str(exc)})
        elif route == "/api/image-description-reply":
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            try:
                self._json(200, image_description_reply(
                    self.server.db_path, self.server.config_path,
                    (query.get("sha256") or [None])[0]))
            except StateError as exc:
                self._json(exc.code, {"error": str(exc)})
            except (ConfigError, sqlite3.Error) as exc:
                self._json(503, {"error": str(exc)})
        elif route.startswith("/api/") or route.startswith("/openapi."):
            self._json(503, {"error": DISABLED_ERROR})
        elif route.startswith("/img/"):
            self._send(503, DISABLED_ERROR, "text/plain; charset=utf-8")
        elif route.startswith("/images/"):
            self._image(route)
        else:
            self._send(404, "not found", "text/plain; charset=utf-8")

    do_HEAD = do_GET

    def _image(self, route):
        """Send one file of the image store, or 404."""
        match = IMAGE_ROUTE.match(route)
        if not match:
            self._send(404, "not found", "text/plain; charset=utf-8")
            return
        folder, name, extension = match.groups()
        path = os.path.join(labdb.image_store(self.server.db_path), folder, name)
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            self._send(404, "not found", "text/plain; charset=utf-8")
            return
        self._send(200, data, IMAGE_CONTENT_TYPES.get(extension, "application/octet-stream"),
                   IMAGE_CACHE)

    def _json_body(self, limit):
        """Return the JSON object of the body, or send HTTP 400 and return None."""
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        if length <= 0 or length > limit:
            self._json(400, {"error": "the body MUST be JSON of at most %d bytes" % limit})
            return None
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            self._json(400, {"error": "the body is not JSON"})
            return None
        if not isinstance(body, dict):
            self._json(400, {"error": "the body MUST be a JSON object"})
            return None
        try:
            # JSON admits a lone surrogate (`"\ud800"`), SQLite cannot store it.
            json.dumps(body, ensure_ascii=False).encode("utf-8")
        except UnicodeEncodeError:
            self._json(400, {"error": "the body holds a lone surrogate character"})
            return None
        return body

    def _wine_state(self):
        body = self._json_body(MAX_BODY)
        if body is None:
            return
        try:
            self._json(200, change_state(self.server.db_path, body.get("slug"),
                                         body.get("action")))
        except StateError as exc:
            self._json(exc.code, {"error": str(exc)})
        except (ConfigError, sqlite3.Error) as exc:
            self._json(503, {"error": str(exc)})

    def _new_wine(self):
        """Answer `POST /api/wine`."""
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length > manual_wines.MAX_BODY:
            # The body stays unread, so the connection cannot serve a next request.
            self.close_connection = True
            self._json(413, {"error": "the body is larger than %d bytes"
                                      % manual_wines.MAX_BODY})
            return
        body = self._json_body(manual_wines.MAX_BODY)
        if body is None:
            return
        try:
            self._json(200, add_wine(self.server.db_path, body, self.server.segmenter))
        except manual_wines.WineError as exc:
            self._json(exc.code, {"error": str(exc)})
        except (ConfigError, sqlite3.Error) as exc:
            self._json(503, {"error": str(exc)})

    def _code(self, route):
        """Answer a POST or a DELETE of a code route."""
        _kind, key, _list_key = CODE_ROUTES[route]
        if self.command == "POST":
            body = self._json_body(MAX_CODE_BODY)
            if body is None:
                return
            slug, value, action = body.get("slug"), body.get(key), add_code
        else:
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            slug = (query.get("slug") or [None])[0]
            value = (query.get(key) or [None])[0]
            action = remove_code
        try:
            self._json(200, action(self.server.db_path, route, slug, value))
        except StateError as exc:
            self._json(exc.code, {"error": str(exc)})
        except (ConfigError, sqlite3.Error) as exc:
            self._json(503, {"error": str(exc)})

    def _atlas_binding(self):
        """Answer a POST or a DELETE of `/api/dataset-atlas-binding`."""
        if self.command == "POST":
            body = self._json_body(MAX_BODY)
            if body is None:
                return
            call = (set_atlas_binding, body.get("slug"), body.get("product_uuid"))
        else:
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            call = (remove_atlas_binding, (query.get("slug") or [None])[0])
        try:
            self._json(200, call[0](self.server.db_path, *call[1:]))
        except StateError as exc:
            self._json(exc.code, {"error": str(exc)})
        except (ConfigError, sqlite3.Error) as exc:
            self._json(503, {"error": str(exc)})

    def _comment(self):
        """Answer a POST or a DELETE of `/api/dataset-comment`."""
        if self.command == "POST":
            body = self._json_body(MAX_COMMENT_BODY)
            if body is None:
                return
            call = (add_comment, body.get("slug"), body.get("text"),
                    body.get("source", "user"))
        else:
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            call = (remove_comment, (query.get("slug") or [None])[0],
                    (query.get("id") or [None])[0])
        try:
            self._json(200, call[0](self.server.db_path, *call[1:]))
        except StateError as exc:
            self._json(exc.code, {"error": str(exc)})
        except (ConfigError, sqlite3.Error) as exc:
            self._json(503, {"error": str(exc)})

    def _favorite(self):
        """Answer a POST of `/api/dataset-favorite`."""
        body = self._json_body(MAX_BODY)
        if body is None:
            return
        try:
            self._json(200, set_favorite(self.server.db_path, body.get("slug"),
                                         body.get("favorite")))
        except StateError as exc:
            self._json(exc.code, {"error": str(exc)})
        except (ConfigError, sqlite3.Error) as exc:
            self._json(503, {"error": str(exc)})

    def _image_description(self):
        """Answer a POST of `/api/image-description`."""
        body = self._json_body(MAX_BODY)
        if body is None:
            return
        try:
            self._json(200, set_image_description(self.server.db_path, body.get("sha256"),
                                                  body.get("values")))
        except StateError as exc:
            self._json(exc.code, {"error": str(exc)})
        except (ConfigError, sqlite3.Error) as exc:
            self._json(503, {"error": str(exc)})

    def _image_body(self):
        """Return the image bytes of the body. Raise `PatchError` 413 for a body that is
        too large."""
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        if length > patches.MAX_BYTES:
            # The body stays unread, so the connection cannot serve a next request.
            self.close_connection = True
            raise patches.PatchError(413, "the image is larger than %d bytes"
                                     % patches.MAX_BYTES)
        return self.rfile.read(length) if length > 0 else b""

    def _patch(self):
        """Answer a POST or a DELETE of `/api/dataset-patch`."""
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        slug = (query.get("slug") or [None])[0]
        try:
            if self.command == "POST":
                answer = store_patch(self.server.db_path, slug, self._image_body(),
                                     (query.get("name") or [None])[0], self.server.segmenter)
            else:
                answer = remove_patch(self.server.db_path, slug)
            self._json(200, answer)
        except patches.PatchError as exc:
            self._json(exc.code, {"error": str(exc)})
        except (ConfigError, sqlite3.Error) as exc:
            self._json(503, {"error": str(exc)})
        except Exception as exc:  # noqa: BLE001 - the page needs an answer for each error
            traceback.print_exc()
            self._json(500, {"error": "internal error: %s" % exc})

    def _alternative(self, route):
        """Answer the routes of the alternative photos."""
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        slug = (query.get("slug") or [None])[0]
        try:
            if route == "/api/dataset-alternative-type":
                body = self._json_body(MAX_BODY)
                if body is None:
                    return
                answer = set_alternative_type(self.server.db_path, body.get("slug"),
                                              body.get("sha256"), body.get("type"),
                                              self.server.segmenter)
            elif self.command == "POST":
                answer = store_alternative(self.server.db_path, slug, self._image_body(),
                                           (query.get("name") or [None])[0],
                                           self.server.segmenter)
            else:
                answer = remove_alternative(self.server.db_path, slug,
                                            (query.get("sha256") or [None])[0])
            self._json(200, answer)
        except patches.PatchError as exc:
            self._json(exc.code, {"error": str(exc)})
        except (ConfigError, sqlite3.Error) as exc:
            self._json(503, {"error": str(exc)})
        except Exception as exc:  # noqa: BLE001 - the page needs an answer for each error
            traceback.print_exc()
            self._json(500, {"error": "internal error: %s" % exc})

    def _write_route(self):
        route = urllib.parse.urlsplit(self.path).path
        if embedding_routes.handles(route):
            self._embedding()
        elif cluster_routes.handles(route):
            self._clusters()
        elif website_import_routes.handles(route):
            self._website_import()
        elif run_jobs.handles(route):
            self._run_jobs()
        elif testset_routes.handles(route):
            self._testset()
        elif health.handles(route):
            self._health()
        elif route == "/api/wine-state" and self.command == "POST":
            self._wine_state()
        elif route == "/api/wine" and self.command == "POST":
            self._new_wine()
        elif route in CODE_ROUTES and self.command in ("POST", "DELETE"):
            self._code(route)
        elif route == "/api/dataset-patch" and self.command in ("POST", "DELETE"):
            self._patch()
        elif route == "/api/dataset-alternative" and self.command in ("POST", "DELETE"):
            self._alternative(route)
        elif route == "/api/dataset-alternative-type" and self.command == "POST":
            self._alternative(route)
        elif route == "/api/dataset-atlas-binding" and self.command in ("POST", "DELETE"):
            self._atlas_binding()
        elif route == "/api/dataset-comment" and self.command in ("POST", "DELETE"):
            self._comment()
        elif route == "/api/dataset-favorite" and self.command == "POST":
            self._favorite()
        elif route == "/api/image-description" and self.command == "POST":
            self._image_description()
        elif route.startswith("/api/"):
            self._json(503, {"error": DISABLED_ERROR})
        else:
            self._send(404, "not found", "text/plain; charset=utf-8")

    do_POST = do_PUT = do_DELETE = _write_route


def make_server(db_path, host="127.0.0.1", port=DEFAULT_PORT, config_path=None,
                segmenter=None):
    """Return the HTTP server. The caller runs `serve_forever`. The Embeddings page
    reads `config_path`, or the `config.yaml` of the project when it is None. A patch
    and an alternative photo go to `segmenter`, the SAM3 client; None means
    `derive.Sam3Client()`."""
    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    server.db_path = db_path
    server.config_path = config_path
    server.segmenter = segmenter
    # The start time that the Health page shows.
    server.started_t = time.time()
    return server


WATCHER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "describe_images.py")
WATCHER_LOG = os.path.join(ROOT, "work", "describe_images.log")


def start_watcher(config_path):
    """Start the watcher of the image descriptions when `image_description.watch` of the
    configuration is true. Return the process, or None. The watcher stops by itself when
    this process is gone (`--parent-pid`)."""
    try:
        with open(config_path, encoding="utf-8") as fh:
            config = yaml.safe_load(fh) or {}
    except (OSError, yaml.YAMLError):
        return None
    section = config.get("image_description")
    if not isinstance(section, dict) or section.get("watch") is not True:
        return None
    os.makedirs(os.path.dirname(WATCHER_LOG), exist_ok=True)
    with open(WATCHER_LOG, "a", encoding="utf-8") as log:
        return subprocess.Popen(
            [sys.executable, WATCHER, "--watch", "--parent-pid", str(os.getpid()),
             "--config", os.path.abspath(config_path)],
            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True)


def stop_watcher(process):
    """Stop the watcher process, if it runs."""
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


def _stop_on_sigterm(signum, frame):
    """A SIGTERM ends `serve_forever` as Ctrl+C does, so the `finally` block runs."""
    raise KeyboardInterrupt


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="The lab server: the Dataset page on the lab database.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--config", default=CONFIG_PATH, help="path of config.yaml")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)
    # A log file gets each line of the start report at once, not at exit.
    sys.stdout.reconfigure(line_buffering=True)

    try:
        db_path = load_config(args.config)
        with closing(open_database(db_path)) as conn:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            states = state_counts(conn)
    except (ConfigError, sqlite3.Error) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1

    print("config: %s" % os.path.abspath(args.config))
    print("database_file: %s" % db_path)
    print("schema version: %d" % version)
    print("wines: %d (%s)" % (sum(states.values()),
                              ", ".join("%s %d" % item for item in states.items())))
    if not sum(states.values()):
        print("  the catalogue is empty; import it with `python3 pipeline/import_catalog.py`")
    print("disabled pages: %s" % ", ".join(DISABLED_PAGES.values()))

    try:
        server = make_server(db_path, args.host, args.port, args.config)
    except OSError as exc:
        print("error: cannot listen on %s:%d: %s" % (args.host, args.port, exc),
              file=sys.stderr)
        return 1
    url = "http://%s:%d/dataset" % (args.host, args.port)
    print("lab server: %s   (Ctrl+C to stop)" % url)
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    watcher = start_watcher(args.config)
    if watcher is not None:
        print("image description watcher: pid %d, log %s" % (watcher.pid, WATCHER_LOG))
    signal.signal(signal.SIGTERM, _stop_on_sigterm)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        server.server_close()
        stop_watcher(watcher)
    return 0


if __name__ == "__main__":
    sys.exit(main())
