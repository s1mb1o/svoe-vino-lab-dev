import os
import sys
import unittest
from importlib import import_module
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(1, str(ROOT / "scripts"))
# `scripts/common.py` reads the old configuration of the review tool: `config.yaml` is
# the configuration of the lab server.
os.environ.setdefault("SVOE_VINO_REVIEW_CONFIG", str(ROOT / "config.old.yaml"))
import vlm_config  # noqa: E402
import common  # noqa: E402
import cluster_rules  # noqa: E402

VERIFY = import_module("04_verify")

GX10_CHAT = "http://192.168.86.14:18081/v1/chat/completions"
NAMES = ["qwen3.5-9b-nvfp4", "qwen3.5-9b", "qwen3-vl-32b", "qwencloud-qwen3.8-max",
         "qwencloud-qwen3.8-flash", "dashscope-qwen3.7-flash"]


def item(**changes):
    out = {"name": "m", "protocol": "openai", "thinking_field": "chat_template_kwargs",
           "endpoint": "http://vlm.invalid/v1", "model": "model-1", "key": None}
    out.update(changes)
    return out


def load(name):
    with open(ROOT / name, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


class EntriesTest(unittest.TestCase):
    def test_an_entry_with_no_key(self):
        entry = vlm_config.entry({"vlm": [item()]}, "m")
        self.assertEqual(entry.url, "http://vlm.invalid/v1/chat/completions")
        self.assertEqual((entry.model, entry.key_env, entry.api_key()), ("model-1", "", ""))

    def test_a_trailing_slash_of_the_endpoint(self):
        entry = vlm_config.entry({"vlm": [item(endpoint="http://vlm.invalid/v1/")]}, "m")
        self.assertEqual(entry.url, "http://vlm.invalid/v1/chat/completions")

    def test_an_env_key_is_read_at_run_time(self):
        entry = vlm_config.entry({"vlm": [item(key="{env:VLM_CONFIG_TEST_KEY}")]}, "m")
        self.assertEqual(entry.key_env, "VLM_CONFIG_TEST_KEY")
        with mock.patch.dict(os.environ, {"VLM_CONFIG_TEST_KEY": "secret-value"}):
            self.assertEqual(entry.api_key(), "secret-value")
        self.assertEqual(entry.api_key(), "")

    def test_max_tokens_is_8192_when_absent(self):
        self.assertEqual(vlm_config.entry({"vlm": [item()]}, "m").max_tokens, 8192)
        self.assertEqual(vlm_config.entry({"vlm": [item(max_tokens=2048)]}, "m").max_tokens,
                         2048)
        for value in (0, -1, "8192", True, 1.5, None):
            with self.subTest(value=value):
                with self.assertRaises(vlm_config.VlmConfigError):
                    vlm_config.entries({"vlm": [item(max_tokens=value)]})

    def test_a_key_value_is_refused_and_not_repeated(self):
        with self.assertRaises(vlm_config.VlmConfigError) as caught:
            vlm_config.entries({"vlm": [item(key="sk-secret-value")]})
        self.assertNotIn("sk-secret-value", str(caught.exception))
        for key in ("{env:}", "{env:A B}", "x{env:A}", 12):
            with self.assertRaises(vlm_config.VlmConfigError):
                vlm_config.entries({"vlm": [item(key=key)]})

    def test_values_that_are_not_valid(self):
        for changes in ({"protocol": "grpc"}, {"thinking_field": "body"},
                        {"endpoint": "vlm.invalid/v1"}, {"model": ""}, {"name": None}):
            with self.subTest(changes=changes):
                with self.assertRaises(vlm_config.VlmConfigError):
                    vlm_config.entries({"vlm": [item(**changes)]})

    def test_a_missing_and_an_unknown_key(self):
        no_key = item()
        del no_key["key"]
        self.assertEqual(vlm_config.entry({"vlm": [no_key]}, "m").key_env, "")
        missing = item()
        del missing["model"]
        with self.assertRaisesRegex(vlm_config.VlmConfigError, "has no key model"):
            vlm_config.entries({"vlm": [missing]})
        with self.assertRaisesRegex(vlm_config.VlmConfigError, "unknown key url"):
            vlm_config.entries({"vlm": [item(url="http://vlm.invalid")]})

    def test_the_form_of_the_section(self):
        self.assertEqual(vlm_config.entries({}), {})
        self.assertEqual(vlm_config.entries(None), {})
        with self.assertRaises(vlm_config.VlmConfigError):
            vlm_config.entries({"vlm": {"m": item()}})
        with self.assertRaises(vlm_config.VlmConfigError):
            vlm_config.entries({"vlm": ["m"]})
        with self.assertRaisesRegex(vlm_config.VlmConfigError, "repeats"):
            vlm_config.entries({"vlm": [item(), item()]})
        with self.assertRaisesRegex(vlm_config.VlmConfigError, "no vlm entry other"):
            vlm_config.entry({"vlm": [item()]}, "other")

    def test_the_file_order(self):
        names = list(vlm_config.entries({"vlm": [item(name="b"), item(name="a")]}))
        self.assertEqual(names, ["b", "a"])


class ProjectConfigTest(unittest.TestCase):
    def test_both_files_hold_the_same_section(self):
        new, old = load("config.yaml"), load("config.old.yaml")
        self.assertEqual(new["vlm"], old["vlm"])
        self.assertEqual(list(vlm_config.entries(new)), NAMES)

    def test_the_entries(self):
        entries = vlm_config.entries(load("config.yaml"))
        nvfp4 = entries["qwen3.5-9b-nvfp4"]
        self.assertEqual((nvfp4.url, nvfp4.model, nvfp4.key_env, nvfp4.thinking_field),
                         (GX10_CHAT, "qwen3.5-9b-nvfp4", "", "chat_template_kwargs"))
        cloud = entries["qwencloud-qwen3.8-max"]
        self.assertEqual(cloud.url, "https://token-plan.ap-southeast-1.maas.aliyuncs.com"
                                    "/compatible-mode/v1/chat/completions")
        self.assertEqual((cloud.model, cloud.key_env, cloud.thinking_field),
                         ("qwen3.8-max", "QWENCLOUD_TOKEN_PLAN_API_KEY", "top_level"))
        self.assertEqual(entries["dashscope-qwen3.7-flash"].key_env, "QWENCLOUD_PAYGO_API_KEY")


class ClusterRulesTest(unittest.TestCase):
    config = {"vlm": [item(name="local"),
                      item(name="cloud", thinking_field="top_level", key="{env:K}")]}

    def test_the_stages_of_config_old(self):
        self.assertEqual((cluster_rules.URL, cluster_rules.MODEL), (GX10_CHAT, "qwen3.5-9b"))
        self.assertEqual((cluster_rules.API, cluster_rules.KEY_ENV), ("llama.cpp", ""))
        self.assertEqual(cluster_rules.RULES_URL,
                         "https://token-plan.ap-southeast-1.maas.aliyuncs.com"
                         "/compatible-mode/v1/chat/completions")
        self.assertEqual((cluster_rules.RULES_MODEL, cluster_rules.RULES_API,
                          cluster_rules.RULES_KEY_ENV),
                         ("qwen3.8-max", "qwencloud", "QWENCLOUD_TOKEN_PLAN_API_KEY"))

    def test_stage_2_uses_the_entry_of_stage_1_by_default(self):
        first, second = cluster_rules.stage_entries({"vlm": "cloud"}, self.config)
        self.assertEqual((first.name, second.name), ("cloud", "cloud"))
        first, second = cluster_rules.stage_entries({"vlm": "local", "rules_vlm": "cloud"},
                                                    self.config)
        self.assertEqual((first.name, second.name), ("local", "cloud"))

    def test_the_default_entry_is_qwen3_5_9b(self):
        first, second = cluster_rules.stage_entries({}, load("config.yaml"))
        self.assertEqual((first.name, second.name), ("qwen3.5-9b", "qwen3.5-9b"))

    def test_an_old_key_is_refused(self):
        for key in cluster_rules.OLD_VLM_KEYS:
            with self.subTest(key=key):
                with self.assertRaisesRegex(common.ConfigError, key):
                    cluster_rules.stage_entries({"vlm": "local", key: "x"}, self.config)

    def test_a_missing_entry_is_refused(self):
        with self.assertRaises(vlm_config.VlmConfigError):
            cluster_rules.stage_entries({"vlm": "other"}, self.config)

    def test_the_default_vlm_is_the_entry_of_stage_1(self):
        vlm = cluster_rules.Vlm()
        self.assertEqual((vlm.url, vlm.model, vlm.api, vlm.key_env),
                         (GX10_CHAT, "qwen3.5-9b", "llama.cpp", ""))


class VerifyBackendsTest(unittest.TestCase):
    def build(self, spec, env=None):
        """Build with `env` added to the shell; without `env`, the key of the Token Plan
        is not set. `patch.dict` restores the shell afterwards."""
        with mock.patch.dict(os.environ, env or {}), \
                mock.patch.object(VERIFY, "log", lambda message: None):
            if env is None:
                os.environ.pop("QWENCLOUD_TOKEN_PLAN_API_KEY", None)
            return VERIFY.build_backends(spec, load("config.yaml"))

    def test_the_default_backend_is_the_old_local_backend(self):
        backend, = self.build("qwen3-vl-32b:12")
        self.assertEqual((backend.name, backend.url, backend.model, backend.key,
                          backend.workers), ("qwen3-vl-32b", GX10_CHAT, "qwen3-vl-32b", "", 12))

    def test_an_unknown_name_and_a_missing_key_are_ignored(self):
        self.assertEqual(self.build("local:12,tokenplan:8,qwencloud-qwen3.8-flash:8"), [])

    def test_a_key_comes_from_the_shell(self):
        backend, = self.build("qwencloud-qwen3.8-flash",
                              {"QWENCLOUD_TOKEN_PLAN_API_KEY": "secret-value"})
        self.assertEqual((backend.model, backend.key, backend.workers),
                         ("qwen3.8-flash", "secret-value", 4))


if __name__ == "__main__":
    unittest.main()
