#!/usr/bin/env python3
"""Compare turntable photos of one bottle with its catalogue cut (a z-rotation test).

Owner messages of about 2026-09-30T23:56:00+0300 and 2026-10-01T00:10:00+0300. The photos
of `--photos` show one bottle on a turntable during one turn of 360° about the vertical
axis of the bottle (the z axis). Each photo gets the steps of the view `full` of the
index: the SAM3 package cut (`embedding_run.cuts_of`), the mask on white, and the index
`resize`. So a photo gets the pixels of a catalogue image.

The reference side is the catalogue cut `CUT_SHA256` of the wine `winemaker-selection`
with the steps of the view `full`. `tools/bottle_rotation` turns the cut about its
vertical axis from -30° to +30° in steps of `--z-step` (`CALIBRATION`); positive angles
move the label to the right. The 0° image is the cut itself, so the 0° vector is the
vector of the catalogue cut. For each photo and entry, the script writes:

- `cosine`: the cosine to the 0° vector;
- `zmax_cosine` and `zmax_angle`: the maximum cosine over the turned vectors, and its
  angle;
- `rank`, `best_other_cosine`, `best_other_slug`: the rank of the wine among the `full`
  vectors of the index (the best item of each wine), as in `rotation_similarity.py`.

The script is read-only for the catalogue and for the indexes. It sends the photos to
SAM3 (the answers go to `data/cache/models/sam3/`) and the images to the `base_url` of
each entry in `config.yaml`. With `--plots-only`, it reads the files of `--out` and draws
the charts again with no request.

    python3 scripts/zrotation_similarity.py --photos ~/Downloads/winemaker-selection-z-rotation \\
        --out docs/reports/zrotation-similarity-2026-10-01
"""

import argparse
import collections
import csv
import datetime
import glob
import json
import os
import re
import sys
import textwrap

import numpy as np
from PIL import Image, ImageDraw, ImageFont

WORKBENCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(WORKBENCH, "pipeline"))
sys.path.insert(0, os.path.join(os.path.dirname(WORKBENCH), "tools", "bottle_rotation"))
import build_embeddings  # noqa: E402
import derive  # noqa: E402
import embedding_run  # noqa: E402
import embeddings  # noqa: E402
import rotation_similarity_plots as plots  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from rotate_bottle import ANGLE_LIMIT, BottleRotator  # noqa: E402
from rotation_similarity import (  # noqa: E402
    ENTRIES, full_steps, load_entry, normalise, row_of, wine_rows)

plt = plots.plt

# The package cut of the `main` image of `winemaker-selection` (method `crop`, alpha).
CUT_SHA256 = "38e6b4e9566b8416d3231fa9daf08f6806223a7abae34f4ce6c5220b38d40ef0"
# The calibration of `tools/bottle_rotation` for this cut (295 x 1094 pixels): the front
# label and the print on the neck. Measured on the cut on 2026-10-01: the top edge of the
# label runs from y 671 at the sides to y 679 in the centre, the bottom edge of the gold
# band from y 995 to y 1002. The polygon lies 2 pixels outside these edges. The white
# print "INKERMAN" on the black capsule is at y 163 to 180; `ink` takes its light pixels.
CALIBRATION = {
    "version": 1,
    "reference_size": [295, 1094],
    "layers": [
        {"name": "label",
         "polygons": [[[0, 669], [30, 672], [50, 674], [80, 676], [100, 677], [180, 677],
                       [210, 676], [240, 674], [260, 669], [295, 668], [295, 996],
                       [250, 997], [220, 1000], [190, 1002], [150, 1003], [110, 1004],
                       [80, 1003], [50, 1000], [20, 996], [0, 995]]],
         "distance": 300, "camera_y": 837, "fill": "vertical", "smooth_profile": True},
        {"name": "neck-print",
         "polygons": [[[95, 159], [205, 159], [205, 184], [95, 184]]],
         "ink": {"min_mean": 110}, "dilate": 1,
         "distance": 300, "camera_y": 837, "fill": "inpaint"},
    ],
}
# A Pixel file name holds the local time of the photo with milliseconds.
PHOTO_TIME = re.compile(r"_(\d{8})_(\d{6})(\d{3})\.")


