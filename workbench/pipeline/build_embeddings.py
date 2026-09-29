"""Build one embedding of `config.yaml`: prepare each input image, get its vector, and
write the files of `data/catalog/embeddings/<name>/`.

The build writes one JSON object per line to stdout: `start`, `progress`,
`item_failed`, `stopping`, and at the end `done`, `stopped`, or `error`. The lab server
sends stdout to `build.log` and shows the progress on the Embeddings page.

A second start does nothing for an item whose embedding hash did not change and whose
prepared image exists. SIGTERM and SIGINT stop the build after the present batch. The
finished items stay, and the next start continues with the rest. A checkpoint writes
the vectors and `index.json` every 30 s (longer for a large index: 20 times the time of
the last checkpoint), at a stop, and at the end.

An entry with `rotation_step` (plan 82) has one vector for each angle of the view `full`.
`--workers N` builds N such items at a time.

Exit codes: 0 the build ended or stopped; 1 a fatal error; 2 a configuration error;
3 another build of the same embedding runs.

Read docs/plans/10_embeddings-page.md.

Usage:
    python pipeline/build_embeddings.py --name gx10-siglip2-so400m-patch16-naflex-p256
    python pipeline/build_embeddings.py --name gx10-siglip2-so400m-patch16-naflex-p512-rot5 --workers 6
"""
import argparse
import base64
import concurrent.futures
import io
import json
import os
import platform
import signal
import socket
import sys
import threading
import time
import traceback
from contextlib import closing

import numpy as np
import requests
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import embeddings  # noqa: E402
import dis_litert  # noqa: E402

TIMEOUT = 300           # s; a cold start of a gateway model takes up to about 48 s
RETRY_WAITS = (2, 4, 8)  # s; the waits after HTTP 429, HTTP 5xx, or no answer
CHECKPOINT_SECONDS = 30


class BackendError(Exception):
    """The model gave no vectors for a batch."""


def emit(event, **values):
    """Write one event line to stdout."""
    values = dict(event=event, **values)
    values.setdefault("time", embeddings.now())
    values.setdefault("t", round(time.time(), 3))
    print(json.dumps(values, ensure_ascii=False), flush=True)


def data_uri(png):
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


class OpenAIBackend:
    """`POST <base_url>/embeddings` with PNG data URIs, as the OpenAI API does."""

    def __init__(self, embedding, session=None, timeout=TIMEOUT, waits=RETRY_WAITS,
                 sleep=time.sleep):
        self.url = embedding.base_url + "/embeddings"
        self.model = embedding.model
        self.extra_body = embedding.extra_body
        self.session = session or requests.Session()
        self.timeout = timeout
        self.waits = waits
        self.sleep = sleep

    def software(self):
        return {"endpoint": self.url}

    def embed(self, images):
        """Return the vectors of a list of PNG files as an array N x dim."""
        body = dict(self.extra_body, model=self.model, input=[data_uri(png) for png in images])
        last = None
        for attempt in range(len(self.waits) + 1):
            try:
                response = self.session.post(self.url, json=body, timeout=self.timeout)
            except requests.RequestException as exc:
                last = "no answer from %s: %s" % (self.url, exc)
            else:
                if response.status_code == 200:
                    return self._vectors(response, len(images))
                last = "HTTP %d from %s: %s" % (response.status_code, self.url,
                                                response.text.strip()[:300])
                if response.status_code != 429 and response.status_code < 500:
                    raise BackendError(last)
            if attempt < len(self.waits):
                # The job row of the Embeddings page shows this line while it waits.
                emit("retry", attempt=attempt + 1, wait=self.waits[attempt], error=last)
                self.sleep(self.waits[attempt])
        raise BackendError(last)

    def _vectors(self, response, count):
        try:
            data = response.json()["data"]
            if all(isinstance(row.get("index"), int) for row in data):
                data = sorted(data, key=lambda row: row["index"])
            vectors = np.asarray([row["embedding"] for row in data], dtype=np.float32)
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise BackendError("the answer of %s is not an embedding list: %s" % (self.url, exc))
        if vectors.ndim != 2 or vectors.shape[0] != count:
            raise BackendError("%s sent %s vectors for %d images"
                               % (self.url, vectors.shape, count))
        return vectors


