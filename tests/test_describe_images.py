import base64
import collections
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


if __name__ == "__main__":
    unittest.main()
