"""Tests of the configuration and of the API of the backend `cascade` (plan 85 of the
workbench), with local fake services and a fixture catalogue directory."""

import http.client
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

import yaml

from matcher.cascade import FastAnswer
from matcher.service import CascadeMatcher, ConfigError, load_matcher

import test_siglip2
from cascade_fakes import EAN_FULL, FakeServices, photo, rules
from test_catalog import EMBEDDING, ROWS, write_catalog
from test_match import multipart
from test_siglip2 import free_port, wait_for_server


ROOT = Path(__file__).resolve().parents[2]
PIPELINE = "cascade-test"


def write_cascade_catalog(root, codes=True, rule_files=True):
    """A fixture catalogue with the tables of the codes and the two rule files."""
    write_catalog(root)
    if codes:
        conn = sqlite3.connect(root / "catalog.sqlite3")
        conn.execute("CREATE TABLE wine_catalog (wine_slug, state)")
        conn.execute("CREATE TABLE wine_code (wine_slug, kind, value)")
        conn.executemany("INSERT INTO wine_catalog VALUES (?, ?)",
                         [("wine-a", "Active"), ("wine-b", "Active"), ("wine-old", "Disabled")])
        conn.executemany("INSERT INTO wine_code VALUES (?, ?, ?)", [
            ("wine-b", "gtin", "0" + EAN_FULL),
            ("wine-old", "gtin", "0" + EAN_FULL),
            ("wine-a", "barcode", "123"),
        ])
        conn.commit()
        conn.close()
    if rule_files:
        clusters, data = rules(slugs=("wine-a", "wine-b"))
        entry = root / "embeddings" / EMBEDDING
        (entry / "clusters.json").write_text(json.dumps(clusters), encoding="utf-8")
        (entry / "cluster-rules.json").write_text(json.dumps(data), encoding="utf-8")
    return root


def entry(catalog, fake, **changes):
    value = {"name": PIPELINE, "backend": "cascade", "catalog": str(catalog),
             "embedding": EMBEDDING, "endpoint": fake.siglip2,
             "barcode": {"endpoint": fake.scanner, "engine": "zxing-cpp", "crops": True},
             "sam3": {"endpoint": fake.sam3, "threshold": 0.35, "hand": True,
                      "label": True, "packages_first": False},
             "rerank": {"clusters": EMBEDDING, "endpoint": fake.vlm,
                        "model": "qwen3.5-9b-nvfp4", "window": 10, "side": 1536,
                        "max_tokens": 256, "timeout_seconds": 60}}
    for key, change in changes.items():
        if change is None:
            value.pop(key, None)
        else:
            value[key] = change
    return value


def write_config(path, pipeline, fast_answer=None, output_dir=None):
    matcher = {"pipeline": pipeline["name"],
               "output_dir": str(output_dir or path.parent / "requests")}
    if fast_answer is not None:
        matcher["fast_answer"] = fast_answer
    path.write_text(yaml.safe_dump({"matcher": matcher, "pipeline": [pipeline]}),
                    encoding="utf-8")
    return path


class CascadeConfigTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.fake = FakeServices()
        self.addCleanup(self.fake.close)
        self.catalog = write_cascade_catalog(self.root / "catalog")

    def load(self, pipeline, fast_answer=None):
        return load_matcher(write_config(self.root / "config.yaml", pipeline, fast_answer))

    def test_a_valid_entry_loads_with_its_stages_and_codes(self):
        matcher = self.load(entry(self.catalog, self.fake),
                            {"answer_at_seconds": 2.9, "timeout_seconds": 9.5})
        self.assertIsInstance(matcher, CascadeMatcher)
        self.assertEqual(matcher.fast_answer, FastAnswer(True, 2.9, 9.5))
        config = matcher.cascade.config
        self.assertEqual((config.barcode.engine, config.sam3.threshold, config.rerank.window),
                         ("zxing-cpp", 0.35, 10))
        self.assertEqual(matcher.cascade.codes.values, {("gtin", "0" + EAN_FULL): ("wine-b",)})
        self.assertEqual(sorted(matcher.cascade.rules.by_slug), ["wine-a", "wine-b"])
        self.assertIn("wine-c", matcher.cards)

    def test_the_stages_are_optional(self):
        pipeline = entry(self.catalog, self.fake)
        for key in ("barcode", "sam3", "rerank"):
            del pipeline[key]
        config = self.load(pipeline).cascade.config
        self.assertEqual((config.barcode, config.sam3, config.rerank), (None, None, None))

    def test_unknown_keys_are_errors_at_every_level(self):
        cases = [entry(self.catalog, self.fake, bundle="x"),
                 entry(self.catalog, self.fake, hand_selection=True),
                 entry(self.catalog, self.fake, barcode={"endpoint": self.fake.scanner,
                                                         "tile_scan": True}),
                 entry(self.catalog, self.fake, sam3={"endpoint": self.fake.sam3, "nouns": []}),
                 entry(self.catalog, self.fake, rerank={"clusters": EMBEDDING,
                                                        "endpoint": self.fake.vlm,
                                                        "thinking": True})]
        for pipeline in cases:
            with self.subTest(pipeline=sorted(pipeline)), self.assertRaises(ConfigError):
                self.load(pipeline)
        with self.assertRaises(ConfigError):
            self.load(entry(self.catalog, self.fake), {"answer_at": 2.9})

    def test_invalid_values_are_errors(self):
        cases = [
            {"barcode": {"endpoint": self.fake.scanner, "engine": "auto"}},
            {"barcode": {"endpoint": self.fake.scanner, "crops": "yes"}},
            {"sam3": {"endpoint": self.fake.sam3, "threshold": 1.5}},
            {"sam3": {"endpoint": self.fake.sam3, "hand": 1}},
            {"rerank": {"clusters": EMBEDDING, "endpoint": self.fake.vlm, "window": 1}},
            {"rerank": {"clusters": "../x", "endpoint": self.fake.vlm}},
            {"rerank": {"clusters": EMBEDDING, "endpoint": "{env:CASCADE_TEST_UNSET}"}},
            {"whole_image": "no"},
        ]
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(ConfigError):
                self.load(entry(self.catalog, self.fake, **changes))
        with self.assertRaisesRegex(ConfigError, "auto runs SAM3"):
            self.load(entry(self.catalog, self.fake,
                            barcode={"endpoint": self.fake.scanner, "engine": "auto"}))

    def test_fast_answer_rules(self):
        for fast in ({"answer_at_seconds": 3.0, "timeout_seconds": 3.0},
                     {"answer_at_seconds": True}, {"timeout_seconds": 0},
                     {"enabled": "yes"}, "on"):
            with self.subTest(fast=fast), self.assertRaises(ConfigError):
                self.load(entry(self.catalog, self.fake), fast)
        siglip2 = {"name": PIPELINE, "backend": "siglip2", "catalog": str(self.catalog),
                   "embedding": EMBEDDING, "endpoint": self.fake.siglip2}
        with self.assertRaisesRegex(ConfigError, "fast_answer requires"):
            self.load(siglip2, {"answer_at_seconds": 2.9})

    def test_crop_scans_need_sam3_and_the_data_must_exist(self):
        pipeline = entry(self.catalog, self.fake)
        del pipeline["sam3"]
        with self.assertRaisesRegex(ConfigError, "crops requires sam3"):
            self.load(pipeline)
        bare = write_cascade_catalog(self.root / "bare", codes=False, rule_files=False)
        with self.assertRaisesRegex(ConfigError, "rerank"):
            self.load(entry(bare, self.fake))
        pipeline = entry(bare, self.fake)
        del pipeline["rerank"]
        with self.assertRaisesRegex(ConfigError, "codes"):
            self.load(pipeline)

    def test_group_matching_uses_the_group_embedding(self):
        matcher = self.load(entry(self.catalog, self.fake, group_embedding=EMBEDDING))
        with mock.patch.object(type(matcher.group), "match_group_many",
                               return_value=[[("wine-a", 0.9)]]) as group:
            self.assertEqual(matcher.match_group_many([b"x"], [b"y"], 3), [[("wine-a", 0.9)]])
        group.assert_called_once()

    def test_group_matching_needs_the_view_label_of_the_group_embedding(self):
        self.assertTrue(self.load(entry(self.catalog, self.fake)).can_match_group)
        full_only = write_catalog(self.root / "full-only",
                                  rows=tuple(row for row in ROWS if row[0] != "label"))
        matcher = self.load(entry(full_only, self.fake, barcode=None, rerank=None))
        self.assertFalse(matcher.can_match_group)


