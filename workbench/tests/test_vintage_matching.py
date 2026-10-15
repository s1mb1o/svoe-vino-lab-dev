"""Verify the post-VLM vintage policy in the isolated runtime copy."""
import json
import unittest

import embedding_lab  # noqa: F401, E402
import cluster_rerank as runtime  # noqa: E402
import vintage_matching as vintage  # noqa: E402
import test_cluster_rerank as baseline  # noqa: E402

A, B, C = baseline.A, baseline.B, baseline.C


def dated(**years):
    return {slug: {"years": {year}, "where": "test"} for slug, year in years.items()}


class PolicyTest(unittest.TestCase):
    def test_exact_vintage_has_priority_over_the_undated_variant(self):
        out, audit = vintage.prefer_year(["undated", "wrong", "exact"], {"q1": "2020"},
                                         dated(exact="2020", wrong="2024"), ["undated"])
        self.assertEqual(out, ["exact", "undated", "wrong"])
        self.assertEqual(audit["reason"], "exact_year")

    def test_unlisted_vintage_prefers_the_undated_variant(self):
        out, audit = vintage.prefer_year(["wrong", "undated"], {"q1": "2020"},
                                         dated(wrong="2024"), ["undated"])
        self.assertEqual(out, ["undated", "wrong"])
        self.assertEqual(audit["observed_year"], "2020")
        self.assertEqual(audit["reason"], "undated_fallback")

    def test_no_visible_year_is_neutral(self):
        original = ["wrong", "undated"]
        out, audit = vintage.prefer_year(original, {"q1": None}, dated(wrong="2024"), ["undated"])
        self.assertEqual(out, original)
        self.assertEqual(audit["preferred"], [])

    def test_no_available_exact_or_undated_candidate_keeps_the_order(self):
        original = ["a", "b"]
        out, audit = vintage.prefer_year(original, {"q1": "2020"}, dated(a="2024", b="2023"), [])
        self.assertEqual(out, original)
        self.assertEqual(audit["reason"], "no_eligible_variant")

    def test_multiple_exact_variants_preserve_their_prior_order(self):
        out, _ = vintage.prefer_year(["wrong", "b", "a", "undated"], {"q1": "2020"},
                                    dated(wrong="2024", a="2020", b="2020"), ["undated"])
        self.assertEqual(out, ["b", "a", "wrong", "undated"])

    def test_multiple_undated_variants_preserve_their_prior_order(self):
        out, _ = vintage.prefer_year(["wrong", "b", "a"], {"q1": "2020"},
                                    dated(wrong="2024"), ["a", "b"])
        self.assertEqual(out, ["b", "a", "wrong"])

    def test_conflicting_readings_are_neutral(self):
        out, audit = vintage.prefer_year(["a", "b"], {"q1": "2020", "q2": "2024"},
                                         dated(a="2024", b="2020"), [])
        self.assertEqual(out, ["a", "b"])
        self.assertEqual(audit["reason"], "conflicting_years")

    def test_one_visible_reading_and_one_null_can_identify_a_year(self):
        out, _ = vintage.prefer_year(["a", "b"], {"q1": None, "q2": "2020"},
                                    dated(a="2024", b="2020"), [])
        self.assertEqual(out, ["b", "a"])

    def test_malformed_readings_do_not_select_a_variant(self):
        for value in (True, 0, 2020, "other", "2020/2024", "not visible", {"2020": 100}):
            with self.subTest(value=value):
                out, audit = vintage.prefer_year(["a", "b"], {"q1": value}, dated(a="2024"), ["b"])
                self.assertEqual(out, ["a", "b"])
                self.assertEqual(audit["reason"], "invalid_readout")

    def test_dated_metadata_does_not_count_as_undated(self):
        out, audit = vintage.prefer_year(["a", "b"], {"q1": "2020"}, dated(a="2024", b="2023"), ["b"])
        self.assertEqual(out, ["a", "b"])
        self.assertEqual(audit["undated"], [])


