"""The label rule build of plan 45 on a small lab, with a fake VLM. No test calls gx10."""
import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path

import yaml

import embedding_lab  # noqa: F401  (puts pipeline/ on sys.path)
from test_clusters import ClusterLab

import clusters  # noqa: E402
import embeddings  # noqa: E402
import label_rules  # noqa: E402

FAKE_VLM = {"name": "fake-vlm", "protocol": "openai", "thinking_field": "chat_template_kwargs",
            "endpoint": "http://127.0.0.1:9/v1", "model": "fake-model"}
DESCRIPTION = {"texts": [{"text": "LABEL", "where": "centre"}], "numbers": [],
               "vintage": None, "colours": ["red"], "design": "plain", "marks": [],
               "bottle": "dark glass"}


class FakeVlm:
    """Answers stage 1 with `DESCRIPTION` and stage 2 with one name question."""

    def __init__(self):
        self.calls = []
        self.fail = None
        self.cut_first = False

    def __call__(self, entry, content, max_tokens, thinking, timeout, extra=None):
        texts = [part["text"] for part in content if part.get("type") == "text"]
        images = sum(1 for part in content if part.get("type") == "image_url")
        stage = "describe" if texts[-1] == label_rules.DESCRIBE_PROMPT else "rules"
        self.calls.append({"stage": stage, "images": images, "thinking": thinking,
                           "max_tokens": max_tokens, "texts": texts, "extra": extra})
        finish = "stop"
        if stage == "describe":
            answer = DESCRIPTION
            if self.cut_first and len(self.calls) == 1:
                finish = "length"
        else:
            if self.fail:
                raise self.fail
            letters = [text.split()[1].rstrip(":") for text in texts if text.startswith("Card ")]
            answer = {"differences": "the names", "rule": "Read the name.",
                      "questions": [{"question": "What name is printed on the label?",
                                     "answers": {x: "NAME %s" % x for x in letters}}],
                      "indistinguishable": []}
        return {"text": json.dumps(answer), "ms": 5, "usage": {}, "finish_reason": finish,
                "model": entry.model, "cached": False}

    def stage(self, name):
        return [call for call in self.calls if call["stage"] == name]


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fixture = ClusterLab(self.tmp.name)
        self.set_rules({})
        self.artifact = clusters.build_to_directory(self.fixture.settings, "gw")
        self.combined = self.artifact["spaces"]["combined"]["clusters"]
        self.vlm = FakeVlm()

    def tearDown(self):
        self.fixture.close()
        self.tmp.cleanup()

    def set_rules(self, block):
        """Write the fake VLM entry and `block` as `label_rules` of the lab config."""
        path = Path(self.fixture.lab.config_path)
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
        config["vlm"] = [FAKE_VLM]
        config["label_rules"] = {"vlm": "fake-vlm", "describe_workers": 2,
                                 "rules_workers": 2, **block}
        path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
        self.settings = embeddings.load_settings(str(path))

    def run_rules(self, **options):
        return label_rules.run(self.settings, "gw", ask_fn=self.vlm, log=lambda text: None,
                               **options)

    def stored(self):
        path = Path(self.fixture.lab.entry_dir()) / clusters.RULES_FILE
        return json.loads(path.read_text(encoding="utf-8"))

    def slugs(self):
        return sorted({s for cluster in self.combined for s in cluster["slugs"]})

    def test_the_first_run_writes_the_descriptions_and_the_rules(self):
        self.assertTrue(self.combined)
        summary = self.run_rules()
        data = self.stored()
        self.assertEqual(sorted(data["cards"]), self.slugs())
        for slug in self.slugs():
            self.assertEqual(data["cards"][slug]["description"]["texts"][0]["text"], "LABEL")
        rules = data["spaces"]["label"]
        self.assertEqual(sorted(rules), sorted(cluster["key"] for cluster in self.combined))
        for cluster in self.combined:
            rec = rules[cluster["key"]]
            self.assertIsNone(rec["error"])
            self.assertEqual(rec["mode"], "sheet")
            self.assertEqual(rec["input_hash"], self.artifact["input_hash"])
            self.assertEqual(sorted(rec["letters"].values()), sorted(cluster["slugs"]))
            q = rec["questions"][0]
            self.assertTrue(q["valid"])
            self.assertEqual(sorted(q["evidence"]), sorted(cluster["slugs"]))
            # The key `bottle` of a description stays out of stage 2.
            self.assertNotIn('"bottle"', rec["prompt"])
            self.assertIn('"LABEL"', rec["prompt"])
        rules_calls = self.vlm.stage("rules")
        self.assertEqual(len(rules_calls), len(self.combined))
        self.assertEqual(sorted(call["images"] for call in rules_calls),
                         sorted(cluster["size"] for cluster in self.combined))
        self.assertTrue(all(not call["thinking"] for call in self.vlm.calls))
        self.assertEqual({call["max_tokens"] for call in rules_calls}, {2500})
        self.assertEqual(summary["rules"]["modes"], {"sheet": len(self.combined)})
        self.assertEqual(data["prompts"]["rules"], label_rules.RULES_PROMPT)

    def test_a_second_run_makes_no_call(self):
        self.run_rules()
        self.vlm.calls.clear()
        summary = self.run_rules()
        self.assertEqual(self.vlm.calls, [])
        self.assertEqual(summary["describe"]["todo"], 0)
        self.assertEqual(summary["rules"]["todo"], 0)

    def test_a_new_note_builds_its_rule_again_and_the_page_shows_it(self):
        self.run_rules()
        cluster = self.combined[0]
        directory = self.fixture.lab.entry_dir()
        clusters.set_note(directory, cluster, "Look at the ratio.")
        detail = clusters.detail(self.settings, "gw")
        shown = next(c for c in detail["artifact"]["spaces"]["combined"]["clusters"]
                     if c["key"] == cluster["key"])
        # The view `combined` shows the rule of the space `label`, stale by its note.
        self.assertEqual(shown["rule"]["key"], cluster["key"])
        self.assertTrue(shown["rule"]["stale"])
        self.vlm.calls.clear()
        self.run_rules()
        self.assertEqual(len(self.vlm.stage("rules")), 1)
        self.assertEqual(self.vlm.stage("describe"), [])
        self.assertIn("Look at the ratio.", self.vlm.stage("rules")[0]["texts"][-1])
        rec = self.stored()["spaces"]["label"][cluster["key"]]
        self.assertEqual(rec["note"], "Look at the ratio.")
        detail = clusters.detail(self.settings, "gw")
        shown = next(c for c in detail["artifact"]["spaces"]["combined"]["clusters"]
                     if c["key"] == cluster["key"])
        self.assertFalse(shown["rule"]["stale"])

    def test_a_dry_run_makes_no_call_and_no_file(self):
        summary = self.run_rules(dry_run=True)
        self.assertEqual(self.vlm.calls, [])
        self.assertEqual(summary["describe"]["todo"], len(self.slugs()))
        self.assertEqual(summary["rules"]["todo"], len(self.combined))
        self.assertFalse((Path(self.fixture.lab.entry_dir()) / clusters.RULES_FILE).exists())

    def test_the_cluster_option_builds_one_cluster(self):
        cluster = self.combined[0]
        self.run_rules(cluster_slug=cluster["slugs"][0])
        data = self.stored()
        self.assertEqual(list(data["spaces"]["label"]), [cluster["key"]])
        self.assertEqual(sorted(data["cards"]), sorted(cluster["slugs"]))
        with self.assertRaises(label_rules.RuleError):
            self.run_rules(cluster_slug="no-such-wine")

    def test_a_cluster_over_the_image_limit_gets_an_error_and_no_call(self):
        self.set_rules({"rules_max_images": 1})
        summary = self.run_rules()
        self.assertEqual(self.vlm.stage("rules"), [])
        self.assertEqual(summary["rules"]["errors"], len(self.combined))
        rec = self.stored()["spaces"]["label"][self.combined[0]["key"]]
        self.assertIn("label_rules.rules_max_images is 1", rec["error"])

    def test_the_image_limit_of_the_service_stops_the_run(self):
        entry = label_rules.config_values(self.settings)["rules_entry"]
        self.vlm.fail = label_rules.ImageLimitError(
            label_rules.image_limit_message(entry, "1", 3))
        summary = self.run_rules()
        self.assertIn("--limit-mm-per-prompt", summary["stopped"])
        self.assertEqual(self.stored()["spaces"]["label"], {})

    def test_a_cluster_build_with_the_same_members_keeps_the_rules(self):
        self.run_rules()
        path = Path(self.fixture.lab.entry_dir()) / clusters.CLUSTERS_FILE
        artifact = json.loads(path.read_text(encoding="utf-8"))
        artifact["input_hash"] = "0" * 64
        path.write_text(json.dumps(artifact), encoding="utf-8")
        self.vlm.calls.clear()
        summary = self.run_rules()
        self.assertEqual(self.vlm.calls, [])
        self.assertEqual(summary["rules"]["restamped"], len(self.combined))
        for rec in self.stored()["spaces"]["label"].values():
            self.assertEqual(rec["input_hash"], "0" * 64)

    def test_a_label_cut_goes_to_stage_2_with_the_shared_caption(self):
        # Give the main image of `transparent` (also the main image of `shared`) a label cut.
        lab = self.fixture.lab
        cut = lab.store_file(embedding_lab.png(embedding_lab.bottle_on_transparent()),
                             "cropped", "png")
        lab.conn.execute(
            "INSERT INTO image_derivative (source_sha256, method, settings, sha256, "
            "box_left, box_top, box_right, box_bottom, kind) "
            "VALUES (?, 'seg', 'test', ?, 0, 0, 10, 10, 'label')", (lab.transparent, cut))
        lab.conn.commit()
        cluster = next(c for c in self.combined if {"transparent", "shared"} <= set(c["slugs"]))
        self.run_rules(cluster_slug="transparent")
        texts = self.vlm.stage("rules")[0]["texts"]
        self.assertTrue(any("the same catalogue picture as card" in text for text in texts))
        rec = self.stored()["spaces"]["label"][cluster["key"]]
        self.assertEqual(rec["questions"][0]["evidence"]["transparent"], [cut])

    def test_the_thinking_and_the_limits_come_from_the_config(self):
        self.set_rules({"rules_thinking": True, "rules_max_tokens": 16000,
                        "rules_timeout_s": 900})
        self.run_rules()
        self.assertTrue(all(call["thinking"] for call in self.vlm.stage("rules")))
        self.assertTrue(all(not call["thinking"] for call in self.vlm.stage("describe")))
        self.assertEqual({call["max_tokens"] for call in self.vlm.stage("rules")}, {16000})

    def test_an_answer_at_max_tokens_is_asked_again_with_a_repetition_penalty(self):
        self.vlm.cut_first = True
        self.set_rules({"describe_workers": 1})
        self.run_rules(stage="describe")
        first, second = self.vlm.calls[0], self.vlm.calls[1]
        self.assertEqual(first["max_tokens"], 1500)
        self.assertEqual(second["max_tokens"], 3000)
        self.assertEqual(second["extra"], {"repetition_penalty": label_rules.REPETITION_PENALTY})
        guarded = [rec for rec in self.stored()["cards"].values() if rec.get("loop_guard")]
        self.assertEqual(len(guarded), 1)

    def test_an_unknown_key_stops_the_build(self):
        self.set_rules({"size": 3})
        with self.assertRaises(label_rules.RuleError) as caught:
            self.run_rules()
        self.assertIn("unknown key: size", str(caught.exception))

    def test_a_second_build_waits_for_no_lock(self):
        directory = self.fixture.lab.entry_dir()
        with clusters.file_lock(directory, label_rules.LOCK, "held"):
            with self.assertRaises(clusters.Busy):
                self.run_rules()
        self.assertTrue(os.path.exists(os.path.join(directory, label_rules.LOCK)))

    def test_a_rebuild_with_wait_runs_after_the_running_build(self):
        # The rebuild after a note change waits for a running build (plan 45).
        directory = self.fixture.lab.entry_dir()
        held, release = threading.Event(), threading.Event()

        def hold():
            with clusters.file_lock(directory, label_rules.LOCK, "held"):
                held.set()
                release.wait(5)
        holder = threading.Thread(target=hold)
        holder.start()
        held.wait(5)
        old_poll, label_rules.LOCK_POLL_S = label_rules.LOCK_POLL_S, 0.05
        try:
            threading.Timer(0.5, release.set).start()
            started = time.monotonic()
            summary = self.run_rules(wait_lock=True)
            waited = time.monotonic() - started
        finally:
            label_rules.LOCK_POLL_S = old_poll
            release.set()
            holder.join(5)
        self.assertGreaterEqual(waited, 0.4)
        self.assertEqual(summary["rules"]["todo"], len(self.combined))


if __name__ == "__main__":
    unittest.main()
