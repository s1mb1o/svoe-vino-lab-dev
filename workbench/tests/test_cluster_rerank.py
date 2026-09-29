"""The cluster re-rank of plan 48: the answers, the trigger, the order, the backend, and
the key `rerank` of a pipeline. No test calls a VLM or SAM3."""
import ast
import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

import yaml

import embedding_lab  # noqa: F401  (puts pipeline/ on sys.path)
from embedding_lab import standard_lab

import cluster_rerank  # noqa: E402
import clusters  # noqa: E402
import pipelines  # noqa: E402
from embeddings import ConfigError  # noqa: E402

MATCHER = Path(__file__).resolve().parents[3] / "svoe-vino-matcher" / "svm" / "cluster_rules.py"
A, B, C, D = "wine-a-12", "wine-b-12", "wine-c-12", "wine-d-12"


def sheet_rule(slugs=(A, B, C), kind="feature", answers=None, valid=True):
    slugs = sorted(slugs)
    answers = answers or {A: "30/70", B: "50/50", C: "70/30"}
    return {"key": clusters.cluster_key(slugs), "slugs": slugs,
            "letters": {chr(65 + i): s for i, s in enumerate(slugs)}, "mode": "sheet",
            "rule": "Read the ratio.", "error": None,
            "questions": [{"id": "q1", "question": "What ratio is printed?", "kind": kind,
                           "valid": valid, "answers": answers}]}


def verdict_rule(slugs=(A, B)):
    slugs = sorted(slugs)
    return {"key": clusters.cluster_key(slugs), "slugs": slugs,
            "letters": {chr(65 + i): s for i, s in enumerate(slugs)}, "mode": "verdict",
            "rule": "If the label shows 2024, it is card B.", "error": None, "questions": []}


def cands(*slugs):
    return [{"slug": s, "score": round(0.9 - 0.01 * i, 4), "rank": i + 1}
            for i, s in enumerate(slugs)]


class AnswerTest(unittest.TestCase):
    def test_the_options_hold_other_and_not_visible_once(self):
        q = sheet_rule()["questions"][0]
        self.assertEqual(cluster_rerank.options_of(q),
                         ["30/70", "50/50", "70/30", "other", "not visible"])
        q = {"answers": {A: "2020", B: "other"}}
        self.assertEqual(cluster_rerank.options_of(q), ["2020", "other", "not visible"])

    def test_the_ratio_selects_one_card(self):
        rule = sheet_rule()
        self.assertEqual(cluster_rerank.sheet_scores(rule, {"q1": "50 / 50"}, rule["slugs"]),
                         {A: -1, B: 1, C: -1})

    def test_not_visible_gives_no_evidence_and_other_counts_against_every_card(self):
        rule = sheet_rule()
        self.assertEqual(cluster_rerank.sheet_scores(rule, {"q1": "not visible"}, rule["slugs"]),
                         {A: 0, B: 0, C: 0})
        self.assertEqual(cluster_rerank.sheet_scores(rule, {"q1": "other"}, rule["slugs"]),
                         {A: -1, B: -1, C: -1})

    def test_an_invalid_question_does_not_count(self):
        rule = sheet_rule(valid=False)
        self.assertEqual(cluster_rerank.sheet_scores(rule, {"q1": "30/70"}, rule["slugs"]),
                         {A: 0, B: 0, C: 0})
        self.assertNotIn("q1:", cluster_rerank.sheet_prompt(rule))

    def test_an_unlisted_year_selects_the_card_without_a_year(self):
        rule = sheet_rule(slugs=(A, B), kind="vintage", answers={A: "2020", B: "other"})
        self.assertEqual(cluster_rerank.sheet_scores(rule, {"q1": "урожай 2023"}, rule["slugs"]),
                         {A: -1, B: 1})
        self.assertEqual(cluster_rerank.sheet_scores(rule, {"q1": "2020"}, rule["slugs"]),
                         {A: 1, B: -1})

    def test_a_year_counts_as_other_only_in_a_vintage_question(self):
        rule = sheet_rule(slugs=(A, B), answers={A: "2020", B: "other"})
        self.assertEqual(cluster_rerank.sheet_scores(rule, {"q1": "2023"}, rule["slugs"]),
                         {A: -1, B: -1})

    def test_a_verdict_allows_the_letters_and_unsure(self):
        rule = verdict_rule()
        schema = cluster_rerank.verdict_schema(rule)
        self.assertEqual(schema["properties"]["wine"]["enum"], ["A", "B", "unsure"])
        self.assertEqual(cluster_rerank.verdict_choice(rule, {"wine": "b"}), B)
        self.assertIsNone(cluster_rerank.verdict_choice(rule, {"wine": "unsure"}))

    def test_positions_keep_their_scores(self):
        base = cands(B, A, D)
        out = cluster_rerank.reorder(base, [0, 1], [A, B], {"kind": "cluster_rules"})
        self.assertEqual([c["slug"] for c in out], [A, B, D])
        self.assertEqual([c["score"] for c in out], [c["score"] for c in base])
        self.assertEqual(out[0]["explain"]["base_rank"], 2)
        self.assertNotIn("explain", out[2])


