"""Exercise YAML settings at parsing, service, and authenticated HTTP boundaries."""

from dataclasses import asdict
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml
from fastapi.testclient import TestClient

from matcher.configuration import (ConfigError, RuntimeSettings, endpoint_url,
                                   minimum_score, read_configuration, runtime_settings,
                                   sam3_endpoint)
from matcher.service import load_matcher
from matcher.tests.config_helpers import process_environment

TEMPLATE = Path(__file__).with_name('config.yaml')


class ConfigurationTest(unittest.TestCase):
    def test_min_score_defaults_to_point_seven_and_accepts_inclusive_limits(self):
        self.assertEqual(minimum_score({'matcher': {}}), 0.7)
        for value in (0, 0.7, 0.85, 1):
            self.assertEqual(minimum_score({'matcher': {'min_score': value}}), value)

    def test_invalid_min_score_stops_loading(self):
        for value in (None, True, False, '0.7', -0.1, 1.1, float('nan'),
                      float('inf'), 10 ** 1000, [], {}):
            document = yaml.safe_load(TEMPLATE.read_text())
            document['matcher']['min_score'] = value
            with self.subTest(value=value), self.assertRaisesRegex(ConfigError, 'matcher.min_score'):
                load_matcher(TEMPLATE, document=document)

    def test_subprocess_fixtures_remove_an_ambient_sam3_endpoint(self):
        with patch.dict(os.environ, {'SAM3_ENDPOINT': 'http://ambient.invalid'}):
            environment = process_environment(TEMPLATE)
        self.assertNotIn('SAM3_ENDPOINT', environment)

    def test_canonical_sam3_environment_overrides_the_yaml_fallback(self):
        document = {'matcher': {'sam3_endpoint': 'http://yaml.test'}}
        with patch.dict(os.environ, {'SAM3_ENDPOINT': 'http://canonical.test'}):
            self.assertEqual(sam3_endpoint(document), 'http://canonical.test')
            self.assertEqual(sam3_endpoint({'matcher': {}}), 'http://canonical.test')
        with patch.dict(os.environ):
            os.environ.pop('SAM3_ENDPOINT', None)
            self.assertEqual(sam3_endpoint(document), 'http://yaml.test')
            self.assertIsNone(sam3_endpoint({'matcher': {}}))

    def test_invalid_canonical_sam3_environment_does_not_use_the_yaml_fallback(self):
        for value in ('', 'ftp://invalid.test', 'http://user:private@host'):
            with self.subTest(value=value), patch.dict(os.environ, {'SAM3_ENDPOINT': value}):
                with self.assertRaises(ConfigError) as caught:
                    sam3_endpoint({'matcher': {'sam3_endpoint': 'http://yaml.test'}})
                self.assertNotIn('private', str(caught.exception))

    def test_defaults_keep_the_existing_service_limits(self):
        self.assertEqual(asdict(runtime_settings({'matcher': {}})), {
            'max_image_bytes': 20971520, 'max_image_pixels': 40000000,
            'upload_timeout_seconds': 30., 'max_inflight_requests': 8,
            'max_queued_requests': 16, 'queue_timeout_seconds': .25})

    def test_each_limit_rejects_invalid_values(self):
        for key, default in asdict(RuntimeSettings()).items():
            invalid = [False, True, None, '', '12', -1, 0, float('nan'), float('inf')]
            if type(default) is int:
                invalid.append(1.5)
            for value in invalid:
                with self.subTest(key=key, value=value), self.assertRaises(ConfigError):
                    runtime_settings({'matcher': {'limits': {key: value}}})

    def test_unknown_or_malformed_limits_fail_at_startup(self):
        for limits in [None, [], 'limits', {'max_inflight_request': 3}]:
            with self.subTest(limits=limits), self.assertRaises(ConfigError):
                runtime_settings({'matcher': {'limits': limits}})

    def test_endpoint_errors_do_not_disclose_values(self):
        for value in ['{env:SECRET}', 'http://user:secret@host', 'http://[broken',
                      'http://host:bad', 'http://', 'http://host\n',
                      'http://host?api_key=secret', 'http://host#fragment', 3]:
            with self.subTest(value=value), self.assertRaises(ConfigError) as caught:
                endpoint_url(value, 'model.endpoint')
            self.assertNotIn('secret', str(caught.exception))

    def test_yaml_parser_errors_do_not_disclose_source_excerpts(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'config.yaml'
            path.write_text('matcher: [private-secret\n')
            with self.assertRaises(ConfigError) as caught:
                read_configuration(path)
            self.assertNotIn('private-secret', str(caught.exception))

    def test_yaml_controls_http_limits_and_environment_cannot_override_it(self):
        with tempfile.TemporaryDirectory() as directory:
            env = process_environment(TEMPLATE, output_dir=directory,
                                      limits={'max_image_bytes': 64, 'max_inflight_requests': 2})
            env.update(SVOE_VINO_MATCHER_MAX_IMAGE_BYTES='99999999')
            with patch.dict(os.environ, env, clear=True):
                from matcher.app import create_app
                app = create_app(env['SVOE_VINO_MATCHER_CONFIG'])
            self.assertEqual(app.state.runtime_settings.max_inflight_requests, 2)
            with TestClient(app) as client:
                response = client.post('/v1/eval/predict', files={'image': ('image.jpg', b'x'*65)})
            self.assertEqual(response.status_code, 413)

    def test_explicit_factory_overrides_are_validated(self):
        with self.assertRaises(ConfigError):
            RuntimeSettings().with_overrides(queue_timeout_seconds=float('nan'))

    def test_every_http_factory_override_uses_strict_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            env = process_environment(TEMPLATE, output_dir=directory)
            with patch.dict(os.environ, env, clear=True):
                from matcher.app import create_app
                for key in asdict(RuntimeSettings()):
                    for value in (0, '123', float('inf')):
                        with self.subTest(key=key, value=value), self.assertRaises(ConfigError):
                            create_app(env['SVOE_VINO_MATCHER_CONFIG'], **{key: value})

    def test_yaml_secret_reference_resolves_only_at_authentication_boundary(self):
        document = yaml.safe_load(TEMPLATE.read_text())
        document['matcher']['token'] = '{env:ONLY_TEST_TOKEN}'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'config.yaml'
            path.write_text(yaml.safe_dump(document))
            matcher = load_matcher(path)
            with self.assertRaises(ConfigError):
                matcher.resolved_token({})
            self.assertEqual(matcher.resolved_token({'ONLY_TEST_TOKEN': 'private-value'}),
                             'private-value')
            self.assertNotIn('private-value', path.read_text())
