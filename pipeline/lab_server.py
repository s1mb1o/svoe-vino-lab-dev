"""The lab server: the Dataset page on the lab database.

The server reads two keys of `config.yaml`: `rootdir` and `database_file`. It opens
the database for each request and checks the schema version. It serves the Dataset
page and `GET /api/dataset` from the table `wine_catalog`. A GET opens the database
read-only. `POST /api/wine-state` changes the state of one wine; it writes the
columns `state` and `removed_by` alone.

The pages Clusters, Embeddings, Testset, and Runs are disabled for now. Each one
answers a notice page with HTTP 503, and each other API route answers HTTP 503 with
a JSON error, except `POST /api/wine-state`. The database does not hold their data
yet. The navigation of every page stays as it is. Read `docs/plans/07_sqlite-lab-database.md`.

Usage:
    python3 pipeline/lab_server.py              # http://127.0.0.1:8168/dataset
    python3 pipeline/lab_server.py --no-browser
"""
import argparse
import json
import os
import sqlite3
import sys
import threading
import urllib.parse
import webbrowser
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lab_pages  # noqa: E402
import labdb  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT, "config.yaml")
# Port 8168 is recorded in `/Users/ashmelev/Admin/mbp2023/PORTS_USED.md`. It is apart
# from 8154 of `svoe-vino-testset/scripts/review_server.py`, so both can run.
DEFAULT_PORT = 8168

# The columns of `wine_catalog` that `/api/dataset` sends, in table order.
CATALOG_COLUMNS = ("wine_slug", "name", "producer", "category", "color", "region",
                   "grapes", "description", "csv_photo_name", "state", "removed_by")
# The states of a wine, in the order of the start report.
STATES = ("Active", "Disabled", "Removed")
# The Dataset page reads the key `slug`. The API sends `wine_slug` under that key.
PAGE_KEYS = {"wine_slug": "slug"}

# The pages of the navigation, in the order of the navigation.
NAV = (("/dataset", "Dataset"), ("/clusters", "Clusters"),
       ("/embedding", "Embeddings"), ("/", "Testset"), ("/runs", "Runs"))
# The disabled pages. `/docs` is the API page of the review tool.
DISABLED_PAGES = {"/clusters": "Clusters", "/embedding": "Embeddings", "/": "Testset",
                  "/runs": "Runs", "/docs": "API docs"}
DISABLED_ERROR = ("disabled for now: the lab database does not hold the data of "
                  "this route yet")
# action -> (the states that allow it, the new state). A removal by a person sets
# `removed_by` = `person`, so the import does not restore the wine.
ACTIONS = {
    "disable": (("Active",), "Disabled"),
    "enable": (("Disabled",), "Active"),
    "remove": (("Active", "Disabled"), "Removed"),
    "restore": (("Removed",), "Active"),
}
# The largest body of `POST /api/wine-state`, in bytes.
MAX_BODY = 4096


class ConfigError(Exception):
    """The configuration or the database does not allow the server to start."""


def load_config(path=CONFIG_PATH):
    """Return the absolute path of the database that `config.yaml` names."""
    try:
        with open(path, encoding="utf-8") as fh:
            config = yaml.safe_load(fh) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError("cannot read %s: %s" % (path, exc))
    database = config.get("database_file")
    if not database:
        raise ConfigError("%s holds no key `database_file`" % path)
    rootdir = config.get("rootdir") or os.path.dirname(ROOT)
    return os.path.abspath(os.path.join(rootdir, database))


def open_database(path, write=False):
    """Open the database, read-only unless `write`. Check the schema version.

    Raise `ConfigError` on a missing file or on a wrong schema version.
    """
    if not os.path.isfile(path):
        raise ConfigError("no database at %s; create it with "
                          "`python3 pipeline/labdb.py %s`" % (path, path))
    conn = sqlite3.connect(Path(path).as_uri() + ("?mode=rw" if write else "?mode=ro"),
                           uri=True)
    try:
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        expected = len(labdb.schema_files())
    except Exception:
        conn.close()
        raise
    if version != expected:
        conn.close()
        if version < expected:
            raise ConfigError("the database has schema version %d and this code needs "
                              "version %d; run `python3 pipeline/labdb.py %s`"
                              % (version, expected, path))
        raise ConfigError("the database has schema version %d; this code knows "
                          "version %d" % (version, expected))
    return conn


def state_counts(conn):
    """Return the number of wines of each state, in the order of `STATES`."""
    counts = dict(conn.execute("SELECT state, count(*) FROM wine_catalog GROUP BY state"))
    return {state: counts.get(state, 0) for state in STATES}


def dataset_records(conn):
    """Return every wine in import order, in the record shape of the Dataset page.

    The records hold each state. The key `state` tells a removed wine apart.
    """
    records = []
    for row in conn.execute("SELECT %s FROM wine_catalog ORDER BY rowid"
                            % ", ".join(CATALOG_COLUMNS)):
        record = {PAGE_KEYS.get(column, column): value
                  for column, value in zip(CATALOG_COLUMNS, row)}
        # The page shows these editors. Their data is not in the database yet.
        record.update({"_patched": False, "_alternatives": [], "_barcodes": [],
                       "_qr_urls": [], "_atlas_product_uuid": None,
                       "_atlas_binding_source": None})
        records.append(record)
    return records