def photo_time(name):
    """Return the time of a photo from its file name, or None."""
    match = PHOTO_TIME.search(name)
    if not match:
        return None
    moment = datetime.datetime.strptime(match.group(1) + match.group(2), "%Y%m%d%H%M%S")
    return moment + datetime.timedelta(milliseconds=int(match.group(3)))


def same(first, second):
    """Tell whether two images have the same size and the same pixels."""
    return first.size == second.size and np.array_equal(np.asarray(first), np.asarray(second))


def find_source(sources, digest):
    """Return (sha256 of the original, source) whose package cut is `digest`."""
    for sha, source in sources.items():
        cut = source["cuts"].get("package")
        if cut is not None and cut["sha256"] == digest:
            return sha, source
    raise SystemExit("no catalogue image has the package cut %s" % digest)


def turned_inputs(cut_path, steps, angles):
    """Return {angle: model input} of the cut turned about its vertical axis. The steps
    after `remove_background` of the view `full` make the model input of each angle."""
    kinds = [step["step"] for step in steps]
    tail = steps[kinds.index("remove_background") + 1:]
    with Image.open(cut_path) as opened:
        rotator = BottleRotator(opened, CALIBRATION)
    if [rotator.width, rotator.height] != CALIBRATION["reference_size"]:
        raise SystemExit("the cut is %d x %d pixels; the calibration is for %s"
                         % (rotator.width, rotator.height, CALIBRATION["reference_size"]))
    return {angle: embeddings.apply_steps(rotator.render(angle), tail, None, None)
            for angle in angles}


def photo_inputs(paths, steps, segmenter):
    """Return a list of dicts: the model input of each photo and its SAM3 cut."""
    out = []
    for number, path in enumerate(paths, 1):
        image, _ = derive.open_image(path)
        trace = embedding_run.Trace()
        cuts = embedding_run.cuts_of(image, {"package"}, segmenter, trace)
        prepared, reason = embedding_run.view_input(image, steps, cuts)
        if prepared is None:
            raise SystemExit("%s: %s" % (path, reason))
        step = trace.steps[0]
        out.append({"number": number, "path": path, "image": prepared,
                    "size": list(image.size), "box": step["out"]["box"],
                    "rule": step["out"]["rule"], "cached": step.get("cached")})
        print("photo %d %s: %s, box %s, input %s, SAM3 cached %s"
              % (number, os.path.basename(path), step["out"]["rule"], step["out"]["box"],
                 prepared.size, step.get("cached")), flush=True)
    return out


def embed_all(backend, images, batch):
    got = []
    for start in range(0, len(images), batch):
        got.extend(backend.embed([embeddings.png_bytes(image)
                                  for image in images[start:start + batch]]))
    return normalise(got)


