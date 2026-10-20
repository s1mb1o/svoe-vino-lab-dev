"""Check saved case alignment, scoring, guards, and the read-only HTTP contract."""

import hashlib
import json
from pathlib import Path
import tempfile
import sqlite3
from urllib.parse import unquote
import threading
import unittest
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from urllib.error import HTTPError
import sys

# The modules of the lab are in `pipeline/`. Another test module adds it too, but this
# module also runs alone (`-p test_run_compare.py`).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))

import lab_server  # noqa: E402
import labdb  # noqa: E402
import run_compare as compare  # noqa: E402


def query(number, **extra):
    return {
        "query_id": f"q-{number}",
        "image_sha256": hashlib.sha256(str(number).encode()).hexdigest(),
        "image_path": f"wine-{number}/photo.jpg",
        "slug": f"wine-{number}",
        "label": "positive",
        "truth": [f"wine-{number}"],
        **extra,
    }


class RunFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.runs = self.root / "runs"
        self.rows = [query(i) for i in range(4)]
        self.write("a", self.rows, [True, True, False, False])
        self.write("b", self.rows, [True, False, True, False])

    def tearDown(self):
        self.temp.cleanup()

    def write(
        self, name, queries, correct=None, *, candidates=None, meta=None, results=None
    ):
        folder = self.runs / name
        folder.mkdir(parents=True, exist_ok=True)
        metadata = {
            "configuration": name,
            "started": "2026-10-01T00:00:00Z",
            "finished": "2026-10-01T00:01:00Z",
            "options": {"set": "my"},
            "query_set": {"total": len(queries)},
        }
        metadata.update(meta or {})
        (folder / "run.json").write_text(json.dumps(metadata))
        if results is None:
            results = []
            for i, row in enumerate(queries):
                slugs = (
                    candidates[i]
                    if candidates is not None
                    else [row["truth"][0] if correct[i] else "wrong"]
                )
                results.append(
                    {
                        **row,
                        "candidates": [{"slug": slug, "score": 0.9} for slug in slugs],
                        "outcome": "saved",
                        "latency_ms": i * 100,
                    }
                )
        for filename, rows in (("queries.jsonl", queries), ("results.jsonl", results)):
            (folder / filename).write_text("".join(json.dumps(r) + "\n" for r in rows))

    def result(self, **options):
        return compare.compare(str(self.runs), None, "a", "b", **options)


