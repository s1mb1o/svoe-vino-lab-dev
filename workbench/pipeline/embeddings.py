"""The embeddings of the lab: the configuration, the inputs, the steps, the hash, the
item status, and the files of `data/catalog/embeddings/<name>/`.

`build_embeddings.py` builds one embedding. `embedding_routes.py` serves the Embeddings
page. Both use this module. The module needs no `torch`. Read
`docs/plans/10_embeddings-page.md`.

The files of one embedding, next to the database file:
    embeddings/<name>/index.json                          the settings and the items
    embeddings/<name>/vectors-<8 hex>.npy                 float32, one row for each item
    embeddings/<name>/images/<source_sha256>_<view>.png   the model input of one item
    embeddings/<name>/build.log                           the output of the last build
    embeddings/<name>/build.lock                          the PID of the running build

An item is one source file in one view. Its `embedding_hash` covers the source file, the
view, the role of the file, the settings of the model and of the steps, and the
processed file that the steps use. A build does nothing for an item whose hash did not
change and whose prepared image exists.
"""
import hashlib
import io
import json
import os
import re
import sqlite3
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np
import yaml
from PIL import Image

import derive
import labdb
import alternatives
import dis_litert

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT, "config.yaml")

# Raise this number when the code of a step changes the pixels. Each item is then stale.
STEPS_VERSION = 1
NAME_PATTERN = r"[a-z0-9][a-z0-9._-]{0,99}"
NAME_RE = re.compile(r"^%s$" % NAME_PATTERN)
# The backends of an embedding model. A matcher with no vectors, for example the official
# recognizer of vino-svoe.ru, is an entry of the key `pipeline` (`pipelines.py`). Read
# docs/plans/34_pipeline-section.md.
BACKENDS = ("openai", "local")
VIEWS = ("full", "label")
ENTRY_KEYS = ("name", "backend", "base_url", "model", "extra_body", "batch_size", "views")
DEFAULT_BATCH_SIZE = 16
MAX_BATCH_SIZE = 256
# The keys of `extra_body` that the local backend gives to the image processor.
LOCAL_EXTRA_KEYS = ("max_num_patches",)
# The keys that the build itself puts in the body of a request.
REQUEST_KEYS = ("model", "input")
# step -> {option: default}. None marks a required option.
STEP_OPTIONS = {
    "segment": {"target": None},
    "segment_dis": {"model": None, "revision": None, "threshold": 0.5, "margin": 0.04},
    "remove_background": {},
    "white_background": {},
    "square_on_white": {},
    "resize": {"max_size": None, "aspect": "keep", "upscale": False},
}
SEGMENT_STEPS = ("segment", "segment_dis")
TARGETS = ("package", "label")
ASPECTS = ("keep", "ignore")
MIN_SIZE, MAX_SIZE = 16, 4096

# The role of each image type of `wine_image`. A `full` image shows the whole package
# with its label. A `label` image is a close-up of a label. The owner chose the names of
# the additional types on 2026-09-25: the kind first, then the side (schema files 010
# and later).
ROLES = {"main": "full", "main_patched": "full", "full_front": "full", "full_back": "full",
         "label_front": "label", "label_back": "label"}
# The order of the columns of one wine. The card image is first: `main_patched` replaces
# `main`.
TYPE_ORDER = ("main_patched", "main", "full_front", "full_back", "label_front", "label_back")

ALPHA_ERROR = ("the gateway drops the alpha channel; the model would see the hidden "
               "colours under the transparent pixels (variant B or E); add "
               "white_background")
TRANSPARENT_ERROR = ("the model input has transparent pixels; the gateway drops the "
                     "alpha channel")
NO_CUT = {"package": "no processed file yet (plan 09)", "label": "no label cut yet"}

INDEX = "index.json"
LOCK = "build.lock"
LOG = "build.log"
IMAGES = "images"
VECTORS_RE = re.compile(r"^vectors-[0-9a-f]{8}\.npy$")
# The script of a build. A lock names a live build only when the process runs it.
BUILD_SCRIPT_NAME = "build_embeddings.py"


