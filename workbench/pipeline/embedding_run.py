"""Make one run of a lab pipeline of the backend `embedding` on one test set: each photo
gets the SAM3 cuts and the steps of the embedding entry, the endpoint of the entry gives
its vectors, and the vectors rank the wines with the catalogue vectors of
`data/catalog/embeddings/<name>/`.

Usage:
    python3 pipeline/embedding_run.py --name <pipeline> --set <set>
        [--workers N] [--limit N] [--label TEXT] [--top-k N]

The pipeline is an entry of the key `pipeline` of `config.yaml` with `backend: embedding`
(owner answers of 2026-09-26T00:12:24+0300 and 00:15:17). Its key `embedding` names an
entry of the key `embeddings` with the backend `openai` or `local`, and that entry MUST
have its index: build it on `/embedding` first. An entry of the backend `local` needs
`torch`, so run it with `embedding_python`. Read docs/plans/33_embedding-run.md. With the
key `rebuild_embeddings_on_run` of `config.yaml` true, the run first updates that index
(`rebuild_on_run.py`, plan 59).

The rules of a run (owner answers of 2026-09-25T23:24:20+0300 and 23:35:19):
- Each test photo counts as a full photo. A view whose step `segment` names the target
  `package` uses the package cut of `derive.derive_image`, and the target `label` uses
  the label cut of `alternatives.label_cut_of`. Then `embeddings.apply_steps` applies the
  steps of the view. These are the functions of the catalogue images, so a test photo gets
  the pixels of a catalogue image. The cuts stay in memory. The SAM3 answers go to
  `data/cache/models/sam3/`, so a second run of a set sends no SAM3 request. When SAM3 finds no
  label, the view `label` has no input.
- A pipeline MAY hold `views`: the steps of the test photo in place of the steps of the
  entry (owner answers of 2026-09-26T00:52:41+0300). A view with no step `segment` takes
  the photo as it is into its steps, with no SAM3 request. A view of the photo ranks the
  catalogue vectors of the same view of the entry; the catalogue side stays the index.
- One request for each photo gives the vector of each view, with the code of the build
  (`build_embeddings.OpenAIBackend` or `LocalBackend`).
- The current items of the index alone count. The score of a wine is the mean of its best
  cosine in each view of the photo. For a wine with both views, the order is the order of
  the sum of the two cosines.

`benchmark.run_benchmark` writes the run files, so the files and the metrics are the files
and the metrics of a `benchmark.py` run. `run.json` holds `configuration: <pipeline>`, and
its `backend` holds `kind: embedding` and `embedding: <the embedding entry>`.
"""
import argparse
import collections
import contextlib
import hashlib
import os
import sqlite3
import sys
import threading
import time
from contextlib import closing

import numpy as np

import alternatives
import benchmark  # also puts scripts/ on sys.path
import build_embeddings
import derive
import embeddings
import labdb
import main_scene
import match_backends
import rebuild_on_run

KIND = "embedding"
# The backends of an embedding entry that this runner accepts.
BACKENDS = ("openai", "local")
DEFAULT_TOP_K = 10
NO_INDEX = "no index: build it on /embedding"
SCORE = ("the mean of the best cosine of the wine in each view of the photo; the current "
         "items of the index alone")
# The version of the key `trace` of a row (plan 41).
TRACE_VERSION = 1


class Trace:
    """The step trace of one photo (plan 41). Each step holds `id`, `start_ms`, and `ms`,
    counted from the start of the photo, and `out`, the result of the step. A SAM3 step
    also holds `cached`. A view with no input holds `skipped`, and a step that raised
    holds `error`."""

    def __init__(self):
        self.started = time.perf_counter()
        self.steps = []

    def now(self):
        return (time.perf_counter() - self.started) * 1000

    @contextlib.contextmanager
    def step(self, step_id, **keys):
        record = dict(id=step_id, **keys)
        start = self.now()
        record["start_ms"] = round(start, 1)
        self.steps.append(record)
        try:
            yield record
        except Exception as exc:
            record["error"] = str(exc)
            raise
        finally:
            record["ms"] = round(self.now() - start, 1)

    def value(self):
        return {"v": TRACE_VERSION, "steps": self.steps}


