"""Verify OCR-only typed evaluation, cache identity and bounded ranking decisions."""
import copy
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from PIL import Image
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
os.environ.setdefault("SVOE_VINO_REVIEW_CONFIG", str(ROOT / "config.old.yaml"))
import cluster_rerank  # noqa: E402
import label_rules  # noqa: E402
import laya_ocr  # noqa: E402
import laya_v  # noqa: E402
import model_cache  # noqa: E402
import vlm_config  # noqa: E402


def rule():
    return {"key": "test", "mode": "sheet", "questions": [
        {"id": "q1", "question": "What grape is printed on the label?", "valid": True,
         "kind": "feature", "answers": {"a": "Muscat", "b": "Chardonnay"}}]}


def png():
    out = io.BytesIO()
    Image.new("RGB", (100, 200), "white").save(out, "PNG")
    return out.getvalue()


def content():
    return [{"type": "image_url", "image_url": {"url": label_rules.data_url(png())}},
            {"type": "text", "text": cluster_rerank.score_prompt(rule())}]


def words():
    return [{"text": "CHARDONNAY", "confidence": 92.25,
             "polygon": [[10, 20], [90, 20], [90, 40], [10, 40]]}]


def entry():
    return vlm_config.entry({"vlm": [{"name": "paddle-laya", "protocol": "laya-ocr",
                                    "thinking_field": "none", "model": "multilingual",
                                    "endpoint": "http://laya.invalid/upstream/laya/v1/"}]},
                            "paddle-laya")


def response():
    return {"model": "laya-rl-agent", "usage": {"input_tokens": 123, "output_tokens": 0},
            "answers": {"q1": {"type": "choice", "choice": "o1", "confidence": 0.6,
                               "probabilities": {"o0": 0.05, "o1": 0.8,
                                                 "o2": 0.05, "o3": 0.1}}}}