class ConfigError(Exception):
    """The configuration, or the database, does not allow the work."""


class ItemError(Exception):
    """One item cannot be prepared."""


class Busy(Exception):
    """Another build of the same embedding runs."""


def now():
    """Return the local time in ISO 8601, for example 2026-09-25T01:00:00+0300."""
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def check_steps(view, spec, segment_first=True):
    """Check the steps of one view. Return them with each default option filled in.

    A view of an entry of `embeddings` starts with `segment`. The steps of a test photo of
    a pipeline (`pipelines.py`, `segment_first=False`) MAY start with another step, for
    example `resize` alone for the photo as it is (owner answers of
    2026-09-26T00:52:41+0300)."""
    if not isinstance(spec, dict) or set(spec) != {"steps"}:
        raise ConfigError("view %s: the view MUST hold the key `steps` alone" % view)
    raw_steps = spec["steps"]
    if not isinstance(raw_steps, list) or not raw_steps:
        raise ConfigError("view %s: `steps` MUST be a list with at least one step" % view)
    steps = []
    for number, raw in enumerate(raw_steps, 1):
        where = "view %s, step %d" % (view, number)
        if not isinstance(raw, dict) or "step" not in raw:
            raise ConfigError("%s: a step MUST be a mapping with the key `step`" % where)
        kind = raw["step"]
        if kind not in STEP_OPTIONS:
            raise ConfigError("%s: unknown step %r; use one of: %s"
                              % (where, kind, ", ".join(STEP_OPTIONS)))
        options = STEP_OPTIONS[kind]
        unknown = sorted(set(raw) - {"step"} - set(options))
        if unknown:
            raise ConfigError("%s: unknown option of %s: %s" % (where, kind, ", ".join(unknown)))
        step = {"step": kind}
        for option, default in options.items():
            if option not in raw and default is None:
                raise ConfigError("%s: %s needs the option `%s`" % (where, kind, option))
            step[option] = raw.get(option, default)
        if kind == "segment" and step["target"] not in TARGETS:
            raise ConfigError("%s: target MUST be one of: %s" % (where, ", ".join(TARGETS)))
        if kind == "segment_dis":
            for option in ("model", "revision"):
                if not isinstance(step[option], str) or not step[option].strip():
                    raise ConfigError("%s: %s MUST be a non-empty string" % (where, option))
            for option in ("threshold", "margin"):
                value = step[option]
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ConfigError("%s: %s MUST be a number" % (where, option))
            if not 0 < step["threshold"] < 1:
                raise ConfigError("%s: threshold MUST be between 0 and 1" % where)
            if not 0 <= step["margin"] <= 0.5:
                raise ConfigError("%s: margin MUST be from 0 to 0.5" % where)
        if kind == "resize":
            size = step["max_size"]
            if isinstance(size, bool) or not isinstance(size, int) or not (
                    MIN_SIZE <= size <= MAX_SIZE):
                raise ConfigError("%s: max_size MUST be an integer from %d to %d"
                                  % (where, MIN_SIZE, MAX_SIZE))
            if step["aspect"] not in ASPECTS:
                raise ConfigError("%s: aspect MUST be one of: %s" % (where, ", ".join(ASPECTS)))
            if not isinstance(step["upscale"], bool):
                raise ConfigError("%s: upscale MUST be true or false" % where)
        steps.append(step)
    kinds = [step["step"] for step in steps]
    repeated = sorted({kind for kind in kinds if kinds.count(kind) > 1})
    if repeated:
        raise ConfigError("view %s: a step MAY occur one time; repeated: %s"
                          % (view, ", ".join(repeated)))
    segment_kinds = [kind for kind in kinds if kind in SEGMENT_STEPS]
    if kinds[0] not in SEGMENT_STEPS and (segment_first or segment_kinds):
        raise ConfigError("view %s: the first step MUST be `segment` or `segment_dis`" % view)
    if len(segment_kinds) > 1:
        raise ConfigError("view %s: one segmentation step is allowed" % view)
    if "remove_background" in kinds:
        position = kinds.index("remove_background")
        if position != 1 or kinds[0] != "segment":
            raise ConfigError("view %s: `remove_background` MUST come directly after "
                              "`segment`" % view)
        if "white_background" not in kinds[position:]:
            raise ConfigError("view %s: %s" % (view, ALPHA_ERROR))
    return steps


