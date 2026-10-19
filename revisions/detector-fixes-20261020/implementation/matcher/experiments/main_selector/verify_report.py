"""Check offline report data, assets and JS syntax without browser automation."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


def verify_coverage_filters(out, data, script):
    """Cross-check the actual HTML aggregation for every group/source/mode scope."""
    from matcher.experiments.main_selector.report import DECISION_FIELD, summary

    start = script.index("function aggregate(rows){")
    function = script[start:script.index("function render(){", start)]
    cases = {c["id"]: c for c in data["cases"]}
    groups = ["all"] + [g["id"] for g in data["groups"]]
    kinds = ["all", "v1_inherited", "existing_scenario_variant", "new_scenario", "additional_real_photo"]
    scopes = [dict(mode=mode, group=group, kind=kind)
              for mode in ("live", "controlled", "fallback") for group in groups for kind in kinds]
    minimal = {ident: dict(group=c["group"], kind=c.get("addition_kind", "v1_inherited"))
               for ident, c in cases.items()}
    code = "const cohortNames=" + json.dumps(dict.fromkeys(DECISION_FIELD)) + ";\n"
    code += "const metricFields=" + json.dumps(DECISION_FIELD) + ";\n"
    code += "function decisionMetric(r){return r[metricFields[r.metric_cohort]]}\n" + function
    code += "const cases=" + json.dumps(minimal) + ";\nconst rows=" + json.dumps(data["results"]) + ";\n"
    code += "const scopes=" + json.dumps(scopes) + ";\n"
    code += "process.stdout.write(JSON.stringify(scopes.map(s=>aggregate(rows.filter(r=>r.mode===s.mode&&(s.group==='all'||cases[r.case_id].group===s.group)&&(s.kind==='all'||cases[r.case_id].kind===s.kind))))));"
    actual = json.loads(subprocess.check_output(["node"], input=code, text=True))
    for scope, totals in zip(scopes, actual):
        scoped = [r for r in data["results"] if r["mode"] == scope["mode"]
                  and (scope["group"] == "all" or cases[r["case_id"]]["group"] == scope["group"])
                  and (scope["kind"] == "all" or cases[r["case_id"]].get("addition_kind", "v1_inherited") == scope["kind"])]
        for cohort, variants in totals.items():
            for variant, values in variants.items():
                expected = summary([r for r in scoped if r["metric_cohort"] == cohort
                                    and r["variant"] == variant], cohort)
                for key, value in values.items():
                    matches = (isinstance(value, float) and isinstance(expected[key], (int, float))
                               and math.isclose(value, expected[key], rel_tol=1e-12, abs_tol=1e-12)) or value == expected[key]
                    if not matches:
                        raise AssertionError(f"HTML filter aggregate mismatch: {scope}/{cohort}/{variant}/{key}")
    old = json.loads((out / "inherited-v1/cases.json").read_text())
    current = {c["id"]: c for c in json.loads((out / "cases.json").read_text())}
    for case in old:
        if current[case["id"]] != case:
            raise AssertionError("Inherited annotation changed: " + case["id"])
    old_caches = json.loads((out / "inherited-v1/prediction-inputs.json").read_text())["files_sha256"]
    for relative, digest in old_caches.items():
        if hashlib.sha256((out / relative).read_bytes()).hexdigest() != digest:
            raise AssertionError("Inherited detector response changed: " + relative)
    parents = {c["id"] for c in old if c["provenance"] == "new_native_render"}
    additions = [c for c in current.values() if c.get("addition_kind") == "existing_scenario_variant"]
    if len(additions) != len(parents) or {c["parent_case_id"] for c in additions} != parents:
        raise AssertionError("Every original native scenario must have one additional view")
    if any(c["image_sha256"] == current[c["parent_case_id"]]["image_sha256"] for c in additions):
        raise AssertionError("An additional view reused the original image")
    return len(scopes)


def verify(out):
    html = (out / "report.html").read_text()
    script = re.search("<script>(.*?)</script>", html, re.S).group(1)
    data, _ = json.JSONDecoder().raw_decode(script.removeprefix("const DATA="))
    filter_scopes = verify_coverage_filters(out, data, script) if data.get("additional_coverage") else 0
    subprocess.run(
        ["node", "--check"], input=script, text=True, check=True, capture_output=True
    )
    cases = {c["id"]: c for c in data["cases"]}
    if not data["results"] == json.loads((out / "comparison.json").read_text()):
        raise AssertionError("Report integrity check failed")
    if not data["summary"] == json.loads((out / "summary.json").read_text()):
        raise AssertionError("Report integrity check failed")
    assets = set()
    span_path = out / "grip-span-verification.json"
    span_guard = json.loads(span_path.read_text()) if span_path.exists() else None
    if data.get("span_guard") != span_guard:
        raise AssertionError("Span countercontrol differs from saved evidence")
    if (
        span_guard is not None
        and span_guard["selector_sha256"]
        != hashlib.sha256(
            (Path(__file__).resolve().parents[2] / "semantic_selector.py").read_bytes()
        ).hexdigest()
    ):
        raise AssertionError("Span countercontrol used a different selector")
    if span_guard is not None:
        assets.update(span_guard[k] for k in ("source_photo", "hand_mask", "crop_path"))
        for control in span_guard.get("controls", []):
            assets.update(control[k] for k in ("hand_mask", "crop_path"))
    for case in cases.values():
        if not "fixture_detections" not in case:
            raise AssertionError("Report integrity check failed")
        assets.add(case["image"])
        assets.update((a["mask"] for a in case["annotations"]))
        assets.update(
            (
                "overlays/%s-%s.png" % (case["id"], layer)
                for layer in ("bottles", "labels", "hands", "target")
            )
        )
    semantic = []
    frozen_sha = hashlib.sha256(
        (out / "comparison-inputs.json").read_bytes()
    ).hexdigest()
    source = Path(__file__).resolve().parents[2]
    source_hashes = {
        name: hashlib.sha256((source / name).read_bytes()).hexdigest()
        for name in ("semantic_selector.py", "main_scene.py")
    }
    revision_path = out / "evaluation-revision.json"
    revision = json.loads(revision_path.read_text()) if revision_path.exists() else None
    if data.get("evaluation_revision") != revision:
        raise AssertionError("Report revision metadata differs from saved evidence")
    if revision is not None:
        if revision["selector_sha256"] != source_hashes["semantic_selector.py"]:
            raise AssertionError("Revision summary used a different selector")
        for name in ("revision-diff.json", "residual-failures.json"):
            if hashlib.sha256((out / name).read_bytes()).hexdigest() != revision["files_sha256"][name]:
                raise AssertionError("Revision audit changed: " + name)
    if data.get("additional_findings"):
        findings = json.loads((out / "additional-findings.json").read_text())
        if data["additional_findings"] != {k: v for k, v in findings.items() if k != "rows"}:
            raise AssertionError("Additional-coverage audit differs from report")
        expected_hashes = dict(
            selector_sha256=source_hashes["semantic_selector.py"],
            auditor_sha256=hashlib.sha256(Path(__file__).with_name("audit_additional_coverage.py").read_bytes()).hexdigest(),
            comparison_inputs_sha256=frozen_sha,
            prediction_inputs_sha256=hashlib.sha256((out / "prediction-inputs.json").read_bytes()).hexdigest(),
        )
        if any(findings[key] != digest for key, digest in expected_hashes.items()):
            raise AssertionError("Additional-coverage audit refers to different inputs/source")
        if findings["semantic_rows"] != sum(r["variant"] == "semantic-v2" for r in data["results"]):
            raise AssertionError("Additional-coverage audit has a different crop denominator")
    probes = json.loads((out / "perturbations.json").read_text())
    if (probes["comparison_inputs_sha256"] != frozen_sha
            or probes["prediction_inputs_sha256"] != hashlib.sha256((out / "prediction-inputs.json").read_bytes()).hexdigest()):
        raise AssertionError("Derived probes refer to different frozen inputs")
    audit = json.loads((out / "assignment-audit.json").read_text())
    if data.get("assignment_audit") != audit:
        raise AssertionError("Report assignment audit differs from saved evidence")
    if (
        audit["scorer_sha256"]
        != hashlib.sha256(
            Path(__file__).with_name("benchmark.py").read_bytes()
        ).hexdigest()
    ):
        raise AssertionError("Assignment audit used a different scorer")
    if (
        audit["selector_sha256"] != source_hashes["semantic_selector.py"]
        or audit["prediction_inputs_sha256"]
        != hashlib.sha256((out / "prediction-inputs.json").read_bytes()).hexdigest()
    ):
        raise AssertionError("Assignment audit refers to different inputs/source")
    if data["perturbations"] != {k: v for k, v in probes.items() if k != "rows"}:
        raise AssertionError("Report perturbation metadata differs from saved replay")
    if probes["selector_sha256"] != source_hashes["semantic_selector.py"]:
        raise AssertionError("Perturbations used a different selector revision")
    for row in data["results"]:
        if (
            row["prediction_inputs_sha256"]
            != hashlib.sha256((out / "prediction-inputs.json").read_bytes()).hexdigest()
        ):
            raise AssertionError("Report refers to a different prediction freeze")
        if not row["selector_source_sha256"] == source_hashes:
            raise AssertionError("Report integrity check failed")
        if not row["comparison_inputs_sha256"] == frozen_sha:
            raise AssertionError("Report integrity check failed")
        if not row["label_retention"] == row["raw_label_retention"]:
            raise AssertionError("Report integrity check failed")
        if row["metric_cohort"] == "rule_conformance" and row["variant"] == "scene-v1":
            if row["conformance_pass"] is not None:
                raise AssertionError("Report integrity check failed")
            for key in (
                "crop_target_coverage",
                "crop_distractor_retention",
                "label_retention",
                "foreign_label_retention",
                "representation_retention",
                "price_tag_retention",
            ):
                if row[key] is not None:
                    raise AssertionError("Legacy fixture metrics must be unavailable")
        case = cases[row["case_id"]]
        if not (row["mode"] == "fallback") == (
            case["provenance"] == "geometry_fixture"
        ):
            raise AssertionError("Report integrity check failed")
        assets.update(row.get("label_crop_paths", []))
        for key in ("crop_path", "keep_mask_path"):
            if row.get(key):
                assets.add(row[key])
        if row["variant"] != "semantic-v2":
            continue
        semantic.append(row)
        if row["tap_status"] not in (
            "absent",
            "missed",
            "multiple_hits",
            "resolved_mask",
            "resolved_label_context",
        ):
            raise AssertionError("Missing tap resolution metadata")
        if not (row.get("crop_path") and row.get("keep_mask_path")):
            raise AssertionError("Report integrity check failed")
        if row["status"] not in ("selected", "no_target"):
            raise AssertionError("Report integrity check failed")
        if row["selection_mode"] not in ("confident", "fallback"):
            raise AssertionError("Report integrity check failed")
        if row["selection_mode"] == "fallback":
            if not (row["fallback_trigger"] and row["reason"].startswith("fallback_")):
                raise AssertionError("Report integrity check failed")
        x, y, X, Y = row["crop_box"]
        with Image.open(out / row["crop_path"]) as crop:
            if not crop.size == (X - x, Y - y):
                raise AssertionError("Report integrity check failed")
        with Image.open(out / row["keep_mask_path"]) as mask:
            if not mask.size == (case["width"], case["height"]):
                raise AssertionError("Report integrity check failed")
        if row["status"] == "no_target":
            if row["selected_id"] is not None:
                raise AssertionError("Report integrity check failed")
            if not row["crop_box"] == [0, 0, case["width"], case["height"]]:
                raise AssertionError("Report integrity check failed")
            if not row["crop_scope"] == "original_frame":
                raise AssertionError("Report integrity check failed")
    for relative in assets:
        path = (out / relative).resolve()
        if not (path.is_relative_to(out) and path.is_file()):
            raise AssertionError(relative)
        with Image.open(path) as image:
            image.verify()
    result = dict(
        passed=True,
        javascript_syntax_valid=True,
        verified_image_assets=len(assets),
        photo_cases=sum(
            (c["provenance"] != "geometry_fixture" for c in cases.values())
        ),
        geometry_cases=sum(
            (c["provenance"] == "geometry_fixture" for c in cases.values())
        ),
        semantic_result_rows=len(semantic),
        semantic_rows_with_crop=len(semantic),
        browser_visual_check="not run for this release; offline data, JavaScript and image assets verified",
        coverage_filter_scopes_verified=filter_scopes,
        pixel_metrics_independent_of_selected_id=True,
        metrics_cohorts=list(data["summary"]["live"]),
    )
    (out / "report-verification.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    print(json.dumps(verify(parser.parse_args().output.resolve()), indent=2))
