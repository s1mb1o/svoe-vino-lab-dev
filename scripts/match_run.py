"""Send every annotated photo to a match backend and record the result.

The photo set of this project is the ground truth. This tool measures a
recognizer against it and writes one directory per run under `runs_dir`, so two
runs can be compared.

Run:

    python3 scripts/match_run.py --backend official-api
    python3 scripts/match_run.py --backend organizers --limit 50
    python3 scripts/match_run.py --backend official-api --dry-run

`--photos-dir DIR` replaces the photo set of the project with a plain directory
of photos. Such a directory holds no ground truth, so the run records the answer
of the backend and states no correctness:

    python3 scripts/match_run.py --backend svm-siglip2-448 --photos-dir ~/photos

The run directory holds:

    run.json          what ran: the backend, the options, the counts
    queries.tsv       the manifest in the form of the jury harness
    queries.jsonl     the same rows with the truth of each photo
    predictions.jsonl the answer in the format of the organizers
    results.jsonl     the full record of every photo, with every candidate
    metrics.json      the aggregate
    summary.md        the same numbers for a human

A photo of `--photos-dir` carries the label `unlabelled`. It holds no true slug,
so the run reports the candidates, the latency, and the errors, and it reports no
share and no recall.

A `positive` photo shows the wine of its slug. A `negative` photo shows a
different wine, so the backend is wrong when it answers with that slug at rank 1.
A `variant` photo shows the wine in another bottle and stays out of the set
unless `--variants` asks for it.
"""
import argparse
import collections
import concurrent.futures
import hashlib
import json
import os
import statistics
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402
import match_backends  # noqa: E402

LABELS_IN_SET = ("positive", "negative", "variant")
# The label of a photo of `--photos-dir`. The directory holds no ground truth.
UNLABELLED = "unlabelled"
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}


# ---------------------------------------------------------------- the query set


def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError) as exc:
        print("warning: cannot read %s: %s" % (path, exc), file=sys.stderr)
        return default


def load_excluded():
    return (load_json(common.EXCLUDED_SLUGS_FILE, {}) or {}).get("excluded") or {}


def load_groups():
    """Return slug -> the set of the slugs of its variant group."""
    blob = load_json(common.VARIANT_GROUPS_FILE, {}) or {}
    out = {}
    for group in (blob.get("groups") or []):
        slugs = [s for s in (group.get("slugs") or []) if isinstance(s, str)]
        for slug in slugs:
            out[slug] = set(slugs)
    return out


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_queries(variants="off", only="all"):
    """Return the query rows, in a stable order.

    A photo enters the set when it holds a label of `LABELS_IN_SET` and its file
    is present. A photo stays out when its slug is excluded, when the label is
    `unusable`, when the entry is an agent proposal with no label, or when the
    entry is marked for deletion.
    """
    labels = (load_json(common.LABEL_FILE, {}) or {}).get("labels") or {}
    excluded = load_excluded()
    groups = load_groups() if variants == "group" else {}
    rows = []
    skipped = collections.Counter()

    for slug in sorted(labels):
        if slug in excluded:
            skipped["excluded slug"] += len(labels[slug])
            continue
        for fname in sorted(labels[slug]):
            entry = labels[slug][fname] or {}
            label = entry.get("label")
            if label not in LABELS_IN_SET:
                skipped["no label" if not label else label] += 1
                continue
            if entry.get("delete"):
                skipped["marked for deletion"] += 1
                continue
            if label == "variant" and variants == "off":
                skipped["variant"] += 1
                continue
            if only != "all" and label != only:
                skipped["other label"] += 1
                continue
            path = os.path.join(common.PHOTO_DIR, slug, fname)
            if not os.path.isfile(path):
                skipped["file not found"] += 1
                continue
            truth = [slug]
            if label == "variant" and variants == "group":
                truth = sorted(groups.get(slug) or {slug})
            rows.append({
                "image_path": "%s/%s" % (slug, fname),
                "abs_path": path,
                "slug": slug,
                "label": label,
                "truth": truth if label in ("positive", "variant") else [],
            })

    rows.sort(key=lambda r: r["image_path"])
    for i, row in enumerate(rows, 1):
        row["query_id"] = "q-%06d" % i
    return rows, skipped