class BackendTest(unittest.TestCase):
    make = baseline.BackendTest.make

    def run_case(self, answer, year="2024", candidates=None, the_rule=None):
        r = the_rule or baseline.sheet_rule(slugs=(A, B), kind="vintage", answers={A: "other", B: year})
        cands = candidates or [{"slug": B, "score": 0.95}, {"slug": A, "score": 0.40}]
        fake = baseline.FakeVlm(json.dumps(answer))
        backend = self.make([r], (cands, 10, 200, None, None), fake)
        backend.vintage_catalogue[B]["name"] = "Wine " + year
        out = backend.ask("p")[0]
        return out, out[0]["explain"], fake

    def test_actual_year_is_extracted_without_candidate_year_options(self):
        out, explain, fake = self.run_case({"q1": "2020"})
        self.assertEqual([c["slug"] for c in out], [A, B])
        prompt = fake.calls[0]["content"][1]["text"]
        self.assertNotIn("2024", prompt)
        self.assertNotIn("Options:", prompt)
        self.assertEqual(fake.calls[0]["schema"]["properties"]["q1"]["type"], ["string", "null"])
        self.assertEqual(explain["raw_vintage_years"], {"q1": "2020"})
        self.assertEqual(explain["vintage_match"]["reason"], "undated_fallback")
        self.assertEqual(explain["option_scores"], {})
        self.assertEqual(explain["evidence_scores"], {A: 0.0, B: 0.0})
        self.assertEqual([c["score"] for c in out], [0.95, 0.40])

    def test_exact_year_wins_over_a_large_embedding_margin(self):
        out, explain, _ = self.run_case({"q1": "2020"}, year="2020",
                                       candidates=[{"slug": A, "score": 0.99}, {"slug": B, "score": 0.10}])
        self.assertEqual([c["slug"] for c in out], [B, A])
        self.assertEqual(explain["vintage_match"]["reason"], "exact_year")

    def test_unreadable_year_does_not_select_the_undated_card(self):
        out, explain, _ = self.run_case({"q1": None})
        self.assertEqual([c["slug"] for c in out], [B, A])
        self.assertEqual(explain["vintage_match"]["reason"], "not_visible")

    def test_incomplete_metadata_does_not_prove_an_undated_variant(self):
        r = baseline.sheet_rule(slugs=(A, B), kind="vintage", answers={A: "other", B: "2024"})
        fake = baseline.FakeVlm('{"q1":"2020"}')
        backend = self.make([r], (baseline.cands(B, A), 10, 200, None, None), fake)
        backend.vintage_catalogue[B]["name"] = "Wine 2024"
        backend.book.descriptions = {}
        out = backend.ask("p")[0]
        self.assertEqual([c["slug"] for c in out], [B, A])
        self.assertEqual(out[0]["explain"]["vintage_match"]["reason"], "no_eligible_variant")

    def test_other_features_keep_their_score_distributions(self):
        r = baseline.sheet_rule(slugs=(A, B), kind="vintage", answers={A: "other", B: "2024"})
        r["questions"].append({"id": "q2", "question": "Sugar?", "kind": "feature", "valid": True,
                                "answers": {A: "dry", B: "semi-dry"}})
        feature_scores = {"dry": 0, "semi-dry": 95, "other": 3, "not visible": 2}
        out, explain, _ = self.run_case({"q1": "2020", "q2": feature_scores}, the_rule=r)
        self.assertEqual([c["slug"] for c in out], [A, B])
        self.assertEqual(explain["option_scores"], {"q2": feature_scores})
        self.assertEqual(explain["vintage_match"]["reason"], "undated_fallback")

    def test_other_wines_keep_their_positions(self):
        candidates = [{"slug": B, "score": 0.95}, {"slug": C, "score": 0.85}, {"slug": A, "score": 0.70}]
        out, _, _ = self.run_case({"q1": "2020"}, candidates=candidates)
        self.assertEqual([c["slug"] for c in out], [A, C, B])
        self.assertNotIn("explain", out[1])

    def test_legacy_vintage_scores_are_rejected_and_preserved_raw(self):
        raw = {"q1": {"other": 0, "2024": 0, "not visible": 0}}
        out, explain, fake = self.run_case(raw)
        self.assertEqual([c["slug"] for c in out], [B, A])
        self.assertTrue(explain["error"])
        self.assertEqual(len(fake.calls), 2)
        self.assertEqual(explain["raw_vintage_years"], raw)
        self.assertFalse(fake.calls[1]["cache_read"])

    def test_missing_vintage_id_keeps_the_base_order(self):
        out, explain, _ = self.run_case({})
        self.assertEqual([c["slug"] for c in out], [B, A])
        self.assertTrue(explain["error"])

    def test_slug_year_and_no_year_tags_supply_candidate_metadata(self):
        backend = self.make([baseline.sheet_rule(slugs=(A, B), kind="vintage", answers={A: "other", B: "2020"})],
                            (baseline.cands(A, B), 10, 200, None, None), baseline.FakeVlm('{"q1":"2020"}'))
        backend.vintage_catalogue[B]["tags"] = ["vintage:2020"]
        backend.vintage_catalogue[A]["tags"] = ["no_year"]
        backend.book.descriptions = {}
        out = backend.ask("p")[0]
        self.assertEqual([c["slug"] for c in out], [B, A])
        self.assertEqual(out[0]["explain"]["vintage_match"]["reason"], "exact_year")

    def test_laya_keeps_its_supported_vintage_score_contract(self):
        r = baseline.sheet_rule(slugs=(A, B), kind="vintage", answers={A: "other", B: "2024"})
        raw = {"q1": {"other": 0, "2024": 100, "not visible": 0}}
        fake = baseline.FakeVlm(json.dumps(raw))
        backend = self.make([r], (baseline.cands(A, B), 10, 200, None, None), fake)
        backend.entry = backend.entry._replace(protocol="laya-v")
        out = backend.ask("p")[0]
        self.assertIsNone(out[0]["explain"]["error"])
        self.assertNotIn("vintage_match", out[0]["explain"])
        self.assertEqual(out[0]["explain"]["option_scores"], raw)
        self.assertEqual(fake.calls[0]["schema"], runtime.score_schema(r))


if __name__ == "__main__":
    unittest.main()
