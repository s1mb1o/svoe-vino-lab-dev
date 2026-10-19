"""Paired selector comparison. Controlled masks and live detections stay separate."""

import argparse
import base64
from io import BytesIO
import hashlib
import inspect
import json
from pathlib import Path
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from matcher.group import _normalize_image
from matcher.semantic_selector import NOUNS, select_variant
from matcher.experiments.main_selector.fallback_suite import verify_frozen_inputs
from matcher.experiments.main_selector.metrics import cohort, pixel_metrics


def encoded(mask):
    f = BytesIO()
    mask.save(f, "PNG")
    return base64.b64encode(f.getvalue()).decode()


def controlled(case, out):
    """GT-derived detector fixtures, with named faults; never called model outputs."""
    detections = []
    labels = {"bottle": "wine bottle", "price_tag": "price tag"}
    profile = case["operation"]
    omitted = [
        a
        for a in case["annotations"]
        if a["parent_instance_id"] == 1
        and a["category"].startswith("label_")
        and (
            a["instance_id"] == 29000
            if profile == "ex_missing_secondary_edge"
            else a["category"] == "label_front"
        )
    ]
    for ann in case["annotations"]:
        if ann["category"] not in (
            "bottle",
            "hand",
            "box",
            "packet",
            "can",
            "price_tag",
            "tool",
            "reflection",
            "depiction",
        ) and not ann["category"].startswith("label_"):
            continue
        if profile.startswith("close_") and ann["category"] == "bottle":
            continue
        with Image.open(out / ann["mask"]) as opened:
            mask = opened.convert("L")
        bounds = ann["box"]
        if profile == "ex_missing_secondary_edge" and ann["instance_id"] == 29000:
            continue
        if (
            profile
            in (
                "ex_missing_secondary_edge",
                "ex_missing_main_label_edge",
                "ex_tap_white_label_gap",
            )
            and ann["instance_id"] == 1
        ):
            draw = ImageDraw.Draw(mask)
            for missing in omitted:
                x, y, X, Y = missing["box"]
                draw.rectangle(
                    (
                        x if profile != "ex_missing_main_label_edge" else (x + X) // 2,
                        y,
                        bounds[2] - 1,
                        Y - 1,
                    ),
                    fill=0,
                )
        if profile == "ex_missing_main_label_edge" and ann in omitted:
            x, y, X, Y = bounds
            bounds = [x, y, (x + X) // 2, Y]
            ImageDraw.Draw(mask).rectangle(((x + X) // 2, y, X - 1, Y - 1), fill=0)
        if profile == "holes" and ann["category"].startswith("label_"):
            draw = ImageDraw.Draw(mask)
            x1, y1, x2, y2 = bounds
            draw.rectangle(
                (
                    x1 + (x2 - x1) // 4,
                    y1 + (y2 - y1) // 4,
                    x2 - (x2 - x1) // 4,
                    y2 - (y2 - y1) // 4,
                ),
                fill=0,
            )
        if profile == "eroded_bottle" and ann["instance_id"] == 1:
            mask = mask.filter(ImageFilter.MinFilter(15))
        if profile == "hand_box" and ann["category"] == "hand":
            bounds = [0, bounds[1], case["width"], bounds[3]]
        detections.append(
            dict(
                label="wine label"
                if ann["category"].startswith("label_")
                else "wine bottle"
                if ann["category"] in ("tool", "reflection", "depiction")
                else labels.get(ann["category"], ann["category"]),
                score=0.9,
                box=bounds,
                area=int(np.count_nonzero(np.asarray(mask))),
                mask_png_b64=encoded(mask),
            )
        )
    if profile == "depiction":
        carton = next(a for a in case["annotations"] if a["instance_id"] == 200)
        mask = Image.new("L", (case["width"], case["height"]))
        x1, y1, x2, y2 = carton["box"]
        box = [
            x1 + (x2 - x1) // 3,
            y1 + (y2 - y1) // 6,
            x2 - (x2 - x1) // 3,
            y2 - (y2 - y1) // 6,
        ]
        ImageDraw.Draw(mask).rectangle(
            (box[0], box[1], box[2] - 1, box[3] - 1), fill=255
        )
        detections.append(
            dict(
                label="wine bottle",
                score=0.99,
                box=box,
                area=int(np.count_nonzero(np.asarray(mask))),
                mask_png_b64=encoded(mask),
            )
        )
    if profile in ("ex_vintage_label_price_card", "ex_promotional_bridge"):
        # Explicit detector-confusion control, separate from native GT masks.
        detections.extend(
            dict(item, label="wine label")
            for item in list(detections)
            if item["label"] == "price tag"
        )
    return detections


def controlled_case(case, out):
    """Keep legacy fixture bytes stable and apply explicitly versioned new faults."""
    detections = controlled(case, out)
    if case.get("v2_fault") == "amodal_panel":
        panel = next(a for a in case["annotations"] if a["instance_id"] == 500)
        mask = Image.new("L", (case["width"], case["height"]))
        x, y, X, Y = panel["box"]
        ImageDraw.Draw(mask).rectangle((x, y, X - 1, Y - 1), fill=255)
        detections.append(dict(label="wine label", score=0.95, box=panel["box"],
                               area=(X - x) * (Y - y), mask_png_b64=encoded(mask)))
    return detections


def selected_gt(case, detections, decision, out):
    if decision.selected_id is None:
        return None, 0.0
    if case["provenance"] == "geometry_fixture":
        # Fixture IDs are declared inputs; do not use mask-IoU assignment for
        # intentionally identical-box/nonexclusive edge cases.
        return int(decision.selected_id[1:]) + 1, 1.0
    index = int(decision.selected_id[1:])
    item = detections[index]
    with Image.open(BytesIO(base64.b64decode(item["mask_png_b64"]))) as opened:
        predicted = np.asarray(opened.convert("L")) >= 128
    # Detector classes are predictions, not GT. A whole carton can be called a
    # label, and a drawing can be called a bottle. Match the selected region to
    # physical/identity GT masks by IoU for BOTH variants. Label/print matches
    # resolve to their annotated parent. Keep this assignment correction separate
    # from selector improvements in before/after reporting.
    candidates = case["annotations"]
    scores = []
    for ann in candidates:
        with Image.open(out / ann["mask"]) as opened:
            truth = np.asarray(opened) > 0
        intersection = np.logical_and(predicted, truth).sum()
        union = np.logical_or(predicted, truth).sum()
        scores.append((float(intersection / max(1, union)), ann))
    if not scores:
        return None, 0.0
    score, ann = max(scores, key=lambda pair: pair[0])
    if score < 0.30:
        return None, score
    return ann.get("parent_instance_id") or ann["instance_id"], score


def assess(case, detections, decision, out, image=None):
    target, iou = selected_gt(case, detections, decision, out)
    correct = decision.status == case["expected_status"]
    if case["expected_status"] == "selected":
        correct = correct and target == case["target_instance_id"]
    if case["expected_status"] == "no_target":
        correct = correct and decision.crop_box == (0, 0, case["width"], case["height"])
    correct = correct and bool(decision.crop)
    if case["provenance"] == "geometry_fixture" and decision.variant == "semantic-v2":
        correct = (
            correct
            and decision.selection_mode == case["expected_selection_mode"]
            and decision.reason == case["expected_reason"]
        )
        if case.get("expected_crop_scope"):
            correct = correct and decision.crop_scope == case["expected_crop_scope"]
        if case.get("expected_tap_candidate_ids") is not None:
            correct = correct and set(decision.tap_candidate_ids) == set(
                case["expected_tap_candidate_ids"]
            )
        if case.get("preserve_points") and decision.crop:
            with Image.open(BytesIO(decision.crop)) as crop:
                for x, y in case["preserve_points"]:
                    correct = (
                        correct
                        and decision.keep_mask.getpixel((x, y)) == 255
                        and crop.getpixel(
                            (x - decision.crop_box[0], y - decision.crop_box[1])
                        )
                        == image.getpixel((x, y))
                    )
    group = cohort(case)
    pixels = pixel_metrics(case, decision, out, image)
    if group == "rule_conformance" and decision.variant == "scene-v1":
        for key in (
            "crop_target_coverage",
            "crop_distractor_retention",
            "label_retention",
            "raw_label_retention",
            "foreign_label_retention",
            "representation_retention",
            "price_tag_retention",
        ):
            pixels[key] = None
    return dict(
        correct=bool(correct),
        metric_cohort=group,
        intent_target_correct=bool(correct)
        if group in ("passive_intent", "interaction")
        else None,
        policy_target_match=bool(correct) if group == "policy_targets" else None,
        policy_fallback_pass=(bool(correct) and decision.selection_mode == "fallback")
        if group == "policy_targets" and decision.variant == "semantic-v2"
        else None,
        no_target_correct=bool(correct) if group == "no_target" else None,
        conformance_pass=bool(correct)
        if group == "rule_conformance" and decision.variant == "semantic-v2"
        else None,
        matched_instance_id=target,
        expected_mode_match=(decision.selection_mode == case["expected_selection_mode"])
        if case.get("expected_selection_mode") and decision.variant == "semantic-v2"
        else None,
        assignment_mask_iou=round(iou, 6),
        **pixels,
        wrong_subject=decision.status == "selected"
        and (
            case["expected_status"] != "selected"
            or target != case["target_instance_id"]
        ),
    )


def run(out, endpoint, modes, partial=False, reuse_cases=False):
    # Replay is read-only with respect to annotations, masks and detector inputs.
    # Preparation is always an explicit separate command, including by default.
    cases = json.loads((out / "cases.json").read_text())
    if not (out / "prediction-inputs.json").is_file():
        raise RuntimeError(
            "Prepare exact prediction inputs with collect_predictions.py before replay"
        )
    frozen_sha = verify_frozen_inputs(out)
    prediction_sha = hashlib.sha256(
        (out / "prediction-inputs.json").read_bytes()
    ).hexdigest()
    recovery_path = out / "detector-recovery.json"
    recovery_inputs = {}
    if recovery_path.exists():
        frozen_predictions = json.loads((out / "prediction-inputs.json").read_text())
        if not frozen_predictions.get("recovery_inputs_sha256"):
            raise RuntimeError("Detector recovery inputs must be frozen before replay")
        recovery_inputs = json.loads(recovery_path.read_text())["cases"]
    enhancement_path = out / "detector-enhancement.json"
    enhancement_inputs = json.loads(enhancement_path.read_text())["cases"] if enhancement_path.exists() else {}
    selector_root = Path(__file__).resolve().parents[2]
    source_hashes = {
        name: hashlib.sha256((selector_root / name).read_bytes()).hexdigest()
        for name in ("semantic_selector.py", "main_scene.py", "selector_detection.py")
    }
    if not partial and len(
        [c for c in cases if c["provenance"] == "new_native_render"]
    ) != len(json.loads((out / "protocol.json").read_text())["cases"]):
        raise RuntimeError(
            "All declared native cases must finish before final evaluation"
        )
    (out / "predictions").mkdir(exist_ok=True)
    (out / "results").mkdir(exist_ok=True)
    (out / "crops").mkdir(exist_ok=True)
    results = []
    for case in cases:
        body = (out / case["image"]).read_bytes()
        image, jpeg = _normalize_image(body)
        if image.size != (case["width"], case["height"]):
            raise RuntimeError("Suite photos must fit the selector coordinate limit")
        for mode in modes:
            if (mode == "fallback") != (case["provenance"] == "geometry_fixture"):
                continue
            if mode == "controlled" and case["provenance"] != "new_native_render":
                continue
            cache = out / "predictions" / (case["id"] + "-" + mode + ".json")
            signature = prediction_signature(case, body, mode)
            response = json.loads(cache.read_text()) if cache.exists() else None
            if response and response["signature"] != signature:
                raise RuntimeError(
                    "Prediction input changed; use collect_predictions.py explicitly: "
                    + case["id"]
                )
            if mode == "fallback":
                response = dict(
                    instances=case["fixture_detections"],
                    detection_ms=0,
                    source="declared geometry fixture, not model predictions",
                )
            if response is None:
                raise RuntimeError(
                    "Missing frozen prediction; run collect_predictions.py before replay: "
                    + case["id"]
                )
            recovery = recovery_inputs.get(case["id"]) if mode == "live" else None
            instances = response["instances"]
            if recovery is not None:
                if (recovery["image_sha256"] != case["image_sha256"]
                        or recovery["primary_prediction_sha256"] != hashlib.sha256(cache.read_bytes()).hexdigest()):
                    raise RuntimeError("Recovery inputs do not match the primary image/cache")
                instances = [*instances, *recovery["instances"]]
            enhancement = enhancement_inputs.get(case["id"]) if mode == "live" else None
            if enhancement is not None:
                if (enhancement["image_sha256"] != case["image_sha256"]
                        or enhancement["primary_prediction_sha256"] != hashlib.sha256(cache.read_bytes()).hexdigest()):
                    raise RuntimeError("Enhancement inputs do not match the primary image/cache")
                instances = enhancement["instances"]
            for variant in ("scene-v1", "semantic-v2"):
                start = time.perf_counter()
                interaction = case["interaction"] if variant == "semantic-v2" else {}
                decision = select_variant(
                    image, instances, variant=variant, **interaction
                )
                if recovery is not None:
                    decision.detection_recovery = ("generic_bottle_found" if recovery["instances"]
                                                   else "generic_bottle_empty")
                if enhancement is not None:
                    decision.detection_refinement = enhancement["audit"]
                elapsed = (time.perf_counter() - start) * 1000
                data = dict(
                    case_id=case["id"],
                    group=case["group"],
                    mode=mode,
                    selector_ms=elapsed,
                    shared_detection_ms=response["detection_ms"],
                    interaction_case=bool(case["interaction"]),
                    selector_source_sha256=source_hashes,
                    comparison_inputs_sha256=frozen_sha,
                    prediction_inputs_sha256=prediction_sha,
                    **decision.as_dict(media=False),
                    **assess(case, instances, decision, out, image),
                )
                if decision.crop:
                    path = Path("crops") / (
                        case["id"] + "-" + mode + "-" + variant + ".png"
                    )
                    (out / path).write_bytes(decision.crop)
                    data["crop_path"] = str(path)
                if decision.keep_mask:
                    path = Path("crops") / (
                        case["id"] + "-" + mode + "-" + variant + "-keep.png"
                    )
                    decision.keep_mask.save(out / path)
                    data["keep_mask_path"] = str(path)
                data["label_crop_paths"] = []
                for index, crop in enumerate(decision.label_crops):
                    path = Path("crops") / (
                        case["id"] + "-" + mode + "-" + variant + f"-label-{index}.png"
                    )
                    (out / path).write_bytes(crop)
                    data["label_crop_paths"].append(str(path))
                (
                    out
                    / "results"
                    / (case["id"] + "-" + mode + "-" + variant + ".json")
                ).write_text(json.dumps(data, indent=2) + "\n")
                results.append(data)
            print("EVALUATED", case["id"], mode, flush=True)
    (out / "comparison.json").write_text(json.dumps(results, indent=2) + "\n")
    if verify_frozen_inputs(out) != frozen_sha:
        raise RuntimeError("Comparison inputs changed during replay")
    if (
        hashlib.sha256((out / "prediction-inputs.json").read_bytes()).hexdigest()
        != prediction_sha
    ):
        raise RuntimeError("Prediction freeze changed during replay")
    return cases, results


def prediction_signature(case, body, mode):
    signature = hashlib.sha256(body + (", ".join(NOUNS) + mode).encode()).hexdigest()
    if mode == "controlled":
        fixture_inputs = dict(
            operation=case["operation"],
            masks=[
                {k: a[k] for k in ("category", "box", "sha256")}
                for a in case["annotations"]
            ],
            implementation=inspect.getsource(controlled),
        )
        if case.get("v2_fault"):
            fixture_inputs.update(v2_fault=case["v2_fault"],
                                  fault_implementation=inspect.getsource(controlled_case))
        signature = hashlib.sha256(
            (signature + json.dumps(fixture_inputs, sort_keys=True)).encode()
        ).hexdigest()
    return signature


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("output", type=Path)
    ap.add_argument(
        "--endpoint",
        help="Deprecated compatibility option; replay never requests detections. Use collect_predictions.py --endpoint.",
    )
    ap.add_argument(
        "--mode", choices=("controlled", "live", "fallback", "all"), default="all"
    )
    ap.add_argument("--partial", action="store_true")
    ap.add_argument(
        "--reuse-cases",
        action="store_true",
        help="Replay the already exported, validated cases without rebuilding masks/overlays",
    )
    args = ap.parse_args()
    run(
        args.output.resolve(),
        args.endpoint,
        ["controlled", "live", "fallback"] if args.mode == "all" else [args.mode],
        args.partial,
        args.reuse_cases,
    )