class LocalBackend:
    """A Hugging Face model on this machine: `mps` when it is available, else `cpu`."""

    def __init__(self, embedding):
        import torch
        import transformers
        from transformers import AutoImageProcessor, AutoModel

        self.torch = torch
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.processor = AutoImageProcessor.from_pretrained(embedding.model)
        self.model = AutoModel.from_pretrained(embedding.model, dtype=torch.float32)
        self.model = self.model.to(self.device).eval()
        self.extra = dict(embedding.extra_body)
        self.versions = {"torch": torch.__version__, "transformers": transformers.__version__,
                         "device": self.device}

    def software(self):
        return dict(self.versions)

    def embed(self, images):
        torch = self.torch
        pictures = [Image.open(io.BytesIO(png)).convert("RGB") for png in images]
        try:
            with torch.inference_mode():
                inputs = self.processor(images=pictures, return_tensors="pt", **self.extra)
                inputs = inputs.to(self.device)
                out = self.model.get_image_features(**inputs)
                if not torch.is_tensor(out):
                    out = out.pooler_output
                return out.float().cpu().numpy()
        except (RuntimeError, ValueError, TypeError) as exc:
            raise BackendError("the local model failed: %s: %s" % (type(exc).__name__, exc))


def make_backend(embedding):
    if embedding.backend == "openai":
        return OpenAIBackend(embedding)
    return LocalBackend(embedding)


def make_dis_segmenter_for_views(views):
    """Return one DIS runtime when `views` use `segment_dis`."""
    specs = [step for steps in views.values() for step in steps
             if step["step"] == "segment_dis"]
    if not specs:
        return None
    identities = {(step["model"], step["revision"]) for step in specs}
    if len(identities) != 1:
        raise embeddings.ConfigError("all segment_dis steps MUST use one model and revision")
    model, revision = identities.pop()
    return dis_litert.Segmenter(model, revision)


def make_dis_segmenter(embedding):
    """Return one DIS runtime when the embedding uses `segment_dis`."""
    return make_dis_segmenter_for_views(embedding.views)


class Stop:
    """The signal handler of SIGTERM and SIGINT. The build stops after the present
    batch."""

    def __init__(self):
        self.requested = False

    def __call__(self, signum, frame):
        if not self.requested:
            self.requested = True
            emit("stopping", signal=signal.Signals(signum).name)


