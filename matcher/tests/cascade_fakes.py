"""Local fakes of the model services and the fixtures of the backend `cascade` tests.

`FakeServices` is one HTTP server with the routes of SigLIP2 (`/v1/embeddings`), SAM3
(`/sam3/segment_multi`, `/sam3/health`), the QR scanner (`/qr/scan`, `/qr/health`), and
the VLM (`/v1/chat/completions`). Each route takes an answer function, a delay, and a
status. The server records each request with its route, fields, and time. During a delay
the server watches the socket: a client that closes the connection is recorded in
`disconnects` with the route and the time, and gets no answer.
"""

import base64
from email.parser import BytesParser
from email.policy import default as email_policy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
import select
import socket
import threading
import time

import numpy as np
from PIL import Image

from matcher.bundle import Bundle
from matcher.codes import check_digit


MODEL = "fake-siglip2"
SIZE = (600, 800)
BACKGROUND = (128, 128, 128)
# The red package of the test photo, and the blue label on it (photo pixels).
PACKAGE = (200, 100, 400, 700)
LABEL = (240, 350, 360, 550)
# A green package at the right edge for the tests of `packages_first`.
OTHER_PACKAGE = (450, 150, 560, 650)
# (vector, slug) of each catalogue row. A red crop gives (1, 0, 0, 0); the whole gray
# photo gives (0, 1, 0, 0); a green crop gives (0, 0, 1, 0).
ROWS = (
    ((1, 0, 0, 0), "wine-a"),
    ((0.95, 0.31, 0, 0), "wine-a2"),
    ((0, 1, 0, 0), "wine-b"),
    ((0, 0, 1, 0), "wine-c"),
    ((0, 0, 0, 1), "wine-d"),
)


def ean13(twelve):
    """Return the EAN-13 of 12 digits with its check digit."""
    return twelve + str(check_digit(twelve))


EAN_PACKAGE = ean13("460000000001")
EAN_FULL = ean13("460000000002")
EAN_SHARED = ean13("460000000003")


def unit(values):
    vector = np.asarray(values, dtype=np.float32)
    return vector / np.linalg.norm(vector)


def card(slug):
    return {"name": "Name %s" % slug, "page_url": "https://vino-svoe.ru/wines/%s" % slug,
            "producer": None, "category": None, "region": None, "color": None,
            "grapes": None, "image_url": None, "qr_urls": [], "sugar": None}


def make_bundle(rows=ROWS, label_rows=()):
    """Return a `Bundle` of 4 dimensions with the view `full` (and `label`)."""
    slugs = tuple(sorted({slug for _, slug in rows + tuple(label_rows)}))
    numbers = {slug: number for number, slug in enumerate(slugs)}

    def view(pairs):
        matrix = np.vstack([unit(vector) for vector, _ in pairs]).astype(np.float32)
        return matrix, np.asarray([numbers[slug] for _, slug in pairs], dtype=np.int64)

    views = {"full": view(rows)}
    if label_rows:
        views["label"] = view(label_rows)
    return Bundle(path=None, embedding={"backend": "openai", "model": MODEL,
                                        "extra_body": {"max_num_patches": 512}},
                  dimension=4, slugs=slugs, views=views,
                  cards={slug: card(slug) for slug in slugs})


def photo(size=SIZE, packages=(PACKAGE,), label=LABEL, fmt="PNG"):
    """Return the bytes of the test photo: a gray scene, red packages, a blue label."""
    image = Image.new("RGB", size, BACKGROUND)
    for box in packages:
        image.paste((0, 160, 0) if box == OTHER_PACKAGE else (220, 20, 20), box)
    if label is not None:
        image.paste((20, 20, 220), label)
    output = BytesIO()
    image.save(output, fmt)
    return output.getvalue()


def mask_png_b64(size, box):
    image = Image.new("L", size, 0)
    image.paste(255, tuple(int(value) for value in box))
    output = BytesIO()
    image.save(output, "PNG")
    return base64.b64encode(output.getvalue()).decode("ascii")


def instance(label, box, size, score=0.9):
    return {"label": label, "box": list(box), "score": score,
            "area": (box[2] - box[0]) * (box[3] - box[1]),
            "mask_png_b64": mask_png_b64(size, box)}


def scene(nouns, size, packages=(PACKAGE,), label=LABEL, hand=None):
    """Return a SAM3 answer for the requested `nouns` on a copy of `size`, with the boxes
    of the test photo scaled to the copy."""
    scale_x, scale_y = size[0] / SIZE[0], size[1] / SIZE[1]

    def scaled(box):
        return (round(box[0] * scale_x), round(box[1] * scale_y),
                round(box[2] * scale_x), round(box[3] * scale_y))

    instances = [instance("wine bottle", scaled(box), size) for box in packages
                 if "wine bottle" in nouns]
    if hand is not None and "hand" in nouns:
        instances.append(instance("hand", scaled(hand), size, 0.85))
    if label is not None and "label" in nouns:
        instances.append(instance("label", scaled(label), size, 0.8))
    return {"width": size[0], "height": size[1], "count": len(instances),
            "instances": instances}