def dataset_view(db_path):
    """Return the answer of `GET /api/dataset`."""
    with closing(open_database(db_path)) as conn:
        records = dataset_records(conn)
    return {
        "database_file": db_path,
        "patch_dir": "", "patches": 0,
        "alternative_dir": "", "alternatives": 0,
        "barcode_file": "", "barcodes": 0, "qr_urls": 0,
        "atlas_matches_file": "", "atlas_bindings_file": "",
        "atlas_bindings": 0, "atlas_manual_bindings": 0,
        "records": records,
    }


class StateError(Exception):
    """A state change is not allowed. `code` is the HTTP status of the answer."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def change_state(db_path, slug, action):
    """Apply one action to one wine. Return the new state and `removed_by`."""
    if action not in ACTIONS:
        raise StateError(400, "unknown action %r; use one of: %s"
                         % (action, ", ".join(ACTIONS)))
    if not isinstance(slug, str) or not slug:
        raise StateError(400, "the request holds no wine slug")
    allowed, target = ACTIONS[action]
    with closing(open_database(db_path, write=True)) as conn:
        conn.isolation_level = None
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute("SELECT state FROM wine_catalog WHERE wine_slug = ?",
                               (slug,)).fetchone()
            if row is None:
                raise StateError(404, "no wine with the slug %s" % slug)
            if row[0] not in allowed:
                raise StateError(409, "the wine %s is %s; %s needs %s"
                                 % (slug, row[0], action, " or ".join(allowed)))
            removed_by = "person" if target == "Removed" else None
            conn.execute("UPDATE wine_catalog SET state = ?, removed_by = ? "
                         "WHERE wine_slug = ?", (target, removed_by, slug))
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
    return {"slug": slug, "state": target, "removed_by": removed_by}


def disabled_page(route):
    """Return the notice page of a disabled route."""
    name = DISABLED_PAGES[route]
    nav = "".join('<a%s href="%s">%s</a>' % (' class="on"' if href == route else "",
                                              href, label) for href, label in NAV)
    return (lab_pages.page("disabled.html")
            .replace("__PAGE__", name).replace("__NAV__", nav))


class Handler(BaseHTTPRequestHandler):
    server_version = "svoe-vino-lab/1"

    def log_message(self, fmt, *args):
        if self.path.startswith("/api/"):
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, code, body, ctype):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def _json(self, code, value):
        self._send(code, json.dumps(value, ensure_ascii=False),
                   "application/json; charset=utf-8")

    def do_GET(self):
        route = urllib.parse.urlsplit(self.path).path
        if route == "/dataset":
            self._send(200, lab_pages.page("dataset.html"), "text/html; charset=utf-8")
        elif route == "/api/dataset":
            try:
                self._json(200, dataset_view(self.server.db_path))
            except (ConfigError, sqlite3.Error) as exc:
                self._json(503, {"error": str(exc)})
        elif route in DISABLED_PAGES:
            self._send(503, disabled_page(route), "text/html; charset=utf-8")
        elif route.startswith("/api/") or route.startswith("/openapi."):
            self._json(503, {"error": DISABLED_ERROR})
        elif route.startswith("/img/"):
            self._send(503, DISABLED_ERROR, "text/plain; charset=utf-8")
        else:
            self._send(404, "not found", "text/plain; charset=utf-8")

    do_HEAD = do_GET

    def _wine_state(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        if length <= 0 or length > MAX_BODY:
            self._json(400, {"error": "the body MUST be JSON of at most %d bytes" % MAX_BODY})
            return
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            self._json(400, {"error": "the body is not JSON"})
            return
        if not isinstance(body, dict):
            self._json(400, {"error": "the body MUST be a JSON object"})
            return
        try:
            self._json(200, change_state(self.server.db_path, body.get("slug"),
                                         body.get("action")))
        except StateError as exc:
            self._json(exc.code, {"error": str(exc)})
        except (ConfigError, sqlite3.Error) as exc:
            self._json(503, {"error": str(exc)})

    def _write_route(self):
        route = urllib.parse.urlsplit(self.path).path
        if route == "/api/wine-state" and self.command == "POST":
            self._wine_state()
        elif route.startswith("/api/"):
            self._json(503, {"error": DISABLED_ERROR})
        else:
            self._send(404, "not found", "text/plain; charset=utf-8")

    do_POST = do_PUT = do_DELETE = _write_route


def make_server(db_path, host="127.0.0.1", port=DEFAULT_PORT):
    """Return the HTTP server. The caller runs `serve_forever`."""
    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    server.db_path = db_path
    return server


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="The lab server: the Dataset page on the lab database.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--config", default=CONFIG_PATH, help="path of config.yaml")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args(argv)
    # A log file gets each line of the start report at once, not at exit.
    sys.stdout.reconfigure(line_buffering=True)

    try:
        db_path = load_config(args.config)
        with closing(open_database(db_path)) as conn:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            states = state_counts(conn)
    except (ConfigError, sqlite3.Error) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1

    print("config: %s" % os.path.abspath(args.config))
    print("database_file: %s" % db_path)
    print("schema version: %d" % version)
    print("wines: %d (%s)" % (sum(states.values()),
                              ", ".join("%s %d" % item for item in states.items())))
    if not sum(states.values()):
        print("  the catalogue is empty; import it with `python3 pipeline/import_catalog.py`")
    print("disabled pages: %s" % ", ".join(DISABLED_PAGES.values()))

    try:
        server = make_server(db_path, args.host, args.port)
    except OSError as exc:
        print("error: cannot listen on %s:%d: %s" % (args.host, args.port, exc),
              file=sys.stderr)
        return 1
    url = "http://%s:%d/dataset" % (args.host, args.port)
    print("lab server: %s   (Ctrl+C to stop)" % url)
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
