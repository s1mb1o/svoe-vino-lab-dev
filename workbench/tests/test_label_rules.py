"""Unit tests of `pipeline/label_rules.py`: the prompts, the check, the VLM calls, the
pictures, and the configuration (plan 45). No test calls gx10."""
import ast
import io
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml
from PIL import Image

import embedding_lab  # noqa: F401  (puts pipeline/ on sys.path)

import embeddings  # noqa: E402
import label_rules  # noqa: E402
import model_cache  # noqa: E402
import vlm_config  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ("DESCRIBE_PROMPT", "RULES_PROMPT", "CARD_BLOCK", "CAPTION", "CAPTION_NO_LABEL",
           "CAPTION_SHARED", "VINTAGE_NOTE")
A, B, C = "wine-a-12", "wine-b-12", "wine-c-12"
LETTERS = {"A": A, "B": B, "C": C}


def constants(path):
    """The string constants of a module, read without an import."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(
                node.targets[0], ast.Name) and isinstance(node.value, ast.Constant):
            out[node.targets[0].id] = node.value.value
    return out


class PromptTest(unittest.TestCase):
    def test_the_prompts_equal_the_prompts_of_the_testset_port(self):
        # `scripts/cluster_rules.py` holds the prompts of `svoe-vino-testset`.
        old = constants(ROOT / "scripts" / "cluster_rules.py")
        for name in PROMPTS:
            self.assertEqual(getattr(label_rules, name), old[name], name)


def rule(questions, text="", groups=()):
    return {"differences": "d", "questions": questions, "rule": text,
            "indistinguishable": list(groups)}


class CheckTest(unittest.TestCase):
    def test_a_feature_question_gives_the_mode_sheet_and_evidence(self):
        out = label_rules.check_rule(rule([
            {"question": "What ratio is printed on the label?",
             "answers": {"A": "30/70", "B": "50 / 50", "C": None}}]), LETTERS,
            sent={A: "sha-a", B: "sha-b", C: "sha-c"})
        self.assertEqual(out["mode"], "sheet")
        q = out["questions"][0]
        self.assertTrue(q["valid"])
        self.assertEqual(q["kind"], "feature")
        self.assertEqual(q["answers"], {A: "30/70", B: "50 / 50", C: None})
        self.assertEqual(q["evidence"], {A: ["sha-a"], B: ["sha-b"]})

    def test_a_bottle_number_and_a_feature_outside_the_label_are_never_valid(self):
        out = label_rules.check_rule(rule([
            {"question": "What is the bottle number (Бут. №)?", "answers": {"A": "1", "B": "2"}},
            {"question": "What colour is the capsule?", "answers": {"A": "red", "B": "gold"}},
        ], text="The glass of card A is green."), LETTERS)
        self.assertEqual([q["kind"] for q in out["questions"]], ["serial", "bottle"])
        self.assertFalse(any(q["valid"] for q in out["questions"]))
        # A rule text about the glass gives no verdict.
        self.assertEqual(out["mode"], "none")

    def test_the_alcohol_value_counts_only_when_nothing_else_differs(self):
        alcohol = {"question": "What alcohol value is printed?",
                   "answers": {"A": "14.4%", "B": "14.5%"}}
        name = {"question": "What name is printed?", "answers": {"A": "ФАНТОМ", "B": "ЛЕТО"}}
        both = label_rules.check_rule(rule([alcohol, name]), LETTERS)
        self.assertEqual([q["valid"] for q in both["questions"]], [False, True])
        alone = label_rules.check_rule(rule([alcohol]), LETTERS)
        self.assertTrue(alone["questions"][0]["valid"])

    def test_a_rule_text_alone_gives_the_mode_verdict(self):
        out = label_rules.check_rule(rule([], text="If the label shows 30/70, it is card A."),
                                     LETTERS, catalog={}, cards={})
        self.assertEqual(out["mode"], "verdict")

    def test_a_year_counts_only_when_the_catalogue_name_states_it(self):
        question = {"question": "What vintage year is printed?",
                    "answers": {"A": "2021", "B": "2022"}}
        pictures_only = label_rules.check_rule(rule([question]), LETTERS, catalog={})
        self.assertFalse(pictures_only["questions"][0]["valid"])
        named = label_rules.check_rule(rule([question]), LETTERS, catalog={
            A: {"name": "Wine 2021"}, B: {"name": "Wine 2022"}})
        self.assertTrue(named["questions"][0]["valid"])

    def test_the_card_with_no_year_keeps_other_as_a_vintage_variant(self):
        catalog = {A: {"name": "Wine 2020"}, B: {"name": "Wine"}}
        cards = {A: {"description": {"vintage": 2020}}, B: {"description": {"vintage": None}}}
        out = label_rules.check_rule(rule([
            {"question": "What vintage year is printed?", "answers": {"A": "2020", "B": "other"}},
        ]), {"A": A, "B": B}, catalog, cards)
        q = out["questions"][0]
        self.assertTrue(q["valid"])
        self.assertEqual(q["answers"], {A: "2020", B: "other"})

    def test_a_mark_of_one_card_gets_yes_and_no(self):
        out = label_rules.check_rule(rule([
            {"question": "Does the label show a kosher mark?", "answers": {"A": "yes", "B": "no"}},
        ]), {"A": A, "B": B})
        self.assertTrue(out["questions"][0]["valid"])

    def test_the_indistinguishable_groups_become_slugs(self):
        out = label_rules.check_rule(rule([], groups=[["A", "C"], ["B"]]), LETTERS)
        self.assertEqual(out["indistinguishable"], [[A, C]])

    def test_normalize(self):
        self.assertEqual(label_rules.normalize(" «30 / 70». "), "30/70")
        self.assertEqual(label_rules.normalize("Ёлка"), "елка")
        self.assertIsNone(label_rules.normalize("Not visible"))

    def test_the_alcohol_of_the_slug(self):
        self.assertEqual(label_rules.alcohol_of("wine-145"), "14.5 %")
        self.assertEqual(label_rules.alcohol_of("wine-12"), "12 %")
        self.assertIsNone(label_rules.alcohol_of("wine"))


class Service:
    """A local chat route that answers each request with the next of `answers`: a pair
    of an HTTP status and a body."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.requests = []
        service = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                pass

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                service.requests.append(json.loads(self.rfile.read(length)))
                status, body = service.answers.pop(0)
                data = json.dumps(body).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.entry = vlm_config.Entry(
            "test-vlm", "openai", "chat_template_kwargs",
            "http://127.0.0.1:%d/v1" % self.server.server_port, "test-model", "")

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def chat_body(text, finish="stop"):
    return {"model": "test-model", "usage": {"completion_tokens": 3},
            "choices": [{"message": {"content": text}, "finish_reason": finish}]}


