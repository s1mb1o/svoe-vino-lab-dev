"""Tests for the rotated rows of workbench plan 82: bundle format 3 and catalogue indexes
with `angles`. A wine scores the best cosine of its rows, so a rotated row of an image
gives the maximum over the rotation. `Bundle.angles` keeps the angle of each row."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from matcher.bundle import BundleError, load_bundle
from matcher.catalog import CatalogError, load_catalog
from test_catalog import EMBEDDING, digest, write_catalog
from test_siglip2 import MODEL, file_record, unit, write_bundle, write_jsonl

# (source number, angle, vector, wine slugs) of each vector row. The image of wine-a
# faces up at 0° and gives the vector (0, 1, 0, 0) at 90°.
ROTATED_ROWS = (
    (0, 0, (1, 0, 0, 0), ("wine-a",)),
    (0, 90, (0, 1, 0, 0), ("wine-a",)),
    (1, 0, (0, 0, 1, 0), ("wine-b",)),
    (1, 90, (0.6, 0.8, 0, 0), ("wine-b",)),
)


def write_rotated_bundle(root, rows=ROTATED_ROWS, item_change=None):
    """Write a version 3 bundle in the format of workbench/pipeline/matcher_bundle.py."""
    root.mkdir()
    vectors = np.vstack([unit(vector) for _, _, vector, _ in rows]).astype(np.float32)
    np.save(root / "vectors.npy", vectors, allow_pickle=False)
    items, candidates = [], []
    for row, (source, angle, _, slugs) in enumerate(rows):
        sha = hashlib.sha256(b"source %d" % source).hexdigest()
        item = {
            "vector_row": row, "source_vector_row": row, "source_sha256": sha,
            "view": "full", "role": "full",
            "embedding_hash": hashlib.sha256(b"item %d" % source).hexdigest(),
            "derivative_sha256": None, "image": "images/%s_full.png" % sha,
            "width": 10, "height": 20, "angle": angle,
        }
        if item_change:
            item_change(row, item)
        items.append(item)
        candidates.extend({"vector_row": row, "wine_slug": slug, "view": "full",
                           "image_type": "main"} for slug in slugs)
    slugs = sorted({candidate["wine_slug"] for candidate in candidates})
    write_jsonl(root / "items.jsonl", items)
    write_jsonl(root / "candidates.jsonl", candidates)
    write_jsonl(root / "wines.jsonl", [
        {"wine_slug": slug, "name": slug, "producer": None, "category": None,
         "region": None, "color": None, "grapes": None,
         "page_url": "https://vino-svoe.ru/wines/" + slug, "image_url": None,
         "qr_urls": []} for slug in slugs])
    write_jsonl(root / "omissions.jsonl", [])
    payloads = ("vectors.npy", "items.jsonl", "candidates.jsonl", "wines.jsonl",
                "omissions.jsonl")
    manifest = {
        "format": "svoe-vino-matcher-bundle", "format_version": 3,
        "created_at": "2026-09-29T00:00:00+0300", "source": {"embedding": "test-rot"},
        "embedding": {"name": "test-rot", "backend": "openai",
                      "base_url": "http://unused.invalid/v1", "model": MODEL,
                      "extra_body": {"max_num_patches": 512}, "views": {"full": []},
                      "rotation_step": 90},
        "vectors": {"file": "vectors.npy", "dtype": "float32",
                    "shape": list(vectors.shape), "normalized": "l2"},
        "scoring": {"similarity": "dot_product", "item_reduction": "max",
                    "view_reduction": "mean"},
        "images": {"included": False, "manifest": None, "count": 0},
        "counts": {"planned_items": 2, "items": len(items), "candidates": len(candidates),
                   "wines": len(slugs), "omissions": 0, "images": 0},
        "files": {name: file_record(root / name) for name in payloads},
    }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return root


class RotatedBundleTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)

    def test_a_version_3_bundle_keeps_the_angle_of_each_row(self):
        bundle = load_bundle(write_rotated_bundle(self.directory / "rot"))
        self.assertEqual(bundle.angles["full"].tolist(), [0, 90, 0, 90])
        self.assertEqual(len(bundle.views["full"][0]), 4)
        # The 90° row of wine-a matches the query exactly: the maximum over the rotation.
        self.assertEqual(bundle.top1("full", unit((0, 1, 0, 0))), ("wine-a", 1.0))
        ranked = bundle.ranked("full", unit((0.6, 0.8, 0, 0)))
        self.assertEqual(ranked[0][0], "wine-b")
        self.assertAlmostEqual(ranked[0][1], 1.0, places=6)
        self.assertEqual([slug for slug, _ in ranked], ["wine-b", "wine-a"])

    def test_versions_1_and_2_have_no_angles(self):
        write_bundle(self.directory / "plain")
        self.assertIsNone(load_bundle(self.directory / "plain").angles)

    def test_a_bad_angle_or_items_file_is_rejected(self):
        changes = {
            "an angle of 360": lambda row, item: item.update(angle=360) if row == 1 else None,
            "a bool angle": lambda row, item: item.update(angle=True) if row == 1 else None,
            "no angle": lambda row, item: item.pop("angle") if row == 2 else None,
        }
        for number, (name, change) in enumerate(changes.items()):
            with self.subTest(name=name):
                root = write_rotated_bundle(self.directory / ("bad%d" % number),
                                            item_change=change)
                with self.assertRaises(BundleError):
                    load_bundle(root)
        root = write_rotated_bundle(self.directory / "changed")
        (root / "items.jsonl").write_text("", encoding="utf-8")
        with self.assertRaisesRegex(BundleError, "items.jsonl does not match"):
            load_bundle(root)


class RotatedCatalogTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)

    def catalog(self, items, vectors, name="catalog"):
        rows = (("full", (1, 0, 0, 0), (("wine-a", "main", "full"),)),
                ("full", (0, 0, 1, 0), (("wine-b", "main", "full"),
                                        ("wine-c", "full_front", "full"))))
        return write_catalog(self.directory / name, rows=rows,
                             vectors=np.vstack([unit(v) for v in vectors]).astype(np.float32),
                             index={"items": items})

    @staticmethod
    def item(number, row, angles=None):
        item = {"row": row, "source_sha256": digest(number), "view": "full", "role": "full",
                "embedding_hash": digest(100 + number), "derivative_sha256": None}
        if angles is not None:
            item["angles"] = angles
        return item

    def test_each_row_of_a_rotated_item_belongs_to_each_owner(self):
        vectors = ((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0.6, 0.8))
        root = self.catalog([self.item(0, 0, [0, 90]), self.item(1, 2, [0, 90])], vectors)
        bundle = load_catalog(root, EMBEDDING)
        matrix, wines = bundle.views["full"]
        # wine-a: 2 rows; wine-b and wine-c share the second image: 2 rows each.
        self.assertEqual(len(matrix), 6)
        self.assertEqual(sorted(bundle.angles["full"].tolist()), [0, 0, 0, 90, 90, 90])
        self.assertEqual(bundle.top1("full", unit((0, 1, 0, 0))), ("wine-a", 1.0))
        self.assertEqual(bundle.top1("full", unit((0, 0, 0.6, 0.8)))[0], "wine-b")

    def test_an_index_without_angles_has_no_angles(self):
        root = self.catalog([self.item(0, 0), self.item(1, 1)], ((1, 0, 0, 0), (0, 0, 1, 0)))
        self.assertIsNone(load_catalog(root, EMBEDDING).angles)

    def test_bad_rows_or_angles_are_rejected(self):
        vectors = ((1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0))
        cases = {
            "a gap": [self.item(0, 0, [0, 90]), self.item(1, 3)],
            "an overlap": [self.item(0, 0, [0, 90]), self.item(1, 1)],
            "angles not a list": [self.item(0, 0, "0,90"), self.item(1, 2)],
            "the first angle not 0": [self.item(0, 0, [90, 0]), self.item(1, 2)],
            "a repeated angle": [self.item(0, 0, [0, 0]), self.item(1, 2)],
            "rows past the file": [self.item(0, 1, [0, 90, 180]), self.item(1, 0)],
        }
        for number, (name, items) in enumerate(cases.items()):
            with self.subTest(name=name):
                root = self.catalog(items, vectors, name="bad%d" % number)
                with self.assertRaises(CatalogError):
                    load_catalog(root, EMBEDDING)


if __name__ == "__main__":
    unittest.main()