def _step(trace, step_id, **keys):
    """Return the step context of `trace`, or a context that records nothing."""
    return trace.step(step_id, **keys) if trace is not None else contextlib.nullcontext({})


def _cached(segmenter):
    """Tell whether the last SAM3 call of this thread read `model_cache`; None when the
    client does not tell."""
    probe = getattr(segmenter, "cached", None)
    return probe() if callable(probe) else None


class Sam3Once:
    """The SAM3 client of one run. After the first failure it asks SAM3 no more, so a run
    with no service does not wait for each photo. This is the rule of `derive._Once`."""

    def __init__(self, client):
        self.client = client
        self.endpoint = getattr(client, "endpoint", None)
        self.failure = None

    def _call(self, method, *args):
        if self.failure:
            raise derive.Sam3Unavailable("no request: SAM3 did not answer earlier in this "
                                         "run: %s" % self.failure)
        try:
            return method(*args)
        except derive.Sam3Unavailable as exc:
            self.failure = str(exc)
            raise

    def segment(self, image):
        return self._call(self.client.segment, image)

    def instances(self, image, texts, masks=True):
        return self._call(self.client.instances, image, texts, masks)

    def cached(self):
        return _cached(self.client)


class CachedSam3(derive.Sam3Client):
    """A SAM3 client that reads the answers of `data/cache/models/sam3/` alone. It sends no
    request, so a page route does not wait for gx10."""

    def _send(self, data, form):
        raise derive.Sam3Unavailable("the SAM3 answer of this photo is not in "
                                     "data/cache/models/sam3/")


# The rule of `derive.derive_image` that gave the package cut, by its settings text.
PACKAGE_RULES = {derive.SETTINGS_ALPHA: "alpha", derive.SETTINGS_WHITE: "white",
                 derive.SETTINGS_SEG: "sam3"}


def cuts_of(image, targets, segmenter, trace=None, scene_selection=False):
    """Return target -> (the box, the processed image) of one opened photo. A target
    that SAM3 did not find is None. Raise `derive.Sam3Unavailable`. `trace` gets the
    steps `sam3-package` and `sam3-label` (plan 41)."""
    out = {}
    if "package" in targets:
        with _step(trace, "sam3-package") as step:
            selection = None
            if scene_selection:
                method, settings, processed, box, selection = main_scene.cut(image, segmenter)
                rule = "main-scene-v%d" % main_scene.VERSION
            else:
                method, settings, processed, box = derive.derive_image(image, segmenter)
                rule = PACKAGE_RULES.get(settings)
            # A transparent photo gives its cut with no SAM3 call.
            step["cached"] = _cached(segmenter) if rule != "alpha" else None
            step["out"] = {"method": method, "rule": rule, "box": list(box),
                           "size": list(processed.size)}
            if selection is not None:
                step["out"]["selection"] = selection
        out["package"] = (box, processed)
    if "label" in targets:
        with _step(trace, "sam3-label") as step:
            instances, _scale = segmenter.instances(image, alternatives.DETECT_TEXTS)
            cut = alternatives.label_cut_of(image, instances)
            step["cached"] = _cached(segmenter)
            step["out"] = ({"found": True, "method": cut[0], "box": list(cut[2]),
                            "size": list(cut[1].size)} if cut else {"found": False})
        out["label"] = (cut[2], cut[1]) if cut else None
    return out


def segment_target(steps):
    """Return the target of a first step `segment`, or None when the view does not cut."""
    return steps[0]["target"] if steps and steps[0]["step"] == "segment" else None


def _no_cut():
    raise embeddings.ItemError("a view with no step `segment` has no processed file")


def cut_targets(views):
    """Return the SAM3 targets that the views `views` (view -> steps) need."""
    return {segment_target(steps) for steps in views.values()} - {None}


def view_input(image, steps, cuts, dis_segmenter=None):
    """Return (the model input of one view as an RGB image, None), or (None, the reason)
    when the view has no input. `cuts` is the answer of `cuts_of`. Raise
    `embeddings.ItemError`."""
    target = segment_target(steps)
    if target is None:
        return embeddings.apply_steps(
            image, steps, None, _no_cut, dis_segmenter=dis_segmenter), None
    cut = cuts.get(target)
    if cut is None:
        return None, "SAM3 found no %s" % target
    box, processed = cut
    return embeddings.apply_steps(
        image, steps, box, lambda p=processed: p, dis_segmenter=dis_segmenter), None


