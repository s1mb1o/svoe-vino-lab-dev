import base64
import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import yaml
from PIL import Image

from image_description_fixture import ROOT, DescriptionCase

import describe_images as DI
import image_descriptions as DESC
import vlm_config

ANSWER = {"package_type": "bottle", "subject_scope": "full_package",
          "package_view": "front", "content_roles": ["front_label"]}
CFG = dict(DI.DEFAULTS, poll_seconds=1)
ENTRY = vlm_config.entry({"vlm": [{
    "name": "gx10-test", "protocol": "openai", "thinking_field": "chat_template_kwargs",
    "endpoint": "http://vlm.invalid/v1", "model": "model-1", "key": None}]}, "gx10-test")


def body(answer=ANSWER, text=None):
    return {"model": "Model-1", "choices": [{"message": {
        "content": text if text is not None else json.dumps(answer)}}]}


class FakeVlm:
    """Stands for `describe_images.post`. `during` runs inside the call."""

    def __init__(self, *bodies, during=None):
        self.bodies, self.during, self.payloads = list(bodies), during, []

    def __call__(self, entry, payload, timeout=None):
        self.payloads.append(payload)
        if self.during:
            self.during()
        item = self.bodies.pop(0) if len(self.bodies) > 1 else self.bodies[0]
        if isinstance(item, Exception):
            raise item
        return item

    def prompt(self, index=0):
        return self.payloads[index]["messages"][0]["content"][1]["text"]


def plan_blocks():
    text = (ROOT / "docs" / "plans" / "26_image-description.md").read_text(encoding="utf-8")
    section = text[text.index("## The prompt"):text.index("## The request")]
    return re.findall(r"```text\n(.*?)\n```", section, re.S)


class PromptTest(unittest.TestCase):
    def test_the_prompt_is_the_prompt_of_the_plan(self):
        prompt, facts = plan_blocks()
        self.assertEqual(DI.PROMPT, prompt)
        self.assertEqual(DI.prompt_text({"package_type": "tetra_pak"}),
                         DI.PROMPT + "\n" + facts)

    def test_the_fixed_facts_keep_the_field_order(self):
        text = DI.prompt_text({"package_view": "back", "content_roles": ["front_label"]})
        self.assertTrue(text.endswith(
            "agree with them:\npackage_view: back\ncontent_roles: [\"front_label\"]"))
        self.assertEqual(DI.prompt_text({}), DI.PROMPT)

    def test_the_schema_of_the_answer(self):
        self.assertEqual(DI.parse_answer(json.dumps(ANSWER)), ANSWER)
        both = dict(ANSWER, subject_scope="multiple_packages",
                    content_roles=["front_label", "back_label"])
        self.assertEqual(DI.parse_answer(json.dumps(both)), both)
        bad = ["not json", "```json\n%s\n```" % json.dumps(ANSWER), json.dumps([ANSWER]),
               json.dumps(dict(ANSWER, extra=1)), json.dumps(dict(ANSWER, package_view="side")),
               json.dumps({k: v for k, v in ANSWER.items() if k != "package_view"}),
               json.dumps(dict(ANSWER, content_roles=["unknown", "front_label"])),
               json.dumps(dict(ANSWER, content_roles=[])),
               json.dumps(dict(ANSWER, content_roles="front_label"))]
        for text in bad:
            with self.subTest(text=text):
                with self.assertRaises(DI.DescribeError) as caught:
                    DI.parse_answer(text)
                self.assertTrue(caught.exception.counted)

    def test_the_schema_and_the_table_hold_the_same_values(self):
        for field, values in DESC.VALUES.items():
            spec = DI.ANSWER_SCHEMA["properties"][field]
            self.assertEqual(tuple((spec.get("items") or spec)["enum"]), values)


class PayloadTest(unittest.TestCase):
    def image_of(self, payload):
        url = payload["messages"][0]["content"][0]["image_url"]["url"]
        self.assertTrue(url.startswith("data:image/jpeg;base64,"))
        return Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1])))

    def test_the_request_of_the_gx10_gateway(self):
        payload = DI.payload_of(ENTRY, "data:image/jpeg;base64,AA==", "p")
        self.assertEqual((payload["model"], payload["temperature"], payload["max_tokens"]),
                         ("model-1", 0, 300))
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertEqual(payload["chat_template_kwargs"], {"enable_thinking": False})
        self.assertNotIn("enable_thinking", payload)
        cloud = ENTRY._replace(thinking_field="top_level")
        payload = DI.payload_of(cloud, "data:image/jpeg;base64,AA==", "p")
        self.assertIs(payload["enable_thinking"], False)
        self.assertNotIn("chat_template_kwargs", payload)

    def test_the_image_is_scaled_down_and_put_on_white(self):
        with tempfile.TemporaryDirectory() as directory:
            big = "%s/big.png" % directory
            Image.new("RGB", (3000, 1500), "red").save(big)
            clear = "%s/clear.png" % directory
            Image.new("RGBA", (50, 50), (0, 0, 0, 0)).save(clear)
            image = self.image_of(DI.payload_of(ENTRY, DI.image_data_url(big, 1024), "p"))
            self.assertEqual(image.size, (1024, 512))
            image = self.image_of(DI.payload_of(ENTRY, DI.image_data_url(clear, 1024), "p"))
            self.assertEqual(image.size, (50, 50))
            self.assertGreater(min(image.convert("RGB").getpixel((25, 25))), 245)


