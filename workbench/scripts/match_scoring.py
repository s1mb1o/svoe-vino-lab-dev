"""The scoring of one match run: the judgement of each answer, the metrics, the summary.

`scripts/match_run.py` and `pipeline/benchmark.py` both use this module, so both runners
score with the same code. The code moved here unchanged from `scripts/match_run.py` on
2026-09-25. Read `docs/plans/12_testsets-benchmark.md`.
"""
import collections
import json
import statistics

LABELS_IN_SET = ("positive", "negative", "variant")

# The label of a photo of `--photos-dir`. The directory holds no ground truth.
UNLABELLED = "unlabelled"

# The virtual NULL wine of the review tool. `<photo_dir>/__null__/` holds the
# photos that match NO card of the catalogue. The place is the statement, so such
# a photo needs no label. It is a rejection case: the backend MUST answer nothing,
# and any answered slug is a false match.
NULL_SLUG = "__null__"

NO_MATCH = "no_match"


def judge(row, candidates, negative_strict):
    """Return the judgement of one answer.

    A positive or a variant photo is scored by the rank of its true slug. A
    negative photo carries no positive truth: the reviewer stated that the photo
    is NOT this wine and did not state which wine it is. So only one outcome is
    a proven error, and no outcome is a proven success.

    A `no_match` photo is the opposite case: the reviewer stated that NO card of
    the catalogue shows this wine. No answer is the only correct outcome, and
    every answer is a proven error.
    """
    ranked = []
    seen = set()
    for cand in candidates:               # one slug keeps its first rank only
        if cand["slug"] not in seen:
            seen.add(cand["slug"])
            ranked.append(cand["slug"])
    top1 = ranked[0] if ranked else None
    out = {"predicted_slug": top1, "rank_of_truth": None, "outcome": None}

    if row["label"] == UNLABELLED:
        # The photo holds no true slug. The run records what came back. Neither
        # a success nor an error can be stated.
        out["outcome"] = "no_answer" if top1 is None else "answered"
        return out

    if row["label"] == NO_MATCH:
        # No card of the catalogue shows this wine. The correct answer is no
        # answer. Every slug that comes back at rank 1 is a false match, and the
        # backend MUST have abstained. The depth does not matter: a card deeper
        # in the list is wrong in the same way, and the interface shows rank 1.
        out["outcome"] = "no_answer" if top1 is None else "false_match_at_1"
        return out

    if row["label"] == "negative":
        if top1 is None:
            out["outcome"] = "no_answer"
        elif top1 == row["slug"]:
            out["outcome"] = "false_match_at_1"
        elif negative_strict and row["slug"] in ranked:
            out["outcome"] = "false_match_in_top_k"
        else:
            out["outcome"] = "other_slug_at_1"
        if row["slug"] in ranked:
            out["rank_of_truth"] = ranked.index(row["slug"]) + 1
        return out

    truth = set(row["truth"])
    for i, slug in enumerate(ranked, 1):
        if slug in truth:
            out["rank_of_truth"] = i
            break
    out["outcome"] = "hit" if out["rank_of_truth"] == 1 else (
        "no_answer" if top1 is None else "miss")
    return out

# The target of the specification of the task, section 2: the answer SHOULD come
# in 3 seconds, and the share of the matches SHOULD reach 90 to 100 percent.
SLA_MS = 3000

TARGET_MATCH_SHARE = 0.90


def f1(hits, answered, total):
    """Return precision, recall, and F1 of one run at one depth.

    The specification asks for the F1 of the top-1 card and of the top-5 cards.
    A service that abstains answers fewer photos, so its precision and its recall
    differ, and F1 states the balance. A service that always answers gets
    precision = recall = F1 = the share of the matches.
    """
    prec = hits / answered if answered else None
    rec = hits / total if total else None
    if not prec or not rec:
        return {"precision": round(prec, 4) if prec is not None else None,
                "recall": round(rec, 4) if rec is not None else None,
                "f1": 0.0 if (prec == 0 or rec == 0) else None}
    return {"precision": round(prec, 4), "recall": round(rec, 4),
            "f1": round(2 * prec * rec / (prec + rec), 4)}


