import base64
import collections
import hashlib
import io
import json
import re
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from contextlib import closing
from unittest import mock

import yaml
from PIL import Image

from image_description_fixture import ROOT, DescriptionCase

import describe_images as DI
import image_descriptions as DESC
import label_descriptions as LD
import label_rules
import model_cache
import vlm_config

ANSWER = {"package_type": "bottle", "subject_scope": "full_package",
          "package_view": "front", "content_roles": ["front_label"],
          "presentation_mode": "on_package"}
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
               json.dumps(dict(ANSWER, content_roles="front_label")),
               json.dumps(dict(ANSWER, presentation_mode="table")),
               json.dumps({k: v for k, v in ANSWER.items() if k != "presentation_mode"})]
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

    def test_a_row_of_the_024_requeue_sends_its_old_values_as_fixed_facts(self):
        old = {"package_type": "bottle", "subject_scope": "label_closeup",
               "package_view": "back", "content_roles": ["back_label"]}
        with self.connect() as conn:
            DESC.record_vlm(conn, self.sha["wine-a"], dict(old, presentation_mode="other"),
                            "vlm-a", "Model-A")
            # The UPDATE of schema 024 (the column exists already in a new database).
            conn.execute("UPDATE image_description SET presentation_mode = NULL, "
                         "vlm_at = NULL, vlm_name = NULL, vlm_model = NULL, "
                         "vlm_answer = NULL, vlm_error = NULL, vlm_attempts = 0")
        answer = dict(ANSWER, presentation_mode="flat_surface")
        fake = FakeVlm(body(answer))
        self.assertEqual(self.run_once(fake), 2)
        self.assertIn(DI.prompt_text(old), [fake.prompt(i) for i in range(2)])
        self.assertIn("These values are already set.", DI.prompt_text(old))
        row = self.row("wine-a")
        self.assertEqual({field: row[field] for field in DESC.FIELDS},
                         dict(old, presentation_mode="flat_surface"))
        self.assertEqual(row["vlm_answer"], answer)

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


# Plan 29: the detail pass, stage 2 of the watcher.
DETAIL = {"texts": [{"text": "МЫСХАКО", "where": "main label"}],
          "numbers": [{"value": "1869", "where": "main label"}], "vintage": None,
          "colours": ["black", "gold"], "design": "a black label with gold text",
          "marks": [{"place": "neck label"}],
          "bottle": {"colour": "dark green", "shape": "standard", "capsule": "black"}}
LABEL_DETAIL = {key: value for key, value in DETAIL.items() if key != "bottle"}
DETAIL_CFG = dict(CFG, details=True)


def owner_prompts():
    """Return the two prompts of the owner message of 2026-09-25T19:14:31+0300."""
    text = (ROOT / "docs" / "owner-messages.md").read_text(encoding="utf-8")
    entry = text[text.index("## 2026-09-25T19:14:31+0300"):]
    entry = entry[:entry.index("\n## ", 5)]
    return re.findall(r"```\n(.*?)\n```", entry, re.S)


def detail_validator(kind, key="bottle"):
    return DI.jsonschema.Draft202012Validator(DI.detail_schema(kind, key))


class DetailPromptTest(unittest.TestCase):
    def test_the_bottle_prompts_are_the_prompts_of_the_owner(self):
        package, label = owner_prompts()
        self.assertEqual(DI.detail_prompt("package", "bottle"), package)
        self.assertEqual(DI.detail_prompt("label", "bottle"), label)

    def test_the_templates_are_the_templates_of_the_plan(self):
        text = (ROOT / "docs" / "plans" / "29_image-details.md").read_text(encoding="utf-8")
        blocks = re.findall(r"```text\n(This is a catalogue.*?)\n```", text, re.S)
        self.assertEqual(blocks, [DI.PACKAGE_PROMPT, DI.LABEL_PROMPT])

    def test_another_package_type_replaces_the_word_bottle(self):
        text = DI.detail_prompt("package", "tetra_pak")
        self.assertNotIn("bottle", text)
        self.assertTrue(text.startswith("This is a catalogue photo of one wine Tetra Pak "
                                        "carton. Describe its label, so that a person can "
                                        "tell this Tetra Pak carton apart from similar "
                                        "Tetra Pak cartons of the same producer."))
        self.assertTrue(text.endswith('"tetra_pak": the colour and the shape of the Tetra '
                                      'Pak carton and of the capsule.'))
        self.assertTrue(DI.detail_prompt("label", "can").startswith(
            "This is a catalogue photo of one wine can label. Describe it.\n"))
        for package_type in DI.image_details.NAMES:
            for kind in ("package", "label"):
                with self.subTest(package_type=package_type, kind=kind):
                    prompt = DI.detail_prompt(kind, package_type)
                    self.assertNotIn("{name", prompt)
                    self.assertNotIn("{key}", prompt)

    def test_the_schema_of_a_detail_answer(self):
        package, label = detail_validator("package"), detail_validator("label")
        self.assertEqual(DI.parse_answer(json.dumps(DETAIL), package), DETAIL)
        self.assertEqual(DI.parse_answer(json.dumps(LABEL_DETAIL), label), LABEL_DETAIL)
        good = [dict(DETAIL, vintage="2021"), dict(DETAIL, vintage=2021),
                dict(DETAIL, colours="black and gold"), dict(DETAIL, marks=["a medal, top"]),
                dict(DETAIL, bottle="dark green, standard shape"),
                dict(DETAIL, numbers=[{"value": 12.5, "where": "bottom"}])]
        for answer in good:
            with self.subTest(answer=answer):
                self.assertEqual(DI.parse_answer(json.dumps(answer), package), answer)
        probe = {("text" if key == "texts" else key): value for key, value in DETAIL.items()}
        bad = [(package, probe), (package, dict(DETAIL, extra=1)), (package, LABEL_DETAIL),
               (package, dict(DETAIL, texts=[{"text": "МЫСХАКО"}])),
               (package, dict(DETAIL, vintage=[2021])), (package, dict(DETAIL, design=None)),
               (label, DETAIL), (detail_validator("package", "can"), DETAIL)]
        for validator, answer in bad:
            with self.subTest(answer=answer):
                with self.assertRaises(DI.DescribeError) as caught:
                    DI.parse_answer(json.dumps(answer), validator)
                self.assertIn("fails the schema", str(caught.exception))


