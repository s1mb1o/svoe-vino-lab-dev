"""Tests of `scripts/runner_smoke.py`, the smoke check of the self-hosted runner.
The tests make no network call and load no model."""
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import runner_smoke  # noqa: E402

try:
    import zxingcpp
except ImportError:
    zxingcpp = None

# The values of the runner environment (owner message of 2026-09-28T08:55:00+0300).
ENV = {
    "SIGLIP2_ENDPOINT": "http://192.168.86.14:18082",
    "GROUNDING_DINO_ENDPOINT": "http://192.168.86.14:18082/upstream/grounding-dino-base",
    "SAM3_ENDPOINT": "http://192.168.86.14:18082/upstream/sam3",
    "VLM_ENDPOINT": "http://192.168.86.14:18081/v1",
    "VLM_MODEL": "qwen3.5-9b-nvfp4",
    "SHIELDGEMMA_ENDPOINT": "http://192.168.86.14:18081/upstream/shieldgemma-2-4b-it",
    "QR_SCANNER_ENDPOINT": "http://192.168.86.14:18081/upstream/qr-scanner",
}


def quiet_report():
    return runner_smoke.Report(out=io.StringIO())


class Ean13Test(unittest.TestCase):

    def test_the_check_digit(self):
        self.assertEqual(runner_smoke.ean13("400638133393"), "4006381333931")
        self.assertEqual(runner_smoke.ean13("200000000000"), "2000000000008")

    def test_the_modules_have_the_guards(self):
        modules = runner_smoke.ean13_modules("4006381333931")
        self.assertEqual(len(modules), 95)
        self.assertEqual(modules[:3], "101")
        self.assertEqual(modules[45:50], "01010")
        self.assertEqual(modules[-3:], "101")

    def test_the_image_has_the_quiet_zone(self):
        image = runner_smoke.ean13_image("4006381333931", module=4)
        self.assertEqual(image.width, (95 + 22) * 4)
        self.assertEqual(image.getpixel((0, 100)), 255)
        self.assertEqual(image.getpixel((11 * 4, 100)), 0)

    @unittest.skipUnless(zxingcpp, "zxingcpp is not installed")
    def test_zxing_reads_the_image(self):
        for code in ("4006381333931", runner_smoke.ean13("212345678901")):
            texts = [r.text for r in zxingcpp.read_barcodes(runner_smoke.ean13_image(code))]
            self.assertEqual(texts, [code])


class ParseTest(unittest.TestCase):

    def test_upstream_splits_the_root_and_the_model(self):
        self.assertEqual(runner_smoke.upstream(ENV["SAM3_ENDPOINT"]),
                         ("http://192.168.86.14:18082", "sam3"))
        self.assertEqual(runner_smoke.upstream(ENV["QR_SCANNER_ENDPOINT"] + "/"),
                         ("http://192.168.86.14:18081", "qr-scanner"))

    def test_upstream_refuses_another_form(self):
        for url in ("http://192.168.86.14:18081", "http://h/upstream/", "http://h/upstream/a/b"):
            with self.assertRaises(ValueError):
                runner_smoke.upstream(url)

    def test_box_iou(self):
        box = runner_smoke.BOTTLE_BOX
        self.assertEqual(runner_smoke.box_iou(box, box), 1.0)
        self.assertEqual(runner_smoke.box_iou((0, 0, 10, 10), (20, 20, 30, 30)), 0.0)
        self.assertAlmostEqual(runner_smoke.box_iou((0, 0, 10, 10), (5, 0, 15, 10)), 1 / 3)

    def test_the_fixture_is_present(self):
        self.assertTrue(runner_smoke.BOTTLE.is_file())


