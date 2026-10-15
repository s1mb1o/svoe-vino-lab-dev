"""Explicit wine attributes for confidence-checked shortlist verification.

An absent word is unknown. Common brand text and dates do not verify a variant.
Grape families remain broader than named varieties. Product-line terms provide
positive evidence; their absence from a catalogue name is not a contradiction.
"""

import re
import wine_terms

FIELDS = ("sugar", "grapes", "colour", "line")
LABELS = {"sugar": "Sugar", "grapes": "Grapes", "colour": "Colour", "line": "Product line"}
RANKING_POLICY = "contradictions-and-explicit-line-v2"

SUGAR = wine_terms.SUGAR
GRAPES = wine_terms.GRAPES
GRAPE_PARENTS = wine_terms.GRAPE_PARENTS
COLOURS = (
    ("rose", r"rose|розе|розов(?:ое|ый|ая)|rozovoe|rozovyi|roze"),
    ("white", r"white|бел(?:ое|ый|ая)|beloe|belyi|blanc\s+de\s+(?:blancs|noirs)|blanc"),
    ("red", r"red|rouge|красн(?:ое|ый|ая)|krasnoe|krasnyi"),
    ("orange", r"orange|оранжев(?:ое|ый|ая)|oranzhevoe"),
)
LINES = (
    ("grand_reserve", r"(?:grand|гранд)\s+(?:reserve|reserva|резерв|резерва)"),
    ("reserve", r"reserve|reserva|резерв|резерва|резервн(?:ое|ый|ая)"),
    ("kosher", r"kosher|koshernoe|кошерн(?:ое|ый|ая)"),
    ("collection", r"collection|коллекци(?:я|онное|онный|онная)"),
)


def normalized(text):
    return wine_terms.base_text(wine_terms.normalize(text))


def extract(text, rules):
    value = normalized(text)
    found = set()
    for kind, pattern in rules:
        pattern = r"\b(?:" + pattern + r")\b"
        if re.search(pattern, value):
            found.add(kind)
            value = re.sub(pattern, " ", value)
    return sorted(found), " ".join(value.split())


def parsed(text):
    sugar_values, _ = extract(text, SUGAR)
    grapes, remaining = extract(text, GRAPES)
    # WHITE and ROSE inside a grape name do not establish wine colour.
    colours, _ = extract(remaining, COLOURS)
    line_text = re.sub(r"\b(?:not|non|не)\s+(?:kosher|кошерн(?:ое|ый|ая))\b", " ", normalized(text))
    lines, _ = extract(line_text, LINES)
    return {"sugar": sugar_values if len(sugar_values) == 1 else None,
            "grapes": grapes or None, "colour": colours if len(colours) == 1 else None,
            "line": lines or None}


def sugar(text):
    values = parsed(text)["sugar"]
    return values[0] if values else None


def observed(words, minimum):
    all_text = " ".join(word["text"] for word in words)
    all_fields = parsed(all_text)
    high_fields = parsed(" ".join(word["text"] for word in words if word["confidence"] >= minimum))
    values, reasons = {}, {}
    _, colour_text = extract(all_text, GRAPES)
    ambiguous = {field for field, text, rules in [("sugar", all_text, SUGAR), ("colour", colour_text, COLOURS)]
                 if len(extract(text, rules)[0]) > 1}
    for field in FIELDS:
        high = high_fields[field]
        if high and high == all_fields[field]:
            values[field] = high
        else:
            values[field] = None
            reasons[field] = "uncertain_or_conflicting_text" if all_fields[field] or high or field in ambiguous else "not_read"
    return values, reasons


def expected(record):
    record = record or {}
    text = " ".join(str(record.get(key) or "") for key in ("name", "slug"))
    values = parsed(text)
    # Some legacy slugs append the broad BRUT category after EXTRA BRUT.
    # Prefer an explicit catalogue name; retain ambiguity within that name.
    name_sugar, _ = extract(record.get("name"), SUGAR)
    if name_sugar:
        values["sugar"] = name_sugar if len(name_sugar) == 1 else None
    raw_grapes = record.get("grapes") or ""
    grape_values, remaining = extract(raw_grapes, GRAPES)
    if raw_grapes:
        values["grapes"] = grape_values or None
    # An incomplete name or partly unknown blend can support a grape match, but
    # cannot establish a conflict through an absent grape.
    complete = bool(raw_grapes and grape_values and not set(remaining.split()) - {"и", "and"})
    colour = str(record.get("color") or "")
    category, leftover = extract(colour, COLOURS)
    if category and not leftover and len(category) == 1:
        if values["colour"] and values["colour"] != category:
            values["colour"] = None
        else:
            values["colour"] = category
    return values, complete


