"""Tests of `pipeline/run_files.py`: the run files of `runs/` for the Runs page (plan 23)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import run_files as RF  # noqa: E402


def cand(slug, rank, score=None):
    return {"slug": slug, "rank": rank, "score": score}


ROWS = [
    {"query_id": "q-1", "image_path": "wine-a/01.jpg", "image_sha256": "a" * 64,
     "slug": "wine-a", "label": "positive", "truth": ["wine-a"], "rank_of_truth": 1,
     "outcome": "correct_at_1", "latency_ms": 30,
     "candidates": [cand("wine-a", 1, 0.9), cand("wine-b", 2, 0.5)]},
    {"query_id": "q-2", "image_path": "wine-b/01.jpg", "image_sha256": "b" * 64,
     "slug": "wine-b", "label": "positive", "truth": ["wine-b"], "rank_of_truth": None,
     "outcome": "absent", "latency_ms": 90, "candidates": [cand("wine-c", 1, 0.7)]},
    # the same bytes as q-1, negative for wine-b: the true wine wine-a stands below it
    {"query_id": "q-3", "image_path": "wine-b/02.jpg", "image_sha256": "a" * 64,
     "slug": "wine-b", "label": "negative", "truth": [], "rank_of_truth": 1,
     "outcome": "false_match_at_1", "latency_ms": 10,
     "candidates": [cand("wine-b", 1, 0.8), cand("wine-a", 2, 0.6)]},
]


class RunFilesTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.runs = Path(self.directory.name) / "runs"
        self.write_run("2026-09-25T100000Z-old", {"options": {"backend": "svm-x"}}, ROWS)
        self.write_run("2026-09-25T110000Z-lab-mock-my",
                       {"configuration": "mock", "options": {"backend": "mock"}}, ROWS[:1])
        (self.runs / ".hidden").mkdir()
        (self.runs / "a-file.txt").write_text("x", encoding="utf-8")

    def tearDown(self):
        self.directory.cleanup()

    def write_run(self, run_id, meta, rows):
        directory = self.runs / run_id
        directory.mkdir(parents=True)
        (directory / "run.json").write_text(json.dumps(meta), encoding="utf-8")
        (directory / "metrics.json").write_text(json.dumps(
            {"positive": {"n": 2, "recall_at_1": 0.5}}), encoding="utf-8")
        (directory / "results.jsonl").write_text(
            "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")

    def test_run_dirs_lists_the_directories_the_newest_first(self):
        self.assertEqual(RF.run_dirs(str(self.runs)),
                         ["2026-09-25T110000Z-lab-mock-my", "2026-09-25T100000Z-old"])
        self.assertEqual(RF.run_dirs(str(self.runs / "missing")), [])

    def test_run_path_refuses_a_path_outside_the_runs(self):
        runs = str(self.runs)
        for run_id in ("", ".", "..", "../x", "a/b", "/etc"):
            self.assertIsNone(RF.run_path(runs, run_id, "run.json"), run_id)
        self.assertIsNone(RF.run_path(runs, "2026-09-25T100000Z-old", "../../x"))
        self.assertTrue(RF.run_path(runs, "2026-09-25T100000Z-old", "run.json")
                        .endswith("run.json"))

    def test_run_head_holds_the_configuration(self):
        runs = str(self.runs)
        mock = RF.run_head(runs, "2026-09-25T110000Z-lab-mock-my")
        old = RF.run_head(runs, "2026-09-25T100000Z-old")
        self.assertEqual((mock["configuration"], mock["backend"]), ("mock", "mock"))
        self.assertEqual((old["configuration"], old["backend"]), (None, "svm-x"))
        self.assertEqual((old["positive"], old["recall_at_1"]), (2, 0.5))

    def test_run_head_holds_use_cache_as_a_boolean_alone(self):
        # The checkbox `Use caches` of the dialog `Run>` (plan 39).
        runs = str(self.runs)
        for run_id, value in (("2026-09-26T100000Z-live", False),
                              ("2026-09-26T110000Z-cached", True),
                              ("2026-09-26T120000Z-wrong", "no")):
            self.write_run(run_id, {"use_cache": value}, ROWS[:1])
        self.assertIs(RF.run_head(runs, "2026-09-26T100000Z-live")["use_cache"], False)
        self.assertIs(RF.run_head(runs, "2026-09-26T110000Z-cached")["use_cache"], True)
        self.assertIsNone(RF.run_head(runs, "2026-09-26T120000Z-wrong")["use_cache"])
        self.assertIsNone(RF.run_head(runs, "2026-09-25T100000Z-old")["use_cache"])

    def test_configuration_of_accepts_a_non_empty_string_alone(self):
        for meta, want in (({"configuration": "mock"}, "mock"), ({"configuration": ""}, None),
                           ({"configuration": 3}, None), ({}, None), (None, None)):
            self.assertEqual(RF.configuration_of(meta), want, meta)

    def test_run_rows_filters_sorts_and_adds_the_twin(self):
        runs, run_id = str(self.runs), "2026-09-25T100000Z-old"
        rows, total = RF.run_rows(runs, run_id)
        self.assertEqual(([r["query_id"] for r in rows], total), (["q-1", "q-2", "q-3"], 3))
        self.assertEqual(rows[2]["twin"]["verdict"], "below")
        self.assertEqual([r["query_id"] for r in RF.run_rows(runs, run_id, "absent")[0]],
                         ["q-2"])
        self.assertEqual([r["query_id"] for r in
                          RF.run_rows(runs, run_id, "negative_above_positive")[0]], ["q-3"])
        self.assertEqual([r["query_id"] for r in RF.run_rows(runs, run_id, "false_match")[0]],
                         ["q-3"])
        self.assertEqual([r["query_id"] for r in
                          RF.run_rows(runs, run_id, sort="latency_desc")[0]],
                         ["q-2", "q-1", "q-3"])
        self.assertEqual([r["query_id"] for r in RF.run_rows(runs, run_id, sort="worst")[0]],
                         ["q-3", "q-2", "q-1"])
        rows, total = RF.run_rows(runs, run_id, query="wine-b/", limit=1, offset=1)
        self.assertEqual(([r["query_id"] for r in rows], total), (["q-3"], 2))

    def test_run_result_finds_one_query(self):
        runs, run_id = str(self.runs), "2026-09-25T100000Z-old"
        self.assertEqual(RF.run_result(runs, run_id, "q-2")["slug"], "wine-b")
        self.assertIsNone(RF.run_result(runs, run_id, "q-9"))
        self.assertIsNone(RF.run_result(runs, "../x", "q-1"))


if __name__ == "__main__":
    unittest.main()
