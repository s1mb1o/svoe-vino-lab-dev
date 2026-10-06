"""Persist checked catalogue metadata and read-only matrices. A bad cache is a miss."""
from collections import defaultdict
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from types import CodeType
import uuid

import numpy as np

from checked_read_cache import signature

VERSION = 1
MAX_ENTRIES = 8
MAX_BYTES = 512 * 1024 * 1024
MAX_ENTRY_BYTES = 256 * 1024 * 1024
MAX_METADATA_BYTES = 8 * 1024 * 1024
GENERATION = re.compile(r"^[0-9a-f]{64}-[0-9a-f]{32}$")


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _digest(value):
    return hashlib.sha256(_json(value)).hexdigest()


def _file(path):
    try:
        return list(signature(path))
    except FileNotFoundError:
        return None


def _code(value):
    """Describe loaded bytecode without marshal's process-dependent reference flags."""
    if isinstance(value, CodeType):
        return [value.co_code.hex(), list(value.co_names), [_code(c) for c in value.co_consts]]
    if isinstance(value, bytes):
        return {"bytes": value.hex()}
    if isinstance(value, tuple):
        return [_code(c) for c in value]
    if isinstance(value, frozenset):
        return {"set": sorted((_code(c) for c in value), key=lambda c: _json(c))}
    return value


def identity(embedding, db_path):
    """Check SQLite main/WAL files, index, prepared membership, settings, and source code."""
    import embeddings
    try:
        directory = Path(embeddings.entry_dir(db_path, embedding.name))
        code = Path(__file__).parent
        files = [Path(db_path).absolute(), Path(str(db_path) + "-wal"),
                 directory / embeddings.INDEX, directory / embeddings.IMAGES]
        files += [code / name for name in ("catalogue_snapshot.py", "embedding_run.py",
                                          "embeddings.py", "alternatives.py", "labdb.py", "arcface.py")]
        settings = [embedding.summary(),
                    [[view, role, embedding.view_config_hash(view, role)]
                     for view in embedding.views for role in ("full", "label")]]
        # Bind the cache to loaded code too. A file can change while a worker runs.
        functions = [getattr(embeddings, name) for name in
                     ("read_inputs", "plan_items", "item_status", "embedding_hash",
                      "not_applicable_reason", "read_vectors", "record_rows", "check_rows")]
        functions += [sys.modules["embedding_run"].Catalogue.__init__]
        loaded_code = _digest([_code(f.__code__) for f in functions])
        return {"version": VERSION, "settings": settings, "loaded_code": loaded_code,
                "python": sys.implementation.cache_tag,
                "sources": [[str(path), _file(path)] for path in files]}
    except (OSError, AttributeError, TypeError, ValueError):
        return None


def _location(embedding, db_path):
    key = _digest([os.path.abspath(db_path), embedding.summary()])
    root = Path(db_path).absolute().parent.parent / "cache" / "catalogue-snapshots"
    return root, key


def _checksum(path):
    value = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def restore(target, embedding, db_path):
    """Restore a snapshot only after its sources, checksums, and shapes pass."""
    import embeddings
    try:
        root, key = _location(embedding, db_path)
        manifest = root / (key + ".json")
        if manifest.stat().st_size > MAX_METADATA_BYTES:
            return False
        meta = json.loads(manifest.read_text())
        checksum = meta.pop("checksum")
        if checksum != _digest(meta) or meta["identity"] != identity(embedding, db_path):
            return False
        generation = meta["generation"]
        if not GENERATION.fullmatch(generation) or not generation.startswith(key + "-"):
            return False
        directory = root / generation
        vector_file = meta["vector_file"]
        if not isinstance(vector_file, str) or not embeddings.VECTORS_RE.fullmatch(vector_file):
            return False
        vector_path = Path(embeddings.entry_dir(db_path, embedding.name)) / vector_file
        if meta["vector_signature"] != _file(vector_path):
            return False
        slugs, dim = meta["slugs"], meta["dim"]
        if (not isinstance(slugs, list) or not slugs
                or any(not isinstance(s, str) for s in slugs) or len(set(slugs)) != len(slugs)
                or not isinstance(dim, int) or not 0 < dim <= 65536):
            return False
        loaded = {"slugs": slugs, "dim": dim, "state": meta["state"],
                  "views": {}, "items": {}, "angles": {}, "rows_of": {}}
        total, checked = 0, []
        for view, record in meta["views"].items():
            if view not in embedding.views:
                return False
            arrays = {}
            for kind, details in record["arrays"].items():
                name = details["file"]
                if not re.fullmatch(r"[0-9]+-(matrix|numbers|angles)\.npy", name):
                    return False
                path = directory / name
                before = signature(path)
                total += before[2]
                if total > MAX_ENTRY_BYTES or _checksum(path) != details["sha256"]:
                    return False
                array = np.load(path, mmap_mode="r", allow_pickle=False)
                if (list(array.shape) != details["shape"] or str(array.dtype) != details["dtype"]
                        or signature(path) != before):
                    return False
                checked.append((path, before))
                arrays[kind] = array
            matrix, numbers = arrays["matrix"], arrays["numbers"]
            count = len(numbers)
            if (matrix.dtype != np.float32 or numbers.dtype != np.int64
                    or numbers.ndim != 1 or matrix.shape != (count, dim) or count == 0
                    or np.any(numbers < 0) or np.any(numbers >= len(slugs))):
                return False
            references, items = record["references"], record["items"]
            if len(references) != count or any(not isinstance(item, dict) for item in items):
                return False
            if any(not isinstance(i, int) or not 0 <= i < len(items) for i in references):
                return False
            loaded["views"][view] = matrix, numbers
            # Rotated rows MUST share their original item object for items_of grouping.
            loaded["items"][view] = [items[i] for i in references]
            rows = defaultdict(list)
            for position, number in enumerate(numbers.tolist()):
                rows[number].append(position)
            loaded["rows_of"][view] = rows
            if "angles" in arrays:
                angles = arrays["angles"]
                if angles.dtype != np.int16 or angles.shape != (count,):
                    return False
                loaded["angles"][view] = angles
        if (not loaded["views"] or meta["identity"] != identity(embedding, db_path)
                or meta["vector_signature"] != _file(vector_path)
                or any(signature(path) != before for path, before in checked)):
            return False
        target.__dict__.update(loaded)
        return True
    except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError):
        return False


