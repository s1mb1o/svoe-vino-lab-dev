"""Shared, bounded wine-term normalization for any OCR reader and catalogue text.

Only a complete dictionary term may be corrected. Unknown tokens, partial grape
families and distinct sugar classes are never guessed through edit distance.
Raw reader results and their confidence/polygons remain outside this module.
"""
import hashlib
import json
from pathlib import Path
import re
import unicodedata

_DICTIONARY = Path(__file__).with_suffix(".json")
_DATA = _DICTIONARY.read_bytes()
LEXICON = json.loads(_DATA)
IDENTITY = {"schema": LEXICON["schema"],
            "dictionary_sha256": hashlib.sha256(_DATA).hexdigest(),
            "algorithm_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
GRAPE_PARENTS = LEXICON["grape_parents"]

# Apply visual lookalikes only if the whole result matches a known wine term.
_CONFUSABLES = str.maketrans({"a": "а", "b": "в", "c": "с", "e": "е",
    "h": "н", "k": "к", "m": "м", "o": "о", "p": "р", "t": "т",
    "x": "х", "y": "у", "0": "о", "8": "в"})


def base_text(text):
    """Normalize spelling/separators, retaining numbers and Cyrillic й."""
    value = unicodedata.normalize("NFC", str(text or "").lower().replace("ё", "е"))
    value = "".join(c if "а" <= c <= "я" else unicodedata.normalize("NFKD", c)
                    for c in value)
    value = "".join(c for c in value if not unicodedata.combining(c))
    return " ".join(re.findall(r"[a-zа-я0-9]+", value))


def rules(field):
    """One shared source for canonical terms, language aliases and OCR aliases."""
    answer = []
    for term in LEXICON[field]:
        aliases = [base_text(term["canonical"])] + [base_text(v) for v in term["ocr_aliases"]]
        pattern = "|".join([term["pattern"]] + [re.escape(v).replace(r"\ ", r"\s+") for v in aliases])
        answer.append((term["id"], pattern))
    return tuple(answer)


SUGAR = rules("sugar")
GRAPES = rules("grapes")
_MATCHERS = [(re.compile(pattern), term["canonical"])
             for field in ("grapes", "sugar")
             for term, (_, pattern) in zip(LEXICON[field], rules(field))]


def normalize(text):
    """Return canonical readable terms, correcting only vocabulary-bounded spans."""
    tokens = base_text(text).split()
    result, position = [], 0
    while position < len(tokens):
        match = None
        # Long phrases must win over components: extra brut, pinot blanc, etc.
        for end in range(min(len(tokens), position + 5), position, -1):
            span = " ".join(tokens[position:end])
            for spelling in dict.fromkeys((span, span.translate(_CONFUSABLES))):
                for pattern, canonical in _MATCHERS:
                    if pattern.fullmatch(spelling):
                        match = canonical, end
                        break
                if match:
                    break
            if match:
                break
        if match:
            result.append(match[0])
            position = match[1]
        else:
            result.append(tokens[position])
            position += 1
    return " ".join(result)


def evidence(words):
    """Keep raw lines separate from normalized text; never increase confidence."""
    changes = []
    for index, word in enumerate(words):
        normalized = normalize(word["text"])
        if normalized != base_text(word["text"]):
            changes.append({"word": index, "raw": word["text"], "normalized": normalized,
                            "confidence": word["confidence"]})
    return dict(IDENTITY, text=normalize(" ".join(w["text"] for w in words)), corrections=changes)
