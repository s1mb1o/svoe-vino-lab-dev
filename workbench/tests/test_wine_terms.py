"""Engine-independent wine vocabulary and bounded OCR corrections."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import wine_terms
import variant_attributes as attrs


class WineTermChecks(unittest.TestCase):
    def test_owner_examples_and_visual_lookalikes(self):
        cases = {"MYCKАТ": "мускат", "MYCKAT": "мускат", "МYСКАТ": "мускат",
                 "Са8иньо бланк": "совиньон-блан", "С0ВИНЬОН БЛАНК": "совиньон-блан",
                 "БPЮT": "брют", "ПОЛYСЛАДК0Е": "полусладкое", "MЕРЛО": "мерло"}
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(wine_terms.normalize(raw), expected)

    def test_multilingual_and_compound_terms_keep_specificity(self):
        cases = {"Sauvignon Blanc": "sauvignon_blanc", "Са8иньо бланк": "sauvignon_blanc",
                 "Каберне Савиньон": "cabernet_sauvignon", "MYCKАТ Белый": "muscat_white",
                 "Müller-Thurgau": "muller_thurgau", "Мюллер Тургау": "muller_thurgau",
                 "Pinot Noir": "pinot_noir", "Кабернет": "cabernet"}
        for raw, expected in cases.items():
            self.assertEqual(attrs.parsed(raw)["grapes"], [expected], raw)
        self.assertEqual(attrs.parsed("Ркацители-Мюллер-Тургау-Шардоне")["grapes"],
                         ["chardonnay", "muller_thurgau", "rkatsiteli"])
        self.assertIsNone(attrs.parsed("Са8иньо бланк")["colour"])
        self.assertEqual(attrs.parsed("Sauvignon")["grapes"], ["sauvignon"])

    def test_sugar_classes_and_qualifiers_remain_distinct(self):
        cases = {"ЭКСТРА-БPЮT": "extra_brut", "BRUT NATURE": "brut_nature",
                 "EXTRA DRY": "extra_dry", "DEMI-SEC": "demi_sec",
                 "полу сухое": "semi_dry", "ПОЛYСЛАДК0Е": "semi_sweet",
                 "СУХОЙ": "dry", "semi sweet": "semi_sweet"}
        for raw, expected in cases.items():
            self.assertEqual(attrs.sugar(raw), expected, raw)
        self.assertIsNone(attrs.sugar("БPЮT ПОЛYСЛАДК0Е"))

    def test_unknown_words_numbers_and_substrings_are_not_guessed(self):
        for raw in ("BRUTAL", "MYCKAT123", "MYC", "Са8иньоXYZ", "brand 2025 12"):
            self.assertEqual(wine_terms.normalize(raw), wine_terms.base_text(raw))
        self.assertEqual(attrs.parsed("MYC")['grapes'], None)
        self.assertIsNone(attrs.parsed("MYCKAT123")["grapes"])

    def test_dictionary_canonical_forms_are_idempotent_and_unique(self):
        ids = []
        for field in ("grapes", "sugar"):
            for term in wine_terms.LEXICON[field]:
                ids.append(term["id"])
                normalized = wine_terms.normalize(term["canonical"])
                self.assertEqual(normalized, term["canonical"])
                self.assertEqual(attrs.parsed(normalized)[field], [term["id"]])
        self.assertEqual(len(ids), len(set(ids)))

    def test_raw_confidence_geometry_and_uncertainty_are_preserved(self):
        words = [{"text": "MYCKАТ", "confidence": 20, "polygon": [[1, 2]]}]
        original = copy.deepcopy(words)
        evidence = wine_terms.evidence(words)
        self.assertEqual(evidence["corrections"][0]["confidence"], 20)
        self.assertEqual(evidence["corrections"][0]["raw"], "MYCKАТ")
        self.assertEqual(words, original)
        observed, reasons = attrs.observed(words, 70)
        self.assertIsNone(observed["grapes"])
        self.assertEqual(reasons["grapes"], "uncertain_or_conflicting_text")
        values, _ = attrs.observed([{"text": "EXTRA", "confidence": 20},
                                   {"text": "БPЮT", "confidence": 99}], 70)
        self.assertIsNone(values["sugar"])


if __name__ == "__main__":
    unittest.main()
