"""Import the live catalogue of vino-svoe.ru into the table `wine_catalog`.

Usage:
    python3 pipeline/import_website.py --db data/catalog/catalog.sqlite3                  # the CLI
    python3 pipeline/import_website.py --db data/catalog/catalog.sqlite3 --prepare DIR    # the UI, step 1
    python3 pipeline/import_website.py --db data/catalog/catalog.sqlite3 --apply DIR      # the UI, step 2

The source is the JSON API `https://api.vino-svoe.ru/v1` and `wines-sitemap.xml` of
vino-svoe.ru. The `robots.txt` of the API allows `*/img/*` and `*/file-proxy/*` alone;
the owner chose the API on 2026-09-25 with this knowledge. Read
`docs/plans/18_import-website.md` and `docs/plans/21_website-import-ui.md`.

Rules of the compare:
- The tool reads each list page over one reused HTTPS connection. The count of distinct
  slugs MUST equal `totalItems`. Two different items with the same slug stop the run. A
  list with no wine stops it. The sitemap gives the `lastmod` of each slug.
- A conflict is a changed text field or a changed main image. The text fields are
  `COMPARED` after the mapping of `list_values`. The tool downloads the original image of
  each website wine and compares its SHA-256 with `main`, never with `main_patched`. The
  same bytes under a new upload name are no change.
- A plain change is a new wine, a missing wine, a restored wine, or a stored main image.
- `renames` lists the possible renames for the dialog: a missing wine and a new wine with
  the same main image, a short slug distance, or the same name and producer. The list is
  display only. The write does not read it.
- A refusal of the table `website_refusal` matches while its situation stays. A matching
  refusal removes its conflict from the run. A write deletes each refusal that did not
  match. Only a conflict gets a refusal: a plain change is never refused (owner messages
  of 2026-09-26T19:58:00+0300 and 20:05:00).
- A problem is not a conflict: a list problem, a website slug with the prefix of a
  manual wine (`manual_wines.is_manual`), a website wine with no image, a new wine with
  an empty required value, a bad extension. A problem stops each mode. A network error
  or an HTTP error after the retries stops the run at once.

The modes:
- The compare is disabled in the code: `COMPARE_ENABLED` is False. The CLI and
  `--prepare` stop with the error `COMPARE_DISABLED` and send no request.
- The CLI stops on a problem or a conflict. The error lists all of them, and nothing
  changes. With none, it applies each plain change.
- `--prepare DIR` never writes the database. It writes `DIR/diff.json` and the website
  images that an apply can need to `DIR/images/`. A conflict is no error.
- `--apply DIR` reads `DIR/diff.json` and the choices of a person in `DIR/choices.json`.
  A conflict with no choice and a cleared plain change are skipped: no write, no
  refusal, no comment. The next compare shows them again. It writes `DIR/result.json`.

Rules of the change:
- A new wine is inserted as `Active` with its image as `main`. Comment `COMMENT_NEW`.
- A `Removed` wine on the website becomes `Active`, also when a person removed it.
  Comment `COMMENT_BACK`.
- An `Active` or a `Disabled` wine that is not on the website becomes `Removed`, with
  `removed_by` = `import`. A manual wine never does. Comment `COMMENT_MISSING`.
- A `Disabled` wine on the website stays `Disabled`.
- A website wine with no `main` row gets its image as `main`. Comment `COMMENT_MAIN`.
- A conflict choice of the dialog writes the row of the table in plan 21 and its comment.
- Each write sets `website_modified_at` of each website wine. Each comment has the
  source `script`.

Rules of the store: as in `seed_images.py`. The file is `images/main/<sha256>.<extension>`,
the extension of the upload name in lower case. `source_name` is the upload name and
`match_method` is `website`. `derive.derive_all` processes each new original before the
write transaction. `alternatives.full_label_cut` then makes its label cut, for the view
`label` of the Embeddings page (plan 22). The first time that SAM3 does not answer stops
the label requests; each original with no label cut counts in `no_label_cut`.

The compare reads the database with no lock, because the downloads take minutes. The
write takes `BEGIN IMMEDIATE` and compares a digest of the rows with the digest of the
compare. A change stops the write with no change. All rows are written in one
transaction.
"""
import argparse
import datetime
import hashlib
import http.client
import io
import json
import os
import re
import sqlite3
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ElementTree

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alternatives  # noqa: E402
import comments  # noqa: E402
import derive  # noqa: E402
import imagestore  # noqa: E402
import labdb  # noqa: E402
import manual_wines  # noqa: E402
from import_catalog import FIELDS, STATES  # noqa: E402
from seed_images import print_derivatives  # noqa: E402

