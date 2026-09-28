"""Build and validate a standalone matcher bundle.

The validator uses only the bundle and NumPy. The builder imports the lab embedding
module inside `build_bundle`, because a consumer of the bundle does not need that module.
"""

from contextlib import closing
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
import time

import numpy as np


FORMAT = "svoe-vino-matcher-bundle"
FORMAT_VERSION = 1
MANIFEST = "manifest.json"
VECTORS = "vectors.npy"
ITEMS = "items.jsonl"
CANDIDATES = "candidates.jsonl"
WINES = "wines.jsonl"
OMISSIONS = "omissions.jsonl"
IMAGE_MANIFEST = "images.jsonl"
REQUIRED_PAYLOADS = (VECTORS, ITEMS, CANDIDATES, WINES, OMISSIONS)
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ITEM_KEYS = {
    "vector_row", "source_vector_row", "source_sha256", "view", "role",
    "embedding_hash", "derivative_sha256", "image", "width", "height",
}
CANDIDATE_KEYS = {"vector_row", "wine_slug", "view", "image_type"}
WINE_KEYS = {"wine_slug", "name", "producer", "category", "region"}
OMISSION_KEYS = {
    "source_sha256", "view", "role", "embedding_hash", "state", "error",
}
IMAGE_KEYS = {"path", "sha256", "bytes"}


class BundleError(ValueError):
    """The source data or bundle does not satisfy the bundle contract."""


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_record(path):
    path = Path(path)
    return {"sha256": sha256_file(path), "bytes": path.stat().st_size}


def _write_json(path, value):
    Path(path).write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path, values):
    with open(path, "w", encoding="utf-8", newline="\n") as target:
        for value in values:
            target.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def _read_json(path, label):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BundleError("cannot read %s: %s" % (label, exc)) from exc
    if not isinstance(value, dict):
        raise BundleError("%s MUST hold a JSON object" % label)
    return value


def _read_jsonl(path, label):
    values = []
    try:
        with open(path, encoding="utf-8") as source:
            for number, line in enumerate(source, 1):
                if not line.strip():
                    raise BundleError("%s line %d is empty" % (label, number))
                try:
                    value = json.loads(line)
                except ValueError as exc:
                    raise BundleError("%s line %d is not JSON: %s"
                                      % (label, number, exc)) from exc
                if not isinstance(value, dict):
                    raise BundleError("%s line %d MUST hold a JSON object"
                                      % (label, number))
                values.append(value)
    except OSError as exc:
        raise BundleError("cannot read %s: %s" % (label, exc)) from exc
    return values


def _relative_path(value, label):
    if not isinstance(value, str) or not value or "\\" in value:
        raise BundleError("%s MUST be a non-empty POSIX relative path" % label)
    path = PurePosixPath(value)
    if path.is_absolute() or value != path.as_posix() or any(
            part in ("", ".", "..") for part in path.parts):
        raise BundleError("%s MUST be a canonical relative path: %r" % (label, value))
    return Path(*path.parts)


def _payload(root, relative, label):
    relative_path = _relative_path(relative, label)
    path = root
    for part in relative_path.parts:
        path = path / part
        if path.is_symlink():
            raise BundleError("%s MUST NOT use a symbolic link" % label)
    if not path.is_file():
        raise BundleError("%s does not exist: %s" % (label, relative))
    return path


def _hex64(value, label, optional=False):
    if optional and value is None:
        return
    if not isinstance(value, str) or not HEX64.match(value):
        raise BundleError("%s MUST be a lowercase SHA-256 value" % label)


