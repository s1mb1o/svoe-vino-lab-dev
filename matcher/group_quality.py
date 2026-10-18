"""Use visible label text to separate visually similar catalogue wines."""

from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
import json
import re
import unicodedata


TRANSLIT = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
                    ("a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "y", "k", "l",
                     "m", "n", "o", "p", "r", "s", "t", "u", "f", "h", "ts", "ch",
                     "sh", "sch", "", "y", "", "e", "yu", "ya")))
STOP = {"wine", "wines", "vino", "vin", "igristoe", "sparkling", "russkiy",
        "vinnyy", "dom", "metode", "methode", "classique", "year", "brut", "bryut",
        "polusladkoe", "polusuhoe", "suhoe", "beloe", "rozovoe", "krasnoe", "blanc",
        "rose", "roze", "sweet", "dry", "semi", "vol", "alk", "obem", "the", "de", "of",
        "collection"}


@lru_cache(maxsize=20000)
def normalized(value):
    """Compare Cyrillic, Latin transliterations, accents, and punctuation."""
    value = unicodedata.normalize("NFKD", value.lower())
    value = "".join(TRANSLIT.get(c, c) for c in value if not unicodedata.combining(c))
    value = re.sub(r"[^a-z0-9]+", " ", value).strip()
    aliases = {"chateau": "shato", "tamagne": "taman", "sauvignon": "sovinon",
               "pinot": "pino", "riesling": "risling", "chardonnay": "shardone",
               "cabernet": "kaberne", "durso": "dyurso", "muscat": "muskat",
               "noir": "nuar", "zbwine": "zb wine", "vayn": "wine",
               "vajn": "wine", "vain": "wine", "vayt": "white",
               "vajt": "white", "vait": "white"}
    return " ".join(aliases.get(word, word) for word in value.split())


@lru_cache(maxsize=20000)
def tokens(value):
    # ZB is a printed brand and a catalogue name. Generic short words stay out.
    return tuple(t for t in normalized(value).split()
                 if (len(t) >= 3 or t == "zb") and not t.isdigit() and t not in STOP)


@lru_cache(maxsize=250000)
def similarity(first, second):
    if first == second:
        return 1.0
    if min(len(first), len(second)) / max(len(first), len(second)) < .55:
        return 0.0
    return SequenceMatcher(None, first, second).ratio()


def token_support(needle, haystack):
    terms, available = tokens(needle), tokens(haystack)
    if not terms or not available:
        return 0.0
    return sum(max(similarity(term, candidate)
                   for candidate in available) for term in terms) / len(terms)


def sugar_class(text):
    value = normalized(text)
    for kind, pattern in (
        ("semi_sweet", r"polusladk\w*|semi\s*sweet|medium\s*sweet|\bmoelleux\b"),
        ("semi_dry", r"polusuh\w*|semi\s*dry|medium\s*dry"),
        ("extra_brut", r"(?:extra|ekstra)\s*(?:brut|bryut)"),
        ("brut", r"\b(?:brut|bryut)\b"),
        ("sweet", r"\bsladk\w*|\bsweet\b|\bdolce\b"),
        ("dry", r"\bsuh\w*|\bdry\b|\bsecco\b"),
    ):
        if re.search(pattern, value):
            return kind
    return None


def color_class(text):
    value = normalized(text)
    for kind, pattern in (("rose", r"\brozov\w*|\broze\b|\brose\b"),
                          ("red", r"\bkrasn\w*|\bred\b|\bruby\b|\brubin\w*"),
                          ("white", r"\bbel\w*|\bwhite\b|\bblanc\b|\bzolot\w*|\bsolom\w*")):
        if re.search(pattern, value):
            return kind
    return None


