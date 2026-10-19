"""Regressions for the exact marginal cases, using the actual API and real index."""
import json
import copy
from pathlib import Path
import tempfile
import unittest

from dinner_lens.data import Knowledge
from dinner_lens.embeddings import EmbeddingIndex
from dinner_lens.engine import Engine
from dinner_lens.paths import default_dataset, default_index, default_style


class CompositionalGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.knowledge = Knowledge(default_dataset(), default_style())
        cls.engine = Engine(cls.knowledge, EmbeddingIndex(cls.knowledge, Path(__file__).resolve().parents[1] / "data/index.v4"), cursor_secret=b'compositional-regression-secret-at-least-32-bytes')
        cls.codes = {w['wine_slug']: w['id'] for w in json.loads(default_dataset().read_bytes())['wines']}

    def all_codes(self, node, attrs=None, filters=None):
        first = page = self.engine.recommend(node_id=node, confirmed_attributes=attrs, filters=filters)
        rows = list(page['results'])
        while page['next_cursor']:
            page = self.engine.more(page['next_cursor'])
            self.assertEqual(first['effective_profile_id'], page['effective_profile_id'])
            rows.extend(page['results'])
        self.assertEqual(len(rows), first['total_eligible'])
        self.assertEqual(len(rows), len({r['wine_slug'] for r in rows}))
        return {self.codes[r['wine_slug']] for r in rows}, rows

    def test_acidic_fish_soup_excludes_moderate_acid_curated_pinot_blanc(self):
        codes, rows = self.all_codes('astrakhan_fish_soup', {'acidity': 'high'})
        self.assertNotIn('F3', codes)
        self.assertGreaterEqual(len(rows), 5)
        self.assertIn('O4', codes)

    def test_raw_oysters_do_not_discover_round_ripe_pinot_gris(self):
        codes, rows = self.all_codes('oysters_lemon')
        self.assertNotIn('F4', codes)
        self.assertGreater(len(rows), 5)

    def test_hearty_beef_pepper_does_not_drift_to_light_pinot_or_rose(self):
        codes, rows = self.all_codes('wok_beef_black_pepper')
        self.assertFalse(codes & {'T1', 'T2', 'T3', 'T4', 'P2'})
        self.assertGreater(len(rows), 5)

    def test_meat_tomato_discovery_does_not_drift_to_delicate_rose(self):
        codes, rows = self.all_codes('pasta_bolognese')
        self.assertNotIn('T4', codes)
        self.assertGreater(len(rows), 5)

    def test_mushroom_umami_preserves_delicacy_and_earthy_options(self):
        codes, rows = self.all_codes('porcini_risotto')
        self.assertFalse(codes & {'R4', 'F1'})
        self.assertTrue({'P2', 'P3', 'K1'} <= codes)
        self.assertGreater(len(rows), 5)

    def test_cream_cannot_bypass_acid_or_mushroom_conflicts(self):
        codes, _ = self.all_codes('porcini_risotto', {'fatty_cream_sauce': True, 'acidity': 'high'})
        self.assertFalse(codes & {'R4', 'F1', 'F3'})
        codes, _ = self.all_codes('chicken_roast_herbs', {'fatty_cream_sauce': True, 'heat': 'high', 'acidity': 'high', 'sauce_sweetness': 'high'})
        self.assertNotIn('H2', codes)
        self.assertTrue({'H1', 'H5'} <= codes)

    def test_rejected_editorial_choices_cannot_reintroduce_weak_wines(self):
        node = 'wok_beef_black_pepper'
        curated = [e['wine_slug'] for e in self.knowledge.nodes[node]['curated']]
        codes, rows = self.all_codes(node, filters={'rejected_wine_slugs': curated})
        self.assertGreater(len(rows), 0)
        self.assertTrue(all(r['selection_source'] == 'embedding' for r in rows))
        self.assertFalse(codes & {'T1', 'T2', 'T3', 'T4', 'P2'})

    def test_invalid_qualitative_evidence_fails_at_startup(self):
        d = json.loads(default_dataset().read_bytes())
        d['suitability_policy']['wines'][0]['qualitative_traits']['acidity'] = 'measured_7.8'
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / 'invalid.json'
            file.write_text(json.dumps(d))
            with self.assertRaisesRegex(ValueError, 'qualitative traits'):
                Knowledge(file, default_style())

    def test_strong_acid_requires_positive_source_evidence_on_every_page(self):
        _, rows = self.all_codes('ribeye_grilled', {'acidity': 'high'})
        self.assertTrue(rows)
        for row in rows:
            traits = self.knowledge.wine_style_annotations[row['wine_slug']]['qualitative_traits']
            self.assertIn(traits['acidity'], {'fresh', 'pronounced'})

    def test_unverifiable_extreme_dessert_sauce_returns_no_fillers(self):
        result = self.engine.recommend(node_id='chocolate_fondant', confirmed_attributes={'heat': 'high', 'acidity': 'high'})
        self.assertEqual(result['results'], [])
        self.assertIsNone(result['next_cursor'])
        self.assertTrue(result['needs_clarification'])

    def test_cream_preserves_duck_profile_and_red_options(self):
        for node in ['duck_breast_cherry', 'duck_confit_lingonberry', 'duck']:
            for attrs in [{'fatty_cream_sauce': True}, {'fatty_cream_sauce': True, 'acidity': 'high'}]:
                with self.subTest(node=node, attrs=attrs):
                    result = self.engine.recommend(node_id=node, confirmed_attributes=attrs)
                    self.assertEqual(result['effective_profile_id'], 'duck_berry')
                    _, rows = self.all_codes(node, attrs)
                    self.assertTrue(rows)
                    self.assertTrue(all(r['facts']['color'] == 'red' for r in rows))

    def test_intrinsic_sourness_survives_cream_without_repeated_flag(self):
        for node in ['vologda_grey_shchi', 'rassolnik_beef', 'seabass_ceviche', 'squid_steamed_lemon',
                     'vinaigrette_salad', 'gazpacho', 'greek_salad_feta']:
            for attrs in [{}, {'fatty_cream_sauce': True}]:
                with self.subTest(node=node, attrs=attrs):
                    codes, rows = self.all_codes(node, attrs)
                    self.assertTrue(rows)
                    self.assertNotIn('F3', codes)
                    self.assertNotIn('K2', codes)
                    self.assertTrue(all(self.knowledge.wine_style_annotations[r['wine_slug']]['qualitative_traits']['acidity'] in {'fresh','pronounced'} for r in rows))
        result = self.engine.recommend(node_id='seabass_ceviche', confirmed_attributes={'acidity':'low'})
        self.assertEqual(result['diagnostics']['sauce_rule_context']['effective_rule_attributes']['acidity'], 'low')
        result = self.engine.recommend(node_id='avocado_maki')
        self.assertNotIn('acidity', result['diagnostics']['sauce_rule_context']['effective_rule_attributes'])

    def test_raw_shellfish_guard_reaches_parent_and_photo_demotion(self):
        result = page = self.engine.recommend_from_recognition({'visual_node_id':'oysters_lemon'})
        self.assertEqual(result['resolved_node_id'], 'raw_bivalves')
        self.assertTrue(result['needs_clarification'])
        rows = list(page['results'])
        while page['next_cursor']:
            page = self.engine.more(page['next_cursor']); rows.extend(page['results'])
        codes = {self.codes[r['wine_slug']] for r in rows}
        self.assertFalse(codes & {'F4','F5'})
        direct, _ = self.all_codes('raw_bivalves')
        self.assertEqual(codes, direct)

    def test_generic_spicy_reasons_do_not_invent_coconut_or_sweetness(self):
        for node,attrs in [('chicken_roast_herbs',{'heat':'high'}), ('spicy_butter_chicken',{})]:
            _,rows = self.all_codes(node,attrs)
            self.assertTrue(rows)
            self.assertTrue(all('кокос' not in r['reason'].casefold() and 'подтверждённая сладость' not in r['reason'].casefold() for r in rows))

    def test_reviewed_full_acid_white_can_match_cream(self):
        codes,_ = self.all_codes('king_crab_steamed_butter', {'fatty_cream_sauce':True,'acidity':'high'})
        self.assertIn('F5', codes)

    def test_high_glaze_can_use_semisweet_without_requiring_chilli(self):
        codes,_ = self.all_codes('chicken_teriyaki', {'sauce_sweetness':'high'})
        self.assertIn('H2', codes)

    def test_default_style_conditions_are_consistent_for_curated_and_discovery(self):
        knowledge = copy.deepcopy(self.knowledge)
        knowledge.nodes['poultry']['pairing_reference_attributes']['poultry_style']='duck'
        engine = Engine(knowledge, self.engine.index, cursor_secret=b'default-gate-tests-only-secret-at-least-32-bytes')
        first = engine.recommend(node_id='poultry')
        rows = list(first['results']); page = first
        while page['next_cursor']:
            page = engine.more(page['next_cursor']); rows.extend(page['results'])
        red = [r for r in rows if r['facts']['color']=='red']
        self.assertTrue(red)
        self.assertTrue(any(r['selection_source']=='curated' for r in red))


if __name__ == '__main__':
    unittest.main()
