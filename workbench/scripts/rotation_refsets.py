#!/usr/bin/env python3
"""Rotation tests with several reference sets of one catalogue image.

Owner message of 2026-09-29T01:44:56+0300. `rotation_multiref.py` gives the reference side
10 vectors (0° to 45° in steps of 5°). This script compares more reference sets, as
start:end:step in degrees: 0:45:5 (the set of `rotation_multiref.py`, for comparison),
0:355:5, 0:359:1, 0:45:1, 0:90:5, and 0:90:1. A reference image is the index image on
white, rotated counter-clockwise with the method of `rotation_similarity.py`. The score of
a query is the maximum cosine over the vectors of a set.

The script embeds the union of the reference angles one time for each entry and takes the
vectors of each set from it. The query side is the side of `rotation_similarity.py`: 0°
to 355° in steps of 5°, on white and on black. A white query at a multiple of 5° has the
pixels of a reference image of each set that holds its angle, so its score is 1.000. So
the script also sends white queries with an angle offset (`--offset`, default 2.5°):
2.5°, 7.5°, ..., 357.5°.

Each set gets its own folder `<out>/refs-<start>-<end>-step<step>/` with `results.csv`,
`meta.json`, `vectors/<entry>.npz`, and the charts. `<out>/summary.csv` and the charts
`<out>/chart-summary-*.png` compare the sets. The images are in `<out>/reference/` and
`<out>/images/`, one time. The script does not change the catalogue index.

    python3 scripts/rotation_refsets.py --out docs/reports/rotation-similarity-2026-09-29/refsets
    python3 scripts/rotation_refsets.py --out docs/reports/rotation-similarity-2026-09-29/refsets --plots-only
"""

import argparse
import collections
import csv
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rotation_multiref  # noqa: E402
import rotation_similarity as rs  # noqa: E402  (it adds pipeline/ to sys.path)
import rotation_similarity_plots as plots  # noqa: E402
from rotation_similarity import build_embeddings, embeddings  # noqa: E402

SETS = ("0:45:5", "0:90:5", "0:355:5", "0:45:1", "0:90:1", "0:359:1")
KEYS = ("white", "black", "white_offset")


def parse_set(text):
    start, end, step = (int(part) for part in text.split(":"))
    angles = [angle for angle in range(start, end + 1, step) if angle < 360]
    end = angles[-1]  # "0:359:3" names the last angle, 357°
    return {"start": start, "end": end, "step": step, "angles": angles,
            "name": "refs-%03d-%03d-step%d" % (start, end, step)}


def angle_label(angle):
    return "%g" % angle


def query_sets(step, offset):
    angles = list(range(0, 360, step))
    return {"white": angles, "black": angles,
            "white_offset": [angle + offset for angle in angles]}


def saved_vectors(out, name, ref_angles, queries):
    """Return the reference vectors, the query vectors, and the reference angles of the
    union file `<out>/vectors/<name>.npz` of an earlier run. Stop when an angle is
    missing."""
    saved = np.load(os.path.join(out, "vectors", name + ".npz"))
    have = [int(angle) for angle in saved["reference_angles"]]
    missing = sorted(set(ref_angles) - set(have))
    if missing:
        raise SystemExit("%s: the saved vectors have no reference angle %s; run without "
                         "--reuse-vectors" % (name, missing[:10]))
    for key in KEYS:
        if not np.allclose(saved["query_%s_angles" % key], queries[key]):
            raise SystemExit("%s: the saved query angles of %s differ" % (name, key))
    return saved["reference"], {key: saved["query_%s" % key] for key in KEYS}, have