def query_inputs(image, views, segmenter, scene_selection=False, dis_segmenter=None):
    """Return (view -> the model input as an RGB image, view -> the reason of a view with
    no input) of one opened photo. `views` maps a view to its steps. SAM3 cuts the photo
    only for a view whose first step is `segment`. A view with no `segment`, for example
    of a pipeline with its own `views`, takes the photo as it is into its steps. Raise
    `derive.Sam3Unavailable` and `embeddings.ItemError`."""
    cuts = cuts_of(image, cut_targets(views), segmenter,
                   scene_selection=scene_selection)
    inputs, missing = {}, {}
    for view, steps in views.items():
        prepared, reason = view_input(image, steps, cuts, dis_segmenter)
        if prepared is None:
            missing[view] = reason
        else:
            inputs[view] = prepared
    return inputs, missing


def index_ready(db_path, name):
    """Tell whether the directory of an entry holds `index.json` and a vector file. This
    is the check of the dialog `Run>`; the runner checks the vectors themselves."""
    try:
        names = {entry.name for entry in os.scandir(embeddings.entry_dir(db_path, name))}
    except (FileNotFoundError, NotADirectoryError, ValueError):
        return False
    return embeddings.INDEX in names and any(embeddings.VECTORS_RE.match(n) for n in names)