def content(images):
    parts = [{"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBORw0KGgo="}}
             for _ in range(images)]
    return parts + [{"type": "text", "text": "Answer with one JSON object."}]


class VlmTest(unittest.TestCase):
    def setUp(self):
        self.cache = tempfile.TemporaryDirectory()
        self.old_root, model_cache.ROOT = model_cache.ROOT, self.cache.name

    def tearDown(self):
        model_cache.ROOT = self.old_root
        self.cache.cleanup()

    def test_the_image_limit_of_the_service_gives_a_meaningful_error(self):
        service = Service([(400, {"error": {
            "message": "At most 1 image(s) may be provided in one prompt. (parameter=image)",
            "type": "BadRequestError", "param": "image", "code": 400}})])
        try:
            with self.assertRaises(label_rules.ImageLimitError) as caught:
                label_rules.ask(service.entry, content(3), 100, False, 10)
        finally:
            service.close()
        message = str(caught.exception)
        for part in ("test-vlm", "at most 1 image(s)", "(3 here)", "--limit-mm-per-prompt",
                     "label_rules.rules_max_images"):
            self.assertIn(part, message)
        self.assertEqual(len(service.requests), 1)

    def test_another_client_error_is_not_sent_again(self):
        service = Service([(400, {"error": {"message": "bad request"}})])
        try:
            with self.assertRaises(label_rules.VlmError) as caught:
                label_rules.ask(service.entry, content(1), 100, False, 10)
        finally:
            service.close()
        self.assertNotIsInstance(caught.exception, label_rules.ImageLimitError)
        self.assertIn("HTTP 400", str(caught.exception))
        self.assertEqual(len(service.requests), 1)

    def test_the_cache_keeps_only_a_complete_json_answer(self):
        service = Service([(200, chat_body('{"a": 1', finish="length")),
                           (200, chat_body('{"a": 1}')), (200, chat_body('{"a": 2}'))])
        try:
            cut = label_rules.ask(service.entry, content(1), 100, False, 10)
            first = label_rules.ask(service.entry, content(1), 100, False, 10)
            second = label_rules.ask(service.entry, content(1), 100, False, 10)
        finally:
            service.close()
        self.assertEqual(cut["finish_reason"], "length")
        self.assertFalse(first["cached"])
        self.assertTrue(second["cached"])
        self.assertEqual(second["text"], '{"a": 1}')
        self.assertEqual(len(service.requests), 2)

    def test_the_request_holds_the_thinking_switch_and_json_mode(self):
        service = Service([(200, chat_body("{}"))])
        try:
            label_rules.ask(service.entry, content(1), 77, True, 10,
                            extra={"repetition_penalty": 1.15})
        finally:
            service.close()
        request = service.requests[0]
        self.assertEqual(request["chat_template_kwargs"], {"enable_thinking": True})
        self.assertEqual(request["response_format"], {"type": "json_object"})
        self.assertEqual(request["max_tokens"], 77)
        self.assertEqual(request["temperature"], 0)
        self.assertEqual(request["repetition_penalty"], 1.15)


