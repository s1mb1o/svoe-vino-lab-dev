"""Quality checks and routing use local masks and synthetic competing identities."""
import base64
import io
from pathlib import Path
import sys
import unittest

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import alternatives  # noqa: E402
import embedding_run  # noqa: E402
import label_gate  # noqa: E402
from embeddings import ConfigError  # noqa: E402


def fixture():
    image = Image.new("RGB", (320, 320), "#303030")
    mask = Image.new("L", image.size)
    ImageDraw.Draw(mask).polygon([(160, 40), (280, 160), (160, 280), (40, 160)], fill=255)
    paper = Image.new("RGB", image.size, "#dce6ef")
    draw = ImageDraw.Draw(paper)
    for y in range(100, 220, 12):
        draw.rectangle((105, y, 215, y + 3), fill="black")
    image.paste(paper, mask=mask)
    buffer = io.BytesIO()
    mask.save(buffer, "PNG")
    instance = {"label": "label", "box": list(mask.getbbox()), "score": 0.95,
                "area": int((np.asarray(mask) > 0).sum()),
                "mask_png_b64": base64.b64encode(buffer.getvalue()).decode("ascii")}
    cut, box = alternatives.label_cut(image, instance)
    white = Image.new("RGB", cut.size, "white")
    white.paste(cut, mask=cut.getchannel("A"))
    context = {"instances": [instance], "cut": ("seg", cut, box),
               "package_box": (0, 0, 320, 320)}
    return image, white, context


class QualityTest(unittest.TestCase):
    def setUp(self):
        self.options = label_gate.check_options({"min_sharpness": 0})
        self.image, self.prepared, self.context = fixture()

    def measure(self, prepared=None, context=None, options=None):
        return label_gate.measure(self.image, prepared or self.prepared,
                                  context or self.context, options or self.options)

    def test_diamond_label_on_white_passes_despite_empty_corners(self):
        out = self.measure()
        self.assertTrue(out["passed"], out)
        self.assertGreater(out["signals"]["purity"], 0.8)
        self.assertLess(float((np.asarray(self.prepared).min(axis=2) < 245).mean()), 0.7)

    def test_surrounding_glass_fails_with_the_same_detector_confidence(self):
        context = dict(self.context, cut=("crop", self.image.convert("RGBA"), (0, 0, 320, 320)))
        out = self.measure(self.image, context)
        self.assertIn("unrelated_content", out["reasons"])
        self.assertEqual(out["signals"]["detector_score"], self.measure()["signals"]["detector_score"])

    def test_upscaled_tiny_label_fails_native_detail_check(self):
        image = self.image.resize((32, 32))
        context = dict(self.context, cut=("crop", image.convert("RGBA"), (4, 4, 29, 29)),
                       package_box=(0, 0, 32, 32))
        out = label_gate.measure(image, self.prepared.resize((512, 512)), context, self.options)
        self.assertIn("insufficient_native_detail", out["reasons"])
        self.assertGreater(min(out["signals"]["input_label_size"]), 128)

    def test_blur_is_measured_inside_the_label(self):
        sharp = self.measure()["signals"]["sharpness"]
        blurred = self.prepared.filter(ImageFilter.GaussianBlur(4))
        blur = self.measure(blurred)["signals"]["sharpness"]
        self.assertLess(blur, sharp / 4)
        options = label_gate.check_options({"min_sharpness": (sharp + blur) / 2})
        self.assertTrue(self.measure(options=options)["passed"])
        self.assertIn("insufficient_sharpness", self.measure(blurred, options=options)["reasons"])

    def test_label_on_another_package_is_rejected(self):
        out = self.measure(context=dict(self.context, package_box=(0, 0, 20, 20)))
        self.assertIn("label_on_other_package", out["reasons"])

    def test_no_label_is_a_quality_rejection(self):
        out = label_gate.measure(self.image, None, {}, self.options)
        self.assertEqual(out["reasons"], ["no_label"])

    def test_malformed_cached_mask_rejects_labels_safely(self):
        instance = dict(self.context["instances"][0], mask_png_b64="broken")
        out = self.measure(context=dict(self.context, instances=[instance]))
        self.assertEqual(out["reasons"], ["invalid_label_data"])

    def test_input_resizing_can_remove_usable_detail(self):
        out = self.measure(self.prepared.resize((32, 32)))
        self.assertIn("insufficient_input_detail", out["reasons"])

    def test_frame_contact_is_a_flag_not_a_blanket_closeup_rejection(self):
        mask = Image.new("L", self.image.size, 255)
        buffer = io.BytesIO()
        mask.save(buffer, "PNG")
        instance = dict(self.context["instances"][0], box=[0, 0, 320, 320],
                        area=320 * 320, mask_png_b64=base64.b64encode(buffer.getvalue()).decode())
        context = {"instances": [instance], "cut": ("crop", self.image, (0, 0, 320, 320))}
        out = self.measure(self.image, context)
        self.assertTrue(out["passed"], out)
        self.assertEqual(out["signals"]["source_frame_edges"], 4)