class LayaOCRTest(unittest.TestCase):
    def setUp(self):
        self.schema = cluster_rerank.score_schema(rule())
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        cache = mock.patch.object(model_cache, "ROOT", self.temp.name)
        cache.start()
        self.addCleanup(cache.stop)

    def test_sends_only_raw_ocr_text_and_positions(self):
        payload, options, image = laya_ocr.request_payload(entry(), content(), self.schema, words())
        self.assertEqual(image, png())
        self.assertEqual(payload["model"], "multilingual")
        self.assertEqual(payload["state"]["paddleocr_label_lines"], [
            {"text": "CHARDONNAY", "confidence": 92.25,
             "box_per_mille": [100, 100, 900, 200]}])
        self.assertNotIn("image", payload["state"])
        self.assertNotIn("data:image", json.dumps(payload))
        self.assertEqual(options["q1"]["o1"], "Chardonnay")
        self.assertIn("not visible", payload["questions"]["q1"]["instructions"])
        self.assertNotIn("supplied label image", payload["questions"]["q1"]["instructions"])

    def test_empty_ocr_is_explicit_and_keeps_abstention_option(self):
        payload, options, _ = laya_ocr.request_payload(entry(), content(), self.schema, [])
        self.assertEqual(payload["state"]["paddleocr_label_lines"], [])
        self.assertIn("not visible", options["q1"].values())

    def test_invalid_ocr_and_image_reject_before_remote_call(self):
        bad = [None, [{"text": "x", "confidence": float("nan")}],
               [{"text": "x", "confidence": True}],
               [{"text": "x", "confidence": 101}],
               [dict(words()[0], polygon=[[1, 2]])]]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(laya_v.LayaVError):
                laya_ocr.request_payload(entry(), content(), self.schema, value)
        invalid = content()
        invalid[0]["image_url"]["url"] = "data:image/png;base64,invalid"
        with self.assertRaises(laya_v.LayaVError):
            laya_ocr.request_payload(entry(), invalid, self.schema, words())

    def test_cache_identity_changes_with_ocr_and_bypasses_on_request(self):
        with mock.patch.object(laya_ocr, "recognize", return_value=words()) as ocr, \
                mock.patch.object(laya_v, "post", return_value=response()) as post:
            fresh = laya_ocr.ask(entry(), content(), 30, self.schema)
            cached = laya_ocr.ask(entry(), content(), 30, self.schema)
            self.assertFalse(fresh["cached"])
            self.assertTrue(cached["cached"])
            self.assertEqual(post.call_count, 1)
            changed = words()
            changed[0]["text"] = "MUSCAT"
            ocr.return_value = changed
            self.assertFalse(laya_ocr.ask(entry(), content(), 30, self.schema)["cached"])
            laya_ocr.ask(entry(), content(), 30, self.schema, cache_read=False)
            self.assertEqual(post.call_count, 3)

    def test_invalid_typed_answer_is_not_cached(self):
        bad = response()
        bad["answers"]["q1"]["probabilities"]["o1"] = 0.7
        with mock.patch.object(laya_ocr, "recognize", return_value=words()), \
                mock.patch.object(laya_v, "post", return_value=bad):
            with self.assertRaises(laya_v.LayaVError):
                laya_ocr.ask(entry(), content(), 30, self.schema)
        self.assertEqual(list(Path(self.temp.name).rglob("*.json")), [])

    def test_dispatch_and_actual_cluster_flip_use_same_bounded_scoring(self):
        backend = object.__new__(cluster_rerank.ClusterRerank)
        backend.options = dict(cluster_rerank.DEFAULTS, vlm="paddle-laya")
        backend.entry = entry()
        backend.book = mock.Mock()
        backend.book.trigger.return_value = (rule(), [0, 1])
        backend.picture = mock.Mock(return_value=(png(), "label"))
        backend.ask_fn = label_rules.ask
        candidates = [{"slug": "a", "score": 0.9}, {"slug": "b", "score": 0.89}]
        original = copy.deepcopy(candidates)
        with mock.patch.object(laya_ocr, "recognize", return_value=words()), \
                mock.patch.object(laya_v, "post", return_value=response()):
            ranked, evidence = backend.rerank("unused", candidates)
        self.assertEqual(ranked[0]["slug"], "b")
        self.assertEqual([c["score"] for c in ranked], [c["score"] for c in original])
        self.assertEqual(evidence["evidence_scores"], {"a": 0.0, "b": 0.7})
        self.assertEqual(evidence["decision_scores"]["b"], 0.925)
        self.assertEqual(candidates, original)

    def test_ocr_failure_keeps_visual_ranking(self):
        with mock.patch.object(laya_ocr, "recognize", side_effect=laya_v.LayaVError("OCR failed")), \
                mock.patch.object(laya_v, "post") as post:
            with self.assertRaises(label_rules.VlmError):
                label_rules.ask(entry(), content(), 256, False, 30, schema=self.schema)
            post.assert_not_called()

    def test_configuration_is_identical_except_reader(self):
        config = yaml.safe_load((ROOT / "config.yaml").read_text())
        pipelines = {p["name"]: p for p in config["pipeline"]}
        name = "barcode-rerank_paddle_laya-siglip2-p512-rot5-seg"
        base = pipelines["barcode-rerank-siglip2-p512-rot5-seg"]
        self.assertEqual(pipelines[name], dict(base, name=name,
                                               rerank=dict(base["rerank"], vlm="paddle-laya")))
        self.assertEqual(entry().url, "http://laya.invalid/upstream/laya/v1/systemone")
        for protocol, thinking in (("laya-ocr", "top_level"), ("openai", "none")):
            raw = entry()._asdict()
            raw.pop("key_env")
            raw.update(protocol=protocol, thinking_field=thinking)
            with self.assertRaises(vlm_config.VlmConfigError):
                vlm_config.entries({"vlm": [raw]})


if __name__ == "__main__":
    unittest.main()