class Catalogue:
    """The current vectors of one embedding, one row for each wine of each item.

    `views[view]` is (the matrix of the rows, the wine number of each row). `slugs[number]`
    is the slug of a wine. `state` is the key `embeddings` of `run.json`. Raise
    `embeddings.ConfigError` when the index gives no current vector."""

    def __init__(self, embedding, db_path):
        name = embedding.name
        directory = embeddings.entry_dir(db_path, name)
        try:
            index = embeddings.read_index(directory)
            vectors = embeddings.read_vectors(directory, index) if index else None
        except (OSError, ValueError) as exc:
            raise embeddings.ConfigError("cannot read the index of %s: %s" % (name, exc))
        if vectors is None:
            raise embeddings.ConfigError("the configuration %s has %s" % (name, NO_INDEX))
        with closing(embeddings.open_database(db_path)) as conn:
            wines, sources = embeddings.read_inputs(conn, db_path)
        items = embeddings.plan_items(embedding, sources)
        status = embeddings.item_status(items, index, embeddings.image_names(directory))
        self.slugs = [wine["slug"] for wine in wines]
        # (sha256, view) -> the numbers of the wines that show the file in that view. A
        # close-up is an item of the view `label` alone, as in `plan_items`.
        owners = collections.defaultdict(list)
        # (wine number, sha256) -> the image type of the first column of the wine with
        # that file. A file of two wines can have a different type in each wine.
        types = {}
        for number, wine in enumerate(wines):
            for image_type, digest in wine["columns"]:
                types.setdefault((number, digest), image_type)
                role = embeddings.ROLES.get(image_type)
                for view in embedding.views:
                    key = (digest, view)
                    if ((role != "label" or view == "label") and key in items
                            and number not in owners[key]):
                        owners[key].append(number)
        rows = {view: ([], [], []) for view in embedding.views}
        for key, (state, record) in status.items():
            if state != "current":
                continue
            row = record.get("row")
            if not isinstance(row, int) or not 0 <= row < len(vectors):
                raise embeddings.ConfigError("the item %s/%s of %s has no valid vector row"
                                             % (key + (name,)))
            for number in owners[key]:
                rows[key[1]][0].append(row)
                rows[key[1]][1].append(number)
                rows[key[1]][2].append({"sha256": key[0], "view": key[1],
                                        "type": types[(number, key[0])],
                                        "embedding_hash": record["embedding_hash"]})
        self.views = {view: (np.asarray(vectors[np.asarray(picked, dtype=np.int64)],
                                        dtype=np.float32),
                             np.asarray(numbers, dtype=np.int64))
                      for view, (picked, numbers, _) in rows.items() if picked}
        # view -> the item of each matrix row, and view -> wine number -> its matrix rows
        # (plan 38). `rank` records the cosine of each item of a candidate.
        self.items = {view: rows[view][2] for view in self.views}
        self.rows_of = {}
        for view, (_, numbers) in self.views.items():
            self.rows_of[view] = collections.defaultdict(list)
            for position, number in enumerate(numbers.tolist()):
                self.rows_of[view][number].append(position)
        if not self.views:
            raise embeddings.ConfigError("the index of %s holds no current vector; build it "
                                         "on /embedding" % name)
        self.dim = int(vectors.shape[1])
        counts = collections.Counter(state for state, _ in status.values())
        self.state = {
            "built_at": index.get("updated_at"),
            "index_file": "%s/%s" % (name, index.get("vectors_file")),
            "dim": self.dim,
            "items": {state: counts.get(state, 0)
                      for state in ("current", "stale", "missing", "failed")},
            "wines": {view: len(set(numbers.tolist()))
                      for view, (_, numbers) in self.views.items()},
        }

    def items_of(self, number, cosines):
        """Return the key `items` of the candidate `number` (plan 38): each current item of
        the wine, in the view order of the entry, the highest cosine first inside a view.
        `cosines` maps a view of the query to the cosine of each matrix row; an item of
        another view gets the cosine None."""
        out = []
        for view, items in self.items.items():
            found = []
            for position in self.rows_of[view].get(number, ()):
                cosine = (round(float(cosines[view][position]), 4) if view in cosines
                          else None)
                found.append(dict(items[position], cosine=cosine))
            if view in cosines:
                found.sort(key=lambda item: -item["cosine"])
            out.extend(found)
        return out

    def view_top(self, view, top, cosines, top_k):
        """Return the `top_k` wines of one view alone, the highest best cosine first (plan
        41): the slug, the cosine, and the item of the best cosine. `top` holds the best
        cosine of each wine, and `cosines` the cosine of each matrix row."""
        found = np.flatnonzero(np.isfinite(top))
        order = sorted(found.tolist(), key=lambda n: (-top[n], self.slugs[n]))[:top_k]
        out = []
        for number in order:
            position = max(self.rows_of[view][number], key=lambda p: cosines[p])
            item = self.items[view][position]
            out.append({"slug": self.slugs[number], "cosine": round(float(top[number]), 4),
                        "sha256": item["sha256"], "type": item["type"],
                        "embedding_hash": item["embedding_hash"]})
        return out

    def rank(self, query, top_k, trace=None, first=None):
        """Return the candidates of the unit vectors `query` (view -> vector). `trace` gets
        one step `search` for each view, with the top list of that view, and the step
        `score` (plan 41). `first`, when set, holds the slugs that go first: the wines of a
        shared GTIN (plan 64). The wines of `first` and the other wines each keep the score
        order, so a wine of `first` outside the normal top-k also comes back."""
        total = np.zeros(len(self.slugs))
        count = np.zeros(len(self.slugs), dtype=np.int64)
        best, cosines = {}, {}
        wanted = set(first or ())
        for view, vector in query.items():
            with _step(trace, "search", view=view) as step:
                if view not in self.views:
                    step["skipped"] = "the index holds no vector of the view %s" % view
                    continue
                matrix, numbers = self.views[view]
                top = np.full(len(self.slugs), -np.inf)
                cosines[view] = matrix @ vector
                np.maximum.at(top, numbers, cosines[view])
                found = np.isfinite(top)
                total[found] += top[found]
                count[found] += 1
                best[view] = top
                if trace is not None:
                    step["out"] = {"rows": int(len(numbers)), "wines": int(found.sum()),
                                   "top": self.view_top(view, top, cosines[view], top_k)}
        with _step(trace, "score") as step:
            present = np.flatnonzero(count)
            score = total[present] / count[present]
            order = sorted(range(len(present)),
                           key=lambda i: (self.slugs[present[i]] not in wanted, -score[i],
                                          self.slugs[present[i]]))[:top_k]
            cands = []
            for rank, i in enumerate(order, 1):
                number = present[i]
                cand = {"slug": self.slugs[number], "score": round(float(score[i]), 4),
                        "rank": rank}
                for view, top in best.items():
                    cand[view] = (round(float(top[number]), 4) if np.isfinite(top[number])
                                  else None)
                cand["items"] = self.items_of(number, cosines)
                cands.append(cand)
            step["out"] = {"wines": int(len(present))}
        return cands


