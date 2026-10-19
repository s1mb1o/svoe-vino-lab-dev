"""Portable comparison: intent, interactions, policy and pixel quality stay separate."""

import argparse
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from matcher.experiments.main_selector.metrics import COHORTS


DECISION_FIELD = dict(
    passive_intent="intent_target_correct",
    interaction="intent_target_correct",
    policy_targets="policy_target_match",
    no_target="no_target_correct",
    rule_conformance="conformance_pass",
)


def summary(rows, cohort):
    def mean(key):
        values = [r[key] for r in rows if r.get(key) is not None]
        return float(np.mean(values)) if values else None

    decisions = [
        r[DECISION_FIELD[cohort]]
        for r in rows
        if r.get(DECISION_FIELD[cohort]) is not None
    ]
    labels = [
        r["label_retention"] for r in rows if r.get("label_retention") is not None
    ]
    return dict(
        cases=len(rows),
        decision_metric=DECISION_FIELD[cohort],
        decision_matches=sum(decisions),
        decision_trials=len(decisions),
        crops_returned=sum(bool(r.get("crop_path")) for r in rows),
        fallback_count=sum(r.get("selection_mode") == "fallback" for r in rows),
        full_frame_context_count=sum(r["full_frame_context"] for r in rows),
        target_coverage_mean=mean("crop_target_coverage"),
        distractor_retention_mean=mean("crop_distractor_retention"),
        label_retention_mean=mean("label_retention"),
        foreign_label_retention_mean=mean("foreign_label_retention"),
        representation_retention_mean=mean("representation_retention"),
        price_tag_retention_mean=mean("price_tag_retention"),
        label_cases=len(labels),
        label_crops_ge98=sum(v >= 0.98 for v in labels),
        expected_mode_matches=sum(r.get("expected_mode_match") is True for r in rows),
        expected_mode_trials=sum(
            r.get("expected_mode_match") is not None for r in rows
        ),
        policy_fallback_matches=sum(
            r.get("policy_fallback_pass") is True for r in rows
        ),
        policy_fallback_trials=sum(
            r.get("policy_fallback_pass") is not None for r in rows
        ),
        decisions_by_selection_mode={
            mode: dict(
                cases=sum(r.get("selection_mode") == mode for r in rows),
                decision_matches=sum(
                    bool(r.get(DECISION_FIELD[cohort]))
                    for r in rows
                    if r.get("selection_mode") == mode
                ),
                decision_trials=sum(
                    r.get(DECISION_FIELD[cohort]) is not None
                    for r in rows
                    if r.get("selection_mode") == mode
                ),
            )
            for mode in sorted({r.get("selection_mode", "unknown") for r in rows})
        },
        decisions_by_crop_scope={
            scope: dict(
                cases=sum(r.get("crop_scope") == scope for r in rows),
                decision_matches=sum(
                    bool(r.get(DECISION_FIELD[cohort]))
                    for r in rows
                    if r.get("crop_scope") == scope
                ),
                decision_trials=sum(
                    r.get(DECISION_FIELD[cohort]) is not None
                    for r in rows
                    if r.get("crop_scope") == scope
                ),
            )
            for scope in sorted({r.get("crop_scope", "unknown") for r in rows})
        },
    )