class DetailSettingsTest(unittest.TestCase):
    def test_the_detail_keys(self):
        cfg = DI.settings({})
        self.assertEqual((cfg["details"], cfg["detail_max_side"]), (False, 1536))
        for value in ({"details": "yes"}, {"details": 1}, {"detail_max_side": 0}):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    DI.settings({"image_description": value})

    def test_detail_max_tokens_is_replaced_by_max_tokens_of_the_vlm_entry(self):
        with self.assertRaises(ValueError) as caught:
            DI.settings({"image_description": {"detail_max_tokens": 4096}})
        self.assertIn("max_tokens of the vlm entry", str(caught.exception))

    def test_the_project_configuration_turns_the_details_on(self):
        config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
        cfg = DI.settings(config)
        self.assertEqual((cfg["details"], cfg["detail_max_side"]), (True, 1536))
        self.assertEqual(vlm_config.entry(config, cfg["vlm"]).max_tokens, 8192)


class RouteVlm(FakeVlm):
    """Answers a class prompt with `klass` and a detail prompt with `detail`. `states`
    keeps the state file at each call."""

    def __init__(self, detail, klass=None):
        super().__init__(detail)
        self.klass, self.states = klass or body(), []

    def __call__(self, entry, payload, timeout=None):
        self.states.append(DESC.read_status())
        if payload["messages"][0]["content"][1]["text"].startswith("Classify"):
            self.payloads.append(payload)
            return self.klass
        return super().__call__(entry, payload, timeout)

    def details(self):
        return [p for p in self.payloads
                if not p["messages"][0]["content"][1]["text"].startswith("Classify")]


def image_size(payload):
    url = payload["messages"][0]["content"][0]["image_url"]["url"]
    return Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1]))).size