class EmbeddingBackend:
    """A backend of `benchmark.run_benchmark`: `id`, `spec`, `top_k`, and `ask(path)`.
    `model` is a backend of `build_embeddings.make_backend`. `name` is the name of the
    pipeline of the run (plan 34); None means the name of the embedding entry. `views` are
    the steps of the test photo of that pipeline; None means the steps of the entry."""

    def __init__(self, embedding, catalogue, model, segmenter, top_k=DEFAULT_TOP_K,
                 name=None, views=None, scene_selection=False, dis_segmenter=None):
        if top_k < 1:
            raise ValueError("top_k MUST be 1 or more")
        self.embedding = embedding
        self.catalogue = catalogue
        self.model = model
        self.segmenter = segmenter
        self.id = name or embedding.name
        self.top_k = top_k
        # A view of the photo ranks the catalogue vectors of the same view of the entry.
        self.views = views or embedding.views
        self.scene_selection = scene_selection
        self.dis_segmenter = dis_segmenter
        # The backend `local` holds one model in the memory of this machine, so it takes
        # one request at a time.
        self._lock = threading.Lock() if embedding.backend == "local" else None
        self.spec = {
            "id": self.id, "kind": KIND, "embedding": embedding.name,
            "label": "lab pipeline %s: the embedding %s" % (self.id, embedding.name),
            "model_backend": embedding.backend,
            "url": embedding.base_url + "/embeddings" if embedding.base_url else None,
            "model": embedding.model, "extra_body": embedding.extra_body,
            "views": self.views, "top_k": top_k, "workers": 1, "score": SCORE,
            "sam3": {"endpoint": getattr(segmenter, "endpoint", None),
                     "package": main_scene.SETTINGS if scene_selection else derive.SETTINGS_SEG,
                     "package_texts": main_scene.TEXTS if scene_selection else derive.SAM3_TEXTS,
                     "label": alternatives.SETTINGS_LABEL},
        }
        if scene_selection:
            self.spec["scene_selection"] = main_scene.VERSION

    def _embed(self, images):
        if self._lock is None:
            return self.model.embed(images)
        with self._lock:
            return self.model.embed(images)

    def ask(self, path, first=None):
        """Return `(candidates, latency_ms, http_status, error, trace)`, as a real backend
        with the step trace of the photo (plan 41). `benchmark.py` writes the trace into
        the row. `first` puts these slugs first in the rank (plan 64, `Catalogue.rank`)."""
        trace = Trace()

        def ms():
            return int(round(trace.now()))

        try:
            with trace.step("input") as step:
                try:
                    image, _ = derive.open_image(path)
                except OSError as exc:
                    raise embeddings.ItemError("Pillow cannot read the photo %s: %s"
                                               % (path, exc))
                step["out"] = {"width": image.width, "height": image.height}
            cuts = cuts_of(image, cut_targets(self.views), self.segmenter, trace,
                           self.scene_selection)
            sent, missing = {}, {}
            for view, steps in self.views.items():
                with trace.step("view", view=view) as step:
                    prepared, reason = view_input(
                        image, steps, cuts, self.dis_segmenter)
                    if prepared is None:
                        missing[view] = step["skipped"] = reason
                        continue
                    data = embeddings.png_bytes(prepared)
                    sent[view] = data
                    step["out"] = {"width": prepared.width, "height": prepared.height,
                                   "bytes": len(data),
                                   "sha256": hashlib.sha256(data).hexdigest()}
            if not sent:
                raise embeddings.ItemError("no view has an input: %s" % "; ".join(
                    "%s: %s" % item for item in sorted(missing.items())))
            views = list(sent)
            with trace.step("embed") as step:
                vectors = self._embed([sent[view] for view in views])
                query = {}
                for view, vector in zip(views, vectors):
                    vector = np.asarray(vector, dtype=np.float32)
                    if vector.shape != (self.catalogue.dim,):
                        raise build_embeddings.BackendError(
                            "the model sent a vector of %d values; the index holds %d"
                            % (vector.size, self.catalogue.dim))
                    norm = float(np.linalg.norm(vector))
                    if not np.isfinite(norm) or norm == 0.0:
                        raise build_embeddings.BackendError("the model sent a vector of "
                                                            "length %s" % norm)
                    query[view] = vector / norm
                step["out"] = {"views": views, "dim": self.catalogue.dim}
            cands = self.catalogue.rank(query, self.top_k, trace, first)
            return cands, ms(), 200, None, trace.value()
        except (derive.Sam3Unavailable, embeddings.ItemError,
                build_embeddings.BackendError) as exc:
            return [], ms(), None, str(exc), trace.value()


