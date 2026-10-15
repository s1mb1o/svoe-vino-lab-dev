"""Verify the typed adapter and the existing rerank decision with fake services."""
import copy
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
os.environ.setdefault("SVOE_VINO_REVIEW_CONFIG", str(ROOT / "config.old.yaml"))
import cluster_rerank  # noqa: E402
import label_rules  # noqa: E402
import laya_v  # noqa: E402
import model_cache  # noqa: E402
import vlm_config  # noqa: E402


def rule():
    return {"mode": "sheet", "questions": [
        {"id": "q1", "question": "What grape is printed?", "valid": True,
         "kind": "feature", "answers": {"a": "Muscat", "b": "Chardonnay"}},
        {"id": "q2", "question": "What year is printed?", "valid": False,
         "kind": "vintage", "answers": {"a": None, "b": "2024"}}]}


def content():
    return [{"type": "image_url", "image_url": {"url": "data:image/png;base64,cG5n"}},
            {"type": "text", "text": cluster_rerank.score_prompt(rule())}]


def entry():
    return vlm_config.entry({"vlm": [{"name": "laya-v", "protocol": "laya-v",
                                    "thinking_field": "none", "model": "laya-v",
                                    "endpoint": "http://laya.invalid/upstream/laya-v/v1/"}]},
                            "laya-v")


def response():
    return {"model": "laya-v", "usage": {"input_tokens": 123, "output_tokens": 0},
            "answers": {
                "q1": {"type": "choice", "choice": "o1", "confidence": 0.6,
                       "probabilities": {"o0": 0.05, "o1": 0.8, "o2": 0.05, "o3": 0.1}},
                "q2": {"type": "choice", "choice": "o2", "confidence": 0.95,
                       "probabilities": {"o0": 0.03, "o1": 0.02, "o2": 0.95}}}}


