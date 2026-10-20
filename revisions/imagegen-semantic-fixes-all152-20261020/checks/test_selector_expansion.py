"""Additional-coverage contracts: declared targets, detector faults and HTML metrics."""

from copy import deepcopy
import hashlib
from io import BytesIO
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from PIL import Image, ImageDraw

from matcher.experiments.main_selector.benchmark import controlled_case, prediction_signature
from matcher.experiments.main_selector.report import DECISION_FIELD, summary
from matcher.experiments.main_selector.metrics import COHORTS


class ExpansionFaultTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.size = (120, 160)
        bottle = Image.new("L", self.size)
        ImageDraw.Draw(bottle).rectangle((40, 30, 74, 149), fill=255)
        bottle.save(self.root / "bottle.png")
        panel = Image.new("L", self.size)
        ImageDraw.Draw(panel).rectangle((10, 10, 99, 154), fill=255)
        ImageDraw.Draw(panel).rectangle((40, 30, 74, 149), fill=0)
        panel.save(self.root / "panel.png")
        self.case = dict(operation="v2_real_bottle_amodal_panel", width=120, height=160,
                         annotations=[dict(instance_id=1, category="bottle", mask="bottle.png", parent_instance_id=None,
                                           box=[40, 30, 75, 150], sha256="bottle"),
                                      dict(instance_id=500, category="display", mask="panel.png", parent_instance_id=None,
                                           box=[10, 10, 100, 155], sha256="panel")])

    def test_filled_panel_is_an_explicit_detector_fault_and_never_changes_visible_gt(self):
        import base64

        before = (self.root / "panel.png").read_bytes()
        original = deepcopy(self.case)
        ordinary = controlled_case(self.case, self.root)
        with_fault = controlled_case(dict(self.case, v2_fault="amodal_panel"), self.root)
        self.assertEqual(len(with_fault), len(ordinary) + 1)
        self.assertEqual(with_fault[-1]["label"], "wine label")
        with Image.open(BytesIO(base64.b64decode(with_fault[-1]["mask_png_b64"]))) as mask:
            self.assertEqual(mask.getpixel((50, 50)), 255)
        with Image.open(self.root / "panel.png") as truth:
            self.assertEqual(truth.getpixel((50, 50)), 0)
        self.assertEqual(self.case, original)
        self.assertEqual((self.root / "panel.png").read_bytes(), before)

    def test_fault_invalidates_only_controlled_signatures_not_live_detector_inputs(self):
        fault = dict(self.case, v2_fault="amodal_panel")
        self.assertEqual(prediction_signature(self.case, b"same RGB", "live"),
                         prediction_signature(fault, b"same RGB", "live"))
        self.assertNotEqual(prediction_signature(self.case, b"same RGB", "controlled"),
                            prediction_signature(fault, b"same RGB", "controlled"))


@unittest.skipUnless(shutil.which("node"), "Node is needed to check report aggregation")
class ReportCoverageAggregationTest(unittest.TestCase):
    def test_browser_aggregate_matches_python_for_filtered_scopes_and_missing_label_gt(self):
        template = (Path(__file__).resolve().parents[1] /
                    "experiments/main_selector/report_template.html").read_text()
        function = template.split("function aggregate(rows){", 1)[1].split("function render(){", 1)[0]
        function = "function aggregate(rows){" + function
        rows = []
        for i, cohort in enumerate(COHORTS):
            for j, variant in enumerate(("scene-v1", "semantic-v2")):
                for k in range(3):
                    row = dict(metric_cohort=cohort, variant=variant, group="one" if k else "two",
                               addition_kind="new_scenario" if k else "v1_inherited",
                               crop_path="crop.png", selection_mode="fallback" if k else "confident",
                               crop_scope="subject_region" if k else "original_frame",
                               full_frame_context=k == 0, crop_target_coverage=0.2 + k * 0.3,
                               crop_distractor_retention=None if k == 1 else 0.6,
                               label_retention=None if k == 0 else 0.4 + k * 0.2,
                               foreign_label_retention=0.3, representation_retention=None,
                               expected_mode_match=None if k == 0 else k == 2,
                               policy_fallback_pass=None if cohort != "policy_targets" else k == 1)
                    row[DECISION_FIELD[cohort]] = None if j == 0 and cohort == "rule_conformance" else k != 1
                    rows.append(row)
        scopes = [rows, [r for r in rows if r["group"] == "one"],
                  [r for r in rows if r["addition_kind"] == "v1_inherited"], []]
        code = "const cohortNames=" + json.dumps(dict.fromkeys(COHORTS)) + ";\n"
        code += "const metricFields=" + json.dumps(DECISION_FIELD) + ";\n"
        code += "function decisionMetric(r){return r[metricFields[r.metric_cohort]]}\n" + function
        code += "process.stdout.write(JSON.stringify(" + json.dumps(scopes) + ".map(aggregate)));"
        actual = json.loads(subprocess.check_output([shutil.which("node"), "-e", code], text=True))
        for scoped_rows, values in zip(scopes, actual):
            for cohort in COHORTS:
                for variant in ("scene-v1", "semantic-v2"):
                    expected = summary([r for r in scoped_rows if r["metric_cohort"] == cohort
                                        and r["variant"] == variant], cohort)
                    for key, value in values[cohort][variant].items():
                        with self.subTest(cohort=cohort, variant=variant, metric=key):
                            if isinstance(value, float):
                                self.assertAlmostEqual(value, expected[key], places=12)
                            else:
                                self.assertEqual(value, expected[key])

    def test_inherited_detector_fixture_implementation_is_unchanged(self):
        # The old controlled fixture function is part of the stored cache key.
        # A new fault must be dispatched outside it, preserving all old signatures.
        import inspect
        from matcher.experiments.main_selector.benchmark import controlled

        self.assertEqual(hashlib.sha256(inspect.getsource(controlled).encode()).hexdigest(),
                         "bc6d48ed463903d3cda34d99eed2db025df524035ac4579c5b01bdcaf3bd1ecb")


if __name__ == "__main__":
    unittest.main()
