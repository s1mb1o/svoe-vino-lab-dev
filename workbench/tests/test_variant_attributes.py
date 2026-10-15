"""Wine variant fields, partial evidence and explicit contradiction checks."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import variant_attributes as attrs


class AttributeChecks(unittest.TestCase):
    def test_shared_dictionary_normalizes_grapes_and_complete_catalogue_blend(self):
        self.assertEqual(attrs.parsed("MYCKАТ Са8иньо бланк")["grapes"], ["muscat", "sauvignon_blanc"])
        values, complete = attrs.expected({"grapes": "Мюллер-Тургау, Ркацители, Шардоне"})
        self.assertEqual(values["grapes"], ["chardonnay", "muller_thurgau", "rkatsiteli"])
        self.assertTrue(complete)

    def test_bilingual_attributes_and_accents(self):
        result = attrs.parsed("BRUT Caberne ROSÉ Réserve Кошерное")
        self.assertEqual(result, {"sugar": ["brut"], "grapes": ["cabernet"],
                                  "colour": ["rose"], "line": ["kosher", "reserve"]})
        self.assertEqual(attrs.parsed("Сухой Красностоп Золотовский Розовый Резервный"),
                         {"sugar": ["dry"], "grapes": ["krasnostop_zolotovsky"],
                          "colour": ["rose"], "line": ["reserve"]})
        self.assertEqual(attrs.parsed("Краснтоп")["grapes"], ["krasnostop"])

    def test_compound_grapes_do_not_establish_wine_colour(self):
        for text, grape in [("Sauvignon Blanc", "sauvignon_blanc"), ("Пино Блан", "pinot_blanc"),
                            ("Мускат Белый", "muscat_white"), ("Traminer Rose", "traminer_pink")]:
            result = attrs.parsed(text)
            self.assertEqual(result["grapes"], [grape])
            self.assertIsNone(result["colour"])

    def test_long_sugar_phrases_do_not_become_shorter_classes(self):
        for text, value in [("extra brut", "extra_brut"), ("semi-dry", "semi_dry"),
                            ("semi-sweet", "semi_sweet"), ("Demi-Sec", "demi_sec"),
                            ("extra dry", "extra_dry"), ("BRUT NATURE", "brut_nature")]:
            self.assertEqual(attrs.sugar(text), value)
        self.assertIsNone(attrs.sugar("BRUT Полусладкое"))

    def test_low_confidence_qualifier_invalidates_only_its_field(self):
        words = [{"text": "EXTRA", "confidence": 20}, {"text": "BRUT", "confidence": 99},
                 {"text": "MERLOT", "confidence": 99}]
        observed, reason = attrs.observed(words, 70)
        self.assertIsNone(observed["sugar"])
        self.assertEqual(observed["grapes"], ["merlot"])
        self.assertEqual(reason["sugar"], "uncertain_or_conflicting_text")

    def test_low_confidence_grape_qualifier_cannot_change_variety_or_colour(self):
        for words in [[{"text": "CABERNET", "confidence": 20}, {"text": "SAUVIGNON", "confidence": 99}],
                      [{"text": "SAUVIGNON", "confidence": 20}, {"text": "BLANC", "confidence": 99}]]:
            observed, _ = attrs.observed(words, 70)
            self.assertIsNone(observed["grapes"])
            self.assertIsNone(observed["colour"])

    def test_broad_grape_does_not_pick_a_specific_variety(self):
        self.assertEqual(attrs.compare("grapes", ["cabernet"], ["cabernet_franc"], True), "match")
        self.assertEqual(attrs.compare("grapes", ["cabernet"], ["cabernet_sauvignon"], True), "match")
        self.assertEqual(attrs.compare("grapes", ["cabernet_franc"], ["cabernet_sauvignon"], True), "conflict")
        self.assertEqual(attrs.compare("grapes", ["pinot_blanc"], ["pinot_noir"], True), "conflict")

    def test_partial_grape_read_is_compatible_with_a_blend(self):
        self.assertEqual(attrs.compare("grapes", ["merlot"], ["merlot", "cabernet_sauvignon"], True), "match")
        self.assertEqual(attrs.compare("grapes", ["merlot", "cabernet_sauvignon"], ["merlot"], True), "conflict")
        self.assertEqual(attrs.compare("grapes", ["merlot", "cabernet_sauvignon"], ["merlot"], False), "unknown")

    def test_incomplete_catalogue_blend_cannot_establish_absent_grape(self):
        values, complete = attrs.expected({"grapes": "Каберне Совиньон, Голубок"})
        self.assertEqual(values["grapes"], ["cabernet_sauvignon"])
        self.assertFalse(complete)
        self.assertEqual(attrs.compare("grapes", ["krasnostop"], values["grapes"], complete), "unknown")

    def test_colour_descriptions_are_not_categorical_colour(self):
        for text in ["Золотистый", "Белый жемчуг с лимонным отливом", "Рубиновый", "Золотой с розовым блеском"]:
            self.assertIsNone(attrs.expected({"color": text})[0]["colour"])
        self.assertEqual(attrs.expected({"color": "Белое"})[0]["colour"], ["white"])
        self.assertEqual(attrs.expected({"slug": "brand-shardone-beloe-suhoe"})[0]["colour"], ["white"])
        self.assertIsNone(attrs.expected({"name": "Розовое", "color": "Белое"})[0]["colour"])

    def test_explicit_catalogue_sugar_precedes_legacy_slug_category(self):
        record = {"name": "Victor Dravigny. Extra Brut",
                  "slug": "abrau-dyurso-victor-dravigny-extra-brut-shardone-beloe-bryut-125"}
        self.assertEqual(attrs.expected(record)[0]["sugar"], ["extra_brut"])
        self.assertEqual(attrs.expected({"name": "Brand", "slug": "brand-polusladkoe"})[0]["sugar"], ["semi_sweet"])
        self.assertIsNone(attrs.expected({"name": "BRUT Полусладкое", "slug": "brand-brut"})[0]["sugar"])

    def test_series_absence_is_unknown_and_negation_is_not_positive(self):
        self.assertEqual(attrs.compare("line", ["kosher"], None), "unknown")
        self.assertEqual(attrs.compare("line", ["reserve"], ["kosher"]), "unknown")
        self.assertEqual(attrs.compare("line", ["reserve"], ["grand_reserve"]), "match")
        self.assertEqual(attrs.compare("line", ["grand_reserve"], ["reserve"]), "unknown")
        self.assertIsNone(attrs.parsed("non-kosher")["line"])
        self.assertIsNone(attrs.parsed("не кошерное")["line"])


class RankingChecks(unittest.TestCase):
    OPTIONS = {"window": 10, "min_confidence": 70}

    @staticmethod
    def rows(*slugs):
        return [{"slug": slug, "rank": i + 1, "score": .99 - i * .01} for i, slug in enumerate(slugs)]

    def verify(self, rows, text, catalog):
        return attrs.verify(rows, [{"text": text, "confidence": 99}], catalog, self.OPTIONS)

    def test_corrected_term_changes_ranking_but_keeps_raw_ocr_and_cosines(self):
        rows = self.rows("saperavi", "muscat")
        words = [{"text": "MYCKАТ", "confidence": 97.78, "polygon": [[1, 2]]}]
        result, evidence = attrs.verify(rows, words, {
            "saperavi": {"grapes": "Саперави"}, "muscat": {"grapes": "Мускат"}}, self.OPTIONS)
        self.assertEqual([r["slug"] for r in result], ["muscat", "saperavi"])
        self.assertEqual(result[0]["score"], rows[1]["score"])
        self.assertEqual(evidence["words"], words)
        self.assertEqual(evidence["normalization"]["text"], "мускат")
        self.assertEqual(evidence["normalization"]["corrections"][0]["confidence"], 97.78)

    def test_unknown_metadata_cannot_lose_to_a_better_described_neighbour(self):
        for text, catalog in [
                ("EXTRA BRUT", {"unknown": {"name": "Cuvee"},
                                "match": {"name": "Extra Brut"}, "conflict": {"name": "Brut"}}),
                ("MYCKАТ", {"unknown": {"name": "Kaffa"},
                            "match": {"grapes": "Мускат"}, "conflict": {"grapes": "Саперави"}})]:
            rows = self.rows("unknown", "conflict", "match")
            result, evidence = self.verify(rows, text, catalog)
            self.assertEqual([r["slug"] for r in result], ["unknown", "match", "conflict"])
            self.assertEqual(evidence["candidate_attributes"]["unknown"][
                "grapes" if text == "MYCKАТ" else "sugar"]["status"], "unknown")

    def test_sugar_match_does_not_overrule_grape_contradiction(self):
        rows = self.rows("wrong", "right")
        catalog = {"wrong": {"name": "Брют", "grapes": "Каберне Совиньон"},
                   "right": {"name": "Брют", "grapes": "Красностоп"}}
        result, evidence = self.verify(rows, "БРЮТ Красностоп", catalog)
        self.assertEqual([r["slug"] for r in result], ["right", "wrong"])
        self.assertEqual(evidence["discriminating_fields"], ["grapes"])
        self.assertEqual(evidence["candidate_attributes"]["wrong"]["grapes"]["status"], "conflict")
        self.assertFalse(evidence["candidate_attributes"]["right"]["sugar"]["discriminating"])

    def test_one_contradiction_dominates_several_positive_matches(self):
        rows = self.rows("wrong", "right", "semi")
        catalog = {"wrong": {"name": "Брют Rose Reserve", "grapes": "Мерло"},
                   "right": {"name": "Брют Red Reserve", "grapes": "Мерло"},
                   "semi": {"name": "Полусладкое White", "grapes": "Каберне Совиньон"}}
        result, _ = self.verify(rows, "Брют Merlot Red Reserve", catalog)
        self.assertEqual(result[0]["slug"], "right")
        self.assertEqual(result[1]["variant_text"]["status"], "conflict")
        self.assertEqual(result[1]["variant_text"]["attributes"]["colour"]["status"], "conflict")

    def test_kosher_presence_promotes_match_without_negative_inference(self):
        rows = self.rows("regular", "kosher")
        result, evidence = self.verify(rows, "Кошерное БРЮТ", {
            "regular": {"name": "Брют"}, "kosher": {"name": "Кошерное брют"}})
        self.assertEqual([r["slug"] for r in result], ["kosher", "regular"])
        self.assertEqual(evidence["conflicts"], [])
        self.assertEqual(result[1]["variant_text"]["attributes"]["line"]["status"], "unknown")

    def test_absent_line_word_does_not_reject_reserved_wine(self):
        rows = self.rows("reserve", "regular")
        result, evidence = self.verify(rows, "MERLOT", {
            "reserve": {"name": "Reserve", "grapes": "Мерло"},
            "regular": {"name": "Classic", "grapes": "Мерло"}})
        self.assertEqual(result, rows)
        self.assertFalse(evidence["applied"])

    def test_brand_and_vintage_do_not_confirm_variant(self):
        rows = self.rows("A", "B")
        result, evidence = self.verify(rows, "Абрау Дюрсо Victor Dravigny 1870 2022", {
            "A": {"name": "Victor Dravigny Брют"}, "B": {"name": "Victor Dravigny Полусладкое"}})
        self.assertEqual(result, rows)
        self.assertFalse(evidence["applied"])

    def test_same_attributes_and_broad_family_preserve_visual_order(self):
        rows = self.rows("franc", "sauvignon")
        result, evidence = self.verify(rows, "CABERNE", {
            "franc": {"grapes": "Каберне Фран"}, "sauvignon": {"grapes": "Каберне Совиньон"}})
        self.assertEqual(result, rows)
        self.assertFalse(evidence["applied"])

    def test_all_conflicting_candidates_preserve_visual_order(self):
        rows = self.rows("A", "B")
        result, evidence = self.verify(rows, "MERLOT", {
            "A": {"grapes": "Каберне Совиньон"}, "B": {"grapes": "Красностоп"}})
        self.assertEqual(result, rows)
        self.assertFalse(evidence["applied"])
        self.assertEqual(evidence["conflicts"], ["A", "B"])

    def test_complete_match_precedes_partial_and_unknown_matches(self):
        rows = self.rows("partial", "complete", "conflict")
        result, _ = self.verify(rows, "Merlot Red Reserve", {
            "partial": {"grapes": "Мерло", "color": "Red"},
            "complete": {"name": "Reserve", "grapes": "Мерло", "color": "Red"},
            "conflict": {"grapes": "Красностоп", "color": "Rose"}})
        self.assertEqual([r["slug"] for r in result], ["complete", "partial", "conflict"])
        self.assertEqual(result[1]["variant_text"]["status"], "partial_match")

    def test_scores_ties_inputs_and_window_are_preserved(self):
        rows = self.rows("wrong", "right", "same", "tail")
        options = dict(self.OPTIONS, window=3)
        catalog = {"wrong": {"name": "Red"}, "right": {"name": "Rose"},
                   "same": {"name": "Rose"}, "tail": {"name": "Rose"}}
        result, _ = attrs.verify(rows, [{"text": "Rosé", "confidence": 99}], catalog, options)
        self.assertEqual([r["slug"] for r in result], ["right", "same", "wrong", "tail"])
        self.assertEqual({r["slug"]: r["score"] for r in result}, {r["slug"]: r["score"] for r in rows})
        self.assertEqual(rows, self.rows("wrong", "right", "same", "tail"))
        self.assertEqual(result[0]["variant_text"]["visual_rank"], 2)


if __name__ == "__main__":
    unittest.main()
