"""The routes of the Runs page of the lab server.

The page reads the run directories of `runs/` with `run_files.py`. The runs stay files;
the lab database does not hold them. The read routes are GET and do not change a run
file:

    GET /runs                                   the page
    GET /runs/charts                            pipeline comparisons and run history
    GET /api/runs                               the head of each run, and the
                                                pipelines of `config.yaml`
    GET /api/run?id=&filter=&sort=&q=&offset=&limit=
                                                the metrics and the rows of one run
    GET /api/run-predictions?id=                all saved predictions as JSONL
    GET /api/run-expected?id=                   all expected answers as JSONL
    GET /api/run-clusters?id=                   the clusters of the embedding of one run
                                                and their card names (plan 43)
    GET /api/run-inputs?id=&query=              the model inputs of one row
    GET /api/run-candidate?id=&query=&slug=     the catalogue inputs of one candidate of
                                                an embedding run and their cosines
    GET /api/run-steps?id=&query=               the steps of one row for the step popup
                                                (plan 41, `run_steps.py`)
    GET /api/run-preview?id=&query=&view=&rank=&token= one recorded candidate preview
    POST /api/run-image-tag                     add a shared image tag to one recorded
                                                query image
    POST /api/run-image-tag-remove              remove a shared image tag from one
                                                recorded query image
    GET /api/wine-merge?slug=                   preview a manual wine merge
    POST /api/wine-merge                        transfer and delete a manual wine

A pipeline is one entry of the key `pipeline` of `config.yaml` (`pipelines.py`, plan
34). The key `configuration` of `run.json` names it. The images come from the image
store of the lab database, through the route `/images/<folder>/<sha256>.<ext>`: the photo
of a row by its `image_sha256`, and the catalogue image of a slug by the rule of
`card_images` of `lab_server.py`. Read `docs/plans/23_runs-page.md`.
"""
import json
import copy
import os
import re
import sqlite3
import sys
import urllib.parse
from contextlib import closing
from functools import lru_cache
from pathlib import Path

import embeddings
import image_tags
import lab_pages
import labdb
import pipelines
import run_files
import run_compare
import run_page_cache
import testsets
import wine_merge
from checked_read_cache import CheckedReadCache
from settings_cache import SETTINGS_CACHE

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS_DIR = os.path.join(ROOT, "runs")
MATCHER_ROOT = os.path.join(os.path.dirname(os.path.dirname(ROOT)), "svoe-vino-matcher")
ROUTES = ("/runs", "/runs/charts", "/runs/compare", "/api/run-compare", "/api/runs", "/api/run", "/api/run-clusters", "/api/run-inputs",
          "/api/run-candidate", "/api/run-steps", "/api/run-preview", "/api/run-artifact", "/api/run-vlm-image", "/api/run-predictions",
          "/api/run-expected", "/api/run-image-tag", "/api/run-image-tag-remove", "/api/drawer-runs",
          "/api/drawer-match-accept", "/api/wine-merge")
JSON_TYPE = "application/json; charset=utf-8"
MAX_LIMIT = 1000
TAG_BODY_MAX = 4096
# The keys of a cluster rule that the VLM box of the page reads.
RULE_KEYS = ("mode", "questions")
# The view of `clusters.json` that the page shows, as on the Testset page (plan 37), and
# the rule space of `cluster-rules.json`: the matcher sends a label crop (plan 30).
CLUSTER_SPACE = "combined"
RULE_SPACE = "label"
CLUSTER_HINT_INPUTS = CheckedReadCache(max_entries=8, max_bytes=32 * 1024 * 1024)


def handles(route):
    """Answer whether `route` belongs to the Runs page."""
    return route in ROUTES


def _json(code, value):
    return code, value, JSON_TYPE, "no-store"


def _error(code, message):
    return _json(code, {"error": message})


