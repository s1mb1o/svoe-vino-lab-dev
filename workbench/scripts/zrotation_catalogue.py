#!/usr/bin/env python3
"""A fair z-rotation test: each catalogue image gets copies turned about its vertical axis.

Owner message of about 2026-10-01T08:06:00+0300 ("try that") and the answer of about 08:09
(the full catalogue, NaFlex p512, the turntable photos and the set `my`).
`zrotation_similarity.py` gave the turned copies to one wine alone, so its count of
photos with rank 1 was optimistic. Here each full image of the catalogue gets the copies,
so each wine has the same advantage.

The calibration of `tools/bottle_rotation` is automatic. The package cut gives the
silhouette. The SAM3 label cut gives the label layer: its alpha channel is the mask, and
a cut with no transparent pixel gives its box. `camera_y` is the centre of the label box,
`distance` is 300, and `fill` is `vertical` (`inpaint` when no glass is around the label).
An image whose calibration fails keeps its 0° image alone. The copies get the steps of the
view `full` after `remove_background`, as in `zrotation_similarity.py`, so the 0° copy is
the model input of the index.

The score of a wine is its best cosine over its full images: over the 0° copies alone
(`single`, the vectors of the index) or over all copies (`z`). For each positive photo of
`--set` and for each turntable photo of `--photos`, the script writes the rank of the true
wine with both scores, and R@1, R@5, and MRR.

The script is read-only for the catalogue and for the indexes. It sends the photos to SAM3
(the answers go to `data/cache/models/sam3/`) and the images to the `base_url` of the
entry. It writes into `--out` alone. A second run reads the vector files of `--out` and
sends no request for them.

    python3 scripts/zrotation_catalogue.py --set my \\
        --photos ~/Downloads/winemaker-selection-z-rotation \\
        --out docs/reports/zrotation-catalogue-2026-10-01
"""

import argparse
import collections
import concurrent.futures
import csv
import glob
import json
import os
import random
import shutil
import sys
import tempfile
import threading
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import zrotation_similarity as single  # also puts pipeline/ and tools/bottle_rotation/ on sys.path
import benchmark  # noqa: E402
import build_embeddings  # noqa: E402
import derive  # noqa: E402
import embedding_run  # noqa: E402
import embeddings  # noqa: E402
from rotate_bottle import ANGLE_LIMIT, BottleRotator  # noqa: E402

plots, plt = single.plots, single.plt

ENTRY = "gx10-siglip2-so400m-patch16-naflex-p512"
TURNTABLE_WINE = "winemaker-selection"
CHUNK = 48  # catalogue images for each vector file of `vectors/chunks/`


# --- the copies of the catalogue (worker processes) --------------------------------------

def label_mask(size, cut_box, label):
    """Return the mask of the label cut `label` in the pixels of the package cut."""
    mask = Image.new("L", size, 0)
    image, _ = derive.open_image(label["path"])
    alpha = (image.getchannel("A") if image.mode == "RGBA"
             else Image.new("L", image.size, 255))
    mask.paste(alpha, (label["box"][0] - cut_box[0], label["box"][1] - cut_box[1]))
    return mask


def calibration_of(size, cut_box, label, directory):
    """Return the calibration of one package cut; the mask goes to `directory`."""
    mask = label_mask(size, cut_box, label)
    mask.save(os.path.join(directory, "mask.png"))
    top = max(0, label["box"][1] - cut_box[1])
    bottom = min(size[1], label["box"][3] - cut_box[1])
    return {"version": 1, "reference_size": list(size),
            "layers": [{"name": "label", "mask": "mask.png", "distance": 300,
                        "camera_y": (top + bottom) / 2, "fill": "vertical",
                        "smooth_profile": True}]}


