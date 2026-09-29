"""Create one manual wine and activate its items in one embedding index.

The CLI and `lab_server.py` use this workflow. The catalogue write completes before
model inference starts. A later index failure keeps the wine and returns a partial
result that an operator can repair on `/embedding`.

Read `docs/plans/78_incremental-new-wine-index.md`.

The CLI calls `create`, which waits for the index. `POST /api/wine` calls `create_wine`
and answers; `new_wine_jobs.py` then runs `update_index` in the background. Read
`docs/plans/84_background-new-wine-index.md`.
"""
import hashlib
import os
from contextlib import closing

import embeddings
import labdb
import manual_wines
import rebuild_on_run

CONFIG_KEY = "new_wine_embedding"


class WorkflowError(manual_wines.WineError):
    """The workflow cannot start. No wine was created."""


def embedding_name(config_path, override=None):
    """Return the selected embedding name. Raise `WorkflowError` for no valid name."""
    try:
        _path, config, _db_path = embeddings.read_config(config_path)
    except embeddings.ConfigError as exc:
        raise WorkflowError(503, str(exc)) from exc
    value = override if override is not None else config.get(CONFIG_KEY)
    if not isinstance(value, str) or not embeddings.NAME_RE.match(value):
        source = "--embedding" if override is not None else CONFIG_KEY
        raise WorkflowError(400 if override is not None else 503,
                            "%s MUST name one embedding" % source)
    return value


def _index_sha256(directory):
    path = os.path.join(directory, embeddings.INDEX)
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except OSError as exc:
        raise embeddings.ConfigError("cannot read the active index: %s" % exc) from exc


def preflight(db_path, config_path, override=None):
    """Validate the configured embedding and its active index before a catalogue write."""
    name = embedding_name(config_path, override)
    try:
        settings = embeddings.load_settings(config_path)
        settings.find(name)
    except KeyError as exc:
        raise WorkflowError(400 if override is not None else 503,
                            "config.yaml has no embedding %s" % name) from exc
    except embeddings.ConfigError as exc:
        raise WorkflowError(503, str(exc)) from exc
    if os.path.realpath(settings.db_path) != os.path.realpath(db_path):
        raise WorkflowError(503, "the workflow database does not match config.yaml")
    directory = embeddings.entry_dir(settings.db_path, name)
    if not rebuild_on_run.index_ready(directory):
        raise WorkflowError(409, "the embedding %s has no active index; build it on "
                            "/embedding first" % name)
    try:
        index = embeddings.read_index(directory)
        vectors = embeddings.read_vectors(directory, index)
        if index is None or vectors is None:
            raise ValueError("the index or vector matrix is absent")
        digest = _index_sha256(directory)
    except (OSError, ValueError, embeddings.ConfigError) as exc:
        raise WorkflowError(503, "the active index of %s is invalid: %s" % (name, exc)) \
            from exc
    return settings, name, directory, digest


def verify(settings, name, slug):
    """Verify the current items of `slug` in the active index. Return index evidence."""
    embedding = settings.find(name)
    directory = embeddings.entry_dir(settings.db_path, name)
    with closing(embeddings.open_database(settings.db_path)) as conn:
        wines, sources = embeddings.read_inputs(conn, settings.db_path)
    wine = next((item for item in wines if item["slug"] == slug), None)
    if wine is None:
        raise embeddings.ConfigError("the active catalogue has no wine %s" % slug)
    digests = {digest for _image_type, digest in wine["columns"]}
    planned = {key: item for key, item in embeddings.plan_items(embedding, sources).items()
               if key[0] in digests}
    if not planned:
        raise embeddings.ConfigError("the wine %s has no applicable index item" % slug)
    index = embeddings.read_index(directory)
    vectors = embeddings.read_vectors(directory, index)
    if index is None or vectors is None:
        raise embeddings.ConfigError("the active index or vector matrix is absent")
    states = embeddings.item_status(planned, index, embeddings.image_names(directory))
    bad = []
    for key, (state, record) in states.items():
        row = record.get("row") if record else None
        if state != "current" or not isinstance(row, int) or not 0 <= row < len(vectors):
            bad.append("%s/%s=%s" % (key[0][:12], key[1], state))
    if bad:
        raise embeddings.ConfigError("the active index does not contain current items "
                                     "for %s: %s" % (slug, ", ".join(bad)))
    return {
        "items": len(planned),
        "index_sha256": _index_sha256(directory),
        "vectors_file": index["vectors_file"],
        "updated_at": index.get("updated_at"),
    }


def _connect(path):
    return labdb.connect(path)


def selected_index(db_path, config_path, override=None):
    """Run the preflight. Return the input of `update_index`: (settings, name, the
    SHA-256 of the active index). Raise `WorkflowError`."""
    settings, name, _directory, before = preflight(db_path, config_path, override)
    return settings, name, before


def create_wine(db_path, body, *, config_path=None, embedding=None, segmenter=None,
                connect=_connect):
    """Run the preflight and create the wine. Return (the create result, the selected
    index). The selected index is None with `config_path=None`.

    The lab server calls `update_index` later, in a background job (plan 84).
    """
    selected = None
    if config_path is not None:
        selected = selected_index(db_path, config_path, embedding)
    with closing(connect(db_path)) as conn:
        conn.isolation_level = None
        conn.execute("PRAGMA foreign_keys = ON")
        created = manual_wines.add_wine(conn, db_path, body, segmenter)
    result = {"slug": created["slug"], "warnings": list(created["warnings"]),
              "index": None}
    return result, selected


def update_index(selected, config_path, slug, *, build=rebuild_on_run.build,
                 log=lambda message: None):
    """Update the selected index and verify the items of `slug`. Return (the index
    result, a warning or None). A failure gives the state `failed` and a warning."""
    settings, name, before = selected
    try:
        final = build(name, config_path, log)
        if final is None:
            raise embeddings.ConfigError("the embedding has no active index")
        evidence = verify(settings, name, slug)
        return {
            "name": name,
            "state": "active",
            "built": final.get("built"),
            "current": final.get("current"),
            "failed": final.get("failed"),
            "pruned": final.get("pruned"),
            "changed": evidence["index_sha256"] != before,
            **evidence,
        }, None
    except (embeddings.ConfigError, OSError, ValueError) as exc:
        message = ("The wine was created, but the index %s was not activated for it: %s. "
                   "Retry the build on /embedding." % (name, exc))
        return {"name": name, "state": "failed", "error": str(exc)}, message


def create(db_path, body, *, config_path=None, embedding=None, segmenter=None,
           connect=_connect, build=rebuild_on_run.build, log=lambda message: None):
    """Create a wine, update one index, and return the workflow result.

    `config_path=None` keeps the old create-only behavior of embedded test servers.
    A failure after the catalogue transaction returns index state `failed`.
    """
    result, selected = create_wine(db_path, body, config_path=config_path,
                                   embedding=embedding, segmenter=segmenter,
                                   connect=connect)
    if selected is None:
        return result
    result["index"], warning = update_index(selected, config_path, result["slug"],
                                            build=build, log=log)
    if warning:
        result["warnings"].append(warning)
    return result