class Embedding:
    """One checked entry of the key `embeddings` of `config.yaml`."""

    def __init__(self, raw):
        if not isinstance(raw, dict):
            raise ConfigError("an entry MUST be a mapping")
        name = raw.get("name")
        if not isinstance(name, str) or not NAME_RE.match(name):
            raise ConfigError("the name %r MUST match %s" % (name, NAME_RE.pattern))
        self.name = name
        # The backend comes before the keys, so that an entry of a pipeline in this list
        # gets the text that names the key `pipeline`.
        self.backend = raw.get("backend")
        if self.backend not in BACKENDS:
            raise ConfigError("backend MUST be one of: %s; a matcher with no vectors, for "
                              "example the backend svoe-vino-ru, is an entry of the key "
                              "`pipeline`" % ", ".join(BACKENDS))
        unknown = sorted(set(raw) - set(ENTRY_KEYS))
        if unknown:
            raise ConfigError("unknown key: %s" % ", ".join(unknown))
        base_url = raw.get("base_url")
        if self.backend == "openai":
            if not isinstance(base_url, str) or not base_url.startswith(("http://", "https://")):
                raise ConfigError("base_url MUST be an http or https URL")
            if "/ui/" in base_url or "#" in base_url:
                raise ConfigError("base_url %s is a page of the llama-swap UI; use the API "
                                  "base, for example http://192.168.86.14:18081/v1" % base_url)
            base_url = base_url.rstrip("/")
        elif base_url is not None:
            raise ConfigError("base_url is a key of the backend openai alone")
        self.base_url = base_url
        self.model = raw.get("model")
        if not isinstance(self.model, str) or not self.model.strip():
            raise ConfigError("model MUST be a non-empty string")
        extra = raw.get("extra_body")
        extra = {} if extra is None else extra
        if not isinstance(extra, dict):
            raise ConfigError("extra_body MUST be a mapping")
        taken = sorted(set(extra) & set(REQUEST_KEYS))
        if taken:
            raise ConfigError("extra_body MUST NOT hold %s; the build sets it"
                              % ", ".join(taken))
        if self.backend == "local":
            other = sorted(set(extra) - set(LOCAL_EXTRA_KEYS))
            if other:
                raise ConfigError("the backend local accepts only %s in extra_body; found: %s"
                                  % (", ".join(LOCAL_EXTRA_KEYS), ", ".join(other)))
        self.extra_body = extra
        batch = raw.get("batch_size", DEFAULT_BATCH_SIZE)
        if isinstance(batch, bool) or not isinstance(batch, int) or not (
                1 <= batch <= MAX_BATCH_SIZE):
            raise ConfigError("batch_size MUST be an integer from 1 to %d" % MAX_BATCH_SIZE)
        self.batch_size = batch
        views = raw.get("views")
        if not isinstance(views, dict) or not views:
            raise ConfigError("views MUST be a mapping with at least one view")
        other = sorted(set(views) - set(VIEWS))
        if other:
            raise ConfigError("unknown view: %s; use %s" % (", ".join(other), " or ".join(VIEWS)))
        self.views = {view: check_steps(view, views[view]) for view in VIEWS if view in views}
        self._hashes = {}

    def view_config_hash(self, view, role="full"):
        """Return the hash of the settings that make the model input and the vector of
        one view. A close-up (role `label`) goes to the model as it is: no steps."""
        key = (view, role)
        if key not in self._hashes:
            self._hashes[key] = sha256_json({
                "backend": self.backend, "model": self.model,
                "extra_body": self.extra_body, "view": view,
                "steps": self.views[view] if role == "full" else [],
                "steps_version": STEPS_VERSION})
        return self._hashes[key]

    def summary(self):
        """Return the settings of the entry, with each default option filled in."""
        return {"name": self.name, "backend": self.backend, "base_url": self.base_url,
                "model": self.model, "extra_body": self.extra_body,
                "batch_size": self.batch_size, "views": self.views}


