import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
# `scripts/common.py` reads the old configuration of the review tool: `config.yaml` is
# the configuration of the lab server.
os.environ.setdefault("SVOE_VINO_REVIEW_CONFIG", str(ROOT / "config.old.yaml"))
import cluster_rules as RULES  # noqa: E402


class ClusterRuleEditTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "rules.json"
        self.old_file = RULES.RULES_FILE
        RULES.RULES_FILE = str(self.path)
        self.slugs = ["wine-a", "wine-b"]
        self.key = RULES.cluster_key(self.slugs)
        self.generated_answer = {
            "questions": [{
                "question": "Old question?",
                "answers": {"A": "old a", "B": "old b"},
            }],
            "rule": "Old rule.",
        }
        self.path.write_text(json.dumps({
            "version": 1,
            "cards": {},
            "clusters": {self.key: {
                "key": self.key,
                "slugs": self.slugs,
                "letters": {"A": "wine-a", "B": "wine-b"},
                "inputs_sha": "keep-this-sha",
                "built_at": "2026-09-24T10:00:00+0300",
                "mode": "sheet",
                "questions": [],
                "rule": "Old rule.",
                "indistinguishable": [],
                "answer": self.generated_answer,
            }},
        }), encoding="utf-8")

    def tearDown(self):
        RULES.RULES_FILE = self.old_file
        self.directory.cleanup()

    def test_edit_rechecks_questions_and_preserves_build_identity(self):
        edited = RULES.edit_rule(self.slugs, {
            "rule": "Read the colour word.",
            "questions": [{
                "question": "Which colour word is printed?",
                "answers": {"wine-a": "red", "wine-b": "white"},
            }],
        }, {})

        self.assertEqual(edited["mode"], "sheet")
        self.assertEqual(edited["inputs_sha"], "keep-this-sha")
        self.assertEqual(edited["built_at"], "2026-09-24T10:00:00+0300")
        self.assertTrue(edited["edited_at"])
        self.assertEqual(edited["questions"], [{
            "id": "q1",
            "question": "Which colour word is printed?",
            "answers": {"wine-a": "red", "wine-b": "white"},
            "kind": "feature",
            "valid": True,
        }])
        self.assertEqual(edited["answer"]["questions"][0]["answers"], {
            "A": "red", "B": "white",
        })
        self.assertEqual(edited["generated_answer"], self.generated_answer)

        stored = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(stored["clusters"][self.key]["rule"], "Read the colour word.")

    def test_no_valid_question_uses_the_edited_verdict_rule(self):
        edited = RULES.edit_rule(self.slugs, {
            "rule": "Gold text is Card A. Silver text is Card B.",
            "questions": [],
        }, {})

        self.assertEqual(edited["mode"], "verdict")
        self.assertEqual(edited["questions"], [])

    def test_invalid_question_does_not_write_the_file(self):
        before = self.path.read_bytes()

        with self.assertRaisesRegex(ValueError, "outside the cluster"):
            RULES.edit_rule(self.slugs, {
                "rule": "Rule.",
                "questions": [{
                    "question": "Question?",
                    "answers": {"wine-a": "a", "wine-b": "b", "wine-c": "c"},
                }],
            }, {})

        self.assertEqual(self.path.read_bytes(), before)

    def test_more_than_three_questions_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "at most 3 questions"):
            RULES.edit_rule(self.slugs, {
                "rule": "Rule.",
                "questions": [{"question": "Q?", "answers": {}}] * 4,
            }, {})


if __name__ == "__main__":
    unittest.main()