def metrics_of(results, backend, top_k, negative_strict, wall_s, workers,
               groups=None):
    """Return the aggregate of one run."""
    groups = groups or {}
    pos = [r for r in results if r["label"] in ("positive", "variant")]
    neg = [r for r in results if r["label"] == "negative"]
    unl = [r for r in results if r["label"] == UNLABELLED]
    nom = [r for r in results if r["label"] == NO_MATCH]
    has_scores = any(c.get("score") is not None
                     for r in results for c in r["candidates"])

    def recall(rows, k):
        if k > top_k:
            return None                    # the backend never returns that deep
        ok = [r for r in rows if r["rank_of_truth"] and r["rank_of_truth"] <= k]
        return round(len(ok) / len(rows), 4) if rows else None

    def histogram(rows):
        out = collections.Counter()
        for r in rows:
            rank = r["rank_of_truth"]
            if rank is None:
                out["absent"] += 1
            elif rank <= 3:
                out[str(rank)] += 1
            elif rank <= 10:
                out["4-10"] += 1
            else:
                out[">10"] += 1
        return dict(out)

    def hits_at(rows, k):
        return sum(1 for r in rows if r["rank_of_truth"] and r["rank_of_truth"] <= k)

    answered = sum(1 for r in pos if r["predicted_slug"])

    # The margin between the first and the second candidate. The specification
    # asks for a noticeable gap, so that the interface can show one card.
    margins = {"correct": [], "wrong": []}
    for r in pos:
        cands = r["candidates"]
        if len(cands) < 2 or cands[0].get("score") is None or cands[1].get("score") is None:
            continue
        gap = cands[0]["score"] - cands[1]["score"]
        margins["correct" if r["rank_of_truth"] == 1 else "wrong"].append(gap)

    # A near-duplicate confusion: the answer is wrong, and the answered slug
    # stands in the variant group of the true wine. The specification names the
    # near-duplicates as the main source of the errors.
    near_dup = 0
    for r in pos:
        if r["rank_of_truth"] == 1 or not r["predicted_slug"]:
            continue
        for truth in r["truth"]:
            if r["predicted_slug"] in (groups.get(truth) or set()):
                near_dup += 1
                break

    # The answer of an unlabelled photo carries no verdict. Its top score and the
    # gap to the second candidate are the only signals of the confidence.
    unl_top, unl_gap = [], []
    for r in unl:
        cands = r["candidates"]
        if cands and cands[0].get("score") is not None:
            unl_top.append(cands[0]["score"])
            if len(cands) > 1 and cands[1].get("score") is not None:
                unl_gap.append(cands[0]["score"] - cands[1]["score"])

    within_sla = [r for r in results if r["latency_ms"] is not None
                  and r["latency_ms"] <= SLA_MS]

    mrr = 0.0
    for r in pos:
        if r["rank_of_truth"]:
            mrr += 1.0 / r["rank_of_truth"]
    lat = sorted(r["latency_ms"] for r in results if r["latency_ms"] is not None)
    false_scores = [r["candidates"][0]["score"] for r in neg
                    if r["outcome"] == "false_match_at_1" and r["candidates"]
                    and r["candidates"][0].get("score") is not None]
    # The score that a backend gave to a card while no card was right. A
    # threshold that refuses these photos MUST stand above this value.
    no_match_scores = [r["candidates"][0]["score"] for r in nom
                       if r["outcome"] == "false_match_at_1" and r["candidates"]
                       and r["candidates"][0].get("score") is not None]

    out = {
        "run_id": None,
        "backend": backend.id,
        "top_k": top_k,
        "has_scores": has_scores,
        "negative_strict": negative_strict,
        "queries": {
            "total": len(results),
            "positive": sum(1 for r in results if r["label"] == "positive"),
            "negative": len(neg),
            "variant": sum(1 for r in results if r["label"] == "variant"),
            "unlabelled": len(unl),
            "no_match": len(nom),
        },
        # A run of `--photos-dir`. The photos hold no ground truth, so this block
        # holds the counts that do not need one, and every share above is empty.
        "unlabelled": None if not unl else {
            "n": len(unl),
            "answered": sum(1 for r in unl if r["predicted_slug"]),
            "no_answer": sum(1 for r in unl if r["outcome"] == "no_answer"),
            "errors": sum(1 for r in unl if r["error"]),
            "top_score_median": round(statistics.median(unl_top), 4) if unl_top else None,
            "score_margin_median": round(statistics.median(unl_gap), 4) if unl_gap else None,
        },
        "positive": {
            "n": len(pos),
            "answered": answered,
            "match_share": recall(pos, 1),       # the share of the specification
            "target_match_share": TARGET_MATCH_SHARE,
            "f1_at_1": f1(hits_at(pos, 1), answered, len(pos)),
            "f1_at_5": f1(hits_at(pos, 5), answered, len(pos)) if top_k >= 5 else None,
            "near_duplicate_confusion": near_dup,
            "score_margin": {
                "correct_median": round(statistics.median(margins["correct"]), 4)
                                  if margins["correct"] else None,
                "wrong_median": round(statistics.median(margins["wrong"]), 4)
                                if margins["wrong"] else None,
            },
            "recall_at_1": recall(pos, 1),
            "recall_at_5": recall(pos, 5),
            "recall_at_10": recall(pos, 10),
            "mrr": round(mrr / len(pos), 4) if pos else None,
            "no_answer": sum(1 for r in pos if r["outcome"] == "no_answer"),
            "errors": sum(1 for r in pos if r["error"]),
            "rank_histogram": histogram(pos),
        },
        # The photos that match no card of the catalogue. The backend MUST answer
        # nothing. `rejection_rate` is the share of these photos that it refused.
        "no_match": None if not nom else {
            "n": len(nom),
            "rejected": sum(1 for r in nom if r["outcome"] == "no_answer"),
            "false_match_at_1": sum(1 for r in nom
                                    if r["outcome"] == "false_match_at_1"),
            "rejection_rate": round(
                sum(1 for r in nom if r["outcome"] == "no_answer") / len(nom), 4),
            "errors": sum(1 for r in nom if r["error"]),
            "false_match_scores": {
                "median": round(statistics.median(no_match_scores), 4)
                          if no_match_scores else None,
                "max": round(max(no_match_scores), 4) if no_match_scores else None,
            },
        },
        "negative": {
            "n": len(neg),
            "false_match_at_1": sum(1 for r in neg
                                    if r["outcome"] == "false_match_at_1"),
            "false_match_in_top_k": sum(1 for r in neg if r["rank_of_truth"]),
            "other_slug_at_1": sum(1 for r in neg
                                   if r["outcome"] == "other_slug_at_1"),
            "no_answer": sum(1 for r in neg if r["outcome"] == "no_answer"),
            "errors": sum(1 for r in neg if r["error"]),
            "slug_rank_histogram": histogram(neg),
            "false_match_scores": {
                "median": round(statistics.median(false_scores), 4) if false_scores else None,
                "max": round(max(false_scores), 4) if false_scores else None,
            },
        },
        "latency_ms": {
            "sla_ms": SLA_MS,
            "within_sla": len(within_sla),
            "within_sla_share": round(len(within_sla) / len(results), 4) if results else None,
            "median": int(statistics.median(lat)) if lat else None,
            "p95": lat[int(len(lat) * 0.95)] if len(lat) > 20 else (lat[-1] if lat else None),
            "max": lat[-1] if lat else None,
            "comparable": workers == 1,
        },
        "wall_s": round(wall_s, 1),
    }
    return out


