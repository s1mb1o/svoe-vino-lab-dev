"""A lab database with linked images for the tests of plan 26.

`DescriptionCase` makes a temporary database with two wines, one `main` image each,
and one image with no link. The image files are real PNG files of the store. The model
cache and the state file of the watcher go to a temporary directory, so a test never
writes into `data/cache/` or `work/`.
"""
import hashlib
import io
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import image_descriptions  # noqa: E402
import labdb  # noqa: E402
import model_cache  # noqa: E402


def png(color, size=(40, 80), mode="RGB"):
    buffer = io.BytesIO()
    Image.new(mode, size, color).save(buffer, "PNG")
    return buffer.getvalue()


class DescriptionCase(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.db = str(self.root / "lab.sqlite3")
        self.old_cache, model_cache.ROOT = model_cache.ROOT, str(self.root / "cache")
        self.status_path = str(self.root / "status.json")
        self.old_status = image_descriptions.STATUS_PATH
        image_descriptions.STATUS_PATH = self.status_path
        conn = labdb.connect(self.db, create=True)
        self.sha = {}
        with conn:
            for slug, color in (("wine-a", "red"), ("wine-b", "blue"), ("none", "green")):
                data = png(color)
                digest = hashlib.sha256(data).hexdigest()
                folder = self.root / "images" / "main"
                folder.mkdir(parents=True, exist_ok=True)
                (folder / ("%s.png" % digest)).write_bytes(data)
                conn.execute("INSERT INTO image (sha256, folder, extension, width, height) "
                             "VALUES (?, 'main', 'png', 40, 80)", (digest,))
                self.sha[slug] = digest
                if slug == "none":
                    continue
                conn.execute(
                    "INSERT INTO wine_catalog (wine_slug, name, producer, category, color, "
                    "region, csv_photo_name) VALUES (?, 'Вино', 'Винодельня', 'Красное', "
                    "'Рубиновый', 'Крым', 'x.webp')", (slug,))
                conn.execute("INSERT INTO wine_image (wine_slug, image_type, sha256, "
                             "source_name, match_method) VALUES (?, 'main', ?, 'x.webp', "
                             "'test')", (slug, digest))
        conn.close()

    def tearDown(self):
        model_cache.ROOT = self.old_cache
        image_descriptions.STATUS_PATH = self.old_status
        self.directory.cleanup()

    def connect(self):
        conn = sqlite3.connect(self.db)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def cache_files(self):
        return [p for p in (self.root / "cache").rglob("*.json")] \
            if os.path.isdir(self.root / "cache") else []