class Settings:
    """The keys of `config.yaml` that the embeddings use."""

    def __init__(self, config_path, db_path, python, entries):
        self.config_path = config_path
        self.db_path = db_path
        self.python = python
        # A list of (name, Embedding or None, the configuration error or None).
        self.entries = entries

    def find(self, name):
        """Return the entry `name`. Raise KeyError for an unknown name, and
        ConfigError for an entry that is not valid."""
        for label, embedding, error in self.entries:
            if label == name:
                if error:
                    raise ConfigError(error)
                return embedding
        raise KeyError(name)


def read_config(path=CONFIG_PATH):
    """Read `config.yaml`. Return (the absolute path of the file, its mapping, the
    absolute path of the database file). Raise ConfigError when the file itself does not
    allow the work. `load_settings` and `pipelines.load` use it."""
    path = os.path.abspath(path)
    try:
        with open(path, encoding="utf-8") as fh:
            config = yaml.safe_load(fh) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError("cannot read %s: %s" % (path, exc))
    if not isinstance(config, dict):
        raise ConfigError("%s MUST hold a mapping" % path)
    database = config.get("database_file")
    if not database:
        raise ConfigError("%s holds no key `database_file`" % path)
    rootdir = config.get("rootdir") or os.path.dirname(os.path.dirname(ROOT))
    return path, config, os.path.abspath(os.path.join(rootdir, database))


def check_entries(config, key, make):
    """Return the entries of the list `key` of `config`, in file order, as (name, the
    checked entry or None, the error or None). `make(raw)` checks one entry and raises
    ConfigError. A name of an earlier entry is an error. Raise ConfigError when the value
    of `key` is not a list."""
    raw_entries = config.get(key) or []
    if not isinstance(raw_entries, list):
        raise ConfigError("the key `%s` MUST be a list" % key)
    entries, seen = [], set()
    for number, raw in enumerate(raw_entries, 1):
        name = raw.get("name") if isinstance(raw, dict) else None
        label = name if isinstance(name, str) and name else "#%d" % number
        try:
            entry = make(raw)
            if entry.name in seen:
                raise ConfigError("the name %s is used by an earlier entry" % entry.name)
            seen.add(entry.name)
            entries.append((label, entry, None))
        except ConfigError as exc:
            entries.append((label, None, str(exc)))
    return entries


def load_settings(path=CONFIG_PATH):
    """Read `config.yaml`. Return the `Settings`. An entry that is not valid keeps its
    error, so that the page can show it. Raise ConfigError when the file itself does
    not allow the work."""
    path, config, db_path = read_config(path)
    python = config.get("embedding_python")
    if python is not None:
        if not isinstance(python, str) or not python.strip():
            raise ConfigError("embedding_python MUST be the path of a Python interpreter")
        python = os.path.expanduser(python)
    return Settings(path, db_path, python, check_entries(config, "embeddings", Embedding))


def embeddings_root(db_path):
    """Return `embeddings/` next to the database file, as `images/` is."""
    return os.path.join(os.path.dirname(os.path.abspath(db_path)), "embeddings")


def entry_dir(db_path, name):
    if not NAME_RE.match(name):
        raise ValueError("not an embedding name: %r" % name)
    return os.path.join(embeddings_root(db_path), name)


def open_database(db_path):
    """Open the lab database read-only. It MUST hold the image tables of schema 007."""
    if not os.path.isfile(db_path):
        raise ConfigError("no database at %s" % db_path)
    conn = sqlite3.connect(Path(os.path.abspath(db_path)).as_uri() + "?mode=ro", uri=True)
    try:
        names = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_schema WHERE type = 'table'")}
    except sqlite3.Error:
        conn.close()
        raise
    missing = sorted({"wine_catalog", "wine_image", "image", "image_derivative",
                      "image_derivative_absence"} - names)
    if missing:
        conn.close()
        raise ConfigError("the database %s has no table %s; the embeddings need schema "
                          "021 or newer" % (db_path, ", ".join(missing)))
    return conn


