#!/usr/bin/env python3
"""Report one run of the cluster rule re-rank against its base run.

Read `docs/plans/05_cluster-label-rules.md`. The run MUST come from the backend
`svm-label-gw-cluster-rules`, which asks for `explain=1`, so each re-ranked row holds
the answers and the scores of the rule.

The report states:

- R@1, R@5 and MRR of the positive photos, and the rejected negative photos, for the
  base and for the re-rank, on the photos that both runs answered;
- the wins, the losses, and the exact McNemar test;
- the same numbers by mode (`sheet`, `verdict`);
- a replay over the clusters that exist without the `confusion` signal. That signal
  comes from match runs over the same test photos. The replay keeps only the cards
  that links of the other signals join to the rank-1 card. It needs no VLM call,
  because the VLM answered about the whole cluster;
- a replay with a second score, found after the partial run of 2026-09-23 and
  therefore post hoc: an answer that equals the expected answer of no card gives no
  evidence. The served score gives -1 to every card with another expected answer.
  This replay reads the questions of the rules file, so a report of an older run
  MUST name the rules file of that run with `--rules`;
- the paired numbers for each half of the wines. Plan 05 asks that a change that
  was chosen after an earlier run is measured on one half and reported on the other;
- the positive «Фантом» photos;
- the base score gap of each change;
- the latency.

Run:
    python3 scripts/cluster_rules_report.py runs/<cluster-rules run>
    python3 scripts/cluster_rules_report.py runs/<run> --base runs/<base run>
    python3 scripts/cluster_rules_report.py runs/<older run> --rules work/<rules file of that run>

It writes `cluster-rules-report.md` and `cluster-rules-report.json` into the run
directory and prints the Markdown.
"""
import argparse
import collections
import hashlib
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402
from cluster_rules import load_rules, normalize  # noqa: E402
from compare_runs import exact_mcnemar, load_run  # noqa: E402

BASE_RUN = "2026-09-23T121203Z-svm-label-gw-difference-alpha-patches"
GAPS = (0.005, 0.01, 0.02, 0.05)


def correct(row, top1):
    """True when `top1` is the right answer for the photo of `row`."""
    if top1 is None:
        return False
    if row["label"] == "positive":
        return top1 in set(row.get("truth") or [row["slug"]])
    return top1 != row["slug"]


def top1(row):
    cands = row.get("candidates") or []
    return cands[0]["slug"] if cands else None


def rule_explain(row):
    """The explain record of the cluster rule step, or None."""
    for c in row.get("candidates") or []:
        e = c.get("explain")
        if isinstance(e, dict) and e.get("kind") == "cluster_rules":
            return e
    return None


def base_scores(row):
    """slug -> the score of the card before the cluster rule step."""
    out = {}
    for c in row.get("candidates") or []:
        e = c.get("explain")
        if isinstance(e, dict) and e.get("kind") == "cluster_rules":
            out[c["slug"]] = e.get("base_score")
    return out


def recall(rows, depth):
    pos = [r for r in rows if r["label"] == "positive"]
    hit = sum(1 for r in pos if r.get("rank_of_truth") and r["rank_of_truth"] <= depth)
    return hit / len(pos) if pos else 0.0


def mrr(rows):
    pos = [r for r in rows if r["label"] == "positive"]
    return sum(1.0 / r["rank_of_truth"] for r in pos if r.get("rank_of_truth")) / max(1, len(pos))


