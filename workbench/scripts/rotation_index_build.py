#!/usr/bin/env python3
"""Build rotated catalogue vectors of one embedding entry, outside the lab index.

Owner message of 2026-09-29T02:02:13+0300 and the answers of 07:06:38 (separate scripts,
the 5° sets first). For each current item of the view `full` of the entry, the script
takes the SAM3 cut of the package on white (the steps `segment`, `remove_background`,
`white_background`), rotates it counter-clockwise by each angle of `--angles`, and applies
the fixed scale of the `resize` step of the 0° image, as `scripts/rotation_similarity.py`
does: the canvas grows, and the package keeps the pixel size of the index image. At 0°
the image is the index image (the script checks the pixels against the stored PNG).

The vectors go to `<out>/<entry>/vectors/<source sha256>.npz` (`angles`, `vectors`: one
L2-normalised float32 row for each angle). A later run adds only the missing angles, so
the script resumes after a stop, and a run with more angles (the 1° sets) extends the
files. The script writes no prepared PNG and does not change the lab index or config.yaml.

    python3 scripts/rotation_index_build.py --angles 0:355:5
    python3 scripts/rotation_index_build.py --angles 0:355:5 --limit 10   # a probe
"""

import argparse
import concurrent.futures
import json
import os
import sys
import tempfile
import time

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rotation_multiref  # noqa: E402
import rotation_similarity as rs  # noqa: E402  (it adds pipeline/ to sys.path)
from rotation_similarity import build_embeddings, embeddings  # noqa: E402

ENTRY = "gx10-siglip2-so400m-patch16-naflex-p512"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "work", "rotation-index")
WHITE = (255, 255, 255)


def parse_angles(specs):
    """"start:end:step" specs -> the sorted union of the angles below 360°."""
    angles = set()
    for spec in specs:
        start, end, step = (int(part) for part in spec.split(":"))
        angles.update(angle for angle in range(start, end + 1, step) if angle < 360)
    return sorted(angles)


def png_fast(image, level):
    """PNG with a low compression level: the pixels are the same, the encoding is faster."""
    import io
    buffer = io.BytesIO()
    image.save(buffer, "PNG", compress_level=level)
    return buffer.getvalue()


def current_full_items(embedding, db_path):
    """Return (sources, items, index, vectors, directory) of the current `full` items."""
    directory = embeddings.entry_dir(db_path, embedding.name)
    index = embeddings.read_index(directory)
    vectors = embeddings.read_vectors(directory, index)
    conn = embeddings.open_database(db_path)
    try:
        wines, sources = embeddings.read_inputs(conn, db_path)
    finally:
        conn.close()
    items = embeddings.plan_items(embedding, sources)
    status = embeddings.item_status(items, index, embeddings.image_names(directory))
    chosen = {key: record for key, (state, record) in status.items()
              if key[1] == "full" and state == "current"}
    return sources, items, chosen, vectors, directory


def load_saved(path):
    try:
        with np.load(path) as saved:
            return [int(angle) for angle in saved["angles"]], saved["vectors"]
    except FileNotFoundError:
        return [], None


def save_atomic(path, angles, vectors):
    fd, temporary = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp-", suffix=".npz")
    os.close(fd)
    try:
        np.savez(temporary, angles=np.asarray(angles, dtype=np.int16),
                 vectors=np.asarray(vectors, dtype=np.float32))
        os.replace(temporary, path)
    except BaseException:
        if os.path.exists(temporary):
            os.remove(temporary)
        raise


class Builder:
    def __init__(self, args, embedding, sources, items, chosen, vectors, directory, out):
        self.args, self.embedding = args, embedding
        self.sources, self.items, self.chosen = sources, items, chosen
        self.vectors, self.directory, self.out = vectors, directory, out
        self.steps = embedding.views["full"]
        self._backend = None

    def backend(self):
        if self._backend is None:
            self._backend = build_embeddings.OpenAIBackend(self.embedding)
        return self._backend



    def one(self, key):
        """Embed the missing angles of one source. Return a log record."""
        digest = key[0]
        path = os.path.join(self.out, "vectors", digest + ".npz")
        have, old = load_saved(path)
        missing = [angle for angle in self.args.angles if angle not in set(have)]
        if not missing:
            return {"sha256": digest, "new": 0}
        started = time.time()
        source, item = self.sources[digest], self.items[key]
        image, _ = embeddings.derive.open_image(source["path"])
        cut = item["cut"]
        rgba, _ = embeddings.derive.open_image(cut["path"])
        cropped_size = (cut["box"][2] - cut["box"][0], cut["box"][3] - cut["box"][1])
        if rgba.size != cropped_size:
            return {"sha256": digest, "error": "the cut is %s; its box is %s"
                    % (rgba.size, cropped_size)}
        base = embeddings.on_white(rgba)
        scale = rs.scale_of(base.size, self.steps[-1])
        record = {"sha256": digest}
        pngs = []
        for angle in missing:
            picture = rs.rotated(base, angle, WHITE, scale)
            if angle == 0:
                stored = Image.open(os.path.join(self.directory, "images",
                                                 embeddings.image_name(digest, "full")))
                record["pixels_equal_index"] = bool(np.array_equal(
                    np.asarray(picture), np.asarray(stored.convert("RGB"))))
            pngs.append(png_fast(picture, self.args.compress))
        prepared = time.time()
        got = rs.normalise(rotation_multiref.embed_all(self.backend(), pngs, self.args.batch))
        if 0 in missing:
            stored_vector = rs.normalise(self.vectors[self.chosen[key]["row"]])
            record["cosine_0_index"] = round(float(got[missing.index(0)] @ stored_vector), 6)
        angles = have + missing
        rows = list(old) + list(got) if old is not None else list(got)
        order = np.argsort(angles)
        save_atomic(path, [angles[i] for i in order], np.asarray(rows)[order])
        record.update({"new": len(missing), "prepare_s": round(prepared - started, 2),
                       "embed_s": round(time.time() - prepared, 2)})
        return record


