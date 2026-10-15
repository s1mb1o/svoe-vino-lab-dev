"""Opt-in wine-term recovery. This module does not change live normalization.

Search the shared vocabulary. Keep raw OCR and correction evidence separate.
Fuzzy evidence can support a match. It cannot establish a contradiction.
"""

from collections import Counter
from functools import lru_cache
import hashlib
from pathlib import Path
import re

import variant_attributes as attrs
import wine_terms

MODES = ("exact", "whitespace", "fuzzy")
METRICS = ("levenshtein", "damerau")
IDENTITY = dict(wine_terms.IDENTITY,
                recovery_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                policy="phrase-recovery-support-only-v1")


def _expand(pattern):
    """Expand the finite grammar used by the shared language patterns.

    Whitespace repeats map to one separator. Other unbounded repeats reject.
    Fail on unsupported syntax instead of silently dropping language aliases.
    """
    position = 0

    def expression():
        nonlocal position
        choices, sequence = [], [""]
        while position < len(pattern) and pattern[position] != ")":
            char = pattern[position]
            position += 1
            if char == "|":
                choices.extend(sequence)
                sequence = [""]
                continue
            if char == "(":
                if pattern[position:position + 2] == "?:":
                    position += 2
                atom = expression()
                if position >= len(pattern) or pattern[position] != ")":
                    raise ValueError("Unclosed language pattern")
                position += 1
            elif char == "\\":
                escaped = pattern[position]
                position += 1
                if escaped != "s":
                    raise ValueError("Unsupported language escape")
                atom = [" "]
            elif char in ".[]{}^$*+?":
                raise ValueError("Unsupported language pattern syntax")
            else:
                atom = [char]
            if position < len(pattern) and pattern[position] in "?*+":
                quantifier = pattern[position]
                position += 1
                if quantifier == "?":
                    atom = [""] + atom
                elif atom != [" "]:
                    raise ValueError("Unbounded language pattern")
            sequence = [left + right for left in sequence for right in atom]
            if len(sequence) > 2048:
                raise ValueError("Language pattern expansion is too large")
        return choices + sequence

    result = expression()
    if position != len(pattern):
        raise ValueError("Unexpected language pattern suffix")
    return result


def _vocabulary():
    entries = []
    for field in ("grapes", "sugar"):
        for term, (_, pattern) in zip(wine_terms.LEXICON[field], wine_terms.rules(field)):
            aliases = {wine_terms.base_text(value) for value in
                       [term["canonical"], *term["ocr_aliases"], *_expand(term["pattern"])]}
            matcher = re.compile(pattern)
            for alias in aliases:
                if not matcher.fullmatch(alias):
                    raise ValueError("Alias does not match its shared language pattern")
            entries.append((field, term["id"], term["canonical"], matcher,
                            tuple(sorted(aliases))))
    return tuple(entries)


VOCABULARY = _vocabulary()
_LOOKALIKES = wine_terms._CONFUSABLES


@lru_cache(maxsize=16384)
def _counts(text):
    return Counter(text)


@lru_cache(maxsize=65536)
def distance(left, right, metric):
    """Return Levenshtein or unrestricted Damerau-Levenshtein distance."""
    if metric not in METRICS:
        raise ValueError("Unknown distance metric")
    if metric == "levenshtein":
        previous = list(range(len(right) + 1))
        for i, a in enumerate(left, 1):
            current = [i]
            for j, b in enumerate(right, 1):
                current.append(min(current[-1] + 1, previous[j] + 1,
                                   previous[j - 1] + (a != b)))
            previous = current
        return previous[-1]
    n, m = len(left), len(right)
    maximum = n + m
    table = [[0] * (m + 2) for _ in range(n + 2)]
    table[0][0] = maximum
    for i in range(n + 1):
        table[i + 1][0], table[i + 1][1] = maximum, i
    for j in range(m + 1):
        table[0][j + 1], table[1][j + 1] = maximum, j
    last = {}
    for i, a in enumerate(left, 1):
        matched = 0
        for j, b in enumerate(right, 1):
            previous_i, previous_j = last.get(b, 0), matched
            cost = a != b
            if not cost:
                matched = j
            table[i + 1][j + 1] = min(table[i][j] + cost, table[i + 1][j] + 1,
                                     table[i][j + 1] + 1,
                                     table[previous_i][previous_j] + i - previous_i - 1
                                     + 1 + j - previous_j - 1)
        last[a] = i
    return table[n + 1][m + 1]


