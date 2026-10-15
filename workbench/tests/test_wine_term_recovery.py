"""Recovery contracts for phrases, uncertainty and saved OCR evidence."""
import copy
from itertools import product
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import variant_attributes as attrs
import wine_term_recovery as recovery
import wine_terms


class RecoveryChecks(unittest.TestCase):
    def test_exact_mode_preserves_every_shared_language_alias(self):
        for field, identity, canonical, matcher, aliases in recovery.VOCABULARY:
            for alias in aliases:
                with self.subTest(alias=alias):
                    self.assertEqual(recovery.recover(alias, "exact")["text"], wine_terms.normalize(alias))

    def test_space_repairs_and_compound_names(self):
        for raw, identity in [("RIESL ING", "riesling"), ("CABERNETSAUVIGNON", "cabernet_sauvignon"),
                              ("EXTRABRUT", "extra_brut"), ("Ркаци тели", "rkatsiteli")]:
            result = recovery.recover(raw, "whitespace")
            self.assertEqual(result["corrections"][0]["identity"], identity)
        self.assertEqual(attrs.parsed(recovery.recover("Каберне-совиньон")["text"])["grapes"], ["cabernet_sauvignon"])

    def test_fuzzy_phrases_precede_exact_components(self):
        for raw, identity in [("Cabernet Sauvignno", "cabernet_sauvignon"),
                              ("EXTRA BRVT", "extra_brut"), ("CHARDONNAYY", "chardonnay")]:
            result = recovery.recover(raw)
            self.assertEqual(result["corrections"][0]["identity"], identity)
            self.assertEqual(result["corrections"][0]["method"], "fuzzy")
        self.assertEqual(recovery.recover("Cabernet Sauvignno", "whitespace")["corrections"], [])

    def test_families_short_terms_numbers_and_unknown_words_stay_unknown(self):
        for raw in ("Пино", "BRUTAL", "MYCKAT123", "Са8иньоXYZ", "MYC", "DRX", "2025 12"):
            self.assertEqual(recovery.recover(raw)["text"], wine_terms.normalize(raw))
        self.assertEqual(attrs.parsed(recovery.recover("Пино")["text"])["grapes"], ["pinot"])

    def test_ambiguity_uses_canonical_identities(self):
        # MERLO and MERLOT are two aliases of the same identity.
        self.assertEqual(recovery.recover("MERLLOT")["corrections"][0]["identity"], "merlot")
        # Similarity to two different Pinot varieties has an insufficient margin.
        self.assertIsNone(recovery._resolve("pinot branc", "grapes", "fuzzy", "damerau"))

    def test_distance_handles_unrestricted_transpositions(self):
        self.assertEqual(recovery.distance("CA", "ABC", "damerau"), 2)
        self.assertEqual(recovery.distance("noir", "nori", "damerau"), 1)
        self.assertEqual(recovery.distance("noir", "nori", "levenshtein"), 2)
        for size in range(4):
            for value in map("".join, product("ab", repeat=size)):
                self.assertEqual(recovery.distance(value, value, "damerau"), 0)
                self.assertEqual(recovery.distance(value, "", "damerau"), len(value))

    def test_words_merge_only_with_line_evidence_and_keep_lowest_confidence(self):
        words = [{"text": "RIESL", "confidence": 98, "box": [0, 0, 50, 10]},
                 {"text": "ING", "confidence": 25, "box": [55, 0, 80, 10]}]
        before = copy.deepcopy(words)
        result = recovery.recover_words(words, "whitespace")
        self.assertEqual(result["words"], [{"text": "рислинг", "confidence": 25}])
        self.assertEqual(result["corrections"][0]["source_words"], [0, 1])
        self.assertEqual(words, before)
        observed, _ = attrs.observed(result["words"], 70)
        self.assertIsNone(observed["grapes"])
        for second_box in ([55, 20, 80, 30], None):
            other = copy.deepcopy(words)
            if second_box is None:
                for word in other:
                    word.pop("box")
            else:
                other[1]["box"] = second_box
            self.assertEqual(recovery.recover_words(other, "whitespace")["corrections"], [])

    def test_blend_separators_and_line_breaks_do_not_join_fragments(self):
        for raw in ("RIESL, ING", "RIESL; ING", "RIESL\nING"):
            self.assertEqual(recovery.recover(raw)["corrections"], [])

    def test_exact_words_do_not_absorb_unrelated_letters(self):
        for raw in ("MERLOT A", "A MERLOT", "CHARDONNAY A", "е полусладкое"):
            self.assertEqual(recovery.recover(raw)["text"], wine_terms.normalize(raw))
            self.assertEqual(recovery.recover(raw)["corrections"], [])

    def test_meaningful_qualifier_is_not_fuzzed_into_another_class(self):
        self.assertEqual(recovery.recover("semi sec")["corrections"], [])
        self.assertEqual(recovery.recover("усладкое")["corrections"], [])

    def test_field_scope_does_not_search_other_attributes(self):
        self.assertEqual(recovery.recover("EXTRA BRVT", field="grapes")["corrections"], [])
        self.assertEqual(recovery.recover("RIESL ING", field="sugar")["corrections"], [])