def _integer(value, label, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise BundleError("%s MUST be an integer of %d or more" % (label, minimum))


def _exact_keys(value, keys, label):
    if set(value) != keys:
        missing = sorted(keys - set(value))
        extra = sorted(set(value) - keys)
        parts = []
        if missing:
            parts.append("missing: %s" % ", ".join(missing))
        if extra:
            parts.append("unknown: %s" % ", ".join(extra))
        raise BundleError("%s has invalid keys (%s)" % (label, "; ".join(parts)))


def _owners(embedding, wines, items):
    """Return (source_sha256, view) -> ordered `(wine, image_type)` owners."""
    import embeddings

    owners = {}
    for wine in wines:
        for image_type, digest in wine["columns"]:
            role = embeddings.ROLES.get(image_type)
            for view in embedding.views:
                key = (digest, view)
                if key not in items or (role == "label" and view != "label"):
                    continue
                values = owners.setdefault(key, [])
                if all(owner["slug"] != wine["slug"] for owner, _ in values):
                    values.append((wine, image_type))
    return owners


def _build_in(directory, settings, embedding, include_images):
    """Write an unchecked bundle into the existing empty `directory`."""
    import embeddings

    source_dir = Path(embeddings.entry_dir(settings.db_path, embedding.name))
    index = embeddings.read_index(source_dir)
    if index is None:
        raise BundleError("the embedding %s has no index" % embedding.name)
    vectors = embeddings.read_vectors(source_dir, index)
    if vectors is None:
        raise BundleError("the embedding %s has no vector file" % embedding.name)
    with closing(embeddings.open_database(settings.db_path)) as conn:
        wines, sources = embeddings.read_inputs(conn, settings.db_path)
    planned = embeddings.plan_items(embedding, sources)
    status = embeddings.item_status(planned, index, embeddings.image_names(source_dir))
    owners = _owners(embedding, wines, planned)

    item_rows = []
    candidate_rows = []
    selected_vectors = []
    image_rows = []
    used_slugs = set()
    omissions = []

    for key, item in planned.items():
        state, record = status[key]
        if state != "current":
            omissions.append({
                "source_sha256": key[0],
                "view": key[1],
                "role": item["role"],
                "embedding_hash": item["embedding_hash"],
                "state": state,
                "error": record.get("error") if isinstance(record, dict) else None,
            })
            continue
        source_row = record.get("row")
        if (isinstance(source_row, bool) or not isinstance(source_row, int)
                or not 0 <= source_row < len(vectors)):
            raise BundleError("the current item %s/%s has no valid vector row" % key)
        item_owners = owners.get(key) or []
        if not item_owners:
            raise BundleError("the current item %s/%s has no active wine" % key)
        image_path = record.get("image")
        relative_image = _relative_path(image_path, "source item image")
        vector_row = len(item_rows)
        item_rows.append({
            "vector_row": vector_row,
            "source_vector_row": source_row,
            "source_sha256": key[0],
            "view": key[1],
            "role": item["role"],
            "embedding_hash": record["embedding_hash"],
            "derivative_sha256": record.get("derivative_sha256"),
            "image": PurePosixPath(*relative_image.parts).as_posix(),
            "width": record.get("width"),
            "height": record.get("height"),
        })
        selected_vectors.append(vectors[source_row])
        for wine, image_type in item_owners:
            candidate_rows.append({
                "vector_row": vector_row,
                "wine_slug": wine["slug"],
                "view": key[1],
                "image_type": image_type,
            })
            used_slugs.add(wine["slug"])
        if include_images:
            source = source_dir / relative_image
            if source.is_symlink() or not source.is_file():
                raise BundleError("the prepared image is not a regular file: %s" % image_path)
            target = Path(directory) / relative_image
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            image_rows.append(dict(path=item_rows[-1]["image"], **file_record(target)))

    if not item_rows:
        raise BundleError("the embedding %s has no current item" % embedding.name)
    matrix = np.ascontiguousarray(np.vstack(selected_vectors), dtype=np.float32)
    np.save(Path(directory) / VECTORS, matrix, allow_pickle=False)
    _write_jsonl(Path(directory) / ITEMS, item_rows)
    _write_jsonl(Path(directory) / CANDIDATES, candidate_rows)
    wine_rows = [{key: wine.get(key if key != "wine_slug" else "slug")
                  for key in ("wine_slug", "name", "producer", "category", "region")}
                 for wine in wines if wine["slug"] in used_slugs]
    _write_jsonl(Path(directory) / WINES, wine_rows)
    _write_jsonl(Path(directory) / OMISSIONS, omissions)
    payloads = list(REQUIRED_PAYLOADS)
    if include_images:
        _write_jsonl(Path(directory) / IMAGE_MANIFEST, image_rows)
        payloads.append(IMAGE_MANIFEST)

    source_config = index.get("config")
    if not isinstance(source_config, dict):
        source_config = embedding.summary()
    manifest = {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "created_at": now(),
        "source": {
            "embedding": embedding.name,
            "index_updated_at": index.get("updated_at"),
            "steps_version": index.get("steps_version"),
            "view_config_hash": index.get("view_config_hash"),
        },
        "embedding": source_config,
        "vectors": {
            "file": VECTORS,
            "dtype": "float32",
            "shape": [int(matrix.shape[0]), int(matrix.shape[1])],
            "normalized": "l2",
        },
        "scoring": {
            "similarity": "dot_product",
            "item_reduction": "max",
            "view_reduction": "mean",
        },
        "images": {
            "included": bool(include_images),
            "manifest": IMAGE_MANIFEST if include_images else None,
            "count": len(image_rows),
        },
        "counts": {
            "planned_items": len(status),
            "items": len(item_rows),
            "candidates": len(candidate_rows),
            "wines": len(wine_rows),
            "omissions": len(omissions),
            "images": len(image_rows),
        },
        "files": {name: file_record(Path(directory) / name) for name in payloads},
    }
    _write_json(Path(directory) / MANIFEST, manifest)
    return manifest


def build_bundle(config_path, embedding_name, output, include_images=False):
    """Build, validate, and publish a matcher bundle. Refuse an existing output."""
    import embeddings

    output = Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise BundleError("the output path exists: %s" % output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".%s." % output.name, dir=output.parent))
    try:
        settings = embeddings.load_settings(config_path)
        try:
            embedding = settings.find(embedding_name)
        except KeyError as exc:
            raise BundleError("unknown embedding: %s" % embedding_name) from exc
        _build_in(temporary, settings, embedding, bool(include_images))
        summary = validate_bundle(temporary)
        if output.exists() or output.is_symlink():
            raise BundleError("the output path appeared during the build: %s" % output)
        temporary.rename(output)
        return dict(summary, path=str(output))
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def _validate_files(root, manifest):
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise BundleError("manifest.files MUST be an object")
    included = (manifest.get("images") or {}).get("included")
    expected = set(REQUIRED_PAYLOADS)
    if included is True:
        expected.add(IMAGE_MANIFEST)
    elif included is not False:
        raise BundleError("manifest.images.included MUST be true or false")
    if set(files) != expected:
        raise BundleError("manifest.files MUST name exactly: %s" % ", ".join(sorted(expected)))
    for name, recorded in files.items():
        if not isinstance(recorded, dict):
            raise BundleError("manifest.files.%s MUST be an object" % name)
        _exact_keys(recorded, {"sha256", "bytes"}, "manifest.files.%s" % name)
        _hex64(recorded["sha256"], "manifest.files.%s.sha256" % name)
        _integer(recorded["bytes"], "manifest.files.%s.bytes" % name)
        path = _payload(root, name, "payload %s" % name)
        actual = file_record(path)
        if actual != recorded:
            raise BundleError("payload %s does not match its SHA-256 or byte size" % name)


