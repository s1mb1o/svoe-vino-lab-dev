"""Routes of the embedding-dependent Clusters page.

    GET  /clusters
    GET  /api/clusters
    GET  /api/clusters/<name>
    POST /api/clusters/<name>/build
    POST /api/clusters/<name>/note

Read `docs/plans/30_embedding-clusters.md`.
"""
import json
import os
import re
import urllib.parse

import clusters
import embeddings
import lab_pages

PAGE = "/clusters"
API = "/api/clusters"
ENTRY_ROUTE = re.compile(r"^/api/clusters/(%s)(/build|/note)?$"
                         % embeddings.NAME_PATTERN)
JSON_TYPE = "application/json; charset=utf-8"
HTML_TYPE = "text/html; charset=utf-8"
NO_STORE = "no-store"
MAX_BODY = 32768


def handles(route):
    return route == PAGE or route == API or route.startswith(API + "/")


def _json(code, value):
    return code, value, JSON_TYPE, NO_STORE


def _error(code, message):
    return _json(code, {"error": message})


def _body(read_body):
    raw = read_body(MAX_BODY)
    if raw is None:
        return {}
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        raise clusters.ClusterError("the body MUST be one JSON object") from exc
    if not isinstance(value, dict):
        raise clusters.ClusterError("the body MUST be one JSON object")
    return value


def _known(settings, name):
    for label, embedding, error in settings.entries:
        if label == name:
            if error:
                return None, _error(400, "embedding %s: %s" % (name, error))
            return embedding, None
    return None, _error(404, "config.yaml has no embedding %s" % name)


def list_view(settings):
    entries = []
    for name, embedding, error in settings.entries:
        record = {"name": name, "error": error}
        if embedding is not None:
            directory = embeddings.entry_dir(settings.db_path, name)
            artifact = clusters.load_artifact(directory)
            record.update(directory=directory, exists=artifact is not None)
            if artifact is not None:
                record.update(
                    built_at=artifact.get("built_at"), settings=artifact.get("settings") or {},
                    counts={space: ((artifact.get("spaces") or {}).get(space) or {}).get(
                        "counts") or {} for space in clusters.SPACES})
                try:
                    status = clusters.artifact_status(settings, name)
                except clusters.ClusterError as exc:
                    record.update(stale=True, status_error=str(exc))
                else:
                    record.update(stale=status.get("stale"),
                                  status_error=status.get("current_error"))
        entries.append(record)
    return {"database_file": settings.db_path, "config_file": settings.config_path,
            "embeddings": entries}


def respond(server, method, path, read_body):
    """Return `(code, body, content type, cache)` for one request."""
    route = urllib.parse.urlsplit(path).path
    if route == PAGE:
        if method not in ("GET", "HEAD"):
            return _error(405, "use GET")
        return 200, lab_pages.page("clusters.html"), HTML_TYPE, NO_STORE
    config_path = getattr(server, "config_path", None) or embeddings.CONFIG_PATH
    try:
        settings = embeddings.load_settings(config_path)
    except embeddings.ConfigError as exc:
        return _error(503, str(exc))
    if route == API:
        if method not in ("GET", "HEAD"):
            return _error(405, "use GET")
        try:
            return _json(200, list_view(settings))
        except clusters.ClusterError as exc:
            return _error(503, str(exc))
    match = ENTRY_ROUTE.match(route)
    if not match:
        return _error(404, "not found")
    name, action = match.groups()
    _, answer = _known(settings, name)
    if answer:
        return answer
    if action is None:
        if method not in ("GET", "HEAD"):
            return _error(405, "use GET")
        try:
            return _json(200, clusters.detail(settings, name))
        except clusters.ClusterError as exc:
            return _error(409, str(exc))
    if method != "POST":
        return _error(405, "use POST")
    try:
        body = _body(read_body)
        if action == "/build":
            # The owner chose on 2026-09-26 that the page sets no threshold.
            if "full_threshold" in body or "label_threshold" in body:
                raise clusters.ClusterError(
                    "the thresholds come from the block `clusters` of config.yaml")
            artifact = clusters.build_to_directory(settings, name)
            return _json(201, {
                "embedding": name, "built_at": artifact["built_at"],
                "settings": artifact["settings"],
                "counts": {space: artifact["spaces"][space]["counts"]
                           for space in clusters.SPACES},
                "file": os.path.join(embeddings.entry_dir(settings.db_path, name),
                                     clusters.CLUSTERS_FILE),
            })
        directory = embeddings.entry_dir(settings.db_path, name)
        artifact = clusters.load_artifact(directory)
        if artifact is None:
            return _error(409, "embedding %s has no clusters; build them first" % name)
        space = body.get("space")
        key = body.get("key")
        if not isinstance(key, str):
            raise clusters.ClusterError("key MUST be a string")
        cluster = clusters.cluster_in(artifact, space, key)
        if cluster is None:
            return _error(404, "the cluster is not in the current artifact")
        note = clusters.set_note(directory, cluster, body.get("text"))
        return _json(200, {"embedding": name, "space": space, "key": key,
                           "note": note})
    except clusters.Busy as exc:
        return _error(409, str(exc))
    except clusters.ClusterError as exc:
        return _error(400, str(exc))
    except (OSError, ValueError) as exc:
        return _error(500, str(exc))