class DetailWatcherTest(DescriptionCase):
    def run_once(self, fake, cfg=DETAIL_CFG):
        with mock.patch.object(DI, "post", fake), \
                mock.patch.object(DI, "log", lambda message: None):
            return DI.run(self.db, ENTRY, cfg)

    def detail(self, slug):
        with closing(self.connect()) as conn:
            return DI.image_details.detail(conn, self.sha[slug])

    def test_stage_2_runs_after_stage_1_with_the_cut(self):
        cuts = {slug: self.add_cut(slug, "package", color)
                for slug, color in (("wine-a", "white"), ("wine-b", "silver"))}
        fake = RouteVlm(body(DETAIL))
        self.assertEqual(self.run_once(fake), 4)
        kinds = ["class" if p["messages"][0]["content"][1]["text"].startswith("Classify")
                 else "detail" for p in fake.payloads]
        self.assertEqual(kinds, ["class", "class", "detail", "detail"])
        self.assertEqual([s["stage"] for s in fake.states], ["class", "class", "detail",
                                                              "detail"])
        for payload in fake.details():
            self.assertEqual(payload["max_tokens"], 8192)
            self.assertEqual(payload["messages"][0]["content"][1]["text"],
                             DI.detail_prompt("package", "bottle"))
            self.assertEqual(image_size(payload), (20, 40))
            self.assertEqual(payload["response_format"], {
                "type": "json_schema", "json_schema": {
                    "name": "answer", "strict": True,
                    "schema": DI.detail_schema("package", "bottle")}})
        self.assertEqual(fake.payloads[0]["response_format"], {"type": "json_object"})
        for slug in ("wine-a", "wine-b"):
            row = self.detail(slug)
            self.assertEqual((row["prompt_kind"], row["package_type"], row["input_sha256"],
                              row["answer"], row["vlm_model"]),
                             ("package", "bottle", cuts[slug], DETAIL, "Model-1"))
        self.assertEqual(self.run_once(fake), 0)
        self.assertEqual(len(fake.payloads), 4)
        with closing(self.connect()) as conn:
            status = DESC.watcher_status(conn, self.status_path)
        self.assertEqual((status["details_eligible"], status["details_done"],
                          status["stage"]), (2, 2, None))

    def test_details_off_sends_no_detail(self):
        fake = RouteVlm(body(DETAIL))
        self.assertEqual(self.run_once(fake, CFG), 2)
        self.assertEqual(fake.details(), [])

    def test_a_new_image_waits_for_its_class_first(self):
        self.run_once(RouteVlm(body(DETAIL)), CFG)
        with closing(self.connect()) as conn, conn:
            conn.execute(
                "INSERT INTO wine_catalog (wine_slug, name, producer, category, color, "
                "region, csv_photo_name) VALUES ('wine-c', 'Вино', 'Винодельня', 'Белое', "
                "'Соломенный', 'Крым', 'x.webp')")
            conn.execute("INSERT INTO wine_image (wine_slug, image_type, sha256, source_name, "
                         "match_method) VALUES ('wine-c', 'main', ?, 'x.webp', 'test')",
                         (self.sha["none"],))
        fake = RouteVlm(body(DETAIL))
        self.assertEqual(self.run_once(fake), 4)
        self.assertTrue(fake.payloads[0]["messages"][0]["content"][1]["text"]
                        .startswith("Classify"))
        self.assertEqual(len(fake.details()), 3)

    def test_multiple_packages_get_no_detail(self):
        fake = RouteVlm(body(DETAIL), body(dict(ANSWER, subject_scope="multiple_packages")))
        self.assertEqual(self.run_once(fake), 2)
        self.assertEqual(fake.details(), [])

    def test_a_label_closeup_gets_the_label_prompt_and_the_label_cut(self):
        label = self.add_cut("wine-a", "label", "yellow")
        self.add_cut("wine-a", "package", "white")
        fake = RouteVlm(body(LABEL_DETAIL), body(dict(ANSWER, subject_scope="label_closeup")))
        self.run_once(fake)
        texts = {p["messages"][0]["content"][1]["text"] for p in fake.details()}
        self.assertEqual(texts, {DI.detail_prompt("label", "bottle")})
        row = self.detail("wine-a")
        self.assertEqual((row["prompt_kind"], row["input_sha256"], row["answer"]),
                         ("label", label, LABEL_DETAIL))
        self.assertEqual(self.detail("wine-b")["input_sha256"], self.sha["wine-b"])

    def test_max_tokens_of_the_vlm_entry_goes_into_the_detail_request(self):
        self.add_cut("wine-a", "package", "white")
        fake = RouteVlm(body(DETAIL))
        with mock.patch.object(DI, "post", fake), \
                mock.patch.object(DI, "log", lambda message: None):
            DI.run(self.db, ENTRY._replace(max_tokens=2048), DETAIL_CFG)
        self.assertEqual({p["max_tokens"] for p in fake.details()}, {2048})
        self.assertEqual({p["max_tokens"] for p in fake.payloads} - {2048}, {DI.MAX_TOKENS})

    def test_an_answer_cut_off_by_max_tokens_is_a_counted_failure(self):
        cut = body(DETAIL)
        cut["choices"][0]["finish_reason"] = "length"
        fake = RouteVlm(cut)
        self.assertEqual(self.run_once(fake), 2)
        self.assertEqual(len(fake.details()), 6)
        row = self.detail("wine-a")
        self.assertEqual((row["answer"], row["vlm_attempts"]), (None, 3))
        self.assertIn("max_tokens 8192 cut off the answer", row["vlm_error"])
        self.assertEqual(len(self.cache_files()), 2)

    def test_a_detail_that_fails_the_schema_writes_no_answer(self):
        probe = {("text" if key == "texts" else key): value for key, value in DETAIL.items()}
        self.run_once(RouteVlm(body(probe)))
        row = self.detail("wine-b")
        self.assertEqual((row["answer"], row["vlm_attempts"]), (None, 3))
        self.assertIn("fails the schema", row["vlm_error"])
        self.assertEqual(len(self.cache_files()), 2)

    def test_the_detail_sha_option(self):
        self.run_once(RouteVlm(body(DETAIL)), CFG)
        config = {"rootdir": str(self.root), "database_file": "lab.sqlite3",
                  "vlm": [{"name": "gx10-test", "protocol": "openai",
                           "thinking_field": "chat_template_kwargs",
                           "endpoint": "http://vlm.invalid/v1", "model": "model-1"}],
                  "image_description": {"vlm": "gx10-test"}}
        path = self.root / "config.yaml"
        path.write_text(yaml.safe_dump(config), encoding="utf-8")
        args = ["--config", str(path), "--detail-sha"]
        fake = RouteVlm(body(DETAIL))
        with mock.patch.object(DI, "post", fake), \
                mock.patch.object(DI, "log", lambda message: None), \
                mock.patch.object(DI, "LOCK_PATH", str(self.root / "describe.lock")):
            self.assertEqual(DI.main(args + [self.sha["wine-a"]]), 0)
            self.assertEqual(DI.main(args + [self.sha["wine-a"]]), 1)
            with mock.patch("sys.stderr"):
                self.assertEqual(DI.main(args + [self.sha["none"]]), 1)
        self.assertEqual(len(fake.details()), 1)
        self.assertEqual(self.detail("wine-a")["answer"], DETAIL)
        self.assertIsNone(self.detail("wine-b"))


# The owner answers of 2026-09-25T23:58:53+0300: up to `workers` calls at the same time.
class WorkersSettingsTest(unittest.TestCase):
    def test_the_workers_key(self):
        self.assertEqual(DI.settings({})["workers"], 1)
        self.assertEqual(DI.settings({"image_description": {"workers": 8}})["workers"], 8)
        for value in (0, -1, "8", True, 2.5, None):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    DI.settings({"image_description": {"workers": value}})

    def test_the_project_configuration_sends_8_requests_at_once(self):
        config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
        self.assertEqual(DI.settings(config)["workers"], 8)


class CountingVlm(FakeVlm):
    """Counts the calls that run at the same time, in all and for each image."""

    def __init__(self, *bodies, pause=0.05):
        super().__init__(*bodies)
        self.pause, self.lock = pause, threading.Lock()
        self.now, self.most, self.most_of_one = collections.Counter(), 0, 0

    def __call__(self, entry, payload, timeout=None):
        image = payload["messages"][0]["content"][0]["image_url"]["url"]
        with self.lock:
            self.now[image] += 1
            self.most = max(self.most, sum(self.now.values()))
            self.most_of_one = max(self.most_of_one, self.now[image])
        try:
            time.sleep(self.pause)
            return super().__call__(entry, payload, timeout)
        finally:
            with self.lock:
                self.now[image] -= 1


