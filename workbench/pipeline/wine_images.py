"""The static wine images of chtozavino.ru (plan `docs/plans/06_wine-images.md` of the
repository).

`build` writes one release directory: `1600/<slug>.webp` and `400/<slug>.webp` for each
Active wine with an image, `manifest.json`, and `SHA256SUMS`. `check_release` and
`check_url` compare a release directory or a published release with a catalogue database.

Rules:
- The image of a wine is its `main_patched` image, else its `main` image. The code reads
  the two fixed views of schema 031 for the rule.
- The file is made from the package cut of that image (`image_derivative`, kind `package`,
  plan 09): an alpha crop of a transparent original, or the SAM3 cut of an opaque one. An
  image with no package cut uses the original. The owner chose this on 2026-10-19 (answer
  "A"). The check reads the views and `image_derivative`, so a matcher catalogue copy with no
  image files is enough. `build` also reads the table `image` for the files.
- `trim` cuts the outer border lines with no margin (owner answers of
  2026-10-19T21:46:00+0300): the fully transparent lines of an image with transparency, and
  the white or black frame of a fully opaque original. A package cut is tight already, so it
  loses its transparent lines alone. Read `trim` for the rules that keep a dark bottle whole.
- A wine with no image gets no file. Its manifest record has `source` null and no files.
- A file keeps the aspect ratio of the trimmed image. Its long side is at most the size. A
  smaller image is not enlarged. The file has no EXIF and no XMP data; the ICC profile
  stays, so that the colours stay correct.
- A check compares the SHA-256 of the originals and of the files. It does not compare a
  date: the table `wine_image` has no time column.
"""

import collections
from contextlib import closing
import hashlib
import io
import json
import os
from pathlib import Path
import random
import re
import shutil
import sqlite3
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

import numpy as np
from PIL import Image, ImageOps

import labdb