@lru_cache(maxsize=16384)
def _resolve(span, field, mode, metric):
    entries = [entry for entry in VOCABULARY if field is None or entry[0] == field]
    spellings = tuple(dict.fromkeys((span, span.translate(_LOOKALIKES))))
    for spelling in spellings:
        for kind, identity, canonical, matcher, aliases in entries:
            if matcher.fullmatch(spelling):
                return {"field": kind, "identity": identity, "canonical": canonical,
                        "method": "exact", "alias": spelling, "distance": 0,
                        "similarity": 1.0, "runner_up": None}
    if mode == "exact" or any(char.isdigit() for char in span):
        return None
    compact = span.replace(" ", "")
    variants = tuple(dict.fromkeys((compact, compact.translate(_LOOKALIKES))))
    identities = {}
    for kind, identity, canonical, matcher, aliases in entries:
        best = None
        for alias in aliases:
            target = alias.replace(" ", "")
            size = max(len(compact), len(target))
            # Short names require exact letters. Longer names allow bounded edits.
            if min(len(compact), len(target)) / size < .75:
                continue
            for spelling in variants:
                # An edit or transposition cannot add more than one needed letter.
                # This bound also excludes unrelated alphabets before dynamic programming.
                overlap = sum(min(count, _counts(target).get(char, 0))
                              for char, count in _counts(spelling).items())
                if overlap / size < .75:
                    continue
                edits = distance(spelling, target, metric)
                score = 1 - edits / size
                if best is None or score > best[0]:
                    best = score, edits, alias
        if best and best[0] >= .75:
            identities[identity] = (best, kind, canonical)
    ranked = sorted(identities.items(), key=lambda item: (-item[1][0][0], item[0]))
    if not ranked:
        return None
    identity, ((score, edits, alias), kind, canonical) = ranked[0]
    runner = ranked[1] if len(ranked) > 1 else None
    # A pruned alias has similarity below .75. Use a lower bound on the margin.
    margin = score - runner[1][0][0] if runner else score - .75
    target = alias.replace(" ", "")
    limit = 0 if min(len(compact), len(target)) <= 4 else (2 if max(len(compact), len(target)) >= 12 else 1)
    parts = span.split()
    if edits and len(parts) > 1:
        for start in range(len(parts)):
            for end in range(start + 1, len(parts) + 1):
                if end - start == len(parts):
                    continue
                anchor = _resolve(" ".join(parts[start:end]), field, "exact", metric)
                if anchor and (anchor["identity"] == identity or anchor["field"] != kind):
                    return None
    if edits and kind == "sugar":
        source = compact.translate(_LOOKALIKES) if any("а" <= c <= "я" for c in target) else compact
        for qualifier in ("semi", "demi", "extra", "полу", "экстра", "деми"):
            if source.startswith(qualifier) and not target.startswith(qualifier):
                return None
        # A surviving suffix of a qualified class cannot prove its shorter class.
        if len(source) > len(target):
            for other_kind, other_id, _, _, other_aliases in entries:
                if other_kind != "sugar" or other_id == identity:
                    continue
                if any(value.replace(" ", "").endswith(source) and value.replace(" ", "").endswith(target)
                       for value in other_aliases):
                    return None
    if edits == 0 and (not runner or margin > 0):
        method = "whitespace"
    elif mode == "fuzzy" and edits <= limit and score >= .85 and margin >= .10 - 1e-9:
        method = "fuzzy"
    else:
        return None
    return {"field": kind, "identity": identity, "canonical": canonical,
            "method": method, "alias": alias, "distance": edits,
            "similarity": round(score, 6), "margin": round(margin, 6),
            "runner_up": runner[0] if runner else None, "runner_cutoff": .75}


def recover(text, mode="fuzzy", field=None, metric="damerau"):
    """Recover bounded spans. Keep broad terms and unknown text unchanged."""
    if mode not in MODES or metric not in METRICS or field not in (None, "grapes", "sugar"):
        raise ValueError("Invalid recovery option")
    if re.search(r"[,;/\n]", str(text)):
        parts = [recover(part, mode, field, metric) for part in re.split(r"[,;/\n]", str(text))]
        offset, corrections = 0, []
        for part, raw in zip(parts, re.split(r"[,;/\n]", str(text))):
            corrections.extend(dict(change, token_start=change["token_start"] + offset,
                                    token_end=change["token_end"] + offset) for change in part["corrections"])
            offset += len(wine_terms.base_text(raw).split())
        return {"text": " ".join(part["text"] for part in parts), "corrections": corrections}
    tokens = wine_terms.base_text(text).split()
    output, corrections, position = [], [], 0
    while position < len(tokens):
        found = None
        for end in range(min(len(tokens), position + 5), position, -1):
            span = " ".join(tokens[position:end])
            match = _resolve(span, field, mode, metric)
            if match:
                found = match, end, span
                break
        if found:
            match, end, span = found
            output.append(match["canonical"])
            if match["method"] != "exact":
                corrections.append(dict(match, raw=span, token_start=position, token_end=end))
            position = end
        else:
            output.append(tokens[position])
            position += 1
    return {"text": " ".join(output), "corrections": corrections}


