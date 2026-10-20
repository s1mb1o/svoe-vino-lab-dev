"""The report must distinguish decisions from the pixels actually returned."""

from io import BytesIO
import base64
from pathlib import Path
import hashlib
import json
import tempfile
import unittest
from unittest import mock

from PIL import Image, ImageDraw

from matcher.semantic_selector import Selection
from matcher.experiments.main_selector.metrics import cohort, pixel_metrics
from matcher.experiments.main_selector.benchmark import assess, run, selected_gt
from matcher.experiments.main_selector.fallback_suite import (
    policy_target,
    policy_geometry,
    verify_frozen_inputs,
)


def png(image):
    output = BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


class CropMetricsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.image = Image.new("RGB", (100, 100), "#ba9874")
        self.image.save(self.root / "photo.png")
        self.case = dict(
            width=100,
            height=100,
            image="photo.png",
            annotations=[],
            target_instance_id=1,
            label_ground_truth=True,
            expected_status="selected",
            provenance="new_native_render",
            interaction={},
        )
        for id_, category, parent, box in (
            (1, "bottle", None, (10, 10, 60, 90)),
            (2, "label_front", 1, (20, 40, 40, 60)),
            (3, "bottle", None, (70, 10, 90, 90)),
        ):
            mask = Image.new("L", self.image.size)
            x, y, X, Y = box
            ImageDraw.Draw(mask).rectangle((x, y, X - 1, Y - 1), fill=255)
            path = f"mask-{id_}.png"
            mask.save(self.root / path)
            self.case["annotations"].append(
                dict(
                    instance_id=id_,
                    category=category,
                    parent_instance_id=parent,
                    mask=path,
                    box=list(box),
                )
            )

    def decision(self, *, box=(0, 0, 100, 100), selected_id="d0"):
        mask = Image.new("L", self.image.size)
        mask.paste(255, box)
        return Selection(
            "selected" if selected_id else "no_target",
            *self.image.size,
            selected_id=selected_id,
            crop=png(self.image.crop(box)),
            crop_box=box,
            keep_mask=mask,
        )

    def test_selected_mask_assignment_does_not_treat_detector_class_as_truth(self):
        with Image.open(self.root / self.case["annotations"][0]["mask"]) as mask:
            body = base64.b64encode(png(mask)).decode()
        decision = self.decision()
        for label in ("wine label", "wine bottle", "box"):
            with self.subTest(label=label):
                matched, iou = selected_gt(
                    self.case,
                    [dict(label=label, mask_png_b64=body)],
                    decision,
                    self.root,
                )
                self.assertEqual((matched, iou), (1, 1.0))
        with Image.open(self.root / self.case["annotations"][1]["mask"]) as mask:
            body = base64.b64encode(png(mask)).decode()
        matched, iou = selected_gt(
            self.case, [dict(label="box", mask_png_b64=body)], decision, self.root
        )
        self.assertEqual((matched, iou), (1, 1.0))

    def test_identical_full_frame_pixels_have_identical_crop_and_label_metrics(self):
        legacy = self.decision(selected_id=None)
        label = self.decision(selected_id="d1")
        label.crop_scope = "context_frame"
        old = pixel_metrics(self.case, legacy, self.root)
        new = pixel_metrics(self.case, label, self.root)
        self.assertEqual(old, new)
        self.assertEqual(old["label_retention"], 1)
        self.assertEqual(old["crop_target_coverage"], 1)
        self.assertEqual(old["crop_distractor_retention"], 1)
        self.assertTrue(old["full_frame_context"])

    def test_target_crop_retains_target_without_credit_for_distractors(self):
        metrics = pixel_metrics(
            self.case, self.decision(box=(10, 10, 60, 90)), self.root
        )
        self.assertEqual(metrics["label_retention"], 1)
        self.assertEqual(metrics["crop_target_coverage"], 1)
        self.assertEqual(metrics["crop_distractor_retention"], 0)
        self.assertFalse(metrics["full_frame_context"])

    def test_label_pixels_are_not_zeroed_by_a_wrong_or_missing_detection_id(self):
        metrics = pixel_metrics(self.case, self.decision(selected_id="d99"), self.root)
        self.assertEqual(metrics["label_retention"], 1)
        self.assertEqual(metrics["raw_label_retention"], 1)

    def test_keep_mask_cannot_credit_pixels_altered_in_actual_crop(self):
        decision = self.decision()
        altered = self.image.copy()
        altered.putpixel((30, 50), (255, 255, 255))
        decision.crop = png(altered)
        metrics = pixel_metrics(self.case, decision, self.root)
        self.assertAlmostEqual(metrics["label_retention"], 399 / 400)
        self.assertAlmostEqual(metrics["crop_target_coverage"], 3999 / 4000)

    def test_mask_holes_and_crop_bounds_reduce_retention_independently(self):
        decision = self.decision(box=(10, 10, 60, 50))
        decision.keep_mask.paste(0, (20, 40, 30, 50))
        metrics = pixel_metrics(self.case, decision, self.root)
        self.assertEqual(metrics["label_retention"], 0.25)

    def test_missing_real_label_gt_is_unavailable_not_zero(self):
        self.case["label_ground_truth"] = False
        metrics = pixel_metrics(self.case, self.decision(), self.root)
        self.assertIsNone(metrics["label_retention"])

    def test_no_ground_truth_target_does_not_invent_coverage(self):
        self.case.update(
            target_instance_id=None, expected_status="no_target", annotations=[]
        )
        metrics = pixel_metrics(self.case, self.decision(selected_id=None), self.root)
        self.assertIsNone(metrics["crop_target_coverage"])
        self.assertIsNone(metrics["crop_distractor_retention"])
        self.assertTrue(metrics["full_frame_context"])

    def test_legacy_fixture_has_no_new_contract_pixel_or_decision_score(self):
        case = dict(self.case, provenance="geometry_fixture")
        decision = self.decision(selected_id=None)
        decision.variant = "scene-v1"
        result = assess(case, [], decision, self.root, self.image)
        for key in (
            "conformance_pass",
            "label_retention",
            "raw_label_retention",
            "crop_target_coverage",
            "crop_distractor_retention",
        ):
            self.assertIsNone(result[key], key)

    def test_default_replay_does_not_prepare_or_rewrite_annotations(self):
        def sha(p):
            return hashlib.sha256(p.read_bytes()).hexdigest()

        for name, value in (
            ("cases.json", []),
            ("protocol.json", {"cases": []}),
            ("policy-targets.json", {}),
        ):
            (self.root / name).write_text(json.dumps(value))
        (self.root / "comparison-inputs.json").write_text(
            json.dumps(
                dict(
                    files_sha256={
                        name: sha(self.root / name)
                        for name in (
                            "cases.json",
                            "protocol.json",
                            "policy-targets.json",
                        )
                    }
                )
            )
        )
        (self.root / "predictions").mkdir()
        (self.root / "prediction-inputs.json").write_text(
            json.dumps(
                dict(
                    annotation_inputs_sha256=sha(self.root / "comparison-inputs.json"),
                    files_sha256={},
                )
            )
        )
        before = {
            name: sha(self.root / name)
            for name in (
                "cases.json",
                "protocol.json",
                "policy-targets.json",
                "comparison-inputs.json",
                "prediction-inputs.json",
            )
        }
        with (
            mock.patch(
                "matcher.experiments.main_selector.export_suite.export",
                side_effect=AssertionError("No implicit export"),
            ),
            mock.patch(
                "matcher.experiments.main_selector.fallback_suite.attach",
                side_effect=AssertionError("No implicit preparation"),
            ),
        ):
            run(self.root, None, [], reuse_cases=False)
        self.assertEqual(before, {name: sha(self.root / name) for name in before})

    def test_metric_cohorts_separate_intent_policy_interaction_and_conformance(self):
        self.assertEqual(cohort(self.case), "passive_intent")
        self.assertEqual(
            cohort(dict(self.case, interaction={"tap": [0.1, 0.5]})), "interaction"
        )
        self.assertEqual(
            cohort(dict(self.case, target_kind="policy_fallback")), "policy_targets"
        )
        self.assertEqual(
            cohort(dict(self.case, expected_status="no_target")), "no_target"
        )
        self.assertEqual(
            cohort(dict(self.case, provenance="geometry_fixture")), "rule_conformance"
        )

    def test_policy_target_is_derived_from_gt_geometry_not_existing_target_id(self):
        case = dict(self.case, target_instance_id=99, acceptable_instance_ids=[1, 3])
        self.assertEqual(policy_target(case, self.root), 1)

    def test_policy_id_match_and_required_fallback_are_separate_metrics(self):
        case = dict(
            self.case, target_kind="policy_fallback", expected_selection_mode="fallback"
        )
        ann = self.case["annotations"][0]
        detection = dict(
            label="wine bottle",
            score=0.9,
            box=ann["box"],
            mask_png_b64=base64.b64encode(
                (self.root / ann["mask"]).read_bytes()
            ).decode(),
        )
        decision = self.decision()
        confident = assess(case, [detection], decision, self.root, self.image)
        self.assertTrue(confident["policy_target_match"])
        self.assertFalse(confident["policy_fallback_pass"])
        decision.selection_mode = "fallback"
        self.assertTrue(
            assess(case, [detection], decision, self.root, self.image)[
                "policy_fallback_pass"
            ]
        )

    def test_policy_geometry_exposes_exact_tie_and_deciding_rule(self):
        for ident, bounds in ((1, (10, 10, 40, 90)), (3, (60, 10, 90, 90))):
            ann = next(a for a in self.case["annotations"] if a["instance_id"] == ident)
            mask = Image.new("L", (100, 100))
            x, y, X, Y = bounds
            ImageDraw.Draw(mask).rectangle((x, y, X - 1, Y - 1), fill=255)
            mask.save(self.root / ann["mask"])
            ann["box"] = list(bounds)
        geometry = policy_geometry(
            dict(self.case, acceptable_instance_ids=[1, 3]), self.root
        )
        self.assertEqual(geometry["winner_instance_id"], 1)
        self.assertEqual(geometry["reason"], "fallback_leftmost")
        self.assertEqual(geometry["runner_distance_margin_px"], 0)
        self.assertTrue(geometry["exact_distance_tie"])

    def test_foreign_labels_representations_and_signage_are_scored_separately(self):
        for ident, category, parent, bounds in (
            (4, "label_front", 3, (75, 40, 85, 60)),
            (5, "tool", None, (60, 20, 70, 30)),
            (6, "price_tag", None, (60, 70, 70, 80)),
        ):
            path = f"extra-{ident}.png"
            mask = Image.new("L", (100, 100))
            x, y, X, Y = bounds
            ImageDraw.Draw(mask).rectangle((x, y, X - 1, Y - 1), fill=255)
            mask.save(self.root / path)
            self.case["annotations"].append(
                dict(
                    instance_id=ident,
                    category=category,
                    parent_instance_id=parent,
                    mask=path,
                    box=list(bounds),
                )
            )
        cropped = pixel_metrics(
            self.case, self.decision(box=(10, 10, 60, 90)), self.root
        )
        complete = pixel_metrics(self.case, self.decision(), self.root)
        for key in (
            "foreign_label_retention",
            "representation_retention",
            "price_tag_retention",
        ):
            self.assertEqual(cropped[key], 0, key)
            self.assertEqual(complete[key], 1, key)

    def test_frozen_input_verification_is_read_only_and_rejects_changed_annotations(
        self,
    ):
        def sha(path):
            return hashlib.sha256(path.read_bytes()).hexdigest()

        self.case["image_sha256"] = sha(self.root / self.case["image"])
        for ann in self.case["annotations"]:
            ann["sha256"] = sha(self.root / ann["mask"])
        (self.root / "cases.json").write_text(json.dumps([self.case]))
        for name in ("protocol.json", "policy-targets.json"):
            (self.root / name).write_text("{}")
        frozen = {
            "files_sha256": {
                name: sha(self.root / name)
                for name in ("cases.json", "protocol.json", "policy-targets.json")
            }
        }
        (self.root / "comparison-inputs.json").write_text(json.dumps(frozen))
        before = {p.name: sha(p) for p in self.root.iterdir()}
        verify_frozen_inputs(self.root)
        self.assertEqual(before, {p.name: sha(p) for p in self.root.iterdir()})
        (self.root / "cases.json").write_text("[]")
        with self.assertRaisesRegex(RuntimeError, "Frozen input changed"):
            verify_frozen_inputs(self.root)

    def test_prediction_cache_freeze_detects_content_edits_and_added_files(self):
        def sha(p):
            return hashlib.sha256(p.read_bytes()).hexdigest()

        self.case["image_sha256"] = sha(self.root / self.case["image"])
        for ann in self.case["annotations"]:
            ann["sha256"] = sha(self.root / ann["mask"])
        (self.root / "cases.json").write_text(json.dumps([self.case]))
        (self.root / "comparison-inputs.json").write_text(
            json.dumps(dict(files_sha256={"cases.json": sha(self.root / "cases.json")}))
        )
        predictions = self.root / "predictions"
        predictions.mkdir()
        cache = predictions / "sample-live.json"
        cache.write_text('{"instances":[]}')
        (self.root / "prediction-inputs.json").write_text(
            json.dumps(
                dict(
                    annotation_inputs_sha256=sha(self.root / "comparison-inputs.json"),
                    files_sha256={"predictions/sample-live.json": sha(cache)},
                )
            )
        )
        verify_frozen_inputs(self.root)
        cache.write_text('{"instances":[{}]}')
        with self.assertRaisesRegex(RuntimeError, "Frozen prediction caches changed"):
            verify_frozen_inputs(self.root)
        cache.write_text('{"instances":[]}')
        (predictions / "unexpected.json").write_text("{}")
        with self.assertRaisesRegex(RuntimeError, "Frozen prediction caches changed"):
            verify_frozen_inputs(self.root)