def render_copies(task):
    """Return (sha256, the PNG of each angle, state) of one catalogue image. The PNG list
    holds the 0° image alone when the calibration fails. Runs in a worker process."""
    digest, package, label, tail, angles = task
    cut, _ = derive.open_image(package["path"])
    zero = embeddings.apply_steps(cut, tail, None, None)
    if label is None:
        return digest, [embeddings.png_bytes(zero)], "no label cut"
    directory = tempfile.mkdtemp(prefix="zcal-")
    try:
        calibration = calibration_of(cut.size, package["box"], label, directory)
        state = "vertical"
        try:
            rotator = BottleRotator(cut, calibration, config_dir=directory)
        except ValueError as exc:
            if "reconstruct glass" not in str(exc):
                raise
            calibration["layers"][0]["fill"] = state = "inpaint"
            rotator = BottleRotator(cut, calibration, config_dir=directory)
        pngs = [embeddings.png_bytes(zero if angle == 0 else embeddings.apply_steps(
            rotator.render(angle), tail, None, None)) for angle in angles]
        return digest, pngs, state
    except (ValueError, embeddings.ItemError) as exc:
        return digest, [embeddings.png_bytes(zero)], "failed: %s" % str(exc)[:120]
    finally:
        shutil.rmtree(directory, ignore_errors=True)


class Embedder:
    """The embedding backend of one entry: one backend for each thread, `batch` images in
    each request."""

    def __init__(self, embedding, batch, workers):
        self.embedding, self.batch, self.workers = embedding, batch, workers
        self.local = threading.local()

    def _embed(self, pngs):
        if not hasattr(self.local, "backend"):
            self.local.backend = build_embeddings.OpenAIBackend(self.embedding)
        return self.local.backend.embed(pngs)

    def __call__(self, pngs):
        """Return the L2-normalised vectors of `pngs`, in order."""
        parts = [pngs[i:i + self.batch] for i in range(0, len(pngs), self.batch)]
        with concurrent.futures.ThreadPoolExecutor(self.workers) as pool:
            got = list(pool.map(self._embed, parts))
        return single.normalise(np.concatenate(got)).astype(np.float32)


def catalogue_copies(args, sources, steps, angles, embed):
    """Return (sha256 list, vectors N x angles x dim, states). The 0° vector stands in for
    each angle of an image with no copies. Each chunk of `CHUNK` images goes to a file of
    `vectors/chunks/`; a later run reads it."""
    kinds = [step["step"] for step in steps]
    tail = steps[kinds.index("remove_background") + 1:]
    digests = sorted(sources)
    chunk_dir = os.path.join(args.out, "vectors", "chunks")
    os.makedirs(chunk_dir, exist_ok=True)
    out, states = [], {}
    started = time.time()
    with concurrent.futures.ProcessPoolExecutor(args.render_workers) as pool:
        for number, first in enumerate(range(0, len(digests), CHUNK)):
            part = digests[first:first + CHUNK]
            path = os.path.join(chunk_dir, "%04d.npz" % number)
            if os.path.exists(path):
                saved = np.load(path, allow_pickle=False)
                if list(saved["digests"]) != part:
                    raise SystemExit("%s holds other images; remove vectors/chunks/" % path)
                out.append(saved["vectors"])
                states.update(zip(part, saved["states"]))
                continue
            tasks = [(digest, sources[digest]["cuts"]["package"],
                      sources[digest]["cuts"].get("label"), tail, angles) for digest in part]
            rendered = list(pool.map(render_copies, tasks, chunksize=2))
            flat = [png for _, pngs, _ in rendered for png in pngs]
            vectors = embed(flat)
            block, position = np.zeros((len(part), len(angles), vectors.shape[1]),
                                       np.float32), 0
            for row, (digest, pngs, state) in enumerate(rendered):
                if len(pngs) == len(angles):
                    block[row] = vectors[position:position + len(angles)]
                else:
                    block[row] = vectors[position]
                position += len(pngs)
                states[digest] = state
            np.savez(path, digests=np.array(part), vectors=block,
                     states=np.array([states[digest] for digest in part]))
            out.append(block)
            done = first + len(part)
            print("catalogue %d / %d images, %.0f s" % (done, len(digests),
                                                         time.time() - started), flush=True)
    return digests, np.concatenate(out), states


