"""Compare printed attributes with independent catalogue values.

Unknown evidence cannot establish a contradiction. A partial grape list cannot prove
that the other grapes are absent. Empty metadata does not deny a product claim.
"""

import re
from datetime import datetime
from functools import lru_cache
import unicodedata

import attribute_facts

LABELS = {
    "grape": "Grape",
    "sweetness": "Sweetness",
    "colour": "Wine colour",
    "vintage": "Vintage",
    "reserve": "Reserve",
    "barrel": "Barrel / oak ageing",
    "kosher": "Kosher",
    "organic": "Organic",
    "unfiltered": "Unfiltered",
    "limited_edition": "Limited edition",
}
GRAPES = {
    "cabernet sauvignon": ("каберне совиньон", "cabernet sauvignon"),
    "cabernet franc": ("каберне фран", "cabernet franc"),
    "pinot noir": ("пино нуар", "pinot noir"),
    "pinot gris": ("пино гри", "pinot gris", "pinot grigio"),
    "pinot blanc": ("пино блан", "pinot blanc"),
    "chardonnay": ("шардоне", "chardonnay"),
    "sauvignon blanc": ("совиньон блан", "sauvignon blanc"),
    "merlot": ("мерло", "merlot"),
    "riesling": ("рислинг", "riesling"),
    "syrah": ("сира", "syrah", "shiraz"),
    "saperavi": ("саперави", "saperavi"),
    "krasnostop": ("красностоп", "krasnostop"),
    "muscat ottonel": ("мускат оттонель", "muscat ottonel"),
    "muscat": ("мускат", "muscat", "moscato"),
    "rkatsiteli": ("ркацители", "rkatsiteli"),
    "aligote": ("алиготе", "aligote"),
    "malbec": ("мальбек", "malbec"),
    "gewurztraminer": ("гевюрцтраминер", "gewurztraminer"),
    "viognier": ("вионье", "viognier"),
}
SUGARS = {
    "extra_brut": ("экстра брют", "extra brut"),
    "brut_nature": ("брют натюр", "brut nature", "zero dosage"),
    "extra_dry": ("экстра драй", "extra dry"),
    "brut": ("брют", "brut"),
    "semi_dry": (
        "полусухое",
        "полусухой",
        "semi dry",
        "polusuhoe",
        "semi seco",
        "medium dry",
        "off dry",
    ),
    "semi_sweet": (
        "полусладкое",
        "полусладкий",
        "semi sweet",
        "polusladkoe",
        "medium sweet",
    ),
    "dry": ("сухое", "сухой", "dry", "sec", "suhoe"),
    "sweet": ("сладкое", "сладкий", "sweet", "doux", "sladkoe"),
}
COLOURS = {
    "rose": ("розовое", "розовый", "rose", "rosato", "rosado"),
    "red": ("красное", "красный", "red", "rosso", "rouge", "tinto"),
    "white": ("белое", "белый", "white", "blanc", "bianco", "blanco"),
    "orange": ("оранжевое", "оранжевый", "orange", "amber wine"),
}
CLAIMS = {
    "reserve": r"\b(?:reserve|reserva|riserva|резерв|резерва)\b",
    "barrel": r"(?:barrel\s*aged|aged\s+in\s+(?:oak|barrel)|oak\s*aged|выдерж\w*\s+(?:в\s+)?(?:дуб\w*\s+)?боч\w*|выдерж\w*\s+в\s+дуб\w*)",
    "kosher": r"\b(?:kosher|кошер\w*)\b",
    "organic": r"\b(?:organic|органическ\w*)\b",
    "unfiltered": r"\b(?:unfiltered|нефильтрован\w*)\b",
    "limited_edition": r"\b(?:limited\s+(?:edition|release)|лимитирован\w*|ограниченн\w*\s+(?:тираж|серия))\b",
}


def norm(value):
    value = unicodedata.normalize("NFKD", str(value or "").lower().replace("ё", "е"))
    return re.sub(
        r"[^\w\s]", " ", "".join(c for c in value if not unicodedata.combining(c))
    )


