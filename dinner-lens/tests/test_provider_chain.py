"""Local-first recognition and bounded cloud fallback without credential leakage."""
import base64
import io
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import urllib.error

from fastapi.testclient import TestClient
from PIL import Image
from dinner_lens.api import create_app
from dinner_lens.configuration import RecognitionSettings, ProviderSettings
from dinner_lens.data import Knowledge
from dinner_lens.embeddings import EmbeddingIndex
from dinner_lens.engine import Engine, PipelineError
from dinner_lens.provider import QwenRecognizer, ProviderFailure

ROOT = Path(__file__).resolve().parents[1]


class ProviderChainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.knowledge = Knowledge(ROOT/'data/pairing-dataset.v4.json', ROOT/'prompts/style-guidance.v2.en.json')
        cls.index = EmbeddingIndex(cls.knowledge, ROOT/'data/index.v4')
        image = io.BytesIO()
        Image.new('RGB', (10, 10)).save(image, format='PNG')
        cls.image = image.getvalue()

    def recognizer(self):
        settings = RecognitionSettings(endpoint='http://127.0.0.1:18081/v1/chat/completions',
            model='local-test-model', protocol='vllm', api_key_env=None, attempts=1,
            fallback=ProviderSettings(endpoint='https://example.org/chat', model='cloud-test-model',
                                      api_key_env='TEST_CLOUD_KEY', attempts=1))
        return QwenRecognizer(self.knowledge, ROOT/'prompts/image-system.en.txt', settings=settings)

    def response(self, model='local-test-model', **updates):
        parsed = dict(visual_node_id='crab', hypothesis_node_id=None, observed_dish='reference data',
                      needs_clarification=True, clarification_question='Which preparation?',
                      visible_attributes=[], uncertain_attributes=[])
        parsed.update(updates)
        return {'model': model, 'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(parsed)}}]}

    def test_local_success_does_not_call_cloud_or_send_cloud_key(self):
        requests = []
        def provider(request, timeout):
            requests.append(request)
            self.assertIsNone(request.get_header('Authorization'))
            payload = json.loads(request.data)
            self.assertEqual(payload['chat_template_kwargs'], {'enable_thinking': False})
            self.assertNotIn('enable_thinking', payload)
            return io.BytesIO(json.dumps(self.response()).encode())
        with patch.dict(os.environ, {'TEST_CLOUD_KEY': 'unit-test-placeholder'}), patch('urllib.request.urlopen', side_effect=provider):
            _, meta = self.recognizer().recognize(self.image)
        self.assertEqual(len(requests), 1)
        self.assertFalse(meta['fallback_used'])
        self.assertEqual(meta['selected_provider'], 'primary')

    def test_provider_failures_use_cloud_with_identical_pixels_and_instructions(self):
        failures = [urllib.error.URLError('test transport'),
            urllib.error.HTTPError('http://local',503,'unavailable',{},None),
            {'model':'wrong-model'}, [],
            {'model':'local-test-model','choices':[None]},
            self.response(visual_node_id='outside-taxonomy'),
            {'model':'local-test-model','choices':[{'finish_reason':'length','message':{'content':'{}'}}]},
            b'\xff invalid utf8']
        for failure in failures:
            requests = []
            def provider(request, timeout):
                requests.append(request)
                if len(requests) == 1:
                    self.assertIsNone(request.get_header('Authorization'))
                    if isinstance(failure, Exception): raise failure
                    return io.BytesIO(failure if isinstance(failure, bytes) else json.dumps(failure).encode())
                self.assertEqual(request.get_header('Authorization'), 'Bearer unit-test-placeholder')
                return io.BytesIO(json.dumps(self.response('cloud-test-model')).encode())
            with self.subTest(failure=type(failure).__name__), patch.dict(os.environ, {'TEST_CLOUD_KEY':'unit-test-placeholder'}), patch('urllib.request.urlopen', side_effect=provider):
                parsed, meta = self.recognizer().recognize(self.image)
            self.assertTrue(meta['fallback_used'])
            self.assertEqual(meta['returned_model'], 'cloud-test-model')
            self.assertEqual([p['status'] for p in meta['provider_attempts']], ['failed','ok'])
            a,b = [json.loads(r.data) for r in requests]
            self.assertEqual(a['messages'], b['messages'])
            self.assertFalse(b['enable_thinking'])
            self.assertNotIn('chat_template_kwargs', b)

    def test_valid_unknown_result_keeps_clarification_without_cloud_call(self):
        with patch('urllib.request.urlopen', return_value=io.BytesIO(json.dumps(self.response(visual_node_id=None)).encode())) as provider:
            parsed, meta = self.recognizer().recognize(self.image)
        self.assertEqual(provider.call_count,1)
        self.assertIsNone(parsed['visual_node_id'])
        self.assertFalse(meta['fallback_used'])

    def test_invalid_image_never_calls_either_provider(self):
        with patch('urllib.request.urlopen') as provider, self.assertRaises(PipelineError):
            self.recognizer().recognize(b'not an image')
        provider.assert_not_called()

    def test_all_failed_receipts_are_bounded_safe_error_codes(self):
        with patch.dict(os.environ, {'TEST_CLOUD_KEY':'unit-test-placeholder'}), patch('urllib.request.urlopen',side_effect=TimeoutError('secret text must not leak')):
            with self.assertRaises(ProviderFailure) as raised:
                self.recognizer().recognize(self.image)
        self.assertEqual(raised.exception.code,'all_providers_failed')
        self.assertEqual(len(raised.exception.provider_attempts),2)
        self.assertNotIn('secret text',json.dumps(raised.exception.provider_attempts))

    def test_fallback_still_uses_real_api_filters_and_continuation(self):
        token='chain-test-only-token-at-least-24-characters'
        engine=Engine(self.knowledge,self.index,cursor_secret=b'chain-test-only-cursor-secret-at-least-32-bytes')
        app=create_app(engine,self.recognizer(),api_token=token)
        replies=[TimeoutError(),io.BytesIO(json.dumps(self.response('cloud-test-model')).encode())]
        with patch.dict(os.environ, {'TEST_CLOUD_KEY':'unit-test-placeholder'}), patch('urllib.request.urlopen',side_effect=replies), TestClient(app) as client:
            client.headers['Authorization']='Bearer '+token
            response=client.post('/v1/recognize-and-recommend',json={'image_base64':base64.b64encode(self.image).decode()})
            self.assertEqual(response.status_code,200)
            first=page=response.json();slugs=[]
            self.assertTrue(first['llm']['fallback_used'])
            while True:
                slugs.extend(page['wine_slugs'])
                self.assertEqual(page['resolved_node_id'],'crab')
                if not page['next_cursor']:break
                page=client.post('/v1/recommendations/more',json={'cursor':page['next_cursor']}).json()
            self.assertEqual(len(slugs),first['total_eligible'])
            self.assertEqual(len(slugs),len(set(slugs)))

    def test_configured_response_model_alias_is_checked_exactly(self):
        recognizer=self.recognizer()
        recognizer.settings=recognizer.settings.model_copy(update={'response_model':'LOCAL-CANONICAL-ID'})
        with patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(self.response('LOCAL-CANONICAL-ID')).encode())) as provider:
            _,meta=recognizer.recognize(self.image)
        self.assertEqual(provider.call_count,1)
        self.assertEqual(meta['requested_model'],'local-test-model')
        self.assertEqual(meta['returned_model'],'LOCAL-CANONICAL-ID')
        self.assertFalse(meta['fallback_used'])

    def test_benchmark_handles_unknown_photo_and_text_without_a_profile(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('recognition_benchmark',ROOT/'scripts/benchmark_recognition.py')
        benchmark=importlib.util.module_from_spec(spec);spec.loader.exec_module(benchmark)
        class Unknown:
            def recognize(self, image):
                return {'visual_node_id':None,'hypothesis_node_id':None,'needs_clarification':True,
                        'clarification_question':'Which food category?'}, {'returned_model':'unit-test-only'}
        engine=Engine(self.knowledge,self.index,cursor_secret=b'benchmark-test-only-cursor-at-least-32-bytes')
        token='benchmark-test-only-token-at-least-24'
        with TestClient(create_app(engine,Unknown(),api_token=token)) as client:
            client.headers['Authorization']='Bearer '+token
            cases=[('/v1/recommendations',{'confirmed_dish':'unknown-food-test-fixture'}),
                   ('/v1/recognize-and-recommend',{'image_base64':base64.b64encode(self.image).decode()})]
            for endpoint,payload in cases:
                with self.subTest(endpoint=endpoint):
                    first,entries,pages,functional,status=benchmark.collect_pages(client,client.post(endpoint,json=payload))
                    self.assertEqual(status,200)
                    self.assertEqual(first['status'],'needs_category')
                    self.assertNotIn('effective_profile_id',first)
                    self.assertEqual(entries,[])
                    self.assertEqual(len(pages),1)
                    self.assertTrue(functional)

    def test_oversized_local_response_uses_separate_cloud_response_limit(self):
        recognizer=self.recognizer()
        recognizer.settings=recognizer.settings.model_copy(update={'max_response_bytes':5})
        replies=[io.BytesIO(b'oversized response'),io.BytesIO(json.dumps(self.response('cloud-test-model')).encode())]
        with patch.dict(os.environ, {'TEST_CLOUD_KEY':'unit-test-placeholder'}), patch('urllib.request.urlopen',side_effect=replies):
            _,meta=recognizer.recognize(self.image)
        self.assertTrue(meta['fallback_used'])
        self.assertEqual(meta['provider_attempts'][0]['error_code'],'response_too_large')

    def test_missing_cloud_credential_does_not_send_anonymous_fallback(self):
        with patch.dict(os.environ,{},clear=True), patch('urllib.request.urlopen',side_effect=TimeoutError()) as provider:
            with self.assertRaises(ProviderFailure) as raised:
                self.recognizer().recognize(self.image)
        self.assertEqual(provider.call_count,1)
        self.assertEqual(raised.exception.provider_attempts[-1]['error_code'],'credential_missing')

    def test_vllm_without_explicit_credential_reference_never_inherits_cloud_key(self):
        settings=RecognitionSettings(protocol='vllm',endpoint='http://127.0.0.1:18081/v1/chat/completions',model='local-test-model')
        self.assertIsNone(settings.api_key_env)
        recognizer=QwenRecognizer(self.knowledge,ROOT/'prompts/image-system.en.txt',settings=settings)
        def provider(request, timeout):
            self.assertIsNone(request.get_header('Authorization'))
            return io.BytesIO(json.dumps(self.response()).encode())
        with patch.dict(os.environ,{'QWENCLOUD_PAYGO_API_KEY':'unit-test-placeholder'}),patch('urllib.request.urlopen',side_effect=provider):
            _,meta=recognizer.recognize(self.image)
        self.assertFalse(meta['fallback_used'])
