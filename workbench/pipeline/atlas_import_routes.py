"""The routes of "New from Atlas" of the Dataset page of the lab server (plan 95).

`lab_server.py` sends each route that `handles` accepts to `respond`, and sends the
answer. The server keeps no job: the dialog sends `advance` again until each Atlas step
is terminal. `create` is a function of `lab_server.py` (`start_atlas_wine`), because it
uses the index jobs and the code scanner of the server. Read
docs/plans/95_new-from-atlas.md.

    POST /api/atlas-import/advance    {url}: send the missing Atlas requests, and send
                                      the state of the three steps and the prefill
    GET  /api/atlas-import/photos     ?url=: the best photo of each group of similar
                                      photos that Atlas has now, and the product name
    POST /api/atlas-import/create     the form values, `url`, and `media_ids`: create the
                                      wine with no main photo
    POST /api/atlas-import/add        {slug, url, media_ids}: add the photos to an
                                      existing wine as additional photos (the button
                                      `load photos` of a card; it runs no Atlas step)
    GET  /atlas-import.js             the script of the dialog
"""
import json
import os
import urllib.parse

import atlas_import
import manual_wines
import patches

API = "/api/atlas-import"
ADVANCE = API + "/advance"
PHOTOS = API + "/photos"
CREATE = API + "/create"
ADD = API + "/add"
SCRIPT_ROUTE = "/atlas-import.js"
SCRIPT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pages",
                           "atlas_import.js")
JSON = "application/json; charset=utf-8"
NO_STORE = "no-store"
BODY_LIMIT = 64 * 1024
ROUTES = {ADVANCE: "POST", PHOTOS: "GET", CREATE: "POST", ADD: "POST", SCRIPT_ROUTE: "GET"}


def handles(route):
    """Tell whether a route belongs to "New from Atlas"."""
    return route in ROUTES


def _json(code, value):
    return code, value, JSON, NO_STORE


def _error(code, message):
    return _json(code, {"error": message})


def _body(read_body):
    data = read_body(BODY_LIMIT)
    if data is None:
        return None
    try:
        body = json.loads(data)
    except ValueError:
        return None
    return body if isinstance(body, dict) else None


def _client(url):
    origin, product_uuid, hidden = atlas_import.parse_url(url)
    return atlas_import.AtlasClient(origin, hidden), product_uuid


def respond(method, path, read_body, create, add):
    """Return (the HTTP status, the body, the content type, the cache header).

    `read_body(limit)` returns the request body, or None for a body that is absent or
    larger than `limit`. `create(body)` creates the wine and returns the answer. `add(body)`
    adds the photos to an existing wine and returns the answer. Each raises
    `atlas_import.AtlasError`, `manual_wines.WineError`, or `patches.PatchError`.
    """
    parts = urllib.parse.urlsplit(path)
    route = parts.path
    if method == "HEAD" and ROUTES[route] == "GET":
        method = "GET"
    if method != ROUTES[route]:
        return _error(405, "%s answers %s only" % (route, ROUTES[route]))
    if route == SCRIPT_ROUTE:
        with open(SCRIPT_FILE, encoding="utf-8") as fh:
            return 200, fh.read(), "text/javascript; charset=utf-8", NO_STORE
    try:
        if route == PHOTOS:
            url = (urllib.parse.parse_qs(parts.query).get("url") or [None])[0]
            client, product_uuid = _client(url)
            return _json(200, atlas_import.select_photos(client, client.product(product_uuid)))
        body = _body(read_body)
        if body is None:
            return _error(400, "the body MUST be a JSON object of at most %d bytes"
                          % BODY_LIMIT)
        if route == ADVANCE:
            client, product_uuid = _client(body.get("url"))
            return _json(200, atlas_import.advance(client, product_uuid))
        return _json(200, (create if route == CREATE else add)(body))
    except (atlas_import.AtlasError, manual_wines.WineError, patches.PatchError) as exc:
        return _error(exc.code, str(exc))
