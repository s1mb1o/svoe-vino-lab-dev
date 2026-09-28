"""A small lab for the tests of the embeddings: a database at the present schema, an
image store with processed files of plan 09, a `config.yaml`, and a fake gateway.

The fake gateway answers `POST /v1/embeddings` with a vector of 8 values made from the
pixels of each image. It never calls gx10.
"""
import base64
import hashlib
import io
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import labdb  # noqa: E402

VIEWS_C_F = {
    "full": {"steps": [{"step": "segment", "target": "package"},
                       {"step": "remove_background"}, {"step": "white_background"},
                       {"step": "resize", "max_size": 64}]},
    "label": {"steps": [{"step": "segment", "target": "label"},
                        {"step": "remove_background"}, {"step": "white_background"}]},
}


def png(image):
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def bottle_on_transparent(colour=(90, 30, 20)):
    """RGBA 60 x 100: an opaque bottle in the box (20, 10, 40, 90), transparent around."""
    image = Image.new("RGBA", (60, 100), (0, 0, 0, 0))
    ImageDraw.Draw(image).rectangle((20, 10, 39, 89), fill=colour + (255,))
    return image


def bottle_on_grey(colour=(20, 90, 30)):
    """RGB 80 x 120: a bottle in the box (30, 20, 50, 100) on a grey background."""
    image = Image.new("RGB", (80, 120), (128, 128, 128))
    ImageDraw.Draw(image).rectangle((30, 20, 49, 99), fill=colour)
    return image


def seg_derivative(image, box):
    """The processed file of plan 09 for an RGB original: the mask as alpha, cropped."""
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).rectangle((box[0], box[1], box[2] - 1, box[3] - 1), fill=255)
    out = image.convert("RGBA")
    out.putalpha(mask)
    return out.crop(box)


class Lab:
    """A temporary lab in `root`."""

    def __init__(self, root, base_url="http://127.0.0.1:9/v1"):
        self.root = Path(root)
        self.db_path = str(self.root / "data" / "lab.sqlite3")
        os.makedirs(os.path.dirname(self.db_path))
        self.conn = labdb.connect(self.db_path, create=True)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.base_url = base_url
        self.entries = []
        self.rowid = 0

    def wine(self, slug, state="Active"):
        self.conn.execute(
            "INSERT INTO wine_catalog (wine_slug, name, producer, category, color, region, "
            "grapes, description, csv_photo_name, state, removed_by) "
            "VALUES (?, ?, ?, 'Вино', 'красное', 'Кубань', NULL, 'd', 'p', ?, ?)",
            (slug, "Name " + slug, "Producer " + slug, state,
             "person" if state == "Removed" else None))
        self.conn.commit()

    def store_file(self, data, folder, extension):
        digest = hashlib.sha256(data).hexdigest()
        target = Path(labdb.image_dir(self.db_path, folder)) / ("%s.%s" % (digest, extension))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        with Image.open(io.BytesIO(data)) as image:
            size = image.size
        self.conn.execute("INSERT INTO image (sha256, folder, extension, width, height) "
                          "VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
                          (digest, folder, extension) + size)
        self.conn.commit()
        return digest

    def image(self, slug, image_type, image, folder="main", derivative=None, box=None):
        """Store an original of `slug`. `derivative` and `box` add the processed file."""
        digest = self.store_file(png(image), folder, "png")
        self.conn.execute(
            "INSERT INTO wine_image (wine_slug, image_type, sha256, source_name, match_method) "
            "VALUES (?, ?, ?, ?, 'test')", (slug, image_type, digest, "%s.png" % digest[:8]))
        if derivative is not None:
            derived = self.store_file(png(derivative), labdb.DERIVED_FOLDER, "png")
            self.conn.execute(
                "INSERT INTO image_derivative (source_sha256, method, settings, sha256, "
                "box_left, box_top, box_right, box_bottom) VALUES (?, ?, 'test', ?, ?, ?, ?, ?) "
                "ON CONFLICT DO NOTHING",
                (digest, "crop" if image.mode == "RGBA" else "seg", derived) + tuple(box))
        self.conn.commit()
        return digest

    def link(self, slug, image_type, digest):
        """Give an original that is stored already to another wine."""
        self.conn.execute(
            "INSERT INTO wine_image (wine_slug, image_type, sha256, source_name, match_method) "
            "VALUES (?, ?, ?, 'shared.png', 'test')", (slug, image_type, digest))
        self.conn.commit()

    def add_entry(self, name="gw", **values):
        entry = {"name": name, "backend": "openai", "base_url": self.base_url,
                 "model": "fake-model", "extra_body": {"max_num_patches": 256},
                 "batch_size": 2, "views": VIEWS_C_F}
        entry.update(values)
        self.entries = [e for e in self.entries if e["name"] != name] + [entry]
        self.write_config()
        return entry

    def write_config(self, python=None):
        config = {"rootdir": str(self.root), "database_file": "data/lab.sqlite3",
                  "embeddings": self.entries}
        if python:
            config["embedding_python"] = python
        (self.root / "config.yaml").write_text(yaml.safe_dump(config, allow_unicode=True),
                                               encoding="utf-8")

    @property
    def config_path(self):
        return str(self.root / "config.yaml")

    def entry_dir(self, name="gw"):
        return str(self.root / "data" / "embeddings" / name)

    def close(self):
        self.conn.close()