def read_inputs(conn, db_path):
    """Return (wines, sources) of the Active wines.

    `wines` is a list in import order. Each wine is a dict with `slug`, `name`,
    `producer`, `category`, `region`, and `columns`: a list of (image_type, sha256). The
    card image is first. A wine with no image is not in the list.

    `sources` maps the sha256 of each original to a dict: `role` (`full` or `label`),
    `path` of the original, `url` of the original on the lab server, and `cuts`: target
    -> the processed file as a dict `sha256`, `path`, `box`, or None. `not_applicable`
    maps a derivative target to its reason. A file that is a full image of one wine and
    a close-up of another wine is a full image.
    """
    def stored(folder, digest, extension):
        return os.path.join(labdb.image_dir(db_path, folder), "%s.%s" % (digest, extension))

    # kind -> source sha256 -> the processed file. An original has at most one cut of
    # each kind (`package`, `label`); schema 017.
    cuts = {target: {} for target in TARGETS}
    for kind, source, digest, left, top, right, bottom, folder, extension in conn.execute(
            "SELECT d.kind, d.source_sha256, d.sha256, d.box_left, d.box_top, d.box_right, "
            "d.box_bottom, i.folder, i.extension FROM image_derivative d "
            "JOIN image i ON i.sha256 = d.sha256"):
        if kind in cuts:
            cuts[kind][source] = {
                "sha256": digest, "box": (left, top, right, bottom),
                "path": stored(folder, digest, extension)}
    absences = {"label": {}}
    for source, settings, reason in conn.execute(
            "SELECT source_sha256, settings, reason FROM image_derivative_absence "
            "WHERE kind = 'label'"):
        if settings == alternatives.SETTINGS_LABEL_ABSENCE:
            absences["label"][source] = reason
    wines, by_slug, sources = [], {}, {}
    for slug, name, producer, category, region, image_type, digest, folder, extension in (
            conn.execute(
                "SELECT w.wine_slug, w.name, w.producer, w.category, w.region, "
                "wi.image_type, wi.sha256, i.folder, i.extension FROM wine_catalog w "
                "JOIN wine_image wi ON wi.wine_slug = w.wine_slug "
                "JOIN image i ON i.sha256 = wi.sha256 "
                "WHERE w.state = 'Active' ORDER BY w.rowid, wi.source_name, wi.sha256")):
        role = ROLES.get(image_type)
        if role is None:
            continue
        wine = by_slug.get(slug)
        if wine is None:
            wine = by_slug[slug] = {"slug": slug, "name": name, "producer": producer,
                                    "category": category, "region": region, "columns": []}
            wines.append(wine)
        wine["columns"].append((image_type, digest))
        source = sources.get(digest)
        if source is None:
            sources[digest] = {
                "role": role, "path": stored(folder, digest, extension),
                "url": "/images/%s/%s.%s" % (folder, digest, extension),
                # `pipeline/seed_label_cuts.py` makes the label cut of a full original.
                "cuts": {target: cuts[target].get(digest) for target in TARGETS},
                "not_applicable": {target: absences.get(target, {}).get(digest)
                                   for target in TARGETS}}
        elif role == "full":
            source["role"] = "full"
    for wine in wines:
        types = {image_type for image_type, _ in wine["columns"]}
        if "main_patched" in types:
            wine["columns"] = [column for column in wine["columns"] if column[0] != "main"]
        wine["columns"].sort(key=lambda column: TYPE_ORDER.index(column[0])
                             if column[0] in TYPE_ORDER else len(TYPE_ORDER))
    used = {digest for wine in wines for _, digest in wine["columns"]}
    sources = {digest: source for digest, source in sources.items() if digest in used}
    return wines, sources


def embedding_hash(source_sha256, view, role, view_config_hash, derivative_sha256):
    return sha256_json({"source_sha256": source_sha256, "view": view, "role": role,
                        "view_config_hash": view_config_hash,
                        "derivative_sha256": derivative_sha256})


