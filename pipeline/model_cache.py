"""The cache of the model calls: GDINO, SAM3, and the VLMs.

A call that repeats an earlier successful call reads the answer from `data/cache/` and
sends no request. Read docs/plans/25_model-call-cache.md.

Rules:
- The key is the sha256 of the canonical JSON of the request fields: `v`, `endpoint`
  (the full URL), `model` (the served name), `params`, `prompt`, and `images` (the sha256
  of each sent image). The timeout, the retries, the headers, and the API key are not in
  the key.
- One record is one JSON file `<ROOT>/<model>/<key[0:2]>/<key>.json`. It holds the
  request fields and the answer as the service sent it.
- The caller stores a success alone. A failure is not stored.
- A record is a hit only when its request fields equal the request fields of the call.
  A file that cannot be read is a miss.
- With `READ` off, each lookup is a miss, and `store` still writes the fresh answer.
- The module imports the standard library alone, so `scripts/` can import it too.
"""
import base64
import binascii
import hashlib
import json
import os
import re
import sys
import tempfile
import time

VERSION = 1

# The directory of the records. A unit test sets this to a temporary directory.
ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "data", "cache")

# The reads of the records in this process. `run_job.py --no-cache` (the checkbox `Use
# caches` of the dialog `Run>`, off) sets it to False before it builds the backend: each
# model call then goes to its service, so the latency of the run is real time (owner
# answers of 2026-09-26T01:32:00+0300). Read docs/plans/39_use-caches-checkbox.md.
READ = True

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]")
_warned = False


def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def request_fields(endpoint, model, params, prompt, images):
    """Return the request fields of one call. `images` is a list of the bytes that are
    sent, in the order of the request."""
    return {"v": VERSION, "endpoint": endpoint, "model": model, "params": params,
            "prompt": prompt, "images": [sha256_hex(data) for data in images]}


def vlm_fields(url, payload):
    """Return the request fields of an OpenAI-compatible chat request, or None when a
    message holds an image URL that is not a base64 data URL. Such a call gets no lookup
    and is not stored, because the content behind a URL can change."""
    images = []
    messages = []
    for message in payload.get("messages") or []:
        content = message.get("content")
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "image_url":
                    image_url = dict(part.get("image_url") or {})
                    head, sep, data = (image_url.get("url") or "").partition(",")
                    if not (head.startswith("data:") and head.endswith(";base64") and sep):
                        return None
                    try:
                        raw = base64.b64decode(data, validate=True)
                    except (binascii.Error, ValueError):
                        return None
                    images.append(raw)
                    image_url["url"] = "%s,sha256:%s" % (head, sha256_hex(raw))
                    part = dict(part, image_url=image_url)
                parts.append(part)
            message = dict(message, content=parts)
        messages.append(message)
    params = {key: value for key, value in payload.items()
              if key not in ("model", "messages")}
    return request_fields(url, payload.get("model") or "", params, messages, images)


def key_of(fields):
    return sha256_hex(canonical(fields).encode("utf-8"))


def path_of(fields, key=None):
    key = key or key_of(fields)
    model = _UNSAFE.sub("-", fields.get("model") or "") or "-"
    return os.path.join(ROOT, model, key[:2], key + ".json")


def lookup(fields):
    """Return the record of `fields`, or None. With `READ` off, return None."""
    if not READ:
        return None
    path = path_of(fields)
    try:
        with open(path, encoding="utf-8") as fh:
            record = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(record, dict) or "answer" not in record:
        return None
    if canonical(record.get("request")) != canonical(fields):
        return None
    return record


def store(fields, answer, ms):
    """Write the record of a successful call. A failed write prints one warning for each
    process and does not raise."""
    global _warned
    key = key_of(fields)
    path = path_of(fields, key)
    record = {"v": VERSION, "key": key, "request": fields,
              "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "ms": round(ms),
              "answer": answer}
    temporary = None
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        handle, temporary = tempfile.mkstemp(prefix=key + ".", suffix=".tmp",
                                             dir=os.path.dirname(path))
        with os.fdopen(handle, "w", encoding="utf-8") as fh:
            fh.write(canonical(record))
        # `mkstemp` makes the file 0600. A record gets the mode of the other data files.
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    except (OSError, TypeError, ValueError) as exc:
        if temporary:
            try:
                os.unlink(temporary)
            except OSError:
                pass
        if not _warned:
            _warned = True
            sys.stderr.write("model_cache: cannot write %s: %s\n" % (path, exc))
