#!/usr/bin/env python3
"""Stage 10. Find the clusters of catalogue cards that the matcher can confuse.

The `vino-svoe.ru` catalogue holds one card per bottle, not one card per wine. Two
cards of one wine can differ only by the vintage or by the alcohol value. Two wines of
one product line can carry one label design. The matcher mixes up both kinds of pair.
A later re-rank step needs to know which cards stand in one group. This script finds
the groups over the WHOLE catalogue. It writes the file that the key `clusters.file`
of `config.yaml` names. The page `/clusters` of the review tool shows that file.

Four signals join two cards. A link records every signal that passed:

1. `name`: the same producer, the same name, and the same category after
   normalisation. The words of the producer are removed from the name, so the name
   «Абрау-Дюрсо Пино Нуар» of the producer «Абрау-Дюрсо» meets «Пино Нуар».
2. `photo`: the SigLIP 2 cosine of the two catalogue photos.
3. `label`: the SigLIP 2 cosine of the two label crops.
4. `confusion`: a match run answered card B at rank 1 for a positive photo of card A.

The vectors come from the index files of `svoe-vino-matcher`. The script calls no
service, so it can run while the pipeline uses gx10.

A cluster is a connected component over the links. Read
`docs/plans/04_catalog-clusters.md` for the rules and for the shape of the file.

Run:
    python3 scripts/10_clusters.py
    python3 scripts/10_clusters.py --show abrau-dyurso-pino-nuar-krasnoe-suhoe-12
    python3 scripts/10_clusters.py --photo-threshold 0.93 --no-confusion
    python3 scripts/10_clusters.py --run 2026-09-22T084237Z-svm-siglip2-448
"""
import argparse
import collections
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402
from common import log  # noqa: E402

try:
    import numpy as np
except ImportError:
    sys.exit("error: numpy is needed. Install it with `python3 -m pip install numpy`.")

SIGNALS = ("name", "photo", "label", "confusion")
# A link keeps at most this many of the photos that a run answered as the other card.
MAX_PHOTOS = 6
WORD = re.compile(r"[0-9a-zа-я]+")
LETTERS = re.compile(r"[a-zа-я]+")


def words(text):
    """The words of a field: lower case, `ё` as `е`, letters and digits only."""
    return WORD.findall((text or "").lower().replace("ё", "е"))


