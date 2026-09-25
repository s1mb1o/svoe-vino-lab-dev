import base64
import contextlib
import io
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
from importlib import import_module
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(1, str(ROOT / "scripts"))
# `scripts/common.py` reads the old configuration of the review tool: `config.yaml` is
# the configuration of the lab server.
os.environ.setdefault("SVOE_VINO_REVIEW_CONFIG", str(ROOT / "config.old.yaml"))
import model_cache  # noqa: E402
import cluster_rules  # noqa: E402

VERIFY = import_module("04_verify")
BENCH = import_module("bench_vlm_models")


def data_url(raw, kind="image/jpeg"):
    return "data:%s;base64,%s" % (kind, base64.b64encode(raw).decode())


def chat(text="{}", choices=True):
    body = {"model": "m", "usage": {"total_tokens": 3}}
    if choices:
        body["choices"] = [{"message": {"content": text}, "finish_reason": "stop"}]
    return body


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeUrlopen:
    """A stand-in for `urllib.request.urlopen`. Each call takes the next answer: a dict
    is a body of HTTP 200, an exception is raised."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.requests = []

    def __call__(self, request, timeout=None):
        self.requests.append(request)
        answer = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        if isinstance(answer, Exception):
            raise answer
        return Response(json.dumps(answer).encode("utf-8"))


def http_error(code):
    return urllib.error.HTTPError("http://vlm.invalid", code, "error", {}, io.BytesIO(b"x"))


class CacheCase(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.old_root, model_cache.ROOT = model_cache.ROOT, self.directory.name
        model_cache._warned = False

    def tearDown(self):
        model_cache.ROOT = self.old_root
        model_cache._warned = False
        self.directory.cleanup()

    def files(self):
        return sorted(str(path.relative_to(self.directory.name))
                      for path in Path(self.directory.name).rglob("*") if path.is_file())


class ModelCacheTest(CacheCase):
    def fields(self, **change):
        values = {"endpoint": "http://gx10.invalid/upstream/sam3/segment_multi",
                  "model": "sam3", "params": {"threshold": "0.35", "mask": "0.5"},
                  "prompt": "wine bottle", "images": [b"one", b"two"]}
        values.update(change)
        return model_cache.request_fields(**values)

    def test_key_changes_with_each_field_and_not_with_the_order_of_params(self):
        base = model_cache.key_of(self.fields())
        self.assertEqual(model_cache.key_of(self.fields()), base)
        self.assertEqual(model_cache.key_of(
            self.fields(params={"mask": "0.5", "threshold": "0.35"})), base)
        others = [self.fields(endpoint="http://127.0.0.1:9/upstream/sam3/segment_multi"),
                  self.fields(model="sam3-new"),
                  self.fields(params={"threshold": "0.4", "mask": "0.5"}),
                  self.fields(prompt="wine bottle, box"),
                  self.fields(images=[b"one", b"three"]),
                  self.fields(images=[b"two", b"one"])]
        keys = {model_cache.key_of(fields) for fields in others}
        self.assertEqual(len(keys), len(others))
        self.assertNotIn(base, keys)

    def test_store_then_lookup_answers_the_record_in_the_model_directory(self):
        fields = self.fields(model="facebook/sam3")
        self.assertIsNone(model_cache.lookup(fields))
        model_cache.store(fields, {"instances": []}, 1234.4)
        key = model_cache.key_of(fields)
        self.assertEqual(self.files(), [os.path.join("facebook-sam3", key[:2], key + ".json")])
        record = model_cache.lookup(fields)
        self.assertEqual(record["answer"], {"instances": []})
        self.assertEqual((record["key"], record["ms"], record["v"]), (key, 1234, 1))
        self.assertEqual(record["request"]["images"],
                         [model_cache.sha256_hex(b"one"), model_cache.sha256_hex(b"two")])
        self.assertRegex(record["created"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d{4}$")
        self.assertEqual(os.stat(model_cache.path_of(fields)).st_mode & 0o777, 0o644)

    def test_lookup_misses_for_a_broken_file_and_for_other_request_fields(self):
        fields = self.fields()
        path = model_cache.path_of(fields)
        os.makedirs(os.path.dirname(path))
        Path(path).write_text("{broken", encoding="utf-8")
        self.assertIsNone(model_cache.lookup(fields))
        record = {"v": 1, "request": self.fields(prompt="other"), "answer": {}}
        Path(path).write_text(json.dumps(record), encoding="utf-8")
        self.assertIsNone(model_cache.lookup(fields))
        model_cache.store(fields, {"instances": [1]}, 5)
        self.assertEqual(model_cache.lookup(fields)["answer"], {"instances": [1]})

    def test_with_read_off_a_lookup_misses_and_a_store_still_writes(self):
        # The checkbox `Use caches` of the dialog `Run>`, off (plan 39).
        self.addCleanup(setattr, model_cache, "READ", True)
        fields = self.fields()
        model_cache.store(fields, {"instances": [1]}, 5)
        model_cache.READ = False
        self.assertIsNone(model_cache.lookup(fields))
        model_cache.store(fields, {"instances": [2]}, 6)
        model_cache.READ = True
        self.assertEqual(model_cache.lookup(fields)["answer"], {"instances": [2]})

    def test_parallel_writes_of_one_key_leave_one_whole_record(self):
        fields = self.fields()
        answer = {"instances": [{"mask_png_b64": "A" * 200000}]}
        threads = [threading.Thread(target=model_cache.store, args=(fields, answer, 1))
                   for _ in range(16)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len(self.files()), 1)
        self.assertTrue(self.files()[0].endswith(".json"))
        self.assertEqual(model_cache.lookup(fields)["answer"], answer)

    def test_failed_write_warns_one_time_and_does_not_raise(self):
        blocker = Path(self.directory.name) / "file"
        blocker.write_text("x", encoding="utf-8")
        model_cache.ROOT = str(blocker)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            model_cache.store(self.fields(), {"instances": []}, 1)
            model_cache.store(self.fields(prompt="other"), {"instances": []}, 1)
        self.assertEqual(stderr.getvalue().count("model_cache: cannot write"), 1)
        self.assertIsNone(model_cache.lookup(self.fields()))

    def test_vlm_fields_replace_each_data_url_by_its_hash(self):
        raw = b"\xff\xd8jpeg bytes"
        payload = {"model": "qwen3.5-9b", "temperature": 0, "max_tokens": 10,
                   "messages": [{"role": "user", "content": [
                       {"type": "image_url", "image_url": {"url": data_url(raw)}},
                       {"type": "text", "text": "describe"}]}]}
        fields = model_cache.vlm_fields("http://gx10.invalid/v1/chat/completions", payload)
        digest = model_cache.sha256_hex(raw)
        self.assertEqual(fields["model"], "qwen3.5-9b")
        self.assertEqual(fields["params"], {"temperature": 0, "max_tokens": 10})
        self.assertEqual(fields["images"], [digest])
        self.assertEqual(fields["prompt"][0]["content"][0]["image_url"]["url"],
                         "data:image/jpeg;base64,sha256:" + digest)
        self.assertNotIn(base64.b64encode(raw).decode(), model_cache.canonical(fields))
        self.assertIn(data_url(raw), json.dumps(payload))  # the payload does not change
        other_text = json.loads(json.dumps(payload))
        other_text["messages"][0]["content"][1]["text"] = "describe again"
        self.assertNotEqual(model_cache.key_of(fields), model_cache.key_of(
            model_cache.vlm_fields("http://gx10.invalid/v1/chat/completions", other_text)))

    def test_vlm_fields_refuse_a_url_that_is_not_a_base64_data_url(self):
        for url in ("https://example.invalid/a.jpg", "data:image/png,plain",
                    "data:image/png;base64,***"):
            payload = {"model": "m", "messages": [{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": url}}]}]}
            self.assertIsNone(model_cache.vlm_fields("http://vlm.invalid", payload), url)
        text_only = {"model": "m", "messages": [{"role": "user", "content": "hello"}]}
        self.assertEqual(model_cache.vlm_fields("http://vlm.invalid", text_only)["images"], [])


class ClusterRulesVlmTest(CacheCase):
    def content(self, text="describe"):
        return [{"type": "image_url", "image_url": {"url": data_url(b"label")}},
                {"type": "text", "text": text}]

    def test_repeated_ask_reads_the_cache(self):
        fake = FakeUrlopen(chat('{"a": 1}'))
        vlm = cluster_rules.Vlm(url="http://vlm.invalid/v1/chat/completions", model="m")
        with mock.patch.object(cluster_rules.urllib.request, "urlopen", fake):
            first = vlm.ask(self.content(), 100)
            second = vlm.ask(self.content(), 100)
            vlm.ask(self.content("other"), 100)
            vlm.ask(self.content(), 200)
        self.assertEqual(len(fake.requests), 3)
        self.assertEqual((vlm.calls, vlm.hits), (3, 1))
        self.assertEqual(second["text"], '{"a": 1}')
        self.assertEqual(second["ms"], first["ms"])
        self.assertEqual(second["finish_reason"], "stop")

    def test_a_cached_answer_needs_no_key(self):
        fake = FakeUrlopen(chat("ok"))
        vlm = cluster_rules.Vlm(url="http://vlm.invalid/v1/chat/completions", model="m",
                                api="qwencloud", key_env="MODEL_CACHE_TEST_KEY")
        with mock.patch.dict(os.environ, {"MODEL_CACHE_TEST_KEY": "secret-value"}), \
                mock.patch.object(cluster_rules.urllib.request, "urlopen", fake):
            vlm.ask(self.content(), 100)
        self.assertEqual(fake.requests[0].get_header("Authorization"), "Bearer secret-value")
        for path in Path(self.directory.name).rglob("*.json"):
            self.assertNotIn("secret-value", path.read_text(encoding="utf-8"))
        self.assertNotIn("MODEL_CACHE_TEST_KEY", os.environ)
        with mock.patch.object(cluster_rules.urllib.request, "urlopen", fake):
            self.assertEqual(vlm.ask(self.content(), 100)["text"], "ok")
        self.assertEqual((len(fake.requests), vlm.hits), (1, 1))

    def test_a_failure_and_a_body_with_no_choice_are_not_stored(self):
        vlm = cluster_rules.Vlm(url="http://vlm.invalid/v1/chat/completions", model="m",
                                retries=1)
        with mock.patch.object(cluster_rules.time, "sleep", lambda seconds: None), \
                mock.patch.object(cluster_rules.urllib.request, "urlopen",
                                  FakeUrlopen(http_error(500))):
            with self.assertRaises(cluster_rules.VlmError):
                vlm.ask(self.content(), 100)
        fake = FakeUrlopen(chat(choices=False), chat("late"))
        with mock.patch.object(cluster_rules.urllib.request, "urlopen", fake):
            self.assertEqual(vlm.ask(self.content(), 100)["text"], "")
            self.assertEqual(vlm.ask(self.content(), 100)["text"], "late")
            self.assertEqual(vlm.ask(self.content(), 100)["text"], "late")
        self.assertEqual((len(fake.requests), vlm.hits), (2, 1))


class VerifyAndBenchTest(CacheCase):
    def test_verify_backend_reads_the_cache(self):
        backend = VERIFY.Backend("local", "http://vlm.invalid/v1/chat/completions", "m",
                                 "", 1)
        fake = FakeUrlopen(chat('{"same_wine": true}'))
        with mock.patch.object(VERIFY.urllib.request, "urlopen", fake):
            first = backend.ask(data_url(b"ref"), data_url(b"cand"), "producer", "title")
            second = backend.ask(data_url(b"ref"), data_url(b"cand"), "producer", "title")
            backend.ask(data_url(b"cand"), data_url(b"ref"), "producer", "title")
        self.assertEqual(first, second)
        self.assertEqual((len(fake.requests), backend.hits), (2, 1))

    def test_bench_call_marks_a_cached_line_and_does_not_store_a_failure(self):
        item = {"producer": "p", "title": "t"}
        fake = FakeUrlopen(http_error(429), chat('{"same_wine": false}'))
        with mock.patch.object(BENCH.urllib.request, "urlopen", fake):
            failed = BENCH.call("qwen3.8-flash", item, data_url(b"r"), data_url(b"c"), "k")
            first = BENCH.call("qwen3.8-flash", item, data_url(b"r"), data_url(b"c"), "k")
            second = BENCH.call("qwen3.8-flash", item, data_url(b"r"), data_url(b"c"), "k")
        self.assertEqual((failed["ok"], failed["http"]), (False, 429))
        self.assertTrue(first["ok"])
        self.assertNotIn("cached", first)
        self.assertEqual((second["cached"], second["raw"]), (True, first["raw"]))
        self.assertEqual(len(fake.requests), 2)
        self.assertEqual(os.listdir(self.directory.name), ["qwen3.8-flash"])


if __name__ == "__main__":
    unittest.main()