def compute(args):
    os.makedirs(os.path.join(args.out, "images"), exist_ok=True)
    os.makedirs(os.path.join(args.out, "vectors"), exist_ok=True)
    paths = sorted(glob.glob(os.path.join(os.path.expanduser(args.photos), "*.jpg")))
    if not paths:
        raise SystemExit("no .jpg photo in %s" % args.photos)
    times = [photo_time(os.path.basename(path)) for path in paths]

    settings = embeddings.load_settings()
    loaded = {name: load_entry(settings, name) for name in args.entries}
    conn = embeddings.open_database(settings.db_path)
    wines, sources = embeddings.read_inputs(conn, settings.db_path)
    conn.close()
    digest, source = find_source(sources, CUT_SHA256)
    sha_to_slug = {}
    for other in wines:
        for _, sha in other["columns"]:
            if sources.get(sha, {}).get("role") == "full":
                sha_to_slug.setdefault(sha, other["slug"])
    slug = sha_to_slug.get(digest)
    print("cut %s of the image %s of the wine %s" % (CUT_SHA256, digest, slug), flush=True)

    # The view `full`: `prepare` MUST give the stored index image, and the 0° turned image
    # MUST give the same pixels.
    first = loaded[args.entries[0]]
    steps = full_steps(first[0])
    for name, (embedding, _, _, _) in loaded.items():
        if full_steps(embedding) != steps:
            raise SystemExit("%s: the view full has other steps" % name)
    item = row_of(first[2], digest)
    stored = Image.open(os.path.join(first[1], item["image"])).convert("RGB")
    plan = embeddings.plan_items(first[0], {digest: source})[(digest, "full")]
    prepared = embeddings.prepare(plan, source["path"])
    print("prepare() equals the stored index image: %s (%s)" % (same(prepared, stored),
                                                                stored.size), flush=True)
    angles = list(range(-int(ANGLE_LIMIT), int(ANGLE_LIMIT) + 1, args.z_step))
    if 0 not in angles:
        raise SystemExit("--z-step MUST divide 30, so that 0° is an angle")
    turned = turned_inputs(source["cuts"]["package"]["path"], steps, angles)
    print("the 0° turned image equals prepare(): %s" % same(turned[0], prepared), flush=True)
    for angle, picture in turned.items():
        picture.save(os.path.join(args.out, "images", "z%+03d.png" % angle))

    photos = photo_inputs(paths, steps, embedding_run.Sam3Once(derive.Sam3Client()))
    for photo in photos:
        photo["image"].save(os.path.join(args.out, "images", "photo_%02d.png"
                                         % photo["number"]))

    rows, zrows, checks = [], [], {}
    images = [turned[angle] for angle in angles] + [photo["image"] for photo in photos]
    for name, (embedding, directory, index, vectors) in loaded.items():
        backend = build_embeddings.OpenAIBackend(embedding)
        got = embed_all(backend, images, args.batch)
        zvectors, pvectors = got[:len(angles)], got[len(angles):]
        zero = zvectors[angles.index(0)]
        stored_vector = normalise(vectors[row_of(index, digest)["row"]])
        checks[name] = round(float(zero @ stored_vector), 6)
        print("%s: the 0° vector against the stored index vector: cosine %.6f"
              % (name, checks[name]), flush=True)
        slugs, item_rows = wine_rows(index, sha_to_slug)
        catalogue = normalise(vectors[item_rows])
        np.savez(os.path.join(args.out, "vectors", "%s.npz" % name), z_angles=angles,
                 z=zvectors.astype(np.float32), photos=pvectors.astype(np.float32),
                 stored=stored_vector.astype(np.float32))
        for photo, vector in zip(photos, pvectors):
            scores = catalogue @ vector
            best = {}
            for wine, score in zip(slugs, scores):
                if score > best.get(wine, -2.0):
                    best[wine] = score
            ranking = sorted(best, key=best.get, reverse=True)
            other = next(wine for wine in ranking if wine != slug)
            zscores = zvectors @ vector
            top = int(np.argmax(zscores))
            moment = times[photo["number"] - 1]
            rows.append({
                "entry": name, "photo": photo["number"],
                "file": os.path.basename(photo["path"]),
                "time_s": (round((moment - times[0]).total_seconds(), 3)
                           if moment and times[0] else ""),
                "width": photo["image"].width, "height": photo["image"].height,
                "cosine": round(float(zero @ vector), 6),
                "cosine_stored": round(float(stored_vector @ vector), 6),
                "zmax_cosine": round(float(zscores[top]), 6), "zmax_angle": angles[top],
                "rank": ranking.index(slug) + 1,
                "best_other_cosine": round(float(best[other]), 6),
                "best_other_slug": other})
            zrows.extend({"entry": name, "photo": photo["number"], "z_angle": angle,
                          "cosine": round(float(score), 6)}
                         for angle, score in zip(angles, zscores))
        print("%s: %d images" % (name, len(images)), flush=True)

    for file_name, table in (("results.csv", rows), ("z_cosines.csv", zrows)):
        with open(os.path.join(args.out, file_name), "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(table[0]))
            writer.writeheader()
            writer.writerows(table)
    wine = next(wine for wine in wines if wine["slug"] == slug)
    meta = {"wine": {key: wine[key] for key in ("slug", "name", "producer", "category")},
            "cut_sha256": CUT_SHA256, "source_sha256": digest,
            "index_image": item["image"], "index_image_size": list(stored.size),
            "prepare_equals_stored": same(prepared, stored),
            "turned_zero_equals_prepare": same(turned[0], prepared),
            "z_angles": angles, "calibration": CALIBRATION,
            "photos": [{"number": photo["number"], "file": os.path.basename(photo["path"]),
                        "size": photo["size"], "box": photo["box"], "rule": photo["rule"],
                        "input_size": list(photo["image"].size)} for photo in photos],
            "photo_folder": os.path.abspath(os.path.expanduser(args.photos)),
            "zero_vs_stored_cosine": checks, "batch": args.batch,
            "entries": {name: loaded[name][0].base_url for name in args.entries}}
    with open(os.path.join(args.out, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
    print("wrote %s" % os.path.join(args.out, "results.csv"))


# The charts have Russian text, as the charts of `rotation_similarity_plots.py` (owner
# message of 2026-09-29T01:23:58+0300). Slots 1 and 2 of the palette; the muted ink for the
# best other wine.
SINGLE, ZMAX, OTHER = plots.PALETTE[0], plots.PALETTE[1], "#898781"
LABEL_DESIGN = ("На снимках — новая этикетка (2025, зелёная полоса WINEMAKER'S SELECTION), "
                "в каталоге — старая (2019, золотая полоса).")


def read_rows(directory):
    """Return {entry without the prefix: {photo: row}} of `results.csv`."""
    data = collections.defaultdict(dict)
    with open(os.path.join(directory, "results.csv"), encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            data[row["entry"].replace(plots.PREFIX, "")][int(row["photo"])] = row
    return data


def column(rows, numbers, key):
    return [float(rows[number][key]) for number in numbers]


def style(ax, numbers, ticks=None):
    plots.style(ax)
    ax.set_xlim(numbers[0] - 0.6, numbers[-1] + 0.6)
    ax.set_xticks(ticks or numbers)
    ax.xaxis.set_major_formatter(lambda value, _: "%d" % value)
    ax.tick_params(axis="x", labelsize=7.5)


def limits(values):
    """The limits of the cosine axis, in steps of 0.05."""
    return plots.low_limit(values), max(0.9, np.ceil((max(values) + 0.02) * 20) / 20)


def subtitle(meta):
    return ("Вино: «%s» (%s). %d снимков одного оборота на поворотном столике. SAM3 вырезает "
            "бутылку, фон белый (шаги вида full индекса). Эталон — вырез каталога %s… на белом "
            "фоне." % (meta["wine"]["name"], meta["wine"]["producer"], len(meta["photos"]),
                       meta["cut_sha256"][:8]))


def chart_models(data, meta, directory, photos, zmax=False):
    """The six entries in one panel. Without `zmax`: the cosine of each photo to the one
    vector of the catalogue cut, with no synthetic rotation; an open circle marks a photo
    where another wine is nearer (rank > 1). With `zmax` (owner answer of about
    2026-10-01T00:28:00+0300): the maximum cosine over the turned copies; an open circle
    marks a photo where the best other wine is at or above this maximum. That mark is
    optimistic: the other wines keep one vector. Both charts use one cosine axis."""
    entries = plots.entries_of(data)
    numbers = sorted(photos)
    key = "zmax_cosine" if zmax else "cosine"
    angles = ("%+d°…%+d°" % (meta["z_angles"][0], meta["z_angles"][-1])).replace("-", "−")
    fig, ax = plt.subplots(figsize=(14, 7.6), facecolor=plots.SURFACE)
    style(ax, numbers)
    ends = []
    for entry in entries:
        rows = data[entry]
        color = plots.model_color(entry, entries)
        cosines = column(rows, numbers, key)
        ax.plot(numbers, cosines, color=color, lw=2, label=plots.TITLES.get(entry, entry))
        missed = [(n, c) for n, c in zip(numbers, cosines)
                  if (c <= float(rows[n]["best_other_cosine"]) if zmax
                      else int(rows[n]["rank"]) > 1)]
        if missed:
            ax.scatter(*zip(*missed), s=24, facecolors=plots.SURFACE, edgecolors=color,
                       linewidths=1.3, zorder=3)
        ends.append(cosines[-1])
    low, high = limits([float(data[entry][n][name]) for entry in entries for n in numbers
                        for name in ("cosine", "zmax_cosine")])
    for entry, y in zip(entries, plots.spread(ends, 0.014 * (high - low) / 0.325)):
        ax.annotate(plots.TITLES.get(entry, entry),
                    xy=(numbers[-1] + 0.1, float(data[entry][numbers[-1]][key])),
                    xytext=(numbers[-1] + 1.3, y), textcoords="data", fontsize=9,
                    color=plots.INK, va="center", annotation_clip=False,
                    arrowprops={"arrowstyle": "-", "color": plots.INK2, "lw": 0.6,
                                "shrinkA": 0, "shrinkB": 2})
    ax.set_ylim(low, high)
    ax.set_ylabel("наибольшее косинусное сходство по копиям" if zmax
                  else "косинусное сходство с вырезом каталога", color=plots.INK2)
    handles, labels = ax.get_legend_handles_labels()
    handles.append(Line2D([], [], ls="none", marker="o", ms=5.5, mfc=plots.SURFACE,
                          mec=plots.INK2, mew=1.3))
    labels.append("кружок: другое вино ближе")
    ax.legend(handles, labels, loc="upper center", ncol=len(labels), frameon=False,
              fontsize=9.5, bbox_to_anchor=(0.5, 1.085))
    if zmax:
        title = ("%s: максимум сходства по %d копиям изображения каталога, повёрнутым по оси z "
                 "(%s)" % (plots.family(entries), len(meta["z_angles"]), angles))
        text = ("Копии: tools/bottle_rotation поворачивает вырез каталога вокруг вертикальной "
                "оси с шагом %d° (0° — сам вырез). Для каждого снимка — наибольший косинус по "
                "копиям. " % (meta["z_angles"][1] - meta["z_angles"][0]) + subtitle(meta))
    else:
        title = ("%s: сходство снимков с одним вектором изображения каталога (без "
                 "синтетического поворота)" % plots.family(entries))
        text = subtitle(meta)
    fig.suptitle(title, x=0.01, y=0.985, ha="left", fontsize=13, color=plots.INK)
    fig.text(0.01, 0.94, textwrap.fill(text, 175), fontsize=9.5, color=plots.INK2, va="top")
    fig.text(0.01, 0.038, "Ось x: номер снимка в порядке съёмки. Под осью: вход модели для "
             "каждого снимка (общий масштаб, чёрная рамка — граница изображения). Один оборот "
             "≈ 31 снимок: снимок 32 похож на снимок 1.", fontsize=9, color=plots.INK2)
    fig.text(0.01, 0.012, LABEL_DESIGN + (" Кружок здесь оптимистичен: у других вин один "
                                          "вектор." if zmax else ""),
             fontsize=9, color=plots.INK2)
    plots.add_thumbnails(ax, plots.thumbnails(photos, round(0.8 * plots.DPI)), 0.8,
                         offset_pt=18)
    fig.subplots_adjust(left=0.055, right=0.885, top=0.81, bottom=0.25)
    fig.savefig(os.path.join(directory, "chart-models-zmax.png" if zmax else "chart-models.png"),
                dpi=plots.DPI, facecolor=plots.SURFACE)
    plt.close(fig)


def chart_by_model(data, meta, directory, photos, step=4):
    """One panel for each entry: the cosine to the 0° vector, the maximum cosine over the
    turned vectors, and the best cosine of another wine."""
    entries = plots.entries_of(data)
    numbers = sorted(photos)
    ticks = numbers[::step]
    angles = meta["z_angles"]
    fig, axes, height = plots.grid(len(entries), row_in=3.225, top_in=1.62, bottom_in=1.15)
    values = [float(data[e][n][key]) for e in entries for n in numbers
              for key in ("cosine", "zmax_cosine", "best_other_cosine")]
    low, high = limits(values)
    thumbs = plots.thumbnails({n: photos[n] for n in ticks}, round(0.5 * plots.DPI))
    for ax, entry in zip(axes.flat, entries):
        style(ax, numbers, ticks)
        rows = data[entry]
        ax.plot(numbers, column(rows, numbers, "best_other_cosine"), color=OTHER, lw=1.2,
                label="лучшее другое вино индекса (один вектор)")
        ax.plot(numbers, column(rows, numbers, "cosine"), color=SINGLE, lw=2,
                label="один вектор: вырез каталога")
        ax.plot(numbers, column(rows, numbers, "zmax_cosine"), color=ZMAX, lw=2,
                label=("максимум по %d копиям выреза, повёрнутым на %+d°…%+d° по оси z"
                       % (len(angles), angles[0], angles[-1])).replace("-", "−"))
        ax.set_title(plots.TITLES.get(entry, entry), loc="left", fontsize=11, color=plots.INK)
        ax.set_ylim(low, high)
        plots.add_thumbnails(ax, thumbs, 0.5)
    for ax in axes[:, 0]:
        ax.set_ylabel("косинусное сходство", color=plots.INK2)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    top = lambda inches: 1 - inches / height  # noqa: E731
    fig.legend(handles[::-1], labels[::-1], loc="upper left", ncol=3, frameon=False,
               bbox_to_anchor=(0.01, top(0.9)), fontsize=9.5)
    fig.suptitle("%s: один вектор против максимума по копиям, повёрнутым вокруг оси бутылки"
                 % plots.family(entries), x=0.01, y=top(0.086), ha="left", fontsize=13,
                 color=plots.INK)
    fig.text(0.01, top(0.36), textwrap.fill(
        "tools/bottle_rotation поворачивает вырез каталога вокруг вертикальной оси с шагом "
        "%d° (0° — сам вырез). Для каждого снимка — наибольший косинус по этим векторам. "
        "У других вин индекса один вектор. " % (angles[1] - angles[0]) + subtitle(meta),
        150), fontsize=9.5, color=plots.INK2, va="top")
    fig.text(0.01, 0.086 / height, "Под осью: вход модели для снимков %s. " % ", ".join(
        str(n) for n in ticks) + LABEL_DESIGN, fontsize=9, color=plots.INK2)
    fig.subplots_adjust(left=0.06, right=0.985, top=top(1.62), bottom=1.15 / height,
                        hspace=0.55, wspace=0.12)
    fig.savefig(os.path.join(directory, "chart-by-model.png"), dpi=plots.DPI,
                facecolor=plots.SURFACE)
    plt.close(fig)


def chart_gain(data, meta, directory, photos, step=4):
    """One panel for each entry: the gain of each photo, the maximum cosine over the turned
    copies minus the cosine to the one vector (owner message of about
    2026-10-01T00:31:00+0300: the curves of the other charts are too near to compare). A
    grey band marks a photo where the wine is already the nearest wine with the one vector.
    An orange bar marks a photo where the wine becomes the nearest wine only with the
    copies. That count is optimistic: the other wines keep one vector."""
    entries = plots.entries_of(data)
    numbers = sorted(photos)
    ticks = numbers[::step]
    angles = ("%+d°…%+d°" % (meta["z_angles"][0], meta["z_angles"][-1])).replace("-", "−")
    gains = {entry: [float(data[entry][n]["zmax_cosine"]) - float(data[entry][n]["cosine"])
                     for n in numbers] for entry in entries}
    high = max(0.05, np.ceil(max(max(values) for values in gains.values()) * 100) / 100)
    fig, axes, height = plots.grid(len(entries), row_in=2.9, top_in=1.3, bottom_in=1.15)
    thumbs = plots.thumbnails({n: photos[n] for n in ticks}, round(0.5 * plots.DPI))
    for ax, entry in zip(axes.flat, entries):
        style(ax, numbers, ticks)
        rows = data[entry]
        for n in numbers:
            if int(rows[n]["rank"]) == 1:
                ax.axvspan(n - 0.5, n + 0.5, color=plots.BAND_COLOR, lw=0, zorder=0)
        new = [n for n in numbers if int(rows[n]["rank"]) > 1
               and float(rows[n]["zmax_cosine"]) > float(rows[n]["best_other_cosine"])]
        ax.bar(numbers, gains[entry], width=0.62, zorder=2,
               color=[ZMAX if n in new else SINGLE for n in numbers])
        ax.set_ylim(0, high)
        ax.yaxis.set_major_formatter(lambda value, _: "%+.2f" % value if value else "0")
        ax.set_title(plots.TITLES.get(entry, entry), loc="left", fontsize=11, color=plots.INK)
        ax.set_title("ср. %+.3f · новых первых: %d"
                     % (float(np.mean(gains[entry])), len(new)), loc="right", fontsize=9,
                     color=plots.INK2)
        plots.add_thumbnails(ax, thumbs, 0.5)
    for ax in axes[:, 0]:
        ax.set_ylabel("прирост косинуса", color=plots.INK2)
    handles = [Patch(color=SINGLE, label="прирост: максимум по копиям − один вектор"),
               Patch(color=ZMAX, label="с копиями вино становится первым (оптимистично)"),
               Patch(color=plots.BAND_COLOR, label="вино первое уже с одним вектором")]
    top = lambda inches: 1 - inches / height  # noqa: E731
    fig.legend(handles=handles, loc="upper left", ncol=3, frameon=False,
               bbox_to_anchor=(0.01, top(0.78)), fontsize=9.5)
    fig.suptitle("%s: что дают %d синтетических копий с поворотом по оси z (%s)"
                 % (plots.family(entries), len(meta["z_angles"]), angles), x=0.01,
                 y=top(0.086), ha="left", fontsize=13, color=plots.INK)
    fig.text(0.01, top(0.36), textwrap.fill(
        "Для каждого снимка: наибольший косинус по копиям минус косинус к одному вектору "
        "выреза каталога (копия 0° — сам вырез, поэтому прирост не меньше нуля). Первое место "
        "с копиями оптимистично: у других вин индекса один вектор. Вино: «%s», %d снимков "
        "одного оборота. Над панелью справа: средний прирост и число новых первых мест."
        % (meta["wine"]["name"], len(meta["photos"])), 150),
        fontsize=9.5, color=plots.INK2, va="top")
    fig.text(0.01, 0.086 / height, "Под осью: вход модели для снимков %s. " % ", ".join(
        str(n) for n in ticks) + LABEL_DESIGN, fontsize=9, color=plots.INK2)
    fig.subplots_adjust(left=0.06, right=0.985, top=top(1.3), bottom=1.15 / height,
                        hspace=0.55, wspace=0.12)
    fig.savefig(os.path.join(directory, "chart-gain.png"), dpi=plots.DPI,
                facecolor=plots.SURFACE)
    plt.close(fig)


def collage(path, tiles, title, note, columns, cell_h=420):
    """The tiles (label, image) at one common scale; a black frame marks each image
    border. The tallest image fills the cell height."""
    scale = (cell_h - 8) / max(image.height for _, image in tiles)
    cell_w = max(56, round(max(image.width for _, image in tiles) * scale) + 12)
    font = ImageFont.truetype(plots.FONT, 18)
    title_font = ImageFont.truetype(plots.FONT, 26)
    small = ImageFont.truetype(plots.FONT, 17)
    rows = -(-len(tiles) // columns)
    label_h, head_h, pad = 28, 74, 12
    width = max(columns * cell_w + (columns + 1) * pad,
                round(max(title_font.getlength(title), small.getlength(note))) + 2 * pad)
    page = Image.new("RGB", (width, head_h + rows * (cell_h + label_h) + (rows + 1) * pad),
                     (255, 255, 255))
    draw = ImageDraw.Draw(page)
    draw.text((pad, 12), title, font=title_font, fill=(11, 11, 11))
    draw.text((pad, 48), note, font=small, fill=(82, 81, 78))
    for number, (label, image) in enumerate(tiles):
        tile = plots.framed(image.resize((max(1, round(image.width * scale)),
                                          max(1, round(image.height * scale))),
                                         Image.Resampling.LANCZOS), 2)
        x0 = pad + (number % columns) * (cell_w + pad)
        y0 = head_h + pad + (number // columns) * (cell_h + label_h + pad)
        page.paste(tile, (x0 + (cell_w - tile.width) // 2, y0 + (cell_h - tile.height) // 2))
        text_w = draw.textlength(label, font=font)
        draw.text((x0 + (cell_w - text_w) / 2, y0 + cell_h + 4), label, font=font,
                  fill=(11, 11, 11))
    page.save(path, optimize=True)


def summary(data, directory):
    """Write `summary.csv`: the means over the photos and the photos with rank 1 for each
    entry. `zmax_first` counts the photos where the maximum over the turned vectors is above
    the best other wine. It is optimistic: the other wines keep one vector."""
    out = []
    for entry in plots.entries_of(data):
        rows = [data[entry][n] for n in sorted(data[entry])]
        single = np.array([float(r["cosine"]) for r in rows])
        zmax = np.array([float(r["zmax_cosine"]) for r in rows])
        other = np.array([float(r["best_other_cosine"]) for r in rows])
        gain = zmax - single
        first = [int(r["photo"]) for r in rows if int(r["rank"]) == 1]
        out.append({"entry": entry, "photos": len(rows),
                    "mean_cosine": round(float(single.mean()), 3),
                    "max_cosine": round(float(single.max()), 3),
                    "max_photo": int(rows[int(single.argmax())]["photo"]),
                    "mean_zmax": round(float(zmax.mean()), 3),
                    "mean_gain": round(float(gain.mean()), 3),
                    "max_gain": round(float(gain.max()), 3),
                    "rank1": len(first), "rank1_photos": " ".join(map(str, first)),
                    "zmax_first": int((zmax > other).sum())})
    with open(os.path.join(directory, "summary.csv"), "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(out[0]))
        writer.writeheader()
        writer.writerows(out)
    for row in out:
        print(row)


def draw(directory):
    data = read_rows(directory)
    with open(os.path.join(directory, "meta.json"), encoding="utf-8") as fh:
        meta = json.load(fh)
    plt.rcParams.update({"font.size": 9.5, "text.color": plots.INK,
                         "axes.labelcolor": plots.INK2})
    photos = {item["number"]: Image.open(os.path.join(
        directory, "images", "photo_%02d.png" % item["number"])).convert("RGB")
        for item in meta["photos"]}
    chart_models(data, meta, directory, photos)
    chart_models(data, meta, directory, photos, zmax=True)
    chart_by_model(data, meta, directory, photos)
    chart_gain(data, meta, directory, photos)
    turned = []
    for angle in meta["z_angles"]:
        name = os.path.join(directory, "images", "z%+03d.png" % angle)
        turned.append((("%+d°" % angle).replace("-", "−"), Image.open(name).convert("RGB")))
    collage(os.path.join(directory, "collage-z.png"), turned,
            "Копии выреза каталога, повёрнутые вокруг оси бутылки (tools/bottle_rotation)",
            "Положительный угол сдвигает этикетку вправо. 0° — сам вырез. Общий масштаб, "
            "чёрная рамка — граница входа модели.", columns=13)
    collage(os.path.join(directory, "collage-photos.png"),
            [(str(number), photos[number]) for number in sorted(photos)],
            "Снимки на поворотном столике: вход модели (вырез SAM3 на белом фоне)",
            "Номер — порядок съёмки. Общий масштаб, чёрная рамка — граница входа модели.",
            columns=17)
    summary(data, directory)
    print("wrote the charts and the collages to %s" % directory)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", required=True, help="the output directory")
    parser.add_argument("--photos", help="the folder of the turntable photos (.jpg)")
    parser.add_argument("--z-step", type=int, default=5, help="the step of the turned "
                        "reference images in degrees")
    parser.add_argument("--batch", type=int, default=8, help="images per request")
    parser.add_argument("--entries", nargs="*", default=list(ENTRIES))
    parser.add_argument("--plots-only", action="store_true",
                        help="draw the charts from the files of --out; send no request")
    args = parser.parse_args(argv)
    if not args.plots_only:
        if not args.photos:
            parser.error("--photos is required without --plots-only")
        compute(args)
    draw(args.out)


if __name__ == "__main__":
    main()
