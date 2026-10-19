"""Version the revised crop contract without rewriting the original photo intent."""

import argparse
import json
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from matcher.experiments.main_selector.export_suite import box, rle, sha
from matcher.experiments.main_selector.fallback_cases import (
    SCENARIOS,
    REVIEW_SCENARIOS,
    materialize,
)


REVISION = "2026-10-19-positive-grip-and-panel"


def policy_target(case, out):
    """Derive a conformance target from GT geometry, never from model outputs."""
    choices = []
    for ann in case["annotations"]:
        if ann["instance_id"] not in case["acceptable_instance_ids"]:
            continue
        with Image.open(out / ann["mask"]) as mask:
            contains = bool(mask.getpixel((case["width"] // 2, case["height"] // 2)))
        x, y, X, Y = ann["box"]
        key = (
            not contains,
            (x + X - case["width"]) ** 2 + (y + Y - case["height"]) ** 2,
            x + X,
            y + Y,
            ann["instance_id"],
        )
        choices.append((key, ann["instance_id"]))
    return min(choices)[1]


def policy_geometry(case, out):
    """Explain the existing GT policy target and its margin, without predictions."""
    rows = []
    for ann in case["annotations"]:
        if ann["instance_id"] not in case["acceptable_instance_ids"]:
            continue
        with Image.open(out / ann["mask"]) as mask:
            contains = bool(mask.getpixel((case["width"] // 2, case["height"] // 2)))
        x, y, X, Y = ann["box"]
        rows.append(
            dict(
                id=ann["instance_id"],
                contains=contains,
                distance2=(x + X - case["width"]) ** 2 + (y + Y - case["height"]) ** 2,
                x=x + X,
                y=y + Y,
            )
        )
    centers = [r for r in rows if r["contains"]]
    pool = centers or rows
    ranked = sorted(pool, key=lambda r: (r["distance2"], r["x"], r["y"], r["id"]))
    reason = "fallback_center_contains" if centers else "fallback_nearest_center"
    narrowed = pool
    for key, tag in (
        ("distance2", "fallback_nearest_center"),
        ("x", "fallback_leftmost"),
        ("y", "fallback_uppermost"),
        ("id", "fallback_stable_id"),
    ):
        if len(narrowed) == 1:
            break
        minimum = min(r[key] for r in narrowed)
        following = [r for r in narrowed if r[key] == minimum]
        if len(following) < len(narrowed):
            reason = tag
        narrowed = following
    return dict(
        winner_instance_id=ranked[0]["id"],
        reason=reason,
        center_contains_ids=[r["id"] for r in centers],
        candidate_count=len(rows),
        distance_px=math.sqrt(ranked[0]["distance2"]) / 2,
        runner_distance_margin_px=(
            math.sqrt(ranked[1]["distance2"]) - math.sqrt(ranked[0]["distance2"])
        )
        / 2
        if len(ranked) > 1
        else None,
        exact_distance_tie=len(ranked) > 1
        and ranked[0]["distance2"] == ranked[1]["distance2"],
        source="unchanged visible GT geometry; diagnostic, not a new intent annotation",
    )


def verify_frozen_inputs(out, *, predictions=True):
    frozen = json.loads((out / "comparison-inputs.json").read_text())
    for name, expected in frozen["files_sha256"].items():
        if sha(out / name) != expected:
            raise RuntimeError("Frozen input changed: " + name)
    for case in json.loads((out / "cases.json").read_text()):
        for name, expected in [
            (case["image"], case["image_sha256"]),
            *[(a["mask"], a["sha256"]) for a in case["annotations"]],
        ]:
            if sha(out / name) != expected:
                raise RuntimeError("Frozen image/mask changed: " + name)
    manifest = out / "prediction-inputs.json"
    if predictions and manifest.exists():
        prediction_freeze = json.loads(manifest.read_text())
        frozen_predictions = prediction_freeze["files_sha256"]
        recovery_path = out / "detector-recovery.json"
        recovery_hash = sha(recovery_path) if recovery_path.exists() else None
        if recovery_hash != prediction_freeze.get("recovery_inputs_sha256"):
            raise RuntimeError("Detector recovery inputs changed or were not frozen")
        enhancement_path = out / "detector-enhancement.json"
        enhancement_hash = sha(enhancement_path) if enhancement_path.exists() else None
        if enhancement_hash != prediction_freeze.get("enhancement_inputs_sha256"):
            raise RuntimeError("Detector enhancement inputs changed or were not frozen")
        if json.loads(manifest.read_text())["annotation_inputs_sha256"] != sha(
            out / "comparison-inputs.json"
        ):
            raise RuntimeError(
                "Prediction freeze belongs to different annotation inputs"
            )
        actual = {
            str(p.relative_to(out)): sha(p)
            for p in sorted((out / "predictions").glob("*.json"))
        }
        if actual != frozen_predictions:
            raise RuntimeError(
                "Frozen prediction caches changed; explicitly collect/freeze new inputs before replay"
            )
    return sha(out / "comparison-inputs.json")


def overlay(out, case):
    layers = {
        name: Image.new("RGBA", (case["width"], case["height"]))
        for name in ("bottles", "labels", "hands", "target")
    }
    for ann in case["annotations"]:
        with Image.open(out / ann["mask"]) as opened:
            mask = opened.convert("L")
        layer = (
            "labels"
            if ann["category"].startswith("label_")
            else "hands"
            if ann["category"] == "hand"
            else "bottles"
        )
        layers[layer].paste(
            {
                "labels": (237, 170, 40, 130),
                "hands": (234, 99, 50, 120),
                "bottles": (58, 133, 196, 100),
            }[layer],
            (0, 0),
            mask,
        )
        if ann["instance_id"] == case["target_instance_id"]:
            edge = np.asarray(mask.filter(ImageFilter.MaxFilter(7))) > np.asarray(mask)
            layers["target"].paste(
                (70, 255, 160, 255), (0, 0), Image.fromarray(edge.astype("uint8") * 255)
            )
    # Only replace target boundaries for existing photos; retain their other layers.
    names = layers if case["provenance"] == "geometry_fixture" else ("target",)
    for name in names:
        layers[name].save(out / "overlays" / (case["id"] + "-" + name + ".png"))


def attach(out, cases):
    cases = [c for c in cases if c["provenance"] != "geometry_fixture"]
    targets = {}
    geometry = {}
    for case in cases:
        if (
            case.get("intent_status") != "ambiguous"
            and case["expected_status"] != "ambiguous"
        ):
            continue
        targets[case["id"]] = policy_target(case, out)
        geometry[case["id"]] = policy_geometry(case, out)
        case.setdefault("intent_status", "ambiguous")
        case["expected_status"] = "selected"
        case["target_instance_id"] = targets[case["id"]]
        case["target_kind"] = "policy_fallback"
        case["expected_selection_mode"] = "fallback"
        case["target_explanation"] = (
            "No unique intended bottle. The annotated crop target follows the revised "
            "photo-center / pixel-distance / left / upper policy; this is a product "
            "fallback, not evidence of user intent."
        )
        overlay(out, case)
    for spec in SCENARIOS + REVIEW_SCENARIOS:
        image, detections, masks = materialize(spec)
        case_id = "fb-" + spec["id"]
        image_path = "images/" + case_id + ".png"
        image.save(out / image_path)
        annotations = []
        for index, mask in enumerate(masks):
            path = "masks/%s-i%d.png" % (case_id, index + 1)
            mask.save(out / path)
            array = np.asarray(mask) > 0
            annotations.append(
                dict(
                    instance_id=index + 1,
                    category={"wine bottle": "bottle", "wine label": "label_front"}.get(
                        spec["items"][index]["label"], spec["items"][index]["label"]
                    ),
                    parent_instance_id=None,
                    mask=path,
                    box=box(array),
                    area=int(array.sum()),
                    segmentation=rle(array),
                    sha256=sha(out / path),
                )
            )
        winner = spec["winner"]
        case = dict(
            id=case_id,
            name=spec["title"],
            group="fallback" if spec in SCENARIOS else "review",
            operation=spec["id"],
            provenance="geometry_fixture",
            width=image.width,
            height=image.height,
            image=image_path,
            image_sha256=sha(out / image_path),
            annotations=annotations,
            interaction=spec.get("interaction", {}),
            expected_status="no_target" if winner is None else "selected",
            target_instance_id=None if winner is None else winner + 1,
            acceptable_instance_ids=[] if winner is None else [winner + 1],
            expected_detection_id=None if winner is None else "d%d" % winner,
            expected_reason=spec["reason"],
            expected_selection_mode=spec.get(
                "mode", "fallback" if spec in SCENARIOS else "confident"
            ),
            expected_crop_scope=spec.get("scope"),
            expected_tap_candidate_ids=spec.get("tap_ids"),
            preserve_points=spec.get("preserve_points", []),
            label_ground_truth=False,
            fixture_detections=detections,
            annotation_source="declared geometry fixture",
            previous_contact_expectation=spec.get("previous_contact_expectation"),
            confidence_contract_revision=spec.get("confidence_contract_revision"),
            target_explanation="Diagnostic geometry fixture, not a photograph or model output. "
            "The gold crosshair marks the photo center; no aim is supplied unless declared.",
        )
        cases.append(case)
        overlay(out, case)
    (out / "cases.json").write_text(json.dumps(cases, indent=2) + "\n")
    protocol = json.loads((out / "protocol.json").read_text())
    protocol["selection_policy_revision"] = REVISION
    protocol.pop("fallback_targets_assigned_before_revised_predictions", None)
    protocol["fallback_targets"] = targets
    protocol["primary_metrics"] = [
        "passive_intent_decision_accuracy",
        "interaction_capability",
        "policy_target_match",
        "no_target_decision",
        "rule_conformance",
        "crop_return_rate",
        "actual_pixel_target_coverage",
        "actual_pixel_label_retention",
        "distractor_retention",
    ]
    for group in protocol["groups"]:
        if group["id"] == "ambiguity":
            group["description"] = (
                "Two or three equal bottles, two equally held bottles, and a wide shelf row. "
                "Intent remains ambiguous, but the selector must return a crop using the "
                "photo-center / nearest / left / upper / stable-ID fallback."
            )
    protocol["fallback_fixtures"] = [
        dict(id="fb-" + s["id"], reason=s["reason"], winner=s["winner"])
        for s in SCENARIOS + REVIEW_SCENARIOS
    ]
    (out / "protocol.json").write_text(json.dumps(protocol, indent=2) + "\n")
    policy = dict(
        revision=REVISION,
        source="original visible GT masks/boxes, not detector outputs",
        interpretation="product-policy conformance; never user-intent accuracy",
        targets=targets,
    )
    (out / "policy-targets.json").write_text(json.dumps(policy, indent=2) + "\n")
    (out / "policy-geometry.json").write_text(json.dumps(geometry, indent=2) + "\n")
    frozen = dict(
        schema_version=1,
        revision=REVISION,
        files_sha256={
            name: sha(out / name)
            for name in (
                "cases.json",
                "protocol.json",
                "policy-targets.json",
                "policy-geometry.json",
                "confidence-contract-declaration.json",
                "confidence-regression-declaration.json",
                "v2-declaration.json",
                "real-v2-declaration.json",
            )
            if (out / name).exists()
        },
    )
    (out / "comparison-inputs.json").write_text(json.dumps(frozen, indent=2) + "\n")
    verify_frozen_inputs(out, predictions=False)
    return cases


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Explicitly prepare and freeze comparison inputs before replay"
    )
    parser.add_argument("output", type=Path)
    out = parser.parse_args().output.resolve()
    prepared = attach(out, json.loads((out / "cases.json").read_text()))
    print(
        "Prepared",
        len(prepared),
        "cases; annotation inputs",
        verify_frozen_inputs(out, predictions=False),
    )