class WorkersTest(DescriptionCase):
    def run_with(self, post, workers, watch=False):
        with mock.patch.object(DI, "post", post), \
                mock.patch.object(DI, "log", lambda message: None):
            return DI.run(self.db, ENTRY, dict(CFG, workers=workers), watch=watch)

    def row(self, slug):
        with closing(self.connect()) as conn:
            return DESC.description(conn, self.sha[slug])

    def test_the_calls_run_at_the_same_time(self):
        barrier = threading.Barrier(2, timeout=10)
        fake = FakeVlm(body(), during=barrier.wait)
        self.assertEqual(self.run_with(fake, 2), 2)
        self.assertEqual(len(fake.payloads), 2)
        for slug in ("wine-a", "wine-b"):
            self.assertIsNotNone(self.row(slug)["vlm_at"])

    def test_an_image_is_in_one_call_at_a_time(self):
        with closing(self.connect()) as conn, conn:
            conn.execute(
                "INSERT INTO wine_catalog (wine_slug, name, producer, category, color, "
                "region, csv_photo_name) VALUES ('wine-c', 'Вино', 'Винодельня', 'Белое', "
                "'Соломенный', 'Крым', 'x.webp')")
            conn.execute("INSERT INTO wine_image (wine_slug, image_type, sha256, source_name, "
                         "match_method) VALUES ('wine-c', 'main', ?, 'x.webp', 'test')",
                         (self.sha["none"],))
        fake = CountingVlm(body(text=json.dumps(dict(ANSWER, package_view="side"))))
        self.assertEqual(self.run_with(fake, 2), 0)
        self.assertEqual(len(fake.payloads), 9)
        self.assertEqual(fake.most_of_one, 1)
        self.assertLessEqual(fake.most, 2)
        for slug in ("wine-a", "wine-b", "none"):
            self.assertEqual(self.row(slug)["vlm_attempts"], 3)

    def test_the_calls_that_run_end_before_a_failure_is_raised(self):
        barrier = threading.Barrier(2, timeout=10)

        def post(entry, payload, timeout=None):
            if barrier.wait() == 0:
                raise DI.DescribeError("HTTP 503: busy", counted=False)
            time.sleep(0.2)
            return body()
        with self.assertRaises(DI.DescribeError):
            self.run_with(post, 2)
        rows = [self.row(slug) for slug in ("wine-a", "wine-b")]
        self.assertEqual(sorted(row["vlm_at"] is not None for row in rows), [False, True])
        failed = next(row for row in rows if row["vlm_at"] is None)
        self.assertEqual((failed["vlm_attempts"], failed["vlm_error"]), (0, "HTTP 503: busy"))

    def test_one_backoff_for_the_calls_that_fail_together(self):
        barrier = threading.Barrier(2, timeout=10)

        def post(entry, payload, timeout=None):
            barrier.wait()
            raise DI.DescribeError("HTTP 503: busy", counted=False)
        sleeps = []

        def sleep(seconds, parent_pid):
            sleeps.append((seconds, DESC.read_status()["state"]))
            return False
        with mock.patch.object(DI, "sleep", sleep):
            self.run_with(post, 2, watch=True)
        self.assertEqual(len(sleeps), 1)
        seconds, state = sleeps[0]
        self.assertEqual(state, "waiting")
        self.assertGreater(seconds, DI.BACKOFF_SECONDS - 5)
        self.assertLessEqual(seconds, DI.BACKOFF_SECONDS)

    def test_the_speed_is_the_wall_time_per_image(self):
        status = DI.Status(ENTRY, CFG)
        status.step(self.sha["wine-a"], True, 20.0, 5.0)
        status.step(self.sha["wine-b"], True, 22.0, 3.0)
        status.set("working")
        state = DESC.read_status()
        self.assertEqual(state["seconds_per_image"], 4.0)
        self.assertEqual((state["last"]["sha256"], state["last"]["seconds"]),
                         (self.sha["wine-b"], 22.0))

    def test_two_workers_give_about_half_the_time_of_a_call(self):
        barrier = threading.Barrier(2, timeout=10)

        def during():
            barrier.wait()
            time.sleep(0.3)
        self.run_with(FakeVlm(body(), during=during), 2)
        state = DESC.read_status()
        self.assertEqual(state["state"], "stopped")
        self.assertLess(state["seconds_per_image"], 0.75 * state["last"]["seconds"])


class PostTimeoutTest(unittest.TestCase):
    """Plan 49: `post` marks a read timeout, and only a read timeout."""

    def post_raising(self, exc):
        with mock.patch.object(DI.urllib.request, "urlopen", side_effect=exc):
            with self.assertRaises(DI.DescribeError) as caught:
                DI.post(ENTRY, {"model": "model-1"})
        return caught.exception

    def test_a_read_timeout_is_marked_and_names_the_full_endpoint(self):
        exc = self.post_raising(TimeoutError("timed out"))
        self.assertEqual((exc.timed_out, exc.counted), (True, False))
        self.assertEqual(str(exc), "no answer from http://vlm.invalid/v1/chat/completions "
                                   "in 300 s: timed out")

    def test_a_connect_timeout_is_not_a_read_timeout(self):
        exc = self.post_raising(DI.urllib.error.URLError(TimeoutError("timed out")))
        self.assertEqual((exc.timed_out, exc.counted), (False, False))

    def test_the_probe_sends_1_token_with_no_image(self):
        seen = []

        def post(entry, payload, timeout=None):
            seen.append((payload, timeout))
            return {"choices": [{"message": {"content": ""}}]}
        with mock.patch.object(DI, "post", post):
            self.assertGreaterEqual(DI.probe(ENTRY), 0)
        payload, timeout = seen[0]
        self.assertEqual(timeout, DI.PROBE_TIMEOUT_SECONDS)
        self.assertEqual(payload, {
            "model": "model-1", "temperature": 0, "max_tokens": 1,
            "messages": [{"role": "user", "content": "ping"}],
            "chat_template_kwargs": {"enable_thinking": False}})


