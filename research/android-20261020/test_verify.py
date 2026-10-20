import copy
import importlib.util
import math
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("android_research_verify", Path(__file__).with_name("verify.py"))
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)


class VerificationTest(unittest.TestCase):
    def setUp(self):
        self.rows = [dict(query_id=str(i), request_ms=100 + i, error=False,
                          hit_1=i == 0, hit_5=i < 2, hit_10=True) for i in range(5)]

    def test_counts_and_inclusive_percentile(self):
        result = verify.calculate(self.rows)
        self.assertEqual(result["hits"], {"1": 1, "5": 2, "10": 5})
        self.assertEqual(result["median_ms"], 102)
        self.assertAlmostEqual(result["p95_ms"], 103.8)

    def test_duplicate_ids_are_rejected(self):
        self.rows[1]["query_id"] = "0"
        with self.assertRaises(ValueError): verify.calculate(self.rows)

    def test_nonfinite_latency_is_rejected(self):
        for value in [math.nan, math.inf, 0, -1, True]:
            self.rows[0]["request_ms"] = value
            with self.assertRaises(ValueError): verify.calculate(self.rows)

    def test_error_is_kept_in_denominator(self):
        self.rows[4].update(error=True, hit_10=False)
        result = verify.calculate(self.rows)
        self.assertEqual(result["assignments"], 5)
        self.assertEqual(result["errors"], 1)

    def test_error_cannot_be_a_hit(self):
        self.rows[0]["error"] = True
        with self.assertRaises(ValueError): verify.calculate(self.rows)

    def test_top_k_flags_are_monotonic(self):
        self.rows[0]["hit_5"] = False
        with self.assertRaises(ValueError): verify.calculate(self.rows)

    def test_paired_gains_and_losses(self):
        changed = copy.deepcopy(self.rows)
        changed[0]["hit_1"] = False
        changed[1]["hit_1"] = True
        self.assertEqual(verify.paired(changed, self.rows), [1, 1])

    def test_unpaired_queries_are_rejected(self):
        with self.assertRaises(ValueError): verify.paired(self.rows[::-1], self.rows)


if __name__ == "__main__":
    unittest.main()