class WatcherTest(DescriptionCase):
    def run_once(self, fake):
        with mock.patch.object(DI, "post", fake), \
                mock.patch.object(DI, "log", lambda message: None):
            return DI.run(self.db, ENTRY, CFG)

    def row(self, slug):
        with self.connect() as conn:
            return DESC.description(conn, self.sha[slug])

    def test_a_manual_value_is_kept_and_goes_into_the_prompt(self):
        with self.connect() as conn:
            DESC.set_values(conn, self.sha["wine-a"], {"package_type": "tetra_pak"})
        fake = FakeVlm(body())
        self.assertEqual(self.run_once(fake), 2)
        row = self.row("wine-a")
        self.assertEqual((row["package_type"], row["subject_scope"], row["package_view"],
                          row["content_roles"], row["created_by"]),
                         ("tetra_pak", "full_package", "front", ["front_label"], "manual"))
        self.assertEqual(row["vlm_answer"]["package_type"], "bottle")
        self.assertEqual((row["vlm_name"], row["vlm_model"]), ("gx10-test", "Model-1"))
        prompts = [fake.prompt(i) for i in range(2)]
        self.assertIn(DI.PROMPT, prompts)
        self.assertIn(DI.prompt_text({"package_type": "tetra_pak"}), prompts)
        self.assertEqual(self.row("wine-b")["created_by"], "vlm")

    def test_a_value_saved_during_the_call_is_kept(self):
        def save():
            with self.connect() as conn:
                DESC.set_values(conn, self.sha["wine-b"], {"package_view": "back"})
        self.run_once(FakeVlm(body(), during=save))
        row = self.row("wine-b")
        self.assertEqual((row["package_view"], row["package_type"]), ("back", "bottle"))
        self.assertEqual(row["vlm_answer"]["package_view"], "front")

    def test_a_filled_row_is_not_sent_again(self):
        fake = FakeVlm(body())
        self.run_once(fake)
        self.assertEqual(len(fake.payloads), 2)
        self.assertEqual(self.run_once(fake), 0)
        self.assertEqual(len(fake.payloads), 2)
        with mock.patch.object(DI, "post", fake), mock.patch.object(DI, "log", lambda m: None):
            self.assertFalse(DI.describe_one(self.db, ENTRY, CFG, self.sha["wine-a"],
                                             "main", "png"))
        self.assertEqual(len(fake.payloads), 2)

    def test_an_answer_that_fails_the_schema_writes_nothing(self):
        fake = FakeVlm(body(text=json.dumps(dict(ANSWER, package_view="side"))))
        self.assertEqual(self.run_once(fake), 0)
        self.assertEqual(len(fake.payloads), 6)
        for slug in ("wine-a", "wine-b"):
            row = self.row(slug)
            self.assertEqual((row["package_view"], row["vlm_at"], row["vlm_attempts"]),
                             (None, None, 3))
            self.assertIn("fails the schema at package_view", row["vlm_error"])
        self.assertEqual(self.cache_files(), [])

    def test_a_valid_answer_is_cached_and_read_back(self):
        fake = FakeVlm(body())
        self.run_once(fake)
        self.assertEqual(len(self.cache_files()), 2)
        with mock.patch.object(DI, "post", fake):
            answer, model, _, hit = DI.describe(ENTRY, str(
                self.root / "images" / "main" / ("%s.png" % self.sha["wine-a"])), {}, 1024)
        self.assertEqual((answer, model, hit), (ANSWER, "Model-1", True))
        self.assertEqual(len(fake.payloads), 2)

    def test_a_failure_of_the_service_is_not_counted(self):
        fake = FakeVlm(DI.DescribeError("HTTP 503: busy", counted=False))
        with self.assertRaises(DI.DescribeError):
            self.run_once(fake)
        row = self.row("wine-b")
        self.assertEqual((row["vlm_attempts"], row["vlm_error"]), (0, "HTTP 503: busy"))
        self.assertIsNone(self.row("wine-a"))

    def test_a_missing_file_is_a_counted_failure(self):
        (self.root / "images" / "main" / ("%s.png" % self.sha["wine-b"])).unlink()
        self.run_once(FakeVlm(body()))
        self.assertEqual(self.row("wine-b")["vlm_attempts"], 3)
        self.assertIsNotNone(self.row("wine-a")["vlm_at"])

    def test_the_watcher_stops_when_its_parent_is_gone(self):
        child = subprocess.Popen([sys.executable, "-c", "pass"])
        child.wait()
        fake = FakeVlm(body())
        with mock.patch.object(DI, "post", fake), mock.patch.object(DI, "log", lambda m: None):
            self.assertEqual(DI.run(self.db, ENTRY, CFG, watch=True, parent_pid=child.pid), 0)
        self.assertEqual(fake.payloads, [])

    def test_the_watcher_waits_while_the_schema_differs(self):
        with self.connect() as conn:
            conn.execute("PRAGMA user_version = 1")
        with self.assertRaises(DI.WaitError):
            self.run_once(FakeVlm(body()))

    def test_the_watcher_writes_its_state(self):
        seen = []

        def look():
            seen.append(DESC.read_status())
        self.run_once(FakeVlm(body(), during=look))
        self.assertEqual([s["state"] for s in seen], ["working", "working"])
        self.assertEqual([s["sha256"] for s in seen], [self.sha["wine-b"], self.sha["wine-a"]])
        self.assertIsNone(seen[0]["last"])
        self.assertEqual(seen[1]["last"]["sha256"], self.sha["wine-b"])
        self.assertTrue(seen[1]["last"]["described"])
        final = DESC.read_status()
        self.assertEqual((final["state"], final["vlm"], final["model"], final["max_attempts"]),
                         ("stopped", "gx10-test", "model-1", 3))
        self.assertIsInstance(final["seconds_per_image"], float)
        self.assertEqual(final["pid"], DI.os.getpid())

    def test_a_failure_of_the_service_writes_the_state_waiting(self):
        states = []
        fake = FakeVlm(DI.DescribeError("HTTP 503: busy", counted=False))
        with mock.patch.object(DI, "post", fake), \
                mock.patch.object(DI, "log", lambda message: None), \
                mock.patch.object(DI, "sleep", lambda seconds, pid: states.append(
                    DESC.read_status()) and False):
            DI.run(self.db, ENTRY, CFG, watch=True)
        self.assertEqual((states[0]["state"], states[0]["error"]), ("waiting", "HTTP 503: busy"))
        self.assertEqual(DESC.read_status()["state"], "stopped")

    def test_one_watcher_at_a_time(self):
        with mock.patch.object(DI, "LOCK_PATH", str(self.root / "describe.lock")):
            first = DI.take_lock(False)
            self.assertIsNotNone(first)
            self.assertIsNone(DI.take_lock(False))
            first.close()
            second = DI.take_lock(False)
            self.assertIsNotNone(second)
            second.close()