class TimeoutProbeTest(DescriptionCase):
    """Plan 49: a timeout counts against the image when the probe answers."""

    TIMEOUT = DI.DescribeError("no answer from http://vlm.invalid/v1/chat/completions in "
                               "300 s: timed out", counted=False, timed_out=True)

    def run_with(self, probe, watch=False, sleep=None):
        with mock.patch.object(DI, "post", FakeVlm(self.TIMEOUT)), \
                mock.patch.object(DI, "probe", probe), \
                mock.patch.object(DI, "log", lambda message: None), \
                mock.patch.object(DI, "sleep", sleep or DI.sleep):
            return DI.run(self.db, ENTRY, CFG, watch=watch)

    def row(self, slug):
        with closing(self.connect()) as conn:
            return DESC.description(conn, self.sha[slug])

    def test_a_timeout_with_a_live_model_counts_and_starts_no_backoff(self):
        self.assertEqual(self.run_with(lambda entry: 0.4), 0)
        for slug in ("wine-a", "wine-b"):
            row = self.row(slug)
            self.assertEqual(row["vlm_attempts"], CFG["max_attempts"])
            self.assertTrue(row["vlm_error"].endswith(
                "timed out; a probe of the model answered in 0.4 s, so the failure counts "
                "against the image"))

    def test_a_timeout_with_a_dead_model_is_a_failure_of_the_service(self):
        def probe(entry):
            raise DI.DescribeError("no answer from http://vlm.invalid/v1/chat/completions: "
                                   "connection refused", counted=False)
        with self.assertRaises(DI.DescribeError) as caught:
            self.run_with(probe)
        self.assertFalse(caught.exception.counted)
        row = self.row("wine-b")
        self.assertEqual(row["vlm_attempts"], 0)
        self.assertIn("timed out; the probe of the model failed too: no answer from "
                      "http://vlm.invalid/v1/chat/completions: connection refused",
                      row["vlm_error"])

    def test_the_state_waiting_names_the_image_and_the_next_try(self):
        def probe(entry):
            raise DI.DescribeError("HTTP 503: busy", counted=False)
        states = []
        self.run_with(probe, watch=True,
                      sleep=lambda seconds, pid: states.append(DESC.read_status()) and False)
        state = states[0]
        self.assertEqual(state["state"], "waiting")
        self.assertEqual((state["error_sha256"], state["error_stage"]),
                         (self.sha["wine-b"], "class"))
        self.assertEqual(state["backoff_seconds"], DI.BACKOFF_SECONDS)
        self.assertEqual(state["running"], [])
        self.assertLessEqual(state["waiting_since"], state["retry_at"])
        self.assertEqual((state["endpoint"], state["timeout_seconds"], state["workers"]),
                         ("http://vlm.invalid/v1/chat/completions", 300, 1))

    def test_the_state_lists_the_calls_that_run(self):
        seen = []
        fake = FakeVlm(body(), during=lambda: seen.append(DESC.read_status()))
        with mock.patch.object(DI, "post", fake), \
                mock.patch.object(DI, "log", lambda message: None):
            DI.run(self.db, ENTRY, CFG)
        self.assertEqual([[c["sha256"] for c in s["running"]] for s in seen],
                         [[self.sha["wine-b"]], [self.sha["wine-a"]]])
        self.assertEqual(seen[0]["running"][0]["stage"], "class")
        self.assertRegex(seen[0]["running"][0]["started_at"], r"^\d{4}-\d\d-\d\dT.*Z$")
        self.assertEqual(DESC.read_status()["running"], [])



# Plan 61: stage 3, the label descriptions with the request of stage 1 of the cluster rules.
LABEL = {"texts": [{"text": "ФАНТОМ", "where": "left side"}],
         "numbers": [{"value": "2018", "where": "left side"}], "vintage": 2018,
         "colours": ["black", "white"], "design": "black and white wavy lines",
         "marks": [], "bottle": {"colour": "dark blue", "capsule": "black"}}
LABEL_ENTRY = vlm_config.entry({"vlm": [{
    "name": "label-test", "protocol": "openai", "thinking_field": "chat_template_kwargs",
    "endpoint": "http://label.invalid/v1", "model": "label-model"}]}, "label-test")
LABEL_SETTINGS = {"entry": LABEL_ENTRY, "thinking": False, "describe_side": 64,
                  "describe_max_tokens": 1500, "timeout_s": 300, "describe_sha": "test-sha"}
LABEL_CFG = dict(CFG, labels=True, label=LABEL_SETTINGS)


def label_body(answer=LABEL, text=None, finish="stop"):
    return {"model": "Label-Model", "usage": {"prompt_tokens": 90, "completion_tokens": 40},
            "choices": [{"message": {"content": text if text is not None else json.dumps(
                answer, ensure_ascii=False)}, "finish_reason": finish}]}


def is_label(payload):
    return payload["messages"][0]["content"][1]["text"] == label_rules.DESCRIBE_PROMPT