class VariablesTest(unittest.TestCase):

    def test_all_variables_pass(self):
        report = quiet_report()
        self.assertEqual(runner_smoke.check_variables(ENV, report), set(runner_smoke.VARIABLES))
        self.assertFalse(report.failed())

    def test_a_missing_and_an_invalid_variable_fail(self):
        env = dict(ENV, SAM3_ENDPOINT="192.168.86.14:18082/upstream/sam3")
        del env["VLM_MODEL"]
        report = quiet_report()
        valid = runner_smoke.check_variables(env, report)
        self.assertNotIn("SAM3_ENDPOINT", valid)
        self.assertNotIn("VLM_MODEL", valid)
        failed = {row[1] for row in report.rows if row[2] == "fail"}
        self.assertEqual(failed, {"SAM3_ENDPOINT", "VLM_MODEL"})

    def test_another_variable_is_never_printed(self):
        out = io.StringIO()
        env = dict(ENV, QWENCLOUD_TOKEN_PLAN_API_KEY="sk-secret-value")
        runner_smoke.check_variables(env, runner_smoke.Report(out=out))
        self.assertNotIn("sk-secret-value", out.getvalue())
        self.assertNotIn("QWENCLOUD", out.getvalue())

    def test_the_services_of_the_runner_environment(self):
        report = quiet_report()
        valid = runner_smoke.check_variables(ENV, report)
        found = {s.name: (s.root, s.model) for s in runner_smoke.services(ENV, valid, report)}
        self.assertEqual(found, {
            "siglip2": ("http://192.168.86.14:18082", runner_smoke.DEFAULT_SIGLIP2_MODEL),
            "grounding-dino": ("http://192.168.86.14:18082", "grounding-dino-base"),
            "sam3": ("http://192.168.86.14:18082", "sam3"),
            "vlm": ("http://192.168.86.14:18081", "qwen3.5-9b-nvfp4"),
            "shieldgemma": ("http://192.168.86.14:18081", "shieldgemma-2-4b-it"),
            "qr-scanner": ("http://192.168.86.14:18081", "qr-scanner"),
        })

    def test_siglip2_model_overrides_the_default(self):
        env = dict(ENV, SIGLIP2_MODEL="siglip2-so400m-patch16-512")
        report = quiet_report()
        found = {s.name: s.model for s in runner_smoke.services(
            env, runner_smoke.check_variables(env, report), report)}
        self.assertEqual(found["siglip2"], "siglip2-so400m-patch16-512")


class PlanTest(unittest.TestCase):

    def test_a_model_that_runs_gets_a_call(self):
        self.assertEqual(runner_smoke.action("ready", False), "call")

    def test_a_model_that_does_not_run_is_idle(self):
        self.assertEqual(runner_smoke.action(None, False), "idle")
        self.assertEqual(runner_smoke.action("starting", False), "warn")

    def test_load_models_calls_each_model(self):
        self.assertEqual(runner_smoke.action(None, True), "call")
        self.assertEqual(runner_smoke.action("starting", True), "call")

    def test_an_idle_service_is_no_failure(self):
        report = quiet_report()
        service = runner_smoke.Service("sam3", "SAM3_ENDPOINT", "u", "r", "sam3",
                                       lambda *a: self.fail("the check was called"))
        runner_smoke.serve(service, None, False, report)
        self.assertEqual(report.rows[0][2], "idle")
        self.assertFalse(report.failed())

    def test_a_check_error_is_a_failure(self):
        def check(service, timeout):
            raise runner_smoke.CheckError("HTTP 500: boom")
        report = quiet_report()
        runner_smoke.serve(runner_smoke.Service("sam3", "v", "u", "r", "sam3", check),
                           "ready", False, report)
        self.assertEqual(report.rows[0][2:], ("fail", "HTTP 500: boom"))


class MainTest(unittest.TestCase):

    def test_no_variables_fail_and_write_the_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = os.path.join(tmp, "summary.md")
            out = io.StringIO()
            stdout, sys.stdout = sys.stdout, out
            try:
                code = runner_smoke.main([], env={"GITHUB_STEP_SUMMARY": summary})
            finally:
                sys.stdout = stdout
            self.assertEqual(code, 1)
            with open(summary, encoding="utf-8") as handle:
                text = handle.read()
            self.assertIn("## Runner smoke", text)
            self.assertIn("| variables | SAM3_ENDPOINT | FAIL | not set |", text)


if __name__ == "__main__":
    unittest.main()