def build_dir_queries(photos_dir):
    """Return the query rows of a plain directory of photos.

    The directory holds no ground truth. Every row carries the label
    `unlabelled`, an empty truth, and an empty slug. The walk is recursive, and
    `image_path` is the path of the file against the directory.
    """
    root = os.path.abspath(os.path.expanduser(photos_dir))
    if not os.path.isdir(root):
        sys.exit("error: --photos-dir is not a directory: %s" % root)
    rows = []
    skipped = collections.Counter()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        for fname in sorted(filenames):
            if fname.startswith("."):
                skipped["hidden file"] += 1
                continue
            if os.path.splitext(fname)[1].lower() not in IMAGE_EXT:
                skipped["not an image"] += 1
                continue
            path = os.path.join(dirpath, fname)
            rows.append({
                "image_path": os.path.relpath(path, root),
                "abs_path": path,
                "slug": "",
                "label": UNLABELLED,
                "truth": [],
            })
    rows.sort(key=lambda r: r["image_path"])
    for i, row in enumerate(rows, 1):
        row["query_id"] = "q-%06d" % i
    return rows, skipped


# --------------------------------------------------------------- the repeat of a run


def load_previous(path):
    """Return `image_path` -> the row of `results.jsonl` of an earlier run.

    The key is the path of the photo, not `query_id`. A `query_id` states the place
    in one query set, and the set changes when a label changes. The path of the
    photo names the same photo in every run.
    """
    if os.path.isdir(path):
        path = os.path.join(path, "results.jsonl")
    if not os.path.exists(path):
        raise SystemExit("error: no results.jsonl in the earlier run: %s" % path)
    out = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("image_path"):
                out[rec["image_path"]] = rec
    if not out:
        raise SystemExit("error: the earlier run holds no row: %s" % path)
    return out


def failed_before(rec, depth):
    """Answer whether this photo counts as a failure at the depth `depth`.

    `depth` is the number of candidates that count as an answer. With `depth` 1 a
    positive photo MUST stand at rank 1. With `depth` 10 the true slug MUST stand
    inside the first 10 candidates, which is the reading of "not in R@10".

    A positive or a variant photo fails when its true slug is absent or deeper
    than `depth`. A negative photo fails when its own slug DID come back inside
    `depth`, because that slug is the wrong answer. A request that failed counts
    as a failure, whatever the depth.
    """
    if rec.get("error"):
        return True
    rank = rec.get("rank_of_truth")
    if rec.get("label") == "negative":
        return rank is not None and rank <= depth
    return rank is None or rank > depth


def select_failures(rows, previous, depth):
    """Keep the rows that failed in the earlier run. Return the rows and a report."""
    kept, report = [], collections.Counter()
    for row in rows:
        rec = previous.get(row["image_path"])
        if rec is None:
            report["not in the earlier run"] += 1
            continue
        if failed_before(rec, depth):
            row["previous"] = {
                "query_id": rec.get("query_id"),
                "rank_of_truth": rec.get("rank_of_truth"),
                "outcome": rec.get("outcome"),
                "predicted_slug": rec.get("predicted_slug"),
                "error": rec.get("error"),
            }
            kept.append(row)
        else:
            report["passed at depth %d" % depth] += 1
    now = {r["image_path"] for r in rows}
    gone = sum(1 for image_path in previous if image_path not in now)
    if gone:
        report["in the earlier run, not in the set now"] = gone
    return kept, report


# ------------------------------------------------------------------- the scoring


