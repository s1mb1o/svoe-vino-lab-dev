"""Read a local image that a drop from the Codex desktop app names.

A drag of an image out of the Codex desktop app carries the address
`app://fs/@fs/<absolute path>`, not a file. The browser cannot open that address. The
page sends the address to the lab server, and the lab server gives the image bytes back.
The page then makes a File and hands it to its usual file flow (`pipeline/pages/drop.js`).

    GET /api/local-image?address=<app://fs/@fs/... or file://...>
                                   the image bytes, or a JSON error

The server reads only a file under `~/.codex*/generated_images/` with an image
extension, and only up to `testsets.UPLOAD_MAX` bytes (owner answers of
2026-09-30T22:26:00+0300). A symbolic link that leaves such a folder is refused. The
module writes no file and changes no row of the lab database. The upload route of the
page still checks the bytes as an image.
"""
import glob
import json
import os
import urllib.parse

import testsets

API = "/api/local-image"
JSON_TYPE = "application/json; charset=utf-8"
NO_STORE = "no-store"
APP_PREFIX = "app://fs/@fs/"
FILE_PREFIX = "file://"
ADDRESS_MAX = 4096
CONTENT_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                 ".webp": "image/webp", ".gif": "image/gif"}


class LocalImageError(Exception):
    """The address does not name an allowed local image. `code` is the HTTP code."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def handles(route):
    """Answer whether `route` belongs to this module."""
    return route == API


def allowed_roots(home=None):
    """Return the real paths of the folders `<home>/.codex*/generated_images`."""
    home = home or os.path.expanduser("~")
    pattern = os.path.join(glob.escape(home), ".codex*", "generated_images")
    return sorted({os.path.realpath(root) for root in glob.glob(pattern)
                   if os.path.isdir(root)})


def path_of(address):
    """Return the absolute path of an `app://fs/@fs/` or `file://` address."""
    if not isinstance(address, str) or not address.strip():
        raise LocalImageError(400, "the drop holds no local image address")
    address = address.strip()
    if len(address) > ADDRESS_MAX:
        raise LocalImageError(400, "the local image address is too long")
    lower = address.lower()
    if lower.startswith(APP_PREFIX):
        raw = "/" + address[len(APP_PREFIX):]
    elif lower.startswith(FILE_PREFIX):
        parts = urllib.parse.urlsplit(address)
        if parts.netloc not in ("", "localhost"):
            raise LocalImageError(400, "a file address MUST name a local file")
        raw = parts.path
    else:
        raise LocalImageError(400, "only an app://fs/@fs/ or file:// address is local")
    raw = urllib.parse.unquote(raw.split("?", 1)[0].split("#", 1)[0])
    if "\0" in raw or not os.path.isabs(raw):
        raise LocalImageError(400, "the local image address holds no absolute path")
    return raw


def read_image(address, roots=None, limit=None):
    """Return `(bytes, file name, content type)` of one allowed local image."""
    roots = allowed_roots() if roots is None else roots
    limit = testsets.UPLOAD_MAX if limit is None else limit
    real = os.path.realpath(path_of(address))
    if not any(os.path.commonpath([root, real]) == root for root in roots):
        raise LocalImageError(403, "the lab server reads only Codex generated images "
                                   "(~/.codex*/generated_images)")
    content_type = CONTENT_TYPES.get(os.path.splitext(real)[1].lower())
    if not content_type:
        raise LocalImageError(400, "the file is not a PNG, JPEG, WebP, or GIF image")
    if not os.path.isfile(real):
        raise LocalImageError(404, "the file does not exist: %s" % os.path.basename(real))
    if os.path.getsize(real) > limit:
        raise LocalImageError(413, "the image is larger than %d bytes" % limit)
    with open(real, "rb") as fh:
        data = fh.read(limit + 1)
    if not data:
        raise LocalImageError(400, "the file is empty")
    if len(data) > limit:
        raise LocalImageError(413, "the image is larger than %d bytes" % limit)
    return data, os.path.basename(real), content_type


def respond(method, path):
    """Answer one request. Return (HTTP code, body, content type, Cache-Control)."""
    if method != "GET":
        return 405, json.dumps({"error": "the route %s answers GET alone" % API}), \
            JSON_TYPE, NO_STORE
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(path).query)
    address = (query.get("address") or [""])[0]
    try:
        data, _name, content_type = read_image(address)
    except LocalImageError as exc:
        return exc.code, json.dumps({"error": str(exc)}), JSON_TYPE, NO_STORE
    return 200, data, content_type, NO_STORE
