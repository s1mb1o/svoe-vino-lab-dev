"""Check label evidence, unsupported variants, and partial dependency failures."""

from io import BytesIO
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image
import yaml

from matcher.group_quality import (LabelEvidence, color_class, conflicts,
                                  merge_label_reads, needs_label_read, normalized,
                                  semantic_rank, sugar_class)
from matcher.group_quality_runtime import (QualityGroupMatcher, body_label_view,
                                          high_resolution_crops)
from matcher.group import GroupMatchError, segment_group, _validate_sam3
from test_group import image_bytes, sam3_answer, FakeOpener
from test_match import write_bundle_v2


def card(name, sugar="Сухое", color="Белое", producer="North Estate"):
    return {"name": name, "sugar": sugar, "color": color,
            "category": "Вино", "producer": producer, "grapes": "Шардоне"}


class EvidenceTest(unittest.TestCase):
    def test_cyrillic_latin_and_sugar_classes(self):
        self.assertEqual(normalized("Шардоне Sauvignon"), "shardone sovinon")
        self.assertEqual(sugar_class("ПОЛУСЛАДКОЕ"), "semi_sweet")
        self.assertEqual(sugar_class("moelleux"), "semi_sweet")
        self.assertEqual(sugar_class("EXTRA BRUT"), "extra_brut")
        self.assertEqual(sugar_class("БРЮТ"), "brut")
        self.assertEqual(color_class("РОЗОВОЕ"), "rose")

    def test_parser_rejects_invented_types_and_accepts_fences(self):
        self.assertEqual(LabelEvidence.parse('```json\n{"front_label":false}\n```').text, "")
        for answer in ({"front_label": "false"}, {"front_label": True, "text": []},
                       {"front_label": True, "brand": "a"*3001}, "broken"):
            with self.subTest(answer=str(answer)[:50]), self.assertRaises(ValueError):
                LabelEvidence.parse(answer)

    def test_only_printed_attributes_veto_visual_candidates(self):
        e = LabelEvidence(True, "North Estate полусладкое розовое", color="white")
        self.assertTrue(conflicts(e, "north-brut", card("Classic", "Брют")))
        self.assertTrue(conflicts(e, "north-white", card("Classic", "Полусладкое")))
        self.assertFalse(conflicts(e, "north-rose", card("Classic", "Полусладкое", "Розовое")))
        self.assertFalse(conflicts(LabelEvidence(True, "North Estate", sugar="brut"),
                                   "north-dry", card("Classic")))

    def test_visible_range_beats_the_stronger_lookalike_and_scores_stay_ordered(self):
        cards = {"north-classic": card("Classic"), "north-reserve": card("Reserve")}
        e = LabelEvidence(True, "NORTH ESTATE CLASSIC CHARDONNAY", "North Estate", "Classic", grapes="Chardonnay")
        result = semantic_rank([("north-reserve", .96), ("north-classic", .89)], e, cards)
        self.assertEqual(result[0][0], "north-classic")
        self.assertEqual([score for _, score in result], sorted((s for _, s in result), reverse=True))

    def test_unreadable_and_brand_only_segments_do_not_get_a_wine(self):
        cards = {"north-brut": card("Classic", "Брют")}
        for e in (LabelEvidence(False, "NORTH ESTATE"),
                  LabelEvidence(True, "NORTH ESTATE", "North Estate"),
                  LabelEvidence(True, "NORTH ESTATE", "North Estate", grapes="Chardonnay")):
            self.assertEqual(semantic_rank([("north-brut", .98)], e, cards), [])

    def test_one_shared_brand_word_does_not_identify_another_producer(self):
        cards = {"aristov-verde": card("Verde", "Полусухое", producer="Aristov")}
        e = LabelEvidence(True, "SAN VERDE CHARDONNAY SEMI DRY", "San Verde", grapes="Chardonnay")
        self.assertEqual(semantic_rank([("aristov-verde", .93)], e, cards), [])

    def test_a_transliteration_error_needs_support_in_the_transcription(self):
        cards = {"abrau-dyurso-classic": card("Classic", "Брют", producer="Абрау-Дюрсо")}
        e = LabelEvidence(True, "АБРАУ-ДЮРГО CLASSIC БРЮТ", "ABRAU-DURYGO", "Classic")
        self.assertEqual(semantic_rank([("abrau-dyurso-classic", .90)], e, cards)[0][0],
                         "abrau-dyurso-classic")

    def test_missing_sugar_triggers_a_detail_read(self):
        cards = {"north-brut": card("Classic", "Брют"),
                 "north-polusladkoe": card("Classic", "Полусладкое")}
        e = LabelEvidence(True, "NORTH ESTATE CLASSIC", "North Estate", "Classic")
        self.assertTrue(needs_label_read(list(zip(cards, (.93, .92))), e, cards))
        detail = LabelEvidence(True, "NORTH ESTATE CLASSIC ПОЛУСЛАДКОЕ", "North Estate", "Classic")
        merged = merge_label_reads(e, detail)
        self.assertEqual(semantic_rank(list(zip(cards, (.93, .92))), merged, cards)[0][0],
                         "north-polusladkoe")
        self.assertEqual(merge_label_reads(e, LabelEvidence(False, "BRUT")), e)

    def test_a_missing_brand_does_not_prevent_the_repair_read(self):
        cards = {"north-shardone": card("North Estate Chardonnay")}
        visual = [("north-shardone", .90)]
        e = LabelEvidence(True, "CHARDONNAY WHITE DRY")
        self.assertEqual(semantic_rank(visual, e, cards), [])
        self.assertTrue(needs_label_read(visual, e, cards))
        self.assertFalse(needs_label_read(visual, LabelEvidence(False, "CHARDONNAY"), cards))
        self.assertFalse(needs_label_read([("north-shardone", .6)], e, cards))

    def test_a_short_printed_brand_matches_its_cyrillic_catalogue_name(self):
        cards = {"zb-vajn-vajt-suhoe-beloe": card("ЗБ вайн ВАЙТ сухое белое",
                                                producer="Золотая Балка")}
        e = LabelEvidence(True, "ZB WINE White", "ZB Wine", "White")
        self.assertEqual(semantic_rank([(next(iter(cards)), .90)], e, cards)[0][0],
                         next(iter(cards)))
        self.assertEqual(normalized("#ZBwine"), "zb wine")
        # A grape name without the brand cannot establish the White range.
        e = LabelEvidence(True, "ZB WINE CHARDONNAY", "ZB Wine", "Chardonnay")
        self.assertEqual(semantic_rank([(next(iter(cards)), .95)], e, cards), [])

    def test_main_label_view_excludes_the_neck_and_keeps_the_base(self):
        im = Image.new("RGB", (100, 300), "red")
        im.paste("blue", (0, 120, 100, 300))
        with Image.open(BytesIO(body_label_view(image_bytes(im)))) as detail:
            r, g, b = detail.getpixel((detail.width // 2, 0))
            self.assertGreater(b, r + 100)
            self.assertAlmostEqual(detail.height / detail.width, 1.8, places=1)

    def test_distinct_brand_words_cannot_reuse_the_same_catalogue_word(self):
        cards = {"shato-taman-brut": card("Шато Тамань", "Брют", producer="Кубань-Вино")}
        e = LabelEvidence(True, "CHATEAU SHUGO BRUT", "CHATEAU SHUGO")
        self.assertEqual(semantic_rank([("shato-taman-brut", .97)], e, cards), [])

    def test_a_known_producer_cannot_match_another_producer_through_a_grape(self):
        cards = {"north-classic": card("Classic", producer="North Estate"),
                 "south-north": card("North Estate Chardonnay", producer="South Winery")}
        e = LabelEvidence(True, "North Estate CHARDONNAY СУХОЕ", "North Estate")
        self.assertNotIn("south-north", dict(semantic_rank(
            [("south-north", .98), ("north-classic", .85)], e, cards)))

    def test_unsupported_named_range_and_unprinted_varietal_return_unknown(self):
        cards = {"north-classic": card("Classic"),
                 "north-shardone": card("North Estate Шардоне")}
        for e in (LabelEvidence(True, "North Estate FIORI СУХОЕ", "North Estate", "Fiori"),
                  LabelEvidence(True, "North Estate BLANC SUNNY БЕЛОЕ СУХОЕ", "North Estate")):
            ranks = semantic_rank([("north-shardone", .97)], e, cards)
            self.assertEqual(ranks, [])
        e = LabelEvidence(True, "North Estate CHARDONNAY СУХОЕ", "North Estate")
        self.assertEqual(semantic_rank([("north-shardone", .9)], e, cards)[0][0], "north-shardone")

    def test_colour_and_sugar_cannot_establish_an_unprinted_range(self):
        cards = {"north-signature": card("North Estate Signature")}
        e = LabelEvidence(True, "North Estate BLANC SUNNY БЕЛОЕ СУХОЕ", "North Estate", "Blanc")
        self.assertEqual(semantic_rank([("north-signature", .95)], e, cards), [])

    def test_a_fully_transcribed_name_survives_a_missing_brand_field(self):
        cards = {"balaklava-pino-nuar": card("Балаклава Пино Нуар", "Брют", producer="Золотая Балка")}
        e = LabelEvidence(True, "БАЛАКЛАВА PINOT NOIR Brut")
        self.assertEqual(semantic_rank([("balaklava-pino-nuar", .877)], e, cards)[0][0],
                         "balaklava-pino-nuar")

    def test_rose_translation_and_generic_producer_names_keep_printed_support(self):
        cards = {"tete-roze": card("Tête de Chevall розе", "Брют", "Розовое", "Estate"),
                 "balka-polusladkoe": card("Золотая Балка", "Полусладкое", producer="Золотая Балка")}
        rose = LabelEvidence(True, "TÊTE DE CHEVAL Rose Brut", "Tête de Cheval", "Rose Brut")
        generic = LabelEvidence(True, "ЗОЛОТАЯ Б ПОЛУСЛАДКОЕ", "ЗОЛОТАЯ Б", "Полусладкое")
        self.assertEqual(semantic_rank([("tete-roze", .9)], rose, cards)[0][0], "tete-roze")
        self.assertEqual(semantic_rank([("balka-polusladkoe", .91)], generic, cards)[0][0],
                         "balka-polusladkoe")

    def test_trace_retains_candidates_vetoed_before_pool_construction(self):
        cards = {"north-classic": card("Classic"),
                 "north-sweet": card("Classic", "Полусладкое"),
                 "north-red": card("Classic", color="Красное")}
        evidence = LabelEvidence(True, "North Estate Classic WHITE DRY", "North Estate", "Classic")
        visual = [("north-sweet", .97), ("north-red", .95), ("north-classic", .9)]
        trace = {}
        self.assertEqual(semantic_rank(visual, evidence, cards, trace=trace),
                         semantic_rank(visual, evidence, cards))
        candidates = {c["slug"]: c for c in trace["candidates"]}
        self.assertEqual(candidates["north-sweet"]["reason"], "sugar_conflict")
        self.assertEqual(candidates["north-red"]["conflict"],
                         {"code": "color_conflict", "observed": "white", "expected": "red"})
        self.assertEqual(candidates["north-classic"]["returned_rank"], 1)
        self.assertEqual(candidates["north-sweet"]["visual_rank"], 1)
        self.assertNotIn("evidence_rank", candidates["north-sweet"])
        json.dumps(trace, allow_nan=False)

    def test_trace_explains_refusals_and_return_limit_without_changing_scores(self):
        cards = {"north-classic": card("Classic"), "north-classic-2": card("Classic")}
        visual = [("north-classic", .9), ("north-classic-2", .89)]
        cases = [(LabelEvidence(False, ""), "no_front_label"),
                 (LabelEvidence(True, "North Estate", "North Estate"), "insufficient_identity_evidence"),
                 (LabelEvidence(True, "North Estate FIORI DRY", "North Estate", "Fiori"), "named_range_mismatch"),
                 (LabelEvidence(True, "North Estate Classic DRY", "North Estate", "Classic"), "supported")]
        for evidence, reason in cases:
            with self.subTest(reason=reason):
                trace = {}
                result = semantic_rank(visual, evidence, cards, limit=1, trace=trace)
                self.assertEqual(result, semantic_rank(visual, evidence, cards, limit=1))
                self.assertIn(reason, {c["reason"] for c in trace["candidates"]})
                if result:
                    self.assertIn("outside_return_limit", {c["reason"] for c in trace["candidates"]})
                    self.assertEqual(trace["supported_count"], 2)
                json.dumps(trace, allow_nan=False)

    def test_trace_bounds_text_conflicts_but_keeps_all_visual_candidates(self):
        cards = {"north-red-" + str(i): card("Classic", color="Красное") for i in range(100)}
        trace = {}
        evidence = LabelEvidence(True, "North Estate Classic WHITE DRY", "North Estate", "Classic")
        result = semantic_rank([("north-red-99", .98)], evidence, cards, trace=trace)
        self.assertEqual(result, [])
        self.assertLessEqual(len(trace["candidates"]), 21)
        self.assertEqual(trace["text_retrieval"]["omitted_conflict_count"], 80)
        self.assertIn("north-red-99", {c["slug"] for c in trace["candidates"]})


class QualityRuntimeTest(unittest.TestCase):
    def matcher(self):
        cards = {"north-classic": card("Classic")}
        return QualityGroupMatcher("quality", SimpleNamespace(bundle=SimpleNamespace(cards=cards)),
                                   quality_endpoint="http://vlm.test")

    def test_one_failed_reader_cannot_turn_into_a_visual_guess(self):
        m = self.matcher()
        evidence = LabelEvidence(True, "North Estate Classic Chardonnay", "North Estate", "Classic", grapes="Chardonnay")
        with patch.object(QualityGroupMatcher, "match_many", return_value=[[('north-classic', .9)]]*4), \
             patch.object(QualityGroupMatcher, "read_label", side_effect=[evidence, ValueError("bad JSON")]):
            ranks, traces = m.rank_crops([b'a', b'b'], [b'a', b'b'], [b'a', b'b'], 5)
        self.assertEqual(sum(bool(r) for r in ranks), 1)
        self.assertEqual(sum(bool(t.get('dependency_error')) for t in traces), 1)

    def test_total_reader_failure_is_a_dependency_error(self):
        with patch.object(QualityGroupMatcher, "match_many", return_value=[[('north-classic', .9)]]*2), \
             patch.object(QualityGroupMatcher, "read_label", side_effect=ValueError("bad JSON")):
            with self.assertRaises(GroupMatchError) as caught:
                self.matcher().rank_crops([b'a'], [b'a'], [b'a'], 1)
        self.assertEqual(caught.exception.status_code, 502)
        trace = caught.exception.audit_metadata['label_evidence'][0]
        self.assertEqual(trace['read_errors'], [{'stage': 'primary', 'error_type': 'ValueError'}])
        self.assertIsNone(trace['label_reads']['primary'])
        self.assertEqual(trace['visual_candidates']['merged'][0]['cosine'], .9)
        self.assertNotIn('bad JSON', json.dumps(trace))

    def test_readiness_reports_the_missing_vlm_as_a_dependency_failure(self):
        from matcher.service import Siglip2Matcher
        with patch.object(Siglip2Matcher, 'check_ready'), \
             patch.object(QualityGroupMatcher, 'read_label', side_effect=ValueError('empty')):
            with self.assertRaises(GroupMatchError) as caught:
                self.matcher().check_ready()
        self.assertEqual(caught.exception.status_code, 503)

    def test_original_pixels_and_normalized_masks_use_the_same_coordinates(self):
        normalized = Image.new('RGB', (60, 40), 'red')
        original = Image.new('RGB', (600, 400), 'red')
        payload = sam3_answer()
        segmented = segment_group(image_bytes(normalized), 'http://sam.test',
                                  opener=FakeOpener(json.dumps(payload).encode()))
        instances = _validate_sam3(payload, 60, 40, labels=('wine bottle', 'wine label'))
        full, label, ocr_body = high_resolution_crops(original, normalized, instances,
                                                     segmented.bottles[0])
        with Image.open(BytesIO(full)) as im:
            self.assertGreater(im.height, 300)
        with Image.open(BytesIO(label)) as im:
            self.assertGreater(im.height, 100)
            self.assertLess(im.height, 200)

        # Masked edges are useful for retrieval but must not erase OCR pixels.
        with Image.open(BytesIO(ocr_body)) as body:
            self.assertLess(body.getextrema()[1][1], 20)

    def test_detail_gate_uses_the_supported_original_resolution_candidate(self):
        m = self.matcher()
        evidence = LabelEvidence(True, "North Estate Classic Chardonnay",
                                 "North Estate", "Classic", grapes="Chardonnay")
        with patch.object(QualityGroupMatcher, "match_many",
                          return_value=[[("north-classic", .7)], [("north-classic", .9)]]), \
             patch.object(QualityGroupMatcher, "read_label", return_value=evidence) as reader:
            ranks, traces = m.rank_crops([b"masked"], [b"original"], [b"label"], 1,
                                         ocr_originals=[b"rectangle"])
        self.assertTrue(ranks[0])
        self.assertFalse(traces[0]["focused_read"])
        self.assertEqual(traces[0]["visual_candidates"]["baseline"][0]["cosine"], .7)
        self.assertEqual(traces[0]["visual_candidates"]["original"][0]["cosine"], .9)
        self.assertEqual(traces[0]["label_reads"]["effective"]["grapes"], "Chardonnay")
        reader.assert_called_once_with([b"rectangle", b"label"])

    def test_detail_trace_retains_both_reads_and_effective_fields(self):
        m = self.matcher()
        primary = LabelEvidence(True, "North Estate", "North Estate")
        detail = LabelEvidence(True, "North Estate Classic Chardonnay DRY", line="Classic", grapes="Chardonnay")
        crop = image_bytes(Image.new('RGB', (60, 90), 'red'))
        with patch.object(QualityGroupMatcher, 'match_many', return_value=[[('north-classic', .9)]]*2), \
             patch.object(QualityGroupMatcher, 'read_label', side_effect=[primary, detail]):
            ranks, traces = m.rank_crops([crop], [crop], [crop], 1)
        trace = traces[0]
        self.assertTrue(ranks[0])
        self.assertTrue(trace['focused_read'])
        self.assertEqual(trace['label_reads']['primary']['brand'], 'North Estate')
        self.assertEqual(trace['label_reads']['detail']['brand'], '')
        self.assertEqual(trace['label_reads']['effective']['brand'], 'North Estate')
        self.assertEqual(trace['label_reads']['effective_source'], 'detail')
        self.assertEqual(trace['semantic']['returned'][0]['slug'], 'north-classic')
        json.dumps(trace, allow_nan=False)

    def test_failed_detail_keeps_primary_and_safe_http_status(self):
        import httpx
        m = self.matcher()
        primary = LabelEvidence(True, 'North Estate', 'North Estate')
        crop = image_bytes(Image.new('RGB', (60, 90), 'red'))
        response = httpx.Response(503, request=httpx.Request('POST', 'http://secret:password@vlm.test'))
        failure = httpx.HTTPStatusError('private response body', request=response.request, response=response)
        with patch.object(QualityGroupMatcher, 'match_many', return_value=[[('north-classic', .9)]]*2), \
             patch.object(QualityGroupMatcher, 'read_label', side_effect=[primary, failure]):
            ranks, traces = m.rank_crops([crop], [crop], [crop], 1)
        self.assertEqual(ranks, [[]])
        trace = traces[0]
        self.assertEqual(trace['label_reads']['effective_source'], 'primary')
        self.assertEqual(trace['read_errors'], [{'stage': 'detail', 'error_type': 'HTTPStatusError', 'http_status': 503}])
        self.assertNotIn('password', json.dumps(trace))
        self.assertNotIn('private response body', json.dumps(trace))

    def test_opt_in_quality_group_route_keeps_the_primary_pipeline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_bundle_v2(root/'bundle')
            config = {'matcher': {'pipeline': 'primary', 'group_pipeline': 'quality',
                                  'sam3_endpoint': 'http://sam.test',
                                  'output_dir': str(root/'output')},
                      'pipeline': [{'name': 'primary', 'backend': 'mock', 'answers': {}},
                                   {'name': 'quality', 'backend': 'siglip2', 'bundle': str(root/'bundle'),
                                    'endpoint': 'http://siglip.test', 'quality_endpoint': 'http://vlm.test',
                                    'quality_model': 'qwen3.5-9b-nvfp4'}]}
            (root/'config.yaml').write_text(yaml.safe_dump(config))
            with patch.dict(os.environ, {'SVOE_VINO_MATCHER_CONFIG': str(root/'config.yaml')}):
                from matcher.app import create_app
            body = image_bytes(Image.new('RGB', (60,40), 'red'))
            segmented = segment_group(body, 'http://sam.test',
                                      opener=FakeOpener(json.dumps(sam3_answer()).encode()))
            app = create_app(root/'config.yaml', output_dir=str(root/'output'))
            with patch.dict(os.environ, {'SAM3_ENDPOINT': 'http://ignored.test'}), \
                 patch.object(QualityGroupMatcher, 'match_group_photo',
                              return_value=(segmented, [[('wine-a', .91)], []],
                                            [{'reason':'supported'}, {'reason':'unreadable'}])) as group_call:
                with TestClient(app) as client:
                    answer = client.post('/v1/group/match', files={'image': ('shelf.jpg', body, 'image/jpeg')})
            self.assertEqual(answer.status_code, 200, answer.text)
            self.assertEqual(group_call.call_args.args[1], 'http://sam.test')
            self.assertEqual(answer.json()['pipeline'], 'quality')
            self.assertEqual(answer.json()['bottles'][0]['match']['slug'], 'wine-a')
            self.assertIsNone(answer.json()['bottles'][1]['match'])
            self.assertEqual(app.state.matcher.pipeline, 'primary')
            self.assertNotIn('label_evidence', answer.json())
            records = list((root/'output').rglob('request.json'))
            self.assertEqual(len(records), 1)
            self.assertEqual(json.loads(records[0].read_text())['response']['label_evidence'][1]['reason'],
                             'unreadable')
            failure = GroupMatchError(502, 'group label reader returned no valid evidence')
            failure.audit_metadata = {'pipeline': 'quality', 'label_evidence': [{'trace_version': 1,
                                       'read_errors': [{'stage': 'primary', 'error_type': 'ValueError'}]}]}
            with patch.object(QualityGroupMatcher, 'match_group_photo', side_effect=failure), TestClient(app) as client:
                answer = client.post('/v1/group/match', files={'image': ('shelf.jpg', body, 'image/jpeg')})
            self.assertEqual(answer.status_code, 502)
            self.assertEqual(answer.json(), {'detail': failure.detail})
            errors = [json.loads(p.read_text())['response'] for p in (root/'output').rglob('request.json')]
            error = next(r for r in errors if r['status_code'] == 502)
            self.assertEqual(error['label_evidence'], failure.audit_metadata['label_evidence'])