@dataclass(frozen=True)
class LabelEvidence:
    front_label: bool
    text: str
    brand: str = ""
    line: str = ""
    sugar: str = ""
    color: str = ""
    grapes: str = ""

    @classmethod
    def parse(cls, answer):
        if isinstance(answer, str):
            text = answer.strip()
            if text.startswith("```"):
                text = text[text.find("\n")+1:].rsplit("```", 1)[0].strip()
            answer = json.loads(text)
        if not isinstance(answer, dict) or type(answer.get("front_label")) is not bool:
            raise ValueError("label evidence needs a boolean front_label")
        fields = {}
        for name in ("text", "brand", "line", "sugar", "color", "grapes"):
            value = answer.get(name, "")
            if not isinstance(value, str) or len(value) > 3000:
                raise ValueError("invalid label evidence field: " + name)
            fields[name] = value
        return cls(front_label=answer["front_label"], **fields)


def catalogue_text(slug, card):
    return " ".join(str(v or "") for v in
                    (slug, card.get("name"), card.get("producer"), card.get("grapes")))


def conflict_reason(evidence, slug, card):
    """Reject explicit sugar and colour conflicts, using words actually transcribed."""
    observed_sugar = sugar_class(evidence.text)
    expected_sugar = sugar_class(str(card.get("sugar") or "") + " " + slug)
    if observed_sugar and expected_sugar and observed_sugar != expected_sugar:
        return {"code": "sugar_conflict", "observed": observed_sugar, "expected": expected_sugar}
    observed_color = color_class(evidence.text)
    expected_color = color_class(slug + " " + str(card.get("category") or "") +
                                 " " + str(card.get("color") or ""))
    if observed_color and expected_color and observed_color != expected_color:
        return {"code": "color_conflict", "observed": observed_color, "expected": expected_color}
    return None


def conflicts(evidence, slug, card):
    return conflict_reason(evidence, slug, card) is not None


def _candidate(trace, slug):
    return trace["_candidates"].setdefault(slug, {"slug": slug})


def _reject(trace, slug, code, **values):
    if trace is not None:
        _candidate(trace, slug).update(decision="rejected", reason=code, **values)


def _finish_trace(trace, result):
    if trace is not None:
        returned = {slug: rank for rank, (slug, _) in enumerate(result, 1)}
        candidates = trace.pop("_candidates")
        for slug, entry in candidates.items():
            if entry.get("decision") == "accepted":
                entry["returned_rank"] = returned.get(slug)
                entry["reason"] = "supported" if slug in returned else "outside_return_limit"
        trace["candidates"] = sorted(candidates.values(), key=lambda c: (
            c.get("visual_rank", 100000), c.get("evidence_rank", 100000), c["slug"]))
        trace["returned"] = [{"rank": i, "slug": slug, "score": score}
                             for i, (slug, score) in enumerate(result, 1)]
    return result


def text_candidates(evidence, cards, limit=20, *, trace=None):
    """Retrieve catalogue names independently of the visual candidate list."""
    if not evidence.front_label or not tokens(evidence.brand + " " + evidence.line):
        return []
    ranked = []
    rejected = []
    brand_rejected = 0
    for slug, card in cards.items():
        text = catalogue_text(slug, card)
        brand = token_support(evidence.brand, text)
        if tokens(evidence.brand) and brand < .7:
            brand_rejected += 1
            continue
        reason = conflict_reason(evidence, slug, card)
        if reason:
            if trace is not None:
                score = (.55*brand + .25*token_support(evidence.line, text) +
                         .2*token_support(evidence.text, text))
                rejected.append((slug, score, reason))
            continue
        line = token_support(evidence.line, text)
        words = token_support(evidence.text, text)
        ranked.append((slug, .55*brand + .25*line + .2*words))
    result = sorted(ranked, key=lambda pair: (-pair[1], pair[0]))[:limit]
    if trace is not None:
        # Retain only 20 plausible text candidates vetoed before pool construction.
        # The complete catalogue is counted, not copied into every bottle trace.
        rejected.sort(key=lambda item: (-item[1], item[0]))
        trace["text_retrieval"] = {
            "catalogue_count": len(cards), "brand_rejected_count": brand_rejected,
            "conflict_rejected_count": len(rejected), "eligible_count": len(ranked),
            "returned_count": len(result), "conflict_trace_limit": 20,
            "omitted_conflict_count": max(0, len(rejected)-20)}
        for rank, (slug, score) in enumerate(result, 1):
            _candidate(trace, slug).update(text_rank=rank, text_score=score)
        for slug, score, reason in rejected[:20]:
            _reject(trace, slug, reason["code"], stage="text_retrieval",
                    conflict=reason, text_score=score)
    return result