FORMAT = "svoe-vino-wine-images"
# Version 2 adds `cut_sha256`: the file is made from the package cut.
VERSION = 2
# The sizes in decreasing order: each file is made from the file of the size before it.
SIZES = (1600, 400)
MANIFEST = "manifest.json"
SUMS = "SHA256SUMS"
# The image types of a wine image, the preferred type first.
SOURCES = ("main_patched", "main")
# The limit of `patches.py`. The largest catalogue original has about 60 MP.
MAX_PIXELS = 100_000_000
# The levels of `derive.py`: a pixel with alpha at most ALPHA_THRESHOLD is transparent. An
# opaque pixel with each channel at least WHITE_LEVEL is white, with each channel at most
# BLACK_LEVEL (255 - WHITE_LEVEL) black.
ALPHA_THRESHOLD = 32
WHITE_LEVEL = 245
BLACK_LEVEL = 10
# 15 Active slugs start with `__`. A leading `-` would read as an option in a shell command.
SLUG = re.compile(r"^[a-z0-9_][a-z0-9_-]*$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
FILE_KEYS = ("bytes", "height", "sha256", "width")


class ImageError(ValueError):
    """The database, an original, or a release does not satisfy the rules."""


def connect(db_path):
    """Open the catalogue database read-only."""
    path = Path(db_path)
    if path.is_symlink() or not path.is_file():
        raise ImageError("the catalogue database is not a regular file: %s" % db_path)
    try:
        return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise ImageError("cannot open %s: %s" % (db_path, exc)) from exc


def expected(conn):
    """Return slug -> (source, source sha256, cut sha256) of each Active wine.

    `source` is `main_patched` or `main`. The cut is the package cut of the source, or None.
    A wine with no image gives (None, None, None).
    """
    try:
        wines = {slug: (None, None) for (slug,) in
                 conn.execute("SELECT wine_slug FROM matcher_wine")}
        rows = conn.execute("SELECT wine_slug, image_type, sha256 FROM matcher_wine_image "
                            "WHERE image_type IN ('main', 'main_patched')").fetchall()
        cuts = dict(conn.execute("SELECT source_sha256, sha256 FROM image_derivative "
                                 "WHERE kind = 'package'"))
    except sqlite3.Error as exc:
        raise ImageError("cannot read the views of the matcher or image_derivative: %s"
                         % exc) from exc
    for slug, image_type, digest in rows:
        if slug not in wines:
            raise ImageError("matcher_wine_image has an image of the unknown wine %s" % slug)
        current = wines[slug][0]
        if current == image_type:
            raise ImageError("the wine %s has two %s images" % (slug, image_type))
        if current is None or SOURCES.index(image_type) < SOURCES.index(current):
            wines[slug] = (image_type, digest)
    for slug in wines:
        if not SLUG.match(slug):
            raise ImageError("the slug %r cannot be a file name" % slug)
    return {slug: (source, digest, cuts.get(digest) if digest else None)
            for slug, (source, digest) in wines.items()}


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def trim(image, frames=True):
    """Cut the outer rows and columns that are a border: fully transparent, white, or black.

    - An image with transparent pixels loses its fully transparent outer lines. A white or
      a black line of such an image is content, for example the dark bottom of a bottle cut.
    - A fully opaque image loses its white or black frame when `frames` is true. The
      outermost line of each side sets the kind of that side, white or black, and the side
      cuts lines of that kind alone. A side with a mixed outermost line cuts nothing, also
      after the other sides change: so a black bottle on a white background stays whole,
      and a frame with two colours keeps the sides that start mixed.
    - With `frames` false (a package cut, which is tight already), a fully opaque image
      stays as it is: the black cap of a can is content.
    - The cut repeats until no side changes. An image that is only border keeps its canvas.
    """
    pixels = np.asarray(image.convert("RGBA"))
    clear = pixels[..., 3] <= ALPHA_THRESHOLD
    height, width = clear.shape
    if not clear.any() and not frames:
        return image
    if clear.any():
        kinds = {"top": clear, "bottom": clear, "left": clear, "right": clear}
    else:
        white = pixels[..., :3].min(axis=2) >= WHITE_LEVEL
        black = pixels[..., :3].max(axis=2) <= BLACK_LEVEL
        lines = {"top": (0, slice(None)), "bottom": (height - 1, slice(None)),
                 "left": (slice(None), 0), "right": (slice(None), width - 1)}
        kinds = {side: next((kind for kind in (white, black) if kind[line].all()), None)
                 for side, line in lines.items()}

    def border(side, rows, cols):
        return kinds[side] is not None and kinds[side][rows, cols].all()

    top, bottom, left, right = 0, height, 0, width
    changed = True
    while changed:
        changed = False
        while bottom - top > 1 and border("top", top, slice(left, right)):
            top, changed = top + 1, True
        while bottom - top > 1 and border("bottom", bottom - 1, slice(left, right)):
            bottom, changed = bottom - 1, True
        while right - left > 1 and border("left", slice(top, bottom), left):
            left, changed = left + 1, True
        while right - left > 1 and border("right", slice(top, bottom), right - 1):
            right, changed = right - 1, True
    if (bottom - top <= 1 or right - left <= 1
            or (top, bottom, left, right) == (0, height, 0, width)):
        return image
    return image.crop((left, top, right, bottom))


def derivatives(path, cut=False):
    """Return size -> (WebP bytes, width, height) of the image at `path`, trimmed.

    `cut` is true for a package cut: its trim keeps the colour frames (`trim`).
    """
    with Image.open(path) as original:
        if original.width * original.height > MAX_PIXELS:
            raise ImageError("%s has %d pixels; the limit is %d"
                             % (path, original.width * original.height, MAX_PIXELS))
        icc_profile = original.info.get("icc_profile")
        image = ImageOps.exif_transpose(original)
        # A palette, RGB, or grey PNG can keep its transparency in `info` (a tRNS chunk).
        alpha = image.mode in ("RGBA", "LA", "PA") or "transparency" in image.info
        image = trim(image.convert("RGBA" if alpha else "RGB"), frames=not cut)
    options = {"icc_profile": icc_profile} if icc_profile else {}
    result = {}
    for size in SIZES:
        image.thumbnail((size, size), Image.Resampling.LANCZOS)
        out = io.BytesIO()
        image.save(out, "WEBP", **options)
        result[size] = (out.getvalue(), image.width, image.height)
    return result


def _originals(conn, db_path):
    """Return sha256 -> the path of the original in the image store."""
    try:
        rows = conn.execute("SELECT sha256, folder, extension FROM image").fetchall()
    except sqlite3.Error as exc:
        raise ImageError("cannot read the table image: %s" % exc) from exc
    return {digest: os.path.join(labdb.image_dir(db_path, folder),
                                 "%s.%s" % (digest, extension))
            for digest, folder, extension in rows}


def build(db_path, out):
    """Write a new release directory `out` from the database. Return the counts."""
    out = Path(out)
    if out.exists() or out.is_symlink():
        raise ImageError("the output directory exists: %s" % out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(db_path)) as conn:
        conn.execute("BEGIN")
        wines = expected(conn)
        originals = _originals(conn, db_path)
        schema = conn.execute("PRAGMA user_version").fetchone()[0]
        conn.rollback()
    # The file is made from the package cut, else from the original.
    uses = collections.Counter(cut or digest for _, digest, cut in wines.values() if digest)
    cache = {}
    temp = Path(tempfile.mkdtemp(prefix=".%s." % out.name, dir=out.parent))
    try:
        for size in SIZES:
            (temp / str(size)).mkdir()
        records = {}
        for slug, (source, digest, cut) in sorted(wines.items()):
            if source is None:
                records[slug] = {"source": None, "source_sha256": None, "cut_sha256": None,
                                 "files": {}}
                continue
            used = cut or digest
            if used in cache:
                made = cache[used]
            else:
                path = originals.get(used)
                if path is None or not os.path.isfile(path):
                    raise ImageError("the %s %s of %s is missing"
                                     % ("package cut" if cut else "original", used, slug))
                if sha256_file(path) != used:
                    raise ImageError("%s: the bytes do not agree with the name" % path)
                made = derivatives(path, cut=bool(cut))
                if uses[used] > 1:
                    cache[used] = made
            files = {}
            for size, (data, width, height) in made.items():
                (temp / str(size) / ("%s.webp" % slug)).write_bytes(data)
                files[str(size)] = {"sha256": sha256_bytes(data), "width": width,
                                    "height": height, "bytes": len(data)}
            records[slug] = {"source": source, "source_sha256": digest, "cut_sha256": cut,
                             "files": files}
        manifest = {
            "format": FORMAT,
            "version": VERSION,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "catalog": {"sha256": sha256_file(db_path), "schema": schema,
                        "active_wines": len(wines)},
            "sizes": list(SIZES),
            "wines": records,
        }
        (temp / MANIFEST).write_text(
            json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n", encoding="utf-8")
        sums = [(sha256_file(temp / name), name) for name in _release_files(temp)]
        (temp / SUMS).write_text("".join("%s  %s\n" % pair for pair in sums), encoding="ascii")
        # mkdtemp makes the directory 0700. Caddy reads the release as another user.
        temp.chmod(0o755)
        os.rename(temp, out)
    except BaseException:
        shutil.rmtree(temp, ignore_errors=True)
        raise
    images = sum(1 for record in records.values() if record["source"])
    return {"out": str(out), "wines": len(records), "images": images,
            "no_image": len(records) - images,
            "patched": sum(1 for r in records.values() if r["source"] == "main_patched"),
            "from_cut": sum(1 for r in records.values() if r["cut_sha256"]),
            "files": images * len(SIZES),
            "bytes": sum(f["bytes"] for r in records.values() for f in r["files"].values())}


def _release_files(directory):
    """Return the relative paths of the files of a release, except `SHA256SUMS`."""
    names = []
    for root, dirs, files in os.walk(directory):
        dirs.sort()
        for name in files:
            relative = os.path.relpath(os.path.join(root, name), directory)
            if relative != SUMS:
                names.append(relative.replace(os.sep, "/"))
    return sorted(names)


def check_manifest(wines, manifest, catalog_update=False):
    """Compare a manifest with `expected` of a database. Return (errors, warnings).

    With `catalog_update`, a wine of the manifest that is not Active in the database is a
    warning: the image release comes before the catalogue update of the matcher.
    """
    if (not isinstance(manifest, dict) or manifest.get("format") != FORMAT
            or manifest.get("version") != VERSION):
        return ["the manifest is not a %s manifest of version %d" % (FORMAT, VERSION)], []
    errors, warnings = [], []
    if manifest.get("sizes") != list(SIZES):
        errors.append("the manifest has the sizes %r; expected %r"
                      % (manifest.get("sizes"), list(SIZES)))
    records = manifest.get("wines")
    if not isinstance(records, dict):
        return errors + ["the manifest has no object wines"], warnings
    for slug in sorted(set(wines) - set(records)):
        errors.append("%s: an Active wine that the manifest does not hold" % slug)
    for slug in sorted(set(records) - set(wines)):
        (warnings if catalog_update else errors).append(
            "%s: in the manifest, but not an Active wine of the database" % slug)
    for slug in sorted(set(wines) & set(records)):
        errors.extend(_check_record(slug, wines[slug], records[slug]))
    return errors, warnings


def _check_record(slug, want, record):
    if not isinstance(record, dict):
        return ["%s: the manifest record is not an object" % slug]
    found = (record.get("source"), record.get("source_sha256"), record.get("cut_sha256"))
    if found != want:
        return ["%s: the manifest has the image %s %s (cut %s); the database has %s %s (cut %s)"
                % ((slug,) + found + want)]
    files = record.get("files")
    if want[0] is None:
        return [] if files == {} else ["%s: a wine with no image has files" % slug]
    if not isinstance(files, dict) or set(files) != {str(size) for size in SIZES}:
        return ["%s: the manifest record does not have one file of each size" % slug]
    problems = []
    for size in SIZES:
        item = files[str(size)]
        valid = (isinstance(item, dict) and sorted(item) == list(FILE_KEYS)
                 and isinstance(item["sha256"], str) and HEX64.match(item["sha256"])
                 and all(type(item[key]) is int and item[key] > 0
                         for key in ("bytes", "height", "width"))
                 and max(item["width"], item["height"]) <= size)
        if not valid:
            problems.append("%s: the record of the file of size %d is not valid" % (slug, size))
    return problems


def _wanted_files(manifest):
    """Return the relative path -> the file record of each file that the manifest names."""
    return {"%s/%s.webp" % (size, slug): item
            for slug, record in manifest["wines"].items()
            for size, item in record["files"].items()}


def _read_manifest(text):
    try:
        return json.loads(text)
    except ValueError as exc:
        raise ImageError("the manifest is not JSON: %s" % exc) from exc


def check_release(db_path, release, catalog_update=False):
    """Check a release directory against the database. Return (errors, warnings)."""
    release = Path(release)
    with closing(connect(db_path)) as conn:
        wines = expected(conn)
    try:
        manifest = _read_manifest((release / MANIFEST).read_text(encoding="utf-8"))
    except OSError as exc:
        return ["cannot read the manifest: %s" % exc], []
    errors, warnings = check_manifest(wines, manifest, catalog_update)
    if errors:
        return errors, warnings
    wanted = _wanted_files(manifest)
    found = _release_files(release)
    for name in sorted(set(found) - set(wanted) - {MANIFEST}):
        errors.append("%s: a file that the manifest does not name" % name)
    for name in sorted(set(wanted) - set(found)):
        errors.append("%s: missing" % name)
    for name in sorted(set(wanted) & set(found)):
        errors.extend(_check_file(name, (release / name).read_bytes(), wanted[name]))
    try:
        sums = (release / SUMS).read_text(encoding="ascii")
    except (OSError, UnicodeError) as exc:
        return errors + ["cannot read %s: %s" % (SUMS, exc)], warnings
    expected_sums = "".join("%s  %s\n" % (sha256_file(release / name), name) for name in found)
    if sums != expected_sums:
        errors.append("%s does not agree with the files of the release" % SUMS)
    return errors, warnings


def _check_file(name, data, item):
    if len(data) != item["bytes"] or sha256_bytes(data) != item["sha256"]:
        return ["%s: the bytes do not agree with the manifest" % name]
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.format != "WEBP" or image.size != (item["width"], item["height"]):
                return ["%s: not a WebP file of %d x %d"
                        % (name, item["width"], item["height"])]
    except (OSError, ValueError):
        return ["%s: not an image" % name]
    return []


def http_get(url, timeout=30):
    """Return (HTTP status, body) of a GET request. An HTTP error gives an empty body."""
    request = urllib.request.Request(url, headers={"User-Agent": "svoe-vino-wine-images/1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        exc.close()
        return exc.code, b""


def check_url(db_path, base_url, sample=50, catalog_update=False, fetch=http_get, seed=None):
    """Check a published release against the database. Return (errors, warnings).

    The check reads the manifest, `sample` random files, and the addresses of each wine
    with no image, which MUST answer HTTP 404.
    """
    base = base_url if base_url.endswith("/") else base_url + "/"
    if urllib.parse.urlsplit(base).scheme not in ("http", "https"):
        raise ImageError("the address is not an HTTP or HTTPS address: %s" % base_url)
    with closing(connect(db_path)) as conn:
        wines = expected(conn)
    status, body = fetch(base + MANIFEST)
    if status != 200:
        return ["%s%s answered HTTP %d" % (base, MANIFEST, status)], []
    try:
        manifest = _read_manifest(body.decode("utf-8"))
    except UnicodeError as exc:
        return ["the manifest is not UTF-8: %s" % exc], []
    errors, warnings = check_manifest(wines, manifest, catalog_update)
    if errors:
        return errors, warnings
    wanted = _wanted_files(manifest)
    for name in random.Random(seed).sample(sorted(wanted), min(sample, len(wanted))):
        status, data = fetch(base + name)
        if status != 200:
            errors.append("%s: HTTP %d" % (name, status))
        else:
            errors.extend(_check_file(name, data, wanted[name]))
    for slug in sorted(slug for slug, record in manifest["wines"].items()
                       if record["source"] is None):
        for size in SIZES:
            name = "%s/%s.webp" % (size, slug)
            status, _ = fetch(base + name)
            if status != 404:
                errors.append("%s: a wine with no image answered HTTP %d; expected 404"
                              % (name, status))
    return errors, warnings
