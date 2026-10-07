"""Verify preview dimensions, pixels, source integrity, cache, and concurrent reads."""
import concurrent.futures
import io
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pipeline'))
import image_thumbnails
from PIL import Image


class ThumbnailsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cache = self.root / 'cache'
        self.source = self.root / 'source.png'

    def test_large_transparent_source_is_unchanged_and_preview_is_bounded(self):
        Image.new('RGBA', (1950, 7371), (30, 60, 90, 100)).save(self.source)
        before = self.source.read_bytes(), self.source.stat().st_mtime_ns
        data = image_thumbnails.get(self.source, self.cache)
        with Image.open(io.BytesIO(data)) as image:
            self.assertEqual(image.size, (203, 768))
            self.assertEqual(image.mode, 'RGBA')
            self.assertEqual(image.getpixel((100, 100))[3], 100)
        self.assertEqual(before, (self.source.read_bytes(), self.source.stat().st_mtime_ns))
        with mock.patch.object(Image, 'open', side_effect=AssertionError('cache decoded source')):
            self.assertEqual(data, image_thumbnails.get(self.source, self.cache))

    def test_small_source_is_not_upscaled_and_replacement_invalidates_cache(self):
        Image.new('RGB', (60, 80), 'red').save(self.source)
        red = image_thumbnails.get(self.source, self.cache)
        with Image.open(io.BytesIO(red)) as image:
            self.assertEqual(image.size, (60, 80))
        Image.new('RGB', (60, 80), 'blue').save(self.source)
        self.assertNotEqual(red, image_thumbnails.get(self.source, self.cache))
        self.source.unlink()
        with self.assertRaises(FileNotFoundError):
            image_thumbnails.get(self.source, self.cache)

    def test_exif_orientation_is_applied(self):
        exif = Image.Exif(); exif[274] = 6
        Image.new('RGB', (1200, 600), 'green').save(self.source, format='JPEG', exif=exif)
        with Image.open(io.BytesIO(image_thumbnails.get(self.source, self.cache))) as image:
            self.assertEqual(image.size, (384, 768))

    def test_concurrent_requests_generate_once(self):
        Image.new('RGB', (1800, 2400), 'red').save(self.source)
        original = Image.open
        with mock.patch.object(Image, 'open', wraps=original) as opened:
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                values = list(pool.map(lambda _: image_thumbnails.get(self.source, self.cache), range(16)))
            self.assertEqual(opened.call_count, 1)
            self.assertTrue(all(data == values[0] for data in values))
        self.assertEqual(len(list(self.cache.glob('*.webp'))), 1)
        self.assertFalse(list(self.cache.glob('*.tmp')))

    def test_cold_builds_are_bounded_across_different_sources(self):
        sources = []
        for n in range(8):
            path = self.root / f'{n}.png'
            Image.new('RGB', (60, 80), (n * 20, 50, 80)).save(path)
            sources.append(path)
        opened = Image.open
        guard = threading.Lock()
        active = peak = 0
        class Tracked:
            def __init__(self, path): self.image = opened(path)
            def __enter__(self):
                nonlocal active, peak
                with guard:
                    active += 1
                    peak = max(peak, active)
                time.sleep(0.01)
                return self.image
            def __exit__(self, *args):
                nonlocal active
                self.image.close()
                with guard: active -= 1
        with mock.patch.object(Image, 'open', side_effect=Tracked):
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(lambda path: image_thumbnails.get(path, self.cache), sources))
        self.assertEqual(peak, 1)

    def test_grayscale_alpha_and_colour_profile_are_preserved(self):
        Image.new('LA', (40, 80), (100, 90)).save(self.source, icc_profile=b'test-profile')
        with Image.open(io.BytesIO(image_thumbnails.get(self.source, self.cache))) as image:
            self.assertEqual(image.mode, 'RGBA')
            self.assertEqual(image.getpixel((20, 40))[3], 90)
            self.assertEqual(image.info['icc_profile'], b'test-profile')

    def test_cache_trims_oldest_files(self):
        self.cache.mkdir()
        for n in range(3):
            path = self.cache / f'{n}.webp'; path.write_bytes(b'x' * 4)
            os.utime(path, (n, n))
        with mock.patch.object(image_thumbnails, 'MAX_CACHE_BYTES', 8):
            image_thumbnails._trim(self.cache)
        self.assertEqual(sorted(p.name for p in self.cache.iterdir()), ['1.webp', '2.webp'])