@lru_cache(maxsize=20000)
def text(value):
    return " ".join(norm(value).split())


def has(value, phrase):
    return (
        re.search(r"(?<!\w)" + re.escape(text(phrase)) + r"(?!\w)", text(value))
        is not None
    )


def matched(value, aliases):
    """Use longest aliases first. Keep separate explicit incompatible values."""
    remaining = text(value)
    out = set()
    for canonical, alias in sorted(
        ((c, a) for c, values in aliases.items() for a in values),
        key=lambda item: len(text(item[1])),
        reverse=True,
    ):
        pattern = r"(?<!\w)" + re.escape(text(alias)) + r"(?!\w)"
        if re.search(pattern, remaining):
            out.add(canonical)
            remaining = re.sub(pattern, " ", remaining)
    return out


def canonical(field, values, beverage=None):
    if not values:
        return set()
    joined = " ; ".join(values)
    if field == "grape":
        found = matched(joined, GRAPES)
        remaining = text(re.sub(r"\b\d+(?:[.,]\d+)?\s*%", " ", joined))
        for alias in sorted(
            {a for aliases in GRAPES.values() for a in aliases},
            key=lambda a: len(text(a)),
            reverse=True,
        ):
            remaining = re.sub(
                r"(?<!\w)" + re.escape(text(alias)) + r"(?!\w)", " ", remaining
            )
        remaining = re.sub(
            r"\b(?:and|with|plus|и|с|сорт|сорта|винограда|grapes?|varieties|variety)\b",
            " ",
            remaining,
        )
        return set() if remaining.strip() else found
    if field == "sweetness":
        if has(joined, "demi sec"):
            if beverage not in ("4", "44"):
                return set()
            other = re.sub(r"demi\s+sec", "", text(joined))
            return matched(other, SUGARS) | {
                "semi_sweet" if beverage == "44" else "semi_dry"
            }
        return matched(joined, SUGARS)
    if field == "colour":
        remaining = joined
        for alias in sorted(
            {a for names in GRAPES.values() for a in names}
            | {"White Zinfandel", "White Merlot", "Orange Muscat"},
            key=len,
            reverse=True,
        ):
            remaining = re.sub(
                r"(?<!\w)" + re.escape(alias) + r"(?!\w)", " ", remaining, flags=re.I
            )
        return matched(remaining, COLOURS)
    if field == "vintage":
        return {
            y
            for y in re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", joined)
            if int(y) <= datetime.now().year + 1
        }
    if field == "barrel":
        raw = " ; ".join(values)
        clauses = re.split(r"(?<!\d),(?!\d)|[;:—]|\b(?:и|and)\b", raw, flags=re.I)
        if any(
            re.search(
                r"\b(?:unoaked|no\s+(?:oak|barrel)|без\s+выдержки|не\s+выдерж\w*)\b",
                clause,
                re.I,
            )
            for clause in clauses
        ) or text(joined) in ("no", "нет"):
            return {"no"}
        found = set()
        for clause in clauses:
            if not re.search(r"oak|barrel|дуб\w*|боч\w*", clause, re.I):
                continue
            if re.search(
                r"не менее|не более|\bдо\b|\bот\b|at least|up to|about|около|more than",
                clause,
                re.I,
            ):
                continue
            for number, unit in re.findall(
                r"(?<![\d.,])(\d+(?:[.,]\d+)?)\s*(months?|мес(?:\.|яц\w*)?|years?|лет|год\w*)",
                clause,
                re.I,
            ):
                months = float(number.replace(",", ".")) * (
                    12 if unit.lower().startswith(("year", "лет", "год")) else 1
                )
                if len(number.split(".")[0].split(",")[0]) < 4 and 0 < months <= 120:
                    found.add("months:" + format(months, "g"))
        for oak, pattern in [
            ("french", r"french|французск\w*"),
            ("american", r"american|американск\w*"),
            ("caucasian", r"caucasian|кавказск\w*"),
        ]:
            if re.search(pattern, raw, re.I):
                found.add("oak:" + oak)
        return found or (
            {"yes"}
            if re.search(CLAIMS["barrel"], text(joined))
            or text(joined) in ("yes", "да")
            else set()
        )
    clauses = re.split(r"(?<!\d),(?!\d)|[;:—]", joined)
    if any(
        re.search(r"\b(?:not|no|не)\s+" + CLAIMS[field], text(clause), re.I)
        for clause in clauses
    ) or text(joined) in ("no", "нет"):
        return {"no"}
    if field == "reserve":
        if has(joined, "gran reserva"):
            return {"gran reserva"}
        if has(joined, "grande reserve") or has(joined, "grand reserve"):
            return {"grand reserve"}
        return {"reserve"} if re.search(CLAIMS[field], text(joined)) else set()
    return (
        {"yes"}
        if re.search(CLAIMS[field], text(joined)) or text(joined) in ("yes", "да")
        else set()
    )