def _validate_vectors(root, manifest, item_count):
    spec = manifest.get("vectors")
    if not isinstance(spec, dict):
        raise BundleError("manifest.vectors MUST be an object")
    _exact_keys(spec, {"file", "dtype", "shape", "normalized"}, "manifest.vectors")
    if spec["file"] != VECTORS or spec["dtype"] != "float32" or spec["normalized"] != "l2":
        raise BundleError("manifest.vectors has an unsupported file, type, or normalization")
    shape = spec["shape"]
    if (not isinstance(shape, list) or len(shape) != 2
            or any(isinstance(value, bool) or not isinstance(value, int) or value < 1
                   for value in shape)):
        raise BundleError("manifest.vectors.shape MUST hold two positive integers")
    if shape[0] != item_count:
        raise BundleError("the vector shape and item count differ")
    try:
        vectors = np.load(root / VECTORS, mmap_mode="r", allow_pickle=False)
    except (OSError, ValueError) as exc:
        raise BundleError("cannot load vectors.npy: %s" % exc) from exc
    if vectors.dtype != np.dtype("float32") or vectors.ndim != 2 or list(vectors.shape) != shape:
        raise BundleError("vectors.npy does not match the declared type or shape")
    if not vectors.flags.c_contiguous:
        raise BundleError("vectors.npy MUST be C-contiguous")
    if not np.isfinite(vectors).all():
        raise BundleError("vectors.npy holds a non-finite value")
    norms = np.linalg.norm(vectors, axis=1)
    if not np.allclose(norms, 1.0, rtol=1e-5, atol=1e-6):
        raise BundleError("vectors.npy holds a vector that is not L2-normalized")
    return vectors