def plan_items(embedding, sources):
    """Return the items of an embedding: (sha256, view) -> item, in a stable order.

    A full image is an item of each view. A close-up is an item of the view `label`
    alone, with no steps. An item is a dict: `source_sha256`, `view`, `role`, `steps`,
    `cut` (the processed file that `segment` uses, or None), and `embedding_hash`.
    """
    items = {}
    for digest, source in sources.items():
        role = source["role"]
        for view, view_steps in embedding.views.items():
            if role == "label" and view != "label":
                continue
            steps = view_steps if role == "full" else []
            if not_applicable_reason(embedding, source, view):
                continue
            cut = (source["cuts"].get(steps[0]["target"])
                   if steps and steps[0]["step"] == "segment" else None)
            items[(digest, view)] = {
                "source_sha256": digest, "view": view, "role": role, "steps": steps,
                "cut": cut,
                "embedding_hash": embedding_hash(
                    digest, view, role, embedding.view_config_hash(view, role),
                    cut["sha256"] if cut else None)}
    return items


def not_applicable_reason(embedding, source, view):
    """Return why `view` has no item for `source`, or None when the view applies."""
    if source["role"] != "full":
        return None
    for step in embedding.views[view]:
        if step["step"] == "segment":
            return source["not_applicable"].get(step["target"])
    return None


def not_applicable_count(embedding, sources):
    """Return the number of source views that the database marks not applicable."""
    return sum(not_applicable_reason(embedding, source, view) is not None
               for source in sources.values() for view in embedding.views)


def on_white(image):
    """Put an image with an alpha channel on white. Return an RGB image."""
    if image.mode == "RGBA":
        white = Image.new("RGBA", image.size, (255, 255, 255, 255))
        return Image.alpha_composite(white, image).convert("RGB")
    return image.convert("RGB")


def resize(image, step):
    """Apply one step `resize`. With `upscale` false, an image with no side above
    `max_size` does not change."""
    size = step["max_size"]
    if not step["upscale"] and max(image.size) <= size:
        return image
    if step["aspect"] == "ignore":
        target = (size, size)
    else:
        scale = size / max(image.size)
        target = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    if target == image.size:
        return image
    return image.resize(target, Image.Resampling.LANCZOS)


def prepare(item, source_path, dis_segmenter=None):
    """Return the model input of one item as an RGB image. Raise ItemError."""
    steps, cut = item["steps"], item["cut"]
    if steps and steps[0]["step"] == "segment" and cut is None:
        raise ItemError(NO_CUT[steps[0]["target"]])
    try:
        image, _ = derive.open_image(source_path)
    except OSError as exc:
        raise ItemError("Pillow cannot read the source %s: %s" % (source_path, exc))

    def processed():
        try:
            return derive.open_image(cut["path"])[0]
        except OSError as exc:
            raise ItemError("cannot read the processed file %s: %s" % (cut["path"], exc))

    return apply_steps(image, steps, cut["box"] if cut else None, processed, dis_segmenter)


def apply_steps(image, steps, box, processed, dis_segmenter=None):
    """Apply the steps of one view to an opened source image. Return an RGB image. Raise
    ItemError.

    `box` is the box of the cut in the pixels of the source, and `processed()` returns the
    processed file of the cut. `prepare` gives the cut of a catalogue image, and
    `embedding_run.py` gives the cut of a test photo (plan 33). So both get their pixels
    from this code.
    """
    for step in steps:
        kind = step["step"]
        if kind == "segment":
            left, top, right, bottom = box
            if right > image.width or bottom > image.height:
                raise ItemError("the box %s of the processed file is outside the source "
                                "of %d x %d pixels" % (box, image.width, image.height))
            image = image.crop(box)
        elif kind == "segment_dis":
            if dis_segmenter is None:
                raise ItemError("the DIS runtime is not available")
            try:
                image = dis_segmenter.segment(
                    image, threshold=step["threshold"], margin=step["margin"])
            except dis_litert.DisError as exc:
                raise ItemError(str(exc)) from exc
        elif kind == "remove_background":
            cut = processed()
            if cut.size != image.size:
                raise ItemError("the processed file is %d x %d pixels; its box is %d x %d"
                                % (cut.size + image.size))
            image = cut
        elif kind == "white_background":
            image = on_white(image)
        elif kind == "square_on_white":
            image = dis_litert.square_on_white(image)
        elif kind == "resize":
            image = resize(image, step)
    if derive.has_transparency(image):
        raise ItemError(TRANSPARENT_ERROR)
    return image.convert("RGB")


