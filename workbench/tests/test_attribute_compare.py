"""Check semantic matches and conservative conflict decisions."""

import unittest
import attribute_compare as compare
import attribute_facts as facts


class ComparisonTest(unittest.TestCase):
    def result(self, field, left, right, beverage=None):
        return compare.outcome(
            field, left, compare.observed(right, " ".join(right)), beverage
        )

    def test_translations_match(self):
        for field, left, right in [
            ("grape", "Мускат", "Muscat"),
            ("colour", "Розовое", "Rosé"),
            ("sweetness", "полусладкое", "semi-sweet"),
            ("reserve", "Reserve", "Reserva"),
        ]:
            with self.subTest(field=field):
                self.assertEqual(self.result(field, [left], [right]), "match")

    def test_sweetness_requires_context_and_exact_term(self):
        self.assertEqual(
            self.result("sweetness", ["Demi-sec"], ["полусладкое"]), "unknown"
        )
        self.assertEqual(
            self.result("sweetness", ["Demi-sec"], ["полусладкое"], "44"), "match"
        )
        self.assertEqual(
            self.result("sweetness", ["Demi-sec"], ["полусладкое"], "4"), "unknown"
        )
        self.assertEqual(
            self.result("sweetness", ["extra brut"], ["brut"], "44"), "unknown"
        )
        self.assertEqual(
            self.result("sweetness", ["extra dry"], ["dry"], "44"), "unknown"
        )

    def test_partial_blend_does_not_establish_conflict(self):
        self.assertEqual(
            self.result("grape", ["Cabernet Sauvignon, Merlot"], ["Merlot"]), "unknown"
        )
        self.assertEqual(
            self.result("grape", ["Мускат"], ["Muscat Ottonel"]), "unknown"
        )
        self.assertEqual(
            self.result("grape", ["100% Pinot Noir"], ["Chardonnay"]), "conflict"
        )

    def test_barrel_duration_is_retained_and_equivalent_units_match(self):
        self.assertEqual(
            self.result("barrel", ["aged in oak 12 months"], ["aged in oak 24 months"]),
            "conflict",
        )
        self.assertEqual(
            self.result("barrel", ["aged in oak 12 months"], ["aged in oak 1 year"]),
            "match",
        )
        self.assertEqual(
            self.result("barrel", ["aged in oak"], ["aged in oak 12 months"]), "unknown"
        )

    def test_extra_information_is_not_a_conflict(self):
        self.assertEqual(self.result("kosher", [], ["кошерное"]), "image_only")
        self.assertEqual(
            compare.outcome("grape", ["Muscat"], facts.empty()["grape"]), "unknown"
        )
        self.assertEqual(
            compare.outcome(
                "grape",
                ["Muscat"],
                {"state": "not_visible", "values": [], "evidence": ""},
            ),
            "metadata_only",
        )

    def test_cached_colour_is_only_read_from_printed_text(self):
        result = compare.facts_from_texts(["Muscat", "полусладкое", "Розовое"], 2022)
        self.assertEqual(result["colour"]["values"], ["Розовое"])
        self.assertEqual(result["vintage"]["state"], "unknown")
        self.assertEqual(
            compare.facts_from_texts(["Since 1896"], 1896)["vintage"]["state"],
            "unknown",
        )
        self.assertEqual(
            compare.facts_from_texts(["Урожай 2022"], 2022)["vintage"]["values"],
            ["2022"],
        )

    def test_conflicting_years_are_unknown(self):
        self.assertEqual(self.result("vintage", ["2021", "2022"], ["2022"]), "unknown")
        self.assertEqual(self.result("vintage", ["2021"], ["2022"]), "conflict")

    def test_stale_evidence_is_not_compared(self):
        sha = "a" * 64
        record = {
            "name": "2021",
            "slug": "wine",
            "main_image_original_url": "/images/main/" + sha + ".jpg",
        }
        data = facts.empty()
        data["vintage"] = compare.observed(["2022"], "Урожай 2022")
        view = {sha: {"state": "failed", "stale": True, "facts": data}}
        comp = compare.comparison(record, view)
        self.assertEqual(comp["conflicts"], 0)
        self.assertTrue(all(r["result"] == "unknown" for r in comp["rows"]))

    def test_patch_is_effective_and_main_disagreement_is_visible(self):
        a, b = "a" * 64, "b" * 64
        data = facts.empty()
        data["vintage"] = compare.observed(["2022"], "2022")
        old = facts.empty()
        old["vintage"] = compare.observed(["2021"], "2021")
        record = {
            "slug": "wine-2022",
            "name": "Wine 2022",
            "main_image_original_url": f"/images/main/{a}.jpg",
            "_patch_url": f"/images/patched/{b}.jpg",
        }
        comp = compare.comparison(
            record,
            {a: {"state": "ready", "facts": old}, b: {"state": "ready", "facts": data}},
        )
        row = next(r for r in comp["rows"] if r["field"] == "vintage")
        self.assertEqual(
            (comp["sha256"], comp["source"], row["result"]), (b, "Patch image", "match")
        )
        self.assertTrue(row["image_disagreement"])
        self.assertEqual(comp["conflicts"], 0)
        self.assertEqual(comp["image_disagreements"], 1)

    def test_colour_in_brand_and_orange_name_stay_unknown(self):
        for value in ["Chateau Blanc", "Cabernet Blanc", "Orange"]:
            self.assertEqual(
                compare.facts_from_texts([value])["colour"]["state"], "unknown"
            )

    def test_generic_vintage_is_additional_image_information(self):
        self.assertEqual(
            self.result("vintage", ["Any vintage"], ["2022"]), "image_only"
        )

    def test_sweetness_reads_exact_slug_term(self):
        values = compare.metadata({"name": "Wine", "slug": "wine-krasnoe-suhoe"})
        self.assertEqual(values["sweetness"], ["suhoe"])

    def test_reserve_tier_does_not_silently_match(self):
        self.assertEqual(
            self.result("reserve", ["Reserva"], ["Gran Reserva"]), "unknown"
        )

    def test_barrel_oak_type_is_retained(self):
        self.assertEqual(
            self.result(
                "barrel",
                ["aged in French oak 12 months"],
                ["aged in American oak 12 months"],
            ),
            "unknown",
        )

    def test_grape_percentages_are_not_combined_across_sources(self):
        self.assertEqual(
            self.result("grape", ["Саперави 60%"], ["Cabernet Franc 40%"]), "unknown"
        )
        self.assertEqual(
            self.result("grape", ["Саперави 100%"], ["Cabernet Franc 40%"]), "conflict"
        )

    def test_barrel_year_and_decimal_duration(self):
        self.assertEqual(
            self.result(
                "barrel",
                ["Вино урожая 2019 года выдерживалось в дубовых бочках 12 месяцев"],
                ["12 месяцев в дубе"],
            ),
            "match",
        )
        self.assertEqual(
            self.result("barrel", ["1,5 года в дубе"], ["18 месяцев в дубе"]), "match"
        )
        self.assertEqual(
            self.result(
                "barrel",
                ["12 мес. в дубе и 6 месяцев в бутылке"],
                ["12 месяцев в дубе"],
            ),
            "match",
        )

    def test_claim_negation_does_not_cross_clauses(self):
        self.assertEqual(
            self.result("organic", ["Не фильтровано, органическое"], ["Organic"]),
            "match",
        )
        self.assertEqual(
            self.result("organic", ["Not only organic"], ["Organic"]), "match"
        )

    def test_brand_colour_and_sweetness_are_not_seeded(self):
        for value in [
            "Sauvignon Blanc",
            "White Zinfandel",
            "Orange Muscat",
            "Cheval Blanc",
            "Dry Creek",
        ]:
            data = compare.facts_from_texts([value])
            self.assertEqual(data["colour"]["state"], "unknown")
            self.assertEqual(data["sweetness"]["state"], "unknown")

    def test_unknown_grape_is_not_discarded_before_comparison(self):
        for value in [
            "Merlot, Tempranillo",
            "Merlot and Tempranillo",
            "Merlot-Tempranillo",
        ]:
            self.assertEqual(self.result("grape", ["Мерло 100%"], [value]), "unknown")
            extracted = compare.facts_from_texts([value])["grape"]
            self.assertEqual(
                compare.outcome("grape", ["Мерло 100%"], extracted), "unknown"
            )