# One Builder in each worker process. The rotation and the PNG encoding hold the GIL, so
# threads gave about 1.6 cores; processes give one core each.
_BUILDER = None


def _init_worker(args):
    global _BUILDER
    settings = embeddings.load_settings()
    embedding = settings.find(args.entry)
    sources, items, chosen, vectors, directory = current_full_items(embedding, settings.db_path)
    _BUILDER = Builder(args, embedding, sources, items, chosen, vectors, directory,
                       os.path.join(args.out, args.entry))


def _one(key):
    return _BUILDER.one(key)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--entry", default=ENTRY)
    parser.add_argument("--angles", nargs="+", required=True, help="start:end:step")
    parser.add_argument("--out", default=OUT)
    parser.add_argument("--workers", type=int, default=6, help="worker processes")
    parser.add_argument("--batch", type=int, default=12, help="images per request")
    parser.add_argument("--compress", type=int, default=1, help="the PNG compression level")
    parser.add_argument("--limit", type=int, default=None, help="the first N sources alone")
    args = parser.parse_args(argv)
    args.angles = parse_angles(args.angles)

    settings = embeddings.load_settings()
    embedding = settings.find(args.entry)
    sources, items, chosen, vectors, directory = current_full_items(embedding, settings.db_path)
    out = os.path.join(args.out, args.entry)
    os.makedirs(os.path.join(out, "vectors"), exist_ok=True)
    keys = sorted(chosen)[:args.limit] if args.limit else sorted(chosen)
    with open(os.path.join(out, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump({"entry": args.entry, "model": embedding.model, "base_url": embedding.base_url,
                   "extra_body": embedding.extra_body, "index_vectors": os.path.basename(
                       os.path.join(directory, embeddings.read_index(directory)["vectors_file"])),
                   "sources": len(chosen), "last_angles": args.angles,
                   "method": "the SAM3 cut on white, rotated counter-clockwise (PIL BICUBIC, "
                             "expand=True, white fill), then the fixed scale of the resize "
                             "step of the 0° image; PNG compress_level %d; batch %d"
                             % (args.compress, args.batch),
                   "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")},
                  fh, ensure_ascii=False, indent=2)
    total = len(keys) * len(args.angles)
    print("entry %s: %d sources, %d angles, up to %d vectors; out %s"
          % (args.entry, len(keys), len(args.angles), total, out), flush=True)
    log = open(os.path.join(out, "build.log"), "a", encoding="utf-8")
    started, done, made, problems = time.time(), 0, 0, 0
    try:
        with concurrent.futures.ProcessPoolExecutor(
                args.workers, initializer=_init_worker, initargs=(args,)) as pool:
            futures = [pool.submit(_one, key) for key in keys]
            for future in concurrent.futures.as_completed(futures):
                try:
                    record = future.result()
                except Exception as exc:  # noqa: BLE001 - one source MUST NOT stop the build
                    record = {"error": "%s: %s" % (type(exc).__name__, exc)}
                record["time"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
                log.write(json.dumps(record) + "\n")
                log.flush()
                done += 1
                made += record.get("new", 0)
                if ("error" in record or record.get("pixels_equal_index") is False
                        or record.get("cosine_0_index", 1.0) < 0.999):
                    problems += 1
                    print("problem: %s" % json.dumps(record), flush=True)
                if done % 20 == 0 or done == len(keys):
                    elapsed = time.time() - started
                    rate = made / elapsed if elapsed else 0.0
                    left = (len(keys) - done) * len(args.angles)
                    print("%d/%d sources, %d vectors, %.1f vectors/s, about %.0f min left, "
                          "%d problems" % (done, len(keys), made, rate,
                                           left / rate / 60 if rate else 0, problems),
                          flush=True)
    except KeyboardInterrupt:
        print("stopped; a new run resumes from the saved files", flush=True)
        return 1
    finally:
        log.close()
    print("done: %d sources, %d new vectors, %d problems, %.0f s"
          % (done, made, problems, time.time() - started), flush=True)
    return 0 if not problems else 2


if __name__ == "__main__":
    sys.exit(main())