def find_pipeline(name, config_path=embeddings.CONFIG_PATH):
    """Return (the pipeline `name` of the backend `embedding`, the path of the database).
    Raise `embeddings.ConfigError`."""
    import pipelines  # here alone: `pipelines.py` MAY import this module
    settings = pipelines.load(config_path)
    try:
        pipeline = settings.find(name)
    except KeyError:
        raise embeddings.ConfigError("config.yaml has no pipeline %s" % name)
    if pipeline.backend != pipelines.EMBEDDING_BACKEND:
        raise embeddings.ConfigError("the pipeline %s has the backend %s; this script runs "
                                     "the backend %s alone"
                                     % (name, pipeline.backend, pipelines.EMBEDDING_BACKEND))
    return pipeline, settings.db_path


def build_backend(entry, db_path, top_k=DEFAULT_TOP_K,
                  make_model=build_embeddings.make_backend, segmenter=None, name=None,
                  views=None, scene_selection=False,
                  make_dis=build_embeddings.make_dis_segmenter_for_views):
    """Return the backend of one embedding entry, for `benchmark.run_benchmark`. Raise
    `embeddings.ConfigError`. `segmenter` is the SAM3 client; None means
    `derive.SAM3_ENDPOINT`. `name` is the name of the pipeline of the run; None means the
    name of the entry. `views` are the steps of the test photo; None means the steps of
    the entry."""
    if entry.backend not in BACKENDS:
        raise embeddings.ConfigError("%s has the backend %s; the embedding runner runs %s "
                                     "alone" % (entry.name, entry.backend, " and ".join(BACKENDS)))
    catalogue = Catalogue(entry, db_path)
    model = make_model(entry)
    effective_views = views or entry.views
    dis_segmenter = make_dis(effective_views)
    return EmbeddingBackend(entry, catalogue, model,
                            Sam3Once(segmenter or derive.Sam3Client()), top_k, name, views,
                            scene_selection, dis_segmenter)


def build_pipeline_backend(pipeline, config_path, top_k=DEFAULT_TOP_K):
    """Return the backend of a pipeline of the backend `embedding` (plan 34; owner answers
    of 2026-09-26T00:12:24+0300 and 00:15:17). `pipeline.embedding` names the entry of the
    key `embeddings`, and `pipeline.name` is the id of the backend. `pipeline.views`, when
    set, holds the steps of the test photo (owner answers of 00:52:41). Raise
    `embeddings.ConfigError`: an unknown or invalid entry, a backend other than openai or
    local, or an entry with no index (`NO_INDEX`). A pipeline with the key `barcode` gets
    `barcode.CodeFirst` around the backend (plan 42). A pipeline with the key `rerank` gets
    `cluster_rerank.ClusterRerank` around the embedding backend, inside the barcode step,
    so a code hit answers first (plan 48)."""
    settings = embeddings.load_settings(config_path)
    try:
        entry = settings.find(pipeline.embedding)
    except KeyError:
        raise embeddings.ConfigError("the pipeline %s names the embedding %s, which "
                                     "config.yaml does not hold"
                                     % (pipeline.name, pipeline.embedding))
    backend = build_backend(entry, settings.db_path, top_k, name=pipeline.name,
                            views=getattr(pipeline, "views", None), scene_selection=True)
    backend.spec["workers"] = getattr(pipeline, "workers", 1)
    if getattr(pipeline, "rerank", None) is not None:
        import cluster_rerank  # noqa: E402  (plan 48, on demand)
        backend = cluster_rerank.ClusterRerank(backend, pipeline.rerank, pipeline.embedding,
                                               config_path, settings.db_path)
    if getattr(pipeline, "barcode", None) is not None:
        import barcode  # noqa: E402  (HTTP scanner, on demand)
        backend = barcode.CodeFirst(backend, pipeline.barcode, settings.db_path,
                                    scanner=getattr(pipeline, "scanner", None))
    return backend


