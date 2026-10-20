"""Exercise the configured rejection floor through real ranking and HTTP."""

import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
import yaml

from matcher.service import load_matcher
from test_match import KNOWN_IMAGE, write_bundle_v2, write_config
from test_siglip2 import FakeSiglip2


class MinimumScoreTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        write_bundle_v2(self.root / 'bundle')
        self.fake = FakeSiglip2((0.69, 0, math.sqrt(1 - 0.69 ** 2), 0))
        self.addCleanup(self.fake.close)
        self.path = write_config(self.root / 'config.yaml', {
            'name': 'threshold-test', 'backend': 'siglip2',
            'bundle': str(self.root / 'bundle'), 'endpoint': self.fake.url})

    def set_floor(self, value):
        document = yaml.safe_load(self.path.read_text())
        document['matcher']['min_score'] = value
        self.path.write_text(yaml.safe_dump(document))

    def test_default_rejects_low_score_but_group_batch_ranking_is_unchanged(self):
        matcher = load_matcher(self.path)
        body = KNOWN_IMAGE.read_bytes()
        self.assertEqual(matcher.min_score, 0.7)
        self.assertEqual(matcher.predict(body), '')
        self.assertEqual(matcher.match(body, 3), [])
        self.assertEqual(matcher.match_many([body], 3)[0][0][0], 'wine-a')

    def test_yaml_override_and_equality_accept_the_same_image(self):
        body = KNOWN_IMAGE.read_bytes()
        raw = load_matcher(self.path).match_many([body], 3)[0]
        self.set_floor(raw[0][1])
        matcher = load_matcher(self.path)
        self.assertEqual(matcher.predict(body), 'wine-a')
        self.assertEqual(matcher.match(body, 3), raw)

    def test_http_predict_keeps_empty_slug_contract_and_match_returns_no_candidates(self):
        with patch.dict(os.environ, {'SVOE_VINO_MATCHER_CONFIG': str(self.path)}):
            from matcher.app import create_app
            app = create_app(self.path)
        with TestClient(app) as client:
            response = client.post('/v1/eval/predict', files={'image': ('wine.webp', KNOWN_IMAGE.read_bytes())})
            self.assertEqual((response.status_code, response.json()), (200, {'slug': ''}))
            response = client.post('/v1/match?k=3', files={'image': ('wine.webp', KNOWN_IMAGE.read_bytes())})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['candidates'], [])
            self.fake.vector = [0.71, 0, math.sqrt(1 - 0.71 ** 2), 0]
            response = client.post('/v1/eval/predict', files={'image': ('wine.webp', KNOWN_IMAGE.read_bytes())})
            self.assertEqual(response.json(), {'slug': 'wine-a'})
