"""Build one embedding of `config.yaml`: prepare each input image, get its vector, and
write the files of `data/embeddings/<name>/`.

The build writes one JSON object per line to stdout: `start`, `progress`,
`item_failed`, `stopping`, and at the end `done`, `stopped`, or `error`. The lab server
sends stdout to `build.log` and shows the progress on the Embeddings page.

A second start does nothing for an item whose embedding hash did not change and whose
prepared image exists. SIGTERM and SIGINT stop the build after the present batch. The
finished items stay, and the next start continues with the rest. A checkpoint writes
the vectors and `index.json` every 30 s, at a stop, and at the end.

Exit codes: 0 the build ended or stopped; 1 a fatal error; 2 a configuration error;
3 another build of the same embedding runs.

Read docs/plans/10_embeddings-page.md.

Usage:
    python pipeline/build_embeddings.py --name gx10-siglip2-so400m-patch16-naflex-p256
"""
import argparse
import base64
import io
import json
import os
import platform
import signal
import socket
import sys
import time
import traceback
from contextlib import closing

import numpy as np
import requests
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import embeddings  # noqa: E402

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


class Stop:
    """The signal handler of SIGTERM and SIGINT. The build stops after the present
    batch."""

    def __init__(self):
        self.requested = False

    def __call__(self, signum, frame):
        if not self.requested:
            self.requested = True
            emit("stopping", signal=signal.Signals(signum).name)


def run(embedding, db_path, directory, make_backend=make_backend, stop=None,
        checkpoint_seconds=CHECKPOINT_SECONDS):
    """Build one embedding. Return the counts of the build."""
    stop = stop or Stop()
    started = time.monotonic()
    with closing(embeddings.open_database(db_path)) as conn:
        _, sources = embeddings.read_inputs(conn, db_path)
    items = embeddings.plan_items(embedding, sources)
    images_dir = os.path.join(directory, embeddings.IMAGES)
    os.makedirs(images_dir, exist_ok=True)
    try:
        index = embeddings.read_index(directory) or {}
        vectors = embeddings.read_vectors(directory, index)
    except (ValueError, OSError) as exc:
        emit("warning", message="the old index cannot be read, so each item is built "
                                "again: %s" % exc)
        index, vectors = {}, None
    status = embeddings.item_status(items, index, embeddings.image_names(directory))

    # The vectors that stay: the current items, and the stale items until the build
    # replaces them.
    kept = {}
    pruned = 0
    for record in index.get("items", []):
        key = (record["source_sha256"], record["view"])
        if key in items:
            if vectors is not None and isinstance(record.get("row"), int):
                kept[key] = (record, vectors[record["row"]])
            continue
        pruned += 1
        try:
            os.remove(os.path.join(images_dir, embeddings.image_name(*key)))
        except FileNotFoundError:
            pass
    failures = {key: record for key, (state, record) in status.items() if state == "failed"}
    todo = [key for key, (state, _) in status.items() if state != "current"]
    current = len(items) - len(todo)
    dim = index.get("dim") if kept else None
    software = {"python": platform.python_version(), "numpy": np.__version__,
                "pillow": Image.__version__}
    counts = {"built": 0, "failed": 0, "done": 0}

    def fail(key, error):
        item = items[key]
        failures[key] = {"source_sha256": key[0], "view": key[1], "role": item["role"],
                         "embedding_hash": item["embedding_hash"], "error": error}
        counts["failed"] += 1
        emit("item_failed", source_sha256=key[0], view=key[1], error=error)

    def checkpoint():
        order = [key for key in items if key in kept
                 and (dim is None or len(kept[key][1]) == dim)]
        records = [dict(kept[key][0], row=row) for row, key in enumerate(order)]
        matrix = (np.vstack([kept[key][1] for key in order]) if order
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

    emit("start", name=embedding.name, pid=os.getpid(), items=len(items), current=current,
         todo=len(todo), pruned=pruned)
    backend = None
    if todo:
        backend = make_backend(embedding)
        software.update(backend.software())
    last_checkpoint = time.monotonic()
    position = 0
    while position < len(todo) and not stop.requested:
        batch = todo[position:position + embedding.batch_size]
        position += len(batch)
        ready = []
        for key in batch:
            item = items[key]
            try:
                image = embeddings.prepare(item, sources[key[0]]["path"])
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
                        (vector / norm).astype(np.float32))
                    failures.pop(key, None)
                    counts["built"] += 1
        counts["done"] += len(batch)
        emit("progress", done=counts["done"], todo=len(todo), built=counts["built"],
             failed=counts["failed"])
        if time.monotonic() - last_checkpoint >= checkpoint_seconds:
            checkpoint()
            last_checkpoint = time.monotonic()
    checkpoint()
    seconds = round(time.monotonic() - started, 1)
    counts.update(current=current, pruned=pruned, todo=len(todo), seconds=seconds)
    if position < len(todo):
        emit("stopped", **counts)
    else:
        emit("done", **counts)
    return counts


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build one embedding of config.yaml.")
    parser.add_argument("--name", required=True, help="the name of the entry")
    parser.add_argument("--config", default=embeddings.CONFIG_PATH, help="path of config.yaml")
    args = parser.parse_args(argv)
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
        run(embedding, settings.db_path, directory, stop=stop)
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