class LayaVTest(unittest.TestCase):
    def setUp(self):
        self.schema = cluster_rerank.score_schema(rule())
        self.payload, self.options = laya_v.request_payload(content(), self.schema)

    def test_typed_request_has_one_choice_per_question(self):
        self.assertEqual(entry().url, "http://laya.invalid/upstream/laya-v/v1/systemone")
        self.assertEqual(self.payload["state"]["image"], content()[0]["image_url"]["url"])
        self.assertEqual(self.payload["questions"]["q1"]["criteria"],
                         {"o0": "Muscat", "o1": "Chardonnay", "o2": "other",
                          "o3": "not visible"})
        self.assertIn("What grape is printed?", self.payload["questions"]["q1"]["instructions"])
        self.assertTrue(all(q["type"] == "choice" for q in self.payload["questions"].values()))
        self.assertNotIn("messages", self.payload)

    def test_probabilities_use_existing_evidence_and_bounded_bonus(self):
        scores = laya_v.scores_of(response(), self.options)
        self.assertFalse(cluster_rerank.option_score_errors(rule(), scores))
        self.assertEqual(scores["q1"]["Chardonnay"], 80)
        evidence = cluster_rerank.evidence_scores(rule(), scores, ["a", "b"])
        # The unreadable vintage cannot support the card with an absent vintage.
        self.assertEqual(evidence, {"a": 0.0, "b": 0.35})
        decisions = {slug: base + cluster_rerank.DECISION_WEIGHT * evidence[slug]
                     for slug, base in {"a": 0.9, "b": 0.89}.items()}
        self.assertGreater(decisions["b"], decisions["a"])

    def test_rounding_keeps_total_100_and_preserves_all_options(self):
        body = response()
        body["answers"]["q2"].update(choice="o0", confidence=0.3333,
                                     probabilities={"o0": 0.3333, "o1": 0.3333, "o2": 0.3333})
        scores = laya_v.scores_of(body, self.options)
        self.assertEqual(scores["q2"], {"2024": 34, "other": 33, "not visible": 33})

    def test_invalid_or_partial_responses_are_rejected(self):
        mutations = [
            lambda b: b.update(model="qwen"),
            lambda b: b.update(extra=True),
            lambda b: b["answers"].pop("q2"),
            lambda b: b["answers"]["q1"].update(type="score"),
            lambda b: b["answers"]["q1"].update(choice="wrong"),
            lambda b: b["answers"]["q1"].update(choice="o0"),
            lambda b: b["answers"]["q1"].update(confidence=True),
            lambda b: b["usage"].update(input_tokens=True),
            lambda b: b["answers"]["q1"]["probabilities"].update(o0=True),
            lambda b: b["answers"]["q1"]["probabilities"].update(o0=float("nan")),
            lambda b: b["answers"]["q1"]["probabilities"].update(o0=float("inf")),
            lambda b: b["answers"]["q1"]["probabilities"].update(o0=-0.1),
            lambda b: b["answers"]["q1"]["probabilities"].update(o1=0.1),
            lambda b: b["answers"]["q1"]["probabilities"].update(extra=0),
        ]
        for i, mutate in enumerate(mutations):
            with self.subTest(i=i):
                body = copy.deepcopy(response())
                mutate(body)
                with self.assertRaises(laya_v.LayaVError):
                    laya_v.scores_of(body, self.options)

    def test_other_vlm_tasks_are_rejected_before_network(self):
        with mock.patch.object(laya_v, "post") as post:
            for schema in (None, cluster_rerank.verdict_schema({"letters": {"A": "a"}})):
                with self.assertRaises(label_rules.VlmError):
                    label_rules.ask(entry(), content(), 256, False, 2, schema=schema)
            post.assert_not_called()

    def test_dispatch_cache_and_fresh_retry(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(model_cache, "ROOT", folder), \
                mock.patch.object(model_cache, "READ", True), \
                mock.patch.object(laya_v, "post", return_value=response()) as post:
            first = label_rules.ask(entry(), content(), 256, False, 2, schema=self.schema)
            second = label_rules.ask(entry(), content(), 256, False, 2, schema=self.schema)
            third = label_rules.ask(entry(), content(), 256, False, 2, schema=self.schema,
                                    cache_read=False)
            self.assertEqual(post.call_count, 2)
            self.assertEqual([r["cached"] for r in (first, second, third)], [False, True, False])
            self.assertEqual(json.loads(first["text"]), laya_v.scores_of(response(), self.options))
            self.assertEqual(first["model"], "laya-v")

    def test_invalid_response_is_not_cached(self):
        invalid = response()
        invalid["answers"].pop("q2")
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(model_cache, "ROOT", folder), \
                mock.patch.object(laya_v, "post", return_value=invalid):
            with self.assertRaises(label_rules.VlmError):
                label_rules.ask(entry(), content(), 256, False, 2, schema=self.schema)
            self.assertEqual(list(Path(folder).rglob("*.json")), [])

    def test_http_request_uses_the_typed_route_and_body(self):
        with mock.patch.object(laya_v.urllib.request, "urlopen",
                               return_value=io.BytesIO(json.dumps(response()).encode())) as send:
            actual = laya_v.post(entry(), self.payload, 2)
        self.assertEqual(actual, response())
        request = send.call_args.args[0]
        self.assertEqual(request.full_url, entry().url)
        self.assertEqual(json.loads(request.data), self.payload)
        self.assertEqual(send.call_args.kwargs["timeout"], 2)

    def test_cluster_backend_moves_a_supported_card_and_preserves_failure_order(self):
        import test_cluster_rerank as fixture_module
        r = fixture_module.sheet_rule(slugs=(fixture_module.A, fixture_module.B),
                                      answers={fixture_module.A: "30/70",
                                               fixture_module.B: "50/50"})
        candidates = fixture_module.cands(fixture_module.A, fixture_module.B)
        probabilities = {"o0": 0.05, "o1": 0.85, "o2": 0.05, "o3": 0.05}
        body = {"model": "laya-v", "usage": {"input_tokens": 100, "output_tokens": 0},
                "answers": {"q1": {"type": "choice", "choice": "o1",
                                     "confidence": 0.5, "probabilities": probabilities}}}
        with tempfile.TemporaryDirectory() as folder:
            fixture = fixture_module.Fixture(folder, [r])
            config = yaml.safe_load(Path(fixture.config_path).read_text())
            config["vlm"] = [{"name": "laya-v", "protocol": "laya-v",
                              "thinking_field": "none", "model": "laya-v",
                              "endpoint": "http://laya.invalid/v1"}]
            Path(fixture.config_path).write_text(yaml.safe_dump(config))
            backend = cluster_rerank.ClusterRerank(
                fixture_module.Inner((candidates, 5, 200, None)),
                cluster_rerank.check_options({"vlm": "laya-v"}), "rules",
                fixture.config_path, fixture.db_path)
            backend.picture = lambda path: (b"png", "label")
            with mock.patch.object(model_cache, "ROOT", folder + "/cache"), \
                    mock.patch.object(laya_v, "post", return_value=body):
                new, explain = backend.rerank("unused", candidates)
            self.assertIsNone(explain["error"])
            self.assertEqual(new[0]["slug"], fixture_module.B)
            self.assertEqual([c["score"] for c in new], [c["score"] for c in candidates])
            self.assertEqual(explain["model"], "laya-v")
            with mock.patch.object(model_cache, "ROOT", folder + "/fresh-cache"), \
                    mock.patch.object(laya_v, "post", side_effect=laya_v.LayaVError("HTTP 503")):
                unchanged, explain = backend.rerank("unused", candidates)
            self.assertEqual([c["slug"] for c in unchanged], [c["slug"] for c in candidates])
            self.assertFalse(explain["changed"])
            self.assertIn("HTTP 503", explain["error"])

    def test_protocol_and_thinking_switch_must_agree(self):
        for protocol, field in (("openai", "none"), ("laya-v", "top_level")):
            with self.assertRaises(vlm_config.VlmConfigError):
                vlm_config.entries({"vlm": [{"name": "bad", "protocol": protocol,
                                            "thinking_field": field, "model": "m",
                                            "endpoint": "http://laya.invalid/v1"}]})

    def test_separate_configuration_preserves_retrieval_and_rerank_settings(self):
        import embeddings
        import pipelines
        config = yaml.safe_load((ROOT / "config.laya-v.yaml").read_text())
        original = yaml.safe_load((ROOT / "config.yaml").read_text())
        actual = config["pipeline"][0]
        base = next(p for p in original["pipeline"]
                    if p["name"] == "barcode-rerank-siglip2-p512-rot5-seg")
        for key in ("embedding", "views", "barcode"):
            self.assertEqual(actual[key], base[key])
        self.assertEqual(actual["rerank"], dict(base["rerank"], vlm="laya-v"))
        self.assertEqual(actual["workers"], 1)
        self.assertEqual(vlm_config.entry(config, "laya-v").protocol, "laya-v")
        settings = embeddings.load_settings(ROOT / "config.laya-v.yaml")
        settings.find(actual["embedding"])
        self.assertEqual(pipelines.Pipeline(actual).name, actual["name"])


if __name__ == "__main__":
    unittest.main()