def observed(values, evidence):
    return {"state": "observed", "values": list(values), "evidence": evidence[:2000]}


def printed_terms(value, aliases):
    """Return exact attribute phrases from the evidence, longest aliases first."""
    spans = []
    for alias in sorted(
        {a for values in aliases.values() for a in values}, key=len, reverse=True
    ):
        pattern = r"(?<!\w)" + re.escape(alias).replace(r"\ ", r"[\s-]+") + r"(?!\w)"
        for match in re.finditer(pattern, value, re.I):
            if not any(
                match.start() < right and match.end() > left for left, right in spans
            ):
                spans.append(match.span())
    return list(dict.fromkeys(value[left:right] for left, right in sorted(spans)))


def facts_from_texts(texts, vintage=None):
    """Seed only explicit printed text. Absence in old descriptions stays Unknown."""
    out = attribute_facts.empty()
    texts = list(
        dict.fromkeys(t.strip() for t in texts if isinstance(t, str) and t.strip())
    )
    for field, aliases in [
        ("grape", GRAPES),
        ("sweetness", SUGARS),
        ("colour", COLOURS),
    ]:
        hits = [
            t
            for t in texts
            if matched(t, aliases) or field == "sweetness" and has(t, "demi sec")
        ]
        if field in ("colour", "sweetness"):

            def descriptor_only(value):
                remaining = text(value)
                for group in (COLOURS, SUGARS, {"demi": ("demi sec",)}):
                    for alias in sorted(
                        {a for values in group.values() for a in values},
                        key=len,
                        reverse=True,
                    ):
                        remaining = re.sub(
                            r"(?<!\w)" + re.escape(text(alias)) + r"(?!\w)",
                            " ",
                            remaining,
                        )
                words = set(remaining.split())
                return words <= {
                    "вино",
                    "wine",
                    "vino",
                    "vin",
                    "игристое",
                    "sparkling",
                    "still",
                } and not (text(value) == "orange")

            hits = [value for value in hits if descriptor_only(value)]
        if hits:
            evidence = "\n".join(hits)[:2000]
            phrases = printed_terms(evidence, aliases)
            if field == "sweetness":
                phrases += printed_terms(
                    evidence, {"demi_sec": ("Demi-sec", "Demi sec")}
                )
            out[field] = observed(
                (hits if field == "grape" else phrases or hits)[:20], evidence
            )
    for field, pattern in CLAIMS.items():
        hits = [t for t in texts if re.search(pattern, text(t))]
        if hits:
            out[field] = observed(hits[:20], "\n".join(hits))
    # A year is seeded from the prior explicit vintage field, never all printed years.
    if re.fullmatch(r"(?:19|20)\d{2}", str(vintage or "")):
        hits = [
            t
            for t in texts
            if has(t, str(vintage))
            and not re.search(
                r"found|since|основан|розлив|bottl|medal|award|медал", text(t)
            )
        ]
        if hits:
            out["vintage"] = observed([str(vintage)], "\n".join(hits))
    return out