def evidence_rank(visual, evidence, cards, limit=20, *, trace=None):
    """Build a pool for final verification; cosine stays separate from text support."""
    if not evidence.front_label:
        return []
    scores = dict(visual)
    retrieved = text_candidates(evidence, cards, limit, trace=trace)
    names = set(scores) | {slug for slug, _ in retrieved}
    ranked = []
    for slug in names:
        card = cards[slug]
        text = catalogue_text(slug, card)
        reason = conflict_reason(evidence, slug, card)
        if reason:
            _reject(trace, slug, reason["code"], stage="evidence_pool", conflict=reason)
            continue
        brand = token_support(evidence.brand, text)
        support = (.35*brand + .2*token_support(evidence.line, text) +
                   .15*token_support(evidence.text, text) +
                   .3*token_support(str(card.get("name") or ""), evidence.text))
        ranked.append((slug, scores.get(slug), support))
    result = sorted(ranked, key=lambda item: (-(.7*(item[1] or .65)+.3*item[2]), item[0]))[:limit]
    if trace is not None:
        retained = {slug for slug, _, _ in result}
        trace["evidence_pool"] = {"eligible_count": len(ranked), "limit": limit,
                                  "omitted_count": max(0, len(ranked)-limit)}
        for slug, cosine, support in ranked:
            _candidate(trace, slug).update(cosine=cosine, text_support=support,
                                          pool_score=.7*(cosine or .65)+.3*support)
            if slug not in retained:
                _reject(trace, slug, "outside_evidence_pool", stage="evidence_pool")
        for rank, (slug, _, _) in enumerate(result, 1):
            _candidate(trace, slug)["evidence_rank"] = rank
    return result


def verified_choice(slug, evidence_words, cards):
    """Require visible evidence for a special designation in a chosen name."""
    text = " ".join(evidence_words)
    name = normalized(cards[slug]["name"])
    observed = normalized(text)
    for variants in (("rose", "roze", "rozovoe"), ("kosher", "koshernoe", "koshernyy")):
        if any(re.search(r"\b" + word + r"\b", name) for word in variants):
            if not any(re.search(r"\b" + word + r"\b", observed) for word in variants):
                return False
    expected_sugar = sugar_class(str(cards[slug].get("sugar") or "") + " " + slug)
    observed_sugar = sugar_class(text)
    return not (observed_sugar and expected_sugar and observed_sugar != expected_sugar)


