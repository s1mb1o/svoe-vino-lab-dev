"""Public YAML, secret isolation and runtime wiring contracts."""
import base64
import copy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml
from fastapi.testclient import TestClient
from PIL import Image

from dinner_lens.paths import bundle_root
from dinner_lens.api import app_from_environment, create_app
from dinner_lens.configuration import ConfigError, asset_path, load_config, RecognitionSettings, EmbeddingSettings
from dinner_lens.data import Knowledge
from dinner_lens.embeddings import EmbeddingIndex, request_vectors
from dinner_lens.engine import Engine, PipelineError
from dinner_lens.provider import QwenRecognizer

ROOT = Path(__file__).resolve().parents[1]
TOKEN = 'configuration-test-only-token-at-least-24'
SECRET = 'configuration-test-only-secret-at-least-32'


class ConfigurationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = yaml.safe_load((ROOT / 'config.yaml').read_text())
        cls.knowledge = Knowledge(ROOT / 'data/pairing-dataset.v4.json', ROOT / 'prompts/style-guidance.v2.en.json')
        cls.index = EmbeddingIndex(cls.knowledge, ROOT / 'data/index.v4')

    def config(self, document):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / 'config.yaml'
        path.write_text(yaml.safe_dump(document))
        return path

    def test_default_configuration_and_relative_paths(self):
        config, path = load_config(ROOT / 'config.yaml')
        self.assertEqual(config.recognition.model, 'qwen3.8-flash')
        self.assertEqual(config.embeddings.dimensions, 1024)
        self.assertEqual(asset_path('relative/index', path), ROOT / 'relative/index')
        self.assertEqual(asset_path(config.assets.dataset, path), bundle_root() / 'data/pairing-dataset.v4.json')

    def test_invalid_settings_fail_without_echoing_inputs(self):
        cases = [('server', 'port', True), ('limits', 'recognition_concurrency', 0),
                 ('limits', 'recognition_queue_seconds', float('nan')),
                 ('limits', 'cursor_ttl_seconds', '3600'), ('recognition', 'attempts', 0),
                 ('recognition', 'endpoint', 'https://user:misplaced-secret@example.org/v1'),
                 ('recognition', 'endpoint', 'https://example.org/v1?key=misplaced-secret'),
                 ('recognition', 'api_key_env', 'misplaced-secret'),
                 ('auth', 'api_token', 'misplaced-secret')]
        for section, field, value in cases:
            document = copy.deepcopy(self.document)
            document[section][field] = value
            with self.subTest(section=section, field=field):
                with self.assertRaises(ConfigError) as raised:
                    load_config(self.config(document))
                self.assertNotIn('misplaced-secret', str(raised.exception))

    def test_yaml_parse_error_does_not_echo_secret(self):
        path = self.config({})
        path.write_text('auth: [misplaced-secret')
        with self.assertRaises(ConfigError) as raised:
            load_config(path)
        self.assertNotIn('misplaced-secret', str(raised.exception))

    def test_factory_uses_yaml_and_ignores_obsolete_public_environment(self):
        document = copy.deepcopy(self.document)
        document['assets']['index'] = str(ROOT / 'data/index.v4')
        document['limits'].update(max_request_bytes=2000, cursor_ttl_seconds=25)
        path = self.config(document)
        env = {'QWENCLOUD_PAYGO_API_KEY': 'unit-test-placeholder', 'DINNER_LENS_CONFIG': str(path), 'DINNER_LENS_API_TOKEN': TOKEN,
               'DINNER_LENS_CURSOR_SECRET': SECRET, 'DINNER_LENS_DATASET': '/missing',
               'DINNER_LENS_INDEX': '/missing', 'XDG_CACHE_HOME': '/missing'}
        with patch.dict(os.environ, env), TestClient(app_from_environment()) as client:
            self.assertEqual(client.get('/readyz').status_code, 200)
            self.assertEqual(client.post('/v1/recommendations', json={'node_id': 'meat'}).status_code, 401)
            client.headers['Authorization'] = 'Bearer ' + TOKEN
            self.assertEqual(client.post('/v1/recommendations', json={'node_id': 'meat'}).status_code, 200)
            self.assertEqual(client.post('/v1/recommendations', content=' ' * 2001).status_code, 413)

    def test_factory_requires_persistent_secret(self):
        with patch.dict(os.environ, {'DINNER_LENS_API_TOKEN': TOKEN}, clear=True):
            with self.assertRaisesRegex(ConfigError, 'DINNER_LENS_CURSOR_SECRET'):
                app_from_environment()

    def test_configured_cursor_expiry_and_restart(self):
        now = [1000]
        args = dict(cursor_secret=SECRET.encode(), cursor_ttl_seconds=5, clock=lambda: now[0])
        engine = Engine(self.knowledge, self.index, **args)
        first = engine.recommend(node_id='ribeye_grilled')
        restarted = Engine(self.knowledge, self.index, **args)
        self.assertTrue(restarted.more(first['next_cursor'])['results'])
        now[0] += 6
        with self.assertRaises(PipelineError):
            restarted.more(first['next_cursor'])

    def test_recognition_endpoint_model_and_generation_settings_reach_provider(self):
        settings = RecognitionSettings(endpoint='https://example.org/chat', model='configured-model',
                                       api_key_env='TEST_PROVIDER_KEY', max_tokens=500,
                                       socket_timeout_seconds=7.0, attempts=1)
        recognizer = QwenRecognizer(self.knowledge, ROOT / 'prompts/image-system.en.txt', settings=settings)
        image = io.BytesIO()
        Image.new('RGB', (10, 10)).save(image, format='JPEG')
        parsed = dict(visual_node_id='meat', hypothesis_node_id=None, observed_dish='reference data',
                      needs_clarification=True, clarification_question='Which meat?',
                      visible_attributes=[], uncertain_attributes=[])
        response = {'model': 'configured-model', 'choices': [{'message': {'content': json.dumps(parsed)}}]}
        def provider(req, timeout):
            self.assertEqual(req.full_url, settings.endpoint)
            self.assertEqual(timeout, 7.0)
            body = json.loads(req.data)
            self.assertEqual(body['model'], settings.model)
            self.assertEqual(body['max_tokens'], 500)
            return io.BytesIO(json.dumps(response).encode())
        with patch.dict(os.environ, {'TEST_PROVIDER_KEY': 'unit-test-placeholder'}), patch('urllib.request.urlopen', side_effect=provider):
            actual, meta = recognizer.recognize(image.getvalue())
        self.assertEqual(actual, parsed)
        self.assertEqual(meta['requested_model'], settings.model)

    def test_configured_embedding_model_dimension_and_endpoint(self):
        settings = EmbeddingSettings(endpoint='https://example.org/embed', model='configured-embedding',
                                     dimensions=2, api_key_env='TEST_EMBEDDING_KEY', attempts=1)
        response = {'model': settings.model, 'data': [{'index': 0, 'embedding': [3, 4]}]}
        def provider(req, timeout):
            self.assertEqual(req.full_url, settings.endpoint)
            self.assertEqual(json.loads(req.data)['dimensions'], 2)
            return io.BytesIO(json.dumps(response).encode())
        with patch.dict(os.environ, {'TEST_EMBEDDING_KEY': 'unit-test-placeholder'}), patch('urllib.request.urlopen', side_effect=provider):
            vectors, _ = request_vectors(['reference data'], settings=settings)
        self.assertAlmostEqual(float(vectors[0][0]), .6)
        with self.assertRaisesRegex(ValueError, 'configured embedding model'):
            EmbeddingIndex(self.knowledge, ROOT / 'data/index.v4', settings=settings)

    def test_configured_image_limit_is_enforced_before_provider(self):
        settings = RecognitionSettings(image={'max_bytes': 5})
        recognizer = QwenRecognizer(self.knowledge, ROOT / 'prompts/image-system.en.txt', settings=settings)
        with self.assertRaises(PipelineError), patch('urllib.request.urlopen') as provider:
            recognizer.recognize(b'too many bytes')
        provider.assert_not_called()

    def test_default_recognition_request_matches_frozen_baseline_bytes(self):
        import hashlib
        reference = json.loads((ROOT / 'tests/data/payload-reference.json').read_text())
        image = (ROOT / 'tests/data/payload-reference.png').read_bytes()
        self.assertEqual(hashlib.sha256(image).hexdigest(), reference['image_sha256'])
        self.assertEqual(self.knowledge.sha256, reference['dataset_sha256'])
        settings, path = load_config(ROOT / 'config.yaml')
        recognizer = QwenRecognizer(self.knowledge, asset_path(settings.recognition.prompt, path), settings=settings.recognition)
        payload = recognizer.payload(image)
        sent = base64.b64decode(payload['messages'][1]['content'][0]['image_url']['url'].split(',', 1)[1])
        variants = {v['sent_image_sha256']: v['baseline_request_sha256'] for v in reference['preprocessor_variants']}
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.assertEqual(hashlib.sha256(body).hexdigest(), variants[hashlib.sha256(sent).hexdigest()])

    def test_cli_serve_uses_yaml_listener_workers_and_logging(self):
        from dinner_lens.cli import main
        document = copy.deepcopy(self.document)
        document['server'].update(host='192.0.2.1', port=10001, workers=2, log_level='warning', access_log=False)
        path = self.config(document)
        with patch.dict(os.environ, {}, clear=True), patch('sys.argv', ['dinner-lens', '--config', str(path), 'serve']), patch('uvicorn.run') as run:
            main()
        run.assert_called_once_with('dinner_lens.api:app_from_environment', factory=True,
                                    host='192.0.2.1', port=10001, workers=2, log_level='warning', access_log=False)
