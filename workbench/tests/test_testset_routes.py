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
from unittest import mock

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import testset_fixture as FX  # noqa: E402
import import_testset as IT  # noqa: E402
import lab_server as LAB  # noqa: E402
import remote_images as RI  # noqa: E402


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
        try:
            return status, json.loads(text)
        except ValueError:
            return status, {"error": text}

    def get_view(self):
        status, text = self.request("/api/testset?set=my")
        self.assertEqual(status, 200)
        return json.loads(text)

    def test_a_row_shows_the_wine_comments_of_the_dataset_route(self):
        status, text = self.request("/api/dataset-comment", "POST",
                                    {"slug": "wine-b", "text": "a wine comment"})
        self.assertEqual(status, 200, text)
        wine_b = next(r for r in self.get_view()["rows"] if r["slug"] == "wine-b")
        self.assertEqual([(c["text"], c["source"]) for c in wine_b["comments"]],
                         [("a wine comment", "user")])
        # A wine comment is not an edit of the set.
        conn = sqlite3.connect(self.db)
        try:
            self.assertIsNone(conn.execute("SELECT edited_at FROM test_set").fetchone()[0])
        finally:
            conn.close()

    def test_the_view_of_a_set(self):
        status, text = self.request("/api/testset?set=my")
        self.assertEqual(status, 200)
        view = json.loads(text)
        self.assertEqual(view["set"], "my")
        self.assertEqual([r["slug"] for r in view["rows"]],
                         ["__null__", "__drawer__", "wine-a", "wine-b", "wine-c"])
        wine_b = next(r for r in view["rows"] if r["slug"] == "wine-b")
        self.assertEqual(wine_b["state"], "Removed")
        photo = wine_b["photos"][0]
        with urllib.request.urlopen(self.base + photo["url"]) as response:
            self.assertEqual(response.read(), PHOTOS["wine-b/01.jpg"])
        self.assertEqual(self.request("/api/testset?set=other")[0], 404)

    def test_the_view_shares_the_global_catalog_favorites(self):
        rows = {row["slug"]: row for row in self.get_view()["rows"]}
        self.assertFalse(rows["wine-b"]["_favorite"])
        self.assertFalse(rows["__null__"]["_favorite"])
        self.assertFalse(rows["__drawer__"]["_favorite"])

        status, text = self.request("/api/dataset-favorite", "POST",
                                    {"slug": "wine-b", "favorite": True})
        self.assertEqual(status, 200, text)
        rows = {row["slug"]: row for row in self.get_view()["rows"]}
        self.assertTrue(rows["wine-b"]["_favorite"])
        self.assertFalse(rows["wine-a"]["_favorite"])
        self.assertFalse(rows["__null__"]["_favorite"])
        self.assertFalse(rows["__drawer__"]["_favorite"])

        status, text = self.request("/api/dataset-favorite", "POST",
                                    {"slug": "wine-b", "favorite": False})
        self.assertEqual(status, 200, text)
        self.assertFalse(next(row for row in self.get_view()["rows"]
                              if row["slug"] == "wine-b")["_favorite"])

    def test_each_write_route(self):
        status, answer = self.post("/api/testset-label", place="wine-b", file="01.jpg",
                                   label="positive")
        self.assertEqual((status, answer["photo"]["entry"]["label"]), (200, "positive"))
        status, answer = self.post("/api/testset-delete", place="wine-b", file="01.jpg",
                                   delete=True)
        self.assertEqual((status, answer["counts"]["deleting"]), (200, 1))
        # The comments of a photo (plan 51). The import made the old `comment` "c" one.
        status, answer = self.post("/api/testset-photo-comment", place="wine-a",
                                   file="01.jpg", text="second")
        self.assertEqual(status, 200)
        self.assertEqual([(c["text"], c["source"]) for c in answer["photo"]["comments"]],
                         [("c", "user"), ("second", "user")])
        self.assertNotIn("comment", answer["photo"]["entry"])
        status, answer = self.post("/api/testset-photo-comment", place="wine-a",
                                   file="01.jpg", text="by a script", source="script")
        self.assertEqual((status, answer["comment"]["source"]), (200, "script"))
        status, answer = self.post("/api/testset-photo-comment", place="wine-a",
                                   file="01.jpg", text="")
        self.assertEqual(status, 400)
        status, answer = self.post("/api/testset-photo-comment-remove", place="wine-a",
                                   file="01.jpg", id=999)
        self.assertEqual(status, 404)
        wine_a = next(r for r in self.get_view()["rows"] if r["slug"] == "wine-a")
        first = wine_a["photos"][0]["comments"][0]
        status, answer = self.post("/api/testset-photo-comment-remove", place="wine-a",
                                   file="01.jpg", id=first["id"])
        self.assertEqual((status, answer["removed"]), (200, first["id"]))
        self.assertEqual([c["text"] for c in answer["photo"]["comments"]],
                         ["second", "by a script"])
        status, answer = self.post("/api/testset-box", place="wine-a", file="01.jpg",
                                   box=[10, 5, 50, 35])
        self.assertEqual((status, answer["photo"]["entry"]["box"]), (200, [10, 5, 50, 35]))
        status, answer = self.post("/api/testset-box", place="wine-a", file="01.jpg",
                                   box=[10, 5, 61, 35])
        self.assertEqual(status, 400)
        self.assertIn("not inside the photo of 60 x 40 pixels", answer["error"])
        # The wine note and the exclusion went away with plan 51. The server answers an
        # unknown API route with 503 `DISABLED_ERROR`.
        for route in ("/api/testset-comment", "/api/testset-wine-note", "/api/testset-exclude"):
            status, answer = self.post(route, slug="wine-b", text="x")
            self.assertEqual((status, answer.get("error")), (503, LAB.DISABLED_ERROR), route)
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

    def test_the_drawer_remove_route(self):
        status, answer = self.post("/api/testset-move", place="wine-a", file="01.jpg",
                                   to="__drawer__")
        self.assertEqual((status, answer["counts"]["drawer"]), (200, 1))
        status, answer = self.post("/api/testset-drawer-remove", place="__drawer__",
                                   file="01.jpg")
        self.assertEqual((status, answer["place"], answer["file"],
                          answer["counts"]["drawer"]),
                         (200, "__drawer__", "01.jpg", 0))
        status, _ = self.post("/api/testset-drawer-remove", place="wine-b", file="01.jpg")
        self.assertEqual(status, 400)


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

    def test_the_crop_route_adds_a_png_to_the_same_wine(self):
        status, answer = self.post("/api/testset-crop", place="wine-a", file="01.jpg",
                                   box=[10, 5, 50, 35])
        self.assertEqual((status, answer["photo"]["place"], answer["photo"]["file"]),
                         (200, "wine-a", "01_crop.png"))
        self.assertEqual((answer["cropped_from"], answer["box"]),
                         ("01.jpg", [10, 5, 50, 35]))
        self.assertEqual((answer["photo"]["width"], answer["photo"]["height"]), (40, 30))
        self.assertEqual(answer["photo"]["entry"], {})
        with urllib.request.urlopen(self.base + answer["photo"]["url"]) as response:
            cropped = response.read()
        with Image.open(io.BytesIO(cropped)) as image:
            self.assertEqual((image.format, image.size), ("PNG", (40, 30)))
        photos = next(row for row in self.get_view()["rows"]
                      if row["slug"] == "wine-a")["photos"]
        self.assertEqual({photo["file"] for photo in photos}, {"01.jpg", "01_crop.png"})
        self.assertEqual(answer["counts"]["photos"], len(PHOTOS) + 1)

        # The same crop is the same image, and a place holds one image once.
        self.assertEqual(self.post("/api/testset-crop", place="wine-a", file="01.jpg",
                                   box=[10, 5, 50, 35])[0], 409)
        for body, code, text in (({"box": [0, 0, 61, 40]}, 400, "not inside"),
                                 ({"box": [0, 0, 3]}, 400, "MUST be"),
                                 ({"box": None}, 400, "MUST be"),
                                 ({"file": "missing.jpg", "box": [0, 0, 3, 3]}, 404,
                                  "has no photo")):
            with self.subTest(body=body):
                status, failure = self.post("/api/testset-crop",
                                            **dict({"place": "wine-a", "file": "01.jpg"},
                                                   **body))
                self.assertEqual(status, code, failure)
                self.assertIn(text, failure["error"])
        self.assertEqual(self.request("/api/testset-crop")[0], 405)

    def test_the_browser_image_fetch_route(self):
        data = jpeg((26, 24))
        source = "https://images.example/wine%20photo.webp"
        with mock.patch("testset_routes.remote_images.fetch_image",
                        return_value=(data, "wine photo.webp")) as fetch:
            status, answer = self.post("/api/testset-fetch", place="wine-a", url=source)
        self.assertEqual((status, answer["photo"]["file"], answer["source_url"]),
                         (200, "wine photo.jpg", source))
        fetch.assert_called_once_with(source, 20 * 1024 * 1024)
        with urllib.request.urlopen(self.base + answer["photo"]["url"]) as response:
            self.assertEqual(response.read(), data)

        # The regular upload rules still decide duplicates, places, and image bytes.
        with mock.patch("testset_routes.remote_images.fetch_image",
                        return_value=(data, "again.jpg")):
            self.assertEqual(self.post("/api/testset-fetch", place="wine-a",
                                       url="https://images.example/again")[0], 409)
            status, other = self.post("/api/testset-fetch", place="__drawer__",
                                      url="https://images.example/again")
        self.assertEqual((status, other["photo"]["file"]), (200, "wine photo.jpg"))

        with mock.patch("testset_routes.remote_images.fetch_image",
                        side_effect=RI.RemoteImageError(
                            "the image address points at a local host: 127.0.0.1")):
            status, failure = self.post("/api/testset-fetch", place="wine-a",
                                        url="http://127.0.0.1/private")
        self.assertEqual(status, 400)
        self.assertIn("local host", failure["error"])
        self.assertEqual(self.request("/api/testset-fetch")[0], 405)


    def test_the_tag_routes(self):
        # Plan 66: the tag belongs to the image, so the view shows it on the photo.
        status, answer = self.post("/api/testset-photo-tag", place="wine-a", file="01.jpg",
                                   tag=" Blurry")
        self.assertEqual(status, 200, answer)
        self.assertEqual((answer["added"], answer["tags"], answer["photo"]["tags"]),
                         ("blurry", ["blurry"], ["blurry"]))
        self.assertEqual(answer["tag_names"], [{"tag": "blurry", "images": 1}])
        view = self.get_view()
        self.assertEqual(view["tag_names"], [{"tag": "blurry", "images": 1}])
        photo = [p for r in view["rows"] if r["slug"] == "wine-a" for p in r["photos"]][0]
        self.assertEqual(photo["tags"], ["blurry"])
        for body, code in (({"tag": "blurry"}, 409), ({"tag": "two words"}, 400),
                           ({"tag": ""}, 400), ({}, 400),
                           ({"tag": "blurry", "file": "99.jpg"}, 404)):
            with self.subTest(body=body):
                status, answer = self.post("/api/testset-photo-tag",
                                           **dict({"place": "wine-a", "file": "01.jpg"}, **body))
                self.assertEqual(status, code, answer)
        status, answer = self.post("/api/testset-photo-tag-remove", place="wine-a",
                                   file="01.jpg", tag="BLURRY")
        self.assertEqual((status, answer["removed"], answer["tags"]), (200, "blurry", []))
        status, answer = self.post("/api/testset-photo-tag-remove", place="wine-a",
                                   file="01.jpg", tag="blurry")
        self.assertEqual(status, 404, answer)
        status, _ = self.request("/api/testset-photo-tag")
        self.assertEqual(status, 405)
        self.assertEqual(self.get_view()["tag_names"], [])

    def test_the_autotag_status_and_start_routes(self):
        job = {"state": "running", "set": "my", "job_id": "job-1", "done": 2,
               "total": 3, "tags": ["label_back", "label_front", "isolated_product",
                                      "scene_photo"]}
        with mock.patch("testset_routes.testset_autotag.job_view", return_value=job) as view:
            status, text = self.request("/api/testset-autotag?set=my")
        self.assertEqual((status, json.loads(text)), (200, job))
        view.assert_called_once_with("my")

        with mock.patch("testset_routes.testset_autotag.start", return_value=job) as start:
            status, answer = self.post("/api/testset-autotag")
        self.assertEqual((status, answer), (202, job))
        start.assert_called_once_with(
            str(Path(__file__).resolve().parents[1] / "config.yaml"), self.db, "my")

        self.assertEqual(self.request("/api/testset-autotag?set=missing")[0], 404)
        self.assertEqual(self.request("/api/testset-autotag", "POST",
                                      {"set": "missing"})[0], 404)
        self.assertEqual(self.request("/api/testset-autotag", "PUT", b"{}")[0], 405)

    def test_the_page_has_the_autotag_button_and_progress_poll(self):
        status, page = self.request("/testset")
        self.assertEqual(status, 200)
        self.assertIn('id="autotag"', page)
        self.assertIn("/api/testset-autotag", page)
        self.assertIn('"label_back", "label_front", "isolated_product", "scene_photo"',
                      page)
        self.assertIn('new Set(["starting", "running", "waiting"])', page)
        self.assertIn("Autotag waiting for VLM:", page)

    def test_the_page_filters_the_drawer_and_its_results_by_image_tag(self):
        status, page = self.request("/testset")
        self.assertEqual(status, 200)
        for fragment in ('id="drawer-tag"', 'id="drawer-results-tag"',
                         'tagFilterMatches(photoTags(photo), want)',
                         'tagFilterMatches(drawerResultTags(row), want)',
                         'No Drawer photo matches this tag filter.',
                         'No waiting Drawer photo matches this tag filter.'):
            self.assertIn(fragment, page)


