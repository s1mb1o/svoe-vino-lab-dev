"""The ports of the matcher backend `cascade` (plan 85) MUST behave as the lab code.

The matcher imports no workbench code. It ports the code rules (`codes.py`,
`barcode.py`, `qr_barcode.py`), the label rule (`alternatives.py`, `derive.py`), and
the cluster re-rank (`cluster_rerank.py`, `label_rules.py`). These tests compare the
constants, the prompts, and the results of both sides on the same inputs. Run them after
a change on either side.
"""

import base64
from io import BytesIO
from pathlib import Path
import sys
import unittest
from unittest import mock

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT.parent))

import alternatives  # noqa: E402
import barcode  # noqa: E402
import cluster_rerank  # noqa: E402
import codes  # noqa: E402
import derive  # noqa: E402
import label_rules  # noqa: E402
import qr_barcode  # noqa: E402
from matcher import codes as matcher_codes  # noqa: E402
from matcher import labels as matcher_labels  # noqa: E402
from matcher import photo as matcher_photo  # noqa: E402
from matcher import rerank as matcher_rerank  # noqa: E402

PROJECT_BARCODE = {"formats": ["EAN13", "Code128"], "code128_gtin_only": True, "qr": True,
                   "tile_scan": False, "max_side": 1600, "upscale": True}
RULE_SHEET = {
    "key": "k1", "mode": "sheet", "slugs": ["wine-a", "wine-b", "wine-c"],
    "letters": {"A": "wine-a", "B": "wine-b", "C": "wine-c"}, "rule": "Look at the year.",
    "questions": [
        {"id": "q1", "question": "Which year?", "kind": "vintage", "valid": True,
         "answers": {"wine-a": "2021", "wine-b": "2023", "wine-c": None}},
        {"id": "q2", "question": "Sugar?", "valid": True,
         "answers": {"wine-a": "Сухое", "wine-b": "полусухое", "wine-c": "other"}},
        {"id": "q3", "question": "Unused", "valid": False, "answers": {"wine-a": "x"}},
    ],
}
DESCRIPTIONS = {"wine-a": {"description": {"texts": [{"text": "Абрау"}, {"text": "Brut"}],
                                           "vintage": "2021", "colours": ["gold"]}}}


def result(function, *args):
    """Return ("ok", the value) or ("error", the exception class name)."""
    try:
        return "ok", function(*args)
    except Exception as exc:  # noqa: BLE001 - both sides MUST fail the same way
        return "error", type(exc).__name__.replace("CodeError", "error")