# --- the queries --------------------------------------------------------------------------

def set_queries(args, settings, steps, embed):
    """Return (rows, vectors) of the positive photos of `--set`. The vectors go to
    `vectors/queries-<set>.npz`; a later run reads them."""
    conn = benchmark.open_database(settings.db_path)
    try:
        rows, skipped = benchmark.build_queries(conn, settings.db_path, args.set)
    finally:
        conn.close()
    rows = [row for row in rows if row["label"] == "positive"]
    if args.limit:
        rows = rows[:args.limit]
    path = os.path.join(args.out, "vectors", "queries-%s.npz" % args.set)
    if os.path.exists(path):
        saved = np.load(path, allow_pickle=False)
        if list(saved["ids"]) == [row["image_sha256"] for row in rows]:
            print("set %s: %d query vectors from %s" % (args.set, len(rows), path), flush=True)
            return rows, saved["vectors"]
        raise SystemExit("%s holds other queries; remove it" % path)
    local = threading.local()

    def prepare(row):
        if not hasattr(local, "segmenter"):
            local.segmenter = embedding_run.Sam3Once(derive.Sam3Client())
        image, _ = derive.open_image(row["abs_path"])
        inputs, missing = embedding_run.query_inputs(image, {"full": steps}, local.segmenter)
        if "full" not in inputs:
            raise SystemExit("%s: %s" % (row["image_path"], missing.get("full")))
        return embeddings.png_bytes(inputs["full"])

    started, pngs = time.time(), []
    with concurrent.futures.ThreadPoolExecutor(args.sam3_workers) as pool:
        for number, png in enumerate(pool.map(prepare, rows), 1):
            pngs.append(png)
            if number % 200 == 0:
                print("set %s: %d / %d photos prepared, %.0f s"
                      % (args.set, number, len(rows), time.time() - started), flush=True)
    vectors = embed(pngs)
    np.savez(path, ids=np.array([row["image_sha256"] for row in rows]), vectors=vectors)
    print("set %s: %d positive photos (left out: %s), %.0f s"
          % (args.set, len(rows), dict(skipped), time.time() - started), flush=True)
    return rows, vectors


def turntable_queries(args, steps, embed):
    """Return (rows, vectors) of the turntable photos of `--photos`."""
    paths = sorted(glob.glob(os.path.join(os.path.expanduser(args.photos), "*.jpg")))
    photos = single.photo_inputs(paths, steps,
                                 embedding_run.Sam3Once(derive.Sam3Client()))
    rows = [{"query": "photo %02d" % photo["number"], "image_path": os.path.basename(path),
             "slug": TURNTABLE_WINE, "image": photo["image"]}
            for photo, path in zip(photos, paths)]
    return rows, embed([embeddings.png_bytes(row["image"]) for row in rows])


# --- the scores ---------------------------------------------------------------------------

