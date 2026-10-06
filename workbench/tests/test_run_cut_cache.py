"""Check real cached SAM3 dependencies and bounded reconstructed PNG reuse."""
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import test_embedding_run as TE
import alternatives
import derive
import embedding_run
import embeddings
import main_scene
import model_cache
import run_steps
import test_run_steps as TS
from checked_read_cache import signature


class RunCutCacheTest(TE.Temporary):
    def setUp(self):
        super().setUp()
        run_steps.VISUAL_INPUTS.clear()
        self.path = self.root / 'photo.png'
        TE.query_photo('green').save(self.path)
        self.views = {'full': [{'step': 'segment', 'target': 'package'},
                               {'step': 'remove_background'}, {'step': 'white_background'}],
                      'label': [{'step': 'segment', 'target': 'label'}]}
        self.endpoint = 'http://fixture-sam3'
        self.records = {}
        self.store_answers()

    def photo(self):
        image, _ = derive.open_image(self.path)
        return SimpleNamespace(path=str(self.path), image=image, error=None,
                               source_state=signature(self.path))

    def store_answers(self):
        client = embedding_run.CachedSam3(self.endpoint)
        image = self.photo().image
        data, _ = client._sent_copy(image)
        instances, _ = TE.FakeSam3().instances(image, alternatives.DETECT_TEXTS)
        for texts in (derive.SAM3_TEXTS, alternatives.DETECT_TEXTS, main_scene.TEXTS):
            params = {'threshold': str(derive.SAM3_THRESHOLD),
                      'mask_threshold': str(derive.SAM3_MASK_THRESHOLD), 'return_masks': 'true'}
            fields = model_cache.request_fields(self.endpoint+'/segment_multi', derive.SAM3_MODEL,
                                                params, texts, [data])
            model_cache.store(fields, {'instances': instances}, 0)
            self.records[texts] = Path(model_cache.path_of(fields))
        client.session.close()

    def call(self, scene=False, views=None):
        return run_steps._reconstruct_inputs(self.photo(), views or self.views, self.endpoint, scene)

    def test_repeat_skips_replay_and_png_encoding_and_returns_independent_values(self):
        with patch.object(embedding_run, 'cuts_of', wraps=embedding_run.cuts_of) as cuts, \
                patch.object(embeddings, 'png_bytes', wraps=embeddings.png_bytes) as png:
            first = self.call()
            expected = json.loads(json.dumps(first))
            first['cuts']['package']['result']['box'][0] = -100
            second = self.call()
            self.assertEqual(json.loads(json.dumps(second)), expected)
            self.assertEqual((cuts.call_count, png.call_count), (2, 2))
            self.assertTrue(second['views']['full']['src'].startswith('data:image/png;base64,'))

    def test_both_targets_encode_the_sam3_photo_once_on_a_cold_read(self):
        original = embedding_run.CachedSam3._sent_copy
        calls = []

        def sent_copy(client, image):
            calls.append(1)
            return original(client, image)

        with patch.object(embedding_run.CachedSam3, '_sent_copy', sent_copy):
            result = self.call()
        self.assertEqual(len(calls), 1)
        self.assertIsNotNone(result['cuts']['package']['box'])
        self.assertIsNotNone(result['cuts']['label']['box'])

    def test_sam3_replacement_with_same_mtime_and_removal_invalidate(self):
        first = self.call()
        path = self.records[alternatives.DETECT_TEXTS]
        stamp = path.stat()
        record = json.loads(path.read_text())
        record['answer']['instances'] = []
        replacement = path.with_suffix('.new')
        replacement.write_text(json.dumps(record))
        os.utime(replacement, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        replacement.replace(path)
        self.assertIsNone(self.call()['cuts']['label']['box'])
        path.unlink()
        missing = self.call()
        self.assertIn('not in', missing['cuts']['label']['reason'])
        self.store_answers()
        self.assertEqual(self.call(), first)

    def test_photo_views_endpoint_scene_and_runtime_settings_are_checked(self):
        first = self.call()
        scene = self.call(scene=True)
        self.assertIn('selection', scene['cuts']['package']['result'])
        views = dict(self.views, raw=[])
        self.assertEqual(self.call(views=views)['views']['raw']['width'], 100)
        with patch.object(derive, 'EDGE_BLUR', derive.EDGE_BLUR + 1):
            self.assertNotEqual(self.call()['cuts']['package']['src'], first['cuts']['package']['src'])
        original = self.endpoint
        self.endpoint = 'http://another-fixture'
        self.assertIn('not in', self.call()['cuts']['package']['reason'])
        self.endpoint = original
        TE.query_photo('red').save(self.path)
        self.store_answers()
        self.assertNotEqual(self.call()['views']['full']['src'], first['views']['full']['src'])

    def test_disabled_reads_and_failed_results_are_not_reused(self):
        self.call()
        with patch.object(model_cache, 'READ', False):
            self.assertIn('not in', self.call()['cuts']['package']['reason'])
        self.assertIsNotNone(self.call()['cuts']['package']['box'])
        self.records[derive.SAM3_TEXTS].unlink()
        self.call()
        self.store_answers()
        self.assertIsNotNone(self.call()['cuts']['package']['box'])

    def test_change_during_read_and_source_code_change_are_not_retained(self):
        source = self.root / 'dependency'
        source.write_text('one')
        cache = run_steps.VisualInputsCache()
        calls = []

        def load():
            state = signature(source)
            calls.append(1)
            source.write_text('two' + str(len(calls)))
            return {'value': len(calls)}, {str(source): state}, True

        self.assertNotEqual(cache.get('key', load), cache.get('key', load))
        self.assertEqual(cache._bytes, 0)
        before_open = self.photo()
        TE.query_photo('red').save(self.path)
        run_steps._reconstruct_inputs(before_open, self.views, self.endpoint, False)
        self.assertEqual(len(run_steps.VISUAL_INPUTS._entries), 0)

    def test_entry_byte_limits_lru_and_clear(self):
        source = self.root / 'dependency'
        source.write_text('source')
        cache = run_steps.VisualInputsCache(max_entries=2, max_bytes=2048)
        calls = []

        def load():
            calls.append(1)
            return {'value': 'x'}, {str(source): signature(source)}, True

        for key in ('one', 'two', 'one', 'three', 'two'):
            cache.get(key, load)
        self.assertEqual(len(calls), 4)
        self.assertLessEqual(len(cache._entries), 2)
        def huge():
            return {'value': 'x'*2048}, {str(source): signature(source)}, True
        cache.get('huge', huge)
        self.assertNotIn('huge', cache._entries)
        cache.clear()
        self.assertEqual((len(cache._entries), cache._bytes), (0, 0))


class RunCutTraceFreshnessTest(TS.StepsTest):
    def test_warm_visuals_keep_current_trace_comparisons_and_card_names(self):
        run_dir, rows = self.run_set()
        row = rows['green/01.png']
        photo = run_steps.Photo(self.lab.conn, self.lab.db_path, row)
        spec = json.loads((Path(run_dir)/'run.json').read_text())['backend']
        client = embedding_run.CachedSam3(spec['sam3']['endpoint'])
        data, _ = client._sent_copy(photo.image)
        instances, _ = TE.FakeSam3().instances(photo.image, alternatives.DETECT_TEXTS)
        params = {'threshold': str(derive.SAM3_THRESHOLD),
                  'mask_threshold': str(derive.SAM3_MASK_THRESHOLD), 'return_masks': 'true'}
        for texts in (derive.SAM3_TEXTS, alternatives.DETECT_TEXTS):
            fields = model_cache.request_fields(client.endpoint+'/segment_multi', derive.SAM3_MODEL,
                                                params, texts, [data])
            model_cache.store(fields, {'instances': instances}, 0)
        client.session.close()
        args = (self.runs, self.lab.db_path, os.path.basename(run_dir), row['query_id'], TS.no_cards)
        run_steps.VISUAL_INPUTS.clear()
        with patch.object(embedding_run, 'cuts_of', wraps=embedding_run.cuts_of) as replay:
            first = run_steps.steps_view(*args)
            records = TS.read_rows(run_dir)
            changed = next(r for r in records if r['query_id'] == row['query_id'])
            view = next(part for part in changed['trace']['steps'] if part['id'] == 'view')
            view['out']['sha256'] = 'different recorded input'
            view['ms'] = 987
            TS.write_rows(run_dir, records)
            self.lab.conn.execute("UPDATE wine_catalog SET name_patched='Current name' WHERE wine_slug='green'")
            self.lab.conn.commit()
            second = run_steps.steps_view(*args)
            self.assertEqual(replay.call_count, 2)
        parts = self.all_steps(second)
        full = next(p for p in parts if p['id']=='view' and p['view']==view['view'])
        self.assertEqual((full['ms'], full['artifacts'][0]['check']), (987, 'changed'))
        original = next(p for p in self.all_steps(first) if p['id']=='view' and p['view']==view['view'])
        self.assertEqual(original['artifacts'][0]['src'], full['artifacts'][0]['src'])
        names = [item['name'] for p in parts for group in p['lists'] for item in group['items']
                 if item['slug']=='green']
        self.assertTrue(names)
        self.assertEqual(set(names), {'Current name'})


if __name__ == '__main__':
    import unittest
    unittest.main()