def respond(server, method, path, card_images, read_body=None, *, card_images_for_slugs=None):
    """Answer one request. Return (HTTP code, body, content type, Cache-Control).

    `card_images(conn)` is `lab_server.card_images`: slug -> the images of the card.
    """
    parts = urllib.parse.urlsplit(path)
    route = parts.path
    query = urllib.parse.parse_qs(parts.query)
    runs_dir = getattr(server, "runs_dir", None) or RUNS_DIR
    if route == "/api/wine-merge":
        try:
            if method == "GET":
                return _json(200, wine_merge.preview(server.db_path, _one(query, "slug")))
            if method != "POST":
                return _error(405, "the route %s answers GET and POST alone" % route)
            raw = read_body(TAG_BODY_MAX) if read_body else None
            try:
                body = json.loads(raw) if raw is not None else None
            except (UnicodeDecodeError, json.JSONDecodeError):
                body = None
            if not isinstance(body, dict):
                return _error(400, "the body MUST be a JSON object")
            slug = wine_merge.source_slug(body.get("slug"))
            jobs = getattr(server, "new_wine_jobs", None)
            job = jobs.get(slug) if jobs else None
            if job and job.get("state") == "indexing":
                return _error(409, "the source wine is still indexing; wait for it to finish")
            return _json(200, wine_merge.merge(server.db_path, body))
        except wine_merge.MergeError as exc:
            return _error(exc.code, str(exc))
        except (OSError, sqlite3.Error, labdb.SchemaError) as exc:
            return _error(503, "cannot merge the wine: %s" % exc)
    if route == "/api/drawer-match-accept":
        if method != "POST":
            return _error(405, "the route %s answers POST alone" % route)
        raw = read_body(TAG_BODY_MAX) if read_body else None
        if raw is None:
            return _error(400, "the body MUST be a JSON object")
        try:
            body = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return _error(400, "the body MUST be a JSON object")
        return accept_drawer_match(runs_dir, server.db_path, body)
    if route in ("/api/run-image-tag", "/api/run-image-tag-remove"):
        if method != "POST":
            return _error(405, "the route %s answers POST alone" % route)
        raw = read_body(TAG_BODY_MAX) if read_body else None
        if raw is None:
            return _error(400, "the body MUST be a JSON object")
        try:
            body = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return _error(400, "the body MUST be a JSON object")
        return write_run_image_tag(runs_dir, server.db_path, body,
                                   remove=route == "/api/run-image-tag-remove")
    if method not in ("GET", "HEAD"):
        return _error(405, "the route %s answers GET alone" % route)
    if route == "/runs":
        return 200, lab_pages.page("runs.html"), "text/html; charset=utf-8", "no-store"
    if route == "/runs/charts":
        return 200, lab_pages.page("run_charts.html"), "text/html; charset=utf-8", "no-store"
    if route == "/runs/compare":
        return 200, lab_pages.page("run_compare.html"), "text/html; charset=utf-8", "no-store"
    if route == "/api/run-compare":
        code, body = run_compare.respond(runs_dir, server.db_path, query)
        return _json(code, body)
    if route == "/api/runs":
        return _json(200, runs_view(runs_dir, server.config_path or embeddings.CONFIG_PATH))
    if route == "/api/drawer-runs":
        return drawer_runs_view(runs_dir, query)
    if route == "/api/run":
        return run_view(runs_dir, server.db_path, query, card_images)
    if route == "/api/run-predictions":
        return predictions_view(runs_dir, query)
    if route == "/api/run-expected":
        return expected_view(runs_dir, query)
    if route == "/api/run-clusters":
        return clusters_view(runs_dir, server, query)
    if route == "/api/run-candidate":
        return candidate_view(runs_dir, server.db_path, query)
    if route == "/api/run-steps":
        return steps_view(runs_dir, server.db_path, query, card_images,
                          card_images_for_slugs=card_images_for_slugs)
    if route == "/api/run-artifact":
        return artifact_view(runs_dir, server.db_path, query)
    if route == "/api/run-vlm-image":
        return vlm_image_view(runs_dir, server.db_path, query)
    if route == "/api/run-preview":
        return preview_view(runs_dir, server.db_path, query)
    return inputs_view(runs_dir, server.db_path, query)


def drawer_runs_view(runs_dir, query):
    """Return the completed Drawer-scoped runs of one test set, newest first."""
    set_name = _one(query, "set")
    if not set_name:
        return _error(400, "name the set: ?set=<set>")
    runs = []
    for run_id in run_files.run_dirs(runs_dir):
        meta = run_files.read_json(run_files.run_path(runs_dir, run_id, "run.json")) or {}
        if meta.get("query_scope") != "drawer" or run_files.test_set_of(meta) != set_name:
            continue
        runs.append(run_files.run_head(runs_dir, run_id))
    return _json(200, {"set": set_name, "runs": runs})