class LabelVlm(FakeVlm):
    """Answers a class prompt with `body()` and a label prompt with the next of
    `bodies`. `payloads` keeps the label requests alone; `stages` keeps the stage of each
    call, and `calls` the entry name and the timeout of each label request."""

    def __init__(self, *bodies, during=None):
        super().__init__(*bodies, during=during)
        self.stages, self.calls = [], []

    def __call__(self, entry, payload, timeout=None):
        if not is_label(payload):
            self.stages.append("class")
            return body()
        self.stages.append("label")
        self.calls.append((entry.name, timeout))
        return super().__call__(entry, payload, timeout)


class LabelPayloadTest(unittest.TestCase):
    def test_the_request_is_the_request_of_the_cluster_rules(self):
        with tempfile.TemporaryDirectory() as directory:
            path = "%s/cut.png" % directory
            Image.new("RGBA", (20, 40), (200, 0, 0, 255)).save(path)
            picture = {"kind": "package", "sha256": "c" * 64, "source_sha256": "a" * 64,
                       "path": path}
            sent = []

            def cluster_post(entry, payload, timeout):
                sent.append(payload)
                return label_body()
            with mock.patch.object(model_cache, "ROOT", "%s/cache-1" % directory), \
                    mock.patch.object(label_rules, "post", cluster_post):
                rec = label_rules.describe(label_rules.ask, LABEL_SETTINGS, picture)
            fake = FakeVlm(label_body())
            with mock.patch.object(model_cache, "ROOT", "%s/cache-2" % directory), \
                    mock.patch.object(DI, "post", fake):
                description, renames, vlm = DI.describe_label(LABEL_SETTINGS, path)
                cache_key = model_cache.key_of(model_cache.vlm_fields(
                    LABEL_ENTRY.url, fake.payloads[0]))
        self.assertEqual(fake.payloads, sent)
        payload = sent[0]
        self.assertEqual((payload["model"], payload["temperature"], payload["max_tokens"],
                          payload["response_format"], payload["chat_template_kwargs"]),
                         ("label-model", 0, 1500, {"type": "json_object"},
                          {"enable_thinking": False}))
        self.assertEqual(image_size(payload), (32, 64))
        self.assertEqual((rec["description"], description, renames), (LABEL, LABEL, []))
        self.assertEqual({key: vlm[key] for key in (
            "vlm_name", "vlm_endpoint", "vlm_model", "vlm_served_model", "max_tokens",
            "thinking")}, {"vlm_name": "label-test",
                           "vlm_endpoint": "http://label.invalid/v1/chat/completions",
                           "vlm_model": "label-model", "vlm_served_model": "Label-Model",
                           "max_tokens": 1500, "thinking": False})
        self.assertEqual(vlm["vlm_request"], {
            "prompt": "label_rules.DESCRIBE_PROMPT",
            "prompt_sha256": hashlib.sha256(label_rules.DESCRIBE_PROMPT.encode()).hexdigest(),
            "describe_side": 64, "sent_size": [32, 64], "image_format": "png",
            "temperature": 0, "response_format": {"type": "json_object"}, "timeout_s": 300,
            "settings_sha": "test-sha", "cache_key": cache_key})
        self.assertEqual(vlm["vlm_reply"], {
            "finish_reason": "stop", "usage": {"prompt_tokens": 90, "completion_tokens": 40},
            "ms": vlm["vlm_reply"]["ms"], "cached": False, "loop_guard": False,
            "repairs": [], "raw": json.dumps(LABEL, ensure_ascii=False)})

    def test_the_check_of_an_answer(self):
        self.assertEqual(DI.label_answer("Here: %s." % json.dumps(LABEL)), (LABEL, []))
        drift = {("text" if key == "texts" else key): value for key, value in LABEL.items()}
        self.assertEqual(DI.label_answer(json.dumps(drift)), (LABEL, [["text", "texts"]]))
        loose = dict(LABEL, texts=["ФАНТОМ", {"text": "2018"}], numbers=[2018, "14.7%"],
                     colours="black", vintage=None, bottle=None, marks=["a medal", {"x": 1}])
        self.assertEqual(DI.label_answer(json.dumps(loose))[0], loose)
        bad = [dict(LABEL, where="left"), {k: v for k, v in LABEL.items() if k != "bottle"},
               dict(LABEL, texts=[{"where": "left"}]), dict(LABEL, design=["a"]),
               dict(LABEL, vintage=20.18), dict(LABEL, texts="ФАНТОМ")]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(DI.DescribeError) as caught:
                DI.label_answer(json.dumps(value, ensure_ascii=False))
            self.assertIn("schema", str(caught.exception))
        with self.assertRaises(DI.DescribeError):
            DI.label_answer("no JSON here")


class LabelSettingsTest(unittest.TestCase):
    def test_the_labels_key(self):
        self.assertFalse(DI.settings({})["labels"])
        self.assertTrue(DI.settings({"image_description": {"labels": True}})["labels"])
        with self.assertRaises(ValueError):
            DI.settings({"image_description": {"labels": "yes"}})

    def test_the_project_configuration_turns_stage_3_on(self):
        path = ROOT / "config.yaml"
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.assertTrue(DI.settings(config)["labels"])
        label = DI.label_settings(str(path))
        self.assertEqual((label["entry"].name, label["describe_side"],
                          label["describe_max_tokens"], label["thinking"], label["timeout_s"]),
                         ("qwen3.5-9b-nvfp4", 2048, 1500, False, 300))

    def test_a_bad_block_label_rules_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = "%s/config.yaml" % directory
            with open(path, "w", encoding="utf-8") as fh:
                yaml.safe_dump({"database_file": "lab.sqlite3", "label_rules": {"size": 1}}, fh)
            with self.assertRaises(ValueError) as caught:
                DI.label_settings(path)
        self.assertIn("unknown key: size", str(caught.exception))