API = "https://api.vino-svoe.ru/v1"
LIST_URL = API + "/wines?page=%d&perPage=%d"
CARD_URL = API + "/wines/%s"
FILE_URL = API + "/file-proxy/str-api-file-name"
SITEMAP_URL = "https://vino-svoe.ru/wines-sitemap.xml"
SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
PER_PAGE = 30  # the maximum of the API
USER_AGENT = "svoe-vino-lab import_website.py"
# The owner disabled the compare in the code (owner message of 2026-09-29T23:23:00+0300,
# answer of 23:27:00). `_compare` refuses each start while the value is False: the CLI,
# `--prepare`, and the button `Compare` of the Dataset page. `--apply` reads only a run
# directory and stays.
COMPARE_ENABLED = False
COMPARE_DISABLED = ("the website compare is disabled in the code: "
                    "import_website.COMPARE_ENABLED is False")
# The pause between two requests, the retries, and the timeout of one request. The
# values of `wine-sites-crawler/.../fetch_vino_svoe_dataset.py`.
DELAY = 0.25
RETRIES = 5
TIMEOUT = 60
RETRY_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})

IMAGE_TYPE = "main"
MATCH_METHOD = "website"
EXTENSION_RE = re.compile(r"^[0-9a-z]+$")
# The fields that the compare checks. The list page holds them.
COMPARED = ("name", "producer", "category", "color", "region")
# The kinds of a plain change, in the order of the dialog.
CHANGE_KINDS = ("new", "missing", "back", "main")
CHOICES = ("database", "website")
COMMENT_NEW = "New on vino-svoe.ru."
COMMENT_BACK = "Back on vino-svoe.ru."
COMMENT_MISSING = "Missing on vino-svoe.ru."
COMMENT_MAIN = "Main image from vino-svoe.ru."
# The files of a run directory of the UI mode.
DIFF_FILE = "diff.json"
CHOICES_FILE = "choices.json"
RESULT_FILE = "result.json"
IMAGES_DIR = "images"
# The number of slugs that one report line names.
SHOWN = 10
# The length of a field value in an error message.
VALUE_CHARS = 60
# A progress line after this many images.
PROGRESS = 100
CHANGED = "the database changed during the import; run the import again"
# A possible rename: at most this many edits between the two slugs, or at most this share
# of the longer slug (owner answer of 2026-09-26T19:22:30+0300).
RENAME_EDITS = 3
RENAME_SHARE = 0.2


class WebsiteError(Exception):
    """The website, the database, or a choice file does not allow the run."""


class FetchError(WebsiteError):
    """A request failed after all retries."""


