"""The copy of the catalogue directory for the matcher (plan 75, stage 2)."""

import collections
import contextlib
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np

import embedding_lab  # noqa: F401  (puts pipeline/ on sys.path)
from embedding_lab import FakeGateway, standard_lab

import build_embeddings  # noqa: E402
import catalog_copy  # noqa: E402
import embeddings  # noqa: E402
import matcher_bundle  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
from matcher.bundle import load_bundle  # noqa: E402
from matcher.catalog import load_catalog  # noqa: E402


def pairs(bundle, view):
    matrix, wines = bundle.views[view]
    return collections.Counter((bundle.slugs[wine], matrix[row].tobytes())
                               for row, wine in enumerate(wines))


class CatalogCopyTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.gateway = FakeGateway()
        self.addCleanup(self.gateway.close)
        self.lab = standard_lab(self.root / "lab", self.gateway.base_url)
        self.addCleanup(self.lab.close)
        settings = embeddings.load_settings(self.lab.config_path)
        self.directory = Path(self.lab.entry_dir())
        self.directory.mkdir(parents=True)
        with contextlib.redirect_stdout(io.StringIO()):
            build_embeddings.run(
                settings.find("gw"), settings.db_path, self.directory,
                make_backend=lambda value: build_embeddings.OpenAIBackend(
                    value, waits=(), timeout=10))

    def copy(self, name="copy", **options):
        return catalog_copy.copy_catalog(self.lab.config_path, self.root / name, **options)

    def test_the_copy_gives_the_matcher_the_data_of_a_bundle(self):
        result = self.copy()
        matcher_bundle.build_bundle(self.lab.config_path, "gw", self.root / "bundle")
        bundle = load_bundle(self.root / "bundle")
        catalog = load_catalog(result["path"], "gw")
        self.assertEqual(catalog.slugs, bundle.slugs)
        self.assertEqual(catalog.cards, bundle.cards)
        self.assertEqual(catalog.embedding, bundle.embedding)
        self.assertEqual(set(catalog.views), set(bundle.views))
        rng = np.random.default_rng(1)
        for view in bundle.views:
            self.assertEqual(pairs(catalog, view), pairs(bundle, view))
            for vector in rng.normal(size=(20, bundle.dimension)).astype(np.float32):
                vector /= np.linalg.norm(vector)
                self.assertEqual(catalog.ranked(view, vector), bundle.ranked(view, vector))
        self.assertNotIn("disabled", catalog.slugs)

    def test_the_copy_holds_the_database_the_index_and_the_images_alone(self):
        result = self.copy()
        out = Path(result["path"])
        index = json.loads((self.directory / "index.json").read_text())
        self.assertEqual(sorted(p.name for p in (out / "embeddings" / "gw").iterdir()),
                         sorted(["index.json", index["vectors_file"]]))
        self.assertEqual((out / "embeddings" / "gw" / "index.json").read_bytes(),
                         (self.directory / "index.json").read_bytes())
        with sqlite3.connect(out / "catalog.sqlite3") as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0],
                             result["schema_version"])
            self.assertTrue(conn.execute("SELECT count(*) FROM matcher_wine").fetchone()[0])
        catalog = Path(self.lab.db_path).parent
        originals = sorted(p.relative_to(catalog) for d in ("images", "cuts")
                           for p in (catalog / d).rglob("*") if p.is_file())
        copied = sorted(p.relative_to(out) for d in ("images", "cuts")
                        for p in (out / d).rglob("*") if p.is_file())
        self.assertEqual(copied, originals)
        self.assertEqual(result["image_files"], len(originals))
        first = originals[0]
        self.assertEqual((out / first).read_bytes(), (catalog / first).read_bytes())
        self.assertEqual(os.stat(out / first).st_ino, os.stat(catalog / first).st_ino)
        manifest = json.loads((out / "copy.json").read_text())
        self.assertEqual(manifest["embeddings"]["gw"]["failed"], len(index["failures"]))
        self.assertGreater(len(index["failures"]), 0)
        self.assertEqual(manifest["embeddings"]["gw"]["missing"], 0)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["copy", "lab"])

    def test_no_images_leaves_out_the_image_directories(self):
        out = Path(self.copy(images=False)["path"])
        self.assertEqual(sorted(p.name for p in out.iterdir()),
                         ["catalog.sqlite3", "copy.json", "embeddings"])

    def test_a_stale_item_stops_the_copy_and_leaves_no_directory(self):
        # A missing prepared image makes the item stale until the next build.
        next((self.directory / "images").iterdir()).unlink()
        with self.assertRaisesRegex(catalog_copy.CopyError, "not current"):
            self.copy()
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["lab"])

    def test_a_running_build_an_unknown_name_or_an_existing_out_stops_the_copy(self):
        with mock.patch.object(embeddings, "running_pid", return_value=4242), \
                self.assertRaisesRegex(catalog_copy.CopyError, "runs"):
            self.copy()
        with self.assertRaisesRegex(catalog_copy.CopyError, "unknown embedding"):
            self.copy(names=["other"])
        (self.root / "copy").mkdir()
        with self.assertRaisesRegex(catalog_copy.CopyError, "exists"):
            self.copy()

    def test_the_command_prints_the_manifest(self):
        out = self.root / "cli"
        command = [sys.executable, str(ROOT / "scripts" / "copy_catalog.py"),
                   "--config", self.lab.config_path, "--out", str(out), "--no-images"]
        done = subprocess.run(command, capture_output=True, text=True, timeout=120)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout)["embeddings"]["gw"]["wines"],
                         len(load_catalog(out, "gw").slugs))
        again = subprocess.run(command, capture_output=True, text=True, timeout=120)
        self.assertEqual(again.returncode, 2)
        self.assertIn("exists", again.stderr)


if __name__ == "__main__":
    unittest.main()
