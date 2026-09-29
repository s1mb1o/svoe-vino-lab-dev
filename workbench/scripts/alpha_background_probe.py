#!/usr/bin/env python3
"""Probe the alpha channel and the background fill of the image embedding models.

Owner message of 2026-09-29T11:12:54+0300. The ResearchLog entry of 2026-09-25 ("the SigLIP
2 models of the gx10 gateway") measured with `dinov3-vitb16` alone that the gateway drops
the alpha channel of an RGBA PNG and that the model sees the colour under a transparent
pixel. This script repeats the test for the SigLIP 2 entries of `config.yaml` and adds
real catalogue cuts.

Part A (synthetic): one 256 x 512 RGBA image, a bottle on transparent pixels. The script
sends the RGBA PNG with red, blue, and white under the transparent pixels, the same
images after Pillow `convert("RGB")` (the alpha channel dropped), and the image
composited on white. If the gateway drops the alpha channel, an RGBA image and its RGB
form give the cosine 1. If the model sees the colour under the transparent pixels, red
and blue give a cosine below 1.

Part B (catalogue): `--samples` current `full` items of the index of each entry, spread
over the sha256 order. For each item, the SAM3 cut of the package (RGBA; the stored cut
keeps the pixels of the original photo under its transparent pixels) is composited on
white (the index input: the script checks the pixels against the stored index PNG), black,
grey 128, red, and blue, and sent raw as RGBA and as its RGB form. Every image gets the
scale of the `resize` step of the white image. The script writes the cosine to the white
image and to the stored index vector, and the rank of the wine in the index (the best
`full` item of each wine; the index images are on white).

No request holds one image alone (NaFlex p256 gives another vector for one image). The
script is read-only for the catalogue and the indexes.

    python3 scripts/alpha_background_probe.py --entries gx10-siglip2-so400m-patch16-256
    python3 scripts/alpha_background_probe.py --summary-only
"""

import argparse
import csv
import io
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rotation_multiref  # noqa: E402
import rotation_similarity as rs  # noqa: E402  (it adds pipeline/ to sys.path)
from rotation_similarity import build_embeddings, embeddings  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "reports", "siglip2-alpha-background-2026-09-29")
ENTRIES = (
    "gx10-siglip2-so400m-patch16-naflex-p256",
    "gx10-siglip2-so400m-patch16-naflex-p512",
    "gx10-siglip2-so400m-patch16-naflex-p1024",
    "gx10-siglip2-so400m-patch16-256",
    "gx10-siglip2-so400m-patch16-384",
    "gx10-siglip2-so400m-patch16-512",
    "gx10-siglip2-so400m-patch14-384",
    "gx10-naflexvit-so400m-patch16-siglip2-p256",
    "gx10-dinov3-vitb16",
)
FILLS = {"white": (255, 255, 255), "black": (0, 0, 0), "grey": (128, 128, 128),
         "red": (255, 0, 0), "blue": (0, 0, 255)}


def png(image):
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def synthetic_bottle(under):
    """RGBA 256 x 512: an opaque bottle with a label on transparent pixels whose RGB is
    `under`."""
    image = Image.new("RGBA", (256, 512), under + (0,))
    draw = ImageDraw.Draw(image)
    draw.rectangle((108, 20, 148, 150), fill=(30, 60, 30, 255))          # neck
    draw.rounded_rectangle((68, 140, 188, 492), radius=30, fill=(30, 70, 35, 255))
    draw.rectangle((78, 250, 178, 400), fill=(245, 240, 225, 255))       # label
    draw.rectangle((88, 270, 168, 290), fill=(150, 20, 30, 255))
    for y in range(305, 390, 12):
        draw.rectangle((92, y, 92 + (y * 7) % 70, y + 5), fill=(40, 40, 40, 255))
    draw.rectangle((108, 20, 148, 40), fill=(120, 20, 20, 255))          # capsule
    return image


def on_fill(rgba, colour):
    canvas = Image.new("RGBA", rgba.size, colour + (255,))
    return Image.alpha_composite(canvas, rgba).convert("RGB")


def unit(vectors):
    vectors = np.asarray(vectors, dtype=np.float64)
    return vectors / np.linalg.norm(vectors, axis=-1, keepdims=True)


def embed(backend, images):
    """Embed PNG bytes in requests of 8; no request holds one image alone."""
    return unit(rotation_multiref.embed_all(backend, images, 8))


def part_a(backend):
    red, blue, white = (synthetic_bottle(c) for c in ((255, 0, 0), (0, 0, 255),
                                                      (255, 255, 255)))
    names = ["rgba_red", "rgb_red", "rgba_blue", "rgb_blue", "rgba_white",
             "white_composite"]
    images = [red, red.convert("RGB"), blue, blue.convert("RGB"), white,
              on_fill(white, FILLS["white"])]
    got = dict(zip(names, embed(backend, [png(image) for image in images])))
    pairs = (("rgba_red", "rgb_red"), ("rgba_blue", "rgb_blue"), ("rgba_red", "rgba_blue"),
             ("rgba_white", "white_composite"), ("rgba_red", "white_composite"),
             ("rgb_red", "rgb_blue"))
    return {"%s~%s" % pair: round(float(got[pair[0]] @ got[pair[1]]), 6) for pair in pairs}


