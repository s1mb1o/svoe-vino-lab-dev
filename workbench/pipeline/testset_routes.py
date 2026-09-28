"""The routes of the Testset page of the lab server.

The page shows the test sets of the lab database and writes the labels of their photos.
`testsets.py` does each read and each write. Read `docs/plans/24_testset-page.md`. The
dialog `New testset…` of `/runs` makes a new set with `testset_from_run.py` (plan 44).

    GET  /testset                 the page
    GET  /api/testset?set=<name>  the rows of one set (the first set without `set`)
    POST /api/testset-label       {set, place, file, label}; label null clears it
    POST /api/testset-delete      {set, place, file, delete}
    POST /api/testset-photo-comment
                                  {set, place, file, text, source?}: a new comment of
                                  one photo; source user (the default) or script
    POST /api/testset-photo-comment-remove
                                  {set, place, file, id}: remove one comment of one photo
    POST /api/testset-photo-tag   {set, place, file, tag}: a new tag of the image of one
                                  photo; each photo of the same bytes shows it (plan 66)
    POST /api/testset-photo-tag-remove
                                  {set, place, file, tag}: remove one tag of the image
    POST /api/testset-box         {set, place, file, box}; box [l, t, r, b] or null
    POST /api/testset-move        {set, place, file, to}; to a slug, __null__ (the row
                                  "No Match"), or __drawer__ (the Drawer)
    POST /api/testset-upload?set=<name>&place=<slug>&name=<file name>
                                  the body is the bytes of one image; place a slug,
                                  __null__, or __drawer__
    GET  /api/testset-from-run?id=<run id>
                                  the dialog `New testset…` of `/runs`: the set of the
                                  run, the proposed name, the counts of the misses
    POST /api/testset-from-run    {run, misses, name}; misses r1 or r5: a new set from
                                  the misses of the run (plan 44, `testset_from_run.py`)
    POST /api/testset-new         {name}: a new empty set (plan 57, `Add new testset …`)

A write runs in one transaction. `lab_server.py` answers HTTP 503 for an error of the
database or of the configuration. The comments of a whole wine use the route
`/api/dataset-comment` of the Dataset page (plan 51).
"""
import json
import urllib.parse
from contextlib import closing

import lab_pages
import testset_from_run
import testsets

PAGE_ROUTE = "/testset"
API = "/api/testset"
UPLOAD = "/api/testset-upload"
FROM_RUN = "/api/testset-from-run"
NEW = "/api/testset-new"
JSON_TYPE = "application/json; charset=utf-8"
# The largest body of a write, in bytes. The JSON form of a comment of 4,000 characters
# MAY need 6 bytes for each character.
MAX_BODY = 32768
# route -> the function of `testsets.py` and the keys of the body that it takes.
WRITES = {
    "/api/testset-label": (testsets.set_label, ("set", "place", "file", "label")),
    "/api/testset-delete": (testsets.set_delete, ("set", "place", "file", "delete")),
    "/api/testset-photo-comment": (testsets.add_photo_comment,
                                   ("set", "place", "file", "text", "source")),
    "/api/testset-photo-comment-remove": (testsets.remove_photo_comment,
                                          ("set", "place", "file", "id")),
    "/api/testset-photo-tag": (testsets.add_photo_tag, ("set", "place", "file", "tag")),
    "/api/testset-photo-tag-remove": (testsets.remove_photo_tag,
                                      ("set", "place", "file", "tag")),
    "/api/testset-box": (testsets.set_box, ("set", "place", "file", "box")),
    "/api/testset-move": (testsets.move_photo, ("set", "place", "file", "to")),
    # The fields of an upload come from the query; `data` is the body. Read `_upload_body`.
    UPLOAD: (testsets.upload_photo, ("set", "place", "data", "name")),
    NEW: (testsets.create_set, ("name",)),
    # `respond` puts the directory of the runs of the server before these keys.
    FROM_RUN: (testset_from_run.build, ("run", "misses", "name")),
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
    if route == FROM_RUN and method in ("GET", "HEAD"):
        run_id = (urllib.parse.parse_qs(parts.query).get("id") or [""])[0]
        with closing(open_database(server.db_path)) as conn:
            try:
                return _json(200, testset_from_run.dialog_view(
                    conn, testset_from_run.runs_dir_of(server), run_id))
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
    if route == FROM_RUN:
        # The directory of the runs comes from the server, never from the body.
        args.insert(0, testset_from_run.runs_dir_of(server))
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