def write_summary_unlabelled(path, meta, met):
    """Write the summary of a run of `--photos-dir`.

    The photos hold no ground truth, so the file states no share and no recall.
    It states what ran, what came back, and how long it took. A person reads the
    answers at the page `/runs` of `scripts/review_server.py`.
    """
    unl = met["unlabelled"]
    lat = met["latency_ms"]

    def num(value, fmt="%s"):
        return "\u2014" if value is None else fmt % value

    lines = [
        "# Run %s" % meta["run_id"],
        "",
        "**A run of a plain directory.** The photos hold no ground truth. This run",
        "records the answer of the backend. It states no correctness, no share, and",
        "no recall.",
        "",
        "| Field | Value |",
        "|---|---|",
        "| Backend | `%s` \u2014 %s |" % (meta["backend"]["id"],
                                          meta["backend"].get("label", "")),
        "| Photos directory | `%s` |" % (meta["options"] or {}).get("photos_dir", ""),
        "| Started | %s |" % meta["started"],
        "| Photos | %d |" % unl["n"],
        "| Top-k asked | %d |" % met["top_k"],
        "| Scores returned | %s |" % ("yes" if met["has_scores"] else "no"),
        "| Wall time | %s s |" % met["wall_s"],
        "",
        "## The answers",
        "",
        "| Measure | Value |",
        "|---|---|",
        "| Photos with a candidate | %d |" % unl["answered"],
        "| Photos with no candidate | %d |" % unl["no_answer"],
        "| Errors | %d |" % unl["errors"],
        "| Median top score | %s |" % num(unl["top_score_median"], "%.4f"),
        "| Median gap, first to second | %s |" % num(unl["score_margin_median"], "%.4f"),
        "",
        "The top score and the gap are the only signals of the confidence here. A",
        "high score is not a proof of a correct answer. A person MUST read the",
        "photos at `/runs` to judge the answers.",
        "",
        "## Latency",
        "",
        "median %s ms, p95 %s ms, max %s ms. Comparable to the jury harness: %s." % (
            num(lat["median"]), num(lat["p95"]), num(lat["max"]),
            "yes" if lat["comparable"] else "no, the run used several workers"),
        "",
    ]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def write_summary(path, meta, met):
    if met.get("unlabelled"):
        write_summary_unlabelled(path, meta, met)
        return
    pos, neg = met["positive"], met["negative"]

    def pct(value):
        return "—" if value is None else "%.1f%%" % (100 * value)

    sub = met.get("subset")
    lines = [
        "# Run %s" % meta["run_id"],
        "",
    ]
    if sub:
        lines += [
            "**A repeat run.** It holds the %d photos of `%s` that failed at depth %d,"
            % (sub["n"], sub["based_on"], sub["rerun_depth"]),
            "out of the %d photos of that run. The shares below describe those photos"
            % (sub["photos_in_earlier_run"] or 0),
            "only. They are NOT the shares of the whole set.",
            "",
            "| Of the repeated photos | Count |",
            "|---|---|",
            "| Correct at rank 1 now | %d |" % sub["recovered_at_1"],
            "| Inside the depth now | %d |" % sub["recovered_at_depth"],
            "| Still failing | %d |" % sub["still_failing"],
            "",
        ]
    lines += [
        "| Field | Value |",
        "|---|---|",
        "| Backend | `%s` — %s |" % (meta["backend"]["id"], meta["backend"].get("label", "")),
        "| Started | %s |" % meta["started"],
        "| Queries | %d (positive %d, negative %d, variant %d, no match %d) |" % (
            met["queries"]["total"], met["queries"]["positive"],
            met["queries"]["negative"], met["queries"]["variant"],
            met["queries"].get("no_match", 0)),
        "| Top-k asked | %d |" % met["top_k"],
        "| Scores returned | %s |" % ("yes" if met["has_scores"] else "no"),
        "| Wall time | %s s |" % met["wall_s"],
        "",
        "## Positive photos",
        "",
        "| Measure | Value |",
        "|---|---|",
        "| n | %d |" % pos["n"],
        "| Match share (R@1), target 90-100%% | %s |" % pct(pos["match_share"]),
        "| F1 top-1 | %s |" % ("—" if not pos.get("f1_at_1") else
                               "%.4f" % pos["f1_at_1"]["f1"]),
        "| F1 top-5 | %s |" % ("—" if not pos.get("f1_at_5") else
                               "%.4f" % pos["f1_at_5"]["f1"]),
        "| Near-duplicate confusion | %d |" % pos.get("near_duplicate_confusion", 0),
        "| R@1 | %s |" % pct(pos["recall_at_1"]),
        "| R@5 | %s |" % pct(pos["recall_at_5"]),
        "| R@10 | %s |" % pct(pos["recall_at_10"]),
        "| MRR | %s |" % ("—" if pos["mrr"] is None else "%.4f" % pos["mrr"]),
        "| No answer | %d |" % pos["no_answer"],
        "| Errors | %d |" % pos["errors"],
        "",
        "Rank of the true slug: `%s`" % json.dumps(pos["rank_histogram"], sort_keys=True),
        "",
        "## Negative photos",
        "",
        "A negative photo shows a different wine. Only a Top-1 answer with that",
        "slug is a proven error. The other outcomes are not successes.",
        "",
        "| Outcome | Count |",
        "|---|---|",
        "| False match at rank 1 | %d |" % neg["false_match_at_1"],
        "| Another slug at rank 1 (unverifiable) | %d |" % neg["other_slug_at_1"],
        "| No answer | %d |" % neg["no_answer"],
        "| Errors | %d |" % neg["errors"],
        "",
        "The slug appeared anywhere in the top-%d for %d of %d negative photos."
        % (met["top_k"], neg["false_match_in_top_k"], neg["n"]),
        "",
    ]
    nom = met.get("no_match")
    if nom:
        lines += [
            "## Photos with no match in the catalogue",
            "",
            "A reviewer put these photos under the NULL wine: no card of the",
            "catalogue shows that wine. No answer is the only correct outcome, and",
            "every answered card is a false match.",
            "",
            "| Measure | Value |",
            "|---|---|",
            "| n | %d |" % nom["n"],
            "| Refused (correct) | %d |" % nom["rejected"],
            "| Rejection rate | %s |" % pct(nom["rejection_rate"]),
            "| False match at rank 1 | %d |" % nom["false_match_at_1"],
            "| Errors | %d |" % nom["errors"],
            "",
        ]
        if nom["false_match_scores"]["max"] is not None:
            lines += [
                "The score of a false match here reached %s at most, and %s in the"
                % (nom["false_match_scores"]["max"],
                   nom["false_match_scores"]["median"]),
                "median. A threshold that refuses these photos MUST stand above that",
                "value.",
                "",
            ]
    lines += [
        "## Latency",
        "",
        "Within the SLA of %s ms: %s of the photos." % (
            met["latency_ms"]["sla_ms"], pct(met["latency_ms"]["within_sla_share"])),
        "",
        "median %s ms, p95 %s ms, max %s ms. Comparable to the jury harness: %s." % (
            met["latency_ms"]["median"], met["latency_ms"]["p95"],
            met["latency_ms"]["max"],
            "yes" if met["latency_ms"]["comparable"] else "no, the run used several workers"),
        "",
    ]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