class RouteTest(unittest.TestCase):
    def setUp(self):
        self.options = label_gate.check_options({})
        self.good = {"passed": True, "reasons": []}

    def choose(self, scores, quality=None):
        return label_gate.choose({"full", "label"}, [{"cosine": s} for s in scores],
                                 quality or self.good, self.options)

    def test_high_score_with_clear_margin_selects_labels(self):
        self.assertEqual(self.choose([0.97, 0.91])["selected_view"], "label")

    def test_actual_semidry_case_falls_back_despite_score_above_point_nine(self):
        out = self.choose([0.9001, 0.8990])
        self.assertEqual(out["selected_view"], "full")
        self.assertIn("label_margin_below_threshold", out["reasons"])

    def test_bad_crop_cannot_win_even_with_perfect_similarity(self):
        out = self.choose([1.0, 0.8], {"passed": False, "reasons": ["unrelated_content"]})
        self.assertEqual(out["selected_view"], "full")

    def test_low_score_with_large_margin_uses_bottles(self):
        self.assertIn("label_score_below_threshold", self.choose([0.89, 0.5])["reasons"])

    def test_one_label_candidate_cannot_establish_a_margin(self):
        self.assertEqual(self.choose([1.0])["selected_view"], "full")

    def test_missing_label_vectors_use_bottles(self):
        out = label_gate.choose({"full"}, [], self.good, self.options)
        self.assertEqual(out["selected_view"], "full")

    def test_invalid_options_are_refused(self):
        for raw in (None, {"typo": 1}, {"min_purity": 1.1}, {"min_score": True},
                    {"min_sharpness": float("nan")}, {"min_native_side": 1.5}):
            with self.subTest(raw=raw), self.assertRaises(ConfigError):
                label_gate.check_options(raw)


def catalogue():
    cat = embedding_run.Catalogue.__new__(embedding_run.Catalogue)
    cat.slugs = ["bottle-winner", "label-winner", "third"]
    cat.dim = 2
    cat.views, cat.items, cat.rows_of, cat.angles = {}, {}, {}, {}
    for view, scores in {"full": [1.0, 0.7, 0.4], "label": [0.91, 0.97, 0.9]}.items():
        cat.views[view] = (np.array([[s, np.sqrt(1 - s*s)] for s in scores], dtype=np.float32),
                           np.array([0, 1, 2]))
        cat.rows_of[view] = {i: [i] for i in range(3)}
        cat.items[view] = [{"sha256": str(i), "view": view, "type": "main",
                            "embedding_hash": str(i)} for i in range(3)]
    return cat


class ScoringTest(unittest.TestCase):
    def test_gate_selects_label_winner_even_when_average_prefers_bottle_winner(self):
        cat = catalogue()
        query = {v: np.array([1., 0.]) for v in cat.views}
        self.assertEqual(cat.rank(query, 3)[0]["slug"], "bottle-winner")
        trace = embedding_run.Trace()
        selected = cat.rank(query, 3, trace, label_gate=label_gate.check_options({}),
                            label_quality={"passed": True, "reasons": []})
        self.assertEqual(selected[0]["slug"], "label-winner")
        self.assertEqual(selected[0]["score"], selected[0]["label"])
        self.assertEqual(selected[0]["score"], 0.97)
        route = next(s["out"] for s in trace.steps if s["id"] == "label-route")
        self.assertTrue(route["winner_disagreement"])
        self.assertEqual(route["selected_view"], "label")

    def test_failed_quality_preserves_the_entire_bottle_order_and_scores(self):
        cat = catalogue()
        query = {v: np.array([1., 0.]) for v in cat.views}
        full = cat.rank({"full": query["full"]}, 3)
        selected = cat.rank(query, 3, label_gate=label_gate.check_options({}),
                            label_quality={"passed": False, "reasons": ["unrelated_content"]})
        self.assertEqual([(c["slug"], c["score"]) for c in selected],
                         [(c["slug"], c["score"]) for c in full])


if __name__ == "__main__":
    unittest.main()