def judge(row, candidates, negative_strict):
    """Return the judgement of one answer.

    A positive or a variant photo is scored by the rank of its true slug. A
    negative photo carries no positive truth: the reviewer stated that the photo
    is NOT this wine and did not state which wine it is. So only one outcome is
    a proven error, and no outcome is a proven success.
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


def subset_block(results, parent, depth, photos_in_earlier_run):
    """Return the record of a repeat run: what it covers and what it changed.

    Every photo of a repeat run failed in the earlier run, so the shares of this
    run describe the failures only. They are NOT the shares of the whole set. The
    useful number is how many photos the repeat put right.
    """
    recovered_at_1 = recovered_at_depth = still = 0
    for r in results:
        if r["label"] == "negative":
            ok = r["rank_of_truth"] is None or r["rank_of_truth"] > depth
        else:
            ok = r["rank_of_truth"] is not None and r["rank_of_truth"] <= depth
        if r["error"]:
            ok = False
        if ok:
            recovered_at_depth += 1
        else:
            still += 1
        if r["label"] != "negative" and r["rank_of_truth"] == 1:
            recovered_at_1 += 1
    return {
        "based_on": parent,
        "rerun_depth": depth,
        "photos_in_earlier_run": photos_in_earlier_run,
        "n": len(results),
        "recovered_at_1": recovered_at_1,
        "recovered_at_depth": recovered_at_depth,
        "still_failing": still,
        "note": ("Every photo of this run failed in the earlier run. The shares of "
                 "this run describe those photos only. They are NOT the shares of "
                 "the whole set."),
    }


# -------------------------------------------------------------------- the output


def git_commit():
    try:
        out = subprocess.run(["git", "-C", common.ROOT, "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or None
    except Exception:  # noqa: BLE001
        return None


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
        "| Queries | %d (positive %d, negative %d, variant %d) |" % (
            met["queries"]["total"], met["queries"]["positive"],
            met["queries"]["negative"], met["queries"]["variant"]),
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


# ---------------------------------------------------------------------- the run


def main():
    ap = argparse.ArgumentParser(
        description="Match every annotated photo against one backend")
    ap.add_argument("--backend", help="the id of a backend of backends.yaml")
    ap.add_argument("--list-backends", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="stop after N photos")
    ap.add_argument("--photos-dir", default="", metavar="DIR",
                    help="match the photos of this directory instead of the photo "
                         "set of the project. The directory holds no ground truth, "
                         "so the run records the candidates and states no "
                         "correctness. The walk is recursive")
    ap.add_argument("--only", choices=("all", "positive", "negative"), default="all")
    ap.add_argument("--variants", choices=("off", "strict", "group"), default="off",
                    help="take the variant photos into the set (default: off)")
    ap.add_argument("--negative-strict", action="store_true",
                    help="count the slug anywhere in the top-k as a false match")
    ap.add_argument("--workers", type=int, default=None,
                    help="how many requests to send at the same time. The default "
                         "is the key `workers` of the backend, or 1. A value of 1 "
                         "keeps the latency comparable to the jury harness")
    ap.add_argument("--from-run", default="", metavar="RUN",
                    help="repeat only the photos that failed in this earlier run "
                         "(the directory, or its results.jsonl)")
    ap.add_argument("--rerun-depth", type=int, default=1, metavar="K",
                    help="with --from-run: how many candidates count as an answer. "
                         "1 repeats every photo that was not correct at rank 1. "
                         "10 repeats every photo that was not in the first 10. "
                         "The default is 1.")
    ap.add_argument("--label", default="", help="a word for the run directory name")
    ap.add_argument("--dry-run", action="store_true",
                    help="build the query set and the manifests, call nothing")
    args = ap.parse_args()

    if args.list_backends:
        specs = match_backends.load_backends(common.BACKENDS_FILE)
        for bid, spec in sorted(specs.items()):
            print("%-16s %s" % (bid, spec.get("label") or ""))
            print("%-16s %s" % ("", spec.get("url")))
        return

    common.print_config()

    if args.photos_dir:
        for name, value, default in (("--from-run", args.from_run, ""),
                                     ("--only", args.only, "all"),
                                     ("--variants", args.variants, "off")):
            if value != default:
                sys.exit("error: %s needs the photo set of the project. It cannot "
                         "be used with --photos-dir." % name)
        rows, skipped = build_dir_queries(args.photos_dir)
        photos_dir = os.path.abspath(os.path.expanduser(args.photos_dir))
    else:
        photos_dir = ""
        rows, skipped = build_queries(variants=args.variants, only=args.only)

    parent = None
    if args.from_run:
        if args.rerun_depth < 1:
            sys.exit("error: --rerun-depth MUST be 1 or more")
        previous = load_previous(args.from_run)
        parent = os.path.basename(os.path.normpath(
            args.from_run[:-len("/results.jsonl")]
            if args.from_run.endswith("results.jsonl") else args.from_run))
        before = len(rows)
        rows, report = select_failures(rows, previous, args.rerun_depth)
        print("repeat of %s: %d of the %d photos of the earlier run failed at "
              "depth %d" % (parent, len(rows), len(previous), args.rerun_depth))
        for key in sorted(report):
            print("  %s: %d" % (key, report[key]))
        if before != len(previous):
            print("  note: the set holds %d photos now and held %d in the earlier run"
                  % (before, len(previous)))

    if args.limit:
        rows = rows[:args.limit]
    if not rows:
        if parent:
            sys.exit("nothing to repeat: every photo of %s passed at depth %d"
                     % (parent, args.rerun_depth))
        sys.exit("error: the query set is empty")
    counts = collections.Counter(r["label"] for r in rows)
    if photos_dir:
        print("photos directory: %s" % photos_dir)
    print("query set: %d photos (%s)" % (
        len(rows), ", ".join("%s %d" % (k, counts[k]) for k in sorted(counts))))
    if skipped:
        print("left out: %s" % ", ".join(
            "%s %d" % (k, v) for k, v in sorted(skipped.items())))
    if photos_dir:
        print("no ground truth: the run records the candidates and states no "
              "correctness")

    # State the rule for the variant photos and the count of the excluded slugs.
    # Both change the query set, and neither is visible in the counts above.
    if photos_dir:
        pass                               # a plain directory knows no variant
    elif args.variants == "off":
        print("variant photos: %d left out (--variants off)" % skipped["variant"])
    elif args.variants == "strict":
        print("variant photos: %d in the set; only the slug of the photo counts as\n"
              "                a true match (--variants strict)" % counts["variant"])
    else:
        print("variant photos: %d in the set; every slug of the variant group counts\n"
              "                as a true match (--variants group)" % counts["variant"])
    if not photos_dir:
        excluded = load_excluded()
        print("excluded slugs: %d in %s; %d photos left out"
              % (len(excluded), os.path.basename(common.EXCLUDED_SLUGS_FILE),
                 skipped["excluded slug"]))

    backend = None
    if not args.dry_run:
        if not args.backend:
            sys.exit("error: --backend is required. Use --list-backends.")
        backend = match_backends.build_backend(common.BACKENDS_FILE, args.backend)
        print("backend: %s (%s), top_k %d, timeout %.0fs"
              % (backend.id, backend.url, backend.top_k, backend.timeout))

    # How many requests go at the same time. `--workers` on the command line wins
    # over the key `workers` of the backend. The backend knows the rate that its
    # server takes; the command line knows the purpose of this one run.
    spec_workers, source = 1, "the default"
    if args.backend:
        try:
            spec = match_backends.load_backends(common.BACKENDS_FILE).get(args.backend)
            spec_workers = max(1, int((spec or {}).get("workers") or 1))
        except match_backends.BackendError:
            spec_workers = 1
    if args.workers is not None:
        workers, source = max(1, args.workers), "--workers"
    else:
        workers = spec_workers
        if spec_workers > 1:
            source = "the key `workers` of the backend %s" % args.backend
    print("requests at the same time: %d (%s)%s"
          % (workers, source, "" if workers == 1 else
             "; the latency is then NOT comparable to the jury harness"))

    stamp = time.strftime("%Y-%m-%dT%H%M%SZ", time.gmtime())
    repeat = ("repeat-d%d" % args.rerun_depth) if parent else ""
    # `dir` marks a run with no ground truth in the name of the directory, so the
    # table of the runs at `/runs` states the kind of the run at first sight.
    kind = "dir" if photos_dir else ""
    name = "-".join(x for x in (stamp, args.backend or "dry-run", kind, repeat,
                                args.label) if x)
    run_dir = os.path.join(common.RUNS_DIR, name)
    os.makedirs(run_dir, exist_ok=True)
    print("run directory: %s" % run_dir)

    print("sha256 of %d photos..." % len(rows))
    for row in rows:
        row["image_sha256"] = sha256_of(row["abs_path"])

    with open(os.path.join(run_dir, "queries.tsv"), "w", encoding="utf-8") as fh:
        fh.write("query_id\timage_path\n")
        for row in rows:
            fh.write("%s\t%s\n" % (row["query_id"], row["image_path"]))
    with open(os.path.join(run_dir, "queries.jsonl"), "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps({k: row[k] for k in (
                "query_id", "image_path", "image_sha256", "slug", "label", "truth")},
                ensure_ascii=False) + "\n")

    meta = {
        "run_id": name,
        "tool": "scripts/match_run.py",
        "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "git_commit": git_commit(),
        "options": {
            "backend": args.backend, "limit": args.limit, "only": args.only,
            "variants": args.variants, "negative_strict": args.negative_strict,
            "workers": workers, "dry_run": args.dry_run,
            # The page `/runs` reads this path to serve the photos of the run.
            "photos_dir": photos_dir,
        },
        "backend": match_backends.redact(backend.spec) if backend else None,
        "config": {key: value for key, value in common.CONFIG_PATHS},
        "query_set": {"total": len(rows), **{k: counts[k] for k in sorted(counts)}},
        "left_out": dict(skipped),
        "based_on": None if not parent else {
            "run_id": parent,
            "rerun_depth": args.rerun_depth,
            "rule": ("a positive photo whose true slug was absent or deeper than "
                     "rank %d, a negative photo whose own slug came back inside "
                     "rank %d, or a request that failed"
                     % (args.rerun_depth, args.rerun_depth)),
            "photos_in_earlier_run": len(previous) if parent else None,
        },
    }
    if args.dry_run:
        meta["finished"] = meta["started"]
        with open(os.path.join(run_dir, "run.json"), "w", encoding="utf-8") as fh:
            json.dump(meta, fh, ensure_ascii=False, indent=2, sort_keys=True)
        print("dry run: the manifests are written, no request was sent")
        return

    t_start = time.time()
    results = []
    lock = threading.Lock()
    pred_fh = open(os.path.join(run_dir, "predictions.jsonl"), "w", encoding="utf-8")
    res_fh = open(os.path.join(run_dir, "results.jsonl"), "w", encoding="utf-8")

    def one(row):
        cands, ms, status, error = backend.ask(row["abs_path"])
        verdict = judge(row, cands, args.negative_strict)
        rec = {
            "query_id": row["query_id"], "image_path": row["image_path"],
            "image_sha256": row["image_sha256"], "slug": row["slug"],
            "label": row["label"], "truth": row["truth"],
            "candidates": cands, "predicted_slug": verdict["predicted_slug"],
            "rank_of_truth": verdict["rank_of_truth"], "outcome": verdict["outcome"],
            "latency_ms": ms, "http_status": status, "error": error,
        }
        if row.get("previous"):
            rec["previous"] = row["previous"]     # what the earlier run answered
        return rec

    def write(rec):
        pred_fh.write(json.dumps({
            "query_id": rec["query_id"], "image_path": rec["image_path"],
            "image_sha256": rec["image_sha256"],
            "predicted_slug": rec["predicted_slug"], "latency_ms": rec["latency_ms"],
        }, ensure_ascii=False) + "\n")
        res_fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        pred_fh.flush()
        res_fh.flush()

    def hms(seconds):
        seconds = int(round(seconds))
        return "%d:%02d:%02d" % (seconds // 3600, seconds % 3600 // 60, seconds % 60)

    done = 0
    t_chunk = t_start

    def progress():
        # One line per chunk of 25 photos, and one line at the end. `chunk` is
        # the time of the last chunk. `ETA` uses the rate of the whole run.
        nonlocal t_chunk
        now = time.time()
        elapsed, left = now - t_start, len(rows) - done
        print("  %d/%d  chunk %.1fs  elapsed %s  ETA %s"
              % (done, len(rows), now - t_chunk, hms(elapsed),
                 hms(elapsed / done * left) if done else "?"), flush=True)
        t_chunk = now

    try:
        if workers > 1:
            with concurrent.futures.ThreadPoolExecutor(workers) as pool:
                for rec in pool.map(one, rows):
                    with lock:
                        results.append(rec)
                        write(rec)
                        done += 1
                        if done % 25 == 0 or done == len(rows):
                            progress()
        else:
            for row in rows:
                rec = one(row)
                results.append(rec)
                write(rec)
                done += 1
                if done % 25 == 0 or done == len(rows):
                    progress()
    except KeyboardInterrupt:
        print("\nstopped by the user after %d photos" % done)
    finally:
        pred_fh.close()
        res_fh.close()

    wall = time.time() - t_start
    met = metrics_of(results, backend, backend.top_k, args.negative_strict,
                     wall, workers, groups=load_groups())
    met["run_id"] = name
    if parent:
        met["subset"] = subset_block(results, parent, args.rerun_depth, len(previous))
    meta["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    meta["wall_s"] = round(wall, 1)
    meta["answered"] = len(results)
    with open(os.path.join(run_dir, "run.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2, sort_keys=True)
    with open(os.path.join(run_dir, "metrics.json"), "w", encoding="utf-8") as fh:
        json.dump(met, fh, ensure_ascii=False, indent=2, sort_keys=True)
    write_summary(os.path.join(run_dir, "summary.md"), meta, met)

    if met.get("unlabelled"):
        unl = met["unlabelled"]
        print("")
        print("no ground truth: %d photo(s), %d with a candidate, %d with none, "
              "%d error(s)" % (unl["n"], unl["answered"], unl["no_answer"],
                               unl["errors"]))
        print("median top score %s, median gap to the second candidate %s" % (
            unl["top_score_median"], unl["score_margin_median"]))
        print("latency: median %s ms, p95 %s ms" % (
            met["latency_ms"]["median"], met["latency_ms"]["p95"]))
        print("written: %s" % run_dir)
        print("read the answers at http://127.0.0.1:8154/runs")
        return

    pos, neg = met["positive"], met["negative"]
    print("")
    if met.get("subset"):
        sub = met["subset"]
        print("repeat of %s at depth %d: %d photo(s) repeated, %d correct at rank 1 "
              "now, %d inside the depth, %d still failing" % (
                  sub["based_on"], sub["rerun_depth"], sub["n"],
                  sub["recovered_at_1"], sub["recovered_at_depth"],
                  sub["still_failing"]))
        print("the shares below cover the repeated photos only")
    print("match share %s (target 90-100%%), F1@1 %s, F1@5 %s, near-duplicate "
          "confusion %d" % (
              pos["match_share"],
              (pos.get("f1_at_1") or {}).get("f1"),
              (pos.get("f1_at_5") or {}).get("f1") if pos.get("f1_at_5") else None,
              pos.get("near_duplicate_confusion", 0)))
    print("within the %d ms SLA: %s of the photos" % (
        met["latency_ms"]["sla_ms"], met["latency_ms"]["within_sla_share"]))
    print("positive %d: R@1 %s  R@5 %s  R@10 %s  errors %d" % (
        pos["n"], pos["recall_at_1"], pos["recall_at_5"], pos["recall_at_10"],
        pos["errors"]))
    print("negative %d: false match at 1 %d, another slug at 1 %d, no answer %d" % (
        neg["n"], neg["false_match_at_1"], neg["other_slug_at_1"], neg["no_answer"]))
    print("latency: median %s ms, p95 %s ms" % (
        met["latency_ms"]["median"], met["latency_ms"]["p95"]))
    print("written: %s" % run_dir)


if __name__ == "__main__":
    main()
