"""Verify stored and recovered VLM inputs without model requests."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import cluster_rerank  # noqa: E402
import derive  # noqa: E402
import embedding_run  # noqa: E402
import label_rules  # noqa: E402
import model_cache  # noqa: E402
import rerank_images as RI  # noqa: E402
import run_routes  # noqa: E402
import run_steps  # noqa: E402


def png(color="red", size=(64, 80)):
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, "PNG")
    return buffer.getvalue()


class RerankImagesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(model_cache, "ROOT", str(self.root / "models")).start()
        RI.REQUESTS.clear()
        # Page reads MUST NOT send network requests, even on a cache miss.
        mock.patch.object(label_rules, "post", side_effect=AssertionError("VLM request")).start()
        mock.patch.object(derive.Sam3Client, "_send", side_effect=AssertionError("SAM3 request")).start()
        self.spec = {"rerank": {"model": "fixture-vlm", "side": 80}}
        self.scores = {"q1": {"2024": 100, "other": 0, "not visible": 0}}
        self.rule = {"questions": [{"id": "q1", "question": "What year?", "valid": True,
                                    "answers": {"a": "2024", "b": None}}]}
        self.result = {"mode": "evidence", "picture": "label", "option_scores": self.scores,
                       "questions": [{"id": "q1", "question": "What year?",
                                      "options": ["2024", "other", "not visible"]}]}
        self.photo = self.root / "photo.png"
        self.photo.write_bytes(png())

    def cache(self, data, text=None, prompt=None):
        content = [{"type": "image_url", "image_url": {"url": label_rules.data_url(data)}},
                   {"type": "text", "text": prompt or cluster_rerank.score_prompt(self.rule)}]
        fields = model_cache.vlm_fields("http://fixture/v1/chat/completions", {
            "model": "fixture-vlm", "messages": [{"role": "user", "content": content}]})
        model_cache.store(fields, {"choices": [{"message": {
            "content": text or json.dumps(self.scores)}}]}, 7)

    def test_save_deduplicates_exact_bytes_and_keeps_dimensions(self):
        data = png()
        info = RI.save(data, "label")
        self.assertEqual(info["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual((info["width"], info["height"]), (64, 80))
        self.assertEqual(RI.saved({"input_image": info}), (data, info))
        before = RI.image_path(info["sha256"]).stat().st_mtime_ns
        RI.save(data, "label")
        self.assertEqual(RI.image_path(info["sha256"]).stat().st_mtime_ns, before)

    def test_stored_image_survives_source_photo_removal(self):
        info = RI.save(png(), "photo")
        self.photo.unlink()
        self.assertEqual(RI.resolve({"input_image": info}, {}, None)[0], png())

    def test_corrupt_and_invalid_records_are_not_served(self):
        info = RI.save(png(), "label")
        RI.image_path(info["sha256"]).write_bytes(png("blue"))
        self.assertIsNone(RI.saved({"input_image": info}))
        self.assertIsNone(RI.saved({"input_image": {"sha256": "../../secret"}}))
        with self.assertRaises(RI.ImageUnavailable):
            RI.image_path("../../secret")

    def test_storage_error_is_metadata_and_does_not_stop_ranking(self):
        with mock.patch.object(Path, "mkdir", side_effect=OSError("disk full")):
            info = RI.save(png(), "label")
        self.assertIn("disk full", info["error"])
        self.assertEqual(info["sha256"], hashlib.sha256(png()).hexdigest())

    def test_historical_crop_must_match_the_cached_vlm_request(self):
        crop = Image.new("RGBA", (30, 60), (50, 60, 70, 128))
        expected = cluster_rerank.png_of(crop, 80)
        self.cache(expected)
        with mock.patch.object(embedding_run, "cuts_of", return_value={"label": ([0, 0, 30, 60], crop)}):
            actual, info = RI.resolve(self.result, self.spec, str(self.photo))
        self.assertEqual(actual, expected)
        self.assertEqual(info["provenance"], "cache")
        self.assertEqual((info["width"], info["height"]), (40, 80))

    def test_historical_wrong_crop_has_no_original_photo_fallback(self):
        self.cache(png("blue"))
        with mock.patch.object(embedding_run, "cuts_of", return_value={"label": ([0, 0, 64, 80], Image.new("RGB", (64, 80), "red"))}):
            with self.assertRaisesRegex(RI.ImageUnavailable, "does not match"):
                RI.resolve(self.result, self.spec, str(self.photo))

    def test_recovery_checks_recorded_questions_and_response(self):
        for prompt, text in (("Different question", None), (None, '{"q1":{"2024":0}}')):
            self.cache(png(), prompt=prompt, text=text)
        with self.assertRaisesRegex(RI.ImageUnavailable, "no matching cached request"):
            RI.resolve(self.result, self.spec, str(self.photo))

    def test_whole_photo_recovery_keeps_exact_scaled_png(self):
        self.result["picture"] = "photo"
        data = cluster_rerank.png_of(Image.new("RGB", (64, 80), "red"), 80)
        self.cache(data)
        self.assertEqual(RI.resolve(self.result, self.spec, str(self.photo))[0], data)

    def test_missing_input_never_calls_a_model(self):
        with mock.patch.object(embedding_run, "cuts_of", return_value={"label": None}):
            with self.assertRaisesRegex(RI.ImageUnavailable, "no matching cached request"):
                RI.resolve(self.result, self.spec, str(self.photo))

    def write_run(self, row):
        directory = self.root / "runs" / "fixture-run"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "run.json").write_text(json.dumps({"backend": self.spec}))
        (directory / "results.jsonl").write_text(json.dumps(row) + "\n")
        return str(directory.parent)

    def test_image_route_serves_recorded_bytes_after_photo_removal(self):
        data = png()
        result = dict(self.result, input_image=RI.save(data, "label"))
        directory = self.write_run({"query_id": "q-1", "trace": {"steps": [
            {"id": "cluster_rules", "out": result}]}})
        self.photo.unlink()
        response = run_routes.vlm_image_view(directory, "missing.sqlite3", {
            "id": ["fixture-run"], "query": ["q-1"]})
        self.assertEqual(response, (200, data, "image/png", "no-store"))

    def test_image_route_rejects_unknown_runs_queries_and_missing_evidence(self):
        directory = self.write_run({"query_id": "q-1"})
        for run, query, expected in (("../secret", "q-1", 400), ("missing", "q-1", 404),
                                      ("fixture-run", "missing", 404), ("fixture-run", "q-1", 404)):
            response = run_routes.vlm_image_view(directory, "missing.sqlite3", {
                "id": [run], "query": [query]})
            self.assertEqual(response[0], expected)

    def test_steps_route_adds_lazy_vlm_artifact_without_recovery(self):
        part = {"id": "cluster_rules", "n": 7, "artifacts": [],
                "result": self.result, "vlm": {"mode": "evidence"}}
        answer = {"run": "fixture-run", "query": "q-1", "rounds": [{"steps": [part]}]}
        with mock.patch.object(run_steps, "steps_view", return_value=answer), mock.patch.object(
                RI, "resolve", side_effect=AssertionError("eager image recovery")):
            response = run_routes.steps_view("runs", "db", {}, lambda conn: {})
        self.assertEqual(response[0], 200)
        artifact = response[1]["rounds"][0]["steps"][0]["artifacts"][0]
        self.assertTrue(artifact["deferred"])
        self.assertEqual(artifact["src"], "/api/run-vlm-image?id=fixture-run&query=q-1")
        self.assertIn("label crop", artifact["caption"])


if __name__ == "__main__":
    unittest.main()