def _validate_records(root, manifest):
    items = _read_jsonl(root / ITEMS, ITEMS)
    wines = _read_jsonl(root / WINES, WINES)
    candidates = _read_jsonl(root / CANDIDATES, CANDIDATES)
    omissions = _read_jsonl(root / OMISSIONS, OMISSIONS)
    counts = manifest.get("counts")
    if not isinstance(counts, dict):
        raise BundleError("manifest.counts MUST be an object")
    expected_counts = {
        "planned_items": len(items) + len(omissions),
        "items": len(items),
        "candidates": len(candidates),
        "wines": len(wines),
        "omissions": len(omissions),
        "images": (manifest.get("images") or {}).get("count"),
    }
    if counts != expected_counts:
        raise BundleError("manifest.counts does not match the payload records")

    views = (manifest.get("embedding") or {}).get("views")
    if not isinstance(views, dict) or not views:
        raise BundleError("manifest.embedding.views MUST be a non-empty object")
    item_by_row = {}
    item_keys = set()
    image_paths = set()
    for number, item in enumerate(items, 1):
        label = "%s line %d" % (ITEMS, number)
        _exact_keys(item, ITEM_KEYS, label)
        _integer(item["vector_row"], label + ".vector_row")
        _integer(item["source_vector_row"], label + ".source_vector_row")
        if item["vector_row"] != number - 1:
            raise BundleError("%s vector rows MUST be contiguous and ordered" % ITEMS)
        _hex64(item["source_sha256"], label + ".source_sha256")
        _hex64(item["embedding_hash"], label + ".embedding_hash")
        _hex64(item["derivative_sha256"], label + ".derivative_sha256", optional=True)
        if item["view"] not in views:
            raise BundleError("%s names an unknown view" % label)
        if item["role"] not in ("full", "label"):
            raise BundleError("%s role MUST be full or label" % label)
        _integer(item["width"], label + ".width", minimum=1)
        _integer(item["height"], label + ".height", minimum=1)
        relative = _relative_path(item["image"], label + ".image")
        image_name = PurePosixPath(*relative.parts).as_posix()
        if image_name in image_paths:
            raise BundleError("%s repeats image %s" % (ITEMS, image_name))
        image_paths.add(image_name)
        key = (item["source_sha256"], item["view"])
        if key in item_keys:
            raise BundleError("%s repeats source/view %s/%s" % ((ITEMS,) + key))
        item_keys.add(key)
        item_by_row[item["vector_row"]] = item

    wine_slugs = set()
    for number, wine in enumerate(wines, 1):
        label = "%s line %d" % (WINES, number)
        _exact_keys(wine, WINE_KEYS, label)
        slug = wine["wine_slug"]
        if not isinstance(slug, str) or not slug:
            raise BundleError("%s wine_slug MUST be a non-empty string" % label)
        if slug in wine_slugs:
            raise BundleError("%s repeats wine_slug %s" % (WINES, slug))
        wine_slugs.add(slug)
        for key in WINE_KEYS - {"wine_slug"}:
            if wine[key] is not None and not isinstance(wine[key], str):
                raise BundleError("%s.%s MUST be a string or null" % (label, key))

    used_rows = set()
    used_wines = set()
    candidate_keys = set()
    for number, candidate in enumerate(candidates, 1):
        label = "%s line %d" % (CANDIDATES, number)
        _exact_keys(candidate, CANDIDATE_KEYS, label)
        row = candidate["vector_row"]
        _integer(row, label + ".vector_row")
        if row not in item_by_row:
            raise BundleError("%s names unknown vector row %s" % (label, row))
        slug = candidate["wine_slug"]
        if slug not in wine_slugs:
            raise BundleError("%s names unknown wine_slug %r" % (label, slug))
        if candidate["view"] != item_by_row[row]["view"]:
            raise BundleError("%s view differs from its item" % label)
        if not isinstance(candidate["image_type"], str) or not candidate["image_type"]:
            raise BundleError("%s image_type MUST be a non-empty string" % label)
        key = (row, slug)
        if key in candidate_keys:
            raise BundleError("%s repeats vector-row/wine %s/%s"
                              % ((CANDIDATES,) + key))
        candidate_keys.add(key)
        used_rows.add(row)
        used_wines.add(slug)
    if used_rows != set(item_by_row):
        raise BundleError("each vector row MUST have at least one candidate")
    if used_wines != wine_slugs:
        raise BundleError("each wine MUST own at least one candidate")

    for number, omission in enumerate(omissions, 1):
        label = "%s line %d" % (OMISSIONS, number)
        _exact_keys(omission, OMISSION_KEYS, label)
        _hex64(omission["source_sha256"], label + ".source_sha256")
        _hex64(omission["embedding_hash"], label + ".embedding_hash")
        if omission["view"] not in views or omission["role"] not in ("full", "label"):
            raise BundleError("%s has an invalid view or role" % label)
        if omission["state"] not in ("failed", "missing", "stale"):
            raise BundleError("%s has an invalid state" % label)
        if omission["error"] is not None and not isinstance(omission["error"], str):
            raise BundleError("%s error MUST be a string or null" % label)
    return items, candidates, wines, omissions, image_paths


