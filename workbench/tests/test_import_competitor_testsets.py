import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from PIL import Image


SCRIPT = Path(__file__).parents[1] / "scripts/import_competitor_testsets.py"
SPEC = importlib.util.spec_from_file_location("competitor_import", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CompetitorImportTest(unittest.TestCase):
    def test_unknown_scored_slug_moves_to_provisional(self):
        record = MODULE.Record(
            "team", Path("x.webp"), Path("repo"), "x.webp", "slug", "missing",
            "scored", "manual exact",
        )
        result = MODULE.normalize_tiers([record], {"present"})[0]
        self.assertEqual("provisional", result.tier)
        self.assertIn("absent from the current catalogue", result.reason)

    def test_snapshot_preserves_provenance_and_reports_overlap(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repo = root / "repo"
            repo.mkdir()
            image = repo / "wine.png"
            Image.new("RGB", (13, 17), "red").save(image)
            records = [
                MODULE.Record("a", image, repo, "wine.png", {"x": 1}, "slug",
                              "scored", "manual"),
                MODULE.Record("b", image, repo, "wine.png", None, "slug",
                              "provisional", "training overlap"),
            ]
            grouped, failures, overlap = MODULE.prepare(records, root / "out")
            self.assertEqual([], failures)
            self.assertEqual({"a-scored", "b-provisional"}, set(grouped))
            self.assertEqual(1, len(overlap))
            manifest = json.loads(
                (root / "out/a-scored/manifest.jsonl").read_text().splitlines()[0]
            )
            self.assertEqual([13, 17], [manifest["width"], manifest["height"]])
            self.assertEqual("wine.png", manifest["source_path"])
            labels = json.loads(
                (root / "out/a-scored/review-labels.json").read_text()
            )
            entry = next(iter(labels["labels"]["slug"].values()))
            self.assertEqual("scored", entry["tier"])
            self.assertEqual(manifest["image_sha256"], entry["image_sha256"])

    def test_conflicting_exact_labels_move_both_rows_to_provisional(self):
        records = [
            MODULE.Record("a", Path("same.webp"), Path("a"), "same.webp", None,
                          "slug-a", "scored", "manual"),
            MODULE.Record("b", Path("same.jpg"), Path("b"), "same.jpg", None,
                          "slug-b", "scored", "manual"),
        ]
        result = MODULE.demote_scored_conflicts(records)
        self.assertEqual(["provisional", "provisional"], [row.tier for row in result])
        self.assertTrue(all("labels conflict" in row.reason for row in result))

    def test_common_scored_set_keeps_one_largest_copy_per_source_stem(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            small = root / "a" / "same.png"
            large = root / "b" / "same.jpg"
            small.parent.mkdir()
            large.parent.mkdir()
            Image.new("RGB", (10, 20), "red").save(small)
            Image.new("RGB", (30, 40), "red").save(large)
            rows = [
                MODULE.Record("a", small, root / "a", "same.png", {"source": "a"},
                              "slug", "scored", "manual"),
                MODULE.Record("b", large, root / "b", "same.jpg", {"source": "b"},
                              "slug", "scored", "manual"),
            ]
            common = MODULE.common_scored_records(rows)
            self.assertEqual(1, len(common))
            self.assertEqual(("competitors-scored-common", large),
                             (common[0].set_name, common[0].image))
            self.assertEqual(2, len(common[0].original_label["sources"]))

    def test_common_scored_set_refuses_a_label_conflict(self):
        rows = [
            MODULE.Record("a", Path("a/same.png"), Path("a"), "same.png", None,
                          "slug-a", "scored", "manual"),
            MODULE.Record("b", Path("b/same.jpg"), Path("b"), "same.jpg", None,
                          "slug-b", "scored", "manual"),
        ]
        with self.assertRaisesRegex(ValueError, "conflicting labels"):
            MODULE.common_scored_records(rows)


if __name__ == "__main__":
    unittest.main()