def _uncertain_sugar(text):
    tokens = wine_terms.base_text(text).split()
    prefixes = ("extra", "экстра", "semi", "полу", "demi", "деми")
    for position, token in enumerate(tokens):
        term = _resolve(token, "sugar", "exact", "damerau")
        if not term or term["identity"] not in ("brut", "dry", "sweet", "sec"):
            continue
        if position:
            prefix = tokens[position - 1]
            qualified = _resolve(prefix + " " + token, "sugar", "exact", "damerau")
            if not qualified and any(distance(prefix, value, "damerau") <= 1 for value in prefixes):
                return True
        if term["identity"] == "brut" and position + 1 < len(tokens):
            suffix = tokens[position + 1]
            qualified = _resolve(token + " " + suffix, "sugar", "exact", "damerau")
            if not qualified and len(suffix) >= 3 and any(value.startswith(suffix) for value in ("nature", "natyur", "натюр")):
                return True
    return False


def _box(word):
    if word.get("polygon"):
        points = word["polygon"]
        return min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points)
    return word.get("box")


def _same_line(left, right):
    if left.get("line_id") is not None and left.get("line_id") == right.get("line_id"):
        return True
    a, b = _box(left), _box(right)
    if a is None or b is None:
        return False
    height = min(a[3] - a[1], b[3] - b[1])
    return (height > 0 and 0 <= b[0] - a[2] <= 1.5 * height
            and abs((a[1] + a[3] - b[1] - b[3]) / 2) <= .25 * height)


def recover_words(words, mode="fuzzy", metric="damerau", minimum=0):
    """Derive words without changing reader text, confidence or geometry."""
    derived, corrections, position = [], [], 0
    while position < len(words):
        end = position + 1
        while end < min(len(words), position + 5) and _same_line(words[end - 1], words[end]):
            end += 1
        selected = None
        for stop in range(end, position + 1, -1):
            raw = " ".join(word["text"] for word in words[position:stop])
            span = wine_terms.base_text(raw)
            match = _resolve(span, None, mode, metric)
            if match and match["method"] != "exact" and min(word["confidence"] for word in words[position:stop]) >= minimum:
                selected = stop, raw, match
                break
        if selected:
            stop, raw, match = selected
            confidence = min(word["confidence"] for word in words[position:stop])
            derived.append({"text": match["canonical"], "confidence": confidence})
            corrections.append(dict(match, raw=raw, source_words=list(range(position, stop)), confidence=confidence))
            position = stop
        else:
            word = words[position]
            allowed_mode = mode if word["confidence"] >= minimum else "exact"
            result = recover(word["text"], allowed_mode, metric=metric)
            derived.append(dict(word, text=result["text"]))
            corrections.extend(dict(change, source_words=[position], confidence=word["confidence"])
                               for change in result["corrections"])
            position += 1
    blocked = ["sugar"] if _uncertain_sugar(" ".join(word["text"] for word in derived)) else []
    return {"words": derived, "corrections": corrections, "blocked_fields": blocked,
            "mode": mode, "metric": metric, **IDENTITY}


def verify(candidates, words, catalog, options, mode="fuzzy", metric="damerau"):
    """Replay the existing ordering policy with fuzzy conflicts kept unknown."""
    recovery = recover_words(words, mode, metric, options["min_confidence"])
    observed, rejections = attrs.observed(recovery["words"], options["min_confidence"])
    explicit, _ = attrs.observed(words, options["min_confidence"])
    for field in recovery["blocked_fields"]:
        observed[field] = None
        rejections[field] = "uncertain_qualifier"
    soft = {change["field"] for change in recovery["corrections"] if change["method"] == "fuzzy"}
    head = candidates[:options["window"]]
    expected = {row["slug"]: attrs.expected(dict(catalog.get(row["slug"]) or {}, slug=row["slug"])) for row in head}
    active = []
    for field in attrs.FIELDS:
        variants = {tuple(values[field] or ()) for values, _ in expected.values()}
        if field != "line":
            variants.discard(())
        if observed[field] and len(variants) >= 2:
            active.append(field)
    details, matches, conflicts = {}, [], []
    for row in head:
        slug = row["slug"]
        values, complete = expected[slug]
        statuses = {}
        for field in active:
            status = attrs.compare(field, observed[field], values[field], complete)
            if field in soft and status == "conflict":
                status = "conflict" if attrs.compare(field, explicit[field], values[field], complete) == "conflict" else "unknown"
            statuses[field] = status
        details[slug] = statuses
        if "conflict" in statuses.values():
            conflicts.append(slug)
        elif "match" in statuses.values():
            matches.append(slug)
    order = {row["slug"]: (row["slug"] in conflicts,
                            "line" in active and details[row["slug"]].get("line") != "match") for row in head}
    applied = bool(matches and len(set(order.values())) > 1)
    result = sorted(head, key=lambda row: order[row["slug"]]) if applied else list(head)
    result += candidates[options["window"]:]
    result = [dict(row, rank=rank) for rank, row in enumerate(result, 1)]
    return result, {"observed_attributes": observed, "attribute_rejections": rejections,
                    "soft_fields": sorted(soft), "discriminating_fields": active,
                    "candidate_statuses": details, "matches": matches, "conflicts": conflicts,
                    "applied": applied, "recovery": recovery}
