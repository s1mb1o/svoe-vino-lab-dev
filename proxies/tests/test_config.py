from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from model_proxy.config import ConfigError, load, parse, parse_size


ROOT = Path(__file__).resolve().parent.parent

BASE = {
    "passthrough": "gx10",
    "hosts": [
        {"name": "gx10", "kind": "llama-swap", "url": "http://gx10.test/", "slots": 4,
         "models": ["sam3", "siglip2-so400m-patch16-naflex"]},
        {"name": "kit", "kind": "bootstrap", "slots": 2, "models": ["sam3"],
         "ssh": {"target": "root@203.0.113.10", "local_port": 18191}},
    ],
}


def variant(**changes: object) -> dict:
    raw = copy.deepcopy(BASE)
    raw.update(changes)
    return raw


class RepositoryConfigTests(unittest.TestCase):
    def test_repository_config_is_valid(self) -> None:
        config = load(ROOT / "config.yaml")
        self.assertEqual((config.listen_host, config.listen_port), ("127.0.0.1", 18092))
        self.assertEqual(config.passthrough, "gx10")
        gx10 = config.hosts[0]
        self.assertEqual(gx10.url, "http://192.168.86.14:18082")
        self.assertIn("grounding-dino-base", gx10.models)
        self.assertIn("siglip2-so400m-patch16-512", gx10.models)
        kit = next(host for host in config.hosts if host.name == "kit")
        self.assertFalse(kit.enabled)
        self.assertEqual(kit.url, "http://127.0.0.1:18191")
        self.assertNotIn("grounding-dino-base", kit.models)
        self.assertEqual(config.pooled_models, frozenset(gx10.models))


class ParseTests(unittest.TestCase):
    def test_defaults_and_derived_values(self) -> None:
        config = parse(variant())
        self.assertEqual(config.listen_port, 18092)
        self.assertEqual(config.hosts[0].url, "http://gx10.test")
        kit = config.hosts[1]
        self.assertEqual(kit.url, "http://127.0.0.1:18191")
        self.assertEqual(kit.ssh.remote_port, 18090)
        self.assertEqual(config.ttl_seconds, 30 * 24 * 60 * 60)
        self.assertEqual(config.max_cache_bytes, 10 * 1024**3)
        self.assertEqual(config.pooled_models,
                         frozenset({"sam3", "siglip2-so400m-patch16-naflex"}))
        self.assertEqual(config.cache_path.parts[-2:],
                         ("svoe-vino-model-proxy", "cache.sqlite3"))
        self.assertFalse(str(config.cache_path).startswith("~"))

    def test_disabled_host_adds_no_pooled_model(self) -> None:
        raw = variant()
        raw["hosts"][1]["models"] = ["sam3", "siglip2-so400m-patch16-512"]
        raw["hosts"][1]["enabled"] = False
        self.assertNotIn("siglip2-so400m-patch16-512", parse(raw).pooled_models)

    def test_rules(self) -> None:
        cases = {
            "unknown key": variant(extra=1),
            "unknown host key": variant(hosts=[dict(BASE["hosts"][0], weight=2)]),
            "url and ssh": variant(hosts=[dict(BASE["hosts"][0],
                                               ssh={"target": "x", "local_port": 18191})]),
            "neither url nor ssh": variant(hosts=[{k: v for k, v in BASE["hosts"][0].items()
                                                   if k != "url"}]),
            "duplicate name": variant(hosts=[BASE["hosts"][0], dict(BASE["hosts"][0])]),
            "duplicate local port": variant(hosts=[
                BASE["hosts"][0], BASE["hosts"][1],
                dict(BASE["hosts"][1], name="kit2")]),
            "passthrough unknown": variant(passthrough="nope"),
            "passthrough disabled": variant(hosts=[dict(BASE["hosts"][0], enabled=False),
                                                   BASE["hosts"][1]]),
            "zero slots": variant(hosts=[dict(BASE["hosts"][0], slots=0)]),
            "empty models": variant(hosts=[dict(BASE["hosts"][0], models=[])]),
            "repeated model": variant(hosts=[dict(BASE["hosts"][0], models=["sam3", "sam3"])]),
            "bad kind": variant(hosts=[dict(BASE["hosts"][0], kind="vllm")]),
            "bad url": variant(hosts=[dict(BASE["hosts"][0], url="gx10.test")]),
            "bad name": variant(hosts=[dict(BASE["hosts"][0], name="gx 10")]),
            "no hosts": variant(hosts=[]),
            "listen port is a tunnel port": variant(listen={"port": 18191}),
            "bad size": variant(cache={"max_size": "ten"}),
            "zero attempts": variant(limits={"attempts": 0}),
            "negative timeout": variant(limits={"queue_timeout": -1}),
            "boolean slots": variant(hosts=[dict(BASE["hosts"][0], slots=True)]),
        }
        for name, raw in cases.items():
            with self.subTest(name), self.assertRaises(ConfigError):
                parse(raw)

    def test_parse_size(self) -> None:
        self.assertEqual(parse_size("256MiB", "x"), 256 * 1024**2)
        self.assertEqual(parse_size("1.5 GiB", "x"), int(1.5 * 1024**3))
        self.assertEqual(parse_size(4096, "x"), 4096)
        for bad in ("", "-1", 0, True, None):
            with self.subTest(bad=bad), self.assertRaises(ConfigError):
                parse_size(bad, "x")

    def test_load_reports_the_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.yaml"
            path.write_text("hosts: [\n", encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "bad.yaml"):
                load(path)
            with self.assertRaisesRegex(ConfigError, "cannot read"):
                load(Path(directory) / "missing.yaml")


if __name__ == "__main__":
    unittest.main()