class CodeParityTest(unittest.TestCase):
    VALUES = ["4600000000015", "4600000000016", " 96385074 ", "036000291452", "0" * 14,
              "12345", "46000A0000015", "", None, 4600000000015]
    URLS = ["URL: HTTPS://Example.COM:443/a#b", "http://[2001:DB8::1]:80/p",
            "https://пример.рф/x?y=1", "ftp://x/y", "https://u:p@x.y/", "https://a b/",
            "http://x.y:8080", "", "x" * 5000, None]

    def test_the_normal_forms_are_the_same(self):
        for value in self.VALUES:
            with self.subTest(value=value):
                self.assertEqual(result(matcher_codes.clean_gtin, value),
                                 result(codes.clean_gtin, value))
        for value in self.URLS:
            with self.subTest(value=str(value)[:30]):
                self.assertEqual(result(matcher_codes.clean_qr_url, value),
                                 result(codes.clean_qr_url, value))
        for digits in ("460000000001", "03600029145", "978020137962", "0000000"):
            self.assertEqual(matcher_codes.check_digit(digits), codes.check_digit(digits))
            self.assertEqual(matcher_codes.is_gtin13(digits + "0"), barcode.is_gtin13(digits + "0"))

    def test_the_kept_codes_are_the_codes_of_the_project_decoder(self):
        instances = [{"text": "4600000000015", "format": "EAN-13"},
                     {"text": "https://example.com/a", "format": "QR Code"},
                     {"text": "4600000000015", "format": "Code 128"},
                     {"text": "4600000000016", "format": "Code 128"},
                     {"text": "ABC", "format": "Code 128"},
                     {"text": "96385074", "format": "EAN-8"},
                     {"text": "036000291452", "format": "UPC-A"},
                     {"text": "x", "format": "Data Matrix"}]
        decoder = barcode.Decoder(barcode.check_options(dict(PROJECT_BARCODE)))
        with mock.patch.object(decoder.scanner, "decode",
                               return_value=qr_barcode.decode_instances(instances)):
            lab = decoder.read(Image.new("RGB", (10, 10)))
        self.assertEqual(matcher_codes.read(instances), lab)

    def test_the_hits_are_the_hits_of_the_lab_lookup(self):
        values = {("gtin", "04600000000015"): ["wine-a"],
                  ("gtin", "04600000000022"): ["wine-b", "wine-c"],
                  ("qr_url", "https://example.com/s"): ["wine-d", "wine-e"]}
        found = [{"kind": "qr_code", "format": "QR Code", "text": "https://EXAMPLE.com/s"},
                 {"kind": "barcode", "format": "EAN-13", "text": "4600000000022"},
                 {"kind": "barcode", "format": "EAN-13", "text": "4600000000015"}]
        lab = barcode.CodeLookup(values)
        port = matcher_codes.CodeTable({key: tuple(slugs) for key, slugs in values.items()})
        for sample in (found, found[:2], found[:1], []):
            self.assertEqual(port.hits(sample), lab.hits(sample))
            self.assertEqual(port.find(sample), lab.find(sample))

    def test_the_scan_image_is_the_image_of_the_lab_decoder(self):
        decoder = barcode.Decoder(barcode.check_options(dict(PROJECT_BARCODE)))
        for size in ((3024, 4032), (300, 400), (1600, 900)):
            image = Image.new("RGB", size, (90, 30, 200))
            image.paste((250, 250, 10), (size[0] // 4, size[1] // 4, size[0] // 2, size[1] // 2))
            with Image.open(BytesIO(matcher_photo.scaled_png(image))) as port:
                self.assertEqual(port.convert("RGB").tobytes(), decoder.scaled(image).tobytes())


class LabelParityTest(unittest.TestCase):
    def test_the_constants_are_the_lab_constants(self):
        self.assertEqual(
            (matcher_labels.BOTTLE_IOU, matcher_labels.BOTTLE_COVER, matcher_labels.BOTTLE_COVER_IOU,
             matcher_labels.DUPLICATE_IOU, matcher_labels.MIN_BOX_SIDE, matcher_labels.INSIDE,
             matcher_labels.BODY_AREA, matcher_labels.BODY_WIDTH, matcher_labels.PART_COVER),
            (alternatives.BOTTLE_IOU, alternatives.BOTTLE_COVER, alternatives.BOTTLE_COVER_IOU,
             alternatives.DUPLICATE_IOU, alternatives.MIN_BOX_SIDE, alternatives.INSIDE,
             alternatives.BODY_AREA, alternatives.BODY_WIDTH, alternatives.PART_COVER))
        self.assertEqual(matcher_labels.LABEL_NOUN, alternatives.LABEL_NOUNS[0])
        self.assertEqual((matcher_photo.MASK_BLUR, matcher_photo.MASK_KEEP, matcher_photo.EDGE_BLUR),
                         (derive.MASK_BLUR, derive.MASK_KEEP, derive.EDGE_BLUR))

    def test_refine_mask_gives_the_lab_pixels(self):
        for size in ((300, 400), (1200, 1600)):
            mask = Image.new("L", size, 0)
            mask.paste(255, (size[0] // 4, size[1] // 5, size[0] // 2, size[1] // 2))
            self.assertEqual(matcher_photo.refine_mask(mask).tobytes(),
                             derive.refine_mask(mask).tobytes())

    def test_the_label_of_a_single_bottle_is_the_lab_label(self):
        size = (300, 400)

        def item(label, box, score=0.9):
            mask = Image.new("L", size, 0)
            mask.paste(255, box)
            output = BytesIO()
            mask.save(output, "PNG")
            return {"label": label, "box": list(box), "score": score,
                    "area": (box[2] - box[0]) * (box[3] - box[1]),
                    "mask_png_b64": base64.b64encode(output.getvalue()).decode("ascii")}
        package = (100, 50, 200, 350)
        cases = [
            [item("label", (120, 150, 180, 250)), item("label", (125, 60, 175, 80))],
            [item("label", (101, 51, 199, 349)), item("label", (120, 150, 180, 250))],
            [item("label", (110, 140, 190, 230)), item("label", (115, 240, 185, 300))],
        ]
        for labels in cases:
            with self.subTest(boxes=[label["box"] for label in labels]):
                # The lab finds the package through the noun `bottle`.
                lab = alternatives.label_instance(labels + [item("bottle", package)])
                choice = matcher_labels.choose(labels, package, *size)
                self.assertEqual(choice.main["box"], lab["box"])
                lab_others = alternatives.body_labels(labels + [item("bottle", package)],
                                                      lab, *size)
                self.assertEqual([other["box"] for other in choice.others],
                                 [other["box"] for other in lab_others])


class RerankParityTest(unittest.TestCase):
    def test_the_prompts_and_the_answer_words_are_the_lab_ones(self):
        self.assertEqual(matcher_rerank.SHEET_PROMPT, cluster_rerank.SHEET_PROMPT)
        self.assertEqual(matcher_rerank.VERDICT_PROMPT, cluster_rerank.VERDICT_PROMPT)
        self.assertEqual(matcher_rerank.NOT_VISIBLE, label_rules.NOT_VISIBLE)
        self.assertEqual((matcher_rerank.OTHER, matcher_rerank.UNSURE,
                          matcher_rerank.NOT_VISIBLE_ANSWER),
                         (cluster_rerank.OTHER, cluster_rerank.UNSURE, cluster_rerank.NOT_VISIBLE))
        self.assertEqual((matcher_rerank.VIEW, matcher_rerank.RULE_SPACE),
                         (label_rules.VIEW, label_rules.RULE_SPACE))

    def test_the_prompts_scores_and_orders_are_the_lab_ones(self):
        rule = RULE_SHEET
        names = {"wine-a": "Абрау Брют", "wine-b": "Vino B"}
        self.assertEqual(matcher_rerank.sheet_prompt(rule), cluster_rerank.sheet_prompt(rule))
        self.assertEqual(matcher_rerank.verdict_prompt(rule, names, DESCRIPTIONS),
                         cluster_rerank.verdict_prompt(rule, names, DESCRIPTIONS))
        self.assertEqual(matcher_rerank.verdict_schema(rule), cluster_rerank.verdict_schema(rule))
        for answers in ({"q1": "2023", "q2": "Полусухое"}, {"q1": "урожай 2019", "q2": "сухое."},
                        {"q1": "not visible"}, "no object", {"q2": None}):
            self.assertEqual(matcher_rerank.sheet_scores(rule, answers, rule["slugs"]),
                             cluster_rerank.sheet_scores(rule, answers, rule["slugs"]))
        for answer in ({"wine": "b"}, {"wine": "unsure"}, {"wine": None}, "x"):
            self.assertEqual(matcher_rerank.verdict_choice(rule, answer),
                             cluster_rerank.verdict_choice(rule, answer))
        for text in ('{"q1": "a"}', 'x {"q1": "a"} y', "[]", None, ""):
            self.assertEqual(matcher_rerank.parse_json(text), label_rules.parse_json(text))

    def test_reorder_keeps_the_lab_positions_and_scores(self):
        pairs = [("wine-a", 0.9), ("wine-x", 0.8), ("wine-b", 0.7), ("wine-c", 0.6)]
        candidates = [{"slug": slug, "score": score, "rank": rank}
                      for rank, (slug, score) in enumerate(pairs, 1)]
        positions, ranking = [0, 2, 3], ["wine-c", "wine-a", "wine-b"]
        lab = cluster_rerank.reorder(candidates, positions, ranking, {})
        self.assertEqual(matcher_rerank.reorder(pairs, positions, ranking),
                         [(card["slug"], card["score"]) for card in lab])


if __name__ == "__main__":
    unittest.main()
