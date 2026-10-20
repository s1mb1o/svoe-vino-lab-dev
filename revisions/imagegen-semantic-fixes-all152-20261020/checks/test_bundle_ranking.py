"""Check exact ranking order and scores after vectorized output conversion."""
from pathlib import Path
import unittest

import numpy as np

from matcher.bundle import Bundle


class BundleRankingTest(unittest.TestCase):
    def assert_reference(self, matrix, owners, query, count=40):
        slugs = tuple('wine-%03d' % number for number in range(count))
        bundle = Bundle(Path('.'), {}, matrix.shape[1], slugs, {'full': (matrix, owners)})
        best = np.full(count, -np.inf, dtype=np.float32)
        np.maximum.at(best, owners, matrix @ query)
        order = np.argsort(-best, kind='stable')
        expected = [(slugs[number], float(best[number])) for number in order
                    if np.isfinite(best[number])]
        actual = bundle.ranked('full', query)
        self.assertEqual(actual, expected)
        self.assertTrue(all(type(score) is float for _, score in actual))

    def test_random_queries_and_shared_rows_match_every_pair(self):
        randomizer = np.random.default_rng(8)
        matrix = randomizer.normal(size=(83, 17)).astype(np.float32)
        owners = randomizer.integers(0, 35, size=83)
        for _ in range(32):
            self.assert_reference(matrix, owners,
                                  randomizer.normal(size=17).astype(np.float32))

    def test_equal_scores_keep_slug_order_and_absent_wines_are_excluded(self):
        self.assert_reference(np.ones((4, 3), dtype=np.float32), np.array([3, 1, 1, 2]),
                              np.ones(3, dtype=np.float32))

    def test_nonfinite_scores_are_excluded(self):
        matrix = np.array([[np.nan], [np.inf], [-np.inf], [0], [-1]], dtype=np.float32)
        self.assert_reference(matrix, np.arange(5), np.ones(1, dtype=np.float32))

    def test_empty_view_returns_no_pairs(self):
        self.assert_reference(np.empty((0, 3), dtype=np.float32), np.array([], dtype=int),
                              np.ones(3, dtype=np.float32))
