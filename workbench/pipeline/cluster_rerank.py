"""The cluster re-rank of a lab pipeline: the key `rerank` (plan 48).

The re-rank reads the label of the test photo with the rule of a cluster. The rules come
from plan 45: `data/catalog/embeddings/<pipeline embedding>/cluster-rules.json`, the space
`label`, for the clusters of the view `combined` of `clusters.json` of the same
directory. A cluster is a group of catalogue cards that look alike.

How it works (a port of the kind `cluster_rules` of `svoe-vino-matcher`,
`svm/cluster_rules.py` and `svm/pipelines/cluster_rules.py`):

1. The base backend answers the photo.
2. The trigger: the rank-1 card is in a cluster whose rule has the mode `sheet` or
   `verdict`, and at least one other card of that cluster is in the first `window`
   positions (owner message of 2026-09-26T13:10:00+0300, the design of the answer of
   13:04). Else the base answer stays, and no VLM call goes out.
3. The picture: the SAM3 label cut of the photo on white, else the whole photo, scaled UP
   or down to the long side `side`.
4. Mode `sheet`: the VLM answers the valid questions of the rule. An equal answer gives +1
   to a card, a different answer -1, and `not visible` or a null expected answer 0.
   Mode `verdict`: the VLM reads the rule text and names one card, or `unsure`.
5. Only the cards of the cluster inside the window change their order. A card with a
   strictly better score moves up; a tie keeps the base order. Every position keeps its
   score.

The VLM always sees every card of the cluster. A VLM failure, an answer that is not JSON,
or no winner keeps the base order; the failure is recorded, and the photo still gets an
answer. The prompts are sent as they are written here. Do not translate them.

Plan 64: a photo with a shared GTIN gets `first`, the wines of the GTIN. The base backend
puts them first. The trigger then asks that the rank-1 card is a wine of the GTIN, and the
window holds only the wines of the GTIN of that cluster. A card that is not a wine of the
GTIN does not move, and the normal trigger does not run.
"""
import io
import json
import os
import re
import sqlite3
import time
from contextlib import closing

from PIL import Image, ImageOps

import clusters
import embeddings
import label_rules
import vlm_config
from embeddings import ConfigError

KIND = "cluster_rules"
OPTION_KEYS = ("window", "vlm", "thinking", "side", "max_tokens", "timeout_s")
DEFAULTS = {"window": 5, "vlm": "qwen3.5-9b-nvfp4", "thinking": False, "side": 1536,
            "max_tokens": 256, "timeout_s": 180}
OTHER = "other"
UNSURE = "unsure"
NOT_VISIBLE = "not visible"
YEAR = re.compile(r"\b(?:19|20)\d{2}\b")

# The prompts of `svoe-vino-matcher/svm/cluster_rules.py`, verbatim. A test compares them.
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