class ComparisonTest(RunFixture):
    def test_four_groups_and_differences_default(self):
        out = self.result()
        self.assertTrue(out["compatibility"]["exact"])
        self.assertEqual(out["group"], "differences")
        self.assertEqual([r["group"] for r in out["rows"]].count("regressions"), 1)
        self.assertEqual(out["total"], 2)
        for key in compare.GROUPS:
            self.assertEqual(out["counts"][key], 1)
        self.assertEqual(out["counts"]["all"], 4)

    def test_group_filters_and_swapping_runs(self):
        for group in compare.GROUPS:
            out = self.result(group=group)
            self.assertEqual(out["total"], 1)
            self.assertEqual(out["rows"][0]["group"], group)
        forward = self.result(group="regressions")["rows"][0]
        reverse = compare.compare(str(self.runs), None, "b", "a", group="improvements")[
            "rows"
        ][0]
        self.assertEqual(forward["image_sha256"], reverse["image_sha256"])

    def test_order_query_ids_and_unique_filenames_do_not_define_identity(self):
        changed = [
            {
                **r,
                "query_id": "other-" + r["query_id"],
                "image_path": "renamed/" + r["query_id"],
            }
            for r in reversed(self.rows)
        ]
        self.write("b", changed, [False, True, False, True])
        out = self.result()
        self.assertTrue(out["compatibility"]["exact"])
        self.assertEqual(out["counts"]["differences"], 2)

    def test_changed_truth_blocks_comparison_until_explicit_common(self):
        rows = [dict(r) for r in self.rows]
        rows[0] = {**rows[0], "truth": ["different"]}
        self.write("b", rows, [True, False, True, False])
        out = self.result()
        self.assertEqual(out["compatibility"]["changed"], 1)
        self.assertFalse(out["comparison_enabled"])
        self.assertEqual(out["rows"], [])
        out = self.result(common=True, group="all")
        self.assertEqual(out["total"], 3)
        self.assertEqual(out["counts"]["not_compared"], 1)

    def test_added_removed_cases_and_changed_image_bytes(self):
        rows = self.rows[1:] + [query(8)]
        self.write("b", rows, [True] * 4)
        out = self.result(group="not_compared")
        self.assertEqual(out["compatibility"]["only_a"], 1)
        self.assertEqual(out["compatibility"]["only_b"], 1)
        self.assertEqual(out["total"], 2)
        self.assertFalse(out["comparison_enabled"])

    def test_renamed_testset_can_have_identical_snapshot(self):
        self.write("b", self.rows, [True] * 4, meta={"options": {"set": "renamed"}})
        out = self.result()
        self.assertTrue(out["compatibility"]["exact"])
        self.assertTrue(out["warnings"])

    def test_no_overlap_is_incompatible_even_with_common_option(self):
        self.write("b", [query(8)], [True])
        out = self.result(common=True)
        self.assertEqual(out["compatibility"]["status"], "incompatible")
        self.assertFalse(out["comparison_enabled"])

    def test_multiple_accepted_answers_and_top_k(self):
        rows = [query(1, truth=["wine-1", "vintage-2023"])]
        self.write("a", rows, candidates=[["vintage-2023"]])
        self.write("b", rows, candidates=[["wrong", "wine-1"]])
        self.assertEqual(self.result()["counts"]["regressions"], 1)
        out = self.result(k=5, group="both_succeed")
        self.assertEqual(out["total"], 1)
        self.assertEqual(out["rows"][0]["b"]["rank_of_truth"], 2)

    def test_truth_order_and_duplicate_candidates(self):
        rows = [query(1, truth=["wine-1", "other"])]
        self.write("a", rows, candidates=[["wrong", "wrong", "wine-1"]])
        self.write(
            "b",
            [{**rows[0], "truth": ["other", "wine-1"]}],
            candidates=[["wrong", "wine-1"]],
        )
        out = self.result(group="both_succeed", k=5)
        self.assertTrue(out["compatibility"]["exact"])
        self.assertEqual(out["rows"][0]["a"]["rank_of_truth"], 2)

    def test_no_match_requires_no_answer_at_every_depth(self):
        rows = [query(1, label="no_match", truth=[], slug="__null__")]
        self.write("a", rows, candidates=[[]])
        self.write("b", rows, candidates=[["wrong"]])
        for k in (1, 5, 10):
            self.assertEqual(self.result(k=k)["counts"]["regressions"], 1)

    def test_negative_and_unlabelled_cases_are_not_successes(self):
        rows = [
            query(1, label="negative", truth=[]),
            query(2, label="unlabelled", truth=[]),
        ]
        self.write("a", rows, candidates=[[], ["something"]])
        self.write("b", rows, candidates=[["wrong"], []])
        out = self.result(group="unscored")
        self.assertEqual(out["total"], 2)
        self.assertEqual(sum(out["counts"][g] for g in compare.GROUPS), 0)

    def test_errors_and_missing_results_stay_separate(self):
        records = [{**self.rows[0], "candidates": [], "error": "timeout"}]
        self.write("b", self.rows, results=records)
        out = self.result(group="errors")
        self.assertEqual(out["total"], 4)
        self.assertEqual(out["counts"]["both_fail"], 0)

    def test_result_annotation_must_match_its_snapshot(self):
        records = [{**r, "truth": ["changed"], "candidates": []} for r in self.rows]
        self.write("b", self.rows, results=records)
        self.assertEqual(self.result(group="errors")["total"], 4)

    def test_repeated_image_assignment_uses_saved_paths(self):
        rows = [
            query(1),
            {**query(1), "query_id": "duplicate", "image_path": "wine-1/copy.jpg"},
        ]
        self.write("a", rows, [True, False])
        self.write("b", list(reversed(rows)), [True, False])
        out = self.result()
        self.assertTrue(out["compatibility"]["exact"])
        self.assertEqual(out["total"], 2)

    def test_ambiguous_duplicate_saved_path_is_rejected(self):
        rows = [query(1), {**query(1), "query_id": "duplicate"}]
        self.write("a", rows, [True, False])
        with self.assertRaisesRegex(compare.CompareError, "duplicate saved paths"):
            self.result()

    def test_snapshot_missing_or_duplicate_query_id_is_rejected(self):
        (self.runs / "a/queries.jsonl").unlink()
        with self.assertRaises(compare.CompareError):
            self.result()
        self.write("a", [query(1), query(1)], [True, True])
        with self.assertRaisesRegex(compare.CompareError, "duplicate query"):
            self.result()

    def test_unfinished_and_dry_run_are_rejected(self):
        for meta in ({"finished": None}, {"options": {"set": "my", "dry_run": True}}):
            self.write("a", self.rows, [True] * 4, meta=meta)
            with self.assertRaises(compare.CompareError) as caught:
                self.result()
            self.assertEqual(caught.exception.code, 409)

    def test_search_pagination_counts_and_read_only_files(self):
        before = {str(f): f.read_bytes() for f in self.runs.glob("*/*")}
        out = self.result(group="all", query="wine-1", limit=1)
        self.assertEqual(out["total"], 1)
        self.assertEqual(out["counts"]["all"], 4)
        self.assertEqual(self.result(group="all", offset=3, limit=1)["total"], 4)
        self.assertEqual(self.result(group="all", query="image_sha256")["total"], 0)
        self.assertEqual(
            before, {str(f): f.read_bytes() for f in self.runs.glob("*/*")}
        )

    def test_cache_detects_replaced_snapshot_and_results(self):
        self.assertEqual(self.result()["total"], 2)
        self.write("b", self.rows, [True, True, False, False])
        self.assertEqual(self.result()["total"], 0)

    def test_api_parameters_and_paths(self):
        for params in (
            {},
            {"a": ["a"], "b": ["a"]},
            {"a": ["a"], "b": ["b"], "k": ["2"]},
            {"a": ["a"], "b": ["b"], "common": ["true"]},
            {"a": ["a", "b"], "b": ["b"]},
            {"a": ["../escape"], "b": ["b"]},
        ):
            self.assertEqual(compare.respond(str(self.runs), None, params)[0], 400)
        self.assertEqual(
            compare.respond(str(self.runs), None, {"a": ["a"], "b": ["gone"]})[0], 404
        )

    def test_cached_values_are_not_exposed_to_response_mutations(self):
        out = self.result(group="all")
        out["rows"][0]["a"]["truth"].append("poisoned")
        out["rows"][0]["a"]["candidates"][0]["slug"] = "poisoned"
        next_out = self.result(group="all")
        self.assertNotIn("poisoned", next_out["rows"][0]["a"]["truth"])
        self.assertNotEqual(
            next_out["rows"][0]["a"]["candidates"][0]["slug"], "poisoned"
        )

    def test_invalid_metadata_and_bad_json_have_explicit_errors(self):
        self.write("a", self.rows, [True] * 4, meta={"query_set": [1]})
        with self.assertRaises(compare.CompareError) as caught:
            self.result()
        self.assertEqual(caught.exception.code, 422)
        (self.runs / "a/run.json").write_text("{")
        with self.assertRaises(compare.CompareError):
            self.result()

    def test_search_uses_both_paths_and_all_saved_candidates(self):
        rows = [query(1)]
        slugs = ["wrong-" + str(i) for i in range(6)] + ["needle", "wine-1"]
        self.write("a", rows, candidates=[slugs])
        self.write(
            "b",
            [{**rows[0], "image_path": "renamed/unique-filename.jpg"}],
            candidates=[slugs],
        )
        for rank in (1, 5, 10):
            self.assertEqual(
                self.result(group="all", query="needle", k=rank)["total"], 1
            )
        self.assertEqual(self.result(group="all", query="unique-filename")["total"], 1)

    def test_extra_results_and_shallow_top_k_are_reported(self):
        path = self.runs / "a/results.jsonl"
        with path.open("a") as stream:
            stream.write(json.dumps({**query(90), "candidates": []}) + "\n")
        out = self.result(k=5)
        self.assertTrue(any("outside its query snapshot" in w for w in out["warnings"]))
        self.assertTrue(any("saved at most" in w for w in out["warnings"]))

    def test_inspect_link_preserves_unicode_and_reserved_characters(self):
        path = "wine-1/фото (1)%#!'*.jpg"
        rows = [query(1, image_path=path)]
        self.write("a", rows, [True])
        self.write("b", rows, [False])
        link = self.result()["rows"][0]["a"]["inspect_url"]
        self.assertEqual(unquote(link.split("#", 1)[1]), "a/" + path)
        self.assertIn("%28", link)
        self.assertIn("%25%23", link)

    def test_null_legacy_image_location_is_unavailable_without_parameter_error(self):
        db = self.root / "legacy.sqlite3"
        with sqlite3.connect(db) as conn:
            conn.execute("CREATE TABLE image(sha256 TEXT,folder TEXT,extension TEXT)")
            conn.execute(
                "INSERT INTO image VALUES (?,NULL,NULL)",
                (self.rows[0]["image_sha256"],),
            )
        out = compare.compare(str(self.runs), str(db), "a", "b", group="all")
        self.assertIsNone(out["images_error"])
        self.assertIsNone(
            next(
                r
                for r in out["rows"]
                if r["image_sha256"] == self.rows[0]["image_sha256"]
            ).get("photo_url")
        )


