"""Check that rejected shelf detections do not create image crops."""
from unittest import TestCase, mock

from PIL import Image

from matcher import group
from test_group import FakeOpener, image_bytes, sam3_answer
import json


class GroupPreparationTest(TestCase):
    def test_duplicate_detection_does_not_encode_crops(self):
        answer = sam3_answer()
        body = image_bytes(Image.new('RGB', (60, 40), (220, 30, 20)))
        with mock.patch.object(group, '_prepare_bottle', wraps=group._prepare_bottle) as prepare:
            result = group.segment_group(body, 'http://fixture.invalid',
                                         opener=FakeOpener(json.dumps(answer).encode()))
        self.assertEqual(prepare.call_count, 2)
        self.assertEqual(len(result.bottles), 2)
        self.assertEqual(result.detected_count, 3)

    def test_edge_fragment_does_not_encode_crops(self):
        answer = sam3_answer()
        prepared_bottle = ((1, 86, 20, 100), Image.new('L', (19, 14), 255))
        prepared_label = ((3, 90, 15, 97), Image.new('L', (12, 7), 255))
        body = image_bytes(Image.new('RGB', (100, 100), 'red'))
        answer['instances'] = [answer['instances'][0]]
        answer['instances'][0]['box'] = prepared_bottle[0]
        with mock.patch.object(group, '_request_sam3', return_value=answer['instances']), \
                mock.patch.object(group, '_instance_mask', return_value=prepared_bottle), \
                mock.patch.object(group, '_best_label', return_value=({}, prepared_label)), \
                mock.patch.object(group, '_prepare_bottle', wraps=group._prepare_bottle) as prepare:
            result = group.segment_group(body, 'http://fixture.invalid')
        prepare.assert_not_called()
        self.assertEqual(result.bottles, ())
        self.assertEqual(result.detected_count, 1)
