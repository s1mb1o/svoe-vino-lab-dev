"""The pipelines of the lab: the key `pipeline` of `config.yaml`.

A pipeline is a matcher that answers a test photo with a ranked list of wines. The dialog
`Run>` of `/testset` (`run_jobs.py`) and the filter of `/runs` (`run_routes.py`) show the
pipelines. The key `configuration` of `run.json` names the pipeline of a run. An embedding
model is an entry of the key `embeddings` (`embeddings.py`), not a pipeline. Read
docs/plans/34_pipeline-section.md.

The backends:
    svoe-vino-ru   a remote matcher, for example the official recognizer of vino-svoe.ru.
                   `remote_run.py` sends each photo of a test set as it is (plan 31).
    embedding      the vectors of one entry of the key `embeddings`, named by the key
                   `embedding`; `embedding_run.py` (plan 33). The owner chose this on
                   2026-09-26T00:12:24+0300: `embeddings` prepares and uses the vectors,
                   and `pipeline` holds the runs. The optional key `views` holds the
                   steps of the test photo (owner answers of 00:52:41); without it the
                   test photo gets the steps of the embedding entry. The optional key
                   `barcode` decodes the photo first (`barcode.py`, plan 42): a code of
                   `wine_code` answers the photo, and the embedding does not run. The
                   optional key `rerank` re-ranks the cards of one cluster with the
                   label rules of plan 45 (`cluster_rerank.py`, plan 48).

The owner removed the pipeline `mock` and its code on 2026-09-26T00:26:27+0300.
"""
import barcode
import cluster_rerank
import embeddings
from embeddings import ConfigError

REMOTE_BACKEND = "svoe-vino-ru"
EMBEDDING_BACKEND = "embedding"
BACKENDS = (REMOTE_BACKEND, EMBEDDING_BACKEND)
# The keys of each backend, in addition to `name` and `backend`.
# The request keys of the backend `svoe-vino-ru` have the meaning of the same keys of
# `backends.yaml`, and the defaults of `match_backends.HttpMultipartBackend`. Read
# docs/plans/31_remote-configuration.md.
REMOTE_KEYS = ("url", "field", "response", "query", "top_k", "timeout_s", "workers", "headers")
REMOTE_DEFAULTS = {"field": "image", "response": "auto", "query": {}, "top_k": 1,
                   "timeout_s": 30, "workers": 1, "headers": {}}
# The answer shapes of `match_backends.SHAPES`. A test keeps the two lists equal.
REMOTE_SHAPES = ("auto", "slug-object", "slug-array", "candidates")
BACKEND_KEYS = {REMOTE_BACKEND: REMOTE_KEYS,
                EMBEDDING_BACKEND: ("embedding", "views", "barcode", "rerank")}