def samples(sources, items, chosen, count):
    keys = sorted(key for key in chosen if items[key]["cut"])
    step = max(1, len(keys) // count)
    return keys[::step][:count]


def part_b(name, embedding, directory, index, vectors, sources, items, chosen, sha_to_slug,
           count, backend, examples_dir):
    steps = rs.full_steps(embedding)
    resize_step = steps[-1]
    slugs, item_rows = rs.wine_rows(index, sha_to_slug)
    catalogue = unit(vectors[item_rows])
    rows = []
    for number, key in enumerate(samples(sources, items, chosen, count)):
        digest = key[0]
        source, cut = sources[digest], items[key]["cut"]
        image, _ = embeddings.derive.open_image(source["path"])
        rgba, _ = embeddings.derive.open_image(cut["path"])
        if rgba.mode != "RGBA" or rgba.size != image.crop(cut["box"]).size:
            continue
        variants = {fill: embeddings.resize(on_fill(rgba, colour), resize_step)
                    for fill, colour in FILLS.items()}
        raw = embeddings.resize(rgba, resize_step)
        variants["raw_rgba"] = raw
        variants["raw_rgb"] = raw.convert("RGB")
        stored = Image.open(os.path.join(directory, chosen[key]["image"])).convert("RGB")
        same = (variants["white"].size == stored.size
                and np.array_equal(np.asarray(variants["white"]), np.asarray(stored)))
        if number < 3 and examples_dir:
            for fill, picture in variants.items():
                picture.save(os.path.join(examples_dir, "%s_%s.png" % (digest[:12], fill)))
        names = list(variants)
        got = dict(zip(names, embed(backend, [png(variants[n]) for n in names])))
        own = sha_to_slug[digest]
        stored_vector = unit(vectors[chosen[key]["row"]])
        for fill in names:
            scores = catalogue @ got[fill]
            best = {}
            for slug, score in zip(slugs, scores):
                if score > best.get(slug, -2.0):
                    best[slug] = score
            ranking = sorted(best, key=best.get, reverse=True)
            rows.append({
                "entry": name, "sha256": digest, "slug": own, "fill": fill,
                "white_equals_index_png": same,
                "cosine_to_white": round(float(got[fill] @ got["white"]), 6),
                "cosine_to_index": round(float(got[fill] @ stored_vector), 6),
                "cosine_raw_rgba_to_raw_rgb": round(float(got["raw_rgba"] @ got["raw_rgb"]), 6),
                "rank": ranking.index(own) + 1})
    return rows


def run(args):
    os.makedirs(os.path.join(args.out, "results"), exist_ok=True)
    examples_dir = os.path.join(args.out, "examples")
    os.makedirs(examples_dir, exist_ok=True)
    for colour in ("red", "blue", "white"):
        synthetic_bottle(FILLS[colour]).save(
            os.path.join(examples_dir, "synthetic_rgba_%s.png" % colour))
    settings = embeddings.load_settings()
    conn = embeddings.open_database(settings.db_path)
    try:
        wines, sources = embeddings.read_inputs(conn, settings.db_path)
    finally:
        conn.close()
    sha_to_slug = {}
    for wine in wines:
        for _, sha in wine["columns"]:
            if sources.get(sha, {}).get("role") == "full":
                sha_to_slug.setdefault(sha, wine["slug"])
    for name in args.entries:
        embedding, directory, index, vectors = rs.load_entry(settings, name)
        items = embeddings.plan_items(embedding, sources)
        status = embeddings.item_status(items, index, embeddings.image_names(directory))
        chosen = {key: record for key, (state, record) in status.items()
                  if key[1] == "full" and state == "current"}
        backend = build_embeddings.OpenAIBackend(embedding)
        synthetic = part_a(backend)
        print("%s: part A %s" % (name, json.dumps(synthetic)), flush=True)
        rows = part_b(name, embedding, directory, index, vectors, sources, items, chosen,
                      sha_to_slug, args.samples, backend,
                      examples_dir if name == args.entries[0] else None)
        with open(os.path.join(args.out, "results", name + ".json"), "w",
                  encoding="utf-8") as fh:
            json.dump({"entry": name, "model": embedding.model,
                       "extra_body": embedding.extra_body, "synthetic": synthetic,
                       "catalogue": rows}, fh, ensure_ascii=False, indent=1)
        print("%s: part B %d images" % (name, len(rows) // 7), flush=True)


def summary(out):
    table_a, table_b = [], []
    for name in ENTRIES:
        path = os.path.join(out, "results", name + ".json")
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        table_a.append(dict(entry=name, **data["synthetic"]))
        rows = data["catalogue"]
        for fill in list(FILLS) + ["raw_rgba", "raw_rgb"]:
            group = [row for row in rows if row["fill"] == fill]
            if not group:
                continue
            table_b.append({
                "entry": name, "fill": fill, "images": len(group),
                "white_equals_index_png": sum(row["white_equals_index_png"] for row in group),
                "mean_cosine_to_white": round(float(np.mean([r["cosine_to_white"] for r in group])), 4),
                "min_cosine_to_white": round(float(np.min([r["cosine_to_white"] for r in group])), 4),
                "mean_cosine_to_index": round(float(np.mean([r["cosine_to_index"] for r in group])), 4),
                "rank_1": sum(row["rank"] == 1 for row in group),
                "mean_rank": round(float(np.mean([row["rank"] for row in group])), 2),
                "min_cosine_raw_rgba_to_raw_rgb": round(float(np.min(
                    [r["cosine_raw_rgba_to_raw_rgb"] for r in group])), 6)})
    for filename, table in (("synthetic.csv", table_a), ("catalogue.csv", table_b)):
        if table:
            with open(os.path.join(out, filename), "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=list(table[0]))
                writer.writeheader()
                writer.writerows(table)
    print("wrote %s" % out)
    return table_a, table_b


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--entries", nargs="+", default=list(ENTRIES))
    parser.add_argument("--samples", type=int, default=40)
    parser.add_argument("--out", default=OUT)
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args(argv)
    if not args.summary_only:
        run(args)
    summary(args.out)


if __name__ == "__main__":
    main()
