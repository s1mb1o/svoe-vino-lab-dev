#!/usr/bin/env python3
"""Stage 8. Find the wines that are variants of one another.

The `vino-svoe.ru` catalogue holds one slug per bottle, not one slug per wine.
The same wine of a different vintage, or of a different alcohol value, gets its
own slug and its own catalogue photo. Two such photos differ only in a small
detail of the label, so a reviewer can mix them up. Example:

    abrau-dyurso-pino-nuar-krasnoe-suhoe-12
    abrau-dyurso-pino-nuar-krasnoe-suhoe-125

The two photos hold the same label design in two colours.

The script builds groups of such slugs in two steps:

1. Metadata. Two slugs with the same `producer` and the same `name` in
   `catalog.jsonl` belong to one group. This step is exact and costs nothing.
2. Image. The script asks the SigLIP2 service on gx10 for one embedding per
   catalogue bottle photo, then joins every pair whose cosine similarity is at
   or above `--threshold`. This step finds the pairs that step 1 misses, such as
   a renamed wine.

A pair from either step joins the two groups. The output is
`derived/variant-groups.json`.

A perceptual hash was tried first and was dropped. A bottle photo is mostly
bottle, so the hash of the silhouette hides the label. A measured example: the
two slugs above scored a Hamming distance of 76 of 256 bits, while two unrelated
wines of the same producer scored 29. The hash ranks the wrong pairs first.

Run:
    python3 scripts/08_variants.py
    python3 scripts/08_variants.py --threshold 0.93 --no-image
"""
import argparse
import collections
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402
from common import EMBED_MODEL, data_url, log, post_json  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Every path comes from `config.yaml`. The review tool reads the same two files.
MY = common.PHOTO_DIR
OUT = common.VARIANT_GROUPS_FILE
CATALOG = common.CATALOG_FILE
# slug -> corrected catalogue photo. See the README, `Patched catalogue photos`.
PATCHES = common.load_patches()
# slug -> cropped catalogue photo. See the README, `Cropped catalogue photos`.
CROPS = common.load_cropped_bottles()