def _remote(raw):
    """Return the request keys of an entry of the backend `svoe-vino-ru`, with each
    default filled in."""
    remote = dict(REMOTE_DEFAULTS)
    remote.update({key: raw[key] for key in REMOTE_KEYS if raw.get(key) is not None})
    url = remote.get("url")
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        raise ConfigError("url MUST be an http or https URL")
    if not isinstance(remote["field"], str) or not remote["field"]:
        raise ConfigError("field MUST be a non-empty string")
    if remote["response"] not in REMOTE_SHAPES:
        raise ConfigError("response MUST be one of: %s" % ", ".join(REMOTE_SHAPES))
    for key in ("top_k", "workers"):
        value = remote[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ConfigError("%s MUST be an integer of 1 or more" % key)
    timeout = remote["timeout_s"]
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ConfigError("timeout_s MUST be a number above 0")
    for key in ("query", "headers"):
        value = remote[key]
        if not isinstance(value, dict) or not all(
                isinstance(k, str) and isinstance(v, (str, int, float))
                for k, v in value.items()):
            raise ConfigError("%s MUST be a mapping of names to values" % key)
        remote[key] = dict(value)
    return remote


class Pipeline:
    """One checked entry of the key `pipeline` of `config.yaml`. `remote` holds the
    request keys of the backend `svoe-vino-ru`. `embedding` is the name of the `embeddings`
    entry of the backend `embedding`, `views` the steps of its test photo (view ->
    steps), or None for the steps of the entry, `barcode` the options of the barcode
    step (plan 42), or None for no barcode step, and `rerank` the options of the cluster
    re-rank (plan 48), or None. Each is None for another backend."""

    def __init__(self, raw):
        if not isinstance(raw, dict):
            raise ConfigError("an entry MUST be a mapping")
        name = raw.get("name")
        if not isinstance(name, str) or not embeddings.NAME_RE.match(name):
            raise ConfigError("the name %r MUST match %s" % (name, embeddings.NAME_RE.pattern))
        self.name = name
        self.backend = raw.get("backend")
        if self.backend not in BACKENDS:
            raise ConfigError("backend MUST be one of: %s; an embedding model is an entry "
                              "of the key `embeddings`" % ", ".join(BACKENDS))
        unknown = sorted(set(raw) - {"name", "backend"} - set(BACKEND_KEYS[self.backend]))
        if unknown:
            raise ConfigError("the backend %s takes no %s" % (self.backend, ", ".join(unknown)))
        self.remote = _remote(raw) if self.backend == REMOTE_BACKEND else None
        self.embedding = self.views = self.barcode = self.rerank = None
        if self.backend == EMBEDDING_BACKEND:
            model = raw.get("embedding")
            if not isinstance(model, str) or not embeddings.NAME_RE.match(model):
                raise ConfigError("embedding MUST be the name of an entry of the key "
                                  "`embeddings`")
            self.embedding = model
            if "views" in raw:
                self.views = _views(raw["views"])
            if "barcode" in raw:
                self.barcode = barcode.check_options(raw["barcode"])
            if "rerank" in raw:
                self.rerank = cluster_rerank.check_options(raw["rerank"])


def _views(views):
    """Check the key `views` of a pipeline of the backend `embedding`: the steps of the test
    photo in each view. The first step MAY be another step than `segment`."""
    if not isinstance(views, dict) or not views:
        raise ConfigError("views MUST be a mapping with at least one view")
    other = sorted(set(views) - set(embeddings.VIEWS))
    if other:
        raise ConfigError("unknown view: %s; use %s"
                          % (", ".join(other), " or ".join(embeddings.VIEWS)))
    return {view: embeddings.check_steps(view, views[view], segment_first=False)
            for view in embeddings.VIEWS if view in views}


class Pipelines:
    """The pipelines of `config.yaml`, and the paths of the file and of the database."""

    def __init__(self, config_path, db_path, entries):
        self.config_path = config_path
        self.db_path = db_path
        # A list of (name, Pipeline or None, the configuration error or None).
        self.entries = entries

    def find(self, name):
        """Return the pipeline `name`. Raise KeyError for an unknown name, and
        ConfigError for an entry that is not valid."""
        for label, pipeline, error in self.entries:
            if label == name:
                if error:
                    raise ConfigError(error)
                return pipeline
        raise KeyError(name)


def load(path=embeddings.CONFIG_PATH):
    """Read the key `pipeline` of `config.yaml`. Return the `Pipelines`. An entry that is
    not valid keeps its error, so that the pages can show it. A pipeline of the backend
    `embedding` MUST name a valid entry of the key `embeddings`, and each view of its key
    `views` MUST be a view of that entry. A file with no key
    `pipeline` has no pipeline. Raise ConfigError when the file itself does not allow the
    work."""
    path, config, db_path = embeddings.read_config(path)
    models = {name: (embedding, error) for name, embedding, error in
              embeddings.check_entries(config, "embeddings", embeddings.Embedding)}

    def make(raw):
        pipeline = Pipeline(raw)
        if pipeline.embedding is not None:
            if pipeline.embedding not in models:
                raise ConfigError("the embedding %s is not an entry of the key `embeddings`"
                                  % pipeline.embedding)
            model, error = models[pipeline.embedding]
            if error:
                raise ConfigError("the embedding %s is not valid: %s"
                                  % (pipeline.embedding, error))
            other = sorted(set(pipeline.views or ()) - set(model.views))
            if other:
                raise ConfigError("the embedding %s has no view %s"
                                  % (pipeline.embedding, ", ".join(other)))
            rules = (pipeline.rerank or {}).get("rules")
            if rules is not None and rules not in models:
                raise ConfigError("rerank.rules names %s, which is not an entry of the key "
                                  "`embeddings`" % rules)
        return pipeline

    return Pipelines(path, db_path, embeddings.check_entries(config, "pipeline", make))