def accept_drawer_match(runs_dir, db_path, body):
    """Apply one recorded top-K Drawer suggestion as a positive test-set photo.

    The run supplies the source file and digest.  The destination must be one of that
    immutable result's candidates and a current catalogue row.  The database move and
    positive label are committed together.
    """
    if not isinstance(body, dict):
        return _error(400, "the body MUST be a JSON object")
    run_id, query_id = body.get("id"), body.get("query")
    set_name, target = body.get("set"), body.get("to")
    if not isinstance(run_id, str) or run_id not in run_files.run_dirs(runs_dir):
        return _error(404, "unknown run")
    if not isinstance(query_id, str) or not query_id:
        return _error(400, "the request holds no query")
    if not isinstance(set_name, str) or not set_name:
        return _error(400, "the request holds no set")
    if not isinstance(target, str) or not target:
        return _error(400, "the request holds no catalogue wine")
    meta = run_files.read_json(run_files.run_path(runs_dir, run_id, "run.json")) or {}
    if meta.get("query_scope") != "drawer":
        return _error(409, "this is not a Drawer matching run")
    if run_files.test_set_of(meta) != set_name:
        return _error(409, "the run belongs to another test set")
    record = run_files.run_result(runs_dir, run_id, query_id)
    if record is None:
        return _error(404, "unknown query")
    if not any(isinstance(candidate, dict) and candidate.get("slug") == target
               for candidate in record.get("candidates") or ()):
        return _error(400, "the wine is not a candidate of this result")
    image_path = record.get("image_path")
    prefix = testsets.DRAWER_SLUG + "/"
    file_name = image_path[len(prefix):] if isinstance(image_path, str) and image_path.startswith(prefix) else ""
    if not file_name or "/" in file_name or "\\" in file_name:
        return _error(409, "the result does not name a Drawer photo")
    digest = record.get("image_sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        return _error(409, "the result holds no image SHA-256")
    try:
        with closing(labdb.connect(db_path)) as conn:
            conn.isolation_level = None
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("BEGIN IMMEDIATE")
            try:
                if conn.execute("SELECT 1 FROM wine_catalog WHERE wine_slug = ?",
                                (target,)).fetchone() is None:
                    raise testsets.TestsetError(404, "no catalogue wine with the slug %s" % target)
                answer = testsets.accept_drawer_match(conn, set_name, file_name, target,
                                                       digest)
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
    except testsets.TestsetError as exc:
        return _error(exc.code, str(exc))
    except (OSError, sqlite3.Error, labdb.SchemaError) as exc:
        return _error(503, "cannot apply the Drawer match: %s" % exc)
    answer.update({"run": run_id, "query": query_id})
    return _json(200, answer)


def _one(query, key, default=""):
    return (query.get(key) or [default])[0]


def _export_view(runs_dir, query, source_name, make_row):
    """Export `source_name` as prediction-format JSONL in a stable order."""
    run_id = _one(query, "id")
    path = run_files.run_path(runs_dir, run_id, source_name)
    if not path:
        return _error(400, "bad run id")
    if run_id not in run_files.run_dirs(runs_dir):
        return _error(404, "unknown run")
    meta = run_files.read_json(run_files.run_path(runs_dir, run_id, "run.json")) or {}
    official = run_files.test_set_of(meta) == "official-test-2026-10-01"
    rows, photo_numbers = [], set()
    try:
        with open(path, encoding="utf-8") as source:
            for line in source:
                if not line.strip():
                    continue
                saved = json.loads(line)
                row = make_row(saved)
                if official:
                    # This set imports eval_photo_NNN.webp as <wine>/NNN.webp.
                    # Keep the source number, including gaps in a partial run.
                    match = re.fullmatch(r"(?:eval_photo_)?([0-9]{3})\.webp",
                                         os.path.basename(row["image_path"]))
                    if not match:
                        raise ValueError("a photo has no official photo number")
                    number = int(match[1])
                    if number < 1 or number in photo_numbers:
                        raise ValueError("official photo numbers MUST be positive and unique")
                    photo_numbers.add(number)
                    row["query_id"] = "q-%06d" % number
                    row["image_path"] = "eval_photo_%03d.webp" % number
                rows.append(row)
        rows.sort(key=lambda row: (row["query_id"], row["image_path"], row["image_sha256"]))
        body = "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
                       for row in rows)
    except FileNotFoundError:
        return _error(404, "this run has no %s" % source_name)
    except (ValueError, KeyError, TypeError) as exc:
        return _error(409, "cannot export %s: %s" % (source_name, exc))
    except OSError:
        return _error(503, "cannot read %s" % source_name)
    return 200, body, "application/x-ndjson; charset=utf-8", "no-store"


def predictions_view(runs_dir, query):
    """Export all saved predictions in a stable order. Do not change the run files."""
    fields = ("query_id", "image_path", "image_sha256", "predicted_slug", "latency_ms")
    return _export_view(runs_dir, query, "predictions.jsonl",
                        lambda saved: {key: saved[key] for key in fields})