def wine_scores(queries, vectors, members):
    """Return (single, z): queries x wines, the best cosine of each wine over the 0° vectors
    and over all vectors of its full images. `members` holds the image rows of each wine."""
    count, angles, dim = vectors.shape
    sims = (queries @ vectors.reshape(count * angles, dim).T).reshape(len(queries), count,
                                                                      angles)
    zero = sims[:, :, angles // 2]
    best = sims.max(axis=2)
    return (np.stack([zero[:, rows].max(axis=1) for rows in members], axis=1),
            np.stack([best[:, rows].max(axis=1) for rows in members], axis=1))


def judge(rows, scores, slugs):
    """Return one record for each query: the rank of the true wine (None when the wine has
    no full image), the top wine, and the best other cosine."""
    column = {slug: i for i, slug in enumerate(slugs)}
    out = []
    for row, line in zip(rows, scores):
        top = int(np.argmax(line))
        true = column.get(row["slug"])
        record = {"top1": slugs[top], "rank": None, "true": None, "other": float(line[top])}
        if true is not None:
            record["rank"] = 1 + int((line > line[true]).sum())
            record["true"] = float(line[true])
            others = np.delete(line, true)
            record["other"] = float(others.max())
        out.append(record)
    return out


def metrics(records):
    ranks = [record["rank"] for record in records]
    count = len(ranks)
    return {"n": count,
            "recall_at_1": round(sum(r == 1 for r in ranks) / count, 4),
            "recall_at_5": round(sum(r is not None and r <= 5 for r in ranks) / count, 4),
            "mrr": round(sum(1 / r for r in ranks if r) / count, 4)}


def changes(first, second):
    """Count the queries that the z score changes against the single score."""
    pairs = [(a["rank"] or 10 ** 6, b["rank"] or 10 ** 6) for a, b in zip(first, second)]
    return {"rank1_gained": sum(a > 1 and b == 1 for a, b in pairs),
            "rank1_lost": sum(a == 1 and b > 1 for a, b in pairs),
            "rank_better": sum(b < a for a, b in pairs),
            "rank_worse": sum(b > a for a, b in pairs),
            "rank_same": sum(a == b for a, b in pairs)}


# --- the charts ---------------------------------------------------------------------------

def chart_recall(summary, directory):
    """R@1 and R@5 with one vector and with the copies, for each query side."""
    sides = [side for side in ("set", "turntable") if side in summary["queries"]]
    labels = {"set": "набор «%s» (%d фото)" % (summary["set"], summary["queries"].get(
        "set", {}).get("single", {}).get("n", 0)),
              "turntable": "снимки на столике (%d)" % summary["queries"].get(
                  "turntable", {}).get("single", {}).get("n", 0)}
    fig, axes = plt.subplots(1, len(sides), figsize=(6.2 * len(sides), 4.6),
                             facecolor=plots.SURFACE, squeeze=False)
    for ax, side in zip(axes[0], sides):
        plots.style(ax)
        ax.set_xlim(-0.6, 1.6)
        ax.set_xticks([0, 1])
        ax.xaxis.set_major_formatter(lambda value, _: ("R@1", "R@5")[int(round(value))])
        for offset, (variant, color, name) in zip((-0.17, 0.17), (
                ("single", single.SINGLE, "один вектор"),
                ("z", single.ZMAX, "копии −30°…+30°"))):
            values = [100 * summary["queries"][side][variant][key]
                      for key in ("recall_at_1", "recall_at_5")]
            bars = ax.bar([0 + offset, 1 + offset], values, width=0.3, color=color,
                          label=name, zorder=2)
            for bar, value in zip(bars, values):
                ax.annotate("%.1f %%" % value, (bar.get_x() + bar.get_width() / 2, value),
                            xytext=(0, 3), textcoords="offset points", ha="center",
                            fontsize=9, color=plots.INK)
        ax.set_ylim(0, 105)
        ax.set_ylabel("доля фото, %", color=plots.INK2)
        ax.set_title(labels[side], loc="left", fontsize=11, color=plots.INK)
    axes[0][0].legend(loc="lower left", frameon=False, fontsize=9.5)
    fig.suptitle("NaFlex p512: копии с поворотом по оси z у каждого вина каталога", x=0.01,
                 y=0.98, ha="left", fontsize=13, color=plots.INK)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.82, bottom=0.1, wspace=0.25)
    fig.savefig(os.path.join(directory, "chart-recall.png"), dpi=plots.DPI,
                facecolor=plots.SURFACE)
    plt.close(fig)