def semantic_rank(visual, evidence, cards, limit=20, *, trace=None):
    """Rank supported identities; a visual lookalike cannot override printed words."""
    if trace is not None:
        trace.clear()
        trace.update(_candidates={}, observed_sugar=sugar_class(evidence.text),
                     observed_color=color_class(evidence.text), return_limit=limit)
        for rank, (slug, cosine) in enumerate(visual, 1):
            _candidate(trace, slug).update(visual_rank=rank, cosine=cosine)
    if not evidence.front_label:
        if trace is not None:
            trace["reason"] = "no_front_label"
            for slug, _ in visual:
                _reject(trace, slug, "no_front_label", stage="label")
        return _finish_trace(trace, [])
    producer_known = any(token_support(evidence.brand, producer) >= .85
                         for producer in {str(card.get('producer') or '')
                                          for card in cards.values()})
    ranked = evidence_rank(visual, evidence, cards, limit=60, trace=trace)
    vocabulary = {word for slug, score, _ in ranked
                  if not tokens(evidence.brand) or
                  token_support(evidence.brand, catalogue_text(slug, cards[slug])) >= .7
                  for word in tokens(str(cards[slug].get("name") or ""))}
    observed = set(tokens(evidence.text))
    anchors = {word for word in observed if len(word) >= 4 and
               any(similarity(word, target) >= .9 for target in vocabulary)}
    brand_words = set(tokens(evidence.brand))
    identity_words = anchors - brand_words
    printed_grape = (tokens(evidence.grapes) and
                     token_support(evidence.grapes, evidence.text) >= .85)
    if trace is not None:
        trace.update(producer_known=producer_known, anchors=sorted(anchors),
                     identity_words=sorted(identity_words), printed_grape=bool(printed_grape))
    if not sugar_class(evidence.text) and not identity_words and not printed_grape:
        if trace is not None:
            trace["reason"] = "insufficient_identity_evidence"
            for slug, _, _ in ranked:
                _reject(trace, slug, "insufficient_identity_evidence", stage="identity")
        return _finish_trace(trace, [])
    results = []
    for slug, cosine, support in ranked:
        if cosine is None or cosine < .72:
            _reject(trace, slug, "missing_visual_score" if cosine is None else
                    "visual_score_below_threshold", stage="semantic", threshold=.72)
            continue
        card = cards[slug]
        text = catalogue_text(slug, card)
        producer_support = token_support(evidence.brand, str(card.get('producer') or ''))
        if producer_known and producer_support < .7:
            _reject(trace, slug, "known_producer_mismatch", stage="semantic",
                    producer_support=producer_support, threshold=.7)
            continue
        # A one-word named range cannot be replaced with another range.
        if (len(normalized(evidence.line).split()) == 1 and
                any(len(word) >= 5 for word in tokens(evidence.line))
                and token_support(evidence.line, text) < .7):
            _reject(trace, slug, "named_range_mismatch", stage="semantic",
                    line_support=token_support(evidence.line, text), threshold=.7)
            continue
        observed_designations = set(normalized(evidence.text).split()) & {'reserve', 'rezerv'}
        if observed_designations and not (set(normalized(text).split()) & {'reserve', 'rezerv'}):
            _reject(trace, slug, "missing_reserve_designation", stage="semantic",
                    observed_designations=sorted(observed_designations))
            continue
        if not verified_choice(slug, [evidence.text], cards):
            _reject(trace, slug, "unverified_designation", stage="semantic")
            continue
        if any(token_support(word, text) < .85 for word in anchors):
            _reject(trace, slug, "anchor_mismatch", stage="semantic", threshold=.85,
                    unsupported_anchors=sorted(word for word in anchors
                                              if token_support(word, text) < .85))
            continue
        name = str(card.get("name") or "")
        varietal_name = [word for word in tokens(name)
                         if token_support(word, evidence.brand) < .8]
        generic_line = (not normalized(evidence.line) or
                        ((color_class(evidence.line) or sugar_class(evidence.line)) and
                         not tokens(evidence.line)))
        if (generic_line and not identity_words and not printed_grape and
                varietal_name and token_support(name, str(card.get('producer') or '')) < .9):
            # Colour and sugar alone do not select a named range or grape SKU.
            _reject(trace, slug, "unprinted_named_range", stage="semantic",
                    varietal_name=varietal_name)
            continue
        grape_terms = tokens(str(card.get('grapes') or ''))
        if (varietal_name and
                all(any(similarity(word, grape) >= .85 or
                        (len(grape) >= 6 and word.startswith(grape))
                        for grape in grape_terms)
                    for word in varietal_name) and
                any(token_support(word, evidence.text) < .8 for word in varietal_name)):
            # A generic white wine cannot establish a particular varietal SKU.
            _reject(trace, slug, "unprinted_varietal", stage="semantic", threshold=.8,
                    unsupported_varietal_words=[word for word in varietal_name
                                               if token_support(word, evidence.text) < .8])
            continue
        coverage = token_support(name, evidence.text) if tokens(name) else 1.0
        brand = token_support(evidence.brand, text)
        brand_minimum = min((token_support(word, text) for word in tokens(evidence.brand)),
                            default=0.0)
        if len(tokens(evidence.brand)) > 1 and brand_minimum < .7:
            # The model can transliterate its brand field differently from its
            # Cyrillic transcription. Require the missing term in the printed text.
            available = set(tokens(text))
            choices = [[target for target in available
                        if similarity(word, target) >= .7 or
                        (similarity(word, target) >= .55 and
                         token_support(target, evidence.text) >= .8)]
                       for word in tokens(evidence.brand)]

            def distinct_assignment(remaining, used):
                if not remaining:
                    return True
                return any(distinct_assignment(remaining[1:], used | {target})
                           for target in remaining[0] if target not in used)

            if not distinct_assignment(sorted(choices, key=len), set()):
                _reject(trace, slug, "distinct_brand_assignment_failed", stage="semantic",
                        brand_support=brand, brand_minimum=brand_minimum,
                        brand_choices={word: sorted(options) for word, options
                                       in zip(tokens(evidence.brand), choices)})
                continue
        name_without_brand = (not tokens(evidence.brand) and len(tokens(name)) >= 2 and
                              cosine >= .85 and coverage >= .95)
        if brand < .7 and not (cosine >= .88 and coverage >= .7) and not name_without_brand:
            _reject(trace, slug, "insufficient_brand_support", stage="semantic",
                    brand_support=brand, name_coverage=coverage,
                    brand_threshold=.7, alternative_cosine_threshold=.88,
                    alternative_coverage_threshold=.7)
            continue
        # A named range that is not on the front label is weaker than the plain wine.
        quality = .55*cosine + .25*support + .2*coverage
        results.append((slug, cosine, quality))
        if trace is not None:
            _candidate(trace, slug).update(decision="accepted", stage="semantic",
                                          brand_support=brand, brand_minimum=brand_minimum,
                                          name_coverage=coverage, quality=quality)
    results.sort(key=lambda item: (-item[2], item[0]))
    if trace is not None:
        trace["reason"] = "supported" if results else "no_supported_catalogue_identity"
        trace["supported_count"] = len(results)
    return _finish_trace(trace, [(slug, quality) for slug, _, quality in results[:limit]])