class VerificationChecks(unittest.TestCase):
    OPTIONS = {"window": 10, "min_confidence": 70}
    ROWS = [{"slug": "wrong", "rank": 1, "score": .9}, {"slug": "right", "rank": 2, "score": .8}]

    def test_whitespace_repair_can_supply_exact_letter_contradiction(self):
        words = [{"text": "RIESL ING", "confidence": 99}]
        rows, evidence = recovery.verify(self.ROWS, words, {
            "wrong": {"grapes": "Шардоне"}, "right": {"grapes": "Рислинг"}}, self.OPTIONS, "whitespace")
        self.assertEqual(rows[0]["slug"], "right")
        self.assertEqual([row["score"] for row in rows], [.8, .9])
        self.assertEqual(evidence["conflicts"], ["wrong"])

    def test_fuzzy_evidence_does_not_create_a_conflict(self):
        rows, evidence = recovery.verify(self.ROWS, [{"text": "CHARDONNAYY", "confidence": 99}], {
            "wrong": {"grapes": "Рислинг"}, "right": {"grapes": "Шардоне"}}, self.OPTIONS)
        self.assertEqual(rows, self.ROWS)
        self.assertEqual(evidence["soft_fields"], ["grapes"])
        self.assertEqual(evidence["conflicts"], [])

    def test_absent_catalogue_identity_is_not_corrected_into_the_shortlist(self):
        _, evidence = recovery.verify(self.ROWS, [{"text": "RIESL ING", "confidence": 99}], {
            "wrong": {"grapes": "Шардоне"}, "right": {"grapes": "Мерло"}}, self.OPTIONS)
        self.assertEqual(evidence["observed_attributes"]["grapes"], ["riesling"])
        self.assertEqual(evidence["conflicts"], ["wrong", "right"])

    def test_fuzzy_addition_does_not_erase_an_explicit_contradiction(self):
        rows, evidence = recovery.verify(self.ROWS, [{"text": "MERLOT CHARDONNAYY", "confidence": 99}], {
            "wrong": {"grapes": "Рислинг"}, "right": {"grapes": "Мерло, Шардоне"}}, self.OPTIONS)
        self.assertEqual(evidence["conflicts"], ["wrong"])
        self.assertEqual(rows[0]["slug"], "right")

    def test_low_confidence_noise_does_not_invalidate_an_exact_read(self):
        _, evidence = recovery.verify(self.ROWS, [{"text": "MERLOT", "confidence": 99},
                                                 {"text": "CHARDONNAYY", "confidence": 0}], {}, self.OPTIONS)
        self.assertEqual(evidence["observed_attributes"]["grapes"], ["merlot"])
        self.assertEqual(evidence["recovery"]["corrections"], [])

    def test_uncertain_qualifier_does_not_become_shorter_sugar_class(self):
        for raw in ("SEM1 DRY", "BRUT NAT"):
            _, evidence = recovery.verify(self.ROWS, [{"text": raw, "confidence": 99}], {
                "wrong": {"name": "Dry"}, "right": {"name": "Semi dry"}}, self.OPTIONS)
            self.assertIsNone(evidence["observed_attributes"]["sugar"], raw)

    def test_low_confidence_fuzzy_qualifier_stays_unknown(self):
        words = [{"text": "EXTRA", "confidence": 20, "line_id": 1},
                 {"text": "BRVT", "confidence": 99, "line_id": 1}]
        _, evidence = recovery.verify(self.ROWS, words, {}, self.OPTIONS)
        self.assertIsNone(evidence["observed_attributes"]["sugar"])


if __name__ == "__main__":
    unittest.main()
