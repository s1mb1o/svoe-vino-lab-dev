"""Replay metrics must preserve the meaning of named-negative annotations."""
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import replay_wine_term_recovery as replay


def sample(label, truth_rank, new_rank, old_top="a", new_top="b"):
    def variant(rank, top):
        return {"rank": rank, "order": [top], "observed_attributes": {},
                "corrections": [], "all_shortlist_conflicts": False, "truth_conflicts": []}
    return {"label": label, "named_slug": "a",
            "variants": {"exact": variant(truth_rank, old_top), "whitespace": variant(new_rank, new_top)}}


class ReplayChecks(unittest.TestCase):
    def test_named_negative_other_identity_is_not_a_proven_positive(self):
        result = replay.metrics([sample("negative", None, None)], "whitespace")
        self.assertEqual(result["named_negative_fixed"], 1)
        self.assertEqual(result["positive_top1"], 0)
        self.assertIsNone(result["positive_top1_rate"])
        self.assertIsNone(result["correction_precision"])

    def test_wrong_wine_promotions_and_rescues_are_separate(self):
        result = replay.metrics([sample("positive", 1, 2), sample("positive", 2, 1)], "whitespace")
        self.assertEqual(result["positive_fixed"], 1)
        self.assertEqual(result["positive_regressed"], 1)
        self.assertEqual(result["positive_top1_rate"], .5)

    def test_producer_variants_stay_in_one_partition(self):
        catalog = {"a": {"producer": "Winery"}, "b": {"producer": "WINERY"}}
        self.assertEqual(replay.partition({"named_slug": "a"}, catalog),
                         replay.partition({"named_slug": "b"}, catalog))

    def test_replay_cache_preserves_metadata_and_normalization_results(self):
        records = [{"name": "Extra Brut", "slug": "wine-brut"},
                   {"grapes": "Мерло, Голубок"}, {"color": "Белое"}, None]
        originals = [replay.attrs.expected(record) for record in records]
        normal = replay.wine_terms.normalize("MYCKAT RIESL ING")
        with mock.patch.object(replay.attrs, "expected", replay.attrs.expected), mock.patch.object(
                replay.wine_terms, "normalize", replay.wine_terms.normalize):
            replay.cache_pure_functions()
            self.assertEqual([replay.attrs.expected(record) for record in records], originals)
            self.assertEqual([replay.attrs.expected(record) for record in records], originals)
            self.assertEqual(replay.wine_terms.normalize("MYCKAT RIESL ING"), normal)


if __name__ == "__main__":
    unittest.main()