class PictureTest(unittest.TestCase):
    def test_a_small_transparent_picture_is_enlarged_on_white(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cut.png"
            Image.new("RGBA", (10, 20), (0, 0, 0, 0)).save(path)
            data, size = label_rules.picture_png(str(path), 64)
        self.assertEqual(size, (32, 64))
        with Image.open(io.BytesIO(data)) as image:
            self.assertEqual(image.mode, "RGB")
            self.assertEqual(image.getpixel((5, 5)), (255, 255, 255))


class ConfigTest(unittest.TestCase):
    def settings(self, block):
        self.tmp = tempfile.TemporaryDirectory()
        path = Path(self.tmp.name) / "config.yaml"
        config = {"database_file": "lab.sqlite3", "vlm": [
            {"name": "one", "protocol": "openai", "thinking_field": "chat_template_kwargs",
             "endpoint": "http://127.0.0.1:9/v1", "model": "m1"},
            {"name": "two", "protocol": "openai", "thinking_field": "top_level",
             "endpoint": "http://127.0.0.1:9/v1", "model": "m2"}]}
        if block is not None:
            config["label_rules"] = block
        path.write_text(yaml.safe_dump(config), encoding="utf-8")
        self.addCleanup(self.tmp.cleanup)
        return embeddings.load_settings(str(path))

    def test_the_defaults_and_the_entries(self):
        values = label_rules.config_values(self.settings({"vlm": "one"}))
        self.assertEqual(values["entry"].name, "one")
        self.assertEqual(values["rules_entry"].name, "one")
        self.assertFalse(values["rules_thinking"])
        self.assertEqual(values["rules_max_images"], 20)
        values = label_rules.config_values(self.settings({"vlm": "one", "rules_vlm": "two"}))
        self.assertEqual(values["rules_entry"].name, "two")

    def test_the_checks_of_the_block(self):
        cases = [({"vlm": "one", "size": 1}, "unknown key: size"),
                 ({"vlm": "one", "rules_thinking": "yes"}, "true or false"),
                 ({"vlm": "one", "rules_max_images": 0}, "rules_max_images"),
                 ({"vlm": "one", "timeout_s": -1}, "timeout_s"),
                 ({"vlm": "one", "rules_max_tokens": 32000}, "rules_context_tokens"),
                 ({"vlm": "missing"}, "no vlm entry missing"),
                 ([], "MUST be a mapping")]
        for block, message in cases:
            with self.assertRaises(label_rules.RuleError) as caught:
                label_rules.config_values(self.settings(block))
            self.assertIn(message, str(caught.exception))

    def test_the_settings_sha_follows_the_prompt_settings(self):
        one = label_rules.config_values(self.settings({"vlm": "one"}))
        thinking = label_rules.config_values(self.settings({"vlm": "one",
                                                            "rules_thinking": True}))
        more = label_rules.config_values(self.settings({"vlm": "one", "rules_workers": 5}))
        self.assertNotEqual(one["rules_sha"], thinking["rules_sha"])
        self.assertEqual(one["rules_sha"], more["rules_sha"])
        self.assertEqual(one["describe_sha"], thinking["describe_sha"])
        # The limits of the additional pictures are in the inputs of a rule, not here.
        images = label_rules.config_values(self.settings({"vlm": "one",
                                                          "rules_max_images": 5}))
        self.assertEqual(one["rules_sha"], images["rules_sha"])



class DescribeRepairTest(unittest.TestCase):
    """Plan 61: stage 1 gives obvious key drift the key of the prompt."""

    def describe(self, answer):
        entry = vlm_config.Entry("test-vlm", "openai", "chat_template_kwargs",
                                 "http://127.0.0.1:9/v1", "test-model", "")
        cfg = {"entry": entry, "describe_side": 64, "describe_max_tokens": 100,
               "thinking": False, "timeout_s": 10, "describe_sha": "s"}

        def ask_fn(entry, content, max_tokens, thinking, timeout, extra=None):
            return {"text": json.dumps(answer, ensure_ascii=False), "ms": 5, "usage": {},
                    "finish_reason": "stop", "model": "test-model", "cached": False}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cut.png"
            Image.new("RGB", (10, 20), "red").save(path)
            return label_rules.describe(ask_fn, cfg, {
                "kind": "package", "sha256": "c" * 64, "source_sha256": "a" * 64,
                "path": str(path)})

    def test_a_drifted_answer_gets_the_keys_of_the_prompt(self):
        rec = self.describe({"text": [{"text": "ФАНТОМ", "where": "left"}], "number": [],
                             "vintage": None, "colours": [], "design": "", "marks": [],
                             "bottle": ""})
        self.assertIsNone(rec["error"])
        self.assertEqual(list(rec["description"]), ["texts", "numbers", "vintage", "colours",
                                                    "design", "marks", "bottle"])
        self.assertEqual(rec["description"]["texts"], [{"text": "ФАНТОМ", "where": "left"}])
        self.assertEqual(rec["repairs"], [["text", "texts"], ["number", "numbers"]])

    def test_an_answer_with_the_keys_of_the_prompt_has_no_repairs(self):
        answer = {"texts": [], "numbers": [], "vintage": None, "colours": [], "design": "",
                  "marks": [], "bottle": ""}
        rec = self.describe(answer)
        self.assertEqual(rec["description"], answer)
        self.assertNotIn("repairs", rec)


class VintageTagTest(unittest.TestCase):
    """A vintage tag of a wine counts as a year of the catalogue name (plan 97, owner
    message of about 2026-10-01T00:08:00+0300)."""

    QUESTION = {"question": "What vintage year is printed?",
                "answers": {"A": "2021", "B": "2020"}}

    def test_the_tags_of_a_card(self):
        catalog = {A: {"tags": ["brut", "2021", "vintage:2019"]}, B: {"tags": ["no_year"]},
                   C: {"tags": ["vintage:21", "20201"]}}
        self.assertEqual(label_rules.vintage_tags(A, catalog), ({"2019", "2021"}, False))
        self.assertEqual(label_rules.vintage_tags(B, catalog), (set(), True))
        self.assertEqual(label_rules.vintage_tags(C, catalog), (set(), False))
        self.assertEqual(label_rules.vintage_tags(A, None), (set(), False))

    def test_a_tagged_year_counts_as_a_year_of_the_name(self):
        names = {A: {"name": "Wine"}, B: {"name": "Wine"}}
        untagged = label_rules.check_rule(rule([self.QUESTION]), {"A": A, "B": B}, names)
        self.assertFalse(untagged["questions"][0]["valid"])
        catalog = {A: {"name": "Wine", "tags": ["2021"]},
                   B: {"name": "Wine", "tags": ["vintage:2020"]}}
        out = label_rules.check_rule(rule([self.QUESTION]), {"A": A, "B": B}, catalog)
        self.assertEqual(out["mode"], "sheet")
        self.assertTrue(out["questions"][0]["valid"])
        self.assertEqual(out["questions"][0]["answers"], {A: "2021", B: "2020"})

    def test_the_tag_no_year_makes_the_card_of_every_other_vintage(self):
        catalog = {A: {"name": "Wine", "tags": ["2021"]}, B: {"name": "Wine", "tags": ["no_year"]}}
        # The label of B reads a year; the tag wins. With no description, B still counts.
        for cards in ({B: {"description": {"vintage": 2019}}}, {}):
            dated, undated = label_rules.vintage_facts([A, B], catalog, cards)
            self.assertEqual(dated, {A: {"years": {"2021"}, "where": "in a tag"}})
            self.assertEqual(undated, [B])
        out = label_rules.check_rule(rule([
            {"question": "What vintage year is printed?", "answers": {"A": "2021", "B": "other"}},
        ]), {"A": A, "B": B}, catalog, {})
        self.assertTrue(out["questions"][0]["valid"])
        self.assertEqual(out["questions"][0]["answers"], {A: "2021", B: "other"})

    def test_a_year_of_the_name_wins_over_a_tag(self):
        catalog = {A: {"name": "Wine 2018", "tags": ["2021", "no_year"]}}
        dated, undated = label_rules.vintage_facts([A], catalog, {})
        self.assertEqual((dated, undated), ({A: {"years": {"2018"}, "where": "in the name"}}, []))

    def test_only_a_cluster_with_a_vintage_tag_gets_the_tag_note(self):
        letters = {"A": A, "B": B}
        pictures = {A: {"kind": "label", "sha256": "sha-a", "path": "a",
                        "source_sha256": "src-a"},
                    B: {"kind": "label", "sha256": "sha-b", "path": "b",
                        "source_sha256": "src-b"}}
        cfg = {"rules_sha": "s"}

        def render(path, side):
            return b"png", (side, side)

        def prompt(catalog):
            return label_rules.rules_content(letters, catalog, {}, "", pictures, 64,
                                             render=render)[2]

        def inputs(catalog):
            return label_rules.inputs_sha([A, B], catalog, {}, pictures, pictures, "", cfg)

        plain = {A: {"name": "Wine"}, B: {"name": "Wine"}}
        other_tags = {A: {"name": "Wine", "tags": ["brut"]}, B: {"name": "Wine"}}
        tagged = {A: {"name": "Wine", "tags": ["2021"]},
                  B: {"name": "Wine", "tags": ["vintage:2020", "no_year"]}}
        self.assertNotIn("Vintage tags.", prompt(plain))
        self.assertEqual(prompt(other_tags), prompt(plain))
        self.assertEqual(inputs(other_tags), inputs(plain))
        note = label_rules.TAG_NOTE % {"tags": "Card A: 2021; Card B: 2020, no_year"}
        text = prompt(tagged)
        self.assertIn("\n\n" + note + "\n\nAnswer with one JSON object:", text)
        self.assertNotEqual(inputs(tagged), inputs(plain))
        # A card with a year tag and a card with `no_year` also get the vintage note,
        # after the tag note.
        mixed = {A: {"name": "Wine", "tags": ["2021"]}, B: {"name": "Wine", "tags": ["no_year"]}}
        text = prompt(mixed)
        self.assertLess(text.index("Vintage tags."), text.index("Vintage variants."))
        self.assertIn("Card A: 2021, in a tag", text)


class ExtraPictureTest(unittest.TestCase):
    """Stage 2 also sends the label pictures of the additional photos (owner message of
    2026-09-30T15:55:42+0300)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cfg = {"rules_entry": vlm_config.Entry(
                        "test-vlm", "openai", "chat_template_kwargs",
                        "http://127.0.0.1:9/v1", "test-model", ""),
                    "rules_max_images": 20, "rules_context_tokens": 32768,
                    "rules_max_tokens": 2500, "rules_max_side": 64,
                    "rules_thinking": False, "rules_timeout_s": 10, "rules_sha": "s"}
        self.calls = []

    def file(self, name, colour):
        path = Path(self.tmp.name) / ("%s.png" % name)
        Image.new("RGB", (32, 64), colour).save(path)
        return str(path)

    def picture(self, name, image_type=None):
        out = {"kind": "label", "sha256": "sha-" + name, "path": self.file(name, "red"),
               "source_sha256": "src-" + name}
        if image_type:
            out["image_type"] = image_type
        return out

    def ask(self, entry, content, max_tokens, thinking, timeout, extra=None):
        self.calls.append(content)
        answer = {"differences": "d", "rule": "r", "indistinguishable": [],
                  "questions": [{"question": "What name is printed on the label?",
                                 "answers": {"A": "ONE", "B": "TWO"}}]}
        return {"text": json.dumps(answer), "ms": 1, "usage": {}, "finish_reason": "stop",
                "model": "test-model", "cached": False}

    def test_the_pictures_of_the_additional_photos(self):
        def source(name, label=True):
            cut = {"sha256": "cut-" + name, "path": "/cut/" + name} if label else None
            return {"path": "/orig/" + name, "cuts": {"package": None, "label": cut}}
        sources = {"main": source("main"), "ff": source("ff"), "fb": source("fb", False),
                   "lf": source("lf", False), "lb": source("lb")}
        wine = {"columns": [("main", "main"), ("full_front", "ff"), ("full_back", "fb"),
                            ("label_front", "lf"), ("label_back", "lb")]}
        out = label_rules.extra_pictures(wine, sources)
        # A full photo with no label cut gives nothing; a close-up with no cut gives its
        # original. The main image is not an additional picture.
        self.assertEqual([(p["image_type"], p["sha256"], p["path"]) for p in out], [
            ("full_front", "cut-ff", "/cut/ff"), ("label_front", "lf", "/orig/lf"),
            ("label_back", "cut-lb", "/cut/lb")])
        self.assertEqual(out[0]["source_sha256"], "ff")
        self.assertEqual(label_rules.extra_pictures(None, sources), [])

    def test_the_order_takes_one_picture_of_each_card_first(self):
        extras = {A: ["a1", "a2", "a3"], B: ["b1"], C: ["c1", "c2"]}
        order = label_rules.extra_order(LETTERS, extras)
        self.assertEqual([p for _, p in order], ["a1", "b1", "c1", "a2", "c2", "a3"])
        self.assertEqual(label_rules.extra_order(LETTERS, None), [])

    def test_the_extras_go_after_their_card_with_the_extra_caption(self):
        letters = {"A": A, "B": B}
        pictures = {A: self.picture("a"), B: self.picture("b")}
        extras = {A: [self.picture("a-back", "full_back")]}
        content, _, _, sent = label_rules.rules_content(letters, {}, {}, "", pictures, 64,
                                                        extras)
        kinds = [part["type"] if part["type"] == "image_url" else part["text"]
                 for part in content[:-1]]
        self.assertEqual(kinds, [
            "Card A:", "image_url",
            label_rules.CAPTION_EXTRA % {"letter": "A", "side": "back"}, "image_url",
            "Card B:", "image_url"])
        self.assertEqual(sent, {A: ["sha-a", "sha-a-back"], B: ["sha-b"]})

    def test_the_extras_are_trimmed_to_the_image_limit(self):
        self.cfg["rules_max_images"] = 3
        pictures = {A: self.picture("a"), B: self.picture("b")}
        extras = {A: [self.picture("a1", "full_front"), self.picture("a2", "label_back")],
                  B: [self.picture("b1", "full_back")]}
        rec = label_rules.build_rule(self.ask, self.cfg, [A, B], {}, {}, pictures,
                                     pictures, "", "h", extras)
        self.assertIsNone(rec["error"])
        images = sum(1 for part in self.calls[0] if part["type"] == "image_url")
        self.assertEqual(images, 3)
        self.assertEqual([p["sha256"] for p in rec["extra_pictures"][A]], ["sha-a1"])
        self.assertNotIn(B, rec["extra_pictures"])
        self.assertEqual([(d["slug"], d["sha256"]) for d in rec["extras_dropped"]],
                         [(B, "sha-b1"), (A, "sha-a2")])
        self.assertEqual(rec["questions"][0]["evidence"], {A: ["sha-a", "sha-a1"],
                                                           B: ["sha-b"]})

    def test_the_extras_are_trimmed_to_the_token_budget_first(self):
        pictures = {A: self.picture("a"), B: self.picture("b")}
        extras = {A: [self.picture("a1", "full_front")], B: [self.picture("b1", "full_back")]}
        letters = {"A": A, "B": B}
        _, one, _, _ = label_rules.rules_content(letters, {}, {}, "", pictures, 64,
                                                 {A: extras[A]})
        _, two, _, _ = label_rules.rules_content(letters, {}, {}, "", pictures, 64, extras)
        self.assertLess(one, two)
        # The budget holds one additional picture at the configured side.
        self.cfg["rules_context_tokens"] = (one + self.cfg["rules_max_tokens"]
                                            + label_rules.CONTEXT_MARGIN)
        rec = label_rules.build_rule(self.ask, self.cfg, [A, B], {}, {}, pictures,
                                     pictures, "", "h", extras)
        self.assertEqual(rec["max_side"], 64)
        self.assertEqual(rec["prompt_tokens_estimate"], one)
        self.assertEqual(list(rec["extra_pictures"]), [A])
        self.assertEqual([d["sha256"] for d in rec["extras_dropped"]], ["sha-b1"])

    def test_a_cluster_with_no_extra_keeps_its_inputs_sha(self):
        pictures = {A: self.picture("a"), B: self.picture("b")}
        old = label_rules.inputs_sha([A, B], {}, {}, pictures, pictures, "", self.cfg)
        # An additional picture of a card outside the cluster changes nothing.
        other = {C: [self.picture("c1", "full_back")]}
        self.assertEqual(label_rules.inputs_sha([A, B], {}, {}, pictures, pictures, "",
                                                self.cfg, other), old)
        mine = {A: [self.picture("a1", "full_back")]}
        new = label_rules.inputs_sha([A, B], {}, {}, pictures, pictures, "", self.cfg, mine)
        self.assertNotEqual(new, old)
        self.cfg["rules_max_images"] = 5
        self.assertNotEqual(label_rules.inputs_sha([A, B], {}, {}, pictures, pictures, "",
                                                   self.cfg, mine), new)
        self.assertEqual(label_rules.inputs_sha([A, B], {}, {}, pictures, pictures, "",
                                                self.cfg), old)


if __name__ == "__main__":
    unittest.main()
