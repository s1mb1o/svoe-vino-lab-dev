"""The cluster re-rank of the backend `cascade`.

This module ports `workbench/pipeline/cluster_rerank.py` (plan 48 of the workbench) and
the helpers `normalize`, `NOT_VISIBLE`, `parse_json`, and the request payload of `ask` of
`workbench/pipeline/label_rules.py`. The rules come from `clusters.json` (the view
`combined`) and `cluster-rules.json` (the space `label`) of one embedding directory of
the catalogue copy.

The trigger: the rank-1 wine is in a cluster whose rule has the mode `sheet` or
`verdict`, and at least one other wine of that cluster is in the first `window`
positions. The VLM reads the label picture with the rule. Only the wines of the cluster
inside the window change their order, and every position keeps its score, so the scores
stay sorted. The prompts are sent as they are written here. Do not translate them.
`workbench/tests/test_matcher_parity.py` compares them with the lab prompts.
"""

import base64
import json
from pathlib import Path
import re


CLUSTERS_FILE = "clusters.json"
RULES_FILE = "cluster-rules.json"
VIEW = "combined"
RULE_SPACE = "label"
OTHER = "other"
UNSURE = "unsure"
NOT_VISIBLE_ANSWER = "not visible"
YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
# The answers that state no value (`workbench/pipeline/label_rules.py`).
NOT_VISIBLE = {"", "null", "none", "n/a", "not visible", "not shown", "unreadable",
               "unknown", "не видно"}

SHEET_PROMPT = (
    "This is a photo of a wine bottle, or of its label. Answer each question by "
    "looking at the label only.\n"
    "If the photo does not show the answer, or you cannot read it, answer "
    "\"not visible\". Do not guess.\n"
    "Choose each answer from its options.\n\n"
    "%(questions)s\n\n"
    "Answer with one JSON object that maps each question id to its answer, for "
    "example {\"q1\": \"...\"}."
)

VERDICT_PROMPT = (
    "This is a photo of a wine bottle, or of its label. It shows one of these wines:\n\n"
    "%(cards)s\n\n"
    "Rule: %(rule)s\n\n"
    "Which wine is it? Answer with one JSON object: {\"wine\": \"<letter>\"}. Answer "
    "{\"wine\": \"unsure\"} when the photo does not show the feature that tells the "
    "wines apart."
)


class RuleError(ValueError):
    """The rule files of the re-rank are missing or not valid."""


def normalize(text):
    """The compared form of an answer, or None for an answer that states no value.

    Lower case, `ё` as `е`, no quotes or end punctuation, no space around `/`, `-`,
    `:` and `%`. `30 / 70` gives `30/70`."""
    if text is None:
        return None
    t = str(text).strip().lower().replace("ё", "е")
    t = t.strip(" \t\n\"'«»`.,;:!?()[]")
    t = re.sub(r"\s*([/\-:%])\s*", r"\1", t)
    t = re.sub(r"\s+", " ", t)
    return None if t in NOT_VISIBLE else t


def parse_json(text):
    """The JSON object of an answer, or None."""
    try:
        value = json.loads(text)
    except (TypeError, ValueError):
        match = re.search(r"\{.*\}", text or "", re.S)
        if not match:
            return None
        try:
            value = json.loads(match.group(0))
        except ValueError:
            return None
    return value if isinstance(value, dict) else None


def options_of(question):
    """The options of one question: the expected answers, `other`, `not visible`.
    `other` is listed once, also when a card expects it."""
    seen, out = set(), []
    for value in question["answers"].values():
        n = normalize(value)
        if n is not None and n not in seen:
            seen.add(n)
            out.append(str(value).strip())
    return out + [o for o in (OTHER, NOT_VISIBLE_ANSWER) if normalize(o) not in seen]


def compared_answer(question, got):
    """The normalized answer that `sheet_scores` compares with the expected answers. For
    a question of kind `vintage`, an answer that holds one year counts as that year when
    a card expects it, and as `other` when no card expects it."""
    if got is None or question.get("kind") != "vintage":
        return got
    years = set(YEAR.findall(got))
    if len(years) != 1:
        return got
    year = years.pop()
    expected = {normalize(v) for v in question["answers"].values()}
    return year if year in expected else OTHER


def sheet_prompt(rule):
    lines = []
    for q in rule["questions"]:
        if not q.get("valid"):
            continue
        opts = ", ".join(json.dumps(o, ensure_ascii=False) for o in options_of(q))
        lines.append("%s: %s\nOptions: %s" % (q["id"], q["question"], opts))
    return SHEET_PROMPT % {"questions": "\n\n".join(lines)}


def _short(desc):
    """A short text of a label description for the verdict prompt."""
    if not isinstance(desc, dict):
        return "no description"
    parts = []
    texts = [str(t.get("text")) for t in desc.get("texts") or [] if isinstance(t, dict)]
    if texts:
        parts.append("texts " + ", ".join(json.dumps(t, ensure_ascii=False) for t in texts[:12]))
    if desc.get("vintage"):
        parts.append("vintage %s" % desc["vintage"])
    for key in ("colours", "design", "marks"):
        value = desc.get(key)
        if value:
            parts.append("%s %s" % (key, value if isinstance(value, str)
                                    else json.dumps(value, ensure_ascii=False)))
    return "; ".join(parts)[:900]


def verdict_prompt(rule, names, descriptions):
    cards = []
    for letter, slug in rule["letters"].items():
        cards.append("%s: name %s; label: %s" % (
            letter, json.dumps(names.get(slug) or slug, ensure_ascii=False),
            _short((descriptions.get(slug) or {}).get("description"))))
    return VERDICT_PROMPT % {"cards": "\n".join(cards), "rule": rule["rule"]}