class NewSetRouteTest(unittest.TestCase):
    """Plan 57: `POST /api/testset-new` makes an empty set."""
    setUp, tearDown = TestsetRoutesTest.setUp, TestsetRoutesTest.tearDown
    request, post = TestsetRoutesTest.request, TestsetRoutesTest.post

    def test_a_new_set_is_listed_last_and_opens_empty(self):
        status, out = self.post("/api/testset-new", name="my-2")
        self.assertEqual((status, out), (200, {"ok": True, "set": "my-2"}))
        status, text = self.request("/api/testset?set=my-2")
        self.assertEqual(status, 200, text)
        view = json.loads(text)
        self.assertEqual(view["set"], "my-2")
        self.assertEqual([(s["name"], s["photos"]) for s in view["sets"]],
                         [("my", len(PHOTOS)), ("my-2", 0)])

    def test_a_bad_or_present_name_is_refused(self):
        self.assertEqual(self.post("/api/testset-new", name="My")[0], 400)
        self.assertEqual(self.post("/api/testset-new")[0], 400)
        self.assertEqual(self.post("/api/testset-new", name="my")[0], 409)
        self.assertEqual(self.request("/api/testset-new")[0], 405)


class RenameSetRouteTest(unittest.TestCase):
    """`POST /api/testset-rename` renames the populated set of the page."""
    setUp, tearDown = TestsetRoutesTest.setUp, TestsetRoutesTest.tearDown
    request, post = TestsetRoutesTest.request, TestsetRoutesTest.post

    def test_a_populated_set_is_available_under_its_new_name(self):
        status, out = self.post("/api/testset-rename", name="test-1")
        self.assertEqual((status, out),
                         (200, {"ok": True, "set": "test-1", "old_set": "my"}))
        self.assertEqual(self.request("/api/testset?set=my")[0], 404)
        status, text = self.request("/api/testset?set=test-1")
        self.assertEqual(status, 200, text)
        view = json.loads(text)
        self.assertEqual((view["set"], view["counts"]["photos"]),
                         ("test-1", len(PHOTOS)))

    def test_bad_same_and_present_names_are_refused(self):
        self.assertEqual(self.post("/api/testset-rename", name="My")[0], 400)
        self.assertEqual(self.post("/api/testset-rename", name="my")[0], 400)
        self.assertEqual(self.post("/api/testset-new", name="two")[0], 200)
        self.assertEqual(self.post("/api/testset-rename", name="two")[0], 409)
        self.assertEqual(self.request("/api/testset-rename")[0], 405)


if __name__ == "__main__":
    unittest.main()