def model_inputs(spec, path, candidates=None):
    """Return `{"inputs", "notes"}` of one photo of a run of `kind: embedding`: the model
    input of each view, made again with the steps of `spec` (the key `backend` of
    `run.json`) and the SAM3 answers of the cache. No request goes to SAM3 or to the
    model. Each input has the keys of `/api/run-inputs` (docs/API.md). `candidates` are
    the candidates of the row; a first candidate with the key `code` is an answer of the
    code lookup (plan 42), so the photo has no model input."""
    first = (candidates or [None])[0]
    if isinstance(first, dict) and first.get("code"):
        import barcode  # noqa: E402  (the note alone; no scanner call)
        return {"inputs": [], "notes": [barcode.answer_note(first)]}
    views = spec.get("views") or {}
    endpoint = (spec.get("sam3") or {}).get("endpoint") or derive.SAM3_ENDPOINT
    try:
        image, _ = derive.open_image(path)
        dis_segmenter = build_embeddings.make_dis_segmenter_for_views(views)
        inputs, missing = query_inputs(image, views, CachedSam3(endpoint),
                                       bool(spec.get("scene_selection")), dis_segmenter)
    except (OSError, ImportError, ValueError, derive.Sam3Unavailable,
            embeddings.ItemError) as exc:
        return {"inputs": [], "notes": ["The model input cannot be made again: %s" % exc]}
    items = []
    for view, prepared in inputs.items():
        data = embeddings.png_bytes(prepared)
        items.append({"sha256": hashlib.sha256(data).hexdigest(), "uses": ["Embedding"],
                      "pipelines": [view], "label": view, "model": spec.get("model"),
                      "width": prepared.width, "height": prepared.height,
                      "mime": "image/png", "src": build_embeddings.data_uri(data)})
    notes = ["The view %s has no input: %s." % item for item in sorted(missing.items())]
    return {"inputs": items, "notes": notes}


OLD_RUN_NOTE = ("This run recorded no cosine of each item, because it ran before plan 38. "
                "The items are the items of this wine in the present index.")


def _index_items(db_path, slug, present, order):
    """Return the items of the wine `slug` in the present index, for a run with no key
    `items`: the cosine None and the state `current`. `present` maps (sha256, view) to
    the record of the index; `order` is the view order of the entry."""
    with closing(embeddings.open_database(db_path)) as conn:
        wines, _sources = embeddings.read_inputs(conn, db_path)
    wine = next((w for w in wines if w["slug"] == slug), None)
    columns, seen = [], set()
    for image_type, digest in (wine or {}).get("columns", ()):
        if digest not in seen:
            seen.add(digest)
            columns.append((image_type, digest))
    return [{"sha256": digest, "view": view, "type": image_type,
             "embedding_hash": present[(digest, view)]["embedding_hash"], "cosine": None,
             "state": "current"}
            for view in order for image_type, digest in columns if (digest, view) in present]


