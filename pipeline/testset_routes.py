"""The routes of the Testset page of the lab server.

The page shows the test sets of the lab database and writes the labels of their photos.
`testsets.py` does each read and each write. Read `docs/plans/24_testset-page.md`.

    GET  /testset                 the page
    GET  /api/testset?set=<name>  the rows of one set (the first set without `set`)
    POST /api/testset-label       {set, place, file, label}; label null clears it
    POST /api/testset-delete      {set, place, file, delete}
    POST /api/testset-comment     {set, place, file, text}; an empty text removes it
    POST /api/testset-box         {set, place, file, box}; box [l, t, r, b] or null
    POST /api/testset-wine-note   {set, slug, text}; an empty text removes it
    POST /api/testset-exclude     {set, slug, excluded, reason}
    POST /api/testset-move        {set, place, file, to}; to a slug, __null__ (the row
                                  "No Match"), or __drawer__ (the Drawer)
    POST /api/testset-upload?set=<name>&place=<slug>&name=<file name>
                                  the body is the bytes of one image; place a slug,
                                  __null__, or __drawer__

A write runs in one transaction. `lab_server.py` answers HTTP 503 for an error of the
database or of the configuration.
"""
import json
import urllib.parse
from contextlib import closing

import lab_pages
import testsets

PAGE_ROUTE = "/testset"
API = "/api/testset"
UPLOAD = "/api/testset-upload"
JSON_TYPE = "application/json; charset=utf-8"
# The largest body of a write, in bytes. The JSON form of a comment of 4,000 characters
# MAY need 6 bytes for each character.
MAX_BODY = 32768
# route -> the function of `testsets.py` and the keys of the body that it takes.
WRITES = {
    "/api/testset-label": (testsets.set_label, ("set", "place", "file", "label")),
    "/api/testset-delete": (testsets.set_delete, ("set", "place", "file", "delete")),
    "/api/testset-comment": (testsets.set_comment, ("set", "place", "file", "text")),
    "/api/testset-box": (testsets.set_box, ("set", "place", "file", "box")),
    "/api/testset-wine-note": (testsets.set_wine_note, ("set", "slug", "text")),
    "/api/testset-exclude": (testsets.set_excluded, ("set", "slug", "excluded", "reason")),
    "/api/testset-move": (testsets.move_photo, ("set", "place", "file", "to")),
    # The fields of an upload come from the query; `data` is the body. Read `_upload_body`.
    UPLOAD: (testsets.upload_photo, ("set", "place", "data", "name")),
}
ROUTES = frozenset((PAGE_ROUTE, API) + tuple(WRITES))


def handles(route):
    """Answer whether `route` belongs to the Testset page."""
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
    try:
        # JSON admits a lone surrogate (`"\ud800"`), SQLite cannot store it.
        json.dumps(body, ensure_ascii=False).encode("utf-8")
    except UnicodeEncodeError:
        return None, _error(400, "the body holds a lone surrogate character")
    return body, None


def _upload_body(query, read_body):
    """Return (the fields of an upload, None), or (None, the error answer). The query
    holds `set`, `place`, and `name`. The body is the bytes of the image."""
    data = read_body(testsets.UPLOAD_MAX)
    if data is None:
        return None, _error(400, "the body MUST be an image of at most %d bytes"
                            % testsets.UPLOAD_MAX)
    fields = {key: values[0] for key, values in urllib.parse.parse_qs(query).items()}
    return dict(fields, data=data), None


def respond(server, method, path, read_body, open_database, card_images):
    """Answer one request. Return (HTTP code, body, content type, Cache-Control).

    `read_body(limit)` returns the bytes of the body, or None when the body is empty or
    longer than `limit`. `open_database(path, write=False)` and `card_images(conn)` are
    the functions of `lab_server.py`.
    """
    parts = urllib.parse.urlsplit(path)
    route = parts.path
    if route == PAGE_ROUTE:
        if method not in ("GET", "HEAD"):
            return _error(405, "the route %s answers GET alone" % route)
        return 200, lab_pages.page("testset.html"), "text/html; charset=utf-8", "no-store"
    if route == API:
        if method not in ("GET", "HEAD"):
            return _error(405, "the route %s answers GET alone" % route)
        query = urllib.parse.parse_qs(parts.query)
        set_name = (query.get("set") or [None])[0] or None
        with closing(open_database(server.db_path)) as conn:
            try:
                return _json(200, testsets.set_view(conn, set_name, card_images))
            except testsets.TestsetError as exc:
                return _error(exc.code, str(exc))
    if method != "POST":
        return _error(405, "the route %s answers POST alone" % route)
    if route == UPLOAD:
        body, error = _upload_body(parts.query, read_body)
    else:
        body, error = _body(read_body)
    if error:
        return error
    write, keys = WRITES[route]
    args = [body.get(key) for key in keys]
    with closing(open_database(server.db_path, write=True)) as conn:
        conn.isolation_level = None
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("BEGIN IMMEDIATE")
        try:
            answer = write(conn, *args)
            conn.execute("COMMIT")
        except testsets.TestsetError as exc:
            conn.execute("ROLLBACK")
            return _error(exc.code, str(exc))
        except BaseException:
            conn.execute("ROLLBACK")
            raise
    return _json(200, answer)
