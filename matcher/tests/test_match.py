"""Tests for the ranked endpoint /v1/match and the wine cards of a version 2 bundle."""

import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
import yaml

from matcher.bundle import infer_sugar, load_bundle
from matcher.service import load_matcher
import test_siglip2
from test_siglip2 import (
    FakeSiglip2, ROWS, damaged_jpeg, file_record, free_port, unit, wait_for_server,
    write_bundle, write_jsonl,
)


ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).resolve().parent / "data"
KNOWN_IMAGE = DATA / "02eef911.webp"
KNOWN_SHA256 = hashlib.sha256(KNOWN_IMAGE.read_bytes()).hexdigest()
TOKEN = "matcher-match-test-token"


def card(slug):
    return {
        "wine_slug": slug, "name": "Name %s полусладкое" % slug,
        "producer": "Producer %s" % slug, "category": "Белое", "region": "Крым",
        "color": "соломенный", "grapes": None,
        "page_url": "https://vino-svoe.ru/wines/%s" % slug,
        "image_url": "https://api.vino-svoe.ru/uploads/%s.webp" % slug,
        "qr_urls": ["https://example.com/%s" % slug],
    }


def write_bundle_v2(root, rows=ROWS, without=()):
    """Write a version 2 bundle. `without` names slugs that get no card."""
    write_bundle(root, rows)
    slugs = sorted({slug for _, _, owners in rows for slug in owners})
    write_jsonl(root / "wines.jsonl", [card(slug) for slug in slugs if slug not in without])
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["format_version"] = 2
    manifest["files"]["wines.jsonl"] = file_record(root / "wines.jsonl")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def write_config(path, pipeline, token=False):
    matcher = {"pipeline": pipeline["name"], "output_dir": str(path.parent / "requests")}
    if token:
        matcher["token"] = "{env:SVOE_VINO_MATCHER_TOKEN}"
    path.write_text(yaml.safe_dump({"matcher": matcher, "pipeline": [pipeline]}),
                    encoding="utf-8")
    return path


class RankedBundleTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)

    def test_the_first_ranked_wine_is_the_top1_wine(self):
        write_bundle(self.directory / "bundle")
        bundle = load_bundle(self.directory / "bundle")
        for vector in ((1, 0, 0, 0), (0.1, 0.5, 0.9, 0), (0, 0, 0, 1), (0.3, 0.3, 0, 0.3)):
            with self.subTest(vector=vector):
                query = unit(vector)
                ranked = bundle.ranked("full", query)
                self.assertEqual(ranked[0][0], bundle.top1("full", query)[0])
                self.assertAlmostEqual(ranked[0][1], bundle.top1("full", query)[1])

    def test_ranked_wines_are_unique_in_score_order_and_ties_go_to_the_smallest_slug(self):
        write_bundle(self.directory / "bundle")
        bundle = load_bundle(self.directory / "bundle")
        ranked = bundle.ranked("full", unit((0, 0, 0, 1)))
        slugs = [slug for slug, _ in ranked]
        scores = [score for _, score in ranked]
        self.assertEqual(slugs[:2], ["wine-shared-a", "wine-shared-b"])
        self.assertEqual(len(slugs), len(set(slugs)))
        self.assertEqual(scores, sorted(scores, reverse=True))
        # `wine-c` has only a label vector. The view `full` does not rank it.
        self.assertNotIn("wine-c", slugs)
        self.assertEqual(len(slugs), 4)

    def test_a_version_1_bundle_has_no_cards(self):
        write_bundle(self.directory / "bundle")
        self.assertIsNone(load_bundle(self.directory / "bundle").cards)

    def test_a_version_2_bundle_gives_cards_with_the_inferred_sugar(self):
        write_bundle_v2(self.directory / "bundle")
        cards = load_bundle(self.directory / "bundle").cards
        self.assertEqual(set(cards), {"wine-a", "wine-b", "wine-c", "wine-shared-a",
                                      "wine-shared-b"})
        self.assertEqual(cards["wine-a"], {
            "name": "Name wine-a полусладкое", "page_url": "https://vino-svoe.ru/wines/wine-a",
            "producer": "Producer wine-a", "category": "Белое", "region": "Крым",
            "color": "соломенный", "grapes": None,
            "image_url": "https://api.vino-svoe.ru/uploads/wine-a.webp",
            "qr_urls": ["https://example.com/wine-a"], "sugar": "Полусладкое",
        })

    def test_a_changed_wines_file_is_rejected(self):
        write_bundle_v2(self.directory / "bundle")
        with open(self.directory / "bundle" / "wines.jsonl", "a", encoding="utf-8") as target:
            target.write("\n")
        with self.assertRaisesRegex(ValueError, "wines.jsonl does not match"):
            load_bundle(self.directory / "bundle")

    def test_the_sugar_rules_match_the_bot_rules(self):
        for slug, name, expected in (
                ("abrau-extra-brut", "Абрау", "Экстра-брют"),
                ("x", "Игристое экстра брют", "Экстра-брют"),
                ("kokur-polusuhoe", "Кокур", "Полусухое"),
                ("x", "Мускат полусладкое", "Полусладкое"),
                ("spumante-bryut", "Спуманте", "Брют"),
                ("kokur-suhoe-2025", "Кокур", "Сухое"),
                ("x", "Мускат белый сладкое", "Сладкое"),
                ("x", "Пино Нуар", None)):
            with self.subTest(slug=slug, name=name):
                self.assertEqual(infer_sugar(slug, name), expected)


class RankedMatcherTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)

    def mock(self, answers=None, bundle=True):
        pipeline = {"name": "match-mock", "backend": "mock",
                    "answers": answers or {KNOWN_SHA256: "wine-b"}}
        if bundle:
            write_bundle_v2(self.directory / "bundle", without=("wine-shared-b",))
            pipeline["bundle"] = str(self.directory / "bundle")
        return load_matcher(write_config(self.directory / "config.yaml", pipeline))

    def assert_ranked(self, ranked):
        slugs = [slug for slug, _ in ranked]
        scores = [score for _, score in ranked]
        self.assertEqual(len(slugs), len(set(slugs)))
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_a_known_mock_image_gives_its_slug_first_and_random_other_wines(self):
        matcher = self.mock()
        ranked = matcher.match(KNOWN_IMAGE.read_bytes(), 3)
        self.assertEqual(ranked[0], ("wine-b", 1.0))
        self.assertEqual(len(ranked), 3)
        self.assert_ranked(ranked)
        self.assertTrue(all(0 <= score < 1 for _, score in ranked[1:]))
        self.assertTrue(set(slug for slug, _ in ranked) <= set(matcher.cards))

    def test_an_unknown_mock_image_gives_all_wines_with_a_card_up_to_k(self):
        matcher = self.mock()
        ranked = matcher.match(b"unknown image", 20)
        self.assertEqual({slug for slug, _ in ranked}, set(matcher.cards))
        self.assertEqual(len(ranked), 4)
        self.assert_ranked(ranked)
        self.assertEqual(len(matcher.match(b"unknown image", 1)), 1)

    def test_a_known_mock_slug_without_a_card_is_skipped(self):
        matcher = self.mock({KNOWN_SHA256: "wine-shared-b"})
        ranked = matcher.match(KNOWN_IMAGE.read_bytes(), 20)
        self.assertNotIn("wine-shared-b", [slug for slug, _ in ranked])
        self.assertEqual(len(ranked), 4)
        self.assertTrue(all(score < 1 for _, score in ranked))

    def test_a_mock_pipeline_without_a_bundle_has_no_cards(self):
        self.assertIsNone(self.mock(bundle=False).cards)

    def test_siglip2_match_ranks_the_full_view_and_skips_a_wine_without_a_card(self):
        write_bundle_v2(self.directory / "bundle", without=("wine-shared-a",))
        fake = FakeSiglip2((0.2, 0.1, 0, 1))
        self.addCleanup(fake.close)
        matcher = load_matcher(write_config(self.directory / "config.yaml", {
            "name": "match-siglip2", "backend": "siglip2",
            "bundle": str(self.directory / "bundle"), "endpoint": fake.url}))
        photo = KNOWN_IMAGE.read_bytes()
        ranked = matcher.match(photo, 20)
        self.assertEqual([slug for slug, _ in ranked], ["wine-shared-b", "wine-a", "wine-b"])
        self.assert_ranked(ranked)
        vector = unit((0.2, 0.1, 0, 1))
        self.assertAlmostEqual(ranked[0][1], float(np.dot(unit((0, 0, 0, 1)), vector)), 6)
        self.assertEqual([slug for slug, _ in matcher.match(photo, 2)],
                         ["wine-shared-b", "wine-a"])
        # `predict` keeps the Top-1 answer of the bundle, with or without a card.
        self.assertEqual(matcher.predict(photo), "wine-shared-a")

    def test_siglip2_matches_multiple_images_in_one_embedding_request(self):
        write_bundle_v2(self.directory / "bundle")
        fake = FakeSiglip2((1, 0, 0, 0))
        self.addCleanup(fake.close)
        matcher = load_matcher(write_config(self.directory / "config.yaml", {
            "name": "match-siglip2", "backend": "siglip2",
            "bundle": str(self.directory / "bundle"), "endpoint": fake.url}))
        ranked = matcher.match_many([KNOWN_IMAGE.read_bytes(), KNOWN_IMAGE.read_bytes()], 1)
        self.assertEqual([[pair[0] for pair in group] for group in ranked],
                         [["wine-a"], ["wine-a"]])
        self.assertEqual(len(fake.requests), 1)
        self.assertEqual(len(fake.requests[0][1]["input"]), 2)

    def test_group_matching_embeds_bottles_and_labels_in_one_request(self):
        rows = (
            ("full", (1, 0, 0, 0), ("wine-a",)),
            ("full", (0, 1, 0, 0), ("wine-b",)),
            ("label", (1, 0, 0, 0), ("wine-a",)),
            ("label", (0, 1, 0, 0), ("wine-b",)),
        )
        write_bundle_v2(self.directory / "bundle", rows=rows)
        fake = FakeSiglip2((1, 0, 0, 0))
        self.addCleanup(fake.close)
        matcher = load_matcher(write_config(self.directory / "config.yaml", {
            "name": "match-siglip2", "backend": "siglip2",
            "bundle": str(self.directory / "bundle"), "endpoint": fake.url}))
        photo = KNOWN_IMAGE.read_bytes()
        ranked = matcher.match_group_many([photo, photo], [photo, photo], 3)
        self.assertEqual([group[0][0] for group in ranked], ["wine-a", "wine-a"])
        self.assertEqual(len(fake.requests), 1)
        self.assertEqual(len(fake.requests[0][1]["input"]), 4)

    def test_group_matching_rejects_an_ambiguous_two_view_result(self):
        def vector(score):
            return (score, math.sqrt(1 - score * score), 0, 0)

        rows = (
            ("full", vector(0.90), ("wine-a",)),
            ("full", vector(0.89), ("wine-b",)),
            ("full", (0, 1, 0, 0), ("wine-c",)),
            ("label", vector(0.88), ("wine-a",)),
            ("label", vector(0.87), ("wine-b",)),
            ("label", (0, 1, 0, 0), ("wine-c",)),
        )
        write_bundle_v2(self.directory / "bundle", rows=rows)
        fake = FakeSiglip2((1, 0, 0, 0))
        self.addCleanup(fake.close)
        matcher = load_matcher(write_config(self.directory / "config.yaml", {
            "name": "match-siglip2", "backend": "siglip2",
            "bundle": str(self.directory / "bundle"), "endpoint": fake.url}))
        self.assertEqual(matcher._rank_group(unit((1, 0, 0, 0)),
                                             unit((1, 0, 0, 0)), 3), [])
        self.assertEqual(matcher._rank_group(unit((0, 1, 0, 0)),
                                             unit((0, 1, 0, 0)), 3)[0][0],
                         "wine-c")


