"""Tests of plan 83: the lab pipelines that call the matcher API. The answer shape `group`
of `scripts/match_backends.py`, the row key `group` of a run, the catalogue images of the
group slugs on the Runs page, and the three entries of `config.yaml`."""
import contextlib
import http.server
import io
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import testset_fixture as FX  # noqa: E402
import import_testset as IT  # noqa: E402
import match_backends  # noqa: E402
import remote_run as RR  # noqa: E402
import run_routes  # noqa: E402
from test_remote_run import LABELS, PHOTOS, write_config  # noqa: E402

NAME = "matcher-group-match"


def card(slug, score, rank=1):
    return {"rank": rank, "slug": slug, "score": score,
            "wine": {"name": "Name %s" % slug, "page_url": "https://x/%s" % slug}}


# b1 and b2 hold the list `candidates` of a matcher with `k`. b3 holds `match` alone, as
# a matcher before plan 83. b4 holds no match.
GROUP_ANSWER = {
    "pipeline": "siglip2-p512-as-is", "latency_ms": 12.5,
    "image": {"width": 1200, "height": 1600, "preview": "data:image/jpeg;base64,AAAA"},
    "detected_count": 5, "truncated": False,
    "bottles": [
        {"id": "b1", "segmentation_score": 0.91, "box": [0.0, 0.1, 0.3, 0.9],
         "mask": "data:image/png;base64,AAAA", "match": card("wine-b", 0.7),
         "candidates": [card("wine-b", 0.7), card("wine-c", 0.6, 2)]},
        {"id": "b2", "segmentation_score": 0.88, "box": [0.3, 0.1, 0.6, 0.9],
         "mask": "data:image/png;base64,AAAA", "match": card("wine-a", 0.9),
         "candidates": [card("wine-a", 0.9), card("wine-b", 0.5, 2)]},
        {"id": "b3", "segmentation_score": 0.75, "box": [0.6, 0.1, 0.9, 0.9],
         "mask": "data:image/png;base64,AAAA", "match": card("wine-a", 0.8)},
        {"id": "b4", "segmentation_score": 0.5, "box": [0.9, None, 1.0, 0.9],
         "mask": "data:image/png;base64,AAAA", "match": None, "candidates": []},
    ],
}


class GroupRecordTest(unittest.TestCase):
    def test_the_record_keeps_boxes_and_candidates_and_drops_the_media(self):
        record = match_backends.group_record(GROUP_ANSWER)
        self.assertEqual(record["image"], {"width": 1200, "height": 1600})
        self.assertEqual((record["detected_count"], record["truncated"]), (5, False))
        self.assertEqual([b["n"] for b in record["bottles"]], [1, 2, 3, 4])
        self.assertEqual([b["id"] for b in record["bottles"]], ["b1", "b2", "b3", "b4"])
        first = record["bottles"][0]
        self.assertEqual(set(first), {"n", "id", "segmentation_score", "box", "candidates"})
        self.assertEqual(first["box"], [0.0, 0.1, 0.3, 0.9])
        self.assertEqual(first["candidates"], [
            {"rank": 1, "slug": "wine-b", "score": 0.7},
            {"rank": 2, "slug": "wine-c", "score": 0.6}])
        self.assertNotIn("preview", json.dumps(record))
        self.assertNotIn("mask", json.dumps(record))

    def test_a_bottle_with_no_list_candidates_uses_its_match(self):
        record = match_backends.group_record(GROUP_ANSWER)
        self.assertEqual(record["bottles"][2]["candidates"],
                         [{"rank": 1, "slug": "wine-a", "score": 0.8}])

    def test_a_bottle_with_no_match_and_a_bad_box(self):
        bottle = match_backends.group_record(GROUP_ANSWER)["bottles"][3]
        self.assertEqual((bottle["candidates"], bottle["box"]), ([], None))

    def test_an_answer_that_is_not_a_group_answer(self):
        for body in ([{"slug": "wine-a"}], {"slug": "wine-a"}, {"bottles": [1]}):
            with self.subTest(body=body):
                with self.assertRaises(ValueError):
                    match_backends.group_record(body)


