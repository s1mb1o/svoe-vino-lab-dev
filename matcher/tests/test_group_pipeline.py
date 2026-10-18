"""Tests for an independent segmented-bottle SigLIP2 pipeline."""

from pathlib import Path
import tempfile
import unittest

import yaml

from matcher.group_pipeline import SegmentedSiglip2Matcher, load_group_matcher
from matcher.service import ConfigError, load_matcher
from test_match import KNOWN_IMAGE, write_bundle_v2
from test_siglip2 import FakeSiglip2


class GroupPipelineTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.fake = FakeSiglip2((1, 0, 0, 0))
        self.addCleanup(self.fake.close)
        # A conflicting label view must not veto the segmented full-view ranking.
        write_bundle_v2(self.root / 'bundle', rows=(
            ('full', (1, 0, 0, 0), ('wine-a',)),
            ('full', (0, 1, 0, 0), ('wine-b',)),
            ('label', (0, 1, 0, 0), ('wine-a',)),
            ('label', (1, 0, 0, 0), ('wine-b',)),
        ))
        self.config = {
            'matcher': {'pipeline': 'single-mock', 'group_pipeline': 'rot5-seg'},
            'pipeline': [
                {'name': 'single-mock', 'backend': 'mock', 'answers': {}},
                {'name': 'rot5-seg', 'backend': 'siglip2',
                 'bundle': str(self.root / 'bundle'), 'endpoint': self.fake.url},
            ],
        }

    def load(self):
        path = self.root / 'config.yaml'
        path.write_text(yaml.safe_dump(self.config), encoding='utf-8')
        primary = load_matcher(path)
        return primary, load_group_matcher(path, primary)

    def test_separate_group_selection_and_full_ranking_ignore_label_disagreement(self):
        primary, group = self.load()
        self.assertEqual(primary.pipeline, 'single-mock')
        self.assertEqual(group.pipeline, 'rot5-seg')
        self.assertIsInstance(group, SegmentedSiglip2Matcher)
        photo = KNOWN_IMAGE.read_bytes()
        ranked = group.match_group_many([photo, photo], [b'unused', b'unused'], 5)
        self.assertEqual([[slug for slug, _ in pairs] for pairs in ranked],
                         [['wine-a'], ['wine-a']])
        self.assertEqual(len(self.fake.requests), 1)
        self.assertEqual(len(self.fake.requests[0][1]['input']), 2)
        self.assertTrue(group.can_match_group)
        self.assertEqual(primary.predict(photo), '')

    def test_missing_selection_reuses_the_existing_matcher(self):
        del self.config['matcher']['group_pipeline']
        primary, group = self.load()
        self.assertIs(primary, group)

    def test_invalid_group_selections_fail_at_startup(self):
        for name in (None, '', 12, 'unknown', 'single-mock'):
            with self.subTest(name=name):
                self.config['matcher']['group_pipeline'] = name
                with self.assertRaisesRegex(ConfigError, 'group_pipeline'):
                    self.load()

    def test_full_only_index_works_and_weak_scores_are_rejected(self):
        write_bundle_v2(self.root / 'full-only', rows=(
            ('full', (0.7, 0.714142842854285, 0, 0), ('wine-a',)),
        ))
        self.config['pipeline'][1]['bundle'] = str(self.root / 'full-only')
        _, group = self.load()
        self.assertTrue(group.can_match_group)
        self.assertEqual(group.match_group_many([KNOWN_IMAGE.read_bytes()], [b'unused'], 1),
                         [[]])
        self.assertEqual(group.match_group_many([], [], 1), [])
        with self.assertRaisesRegex(ValueError, 'counts differ'):
            group.match_group_many([b'image'], [], 1)