class CascadeEndpointTest(unittest.TestCase):
    def start(self, fast_answer=None, **changes):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        self.fake = FakeServices()
        self.addCleanup(self.fake.close)
        catalog = write_cascade_catalog(root / "catalog")
        self.requests_dir = root / "requests"
        config = write_config(root / "config.yaml", entry(catalog, self.fake, **changes),
                              fast_answer, self.requests_dir)
        environment = dict(os.environ, SVOE_VINO_MATCHER_CONFIG=str(config))
        environment.pop("SVOE_VINO_MATCHER_TOKEN", None)
        port = free_port()
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "matcher.app:app",
             "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
            cwd=ROOT, env=environment, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True)
        self.addCleanup(test_siglip2.Siglip2HarnessTest.stop, process)
        wait_for_server(process, port)
        return port

    def request(self, port, method, path, body=None, headers=None, timeout=15):
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def post(self, port, path, body=None):
        payload, content_type = multipart(body or photo())
        return self.request(port, "POST", path, payload, {"Content-Type": content_type})

    def records(self):
        return [json.loads(path.read_text(encoding="utf-8"))
                for path in sorted(self.requests_dir.rglob("request.json"))]

    def test_predict_answers_and_the_audit_holds_the_decision(self):
        port = self.start({"answer_at_seconds": 2.0, "timeout_seconds": 5.0}, rerank=None)
        status, answer = self.post(port, "/v1/eval/predict")
        self.assertEqual((status, answer), (200, {"slug": "wine-a"}))
        response = self.records()[-1]["response"]
        self.assertEqual(response["decision"]["source"], "crop")
        self.assertEqual(response["decision"]["reason"], "done")
        self.assertIn("scan_full", [stage["id"] for stage in response["stages"]])

    def test_the_time_budget_counts_from_the_request_headers(self):
        port = self.start({"answer_at_seconds": 1.0, "timeout_seconds": 5.0}, rerank=None)
        self.fake.delays["segment"] = 5.0
        payload, content_type = multipart(photo())
        head = ("POST /v1/eval/predict HTTP/1.1\r\nHost: 127.0.0.1\r\n"
                "Content-Type: %s\r\nContent-Length: %d\r\nConnection: close\r\n\r\n"
                % (content_type, len(payload))).encode("ascii")
        with socket.create_connection(("127.0.0.1", port), timeout=10) as client:
            started = time.monotonic()
            client.sendall(head + payload[:len(payload) // 2])
            time.sleep(0.5)
            client.sendall(payload[len(payload) // 2:])
            answer = b""
            while True:
                chunk = client.recv(65536)
                if not chunk:
                    break
                answer += chunk
            elapsed = time.monotonic() - started
        self.assertIn(b"200 OK", answer.split(b"\r\n", 1)[0])
        self.assertTrue(answer.endswith(b'{"slug":"wine-b"}'), answer[-80:])
        # The upload took 0.5 s. A timer that started after the upload would answer at
        # 1.5 s; the timer of the headers answers at 1.0 s.
        self.assertGreaterEqual(elapsed, 0.95)
        self.assertLess(elapsed, 1.35)
        self.assertEqual(self.records()[-1]["response"]["decision"]["reason"], "answer_at")

    def test_match_returns_cards_and_non_increasing_scores(self):
        port = self.start(rerank=None)
        status, answer = self.post(port, "/v1/match?k=3")
        self.assertEqual(status, 200, answer)
        self.assertEqual(answer["pipeline"], PIPELINE)
        candidates = answer["candidates"]
        self.assertEqual([candidate["rank"] for candidate in candidates], [1, 2, 3])
        self.assertEqual(candidates[0]["slug"], "wine-a")
        scores = [candidate["score"] for candidate in candidates]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertTrue(all(candidate["wine"]["name"] for candidate in candidates))

    def test_a_full_photo_code_answers_both_endpoints(self):
        port = self.start({"answer_at_seconds": 2.0, "timeout_seconds": 5.0}, rerank=None)
        self.fake.scan = lambda image: [{"text": EAN_FULL, "format": "EAN-13"}]
        self.assertEqual(self.post(port, "/v1/eval/predict"), (200, {"slug": "wine-b"}))
        status, answer = self.post(port, "/v1/match?k=2")
        self.assertEqual([(c["slug"], c["score"]) for c in answer["candidates"]][0],
                         ("wine-b", 1.0))

    def test_readiness_checks_the_services(self):
        port = self.start(rerank=None)
        self.assertEqual(self.request(port, "GET", "/readyz"),
                         (200, {"status": "ok", "pipeline": PIPELINE}))
        self.fake.statuses["health"] = 503
        status, answer = self.request(port, "GET", "/readyz")
        self.assertEqual(status, 503)
        # The checks run in parallel; the first failure answers.
        self.assertIn(answer["detail"], ("SAM3 service returned HTTP 503",
                                         "QR scanner returned HTTP 503"))

    def test_a_service_failure_gives_its_status(self):
        port = self.start(rerank=None, sam3=None, barcode=None)
        self.fake.statuses["embed"] = 500
        status, answer = self.post(port, "/v1/eval/predict")
        self.assertEqual((status, answer), (502, {"detail": "SigLIP2 service returned HTTP 500"}))
        self.assertEqual(self.records()[-1]["response"]["status_code"], 502)


if __name__ == "__main__":
    unittest.main()
