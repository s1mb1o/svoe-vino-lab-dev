"""Read a vintage, then prefer the exact vintage or the undated variant.

The caller MUST restrict the ranking to the triggered wine cluster.
An unreadable vintage is neutral. A missing description does not prove no vintage.
"""
import re
import sqlite3
from contextlib import closing

YEAR = re.compile(r"(?:19|20)[0-9]{2}\Z")


def vintage_questions(rule):
    return [q for q in rule.get("questions", []) if q.get("kind") == "vintage"]


def feature_rule(rule):
    return dict(rule, questions=[q for q in rule.get("questions", []) if q.get("kind") != "vintage"])


def feature_answers(rule, answer):
    if not isinstance(answer, dict):
        return answer
    ids = {q["id"] for q in vintage_questions(rule)}
    return {qid: value for qid, value in answer.items() if qid not in ids}


def year_answers(rule, answer):
    if not isinstance(answer, dict):
        return {}
    return {q["id"]: answer.get(q["id"]) for q in vintage_questions(rule)}


def readout_schema(rule, feature_schema):
    properties = dict(feature_schema["properties"])
    for q in vintage_questions(rule):
        properties[q["id"]] = {"type": ["string", "null"], "pattern": "^(?:19|20)[0-9]{2}$"}
    return {"type": "object", "additionalProperties": False,
            "properties": properties, "required": list(properties)}


def readout_prompt(rule, feature_prompt):
    years = vintage_questions(rule)
    if not years:
        return feature_prompt
    prefix = (feature_prompt + "\n\n") if feature_rule(rule)["questions"] else ""
    lines = ["%s: %s" % (q["id"], q["question"]) for q in years]
    return prefix + (
        "For VINTAGE questions, copy the actual four-digit vintage printed on the label. "
        "Return a string with that year, or null if it is absent, unreadable or ambiguous. "
        "Do not use a founding year, award year or bottling date as the vintage. "
        "Do not choose a wine. Do not give vintage option scores. "
        "Do not replace an unlisted year with other. Candidate years are not supplied.\n\n"
        + "\n".join(lines)
        + "\n\nReturn one complete JSON object. Vintage question ids map to a year string or null. "
        "Other question ids map to their complete score objects."
    )


def response_errors(rule, answer, score_errors):
    if not vintage_questions(rule):
        return score_errors(rule, answer)
    errors = score_errors(feature_rule(rule), feature_answers(rule, answer))
    expected = {q["id"] for q in rule["questions"]}
    if not isinstance(answer, dict):
        errors["_response"] = "the readout is not a JSON object"
        return errors
    if set(answer) != expected:
        errors["_response"] = "the readout MUST contain exactly the requested question ids"
    for q in vintage_questions(rule):
        value = answer.get(q["id"])
        if q["id"] not in answer or (value is not None and
                                      (not isinstance(value, str) or not YEAR.fullmatch(value))):
            errors[q["id"]] = "the vintage readout MUST be a four-digit year string or null"
    return errors


def load_catalogue(db_path):
    """Read canonical names and vintage tags without modifying the database."""
    with closing(sqlite3.connect("file:%s?mode=ro" % db_path, uri=True, timeout=30)) as conn:
        catalog = {slug: {"name": name, "tags": []} for slug, name in conn.execute(
            "SELECT wine_slug, COALESCE(name_patched, name) FROM wine_catalog")}
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='wine_tag'").fetchone():
            for slug, tag in conn.execute("SELECT wine_slug, tag FROM wine_tag"):
                if slug in catalog:
                    catalog[slug]["tags"].append(tag)
        return catalog


def prefer_year(ranking, readouts, dated, undated):
    """Use a stable preference inside the supplied candidate cluster window."""
    ranking = list(ranking)
    audit = {"readouts": readouts, "observed_year": None, "preferred": [],
             "reason": "not_visible", "changed": False,
             "candidate_years": {slug: sorted(info["years"]) for slug, info in dated.items()
                                 if slug in ranking},
             "undated": [slug for slug in ranking if slug in undated and slug not in dated]}
    if not isinstance(readouts, dict) or any(value is not None and
                                           (not isinstance(value, str) or not YEAR.fullmatch(value))
                                           for value in readouts.values()):
        audit["reason"] = "invalid_readout"
        return ranking, audit
    years = {value for value in readouts.values() if value is not None}
    if len(years) != 1:
        if years:
            audit["reason"] = "conflicting_years"
        return ranking, audit
    year = years.pop()
    audit["observed_year"] = year
    exact = [slug for slug in ranking if set((dated.get(slug) or {}).get("years", ())) == {year}]
    preferred = exact or audit["undated"]
    audit.update(preferred=preferred, reason="exact_year" if exact else
                 "undated_fallback" if preferred else "no_eligible_variant")
    chosen = set(preferred)
    result = [slug for slug in ranking if slug in chosen] + [slug for slug in ranking if slug not in chosen]
    audit["changed"] = result != ranking
    return result, audit
