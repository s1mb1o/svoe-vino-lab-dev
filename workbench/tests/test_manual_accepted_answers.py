"""Verify manual accepted answers for exact images in one Workbench testset."""
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
import test_benchmark as baseline  # noqa: E402


class ManualAcceptedAnswersTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.db, self.schema = FX.make_database(self.root)
        photos = {"wine-a/front.jpg": b"same", "wine-b/other-name.jpg": b"same",
                  "wine-c/front.jpg": b"different"}
        labels = {slug: {name: {"label": "positive"}}
                  for slug, name in (path.split("/") for path in photos)}
        self.import_set("my", photos, labels)

    def import_set(self, name, photos, labels):
        source = FX.write_set(self.root, photos, labels, name=name)
        IT.import_testset(self.db, name, source, lambda message: None, self.schema)

    def query_rows(self, name="my"):
        with sqlite3.connect(self.db) as conn:
            return BM.build_queries(conn, self.db, name)[0]

    def benchmark(self, answers, **options):
        backend = baseline.FakeBackend(answers)
        path, metrics = BM.run_benchmark(
            self.db, "my", backend, str(self.root / "runs"), embeddings={},
            log=lambda message: None, schema_dir=self.schema, **options)
        return Path(path), metrics, backend

    def test_exact_image_assignments_share_truth_and_keep_row_identity(self):
        rows = self.query_rows()
        self.assertEqual([(row["query_id"], row["image_path"], row["truth"]) for row in rows], [
            ("q-000001", "wine-a/front.jpg", ["wine-a", "wine-b"]),
            ("q-000002", "wine-b/other-name.jpg", ["wine-a", "wine-b"]),
            ("q-000003", "wine-c/front.jpg", ["wine-c"]),
        ])
        self.assertEqual(rows[0]["image_sha256"], rows[1]["image_sha256"])

    def test_either_manual_answer_is_correct_for_each_assignment(self):
        for row in self.query_rows()[:2]:
            for slug in ("wine-a", "wine-b"):
                with self.subTest(place=row["slug"], answer=slug):
                    verdict = MS.judge(row, [{"slug": slug}], False)
                    self.assertEqual((verdict["outcome"], verdict["rank_of_truth"]), ("hit", 1))
            verdict = MS.judge(row, [{"slug": "wine-c"}, {"slug": "wine-b"}], False)
            self.assertEqual((verdict["outcome"], verdict["rank_of_truth"]), ("miss", 2))

    def test_other_labels_and_deleted_assignments_supply_no_accepted_answer(self):
        for label, deleted in ((None, 0), ("variant", 0), ("negative", 0),
                               ("unusable", 0), ("positive", 1)):
            with self.subTest(label=label, deleted=deleted):
                with sqlite3.connect(self.db) as conn:
                    conn.execute("UPDATE test_photo SET label = ?, marked_delete = ? "
                                 "WHERE set_name = 'my' AND place = 'wine-b'", (label, deleted))
                rows = self.query_rows()
                self.assertEqual(rows[0]["truth"], ["wine-a"])
                if label == "negative" and not deleted:
                    negative = next(row for row in rows if row["slug"] == "wine-b")
                    self.assertEqual(negative["truth"], [])
                    self.assertEqual(MS.judge(negative, [{"slug": "wine-b"}], False)["outcome"],
                                     "false_match_at_1")

    def test_inactive_and_missing_catalogue_wines_supply_no_accepted_answer(self):
        for state in ("Disabled", "Removed"):
            with self.subTest(state=state):
                with sqlite3.connect(self.db) as conn:
                    conn.execute("UPDATE wine_catalog SET state = ?, removed_by = ? "
                                 "WHERE wine_slug = 'wine-b'",
                                 (state, "person" if state == "Removed" else None))
                self.assertEqual(self.query_rows()[0]["truth"], ["wine-a"])
        with sqlite3.connect(self.db) as conn:
            conn.execute("DELETE FROM wine_catalog WHERE wine_slug = 'wine-b'")
        self.assertEqual(self.query_rows()[0]["truth"], ["wine-a"])

    def test_positive_assignment_in_another_testset_does_not_supply_an_answer(self):
        self.import_set("other", {"wine-c/copy.jpg": b"same"},
                        {"wine-c": {"copy.jpg": {"label": "positive"}}})
        self.assertEqual(self.query_rows()[0]["truth"], ["wine-a", "wine-b"])
        self.assertEqual(self.query_rows("other")[0]["truth"], ["wine-c"])

    def test_no_match_and_drawer_do_not_supply_accepted_answers(self):
        self.import_set("special", {"wine-a/front.jpg": b"same", "__null__/copy.jpg": b"same",
                                    "__drawer__/copy.jpg": b"same"},
                        {slug: {name: {"label": "positive"}} for slug, name in
                         (("wine-a", "front.jpg"), ("__null__", "copy.jpg"),
                          ("__drawer__", "copy.jpg"))})
        rows = self.query_rows("special")
        self.assertEqual([(row["slug"], row["truth"]) for row in rows],
                         [("__null__", []), ("wine-a", ["wine-a"])])
        self.assertEqual(MS.judge(rows[0], [{"slug": "wine-a"}], False)["outcome"],
                         "false_match_at_1")

    def test_same_file_name_with_different_bytes_does_not_share_truth(self):
        rows = self.query_rows()
        self.assertEqual(rows[2]["truth"], ["wine-c"])
        self.assertNotEqual(rows[0]["image_sha256"], rows[2]["image_sha256"])

    def test_repeated_assignment_under_one_slug_does_not_duplicate_truth(self):
        with sqlite3.connect(self.db) as conn:
            conn.execute("INSERT INTO test_photo (set_name, place, file_name, sha256, label) "
                         "SELECT set_name, place, 'second.jpg', sha256, label FROM test_photo "
                         "WHERE set_name = 'my' AND place = 'wine-a'")
        rows = self.query_rows()
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(row["truth"] == ["wine-a", "wine-b"]
                            for row in rows if row["slug"] != "wine-c"))

    def test_run_persists_accepted_answers_and_scores_both_assignments_as_hits(self):
        before = Path(self.db).read_bytes()
        path, metrics, backend = self.benchmark({"same": ["wine-b"], "different": ["wine-c"]})
        queries = [json.loads(line) for line in (path / "queries.jsonl").read_text().splitlines()]
        results = [json.loads(line) for line in (path / "results.jsonl").read_text().splitlines()]
        self.assertEqual([row["truth"] for row in queries],
                         [["wine-a", "wine-b"], ["wine-a", "wine-b"], ["wine-c"]])
        self.assertEqual([row["truth"] for row in results], [row["truth"] for row in queries])
        self.assertEqual([row["outcome"] for row in results], ["hit"] * 3)
        self.assertEqual(metrics["positive"]["recall_at_1"], 1.0)
        self.assertEqual(metrics["positive"]["near_duplicate_confusion"], 0)
        self.assertEqual(len(backend.asked), 3)
        self.assertEqual(Path(self.db).read_bytes(), before)

    def test_limit_does_not_remove_an_accepted_answer_from_an_unasked_assignment(self):
        path, metrics, backend = self.benchmark({"same": ["wine-b"]}, limit=1)
        query = json.loads((path / "queries.jsonl").read_text().strip())
        self.assertEqual(query["truth"], ["wine-a", "wine-b"])
        self.assertEqual(metrics["positive"]["recall_at_1"], 1.0)
        self.assertEqual(len(backend.asked), 1)

    def test_repeat_does_not_reuse_verdicts_with_different_accepted_answers(self):
        row = self.query_rows()[0]
        old = dict(row, truth=["wine-a"], outcome="hit", error=None)
        earlier = self.root / "earlier"
        earlier.mkdir()
        (earlier / "results.jsonl").write_text(json.dumps(old) + "\n")
        copied, asked, plan = BM.repeat_plan([row], str(earlier))
        self.assertEqual(copied, [])
        self.assertEqual(asked, [row])
        self.assertEqual(plan["new"], 1)
        with sqlite3.connect(self.db) as conn:
            conn.execute("UPDATE test_photo SET label = NULL "
                         "WHERE set_name = 'my' AND place = 'wine-b'")
        self.assertFalse(BM.same_query(self.query_rows()[0], row))


if __name__ == "__main__":
    unittest.main()