def needs_label_read(visual, evidence, cards):
    """Read a focused label when a missing attribute separates likely candidates."""
    if not evidence.front_label:
        return False
    # A missing or damaged brand is itself a reason to read more pixels.
    # Requiring a brand match here prevents the second read from repairing it.
    if not semantic_rank(visual, evidence, cards, limit=2):
        return any(score >= .78 for _, score in visual[:15])
    plausible = [(slug, score) for slug, score in visual[:15]
                 if score >= .78 and token_support(evidence.brand, catalogue_text(slug, cards[slug])) >= .7]
    if not plausible:
        return False
    if not sugar_class(evidence.text):
        kinds = {sugar_class(str(cards[slug].get("sugar") or "") + " " + slug)
                 for slug, _ in plausible}
        if len(kinds - {None}) > 1:
            return True
    if not color_class(evidence.text):
        colors = {color_class(slug + " " + str(cards[slug].get("category") or ""))
                  for slug, _ in plausible}
        if len(colors - {None}) > 1:
            return True
    return False


def merge_label_reads(primary, detail):
    """The detail crop has more pixels per letter and supplies missing attributes."""
    if not detail.front_label or not tokens(detail.brand + " " + detail.line + " " + detail.text):
        return primary
    printed_grape = tokens(detail.grapes) and token_support(detail.grapes, detail.text) >= .85
    if not (sugar_class(detail.text) or color_class(detail.text) or printed_grape):
        return primary
    return LabelEvidence(True, detail.text, detail.brand or primary.brand,
                         detail.line or primary.line, detail.sugar,
                         detail.color, detail.grapes)