class HttpComparisonTest(RunFixture):
    def setUp(self):
        super().setUp()
        self.db = str(self.root / "catalog.sqlite3")
        labdb.connect(self.db, create=True).close()
        config = self.root / "config.yaml"
        config.write_text("pipeline: []\nembeddings: []\n")
        self.server = lab_server.make_server(self.db, port=0, config_path=str(config))
        self.server.runs_dir = str(self.runs)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = "http://127.0.0.1:" + str(self.server.server_address[1])

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        super().tearDown()

    def test_http_get_page_api_and_method_guard(self):
        with urlopen(self.url + "/runs/compare") as response:
            self.assertIn(b"Compare runs", response.read())
        with urlopen(
            self.url + "/api/run-compare?" + urlencode({"a": "a", "b": "b"})
        ) as response:
            body = json.load(response)
            self.assertIsNone(body["images_error"])
            self.assertEqual(body["total"], 2)
            self.assertEqual(body["group"], "differences")
        with self.assertRaises(HTTPError) as caught:
            urlopen(Request(self.url + "/api/run-compare", data=b"{}", method="POST"))
        self.assertEqual(caught.exception.code, 405)
        caught.exception.close()

    def test_http_rejects_unknown_run_and_missing_snapshot(self):
        (self.runs / "a/queries.jsonl").unlink()
        with self.assertRaises(HTTPError) as caught:
            urlopen(self.url + "/api/run-compare?a=a&b=b")
        self.assertEqual(caught.exception.code, 422)
        caught.exception.close()

    def test_http_run_heads_expose_picker_fields(self):
        with urlopen(self.url + "/api/runs") as response:
            heads = json.load(response)["runs"]
        self.assertEqual(len(heads), 2)
        for head in heads:
            self.assertEqual(head["set"], "my")
            self.assertTrue(head["finished"])
            self.assertFalse(head["dry_run"])
            self.assertEqual(head["queries"], 4)