def chart_turntable(rows, first, second, directory):
    """The margin of the true wine on each turntable photo: its score minus the best other
    score, with one vector and with the copies. Above 0, the wine has rank 1."""
    numbers = list(range(1, len(rows) + 1))
    fig, ax = plt.subplots(figsize=(14, 6.4), facecolor=plots.SURFACE)
    single.style(ax, numbers)
    ax.axhline(0, color=plots.INK2, lw=1, zorder=1)
    for records, color, name in ((first, single.SINGLE, "один вектор у каждого вина"),
                                 (second, single.ZMAX, "13 копий у каждого вина")):
        ax.plot(numbers, [r["true"] - r["other"] for r in records], color=color, lw=2,
                label=name, zorder=2)
    ax.set_ylabel("косинус вина минус лучший косинус другого вина", color=plots.INK2)
    ax.legend(loc="upper right", frameon=False, fontsize=9.5)
    fig.suptitle("Снимки на столике: запас вина «%s» над лучшим другим вином" % TURNTABLE_WINE,
                 x=0.01, y=0.98, ha="left", fontsize=13, color=plots.INK)
    fig.text(0.01, 0.925, "Выше нуля — вино на первом месте. NaFlex p512; копии −30°…+30° с "
             "шагом 5° у каждого изображения каталога.", fontsize=9.5, color=plots.INK2)
    plots.add_thumbnails(ax, plots.thumbnails({n: row["image"] for n, row in zip(numbers, rows)},
                                              round(0.8 * plots.DPI)), 0.8, offset_pt=18)
    fig.subplots_adjust(left=0.07, right=0.98, top=0.86, bottom=0.25)
    fig.savefig(os.path.join(directory, "chart-turntable-margin.png"), dpi=plots.DPI,
                facecolor=plots.SURFACE)
    plt.close(fig)


