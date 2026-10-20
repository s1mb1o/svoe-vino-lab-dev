"""Tests for the catalogue reader with a fixture catalogue directory of the lab layout."""

import collections
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

import numpy as np
import yaml

from matcher.bundle import load_bundle
from matcher.catalog import CatalogError, load_catalog, normalize_qr_url
from matcher.service import ConfigError, load_matcher
from test_siglip2 import DATA, MODEL, FakeSiglip2, unit, write_bundle

EMBEDDING = "test-siglip2"
VECTORS = "vectors-0123abcd.npy"
# (view, vector, (wine slug, image type, role) of each wine that has the source image).
# The label close-up of wine-c counts in the view `label` alone. The last source is one
# image of two wines.
ROWS = (
    ("full", (1, 0, 0, 0), (("wine-a", "main", "full"),)),
    ("full", (0, 1, 0, 0), (("wine-b", "main", "full"),)),
    ("label", (0, 0, 1, 0), (("wine-c", "label_front", "label"),)),
    ("full", (0, 0, 0, 1), (("wine-shared-b", "main", "full"),
                            ("wine-shared-a", "full_front", "full"))),
)
# The rows of test_siglip2.write_bundle: the same vectors and wines as ROWS.
BUNDLE_ROWS = tuple((view, vector, tuple(slug for slug, _, _ in owners))
                    for view, vector, owners in ROWS)


def digest(number):
    return "%064x" % (number + 1)


def write_catalog(root, rows=ROWS, wines=None, vectors=None, index=None):
    """Write a catalogue directory: the two views as tables, one index, one vector file."""
    entry = root / "embeddings" / EMBEDDING
    entry.mkdir(parents=True)
    conn = sqlite3.connect(root / "catalog.sqlite3")
    conn.execute("CREATE TABLE matcher_wine (wine_slug, name, producer, category, region, "
                 "color, grapes, main_source_name, qr_values)")
    conn.execute("CREATE TABLE matcher_wine_image (wine_slug, image_type, sha256, role)")
    slugs = sorted({slug for _, _, owners in rows for slug, _, _ in owners})
    for slug in slugs:
        conn.execute("INSERT INTO matcher_wine VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (wines or {}).get(slug, (slug, slug, None, None, None, None, None,
                                              None, "[]")))
    items = []
    for number, (view, _, owners) in enumerate(rows):
        for slug, image_type, role in owners:
            conn.execute("INSERT INTO matcher_wine_image VALUES (?, ?, ?, ?)",
                         (slug, image_type, digest(number), role))
        items.append({"row": number, "source_sha256": digest(number), "view": view,
                      "role": "full", "embedding_hash": digest(100 + number),
                      "derivative_sha256": None})
    conn.commit()
    conn.close()
    matrix = vectors if vectors is not None else np.vstack(
        [unit(vector) for _, vector, _ in rows]).astype(np.float32)
    np.save(entry / VECTORS, matrix, allow_pickle=False)
    record = {"name": EMBEDDING, "dim": int(matrix.shape[1]), "vectors_file": VECTORS,
              "items": items, "failures": [],
              "config": {"name": EMBEDDING, "backend": "openai",
                         "base_url": "http://unused.invalid/v1", "model": MODEL,
                         "extra_body": {"max_num_patches": 512},
                         "views": {"full": [], "label": []}}}
    record.update(index or {})
    (entry / "index.json").write_text(json.dumps(record), encoding="utf-8")
    return root


def pairs(bundle, view):
    matrix, wines = bundle.views[view]
    return collections.Counter((bundle.slugs[wine], matrix[row].tobytes())
                               for row, wine in enumerate(wines))


class CatalogTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)

    def catalog(self, **options):
        return write_catalog(self.directory / "catalog", **options)

    def test_the_catalog_gives_the_vectors_and_answers_of_the_same_bundle(self):
        bundle_dir = self.directory / "bundle"
        write_bundle(bundle_dir, BUNDLE_ROWS)
        bundle, catalog = load_bundle(bundle_dir), load_catalog(self.catalog(), EMBEDDING)
        self.assertEqual(catalog.slugs, bundle.slugs)
        self.assertEqual(catalog.dimension, bundle.dimension)
        self.assertEqual(set(catalog.views), set(bundle.views))
        for view in bundle.views:
            self.assertEqual(pairs(catalog, view), pairs(bundle, view))
        for query in ((0.1, 0.5, 0.9, 0), (0, 0, 0, 1), (0.5, 0.5, 0.5, 0.5)):
            vector = unit(query)
            for view in bundle.views:
                self.assertEqual(catalog.top1(view, vector), bundle.top1(view, vector))
                self.assertEqual(catalog.ranked(view, vector), bundle.ranked(view, vector))
        self.assertEqual(catalog.embedding["model"], MODEL)

    def test_a_label_image_counts_in_the_label_view_alone(self):
        rows = (("full", (1, 0, 0, 0), (("wine-a", "main", "full"),
                                        ("wine-d", "label_back", "label"))),
                ("label", (1, 0, 0, 0), (("wine-a", "main", "full"),
                                         ("wine-d", "label_back", "label"))))
        catalog = load_catalog(self.catalog(rows=rows), EMBEDDING)
        full = {catalog.slugs[wine] for wine in catalog.views["full"][1]}
        label = {catalog.slugs[wine] for wine in catalog.views["label"][1]}
        self.assertEqual((full, label), ({"wine-a"}, {"wine-a", "wine-d"}))

    def test_the_card_has_the_public_urls_and_the_normalized_qr_urls(self):
        slug = "a-wine-krasnoe-suhoe-13"
        qr = ["URL: HTTPS://Example.COM:443/a", "https://example.com/a", "ftp://x/y",
              "http://b.example"]
        wines = {slug: (slug, "Вино", "Винодельня", "Красное", "Крым", "Рубиновый", None,
                        "Screenshot 2023 at 17.55.png", json.dumps(qr))}
        rows = (("full", (1, 0, 0, 0), ((slug, "main", "full"),)),)
        card = load_catalog(self.catalog(rows=rows, wines=wines), EMBEDDING).cards[slug]
        self.assertEqual(card["page_url"], "https://vino-svoe.ru/wines/" + slug)
        self.assertEqual(card["image_url"],
                         "https://api.vino-svoe.ru/v1/img/str-api/1920/1920/resize/uploads/"
                         "Screenshot%202023%20at%2017.55.png")
        self.assertEqual(card["qr_urls"], ["http://b.example/", "https://example.com/a"])
        self.assertEqual((card["name"], card["producer"], card["grapes"], card["sugar"]),
                         ("Вино", "Винодельня", None, "Сухое"))
        self.assertEqual(list(card), ["name", "page_url", "producer", "category", "region",
                                      "color", "grapes", "image_url", "qr_urls", "sugar"])

    def test_a_wine_without_an_item_gets_no_card(self):
        root = self.catalog()
        conn = sqlite3.connect(root / "catalog.sqlite3")
        conn.execute("INSERT INTO matcher_wine VALUES ('wine-z', 'Z', NULL, NULL, NULL, NULL, "
                     "NULL, NULL, '[]')")
        conn.commit()
        conn.close()
        catalog = load_catalog(root, EMBEDDING)
        self.assertNotIn("wine-z", catalog.cards)
        self.assertEqual(set(catalog.cards), set(catalog.slugs))

    def test_the_qr_rules_are_the_rules_of_the_bundle_builder(self):
        self.assertEqual(normalize_qr_url(" URL:http://A.example:80 "), "http://a.example/")
        self.assertEqual(normalize_qr_url("https://user:pw@a.example/"), None)
        self.assertEqual(normalize_qr_url("not a url"), None)

    def test_an_invalid_catalog_is_rejected(self):
        cases = {
            "no directory": lambda root: self.directory / "missing",
            "no view": lambda root: self.drop(root, "matcher_wine_image"),
            "other columns": lambda root: self.rename_column(root),
            "vector file name": lambda root: self.patch_index(root, vectors_file="v.npy"),
            "missing vector file": lambda root: self.patch_index(
                root, vectors_file="vectors-ffffffff.npy"),
            "row out of range": lambda root: self.patch_index(root, items=[
                {"row": 9, "source_sha256": digest(0), "view": "full"}] * 4),
        }
        for label, change in cases.items():
            with self.subTest(label):
                root = write_catalog(self.directory / label.replace(" ", "-"))
                with self.assertRaises(CatalogError):
                    load_catalog(change(root), EMBEDDING)

    def test_an_invalid_vector_file_is_rejected(self):
        cases = {
            "not normalized": np.ones((4, 4), dtype=np.float32),
            "float64": np.eye(4, dtype=np.float64),
            "shape": np.eye(3, 4, dtype=np.float32),
        }
        for label, vectors in cases.items():
            with self.subTest(label):
                root = write_catalog(self.directory / label, vectors=vectors)
                with self.assertRaises(CatalogError):
                    load_catalog(root, EMBEDDING)

    def test_an_invalid_embedding_name_or_no_active_item_is_rejected(self):
        root = self.catalog()
        for name in ("", "../x", "Upper", None):
            with self.subTest(name), self.assertRaises(CatalogError):
                load_catalog(root, name)
        self.drop(root, "matcher_wine_image")
        conn = sqlite3.connect(root / "catalog.sqlite3")
        conn.execute("CREATE TABLE matcher_wine_image (wine_slug, image_type, sha256, role)")
        conn.commit()
        conn.close()
        with self.assertRaises(CatalogError):
            load_catalog(root, EMBEDDING)

    def drop(self, root, table):
        conn = sqlite3.connect(root / "catalog.sqlite3")
        conn.execute("DROP TABLE %s" % table)
        conn.commit()
        conn.close()
        return root

    def rename_column(self, root):
        conn = sqlite3.connect(root / "catalog.sqlite3")
        conn.execute("ALTER TABLE matcher_wine RENAME COLUMN qr_values TO qr")
        conn.commit()
        conn.close()
        return root

    def patch_index(self, root, **values):
        path = root / "embeddings" / EMBEDDING / "index.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record.update(values)
        path.write_text(json.dumps(record), encoding="utf-8")
        return root


class CatalogPipelineTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.root = write_catalog(self.directory / "catalog")

    def load(self, entry):
        path = self.directory / "config.yaml"
        path.write_text(yaml.safe_dump({"matcher": {"pipeline": entry["name"]},
                                        "pipeline": [entry]}), encoding="utf-8")
        return load_matcher(path)

    def test_a_siglip2_pipeline_reads_the_catalog(self):
        fake = FakeSiglip2((0.1, 0.5, 0.9, 0))
        self.addCleanup(fake.close)
        matcher = self.load({"name": "p", "backend": "siglip2", "catalog": str(self.root),
                             "embedding": EMBEDDING, "endpoint": fake.url})
        photo = (DATA / "02eef911.webp").read_bytes()
        self.assertEqual(matcher.predict(photo), "wine-b")
        self.assertEqual([slug for slug, _ in matcher.match(photo, 2)], ["wine-b", "wine-a"])
        self.assertEqual(fake.requests[0][1]["model"], MODEL)

    def test_a_mock_pipeline_takes_its_cards_from_the_catalog(self):
        matcher = self.load({"name": "m", "backend": "mock", "answers": {},
                             "catalog": str(self.root), "embedding": EMBEDDING})
        self.assertEqual(sorted(matcher.cards),
                         ["wine-a", "wine-b", "wine-c", "wine-shared-a", "wine-shared-b"])

    def test_an_invalid_source_entry_is_rejected(self):
        bundle = self.directory / "bundle"
        write_bundle(bundle, BUNDLE_ROWS)
        base = {"name": "p", "backend": "siglip2", "endpoint": "http://127.0.0.1:9"}
        cases = {
            "both": dict(base, bundle=str(bundle), catalog=str(self.root), embedding=EMBEDDING),
            "no embedding": dict(base, catalog=str(self.root)),
            "embedding alone": dict(base, bundle=str(bundle), embedding=EMBEDDING),
            "unknown embedding": dict(base, catalog=str(self.root), embedding="other"),
            "no source": dict(base),
        }
        for label, entry in cases.items():
            with self.subTest(label), self.assertRaises(ConfigError):
                self.load(entry)


if __name__ == "__main__":
    unittest.main()