class GroupRankedTest(unittest.TestCase):
    def test_the_first_candidate_of_each_bottle_the_highest_score_first(self):
        ranked = match_backends.group_ranked(match_backends.group_record(GROUP_ANSWER))
        # b2 (wine-a 0.9), b3 (wine-a 0.8, dropped), b1 (wine-b 0.7); b4 has no match.
        self.assertEqual(ranked, [{"slug": "wine-a", "score": 0.9, "rank": 1},
                                  {"slug": "wine-b", "score": 0.7, "rank": 2}])

    def test_a_tie_keeps_the_order_and_a_missing_score_comes_last(self):
        record = {"bottles": [
            {"candidates": [{"rank": 1, "slug": "s-none", "score": None}]},
            {"candidates": [{"rank": 1, "slug": "s-first", "score": 0.5}]},
            {"candidates": [{"rank": 1, "slug": "s-second", "score": 0.5}]},
        ]}
        self.assertEqual([c["slug"] for c in match_backends.group_ranked(record)],
                         ["s-first", "s-second", "s-none"])

    def test_backends_yaml_refuses_the_shape_group(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "backends.yaml"
            path.write_text(json.dumps({"backends": [
                {"id": "g", "url": "http://x/v1/group/match", "response": "group"}]}),
                encoding="utf-8")
            with self.assertRaisesRegex(match_backends.BackendError, "lab pipelines"):
                match_backends.load_backends(str(path))


class GroupMatcher(http.server.BaseHTTPRequestHandler):
    """A matcher that answers `POST /v1/group/match`. `answer` is the answer body."""

    requests = []
    answer = GROUP_ANSWER

    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        GroupMatcher.requests.append(self.path)
        body = json.dumps(GroupMatcher.answer).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class GroupRunTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.db, self.schema = FX.make_database(self.root)
        IT.import_testset(self.db, "my", FX.write_set(self.root, PHOTOS, LABELS),
                          lambda m: None, self.schema)
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), GroupMatcher)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        GroupMatcher.requests = []
        GroupMatcher.answer = GROUP_ANSWER
        url = "http://127.0.0.1:%d/v1/group/match" % self.server.server_port
        self.config = write_config(self.root, self.db, [
            {"name": NAME, "backend": "svoe-vino-ru", "url": url, "response": "group",
             "query": {"k": 5}, "top_k": 20}])
        self.runs = self.root / "runs"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.directory.cleanup()

    def rows(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = RR.main(["--name", NAME, "--set", "my", "--config", self.config,
                            "--runs-dir", str(self.runs)])
        self.assertEqual(code, 0, out.getvalue())
        (run_dir,) = self.runs.iterdir()
        return {row["image_path"]: row for row in (
            json.loads(line) for line in
            (run_dir / "results.jsonl").read_text(encoding="utf-8").splitlines())}

    def test_a_run_row_holds_the_group_record_and_the_ranked_list(self):
        rows = self.rows()
        self.assertEqual(GroupMatcher.requests, ["/v1/group/match?k=5"] * 3)
        row = rows["wine-b/01.jpg"]
        self.assertEqual([c["slug"] for c in row["candidates"]], ["wine-a", "wine-b"])
        self.assertEqual((row["rank_of_truth"], row["error"]), (2, None))
        self.assertEqual(rows["wine-a/01.jpg"]["rank_of_truth"], 1)
        self.assertEqual(row["group"], match_backends.group_record(GROUP_ANSWER))
        self.assertNotIn("trace", row)
        # The Runs page asks the catalogue image of each slug of each bottle.
        self.assertEqual(run_routes._row_slugs(row), {"wine-a", "wine-b", "wine-c"})

    def test_an_answer_with_no_bottle_keeps_the_record_and_states_the_error(self):
        GroupMatcher.answer = dict(GROUP_ANSWER, bottles=[], detected_count=0)
        row = self.rows()["wine-a/01.jpg"]
        self.assertEqual(row["candidates"], [])
        self.assertEqual(row["error"], "the answer holds no bottle with a match")
        self.assertEqual(row["group"]["bottles"], [])
        self.assertEqual(row["group"]["detected_count"], 0)


class ProjectConfigTest(unittest.TestCase):
    def test_the_three_matcher_pipelines_call_the_prod_matcher(self):
        expected = {
            "matcher-eval-predict": ("/v1/eval/predict", "slug-object", {}, 1),
            "matcher-match-k20": ("/v1/match", "candidates", {"k": 20}, 20),
            "matcher-group-match": ("/v1/group/match", "group", {"k": 5}, 20),
        }
        for name, (path, shape, query, top_k) in expected.items():
            with self.subTest(name=name):
                entry, _ = RR.find_entry(name)
                remote = entry.remote
                self.assertEqual(remote["url"], "http://192.168.86.14:28000" + path)
                self.assertEqual((remote["response"], remote["query"], remote["top_k"]),
                                 (shape, query, top_k))


if __name__ == "__main__":
    unittest.main()