def _expected_row(saved):
    """Return one prediction-format row from one saved query."""
    truth = saved["truth"]
    if not isinstance(truth, list) or len(truth) > 1:
        raise ValueError("truth MUST be a list with at most one slug")
    if truth and (not isinstance(truth[0], str) or not truth[0]):
        raise ValueError("the truth slug MUST be a non-empty string")
    return {"query_id": saved["query_id"], "image_path": saved["image_path"],
            "image_sha256": saved["image_sha256"],
            "predicted_slug": truth[0] if truth else None, "latency_ms": 0}


def expected_view(runs_dir, query):
    """Export the saved query truth as prediction-format JSONL with zero latency."""
    return _export_view(runs_dir, query, "queries.jsonl", _expected_row)


def _read_configurations(config_path):
    """Return (the pipelines of `config.yaml`, in file order, the error of the file or
    None). An entry that is not valid keeps its name and its error."""
    try:
        settings = pipelines.load(config_path)
    except embeddings.ConfigError as exc:
        return [], str(exc)
    return [{"name": name, "backend": pipeline.backend if pipeline else None,
             # The configured origin identifies an endpoint override. Device pipelines
             # do not opt in to endpoint overrides and therefore expose no value here.
             "endpoint": (pipelines.endpoint_origin(pipeline)
                          if pipeline and pipeline.endpoint_override else None),
             "error": error} for name, pipeline, error in settings.entries], None


@lru_cache(maxsize=8)
def _configuration_snapshot(path, revision):
    """Reuse checked pipeline summaries while the config file is unchanged."""
    return _read_configurations(path)