def check_options(raw):
    """Return the checked key `rerank` of a pipeline, with each default filled in. Raise
    ConfigError."""
    if not isinstance(raw, dict):
        raise ConfigError("rerank MUST be a mapping")
    if "rules" in raw:
        raise ConfigError("rerank.rules was removed; the re-rank uses the pipeline embedding")
    unknown = sorted(set(raw) - set(OPTION_KEYS))
    if unknown:
        raise ConfigError("rerank has the unknown key %s" % ", ".join(unknown))
    out = dict(DEFAULTS)
    out.update({key: value for key, value in raw.items() if value is not None})
    for key, low in (("window", 2), ("side", 64), ("max_tokens", 1)):
        value = out[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < low:
            raise ConfigError("rerank.%s MUST be an integer of at least %d" % (key, low))
    if not isinstance(out["thinking"], bool):
        raise ConfigError("rerank.thinking MUST be true or false")
    if not isinstance(out["vlm"], str) or not out["vlm"].strip():
        raise ConfigError("rerank.vlm MUST name an entry of the key `vlm`")
    timeout = out["timeout_s"]
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ConfigError("rerank.timeout_s MUST be a number above 0")
    return out


# ---------------------------------------------------------------- the answers

def normalize(text):
    return label_rules.normalize(text)


def options_of(question):
    """The options of one question: the expected answers, `other`, `not visible`.
    `other` is listed once, also when a card expects it."""
    seen, out = set(), []
    for value in question["answers"].values():
        n = normalize(value)
        if n is not None and n not in seen:
            seen.add(n)
            out.append(str(value).strip())
    return out + [o for o in (OTHER, NOT_VISIBLE) if normalize(o) not in seen]


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


def reorder(candidates, positions, ranking, explain):
    """Put the cards of `positions` in the order of `ranking`. Every other candidate keeps
    its position, and every position keeps its score. Each card of `positions` carries
    `explain`, with its rank and score before this step."""
    by_slug = {candidates[i]["slug"]: candidates[i] for i in positions}
    out = [dict(c) for c in candidates]
    for pos, slug in zip(positions, ranking):
        card = by_slug[slug]
        out[pos] = {**card, "score": candidates[pos]["score"],
                    "explain": {**explain, "base_rank": card.get("rank", pos + 1),
                                "base_score": card.get("score"),
                                "inner": card.get("explain")}}
    for i, c in enumerate(out, 1):
        c["rank"] = i
    return out


# ---------------------------------------------------------------- the rules

class RuleBook:
    """The rules of the current `combined` clusters of one embedding directory, by slug."""

    def __init__(self, directory):
        artifact = clusters.load_artifact(directory)
        if artifact is None:
            raise ConfigError("%s holds no %s; build the clusters first"
                              % (directory, clusters.CLUSTERS_FILE))
        path = os.path.join(directory, clusters.RULES_FILE)
        data = clusters.read_json(path, default=None)
        if not isinstance(data, dict):
            raise ConfigError("%s holds no rules; run pipeline/build_label_rules.py" % path)
        rules = (data.get("spaces") or {}).get(label_rules.RULE_SPACE) or {}
        self.descriptions = data.get("cards") or {}
        self.by_slug = {}
        view = ((artifact.get("spaces") or {}).get(label_rules.VIEW) or {}).get("clusters") or []
        self.counts = {"clusters": len(view), "sheet": 0, "verdict": 0, "none": 0,
                       "no_rule": 0, "error": 0}
        for cluster in view:
            rule = rules.get(cluster["key"])
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
        self.clusters_file = os.path.join(directory, clusters.CLUSTERS_FILE)
        self.rules_file = path
        self.built_at = artifact.get("built_at")
        self.updated_at = data.get("updated_at")

    def trigger(self, candidates, window, first=None):
        """Return the rule and the window positions of its cards, or (None, []). The
        re-rank acts when the rank-1 card is in a cluster that holds a rule, and at least
        one other card of that cluster is in the window. With `first`, the wines of a
        shared GTIN (plan 64), the rank-1 card MUST be one of them, and the window holds
        only these wines."""
        if not candidates:
            return None, []
        if first is not None and candidates[0]["slug"] not in first:
            return None, []
        rule = self.by_slug.get(candidates[0]["slug"])
        if rule is None:
            return None, []
        members = set(rule["slugs"])
        if first is not None:
            members &= set(first)
        positions = [i for i, c in enumerate(candidates[:window]) if c["slug"] in members]
        return (rule, positions) if len(positions) >= 2 else (None, [])

    def describe(self):
        return {"rules_file": self.rules_file, "clusters_file": self.clusters_file,
                "clusters_built_at": self.built_at, "rules_updated_at": self.updated_at,
                **self.counts}


def catalogue_names(db_path):
    """slug -> the catalogue name, for the verdict prompt."""
    uri = "file:%s?mode=ro" % db_path
    with closing(sqlite3.connect(uri, uri=True, timeout=30)) as conn:
        return {slug: name for slug, name in conn.execute(
            "SELECT wine_slug, name FROM wine_catalog")}


# ---------------------------------------------------------------- the backend

def png_of(image, side):
    """Return the PNG bytes of an image: upright, on white, scaled UP or down to the long
    side `side`."""
    image = ImageOps.exif_transpose(image)
    if image.mode in ("RGBA", "LA", "P"):
        image = image.convert("RGBA")
        white = Image.new("RGB", image.size, "white")
        white.paste(image, mask=image.getchannel("A"))
        image = white
    else:
        image = image.convert("RGB")
    if max(image.size) != side:
        scale = side / max(image.size)
        image = image.resize((max(1, round(image.width * scale)),
                              max(1, round(image.height * scale))), Image.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


class ClusterRerank:
    """A backend of `benchmark.run_benchmark` for a pipeline with the key `rerank`. It
    wraps `inner` (an `embedding_run.EmbeddingBackend`). `ask` returns five values, as the
    inner backend: the step `cluster_rules` goes at the end of the trace when the step
    acts. `ask_fn` and `segmenter` are for the tests."""

    def __init__(self, inner, options, embedding, config_path, db_path, ask_fn=None,
                 segmenter=None):
        self.inner = inner
        self.options = options
        try:
            _, config, _ = embeddings.read_config(config_path)
            self.entry = vlm_config.entry(config, options["vlm"])
        except (embeddings.ConfigError, vlm_config.VlmConfigError) as exc:
            raise ConfigError("rerank: %s" % exc) from exc
        directory = embeddings.entry_dir(db_path, embedding)
        self.book = RuleBook(directory)
        self.names = catalogue_names(db_path)
        self.ask_fn = ask_fn or label_rules.ask
        self.segmenter = segmenter or getattr(inner, "segmenter", None)
        self.id, self.top_k = inner.id, inner.top_k
        # `run_job.build` and `embedding_run.main` read the index state of the run.
        self.catalogue = getattr(inner, "catalogue", None)
        self.spec = dict(inner.spec, rerank=dict(options, rules=embedding, kind=KIND,
                                                **self.book.describe()))
        self.spec["label"] = "%s, then the cluster re-rank" % inner.spec.get("label", self.id)

    def picture(self, path):
        """Return (the PNG bytes, `label` or `photo`): the label cut of the photo, else
        the whole photo. Raise OSError or `derive.Sam3Unavailable`."""
        import derive           # here alone: the SAM3 client
        import embedding_run    # here alone: `embedding_run` imports this module on demand
        image, _ = derive.open_image(path)
        segmenter = self.segmenter or embedding_run.Sam3Once(derive.Sam3Client())
        cut = embedding_run.cuts_of(image, {"label"}, segmenter).get("label")
        if cut is not None:
            return png_of(cut[1], self.options["side"]), "label"
        return png_of(image, self.options["side"]), "photo"

    def rerank(self, path, cands, first=None):
        """Return (the new candidates, the explain record) for a photo that triggers the
        step, or (None, None) for a photo that does not. `first` goes to the trigger: the
        wines of a shared GTIN (plan 64)."""
        size = self.options["window"]
        rule, positions = (self.book.trigger(cands, size) if first is None
                           else self.book.trigger(cands, size, first))
        if rule is None:
            return None, None
        mode = rule["mode"]
        window = [cands[i]["slug"] for i in positions]
        explain = {"kind": KIND, "cluster": rule["key"], "mode": mode, "window": window,
                   "cached": False, "ms": 0, "error": None, "picture": None}
        if mode == "sheet":
            prompt, schema = sheet_prompt(rule), None
            explain["questions"] = [{"id": q["id"], "question": q["question"],
                                     "options": options_of(q)}
                                    for q in rule["questions"] if q.get("valid")]
        else:
            prompt = verdict_prompt(rule, self.names, self.book.descriptions)
            schema = verdict_schema(rule)
            explain.update(rule=rule["rule"], letters=rule["letters"])
        ranking = list(window)
        try:
            png, kind = self.picture(path)
            explain["picture"] = kind
            content = [{"type": "image_url", "image_url": {"url": label_rules.data_url(png)}},
                       {"type": "text", "text": prompt}]
            out = self.ask_fn(self.entry, content, self.options["max_tokens"],
                              self.options["thinking"], self.options["timeout_s"],
                              schema=schema)
            explain.update(cached=out["cached"], ms=out["ms"])
            answer = label_rules.parse_json(out["text"])
            if answer is None or out["finish_reason"] == "length":
                raise label_rules.VlmError("the answer is not a JSON object (finish_reason %s)"
                                           % out["finish_reason"])
        except Exception as exc:  # noqa: BLE001 - a failure keeps the base order
            explain["error"] = "%s: %s" % (type(exc).__name__, exc)
            answer = None
        if answer is not None and mode == "sheet":
            scores = sheet_scores(rule, answer, rule["slugs"])
            explain.update(answers=answer, scores=scores)
            ranking = sorted(window, key=lambda s: (-scores[s], window.index(s)))
        elif answer is not None:
            chosen = verdict_choice(rule, answer)
            explain.update(answer=answer, chosen=chosen)
            if chosen in window:
                ranking = [chosen] + [s for s in window if s != chosen]
        explain["changed"] = ranking[0] != window[0]
        return reorder(cands, positions, ranking, explain), explain

    def ask(self, path, first=None):
        """Return `(candidates, latency_ms, http_status, error, trace)`. `first` goes to
        the inner backend and to the trigger: the wines of a shared GTIN (plan 64)."""
        answer = self.inner.ask(path) if first is None else self.inner.ask(path, first=first)
        cands, ms, status, error = answer[:4]
        trace = answer[4] if len(answer) > 4 else None
        # A photo with no answer, or an answer of the code lookup (plan 42), stays.
        if error or not cands or cands[0].get("code"):
            return answer
        started = time.perf_counter()
        new, explain = self.rerank(path, cands, first)
        if new is None:
            return answer
        step_ms = (time.perf_counter() - started) * 1000
        if isinstance(trace, dict):
            trace = dict(trace, steps=list(trace.get("steps") or []) + [{
                "id": KIND, "start_ms": round(float(ms), 1), "ms": round(step_ms, 1),
                "out": {key: explain.get(key) for key in (
                    "cluster", "mode", "window", "picture", "cached", "changed", "error")}}])
        return new, ms + int(round(step_ms)), status, error, trace
