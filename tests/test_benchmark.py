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
    "wine-c/01.jpg": b"c1",
    "__null__/n1.jpg": b"n1", "__null__/n2.jpg": b"n2",
}
LABELS = {
    "wine-a": {"01.jpg": {"label": "positive"}, "02.jpg": {"label": "negative"},
               "03.jpg": {"label": "positive", "delete": True}},
    "wine-b": {"01.jpg": {"label": "positive"}, "02.jpg": {"label": "variant"},
               "03.jpg": {"label": "unusable"}},
    "wine-c": {"01.jpg": {"label": "positive"}},
    "__null__": {"n2.jpg": {"label": "unusable"}},
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
        set_dir = FX.write_set(self.root, PHOTOS, LABELS, excluded={"wine-c": {"reason": "r"}},
                               groups=[["wine-a", "wine-b"]])
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
        self.assertEqual(dict(skipped), {"unusable": 2, "marked for deletion": 1, "variant": 1,
                                         "excluded slug": 1})
        self.assertTrue(all(Path(r["abs_path"]).is_file() for r in rows))

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
        self.assertEqual(source.parent.name, "testset")
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


if __name__ == "__main__":
    unittest.main()