class SettingsTest(unittest.TestCase):
    def test_the_defaults_and_the_checks(self):
        self.assertEqual(DI.settings({}), DI.DEFAULTS)
        self.assertEqual(DI.settings({"image_description": {"max_side": 512}})["max_side"], 512)
        for value in ({"max_side": 0}, {"poll_seconds": "30"}, {"other": 1}, "on"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    DI.settings({"image_description": value})

    def test_the_project_configuration(self):
        config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
        cfg = DI.settings(config)
        self.assertEqual(cfg["vlm"], "qwen3.5-9b-nvfp4")
        self.assertEqual(vlm_config.entry(config, cfg["vlm"]).model, "qwen3.5-9b-nvfp4")


class CachedReplyTest(DescriptionCase):
    """`cached_reply`: the raw reply of the call that filled a row, for `/dataset`."""

    def run_once(self):
        with mock.patch.object(DI, "post", FakeVlm(body())), \
                mock.patch.object(DI, "log", lambda message: None):
            DI.run(self.db, ENTRY, CFG)

    def reply(self, slug):
        with self.connect() as conn:
            row = DESC.description(conn, self.sha[slug])
        path = str(self.root / "images" / "main" / ("%s.png" % self.sha[slug]))
        return DI.cached_reply(ENTRY, path, row, CFG["max_side"])

    def set_values(self, slug, values):
        with self.connect() as conn:
            DESC.set_values(conn, self.sha[slug], values)

    def test_the_record_of_the_filling_call_is_found(self):
        self.set_values("wine-a", {"package_type": "tetra_pak"})
        self.run_once()
        for slug, preset in (("wine-a", {"package_type": "tetra_pak"}), ("wine-b", {})):
            record = self.reply(slug)
            self.assertEqual(json.loads(
                record["answer"]["choices"][0]["message"]["content"]), ANSWER)
            self.assertEqual(record["request"]["prompt"][0]["content"][1]["text"],
                             DI.prompt_text(preset))

    def test_a_value_set_after_the_call_keeps_the_record(self):
        self.run_once()
        self.set_values("wine-b", {"package_view": "back"})
        self.assertIsNotNone(self.reply("wine-b"))

    def test_a_changed_fixed_fact_gives_no_record(self):
        self.set_values("wine-a", {"package_type": "tetra_pak"})
        self.run_once()
        self.set_values("wine-a", {"package_type": "box"})
        self.assertIsNone(self.reply("wine-a"))

    def test_a_record_with_another_answer_does_not_count(self):
        self.run_once()
        with self.connect() as conn:
            conn.execute("UPDATE image_description SET vlm_answer = ? WHERE sha256 = ?",
                         (json.dumps(dict(ANSWER, package_type="can")), self.sha["wine-b"]))
        self.assertIsNone(self.reply("wine-b"))


if __name__ == "__main__":
    unittest.main()
