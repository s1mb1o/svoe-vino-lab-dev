"""Selective trigger and structured text ranking. This module reads no truth labels."""

from dataclasses import dataclass, field
from functools import lru_cache
import re
from time import perf_counter

from . import ocr, rerank
from .ocr import OCRConfig
from .codes import is_unique


@dataclass(frozen=True)
class SelectiveOCRConfig:
    enabled: bool = True
    score_threshold: float = 0.70
    margin_threshold: float = 0.03
    pool: int = 50
    input: str = "full"
    side: int = 1536
    timeout_seconds: float = 2.0
    alpha: float = 0.10
    conflict_penalty: float = 0.03
    ocr: OCRConfig = field(default_factory=OCRConfig)


def config(raw):
    if not isinstance(raw, dict):
        raise ValueError("selective_ocr MUST be a map")
    unknown = set(raw) - set(SelectiveOCRConfig.__dataclass_fields__)
    if unknown:
        raise ValueError("selective_ocr has unknown keys: %s" % ", ".join(sorted(unknown)))
    data = dict(raw)
    data["ocr"] = ocr.config(data.get("ocr", {}))
    value = SelectiveOCRConfig(**data)
    if not isinstance(value.enabled, bool):
        raise ValueError("selective_ocr.enabled MUST be a boolean")
    ocr.number(value.score_threshold, "score_threshold", -1, 1)
    ocr.number(value.margin_threshold, "margin_threshold", 0, 2)
    ocr.integer(value.pool, "pool", 1, 500)
    ocr.integer(value.side, "side", 64, 4096)
    ocr.number(value.timeout_seconds, "timeout_seconds", 0.01, 60)
    ocr.number(value.alpha, "alpha", 0, 1)
    ocr.number(value.conflict_penalty, "conflict_penalty", 0, 1)
    if value.input not in ("full", "label"):
        raise ValueError("selective_ocr.input MUST be full or label")
    return value


def evidence(run, answer):
    if answer is None:
        return "error"
    if answer.code is not None and is_unique(answer.code):
        return "unique-code"
    if answer.rerank is None:
        return "error" if any(s["id"].startswith("vlm:") and s.get("status") == "error"
                              for s in run.stages) else "untriggered"
    rule = run.cascade.rules.by_slug[answer.pairs[0][0]]
    response = run.vlm.get(answer.rerank["cluster"])
    parsed = response if isinstance(response, dict) else rerank.parse_json(response)
    if not parsed:
        return "unsure"
    if rule["mode"] == "verdict":
        chosen = rerank.verdict_choice(rule, parsed)
        return "supported" if chosen == answer.pairs[0][0] else "contradicted" if chosen else "unsure"
    agreements = 0
    for question in rule.get("questions", []):
        if not question.get("valid"):
            continue
        expected = rerank.normalize((question.get("answers") or {}).get(answer.pairs[0][0]))
        actual = rerank.compared_answer(question, rerank.normalize(parsed.get(question["id"])))
        if expected is None or actual is None:
            continue
        if actual != expected:
            return "contradicted"
        agreements += 1
    return "supported" if agreements else "unsure"


def trigger(pairs, verification, settings):
    if not pairs or verification in ("unique-code", "supported"):
        return False
    margin = pairs[0][1] - pairs[1][1] if len(pairs) > 1 else pairs[0][1]
    return (pairs[0][1] < settings.score_threshold or margin < settings.margin_threshold
            or verification in ("unsure", "contradicted", "error"))


CYRILLIC = str.maketrans({
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "i", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya"})
YEAR = re.compile(r"^(?:19|20)\d{2}$")
GROUPS = {
    "colour": {"red": ("red", "krasnoe", "krasnyi"), "white": ("white", "beloe", "belyi"),
               "rose": ("rose", "roze", "rozovoe", "rozovyi"),
               "orange": ("orange", "oranzhevoe", "oranzhevyi")},
    "sugar": {"brut": ("brut", "bryut"), "extra_brut": ("extra brut", "ekstra bryut"),
              "dry": ("dry", "suhoe", "sukhoi"), "semi_dry": ("semi dry", "polusuhoe", "polusukhoi"),
              "semi_sweet": ("semi sweet", "polusladkoe"), "sweet": ("sweet", "sladkoe")}}


def tokens(value):
    return [t for t in re.findall(r"[a-z0-9]+", str(value or "").lower().translate(CYRILLIC))
            if 2 <= len(t) <= 128]


@lru_cache(maxsize=8192)
def similarity(a, b):
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    previous = list(range(len(b) + 1))
    for i, left in enumerate(a, 1):
        current = [i]
        for j, right in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[-1] + 1,
                               previous[j - 1] + (left != right)))
        previous = current
    return 1 - previous[-1] / max(len(a), len(b))


def coverage(wanted, observed, threshold=0.72, deadline=None):
    if not wanted or not observed:
        return 0.0
    weights = [min(12, max(2, len(t))) for t in wanted]
    scores = []
    for token in wanted:
        best = 0.0
        for i, other in enumerate(observed):
            if deadline is not None and i % 16 == 0 and perf_counter() >= deadline:
                raise TimeoutError("OCR scoring deadline expired")
            # The length ratio is an upper bound for Levenshtein similarity.
            if min(len(token), len(other)) / max(len(token), len(other)) >= threshold:
                best = max(best, similarity(token, other))
        scores.append(best)
    return sum(w * s for w, s in zip(weights, scores) if s >= threshold) / sum(weights)


def attributes(values):
    text = " ".join(values)
    found = {}
    for group, choices in GROUPS.items():
        for value, spellings in choices.items():
            if any(spelling in text for spelling in spellings):
                found.setdefault(group, set()).add(value)
    years = {value for value in values if YEAR.match(value)}
    if years:
        found["year"] = years
    return found


def rank(pairs, text, cards, settings, deadline=None):
    """Return adjusted pairs and auditable metadata for the bounded visual pool."""
    observed = list(dict.fromkeys(tokens(text)))[:512]
    seen = attributes(observed)
    rows = []
    for slug, visual in pairs:
        if deadline is not None and perf_counter() >= deadline:
            raise TimeoutError("OCR scoring deadline expired")
        card = cards.get(slug)
        if card is None:
            continue
        candidate_tokens = tokens(" ".join(str(card.get(k) or "")
                                           for k in ("name", "category", "color")) + " " + slug)
        fields = {k: coverage(tokens(card.get(k)), observed, deadline=deadline)
                  for k in ("name", "producer", "grapes")}
        fields["category"] = coverage(tokens(str(card.get("category") or "") + " "
                                              + str(card.get("color") or "")), observed, deadline=deadline)
        fields["vintage"] = coverage([t for t in candidate_tokens if YEAR.match(t)], observed, 0.99, deadline)
        score = sum(w * fields[k] for k, w in (("name", .40), ("producer", .30),
                    ("grapes", .15), ("category", .10), ("vintage", .05)))
        expected = attributes(candidate_tokens)
        conflicts = sum(k in expected and not values.intersection(expected[k])
                        for k, values in seen.items())
        adjusted = round(visual + settings.alpha * score - settings.conflict_penalty * conflicts, 4)
        rows.append({"slug": slug, "score": adjusted, "visual_score": visual,
                     "ocr_score": round(score, 4), "conflicts": conflicts,
                     "fields": {k: round(v, 4) for k, v in fields.items()}})
    rows.sort(key=lambda r: (-r["score"], r["slug"]))
    return [(r["slug"], r["score"]) for r in rows], rows