def metadata(record):
    """Use explicit source fields. Free prose can supply positive product claims."""
    result = {f: [] for f in attribute_facts.FIELDS}
    result["grape"] = [record["grapes"]] if record.get("grapes") else []
    source = " ".join(
        str(record.get(k) or "") for k in ("category", "name", "color", "slug")
    )
    # The catalogue category carries beverage colour; color can carry a shade.
    result["colour"] = [record.get("category") or record.get("color") or ""]
    sugar = matched(source, SUGARS)
    if has(source, "demi sec"):
        result["sweetness"] = ["Demi-sec"]
    elif sugar:
        # Keep the exact matched source term. Do not repeat the full name and slug.
        terms = []
        for canonical_name, aliases in SUGARS.items():
            if canonical_name not in sugar:
                continue
            for alias in aliases:
                pattern = (
                    r"(?<!\w)" + re.escape(alias).replace(r"\ ", r"[\s-]+") + r"(?!\w)"
                )
                match = re.search(pattern, source, re.I)
                if match:
                    terms.append(match.group())
                    break
        result["sweetness"] = list(dict.fromkeys(terms))
    named = re.findall(
        r"(?<!\d)(?:19|20)\d{2}(?!\d)",
        " ".join(str(record.get(k) or "") for k in ("name", "slug")),
    )
    tags = [
        re.sub(r"^vintage:", "", t)
        for t in record.get("_tags", [])
        if re.fullmatch(r"(?:vintage:)?(?:19|20)\d{2}", t)
    ]
    result["vintage"] = sorted(set(named or tags))
    if not result["vintage"] and any(
        t in ("no_year", "generic") for t in record.get("_tags", [])
    ):
        result["vintage"] = ["Any vintage"]
    claims_text = " ".join(str(record.get(k) or "") for k in ("name", "description"))
    # Sentence boundaries retain duration evidence without taking unrelated prose.
    sentences = re.split(r"(?<=[.!?])\s+|\n+", claims_text)
    for field, pattern in CLAIMS.items():
        result[field] = [
            sentence for sentence in sentences if re.search(pattern, text(sentence))
        ][:20]
    return result


def outcome(field, meta, fact, beverage=None):
    meta = [
        v
        for v in meta
        if text(v) not in ("", "n a", "unknown", "not specified", "0", "false")
    ]
    values = fact.get("values", [])
    state = fact.get("state", "unknown")
    if state in ("unknown", "unreadable"):
        return "unknown"
    if state == "not_visible":
        return "metadata_only" if any(meta) else "unknown"
    if not any(meta) or field == "vintage" and meta == ["Any vintage"]:
        return "image_only"
    left, right = canonical(field, meta, beverage), canonical(field, values, beverage)
    if not left or not right:
        return "unknown"
    if left == right and len(left) == 1:
        return "match"
    if field == "grape":
        if left == right:
            return "match"
        if any("muscat" in a and "muscat" in b for a in left for b in right):
            return "unknown"

        def complete(values):
            percentages = [
                float(v.replace(",", "."))
                for v in re.findall(r"(\d+(?:[.,]\d+)?)\s*%", " ".join(values))
            ]
            return bool(
                percentages
                and (100 in percentages or abs(sum(percentages) - 100) < 0.01)
            )

        if complete(meta) and right - left or complete(values) and left - right:
            return "conflict"
        return "unknown"
    if field == "sweetness" and left != right:
        # Conservative intervals include classification overlap and sparkling tolerance.
        ranges = {
            "4": {
                "dry": (0, 9),
                "semi_dry": (4, 18),
                "semi_sweet": (12, 45),
                "sweet": (45, float("inf")),
            },
            "44": {
                "brut_nature": (0, 3),
                "extra_brut": (0, 9),
                "brut": (0, 15),
                "extra_dry": (9, 20),
                "dry": (14, 35),
                "semi_sweet": (29, 53),
                "sweet": (47, float("inf")),
            },
        }
        if beverage not in ranges or len(left) != 1 or len(right) != 1:
            return "unknown"
        ra = ranges[beverage].get(next(iter(left)))
        rb = ranges[beverage].get(next(iter(right)))
        if ra is None or rb is None:
            return "unknown"
        return "conflict" if max(ra[0], rb[0]) > min(ra[1], rb[1]) else "unknown"
    if field == "reserve" and left != right and "no" not in left | right:
        return "unknown"
    if field == "barrel":
        if "no" in left | right:
            return "match" if left == right else "conflict"
        a_months = {v for v in left if v.startswith("months:")}
        b_months = {v for v in right if v.startswith("months:")}
        if len(a_months) > 1 or len(b_months) > 1:
            return "unknown"
        if len(a_months) == len(b_months) == 1 and a_months != b_months:
            return "conflict"
        return "match" if left == right else "unknown"
    if len(left) != 1 or len(right) != 1:
        return "unknown"
    return "conflict"


