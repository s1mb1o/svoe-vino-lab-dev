"""Reviewed gesture/depiction regressions and camera-roll negative controls."""

import base64
from io import BytesIO
import json
from pathlib import Path
import unittest

import numpy as np
from PIL import Image

from matcher.semantic_selector import select
from test_semantic_selector import rotate_inputs


class ImageGenIntentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {r['case_id']: r for r in json.loads(
            (Path(__file__).parent / 'data/imagegen-intent-regressions-20261020.json').read_text())['rows']}

    def variants(self, ident):
        row = self.rows[ident]
        width, height = row['size']
        y, x = np.indices((height, width))
        image = Image.fromarray(np.stack(((x + y) % 251, (3*x + y) % 251,
                                         (x + 2*y) % 251), axis=-1).astype('uint8'))
        for rotation in (None, Image.Transpose.ROTATE_90, Image.Transpose.ROTATE_180,
                         Image.Transpose.ROTATE_270):
            if rotation is None:
                yield 'original', image, row['instances']
            else:
                photo, items = rotate_inputs(image, row['instances'], rotation)
                yield str(rotation), photo, items
        mirrored = []
        for item in row['instances']:
            a, b, c, d = item['box']
            with Image.open(BytesIO(base64.b64decode(item['mask_png_b64']))) as opened:
                mask = opened.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                output = BytesIO()
                mask.save(output, 'PNG')
            mirrored.append(dict(item, box=[width-c, b, width-a, d],
                                 mask_png_b64=base64.b64encode(output.getvalue()).decode()))
        yield 'mirror', image.transpose(Image.Transpose.FLIP_LEFT_RIGHT), mirrored

    def check_preserved_labels(self, photo, items, result):
        candidate = next(c for c in result.candidates if c['id'] == result.selected_id)
        keep = np.asarray(result.keep_mask) >= 128
        for ident in candidate['label_ids']:
            mask = Image.open(BytesIO(base64.b64decode(items[int(ident[1:])]['mask_png_b64']))).convert('L')
            pixels = np.asarray(mask) >= 128
            self.assertTrue(np.all(keep[pixels]))
        with Image.open(BytesIO(result.crop)) as crop:
            expected = np.asarray(photo.crop(result.crop_box))
            actual = np.asarray(crop)
            x, y, X, Y = result.crop_box
            visible = keep[y:Y, x:X]
            np.testing.assert_array_equal(actual[visible], expected[visible])

    def test_pointed_bottle_is_selected_under_rotation_and_mirroring(self):
        for operation, photo, items in self.variants('HA02'):
            with self.subTest(operation=operation):
                result = select(photo, items)
                self.assertEqual((result.selected_id, result.reason), ('d1', 'explicit_pointing_gesture'))
                candidate = next(c for c in result.candidates if c['id'] == 'd1')
                self.assertTrue(candidate['signals']['pointing_evidence'])
                self.check_preserved_labels(photo, items, result)

    def test_explicit_tap_remains_above_pointing(self):
        _, photo, items = next(self.variants('HA02'))
        result = select(photo, items, tap=(.57, .45))
        self.assertEqual((result.selected_id, result.reason), ('d0', 'explicit_tap'))

    def test_side_body_grips_survive_rotation_and_transparent_wrapping(self):
        for ident in ('VI03', 'VI04', 'VI05'):
            for operation, photo, items in self.variants(ident):
                with self.subTest(case=ident, operation=operation):
                    result = select(photo, items)
                    self.assertEqual(result.selected_id, self.rows[ident]['target'])
                    self.assertEqual(result.reason, 'unique_visible_hand_contact')
                    candidate = next(c for c in result.candidates if c['id'] == result.selected_id)
                    self.assertTrue(any(e.get('side_body_contact') for e in candidate['signals']['grip_evidence'].values()))
                    self.check_preserved_labels(photo, items, result)

    def test_neck_and_base_projection_still_use_fallback(self):
        for ident in ('HA03', 'HA04'):
            for operation, photo, items in self.variants(ident):
                with self.subTest(case=ident, operation=operation):
                    result = select(photo, items)
                    self.assertEqual(result.selection_mode, 'fallback')

    def test_two_confirmed_grips_do_not_become_one_hand_subject(self):
        for operation, photo, items in self.variants('HA05'):
            with self.subTest(operation=operation):
                result = select(photo, items)
                self.assertEqual(result.selection_mode, 'fallback')
                self.assertEqual(result.fallback_trigger, 'multiple_hand_subjects')

    def test_display_panel_and_printed_bottle_cannot_beat_the_real_bottle(self):
        for operation, photo, items in self.variants('OW01'):
            with self.subTest(operation=operation):
                result = select(photo, items)
                self.assertEqual(result.selected_id, 'd4')
                self.assertIn({'id': 'd8', 'reason': 'display_panel_beside_physical_bottle'}, result.rejected)
                self.assertIn({'id': 'd0', 'reason': 'bottle_depiction_in_display_panel'}, result.rejected)
                self.check_preserved_labels(photo, items, result)

    def test_panel_without_a_separate_bottle_does_not_get_this_rejection(self):
        _, photo, items = next(self.variants('OW01'))
        items = [dict(item, score=0) if i == 4 else item for i, item in enumerate(items)]
        result = select(photo, items)
        self.assertFalse(any(r['reason'] == 'display_panel_beside_physical_bottle' for r in result.rejected))

    def test_real_bottle_in_open_packaging_remains_eligible(self):
        for operation, photo, items in self.variants('OW03'):
            with self.subTest(operation=operation):
                result = select(photo, items)
                self.assertEqual(result.selected_id, 'd3')
                self.assertFalse(any(r['id'] == 'd3' and r['reason'] == 'bottle_depiction_in_display_panel' for r in result.rejected))


if __name__ == '__main__':
    unittest.main()