def png_bytes(image):
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def image_name(source_sha256, view):
    return "%s_%s.png" % (source_sha256, view)


def image_names(directory):
    """Return the names of the prepared images of an embedding directory."""
    try:
        return {entry.name for entry in os.scandir(os.path.join(directory, IMAGES))}
    except FileNotFoundError:
        return set()


def write_atomic(path, data):
    """Write `data` to `path` through a temporary file in the same directory."""
    fd, temporary = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp-")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.remove(temporary)
        except OSError:
            pass
        raise


def read_index(directory):
    """Return the index of an embedding directory, or None when it has none. Raise
    ValueError for a file that is not JSON."""
    try:
        with open(os.path.join(directory, INDEX), encoding="utf-8") as fh:
            index = json.load(fh)
    except FileNotFoundError:
        return None
    if not isinstance(index, dict):
        raise ValueError("%s is not a JSON object" % os.path.join(directory, INDEX))
    return index


def read_vectors(directory, index):
    """Return the vectors that the index names, or None. Raise ValueError when the
    file does not agree with the index."""
    name = (index or {}).get("vectors_file")
    if not name:
        return None
    if not VECTORS_RE.match(name):
        raise ValueError("not a vector file name: %r" % name)
    vectors = np.load(os.path.join(directory, name), allow_pickle=False)
    if vectors.ndim != 2 or vectors.shape[0] != len(index.get("items", [])):
        raise ValueError("%s holds %s vectors; the index holds %d items"
                         % (name, vectors.shape, len(index.get("items", []))))
    return vectors


def write_checkpoint(directory, index, vectors):
    """Write the vectors and the index. Return the index as written.

    The new vector file comes first, then the index that names it, then the old vector
    files are deleted. So a reader never sees an index that names a missing file.
    """
    buffer = io.BytesIO()
    np.save(buffer, np.asarray(vectors, dtype=np.float32), allow_pickle=False)
    data = buffer.getvalue()
    name = "vectors-%s.npy" % hashlib.sha256(data).hexdigest()[:8]
    write_atomic(os.path.join(directory, name), data)
    index = dict(index, vectors_file=name)
    text = json.dumps(index, ensure_ascii=False, indent=1) + "\n"
    write_atomic(os.path.join(directory, INDEX), text.encode("utf-8"))
    for entry in os.scandir(directory):
        if VECTORS_RE.match(entry.name) and entry.name != name:
            os.remove(entry.path)
    return index


def item_status(items, index, names):
    """Return (sha256, view) -> (status, record) for each item.

    `current`: the index holds the item with the same hash, and its image exists.
    `failed`: the last try of this hash failed. The record is the failure.
    `stale`: the index holds the item with another hash, or its image is missing.
    `missing`: the index does not hold the item.
    """
    index = index or {}
    recorded = {(record["source_sha256"], record["view"]): record
                for record in index.get("items", [])}
    failures = {(failure["source_sha256"], failure["view"]): failure
                for failure in index.get("failures", [])}
    out = {}
    for key, item in items.items():
        record, failure = recorded.get(key), failures.get(key)
        if (record and record["embedding_hash"] == item["embedding_hash"]
                and image_name(*key) in names):
            out[key] = ("current", record)
        elif failure and failure["embedding_hash"] == item["embedding_hash"]:
            out[key] = ("failed", failure)
        elif record:
            out[key] = ("stale", record)
        else:
            out[key] = ("missing", None)
    return out


def read_lock(directory):
    """Return the content of `build.lock`, or None. A lock that is not JSON is None."""
    try:
        with open(os.path.join(directory, LOCK), encoding="utf-8") as fh:
            lock = json.load(fh)
    except (OSError, ValueError):
        return None
    return lock if isinstance(lock, dict) else None