def load_catalog():
    out = {}
    with open(CATALOG, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rec = json.loads(line)
                out[rec["slug"]] = rec
    return out


def my_slugs():
    return sorted(
        d for d in os.listdir(MY)
        if not d.startswith(".") and os.path.isdir(os.path.join(MY, d))
    )


class Union:
    """Union-find over slugs. A pair from any step joins two groups."""

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
            self.parent[rb] = ra

    def groups(self):
        out = collections.defaultdict(list)
        for x in self.parent:
            out[self.find(x)].append(x)
        return [sorted(v) for v in out.values() if len(v) > 1]


def metadata_pairs(slugs, catalog):
    """Group the slugs that share a producer and a name."""
    by_key = collections.defaultdict(list)
    for s in slugs:
        rec = catalog.get(s)
        if not rec:
            continue
        key = (rec.get("producer", "").strip(), rec.get("name", "").strip())
        if key[0] or key[1]:
            by_key[key].append(s)
    pairs = []
    for key, members in by_key.items():
        for other in members[1:]:
            pairs.append((members[0], other, "metadata", None))
    return pairs


def embed_bottles(slugs, catalog, batch, maxside):
    """Return slug -> unit vector of the catalogue bottle photo.

    Every run embeds the photos again. The vectors are not cached, because the
    matching of a picture against the set is the work of an external application.
    """
    cache = {}
    todo = []
    for s in slugs:
        if s in cache:
            continue
        # The script embeds the picture that the review tool shows: the crop,
        # then the corrected photo of `patch_dir`, then the photo of the record.
        # A group is found by comparing the bottle photos, so a photo that the
        # tool no longer shows MUST NOT decide a group.
        path = common.catalogue_picture(s, catalog.get(s), CROPS, PATCHES)
        if path and os.path.exists(path):
            todo.append((s, path))
    log("bottle photos to embed: %d" % len(todo))

    for i in range(0, len(todo), batch):
        chunk = todo[i:i + batch]
        urls = [data_url(p, maxside=maxside) for _, p in chunk]
        t0 = time.time()
        res = post_json("/v1/embeddings", {"model": EMBED_MODEL, "input": urls})
        for (s, _), item in zip(chunk, res["data"]):
            cache[s] = item["embedding"]
        log("embedded %d/%d in %.1fs" % (min(i + batch, len(todo)), len(todo),
                                         time.time() - t0))

    import math
    unit = {}
    for s, v in cache.items():
        if s not in slugs:
            continue
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        unit[s] = [x / n for x in v]
    return unit


def image_pairs(unit, threshold):
    """Return every pair of slugs whose cosine similarity reaches the threshold."""
    try:
        import numpy as np
    except ImportError:
        sys.exit("error: numpy is needed for the image step; use --no-image")
    keys = sorted(unit)
    if not keys:
        return []
    m = np.asarray([unit[k] for k in keys], dtype=np.float32)
    sim = m @ m.T
    pairs = []
    n = len(keys)
    for i in range(n):
        for j in range(i + 1, n):
            v = float(sim[i, j])
            if v >= threshold:
                pairs.append((keys[i], keys[j], "image", round(v, 4)))
    return pairs


def main():
    ap = argparse.ArgumentParser(description="Find the variant groups of the wines")
    ap.add_argument("--threshold", type=float, default=0.95,
                    help="cosine similarity that joins two slugs (default 0.95)")
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--maxside", type=int, default=384)
    ap.add_argument("--no-image", action="store_true",
                    help="use the metadata step only")
    args = ap.parse_args()

    catalog = load_catalog()
    slugs = my_slugs()
    log("wines in my/: %d   catalogue slugs: %d" % (len(slugs), len(catalog)))

    union = Union()
    for s in slugs:
        union.find(s)

    pairs = metadata_pairs(slugs, catalog)
    log("metadata pairs: %d" % len(pairs))

    if not args.no_image:
        unit = embed_bottles(slugs, catalog, args.batch, args.maxside)
        log("embedded bottle photos: %d" % len(unit))
        ipairs = image_pairs(unit, args.threshold)
        log("image pairs at cosine >= %.3f: %d" % (args.threshold, len(ipairs)))
        pairs += ipairs

    for a, b, _why, _score in pairs:
        union.join(a, b)

    groups = sorted(union.groups(), key=lambda g: (-len(g), g[0]))
    reasons = collections.defaultdict(list)
    for a, b, why, score in pairs:
        reasons[tuple(sorted((a, b)))].append(
            {"by": why} if score is None else {"by": why, "cosine": score}
        )

    out = {
        "version": 1,
        "updated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "note": (
            "Groups of wine slugs that hold the same wine in another bottle: another "
            "vintage, another alcohol value, or another package design. A group is "
            "built from a metadata step (same producer and same name in "
            "catalog.jsonl) and from an image step (cosine similarity of SigLIP2 "
            "embeddings of the catalogue bottle photos). The review tool places the "
            "rows of one group next to each other and gives them one background "
            "colour."
        ),
        "method": {
            "metadata": "same producer and same name",
            "image": None if args.no_image else {
                "model": EMBED_MODEL, "threshold": args.threshold,
                "maxside": args.maxside,
            },
        },
        "counts": {
            "wines": len(slugs),
            "groups": len(groups),
            "slugs_in_groups": sum(len(g) for g in groups),
            "metadata_pairs": sum(1 for p in pairs if p[2] == "metadata"),
            "image_pairs": sum(1 for p in pairs if p[2] == "image"),
        },
        "groups": [
            {
                "id": "g%03d" % (i + 1),
                "slugs": g,
                "producer": (catalog.get(g[0]) or {}).get("producer", ""),
                "name": (catalog.get(g[0]) or {}).get("name", ""),
            }
            for i, g in enumerate(groups)
        ],
        "pairs": [
            {"a": a, "b": b, "by": why, **({} if score is None else {"cosine": score})}
            for a, b, why, score in sorted(pairs)
        ],
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")

    log("groups: %d   slugs in a group: %d   -> %s"
        % (len(groups), out["counts"]["slugs_in_groups"], OUT))
    for g in groups[:10]:
        log("  %s" % ", ".join(g))


if __name__ == "__main__":
    main()