def load_catalog():
    out = {}
    with open(common.CATALOG_FILE, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rec = json.loads(line)
                out[rec["slug"]] = rec
    return out


def load_labels():
    """slug -> file -> label entry, from the label file of the dataset."""
    if not os.path.isfile(common.LABEL_FILE):
        return {}
    with open(common.LABEL_FILE, encoding="utf-8") as fh:
        return (json.load(fh) or {}).get("labels") or {}


# ------------------------------------------------------------------ the names

def name_key(rec):
    """The key of the `name` signal, or None.

    The name words are a sorted set, so a change of word order gives the same key.
    A name that holds only the words of the producer gives no key. Such a name
    would join every card of the producer whose name is the producer name.
    """
    producer = set(words(rec.get("producer")))
    rest = sorted(set(words(rec.get("name"))) - producer)
    if not producer or not rest:
        return None
    return (" ".join(sorted(producer)), " ".join(rest),
            " ".join(words(rec.get("category"))))


def grape_words(rec):
    """The grape words of a card, letters only, so `100 %` does not count."""
    return set(LETTERS.findall((rec.get("grapes") or "").lower().replace("ё", "е")))


def grapes_agree(one, two):
    """True when the grapes of one card are a subset of the grapes of the other.

    The name of a card does not always hold its grape. Measured on 2026-09-22: 32 of
    107 name pairs held different grapes. An example is the line «Иноходец» of
    «Вина Арпачина», which holds one card for each grape under one name. Those cards
    are different wines. A subset still agrees, because one card of a wine can list
    the main grape and the other card the whole blend: «Рислинг» against «Рислинг
    Рейнский». An empty field agrees with every field.
    """
    return not one or not two or one <= two or two <= one


def name_pairs(catalog):
    by_key = collections.defaultdict(list)
    for slug, rec in catalog.items():
        key = name_key(rec)
        if key:
            by_key[key].append(slug)
    grapes = {slug: grape_words(rec) for slug, rec in catalog.items()}
    pairs = set()
    for members in by_key.values():
        members.sort()
        for i, a in enumerate(members):
            for b in members[i + 1:]:
                if grapes_agree(grapes[a], grapes[b]):
                    pairs.add((a, b))
    return pairs


# ---------------------------------------------------------------- the vectors

class Index:
    """The vectors of one matcher index, as unit vectors, with a cosine lookup."""

    def __init__(self, path, catalog):
        if not os.path.isfile(path):
            sys.exit(f"error: the index file is not on disk: {path}")
        data = np.load(path, allow_pickle=False)
        slugs = [str(s) for s in data["slugs"]]
        vec = np.asarray(data["vectors"], dtype=np.float32)
        norm = np.linalg.norm(vec, axis=1)
        # A non-finite vector carries no information. The matcher once built an
        # index of such vectors, so this guard stays.
        keep = np.isfinite(vec).all(axis=1) & (norm > 0)
        keep &= np.array([s in catalog for s in slugs], dtype=bool)
        self.dropped_bad = int((~np.isfinite(vec).all(axis=1) | (norm <= 0)).sum())
        self.dropped_unknown = sorted({s for s in slugs if s not in catalog})
        self.path = path
        self.slugs = [s for s, k in zip(slugs, keep) if k]
        self.vec = vec[keep] / norm[keep, None]
        self.rows = collections.defaultdict(list)
        for i, s in enumerate(self.slugs):
            self.rows[s].append(i)
        self.sim = self.vec @ self.vec.T
        meta_path = path[:-len(".npz")] + ".meta.json" if path.endswith(".npz") else ""
        self.meta = {}
        if meta_path and os.path.isfile(meta_path):
            with open(meta_path, encoding="utf-8") as fh:
                self.meta = json.load(fh)

    def describe(self):
        built = self.meta.get("built_at_unix")
        return {
            "file": self.path,
            "index_id": self.meta.get("index_id"),
            "pipeline": self.meta.get("pipeline"),
            "source": self.meta.get("source", "photo"),
            "built_at": (time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(built))
                         if built else None),
            "vectors": len(self.slugs),
            "cards": len(self.rows),
            "dropped_non_finite": self.dropped_bad,
            "dropped_unknown_slugs": len(self.dropped_unknown),
        }

    def cosine(self, a, b):
        """The highest cosine over the vectors of two cards, or None."""
        ra, rb = self.rows.get(a), self.rows.get(b)
        if not ra or not rb:
            return None
        return float(self.sim[np.ix_(ra, rb)].max())

    def pairs(self, threshold):
        """Every pair of cards with a cosine at or above `threshold`."""
        iu, ju = np.triu_indices(len(self.slugs), 1)
        hit = self.sim[iu, ju] >= threshold
        out = {}
        for i, j in zip(iu[hit], ju[hit]):
            a, b = self.slugs[i], self.slugs[j]
            if a == b:
                continue
            key = (a, b) if a < b else (b, a)
            out[key] = max(out.get(key, -1.0), float(self.sim[i, j]))
        return out


# ------------------------------------------------------------- the confusions

def load_confusions(run_ids, catalog, labels):
    """Count the positive photos of card A that a run answered as card B.

    A photo counts only when the current label file still marks it `positive` in the
    folder of card A. An old run can hold a label that a reviewer changed later, or a
    photo that a reviewer moved to another card.
    """
    counts = collections.Counter()           # (a, b): photos of a answered as b
    photos = collections.defaultdict(list)
    report = []
    for run_id in run_ids:
        run_dir = os.path.join(common.RUNS_DIR, run_id)
        path = os.path.join(run_dir, "results.jsonl")
        if not os.path.isfile(path):
            sys.exit(f"error: the run has no results.jsonl: {path}")
        backend = None
        try:
            with open(os.path.join(run_dir, "run.json"), encoding="utf-8") as fh:
                backend = ((json.load(fh) or {}).get("backend") or {}).get("id")
        except (OSError, ValueError):
            pass
        positives = wrong = used = stale = 0
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                row = json.loads(line)
                a = row.get("slug") or ""
                cands = row.get("candidates") or []
                if row.get("label") != "positive" or a not in catalog or not cands:
                    continue
                positives += 1
                b = cands[0].get("slug") or ""
                if b in set(row.get("truth") or [a]) or b not in catalog:
                    continue
                wrong += 1
                folder, _, file = (row.get("image_path") or "").partition("/")
                entry = (labels.get(folder) or {}).get(file) or {}
                if folder != a or entry.get("label") != "positive":
                    stale += 1
                    continue
                used += 1
                counts[(a, b)] += 1
                if len(photos[(a, b)]) < MAX_PHOTOS:
                    photos[(a, b)].append({"slug": a, "file": file, "answered": b,
                                           "run": run_id})
        report.append({"id": run_id, "backend": backend, "positives": positives,
                       "wrong_at_1": wrong, "used": used, "stale": stale})
    return counts, photos, report