def collage_sample(args, sources, states, steps, angles, directory, count=24):
    """Show the copies at −30°, 0°, and +30° of `count` random catalogue images."""
    kinds = [step["step"] for step in steps]
    tail = steps[kinds.index("remove_background") + 1:]
    shown = (angles[0], 0, angles[-1])
    picked = random.Random(1).sample(sorted(sources), count)
    tasks = [(digest, sources[digest]["cuts"]["package"], sources[digest]["cuts"].get("label"),
              tail, list(shown)) for digest in picked]
    with concurrent.futures.ProcessPoolExecutor(args.render_workers) as pool:
        rendered = list(pool.map(render_copies, tasks))
    font = ImageFont.truetype(plots.FONT, 15)
    height, pad, columns = 300, 10, 6
    tiles = []
    for digest, pngs, state in rendered:
        images = [Image.open(__import__("io").BytesIO(png)).convert("RGB") for png in pngs]
        scale = height / max(image.height for image in images)
        images = [image.resize((max(1, round(image.width * scale)), height)) for image in images]
        tiles.append((images, state))
    cell = max(sum(image.width for image in images) + 2 * pad for images, _ in tiles)
    rows = -(-len(tiles) // columns)
    page = Image.new("RGB", (columns * cell, 40 + rows * (height + 30)), "white")
    draw = ImageDraw.Draw(page)
    draw.text((pad, 10), "Автоматическая калибровка: копии −30°, 0°, +30° у %d случайных "
              "изображений каталога" % count, font=font, fill=(11, 11, 11))
    for number, (images, state) in enumerate(tiles):
        x = (number % columns) * cell + pad
        y = 40 + (number // columns) * (height + 30)
        for image in images:
            page.paste(image, (x, y))
            x += image.width + 3
        draw.text(((number % columns) * cell + pad, y + height + 4), state, font=font,
                  fill=(82, 81, 78))
    page.save(os.path.join(directory, "collage-auto-calibration.png"), optimize=True)


# --- the run ------------------------------------------------------------------------------

def write_records(path, rows, first, second):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["query", "image_path", "slug", "rank_single", "rank_z",
                         "true_single", "true_z", "other_single", "other_z", "top1_single",
                         "top1_z"])
        for row, a, b in zip(rows, first, second):
            writer.writerow([row.get("query") or row.get("query_id"), row["image_path"],
                             row["slug"], a["rank"], b["rank"],
                             None if a["true"] is None else round(a["true"], 6),
                             None if b["true"] is None else round(b["true"], 6),
                             round(a["other"], 6), round(b["other"], 6), a["top1"], b["top1"]])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", required=True, help="the output directory")
    parser.add_argument("--set", default="my", help="the test set; its positive photos")
    parser.add_argument("--photos", help="the folder of the turntable photos (.jpg)")
    parser.add_argument("--entry", default=ENTRY)
    parser.add_argument("--z-step", type=int, default=5, help="a divisor of 30")
    parser.add_argument("--batch", type=int, default=16, help="images per request")
    parser.add_argument("--workers", type=int, default=4, help="parallel embedding requests")
    parser.add_argument("--sam3-workers", type=int, default=4)
    parser.add_argument("--render-workers", type=int, default=8)
    parser.add_argument("--limit", type=int, help="the first N positive photos of the set")
    args = parser.parse_args(argv)
    os.makedirs(os.path.join(args.out, "vectors"), exist_ok=True)
    angles = list(range(-int(ANGLE_LIMIT), int(ANGLE_LIMIT) + 1, args.z_step))
    if 0 not in angles:
        raise SystemExit("--z-step MUST divide 30, so that 0° is an angle")
    started = time.time()

    settings = embeddings.load_settings()
    embedding = settings.find(args.entry)
    steps = single.full_steps(embedding)
    embed = Embedder(embedding, args.batch, args.workers)
    conn = embeddings.open_database(settings.db_path)
    wines, sources = embeddings.read_inputs(conn, settings.db_path)
    conn.close()
    full = {digest: source for digest, source in sources.items()
            if source["role"] == "full" and source["cuts"].get("package")}
    digests, vectors, states = catalogue_copies(args, full, steps, angles, embed)
    row_of = {digest: i for i, digest in enumerate(digests)}
    slugs, members = [], []
    for wine in wines:
        rows = sorted({row_of[digest] for _, digest in wine["columns"] if digest in row_of})
        if rows:
            slugs.append(wine["slug"])
            members.append(rows)
    state_counts = collections.Counter(state.split(":")[0] for state in states.values())
    print("catalogue: %d images of %d wines, calibration %s" % (len(digests), len(slugs),
                                                              dict(state_counts)), flush=True)
    with open(os.path.join(args.out, "calibration.csv"), "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["source_sha256", "state"])
        writer.writerows(sorted(states.items()))

    summary = {"entry": args.entry, "set": args.set, "z_angles": angles,
               "catalogue_images": len(digests), "wines": len(slugs),
               "calibration": dict(state_counts), "queries": {}}
    sides = [("set", set_queries(args, settings, steps, embed))]
    if args.photos:
        sides.append(("turntable", turntable_queries(args, steps, embed)))
    for side, (rows, queries) in sides:
        first, second = wine_scores(queries, vectors, members)
        first, second = judge(rows, first, slugs), judge(rows, second, slugs)
        summary["queries"][side] = {"single": metrics(first), "z": metrics(second),
                                    "changes": changes(first, second)}
        write_records(os.path.join(args.out, "results-%s.csv" % side), rows, first, second)
        print("%s: single %s, z %s, %s" % (side, summary["queries"][side]["single"],
                                           summary["queries"][side]["z"],
                                           summary["queries"][side]["changes"]), flush=True)
        if side == "turntable":
            chart_turntable(rows, first, second, args.out)
    summary["seconds"] = round(time.time() - started)
    with open(os.path.join(args.out, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    plt.rcParams.update({"font.size": 9.5, "text.color": plots.INK,
                         "axes.labelcolor": plots.INK2})
    chart_recall(summary, args.out)
    collage_sample(args, full, states, steps, angles, args.out)
    print("wrote %s in %d s" % (args.out, summary["seconds"]))


if __name__ == "__main__":
    main()
