"""Check run index freshness, complete records, and bounded repeat reads."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import run_files as RF


class RunIndexTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runs = Path(self.tmp.name)
        self.directory = self.runs / "run"
        self.directory.mkdir()
        self.path = self.directory / "results.jsonl"
        self.rows = [
            {"query_id": "q1", "image_path": "винo/1.jpg", "image_sha256": "same",
             "slug": "a", "label": "positive", "rank_of_truth": 1,
             "trace": [{"image": "full trace"}], "latency_ms": 30,
             "candidates": [{"slug": "a", "rank": 1, "score": .9,
                             "items": [{"vector": [1, 2]}]}]},
            {"query_id": "q2", "image_path": "b/2.jpg", "image_sha256": "same",
             "slug": "b", "label": "negative", "rank_of_truth": 1,
             "outcome": "false_match_at_1", "latency_ms": 10,
             "candidates": [{"slug": "b", "rank": 1, "score": .8,
                             "explain": {"kind": "cluster_rules", "changed": True,
                                         "questions": [{"text": "full explanation"}]}},
                            {"slug": "a", "rank": 2}]},
            {"query_id": "q3", "image_path": "c/3.jpg", "predicted_slug": "match-c",
             "label": "positive", "slug": "c", "rank_of_truth": None,
             "error": "failed", "latency_ms": 90, "candidates": []},
        ]
        self.write(self.rows)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rows):
        self.path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))

    def read(self, **options):
        return RF.run_rows(str(self.runs), "run", **options)

    def test_filter_sort_and_twin_results_keep_their_meaning(self):
        for mode, ids in [("all", ["q1", "q2", "q3"]), ("hit", ["q1"]),
                          ("error", ["q3"]), ("absent", ["q3"]),
                          ("negative_above_positive", ["q2"]),
                          ("rule_acted", ["q2"]), ("rule_changed", ["q2"])]:
            with self.subTest(mode=mode):
                rows, total = self.read(mode=mode)
                self.assertEqual([r["query_id"] for r in rows], ids)
                self.assertEqual(total, len(ids))
        for sort, ids in [("latency_desc", ["q3", "q1", "q2"]),
                          ("score_desc", ["q1", "q2", "q3"]),
                          ("score_asc", ["q2", "q1", "q3"]),
                          ("worst", ["q2", "q3", "q1"])]:
            self.assertEqual([r["query_id"] for r in self.read(sort=sort)[0]], ids)
        self.assertEqual(self.read(query="MATCH-C")[1], 1)
        self.assertEqual(self.read()[0][1]["twin"]["verdict"], "below")

    def test_repeat_requests_decode_only_the_page_and_one_selected_query(self):
        self.read()
        with patch.object(RF.json, "loads", wraps=json.loads) as loads:
            rows, total = self.read(limit=1, offset=1)
            one = RF.run_result(str(self.runs), "run", "q3")
            self.assertEqual(loads.call_count, 2)
        self.assertEqual((rows[0]["query_id"], total, one["query_id"]), ("q2", 3, "q3"))

    def test_direct_query_does_not_scan_the_remaining_run(self):
        with patch.object(RF.json, "loads", wraps=json.loads) as loads:
            one = RF.run_result(str(self.runs), "run", "q1")
        self.assertEqual(loads.call_count, 1)
        self.assertEqual(one, self.rows[0])

    def test_unfiltered_manifest_page_needs_no_filter_pass(self):
        self.read()
        with patch.object(RF, "row_matches", side_effect=AssertionError("filter scan")):
            rows, total = self.read(limit=1, offset=1)
        self.assertEqual((rows[0]["query_id"], total), ("q2", 3))

    def test_cold_query_uses_saved_offsets_and_observes_source_changes(self):
        self.read()
        RF._RESULT_CACHE.clear()
        RF._QUERY_CACHE.clear()
        with patch.object(RF.json, "loads", wraps=json.loads) as decode:
            one = RF.run_result(str(self.runs), "run", "q3")
        self.assertEqual(one, self.rows[2])
        self.assertEqual(decode.call_count, 2)  # Offset table and selected record.
        RF._RESULT_CACHE.clear()
        RF._QUERY_CACHE.clear()
        with patch.object(RF.json, "loads", wraps=json.loads) as decode:
            self.assertIsNone(RF.run_result(str(self.runs), "run", "unknown"))
        self.assertEqual(decode.call_count, 1)
        with self.path.open("a") as output:
            output.write(json.dumps({"query_id": "q4", "image_path": "added"}) + "\n")
        self.assertEqual(RF.run_result(str(self.runs), "run", "q4")["image_path"], "added")
        self.read()
        old = self.path.stat()
        self.path.write_bytes(self.path.read_bytes().replace(b'"q3"', b'"qx"'))
        os.utime(self.path, ns=(old.st_atime_ns, old.st_mtime_ns))
        self.assertIsNone(RF.run_result(str(self.runs), "run", "q3"))
        self.assertEqual(RF.run_result(str(self.runs), "run", "qx")["query_id"], "qx")

    def test_corrupt_offset_table_is_repaired_from_the_saved_row_summary(self):
        self.read()
        directory = self.runs / ".row-index-cache" / "queries-v1"
        next(directory.glob("*.json")).write_text("invalid")
        RF._RESULT_CACHE.clear()
        RF._QUERY_CACHE.clear()
        with patch.object(RF, "_result_index", side_effect=AssertionError("source scan")), \
                patch.object(RF.json, "loads", wraps=json.loads) as decode:
            one = RF.run_result(str(self.runs), "run", "q3")
        self.assertEqual(one, self.rows[2])
        self.assertEqual(decode.call_count, 3)
        RF._RESULT_CACHE.clear()
        RF._QUERY_CACHE.clear()
        with patch.object(RF.json, "loads", wraps=json.loads) as decode:
            self.assertEqual(RF.run_result(str(self.runs), "run", "q3"), one)
        self.assertEqual(decode.call_count, 2)

    def test_saved_offsets_preserve_query_types_first_duplicates_and_bounds(self):
        self.write(self.rows + [{"query_id": 1, "image_path": "integer"},
                                {"query_id": "1", "image_path": "string"},
                                {"query_id": "q3", "image_path": "duplicate"}])
        self.read()
        RF._RESULT_CACHE.clear()
        RF._QUERY_CACHE.clear()
        self.assertEqual(RF.run_result(str(self.runs), "run", "q3"), self.rows[2])
        self.assertEqual(RF.run_result(str(self.runs), "run", 1)["image_path"], "integer")
        self.assertEqual(RF.run_result(str(self.runs), "run", "1")["image_path"], "string")
        for i in range(5):
            directory = self.runs / str(i)
            directory.mkdir()
            (directory / "results.jsonl").write_text(json.dumps({"query_id": "other"}) + "\n")
            RF.run_rows(str(self.runs), str(i))
        self.assertLessEqual(len(RF._QUERY_CACHE), RF._MAX_CACHED_RUNS)
        self.assertLessEqual(sum(len(item[1]) for item in RF._QUERY_CACHE.values()),
                             RF._MAX_CACHED_ROWS)

    def test_disk_summary_survives_memory_eviction_and_observes_append(self):
        expected = self.read()
        RF._RESULT_CACHE.clear()
        with patch.object(RF.json, "loads", wraps=json.loads) as decode:
            actual = self.read(limit=1)
        self.assertEqual(actual, (expected[0][:1], expected[1]))
        # One JSON cache and one selected result; no full results scan.
        self.assertEqual(decode.call_count, 2)
        RF._RESULT_CACHE.clear()
        with self.path.open("a") as output:
            output.write(json.dumps({"query_id": "q4"}) + "\n")
        self.assertEqual(self.read()[1], 4)

    def test_returned_records_are_complete_and_do_not_modify_the_index(self):
        rows, _ = self.read()
        self.assertEqual(rows[0]["trace"], self.rows[0]["trace"])
        self.assertEqual(rows[0]["candidates"], self.rows[0]["candidates"])
        rows[0].pop("trace")
        rows[0]["candidates"][0].clear()
        one = RF.run_result(str(self.runs), "run", "q1")
        self.assertEqual(one, self.rows[0])
        self.assertEqual(self.read()[0][0]["trace"], self.rows[0]["trace"])

    def test_returned_twin_conflicts_cannot_change_cached_truths(self):
        self.write(self.rows + [{"query_id": "q4", "slug": "c", "label": "positive",
                                 "image_sha256": "same"}])
        rows, _ = self.read()
        rows[0]["twin"]["conflict_slugs"]["positive"].clear()
        self.assertEqual(self.read()[0][0]["twin"]["conflict_slugs"]["positive"], ["a", "c"])

    def test_append_and_incomplete_tail_invalidate_the_index(self):
        self.read()
        tail = json.dumps({"query_id": "q4", "image_path": "new.jpg"})
        with self.path.open("a") as fh:
            fh.write("\ninvalid\n" + tail[:12])
        self.assertEqual(self.read()[1], 3)
        with self.path.open("a") as fh:
            fh.write(tail[12:] + "\n")
        self.assertEqual(self.read()[1], 4)
        self.assertEqual(RF.run_result(str(self.runs), "run", "q4")["image_path"], "new.jpg")

    def test_same_size_rewrite_and_atomic_replace_with_same_mtime_are_fresh(self):
        for replace in (False, True):
            self.write(self.rows)
            self.read()
            stat = self.path.stat()
            data = self.path.read_bytes().replace(b'"q1"', b'"qx"')
            if replace:
                other = self.path.with_suffix(".new")
                other.write_bytes(data)
                os.utime(other, ns=(stat.st_atime_ns, stat.st_mtime_ns))
                other.replace(self.path)
            else:
                self.path.write_bytes(data)
                os.utime(self.path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
            self.assertEqual(self.read()[0][0]["query_id"], "qx")
            self.assertIsNone(RF.run_result(str(self.runs), "run", "q1"))

    def test_runs_keep_separate_indexes_and_first_duplicate_query_wins(self):
        self.write(self.rows + [{"query_id": "q1", "image_path": "duplicate"}])
        self.read()
        for i in range(5):
            directory = self.runs / str(i)
            directory.mkdir()
            (directory / "results.jsonl").write_text(json.dumps({"query_id": "other"}) + "\n")
            RF.run_rows(str(self.runs), str(i))
        self.assertEqual(RF.run_result(str(self.runs), "run", "q1"), self.rows[0])
        self.assertLessEqual(len(RF._RESULT_CACHE), RF._MAX_CACHED_RUNS)


if __name__ == "__main__":
    unittest.main()