def configurations(config_path):
    """Return fresh pipeline summaries. Invalidate edits and atomic replacements."""
    path = os.path.abspath(config_path)
    try:
        stat = os.stat(path)
    except OSError:
        return _read_configurations(path)
    revision = (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
    return copy.deepcopy(_configuration_snapshot(path, revision))


def _url_origin(url):
    """Return a comparable `(scheme, host, port)` origin, or None."""
    if not isinstance(url, str) or not url:
        return None
    try:
        parts = urllib.parse.urlsplit(url)
        port = parts.port
    except ValueError:
        return None
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return None
    if port is None:
        port = 80 if parts.scheme == "http" else 443
    return parts.scheme, parts.hostname.lower(), port


def runs_view(runs_dir, config_path):
    """Return the head of each run, the newest first, and the pipelines."""
    entries, error = configurations(config_path)
    endpoints = {entry["name"]: entry["endpoint"] for entry in entries
                 if entry["endpoint"]}
    runs = []
    for run_id in run_files.run_dirs(runs_dir):
        head = run_files.run_head(runs_dir, run_id)
        actual = head.get("backend_url")
        configured = endpoints.get(head.get("configuration"))
        head["endpoint_override_url"] = (
            actual if actual and (head.get("endpoint_override")
                                  or (configured and _url_origin(actual)
                                      and _url_origin(actual) != _url_origin(configured)))
            else None)
        runs.append(head)
    return {"runs_dir": runs_dir,
            "runs": runs,
            "configurations": entries, "config_error": error}


def _connect(db_path):
    """Open the lab database read-only."""
    if not db_path or not os.path.isfile(db_path):
        raise sqlite3.OperationalError("no database at %s" % db_path)
    return sqlite3.connect(Path(os.path.abspath(db_path)).as_uri() + "?mode=ro", uri=True)


def _store_rows(conn, digests):
    """Return sha256 -> (folder, extension) of the `image` rows of `digests`."""
    out, digests = {}, sorted(digests)
    for start in range(0, len(digests), 500):
        chunk = digests[start:start + 500]
        out.update((digest, (folder, extension)) for digest, folder, extension in conn.execute(
            "SELECT sha256, folder, extension FROM image WHERE sha256 IN (%s)"
            % ", ".join("?" for _ in chunk), chunk))
    return out


def _row_slugs(row):
    """Return the slugs whose catalogue image one row shows."""
    slugs = {c.get("slug") for c in row.get("candidates") or ()}
    # The candidates of each bottle of a group answer (plan 83).
    for bottle in (row.get("group") or {}).get("bottles") or ():
        slugs.update(c.get("slug") for c in bottle.get("candidates") or ())
    slugs.update(row.get("truth") or ())
    slugs.update((row.get("twin") or {}).get("slugs") or ())
    slugs.discard(None)
    return slugs


def add_images(conn, rows, card_images):
    """Add `photo_url` and the shared image `tags` to each row.

    Return (slug -> catalogue image URL, the slugs with a patch). The photo URL takes
    the folder of the `image` row: most test photos are in `testset`, and a photo whose
    bytes were a lab image before keeps that folder.
    """
    digests = {r.get("image_sha256") for r in rows if r.get("image_sha256")}
    store = _store_rows(conn, digests)
    tagged = image_tags.tags(conn, digests)
    for row in rows:
        digest = row.get("image_sha256") or ""
        hit = store.get(digest)
        row["photo_url"] = ("/images/%s/%s.%s" % (hit[0], row["image_sha256"], hit[1])
                            if hit else None)
        row["tags"] = tagged.get(digest, [])
    wanted = set().union(*(_row_slugs(r) for r in rows)) if rows else set()
    cards = card_images(conn)
    bottles, patched = {}, []
    for slug in sorted(wanted):
        image = cards.get(slug)
        if not image:
            continue
        url = image.get("_patch_image_url") or image.get("main_image_url")
        if url:
            bottles[slug] = url
        if image.get("_patch_url"):
            patched.append(slug)
    return bottles, patched


def run_view(runs_dir, db_path, query, card_images):
    """Answer the metrics and the filtered rows of one run."""
    run_id = _one(query, "id")
    if not run_files.run_path(runs_dir, run_id, "run.json"):
        return _error(400, "bad run id")
    if run_id not in run_files.run_dirs(runs_dir):
        return _error(404, "unknown run")
    mode = _one(query, "filter", "all")
    try:
        limit = max(1, min(int(_one(query, "limit", "200")), MAX_LIMIT))
        offset = max(0, int(_one(query, "offset", "0")))
    except ValueError:
        return _error(400, "limit and offset MUST be numbers")
    sort = _one(query, "sort", "manifest")
    if sort not in run_files.ROW_SORTS:
        return _error(400, "sort MUST be one of %s" % ", ".join(run_files.ROW_SORTS))
    options = (mode, (_one(query, "q") or "").strip().lower(), limit, offset, sort)
    page_key = run_page_cache.token(runs_dir, run_id, db_path, card_images, options)
    page = run_page_cache.load(page_key)
    if (page is not None and page_key == run_page_cache.token(
            runs_dir, run_id, db_path, card_images, options)):
        return _json(200, page)
    rows, total = run_files.run_rows(runs_dir, run_id, mode, _one(query, "q"), limit,
                                     offset, sort)
    # The items of a candidate of an embedding run come through `/api/run-candidate`
    # (plan 38), and the step trace through `/api/run-steps` (plan 41), so a page of rows
    # stays small.
    for row in rows:
        row.pop("trace", None)
        for cand in row.get("candidates") or ():
            cand.pop("items", None)
    bottles, patched, tag_names, images_error = {}, [], [], None
    try:
        with closing(_connect(db_path)) as conn:
            bottles, patched = add_images(conn, rows, card_images)
            tag_names = image_tags.names(conn)
    except sqlite3.Error as exc:
        images_error = "cannot read the image store: %s" % exc
        for row in rows:
            row.setdefault("photo_url", None)
            row.setdefault("tags", [])
    page = {
        "run": run_files.read_json(run_files.run_path(runs_dir, run_id, "run.json")) or {},
        "metrics": run_files.read_json(
            run_files.run_path(runs_dir, run_id, "metrics.json")) or {},
        "head": run_files.run_head(runs_dir, run_id),
        "filter": mode, "sort": sort, "total": total, "offset": offset, "limit": limit,
        "rows": rows, "bottles": bottles, "patched": patched, "tag_names": tag_names,
        "images_error": images_error,
    }
    if page_key == run_page_cache.token(runs_dir, run_id, db_path, card_images, options):
        body = run_page_cache.store(page_key, page)
        if body is not None:
            return _json(200, body)
    return _json(200, page)


def write_run_image_tag(runs_dir, db_path, body, *, remove=False):
    """Add or remove one shared image tag and return the present tags of the query.

    The run and query resolve the digest server-side, so a caller cannot tag unrelated
    image bytes by inventing a SHA-256. The immutable run files are not changed.
    """
    if not isinstance(body, dict):
        return _error(400, "the body MUST be a JSON object")
    run_id, query_id, text = body.get("id"), body.get("query"), body.get("tag")
    if not isinstance(run_id, str) or run_id not in run_files.run_dirs(runs_dir):
        return _error(404, "unknown run")
    if not isinstance(query_id, str) or not query_id:
        return _error(400, "the request holds no query")
    record = run_files.run_result(runs_dir, run_id, query_id)
    if record is None:
        return _error(404, "unknown query")
    digest = record.get("image_sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        return _error(404, "the query holds no image SHA-256")
    try:
        with closing(labdb.connect(db_path)) as conn:
            if conn.execute("SELECT 1 FROM image WHERE sha256 = ?", (digest,)).fetchone() is None:
                return _error(404, "the query image is not in the lab image store")
            try:
                with conn:
                    if remove:
                        tag = image_tags.normal(text)
                        image_tags.remove(conn, digest, tag)
                        change = {"removed": tag}
                    else:
                        change = {"added": image_tags.add(conn, digest, text)}
            except image_tags.TagError as exc:
                return _error(400, str(exc))
            except image_tags.DuplicateError as exc:
                return _error(409, str(exc))
            return _json(200, {"ok": True, "run": run_id, "query": query_id,
                               "sha256": digest, **change,
                               "tags": image_tags.tags(conn, (digest,)).get(digest, []),
                               "tag_names": image_tags.names(conn)})
    except (OSError, sqlite3.Error, labdb.SchemaError) as exc:
        return _error(503, "cannot write the image tag: %s" % exc)


def run_embedding(runs_dir, run_id):
    """Return the name of the lab embedding of one run, or None (plan 43). A run of a
    pipeline records it in `backend.embedding`. A run of an embedding configuration from
    before plan 34 records it in `backend.id`. A run of another backend has none."""
    meta = run_files.read_json(run_files.run_path(runs_dir, run_id, "run.json")) or {}
    backend = meta.get("backend") or {}
    if backend.get("kind") != "embedding":
        return None
    name = backend.get("embedding") or backend.get("id")
    return name if isinstance(name, str) and embeddings.NAME_RE.match(name) else None


def clusters_view(runs_dir, server, query):
    """Answer the clusters of the embedding of one run (plan 43): the view `combined` of
    `data/catalog/embeddings/<name>/clusters.json`, the `label` rule of each cluster from
    `cluster-rules.json` of the same directory, and the card name of each cluster slug.
    A run with no embedding, or an embedding with no cluster build, gives no cluster."""
    import clusters as embedding_clusters  # noqa: E402  (numpy, on demand)
    run_id = _one(query, "id")
    if run_id not in run_files.run_dirs(runs_dir):
        return _error(404, "unknown run")
    answer = {"exists": False, "embedding": run_embedding(runs_dir, run_id),
              "space": CLUSTER_SPACE, "file": None, "built_at": None, "stale": None,
              "clusters": [], "cards": {}}
    name = answer["embedding"]
    if name is None:
        return _json(200, answer)
    directory = embeddings.entry_dir(server.db_path, name)
    answer["file"] = os.path.join(directory, embedding_clusters.CLUSTERS_FILE)
    try:
        artifact = CLUSTER_HINT_INPUTS.get(
            (directory, "artifact"), [answer["file"]],
            lambda: embedding_clusters.load_artifact(directory), copy_value=False)
        rule_path = os.path.join(directory, embedding_clusters.RULES_FILE)
        rules = CLUSTER_HINT_INPUTS.get(
            (directory, "rules"), [rule_path],
            lambda: embedding_clusters.load_rules(directory), copy_value=False).get(RULE_SPACE) or {}
    except embedding_clusters.ClusterError as exc:
        return _json(200, dict(answer, error=str(exc)))
    if artifact is None:
        return _json(200, answer)
    try:
        settings = SETTINGS_CACHE.get(server.config_path or embeddings.CONFIG_PATH,
                                      embeddings.load_settings)
        answer["stale"] = embedding_clusters.artifact_status(settings, name, artifact=artifact)["stale"]
    except (embedding_clusters.ClusterError, embeddings.ConfigError, OSError,
            sqlite3.Error, ValueError):
        pass  # the status is a hint of the frame; `null` means "not known"
    view = ((artifact.get("spaces") or {}).get(CLUSTER_SPACE) or {}).get("clusters") or []
    clusters = []
    for cluster in view:
        slugs = cluster.get("slugs") or []
        rule = rules.get(cluster.get("key"))
        clusters.append({"id": cluster.get("id"), "key": cluster.get("key"),
                         "kind": cluster.get("kind"),
                         "size": cluster.get("size", len(slugs)), "slugs": list(slugs),
                         "rule": {k: copy.deepcopy(rule.get(k)) for k in RULE_KEYS}
                         if isinstance(rule, dict) else None})
    answer.update(exists=True, built_at=artifact.get("built_at"), clusters=clusters)
    wanted = sorted({slug for cluster in clusters for slug in cluster["slugs"]})
    cards = answer["cards"]
    try:
        with closing(_connect(server.db_path)) as conn:
            for start in range(0, len(wanted), 500):
                chunk = wanted[start:start + 500]
                for slug, name in conn.execute(
                        "SELECT wine_slug, COALESCE(name_patched, name) FROM wine_catalog "
                        "WHERE wine_slug IN (%s)"
                        % ", ".join("?" for _ in chunk), chunk):
                    cards[slug] = {"name": name or ""}
    except sqlite3.Error:
        pass  # the names are a hint of the VLM box; the slug stands in their place
    return _json(200, answer)


def inputs_view(runs_dir, db_path, query):
    """Answer the exact model-bound images of one recorded query."""
    run_id, query_id = _one(query, "id"), _one(query, "query")
    if run_id not in run_files.run_dirs(runs_dir):
        return _error(404, "unknown run")
    record = run_files.run_result(runs_dir, run_id, query_id)
    if record is None:
        return _error(404, "unknown query")
    meta = run_files.read_json(run_files.run_path(runs_dir, run_id, "run.json")) or {}
    backend_url = str((meta.get("backend") or {}).get("url") or "")
    # A run of `embedding_run.py` (plan 33) prepared the photo with the steps of a lab
    # configuration. The backend `local` sends no HTTP request, so its run has no URL.
    embedded = (meta.get("backend") or {}).get("kind") == "embedding"
    if not backend_url and not embedded:
        # The configuration `mock` sends no request, so no image went to a model.
        return _json(200, {"run": run_id, "query": query_id, "inputs": [],
                           "notes": ["This run sent no request to a model, so it has no "
                                     "model input."]})
    if (meta.get("backend") or {}).get("kind") == "remote":
        # `remote_run.py` sends the photo as it is to a matcher outside this workspace
        # (plan 31). The local matcher configurations do not know its URL.
        return _json(200, {"run": run_id, "query": query_id, "inputs": [],
                           "notes": ["This run sent the photo as it is to the remote matcher "
                                     "%s. The matcher reports no model input." % backend_url]})
    digest = str(record.get("image_sha256") or "")
    try:
        with closing(_connect(db_path)) as conn:
            hit = _store_rows(conn, {digest}).get(digest) if digest else None
    except sqlite3.Error as exc:
        return _error(503, "cannot read the image store: %s" % exc)
    if not hit:
        return _error(404, "the source image of this query is not in the lab image store")
    path = os.path.join(labdb.image_dir(db_path, hit[0]), "%s.%s" % (digest, hit[1]))
    if embedded:
        # The steps of run.json and the SAM3 answers of the cache; no request to a model.
        # The candidates tell an answer of the code lookup (plan 42).
        import embedding_run  # noqa: E402  (the SAM3 cuts and the steps, on demand)
        return _json(200, {"run": run_id, "query": query_id,
                           **embedding_run.model_inputs(
                               meta["backend"], path, list(record.get("candidates") or []))})
    scripts = os.path.join(ROOT, "scripts")
    if scripts not in sys.path:
        sys.path.insert(1, scripts)
    import run_model_inputs  # noqa: E402  (PIL and the matcher code, on demand)
    try:
        answer = run_model_inputs.build_model_inputs(
            Path(MATCHER_ROOT), backend_url, Path(path), digest,
            list(record.get("candidates") or []))
    except run_model_inputs.InputRebuildError as exc:
        return _error(422, str(exc))
    except (OSError, ValueError) as exc:
        return _error(500, "cannot rebuild model inputs: %s" % exc)
    return _json(200, {"run": run_id, "query": query_id, **answer})


def steps_view(runs_dir, db_path, query, card_images, *, card_images_for_slugs=None):
    """Answer the steps of one recorded query for the step popup (plan 41):
    `run_steps.steps_view`."""
    import run_steps  # noqa: E402  (PIL, numpy, and the SAM3 cuts, on demand)
    try:
        answer = run_steps.defer_artifacts(run_steps.steps_view(runs_dir, db_path, _one(query, "id"),
                                               _one(query, "query"), card_images,
                                               card_images_for_slugs=card_images_for_slugs))
        for round_ in answer["rounds"]:
            for part in round_["steps"]:
                result = part.get("result") or {}
                if part["id"] == "cluster_rules" and (result.get("picture") or result.get("input_image")):
                    info = result.get("input_image") or {}
                    kind = info.get("kind") or result.get("picture")
                    part["artifacts"].append({
                        "src": "/api/run-vlm-image?" + urllib.parse.urlencode({
                            "id": answer["run"], "query": answer["query"]}),
                        "caption": "Image sent to VLM · " + ("label crop" if kind == "label" else "whole photo"),
                        "width": info.get("width"), "height": info.get("height"),
                        "deferred": True})
        return _json(200, answer)
    except run_steps.StepError as exc:
        return _error(exc.code, str(exc))


def vlm_image_view(runs_dir, db_path, query):
    """Serve only a saved run's recorded or locally verified VLM input PNG."""
    import hashlib
    import rerank_images
    import run_steps
    try:
        run_id, query_id = _one(query, "id"), _one(query, "query")
        paths = [run_files.run_path(runs_dir, run_id, name) for name in ("run.json", "results.jsonl")]
        if any(path is None for path in paths):
            return _error(400, "bad run id")
        before = run_steps.VisualInputsCache.state(paths)
        row, _meta, spec = run_steps._run_data(runs_dir, run_id, query_id)
        result = rerank_images.evidence(row)
        if not result:
            return _error(404, "This query has no recorded VLM re-rank.")
        hit = rerank_images.saved(result)
        if hit:
            data = hit[0]
        else:
            with closing(_connect(db_path)) as conn:
                photo = run_steps.Photo(conn, db_path, row)
            if not photo.path or not photo.source_state:
                return _error(404, "The original photo is unavailable for VLM input recovery.")
            if hashlib.sha256(Path(photo.path).read_bytes()).hexdigest() != row.get("image_sha256"):
                return _error(404, "The original photo differs from the saved run.")
            data, _info = rerank_images.resolve(result, spec, photo.path)
            if run_steps.VisualInputsCache.state([photo.path]) != (photo.source_state,):
                return _error(404, "The original photo changed during VLM input recovery.")
        if before is None or run_steps.VisualInputsCache.state(paths) != before:
            return _error(404, "The run changed during VLM input recovery.")
    except run_steps.StepError as exc:
        return _error(exc.code, str(exc))
    except rerank_images.ImageUnavailable as exc:
        return _error(404, str(exc))
    except (OSError, ValueError, sqlite3.Error) as exc:
        return _error(404, "Cannot read the VLM input image: %s" % exc)
    return 200, data, "image/png", "no-store"


def artifact_view(runs_dir, db_path, query):
    import run_steps
    try:
        data = run_steps.artifact_image(runs_dir, db_path, _one(query, "id"),
                                       _one(query, "query"), _one(query, "step"),
                                       _one(query, "artifact"), _one(query, "token"))
    except run_steps.StepError as exc:
        return _error(exc.code, str(exc))
    return 200, data, "image/png", "no-store"


def preview_view(runs_dir, db_path, query):
    """Return one checked rotated candidate PNG. Keep failure responses as JSON."""
    import run_steps
    try:
        data = run_steps.preview_image(runs_dir, db_path, _one(query, "id"),
                                       _one(query, "query"), _one(query, "view"),
                                       _one(query, "rank"), _one(query, "token"))
    except run_steps.StepError as exc:
        return _error(exc.code, str(exc))
    return 200, data, "image/png", "no-store"


def candidate_view(runs_dir, db_path, query):
    """Answer the catalogue inputs of one candidate of one recorded query of an embedding
    run, with the cosine of each (plan 38): `embedding_run.candidate_items`."""
    run_id, query_id, slug = _one(query, "id"), _one(query, "query"), _one(query, "slug")
    if run_id not in run_files.run_dirs(runs_dir):
        return _error(404, "unknown run")
    record = run_files.run_result(runs_dir, run_id, query_id)
    if record is None:
        return _error(404, "unknown query")
    cand = next((c for c in record.get("candidates") or () if c.get("slug") == slug), None)
    if cand is None:
        return _error(404, "the slug is not a candidate of this query")
    head = {"run": run_id, "query": query_id, "slug": slug}
    spec = (run_files.read_json(run_files.run_path(runs_dir, run_id, "run.json"))
            or {}).get("backend") or {}
    if spec.get("kind") != "embedding":
        return _json(200, dict(head, score=cand.get("score"), views={}, items=[], notes=[
            "This run is not a run of an embedding pipeline, so it holds no cosine of a "
            "catalogue input."]))
    import embedding_run  # noqa: E402  (numpy and the index, on demand)
    return _json(200, dict(head, **embedding_run.candidate_items(spec, cand, db_path)))