# ---------------------------------------------------------------- the clusters

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

    def groups(self):
        out = collections.defaultdict(list)
        for x in self.parent:
            out[self.find(x)].append(x)
        return [sorted(v) for v in out.values() if len(v) > 1]


def kind_of(members, links):
    """`same-wine`, `look-alike`, or `mixed`. Read the module docstring."""
    named = [(a, b) for (a, b), by in links.items() if "name" in by]
    if not named:
        return "look-alike"
    union = Union()
    for a, b in named:
        union.join(a, b)
    roots = {union.find(m) for m in members}
    return "same-wine" if len(roots) == 1 else "mixed"


def build(catalog, args, labels):
    links = collections.defaultdict(set)     # (a, b) with a < b -> signals
    if not args.no_name:
        for pair in name_pairs(catalog):
            links[pair].add("name")

    photo = label = None
    if not args.no_photo:
        photo = Index(common.rootpath(args.photo_index), catalog)
        for pair in photo.pairs(args.photo_threshold):
            links[pair].add("photo")
    if not args.no_label:
        label = Index(common.rootpath(args.label_index), catalog)
        for pair in label.pairs(args.label_threshold):
            links[pair].add("label")

    counts, photos, runs = collections.Counter(), {}, []
    if not args.no_confusion and args.run:
        counts, photos, runs = load_confusions(args.run, catalog, labels)
        pair_total = collections.Counter()
        for (a, b), n in counts.items():
            pair_total[(a, b) if a < b else (b, a)] += n
        for pair, n in pair_total.items():
            if n >= args.min_confusions:
                links[pair].add("confusion")

    union = Union()
    for a, b in links:
        union.join(a, b)
    groups = union.groups()

    keys = {slug: name_key(rec) for slug, rec in catalog.items()}
    clusters = []
    for members in groups:
        inner = {pair: by for pair, by in links.items() if pair[0] in members}
        records = []
        for (a, b), by in inner.items():
            cos_photo = photo.cosine(a, b) if photo else None
            cos_label = label.cosine(a, b) if label else None
            # `same` passed. `grapes-differ` holds one name key and two grape sets
            # that disagree, such as two cards of one line. None: two names.
            same_key = not args.no_name and bool(keys[a]) and keys[a] == keys[b]
            records.append({
                "a": a, "b": b, "by": sorted(by, key=SIGNALS.index),
                "name": ("same" if "name" in by else "grapes-differ") if same_key
                        else None,
                "photo": None if cos_photo is None else round(cos_photo, 4),
                "label": None if cos_label is None else round(cos_label, 4),
                "a_as_b": counts[(a, b)], "b_as_a": counts[(b, a)],
                "photos": (photos.get((a, b), []) + photos.get((b, a), []))[:MAX_PHOTOS],
            })
        records.sort(key=lambda r: (-len(r["by"]), r["a"], r["b"]))
        clusters.append({
            "kind": kind_of(members, inner),
            "size": len(members),
            "signals": sorted({s for by in inner.values() for s in by}, key=SIGNALS.index),
            "slugs": members,
            "producers": sorted({(catalog[m].get("producer") or "").strip()
                                 for m in members}),
            "confusions": sum(r["a_as_b"] + r["b_as_a"] for r in records),
            "links": records,
        })
    clusters.sort(key=lambda c: (-c["size"], c["slugs"][0]))
    for i, c in enumerate(clusters, 1):
        c["id"] = "c%03d" % i
    return clusters, links, photo, label, runs


def summary(catalog, clusters, links):
    sizes = collections.Counter(c["size"] for c in clusters)
    return {
        "cards": len(catalog),
        "clusters": len(clusters),
        "cards_in_clusters": sum(c["size"] for c in clusters),
        "largest": max((c["size"] for c in clusters), default=0),
        "kinds": dict(collections.Counter(c["kind"] for c in clusters)),
        "links": {s: sum(1 for by in links.values() if s in by) for s in SIGNALS},
        "sizes": {str(k): sizes[k] for k in sorted(sizes)},
    }