class LabelWatcherTest(DescriptionCase):
    def run_once(self, fake, cfg=LABEL_CFG):
        with mock.patch.object(DI, "post", fake), \
                mock.patch.object(DI, "log", lambda message: None):
            return DI.run(self.db, ENTRY, cfg)

    def rows(self, slug):
        with closing(self.connect()) as conn:
            return LD.rows(conn, self.sha[slug])

    def failure(self, slug):
        with closing(self.connect()) as conn:
            return LD.failure(conn, self.sha[slug])

    def payload_of(self, slug, max_tokens=1500, extra=None):
        """The label request of the original of `slug`, as stage 3 sends it."""
        png, _ = label_rules.picture_png(str(self.root / "images" / "main" / (
            "%s.png" % self.sha[slug])), 64)
        content = [{"type": "image_url", "image_url": {"url": label_rules.data_url(png)}},
                   {"type": "text", "text": label_rules.DESCRIBE_PROMPT}]
        return DI.label_payload(LABEL_ENTRY, content, max_tokens, False, extra)

    def label_records(self):
        """The records of `data/cache/` of the label requests: the prompt of the request
        is `DESCRIBE_PROMPT`."""
        records = [json.loads(path.read_text(encoding="utf-8")) for path in self.cache_files()]
        return [record for record in records
                if record["request"]["prompt"][0]["content"][1]["text"]
                == label_rules.DESCRIBE_PROMPT]

    def test_stage_3_runs_after_stage_1_and_keeps_the_settings(self):
        fake = LabelVlm(label_body())
        self.assertEqual(self.run_once(fake), 4)
        self.assertEqual(fake.stages, ["class", "class", "label", "label"])
        self.assertEqual(fake.calls, [("label-test", 300)] * 2)
        for slug in ("wine-b", "wine-a"):
            rows = self.rows(slug)
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual((row["created_by"], row["description"], row["vlm_name"],
                              row["vlm_served_model"], row["max_tokens"], row["thinking"],
                              row["input_sha256"]),
                             ("vlm", LABEL, "label-test", "Label-Model", 1500, False,
                              self.sha[slug]))
            self.assertEqual(row["vlm_request"]["input_kind"], "original")
            self.assertEqual(row["vlm_request"]["cache_key"], model_cache.key_of(
                model_cache.vlm_fields(LABEL_ENTRY.url, self.payload_of(slug))))
            self.assertRegex(row["created_at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertEqual(len(self.label_records()), 2)
        self.assertEqual(self.run_once(fake), 0)
        self.assertEqual(len(fake.payloads), 2)

    def test_labels_off_sends_no_label_request(self):
        fake = LabelVlm(label_body())
        self.assertEqual(self.run_once(fake, dict(LABEL_CFG, labels=False)), 2)
        self.assertEqual(fake.payloads, [])
        self.assertEqual(self.rows("wine-a"), [])

    def test_an_image_waits_for_its_class_before_its_label_call(self):
        found = DI.next_items(self.db, LABEL_CFG, 4, set())
        self.assertEqual([(stage, item[0]) for stage, item in found],
                         [("class", self.sha["wine-b"]), ("class", self.sha["wine-a"])])
        self.run_once(LabelVlm(label_body()), CFG)
        found = DI.next_items(self.db, LABEL_CFG, 4, {self.sha["wine-b"]})
        self.assertEqual([(stage, item[0]) for stage, item in found],
                         [("label", self.sha["wine-a"])])

    def test_the_package_cut_goes_to_the_vlm(self):
        cut = self.add_cut("wine-a", "package")
        self.run_once(LabelVlm(label_body()))
        row = self.rows("wine-a")[0]
        self.assertEqual((row["input_sha256"], row["vlm_request"]["input_kind"]),
                         (cut, "package"))
        self.assertEqual(self.rows("wine-b")[0]["vlm_request"]["input_kind"], "original")

    def test_a_drifted_answer_is_repaired(self):
        drift = {("text" if key == "texts" else "number" if key == "numbers" else key): value
                 for key, value in LABEL.items()}
        self.run_once(LabelVlm(label_body(drift)))
        row = self.rows("wine-a")[0]
        self.assertEqual(row["description"], LABEL)
        self.assertEqual(list(row["description"]), list(LABEL))
        self.assertEqual(row["vlm_reply"]["repairs"], [["text", "texts"], ["number", "numbers"]])
        self.assertEqual(json.loads(row["vlm_reply"]["raw"]), drift)

    def test_an_answer_that_fails_the_check_writes_nothing(self):
        fake = LabelVlm(label_body(dict(LABEL, where="left")))
        for _ in range(3):
            self.run_once(fake)
        self.assertEqual(self.rows("wine-a"), [])
        failure = self.failure("wine-a")
        self.assertEqual(failure["attempts"], 3)
        self.assertIn("fails the schema", failure["error"])
        self.assertEqual(self.label_records(), [])
        self.run_once(fake)
        self.assertEqual(len(fake.payloads), 6)
        with closing(self.connect()) as conn:
            status = DESC.watcher_status(conn, self.status_path)
        self.assertEqual((status["labels_failed"], status["labels_pending"]), (2, 0))

    def test_a_cached_answer_that_fails_the_check_is_sent_again(self):
        fields = model_cache.vlm_fields(LABEL_ENTRY.url, self.payload_of("wine-a"))
        model_cache.store(fields, label_body(text='{"a": 1}'), 5)
        fake = LabelVlm(label_body())
        self.run_once(fake)
        self.assertEqual(len(fake.payloads), 2)
        self.assertEqual(self.rows("wine-a")[0]["description"], LABEL)
        self.assertFalse(self.rows("wine-a")[0]["vlm_reply"]["cached"])
        record = model_cache.lookup(fields)
        self.assertEqual(json.loads(record["answer"]["choices"][0]["message"]["content"]), LABEL)

    def test_a_valid_cached_answer_is_read_back(self):
        fields = model_cache.vlm_fields(LABEL_ENTRY.url, self.payload_of("wine-a"))
        model_cache.store(fields, label_body(), 15000)
        fake = LabelVlm(label_body())
        self.run_once(fake)
        self.assertEqual(len(fake.payloads), 1)
        reply = self.rows("wine-a")[0]["vlm_reply"]
        self.assertEqual((reply["cached"], reply["ms"]), (True, 15000))

    def test_the_loop_guard(self):
        fake = LabelVlm(label_body(text='{"texts": [', finish="length"), label_body())
        self.run_once(fake, dict(LABEL_CFG, max_attempts=1))
        first, second = fake.payloads[:2]
        self.assertEqual((first["max_tokens"], "repetition_penalty" in first), (1500, False))
        self.assertEqual((second["max_tokens"], second["repetition_penalty"]),
                         (3000, label_rules.REPETITION_PENALTY))
        row = self.rows("wine-b")[0]
        self.assertEqual((row["max_tokens"], row["vlm_request"]["repetition_penalty"],
                          row["vlm_reply"]["loop_guard"]),
                         (3000, label_rules.REPETITION_PENALTY, True))
        self.assertEqual(self.rows("wine-a")[0]["vlm_reply"]["loop_guard"], False)
        self.assertEqual(len(self.label_records()), 2)

    def test_two_cut_off_answers_are_a_counted_failure(self):
        fake = LabelVlm(label_body(text='{"texts": [', finish="length"))
        self.run_once(fake, dict(LABEL_CFG, max_attempts=1))
        self.assertEqual(len(fake.payloads), 4)
        self.assertEqual(self.rows("wine-a"), [])
        failure = self.failure("wine-a")
        self.assertEqual(failure["attempts"], 1)
        self.assertIn("cut off", failure["error"])

    def test_a_manual_row_saved_during_the_call_stays_the_latest(self):
        def save():
            with closing(self.connect()) as conn, conn:
                for slug in ("wine-a", "wine-b"):
                    LD.add_manual(conn, self.sha[slug], {"design": "the owner"})
        fake = LabelVlm(label_body(), during=save)
        self.assertEqual(self.run_once(fake), 2)
        self.assertEqual(len(fake.payloads), 1)
        for slug in ("wine-a", "wine-b"):
            self.assertEqual([row["created_by"] for row in self.rows(slug)], ["manual"])

    def test_a_failure_of_the_service_is_not_counted(self):
        fake = LabelVlm(DI.DescribeError("HTTP 503: busy", counted=False))
        with self.assertRaises(DI.DescribeError):
            self.run_once(fake)
        failure = self.failure("wine-b")
        self.assertEqual((failure["attempts"], failure["error"]), (0, "HTTP 503: busy"))

    def test_the_state_and_the_counts_of_stage_3(self):
        seen = []
        fake = LabelVlm(label_body(), during=lambda: seen.append(DESC.read_status()))
        self.run_once(fake)
        self.assertEqual((seen[0]["stage"], seen[0]["running"][0]["stage"],
                          seen[0]["labels_vlm"]), ("label", "label", "label-test"))
        with closing(self.connect()) as conn:
            status = DESC.watcher_status(conn, self.status_path)
            view = DESC.call_view(conn, self.sha["wine-a"], "label")
        self.assertEqual({key: status[key] for key in (
            "labels_linked", "labels_done", "labels_failed", "labels_pending")},
            {"labels_linked": 2, "labels_done": 2, "labels_failed": 0, "labels_pending": 0})
        self.assertEqual((view["url"], view["input_kind"], view["attempts"], view["slug"]),
                         ("/images/main/%s.png" % self.sha["wine-a"], "original", 0, "wine-a"))

    def test_the_label_sha_option(self):
        config = {"rootdir": str(self.root), "database_file": "lab.sqlite3",
                  "vlm": [{"name": "gx10-test", "protocol": "openai",
                           "thinking_field": "chat_template_kwargs",
                           "endpoint": "http://vlm.invalid/v1", "model": "model-1"},
                          {"name": "label-test", "protocol": "openai",
                           "thinking_field": "chat_template_kwargs",
                           "endpoint": "http://label.invalid/v1", "model": "label-model"}],
                  "image_description": {"vlm": "gx10-test"},
                  "label_rules": {"vlm": "label-test", "describe_side": 64}}
        path = self.root / "config.yaml"
        path.write_text(yaml.safe_dump(config), encoding="utf-8")
        args = ["--config", str(path), "--label-sha"]
        fake = LabelVlm(label_body())
        with mock.patch.object(DI, "post", fake), \
                mock.patch.object(DI, "log", lambda message: None), \
                mock.patch.object(DI, "LOCK_PATH", str(self.root / "describe.lock")):
            self.assertEqual(DI.main(args + [self.sha["wine-a"]]), 0)
            self.assertEqual(DI.main(args + [self.sha["wine-a"]]), 1)
            with mock.patch("sys.stderr"):
                self.assertEqual(DI.main(args + [self.sha["none"]]), 1)
        self.assertEqual(len(fake.payloads), 1)
        self.assertEqual(fake.calls, [("label-test", 300)])
        self.assertEqual(self.rows("wine-a")[0]["vlm_name"], "label-test")
        self.assertEqual(self.rows("wine-b"), [])


if __name__ == "__main__":
    unittest.main()
