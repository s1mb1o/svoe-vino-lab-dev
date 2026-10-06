"""Persist disposable summaries with source identity and content checks."""
import hashlib
import json
import os
import tempfile

MISS = object()


def _digest(value):
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(data.encode()).hexdigest()


def _path(directory, kind, name):
    return os.path.join(directory, kind, hashlib.sha256(str(name).encode()).hexdigest() + ".json")


def load(directory, kind, name, identity):
    """Return a checked payload, or MISS. An unreadable cache is a miss."""
    if directory is None:
        return MISS
    try:
        with open(_path(directory, kind, name), encoding="utf-8") as source:
            record = json.load(source)
        if (isinstance(record, dict) and record.get("identity") == _digest(identity)
                and "data" in record and record.get("checksum") == _digest(record["data"])):
            return record["data"]
    except (OSError, ValueError, TypeError):
        pass
    return MISS


def store(directory, kind, name, identity, data):
    """Replace one cache file atomically. A cache write cannot fail a request."""
    if directory is None:
        return
    temporary = None
    try:
        path = _path(directory, kind, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        record = {"identity": _digest(identity), "checksum": _digest(data), "data": data}
        descriptor, temporary = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp-")
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(record, output, ensure_ascii=False, separators=(",", ":"))
        os.replace(temporary, path)
        temporary = None
    except (OSError, ValueError, TypeError):
        pass
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except OSError:
                pass