def run(args, sets):
    for name in ("vectors", "reference", "images"):
        os.makedirs(os.path.join(args.out, name), exist_ok=True)
    settings = embeddings.load_settings()
    loaded = {name: rs.load_entry(settings, name) for name in args.entries}
    conn = embeddings.open_database(settings.db_path)
    wines, sources = embeddings.read_inputs(conn, settings.db_path)
    conn.close()
    wine, digest = rs.pick_wine(wines, sources, loaded, args.slug)
    print("wine %s (%s), main image %s" % (wine["slug"], wine["name"], digest), flush=True)

    steps = rs.full_steps(loaded[args.entries[0]][0])
    bases, resize_step = rs.base_images(sources[digest], steps)
    scale = rs.scale_of(bases["white"].size, resize_step)
    colors = {"white": rs.BACKGROUNDS["white"], "black": rs.BACKGROUNDS["black"],
              "white_offset": rs.BACKGROUNDS["white"]}
    bases["white_offset"] = bases["white"]
    ref_angles = sorted({angle for item in sets for angle in item["angles"]})
    queries = query_sets(args.step, args.offset)
    pngs = []
    for angle in ([] if args.reuse_vectors else ref_angles):
        picture = rs.rotated(bases["white"], angle, colors["white"], scale)
        picture.save(os.path.join(args.out, "reference", "white_%03d.png" % angle))
        pngs.append(embeddings.png_bytes(picture))
    for key in ([] if args.reuse_vectors else KEYS):
        for angle in queries[key]:
            picture = rs.rotated(bases[key], angle, colors[key], scale)
            name = ("%s_%03d.png" % (key, angle) if key != "white_offset"
                    else "white_offset_%05.1f.png" % angle)
            picture.save(os.path.join(args.out, "images", name))
            pngs.append(embeddings.png_bytes(picture))
    if not args.reuse_vectors:
        print("%d reference and %d query images" % (len(ref_angles),
                                                     len(pngs) - len(ref_angles)), flush=True)

    rows = {item["name"]: [] for item in sets}
    for name, (embedding, directory, index, vectors) in loaded.items():
        stored = rs.normalise(vectors[rs.row_of(index, digest)["row"]])
        if args.reuse_vectors:
            reference, vectors_of, all_angles = saved_vectors(args.out, name, ref_angles,
                                                              queries)
        else:
            backend = build_embeddings.OpenAIBackend(embedding)
            got = rs.normalise(rotation_multiref.embed_all(backend, pngs, args.batch))
            reference = got[:len(ref_angles)]
            vectors_of, offset = {}, len(ref_angles)
            for key in KEYS:
                vectors_of[key] = got[offset:offset + len(queries[key])]
                offset += len(queries[key])
            all_angles = ref_angles
            np.savez(os.path.join(args.out, "vectors", name + ".npz"),
                     reference_angles=np.asarray(ref_angles),
                     reference=reference.astype(np.float32), stored=stored.astype(np.float32),
                     **{"query_%s_angles" % key: np.asarray(queries[key]) for key in KEYS},
                     **{"query_%s" % key: vectors_of[key].astype(np.float32) for key in KEYS})
        print("%s: the 0° reference vector against the indexed vector, cosine %.6f"
              % (name, reference[all_angles.index(0)] @ stored), flush=True)
        position = {angle: i for i, angle in enumerate(all_angles)}
        for item in sets:
            chosen = [position[angle] for angle in item["angles"]]
            subset = reference[chosen]
            folder = os.path.join(args.out, item["name"])
            os.makedirs(os.path.join(folder, "vectors"), exist_ok=True)
            np.savez(os.path.join(folder, "vectors", name + ".npz"),
                     reference_angles=np.asarray(item["angles"]),
                     reference=subset.astype(np.float32), stored=stored.astype(np.float32),
                     **{"query_%s_angles" % key: np.asarray(queries[key]) for key in KEYS},
                     **{"query_%s" % key: vectors_of[key].astype(np.float32) for key in KEYS})
            for key in KEYS:
                multi = vectors_of[key] @ subset.T
                single = vectors_of[key] @ stored
                for i, angle in enumerate(queries[key]):
                    rows[item["name"]].append({
                        "entry": name, "background": key, "angle": angle_label(angle),
                        "cosine_single": round(float(single[i]), 6),
                        "cosine_multi": round(float(multi[i].max()), 6),
                        "best_reference_angle": item["angles"][int(multi[i].argmax())]})
        print("%s: %d sets" % (name, len(sets)), flush=True)

    summary = []
    for item in sets:
        folder = os.path.join(args.out, item["name"])
        with open(os.path.join(folder, "results.csv"), "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[item["name"]][0]))
            writer.writeheader()
            writer.writerows(rows[item["name"]])
        meta = {"wine": {key: wine[key] for key in ("slug", "name", "producer", "category")},
                "main_sha256": digest, "set": {key: item[key] for key in
                                               ("start", "end", "step", "name")},
                "reference_angles": item["angles"], "reference_background": "white",
                "query_angles": queries["white"], "query_offset": args.offset,
                "scale": scale, "score": "the maximum cosine over the reference vectors",
                "vectors": "vectors/<entry>.npz: reference_angles, reference, stored, "
                           "query_<key>_angles, query_<key> for the keys white, black, "
                           "white_offset (all L2-normalised float32)",
                "entries": {name: loaded[name][0].base_url for name in args.entries}}
        with open(os.path.join(folder, "meta.json"), "w", encoding="utf-8") as fh:
            json.dump(meta, fh, ensure_ascii=False, indent=2)
        groups = collections.defaultdict(list)
        for row in rows[item["name"]]:
            groups[(row["entry"], row["background"])].append(row)
        for (entry, key), group in groups.items():
            scores = [row["cosine_multi"] for row in group]
            worst = min(group, key=lambda row: row["cosine_multi"])
            summary.append({"set": item["name"], "start": item["start"], "end": item["end"],
                            "step": item["step"], "count": len(item["angles"]),
                            "entry": entry, "background": key,
                            "mean_multi": round(float(np.mean(scores)), 6),
                            "min_multi": worst["cosine_multi"], "min_angle": worst["angle"],
                            "mean_single": round(float(np.mean(
                                [row["cosine_single"] for row in group])), 6)})
    # An earlier run of other sets keeps its rows and its place in the list of sets.
    names = [item["name"] for item in sets]
    summary_path = os.path.join(args.out, "summary.csv")
    if os.path.exists(summary_path):
        with open(summary_path, encoding="utf-8") as fh:
            summary = [row for row in csv.DictReader(fh) if row["set"] not in names] + summary
    with open(summary_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(summary[-1]))
        writer.writeheader()
        writer.writerows(summary)
    meta_path = os.path.join(args.out, "meta.json")
    earlier = []
    if os.path.exists(meta_path):
        with open(meta_path, encoding="utf-8") as fh:
            earlier = [name for name in json.load(fh)["sets"] if name not in names]
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump({"wine": {key: wine[key] for key in ("slug", "name", "producer", "category")},
                   "sets": earlier + names, "query_offset": args.offset,
                   "query_angles": queries["white"]}, fh, ensure_ascii=False, indent=2)
    print("wrote %s" % args.out, flush=True)


def read_set(folder):
    with open(os.path.join(folder, "meta.json"), encoding="utf-8") as fh:
        meta = json.load(fh)
    data = collections.defaultdict(lambda: collections.defaultdict(dict))
    with open(os.path.join(folder, "results.csv"), encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            angle = float(row["angle"])
            angle = int(angle) if angle.is_integer() else angle
            entry = row["entry"].replace(plots.PREFIX, "")
            data[entry][row["background"]][angle] = (float(row["cosine_multi"]), 1)
    return meta, data


def draw_set(out, folder, images):
    meta, data = read_set(folder)
    item = meta["set"]
    count = len(meta["reference_angles"])
    plots.SERIES_NAMES["white_offset"] = "белый фон, сдвиг запроса +%g°" % meta["query_offset"]
    plots.SERIES_GENITIVE["white_offset"] = ("белом фоне, сдвиг запроса +%g°"
                                             % meta["query_offset"])
    full = full_circle(item)
    band = None if full else (item["start"], item["end"])
    head = "опорные векторы %d°–%d°, шаг %d° (%d шт.)" % (item["start"], item["end"],
                                                          item["step"], count)
    text = ("Вино: «%s». Опорные векторы: белый фон, поворот %d°–%d°, шаг %d° (%d шт.). "
            "Сходство — максимум по ним." % (meta["wine"]["name"], item["start"], item["end"],
                                             item["step"], count))
    footer = " Белый фон без сдвига: при угле опорного вектора запрос = опорное изображение."
    ylabel = "максимум косинуса по %d опорным векторам" % count
    plots.chart_by_model(data, meta, folder, images["white"],
                         title="{family}: " + head, text=text, ylabel=ylabel,
                         rank=False, band=band, footer=footer, keys=KEYS)
    for key in KEYS:
        plots.chart_models(data, meta, folder, key, images["black" if key == "black" else "white"],
                           title="{family}: " + head + ", бутылка на {background}", text=text,
                           ylabel=ylabel, band=band, footer=footer if key == "white" else "")


def read_summary(out):
    with open(os.path.join(out, "summary.csv"), encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def full_circle(item):
    """True for a set that covers the circle: it starts at 0° and its next angle is 360°."""
    return int(item["start"]) == 0 and int(item["end"]) + int(item["step"]) >= 360


def entries_in(rows):
    return plots.entries_of({row["entry"].replace(plots.PREFIX, "") for row in rows})


def panels(entries):
    """One panel for each entry, at most 3 in a row. Return (figure, axes, height)."""
    fig, axes, height = plots.grid(len(entries), row_in=2.92, top_in=1.36, bottom_in=0.8)
    for ax, entry in zip(axes.flat, entries):
        ax.set_facecolor(plots.SURFACE)
        ax.grid(True, color=plots.GRID, lw=0.8)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(plots.GRID)
        ax.tick_params(colors=plots.INK2)
        ax.set_title(plots.TITLES.get(entry, entry), loc="left", fontsize=11, color=plots.INK)
    return fig, axes, height


def finish(fig, axes, height, title, text, footer, path, ncol=3):
    handles, labels = [], []
    for ax in axes.flat:
        for handle, label in zip(*ax.get_legend_handles_labels()):
            if label not in labels:
                handles.append(handle)
                labels.append(label)
    top = lambda inches: 1 - inches / height  # noqa: E731
    fig.legend(handles, labels, loc="upper left", ncol=ncol, frameon=False,
               bbox_to_anchor=(0.01, top(0.52)), fontsize=9)
    fig.suptitle(title, x=0.01, y=top(0.08), ha="left", fontsize=13, color=plots.INK)
    fig.text(0.01, top(0.4), text, fontsize=9.5, color=plots.INK2)
    fig.text(0.01, 0.08 / height, footer, fontsize=9, color=plots.INK2)
    fig.subplots_adjust(left=0.06, right=0.985, top=top(1.36), bottom=0.8 / height,
                        hspace=0.35, wspace=0.08)
    fig.savefig(path, dpi=plots.DPI, facecolor=plots.SURFACE)
    plots.plt.close(fig)


def draw_full_circle(out):
    """For each entry: the mean and the minimum score of the full-circle sets by step."""
    rows = [row for row in read_summary(out) if full_circle(row)]
    steps = sorted({int(row["step"]) for row in rows})
    if len(steps) < 2:
        return
    with open(os.path.join(out, "meta.json"), encoding="utf-8") as fh:
        meta = json.load(fh)
    entries = entries_in(rows)
    fig, axes, height = panels(entries)
    for ax, entry in zip(axes.flat, entries):
        for key in ("black", "white_offset"):
            chosen = sorted((int(row["step"]), row) for row in rows
                            if row["entry"].replace(plots.PREFIX, "") == entry
                            and row["background"] == key)
            for metric, dash, name in (("mean", "solid", "среднее"), ("min", (0, (5, 3)),
                                                                        "минимум")):
                ax.plot([step for step, _ in chosen],
                        [float(row["%s_multi" % metric]) for _, row in chosen],
                        color=plots.SERIES_COLORS[key], lw=2, ls=dash, marker="o", ms=5,
                        label="%s: %s" % (plots.SERIES_NAMES[key], name))
        ax.set_xticks(steps)
        ax.xaxis.set_major_formatter(lambda value, _: "%d°" % value)
    for ax in axes[-1]:
        ax.set_xlabel("шаг опорных векторов (полный круг)", color=plots.INK2)
    for ax in axes[:, 0]:
        ax.set_ylabel("косинус по углам запроса", color=plots.INK2)
    counts = {int(row["step"]): int(row["count"]) for row in rows}
    finish(fig, axes, height, "%s: опорные векторы на полном круге, влияние шага"
           % plots.family(entries),
           "Вино: «%s». Запрос: 0°–355°, шаг 5° (чёрный фон) и 2.5°–357.5° (белый фон, сдвиг "
           "+%g°). Опорные векторы: белый фон." % (meta["wine"]["name"], meta["query_offset"]),
           "Число опорных векторов: %s. Расстояние от запроса до ближайшего опорного угла "
           "зависит от шага неравномерно, см. график допуска." % ", ".join(
               "%d° — %d" % (step, counts[step]) for step in steps),
           os.path.join(out, "chart-full-circle-steps.png"), ncol=2)


def nearest(angle, step):
    rest = angle % step
    return min(rest, step - rest)


def draw_tolerance(out):
    """The score by the distance from the query to the nearest reference angle. The data
    are the queries of all full-circle sets."""
    with open(os.path.join(out, "meta.json"), encoding="utf-8") as fh:
        meta = json.load(fh)
    groups = collections.defaultdict(list)
    steps = set()
    for name in meta["sets"]:
        folder = os.path.join(out, name)
        with open(os.path.join(folder, "meta.json"), encoding="utf-8") as fh:
            item = json.load(fh)["set"]
        if not full_circle(item):
            continue
        steps.add(item["step"])
        with open(os.path.join(folder, "results.csv"), encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                side = "black" if row["background"] == "black" else "white"
                distance = nearest(float(row["angle"]), item["step"])
                groups[(row["entry"].replace(plots.PREFIX, ""), side, distance)].append(
                    float(row["cosine_multi"]))
    table = [{"entry": entry, "background": side, "distance": distance,
              "count": len(scores), "mean": round(float(np.mean(scores)), 6),
              "min": round(float(np.min(scores)), 6)}
             for (entry, side, distance), scores in sorted(groups.items())]
    with open(os.path.join(out, "tolerance.csv"), "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(table[0]))
        writer.writeheader()
        writer.writerows(table)
    plt = plots.plt
    entries = plots.entries_of({row["entry"] for row in table})
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.4), sharey=True, facecolor=plots.SURFACE)
    for ax, side, name in ((axes[0], "white", "белый фон (запросы без сдвига и со сдвигом)"),
                           (axes[1], "black", "чёрный фон")):
        plots.style(ax)
        for entry in entries:
            points = sorted((row["distance"], row["mean"]) for row in table
                            if row["entry"] == entry and row["background"] == side)
            ax.plot(*zip(*points), color=plots.model_color(entry, entries), lw=2, marker="o",
                    ms=4, label=plots.TITLES.get(entry, entry))
        top = max(row["distance"] for row in table)
        ax.set_xlim(-0.2, top + 0.2)
        ax.set_xticks(np.arange(0, top + 0.5, 0.5))
        ax.xaxis.set_major_formatter(lambda value, _: "%g°" % value)
        ax.set_title(name, loc="left", fontsize=11, color=plots.INK)
        ax.set_xlabel("расстояние от угла запроса до ближайшего опорного угла", color=plots.INK2)
    axes[0].set_ylabel("среднее максимума косинуса", color=plots.INK2)
    axes[0].legend(loc="lower left", ncol=2, frameon=False, fontsize=9)
    steps = sorted(steps)
    fig.suptitle("%s: допуск по углу — сходство и расстояние до ближайшего опорного "
                 "вектора" % plots.family(entries), x=0.01, y=0.985, ha="left", fontsize=13, color=plots.INK)
    fig.text(0.01, 0.93, "Вино: «%s». Данные всех наборов на полном круге (шаг %s°). Опорные "
             "векторы: белый фон." % (meta["wine"]["name"], ", ".join(map(str, steps))),
             fontsize=9.5, color=plots.INK2)
    fig.text(0.01, 0.015, "0° на белом фоне: запрос = опорное изображение (1.000). Число "
             "запросов в каждой точке — в tolerance.csv.", fontsize=9, color=plots.INK2)
    fig.subplots_adjust(left=0.06, right=0.985, top=0.85, bottom=0.14, wspace=0.06)
    fig.savefig(os.path.join(out, "chart-tolerance.png"), dpi=plots.DPI,
                facecolor=plots.SURFACE)
    plt.close(fig)


def draw_summary(out):
    """For each entry: the mean (or the minimum) score of each set, by range and step.
    The chart holds the sets of the steps 1° and 5° over 0°–45°, 0°–90°, and the circle."""
    rows = [row for row in read_summary(out)
            if int(row["step"]) in (1, 5) and (int(row["end"]) in (45, 90) or full_circle(row))]
    with open(os.path.join(out, "meta.json"), encoding="utf-8") as fh:
        meta = json.load(fh)
    plt = plots.plt
    names = {45: "0°–45°", 90: "0°–90°", 355: "0°–360°", 359: "0°–360°"}
    x_of = {45: 0, 90: 1, 355: 2, 359: 2}
    for metric, label in (("mean", "среднее по углам запроса"), ("min", "минимум по углам запроса")):
        entries = entries_in(rows)
        fig, axes, height = panels(entries)
        values = []
        for ax, entry in zip(axes.flat, entries):
            for key in ("black", "white_offset"):
                baseline = None
                for step, dash in ((5, (0, (5, 3))), (1, "solid")):
                    points = sorted((x_of[int(row["end"])], float(row["%s_multi" % metric]))
                                    for row in rows
                                    if row["entry"].replace(plots.PREFIX, "") == entry
                                    and row["background"] == key and int(row["step"]) == step)
                    if not points:
                        continue
                    values.extend(value for _, value in points)
                    ax.plot(*zip(*points), color=plots.SERIES_COLORS[key], lw=2, ls=dash,
                            marker="o", ms=6, label="%s, шаг %d°"
                            % (plots.SERIES_NAMES[key], step))
                    if baseline is None and metric == "mean":
                        baseline = next(float(row["mean_single"]) for row in rows
                                        if row["entry"].replace(plots.PREFIX, "") == entry
                                        and row["background"] == key)
                if baseline is not None:
                    ax.axhline(baseline, color=plots.SERIES_COLORS[key], lw=1, ls=":",
                               label="%s: 1 вектор индекса" % plots.SERIES_NAMES[key])
                    values.append(baseline)
            ax.set_xticks([0, 1, 2])
            ax.set_xticklabels([names[45], names[90], names[355]])
            ax.set_xlim(-0.3, 2.3)
        low = min(values)
        for ax in axes.flat:
            ax.set_ylim(np.floor(low * 50) / 50 - 0.01, 1.0)
        for ax in axes[-1]:
            ax.set_xlabel("диапазон углов опорных векторов", color=plots.INK2)
        for ax in axes[:, 0]:
            ax.set_ylabel("косинус, %s" % label, color=plots.INK2)
        counts = {}
        for row in rows:
            counts[(int(row["step"]), x_of[int(row["end"])])] = int(row["count"])
        finish(fig, axes, height, "%s: наборы опорных векторов, %s" % (plots.family(entries),
                                                                        label),
               "Вино: «%s». Запрос: 0°–355°, шаг 5° (чёрный фон) и 2.5°–357.5° (белый фон, "
               "сдвиг +%g°). Опорные векторы: белый фон." % (meta["wine"]["name"],
                                                            meta["query_offset"]),
               "Число опорных векторов: шаг 5° — %s; шаг 1° — %s (для 0°–45°, 0°–90°, "
               "0°–360°)." % tuple(" / ".join(str(counts[(step, x)]) for x in range(3)
                                              if (step, x) in counts) for step in (5, 1)),
               os.path.join(out, "chart-summary-%s.png" % metric))


def draw(out):
    plots.plt.rcParams.update({"font.size": 9.5, "text.color": plots.INK,
                               "axes.labelcolor": plots.INK2})
    with open(os.path.join(out, "meta.json"), encoding="utf-8") as fh:
        meta = json.load(fh)
    images = {key: plots.load_images(os.path.join(out), key, meta["query_angles"])
              for key in ("white", "black")}
    for name in meta["sets"]:
        draw_set(out, os.path.join(out, name), images)
    draw_summary(out)
    draw_full_circle(out)
    draw_tolerance(out)
    print("wrote the charts to %s" % out)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", required=True, help="the output directory")
    parser.add_argument("--sets", nargs="*", default=list(SETS), help="start:end:step")
    parser.add_argument("--slug", help="the wine; default: the first wine that fits")
    parser.add_argument("--step", type=int, default=5, help="the query angle step")
    parser.add_argument("--offset", type=float, default=2.5,
                        help="the angle offset of the extra white queries")
    parser.add_argument("--batch", type=int, default=8, help="images per request")
    parser.add_argument("--entries", nargs="*", default=list(rs.ENTRIES))
    parser.add_argument("--reuse-vectors", action="store_true",
                        help="take the vectors from <out>/vectors/ of an earlier run; send "
                             "no request")
    parser.add_argument("--plots-only", action="store_true",
                        help="draw the charts from an earlier run; send no request")
    args = parser.parse_args(argv)
    if not args.plots_only:
        run(args, [parse_set(text) for text in args.sets])
    draw(args.out)


if __name__ == "__main__":
    main()