class Union:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def join(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def no_confusion_union(clusters):
    """The components of the links that hold a signal other than `confusion`."""
    u = Union()
    for c in clusters:
        for link in c.get("links") or []:
            if set(link.get("by") or []) - {"confusion"}:
                u.join(link["a"], link["b"])
    return u


def unseen_is_no_evidence(rule, answers):
    """The post hoc score: an answer that no card expects gives no evidence.

    Else the same as the served score: +1 for an equal answer, -1 for another
    expected answer, 0 for a null expected answer or an answer with no value.
    """
    slugs = rule["slugs"]
    scores = {s: 0 for s in slugs}
    for q in rule.get("questions") or []:
        if not q.get("valid"):
            continue
        got = normalize((answers or {}).get(q["id"]))
        if got is None:
            continue
        want = {s: normalize(q["answers"].get(s)) for s in slugs}
        if got not in want.values():
            continue
        for s in slugs:
            if want[s] is not None:
                scores[s] += 1 if want[s] == got else -1
    return scores


def replay_top1(explain, union=None, rule=None):
    """The rank-1 card of a replay of the recorded answers.

    `union` keeps only the cards that links of other signals than `confusion` join to
    the rank-1 card. `rule` replaces the served score with `unseen_is_no_evidence`.
    """
    window = explain.get("window") or []
    if not window:
        return None
    members = window
    if union is not None:
        root = union.find(window[0])
        members = [s for s in window if union.find(s) == root]
    if len(members) < 2 or explain.get("error"):
        return window[0]
    if explain.get("mode") == "sheet":
        scores = (unseen_is_no_evidence(rule, explain.get("answers")) if rule
                  else explain.get("scores") or {})
        return sorted(members, key=lambda s: (-scores.get(s, 0), members.index(s)))[0]
    chosen = explain.get("chosen")
    return chosen if chosen in members else window[0]


def half_of(slug):
    """The half of the wines that holds `slug`, `A` or `B`, by the SHA-1 of the slug.

    The split does not change, so every report uses the same two halves.
    """
    return "AB"[int(hashlib.sha1(slug.encode("utf-8")).hexdigest(), 16) % 2]


def paired_counts(pairs, new_top):
    """Wins and losses of the new answer against the base answer."""
    wins = losses = 0
    for base, row in pairs:
        b, n = correct(base, top1(base)), correct(row, new_top(row))
        wins += int(n and not b)
        losses += int(b and not n)
    return wins, losses


def fmt_p(p):
    return "%.2g" % p if p < 0.001 else "%.3f" % p


def main():
    ap = argparse.ArgumentParser(description="Report a cluster rule run against its base")
    ap.add_argument("run", help="the run directory of the cluster rule backend")
    ap.add_argument("--base", default="", help="the base run. The default is %s" % BASE_RUN)
    ap.add_argument("--rules", default="",
                    help="the rules file of the run, for the post hoc score. The default "
                         "is the current rules file")
    args = ap.parse_args()
    common.select_dataset(None)
    base_path = args.base or os.path.join(common.RUNS_DIR, BASE_RUN)
    run_id, run = load_run(args.run)
    base_id, base = load_run(base_path)
    run_dir = args.run if os.path.isdir(args.run) else os.path.dirname(args.run)

    keys = sorted(k for k in run if k in base)
    dropped = sum(1 for k in keys if run[k].get("image_sha256") != base[k].get("image_sha256"))
    keys = [k for k in keys if run[k].get("image_sha256") == base[k].get("image_sha256")]
    pairs = [(base[k], run[k]) for k in keys]
    pos = [(b, r) for b, r in pairs if r["label"] == "positive"]
    neg = [(b, r) for b, r in pairs if r["label"] == "negative"]

    clusters = (json.load(open(common.CLUSTERS_FILE, encoding="utf-8")) or {}).get("clusters") or []
    cluster_id = {}
    for c in clusters:
        for s in c["slugs"]:
            cluster_id[s] = c["id"]
    union = no_confusion_union(clusters)

    if args.rules:
        with open(args.rules, encoding="utf-8") as fh:
            rules = json.load(fh)["clusters"]
    else:
        rules = load_rules()["clusters"]
    out_rules = args.rules or "the current rules file"

    def variant(restrict, rescore):
        """A function row -> rank-1 card for one replay."""
        def pick(row):
            e = rule_explain(row)
            if not e:
                return top1(row)
            rule = rules.get(e.get("cluster")) if rescore else None
            if rescore and rule is None:
                return top1(row)
            return replay_top1(e, union if restrict else None, rule)
        return pick

    served = lambda row: top1(row)                                  # noqa: E731
    replay = variant(True, False)

    out = {"run": run_id, "base_run": base_id, "pairs": len(pairs), "dropped": dropped,
           "positives": len(pos), "negatives": len(neg), "rules": out_rules}
    for name, rows in (("base", [b for b, _ in pairs]), ("rerank", [r for _, r in pairs])):
        out[name] = {"r1": recall(rows, 1), "r5": recall(rows, 5), "mrr": mrr(rows),
                     "negatives_rejected": sum(1 for r in rows if r["label"] == "negative"
                                               and correct(r, top1(r))) / max(1, len(neg))}
    w, l = paired_counts(pos, served)
    out["positives_paired"] = {"wins": w, "losses": l, "p": exact_mcnemar(w, l)}
    w, l = paired_counts(neg, served)
    out["negatives_paired"] = {"wins": w, "losses": l, "p": exact_mcnemar(w, l)}

    # where the step acted
    acted = [(b, r) for b, r in pairs if rule_explain(r)]
    modes = collections.defaultdict(lambda: collections.Counter())
    for b, r in acted:
        e = rule_explain(r)
        m = modes[e["mode"]]
        m["triggered"] += 1
        m["changed"] += int(bool(e.get("changed")))
        m["vlm_failed"] += int(bool(e.get("error")))
        m["cached"] += int(bool(e.get("cached")))
        bc, nc = correct(b, top1(b)), correct(r, top1(r))
        m["wins"] += int(nc and not bc)
        m["losses"] += int(bc and not nc)
        m["positives"] += int(r["label"] == "positive")
    out["acted"] = {"triggered": len(acted), "modes": {k: dict(v) for k, v in modes.items()}}

    # the replay without the confusion signal
    w, l = paired_counts(pos, replay)
    hits = sum(1 for _, r in pos if correct(r, replay(r)))
    still = sum(1 for _, r in acted if replay_top1(rule_explain(r), union) is not None
                and len([s for s in rule_explain(r).get("window") or []
                         if union.find(s) == union.find(rule_explain(r)["window"][0])]) >= 2)
    wn, ln = paired_counts(neg, replay)
    out["no_confusion_replay"] = {
        "triggered": still, "r1": hits / max(1, len(pos)),
        "positives_paired": {"wins": w, "losses": l, "p": exact_mcnemar(w, l)},
        "negatives_paired": {"wins": wn, "losses": ln, "p": exact_mcnemar(wn, ln)}}

    # the four variants: the served score or the post hoc score, over all clusters or
    # over the clusters without the confusion signal
    out["variants"] = []
    for name, restrict, rescore in (("served score, all clusters", False, False),
                                    ("served score, no confusion links", True, False),
                                    ("post hoc score, all clusters", False, True),
                                    ("post hoc score, no confusion links", True, True)):
        pick = served if not (restrict or rescore) else variant(restrict, rescore)
        w, l = paired_counts(pos, pick)
        wn, ln = paired_counts(neg, pick)
        out["variants"].append({
            "name": name, "r1": sum(1 for _, r in pos if correct(r, pick(r))) / max(1, len(pos)),
            "wins": w, "losses": l, "p": exact_mcnemar(w, l),
            "neg_wins": wn, "neg_losses": ln, "neg_p": exact_mcnemar(wn, ln)})

    # the two halves of the wines
    out["halves"] = {}
    for h in "AB":
        hp = [(b, r) for b, r in pos if half_of(r["slug"]) == h]
        hn = [(b, r) for b, r in neg if half_of(r["slug"]) == h]
        wins, losses = paired_counts(hp, served)
        neg_wins, neg_losses = paired_counts(hn, served)
        out["halves"][h] = {
            "positives": len(hp), "negatives": len(hn),
            "base_r1": sum(1 for b, _ in hp if correct(b, top1(b))) / max(1, len(hp)),
            "rerank_r1": sum(1 for _, r in hp if correct(r, top1(r))) / max(1, len(hp)),
            "wins": wins, "losses": losses, "p": exact_mcnemar(wins, losses),
            "neg_wins": neg_wins, "neg_losses": neg_losses,
            "neg_p": exact_mcnemar(neg_wins, neg_losses)}

    # «Фантом»
    fan = [(b, r) for b, r in pos if "fantom" in r["slug"]]
    out["fantom"] = {"positives": len(fan),
                     "base_hits": sum(1 for b, _ in fan if correct(b, top1(b))),
                     "rerank_hits": sum(1 for _, r in fan if correct(r, top1(r))),
                     "post_hoc_hits": sum(1 for _, r in fan if correct(r, variant(False, True)(r)))}

    # the base score gap of each change
    gap_rows = collections.defaultdict(collections.Counter)
    clusters_wl = collections.defaultdict(collections.Counter)
    for b, r in acted:
        e = rule_explain(r)
        if not e.get("changed"):
            continue
        scores = base_scores(r)
        old, new = e["window"][0], top1(r)
        gap = (scores.get(old) or 0) - (scores.get(new) or 0)
        bucket = next(("< %.3f" % g for g in GAPS if gap < g), ">= %.3f" % GAPS[-1])
        bc, nc = correct(b, top1(b)), correct(r, top1(r))
        verdict = "win" if nc and not bc else "loss" if bc and not nc else "neutral"
        gap_rows[bucket][verdict] += 1
        clusters_wl[cluster_id.get(old, "?")][verdict] += 1
    out["gaps"] = {k: dict(v) for k, v in gap_rows.items()}
    out["clusters"] = {k: dict(v) for k, v in clusters_wl.items()}

    # latency
    lat_on = [r["latency_ms"] for _, r in acted if r.get("latency_ms") is not None]
    lat_off = [r["latency_ms"] for _, r in pairs if not rule_explain(r)
               and r.get("latency_ms") is not None]
    vlm = [rule_explain(r)["ms"] for _, r in acted
           if not rule_explain(r).get("cached") and rule_explain(r).get("ms")]
    out["latency"] = {
        "triggered_median_ms": statistics.median(lat_on) if lat_on else None,
        "other_median_ms": statistics.median(lat_off) if lat_off else None,
        "vlm_calls": len(vlm), "vlm_median_ms": statistics.median(vlm) if vlm else None}

    md = render(out)
    with open(os.path.join(run_dir, "cluster-rules-report.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    with open(os.path.join(run_dir, "cluster-rules-report.md"), "w", encoding="utf-8") as fh:
        fh.write(md)
    print(md)


def render(o):
    b, n = o["base"], o["rerank"]
    pp, np_ = o["positives_paired"], o["negatives_paired"]
    lines = [
        "# Cluster rule re-rank: %s" % o["run"], "",
        "Base: `%s`. Paired photos: %d (%d positive, %d negative). Dropped pairs with "
        "different bytes: %d." % (o["base_run"], o["pairs"], o["positives"], o["negatives"],
                                  o["dropped"]), "",
        "| Metric | Base | Re-rank |", "|---|---:|---:|",
        "| R@1 of the positives | %.4f | %.4f |" % (b["r1"], n["r1"]),
        "| R@5 of the positives | %.4f | %.4f |" % (b["r5"], n["r5"]),
        "| MRR of the positives | %.4f | %.4f |" % (b["mrr"], n["mrr"]),
        "| Negatives rejected | %.4f | %.4f |" % (b["negatives_rejected"], n["negatives_rejected"]),
        "",
        "Positives: %d wins, %d losses, exact McNemar p %s." % (pp["wins"], pp["losses"], fmt_p(pp["p"])),
        "Negatives: %d wins, %d losses, exact McNemar p %s." % (np_["wins"], np_["losses"], fmt_p(np_["p"])),
        "", "## Where the step acted", "",
        "The step acted on %d of %d photos." % (o["acted"]["triggered"], o["pairs"]), "",
        "| Mode | Acted | Positives | Changed | Wins | Losses | VLM failed | From cache |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for mode, m in sorted(o["acted"]["modes"].items()):
        lines.append("| %s | %d | %d | %d | %d | %d | %d | %d |" % (
            mode, m.get("triggered", 0), m.get("positives", 0), m.get("changed", 0),
            m.get("wins", 0), m.get("losses", 0), m.get("vlm_failed", 0), m.get("cached", 0)))
    r = o["no_confusion_replay"]
    lines += [
        "", "## The clusters without the `confusion` signal (replay)", "",
        "The replay keeps only the cards that links of the other signals join to the "
        "rank-1 card. The step then acts on %d photos." % r["triggered"], "",
        "R@1 of the positives: %.4f. Positives: %d wins, %d losses, exact McNemar p %s. "
        "Negatives: %d wins, %d losses, p %s." % (
            r["r1"], r["positives_paired"]["wins"], r["positives_paired"]["losses"],
            fmt_p(r["positives_paired"]["p"]), r["negatives_paired"]["wins"],
            r["negatives_paired"]["losses"], fmt_p(r["negatives_paired"]["p"])),
        "", "## The four variants", "",
        "The served score is the design of the plan. The post hoc score was chosen after "
        "the partial run: an answer that no card expects gives no evidence. Both replays "
        "reuse the recorded answers. The post hoc score reads the questions of %s." % (
            "`%s`" % o["rules"] if o["rules"].endswith(".json") else o["rules"]), "",
        "| Variant | R@1 | Wins | Losses | p | Negative wins | Negative losses |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ] + ["| %s | %.4f | %d | %d | %s | %d | %d |" % (
        v["name"], v["r1"], v["wins"], v["losses"], fmt_p(v["p"]), v["neg_wins"],
        v["neg_losses"]) for v in o["variants"]] + [
        "", "## The two halves of the wines", "",
        "The halves split the wines by the SHA-1 of the slug. A change that was chosen "
        "after an earlier run is measured on one half and reported on the other half.", "",
        "| Half | Positives | Base R@1 | Re-rank R@1 | Wins | Losses | p | Negatives | "
        "Negative wins | Negative losses |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ] + ["| %s | %d | %.4f | %.4f | %d | %d | %s | %d | %d | %d |" % (
        h, v["positives"], v["base_r1"], v["rerank_r1"], v["wins"], v["losses"],
        fmt_p(v["p"]), v["negatives"], v["neg_wins"], v["neg_losses"])
        for h, v in sorted(o["halves"].items())] + [
        "", "## «Фантом»", "",
        "%d positive photos: the base answers %d right, the re-rank %d, the post hoc score %d." % (
            o["fantom"]["positives"], o["fantom"]["base_hits"], o["fantom"]["rerank_hits"],
            o["fantom"]["post_hoc_hits"]),
        "", "## The base score gap of each change", "",
        "| Gap below rank 1 | Wins | Losses | Neutral |", "|---|---:|---:|---:|",
    ]
    for k in sorted(o["gaps"], key=lambda x: (x.startswith(">="), float(x.split()[-1]))):
        g = o["gaps"][k]
        lines.append("| %s | %d | %d | %d |" % (k, g.get("win", 0), g.get("loss", 0),
                                              g.get("neutral", 0)))
    worst = sorted(o["clusters"].items(), key=lambda kv: (-kv[1].get("loss", 0),
                                                          -kv[1].get("win", 0)))[:12]
    lines += ["", "## Clusters with the most changes", "",
              "| Cluster | Wins | Losses | Neutral |", "|---|---:|---:|---:|"]
    for cid, v in worst:
        lines.append("| %s | %d | %d | %d |" % (cid, v.get("win", 0), v.get("loss", 0),
                                               v.get("neutral", 0)))
    lt = o["latency"]
    lines += ["", "## Latency", "",
              "Median latency: %s ms where the step acted, %s ms elsewhere. VLM calls: %d, "
              "median %s ms." % (lt["triggered_median_ms"], lt["other_median_ms"],
                                 lt["vlm_calls"], lt["vlm_median_ms"]), ""]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
