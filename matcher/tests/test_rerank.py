"""Tests of the cluster re-rank rules of the backend `cascade`."""

import json
from pathlib import Path
import tempfile
import unittest

from matcher import rerank

from cascade_fakes import chat_body, rules


def book(mode="verdict", slugs=("wine-a", "wine-b")):
    return rerank.RuleBook(*rules(mode, slugs))


class AnswerTest(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(rerank.normalize("  «Полусладкое»  "), "полусладкое")
        self.assertEqual(rerank.normalize("30 / 70"), "30/70")
        self.assertEqual(rerank.normalize("Ёлка"), "елка")
        for empty in (None, "", "Not visible", "n/a", "не видно", "UNKNOWN."):
            self.assertIsNone(rerank.normalize(empty))

    def test_parse_json(self):
        self.assertEqual(rerank.parse_json('{"wine": "A"}'), {"wine": "A"})
        self.assertEqual(rerank.parse_json('Answer: {"q1": "red"} done'), {"q1": "red"})
        for text in ("[1, 2]", "no json", None):
            self.assertIsNone(rerank.parse_json(text))

    def test_answer_of_refuses_cut_and_empty_answers(self):
        self.assertEqual(rerank.answer_of(chat_body({"wine": "A"})), {"wine": "A"})
        for body in (chat_body({"wine": "A"}, "length"), {"choices": []}, {},
                     {"choices": [{"message": {"content": "plain text"}}]}):
            with self.subTest(body=str(body)[:40]), self.assertRaises(ValueError):
                rerank.answer_of(body)


class RuleTest(unittest.TestCase):
    def test_options_and_sheet_prompt(self):
        rule = book("sheet").by_slug["wine-a"]
        self.assertEqual(rerank.options_of(rule["questions"][0]),
                         ["red", "blue", "other", "not visible"])
        prompt = rerank.sheet_prompt(rule)
        self.assertTrue(prompt.startswith(rerank.SHEET_PROMPT.split("%(questions)s")[0]))
        self.assertIn('q1: What colour is the label?\nOptions: "red", "blue", "other", '
                      '"not visible"', prompt)

    def test_sheet_scores_and_vintage_answers(self):
        rule = book("sheet").by_slug["wine-a"]
        self.assertEqual(rerank.sheet_scores(rule, {"q1": "Blue"}, rule["slugs"]),
                         {"wine-a": -1, "wine-b": 1})
        self.assertEqual(rerank.sheet_scores(rule, {"q1": "not visible"}, rule["slugs"]),
                         {"wine-a": 0, "wine-b": 0})
        question = {"kind": "vintage", "answers": {"a": "2021", "b": "2023"}}
        self.assertEqual(rerank.compared_answer(question, "урожай 2023 года"), "2023")
        self.assertEqual(rerank.compared_answer(question, "2019"), "other")
        self.assertEqual(rerank.compared_answer(question, "2021 or 2023"), "2021 or 2023")

    def test_verdict_prompt_schema_and_choice(self):
        rule = book().by_slug["wine-a"]
        prompt = rerank.verdict_prompt(rule, {"wine-a": "Вино А"}, {})
        self.assertIn('A: name "Вино А"; label: no description', prompt)
        self.assertIn('B: name "wine-b"; label: no description', prompt)
        self.assertIn("Rule: The label of wine B is blue.", prompt)
        self.assertEqual(rerank.verdict_schema(rule)["properties"]["wine"]["enum"],
                         ["A", "B", "unsure"])
        self.assertEqual(rerank.verdict_choice(rule, {"wine": " b. "}), "wine-b")
        self.assertIsNone(rerank.verdict_choice(rule, {"wine": "unsure"}))

    def test_window_ranking_and_reorder_keep_the_position_scores(self):
        rule = book().by_slug["wine-a"]
        pairs = [("wine-a", 0.9), ("wine-x", 0.8), ("wine-b", 0.7)]
        ranking = rerank.window_ranking(rule, {"wine": "B"}, ["wine-a", "wine-b"])
        self.assertEqual(ranking, ["wine-b", "wine-a"])
        self.assertEqual(rerank.reorder(pairs, [0, 2], ranking),
                         [("wine-b", 0.9), ("wine-x", 0.8), ("wine-a", 0.7)])
        self.assertEqual(rerank.window_ranking(rule, {"wine": "C"}, ["wine-a", "wine-b"]),
                         ["wine-a", "wine-b"])

    def test_trigger_window_and_first(self):
        rules_ = book()
        pairs = [("wine-a", 0.9)] + [("x%d" % n, 0.5) for n in range(8)] + [("wine-b", 0.4)]
        rule, positions = rules_.trigger(pairs, 10)
        self.assertEqual((rule["key"], positions), ("k1", [0, 9]))
        self.assertEqual(rules_.trigger(pairs, 9), (None, []))
        self.assertEqual(rules_.trigger([("x0", 1.0)] + pairs, 10), (None, []))
        self.assertEqual(rules_.trigger(pairs, 10, first={"wine-a"}), (None, []))
        self.assertEqual(rules_.trigger(pairs, 10, first={"wine-a", "wine-b"})[1], [0, 9])

    def test_payload(self):
        rule = book().by_slug["wine-a"]
        body = rerank.payload(rule, b"png-bytes", "model-x", 64, {}, {})
        self.assertEqual(set(body), {"model", "temperature", "max_tokens", "response_format",
                                     "messages", "chat_template_kwargs"})
        self.assertEqual((body["model"], body["temperature"], body["max_tokens"]),
                         ("model-x", 0, 64))
        self.assertEqual(body["chat_template_kwargs"], {"enable_thinking": False})
        content = body["messages"][0]["content"]
        self.assertEqual(content[0]["image_url"]["url"], "data:image/png;base64,cG5nLWJ5dGVz")
        self.assertEqual(content[1]["type"], "text")
        sheet = rerank.payload(book("sheet").by_slug["wine-a"], b"x", "m", 8, {}, {})
        self.assertEqual(sheet["response_format"], {"type": "json_object"})

    def test_rule_book_counts_and_files(self):
        clusters, data = rules()
        clusters["spaces"]["combined"]["clusters"].extend([
            {"key": "k2", "slugs": ["c", "d"]}, {"key": "k3", "slugs": ["e", "f"]}])
        data["spaces"]["label"]["k2"] = {"key": "k2", "slugs": ["c", "d"], "error": "boom"}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / rerank.CLUSTERS_FILE).write_text(json.dumps(clusters), encoding="utf-8")
            (root / rerank.RULES_FILE).write_text(json.dumps(data), encoding="utf-8")
            loaded = rerank.RuleBook.load(root)
        self.assertEqual(loaded.counts, {"clusters": 3, "sheet": 0, "verdict": 1, "none": 0,
                                         "no_rule": 1, "error": 1})
        self.assertEqual(sorted(loaded.by_slug), ["wine-a", "wine-a2"])
        with tempfile.TemporaryDirectory() as directory, \
                self.assertRaises(rerank.RuleError):
            rerank.RuleBook.load(directory)


if __name__ == "__main__":
    unittest.main()
