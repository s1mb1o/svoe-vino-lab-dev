"""The routes of the label descriptions of the images (plan 61,
`docs/plans/61_label-descriptions.md`).

    GET    /api/image-label-descriptions?sha256=<sha256>
    POST   /api/image-label-description    {"sha256": "...", "description": {...}}
    DELETE /api/image-label-description    {"id": <id>}

Each answer is the view of one image (`label_descriptions.view`): its rows, the latest
first, the id of the latest row, and its failures of stage 3. The image MUST be linked to
a wine. A POST adds a manual row, which becomes the latest. A DELETE removes one row; when
it removes the last row of the image, the image waits for stage 3 again.
"""
import json
import re
import urllib.parse
from contextlib import closing

import image_descriptions
import label_descriptions

LIST = "/api/image-label-descriptions"
ONE = "/api/image-label-description"
ROUTES = frozenset((LIST, ONE))
JSON_TYPE = "application/json; charset=utf-8"
SHA256_RE = re.compile(r"^[0-9a-f]{64}\Z")
# The largest body of a write. The JSON form of one character of a description MAY need
# 6 bytes, for example `\ud83c`.
MAX_BODY = 6 * label_descriptions.MAX_MANUAL_BYTES + 1024


def handles(route):
    """Answer whether `route` belongs to the label descriptions."""
    return route in ROUTES


def _json(code, value):
    return code, value, JSON_TYPE, "no-store"


def _error(code, message):
    return _json(code, {"error": message})


def _body(read_body):
    """Return (the JSON object of the body, None), or (None, the error answer)."""
    data = read_body(MAX_BODY)
    if data is None:
        return None, _error(400, "the body MUST be JSON of at most %d bytes" % MAX_BODY)
    try:
        body = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None, _error(400, "the body is not JSON")
    if not isinstance(body, dict):
        return None, _error(400, "the body MUST be a JSON object")
    return body, None


def _max_attempts():
    """Return `max_attempts` of the running watcher, else 3."""
    return image_descriptions.max_attempts_of(image_descriptions.read_status() or {})


def _write(open_database, db_path, work):
    """Run `work(conn)` in one write transaction and return its result."""
    with closing(open_database(db_path, write=True)) as conn:
        conn.isolation_level = None
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("BEGIN IMMEDIATE")
        try:
            result = work(conn)
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
    return result


def _add(open_database, db_path, body):
    sha256, description = body.get("sha256"), body.get("description")
    if not isinstance(sha256, str) or not SHA256_RE.match(sha256):
        return _error(400, "`sha256` MUST be 64 lower-case hex digits")
    if not isinstance(description, dict):
        return _error(400, "`description` MUST be a JSON object")
    try:
        size = len(label_descriptions.dumps(description).encode("utf-8"))
    except UnicodeEncodeError:
        # JSON admits a lone surrogate (`"\ud800"`), SQLite cannot store it.
        return _error(400, "`description` holds a lone surrogate character")
    if size > label_descriptions.MAX_MANUAL_BYTES:
        return _error(400, "`description` MUST be at most %d bytes of JSON"
                      % label_descriptions.MAX_MANUAL_BYTES)
    max_attempts = _max_attempts()

    def work(conn):
        if not image_descriptions.is_linked(conn, sha256):
            return _error(404, "no wine image with the sha256 %s" % sha256)
        label_descriptions.add_manual(conn, sha256, description)
        return _json(200, label_descriptions.view(conn, sha256, max_attempts))
    return _write(open_database, db_path, work)


def _remove(open_database, db_path, body):
    row_id = body.get("id")
    if not isinstance(row_id, int) or isinstance(row_id, bool) or row_id < 1:
        return _error(400, "`id` MUST be a positive integer")
    max_attempts = _max_attempts()

    def work(conn):
        sha256 = label_descriptions.remove(conn, row_id)
        if sha256 is None:
            return _error(404, "no label description with the id %d" % row_id)
        return _json(200, label_descriptions.view(conn, sha256, max_attempts))
    return _write(open_database, db_path, work)


def respond(server, method, path, read_body, open_database):
    """Answer one request. Return (HTTP code, body, content type, Cache-Control).

    `read_body(limit)` returns the bytes of the body, or None when the body is empty or
    longer than `limit`. `open_database(path, write=False)` is the function of
    `lab_server.py`: it raises `ConfigError` for a database that the code cannot use.
    """
    parts = urllib.parse.urlsplit(path)
    route = parts.path
    if route == LIST:
        if method not in ("GET", "HEAD"):
            return _error(405, "the route %s answers GET alone" % route)
        sha256 = (urllib.parse.parse_qs(parts.query).get("sha256") or [""])[0]
        if not SHA256_RE.match(sha256):
            return _error(400, "`sha256` MUST be 64 lower-case hex digits")
        with closing(open_database(server.db_path)) as conn:
            if not image_descriptions.is_linked(conn, sha256):
                return _error(404, "no wine image with the sha256 %s" % sha256)
            return _json(200, label_descriptions.view(conn, sha256, _max_attempts()))
    if method not in ("POST", "DELETE"):
        return _error(405, "the route %s answers POST and DELETE alone" % route)
    body, error = _body(read_body)
    if error:
        return error
    if method == "POST":
        return _add(open_database, server.db_path, body)
    return _remove(open_database, server.db_path, body)
