"""Verify independent duplicate entries and existing move actions."""
import concurrent.futures
import hashlib
import sqlite3
import unittest
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(1, str(ROOT / "scripts"))
import benchmark  # noqa: E402
import test_testset_routes as RT  # noqa: E402
import testsets  # noqa: E402


class DuplicateRoutesTest(unittest.TestCase):
    setUp = RT.TestsetRoutesTest.setUp
    tearDown = RT.TestsetRoutesTest.tearDown
    request = RT.TestsetRoutesTest.request
    post = RT.TestsetRoutesTest.post
    get_view = RT.TestsetRoutesTest.get_view

    def duplicate(self, **values):
        return self.post("/api/testset-duplicate", **dict({"place": "wine-a", "file": "01.jpg"}, **values))

    def image_files(self):
        return {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in (self.root / "data" / "images").rglob("*") if path.is_file()}

    def test_duplicate_reuses_bytes_and_keeps_the_source_entry(self):
        before = self.get_view()
        source = next(row for row in before["rows"] if row["slug"] == "wine-a")["photos"][0]
        files = self.image_files()
        status, answer = self.duplicate(sha256=source["sha256"])
        self.assertEqual(status, 200, answer)
        photo = answer["photo"]
        self.assertEqual(photo["file"], "01.jpg.duplicate2.jpg")
        self.assertEqual((photo["sha256"], photo["url"]), (source["sha256"], source["url"]))
        self.assertNotIn("label", photo["entry"])
        self.assertEqual(photo["comments"], [])
        self.assertEqual(photo["entry"]["duplicated_from"], "01.jpg")
        self.assertEqual(self.image_files(), files)
        rows = next(row for row in self.get_view()["rows"] if row["slug"] == "wine-a")["photos"]
        self.assertEqual(rows[0], source)
        self.assertEqual(answer["counts"]["photos"], before["counts"]["photos"] + 1)

    def test_repeat_duplicates_have_distinct_names(self):
        names = [self.duplicate()[1]["photo"]["file"] for _ in range(3)]
        self.assertEqual(names, ["01.jpg.duplicate2.jpg", "01.jpg.duplicate3.jpg", "01.jpg.duplicate4.jpg"])
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM image").fetchone()[0], 3)

    def test_concurrent_requests_get_distinct_entries(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            answers = list(pool.map(lambda _: self.duplicate(), range(2)))
        self.assertEqual([status for status, _ in answers], [200, 200])
        self.assertEqual({answer["photo"]["file"] for _, answer in answers},
                         {"01.jpg.duplicate2.jpg", "01.jpg.duplicate3.jpg"})

    def test_duplicate_keeps_shared_tags_and_box_without_copying_a_verdict(self):
        self.post("/api/testset-photo-tag", place="wine-a", file="01.jpg", tag="scene_photo")
        self.post("/api/testset-box", place="wine-a", file="01.jpg", box=[1, 2, 20, 25])
        self.post("/api/testset-delete", place="wine-a", file="01.jpg", delete=True)
        status, answer = self.duplicate()
        self.assertEqual(status, 200, answer)
        self.assertEqual(answer["photo"]["tags"], ["scene_photo"])
        self.assertEqual(answer["photo"]["entry"]["box"], [1, 2, 20, 25])
        self.assertNotIn("delete", answer["photo"]["entry"])
        self.assertNotIn("label", answer["photo"]["entry"])

    def test_duplicate_can_move_through_drawer_to_another_wine(self):
        _, created = self.duplicate()
        name = created["photo"]["file"]
        status, moved = self.post("/api/testset-move", place="wine-a", file=name, to="__drawer__")
        self.assertEqual(status, 200, moved)
        status, moved = self.post("/api/testset-move", place="__drawer__",
                                  file=moved["photo"]["file"], to="wine-b")
        self.assertEqual(status, 200, moved)
        source = next(row for row in self.get_view()["rows"] if row["slug"] == "wine-a")["photos"]
        self.assertEqual(len(source), 1)
        self.assertEqual(source[0]["entry"]["label"], "positive")
        self.assertEqual(moved["photo"]["sha256"], source[0]["sha256"])

    def test_duplicate_after_move_and_positive_label_adds_an_accepted_answer(self):
        _, created = self.duplicate()
        _, moved = self.post("/api/testset-move", place="wine-a",
                              file=created["photo"]["file"], to="wine-b")
        self.post("/api/testset-label", place="wine-b", file=moved["photo"]["file"], label="positive")
        with sqlite3.connect(self.db) as conn:
            conn.execute("UPDATE wine_catalog SET state='Active', removed_by=NULL WHERE wine_slug='wine-b'")
            rows, _ = benchmark.build_queries(conn, self.db, "my")
        same = [row for row in rows if row["image_sha256"] == created["photo"]["sha256"]]
        self.assertEqual(len(same), 2)
        self.assertTrue(all(row["truth"] == ["wine-a", "wine-b"] for row in same))

    def test_invalid_and_stale_requests_do_not_add_entries(self):
        before = self.get_view()
        for values, expected in (({"place": None}, 400), ({"file": None}, 400),
                                  ({"file": "missing.jpg"}, 404), ({"place": "../wine-a"}, 404),
                                  ({"sha256": "0" * 64}, 409), ({"sha256": True}, 400)):
            status, _ = self.duplicate(**values)
            self.assertEqual(status, expected)
        self.assertEqual(self.request("/api/testset-duplicate", "POST",
                         {"set": "missing", "place": "wine-a", "file": "01.jpg"})[0], 404)
        self.assertEqual(self.request("/api/testset-duplicate")[0], 405)
        self.assertEqual(self.get_view(), before)

    def test_failure_rolls_back_the_new_entry(self):
        before = self.get_view()
        with mock.patch.object(testsets, "_edited", side_effect=sqlite3.OperationalError("controlled fault")):
            self.assertEqual(self.duplicate()[0], 503)
        self.assertEqual(self.get_view(), before)

    def test_duplicate_of_drawer_and_no_match_entries_has_independent_names(self):
        for place in ("__null__", "__drawer__"):
            with self.subTest(place=place):
                if place == "__drawer__":
                    self.post("/api/testset-move", place="__null__", file="n1.jpg", to=place)
                status, answer = self.duplicate(place=place, file="n1.jpg")
                self.assertEqual(status, 200, answer)
                self.assertEqual(answer["photo"]["file"], "n1.jpg.duplicate2.jpg")


if __name__ == "__main__":
    unittest.main()