def comparison(record, observations):
    """Build one table with active-image evidence and independent main/patch checks."""

    def sha(url):
        match = re.search(r"/([a-f0-9]{64})\.", url or "")
        return match.group(1) if match else None

    main, patch = (
        sha(record.get("main_image_original_url")),
        sha(record.get("_patch_url")),
    )
    active = patch or main
    view = observations.get(active) or {
        "state": "not_tracked"
        if record.get("state") == "Removed"
        else "missing"
        if not active
        else "not_queued",
        "facts": attribute_facts.empty(),
        "stale": False,
    }
    source = "Patch image" if patch else "Main image"
    meta = metadata(record)
    rows = []
    current = view["state"] == "ready" and not view.get("stale")
    for field in attribute_facts.FIELDS:
        fact = view["facts"][field]
        status = (
            outcome(field, meta[field], fact, record.get("_beverage_type_code"))
            if current
            else "unknown"
        )
        row = {
            "field": field,
            "label": LABELS[field],
            "metadata": meta[field],
            "image": fact["values"],
            "evidence": fact["evidence"],
            "image_state": fact["state"],
            "result": status,
            "image_disagreement": False,
        }
        if main and patch:
            other = observations.get(main) or {}
            if current and other.get("state") == "ready" and not other.get("stale"):
                other_fact = other["facts"][field]
                if other_fact["state"] == "observed" and fact["state"] == "observed":
                    row["image_disagreement"] = (
                        outcome(
                            field,
                            other_fact["values"],
                            fact,
                            record.get("_beverage_type_code"),
                        )
                        == "conflict"
                    )
                    if row["image_disagreement"]:
                        row["main_image_values"] = other_fact["values"]
        rows.append(row)
    return {
        "metadata_inputs": [
            record.get(k) or ""
            for k in ("name", "category", "color", "grapes", "description")
        ]
        + [record.get("_tags") or [], record.get("_beverage_type_code") or ""],
        "source": source,
        "sha256": active,
        "state": view["state"],
        "stale": view.get("stale", False),
        "error": view.get("error"),
        "extracted_at": view.get("created_at"),
        "extraction_source": view.get("source"),
        "model": view.get("model"),
        "rows": rows,
        "conflicts": sum(r["result"] == "conflict" for r in rows),
        "image_disagreements": sum(r["image_disagreement"] for r in rows),
        "additional": sum(r["result"] in ("image_only", "metadata_only") for r in rows),
    }


def attach(conn, records, version=None):
    observations = attribute_facts.views(conn, version)
    counts = {
        "images_differ": 0,
        "conflicts": 0,
        "additional": 0,
        "pending": 0,
        "failed": 0,
        "ready": 0,
    }
    for record in records:
        comp = comparison(record, observations)
        record["_attribute_comparison"] = comp
        if record.get("state") != "Removed":
            counts["conflicts"] += bool(comp["conflicts"])
            counts["images_differ"] += bool(comp["image_disagreements"])
            counts["additional"] += bool(comp["additional"])
            if comp["state"] in counts:
                counts[comp["state"]] += 1
            elif comp["state"] == "running":
                counts["pending"] += 1
    counts.update(attribute_facts.settings(conn))
    return counts
