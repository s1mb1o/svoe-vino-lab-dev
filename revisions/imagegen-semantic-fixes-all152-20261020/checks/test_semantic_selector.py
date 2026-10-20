"""Semantic selector contracts, context retention, fallback and integration."""

import base64
from io import BytesIO
import json
from pathlib import Path
import unittest
from unittest import mock

import numpy as np
from PIL import Image, ImageDraw

from matcher.group import GroupMatchError
from selector_cases import (
    SCENARIOS,
    REVIEW_SCENARIOS,
    materialize,
)
from matcher.semantic_selector import NOUNS, select, select_photo, select_variant
from test_group import FakeOpener


SIZE = (240, 240)


def png(im):
    f = BytesIO()
    im.save(f, "PNG")
    return f.getvalue()


def detection(label, box, *, mask_box=None, score=0.9, holes=()):
    mask = Image.new("L", SIZE)
    b = mask_box or box
    ImageDraw.Draw(mask).rectangle((b[0], b[1], b[2] - 1, b[3] - 1), fill=255)
    for x, y, X, Y in holes:
        ImageDraw.Draw(mask).rectangle((x, y, X - 1, Y - 1), fill=0)
    return dict(
        label=label,
        box=list(box),
        score=score,
        area=1,
        mask_png_b64=base64.b64encode(png(mask)).decode(),
    )


def rotate_inputs(photo, items, operation):
    w, h = photo.size
    result = []
    for item in items:
        x, y, X, Y = item["box"]
        bounds = {
            Image.Transpose.ROTATE_90: (y, w - X, Y, w - x),
            Image.Transpose.ROTATE_180: (w - X, h - Y, w - x, h - y),
            Image.Transpose.ROTATE_270: (h - Y, x, h - y, X),
        }[operation]
        with Image.open(BytesIO(base64.b64decode(item["mask_png_b64"]))) as opened:
            mask = opened.transpose(operation)
        result.append(
            dict(
                item,
                box=list(bounds),
                mask_png_b64=base64.b64encode(png(mask)).decode(),
            )
        )
    return photo.transpose(operation), result