def _chunks(values, size):
    """Split `values` into near-equal chunks of about `size` values. No chunk holds one
    value when there are two values or more (plan 82: no request holds one image alone;
    NaFlex p256 gives another vector for one image)."""
    count = max(1, -(-len(values) // size))
    while count > 1 and len(values) // count < 2:
        count -= 1
    base, extra = divmod(len(values), count)
    out, start = [], 0
    for number in range(count):
        stop = start + base + (1 if number < extra else 0)
        out.append(values[start:stop])
        start = stop
    return out


def _rotated_pngs(item, source_path):
    """Return (the PNG bytes of each angle, the size of the 0° image) of one rotated item
    (plan 82). With more than one worker, a worker process calls it: the rotation and the
    PNG encoding hold the GIL. Raise embeddings.ItemError."""
    images = embeddings.rotated_inputs(item, source_path, item["angles"])
    return [embeddings.png_bytes(image) for image in images], images[0].size


def run(embedding, db_path, directory, make_backend=make_backend,
        make_dis=make_dis_segmenter, stop=None,
        checkpoint_seconds=CHECKPOINT_SECONDS, workers=1):
    """Build one embedding. Return the counts of the build.

    An item with one vector goes to the model in batches of `batch_size` items. An item
    with `angles` (an entry with `rotation_step`, plan 82) has one vector for each angle:
    `workers` such items go at a time, each in requests of about `batch_size` images."""
    stop = stop or Stop()
    started = time.monotonic()
    with closing(embeddings.open_database(db_path)) as conn:
        wines, sources = embeddings.read_inputs(conn, db_path)
    # source sha256 -> the wines that use the file, in import order. `item_failed` names
    # them, so the log shows which wine has the failed image.
    users = {}
    for wine in wines:
        for image_type, digest in wine["columns"]:
            users.setdefault(digest, []).append((wine, image_type))
    items = embeddings.plan_items(embedding, sources)
    images_dir = os.path.join(directory, embeddings.IMAGES)
    os.makedirs(images_dir, exist_ok=True)
    try:
        index = embeddings.read_index(directory) or {}
        vectors = embeddings.read_vectors(directory, index, strict=False)
    except (ValueError, OSError) as exc:
        emit("warning", message="the old index cannot be read, so each item is built "
                                "again: %s" % exc)
        index, vectors = {}, None
    status = embeddings.item_status(items, index, embeddings.image_names(directory))

    # The vectors that stay: the current items, and the stale items until the build
    # replaces them. Each value is a matrix: one row, or one row for each angle (plan 82).
    kept = {}
    pruned = 0
    taken = np.zeros(len(vectors) if vectors is not None else 0, dtype=bool)
    for record in index.get("items", []):
        key = (record["source_sha256"], record["view"])
        if key in items:
            if vectors is not None:
                try:
                    rows = embeddings.record_rows(record, len(vectors))
                except ValueError:
                    continue  # a record with no valid rows; its item is built again
                if (status[key][0] == "current" and embeddings.record_angles(record)
                        != items[key].get("angles", [0])):
                    continue  # the hash is current, the rows are not; build it again
                if taken[rows].any():
                    continue  # rows that an earlier record uses; the item is built again
                taken[rows] = True
                kept[key] = (record, vectors[rows])
            continue
        pruned += 1
        try:
            os.remove(os.path.join(images_dir, embeddings.image_name(*key)))
        except FileNotFoundError:
            pass
    failures = {key: record for key, (state, record) in status.items() if state == "failed"}
    todo = [key for key, (state, _) in status.items() if state != "current"]
    plain = [key for key in todo if "angles" not in items[key]]
    rotated = [key for key in todo if "angles" in items[key]]
    current = len(items) - len(todo)
    dim = index.get("dim") if kept else None
    software = {"python": platform.python_version(), "numpy": np.__version__,
                "pillow": Image.__version__}
    counts = {"built": 0, "failed": 0, "done": 0}
    if rotated:
        counts["vectors"] = 0

    def fail(key, error):
        item = items[key]
        failures[key] = {"source_sha256": key[0], "view": key[1], "role": item["role"],
                         "embedding_hash": item["embedding_hash"], "error": error}
        counts["failed"] += 1
        (wine, image_type), *others = users[key[0]]
        names = dict(wine=wine["slug"], name=wine["name"], image_type=image_type)
        if others:
            names["other_wines"] = [other["slug"] for other, _ in others]
        emit("item_failed", source_sha256=key[0], view=key[1], **names, error=error)

    def checkpoint():
        order = [key for key in items if key in kept
                 and (dim is None or kept[key][1].shape[1] == dim)]
        records, blocks, offset = [], [], 0
        for key in order:
            record, block = kept[key]
            record = dict(record, row=offset)
            if block.shape[0] == 1:
                record.pop("angles", None)
            elif len(record.get("angles") or ()) != block.shape[0]:
                raise AssertionError("the item %s/%s has %d vector rows and the angles %r"
                                     % (key + (block.shape[0], record.get("angles"))))
            records.append(record)
            blocks.append(block)
            offset += block.shape[0]
        matrix = (np.vstack(blocks) if blocks
                  else np.zeros((0, dim or 0), dtype=np.float32))
        embeddings.write_checkpoint(directory, {
            "name": embedding.name,
            "config": embedding.summary(),
            "steps_version": embeddings.STEPS_VERSION,
            "view_config_hash": {view: embedding.view_config_hash(view)
                                 for view in embedding.views},
            "dim": dim,
            "updated_at": embeddings.now(),
            "host": socket.gethostname(),
            "software": software,
            "items": records,
            "failures": [failures[key] for key in items if key in failures],
        }, matrix)

    timer = {"last": time.monotonic(), "seconds": 0.0}

    def maybe_checkpoint():
        # A large index takes seconds to write, so the interval grows with the write time.
        wait = max(checkpoint_seconds, 20 * timer["seconds"])
        if time.monotonic() - timer["last"] >= wait:
            begun = time.monotonic()
            checkpoint()
            timer["last"] = time.monotonic()
            timer["seconds"] = timer["last"] - begun

    emit("start", name=embedding.name, pid=os.getpid(), items=len(items), current=current,
         todo=len(todo), pruned=pruned)
    backend = None
    dis_segmenter = None
    if todo:
        dis_segmenter = make_dis(embedding)
        if dis_segmenter is not None:
            software.update(dis_segmenter.software())
        backend = make_backend(embedding)
        software.update(backend.software())
    position = 0
    while position < len(plain) and not stop.requested:
        batch = plain[position:position + embedding.batch_size]
        position += len(batch)
        ready = []
        for key in batch:
            item = items[key]
            try:
                image = embeddings.prepare(
                    item, sources[key[0]]["path"], dis_segmenter=dis_segmenter)
                png = embeddings.png_bytes(image)
                embeddings.write_atomic(
                    os.path.join(images_dir, embeddings.image_name(*key)), png)
            except embeddings.ItemError as exc:
                fail(key, str(exc))
                continue
            except OSError as exc:
                fail(key, "cannot write the prepared image: %s" % exc)
                continue
            ready.append((key, png, image.size))
        if ready:
            # The job row shows `waiting for the model` until the next line. A cold start
            # of a gateway model takes up to about 48 s.
            emit("request", images=len(ready))
            try:
                result = backend.embed([png for _, png, _ in ready])
            except BackendError as exc:
                for key, _, _ in ready:
                    fail(key, str(exc))
            else:
                for (key, _, size), vector in zip(ready, result):
                    if dim is None:
                        dim = len(vector)
                    if len(vector) != dim:
                        fail(key, "the vector has %d dimensions; the others have %d"
                             % (len(vector), dim))
                        continue
                    norm = float(np.linalg.norm(vector))
                    if not np.isfinite(norm) or norm == 0.0:
                        fail(key, "the model sent a vector of length %s" % norm)
                        continue
                    item = items[key]
                    kept[key] = ({
                        "source_sha256": key[0], "view": key[1], "role": item["role"],
                        "embedding_hash": item["embedding_hash"],
                        "derivative_sha256": item["cut"]["sha256"] if item["cut"] else None,
                        "image": "%s/%s" % (embeddings.IMAGES, embeddings.image_name(*key)),
                        "width": size[0], "height": size[1]},
                        (vector / norm).astype(np.float32)[None, :])
                    failures.pop(key, None)
                    counts["built"] += 1
        counts["done"] += len(batch)
        emit("progress", done=counts["done"], todo=len(todo), built=counts["built"],
             failed=counts["failed"])
        maybe_checkpoint()

    # Plan 82: the items of a rotated view, one vector for each angle.
    local = threading.local()

    def embed_rotated(key, prep, own_backend):
        """Return (the 0° PNG, its size, the vectors) of one rotated item. A worker
        thread runs it; the main thread records the result."""
        item = items[key]
        path = sources[key[0]]["path"]
        if prep is None:
            pngs, size = _rotated_pngs(item, path)
        else:
            pngs, size = prep.submit(_rotated_pngs, item, path).result()
        if own_backend is None:
            if not hasattr(local, "backend"):
                local.backend = make_backend(embedding)
            own_backend = local.backend
        got = []
        for chunk in _chunks(pngs, embedding.batch_size):
            got.extend(own_backend.embed(chunk))
        return pngs[0], size, got

    def finish_rotated(key, outcome):
        nonlocal dim
        counts["done"] += 1
        if isinstance(outcome, BaseException):
            fail(key, str(outcome) if isinstance(outcome, (embeddings.ItemError, BackendError))
                 else "%s: %s" % (type(outcome).__name__, outcome))
            return
        png, size, got = outcome
        item = items[key]
        matrix = np.asarray(got, dtype=np.float32)
        if matrix.ndim != 2 or matrix.shape[0] != len(item["angles"]):
            fail(key, "the model sent %s vectors for %d angles"
                 % (matrix.shape, len(item["angles"])))
            return
        if dim is None:
            dim = matrix.shape[1]
        if matrix.shape[1] != dim:
            fail(key, "the vector has %d dimensions; the others have %d"
                 % (matrix.shape[1], dim))
            return
        norms = np.linalg.norm(matrix, axis=1)
        if not np.all(np.isfinite(norms)) or np.any(norms == 0.0):
            fail(key, "the model sent a vector of length 0 or not finite")
            return
        try:
            embeddings.write_atomic(
                os.path.join(images_dir, embeddings.image_name(*key)), png)
        except OSError as exc:
            fail(key, "cannot write the prepared image: %s" % exc)
            return
        kept[key] = ({
            "source_sha256": key[0], "view": key[1], "role": item["role"],
            "embedding_hash": item["embedding_hash"],
            "derivative_sha256": item["cut"]["sha256"] if item["cut"] else None,
            "image": "%s/%s" % (embeddings.IMAGES, embeddings.image_name(*key)),
            "width": size[0], "height": size[1], "angles": list(item["angles"])},
            (matrix / norms[:, None]).astype(np.float32))
        failures.pop(key, None)
        counts["built"] += 1
        counts["vectors"] += len(item["angles"])

    def rotated_progress():
        emit("progress", done=counts["done"], todo=len(todo), built=counts["built"],
             failed=counts["failed"], vectors=counts["vectors"])
        maybe_checkpoint()

    finished = 0
    if rotated and position >= len(plain) and not stop.requested:
        if workers <= 1:
            for key in rotated:
                if stop.requested:
                    break
                emit("request", images=len(items[key]["angles"]))
                try:
                    outcome = embed_rotated(key, None, backend)
                except Exception as exc:  # noqa: BLE001 - one item MUST NOT stop the build
                    outcome = exc
                finish_rotated(key, outcome)
                finished += 1
                rotated_progress()
        else:
            queue = iter(rotated)
            with concurrent.futures.ProcessPoolExecutor(workers) as prep, \
                    concurrent.futures.ThreadPoolExecutor(workers) as pool:
                pending = {}

                def submit_next():
                    key = next(queue, None)
                    if key is None:
                        return
                    emit("request", images=len(items[key]["angles"]))
                    pending[pool.submit(embed_rotated, key, prep, None)] = key

                for _ in range(workers):
                    if not stop.requested:
                        submit_next()
                while pending:
                    done_now, _ = concurrent.futures.wait(
                        pending, return_when=concurrent.futures.FIRST_COMPLETED)
                    for future in done_now:
                        key = pending.pop(future)
                        try:
                            outcome = future.result()
                        except Exception as exc:  # noqa: BLE001 - one item MUST NOT stop
                            outcome = exc
                        finish_rotated(key, outcome)
                        finished += 1
                        rotated_progress()
                        if not stop.requested:
                            submit_next()
    checkpoint()
    seconds = round(time.monotonic() - started, 1)
    counts.update(current=current, pruned=pruned, todo=len(todo), seconds=seconds)
    if position < len(plain) or finished < len(rotated):
        emit("stopped", **counts)
    else:
        emit("done", **counts)
    return counts


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build one embedding of config.yaml.")
    parser.add_argument("--name", required=True, help="the name of the entry")
    parser.add_argument("--config", default=embeddings.CONFIG_PATH, help="path of config.yaml")
    parser.add_argument("--workers", type=int, default=1,
                        help="rotated items at a time (plan 82); the default is 1")
    args = parser.parse_args(argv)
    if args.workers < 1:
        parser.error("--workers MUST be 1 or more")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)

    try:
        settings = embeddings.load_settings(args.config)
        embedding = settings.find(args.name)
    except KeyError:
        emit("error", message="config.yaml has no embedding %s" % args.name)
        return 2
    except embeddings.ConfigError as exc:
        emit("error", message=str(exc))
        return 2
    directory = embeddings.entry_dir(settings.db_path, embedding.name)
    os.makedirs(directory, exist_ok=True)
    try:
        embeddings.acquire_lock(directory)
    except embeddings.Busy as exc:
        emit("error", message=str(exc))
        return 3
    stop = Stop()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        run(embedding, settings.db_path, directory, stop=stop, workers=args.workers)
    except embeddings.ConfigError as exc:
        emit("error", message=str(exc))
        return 2
    except Exception as exc:  # noqa: BLE001 - the page shows each fatal error
        traceback.print_exc()
        emit("error", message="%s: %s" % (type(exc).__name__, exc))
        return 1
    finally:
        embeddings.release_lock(directory)
    return 0


if __name__ == "__main__":
    sys.exit(main())