def dominant(image):
    """Return `red`, `green`, `blue`, or `gray`: the colour with the most pixels."""
    pixels = np.asarray(image.convert("RGB"), dtype=np.int16).reshape(-1, 3)
    red, green, blue = pixels[:, 0], pixels[:, 1], pixels[:, 2]
    counts = {
        "red": int(((red > 150) & (green < 80) & (blue < 80)).sum()),
        "green": int(((green > 120) & (red < 80) & (blue < 80)).sum()),
        "blue": int(((blue > 150) & (red < 80) & (green < 80)).sum()),
        "gray": int((np.abs(pixels - 128).max(axis=1) < 20).sum()),
    }
    return max(counts, key=counts.get)


def colour_vector(image):
    return {"red": (1, 0, 0, 0), "gray": (0, 1, 0, 0), "green": (0, 0, 1, 0),
            "blue": (0, 0, 0, 1)}[dominant(image)]


def chat_body(answer, finish_reason="stop"):
    return {"choices": [{"message": {"content": json.dumps(answer)},
                         "finish_reason": finish_reason}]}


def _multipart(content_type, body):
    message = BytesParser(policy=email_policy).parsebytes(
        b"Content-Type: " + content_type.encode("latin-1") + b"\r\n\r\n" + body)
    fields = {}
    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        fields[name] = part.get_payload(decode=True)
    return fields


class FakeServices:
    """The four model services on one local port."""

    def __init__(self):
        self.lock = threading.Lock()
        self.requests = []
        self.disconnects = []
        self.delays = {"embed": 0.0, "segment": 0.0, "scan": 0.0, "chat": 0.0}
        self.statuses = {"embed": 200, "segment": 200, "scan": 200, "chat": 200,
                         "health": 200}
        self.embed = colour_vector
        self.segment = lambda nouns, size: scene(nouns, size)
        self.scan = lambda image: []
        self.chat = lambda payload: chat_body({})
        fake = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):
                pass

            def answer(self, status, value):
                payload = json.dumps(value).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def wait(self, route):
                """Sleep the delay of `route`. Return False after a client disconnect."""
                end = time.monotonic() + fake.delays.get(route, 0.0)
                while time.monotonic() < end:
                    readable, _, _ = select.select([self.connection], [], [],
                                                   min(0.01, max(0.0, end - time.monotonic())))
                    if readable and self.connection.recv(1, socket.MSG_PEEK) == b"":
                        with fake.lock:
                            fake.disconnects.append((route, time.monotonic()))
                        self.close_connection = True
                        return False
                return True

            def do_GET(self):
                with fake.lock:
                    fake.requests.append({"route": "health", "path": self.path,
                                          "time": time.monotonic()})
                status = fake.statuses["health"]
                self.answer(status, {"status": "ok" if status == 200 else "down"})

            def do_POST(self):
                body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                content_type = self.headers.get("Content-Type", "")
                if self.path == "/v1/embeddings":
                    route, fields = "embed", json.loads(body)
                elif self.path == "/v1/chat/completions":
                    route, fields = "chat", json.loads(body)
                elif self.path == "/sam3/segment_multi":
                    route, fields = "segment", _multipart(content_type, body)
                elif self.path == "/qr/scan":
                    route, fields = "scan", _multipart(content_type, body)
                else:
                    self.answer(404, {"detail": "unknown route %s" % self.path})
                    return
                with fake.lock:
                    fake.requests.append({"route": route, "path": self.path,
                                          "fields": fields, "time": time.monotonic()})
                if not self.wait(route):
                    return
                status = fake.statuses[route]
                if status != 200:
                    self.answer(status, {"detail": "fake failure"})
                    return
                self.answer(200, fake.respond(route, fields))

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = "http://127.0.0.1:%d" % self.server.server_address[1]
        self.siglip2 = self.url
        self.sam3 = self.url + "/sam3"
        self.scanner = self.url + "/qr"
        self.vlm = self.url + "/v1"

    def respond(self, route, fields):
        if route == "embed":
            vectors = []
            for uri in fields["input"]:
                raw = base64.b64decode(uri.split(",", 1)[1])
                with Image.open(BytesIO(raw)) as image:
                    vectors.append([float(v) for v in unit(self.embed(image))])
            return {"data": [{"index": index, "embedding": vector}
                             for index, vector in enumerate(vectors)]}
        if route == "segment":
            nouns = tuple(noun.strip() for noun in fields["texts"].decode().split(","))
            with Image.open(BytesIO(fields["image"])) as image:
                size = image.size
            return self.segment(nouns, size)
        if route == "scan":
            with Image.open(BytesIO(fields["image"])) as image:
                image.load()
                return {"instances": self.scan(image)}
        return self.chat(fields)

    def routes(self, route):
        with self.lock:
            return [request for request in self.requests if request["route"] == route]

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


def rules(mode="verdict", slugs=("wine-a", "wine-a2")):
    """Return (clusters.json, cluster-rules.json) of one cluster with one rule."""
    clusters = {"spaces": {"combined": {"clusters": [{"key": "k1", "slugs": list(slugs)}]}}}
    rule = {"key": "k1", "slugs": list(slugs), "mode": mode, "error": None,
            "letters": {"A": slugs[0], "B": slugs[1]},
            "rule": "The label of wine B is blue.",
            "questions": [{"id": "q1", "question": "What colour is the label?",
                           "answers": {slugs[0]: "red", slugs[1]: "blue"},
                           "valid": True}]}
    return clusters, {"spaces": {"label": {"k1": rule}}, "cards": {}}