class Fixture:
    """A lab directory: a database with the catalogue names, a config with one vlm entry,
    and an embedding directory `rules` with `clusters.json` and `cluster-rules.json`."""

    def __init__(self, root, rules):
        self.root = Path(root)
        self.db_path = str(self.root / "data" / "lab.sqlite3")
        os.makedirs(os.path.dirname(self.db_path))
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute("CREATE TABLE wine_catalog "
                         "(wine_slug TEXT, name TEXT, name_patched TEXT)")
            conn.executemany("INSERT INTO wine_catalog (wine_slug, name) VALUES (?, ?)",
                             [(s, "Name " + s) for s in (A, B, C, D)])
            conn.commit()
        self.config_path = str(self.root / "config.yaml")
        Path(self.config_path).write_text(yaml.safe_dump({
            "rootdir": str(self.root), "database_file": "data/lab.sqlite3",
            "vlm": [{"name": "fake-vlm", "protocol": "openai",
                     "thinking_field": "chat_template_kwargs",
                     "endpoint": "http://127.0.0.1:9/v1", "model": "fake"}]}), encoding="utf-8")
        directory = self.root / "data" / "embeddings" / "rules"
        directory.mkdir(parents=True)
        (directory / clusters.CLUSTERS_FILE).write_text(json.dumps({
            "built_at": "2026-09-26T12:00:00+0300", "input_hash": "h",
            "spaces": {"combined": {"clusters": [
                {"id": "c%03d" % (i + 1), "key": r["key"], "slugs": r["slugs"]}
                for i, r in enumerate(rules) if not r.get("old")]}}}), encoding="utf-8")
        (directory / clusters.RULES_FILE).write_text(json.dumps({
            "cards": {A: {"description": {"texts": [{"text": "LABEL A"}]}}},
            "spaces": {"label": {r["key"]: r for r in rules}}}), encoding="utf-8")


class Inner:
    def __init__(self, answer):
        self.answer = answer
        self.id, self.top_k, self.spec = "base", 10, {"id": "base", "label": "base"}

    def ask(self, path):
        return self.answer


class FakeVlm:
    def __init__(self, text='{"q1": "50/50"}', fail=None):
        self.text, self.fail, self.calls = text, fail, []

    def __call__(self, entry, content, max_tokens, thinking, timeout, schema=None):
        self.calls.append({"content": content, "schema": schema, "thinking": thinking,
                           "max_tokens": max_tokens})
        if self.fail:
            raise self.fail
        return {"text": self.text, "ms": 7, "usage": {}, "finish_reason": "stop",
                "model": "fake", "cached": False}


