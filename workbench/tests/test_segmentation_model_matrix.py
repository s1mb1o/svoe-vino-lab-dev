import os
import sys
import unittest

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import segmentation_model_matrix as matrix  # noqa: E402


class SegmentationModelMatrixTests(unittest.TestCase):
    def test_none_steps_keep_the_full_image(self):
        steps = matrix.none_steps()
        self.assertEqual([step["step"] for step in steps],
                         ["white_background", "resize"])
        self.assertEqual(steps[1]["max_size"], 1024)
        self.assertEqual(steps[1]["aspect"], "keep")
        self.assertFalse(steps[1]["upscale"])

    def test_comparable_levels_cover_each_model_once(self):
        names = [name for _, naflex, fixed in matrix.LEVELS for name in (naflex, fixed)]
        self.assertCountEqual(names, matrix.MODELS)
        self.assertEqual(len(names), len(set(names)))

    def test_catalogue_mapping_and_rank_use_best_source_of_each_wine(self):
        manifest = {"catalogue": [
            {"wines": ["a", "shared"]},
            {"wines": ["b", "shared"]},
            {"wines": ["a"]},
        ]}
        wines, sources, wine_numbers = matrix.catalogue_mapping(manifest)
        catalogue = np.asarray([[1.0, 0.0], [0.0, 1.0], [0.8, 0.2]], dtype=np.float32)
        candidates, positions = matrix.rank_query(
            np.asarray([0.0, 1.0], dtype=np.float32), catalogue, wines, sources, wine_numbers)
        self.assertEqual([row["slug"] for row in candidates], ["b", "shared", "a"])
        self.assertEqual(int(positions[wines.index("b")]), 1)
        self.assertEqual(int(positions[wines.index("a")]), 3)

    def test_rank_leaves_wine_without_vector_absent(self):
        wines = ["a", "b"]
        catalogue = np.asarray([[1.0, 0.0], [np.nan, np.nan]], dtype=np.float32)
        candidates, positions = matrix.rank_query(
            np.asarray([1.0, 0.0], dtype=np.float32), catalogue, wines,
            np.asarray([0]), np.asarray([0]))
        self.assertEqual(candidates[0]["slug"], "a")
        self.assertEqual(int(positions[1]), -1)

    def test_positive_result_has_full_catalogue_rank(self):
        query = {"query_id": "q-1", "image_path": "a/x.jpg", "image_sha256": "0" * 64,
                 "slug": "a", "label": "positive", "truth": ["a"]}
        row = matrix.result_row(query, [{"slug": "b", "score": 0.8, "rank": 1}],
                                np.asarray([4, 1]), {"a": 0, "b": 1})
        self.assertEqual(row["rank_of_truth"], 4)
        self.assertEqual(row["full_rank_of_truth"], 4)
        self.assertEqual(row["outcome"], "miss")

    def test_positive_rank_beyond_top_ten_is_absent_from_workbench_metric(self):
        query = {"query_id": "q-1", "image_path": "a/x.jpg", "image_sha256": "0" * 64,
                 "slug": "a", "label": "positive", "truth": ["a"]}
        row = matrix.result_row(query, [{"slug": "b", "score": 0.8, "rank": 1}],
                                np.asarray([12, 1]), {"a": 0, "b": 1})
        self.assertIsNone(row["rank_of_truth"])
        self.assertEqual(row["full_rank_of_truth"], 12)

    def test_error_never_counts_as_correct_in_paired_test(self):
        base = {"query_id": "q", "label": "positive", "rank_of_truth": None,
                "outcome": "no_answer", "error": "failed"}
        better = {"query_id": "q", "label": "positive", "rank_of_truth": 1,
                  "outcome": "hit", "error": None}
        result = matrix.pair_block([base], [better])["positive_r1"]
        self.assertEqual(result["second_wins"], 1)
        self.assertEqual(result["second_losses"], 0)
        self.assertEqual(result["second_rate"], 1.0)

    def test_exact_mcnemar_is_two_sided(self):
        self.assertEqual(matrix.exact_mcnemar(0, 0), 1.0)
        self.assertEqual(matrix.exact_mcnemar(1, 0), 1.0)
        self.assertAlmostEqual(matrix.exact_mcnemar(10, 0), 0.001953125)


if __name__ == "__main__":
    unittest.main()