def _prune(root, keep):
    """Delete only this cache's old generations. The writer holds the cache lock."""
    generations = []
    for path in root.iterdir():
        if path.is_dir() and not path.is_symlink() and GENERATION.fullmatch(path.name):
            size = sum(child.stat().st_size for child in path.iterdir() if child.is_file())
            manifest = root / (path.name.split("-")[0] + ".json")
            if manifest.exists():
                size += manifest.stat().st_size
            generations.append((path.stat().st_mtime_ns, path, size))
    generations.sort(reverse=True)
    total, count = 0, 0
    # Keep the new generation even when two writers get the same timestamp.
    generations.sort(key=lambda item: item[1].name != keep)
    for _, path, size in generations:
        count += 1
        total += size
        if count > MAX_ENTRIES or total > MAX_BYTES:
            shutil.rmtree(path)
    for manifest in root.glob("*.json"):
        if re.fullmatch(r"[0-9a-f]{64}\.json", manifest.name):
            try:
                generation = json.loads(manifest.read_text())["generation"]
                if GENERATION.fullmatch(generation) and not (root / generation).exists():
                    manifest.unlink()
            except (OSError, ValueError, KeyError, TypeError):
                pass


def store(target, embedding, db_path, before, vector_file, vector_signature):
    """Publish complete files atomically. A failed or unstable cache write is harmless."""
    import embeddings
    temporary, manifest_tmp, completed = None, None, None
    try:
        vector_path = Path(embeddings.entry_dir(db_path, embedding.name)) / vector_file
        if (before is None or before != identity(embedding, db_path)
                or vector_signature != _file(vector_path)):
            return
        root, key = _location(embedding, db_path)
        root.mkdir(parents=True, exist_ok=True)
        with (root / ".write.lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return
            temporary = Path(tempfile.mkdtemp(prefix=".tmp-", dir=root))
            generation = key + "-" + uuid.uuid4().hex
            meta = {"identity": before, "generation": generation, "vector_file": vector_file,
                    "vector_signature": vector_signature, "slugs": target.slugs,
                    "dim": target.dim, "state": target.state, "views": {}}
            total = 0
            for number, (view, (matrix, numbers)) in enumerate(target.views.items()):
                unique, lookup, references = [], {}, []
                for item in target.items[view]:
                    if id(item) not in lookup:
                        lookup[id(item)] = len(unique)
                        unique.append(item)
                    references.append(lookup[id(item)])
                arrays = {"matrix": matrix, "numbers": numbers}
                if view in target.angles:
                    arrays["angles"] = target.angles[view]
                record = {"items": unique, "references": references, "arrays": {}}
                for kind, array in arrays.items():
                    path = temporary / (str(number) + "-" + kind + ".npy")
                    np.save(path, array, allow_pickle=False)
                    total += path.stat().st_size
                    if total > min(MAX_ENTRY_BYTES, MAX_BYTES):
                        return
                    record["arrays"][kind] = {"file": path.name, "sha256": _checksum(path),
                                             "shape": list(array.shape), "dtype": str(array.dtype)}
                meta["views"][view] = record
            meta["checksum"] = _digest(meta)
            data = _json(meta)
            if (len(data) > MAX_METADATA_BYTES or total + len(data) > min(MAX_ENTRY_BYTES, MAX_BYTES)
                    or before != identity(embedding, db_path)
                    or vector_signature != _file(vector_path)):
                return
            completed = root / generation
            temporary.rename(completed)
            temporary = None
            descriptor, manifest_tmp = tempfile.mkstemp(prefix=".tmp-", dir=root)
            with os.fdopen(descriptor, "wb") as output:
                output.write(data)
            os.replace(manifest_tmp, root / (key + ".json"))
            manifest_tmp, completed = None, None
            _prune(root, generation)
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    finally:
        for path in (temporary, completed):
            if path is not None:
                shutil.rmtree(path, ignore_errors=True)
        if manifest_tmp is not None:
            try:
                os.unlink(manifest_tmp)
            except OSError:
                pass
