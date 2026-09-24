"""The lab server: the Dataset page on the lab database.

The server reads two keys of `config.yaml`: `rootdir` and `database_file`. It opens
the database read-only for each request and checks the schema version. It serves
the Dataset page and `GET /api/dataset` from the table `wine_catalog`.

The pages Clusters, Embeddings, Testset, and Runs are disabled for now. Each one
answers a notice page with HTTP 503, and each other API route answers HTTP 503 with
a JSON error. The database does not hold their data yet. The navigation of every
page stays as it is. Read `docs/plans/07_sqlite-lab-database.md`.

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
                   "grapes", "description", "csv_photo_name")
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


def open_database(path):
    """Open the database read-only. Raise `ConfigError` on a wrong schema version."""
    if not os.path.isfile(path):
        raise ConfigError("no database at %s; create it with "
                          "`python3 pipeline/labdb.py %s`" % (path, path))
    conn = sqlite3.connect(Path(path).as_uri() + "?mode=ro", uri=True)
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


def catalog_source(conn):
    """Return the row of `catalog_source` as a map, or None."""
    row = conn.execute("SELECT source_path, source_sha256, source_rows, imported_at "
                       "FROM catalog_source").fetchone()
    if row is None:
        return None
    return dict(zip(("source_path", "source_sha256", "source_rows", "imported_at"), row))


def dataset_records(conn):
    """Return the wines in seed order, in the record shape of the Dataset page."""
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
        # The page shows this value under the label `catalog.jsonl`.
        "catalog_file": "%s, table wine_catalog" % db_path,
        "database_file": db_path,
        "patch_dir": "", "patches": 0,
        "alternative_dir": "", "alternatives": 0,
        "barcode_file": "", "barcodes": 0, "qr_urls": 0,
        "atlas_matches_file": "", "atlas_bindings_file": "",
        "atlas_bindings": 0, "atlas_manual_bindings": 0,
        "records": records,
    }


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

    def _write_route(self):
        route = urllib.parse.urlsplit(self.path).path
        if route.startswith("/api/"):
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
            source = catalog_source(conn)
            wines = conn.execute("SELECT count(*) FROM wine_catalog").fetchone()[0]
    except (ConfigError, sqlite3.Error) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1

    print("config: %s" % os.path.abspath(args.config))
    print("database_file: %s" % db_path)
    print("schema version: %d" % version)
    if source:
        print("catalogue source: %s" % source["source_path"])
        print("  sha256 %s, %d rows, seeded %s"
              % (source["source_sha256"], source["source_rows"], source["imported_at"]))
    else:
        print("catalogue source: none; seed it with `python3 pipeline/seed_catalog.py`")
    print("wines: %d" % wines)
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
