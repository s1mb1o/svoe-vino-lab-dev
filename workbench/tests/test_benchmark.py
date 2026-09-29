import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import testset_fixture as FX  # noqa: E402
import benchmark as BM  # noqa: E402
import import_testset as IT  # noqa: E402
import match_scoring as MS  # noqa: E402

PHOTOS = {
    "wine-a/01.jpg": b"a1", "wine-a/02.jpg": b"a2", "wine-a/03.jpg": b"a3",
    "wine-b/01.jpg": b"b1", "wine-b/02.jpg": b"b2", "wine-b/03.jpg": b"b3",
    "__null__/n1.jpg": b"n1", "__null__/n2.jpg": b"n2",
}
LABELS = {
    "wine-a": {"01.jpg": {"label": "positive"}, "02.jpg": {"label": "negative"},
               "03.jpg": {"label": "positive", "delete": True}},
    "wine-b": {"01.jpg": {"label": "positive"}, "02.jpg": {"label": "variant"},
               "03.jpg": {"label": "unusable"}},
    "__null__": {"n1.jpg": {"label": "positive"}, "n2.jpg": {"label": "unusable"}},
}


class FakeBackend:
    """A backend that answers from a table: image path suffix -> slugs."""

    def __init__(self, answers):
        self.id = "fake"
        self.spec = {"id": "fake", "url": "http://127.0.0.1:9/none", "workers": 1, "top_k": 10}
        self.top_k = 10
        self.answers = answers
        self.asked = []

    def ask(self, path):
        self.asked.append(path)
        with open(path, "rb") as fh:
            key = fh.read().decode()
        slugs = self.answers.get(key, [])
        return ([{"slug": s, "score": 1.0 - i / 10, "rank": i + 1} for i, s in enumerate(slugs)],
                5, 200, None)


class BenchmarkTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.db, self.schema = FX.make_database(self.root)
        set_dir = FX.write_set(self.root, PHOTOS, LABELS, groups=[["wine-a", "wine-b"]])
        IT.import_testset(self.db, "my", set_dir, lambda m: None, self.schema)
        self.runs = self.root / "runs"

    def tearDown(self):
        self.directory.cleanup()

    def queries(self):
        conn = BM.open_database(self.db, self.schema)
        try:
            return BM.build_queries(conn, self.db, "my")
        finally:
            conn.close()

    def test_the_query_set_follows_match_run(self):
        rows, skipped = self.queries()
        self.assertEqual([(r["query_id"], r["image_path"], r["label"], r["truth"]) for r in rows], [
            ("q-000001", "__null__/n1.jpg", "no_match", []),
            ("q-000002", "wine-a/01.jpg", "positive", ["wine-a"]),
            ("q-000003", "wine-a/02.jpg", "negative", []),
            ("q-000004", "wine-b/01.jpg", "positive", ["wine-b"]),
        ])
        self.assertEqual(dict(skipped), {"unusable": 2, "marked for deletion": 1, "variant": 1})
        self.assertTrue(all(Path(r["abs_path"]).is_file() for r in rows))

    def test_an_old_exclusion_leaves_no_photo_out(self):
        # Plan 51 (owner answer of 2026-09-26T18:08:34+0300): the exclusion went away. The
        # reason of an old excluded-slugs.json is a wine comment, and the photo enters.
        set_dir = FX.write_set(self.root, {"wine-c/01.jpg": b"c1", "__null__/n9.jpg": b"n9"},
                               {"wine-c": {"01.jpg": {"label": "positive"}}},
                               excluded={"wine-c": {"reason": "r"}, "__null__": "all"},
                               name="old")
        IT.import_testset(self.db, "old", set_dir, lambda m: None, self.schema)
        conn = BM.open_database(self.db, self.schema)
        try:
            rows, skipped = BM.build_queries(conn, self.db, "old")
        finally:
            conn.close()
        self.assertEqual([(r["image_path"], r["label"]) for r in rows],
                         [("__null__/n9.jpg", "no_match"), ("wine-c/01.jpg", "positive")])
        self.assertEqual(dict(skipped), {})

    def test_the_run_writes_the_files_of_match_run(self):
        backend = FakeBackend({"a1": ["wine-a"], "a2": ["wine-a"], "b1": ["wine-a", "wine-b"]})
        run_dir, met = BM.run_benchmark(self.db, "my", backend, str(self.runs), embeddings={},
                                        log=lambda m: None, schema_dir=self.schema)
        names = sorted(p.name for p in Path(run_dir).iterdir())
        self.assertEqual(names, ["metrics.json", "predictions.jsonl", "queries.jsonl",
                                 "queries.tsv", "results.jsonl", "run.json", "summary.md"])
        queries = [json.loads(line) for line in (Path(run_dir) / "queries.jsonl").read_text().splitlines()]
        self.assertEqual(set(queries[0]), {"query_id", "image_path", "image_sha256", "slug",
                                           "label", "truth"})
        results = [json.loads(line) for line in (Path(run_dir) / "results.jsonl").read_text().splitlines()]
        self.assertEqual([(r["image_path"], r["outcome"], r["rank_of_truth"]) for r in results], [
            ("__null__/n1.jpg", "no_answer", None),
            ("wine-a/01.jpg", "hit", 1),
            ("wine-a/02.jpg", "false_match_at_1", 1),
            ("wine-b/01.jpg", "miss", 2),
        ])
        run = json.loads((Path(run_dir) / "run.json").read_text())
        self.assertEqual((run["tool"], run["options"]["set"], run["answered"]),
                         ("pipeline/benchmark.py", "my", 4))
        self.assertEqual(run["query_set"], {"total": 4, "negative": 1, "no_match": 1, "positive": 2})
        self.assertIn("-lab-fake-my", run["run_id"])

    def test_the_metrics_are_the_metrics_of_match_scoring(self):
        backend = FakeBackend({"a1": ["wine-a"], "b1": ["wine-a", "wine-b"]})
        run_dir, met = BM.run_benchmark(self.db, "my", backend, str(self.runs), embeddings={},
                                        log=lambda m: None, schema_dir=self.schema)
        results = [json.loads(line) for line in (Path(run_dir) / "results.jsonl").read_text().splitlines()]
        again = MS.metrics_of(results, backend, 10, False, met["wall_s"], 1,
                              groups={"wine-a": {"wine-a", "wine-b"}, "wine-b": {"wine-a", "wine-b"}})
        again["run_id"] = met["run_id"]
        self.assertEqual(again, json.loads((Path(run_dir) / "metrics.json").read_text()))
        # wine-b/01 answered wine-a at rank 1, and wine-a is in the group of wine-b.
        self.assertEqual(met["positive"]["near_duplicate_confusion"], 1)

    def test_limit_sends_the_first_queries_alone(self):
        backend = FakeBackend({})
        BM.run_benchmark(self.db, "my", backend, str(self.runs), limit=2, embeddings={},
                         log=lambda m: None, schema_dir=self.schema)
        self.assertEqual(len(backend.asked), 2)

    def test_an_unknown_set_is_an_error(self):
        with self.assertRaisesRegex(BM.BenchmarkError, "no test set 'none'"):
            BM.run_benchmark(self.db, "none", FakeBackend({}), str(self.runs), embeddings={},
                             log=lambda m: None, schema_dir=self.schema)

    def test_a_wrong_schema_version_is_an_error(self):
        conn = sqlite3.connect(self.db)
        conn.execute("PRAGMA user_version = 1")
        conn.close()
        with self.assertRaisesRegex(BM.BenchmarkError, "schema version 1"):
            BM.open_database(self.db, self.schema)

    def test_the_runner_does_not_write_to_the_database(self):
        before = Path(self.db).read_bytes()
        BM.run_benchmark(self.db, "my", FakeBackend({}), str(self.runs), embeddings={},
                         log=lambda m: None, schema_dir=self.schema)
        self.assertEqual(Path(self.db).read_bytes(), before)

    def test_a_photo_of_another_folder_gets_the_path_of_that_folder(self):
        # The bytes of a test photo MAY be a catalogue image that `image` held before the
        # import. The row then keeps its folder, for example `main`.
        row = next(r for r in self.queries()[0] if r["image_path"] == "wine-a/01.jpg")
        source = Path(row["abs_path"])
        self.assertEqual(source.parent.parts[-2:], ("testsets", "images"))
        target = Path(self.db).parent / "images" / "main" / source.name
        target.parent.mkdir(parents=True)
        source.rename(target)
        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE image SET folder = 'main' WHERE sha256 = ?", (row["image_sha256"],))
        conn.commit()
        conn.close()
        row = next(r for r in self.queries()[0] if r["image_path"] == "wine-a/01.jpg")
        self.assertEqual(Path(row["abs_path"]), target)

    def test_run_json_holds_the_configuration_only_when_it_is_given(self):
        # Plan 23: the Runs page filters the runs by the key `configuration` of run.json.
        plain, _ = BM.run_benchmark(self.db, "my", FakeBackend({}), str(self.runs),
                                    embeddings={}, log=lambda m: None, schema_dir=self.schema)
        named, _ = BM.run_benchmark(self.db, "my", FakeBackend({}), str(self.runs),
                                    embeddings={}, label="named", log=lambda m: None,
                                    schema_dir=self.schema, configuration="mock")
        plain_meta = json.loads(Path(plain, "run.json").read_text(encoding="utf-8"))
        named_meta = json.loads(Path(named, "run.json").read_text(encoding="utf-8"))
        self.assertNotIn("configuration", plain_meta)
        self.assertEqual(named_meta["configuration"], "mock")

    def test_run_json_holds_use_cache_only_when_it_is_given(self):
        # Plan 39: the checkbox `Use caches` of the dialog `Run>`.
        metas = {}
        for label, use_cache in ((None, None), ("live", False), ("cached", True)):
            run_dir, _ = BM.run_benchmark(self.db, "my", FakeBackend({}), str(self.runs),
                                          embeddings={}, label=label, log=lambda m: None,
                                          schema_dir=self.schema, use_cache=use_cache)
            metas[label] = json.loads(Path(run_dir, "run.json").read_text(encoding="utf-8"))
        self.assertNotIn("use_cache", metas[None])
        self.assertIs(metas["live"]["use_cache"], False)
        self.assertIs(metas["cached"]["use_cache"], True)

    def test_a_fifth_value_of_ask_is_the_trace_of_the_row(self):
        # Plan 41: the step trace of the embedding runner. A backend of four values gets no
        # key `trace`.
        class Tracing(FakeBackend):
            def ask(self, path):
                return super().ask(path) + ({"v": 1, "steps": [{"id": "input", "ms": 1.0}]},)

        plain, _ = BM.run_benchmark(self.db, "my", FakeBackend({"a1": ["wine-a"]}),
                                    str(self.runs), embeddings={}, log=lambda m: None,
                                    schema_dir=self.schema)
        traced, _ = BM.run_benchmark(self.db, "my", Tracing({"a1": ["wine-a"]}), str(self.runs),
                                     embeddings={}, label="traced", log=lambda m: None,
                                     schema_dir=self.schema)
        rows = {name: [json.loads(line) for line in
                       Path(run_dir, "results.jsonl").read_text().splitlines()]
                for name, run_dir in (("plain", plain), ("traced", traced))}
        self.assertTrue(all("trace" not in row for row in rows["plain"]))
        self.assertEqual([row["trace"]["steps"][0]["id"] for row in rows["traced"]],
                         ["input"] * 4)
        self.assertEqual([row["outcome"] for row in rows["traced"]],
                         [row["outcome"] for row in rows["plain"]])

    def test_the_photos_of_a_removed_wine_leave_the_run_until_a_restore(self):
        # Owner answer of 2026-09-25T17:13:17+0300 (plan 24).
        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE wine_catalog SET state = 'Removed', removed_by = 'person' "
                     "WHERE wine_slug = 'wine-a'")
        conn.commit()
        rows, skipped = self.queries()
        self.assertNotIn("wine-a", {r["slug"] for r in rows})
        self.assertEqual(skipped["removed wine"], 3)
        self.assertEqual(self.query_count("wine-a"), 3)
        conn.execute("UPDATE wine_catalog SET state = 'Active', removed_by = NULL "
                     "WHERE wine_slug = 'wine-a'")
        conn.commit()
        conn.close()
        rows, skipped = self.queries()
        self.assertEqual(sum(r["slug"] == "wine-a" for r in rows), 2)
        self.assertNotIn("removed wine", skipped)

    def test_the_photos_of_a_wine_outside_the_dataset_leave_the_run(self):
        # Plan 87 (owner answer of 2026-09-29T19:25:36+0300): each wine of the jury test
        # set is in the dataset. A disabled wine and a place that wine_catalog does not
        # hold are outside it, whatever the label. An Active manual wine is in it, as any
        # other Active wine (owner message of 2026-09-29T19:42:59+0300).
        conn = sqlite3.connect(self.db)
        conn.execute("INSERT INTO wine_catalog (wine_slug, name, producer, category, color, "
                     "region, description, csv_photo_name) VALUES ('__hand-made', 'n', 'p', "
                     "'c', 'co', 'r', 'd', 'x.webp')")
        conn.commit()
        set_dir = FX.write_set(
            self.root, {"wine-a/01.jpg": b"oa1", "wine-c/01.jpg": b"oc1",
                        "wine-c/02.jpg": b"oc2", "__hand-made/01.jpg": b"oh1",
                        "wine-z/01.jpg": b"oz1"},
            {"wine-a": {"01.jpg": {"label": "positive"}},
             "wine-c": {"01.jpg": {"label": "positive"}, "02.jpg": {"label": "negative"}},
             "__hand-made": {"01.jpg": {"label": "positive"}},
             "wine-z": {"01.jpg": {"label": "positive"}}}, name="out")
        IT.import_testset(self.db, "out", set_dir, lambda m: None, self.schema)
        conn.execute("UPDATE wine_catalog SET state = 'Disabled' WHERE wine_slug = 'wine-c'")
        conn.commit()

        def queries():
            db = BM.open_database(self.db, self.schema)
            try:
                return BM.build_queries(db, self.db, "out")
            finally:
                db.close()

        rows, skipped = queries()
        self.assertEqual([(r["image_path"], r["truth"]) for r in rows],
                         [("__hand-made/01.jpg", ["__hand-made"]),
                          ("wine-a/01.jpg", ["wine-a"])])
        self.assertEqual(dict(skipped), {"disabled wine": 2, "wine not in the catalogue": 1})
        conn.execute("UPDATE wine_catalog SET state = 'Active' WHERE wine_slug = 'wine-c'")
        conn.execute("UPDATE wine_catalog SET state = 'Disabled' "
                     "WHERE wine_slug = '__hand-made'")
        conn.commit()
        conn.close()
        rows, skipped = queries()
        self.assertEqual([(r["image_path"], r["label"]) for r in rows],
                         [("wine-a/01.jpg", "positive"), ("wine-c/01.jpg", "positive"),
                          ("wine-c/02.jpg", "negative")])
        self.assertEqual(dict(skipped), {"disabled wine": 1, "wine not in the catalogue": 1})

    def query_count(self, place):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute("SELECT count(*) FROM test_photo WHERE place = ?",
                                (place,)).fetchone()[0]
        finally:
            conn.close()

    def test_a_null_photo_with_no_label_is_a_no_match_query(self):
        # Plan 36 (owner answer of 2026-09-26T00:29:00+0300): the place `__null__` is the
        # row "No Match", so a NULL photo needs no label, as in match_run.py.
        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE test_photo SET label = NULL WHERE place = '__null__' AND "
                     "file_name = 'n1.jpg'")
        conn.commit()
        conn.close()
        rows, skipped = self.queries()
        by_path = {r["image_path"]: r for r in rows}
        self.assertEqual((by_path["__null__/n1.jpg"]["label"],
                          by_path["__null__/n1.jpg"]["truth"]), ("no_match", []))
        self.assertNotIn("unconfirmed NULL", skipped)

    def test_a_drawer_photo_is_never_a_query(self):
        # Plan 36: the Drawer keeps a photo for a later wine; no run uses it.
        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE test_photo SET place = '__drawer__' WHERE place = '__null__' "
                     "AND file_name = 'n1.jpg'")
        conn.commit()
        conn.close()
        rows, skipped = self.queries()
        self.assertFalse([r for r in rows if r["image_path"].startswith("__drawer__/")])
        self.assertEqual(skipped["drawer"], 1)


if __name__ == "__main__":
    unittest.main()