def multipart(body, boundary="matcher-match-test"):
    return ("--%s\r\nContent-Disposition: form-data; name=\"image\"; filename=\"photo.webp\""
            "\r\nContent-Type: image/webp\r\n\r\n" % boundary).encode() + body + (
            "\r\n--%s--\r\n" % boundary).encode(), "multipart/form-data; boundary=%s" % boundary


class MatchEndpointTest(unittest.TestCase):
    """Run the API with a mock pipeline, a version 2 bundle, and a bearer token."""

    def start(self, pipeline, token=False):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        if pipeline.get("bundle") is True:
            write_bundle_v2(root / "bundle")
            pipeline["bundle"] = str(root / "bundle")
        config = write_config(root / "config.yaml", pipeline, token)
        environment = os.environ.copy()
        environment["SVOE_VINO_MATCHER_CONFIG"] = str(config)
        environment["SVOE_VINO_MATCHER_TOKEN"] = TOKEN
        port = free_port()
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "matcher.app:app",
             "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
            cwd=ROOT, env=environment, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True)
        self.addCleanup(test_siglip2.Siglip2HarnessTest.stop, process)
        wait_for_server(process, port)
        return port, root

    def post(self, port, query="", body=None, token=TOKEN, path="/v1/match"):
        payload, content_type = multipart(
            KNOWN_IMAGE.read_bytes() if body is None else body)
        headers = {"Content-Type": content_type}
        if token:
            headers["Authorization"] = "Bearer %s" % token
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        try:
            connection.request("POST", path + query, body=payload, headers=headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read() or b"null")
        finally:
            connection.close()

    def test_match_returns_ranked_candidates_with_cards(self):
        port, root = self.start({"name": "match-mock", "backend": "mock",
                                 "answers": {KNOWN_SHA256: "wine-b"}, "bundle": True},
                                token=True)
        status, answer = self.post(port)
        self.assertEqual(status, 200, answer)
        self.assertEqual(set(answer), {"pipeline", "latency_ms", "candidates"})
        self.assertEqual(answer["pipeline"], "match-mock")
        self.assertGreaterEqual(answer["latency_ms"], 0)
        candidates = answer["candidates"]
        self.assertEqual([row["rank"] for row in candidates], [1, 2, 3, 4, 5])
        self.assertEqual((candidates[0]["slug"], candidates[0]["score"]), ("wine-b", 1.0))
        expected = dict(card("wine-b"), sugar="Полусладкое")
        del expected["wine_slug"]
        self.assertEqual(candidates[0]["wine"], expected)
        scores = [row["score"] for row in candidates]
        self.assertEqual(scores, sorted(scores, reverse=True))

        status, answer = self.post(port, "?k=2")
        self.assertEqual(status, 200, answer)
        self.assertEqual(len(answer["candidates"]), 2)
        for query in ("?k=0", "?k=21", "?k=x"):
            with self.subTest(query=query):
                self.assertEqual(self.post(port, query)[0], 422)
        # The middleware answers 401 before it reads the body. A small body avoids a
        # broken pipe in the client.
        self.assertEqual(self.post(port, body=b"x", token=None)[0], 401)
        self.assertEqual(self.post(port, body=b"")[0], 400)

        records = [json.loads(path.read_text(encoding="utf-8"))
                   for path in (root / "requests").rglob("request.json")]
        matched = [record["response"] for record in records
                   if record["response"]["status_code"] == 200]
        self.assertEqual(len(matched), 2)
        self.assertTrue(all(response["candidates"][0] == "wine-b" for response in matched))

    def test_a_pipeline_without_cards_answers_503(self):
        port, _ = self.start({"name": "match-mock", "backend": "mock", "answers": {}})
        status, answer = self.post(port, token=None)
        self.assertEqual(status, 503)
        self.assertIn("format version 2", answer["detail"])

    def test_a_damaged_jpeg_answers_422_on_both_single_image_endpoints(self):
        fake = FakeSiglip2(unit((1, 0, 0, 0)))
        self.addCleanup(fake.close)
        port, root = self.start({"name": "match-siglip2", "backend": "siglip2",
                                 "bundle": True, "endpoint": fake.url})
        for endpoint in ("/v1/eval/predict", "/v1/match"):
            with self.subTest(endpoint=endpoint):
                status, answer = self.post(port, body=damaged_jpeg(), token=None,
                                           path=endpoint)
                self.assertEqual(status, 422, answer)
                self.assertEqual(answer, {"detail": "image file is invalid or damaged"})
        self.assertEqual(fake.requests, [])

        records = [json.loads(path.read_text(encoding="utf-8"))
                   for path in (root / "requests").rglob("request.json")]
        self.assertEqual(sorted(record["request"]["path"] for record in records),
                         ["/v1/eval/predict", "/v1/match"])
        for record in records:
            self.assertEqual(record["response"],
                             {"status_code": 422, "error_type": "ImageRejected"})


if __name__ == "__main__":
    unittest.main()
