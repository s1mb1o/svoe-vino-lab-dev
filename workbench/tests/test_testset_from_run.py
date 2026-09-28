"""A new test set from the misses of a run (plan 44): `pipeline/testset_from_run.py`
through the routes of `pipeline/testset_routes.py` on the lab server."""
import hashlib
import io
import json
import os
import sqlite3
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import testset_fixture as FX  # noqa: E402
import benchmark  # noqa: E402
import import_testset as IT  # noqa: E402
import lab_server as LAB  # noqa: E402


def jpeg(width):
    buffer = io.BytesIO()
    Image.new("RGB", (width, 40), "white").save(buffer, "JPEG")
    return buffer.getvalue()


PHOTOS = {"wine-a/01.jpg": jpeg(60), "wine-a/02.jpg": jpeg(61), "wine-a/03.jpg": jpeg(62),
          "wine-b/01.jpg": jpeg(63), "wine-b/02.jpg": jpeg(64), "wine-c/01.jpg": jpeg(65),
          "wine-c/02.jpg": jpeg(66), "__null__/n1.jpg": jpeg(67)}
LABELS = {
    "wine-a": {"01.jpg": {"label": "positive", "comment": "a1", "ts": "t1"},
               "02.jpg": {"label": "positive", "box": [1, 2, 30, 20]},
               "03.jpg": {"label": "positive"}},
    # The run saw wine-b/01.jpg as positive; the set holds `negative` now.
    "wine-b": {"01.jpg": {"label": "negative"}, "02.jpg": {"label": "positive"}},
    "wine-c": {"01.jpg": {"label": "positive", "source_url": "http://x", "custom": 5},
               "02.jpg": {"label": "negative"}},
}
SOURCE_NOTE = "the note of the set my"
RUN = "2026-09-26T100000Z-lab-mock-my"
NO_SET_RUN = "2026-09-26T090000Z-old"
DRY_RUN = "2026-09-26T100500Z-lab-mock-my-dry"
LOST_SET_RUN = "2026-09-26T101000Z-lab-mock-lost"
HIT_RUN = "2026-09-26T101500Z-lab-mock-my-hits"
MY1_RUN = "2026-09-26T102000Z-lab-mock-my-1"


def sha(relative):
    return hashlib.sha256(PHOTOS[relative]).hexdigest()


def row(path, rank, label="positive", digest=None, error=None):
    slug = path.rpartition("/")[0]
    return {"query_id": "q-" + path, "image_path": path,
            "image_sha256": digest or sha(path), "slug": slug, "label": label,
            "truth": [slug] if label == "positive" else [], "rank_of_truth": rank,
            "error": error, "candidates": []}


ROWS = [
    row("wine-a/01.jpg", 2),                     # an R@1 miss alone; copied
    row("wine-a/02.jpg", None),                  # an R@1 and an R@5 miss; copied
    row("wine-a/03.jpg", 4, digest="0" * 64),    # an R@1 miss; other bytes
    row("wine-b/01.jpg", 7),                     # an R@1 and an R@5 miss; label changed
    row("wine-b/02.jpg", 1),                     # a hit
    row("wine-c/01.jpg", None, error="timeout"),  # a failed request; copied
    row("wine-c/gone.jpg", 3, digest="1" * 64),  # an R@1 miss; gone
    row("wine-c/02.jpg", 1, label="negative"),   # a negative photo is never selected
    row("__null__/n1.jpg", None, label="no_match"),
]
R1_COPY = ["wine-a/01.jpg", "wine-a/02.jpg", "wine-c/01.jpg"]


class TestsetFromRunTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.db, self.schema = FX.make_database(self.root)
        set_dir = FX.write_set(self.root, PHOTOS, LABELS,
                               excluded={"wine-b": {"reason": "bad photo", "ts": "t"}},
                               groups=[["wine-a", "wine-b"]])
        (Path(set_dir) / "review-labels.json").write_text(json.dumps({
            "version": 2, "labels": LABELS, "note": SOURCE_NOTE,
            "wines": {"wine-a": {"comment": "note a"}, "wine-b": {"comment": "note b"}}}),
            encoding="utf-8")
        IT.import_testset(self.db, "my", set_dir, lambda m: None, self.schema)
        self.runs = self.root / "runs"
        self.write_run(RUN, {"options": {"set": "my", "dry_run": False}}, ROWS)
        self.write_run(NO_SET_RUN, {"options": {"backend": "svm-x"}}, ROWS)
        self.write_run(DRY_RUN, {"options": {"set": "my", "dry_run": True}}, ROWS)
        self.write_run(LOST_SET_RUN, {"options": {"set": "lost"}}, ROWS)
        self.write_run(HIT_RUN, {"options": {"set": "my"}}, [row("wine-b/02.jpg", 1)])
        self.write_run(MY1_RUN, {"options": {"set": "my-1"}}, [row("wine-a/01.jpg", 3)])
        self.server = LAB.make_server(self.db, port=0)
        self.server.runs_dir = str(self.runs)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = "http://127.0.0.1:%d" % self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.directory.cleanup()

    def write_run(self, run_id, meta, rows):
        directory = self.runs / run_id
        directory.mkdir(parents=True)
        (directory / "run.json").write_text(json.dumps(meta), encoding="utf-8")
        (directory / "results.jsonl").write_text(
            "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")

    def request(self, path, body=None):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(self.base + path, data=data,
                                     method="GET" if body is None else "POST",
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            with exc:
                return exc.code, json.loads(exc.read().decode("utf-8"))

    def dialog(self, run_id):
        return self.request("/api/testset-from-run?id=" + urllib.parse.quote(run_id))

    def create(self, run_id=RUN, misses="r1", name="my-1"):
        return self.request("/api/testset-from-run",
                            {"run": run_id, "misses": misses, "name": name})

    def query(self, sql, args=()):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute(sql, args).fetchall()
        finally:
            conn.close()

    def test_the_counts_of_the_dialog(self):
        status, view = self.dialog(RUN)
        self.assertEqual(status, 200, view)
        self.assertEqual((view["run"], view["set"], view["name"]), (RUN, "my", "my-1"))
        r1, r5 = view["misses"]["r1"], view["misses"]["r5"]
        self.assertEqual((r1["selected"], r1["copied"], r1["errors"]), (6, 3, 1))
        self.assertEqual(r1["left_out"], {"gone": 1, "other bytes": 1, "label changed": 1})
        self.assertEqual((r5["selected"], r5["copied"], r5["errors"]), (3, 2, 1))
        self.assertEqual(r5["left_out"], {"gone": 0, "other bytes": 0, "label changed": 1})
        self.assertEqual((r1["title"], r5["title"]), ("R@1 misses", "R@5 misses"))

    def test_a_new_set_copies_the_rows(self):
        status, answer = self.create()
        self.assertEqual(status, 200, answer)
        self.assertEqual((answer["set"], answer["source"], answer["photos"],
                          answer["photo_comments"], answer["variant_slugs"]),
                         ("my-1", "my", 3, 1, 2))
        # The notes of the wines and the exclusions are wine comments of no set (plan 51).
        self.assertFalse({"wine_notes", "excluded"} & set(answer))
        columns = [c[1] for c in self.query("PRAGMA table_info(test_photo)")
                   if c[1] != "set_name"]
        select = ("SELECT %s FROM test_photo WHERE set_name = ? ORDER BY place, file_name"
                  % ", ".join(columns))
        copied = self.query(select, ("my-1",))
        source = [r for r in self.query(select, ("my",)) if "%s/%s" % r[:2] in R1_COPY]
        self.assertEqual(copied, source)
        self.assertEqual(["%s/%s" % r[:2] for r in copied], R1_COPY)
        # the box and a field of `extra` came with the rows
        by_path = {"%s/%s" % r[:2]: dict(zip(columns, r)) for r in copied}
        self.assertEqual(by_path["wine-a/02.jpg"]["box_right"], 30)
        self.assertEqual(json.loads(by_path["wine-c/01.jpg"]["extra"]), {"custom": 5})
        # the comment of the photo came with it, with its time and its source (plan 51)
        comment = ("SELECT place, file_name, created_at, source, text FROM test_photo_comment "
                   "WHERE set_name = ?")
        self.assertEqual(self.query(comment, ("my-1",)), self.query(comment, ("my",)))
        self.assertEqual([r[-1] for r in self.query(comment, ("my-1",))], ["a1"])
        self.assertEqual(self.query("SELECT wine_slug, group_no FROM test_variant WHERE "
                                    "set_name = 'my-1' ORDER BY 1"),
                         [("wine-a", 0), ("wine-b", 0)])
        ((source_dir, edited_at, note),) = self.query(
            "SELECT source_dir, edited_at, label_note FROM test_set WHERE set_name = 'my-1'")
        self.assertEqual(source_dir, os.path.join(os.path.realpath(self.runs), RUN))
        self.assertTrue(edited_at)
        self.assertTrue(note.startswith("The set my-1 was built on %s from the R@1 misses "
                                        "of the run %s of the test set my" % (edited_at, RUN)))
        self.assertIn("Selected: 6, 1 of them with a failed request. Copied: 3. Left out: "
                      "gone 1, other bytes 1, label changed 1.", note)
        self.assertTrue(note.endswith("\n\n" + SOURCE_NOTE))
        # the Testset page reads the new set, and a run takes its photos
        status, view = self.request("/api/testset?set=my-1")
        self.assertEqual((status, view["counts"]["photos"]), (200, 3))
        conn = sqlite3.connect(self.db)
        try:
            queries, _ = benchmark.build_queries(conn, self.db, "my-1")
        finally:
            conn.close()
        self.assertEqual([(q["image_path"], q["label"]) for q in queries],
                         [(path, "positive") for path in R1_COPY])

    def test_the_r5_misses(self):
        status, answer = self.create(misses="r5", name="my-r5")
        self.assertEqual((status, answer["photos"]), (200, 2), answer)
        self.assertEqual(self.query("SELECT place || '/' || file_name FROM test_photo WHERE "
                                    "set_name = 'my-r5' ORDER BY 1"),
                         [("wine-a/02.jpg",), ("wine-c/01.jpg",)])

    def test_the_proposed_name(self):
        self.assertEqual(self.create(name="my-1")[0], 200)
        self.assertEqual(self.dialog(RUN)[1]["name"], "my-2")
        self.assertEqual(self.create(name="my-3")[0], 200)
        self.assertEqual(self.dialog(RUN)[1]["name"], "my-2")
        # a set with a number keeps the base name of its source (owner answer of 09:12:00)
        status, view = self.dialog(MY1_RUN)
        self.assertEqual((status, view["set"], view["name"]), (200, "my-1", "my-2"))

    def test_the_page_holds_the_button_and_the_dialog(self):
        with urllib.request.urlopen(self.base + "/runs") as response:
            page = response.read().decode("utf-8")
        for mark in ('id="nts-open"', 'id="nts-dlg"', 'id="nts-name"', 'id="nts-create"',
                     "/api/testset-from-run"):
            self.assertIn(mark, page)

    def test_the_refusals(self):
        self.assertEqual(self.dialog("2026-01-01T000000Z-none")[0], 404)
        self.assertEqual(self.dialog("../runs")[0], 404)
        self.assertEqual(self.dialog(NO_SET_RUN)[0], 409)
        self.assertEqual(self.dialog(DRY_RUN)[0], 409)
        self.assertEqual(self.dialog(LOST_SET_RUN)[0], 404)
        self.assertEqual(self.create(misses="r3")[0], 400)
        for name in ("My-1", "my 1", "", None, "my/1"):
            self.assertEqual(self.create(name=name)[0], 400, name)
        status, answer = self.create(name="my")
        self.assertEqual(status, 409)
        self.assertIn("exists already", answer["error"])
        status, answer = self.create(run_id=HIT_RUN)
        self.assertEqual(status, 409)
        self.assertIn("no photo to copy", answer["error"])
        self.assertEqual(self.create(run_id=NO_SET_RUN)[0], 409)
        # each refusal rolled back its transaction
        self.assertEqual(self.query("SELECT set_name FROM test_set"), [("my",)])
        self.assertEqual(self.query("SELECT count(*) FROM test_photo WHERE set_name <> 'my'"),
                         [(0,)])


if __name__ == "__main__":
    unittest.main()
