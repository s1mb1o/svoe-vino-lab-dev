"""The routes of the Runs page of the lab server.

The page reads the run directories of `runs/` with `run_files.py`. The runs stay files;
the lab database does not hold them. Each route is GET and writes nothing:

    GET /runs                                   the page
    GET /api/runs                               the head of each run, and the
                                                pipelines of `config.yaml`
    GET /api/run?id=&filter=&sort=&q=&offset=&limit=
                                                the metrics and the rows of one run
    GET /api/run-clusters?id=                   the clusters of the embedding of one run
                                                and their card names (plan 43)
    GET /api/run-inputs?id=&query=              the model inputs of one row
    GET /api/run-candidate?id=&query=&slug=     the catalogue inputs of one candidate of
                                                an embedding run and their cosines

A pipeline is one entry of the key `pipeline` of `config.yaml` (`pipelines.py`, plan
34). The key `configuration` of `run.json` names it. The images come from the image
store of the lab database, through the route `/images/<folder>/<sha256>.<ext>`: the photo
of a row by its `image_sha256`, and the catalogue image of a slug by the rule of
`card_images` of `lab_server.py`. Read `docs/plans/23_runs-page.md`.
"""
import os
import sqlite3
import sys
import urllib.parse
from contextlib import closing
from pathlib import Path

import embeddings
import lab_pages
import labdb
import pipelines
import run_files

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS_DIR = os.path.join(ROOT, "runs")
MATCHER_ROOT = os.path.join(os.path.dirname(ROOT), "svoe-vino-matcher")
ROUTES = ("/runs", "/api/runs", "/api/run", "/api/run-clusters", "/api/run-inputs",
          "/api/run-candidate")
JSON_TYPE = "application/json; charset=utf-8"
MAX_LIMIT = 1000
# The keys of a cluster rule that the VLM box of the page reads.
RULE_KEYS = ("mode", "questions")
# The view of `clusters.json` that the page shows, as on the Testset page (plan 37), and
# the rule space of `cluster-rules.json`: the matcher sends a label crop (plan 30).
CLUSTER_SPACE = "combined"
RULE_SPACE = "label"


def handles(route):
    """Answer whether `route` belongs to the Runs page."""
    return route in ROUTES


def _json(code, value):
    return code, value, JSON_TYPE, "no-store"


def _error(code, message):
    return _json(code, {"error": message})


def respond(server, method, path, card_images):
    """Answer one request. Return (HTTP code, body, content type, Cache-Control).

    `card_images(conn)` is `lab_server.card_images`: slug -> the images of the card.
    """
    parts = urllib.parse.urlsplit(path)
    route = parts.path
    query = urllib.parse.parse_qs(parts.query)
    if method not in ("GET", "HEAD"):
        return _error(405, "the route %s answers GET alone" % route)
    runs_dir = getattr(server, "runs_dir", None) or RUNS_DIR
    if route == "/runs":
        return 200, lab_pages.page("runs.html"), "text/html; charset=utf-8", "no-store"
    if route == "/api/runs":
        return _json(200, runs_view(runs_dir, server.config_path or embeddings.CONFIG_PATH))
    if route == "/api/run":
        return run_view(runs_dir, server.db_path, query, card_images)
    if route == "/api/run-clusters":
        return clusters_view(runs_dir, server, query)
    if route == "/api/run-candidate":
        return candidate_view(runs_dir, server.db_path, query)
    return inputs_view(runs_dir, server.db_path, query)


def _one(query, key, default=""):
    return (query.get(key) or [default])[0]


def configurations(config_path):
    """Return (the pipelines of `config.yaml`, in file order, the error of the file or
    None). An entry that is not valid keeps its name and its error."""
    try:
        settings = pipelines.load(config_path)
    except embeddings.ConfigError as exc:
        return [], str(exc)
    return [{"name": name, "backend": pipeline.backend if pipeline else None,
             "error": error} for name, pipeline, error in settings.entries], None


def runs_view(runs_dir, config_path):
    """Return the head of each run, the newest first, and the pipelines."""
    entries, error = configurations(config_path)
    return {"runs_dir": runs_dir,
            "runs": [run_files.run_head(runs_dir, run_id)
                     for run_id in run_files.run_dirs(runs_dir)],
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
    slugs.update(row.get("truth") or ())
    slugs.update((row.get("twin") or {}).get("slugs") or ())
    slugs.discard(None)
    return slugs


def add_images(conn, rows, card_images):
    """Add `photo_url` to each row. Return (slug -> catalogue image URL, the slugs with
    a patch). The photo URL takes the folder of the `image` row: most test photos are
    in `testset`, and a photo whose bytes were a lab image before keeps that folder."""
    store = _store_rows(conn, {r.get("image_sha256") for r in rows if r.get("image_sha256")})
    for row in rows:
        hit = store.get(row.get("image_sha256") or "")
        row["photo_url"] = ("/images/%s/%s.%s" % (hit[0], row["image_sha256"], hit[1])
                            if hit else None)
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
    rows, total = run_files.run_rows(runs_dir, run_id, mode, _one(query, "q"), limit,
                                     offset, sort)
    # The items of a candidate of an embedding run come through `/api/run-candidate`
    # (plan 38), so a page of rows stays small.
    for row in rows:
        for cand in row.get("candidates") or ():
            cand.pop("items", None)
    bottles, patched, images_error = {}, [], None
    try:
        with closing(_connect(db_path)) as conn:
            bottles, patched = add_images(conn, rows, card_images)
    except sqlite3.Error as exc:
        images_error = "cannot read the image store: %s" % exc
        for row in rows:
            row.setdefault("photo_url", None)
    return _json(200, {
        "run": run_files.read_json(run_files.run_path(runs_dir, run_id, "run.json")) or {},
        "metrics": run_files.read_json(
            run_files.run_path(runs_dir, run_id, "metrics.json")) or {},
        "head": run_files.run_head(runs_dir, run_id),
        "filter": mode, "sort": sort, "total": total, "offset": offset, "limit": limit,
        "rows": rows, "bottles": bottles, "patched": patched, "images_error": images_error,
    })


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
    `data/embeddings/<name>/clusters.json`, the `label` rule of each cluster from
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
        artifact = embedding_clusters.load_artifact(directory)
        rules = embedding_clusters.load_rules(directory).get(RULE_SPACE) or {}
    except embedding_clusters.ClusterError as exc:
        return _json(200, dict(answer, error=str(exc)))
    if artifact is None:
        return _json(200, answer)
    try:
        settings = embeddings.load_settings(server.config_path or embeddings.CONFIG_PATH)
        answer["stale"] = embedding_clusters.artifact_status(settings, name)["stale"]
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
                         "size": cluster.get("size", len(slugs)), "slugs": slugs,
                         "rule": {k: rule.get(k) for k in RULE_KEYS}
                         if isinstance(rule, dict) else None})
    answer.update(exists=True, built_at=artifact.get("built_at"), clusters=clusters)
    wanted = sorted({slug for cluster in clusters for slug in cluster["slugs"]})
    cards = answer["cards"]
    try:
        with closing(_connect(server.db_path)) as conn:
            for start in range(0, len(wanted), 500):
                chunk = wanted[start:start + 500]
                for slug, name in conn.execute(
                        "SELECT wine_slug, name FROM wine_catalog WHERE wine_slug IN (%s)"
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
    path = os.path.join(labdb.image_store(db_path), hit[0], "%s.%s" % (digest, hit[1]))
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