def compatible_grape(a, b):
    return a == b or GRAPE_PARENTS.get(a) == b or GRAPE_PARENTS.get(b) == a


def compare(field, observed_values, expected_values, complete_grapes=False):
    if not observed_values or not expected_values:
        return "unknown"
    if field == "grapes":
        if all(any(compatible_grape(a, b) for b in expected_values) for a in observed_values):
            return "match"
        return "conflict" if complete_grapes else "unknown"
    if field == "line":
        expected_terms = set(expected_values)
        if "grand_reserve" in expected_terms:
            expected_terms.add("reserve")
        return "match" if set(observed_values) <= expected_terms else "unknown"
    return "match" if observed_values == expected_values else "conflict"


def verify(candidates, words, catalog, options):
    observed_values, rejections = observed(words, options["min_confidence"])
    head = [dict(row) for row in candidates[:options["window"]]]
    catalog_values = {row["slug"]: expected(dict(catalog.get(row["slug"]) or {}, slug=row["slug"])) for row in head}
    active = []
    for field in FIELDS:
        variants = {tuple(values[field] or ()) for values, _ in catalog_values.values()}
        if field != "line":
            variants.discard(())
        if observed_values[field] and len(variants) >= 2:
            active.append(field)
    details, buckets = {}, {}
    for row in head:
        values, complete_grapes = catalog_values[row["slug"]]
        fields = {field: {"observed": observed_values[field], "expected": values[field],
                         "status": compare(field, observed_values[field], values[field], complete_grapes)
                                   if field in active else "unused",
                         "discriminating": field in active} for field in FIELDS}
        statuses = [fields[field]["status"] for field in active]
        if "conflict" in statuses:
            bucket = 3
        elif statuses and all(value == "match" for value in statuses):
            bucket = 0
        elif "match" in statuses:
            bucket = 1
        else:
            bucket = 2
        details[row["slug"]] = fields
        buckets[row["slug"]] = bucket
    matches = [row["slug"] for row in head if buckets[row["slug"]] in (0, 1)]
    conflicts = [row["slug"] for row in head if buckets[row["slug"]] == 3]
    # Missing catalogue metadata must not make a compatible visual winner lose
    # to a more completely described neighbour. A visibly named product line
    # remains positive evidence; reliable contradictions still rank last.
    order = {slug: (buckets[slug] == 3,
                    "line" in active and details[slug]["line"]["status"] != "match")
             for slug in buckets}
    applied = bool(matches and len(set(order.values())) > 1)
    if applied:
        head.sort(key=lambda row: order[row["slug"]])
    answer = head + [dict(row) for row in candidates[options["window"]:]]
    before = {row["slug"]: row.get("rank") for row in candidates}
    for rank, row in enumerate(answer, 1):
        row["rank"] = rank
        if applied:
            slug = row["slug"]
            field_data = details.get(slug, {})
            row["variant_text"] = {
                "observed": (observed_values["sugar"] or [None])[0],
                "expected": ((field_data.get("sugar") or {}).get("expected") or [None])[0],
                "status": {0: "match", 1: "partial_match", 2: "unknown", 3: "conflict"}.get(buckets.get(slug), "unknown"),
                "attributes": field_data, "visual_rank": before.get(slug),
            }
    return answer, {"observed_sugar": (observed_values["sugar"] or [None])[0],
                    "observed_attributes": observed_values, "attribute_rejections": rejections,
                    "discriminating_fields": active, "candidate_attributes": details,
                    "applied": applied, "matches": matches, "conflicts": conflicts, "words": words,
                    "normalization": wine_terms.evidence(words),
                    "ranking_policy": RANKING_POLICY,
                    "reason": "explicit_variant_text" if applied else "no_discriminating_text"}
