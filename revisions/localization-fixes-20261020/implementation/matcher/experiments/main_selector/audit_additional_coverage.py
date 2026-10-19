"""Audit added inputs and distinguish selected-subject labels from target labels."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from matcher.experiments.main_selector.metrics import pixel_metrics


def audit(out):
    cases = {c["id"]: c for c in json.loads((out / "cases.json").read_text())}
    results = json.loads((out / "comparison.json").read_text())
    rows = []
    for row in results:
        case = cases[row["case_id"]]
        if row["variant"] != "semantic-v2" or case["provenance"] == "geometry_fixture":
            continue
        selected = row["matched_instance_id"]
        selected_labels = None
        if selected is not None and case.get("label_ground_truth"):
            with Image.open(out / row["keep_mask_path"]) as opened:
                mask = opened.convert("L")
            decision = SimpleNamespace(crop=(out / row["crop_path"]).read_bytes(),
                                       keep_mask=mask, crop_box=row["crop_box"])
            # A temporary target override measures the assigned subject's own labels.
            # It never changes the frozen annotations or expected-target metrics.
            selected_labels = pixel_metrics(dict(case, target_instance_id=selected), decision, out)["label_retention"]
        rows.append(dict(
            case_id=case["id"], group=case["group"], mode=row["mode"],
            addition_kind=case.get("addition_kind", "v1_inherited"), selected_gt_id=selected,
            expected_gt_id=case["target_instance_id"], cohort=row["metric_cohort"],
            selected_label_retention=selected_labels, expected_label_retention=row["label_retention"],
            decision_match=row["correct"], expected_mode_match=row["expected_mode_match"],
            selection_mode=row["selection_mode"], reason=row["reason"],
        ))
    trials = [r for r in rows if r["selected_label_retention"] is not None]
    additions = [c for c in cases.values() if c.get("addition_kind")]
    new = [r for r in rows if r["addition_kind"] != "v1_inherited"]
    issues = [r for r in new if r["decision_match"] is False or r["expected_mode_match"] is False
              or (r["expected_label_retention"] is not None and r["expected_label_retention"] < .98)]
    result = dict(
        interpretation="Frozen annotation and detector inputs; results belong to the selector SHA recorded below. Targets were fixed before predictions. Expected-target labels and assigned selected-subject labels are distinct metrics. An IoU assignment can be imperfect, especially for incomplete COCO polygons.",
        selector_sha256=hashlib.sha256((Path(__file__).resolve().parents[2] / "semantic_selector.py").read_bytes()).hexdigest(),
        auditor_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        comparison_inputs_sha256=hashlib.sha256((out / "comparison-inputs.json").read_bytes()).hexdigest(),
        prediction_inputs_sha256=hashlib.sha256((out / "prediction-inputs.json").read_bytes()).hexdigest(),
        photo_cases=sum(c["provenance"] != "geometry_fixture" for c in cases.values()),
        added_images=len(additions),
        added_native_views=sum(c.get("addition_kind") == "existing_scenario_variant" for c in additions),
        added_native_scenarios=sum(c.get("addition_kind") == "new_scenario" for c in additions),
        added_real_photos=sum(c.get("addition_kind") == "additional_real_photo" for c in additions),
        all_semantic_rows_with_crop=sum(bool(r["crop_path"]) for r in results if r["variant"] == "semantic-v2"),
        semantic_rows=sum(r["variant"] == "semantic-v2" for r in results),
        assigned_selected_label_trials=len(trials),
        assigned_selected_labels_ge98=sum(r["selected_label_retention"] >= .98 for r in trials),
        assigned_selected_label_failures=[r for r in trials if r["selected_label_retention"] < .98],
        new_issue_case_mode_rows=len(issues),
        new_issue_unique_cases=len({r["case_id"] for r in issues}),
        new_issues=issues, rows=rows,
    )
    (out / "additional-findings.json").write_text(json.dumps(result, indent=2) + "\n")
    return {k: v for k, v in result.items() if k not in ("rows", "new_issues")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    print(json.dumps(audit(parser.parse_args().output.resolve()), indent=2))