class BackendTest(unittest.TestCase):
    def make(self, rules, answer, vlm, options=None):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        fixture = Fixture(self.tmp.name, rules)
        opts = cluster_rerank.check_options(dict({"vlm": "fake-vlm"},
                                                 **(options or {})))
        backend = cluster_rerank.ClusterRerank(Inner(answer), opts, "rules",
                                               fixture.config_path, fixture.db_path,
                                               ask_fn=vlm)
        backend.picture = lambda path: (b"png", "label")
        return backend

    def test_the_rule_moves_the_card_up(self):
        trace = {"v": 1, "steps": [{"id": "embed", "start_ms": 0, "ms": 5}]}
        vlm = FakeVlm()
        backend = self.make([sheet_rule()], (cands(A, D, B, C), 100, 200, None, trace), vlm)
        out, ms, status, error, new_trace = backend.ask("photo.jpg")
        self.assertEqual([c["slug"] for c in out], [B, D, A, C])
        explain = out[0]["explain"]
        self.assertEqual(explain["kind"], "cluster_rules")
        self.assertEqual(explain["window"], [A, B, C])
        self.assertTrue(explain["changed"])
        self.assertEqual(explain["base_rank"], 3)
        self.assertEqual(explain["scores"], {A: -1, B: 1, C: -1})
        self.assertEqual(explain["questions"][0]["options"][-2:], ["other", "not visible"])
        self.assertNotIn("explain", out[1])
        self.assertEqual(new_trace["steps"][-1]["id"], "cluster_rules")
        self.assertGreaterEqual(ms, 100)
        self.assertEqual((status, error), (200, None))
        self.assertIsNone(vlm.calls[0]["schema"])
        self.assertFalse(vlm.calls[0]["thinking"])
        self.assertEqual(vlm.calls[0]["content"][0]["type"], "image_url")

    def test_a_verdict_sends_its_schema_and_moves_the_chosen_card(self):
        vlm = FakeVlm('{"wine": "B"}')
        backend = self.make([verdict_rule()], (cands(A, B, D), 100, 200, None, None), vlm)
        out = backend.ask("photo.jpg")[0]
        self.assertEqual([c["slug"] for c in out], [B, A, D])
        self.assertEqual(vlm.calls[0]["schema"]["properties"]["wine"]["enum"], ["A", "B", "unsure"])
        self.assertIn("Name wine-a-12", vlm.calls[0]["content"][1]["text"])
        self.assertIn("LABEL A", vlm.calls[0]["content"][1]["text"])

    def test_unsure_and_a_tie_keep_the_base_order(self):
        backend = self.make([verdict_rule()], (cands(A, B), 100, 200, None, None),
                            FakeVlm('{"wine": "unsure"}'))
        self.assertEqual([c["slug"] for c in backend.ask("p")[0]], [A, B])
        backend = self.make([sheet_rule()], (cands(A, B), 100, 200, None, None),
                            FakeVlm('{"q1": "not visible"}'))
        out = backend.ask("p")[0]
        self.assertEqual([c["slug"] for c in out], [A, B])
        self.assertFalse(out[0]["explain"]["changed"])

    def test_a_vlm_failure_keeps_the_base_order_and_records_the_error(self):
        backend = self.make([sheet_rule()], (cands(A, B), 100, 200, None, None),
                            FakeVlm(fail=RuntimeError("down")))
        out, _, status, error, _ = backend.ask("p")
        self.assertEqual([c["slug"] for c in out], [A, B])
        self.assertIn("down", out[0]["explain"]["error"])
        self.assertEqual((status, error), (200, None))

    def test_no_trigger_calls_no_vlm(self):
        vlm = FakeVlm()
        answer = (cands(D, A, C), 100, 200, None, None)    # rank 1 in no cluster
        backend = self.make([sheet_rule()], answer, vlm)
        self.assertIs(backend.ask("p"), answer)
        answer = (cands(A, D, D + "x", D + "y", D + "z", B), 100, 200, None, None)
        backend = self.make([sheet_rule()], answer, vlm)   # B stands outside the window
        self.assertIs(backend.ask("p"), answer)
        self.assertEqual(vlm.calls, [])

    def test_a_code_hit_and_an_error_stay(self):
        vlm = FakeVlm()
        coded = ([{"slug": A, "score": 1.0, "rank": 1, "code": "4600"},
                  {"slug": B, "score": 1.0, "rank": 2, "code": "4600"}], 5, 200, None, None)
        backend = self.make([sheet_rule()], coded, vlm)
        self.assertIs(backend.ask("p"), coded)
        failed = ([], 5, None, "no view has an input", None)
        backend = self.make([sheet_rule()], failed, vlm)
        self.assertIs(backend.ask("p"), failed)
        self.assertEqual(vlm.calls, [])

    def test_a_rule_of_an_old_cluster_or_with_an_error_is_not_used(self):
        old = dict(sheet_rule(slugs=(A, B)), old=True)
        broken = dict(sheet_rule(slugs=(C, D)), error="HTTP 500")
        vlm = FakeVlm()
        backend = self.make([old, broken], (cands(A, B, C, D), 100, 200, None, None), vlm)
        self.assertEqual(backend.ask("p")[0][0]["slug"], A)
        backend = self.make([old, broken], (cands(C, D, A), 100, 200, None, None), vlm)
        self.assertEqual(backend.ask("p")[0][0]["slug"], C)
        self.assertEqual(vlm.calls, [])
        self.assertEqual(backend.book.counts["error"], 1)

    def test_the_spec_names_the_rules(self):
        backend = self.make([sheet_rule()], (cands(A, B), 100, 200, None, None), FakeVlm())
        self.assertEqual(backend.spec["rerank"]["rules"], "rules")
        self.assertEqual(backend.spec["rerank"]["sheet"], 1)
        self.assertIn("then the cluster re-rank", backend.spec["label"])


