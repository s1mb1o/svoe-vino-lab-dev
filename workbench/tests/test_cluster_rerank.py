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

MATCHER = Path(__file__).resolve().parents[2] / "matcher" / "rerank.py"
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


def one_sided_rule(slugs=(A, B)):
    slugs = sorted(slugs)
    return {"key": clusters.cluster_key(slugs), "slugs": slugs,
            "letters": {chr(65 + i): s for i, s in enumerate(slugs)}, "mode": "verdict",
            "rule": "If the label shows semi-dry, it is card B; otherwise it is card A.",
            "error": None, "questions": [{
                "id": "q1", "question": "What sugar level is printed?", "kind": "feature",
                "valid": False, "answers": {A: None, B: "semi-dry"}}]}


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

    def test_the_score_schema_requires_every_option(self):
        rule = sheet_rule()
        schema = cluster_rerank.score_schema(rule)
        q1 = schema["properties"]["q1"]
        self.assertEqual(q1["required"], cluster_rerank.options_of(rule["questions"][0]))
        self.assertFalse(q1["additionalProperties"])
        self.assertIn("Do not select a wine or a card", cluster_rerank.score_prompt(rule))

    def test_option_scores_become_candidate_evidence(self):
        rule = sheet_rule()
        answer = {"q1": {"30/70": 5, "50/50": 80, "70/30": 5,
                         "other": 0, "not visible": 10}}
        checked = cluster_rerank.checked_option_scores(rule, answer)
        self.assertEqual(cluster_rerank.evidence_scores(rule, checked, rule["slugs"]),
                         {A: 0.0, B: 0.7, C: 0.0})

    def test_a_one_sided_question_is_scoreable_but_null_stays_neutral(self):
        rule = one_sided_rule()
        self.assertEqual([q["id"] for q in cluster_rerank.scoreable_questions(rule)], ["q1"])
        answer = {"q1": {"semi-dry": 90, "other": 5, "not visible": 5}}
        scores = cluster_rerank.evidence_scores(
            rule, cluster_rerank.checked_option_scores(rule, answer), rule["slugs"])
        self.assertEqual(scores, {A: 0.0, B: 0.85})

    def test_not_visible_removes_positive_evidence(self):
        rule = one_sided_rule()
        answer = {"q1": {"semi-dry": 3, "other": 2, "not visible": 95}}
        scores = cluster_rerank.evidence_scores(
            rule, cluster_rerank.checked_option_scores(rule, answer), rule["slugs"])
        self.assertEqual(scores, {A: 0.0, B: 0.0})

    def test_an_invalid_score_total_is_rejected(self):
        rule = one_sided_rule()
        with self.assertRaisesRegex(cluster_rerank.label_rules.VlmError, "total 90"):
            cluster_rerank.checked_option_scores(
                rule, {"q1": {"semi-dry": 10, "other": 10, "not visible": 70}})

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
    def __init__(self, text=('{"q1":{"30/70":0,"50/50":100,"70/30":0,'
                             '"other":0,"not visible":0}}'), fail=None):
        self.text, self.fail, self.calls = text, fail, []

    def __call__(self, entry, content, max_tokens, thinking, timeout, schema=None,
                 cache_read=True, cache_validator=None):
        self.calls.append({"content": content, "schema": schema, "thinking": thinking,
                           "max_tokens": max_tokens, "cache_read": cache_read})
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
        self.assertEqual(explain["option_scores"]["q1"]["50/50"], 100)
        self.assertEqual(explain["evidence_scores"], {A: 0.0, B: 1.0, C: 0.0})
        self.assertEqual(explain["base_scores"][B], 0.88)
        self.assertEqual(explain["decision_scores"][B], 0.93)
        self.assertEqual(explain["ranking"], [B, A, C])
        self.assertEqual(explain["questions"][0]["options"][-2:], ["other", "not visible"])
        self.assertNotIn("explain", out[1])
        self.assertEqual(new_trace["steps"][-1]["id"], "cluster_rules")
        self.assertGreaterEqual(ms, 100)
        self.assertEqual((status, error), (200, None))
        self.assertEqual(vlm.calls[0]["schema"]["required"], ["q1"])
        self.assertFalse(vlm.calls[0]["thinking"])
        self.assertEqual(vlm.calls[0]["content"][0]["type"], "image_url")
        trace_out = new_trace["steps"][-1]["out"]
        self.assertEqual(trace_out["option_scores"], explain["option_scores"])
        self.assertEqual(trace_out["decision_scores"], explain["decision_scores"])

    def test_a_legacy_verdict_with_no_question_calls_no_vlm(self):
        vlm = FakeVlm('{"wine": "B"}')
        answer = (cands(A, B, D), 100, 200, None, None)
        backend = self.make([verdict_rule()], answer, vlm)
        self.assertIs(backend.ask("photo.jpg"), answer)
        self.assertEqual(vlm.calls, [])

    def test_not_visible_and_a_decision_tie_keep_the_base_order(self):
        backend = self.make([sheet_rule()], (cands(A, B), 100, 200, None, None),
                            FakeVlm('{"q1":{"30/70":0,"50/50":0,"70/30":0,'
                                    '"other":0,"not visible":100}}'))
        out = backend.ask("p")[0]
        self.assertEqual([c["slug"] for c in out], [A, B])
        self.assertFalse(out[0]["explain"]["changed"])

    def test_aratti_missing_text_keeps_the_2024_base_winner(self):
        vlm = FakeVlm('{"q1":{"semi-dry":3,"other":2,"not visible":95}}')
        backend = self.make([one_sided_rule()],
                            (cands(B, A, D), 100, 200, None, None), vlm)
        out = backend.ask("aratti-2024.webp")[0]
        self.assertEqual([candidate["slug"] for candidate in out], [B, A, D])
        explain = out[0]["explain"]
        self.assertEqual(explain["source_mode"], "verdict")
        self.assertEqual(explain["evidence_scores"], {B: 0.0, A: 0.0})
        self.assertFalse(explain["changed"])

    def test_a_visible_one_sided_feature_can_move_its_card(self):
        vlm = FakeVlm('{"q1":{"semi-dry":95,"other":3,"not visible":2}}')
        backend = self.make([one_sided_rule()], (cands(A, B), 100, 200, None, None), vlm)
        out = backend.ask("semi-dry.webp")[0]
        self.assertEqual([candidate["slug"] for candidate in out], [B, A])
        self.assertEqual(out[0]["explain"]["evidence_scores"], {A: 0.0, B: 0.93})

    def test_an_invalid_score_answer_keeps_the_base_order_and_records_the_error(self):
        vlm = FakeVlm('{"q1":{"semi-dry":10,"other":10,"not visible":70}}')
        backend = self.make([one_sided_rule()], (cands(A, B), 100, 200, None, None), vlm)
        out = backend.ask("p")[0]
        self.assertEqual([candidate["slug"] for candidate in out], [A, B])
        self.assertIn("total 90", out[0]["explain"]["error"])
        explain = out[0]["explain"]
        self.assertEqual(len(vlm.calls), 2)
        self.assertFalse(vlm.calls[1]["cache_read"])
        self.assertEqual(len(explain["attempts"]), 2)
        self.assertEqual(explain["raw_option_scores"]["q1"]["semi-dry"], 10)
        self.assertEqual(explain["option_scores"], {})
        self.assertIn("total 90", explain["validation_errors"]["q1"])

    def test_a_retry_corrects_a_zero_sum_without_losing_the_first_answers(self):
        rule = sheet_rule(slugs=(A, B), answers={A: "SAUVIGNON", B: "SAPERAVI"})
        rule["questions"] += [
            {"id": "q2", "question": "Sugar?", "kind": "feature", "valid": False,
             "answers": {A: "dry", B: None}},
            {"id": "q3", "question": "Colour?", "kind": "feature", "valid": False,
             "answers": {A: "white", B: None}}]
        raw = {"q1": {"SAUVIGNON": 0, "SAPERAVI": 100, "other": 0, "not visible": 0},
               "q2": {"dry": 100, "other": 0, "not visible": 0},
               "q3": {"white": 0, "other": 0, "not visible": 0}}
        calls = []

        def ask(*args, **kwargs):
            calls.append((args, kwargs))
            reply = json.loads(json.dumps(raw))
            if len(calls) == 2:
                reply["q3"]["other"] = 100
            self.assertEqual(kwargs["cache_validator"](reply), len(calls) == 2)
            return {"text": json.dumps(reply), "cached": len(calls) == 1,
                    "ms": 11842 if len(calls) == 1 else 100, "finish_reason": "stop"}

        base = [{"slug": A, "score": 0.8608, "rank": 1},
                {"slug": B, "score": 0.8316, "rank": 2}]
        backend = self.make([rule], (base, 10, 200, None, None), ask)
        out = backend.ask("p")[0]
        self.assertEqual([c["slug"] for c in out], [B, A])
        explain = out[0]["explain"]
        self.assertIsNone(explain["error"])
        self.assertEqual(explain["decision_scores"], {A: 0.877467, B: 0.8816})
        self.assertEqual(explain["attempts"][0]["raw_option_scores"], raw)
        self.assertEqual(set(explain["attempts"][0]["validation_errors"]), {"q3"})
        self.assertIn("q3 total 0", calls[1][0][1][-1]["text"])
        self.assertFalse(calls[1][1]["cache_read"])
        self.assertEqual(explain["ms"], 100)  # Cached latency is not charged to the retry.
        self.assertFalse(explain["cached"])

    def test_retry_transport_failure_preserves_the_rejected_response(self):
        vlm = FakeVlm('{"q1":{"semi-dry":0,"other":0,"not visible":0}}')

        def ask(*args, **kwargs):
            if vlm.calls:
                raise RuntimeError("retry unavailable")
            return vlm(*args, **kwargs)

        backend = self.make([one_sided_rule()], (cands(A, B), 10, 200, None, None), ask)
        out = backend.ask("p")[0]
        explain = out[0]["explain"]
        self.assertEqual(out[0]["slug"], A)
        self.assertIn("retry unavailable", explain["error"])
        self.assertEqual(explain["raw_option_scores"]["q1"]["semi-dry"], 0)
        self.assertEqual(len(explain["attempts"]), 2)
        self.assertIn("total 0", explain["attempts"][0]["error"])

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
    @unittest.skipUnless(MATCHER.exists(), "the native matcher is not next to the workbench")
    def test_the_prompts_equal_the_prompts_of_the_matcher(self):
        tree = ast.parse(MATCHER.read_text(encoding="utf-8"))
        found = {node.targets[0].id: node.value.value for node in tree.body
                 if isinstance(node, ast.Assign) and len(node.targets) == 1
                 and isinstance(node.targets[0], ast.Name)
                 and isinstance(node.value, ast.Constant)}
        self.assertEqual(cluster_rerank.SHEET_PROMPT, found["SHEET_PROMPT"])
        self.assertEqual(cluster_rerank.VERDICT_PROMPT, found["VERDICT_PROMPT"])
        self.assertEqual(cluster_rerank.SCORE_PROMPT, found["SCORE_PROMPT"])


if __name__ == "__main__":
    unittest.main()
