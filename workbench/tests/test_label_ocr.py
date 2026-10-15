"""Local PaddleOCR response parsing; these checks load no OCR runtime."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import label_ocr


class PaddleResultTests(unittest.TestCase):
    def test_complete_lines_native_confidence_and_polygon_are_preserved(self):
        words = label_ocr.words_of({"rec_texts": [" ЭКСТРА БРЮТ ", ""], "rec_scores": [.975, .9],
            "rec_polys": [[[1, 2], [30, 2], [30, 12], [1, 12]], [[0, 0]] * 4]})
        self.assertEqual(words, [{"text": "ЭКСТРА БРЮТ", "confidence": 97.5,
            "polygon": [[1., 2.], [30., 2.], [30., 12.], [1., 12.]]}])

    def test_text_and_confidence_counts_must_match(self):
        with self.assertRaisesRegex(ValueError, "counts differ"):
            label_ocr.words_of({"rec_texts": ["БРЮТ"], "rec_scores": []})

    def test_invalid_confidence_is_rejected(self):
        for score in (float("nan"), float("inf"), -0.1, 1.1, True):
            with self.subTest(score=score), self.assertRaises(ValueError):
                label_ocr.words_of({"rec_texts": ["БРЮТ"], "rec_scores": [score]})

    def test_invalid_polygons_are_rejected(self):
        for polygon in ([[0, 0]], [[0, 0, 0]] * 4, [[float("nan"), 0]] * 4):
            with self.subTest(polygon=polygon), self.assertRaises(ValueError):
                label_ocr.words_of({"rec_texts": ["БРЮТ"], "rec_scores": [.99], "rec_polys": [polygon]})

    def test_empty_ocr_result_is_valid(self):
        self.assertEqual(label_ocr.words_of({"rec_texts": [], "rec_scores": []}), [])