def main():
    cfg = common.CLUSTERS
    ap = argparse.ArgumentParser(description="Find the clusters of catalogue cards")
    ap.add_argument("--photo-index", default=cfg.get("photo_index") or "",
                    help="the .npz index of the whole catalogue photo")
    ap.add_argument("--label-index", default=cfg.get("label_index") or "",
                    help="the .npz index of the catalogue label crops")
    ap.add_argument("--photo-threshold", type=float,
                    default=float(cfg.get("photo_threshold", 0.95)))
    ap.add_argument("--label-threshold", type=float,
                    default=float(cfg.get("label_threshold", 0.95)))
    ap.add_argument("--min-confusions", type=int,
                    default=int(cfg.get("min_confusions", 1)),
                    help="photos, over both directions and all runs, that join two cards")
    ap.add_argument("--run", action="append", default=None, metavar="RUN_ID",
                    help="a match run of the dataset. Repeat it for several runs. "
                         "It replaces the runs of config.yaml")
    ap.add_argument("--no-name", action="store_true")
    ap.add_argument("--no-photo", action="store_true")
    ap.add_argument("--no-label", action="store_true")
    ap.add_argument("--no-confusion", action="store_true")
    ap.add_argument("--dataset", default="", metavar="NAME",
                    help="the dataset whose runs and labels give the confusions")
    ap.add_argument("--out", default="", help="the output file. The default is "
                                              "clusters.file of config.yaml")
    ap.add_argument("--show", action="append", default=[], metavar="SLUG",
                    help="print the cluster of this card")
    args = ap.parse_args()
    if args.run is None:
        args.run = list(cfg.get("runs") or [])
    if not args.no_photo and not args.photo_index:
        sys.exit("error: no photo index. Set clusters.photo_index or use --no-photo.")
    if not args.no_label and not args.label_index:
        sys.exit("error: no label index. Set clusters.label_index or use --no-label.")
    try:
        common.select_dataset(args.dataset or None)
    except common.ConfigError as exc:
        sys.exit("error: %s" % exc)
    out_path = common.rootpath(args.out) if args.out else common.CLUSTERS_FILE

    catalog = load_catalog()
    labels = load_labels()
    log("catalogue cards: %d" % len(catalog))
    clusters, links, photo, label, runs = build(catalog, args, labels)
    for name, index in (("photo", photo), ("label", label)):
        if index is not None:
            d = index.describe()
            log("%s index: %d cards, built %s, %s"
                % (name, d["cards"], d["built_at"], index.path))
            if d["dropped_non_finite"] or d["dropped_unknown_slugs"]:
                log("  dropped: %d non-finite vectors, %d slugs not in the catalogue"
                    % (d["dropped_non_finite"], d["dropped_unknown_slugs"]))
    for r in runs:
        log("run %s: %d positives, %d wrong at rank 1, %d used, %d stale"
            % (r["id"], r["positives"], r["wrong_at_1"], r["used"], r["stale"]))

    counts = summary(catalog, clusters, links)
    out = {
        "version": 1,
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "note": ("Clusters of catalogue cards that the matcher confuses, or can "
                 "confuse. scripts/10_clusters.py writes this file, and the page "
                 "/clusters of the review tool shows it. Read "
                 "docs/plans/04_catalog-clusters.md."),
        "settings": {
            "signals": [s for s in SIGNALS if not getattr(args, "no_" + s)],
            "photo_threshold": args.photo_threshold,
            "label_threshold": args.label_threshold,
            "min_confusions": args.min_confusions,
        },
        "inputs": {
            "catalog_file": common.CATALOG_FILE,
            "photo_index": photo.describe() if photo else None,
            "label_index": label.describe() if label else None,
            "dataset": common.DATASET,
            "label_file": common.LABEL_FILE,
            "runs": runs,
        },
        "counts": counts,
        "clusters": clusters,
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    tmp = out_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    os.replace(tmp, out_path)

    log("links: %s" % ", ".join("%s %d" % kv for kv in counts["links"].items()))
    log("clusters: %d   cards in a cluster: %d   largest: %d   kinds: %s"
        % (counts["clusters"], counts["cards_in_clusters"], counts["largest"],
           ", ".join("%s %d" % kv for kv in sorted(counts["kinds"].items()))))
    log("sizes: %s" % ", ".join("%s: %d" % kv for kv in counts["sizes"].items()))
    log("-> %s" % out_path)
    for c in clusters[:5]:
        log("  %s  %-10s %2d cards  %s" % (c["id"], c["kind"], c["size"],
                                          ", ".join(c["slugs"][:4])
                                          + (" ..." if c["size"] > 4 else "")))
    for slug in args.show:
        hit = next((c for c in clusters if slug in c["slugs"]), None)
        if hit is None:
            log("%s: in no cluster" % slug)
            continue
        log("%s: %s, %s, %d cards" % (slug, hit["id"], hit["kind"], hit["size"]))
        for r in hit["links"]:
            log("  %s -- %s  by %s  photo %s  label %s  confusions %d/%d"
                % (r["a"], r["b"], "+".join(r["by"]), r["photo"], r["label"],
                   r["a_as_b"], r["b_as_a"]))


if __name__ == "__main__":
    main()
