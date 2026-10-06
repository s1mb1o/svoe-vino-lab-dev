"""Render rejected and recovered VLM evidence without a browser or model service."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path


@unittest.skipUnless(shutil.which("node"), "Node.js is needed for the shared renderer")
class RetryDisplayTest(unittest.TestCase):
    def render(self, value):
        source = Path(__file__).resolve().parents[1] / "pipeline/pages/steps.js"
        script = source.read_text() + "\nprocess.stdout.write(Steps.vlm(" + json.dumps(value) + "));"
        return subprocess.check_output(["node", "-e", script], text=True)

    def fixture(self):
        return {
            "mode": "evidence", "window": ["a", "b"], "option_scores": {},
            "questions": [{"id": "q1", "question": "Variety?", "options": ["SAPERAVI"]},
                          {"id": "q3", "question": "Colour?", "options": ["white", "other"]}],
            "raw_option_scores": {"q1": {"SAPERAVI": 100}, "q3": {"white": 0, "other": 0}},
            "validation_errors": {"q3": "q3 total 0; expected 100"},
            "error": "VlmError: q3 total 0; expected 100",
        }

    def test_rejected_answer_keeps_valid_scores_and_marks_the_failed_question(self):
        html = self.render(self.fixture())
        self.assertIn("<b>SAPERAVI</b> 100%", html)
        self.assertIn("Rejected: q3 total 0", html)
        self.assertIn("These scores were not used for ranking", html)
        self.assertNotIn("no answer", html)
        self.assertNotIn("scores: <b>a</b> 0", html)

    def test_successful_retry_keeps_rejected_attempt_visible_and_escapes_raw_text(self):
        value = self.fixture()
        value["attempts"] = [dict(number=1, cached=True, error=value["error"],
                                  raw_option_scores=value["raw_option_scores"],
                                  validation_errors=value["validation_errors"],
                                  raw_text='<script>alert("x")</script>'),
                             dict(number=2, cached=False, ms=100, error=None,
                                  raw_option_scores={"q1": {"SAPERAVI": 100}},
                                  validation_errors={})]
        value.update(error=None, validation_errors={},
                     option_scores={"q1": {"SAPERAVI": 100}, "q3": {"white": 0, "other": 100}})
        html = self.render(value)
        self.assertIn("Response accepted after one retry", html)
        self.assertIn("Attempt 1", html)
        self.assertIn("Attempt 2", html)
        self.assertIn("q3 total 0", html)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_legacy_sheet_answers_still_render(self):
        html = self.render({"mode": "sheet", "answers": {"q1": "dry"},
                            "questions": [{"id": "q1", "question": "Sugar?"}]})
        self.assertIn('class="a">dry', html)
        self.assertNotIn("Rejected", html)

    def test_old_evidence_runs_do_not_claim_that_the_model_gave_no_answer(self):
        value = self.fixture()
        value.pop("raw_option_scores")
        html = self.render(value)
        self.assertIn("Raw option scores were not recorded in this run", html)
        self.assertNotIn("no answer", html)