def candidate_items(spec, cand, db_path):
    """Return `{"score", "views", "items", "notes"}` of one candidate of a run of
    `kind: embedding` (plan 38). `spec` is the key `backend` of `run.json`. The items are
    the key `items` of the candidate, with `best`, `state`, `url`, `width`, and `height`.
    `state` `same` means that the present index holds the item with the hash of the run,
    so `url` names the PNG that went to the model. `changed` and `gone` get no URL. A run
    with no key `items` gets the items of the present index and a note. A candidate of the
    code lookup (the key `code`, plan 42) gets no item and one note."""
    import embedding_routes  # here alone: the URL of a prepared image
    if cand.get("code"):
        import barcode  # noqa: E402  (the note alone; no scanner call)
        return {"score": cand.get("score"), "views": {}, "items": [],
                "notes": [barcode.candidate_note(cand)]}
    name = spec.get("embedding")
    notes, index = [], {}
    if not name:
        return {"score": cand.get("score"), "views": {}, "items": [],
                "notes": ["run.json names no embedding entry."]}
    try:
        directory = embeddings.entry_dir(db_path, name)
        index = embeddings.read_index(directory) or {}
        names = embeddings.image_names(directory)
    except (OSError, ValueError) as exc:
        names = set()
        notes.append("Cannot read the index of %s: %s." % (name, exc))
    present = {(record["source_sha256"], record["view"]): record
               for record in index.get("items", [])}
    query_views = [view for view in spec.get("views") or {} if view in cand]
    best = {view: cand.get(view) for view in query_views}
    if isinstance(cand.get("items"), list):
        items = []
        for item in cand["items"]:
            record = present.get((item["sha256"], item["view"]))
            if record is None or embeddings.image_name(item["sha256"], item["view"]) not in names:
                state = "gone"
            elif record["embedding_hash"] != item["embedding_hash"]:
                state = "changed"
            else:
                state = "same"
            items.append(dict(item, state=state))
        if any(item["state"] != "same" for item in items):
            notes.append("The index of %s changed after the run. An item with no image has "
                         "another input now, or no input." % name)
    else:
        order = list((index.get("config") or {}).get("views") or {})
        try:
            items = _index_items(db_path, cand.get("slug"), present, order)
        except (sqlite3.Error, embeddings.ConfigError) as exc:
            items = []
            notes.append("Cannot read the images of the wine: %s." % exc)
        notes.insert(0, OLD_RUN_NOTE)
    for item in items:
        record = present.get((item["sha256"], item["view"]))
        shown = item["state"] in ("same", "current")
        item["best"] = item["cosine"] is not None and item["cosine"] == best.get(item["view"])
        item["url"] = (embedding_routes.image_url(name, item["sha256"], item["view"],
                                                  item["embedding_hash"]) if shown else None)
        item["width"] = record.get("width") if shown else None
        item["height"] = record.get("height") if shown else None
    unused = sorted({item["view"] for item in items} - set(query_views))
    if unused:
        notes.append("The query has no view %s, so the run did not compare these items."
                     % " and no view ".join(unused))
    return {"score": cand.get("score"), "views": best, "items": items, "notes": notes}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Make one run of a pipeline of the backend embedding of config.yaml on "
                    "one test set, and write the run files.")
    parser.add_argument("--name", required=True,
                        help="the name of a pipeline of the backend embedding")
    parser.add_argument("--set", required=True, dest="set_name", help="the test set, for example my")
    parser.add_argument("--workers", type=int, default=None,
                        help="photos at a time; the default is 1")
    parser.add_argument("--limit", type=int, default=None, help="send the first N queries alone")
    parser.add_argument("--label", default=None, help="a suffix of the run id")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K,
                        help="the candidates of each photo")
    parser.add_argument("--config", default=embeddings.CONFIG_PATH, help="path of config.yaml")
    parser.add_argument("--runs-dir", default=benchmark.RUNS_DIR, help="the directory of the runs")
    args = parser.parse_args(argv)
    for value, what in ((args.workers, "--workers"), (args.limit, "--limit"),
                        (args.top_k, "--top-k")):
        if value is not None and value < 1:
            parser.error("%s MUST be 1 or more" % what)

    def log(message):
        print(message, flush=True)

    try:
        pipeline, db_path = find_pipeline(args.name, args.config)
        rebuild_on_run.before_run(pipeline, args.config, log)  # plan 59
        backend = build_pipeline_backend(pipeline, args.config, args.top_k)
        items = backend.catalogue.state["items"]
        log("index %s: %d current items; %d stale, %d missing, %d failed items stay out"
            % (backend.catalogue.state["index_file"], items["current"], items["stale"],
               items["missing"], items["failed"]))
        run_dir, met = benchmark.run_benchmark(
            db_path, args.set_name, backend, args.runs_dir, workers=args.workers,
            limit=args.limit, label=args.label, embeddings=backend.catalogue.state,
            log=log, configuration=pipeline.name)
    except ImportError as exc:
        print("error: %s; the backend local needs the packages of requirements-local.txt: "
              "run the script with embedding_python" % exc, file=sys.stderr)
        return 1
    except (benchmark.BenchmarkError, embeddings.ConfigError, build_embeddings.BackendError,
            match_backends.BackendError, labdb.SchemaError, sqlite3.Error, OSError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    pos = met["positive"]
    print("positive: %d, recall@1 %s, recall@5 %s, mrr %s" % (
        pos["n"], pos["recall_at_1"], pos["recall_at_5"], pos["mrr"]))
    print("negative: %d, false match at 1: %d" % (
        met["negative"]["n"], met["negative"]["false_match_at_1"]))
    print("run: %s" % run_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
