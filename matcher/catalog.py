"""Read one embedding of a catalogue directory of the lab.

The lab keeps the catalogue in `workbench/data/catalog/` (plan 75 of the workbench), and
`workbench/scripts/copy_catalog.py` makes a consistent copy of it. The matcher reads the
two fixed views `matcher_wine` and `matcher_wine_image` of `catalog.sqlite3`,
`embeddings/<name>/index.json`, and the vector file that the index names. It imports no
workbench code. The result is the same `Bundle` object as the result of `load_bundle`.

One exception reads base tables: `load_codes` reads `wine_code` and the state in
`wine_catalog` for the backend `cascade`. No view of the lab holds the GTINs, and the
owner chose this read on 2026-09-29 (plan 85 of the workbench).
"""

import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import quote, urlsplit, urlunsplit

import numpy as np

from .bundle import CARD_FIELDS, Bundle, infer_sugar


DATABASE = "catalog.sqlite3"
EMBEDDINGS = "embeddings"
INDEX = "index.json"
NAME = re.compile(r"^[a-z0-9][a-z0-9._-]{0,99}$")
VECTORS = re.compile(r"^vectors-[0-9a-f]{8}\.npy$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
WINE_VIEW = "matcher_wine"
WINE_COLUMNS = ("wine_slug", "name", "producer", "category", "region", "color", "grapes",
                "main_source_name", "qr_values")
IMAGE_VIEW = "matcher_wine_image"
IMAGE_COLUMNS = ("wine_slug", "image_type", "sha256", "role")
# The public catalogue pages and images. They are the forms of the bundle builder
# (`workbench/pipeline/matcher_bundle.py`, plan 74).
PAGE_URL_PREFIX = "https://vino-svoe.ru/wines/"
IMAGE_URL_PREFIX = "https://api.vino-svoe.ru/v1/img/str-api/1920/1920/resize/uploads/"


class CatalogError(ValueError):
    """The catalogue directory is missing or does not satisfy the contract."""


def normalize_qr_url(value):
    """Return the normalized HTTP or HTTPS URL of one QR value, or None.

    The rules are the rules of `telegram-bot/src/chto_za_vino_bot/catalog.py` and of the
    bundle builder.
    """
    text = value.strip()
    if text.startswith("URL:"):
        text = text[4:].strip()
    try:
        parts = urlsplit(text)
    except ValueError:
        return None
    if parts.scheme.lower() not in ("http", "https") or not parts.hostname:
        return None
    if parts.username or parts.password:
        return None
    try:
        host = parts.hostname.encode("idna").decode("ascii").lower()
        port = parts.port
    except (UnicodeError, ValueError):
        return None
    default_port = (parts.scheme.lower() == "http" and port == 80) or (
        parts.scheme.lower() == "https" and port == 443)
    netloc = host if port is None or default_port else "%s:%d" % (host, port)
    return urlunsplit((parts.scheme.lower(), netloc, parts.path or "/", parts.query, ""))


def _read_index(directory):
    try:
        index = json.loads((directory / INDEX).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CatalogError("cannot read %s: %s" % (directory / INDEX, exc)) from exc
    if not isinstance(index, dict):
        raise CatalogError("%s MUST hold a JSON object" % (directory / INDEX))
    if not isinstance(index.get("config"), dict):
        raise CatalogError("%s MUST hold the object config" % (directory / INDEX))
    if not isinstance(index.get("items"), list):
        raise CatalogError("%s MUST hold the list items" % (directory / INDEX))
    return index


def _read_vectors(directory, index):
    name = index.get("vectors_file")
    if not isinstance(name, str) or not VECTORS.match(name):
        raise CatalogError("%s names no valid vector file: %r" % (directory / INDEX, name))
    path = directory / name
    if path.is_symlink() or not path.is_file():
        raise CatalogError("the vector file is not a regular file: %s" % path)
    try:
        vectors = np.load(path, allow_pickle=False)
    except (OSError, ValueError) as exc:
        raise CatalogError("cannot load %s: %s" % (path, exc)) from exc
    rotated = any(isinstance(item, dict) and "angles" in item for item in index["items"])
    if (vectors.dtype != np.float32 or vectors.ndim != 2
            or (not rotated and vectors.shape[0] != len(index["items"]))
            or (index.get("dim") is not None and vectors.shape[1] != index["dim"])):
        raise CatalogError("%s holds %s %s; the index holds %d items of dimension %r"
                           % (name, vectors.dtype, vectors.shape, len(index["items"]),
                              index.get("dim")))
    if rotated:
        _check_rows(index["items"], vectors.shape[0])
    if not np.isfinite(vectors).all():
        raise CatalogError("%s holds a value that is not finite" % name)
    if not np.allclose(np.linalg.norm(vectors, axis=1), 1.0, rtol=1e-5, atol=1e-6):
        raise CatalogError("%s holds a vector that is not L2-normalized" % name)
    return vectors


def _record_rows(item, count):
    """Return the vector rows of one index item as a range (workbench plan 82): `row` is
    the 0° row, and an item with `angles` has one row for each angle. Raise CatalogError."""
    row, angles = item.get("row"), item.get("angles")
    if isinstance(row, bool) or not isinstance(row, int) or row < 0:
        raise CatalogError("an index item has an invalid row")
    if angles is not None and (
            not isinstance(angles, list) or len(angles) < 2
            or any(isinstance(a, bool) or not isinstance(a, int) or not 0 <= a < 360
                   for a in angles)
            or len(set(angles)) != len(angles) or angles[0] != 0):
        raise CatalogError("an index item has an invalid list angles")
    stop = row + (1 if angles is None else len(angles))
    if stop > count:
        raise CatalogError("the rows of an index item pass the vector file")
    return range(row, stop)


def _check_rows(items, count):
    """The rows of the items MUST cover the vector file one time each (plan 82)."""
    spans = sorted((_record_rows(item, count) for item in items if isinstance(item, dict)),
                   key=lambda span: span.start)
    expected = 0
    for span in spans:
        if span.start != expected:
            raise CatalogError("the index rows have a gap or an overlap at row %d" % expected)
        expected = span.stop
    if expected != count:
        raise CatalogError("the index gives %d vector rows; the file holds %d"
                           % (expected, count))


def _rows(conn, view, columns):
    found = tuple(row[1] for row in conn.execute("PRAGMA table_info(%s)" % view))
    if found != columns:
        raise CatalogError("the database has no view %s with the columns %s (found: %s)"
                           % (view, ", ".join(columns), ", ".join(found) or "none"))
    return conn.execute("SELECT %s FROM %s" % (", ".join(columns), view)).fetchall()


def _card(slug, name, producer, category, region, color, grapes, main, qr_values):
    try:
        values = json.loads(qr_values) if qr_values is not None else []
    except ValueError as exc:
        raise CatalogError("the wine %s has invalid qr_values: %s" % (slug, exc)) from exc
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise CatalogError("the wine %s has invalid qr_values" % slug)
    card = {
        "name": name,
        "page_url": PAGE_URL_PREFIX + quote(slug, safe=""),
        "producer": producer,
        "category": category,
        "region": region,
        "color": color,
        "grapes": grapes,
        "image_url": None if main is None else IMAGE_URL_PREFIX + quote(main, safe=""),
        "qr_urls": sorted({url for url in map(normalize_qr_url, values) if url}),
    }
    card = {key: card[key] for key in CARD_FIELDS}
    card["sugar"] = infer_sugar(slug, name)
    return card


def _read_views(path):
    """Return (slug -> card, source sha256 -> [(slug, role)]) of the two views."""
    if path.is_symlink() or not path.is_file():
        raise CatalogError("the catalogue database is not a regular file: %s" % path)
    try:
        conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise CatalogError("cannot open %s: %s" % (path, exc)) from exc
    try:
        wines = {row[0]: _card(*row) for row in _rows(conn, WINE_VIEW, WINE_COLUMNS)}
        owners = {}
        for slug, _, digest, role in _rows(conn, IMAGE_VIEW, IMAGE_COLUMNS):
            if slug not in wines or role not in ("full", "label"):
                raise CatalogError("%s has an invalid row for the wine %s" % (IMAGE_VIEW, slug))
            owners.setdefault(digest, []).append((slug, role))
    except sqlite3.Error as exc:
        raise CatalogError("cannot read %s: %s" % (path, exc)) from exc
    finally:
        conn.close()
    return wines, owners


def load_codes(directory):
    """Return the codes of the Active wines of a catalogue directory: (kind, value) ->
    the sorted slugs of the wines. Raise CatalogError.

    The query is the query of `workbench/pipeline/barcode.py` `CodeLookup.load`. The kinds
    are `gtin` (GTIN-14) and `qr_url` (the normal form of `codes.clean_qr_url`). A value
    MAY belong to several wines.
    """
    path = Path(directory) / DATABASE
    if path.is_symlink() or not path.is_file():
        raise CatalogError("the catalogue database is not a regular file: %s" % path)
    try:
        conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise CatalogError("cannot open %s: %s" % (path, exc)) from exc
    try:
        rows = conn.execute(
            "SELECT c.kind, c.value, c.wine_slug FROM wine_code c "
            "JOIN wine_catalog w ON w.wine_slug = c.wine_slug "
            "WHERE w.state = 'Active' AND c.kind IN ('gtin', 'qr_url')").fetchall()
    except sqlite3.Error as exc:
        raise CatalogError("cannot read the codes of %s: %s" % (path, exc)) from exc
    finally:
        conn.close()
    values = {}
    for kind, value, slug in rows:
        if not isinstance(value, str) or not value or not isinstance(slug, str):
            raise CatalogError("wine_code has an invalid row for the wine %r" % (slug,))
        values.setdefault((kind, value), set()).add(slug)
    return {key: tuple(sorted(slugs)) for key, slugs in values.items()}


def load_catalog(directory, embedding):
    """Load one embedding of a catalogue directory as a `Bundle`. Raise CatalogError.

    An item `(source_sha256, view)` belongs to each wine with an image of this SHA-256.
    The view `label` takes the images of each role; the view `full` takes the images of
    the role `full` alone. These are the rules of the bundle builder. The reader uses each
    item of `index.json`; the copy script of the workbench checks their freshness.
    """
    root = Path(directory)
    if not root.is_dir():
        raise CatalogError("the catalogue is not a directory: %s" % root)
    if not isinstance(embedding, str) or not NAME.match(embedding):
        raise CatalogError("not an embedding name: %r" % (embedding,))
    entry = root / EMBEDDINGS / embedding
    index = _read_index(entry)
    vectors = _read_vectors(entry, index)
    wines, owners = _read_views(root / DATABASE)

    rows = {}
    angles = {}
    rotated = False
    for number, item in enumerate(index["items"]):
        if not isinstance(item, dict):
            raise CatalogError("item %d of the index is not an object" % number)
        digest, view = item.get("source_sha256"), item.get("view")
        if (not isinstance(digest, str) or not HEX64.match(digest)
                or not isinstance(view, str) or not view):
            raise CatalogError("item %d of the index has an invalid row, sha256, or view"
                               % number)
        try:
            span = _record_rows(item, len(vectors))
        except CatalogError:
            raise CatalogError("item %d of the index has an invalid row, sha256, or view"
                               % number) from None
        # Plan 82: a rotated item has one row for each angle; each row belongs to each
        # owner, so the wine scores the maximum over the rotation.
        item_angles = item.get("angles") or [0]
        rotated = rotated or "angles" in item
        seen = set()
        for slug, role in owners.get(digest, ()):
            if (view == "label" or role == "full") and slug not in seen:
                seen.add(slug)
                for row, angle in zip(span, item_angles):
                    rows.setdefault(view, []).append((row, slug))
                    angles.setdefault(view, []).append(angle)

    slugs = tuple(sorted({slug for pairs in rows.values() for _, slug in pairs}))
    if not slugs:
        raise CatalogError("the embedding %s has no item of an active wine" % embedding)
    numbers = {slug: number for number, slug in enumerate(slugs)}
    views = {
        view: (np.ascontiguousarray(vectors[[row for row, _ in pairs]]),
               np.asarray([numbers[slug] for _, slug in pairs], dtype=np.int64))
        for view, pairs in rows.items()
    }
    return Bundle(path=root, embedding=index["config"], dimension=int(vectors.shape[1]),
                  slugs=slugs, views=views, cards={slug: wines[slug] for slug in slugs},
                  angles=({view: np.asarray(values, dtype=np.int16)
                           for view, values in angles.items()} if rotated else None))
