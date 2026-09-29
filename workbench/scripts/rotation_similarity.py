#!/usr/bin/env python3
"""Rotate the package of one catalogue main image and compare it with its indexed vector.

Owner message of 2026-09-29T01:10:49+0300. The script takes the `main` image of one
Active wine that each named embedding entry holds as an item of the view `full`. It builds
the view `full` as the index did (the SAM3 cut of the package), but puts the cut on a
white or on a black background. It rotates the result in steps of `--step` degrees
counter-clockwise. The canvas grows to hold the rotated image (`expand`); the package
keeps the pixel size of the indexed image. The script embeds each image with each entry
and writes the cosine similarity to the indexed `full` vector of the same image. It also
writes the rank of the wine among the `full` vectors of the index (the best item of each
wine), and the best cosine of another wine.

The script is read-only for the catalogue and for the indexes. It sends the images to the
`base_url` of each entry in `config.yaml`.

    python3 scripts/rotation_similarity.py --out docs/reports/rotation-similarity-2026-09-29
"""

import argparse
import csv
import io
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "pipeline"))
import build_embeddings  # noqa: E402
import embeddings  # noqa: E402

ENTRIES = (
    "gx10-siglip2-so400m-patch16-naflex-p256",
    "gx10-siglip2-so400m-patch16-naflex-p512",
    "gx10-siglip2-so400m-patch16-naflex-p1024",
    "gx10-siglip2-so400m-patch16-256",
    "gx10-siglip2-so400m-patch16-384",
    "gx10-siglip2-so400m-patch16-512",
)
BACKGROUNDS = {"white": (255, 255, 255), "black": (0, 0, 0)}


def load_entry(settings, name):
    embedding = settings.find(name)
    directory = embeddings.entry_dir(settings.db_path, name)
    index = embeddings.read_index(directory)
    vectors = embeddings.read_vectors(directory, index)
    return embedding, directory, index, vectors


def full_steps(embedding):
    steps = embedding.views["full"]
    kinds = [step["step"] for step in steps]
    if kinds != ["segment", "remove_background", "white_background", "resize"]:
        raise SystemExit("%s: unexpected steps of the view full: %s" % (embedding.name, kinds))
    return steps


def pick_wine(wines, sources, loaded, slug=None):
    """Return (wine, sha256 of its main image). The image MUST be a `full` item of each
    entry. With no `slug`, take the first such wine with no `main_patched` image."""
    for wine in wines:
        if slug and wine["slug"] != slug:
            continue
        types = dict(wine["columns"])
        if "main" not in types or (not slug and "main_patched" in types):
            continue
        digest = types["main"]
        if sources[digest]["cuts"].get("package") is None:
            continue
        if all(row_of(index, digest) is not None for _, _, index, _ in loaded.values()):
            return wine, digest
    raise SystemExit("no wine fits (slug %r)" % slug)


def row_of(index, digest):
    for item in index["items"]:
        if item["source_sha256"] == digest and item["view"] == "full":
            return item
    return None


def wine_rows(index, sha_to_slug):
    """Return (slugs, rows): the wine of each `full` item and the item rows."""
    slugs, rows = [], []
    for item in index["items"]:
        if item["view"] != "full":
            continue
        slug = sha_to_slug.get(item["source_sha256"])
        if slug is None:
            continue
        slugs.append(slug)
        rows.append(item["row"])
    return np.asarray(slugs), np.asarray(rows)


def base_images(source, steps):
    """Return {background: RGB image} of the cut before `resize`, and the resize step."""
    image, _ = embeddings.derive.open_image(source["path"])
    cut = source["cuts"]["package"]
    cropped = image.crop(cut["box"])
    rgba, _ = embeddings.derive.open_image(cut["path"])
    if rgba.size != cropped.size:
        raise SystemExit("the cut is %s; its box is %s" % (rgba.size, cropped.size))
    out = {}
    for name, color in BACKGROUNDS.items():
        if rgba.mode == "RGBA":
            canvas = Image.new("RGBA", rgba.size, color + (255,))
            out[name] = Image.alpha_composite(canvas, rgba).convert("RGB")
        else:
            out[name] = rgba.convert("RGB")
    return out, steps[-1]


def scale_of(size, resize_step):
    """The scale of the index `resize` step for an image of `size`."""
    longest = max(size)
    if not resize_step["upscale"] and longest <= resize_step["max_size"]:
        return 1.0
    return resize_step["max_size"] / longest


def rotated(image, angle, color, scale):
    """Rotate counter-clockwise with a growing canvas, then apply the fixed `scale`."""
    if angle % 360:
        image = image.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True,
                             fillcolor=color)
    if scale != 1.0:
        target = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
        image = image.resize(target, Image.Resampling.LANCZOS)
    return image


