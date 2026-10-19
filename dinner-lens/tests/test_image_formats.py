"""Direct photo uploads must normalize supported codecs before any model request."""
import base64
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

from dinner_lens.api import create_app
from dinner_lens.configuration import ImageSettings, RecognitionSettings
from dinner_lens.data import Knowledge
from dinner_lens.embeddings import EmbeddingIndex
from dinner_lens.engine import Engine, PipelineError
from dinner_lens.provider import QwenRecognizer, sanitize_image

ROOT = Path(__file__).resolve().parents[1]
TOKEN = 'image-format-test-token-at-least-24-characters'


def photo(format_name, mode='RGB', size=(32, 16), **options):
    output = io.BytesIO()
    color = (220, 30, 20, 96) if mode == 'RGBA' else (220, 30, 20)
    Image.new(mode, size, color).save(output, format=format_name, **options)
    return output.getvalue()


class ImageFormatTests(unittest.TestCase):
    def test_heic_and_webp_decode_to_metadata_free_jpeg(self):
        for format_name in ('HEIF', 'WEBP'):
            with self.subTest(format=format_name):
                exif = Image.Exif()
                exif[270] = 'Private caption and location'
                raw = photo(format_name, exif=exif.tobytes(), xmp=b'Private XMP caption')
                cleaned, mime = sanitize_image(raw)
                self.assertEqual(mime, 'image/jpeg')
                with Image.open(io.BytesIO(cleaned)) as image:
                    self.assertEqual(image.size, (32, 16))
                    self.assertGreater(image.getpixel((10, 10))[0], 180)
                    self.assertFalse(image.getexif())
                    self.assertNotIn('xmp', image.info)
                self.assertNotIn(b'Private', cleaned)

    def test_heic_native_orientation_and_webp_exif_orientation_apply_once(self):
        exif = Image.Exif()
        exif[274] = 6
        for format_name in ('HEIF', 'WEBP'):
            with self.subTest(format=format_name):
                cleaned, _ = sanitize_image(photo(format_name, exif=exif.tobytes()))
                with Image.open(io.BytesIO(cleaned)) as image:
                    self.assertEqual(image.size, (16, 32))
                    self.assertFalse(image.getexif())

    def test_transparent_heic_and_webp_preserve_alpha_as_png(self):
        for format_name in ('HEIF', 'WEBP'):
            with self.subTest(format=format_name):
                cleaned, mime = sanitize_image(photo(format_name, mode='RGBA', lossless=True))
                self.assertEqual(mime, 'image/png')
                with Image.open(io.BytesIO(cleaned)) as image:
                    self.assertEqual(image.mode, 'RGBA')
                    self.assertAlmostEqual(image.getpixel((10, 10))[3], 96, delta=2)

    def test_heif_selects_primary_image_even_when_not_first(self):
        output = io.BytesIO()
        Image.new('RGB', (32, 16), 'red').save(output, format='HEIF', save_all=True,
            append_images=[Image.new('RGB', (16, 32), 'blue')], primary_index=1)
        cleaned, _ = sanitize_image(output.getvalue())
        with Image.open(io.BytesIO(cleaned)) as image:
            self.assertEqual(image.size, (16, 32))
            self.assertGreater(image.getpixel((8, 8))[2], 200)

    def test_animated_webp_uses_first_frame(self):
        output = io.BytesIO()
        Image.new('RGB', (32, 16), 'red').save(output, format='WEBP', save_all=True,
            append_images=[Image.new('RGB', (32, 16), 'blue')], duration=100, loop=0)
        cleaned, _ = sanitize_image(output.getvalue())
        with Image.open(io.BytesIO(cleaned)) as image:
            self.assertEqual(getattr(image, 'n_frames', 1), 1)
            self.assertGreater(image.getpixel((8, 8))[0], 200)

    def test_new_formats_obey_pixel_and_input_byte_limits(self):
        for format_name in ('HEIF', 'WEBP'):
            raw = photo(format_name)
            with self.subTest(format=format_name):
                for settings in (ImageSettings(max_pixels=511), ImageSettings(max_bytes=len(raw)-1)):
                    with self.assertRaises(PipelineError):
                        sanitize_image(raw, settings)

    def test_new_formats_obey_resized_pixel_and_output_byte_limits(self):
        for format_name in ('HEIF', 'WEBP'):
            raw = photo(format_name, size=(512, 256))
            with self.subTest(format=format_name):
                cleaned, _ = sanitize_image(raw, ImageSettings(max_side=256, max_bytes=2048))
                self.assertLessEqual(len(cleaned), 2048)
                with Image.open(io.BytesIO(cleaned)) as image:
                    self.assertEqual(image.size, (256, 128))

    def test_corrupt_and_truncated_new_formats_are_input_errors(self):
        for format_name in ('HEIF', 'WEBP'):
            raw = photo(format_name)
            for broken in (raw[:24], raw[:len(raw)//2]):
                with self.subTest(format=format_name, length=len(broken)), self.assertRaises(PipelineError) as raised:
                    sanitize_image(broken)
                self.assertEqual(raised.exception.code, 'invalid_image')

    def test_unsupported_formats_remain_rejected(self):
        for raw in (photo('TIFF'), b'not an image', b''):
            with self.assertRaises(PipelineError):
                sanitize_image(raw)


class ImageFormatApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        knowledge = Knowledge(ROOT/'data/pairing-dataset.v4.json', ROOT/'prompts/style-guidance.v2.en.json')
        index = EmbeddingIndex(knowledge, ROOT/'data/index.v4')
        engine = Engine(knowledge, index, cursor_secret=b'image-format-test-cursor-secret-at-least-32-bytes')
        recognizer = QwenRecognizer(knowledge, ROOT/'prompts/image-system.en.txt',
            settings=RecognitionSettings(model='image-format-test-model', protocol='vllm', api_key_env=None, attempts=1))
        cls.app = create_app(engine, recognizer, api_token=TOKEN)
        cls.reply = json.dumps({'model': 'image-format-test-model', 'choices': [{'finish_reason': 'stop',
            'message': {'content': json.dumps(dict(visual_node_id='crab', hypothesis_node_id=None,
                observed_dish='reference data', needs_clarification=False, clarification_question=None,
                visible_attributes=[], uncertain_attributes=[]))}}]}).encode()

    def test_raw_base64_and_every_supported_data_url_reach_model_as_jpeg_or_png(self):
        with TestClient(self.app) as client:
            client.headers['Authorization'] = 'Bearer ' + TOKEN
            for format_name, mimes in (('HEIF', ('image/heic', 'image/heif')),
                                       ('WEBP', ('image/webp',)), ('JPEG', ('image/jpeg',)), ('PNG', ('image/png',))):
                encoded = base64.b64encode(photo(format_name)).decode()
                for prefix in ('', *(f'data:{mime};base64,' for mime in mimes)):
                    with self.subTest(format=format_name, prefix=prefix), patch('urllib.request.urlopen',
                            return_value=io.BytesIO(self.reply)) as provider:
                        response = client.post('/v1/recognize-and-recommend', json={'image_base64': prefix + encoded})
                        self.assertEqual(response.status_code, 200, response.text)
                        self.assertIn('results', response.json())
                        self.assertFalse(response.json()['llm']['fallback_used'])
                        provider.assert_called_once()
                        payload = json.loads(provider.call_args.args[0].data)
                        url = payload['messages'][1]['content'][0]['image_url']['url']
                        mime, data = url.split(',', 1)
                        self.assertIn(mime, ('data:image/jpeg;base64', 'data:image/png;base64'))
                        with Image.open(io.BytesIO(base64.b64decode(data))) as image:
                            self.assertEqual(image.size, (32, 16))

    def test_invalid_or_disguised_images_never_call_model(self):
        with TestClient(self.app) as client, patch('urllib.request.urlopen') as provider:
            client.headers['Authorization'] = 'Bearer ' + TOKEN
            for mime, raw in (('image/heic', photo('HEIF')[:24]), ('image/webp', photo('WEBP')[:24]),
                              ('image/heic', photo('TIFF')), ('image/avif', photo('HEIF'))):
                with self.subTest(mime=mime, length=len(raw)):
                    response = client.post('/v1/recognize-and-recommend', json={
                        'image_base64': f'data:{mime};base64,' + base64.b64encode(raw).decode()})
                    self.assertEqual(response.status_code, 422, response.text)
            provider.assert_not_called()


if __name__ == '__main__':
    unittest.main()