def _validate_images(root, manifest, image_paths):
    spec = manifest.get("images")
    if not isinstance(spec, dict) or set(spec) != {"included", "manifest", "count"}:
        raise BundleError("manifest.images has invalid keys")
    _integer(spec["count"], "manifest.images.count")
    if not spec["included"]:
        if spec["manifest"] is not None or spec["count"] != 0:
            raise BundleError("a bundle without images MUST have no image manifest or count")
        if (root / "images").exists() or (root / "images").is_symlink():
            raise BundleError("a bundle without images MUST NOT hold an images directory")
        return
    if spec["manifest"] != IMAGE_MANIFEST:
        raise BundleError("a bundle with images MUST name images.jsonl")
    images = _read_jsonl(root / IMAGE_MANIFEST, IMAGE_MANIFEST)
    if len(images) != spec["count"] or len(images) != len(image_paths):
        raise BundleError("the image count does not match the items")
    found = set()
    for number, image in enumerate(images, 1):
        label = "%s line %d" % (IMAGE_MANIFEST, number)
        _exact_keys(image, IMAGE_KEYS, label)
        relative = _relative_path(image["path"], label + ".path")
        name = PurePosixPath(*relative.parts).as_posix()
        if name in found:
            raise BundleError("%s repeats path %s" % (IMAGE_MANIFEST, name))
        found.add(name)
        _hex64(image["sha256"], label + ".sha256")
        _integer(image["bytes"], label + ".bytes")
        path = _payload(root, name, "prepared image %s" % name)
        if file_record(path) != {"sha256": image["sha256"], "bytes": image["bytes"]}:
            raise BundleError("prepared image %s does not match its manifest" % name)
    if found != image_paths:
        raise BundleError("the image manifest paths do not match the items")


def validate_bundle(directory):
    """Validate one bundle. Return its counts and vector shape."""
    root = Path(directory).absolute()
    if root.is_symlink() or not root.is_dir():
        raise BundleError("the bundle is not a regular directory: %s" % root)
    manifest = _read_json(root / MANIFEST, MANIFEST)
    if manifest.get("format") != FORMAT:
        raise BundleError("unsupported bundle format: %r" % manifest.get("format"))
    if manifest.get("format_version") != FORMAT_VERSION:
        raise BundleError("unsupported bundle format version: %r"
                          % manifest.get("format_version"))
    if not isinstance(manifest.get("source"), dict):
        raise BundleError("manifest.source MUST be an object")
    if not isinstance(manifest.get("embedding"), dict):
        raise BundleError("manifest.embedding MUST be an object")
    if manifest.get("scoring") != {
            "similarity": "dot_product", "item_reduction": "max",
            "view_reduction": "mean"}:
        raise BundleError("manifest.scoring is not supported")
    _validate_files(root, manifest)
    items, candidates, wines, omissions, image_paths = _validate_records(root, manifest)
    vectors = _validate_vectors(root, manifest, len(items))
    _validate_images(root, manifest, image_paths)
    return {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "items": len(items),
        "candidates": len(candidates),
        "wines": len(wines),
        "omissions": len(omissions),
        "images": manifest["images"]["count"],
        "dimension": int(vectors.shape[1]),
    }
