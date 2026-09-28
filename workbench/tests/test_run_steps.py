"""Tests of the step popup of the Runs page (plan 41): `pipeline/run_steps.py` through
`run_routes.steps_view`.

The lab, the fake SAM3, and the fake model come from `test_embedding_run.py`. No test
calls gx10 or the matcher.
"""
import json
import os
import sqlite3
from pathlib import Path
from unittest import mock

import test_embedding_run as TE  # noqa: E402  (puts pipeline/ and scripts/ on sys.path)
import benchmark  # noqa: E402
import embedding_run  # noqa: E402
import run_routes  # noqa: E402
import run_steps  # noqa: E402

EMBEDDING_NAMES = ["Input photo", "Package cut", "Label cut", "View full", "View label",
                   "Embedding", "Search, space full", "Search, space label", "Score"]


def no_cards(conn):
    return {}


def read_rows(run_dir):
    with open(os.path.join(run_dir, "results.jsonl"), encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def write_rows(run_dir, rows):
    with open(os.path.join(run_dir, "results.jsonl"), "w", encoding="utf-8") as fh:
        fh.write("".join(json.dumps(row) + "\n" for row in rows))


class StepsTest(TE.Temporary):
    def setUp(self):
        super().setUp()
        self.lab = TE.catalogue_lab(self.root)
        self.embedding = TE.build(self.lab)
        TE.add_set(self.lab)
        self.runs = str(self.root / "runs")

    def run_set(self, scene_selection=False):
        backend = embedding_run.build_backend(self.embedding, self.lab.db_path,
                                              make_model=lambda e: TE.ColourModel(),
                                              segmenter=TE.FakeSam3(),
                                              scene_selection=scene_selection)
        run_dir, _ = benchmark.run_benchmark(
            self.lab.db_path, "my", backend, self.runs, embeddings=backend.catalogue.state,
            log=lambda message: None, configuration="gw")
        return run_dir, {row["image_path"]: row for row in read_rows(run_dir)}

    def steps(self, run_id, query):
        with mock.patch.object(embedding_run, "CachedSam3", TE.FakeSam3):
            code, body, _, _ = run_routes.steps_view(self.runs, self.lab.db_path,
                                                     {"id": [run_id], "query": [query]},
                                                     no_cards)
        return code, body

    def all_steps(self, body):
        return [part for one in body["rounds"] for part in one["steps"]]


class EmbeddingStepsTest(StepsTest):
    def test_the_package_result_explains_the_main_scene_selection(self):
        run_dir, rows = self.run_set(scene_selection=True)
        row = rows["green/01.png"]
        code, body = self.steps(os.path.basename(run_dir), row["query_id"])
        package = next(part for part in self.all_steps(body) if part["id"] == "sam3-package")
        selection = package["result"]["selection"]
        self.assertEqual((code, package["name"], selection["version"]),
                         (200, "Package selection and cut", 1))
        self.assertEqual(selection["selected"]["label"], "bottle")
        self.assertTrue(selection["candidates"][0]["selected"])
        self.assertIn("scene_score", selection["candidates"][0])
        self.assertIn("main-scene selector chose bottle", package["notes"][-1])

    def test_a_traced_row_gives_three_rounds_with_the_step_times(self):
        run_dir, rows = self.run_set()
        row = rows["green/01.png"]
        code, body = self.steps(os.path.basename(run_dir), row["query_id"])
        self.assertEqual(code, 200, body)
        self.assertEqual((body["kind"], body["recorded"], body["notes"]),
                         ("embedding", True, []))
        self.assertEqual([one["title"] for one in body["rounds"]],
                         ["Round 0", "Round 1", "Round 2"])
        steps = self.all_steps(body)
        self.assertEqual([part["name"] for part in steps], EMBEDDING_NAMES)
        self.assertEqual([part["n"] for part in steps], list(range(len(EMBEDDING_NAMES))))
        self.assertTrue(all(part["ms"] is not None and part["state"] == "done"
                            for part in steps))
        photo = steps[0]["artifacts"][0]
        self.assertTrue(photo["src"].startswith("/images/"))
        self.assertEqual((photo["width"], photo["height"]), (100, 150))
        package = steps[1]
        self.assertEqual((package["service"], package["model"], package["group"]),
                         ("fake-sam3", "sam3", "segment"))
        self.assertEqual(package["artifacts"][0]["boxes"],
                         [row["trace"]["steps"][1]["out"]["box"]])
        self.assertTrue(package["artifacts"][1]["src"].startswith("data:image/png;base64,"))
        for view in steps[3:5]:
            self.assertEqual(view["artifacts"][0]["check"], "same", view)
        full = steps[6]["lists"][0]
        self.assertEqual(full["items"][0]["slug"], "green")
        self.assertTrue(all(item["image"].startswith("/embeddings/gw/images/")
                            for item in full["items"]))
        self.assertEqual(steps[6]["result"], {"rows": 3, "wines": 3})
        self.assertEqual([item["slug"] for item in steps[8]["lists"][0]["items"]],
                         [c["slug"] for c in row["candidates"]])
        self.assertTrue(steps[8]["lists"][0]["items"][0]["truth"])

    def test_a_model_input_that_differs_from_the_run_is_marked(self):
        run_dir, _ = self.run_set()
        rows = read_rows(run_dir)
        for row in rows:
            for part in row["trace"]["steps"]:
                if part["id"] == "view" and "out" in part:
                    part["out"]["sha256"] = "0" * 64
        write_rows(run_dir, rows)
        code, body = self.steps(os.path.basename(run_dir), rows[0]["query_id"])
        view = next(part for part in self.all_steps(body) if part["id"] == "view")
        self.assertEqual((code, view["artifacts"][0]["check"]), (200, "changed"))
        self.assertIn("differs from the input of the run", view["notes"][-1])

    def test_an_old_row_has_the_steps_with_no_time(self):
        run_dir, _ = self.run_set()
        rows = read_rows(run_dir)
        for row in rows:
            row.pop("trace")
        write_rows(run_dir, rows)
        row = next(r for r in rows if r["image_path"] == "green/01.png")
        code, body = self.steps(os.path.basename(run_dir), row["query_id"])
        self.assertEqual((code, body["recorded"], body["notes"]), (200, False, [run_steps.NO_TIME]))
        steps = self.all_steps(body)
        self.assertEqual([part["name"] for part in steps], EMBEDDING_NAMES)
        self.assertTrue(all(part["ms"] is None for part in steps))
        for view in steps[3:5]:
            self.assertIsNone(view["artifacts"][0]["check"])
        label = steps[7]["lists"][0]
        self.assertEqual(label["note"], run_steps.NO_SPACE_LIST)
        cosines = [item["score"] for item in label["items"]]
        self.assertEqual(cosines, sorted(cosines, reverse=True))

    def test_a_photo_with_no_label_has_a_skipped_label_view(self):
        run_dir, rows = self.run_set()
        code, body = self.steps(os.path.basename(run_dir), rows["red/02.png"]["query_id"])
        steps = {part["name"]: part for part in self.all_steps(body)}
        self.assertEqual(code, 200)
        self.assertIn("SAM3 found no label.", steps["Label cut"]["notes"])
        self.assertEqual(steps["View label"]["state"], "skipped")
        self.assertNotIn("Search, space label", steps)

    def test_a_code_answer_shows_the_decode_step_alone(self):
        run_dir, _ = self.run_set()
        rows = read_rows(run_dir)
        row = rows[0]
        hit = {"source": "gtin", "code": "04600682000181", "read": "4600682000181",
               "format": "EAN13", "slugs": ["green"]}
        row["trace"] = {"v": 1, "steps": [{"id": "barcode", "start_ms": 0.0, "ms": 12.5, "out": {
            "codes": [{"kind": "barcode", "format": "EAN13", "text": "4600682000181"}],
            "hit": hit}}]}
        row["candidates"] = [{"slug": "green", "score": 1.0, "rank": 1, "source": "gtin",
                              "code": "04600682000181", "read": "4600682000181",
                              "format": "EAN13"}]
        write_rows(run_dir, rows)
        code, body = self.steps(os.path.basename(run_dir), row["query_id"])
        self.assertEqual((code, len(body["rounds"])), (200, 1))
        steps = self.all_steps(body)
        self.assertEqual([part["name"] for part in steps],
                         ["Input photo", "Decode codes, whole photo"])
        decode = steps[1]
        self.assertEqual((decode["ms"], decode["model"]), (12.5, "zxing-cpp"))
        self.assertEqual([item["slug"] for item in decode["lists"][0]["items"]], ["green"])
        self.assertIn("No embedding model ran.", decode["notes"][0])

    def test_an_unknown_run_or_query_is_not_found(self):
        run_dir, _ = self.run_set()
        self.assertEqual(self.steps("nope", "q-000001")[0], 404)
        self.assertEqual(self.steps(os.path.basename(run_dir), "q-999999")[0], 404)


class OtherRunsTest(StepsTest):
    def setUp(self):
        super().setUp()
        conn = sqlite3.connect(self.lab.db_path)
        self.digest = conn.execute("SELECT sha256 FROM test_photo ORDER BY place, file_name "
                                   "LIMIT 1").fetchone()[0]
        conn.close()

    def write_run(self, run_id, backend, candidates, **row):
        directory = Path(self.runs, run_id)
        directory.mkdir(parents=True)
        (directory / "run.json").write_text(json.dumps({"backend": backend}), encoding="utf-8")
        record = {"query_id": "q-000001", "image_path": "blue/01.png",
                  "image_sha256": self.digest, "slug": "blue", "label": "positive",
                  "truth": ["blue"], "candidates": candidates, "rank_of_truth": None,
                  "outcome": "miss", "latency_ms": 5000, "http_status": 200, "error": None}
        record.update(row)
        write_rows(str(directory), [record])
        return run_id

    def test_a_matcher_run_shows_the_order_before_each_re_rank_step(self):
        vlm = {"kind": "cluster_rules", "cluster": "abc123", "mode": "sheet",
               "window": ["red", "green"], "cached": False, "ms": 3423, "error": None,
               "questions": [{"id": "q1", "question": "Is it red?"}],
               "answers": {"q1": "yes"}, "scores": {"red": -2, "green": 2}, "changed": True}
        cands = [
            {"slug": "green", "score": 0.8, "rank": 1, "explain": dict(
                vlm, base_rank=2, base_score=0.80, inner={
                    "kind": "difference", "base_rank": 1, "base_score": 0.85, "evidence": 0.5,
                    "seen": [{"token": "pino", "weight": 0.4}], "contradicted": []})},
            {"slug": "red", "score": 0.79, "rank": 2, "explain": dict(
                vlm, base_rank=1, base_score=0.82, inner={
                    "kind": "difference", "base_rank": 2, "base_score": 0.84, "evidence": -0.7,
                    "seen": [], "contradicted": ["colour"]})},
            {"slug": "blue", "score": 0.5, "rank": 3},
        ]
        run_id = self.write_run("run-matcher", {
            "id": "svm-rules", "url": "http://127.0.0.1:8158/v1/pipelines/cluster-rules/predict",
            "query": {"explain": 1, "limit": 10}, "top_k": 10}, cands, rank_of_truth=3)
        with mock.patch.object(run_steps, "MATCHER_ROOT", str(self.root / "no-matcher")):
            code, body = self.steps(run_id, "q-000001")
        self.assertEqual((code, body["kind"]), (200, "matcher"))
        steps = self.all_steps(body)
        self.assertEqual([part["name"] for part in steps], [
            "Input photo", "Matcher inputs", "Search", "Difference words", "VLM cluster rule"])
        self.assertEqual(len(body["rounds"]), 4)
        self.assertIn("cannot be made again", steps[1]["notes"][0])
        slugs = lambda part: [item["slug"] for item in part["lists"][0]["items"]]  # noqa: E731
        moves = lambda part: [item["moved"] for item in part["lists"][0]["items"]]  # noqa: E731
        self.assertEqual((slugs(steps[2]), steps[2]["ms"]), (["green", "red", "blue"], 5000))
        self.assertEqual([item["score"] for item in steps[2]["lists"][0]["items"]],
                         [0.85, 0.84, 0.5])
        self.assertEqual((slugs(steps[3]), moves(steps[3])),
                         (["red", "green", "blue"], [1, -1, None]))
        self.assertIn("contradicted colour", steps[3]["lists"][0]["items"][0]["detail"])
        self.assertIn("seen pino", steps[3]["lists"][0]["items"][1]["detail"])
        rule = steps[4]
        self.assertEqual((rule["ms"], rule["vlm"]["answers"], rule["vlm"]["changed"]),
                         (3423, {"q1": "yes"}, True))
        self.assertEqual((slugs(rule), moves(rule)), (["green", "red", "blue"], [1, -1, None]))

    def test_a_vlm_record_with_no_question_text_gets_a_note(self):
        cands = [{"slug": "green", "score": 0.8, "rank": 1, "explain": {
            "kind": "cluster_rules", "cluster": "abc123", "mode": "sheet",
            "window": ["green"], "ms": 10, "answers": {"q1": "no"}, "base_rank": 1}}]
        run_id = self.write_run("run-rules", {
            "id": "svm-rules", "url": "http://127.0.0.1:8158/v1/pipelines/rules/predict"}, cands)
        with mock.patch.object(run_steps, "MATCHER_ROOT", str(self.root / "no-matcher")):
            _, body = self.steps(run_id, "q-000001")
        rule = self.all_steps(body)[-1]
        self.assertEqual((rule["name"], rule["vlm"]["questions"]), ("VLM cluster rule", []))
        self.assertIn("with no question text", rule["notes"][0])

    def test_a_remote_run_shows_the_photo_and_the_answer(self):
        run_id = self.write_run("run-remote", {
            "kind": "remote", "id": "vino-svoe-search-by-photo",
            "url": "https://api.vino-svoe.ru/v1/wines/search-by-photo"},
            [{"slug": "blue", "score": None, "rank": 1}], rank_of_truth=1, outcome="hit")
        code, body = self.steps(run_id, "q-000001")
        steps = self.all_steps(body)
        self.assertEqual((code, body["kind"], [part["name"] for part in steps]),
                         (200, "remote", ["Input photo", "Remote search"]))
        self.assertEqual((steps[1]["service"], steps[1]["ms"]), ("api.vino-svoe.ru", 5000))
        self.assertEqual(steps[1]["lists"][0]["items"][0]["slug"], "blue")

    def test_a_mock_run_sent_no_request(self):
        run_id = self.write_run("run-mock", {"id": "mock", "url": None},
                                [{"slug": "red", "score": 0.3, "rank": 1}])
        code, body = self.steps(run_id, "q-000001")
        steps = self.all_steps(body)
        self.assertEqual((code, body["kind"], steps[1]["name"]), (200, "none", "Backend answer"))
        self.assertIn("sent no request", steps[1]["notes"][0])