class SemanticSelectorTest(unittest.TestCase):
    def setUp(self):
        self.photo = Image.new("RGB", SIZE, "#b99373")
        self.bottle = detection("wine bottle", (70, 10, 170, 235))
        self.label = detection("wine label", (75, 100, 165, 200))

    def test_large_logo_is_not_a_subject(self):
        logo = detection("logo", (85, 120, 155, 190), score=0.99)
        result = select(self.photo, [logo, self.bottle, self.label])
        self.assertEqual((result.status, result.selected_id), ("selected", "d1"))
        self.assertEqual(len(result.candidates), 1)
        self.assertEqual(len(result.label_crops), 1)

    def test_nested_artwork_misclassified_as_label_uses_complete_enclosing_label(self):
        logo = detection("wine label", (95, 130, 145, 180), score=0.99)
        result = select(self.photo, [self.bottle, self.label, logo])
        self.assertEqual(result.candidates[0]["label_ids"], ["d1"])
        self.assertEqual(len(result.label_crops), 1)

    def test_nested_boxes_do_not_remove_labels_from_different_bottle_owners(self):
        instances = [
            detection("wine bottle", (40, 0, 200, 240), mask_box=(40, 0, 110, 240)),
            detection("wine bottle", (100, 20, 190, 220), mask_box=(120, 20, 190, 220)),
            detection("wine label", (50, 80, 180, 200), mask_box=(50, 80, 100, 200)),
            detection("wine label", (125, 100, 175, 180)),
        ]
        result = select(self.photo, instances)
        ownership = {c["id"]: c["label_ids"] for c in result.candidates}
        self.assertEqual(ownership, {"d0": ["d2"], "d1": ["d3"]})

    def test_complete_label_box_preserves_holes_and_original_pixels(self):
        label = detection(
            "wine label", (75, 100, 165, 200), mask_box=(95, 120, 145, 180)
        )
        bottle = detection(
            "wine bottle", (70, 10, 170, 235), mask_box=(90, 10, 150, 235)
        )
        result = select(self.photo, [bottle, label])
        self.assertEqual(result.keep_mask.getpixel((76, 101)), 255)
        with Image.open(BytesIO(result.label_crops[0])) as im:
            self.assertEqual(im.getpixel((5, 5)), self.photo.getpixel((76, 101)))

    def test_lone_label_keeps_whole_frame_even_if_detection_is_only_a_logo(self):
        result = select(self.photo, [detection("wine label", (90, 90, 130, 130))])
        self.assertEqual(result.crop_box, (0, 0, 240, 240))
        self.assertTrue(np.all(np.asarray(result.keep_mask) == 255))
        with Image.open(BytesIO(result.label_crops[0])) as view:
            self.assertEqual(view.size, SIZE)

    def test_secondary_labels_return_separate_views(self):
        other = detection("wine label", (90, 30, 150, 55))
        result = select(self.photo, [self.bottle, self.label, other])
        self.assertEqual(len(result.label_crops), 2)

    def test_label_role_is_not_guessed_from_codes(self):
        result = select(
            self.photo, [self.bottle, detection("label_back", (75, 100, 165, 200))]
        )
        self.assertEqual(result.candidates[0]["label_ids"], ["d1"])

    def test_no_label_does_not_remove_a_bottle(self):
        result = select(self.photo, [self.bottle])
        self.assertEqual(result.status, "selected")
        self.assertEqual(result.keep_mask.getpixel((71, 11)), 255)

    def test_equal_bottles_return_left_crop_with_fallback_metadata(self):
        result = select(
            self.photo,
            [
                detection("wine bottle", (15, 20, 85, 230)),
                detection("wine bottle", (155, 20, 225, 230)),
            ],
        )
        self.assertEqual(result.status, "selected")
        self.assertEqual(result.selected_id, "d0")
        self.assertEqual(result.selection_mode, "fallback")
        self.assertEqual(result.reason, "fallback_leftmost")
        self.assertEqual(result.fallback_trigger, "no_clear_main_subject")
        self.assertTrue(result.crop)
        self.assertEqual(len(result.candidates), 2)

    def test_center_of_three_equal_bottles_is_not_invented_intent(self):
        result = select(
            self.photo,
            [detection("wine bottle", (x, 20, x + 50, 220)) for x in (5, 95, 185)],
        )
        self.assertEqual(result.selected_id, "d1")
        self.assertEqual(result.selection_mode, "fallback")
        self.assertEqual(result.reason, "fallback_center_contains")

    def test_tap_on_label_selects_its_bottle(self):
        instances = [
            detection("wine bottle", (15, 20, 85, 230)),
            detection("wine bottle", (155, 20, 225, 230)),
            detection("wine label", (160, 100, 220, 180)),
        ]
        result = select(self.photo, instances, tap=(0.78, 0.6))
        self.assertEqual((result.selected_id, result.reason), ("d1", "explicit_tap"))
        self.assertEqual(result.selection_mode, "confident")
        self.assertIsNone(result.fallback_trigger)

    def test_tap_miss_returns_crop_even_if_one_bottle_exists(self):
        result = select(self.photo, [self.bottle], tap=(0, 0))
        self.assertEqual(result.status, "selected")
        self.assertEqual(result.reason, "only_credible_subject")
        self.assertEqual(result.selection_mode, "confident")
        self.assertIsNone(result.fallback_trigger)
        self.assertTrue(result.crop)

    def test_missed_tap_continues_unique_hand_check(self):
        instances = [
            detection("wine bottle", (15, 20, 85, 230)),
            detection("wine bottle", (100, 60, 140, 200)),
            detection("hand", (40, 80, 60, 190)),
        ]
        result = select(self.photo, instances, tap=(0.98, 0.02))
        self.assertEqual(
            (result.selected_id, result.reason), ("d0", "unique_visible_hand_contact")
        )
        self.assertTrue(result.crop)

    def test_missed_tap_continues_reticle_and_dominance_checks(self):
        pair = [
            detection("wine bottle", (15, 20, 85, 230)),
            detection("wine bottle", (155, 20, 225, 230)),
        ]
        result = select(self.photo, pair, tap=(0, 0), aim=(0.8, 0.5))
        self.assertEqual(
            (result.selected_id, result.reason), ("d1", "explicit_capture_reticle")
        )
        result = select(
            self.photo,
            [
                detection("wine bottle", (0, 0, 90, 240)),
                detection("wine bottle", (130, 80, 165, 175)),
            ],
            tap=(0.99, 0.01),
        )
        self.assertEqual(result.selected_id, "d0")
        self.assertIn(
            result.reason,
            ("dominant_foreground_subject", "foreground_scale_and_lower_base"),
        )

    def test_mask_tap_takes_precedence_over_other_owners_label_rectangle(self):
        instances = [
            detection("wine bottle", (10, 20, 80, 230)),
            detection("wine bottle", (100, 20, 124, 230)),
            detection("wine bottle", (125, 20, 195, 230)),
            detection("wine label", (20, 100, 135, 180), mask_box=(20, 100, 75, 180)),
        ]
        result = select(self.photo, instances, tap=(0.54, 0.6))
        self.assertEqual((result.selected_id, result.reason), ("d2", "explicit_tap"))
        self.assertEqual(result.tap_candidate_ids, ["d2"])

    def test_multihit_tap_never_selects_an_untapped_center_candidate(self):
        instances = [
            detection("wine bottle", (10, 20, 150, 230)),
            detection("wine bottle", (100, 20, 124, 230)),
            detection("wine bottle", (130, 20, 230, 230)),
        ]
        result = select(self.photo, instances, tap=(0.58, 0.6))
        self.assertEqual(set(result.tap_candidate_ids), {"d0", "d2"})
        self.assertIn(result.selected_id, result.tap_candidate_ids)
        center = next(c for c in result.candidates if c["id"] == "d1")
        self.assertFalse(center["eligible_for_selection"])
        self.assertTrue(result.crop)

    def test_valid_unique_tap_still_overrides_hand(self):
        instances = [
            detection("wine bottle", (15, 20, 85, 230)),
            detection("wine bottle", (155, 20, 225, 230)),
            detection("hand", (85, 80, 120, 190)),
        ]
        result = select(self.photo, instances, tap=(0.8, 0.5))
        self.assertEqual((result.selected_id, result.reason), ("d1", "explicit_tap"))

    def test_explicit_reticle_resolves_equal_bottles(self):
        instances = [
            detection("wine bottle", (15, 20, 85, 230)),
            detection("wine bottle", (155, 20, 225, 230)),
        ]
        self.assertEqual(
            select(self.photo, instances, aim=(0.8, 0.5)).selected_id, "d1"
        )

    def test_hand_box_without_mask_contact_is_not_a_grip(self):
        instances = [
            detection("wine bottle", (15, 20, 85, 230)),
            detection("wine bottle", (155, 20, 225, 230)),
            detection("hand", (0, 0, 240, 240), mask_box=(105, 10, 135, 30)),
        ]
        result = select(self.photo, instances)
        self.assertEqual(result.selection_mode, "fallback")
        self.assertEqual(
            [x["signals"]["hand_contact"] for x in result.candidates], [0, 0]
        )

    def test_unique_mask_contact_needs_positive_grip_evidence(self):
        instances = [
            detection("wine bottle", (15, 20, 85, 230)),
            detection("wine bottle", (155, 20, 225, 230)),
            detection("hand", (85, 80, 120, 190)),
        ]
        result = select(self.photo, instances)
        self.assertEqual(result.selection_mode, "fallback")
        self.assertEqual(result.fallback_trigger, "hand_contact_not_confirmed")
        # A substantial hand crossing the front supplies the missing evidence.
        instances[-1] = detection("hand", (70, 80, 120, 190))
        result = select(self.photo, instances)
        self.assertEqual(
            (result.selected_id, result.reason), ("d0", "unique_visible_hand_contact")
        )

    def test_two_held_bottles_use_fallback_instead_of_false_grip_priority(self):
        instances = [
            detection("wine bottle", (15, 20, 85, 230)),
            detection("wine bottle", (155, 20, 225, 230)),
            detection("hand", (85, 80, 115, 190)),
            detection("hand", (125, 80, 155, 190)),
        ]
        self.assertEqual(select(self.photo, instances).selection_mode, "fallback")

    def test_two_grips_with_slightly_different_support_remain_fallback(self):
        instances = [
            detection("wine bottle", (15, 20, 85, 230)),
            detection("wine bottle", (155, 20, 225, 230)),
            detection("hand", (85, 80, 115, 190)),
            detection("hand", (125, 80, 155, 165)),
        ]
        self.assertEqual(select(self.photo, instances).selection_mode, "fallback")

    def test_tap_status_distinguishes_absent_missed_mask_and_label_context(self):
        self.assertEqual(select(self.photo, [self.bottle]).tap_status, "absent")
        missed = select(self.photo, [self.bottle], tap=(0, 0))
        self.assertEqual(missed.tap_status, "missed")
        self.assertEqual(missed.selection_mode, "confident")
        self.assertEqual(missed.as_dict(media=False)["tap_status"], "missed")
        self.assertEqual(
            select(self.photo, [self.bottle], tap=(0.5, 0.5)).tap_status,
            "resolved_mask",
        )
        missing_paper = detection(
            "wine bottle", (70, 10, 170, 235), holes=[(70, 100, 170, 200)]
        )
        self.assertEqual(
            select(self.photo, [missing_paper, self.label], tap=(0.5, 0.6)).tap_status,
            "resolved_label_context",
        )

    def test_multiple_tap_hits_are_reported_separately(self):
        result = select(
            self.photo,
            [
                detection("wine bottle", (10, 20, 150, 230)),
                detection("wine bottle", (130, 20, 230, 230)),
            ],
            tap=(0.58, 0.5),
        )
        self.assertEqual(result.tap_status, "multiple_hits")
        self.assertEqual(set(result.tap_candidate_ids), {"d0", "d1"})

    def test_non_dominating_price_card_misclassified_as_wine_label_cannot_hijack(self):
        items = [
            detection("wine bottle", (10, 20, 70, 230)),
            detection("price tag", (160, 40, 235, 190)),
            detection("wine label", (160, 40, 235, 190)),
        ]
        result = select(self.photo, items)
        self.assertEqual(result.selected_id, "d0")
        self.assertIn({"id": "d2", "reason": "standalone_price_tag"}, result.rejected)

    def test_associated_wine_paper_survives_false_price_tag_detection(self):
        result = select(
            self.photo, [self.bottle, self.label, dict(self.label, label="price tag")]
        )
        self.assertEqual(result.candidates[0]["label_ids"], ["d1"])
        self.assertTrue(result.label_crops)

    def test_attached_tag_outside_bottle_box_survives_price_tag_confusion(self):
        bottle = detection("wine bottle", (70, 10, 120, 235))
        tag = detection("wine label", (105, 30, 170, 60))
        main = detection("wine label", (75, 100, 115, 180))
        result = select(self.photo, [bottle, main, tag, dict(tag, label="price tag")])
        self.assertEqual(result.selected_id, "d0")
        self.assertEqual(set(result.candidates[0]["label_ids"]), {"d1", "d2"})
        self.assertGreaterEqual(result.crop_box[2], 170)
        self.assertEqual(result.keep_mask.getpixel((165, 45)), 255)

    def test_partial_paper_overlap_with_two_bottles_stays_unassigned(self):
        items = [
            detection("wine bottle", (70, 10, 115, 235)),
            detection("wine bottle", (125, 10, 170, 235)),
            detection("wine label", (95, 100, 145, 140)),
        ]
        result = select(self.photo, items)
        self.assertTrue(all(not c["label_ids"] for c in result.candidates))

    def test_attached_paper_with_only_price_tag_class_is_preserved(self):
        result = select(
            self.photo,
            [
                detection("wine bottle", (70, 10, 120, 235)),
                detection("price tag", (105, 30, 170, 60)),
            ],
        )
        self.assertEqual(result.selected_id, "d0")
        self.assertEqual(result.candidates[0]["label_ids"], ["d1"])
        self.assertEqual(result.keep_mask.getpixel((165, 45)), 255)

    def test_standalone_price_tag_cannot_become_a_wine_candidate(self):
        result = select(self.photo, [detection("price tag", (20, 40, 220, 200))])
        self.assertEqual(result.status, "no_target")
        self.assertIsNone(result.selected_id)
        self.assertTrue(result.crop)

    def test_paper_crossing_box_edge_survives_zero_visible_mask_overlap(self):
        bottle = detection(
            "wine bottle", (70, 10, 120, 235), holes=[(100, 30, 120, 60)]
        )
        tag = detection("wine label", (100, 30, 165, 60))
        result = select(self.photo, [bottle, tag, dict(tag, label="price tag")])
        self.assertEqual(result.candidates[0]["label_ids"], ["d1"])
        self.assertEqual(result.keep_mask.getpixel((160, 45)), 255)

    def test_wine_label_presence_cannot_steal_a_held_unlabelled_carton(self):
        items = [
            detection("wine bottle", (15, 20, 85, 230)),
            detection("wine label", (20, 100, 80, 180)),
            detection("box", (80, 65, 155, 170)),
            detection("hand", (85, 80, 115, 190)),
        ]
        result = select(self.photo, items)
        self.assertEqual(
            (result.selected_id, result.reason), ("d2", "unique_visible_hand_contact")
        )
        without_label = select(self.photo, [items[0], *items[2:]])
        self.assertEqual(without_label.selected_id, "d1")
        self.assertEqual(result.crop_box, without_label.crop_box)

    def test_unowned_complete_label_extent_is_not_discarded_for_a_logo_mask(self):
        result = select(
            self.photo,
            [
                detection("wine bottle", (180, 30, 230, 230)),
                detection("wine label", (0, 0, 170, 240), mask_box=(0, 0, 20, 40)),
            ],
        )
        self.assertEqual(result.selection_mode, "fallback")
        self.assertEqual(result.crop_scope, "context_frame")
        self.assertEqual(result.keep_mask.getpixel((100, 180)), 255)

        tapped = select(
            self.photo,
            [
                detection("wine bottle", (180, 30, 230, 230)),
                detection("wine label", (0, 0, 170, 240), mask_box=(0, 0, 20, 40)),
            ],
            tap=(100 / 240, 180 / 240),
        )
        self.assertEqual((tapped.selected_id, tapped.reason), ("d1", "explicit_tap"))
        self.assertEqual(tapped.tap_status, "resolved_label_context")

    def test_incidental_front_wrap_cannot_erase_a_stronger_grip(self):
        spec = next(s for s in REVIEW_SCENARIOS if s["id"] == "weak-wrap-strong-grip")
        photo, items, _ = materialize(spec)
        result = select(photo, items)
        self.assertEqual(result.selection_mode, "fallback")
        self.assertEqual(
            [
                c["id"]
                for c in result.candidates
                if c["signals"]["confirmed_hand_owner"]
            ],
            ["d0"],
        )
        # Removing the small front stripe must not change the strong owner.
        items[-1] = detection("hand", (85, 80, 100, 190))
        control = select(photo, items)
        self.assertEqual(control.selected_id, result.selected_id)
        self.assertEqual(
            [
                c["id"]
                for c in control.candidates
                if c["signals"]["confirmed_hand_owner"]
            ],
            ["d0"],
        )
        items[-1] = detection("hand", (70, 80, 100, 190))
        positive = select(photo, items)
        self.assertEqual(
            (positive.selected_id, positive.reason),
            ("d0", "unique_visible_hand_contact"),
        )

    def test_confirmed_owners_block_unheld_foreground_even_with_an_uncertain_hand(self):
        for name, owners in (
            ("multiple-grips-unheld-foreground", {"d0", "d1"}),
            ("owner-and-uncertain-background", {"d0"}),
        ):
            spec = next(s for s in REVIEW_SCENARIOS if s["id"] == name)
            with self.subTest(name=name):
                photo, items, _ = materialize(spec)
                result = select(photo, items)
                self.assertEqual(result.selection_mode, "fallback")
                self.assertEqual(
                    {
                        c["id"]
                        for c in result.candidates
                        if c["signals"]["confirmed_hand_owner"]
                    },
                    owners,
                )
                self.assertEqual(result.selected_id, "d%d" % spec["winner"])

    def test_held_neck_and_explicit_tap_keep_unowned_complete_paper(self):
        for name in ("held-neck-dominant-paper", "held-neck-pending-logo"):
            spec = next(s for s in REVIEW_SCENARIOS if s["id"] == name)
            photo, items, _ = materialize(spec)
            x, y, X, Y = items[0]["box"]
            tap = ((x + X) / (2 * photo.width), (y + Y) / (2 * photo.height))
            for interaction in ({}, {"tap": tap}):
                with self.subTest(name=name, interaction=interaction):
                    result = select(photo, items, **interaction)
                    self.assertEqual(
                        result.selected_id,
                        "d0" if interaction else "d%d" % spec["winner"],
                    )
                    self.assertEqual(result.crop_scope, "context_frame")
                    with Image.open(BytesIO(result.crop)) as crop:
                        np.testing.assert_array_equal(crop, photo)

    def test_foreground_with_visible_neck_survives_actual_camera_roll(self):
        items = []
        for bounds in ((0, 0, 70, 240), (100, 65, 155, 215), (165, 65, 220, 215)):
            item = detection("wine bottle", bounds)
            x, y, X, Y = bounds
            w, h = X - x, Y - y
            mask = Image.new("L", SIZE)
            ImageDraw.Draw(mask).polygon(
                [
                    (x, Y - 1),
                    (X - 1, Y - 1),
                    (X - 1, y + h * 0.45),
                    (x + w * 0.65, y + h * 0.30),
                    (x + w * 0.65, y),
                    (x + w * 0.35, y),
                    (x + w * 0.35, y + h * 0.30),
                    (x, y + h * 0.45),
                ],
                fill=255,
            )
            item["mask_png_b64"] = base64.b64encode(png(mask)).decode()
            items.append(item)
        for operation in (
            Image.Transpose.ROTATE_90,
            Image.Transpose.ROTATE_180,
            Image.Transpose.ROTATE_270,
        ):
            with self.subTest(operation=operation):
                photo, rotated = rotate_inputs(self.photo, items, operation)
                result = select(photo, rotated)
                self.assertEqual(result.selected_id, "d0")
                self.assertEqual(result.reason, "foreground_scale_and_lower_base")

    def test_attached_paper_stays_complete_after_actual_camera_roll(self):
        tag = detection("wine label", (105, 30, 170, 60))
        items = [
            detection("wine bottle", (70, 10, 120, 235)),
            tag,
            dict(tag, label="price tag"),
        ]
        for operation, point in (
            (Image.Transpose.ROTATE_90, (45, 79)),
            (Image.Transpose.ROTATE_180, (79, 194)),
            (Image.Transpose.ROTATE_270, (194, 160)),
        ):
            with self.subTest(operation=operation):
                photo, rotated = rotate_inputs(self.photo, items, operation)
                result = select(photo, rotated)
                self.assertEqual(result.selected_id, "d0")
                self.assertEqual(result.candidates[0]["label_ids"], ["d1"])
                self.assertEqual(result.keep_mask.getpixel(point), 255)

    def test_price_only_context_is_not_wine_identity_for_hand_conflicts(self):
        items = [
            detection("wine bottle", (15, 20, 85, 100)),
            detection("wine bottle", (95, 10, 155, 230)),
            detection("price tag", (105, 100, 145, 150)),
            detection("hand", (60, 40, 80, 85)),
        ]
        result = select(self.photo, items)
        self.assertEqual(
            (result.selected_id, result.reason), ("d0", "unique_visible_hand_contact")
        )

    def test_labeled_held_carton_is_not_blanket_rejected_for_a_nearby_bottle(self):
        items = [
            detection("wine bottle", (15, 20, 85, 230)),
            detection("wine label", (20, 100, 80, 180)),
            detection("box", (80, 65, 155, 170)),
            detection("hand", (85, 80, 115, 190)),
            detection("wine label", (115, 100, 150, 150)),
        ]
        result = select(self.photo, items)
        self.assertEqual(
            (result.selected_id, result.reason), ("d2", "unique_visible_hand_contact")
        )

    def test_foreground_crop_is_invariant_to_detection_order_and_duplicates(self):
        items = [
            detection("wine bottle", (0, 0, 70, 240)),
            detection("wine bottle", (100, 65, 155, 215)),
            detection("wine bottle", (165, 65, 220, 215)),
        ]
        original = select(self.photo, items)
        for altered in (items[::-1], items[1:] + items[:1], items + [items[0]]):
            with self.subTest(order=altered):
                result = select(self.photo, altered)
                self.assertEqual(result.reason, "foreground_scale_and_lower_base")
                self.assertEqual(result.crop_box, original.crop_box)
                self.assertEqual(result.crop, original.crop)

    def test_uniform_resize_preserves_clear_foreground_selection(self):
        items = [
            detection("wine bottle", (0, 0, 70, 240)),
            detection("wine bottle", (100, 65, 155, 215)),
            detection("wine bottle", (165, 65, 220, 215)),
        ]
        resized = []
        for item in items:
            with Image.open(BytesIO(base64.b64decode(item["mask_png_b64"]))) as opened:
                mask = opened.resize((480, 480), Image.Resampling.NEAREST)
            resized.append(
                dict(
                    item,
                    box=[v * 2 for v in item["box"]],
                    mask_png_b64=base64.b64encode(png(mask)).decode(),
                )
            )
        result = select(self.photo.resize((480, 480)), resized)
        self.assertEqual(result.selected_id, "d0")
        self.assertEqual(result.reason, "foreground_scale_and_lower_base")

    def test_duplicate_hand_detections_do_not_create_two_different_subjects(self):
        items = [
            detection("wine bottle", (15, 20, 85, 230)),
            detection("wine bottle", (155, 20, 225, 230)),
            detection("hand", (85, 80, 115, 190)),
        ]
        result = select(self.photo, items + [items[-1]])
        self.assertEqual(result.selected_id, "d0")
        self.assertEqual(result.selection_mode, "fallback")
        items[-1] = detection("hand", (70, 80, 115, 190))
        result = select(self.photo, items + [items[-1]])
        self.assertEqual(result.reason, "unique_visible_hand_contact")

    def test_grip_support_metadata_keeps_independent_hand_values(self):
        items = [
            detection("wine bottle", (15, 20, 85, 230)),
            detection("wine bottle", (155, 20, 225, 230)),
            detection("hand", (85, 80, 115, 190)),
            detection("hand", (125, 130, 155, 160)),
        ]
        result = select(self.photo, items)
        self.assertEqual(result.selection_mode, "fallback")
        self.assertEqual(result.fallback_trigger, "multiple_hand_subjects")
        self.assertEqual(
            set(result.candidates[0]["signals"]["hand_contacts"]), {"d2", "d3"}
        )

    def test_ambiguous_rectangle_label_ownership_does_not_cross_assign(self):
        items = [
            detection("wine bottle", (10, 20, 150, 230), mask_box=(10, 20, 40, 230)),
            detection("wine bottle", (80, 20, 230, 230), mask_box=(200, 20, 230, 230)),
            detection("wine label", (100, 100, 140, 150)),
        ]
        result = select(self.photo, items)
        self.assertTrue(
            all(
                not item["label_ids"]
                for item in result.candidates
                if item["kind"] == "wine bottle"
            )
        )

    def test_tiny_contact_distractor_cannot_saturate_and_cancel_a_grip(self):
        instances = [
            detection("wine bottle", (20, 20, 90, 230)),
            detection("wine bottle", (140, 20, 210, 230)),
            detection("hand", (90, 80, 110, 190)),
            detection("can", (110, 100, 120, 120)),
        ]
        result = select(self.photo, instances)
        self.assertEqual(result.selection_mode, "fallback")
        signals = {c["id"]: c["signals"]["hand_contact"] for c in result.candidates}
        self.assertGreater(signals["d0"], signals["d3"] * 1.5)
        instances[2] = detection("hand", (80, 80, 110, 190))
        positive = select(self.photo, instances)
        self.assertEqual(
            (positive.selected_id, positive.reason),
            ("d0", "unique_visible_hand_contact"),
        )

    def test_frozen_pointing_and_projected_hand_masks_use_fallback_under_roll(self):
        data = json.loads(
            (Path(__file__).parent / "data/semantic-confidence-masks.json").read_text()
        )
        for row in data["rows"]:
            if row["case_id"] not in ("hc-039", "hc-041"):
                continue
            photo = Image.new("RGB", row["size"], "#987654")
            for rotation in (
                None,
                Image.Transpose.ROTATE_90,
                Image.Transpose.ROTATE_180,
                Image.Transpose.ROTATE_270,
            ):
                with self.subTest(
                    case=row["case_id"], mode=row["mode"], rotation=rotation
                ):
                    image, items = (
                        rotate_inputs(photo, row["instances"], rotation)
                        if rotation
                        else (photo, row["instances"])
                    )
                    result = select(image, items)
                    self.assertEqual(result.selection_mode, "fallback")
                    self.assertEqual(
                        result.fallback_trigger, "hand_contact_not_confirmed"
                    )
                    self.assertTrue(result.crop)

    def test_frozen_positive_grips_and_real_pour_keep_their_subjects(self):
        data = json.loads(
            (Path(__file__).parent / "data/semantic-confidence-masks.json").read_text()
        )
        for row in data["rows"]:
            if row["case_id"] not in (
                "hc-020",
                "hc-024",
                "hc-033",
                "hc-040",
                "hc-042",
                "real-541773",
            ):
                continue
            for rotation in (
                None,
                Image.Transpose.ROTATE_90,
                Image.Transpose.ROTATE_180,
                Image.Transpose.ROTATE_270,
            ):
                with self.subTest(
                    case=row["case_id"], mode=row["mode"], rotation=rotation
                ):
                    photo = Image.new("RGB", row["size"], "#987654")
                    image, items = (
                        rotate_inputs(photo, row["instances"], rotation)
                        if rotation
                        else (photo, row["instances"])
                    )
                    result = select(image, items)
                    expected = (
                        "d2"
                        if row["case_id"] == "real-541773"
                        else "d0"
                        if row["mode"] == "controlled"
                        else "d1"
                    )
                    expected = {"hc-020": "d4", "hc-024": "d5"}.get(
                        row["case_id"], expected
                    )
                    self.assertEqual(
                        (result.selected_id, result.reason),
                        (expected, "unique_visible_hand_contact"),
                    )
                    if row["case_id"] == "real-541773":
                        evidence = next(
                            c for c in result.candidates if c["id"] == expected
                        )["signals"]["grip_evidence"]["d8"]
                        self.assertFalse(evidence["front_wrap"])
                        self.assertTrue(evidence["terminal_opposition"])

    def test_frozen_printed_panel_keeps_context_and_rejects_inner_artwork(self):
        data = json.loads(
            (Path(__file__).parent / "data/semantic-confidence-masks.json").read_text()
        )
        row = next(
            r for r in data["rows"] if r["case_id"] == "hc-031" and r["mode"] == "live"
        )
        photo = Image.new("RGB", row["size"], "#987654")
        result = select(photo, row["instances"])
        self.assertEqual(
            (result.selected_id, result.selection_mode), ("d2", "fallback")
        )
        self.assertEqual(result.fallback_trigger, "enclosing_label_panel")
        self.assertIn(
            dict(id="d0", reason="bottle_depiction_in_label_panel"), result.rejected
        )
        self.assertEqual(result.crop_scope, "context_frame")
        with Image.open(BytesIO(result.crop)) as crop:
            np.testing.assert_array_equal(crop, photo)

    def test_panel_rectangle_alone_cannot_reject_a_real_foreground_bottle(self):
        items = [
            detection("wine bottle", (90, 40, 150, 220)),
            detection("wine label", (40, 10, 200, 235), holes=[(90, 40, 150, 220)]),
        ]
        result = select(self.photo, items, tap=(0.5, 0.5))
        self.assertEqual(result.selected_id, "d0")
        self.assertFalse(
            any(
                r["reason"] == "bottle_depiction_in_label_panel"
                for r in result.rejected
            )
        )

    def test_live_body_grips_stay_selected_when_another_bottle_is_at_photo_center(self):
        data = json.loads(
            (Path(__file__).parent / "data/semantic-confidence-masks.json").read_text()
        )
        for row in data["rows"]:
            if row["case_id"] not in ("hc-020", "hc-024"):
                continue
            w, h = row["size"]
            size = (2 * w + 200, h)
            photo = Image.new("RGB", size, "#987654")
            items = []
            for item in row["instances"]:
                with Image.open(
                    BytesIO(base64.b64decode(item["mask_png_b64"]))
                ) as opened:
                    mask = Image.new("L", size)
                    mask.paste(opened, (0, 0))
                items.append(
                    dict(item, mask_png_b64=base64.b64encode(png(mask)).decode())
                )
            center = size[0] // 2
            mask = Image.new("L", size)
            box = (center - 30, 40, center + 30, h - 40)
            ImageDraw.Draw(mask).rectangle(
                (box[0], box[1], box[2] - 1, box[3] - 1), fill=255
            )
            items.append(
                dict(
                    label="wine bottle",
                    box=list(box),
                    score=0.9,
                    mask_png_b64=base64.b64encode(png(mask)).decode(),
                )
            )
            with self.subTest(case=row["case_id"]):
                result = select(photo, items)
                self.assertEqual(
                    (result.selected_id, result.reason),
                    (
                        {"hc-020": "d4", "hc-024": "d5"}[row["case_id"]],
                        "unique_visible_hand_contact",
                    ),
                )

    def test_shortened_pointing_contact_is_not_confirmed_by_the_span_window(self):
        data = json.loads(
            (Path(__file__).parent / "data/semantic-confidence-masks.json").read_text()
        )
        row = next(
            r
            for r in data["rows"]
            if r["case_id"] == "hc-039" and r["mode"] == "controlled"
        )
        for region in (
            (245, 617, 346, row["size"][1]),
            (0, 617, row["size"][0], row["size"][1]),
        ):
            items = []
            for item in row["instances"]:
                if item["label"] == "hand":
                    with Image.open(
                        BytesIO(base64.b64decode(item["mask_png_b64"]))
                    ) as opened:
                        mask = opened.convert("L")
                    # Simulate a missing detector-mask segment next to the bottle,
                    # retaining the rest of the arm and the original photograph.
                    mask.paste(0, region)
                    item = dict(item, mask_png_b64=base64.b64encode(png(mask)).decode())
                items.append(item)
            for rotation in (
                None,
                Image.Transpose.ROTATE_90,
                Image.Transpose.ROTATE_180,
                Image.Transpose.ROTATE_270,
            ):
                photo = Image.new("RGB", row["size"], "#987654")
                image, detections = (
                    rotate_inputs(photo, items, rotation)
                    if rotation
                    else (photo, items)
                )
                with self.subTest(region=region, rotation=rotation):
                    result = select(image, detections)
                    evidence = next(c for c in result.candidates if c["id"] == "d0")[
                        "signals"
                    ]["grip_evidence"]["d4"]
                    self.assertLess(evidence["contact_span"], 0.50)
                    self.assertGreater(evidence["front_fraction"], 0.12)
                    self.assertGreater(evidence["front_body_fraction"], 0.10)
                    self.assertFalse(evidence["localized_front_contact"])
                    self.assertFalse(evidence["broad_front_contact"])
                    self.assertEqual(result.selection_mode, "fallback")
                    self.assertEqual(
                        result.fallback_trigger, "hand_contact_not_confirmed"
                    )

    def test_amodal_and_visible_panel_masks_have_safe_untapped_context(self):
        for holes in ([], [(90, 40, 150, 220)]):
            with self.subTest(amodal=not holes):
                result = select(
                    self.photo,
                    [
                        detection("wine bottle", (90, 40, 150, 220)),
                        detection("wine label", (40, 10, 200, 235), holes=holes),
                    ],
                )
                self.assertEqual(result.selection_mode, "fallback")
                self.assertEqual(result.crop_scope, "context_frame")
                with Image.open(BytesIO(result.crop)) as crop:
                    np.testing.assert_array_equal(crop, self.photo)
                # A filled mask cannot distinguish a real bottle from artwork.
                # Record the ambiguity instead of crediting a correct physical ID.
                self.assertEqual(result.selected_id, "d1" if not holes else "d0")

    def test_positive_strong_grip_cannot_be_stolen_by_weak_incidental_wrap(self):
        spec = next(s for s in REVIEW_SCENARIOS if s["id"] == "weak-wrap-strong-grip")
        photo, items, _ = materialize(spec)
        mask = Image.new("L", SIZE)
        draw = ImageDraw.Draw(mask)
        draw.rectangle((70, 80, 99, 189), fill=255)
        draw.rectangle((100, 100, 154, 101), fill=255)
        items[-1] = dict(
            items[-1],
            box=[70, 80, 155, 190],
            mask_png_b64=base64.b64encode(png(mask)).decode(),
        )
        result = select(photo, items)
        self.assertEqual(
            (result.selected_id, result.reason), ("d0", "unique_visible_hand_contact")
        )

    def test_omitted_secondary_label_inside_mask_hole_keeps_original_pixels(self):
        bottle = detection("wine bottle", (70, 10, 170, 235), holes=[(95, 30, 145, 60)])
        result = select(self.photo, [bottle, self.label])
        self.assertEqual(result.keep_mask.getpixel((120, 45)), 255)
        with Image.open(BytesIO(result.crop)) as crop:
            self.assertEqual(
                crop.getpixel((120 - result.crop_box[0], 45 - result.crop_box[1])),
                self.photo.getpixel((120, 45)),
            )

    def test_subject_rectangle_preserves_exterior_connected_label_pixels(self):
        bottle = detection(
            "wine bottle",
            (70, 10, 170, 235),
            holes=[(70, 30, 100, 60), (120, 30, 145, 60)],
        )
        result = select(self.photo, [bottle, self.label])
        self.assertEqual(result.keep_mask.getpixel((80, 45)), 255)
        self.assertEqual(result.keep_mask.getpixel((130, 45)), 255)
        self.assertEqual(result.keep_mask.getpixel((50, 45)), 0)

    def test_shrunken_or_shifted_label_boxes_do_not_erase_enclosed_paper(self):
        bottle = detection(
            "wine bottle", (70, 10, 170, 235), holes=[(75, 100, 165, 200)]
        )
        neck = detection("wine label", (90, 30, 150, 55))
        for predicted_box in ((95, 120, 145, 180), (85, 80, 165, 180)):
            with self.subTest(predicted_box=predicted_box):
                result = select(
                    self.photo, [bottle, neck, detection("wine label", predicted_box)]
                )
                self.assertEqual(result.selected_id, "d0")
                self.assertEqual(result.keep_mask.getpixel((76, 101)), 255)
                self.assertEqual(result.keep_mask.getpixel((164, 199)), 255)

    def test_label_context_is_explicit_and_preserved_with_competing_package(self):
        result = select(
            self.photo,
            [
                detection("wine label", (60, 40, 180, 200)),
                detection("packet", (190, 100, 235, 160)),
            ],
        )
        self.assertEqual(result.selected_id, "d0")
        self.assertEqual(result.crop_scope, "context_frame")
        self.assertEqual(result.as_dict(media=False)["crop_scope"], "context_frame")
        self.assertEqual(result.crop_box, (0, 0, *SIZE))
        with Image.open(BytesIO(result.crop)) as crop:
            np.testing.assert_array_equal(crop, self.photo)

    def test_size_gate_cannot_turn_two_contacts_into_a_unique_held_carton(self):
        instances = [
            detection("wine bottle", (15, 20, 45, 220)),
            detection("wine bottle", (150, 80, 180, 140)),
            detection("box", (90, 70, 140, 140)),
            detection("hand", (140, 90, 150, 130)),
        ]
        result = select(self.photo, instances)
        # Background contact is ambiguous; it cannot establish a unique held
        # carton or suppress independent foreground evidence on another bottle.
        self.assertEqual(
            (result.selected_id, result.reason),
            ("d0", "foreground_scale_and_lower_base"),
        )

    def test_offcenter_large_subject_beats_small_center_background(self):
        result = select(
            self.photo,
            [
                detection("wine bottle", (0, 0, 90, 240)),
                detection("wine bottle", (130, 80, 165, 175)),
            ],
        )
        self.assertEqual(result.selected_id, "d0")
        self.assertEqual(result.selection_mode, "confident")

    def test_confidence_does_not_invent_main_subject(self):
        result = select(
            self.photo,
            [
                detection("wine bottle", (15, 20, 85, 230), score=0.99),
                detection("wine bottle", (155, 20, 225, 230), score=0.41),
            ],
        )
        self.assertEqual(result.selection_mode, "fallback")

    def test_low_confidence_and_hands_only_are_no_target(self):
        for instances in (
            [],
            [detection("hand", (10, 10, 230, 230))],
            [dict(self.bottle, score=0.39)],
        ):
            result = select(self.photo, instances)
            self.assertEqual(result.status, "no_target")
            self.assertEqual(result.selection_mode, "fallback")
            self.assertEqual(result.reason, "fallback_original_frame")
            self.assertIsNone(result.selected_id)
            self.assertEqual(result.crop_box, (0, 0, *SIZE))
            self.assertTrue(np.all(np.asarray(result.keep_mask) == 255))
            with Image.open(BytesIO(result.crop)) as crop:
                np.testing.assert_array_equal(crop, self.photo)

    def test_all_declared_fallback_edge_cases(self):
        for spec in SCENARIOS:
            with self.subTest(case=spec["id"]):
                image, instances, _ = materialize(spec)
                result = select(image, instances, **spec.get("interaction", {}))
                winner = spec["winner"]
                self.assertEqual(
                    result.selected_id, None if winner is None else f"d{winner}"
                )
                self.assertEqual(result.reason, spec["reason"])
                self.assertEqual(result.selection_mode, "fallback")
                self.assertTrue(result.crop)
                self.assertIsNotNone(result.keep_mask)
                self.assertEqual(
                    result.as_dict(media=False)["selection_mode"], "fallback"
                )

    def test_all_review_regression_fixtures(self):
        for spec in REVIEW_SCENARIOS:
            with self.subTest(case=spec["id"]):
                image, instances, _ = materialize(spec)
                result = select(image, instances, **spec.get("interaction", {}))
                self.assertEqual(result.selected_id, f"d{spec['winner']}")
                self.assertEqual(result.reason, spec["reason"])
                self.assertEqual(result.selection_mode, spec.get("mode", "confident"))
                if spec.get("scope"):
                    self.assertEqual(result.crop_scope, spec["scope"])
                if spec.get("tap_ids"):
                    self.assertEqual(
                        set(result.tap_candidate_ids), set(spec["tap_ids"])
                    )
                with Image.open(BytesIO(result.crop)) as crop:
                    for x, y in spec.get("preserve_points", []):
                        self.assertEqual(
                            crop.getpixel(
                                (x - result.crop_box[0], y - result.crop_box[1])
                            ),
                            image.getpixel((x, y)),
                        )

    def test_center_means_visible_mask_not_its_bounding_box(self):
        instances = [
            detection("wine bottle", (80, 20, 160, 220), mask_box=(80, 20, 115, 220)),
            detection("wine bottle", (110, 20, 190, 220), mask_box=(110, 20, 145, 220)),
        ]
        result = select(self.photo, instances)
        self.assertEqual(
            (result.selected_id, result.reason), ("d1", "fallback_center_contains")
        )

    def test_fallback_keeps_complete_associated_labels(self):
        instances = [
            detection("wine bottle", (15, 20, 85, 230)),
            detection("wine bottle", (155, 20, 225, 230)),
            detection("wine label", (20, 100, 80, 180), mask_box=(30, 110, 70, 170)),
        ]
        result = select(self.photo, instances)
        self.assertEqual(result.selection_mode, "fallback")
        self.assertEqual(result.keep_mask.getpixel((21, 101)), 255)
        self.assertEqual(len(result.label_crops), 1)

    def test_stable_id_is_numeric_and_repeatable_with_identical_centers(self):
        instances = [detection("logo", (1, 1, 2, 2)) for _ in range(11)]
        instances[2] = detection(
            "wine bottle", (80, 40, 160, 200), mask_box=(80, 40, 105, 200)
        )
        instances[10] = detection(
            "wine bottle", (80, 40, 160, 200), mask_box=(135, 40, 160, 200)
        )
        for _ in range(2):
            result = select(self.photo, instances)
            self.assertEqual(
                (result.selected_id, result.reason), ("d2", "fallback_stable_id")
            )

    def test_tap_on_overlapping_masks_uses_fallback(self):
        image, instances, _ = materialize(
            next(s for s in SCENARIOS if s["id"] == "overlap")
        )
        result = select(image, instances, tap=(0.5, 0.5))
        self.assertEqual(result.fallback_trigger, "tap_has_no_unique_owner")
        self.assertEqual(result.selected_id, "d1")

    def test_empty_masks_and_outside_boxes_use_full_frame(self):
        empty = detection("wine bottle", (1, 1, 2, 2))
        empty["mask_png_b64"] = base64.b64encode(png(Image.new("L", SIZE))).decode()
        outside = dict(self.bottle, box=[300, 300, 400, 400])
        for item in (empty, outside):
            result = select(self.photo, [item])
            self.assertEqual(result.reason, "fallback_original_frame")
            self.assertTrue(result.crop)

    def test_photo_center_on_odd_image_and_mask_boundary(self):
        image = Image.new("RGB", (241, 239), "gray")
        instances = [
            detection("wine bottle", (80, 20, 120, 220)),
            detection("wine bottle", (120, 20, 160, 220)),
        ]
        # Full masks are resized by the documented decoder to oriented size.
        for item in instances:
            mask = Image.new("L", image.size)
            x, y, X, Y = item["box"]
            ImageDraw.Draw(mask).rectangle((x, y, X - 1, Y - 1), fill=255)
            item["mask_png_b64"] = base64.b64encode(png(mask)).decode()
        result = select(image, instances)
        self.assertEqual(
            (result.selected_id, result.reason), ("d1", "fallback_center_contains")
        )

    def test_full_image_fallback_follows_exif_orientation(self):
        image = Image.new("RGB", (90, 60), "#b99373")
        exif = image.getexif()
        exif[274] = 6
        encoded = BytesIO()
        image.save(encoded, "JPEG", exif=exif)
        result = select_photo(encoded.getvalue(), None, instances=[])
        self.assertEqual((result.width, result.height), (60, 90))
        self.assertEqual(result.crop_box, (0, 0, 60, 90))
        with Image.open(BytesIO(result.crop)) as crop:
            self.assertEqual(crop.size, (60, 90))

    def test_duplicate_instance_does_not_create_ambiguity(self):
        self.assertEqual(
            select(self.photo, [self.bottle, dict(self.bottle)]).status, "selected"
        )

    def test_bottle_picture_inside_carton_is_not_selected_as_physical_bottle(self):
        result = select(self.photo, [detection("box", (40, 10, 200, 230)), self.bottle])
        self.assertEqual(result.selected_id, "d0")
        self.assertEqual(result.rejected[0]["reason"], "embedded_in_packaging")

    def test_invalid_points_are_rejected(self):
        for point in (
            (float("nan"), 0.5),
            (0.5, float("inf")),
            (-0.1, 0.5),
            (True, 0.5),
            (0.5,),
        ):
            with self.subTest(point=point), self.assertRaises(ValueError):
                select(self.photo, [self.bottle], tap=point)

    def test_input_detections_are_not_mutated(self):
        before = json.dumps([self.bottle, self.label], sort_keys=True)
        select(self.photo, [self.bottle, self.label])
        self.assertEqual(before, json.dumps([self.bottle, self.label], sort_keys=True))

    def test_supplied_detections_make_no_network_call(self):
        with mock.patch("matcher.semantic_selector._request_sam3") as request:
            result = select_photo(png(self.photo), None, instances=[self.bottle])
        request.assert_not_called()
        self.assertEqual(result.status, "selected")

    def test_one_shared_request_contains_bottle_label_hand(self):
        answer = dict(
            width=240, height=240, count=2, instances=[self.bottle, self.label]
        )
        opener = FakeOpener(json.dumps(answer).encode())
        result = select_photo(png(self.photo), "http://sam3.test", opener=opener)
        self.assertEqual(result.status, "selected")
        self.assertEqual(len(opener.requests), 1)
        self.assertIn(", ".join(NOUNS).encode(), opener.requests[0][0].data)

    def test_invalid_mask_is_dependency_error(self):
        with self.assertRaises(GroupMatchError):
            select(self.photo, [dict(self.bottle, mask_png_b64="broken")])

    def test_scene_v1_remains_available_and_forces_a_winner(self):
        instances = [
            detection("wine bottle", (15, 20, 85, 230)),
            detection("wine bottle", (155, 20, 225, 230)),
        ]
        result = select_variant(self.photo, instances, variant="scene-v1")
        self.assertEqual((result.variant, result.status), ("scene-v1", "selected"))

    def test_scene_v1_retains_its_original_frame_fallback(self):
        result = select_variant(self.photo, [], variant="scene-v1")
        self.assertEqual(result.status, "no_target")
        self.assertEqual(result.crop_box, (0, 0, *SIZE))
        with Image.open(BytesIO(result.crop)) as crop:
            self.assertEqual(crop.size, SIZE)

