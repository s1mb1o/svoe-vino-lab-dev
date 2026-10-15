"""Tests of the step popup of the Runs page (plan 41): `pipeline/run_steps.py` through
`run_routes.steps_view`.

The lab, the fake SAM3, and the fake model come from `test_embedding_run.py`. No test
calls gx10 or the matcher.
"""
import io
import json
import os
import sqlite3
import types
from pathlib import Path
from unittest import mock

from PIL import Image

import test_embedding_run as TE  # noqa: E402  (puts pipeline/ and scripts/ on sys.path)
import benchmark  # noqa: E402
import embedding_run  # noqa: E402
import embeddings  # noqa: E402
import main_scene  # noqa: E402
import run_routes  # noqa: E402
import run_steps  # noqa: E402
import variant_attributes  # noqa: E402

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

    def run_set(self, scene_selection=False, label_gate=None):
        backend = embedding_run.build_backend(self.embedding, self.lab.db_path,
                                              make_model=lambda e: TE.ColourModel(),
                                              segmenter=TE.FakeSam3(),
                                              scene_selection=scene_selection,
                                              label_gate=label_gate)
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
    def test_local_distance_cards_use_native_value_and_lower_direction(self):
        run_dir, rows = self.run_set()
        row = rows["green/01.png"]
        candidate = row["candidates"][0]
        bottle_score = candidate["score"]
        ref = next(i for i in candidate["items"] if i["view"] == "label")
        candidate["comparison"] = {"field": "aligned_distance", "value": .12,
            "bottle_rank": 2, "bottle_score": bottle_score,
            "reference": dict(ref, source_sha256=ref["sha256"])}
        row["trace"]["steps"].append({"id": "local-comparison", "out": {
            "applied": True, "field": "aligned_distance", "higher_is_better": False,
            "cached_pairs": 18, "fresh_pairs": 2}})
        meta_path = Path(run_dir) / "run.json"
        meta = json.loads(meta_path.read_text())
        meta["backend"]["local_comparison"] = {"method": "lpips-aligned_distance", "index": "gw"}
        meta_path.write_text(json.dumps(meta))
        write_rows(run_dir, [row if r["query_id"] == row["query_id"] else r for r in read_rows(run_dir)])
        code, body = self.steps(os.path.basename(run_dir), row["query_id"])
        self.assertEqual(code, 200)
        part = next(s for s in self.all_steps(body) if s["id"] == "local-comparison")
        card = part["lists"][0]["items"][0]
        self.assertEqual(card["score"], .12)
        self.assertIn("lower better", card["detail"])
        self.assertIn("bottle rank 2", card["detail"])
        self.assertTrue(card["image"].startswith("/embeddings/gw/images/"))
        self.assertEqual(candidate["score"], bottle_score)
        self.assertTrue(any("18 cached pairs; 2 fresh pairs" in n for n in part["notes"]))

    def test_local_comparison_failure_explains_bottle_fallback(self):
        run_dir, rows = self.run_set()
        row = rows["green/01.png"]
        row["trace"]["steps"].append({"id": "local-comparison", "out": {
            "applied": False, "reason": "comparison_failed", "error": "local model failed"}})
        meta_path = Path(run_dir) / "run.json"
        meta = json.loads(meta_path.read_text())
        meta["backend"]["local_comparison"] = {"method": "dinov2-score", "index": "gw"}
        meta_path.write_text(json.dumps(meta))
        write_rows(run_dir, [row if r["query_id"] == row["query_id"] else r for r in read_rows(run_dir)])
        code, body = self.steps(os.path.basename(run_dir), row["query_id"])
        self.assertEqual(code, 200)
        part = next(s for s in self.all_steps(body) if s["id"] == "local-comparison")
        self.assertIn("Bottle fallback: comparison_failed", part["notes"])
        self.assertIn("Comparison error: local model failed", part["notes"])

    def test_variant_details_show_each_attribute_match_and_conflict(self):
        run_dir, rows = self.run_set()
        row = rows["green/01.png"]
        original = row["candidates"][:3]
        first, second, third = [c["slug"] for c in original]
        catalogue = {first: {"name": "Брют Rose Reserve", "grapes": "Мерло"},
                     second: {"name": "Брют Red Reserve", "grapes": "Мерло"},
                     third: {"name": "Полусладкое White", "grapes": "Каберне Совиньон"}}
        answer, evidence = variant_attributes.verify(original,
            [{"text": "BRUT MERLOT RED RESERVE", "confidence": 98}], catalogue,
            {"window": 10, "min_confidence": 70})
        row["candidates"] = answer
        row["trace"]["steps"].append({"id": "label-text", "out": evidence})
        write_rows(run_dir, [row if r["query_id"] == row["query_id"] else r for r in read_rows(run_dir)])
        code, body = self.steps(os.path.basename(run_dir), row["query_id"])
        self.assertEqual(code, 200)
        part = next(s for s in self.all_steps(body) if s["id"] == "label-text")
        items = part["lists"][0]["items"]
        self.assertEqual(items[0]["slug"], second)
        self.assertEqual(items[0]["moved"], 1)
        self.assertEqual(items[0]["score"], original[1]["score"])
        self.assertIn("Grapes: merlot · match", items[0]["detail"])
        self.assertIn("Colour: red · match", items[0]["detail"])
        self.assertIn("Product line: reserve · match", items[0]["detail"])
        self.assertIn("Colour: rose · conflict", items[1]["detail"])
        self.assertTrue(any("distinguishes shortlisted variants" in note for note in part["notes"]))

    def test_shared_normalization_details_keep_raw_ocr_and_show_correction(self):
        run_dir, rows = self.run_set()
        row = rows["green/01.png"]
        original = row["candidates"][:2]
        first, second = [c["slug"] for c in original]
        words = [{"text": "MYCKАТ", "confidence": 97.78}]
        answer, evidence = variant_attributes.verify(original, words,
            {first: {"grapes": "Саперави"}, second: {"grapes": "Мускат"}},
            {"window": 10, "min_confidence": 70})
        row["candidates"] = answer
        row["trace"]["steps"].append({"id": "label-text", "out": evidence})
        write_rows(run_dir, [row if r["query_id"] == row["query_id"] else r for r in read_rows(run_dir)])
        code, body = self.steps(os.path.basename(run_dir), row["query_id"])
        self.assertEqual(code, 200)
        part = next(s for s in self.all_steps(body) if s["id"] == "label-text")
        self.assertEqual(part["result"]["words"], words)
        self.assertTrue(any("MYCKАТ → мускат" in note and "97.78" in note for note in part["notes"]))

    def test_variant_details_show_unknown_and_unused_fields_without_reordering(self):
        run_dir, rows = self.run_set()
        row = rows["green/01.png"]
        original = row["candidates"][:3]
        catalogue = {c["slug"]: {"name": "Brut", "grapes": "Мерло"} for c in original}
        row["candidates"], evidence = variant_attributes.verify(original,
            [{"text": "MERLOT", "confidence": 99}], catalogue, {"window": 10, "min_confidence": 70})
        self.assertFalse(evidence["applied"])
        row["trace"]["steps"].append({"id": "label-text", "out": evidence})
        write_rows(run_dir, [row if r["query_id"] == row["query_id"] else r for r in read_rows(run_dir)])
        code, body = self.steps(os.path.basename(run_dir), row["query_id"])
        self.assertEqual(code, 200)
        part = next(s for s in self.all_steps(body) if s["id"] == "label-text")
        items = part["lists"][0]["items"]
        self.assertEqual([i["slug"] for i in items], [c["slug"] for c in original])
        self.assertIn("Grapes: merlot · unused", items[0]["detail"])
        self.assertIn("Colour: unknown · unused", items[0]["detail"])
        self.assertTrue(all(not item.get("moved") for item in items))

    def test_paddle_text_details_show_recorded_evidence_and_reordered_answer(self):
        run_dir, rows = self.run_set()
        row = rows["green/01.png"]
        original = row["candidates"][:3]
        reordered = [original[2], original[0], original[1]]
        visual_ranks = {c["slug"]: c["rank"] for c in original}
        for rank, candidate in enumerate(reordered, 1):
            candidate["variant_text"] = {"expected": "brut", "status": "match",
                                         "visual_rank": visual_ranks[candidate["slug"]]}
            candidate["rank"] = rank
        row["candidates"] = reordered
        row["trace"]["steps"].append({"id": "label-text", "out": {
            "observed_sugar": "brut", "applied": True, "reason": "explicit_variant_text",
            "words": [{"text": "БРЮТ", "confidence": 82.68}]}})
        path = Path(run_dir) / "run.json"
        meta = json.loads(path.read_text())
        meta["backend"]["main_label"] = {"ocr": "paddleocr", "min_confidence": 70}
        path.write_text(json.dumps(meta))
        write_rows(run_dir, [row if r["query_id"] == row["query_id"] else r
                             for r in read_rows(run_dir)])
        code, body = self.steps(os.path.basename(run_dir), row["query_id"])
        self.assertEqual(code, 200, body)
        part = next(s for s in self.all_steps(body) if s["id"] == "label-text")
        self.assertEqual(part["model"], "PaddleOCR PP-OCRv5 East Slavic")
        self.assertEqual(part["result"]["words"], [{"text": "БРЮТ", "confidence": 82.68}])
        first = part["lists"][0]["items"][0]
        self.assertEqual((first["slug"], first["rank"], first["moved"]),
                         (original[2]["slug"], 1, 2))
        self.assertEqual(first["score"], original[2]["score"])

    def test_gated_steps_show_quality_and_routing_without_a_rejected_label_input(self):
        run_dir, rows = self.run_set(label_gate={})
        row = rows["green/01.png"]
        code, body = self.steps(os.path.basename(run_dir), row["query_id"])
        self.assertEqual(code, 200, body)
        parts = self.all_steps(body)
        quality = next(part for part in parts if part["id"] == "label-quality")
        route = next(part for part in parts if part["id"] == "label-route")
        label = next(part for part in parts if part["id"] == "view" and part["view"] == "label")
        self.assertFalse(quality["result"]["passed"])
        self.assertEqual(quality["name"], "Label crop quality · Rejected")
        self.assertTrue(any("minimum 128 px on each side" in note for note in quality["notes"]))
        self.assertIn("The label input is skipped. Matching falls back to the bottle space.",
                      quality["notes"])
        self.assertIn("insufficient_native_detail", quality["result"]["reasons"])
        self.assertEqual(route["result"]["selected_view"], "full")
        self.assertEqual(route["settings"]["label_gate"]["min_score"], .90)
        self.assertTrue(any("bottle ranking" in note for note in route["notes"]))
        self.assertEqual((label["state"], label["artifacts"]), ("skipped", []))
        self.assertFalse(any(part["id"] == "search" and part.get("view") == "label"
                             for part in parts))
        score = next(part for part in parts if part["id"] == "score")
        self.assertEqual(score["result"]["selected_view"], "full")

    def test_accepted_crop_details_do_not_claim_that_labels_were_selected(self):
        run_dir, rows = self.run_set(label_gate={"min_native_side": 1, "min_input_side": 1,
                                               "min_purity": 0, "min_sharpness": 0,
                                               "min_margin": 2})
        code, body = self.steps(os.path.basename(run_dir), rows["green/01.png"]["query_id"])
        self.assertEqual(code, 200, body)
        parts = self.all_steps(body)
        quality = next(part for part in parts if part["id"] == "label-quality")
        route = next(part for part in parts if part["id"] == "label-route")
        self.assertEqual(quality["name"], "Label crop quality · Accepted")
        self.assertIn("Similarity and margin are checked next.", quality["notes"][-1])
        self.assertEqual(route["name"], "Select retrieval space · Bottle")
        self.assertTrue(any("insufficient lead" in note for note in route["notes"]))
        self.assertTrue(any("Label margin:" in note and "minimum 2.0000" in note
                            for note in route["notes"]))

    def test_crop_details_use_recorded_signals_and_thresholds(self):
        result = {"passed": False, "reasons": ["unrelated_content"], "signals": {
            "purity": .37023, "detector_score": .95166, "native_label_size": [699.22, 720.70],
            "input_label_size": [447, 462], "sharpness": 6236.3755, "package_overlap": 1.0,
        }}
        options = {"min_purity": .85, "min_detector_score": .7, "min_native_side": 128,
                   "min_input_side": 128, "min_sharpness": 80, "min_package_overlap": .8}
        part = run_steps.quality_step({"out": result}, options)
        self.assertEqual(part["result"], result)
        self.assertEqual(part["group"], "label content 37.0%")
        self.assertIn("FAIL · Label content: 37.0% (minimum 85.0%).", part["notes"])
        self.assertIn("PASS · Detector confidence: 0.9517 (minimum 0.7000).", part["notes"])
        self.assertIn("Rejected: The crop contains too much glass or other unrelated content.",
                      part["notes"])

    def test_absent_crop_measurements_are_not_presented_as_zero_or_passed(self):
        part = run_steps.quality_step({"out": {"passed": False, "reasons": ["no_label"]}}, {})
        self.assertEqual(part["name"], "Label crop quality · Rejected")
        self.assertIn("Label content: not measured.", part["notes"])
        self.assertFalse(any(note.startswith("PASS") for note in part["notes"]))
        self.assertIn("Rejected: No label was detected.", part["notes"])

    def test_the_package_result_explains_the_main_scene_selection(self):
        run_dir, rows = self.run_set(scene_selection=True)
        row = rows["green/01.png"]
        code, body = self.steps(os.path.basename(run_dir), row["query_id"])
        package = next(part for part in self.all_steps(body) if part["id"] == "sam3-package")
        selection = package["result"]["selection"]
        self.assertEqual((code, package["name"], selection["version"]),
                         (200, "Package selection and cut", main_scene.VERSION))
        self.assertEqual(selection["selected"]["label"], "bottle")
        self.assertTrue(selection["candidates"][0]["selected"])
        self.assertIn("scene_score", selection["candidates"][0])
        self.assertIn("main-scene selector chose bottle", package["notes"][-1])

    def test_the_step_replay_keeps_the_saved_selector_version(self):
        run_dir, rows = self.run_set(scene_selection=1)
        with mock.patch.object(embedding_run, "cuts_of", wraps=embedding_run.cuts_of) as cut:
            code, body = self.steps(os.path.basename(run_dir), rows["green/01.png"]["query_id"])
        self.assertEqual(code, 200, body)
        package_call = next(call for call in cut.call_args_list if "package" in call.args[1])
        self.assertIs(type(package_call.kwargs["scene_selection"]), int)
        self.assertEqual(package_call.kwargs["scene_selection"], 1)

    def test_the_package_result_explains_restored_mask_holes(self):
        run_dir, rows = self.run_set(scene_selection=True)
        saved = read_rows(run_dir)
        for row in saved:
            for record in row["trace"]["steps"]:
                if record["id"] == "sam3-package":
                    record["out"]["selection"]["mask_holes_restored_pixels"] = 120
        write_rows(run_dir, saved)
        code, body = self.steps(os.path.basename(run_dir), rows["green/01.png"]["query_id"])
        self.assertEqual(code, 200, body)
        package = next(part for part in self.all_steps(body) if part["id"] == "sam3-package")
        self.assertTrue(any("Restored 120 pixels" in note for note in package["notes"]))

    def test_the_visual_cache_separates_selector_versions(self):
        photo = types.SimpleNamespace(path="/fake/photo.png", image=Image.new("RGB", (20, 20)))
        key1 = run_steps._visual_key(photo, {}, "http://fake-sam3", 1)
        key2 = run_steps._visual_key(photo, {}, "http://fake-sam3", main_scene.VERSION)
        self.assertNotEqual(key1, key2)
        self.assertEqual(key2, run_steps._visual_key(photo, {}, "http://fake-sam3", True))
        self.assertNotEqual(key2, run_steps._visual_key(photo, {}, "http://fake-sam3", 2))
        self.assertNotEqual(key2, run_steps._visual_key(photo, {}, "http://fake-sam3", 3))

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
        self.assertTrue(package["artifacts"][1]["src"].startswith("/api/run-artifact?"))
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

    def test_a_hit_at_an_angle_shows_the_index_image_rotated(self):
        run_dir, _ = self.run_set()
        rows = read_rows(run_dir)
        search = next(part for part in rows[0]["trace"]["steps"]
                      if part["id"] == "search" and part["view"] == "full")
        top = search["out"]["top"]
        top[0]["angle"], top[1]["angle"] = 90, 0
        write_rows(run_dir, rows)
        code, body = self.steps(os.path.basename(run_dir), rows[0]["query_id"])
        part = next(part for part in self.all_steps(body)
                    if part["name"] == "Search, space full")
        items = part["lists"][0]["items"]
        self.assertEqual(code, 200)
        self.assertTrue(items[0]["image"].startswith("/api/run-preview?"))
        self.assertTrue(items[0]["image_deferred"])
        query = run_steps.urllib.parse.parse_qs(run_steps.urllib.parse.urlsplit(items[0]["image"]).query)
        status, data, content_type, _ = run_routes.preview_view(self.runs, self.lab.db_path, query)
        self.assertEqual((status, content_type), (200, "image/png"))
        with Image.open(io.BytesIO(data)) as rotated, \
                Image.open(os.path.join(
                    embeddings.entry_dir(self.lab.db_path, "gw"), embeddings.IMAGES,
                    embeddings.image_name(top[0]["sha256"], "full"))) as stored:
            self.assertEqual(rotated.size, (stored.height, stored.width))
        self.assertTrue(items[1]["image"].startswith("/embeddings/gw/images/"))
        self.assertEqual([item["detail"].rsplit(" · ", 1)[-1] for item in items[:2]],
                         ["90°", "0°"])
        self.assertNotIn("°", items[2]["detail"])

    def test_the_embedding_rerank_step_exposes_option_and_decision_scores(self):
        run_dir, _ = self.run_set()
        rows = read_rows(run_dir)
        row = next(record for record in rows if record["image_path"] == "green/01.png")
        first, second = row["candidates"][:2]
        window = [second["slug"], first["slug"]]
        result = {
            "kind": "cluster_rules", "cluster": "abc123", "mode": "evidence",
            "source_mode": "verdict", "window": window,
            "ranking": [first["slug"], second["slug"]], "picture": "label",
            "questions": [{"id": "q1", "question": "What sugar level is printed?",
                           "options": ["semi-dry", "other", "not visible"],
                           "expected": {second["slug"]: None, first["slug"]: "semi-dry"}}],
            "option_scores": {"q1": {"semi-dry": 95, "other": 3, "not visible": 2}},
            "base_scores": {second["slug"]: 0.80, first["slug"]: 0.78},
            "evidence_scores": {second["slug"]: 0.0, first["slug"]: 0.93},
            "decision_scores": {second["slug"]: 0.80, first["slug"]: 0.8265},
            "decision_weight": 0.05, "cached": False, "ms": 1234, "error": None,
            "changed": True,
            "raw_option_scores": {"q1": {"semi-dry": 95, "other": 3, "not visible": 2}},
            "validation_errors": {},
            "attempts": [{"number": 1, "raw_text": "{invalid}",
                          "validation_errors": {"q1": "total 0; expected 100"}}],
        }
        row["trace"]["steps"].append({"id": "cluster_rules", "start_ms": 50,
                                      "ms": 1234, "out": result})
        first["explain"] = dict(result, base_rank=2, base_score=0.78, inner=None)
        second["explain"] = dict(result, base_rank=1, base_score=0.80, inner=None)
        write_rows(run_dir, rows)

        code, body = self.steps(os.path.basename(run_dir), row["query_id"])
        part = self.all_steps(body)[-1]
        self.assertEqual((code, len(body["rounds"]), part["name"]),
                         (200, 4, "VLM evidence re-rank"))
        self.assertEqual(part["vlm"]["option_scores"], result["option_scores"])
        self.assertEqual(part["vlm"]["evidence_scores"], result["evidence_scores"])
        self.assertEqual(part["vlm"]["decision_scores"], result["decision_scores"])
        self.assertEqual(part["vlm"]["raw_option_scores"], result["raw_option_scores"])
        self.assertEqual(part["vlm"]["validation_errors"], result["validation_errors"])
        self.assertEqual(part["vlm"]["attempts"], result["attempts"])
        self.assertIn("embedding 0.7800 · evidence 0.9300 · decision 0.8265",
                      part["lists"][0]["items"][0]["detail"])
        self.assertEqual(part["lists"][0]["items"][0]["moved"], 1)

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
        self.assertEqual((decode["ms"], decode["model"]), (12.5, "qr-scanner"))
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
