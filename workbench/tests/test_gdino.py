import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import gdino  # noqa: E402
import model_cache  # noqa: E402


class Response:
    def __init__(self, status, body=None):
        self.status_code, self.body = status, body or {}
        self.text, self.headers = json.dumps(self.body), {}

    def json(self):
        return self.body


class FakeSession:
    """Each post takes the next answer. The last answer repeats."""

    def __init__(self, *answers):
        self.answers = list(answers) or [Response(200, {"instances": []})]
        self.posts = []

    def post(self, url, files=None, data=None, timeout=None):
        self.posts.append((url, Image.open(io.BytesIO(files["image"][1])).size, dict(data)))
        return self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]


def found(*labels):
    return Response(200, {"count": len(labels), "model": "IDEA-Research/grounding-dino-base",
                          "instances": [{"label": label, "box": [1, 2, 3, 4], "score": 0.5}
                                        for label in labels]})


class GdinoTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.old_root, model_cache.ROOT = model_cache.ROOT, self.directory.name

    def tearDown(self):
        model_cache.ROOT = self.old_root
        self.directory.cleanup()

    def client(self, session, model="grounding-dino-base"):
        client = gdino.GdinoClient(model, "http://gx10.invalid/")
        client.session = session
        return client

    def test_detect_sends_a_small_copy_and_a_repeat_reads_the_cache(self):
        session = FakeSession(found("wine bottle"))
        client = self.client(session)
        image = Image.new("RGB", (1000, 3072), "white")
        instances, scale = client.detect(image, "wine bottle")
        self.assertEqual(session.posts, [(
            "http://gx10.invalid/upstream/grounding-dino-base/detect", (500, 1536),
            {"texts": "wine bottle", "threshold": "0.25", "text_threshold": "0.25"})])
        self.assertEqual((scale, [item["label"] for item in instances]), (0.5, ["wine bottle"]))
        self.assertEqual(client.detect(image, "wine bottle"), (instances, scale))
        self.assertEqual((len(session.posts), client.hits), (1, 1))
        client.detect(image, "wine bottle", threshold=0.1)
        client.detect(image, "label")
        client.detect(Image.new("RGB", (1000, 3072), "black"), "wine bottle")
        self.assertEqual(len(session.posts), 4)
        self.assertEqual(os.listdir(self.directory.name), ["grounding-dino-base"])

    def test_each_model_has_its_own_records(self):
        image = Image.new("RGB", (40, 60), "white")
        base, other = FakeSession(found("a")), FakeSession(found("b"))
        self.client(base).detect(image, "bottle")
        self.assertEqual(self.client(other, "mm-gdino-base").detect(image, "bottle")[0][0]
                         ["label"], "b")
        self.assertEqual(sorted(os.listdir(self.directory.name)),
                         ["grounding-dino-base", "mm-gdino-base"])

    def test_retry_after_429_and_a_failure_is_not_stored(self):
        image = Image.new("RGB", (40, 60), "white")
        old = (gdino.GDINO_RETRIES, gdino.time.sleep)
        gdino.GDINO_RETRIES, gdino.time.sleep = 2, lambda seconds: None
        try:
            session = FakeSession(Response(429), found("bottle"))
            self.assertEqual(len(self.client(session).detect(image, "bottle")[0]), 1)
            self.assertEqual(len(session.posts), 2)
            down = FakeSession(Response(503))
            with self.assertRaisesRegex(gdino.GdinoUnavailable, "HTTP 503"):
                self.client(down).detect(image, "can")
            self.assertEqual(len(down.posts), 3)
            bad = FakeSession(Response(422, {"detail": "texts"}))
            with self.assertRaises(gdino.GdinoUnavailable):
                self.client(bad).detect(image, "can")
            self.assertEqual(len(bad.posts), 1)
        finally:
            gdino.GDINO_RETRIES, gdino.time.sleep = old
        later = FakeSession(found("can"))
        self.assertEqual(len(self.client(later).detect(image, "can")[0]), 1)
        self.assertEqual(len(later.posts), 1)

    def test_command_line_states_miss_then_hit(self):
        path = Path(self.directory.name) / "photo.png"
        Image.new("RGBA", (30, 50), (255, 255, 255, 0)).save(path)
        session = FakeSession(found("bottle"))
        states = []
        with mock.patch.object(gdino.requests, "Session", lambda: session):
            for _ in range(2):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    self.assertEqual(gdino.main([str(path), "--texts", "bottle"]), 0)
                states.append(json.loads(out.getvalue())["cache"])
        self.assertEqual((states, len(session.posts)), (["miss", "hit"], 1))


if __name__ == "__main__":
    unittest.main()