def build(out):
    protocol = json.loads((out / "protocol.json").read_text())
    cases = json.loads((out / "cases.json").read_text())
    rows = json.loads((out / "comparison.json").read_text())
    groups = protocol["groups"] + [
        dict(
            id="real",
            title="Real photographs from COCO",
            rules=[3, 4, 7],
            description="Inherited real COCO photos with bottle polygons; additional real photos are assigned to their relevant scenario groups. No real label masks. Target judgments have not been independently adjudicated, and background instance coverage can be incomplete.",
        ),
        dict(
            id="fallback",
            title="Always-crop fallback: tie and missing-candidate contracts",
            rules=[7, 8],
            description="Declared geometry fixtures test center-mask coverage, pixel distance, left/upper/ID ties, overlapping masks, missed inputs and absent candidates. Excluded from photo accuracy; only semantic-v2 is scored for the new contract.",
        ),
        dict(
            id="review",
            title="Review regressions: intent checks and complete context",
            rules=[3, 4, 6, 8],
            description="Declared fixtures reproduce missed taps, multi-hit taps, a tiny hand-contact distractor, an undetected secondary-label hole, unequal double grips and label-only context. Original pixels must survive; every successful response must contain a crop.",
        ),
    ]
    totals = {
        mode: {
            c: {
                variant: summary(
                    [
                        r
                        for r in rows
                        if r["mode"] == mode
                        and r["variant"] == variant
                        and r["metric_cohort"] == c
                    ],
                    c,
                )
                for variant in ("scene-v1", "semantic-v2")
            }
            for c in COHORTS
        }
        for mode in ("live", "controlled", "fallback")
    }
    page_cases = [
        dict(
            {k: v for k, v in c.items() if k != "fixture_detections"},
            annotations=[
                {k: v for k, v in a.items() if k != "segmentation"}
                for a in c["annotations"]
            ],
        )
        for c in cases
    ]
    geometry = json.loads((out / "policy-geometry.json").read_text())
    for case in page_cases:
        case["policy_geometry"] = geometry.get(case["id"])
        if case["id"] == "hc-101":
            case["review_note"] = (
                "This inherited source recipe removes every entity. The additional view is an "
                "empty-background negative control; it adds no evidence about wine-glass recognition."
            )
        if case["id"] in ("hc-039", "hc-041"):
            case["review_note"] = (
                "Unique contact no longer certifies a grip. Positive grip geometry is required; "
                "these cases now use geometric fallback. The original GT target stays fixed. "
                "Live detector boxes can break a GT tie differently, so a policy-ID mismatch remains visible."
            )
        if case["id"] == "hc-031":
            case["review_note"] = (
                "The outer wine-label detection covers the carton; nested bottle artwork is rejected. "
                "The full panel is retained as fallback context. The former wrong-ID score also came "
                "from label-only GT assignment: assignment-audit.json rescores the unchanged old crop "
                "for both variants and separates that measurement correction from this behavior change."
            )
        if case["id"] == "real-180751":
            case["review_note"] = (
                "Contested real target: SAM3 calls a held horizontal region a bottle, "
                "but its physical identity may be a sampling tool. The original "
                "standing-bottle annotation is retained. A conservative conflict "
                "rule is development tuning on this example; independent human "
                "adjudication and new real photographs remain necessary."
            )
        if case["id"] == "real-402720":
            case["review_note"] = (
                "Wine identity is unverified. COCO annotates generic bottles, and the tall "
                "labelled bottle may be another beverage. The original wine wording and target "
                "judgment remain frozen for audit; this is a bottle-framing regression, not "
                "a verified wine-intent positive."
            )
    payload = dict(
        evaluation_revision=json.loads((out / "evaluation-revision.json").read_text())
        if (out / "evaluation-revision.json").exists() else None,
        additional_findings={k: v for k, v in json.loads((out / "additional-findings.json").read_text()).items()
                             if k != "rows"} if (out / "additional-findings.json").exists() else None,
        additional_coverage=protocol.get("additional_coverage"),
        addition_summary={
            mode: {
                kind: {
                    c: {
                        variant: summary([r for r in rows if r["mode"] == mode
                                          and r["variant"] == variant and r["metric_cohort"] == c
                                          and next(case for case in cases if case["id"] == r["case_id"])
                                          .get("addition_kind", "v1_inherited") == kind], c)
                        for variant in ("scene-v1", "semantic-v2")
                    } for c in COHORTS
                } for kind in ("v1_inherited", "existing_scenario_variant", "new_scenario", "additional_real_photo")
            } for mode in ("live", "controlled", "fallback")
        },
        span_guard=json.loads((out / "grip-span-verification.json").read_text())
        if (out / "grip-span-verification.json").exists()
        else None,
        assignment_audit=json.loads((out / "assignment-audit.json").read_text())
        if (out / "assignment-audit.json").exists()
        else None,
        cases=page_cases,
        results=rows,
        groups=groups,
        summary=totals,
        group_summary={
            mode: {
                g["id"]: {
                    c: {
                        variant: summary(
                            [
                                r
                                for r in rows
                                if r["mode"] == mode
                                and r["variant"] == variant
                                and r["metric_cohort"] == c
                                and r["group"] == g["id"]
                            ],
                            c,
                        )
                        for variant in ("scene-v1", "semantic-v2")
                    }
                    for c in COHORTS
                }
                for g in groups
            }
            for mode in ("live", "controlled", "fallback")
        },
        samples=json.loads((out / "external-samples.json").read_text()),
        perturbations={
            k: v
            for k, v in json.loads((out / "perturbations.json").read_text()).items()
            if k != "rows"
        },
        revision_summary={
            mode: {
                revision: {
                    c: {
                        variant: summary(
                            [
                                r
                                for r in rows
                                if r["mode"] == mode
                                and r["variant"] == variant
                                and r["metric_cohort"] == c
                                and (
                                    next(
                                        case
                                        for case in cases
                                        if case["id"] == r["case_id"]
                                    ).get("extension", False)
                                )
                                == (revision == "expansion")
                            ],
                            c,
                        )
                        for variant in ("scene-v1", "semantic-v2")
                    }
                    for c in COHORTS
                }
                for revision in ("original", "expansion")
            }
            for mode in ("live", "controlled", "fallback")
        },
    )
    (out / "summary.json").write_text(json.dumps(totals, indent=2) + "\n")
    data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).replace(
        "<", "\\u003c"
    )
    template = Path(__file__).with_name("report_template.html").read_text()
    (out / "report.html").write_text(template.replace("__DATA__", data))
    return totals


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    print(json.dumps(build(parser.parse_args().output.resolve()), indent=2))
