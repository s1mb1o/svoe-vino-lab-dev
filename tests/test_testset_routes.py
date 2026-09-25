"""The routes of the Testset page (plan 24) through the lab server."""
import io
import json
import sqlite3
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import testset_fixture as FX  # noqa: E402
import import_testset as IT  # noqa: E402
import lab_server as LAB  # noqa: E402


def jpeg(size):
    buffer = io.BytesIO()
    Image.new("RGB", size, "white").save(buffer, "JPEG")
    return buffer.getvalue()


PHOTOS = {"wine-a/01.jpg": jpeg((60, 40)), "wine-b/01.jpg": jpeg((30, 30)),
          "__null__/n1.jpg": jpeg((20, 20))}
LABELS = {"wine-a": {"01.jpg": {"label": "positive", "comment": "c", "ts": "t"}}}


class TestsetRoutesTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.db, self.schema = FX.make_database(self.root)
        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE wine_catalog SET state = 'Removed', removed_by = 'person' "
                     "WHERE wine_slug = 'wine-b'")
        conn.commit()
        conn.close()
        IT.import_testset(self.db, "my", FX.write_set(self.root, PHOTOS, LABELS),
                          lambda m: None, self.schema)
        self.server = LAB.make_server(self.db, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = "http://127.0.0.1:%d" % self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.directory.cleanup()

    def request(self, path, method="GET", body=None):
        data = (json.dumps(body).encode() if isinstance(body, dict) else body)
        req = urllib.request.Request(self.base + path, method=method, data=data,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as response:
                return response.status, response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            with exc:
                return exc.code, exc.read().decode("utf-8")

    def post(self, route, **body):
        status, text = self.request(route, "POST", dict(body, set="my"))
        return status, json.loads(text)

    def test_the_view_of_a_set(self):
        status, text = self.request("/api/testset?set=my")
        self.assertEqual(status, 200)
        view = json.loads(text)
        self.assertEqual(view["set"], "my")
        self.assertEqual([r["slug"] for r in view["rows"]],
                         ["__null__", "wine-a", "wine-b", "wine-c"])
        wine_b = next(r for r in view["rows"] if r["slug"] == "wine-b")
        self.assertEqual(wine_b["state"], "Removed")
        photo = wine_b["photos"][0]
        with urllib.request.urlopen(self.base + photo["url"]) as response:
            self.assertEqual(response.read(), PHOTOS["wine-b/01.jpg"])
        self.assertEqual(self.request("/api/testset?set=other")[0], 404)

    def test_each_write_route(self):
        status, answer = self.post("/api/testset-label", place="wine-b", file="01.jpg",
                                   label="positive")
        self.assertEqual((status, answer["photo"]["entry"]["label"]), (200, "positive"))
        status, answer = self.post("/api/testset-delete", place="wine-b", file="01.jpg",
                                   delete=True)
        self.assertEqual((status, answer["counts"]["deleting"]), (200, 1))
        status, answer = self.post("/api/testset-comment", place="wine-a", file="01.jpg",
                                   text="")
        self.assertEqual((status, "comment" in answer["photo"]["entry"]), (200, False))
        status, answer = self.post("/api/testset-box", place="wine-a", file="01.jpg",
                                   box=[10, 5, 50, 35])
        self.assertEqual((status, answer["photo"]["entry"]["box"]), (200, [10, 5, 50, 35]))
        status, answer = self.post("/api/testset-box", place="wine-a", file="01.jpg",
                                   box=[10, 5, 61, 35])
        self.assertEqual(status, 400)
        self.assertIn("not inside the photo of 60 x 40 pixels", answer["error"])
        status, answer = self.post("/api/testset-wine-note", slug="wine-b", text="removed")
        self.assertEqual((status, answer["note"]), (200, "removed"))
        status, answer = self.post("/api/testset-exclude", slug="wine-a", excluded=True,
                                   reason="wrong bottle photo")
        self.assertEqual((status, answer["excluded"]), (200, True))
        conn = sqlite3.connect(self.db)
        try:
            self.assertEqual(conn.execute("SELECT label, marked_delete FROM test_photo "
                                          "WHERE place = 'wine-b'").fetchall(),
                             [("positive", 1)])
            self.assertIsNotNone(conn.execute("SELECT edited_at FROM test_set").fetchone()[0])
        finally:
            conn.close()

    def test_request_errors(self):
        route = "/api/testset-label"
        for body, code, text in ((b"", 400, "at most"), (b"{", 400, "not JSON"),
                                 (b"[1]", 400, "JSON object"),
                                 (b'{"set": "my", "place": "\\ud800"}', 400, "surrogate"),
                                 (b"x" * 40000, 400, "at most")):
            status, answer = self.request(route, "POST", body)
            self.assertEqual(status, code, body[:20])
            self.assertIn(text, json.loads(answer)["error"])
        status, answer = self.post(route, place="wine-a", file="missing.jpg", label=None)
        self.assertEqual(status, 404)
        status, answer = self.post(route, place="__null__", file="n1.jpg", label="variant")
        self.assertEqual(status, 400)
        self.assertEqual(self.request(route)[0], 405)
        self.assertEqual(self.request("/api/testset", "POST", b"{}")[0], 405)

    def test_a_missing_database_answers_503(self):
        self.server.db_path = str(self.root / "missing.sqlite3")
        for path, method, body in (("/api/testset", "GET", None),
                                   ("/api/testset-label", "POST", b"{}")):
            status, answer = self.request(path, method, body)
            self.assertEqual(status, 503, path)
            self.assertIn("no database", json.loads(answer)["error"])

    def test_head_of_the_page_sends_no_body(self):
        status, body = self.request("/testset", "HEAD")
        self.assertEqual((status, body), (200, ""))

    def test_the_move_route(self):
        status, answer = self.post("/api/testset-move", place="wine-a", file="01.jpg",
                                   to="__null__")
        self.assertEqual((status, answer["photo"]["place"]), (200, "__null__"))
        self.assertNotIn("label", answer["photo"]["entry"])
        status, answer = self.post("/api/testset-move", place="__null__", file="01.jpg",
                                   to="wine-z")
        self.assertEqual(status, 404)


    def test_the_upload_route(self):
        data = jpeg((25, 25))
        route = "/api/testset-upload?set=my&place=__null__&name=a%20b.jpg"
        status, text = self.request(route, "POST", data)
        answer = json.loads(text)
        self.assertEqual((status, answer["photo"]["file"]), (200, "a b.jpg"))
        with urllib.request.urlopen(self.base + answer["photo"]["url"]) as response:
            self.assertEqual(response.read(), data)
        status, text = self.request(route, "POST", data)
        self.assertEqual(status, 409)
        status, text = self.request(route, "POST", b"")
        self.assertEqual(status, 400)
        self.assertIn("at most", json.loads(text)["error"])
        status, text = self.request("/api/testset-upload?set=my&place=wine-z&name=a.jpg",
                                    "POST", data)
        self.assertEqual(status, 404)
        self.assertEqual(self.request(route)[0], 405)


if __name__ == "__main__":
    unittest.main()