def build_alive(pid):
    """Tell whether the process `pid` runs and runs a build. A stale lock can name a
    PID that the system gave to another process later."""
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass
    try:
        command = subprocess.run(["ps", "-o", "command=", "-p", str(pid)],
                                 capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return True
    # The file name of one argument MUST be the script. `test_build_embeddings.py` is
    # not the script.
    return any(os.path.basename(token) == BUILD_SCRIPT_NAME for token in command.split())


def running_pid(directory):
    """Return the PID of the build that holds the lock, or None."""
    lock = read_lock(directory)
    pid = lock.get("pid") if lock else None
    return pid if build_alive(pid) else None


def acquire_lock(directory):
    """Take `build.lock` for this process. A lock of a dead process is removed. Raise
    Busy when a live build holds the lock."""
    path = os.path.join(directory, LOCK)
    for _ in range(2):
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            pid = running_pid(directory)
            if pid:
                raise Busy("another build of this embedding runs: PID %d" % pid)
            try:
                os.remove(path)
            except FileNotFoundError:
                pass
            continue
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"pid": os.getpid(), "started_at": now()}, fh)
        return
    raise Busy("cannot take %s" % path)


def release_lock(directory):
    lock = read_lock(directory)
    if lock and lock.get("pid") == os.getpid():
        try:
            os.remove(os.path.join(directory, LOCK))
        except FileNotFoundError:
            pass


def read_events(directory):
    """Return the JSON events of `build.log`, and its last line that is not JSON."""
    try:
        with open(os.path.join(directory, LOG), encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except FileNotFoundError:
        return [], None
    events, other = [], None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except ValueError:
            value = None
        if isinstance(value, dict) and isinstance(value.get("event"), str):
            events.append(value)
        else:
            other = line
    return events, other


FINAL_STATES = {"done": "done", "stopped": "stopped", "error": "failed"}


def _phase(run):
    """Return the phase of a running build: the model request or the retry that no
    `progress` line followed yet, as the keys `phase`, `phase_event`, and `phase_t`."""
    last = next((event for event in reversed(run)
                 if event["event"] in ("progress", "request", "retry")), None)
    if not last or last["event"] == "progress":
        return {}
    if last["event"] == "request":
        text = "waiting for the model"
    else:
        text = "retry %s in %s s: %s" % (last.get("attempt"), last.get("wait"),
                                         last.get("error") or "")
    return {"phase": text, "phase_event": last["event"], "phase_t": last.get("t")}


def job_state(directory):
    """Return the job of an embedding from `build.lock` and `build.log`.

    `state` is None (no build yet), `running`, `stopping`, `done`, `stopped`, or
    `failed`. A build that started outside the lab server has no progress on the page.
    """
    pid = running_pid(directory)
    events, other = read_events(directory)
    starts = [number for number, event in enumerate(events) if event["event"] == "start"]
    run = events[starts[-1]:] if starts else events
    start = run[0] if run and run[0]["event"] == "start" else None
    progress = next((event for event in reversed(run)
                     if event["event"] in ("progress", "start")), None) or {}
    final = next((event for event in reversed(run) if event["event"] in FINAL_STATES), None)
    job = {"state": None, "pid": pid, "started_at": None, "started_t": None,
           "todo": progress.get("todo"), "done": progress.get("done", 0),
           "built": progress.get("built", 0), "failed": progress.get("failed", 0),
           "message": None, "phase": None, "phase_event": None, "phase_t": None}
    if start:
        job.update(started_at=start.get("time"), started_t=start.get("t"))
    if pid:
        if start and start.get("pid") == pid:
            job["state"] = ("stopping" if any(event["event"] == "stopping" for event in run)
                            else "running")
            job.update(_phase(run))
        else:
            job.update(state="running", started_at=None, started_t=None, todo=None,
                       done=0, built=0, failed=0,
                       message="a build started outside the lab server; no progress here")
    elif final:
        job["state"] = FINAL_STATES[final["event"]]
        job["message"] = final.get("message")
        if final["event"] != "error":
            job.update(done=final.get("done", job["done"]), built=final.get("built", 0),
                       failed=final.get("failed", 0))
    elif events or other:
        job["state"] = "failed"
        job["message"] = other or "the build ended with no final line"
    return job