def normalise(matrix):
    matrix = np.asarray(matrix, dtype=np.float64)
    return matrix / np.linalg.norm(matrix, axis=-1, keepdims=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", required=True, help="the output directory")
    parser.add_argument("--slug", help="the wine; default: the first wine that fits")
    parser.add_argument("--step", type=int, default=5, help="the angle step in degrees")
    parser.add_argument("--batch", type=int, default=8, help="images per request")
    parser.add_argument("--entries", nargs="*", default=list(ENTRIES))
    args = parser.parse_args(argv)
    os.makedirs(os.path.join(args.out, "images"), exist_ok=True)

    settings = embeddings.load_settings()
    loaded = {name: load_entry(settings, name) for name in args.entries}
    conn = embeddings.open_database(settings.db_path)
    wines, sources = embeddings.read_inputs(conn, settings.db_path)
    conn.close()
    wine, digest = pick_wine(wines, sources, loaded, args.slug)
    source = sources[digest]
    sha_to_slug = {}
    for other in wines:
        for _, sha in other["columns"]:
            if sources.get(sha, {}).get("role") == "full":
                sha_to_slug.setdefault(sha, other["slug"])
    print("wine %s (%s), main image %s" % (wine["slug"], wine["name"], digest), flush=True)

    # The index image of the view `full`: the pixels of `prepare` MUST equal the stored PNG.
    first = loaded[args.entries[0]]
    steps = full_steps(first[0])
    for name, (embedding, directory, index, _) in loaded.items():
        if full_steps(embedding) != steps:
            raise SystemExit("%s: the view full has other steps" % name)
    item = row_of(first[2], digest)
    stored = Image.open(os.path.join(first[1], item["image"])).convert("RGB")
    plan = embeddings.plan_items(first[0], {digest: source})[(digest, "full")]
    prepared = embeddings.prepare(plan, source["path"])
    same_pixels = (prepared.size == stored.size
                   and np.array_equal(np.asarray(prepared), np.asarray(stored)))
    print("prepare() equals the stored index image: %s (%s)" % (same_pixels, stored.size),
          flush=True)

    bases, resize_step = base_images(source, steps)
    scale = scale_of(bases["white"].size, resize_step)
    zero_white = rotated(bases["white"], 0, BACKGROUNDS["white"], scale)
    same_rebuild = np.array_equal(np.asarray(zero_white), np.asarray(stored))
    print("the 0° white rebuild equals the stored index image: %s" % same_rebuild, flush=True)

    angles = list(range(0, 360, args.step))
    images = []  # (background, angle, PNG bytes, size)
    for background, color in BACKGROUNDS.items():
        for angle in angles:
            picture = rotated(bases[background], angle, color, scale)
            png = embeddings.png_bytes(picture)
            images.append((background, angle, png, picture.size))
            picture.save(os.path.join(args.out, "images", "%s_%03d.png" % (background, angle)))

    rows = []
    for name, (embedding, directory, index, vectors) in loaded.items():
        backend = build_embeddings.OpenAIBackend(embedding)
        reference = normalise(vectors[row_of(index, digest)["row"]])
        slugs, item_rows = wine_rows(index, sha_to_slug)
        catalogue = normalise(vectors[item_rows])
        stored_png = embeddings.png_bytes(stored)
        check = normalise(backend.embed([stored_png])[0])
        print("%s: the stored image embedded again, cosine %.6f" % (name, check @ reference),
              flush=True)
        got = []
        for start in range(0, len(images), args.batch):
            chunk = images[start:start + args.batch]
            got.extend(backend.embed([png for _, _, png, _ in chunk]))
        for (background, angle, _, size), vector in zip(images, normalise(got)):
            scores = catalogue @ vector
            best = {}
            for slug, score in zip(slugs, scores):
                if score > best.get(slug, -2.0):
                    best[slug] = score
            ranking = sorted(best, key=best.get, reverse=True)
            other = next(slug for slug in ranking if slug != wine["slug"])
            rows.append({
                "entry": name, "background": background, "angle": angle,
                "width": size[0], "height": size[1],
                "cosine": round(float(vector @ reference), 6),
                "rank": ranking.index(wine["slug"]) + 1,
                "best_other_cosine": round(float(best[other]), 6),
                "best_other_slug": other})
        print("%s: %d images" % (name, len(images)), flush=True)

    with open(os.path.join(args.out, "results.csv"), "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    meta = {"wine": {key: wine[key] for key in ("slug", "name", "producer", "category")},
            "main_sha256": digest, "index_image": item["image"],
            "index_image_size": list(stored.size), "cut_size": list(bases["white"].size),
            "scale": scale, "step": args.step, "rotation": "counter-clockwise, PIL BICUBIC, "
            "expand=True, fill with the background color, then the fixed index scale",
            "prepare_equals_stored": same_pixels, "rebuild_equals_stored": same_rebuild,
            "entries": {name: loaded[name][0].base_url for name in args.entries}}
    with open(os.path.join(args.out, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
    print("wrote %s" % os.path.join(args.out, "results.csv"))


if __name__ == "__main__":
    main()