class Client:
    """A sequential HTTPS client with one reused connection for each host, a pause
    between two requests, and retries."""

    def __init__(self, delay=DELAY, retries=RETRIES, timeout=TIMEOUT):
        self.delay = delay
        self.retries = retries
        self.timeout = timeout
        self._last = 0.0
        self._connections = {}
        self.requests = 0
        self.bytes = 0

    def _drop(self, host):
        connection = self._connections.pop(host, None)
        if connection is not None:
            connection.close()

    def close(self):
        for host in list(self._connections):
            self._drop(host)

    def get(self, url, accept="application/json"):
        """Return the body of `url`. Raise `FetchError` after the last retry."""
        parts = urllib.parse.urlsplit(url)
        if parts.scheme != "https":
            raise FetchError("%s: not an HTTPS address" % url)
        target = parts.path + ("?" + parts.query if parts.query else "")
        last = None
        for attempt in range(self.retries + 1):
            wait = self.delay - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            try:
                self._last = time.monotonic()
                self.requests += 1
                connection = self._connections.get(parts.netloc)
                if connection is None:
                    connection = http.client.HTTPSConnection(parts.netloc,
                                                             timeout=self.timeout)
                    self._connections[parts.netloc] = connection
                connection.request("GET", target, headers={
                    "User-Agent": USER_AGENT, "Accept": accept})
                response = connection.getresponse()
                body = response.read()
                if response.will_close:
                    self._drop(parts.netloc)
                if response.status == 200:
                    self.bytes += len(body)
                    return body
                last = "HTTP %d %s" % (response.status, response.reason)
                if response.status not in RETRY_CODES:
                    break
            # A network error, a timeout, an SSL error, or a broken answer.
            except (OSError, http.client.HTTPException) as exc:
                self._drop(parts.netloc)
                last = exc
            if attempt < self.retries:
                time.sleep(min(2 ** attempt, 10))
        raise FetchError("%s: %s" % (url, last))

    def get_json(self, url):
        try:
            return json.loads(self.get(url).decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise FetchError("%s: the answer is not JSON: %s" % (url, exc))


class Report:
    """The result of one write."""

    def __init__(self):
        self.website = 0          # wines on the website
        self.images = 0           # images downloaded
        self.added = []           # slugs of new wines
        self.restored = []        # slugs: Removed -> Active
        self.removed = []         # slugs: Active or Disabled -> Removed
        self.mains = []           # slugs of existing wines that got a main image
        self.texts = []           # "slug field" of the text choices `website`
        self.replaced = []        # slugs of the image choices `website`
        self.refusals = []        # "slug kind" of the new refusals
        self.unresolved = []      # ids of the conflicts with no choice; nothing is written
        self.skipped = []         # ids of the cleared plain changes; nothing is written
        self.refused = 0          # conflicts that a refusal skipped
        self.stale = 0            # refusals deleted, because they did not match
        self.times = 0            # values of `website_modified_at` written
        self.unchanged = 0        # other website wines of the database
        self.written = 0          # image files written to the store
        self.comments = 0         # comments added
        self.requests = 0
        self.bytes = 0
        self.states = {}
        self.label_cuts = 0       # label cuts written
        self.no_label_cut = 0     # new originals with no label cut and no marker
        self.derivatives = derive.Derivatives()

    def empty(self):
        return not (self.added or self.restored or self.removed or self.mains
                    or self.texts or self.replaced or self.refusals or self.stale
                    or self.times)

    def as_dict(self):
        out = {key: value for key, value in vars(self).items() if key != "derivatives"}
        out["processed"] = dict(self.derivatives.methods)
        out["no_sam3"] = self.derivatives.unavailable
        return out


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def clean(value):
    """Return a text value without its outer white space, or None when it is empty.
    A card holds some values as an object with `name`."""
    if isinstance(value, dict):
        value = value.get("name")
    if not isinstance(value, str):
        return None
    return value.strip() or None


def list_values(item):
    """Return the compared fields of one list item after the mapping of plan 18."""
    category = clean(item.get("category"))
    return {
        "name": clean(item.get("title")),
        "producer": clean(item.get("manufacturer")),
        "category": category.split()[0] if category else None,
        "color": clean(item.get("color")),
        "region": clean(item.get("region")),
    }


def image_url(item):
    """Return the `/uploads/...` path of the main image of an item, or None."""
    image = item.get("image")
    url = image.get("url") if isinstance(image, dict) else None
    return url if isinstance(url, str) and url.strip() else None


def upload_name(url):
    return url.rstrip("/").rsplit("/", 1)[-1]


def file_url(url):
    """Return the address of the original upload behind `/uploads/...`."""
    return FILE_URL + urllib.parse.quote(url, safe="/._-")


def extension_of(name):
    return os.path.splitext(name)[1][1:].lower()


def _short(value):
    text = "NULL" if value is None else repr(value)
    return text if len(text) <= VALUE_CHARS else text[:VALUE_CHARS - 1] + "…"


def _names(slugs):
    shown = ", ".join(slugs[:SHOWN])
    return shown + (", …" if len(slugs) > SHOWN else "")


# ------------------------------------------------------------------ the image store
# The store path, the URL, the read of `image`, and the `INSERT INTO image` are each in
# one function. The flat image store of plan 13 changes them.


def store_path(db_path, folder, digest, extension):
    """Return the path of one file of the image store."""
    return os.path.join(labdb.image_dir(db_path, folder), "%s.%s" % (digest, extension))


def store_url(folder, digest, extension):
    """Return the URL of one file of the image store on the lab server."""
    return "/images/%s/%s.%s" % (folder, digest, extension)


def stored_file(conn, digest):
    """Return (folder, extension) of a file that `image` holds, or None."""
    return conn.execute("SELECT folder, extension FROM image WHERE sha256 = ?",
                        (digest,)).fetchone()


def insert_image(conn, digest, folder, extension, width, height):
    """Write the row of `image` of an original, unless the table holds it."""
    conn.execute("INSERT INTO image (sha256, folder, extension, width, height) "
                 "VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
                 (digest, folder, extension, width, height))
    if width is not None:
        conn.execute("UPDATE image SET width = ?, height = ? WHERE sha256 = ? "
                     "AND width IS NULL", (width, height, digest))


def pixel_size(data):
    """Return (width, height) from the header of the image bytes, or (None, None)."""
    try:
        with Image.open(io.BytesIO(data)) as image:
            return image.size
    except (OSError, ValueError, SyntaxError):
        return None, None


# ------------------------------------------------------------------------ the compare


class State:
    """The rows of the database that the compare reads and the write checks."""

    def __init__(self, conn):
        self.wines = {row[0]: row for row in conn.execute(
            "SELECT %s, state, removed_by FROM wine_catalog ORDER BY rowid"
            % ", ".join(FIELDS))}
        self.mains = {slug: (digest, name, folder, extension)
                      for slug, digest, name, folder, extension in conn.execute(
                          "SELECT w.wine_slug, w.sha256, w.source_name, i.folder, "
                          "i.extension FROM wine_image w JOIN image i ON i.sha256 = w.sha256 "
                          "WHERE w.image_type = ?", (IMAGE_TYPE,))}
        self.refusals = {(slug, kind, field): value for slug, kind, field, value in
                         conn.execute("SELECT wine_slug, kind, field, website_value "
                                      "FROM website_refusal")}

    def digest(self):
        rows = [list(row) for row in self.wines.values()]
        mains = sorted([slug, main[0]] for slug, main in self.mains.items())
        refusals = sorted(list(key) + [value] for key, value in self.refusals.items())
        data = json.dumps([rows, mains, refusals], ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(data.encode("utf-8")).hexdigest()


def fetch_list(client, problems, log):
    """Return slug -> list item of the whole catalogue, in list order."""
    items = {}
    page, pages, total = 1, 1, None
    while page <= pages:
        data = client.get_json(LIST_URL % (page, PER_PAGE))
        try:
            pages, total, rows = int(data["totalPages"]), int(data["totalItems"]), data["items"]
        except (KeyError, TypeError, ValueError) as exc:
            raise WebsiteError("list page %d has no valid totalPages, totalItems, and "
                               "items: %s" % (page, exc))
        for item in rows:
            slug = clean(item.get("slug")) if isinstance(item, dict) else None
            if slug is None:
                problems.append("list page %d: an item has no slug" % page)
                continue
            old = items.get(slug)
            if old is None:
                items[slug] = item
            elif old != item:
                problems.append("%s: the list holds two different items with this slug"
                                % slug)
        if page % 10 == 0 or page == pages:
            log("list: page %d/%d, %d wines" % (page, pages, len(items)))
        page += 1
    if not items:
        raise WebsiteError("the website list holds no wine")
    if len(items) != total:
        problems.append("the list holds %d distinct slugs, and totalItems is %d; the "
                        "catalogue changed during the read, so run the import again"
                        % (len(items), total))
    return items


def fetch_sitemap(client):
    """Return slug -> `lastmod` of `wines-sitemap.xml`."""
    try:
        root = ElementTree.fromstring(client.get(SITEMAP_URL, accept="application/xml"))
    except ElementTree.ParseError as exc:
        raise WebsiteError("the wine sitemap is not valid XML: %s" % exc)
    times = {}
    for url in root.iter(SITEMAP_NS + "url"):
        loc = (url.findtext(SITEMAP_NS + "loc") or "").strip()
        lastmod = (url.findtext(SITEMAP_NS + "lastmod") or "").strip()
        if "/wines/" in loc and lastmod:
            times[urllib.parse.unquote(loc.rstrip("/").rsplit("/", 1)[-1])] = lastmod
    return times


def _stored(state, slug):
    """Return the stored main image of a wine for the dialog, or None."""
    main = state.mains.get(slug)
    if main is None:
        return None
    digest, name, folder, extension = main
    return {"sha256": digest, "source_name": name, "url": store_url(folder, digest, extension)}


def compare(conn, client, log=print):
    """Compare the website with the database. Return (diff, blobs): the JSON-safe diff of
    plan 21, and sha256 -> bytes of each website image that a write can need."""
    state = State(conn)
    problems = []
    items = fetch_list(client, problems, log)
    problems.extend("%s: a website slug starts with %r, the prefix of a manual wine"
                    % (slug, manual_wines.MANUAL_PREFIX) for slug in items
                    if manual_wines.is_manual(slug))
    times = fetch_sitemap(client)
    wines, mains, refusals = state.wines, state.mains, state.refusals
    status = len(FIELDS)
    matched = set()

    def refused(key, value=None):
        if key in refusals and refusals[key] == value:
            matched.add(key)
            return True
        return False

    conflicts, changes = [], []
    for slug, item in items.items():
        old = wines.get(slug)
        if old is None:
            continue
        new = list_values(item)
        for field in COMPARED:
            before = old[FIELDS.index(field)]
            if before != new[field] and not refused((slug, "text", field), new[field]):
                conflicts.append({"id": "text:%s:%s" % (slug, field), "slug": slug,
                                  "kind": "text", "field": field, "state": old[status],
                                  "name": old[1], "database": before, "website": new[field]})

    blobs, images = {}, {}
    done = 0
    for slug, item in items.items():
        url = image_url(item)
        if url is None:
            problems.append("%s: the website shows no image" % slug)
            continue
        data = client.get(file_url(url), accept="image/*")
        done += 1
        if done % PROGRESS == 0 or done == len(items):
            log("images: %d/%d" % (done, len(items)))
        digest, name = hashlib.sha256(data).hexdigest(), upload_name(url)
        extension = extension_of(name)
        if not EXTENSION_RE.match(extension):
            problems.append("%s: the upload name %r has no valid extension" % (slug, name))
            continue
        images[slug] = {"sha256": digest, "name": name, "extension": extension,
                        "file": "%s/%s.%s" % (IMAGES_DIR, digest, extension)}
        main = mains.get(slug)
        if main is None or main[0] != digest:
            blobs[digest] = data
        if main is not None and main[0] != digest and not refused((slug, "image", ""), digest):
            conflicts.append({"id": "image:%s" % slug, "slug": slug, "kind": "image",
                              "state": wines[slug][status], "name": wines[slug][1],
                              "database": _stored(state, slug), "website": images[slug]})

    for slug, item in items.items():
        if slug in wines:
            continue
        card = client.get_json(CARD_URL % urllib.parse.quote(slug, safe=""))
        values = list_values(item)
        grapes = [clean(grape) for grape in card.get("grapes") or []]
        values.update({"wine_slug": slug,
                       "grapes": ", ".join(name for name in grapes if name) or None,
                       "description": clean(card.get("description")),
                       "csv_photo_name": images[slug]["name"] if slug in images else None})
        empty = [field for field in FIELDS if field != "grapes" and values[field] is None]
        if empty:
            problems.append("%s: the new wine has no %s" % (slug, ", ".join(empty)))
        changes.append({"id": "new:%s" % slug, "slug": slug, "kind": "new",
                        "name": values["name"], "producer": values["producer"],
                        "row": [values[field] for field in FIELDS], "image": images.get(slug)})
    for slug, row in wines.items():
        if slug in items or row[status] == "Removed" or manual_wines.is_manual(slug):
            continue
        changes.append({"id": "missing:%s" % slug, "slug": slug, "kind": "missing",
                        "name": row[1], "producer": row[2], "state": row[status],
                        "stored": _stored(state, slug)})
    for slug in items:
        row = wines.get(slug)
        if row is not None and row[status] == "Removed":
            changes.append({"id": "back:%s" % slug, "slug": slug, "kind": "back",
                            "name": row[1], "producer": row[2], "removed_by": row[status + 1],
                            "stored": _stored(state, slug)})
    for slug in items:
        if slug in wines and slug not in mains and slug in images:
            changes.append({"id": "main:%s" % slug, "slug": slug, "kind": "main",
                            "name": wines[slug][1], "producer": wines[slug][2],
                            "state": wines[slug][status], "image": images[slug]})

    needed = {entry["image"]["sha256"] for entry in changes if entry.get("image")}
    needed |= {entry["website"]["sha256"] for entry in conflicts if entry["kind"] == "image"}
    diff = {
        "created_at": now_utc(), "snapshot": state.digest(), "website": len(items),
        "images": done, "problems": problems, "conflicts": conflicts, "changes": changes,
        "refused": len(matched), "stale": [list(key) for key in refusals if key not in matched],
        "times": {slug: times.get(slug) for slug in items},
        "unchanged": sum(1 for slug in items if slug in wines),
        "requests": getattr(client, "requests", 0), "bytes": getattr(client, "bytes", 0),
    }
    return diff, {digest: data for digest, data in blobs.items() if digest in needed}


def conflict_line(entry):
    """Return the error line of one conflict in the form of plan 18."""
    if entry["kind"] == "text":
        return "%s (%s): the text changed: %s %s -> %s" % (
            entry["slug"], entry["state"], entry["field"], _short(entry["database"]),
            _short(entry["website"]))
    stored, website = entry["database"], entry["website"]
    return ("%s: the main image changed: stored %s (sha256 %s), website %s (sha256 %s)"
            % (entry["slug"], stored["source_name"], stored["sha256"], website["name"],
               website["sha256"]))


def edit_distance(a, b, limit):
    """Return the Levenshtein distance of two strings, or `limit + 1` when it is larger."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    previous = list(range(len(b) + 1))
    for i, char in enumerate(a, 1):
        current = [i]
        for j, other in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1,
                               previous[j - 1] + (char != other)))
        if min(current) > limit:
            return limit + 1
        previous = current
    return min(previous[-1], limit + 1)


def _plain(value):
    """Return a name or a producer in lower case, with no punctuation and single spaces."""
    return " ".join(re.sub(r"[\W_]+", " ", (value or "").lower().replace("ё", "е")).split())


def renames(diff):
    """Return the possible renames of a diff: [{"old", "new", "reasons"}], the slug of a
    missing wine, the slug of a new wine, and the matched rules. Display only."""
    new = [entry for entry in diff["changes"] if entry["kind"] == "new"]
    found = []
    for old in diff["changes"]:
        if old["kind"] != "missing":
            continue
        stored = (old.get("stored") or {}).get("sha256")
        name = _plain(old["name"]), _plain(old["producer"])
        for entry in new:
            reasons = []
            if stored and stored == (entry.get("image") or {}).get("sha256"):
                reasons.append("same image")
            limit = max(RENAME_EDITS, int(RENAME_SHARE * max(len(old["slug"]), len(entry["slug"]))))
            distance = edit_distance(old["slug"], entry["slug"], limit)
            if distance <= limit:
                reasons.append("slug distance %d" % distance)
            if name[0] and name == (_plain(entry["name"]), _plain(entry["producer"])):
                reasons.append("same name and producer")
            if reasons:
                found.append({"old": old["slug"], "new": entry["slug"], "reasons": reasons})
    return found


# -------------------------------------------------------------------------- the write


def check_choices(diff, choices):
    """Return (conflict id -> choice, change id -> bool). A conflict with no choice is not
    in the first dict. Raise `WebsiteError`."""
    if not isinstance(choices, dict):
        raise WebsiteError("the choice file MUST hold an object")
    picked = choices.get("conflicts") or {}
    ticked = choices.get("changes") or {}
    ids = [entry["id"] for entry in diff["conflicts"] if entry["id"] in picked]
    bad = [key for key in ids if picked[key] not in CHOICES]
    if bad:
        raise WebsiteError("the conflicts %s need database or website" % _names(bad))
    bad = [key for key, value in ticked.items() if not isinstance(value, bool)]
    if bad:
        raise WebsiteError("the changes %s need true or false" % _names(bad))
    return ({key: picked[key] for key in ids},
            {entry["id"]: ticked.get(entry["id"], True) for entry in diff["changes"]})


def _notes(by_kind, texts, images, kept):
    """Return the comments of one write: (slug, text)."""
    notes = [(e["slug"], COMMENT_NEW) for e in by_kind["new"]]
    notes += [(e["slug"], COMMENT_BACK) for e in by_kind["back"]]
    notes += [(e["slug"], COMMENT_MISSING) for e in by_kind["missing"]]
    notes += [(e["slug"], COMMENT_MAIN) for e in by_kind["main"]]
    notes += [(e["slug"], "%s from vino-svoe.ru; was %s." % (e["field"], _short(e["database"])))
              for e in texts]
    notes += [(e["slug"], "main image from vino-svoe.ru; was %s." % e["database"]["source_name"])
              for e in images]
    notes += [(e["slug"], "kept %s; vino-svoe.ru has %s." % (e["field"], _short(e["website"])))
              for e in kept if e["kind"] == "text"]
    notes += [(e["slug"], "kept main image; vino-svoe.ru has %s." % e["website"]["name"])
              for e in kept if e["kind"] == "image"]
    return notes


def write(db_path, diff, blobs, choices=None, segmenter=None, log=print):
    """Write the diff with the choices of a person. None: each plain change, and the diff
    MUST hold no conflict. Return a `Report`. Raise `WebsiteError`."""
    if diff["problems"]:
        raise WebsiteError("the compare found %d problems" % len(diff["problems"]))
    if choices is None and diff["conflicts"]:
        raise WebsiteError("the diff holds conflicts and no choices")
    picked, ticked = check_choices(diff, choices or {})
    by_kind = {kind: [entry for entry in diff["changes"]
                      if entry["kind"] == kind and ticked[entry["id"]]] for kind in CHANGE_KINDS}
    skipped = [entry["id"] for entry in diff["changes"] if not ticked[entry["id"]]]
    texts = [entry for entry in diff["conflicts"]
             if entry["kind"] == "text" and picked.get(entry["id"]) == "website"]
    images = [entry for entry in diff["conflicts"]
              if entry["kind"] == "image" and picked.get(entry["id"]) == "website"]
    kept = [entry for entry in diff["conflicts"] if picked.get(entry["id"]) == "database"]
    unresolved = [entry["id"] for entry in diff["conflicts"] if entry["id"] not in picked]
    for entry in texts:
        if entry["field"] not in COMPARED:
            raise WebsiteError("%s: the field %r is not compared" % (entry["id"], entry["field"]))
    # The new main rows: (slug, website image).
    mains = ([(entry["slug"], entry["image"]) for entry in by_kind["new"] + by_kind["main"]]
             + [(entry["slug"], entry["website"]) for entry in images])
    refusals = ([(e["slug"], "text", e["field"], e["website"]) for e in kept
                 if e["kind"] == "text"]
                + [(e["slug"], "image", "", e["website"]["sha256"]) for e in kept
                   if e["kind"] == "image"])
    notes = _notes(by_kind, texts, images, kept)

    report = Report()
    conn = labdb.connect(db_path)
    conn.isolation_level = None
    try:
        if State(conn).digest() != diff["snapshot"]:
            raise WebsiteError(CHANGED)
        files = {}
        for _, image in mains:
            digest = image["sha256"]
            if digest in files:
                continue
            data = blobs.get(digest)
            if data is None or hashlib.sha256(data).hexdigest() != digest:
                raise WebsiteError("the website image %s is missing or damaged" % image["name"])
            row = stored_file(conn, digest)
            folder, extension = row or (labdb.IMAGE_FOLDERS[IMAGE_TYPE], image["extension"])
            files[digest] = (data, folder, extension) + pixel_size(data)
        originals = {}
        for digest, (data, folder, extension, _, _) in files.items():
            path = store_path(db_path, folder, digest, extension)
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                if imagestore.store_bytes(data, path, digest):
                    report.written += 1
            except (imagestore.StoreError, OSError) as exc:
                raise WebsiteError("cannot store an image: %s" % exc)
            originals[digest] = path
        client = segmenter or derive.Sam3Client()
        report.derivatives = derive.derive_all(conn, db_path, originals, client, log)
        labels = []
        for digest, path in originals.items():
            if labels and labels[-1].unavailable:
                report.no_label_cut += 1
                continue
            label_notes = []
            label = alternatives.full_label_cut(conn, db_path, digest, path, client,
                                                label_notes)
            labels.append(label)
            if label.links:
                report.label_cuts += 1
            elif not (label.present or label.not_applicable):
                report.no_label_cut += 1
                log("no label cut: %s: %s" % (path, "; ".join(label_notes)))

        conn.execute("BEGIN IMMEDIATE")
        try:
            if State(conn).digest() != diff["snapshot"]:
                raise WebsiteError(CHANGED)
            conn.executemany(
                "INSERT INTO wine_catalog (%s, state) VALUES (%s, 'Active')"
                % (", ".join(FIELDS), ", ".join("?" for _ in FIELDS)),
                [entry["row"] for entry in by_kind["new"]])
            conn.executemany("UPDATE wine_catalog SET state = 'Active', removed_by = NULL "
                             "WHERE wine_slug = ?", [(e["slug"],) for e in by_kind["back"]])
            conn.executemany("UPDATE wine_catalog SET state = 'Removed', "
                             "removed_by = 'import' WHERE wine_slug = ?",
                             [(e["slug"],) for e in by_kind["missing"]])
            for entry in texts:
                conn.execute("UPDATE wine_catalog SET %s = ? WHERE wine_slug = ?"
                             % entry["field"], (entry["website"], entry["slug"]))
            for digest, (_, folder, extension, width, height) in files.items():
                insert_image(conn, digest, folder, extension, width, height)
            conn.executemany("DELETE FROM wine_image WHERE wine_slug = ? AND image_type = ?",
                             [(entry["slug"], IMAGE_TYPE) for entry in images])
            conn.executemany(
                "INSERT INTO wine_image (wine_slug, image_type, sha256, source_name, "
                "match_method) VALUES (?, ?, ?, ?, ?)",
                [(slug, IMAGE_TYPE, image["sha256"], image["name"], MATCH_METHOD)
                 for slug, image in mains])
            derive.write_rows(conn, report.derivatives)
            for label in labels:
                alternatives.write_processed_rows(conn, label)
            conn.executemany("DELETE FROM website_refusal WHERE wine_slug = ? AND kind = ? "
                             "AND field = ?", [tuple(key) for key in diff["stale"]])
            stamp = now_utc()
            conn.executemany(
                "INSERT INTO website_refusal (wine_slug, kind, field, website_value, "
                "created_at) VALUES (?, ?, ?, ?, ?) ON CONFLICT (wine_slug, kind, field) "
                "DO UPDATE SET website_value = excluded.website_value, "
                "created_at = excluded.created_at", [row + (stamp,) for row in refusals])
            for slug, text in notes:
                comments.add(conn, slug, text, "script")
            for slug, lastmod in diff["times"].items():
                cursor = conn.execute(
                    "UPDATE wine_catalog SET website_modified_at = ? WHERE wine_slug = ? "
                    "AND website_modified_at IS NOT ?", (lastmod, slug, lastmod))
                report.times += cursor.rowcount
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        states = dict(conn.execute("SELECT state, count(*) FROM wine_catalog GROUP BY state"))
    finally:
        conn.close()
    report.website, report.images = diff["website"], diff["images"]
    report.requests, report.bytes = diff["requests"], diff["bytes"]
    report.added = [e["slug"] for e in by_kind["new"]]
    report.restored = [e["slug"] for e in by_kind["back"]]
    report.removed = [e["slug"] for e in by_kind["missing"]]
    report.mains = [e["slug"] for e in by_kind["main"]]
    report.texts = ["%s %s" % (e["slug"], e["field"]) for e in texts]
    report.replaced = [e["slug"] for e in images]
    report.refusals = ["%s %s" % (row[0], row[1]) for row in refusals]
    report.unresolved = unresolved
    report.skipped = skipped
    report.refused, report.stale = diff["refused"], len(diff["stale"])
    touched = {e["slug"] for e in diff["changes"] if e["kind"] in ("back", "main")}
    touched |= {e["slug"] for e in diff["conflicts"] if e["id"] in picked}
    report.unchanged = diff["unchanged"] - len(touched)
    report.comments = len(notes)
    report.states = {name: states.get(name, 0) for name in STATES}
    return report


# ---------------------------------------------------------------------------- the modes


def _compare(db_path, client, log):
    if not COMPARE_ENABLED:
        raise WebsiteError(COMPARE_DISABLED)
    client = client or Client()
    conn = labdb.connect(db_path)
    try:
        return compare(conn, client, log)
    finally:
        conn.close()
        if hasattr(client, "close"):
            client.close()


def import_website(db_path, client=None, segmenter=None, log=print):
    """The CLI mode: stop on a problem or a conflict, or apply each plain change.
    Return a `Report`, or raise `WebsiteError` with all problems and conflicts."""
    diff, blobs = _compare(db_path, client, log)
    stops = diff["problems"] + [conflict_line(entry) for entry in diff["conflicts"]]
    if stops:
        raise WebsiteError("the import stops, and nothing changed. %d problems:\n  %s"
                           % (len(stops), "\n  ".join(stops)))
    return write(db_path, diff, blobs, None, segmenter, log)


def write_json(path, value):
    """Write a JSON file in one step: a reader sees the old file or the new one."""
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8") as fh:
        json.dump(value, fh, ensure_ascii=False, indent=1)
    os.replace(temp, path)


def prepare(db_path, directory, client=None, log=print):
    """The UI mode, step 1: write `diff.json` and the images to `directory`. Return the
    diff. Raise `WebsiteError` when the compare found a problem."""
    diff, blobs = _compare(db_path, client, log)
    if diff["problems"]:
        raise WebsiteError("the compare stops. %d problems:\n  %s"
                           % (len(diff["problems"]), "\n  ".join(diff["problems"])))
    os.makedirs(os.path.join(directory, IMAGES_DIR), exist_ok=True)
    files = {entry["image"]["sha256"]: entry["image"]["file"]
             for entry in diff["changes"] if entry.get("image")}
    files.update({entry["website"]["sha256"]: entry["website"]["file"]
                  for entry in diff["conflicts"] if entry["kind"] == "image"})
    for digest, name in files.items():
        imagestore.store_bytes(blobs[digest], os.path.join(directory, name), digest)
    diff["database"] = os.path.abspath(db_path)
    write_json(os.path.join(directory, DIFF_FILE), diff)
    return diff


def apply_directory(db_path, directory, segmenter=None, log=print):
    """The UI mode, step 2: write the diff of `directory` with its choices. Return a
    `Report`. Raise `WebsiteError`."""
    try:
        with open(os.path.join(directory, DIFF_FILE), encoding="utf-8") as fh:
            diff = json.load(fh)
        with open(os.path.join(directory, CHOICES_FILE), encoding="utf-8") as fh:
            choices = json.load(fh)
    except (OSError, ValueError) as exc:
        raise WebsiteError("cannot read the run directory %s: %s" % (directory, exc))
    if diff.get("database") != os.path.abspath(db_path):
        raise WebsiteError("the diff belongs to the database %s" % diff.get("database"))
    blobs = {}
    for entry in diff["changes"] + diff["conflicts"]:
        image = entry.get("image") or (entry["website"] if entry["kind"] == "image" else None)
        if image:
            try:
                with open(os.path.join(directory, image["file"]), "rb") as fh:
                    blobs[image["sha256"]] = fh.read()
            except OSError:
                pass
    return write(db_path, diff, blobs, choices, segmenter, log)


def _line(label, slugs):
    return "%s: %d%s" % (label, len(slugs), ": " + _names(slugs) if slugs else "")


def print_report(report, db_path):
    print("source: %s" % API)
    print("wines on the website: %d" % report.website)
    print("images downloaded: %d" % report.images)
    print("requests: %d, %.1f MB" % (report.requests, report.bytes / 1e6))
    print(_line("added", report.added))
    print(_line("restored", report.restored))
    print(_line("removed", report.removed))
    print(_line("main images stored", report.mains))
    print(_line("text from the website", report.texts))
    print(_line("main images replaced", report.replaced))
    print(_line("refusals written", report.refusals))
    print(_line("conflicts with no choice, not written", report.unresolved))
    print(_line("cleared changes, not written", report.skipped))
    print("skipped by a refusal: %d" % report.refused)
    print("refusals deleted: %d" % report.stale)
    print("website times written: %d" % report.times)
    print("unchanged: %d" % report.unchanged)
    print("image files written: %d" % report.written)
    print_derivatives(report.derivatives)
    print("label cuts written: %d" % report.label_cuts)
    print("no label cut: %d" % report.no_label_cut)
    print("comments added: %d" % report.comments)
    print("database: %s" % db_path)
    print("states: %s" % ", ".join("%s %d" % item for item in report.states.items()))
    print("result: %s" % ("no change" if report.empty() else "imported"))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Import the catalogue of vino-svoe.ru into wine_catalog. The CLI stops "
                    "on a changed text or a changed main image. --prepare and --apply are "
                    "the two steps of the merge dialog of the lab server.")
    parser.add_argument("--db", required=True, help="path of the lab database")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--prepare", metavar="DIR",
                      help="compare, and write the diff and the images to DIR")
    mode.add_argument("--apply", metavar="DIR",
                      help="write the diff of DIR with the choices of DIR/choices.json")
    args = parser.parse_args(argv)

    def log(message):
        print(message, flush=True)

    errors = (WebsiteError, labdb.SchemaError, sqlite3.Error, OSError, comments.CommentError)
    if args.prepare:
        try:
            diff = prepare(args.db, args.prepare, log=log)
        except errors as exc:
            print("error: %s" % exc, file=sys.stderr)
            return 1
        print("prepared: %d conflicts, %d changes, %d skipped by a refusal: %s"
              % (len(diff["conflicts"]), len(diff["changes"]), diff["refused"],
                 os.path.join(args.prepare, DIFF_FILE)))
        return 0
    if args.apply:
        try:
            report = apply_directory(args.db, args.apply, log=log)
        except errors as exc:
            print("error: %s" % exc, file=sys.stderr)
            write_json(os.path.join(args.apply, RESULT_FILE), {"ok": False, "error": str(exc)})
            return 1
        write_json(os.path.join(args.apply, RESULT_FILE), dict(report.as_dict(), ok=True))
        print_report(report, args.db)
        return 0
    try:
        report = import_website(args.db, log=log)
    except errors as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    print_report(report, args.db)
    return 0


if __name__ == "__main__":
    sys.exit(main())