def verdict_schema(rule):
    """The JSON schema of a verdict: one letter of the rule, or `unsure`."""
    return {"type": "object", "additionalProperties": False,
            "properties": {"wine": {"type": "string",
                                    "enum": list(rule["letters"]) + [UNSURE]}},
            "required": ["wine"]}


def sheet_scores(rule, answers, slugs):
    """The score of each card: +1 for an equal answer, -1 for a different one. A null
    expected answer, and an answer that states no value, give 0."""
    scores = {s: 0 for s in slugs}
    for q in rule["questions"]:
        if not q.get("valid"):
            continue
        got = normalize(answers.get(q["id"])) if isinstance(answers, dict) else None
        got = compared_answer(q, got)
        if got is None:
            continue
        for s in slugs:
            want = normalize(q["answers"].get(s))
            if want is not None:
                scores[s] += 1 if got == want else -1
    return scores


def verdict_choice(rule, answer):
    """The slug that the verdict names, or None."""
    if not isinstance(answer, dict):
        return None
    letter = str(answer.get("wine") or "").strip().upper().strip(".\"' ")
    return rule["letters"].get(letter)


def window_ranking(rule, answer, window):
    """Return the new order of the window slugs for one VLM answer. A tie keeps the
    base order; a verdict moves the chosen wine to the front."""
    if rule["mode"] == "sheet":
        scores = sheet_scores(rule, answer, rule["slugs"])
        return sorted(window, key=lambda slug: (-scores[slug], window.index(slug)))
    chosen = verdict_choice(rule, answer)
    if chosen in window:
        return [chosen] + [slug for slug in window if slug != chosen]
    return list(window)


def reorder(pairs, positions, ranking):
    """Put the wines of `positions` in the order of `ranking`. Every other wine keeps
    its position, and every position keeps its score."""
    out = list(pairs)
    for position, slug in zip(positions, ranking):
        out[position] = (slug, pairs[position][1])
    return out


def data_url(png):
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def payload(rule, picture, model, max_tokens, names, descriptions):
    """Return the chat request of one re-rank: JSON mode (a JSON schema for a verdict),
    temperature 0, and thinking off in `chat_template_kwargs`."""
    if rule["mode"] == "sheet":
        prompt, schema = sheet_prompt(rule), None
    else:
        prompt, schema = verdict_prompt(rule, names, descriptions), verdict_schema(rule)
    response_format = {"type": "json_object"} if schema is None else {
        "type": "json_schema", "json_schema": {"name": "answer", "schema": schema}}
    content = [{"type": "image_url", "image_url": {"url": data_url(picture)}},
               {"type": "text", "text": prompt}]
    return {"model": model, "temperature": 0, "max_tokens": max_tokens,
            "response_format": response_format,
            "messages": [{"role": "user", "content": content}],
            "chat_template_kwargs": {"enable_thinking": False}}


def answer_of(body):
    """Return the JSON answer of one chat body. Raise ValueError for a body with no
    answer, for an answer that is not a JSON object, and for a cut answer."""
    try:
        choice = body["choices"][0]
        text = (choice["message"].get("content") or "").strip()
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        raise ValueError("the chat body holds no answer") from exc
    answer = parse_json(text)
    if answer is None or choice.get("finish_reason") == "length":
        raise ValueError("the answer is not a JSON object (finish_reason %s)"
                         % choice.get("finish_reason"))
    return answer


def _read_json(path):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuleError("cannot read %s: %s" % (path, exc)) from exc
    if not isinstance(value, dict):
        raise RuleError("%s MUST hold one JSON object" % path)
    return value


class RuleBook:
    """The rules of the `combined` clusters of one embedding directory, by slug."""

    def __init__(self, clusters, rules):
        spaces = rules.get("spaces") if isinstance(rules.get("spaces"), dict) else {}
        by_key = spaces.get(RULE_SPACE) if isinstance(spaces.get(RULE_SPACE), dict) else {}
        self.descriptions = rules.get("cards") if isinstance(rules.get("cards"), dict) else {}
        view = ((clusters.get("spaces") or {}).get(VIEW) or {}).get("clusters") or []
        self.by_slug = {}
        self.counts = {"clusters": len(view), "sheet": 0, "verdict": 0, "none": 0,
                       "no_rule": 0, "error": 0}
        for cluster in view:
            rule = by_key.get(cluster.get("key")) if isinstance(cluster, dict) else None
            if rule is None:
                self.counts["no_rule"] += 1
                continue
            if rule.get("error"):
                self.counts["error"] += 1
                continue
            mode = rule.get("mode") or "none"
            self.counts[mode] = self.counts.get(mode, 0) + 1
            if mode in ("sheet", "verdict"):
                for slug in rule["slugs"]:
                    self.by_slug[slug] = rule

    @classmethod
    def load(cls, directory):
        """Read the two rule files of one embedding directory. Raise RuleError."""
        root = Path(directory)
        return cls(_read_json(root / CLUSTERS_FILE), _read_json(root / RULES_FILE))

    def trigger(self, pairs, window, first=None):
        """Return the rule and the window positions of its wines, or (None, []).

        `pairs` is the ranked `(slug, score)` list. With `first`, the wines of a shared
        GTIN (plan 64 of the workbench), the rank-1 wine MUST be one of them, and the
        window holds only these wines."""
        if not pairs:
            return None, []
        if first is not None and pairs[0][0] not in first:
            return None, []
        rule = self.by_slug.get(pairs[0][0])
        if rule is None:
            return None, []
        members = set(rule["slugs"])
        if first is not None:
            members &= set(first)
        positions = [i for i, (slug, _) in enumerate(pairs[:window]) if slug in members]
        return (rule, positions) if len(positions) >= 2 else (None, [])