class OptionTest(unittest.TestCase):
    def test_the_defaults_and_the_checks(self):
        opts = cluster_rerank.check_options({})
        self.assertEqual((opts["window"], opts["vlm"], opts["thinking"], opts["side"]),
                         (5, "qwen3.5-9b-nvfp4", False, 1536))
        for raw, message in (({"size": 1}, "unknown key size"),
                             ({"window": 1}, "rerank.window"),
                             ({"rules": "gw"}, "rerank.rules was removed"),
                             ({"thinking": "no"}, "rerank.thinking"), ([], "mapping")):
            with self.assertRaises(ConfigError) as caught:
                cluster_rerank.check_options(raw)
            self.assertIn(message, str(caught.exception))

    def test_a_pipeline_takes_the_key_rerank(self):
        with tempfile.TemporaryDirectory() as root:
            lab = standard_lab(root, "http://127.0.0.1:9/v1")
            try:
                path = Path(lab.config_path)
                config = yaml.safe_load(path.read_text(encoding="utf-8"))
                config["pipeline"] = [
                    {"name": "rr", "backend": "embedding", "embedding": "gw",
                     "rerank": {"window": 4}},
                    {"name": "bad", "backend": "embedding", "embedding": "gw",
                     "rerank": {"rules": "missing"}}]
                path.write_text(yaml.safe_dump(config), encoding="utf-8")
                found = pipelines.load(lab.config_path)
                self.assertEqual(found.find("rr").rerank["window"], 4)
                with self.assertRaises(ConfigError) as caught:
                    found.find("bad")
                self.assertIn("rerank.rules was removed", str(caught.exception))
            finally:
                lab.close()


class PromptTest(unittest.TestCase):
    @unittest.skipUnless(MATCHER.exists(), "svoe-vino-matcher is not next to the lab")
    def test_the_prompts_equal_the_prompts_of_the_matcher(self):
        tree = ast.parse(MATCHER.read_text(encoding="utf-8"))
        found = {node.targets[0].id: node.value.value for node in tree.body
                 if isinstance(node, ast.Assign) and len(node.targets) == 1
                 and isinstance(node.targets[0], ast.Name)
                 and isinstance(node.value, ast.Constant)}
        self.assertEqual(cluster_rerank.SHEET_PROMPT, found["SHEET_PROMPT"])
        self.assertEqual(cluster_rerank.VERDICT_PROMPT, found["VERDICT_PROMPT"])


if __name__ == "__main__":
    unittest.main()