def standard_lab(root, base_url):
    """The wines of most tests.

    - `transparent`: an RGBA main image with a `crop` processed file, and a close-up.
    - `grey`: an RGB main image with a `seg` processed file.
    - `patched`: a `main` and a `main_patched`; the `main_patched` wins.
    - `shared`: the main image of `transparent`, a second time.
    - `unprocessed`: a main image with no processed file.
    - `disabled`: a Disabled wine; not an input.
    """
    lab = Lab(root, base_url)
    for slug in ("transparent", "grey", "patched", "shared", "unprocessed"):
        lab.wine(slug)
    lab.wine("disabled", state="Disabled")
    transparent = bottle_on_transparent()
    lab.transparent = lab.image("transparent", "main", transparent,
                                derivative=transparent.crop((20, 10, 40, 90)),
                                box=(20, 10, 40, 90))
    lab.closeup = lab.image("transparent", "label_front", Image.new("RGB", (40, 30), (200, 10, 10)),
                            folder="additional")
    grey = bottle_on_grey()
    lab.grey = lab.image("grey", "main", grey, derivative=seg_derivative(grey, (30, 20, 50, 100)),
                         box=(30, 20, 50, 100))
    old = bottle_on_grey((5, 5, 200))
    lab.patched_main = lab.image("patched", "main", old,
                                 derivative=seg_derivative(old, (30, 20, 50, 100)),
                                 box=(30, 20, 50, 100))
    new = bottle_on_transparent((200, 200, 0))
    lab.patched = lab.image("patched", "main_patched", new, folder="patched",
                            derivative=new.crop((20, 10, 40, 90)), box=(20, 10, 40, 90))
    lab.link("shared", "main", lab.transparent)
    lab.unprocessed = lab.image("unprocessed", "main", bottle_on_grey((1, 2, 3)))
    lab.disabled = lab.image("disabled", "main", bottle_on_grey((9, 9, 9)),
                             derivative=seg_derivative(bottle_on_grey((9, 9, 9)), (30, 20, 50, 100)),
                             box=(30, 20, 50, 100))
    lab.add_entry()
    return lab


class FakeGateway:
    """`POST /v1/embeddings` with 8 values for each image: the mean of R, G, B, the
    width, the height, and 1, 1, 1. `status` makes each answer fail with that code."""

    def __init__(self):
        self.requests = []
        self.status = 200
        gateway = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                gateway.requests.append(body)
                if gateway.status != 200:
                    data = b'{"error": "fake failure"}'
                    self.send_response(gateway.status)
                else:
                    rows = []
                    for number, uri in enumerate(body["input"]):
                        raw = base64.b64decode(uri.split(",", 1)[1])
                        with Image.open(io.BytesIO(raw)) as image:
                            pixels = np.asarray(image.convert("RGB"), dtype=np.float32)
                            size = image.size
                        vector = list(pixels.reshape(-1, 3).mean(axis=0) / 255.0) + [
                            size[0] / 100.0, size[1] / 100.0, 1.0, 1.0, 1.0]
                        rows.append({"object": "embedding", "index": number,
                                     "embedding": [float(value) for value in vector]})
                    data = json.dumps({"object": "list", "data": rows}).encode()
                    self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = "http://127.0.0.1:%d/v1" % self.server.server_address[1]

    def images(self):
        return sum(len(body["input"]) for body in self.requests)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
