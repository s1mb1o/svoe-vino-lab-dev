#!/usr/bin/env python3
"""Compare the turntable photos with 360° renders of the reconstructed bottle.

Owner message of about 2026-10-01T08:30:00+0300. `tools/bottle_rotation/reconstruction`
rebuilds the bottle of `winemaker-selection` from three FRAP photos of the 2020 edition
as a textured surface of revolution, and renders any yaw. The script renders the yaws 0°
to 355° in steps of `--yaw-step` with the camera of `render_showcase.py` (orthographic,
elevation 5°, synthetic studio shading). Yaw 0° shows the front, 180° the back. Each
render is a transparent PNG, so it gets the processing of a transparent catalogue image:
the alpha crop of `derive.derive_image` and the steps of the view `full`.

The photo vectors, the cosine to the catalogue cut, and the maximum over the copies of
`rotate_bottle.py` come from the output folder of `zrotation_similarity.py`
(`--photos-from`). For each photo and entry, the script writes the best render and its
yaw, and the rank of the wine when its vectors also hold the renders. That rank is
optimistic: the other wines keep their index vectors. A control measures the same gain
for the catalogue images of the other wines: the maximum cosine over the renders minus
the cosine to the catalogue cut.

The script is read-only for the catalogue, the indexes, and the reconstruction. It sends
the renders to the `base_url` of each entry and writes into `--out` alone. With
`--plots-only`, it draws the charts again with no request.

    python3 scripts/zrotation_reconstruction.py \\
        --photos-from docs/reports/zrotation-similarity-2026-10-01 \\
        --out docs/reports/zrotation-reconstruction-2026-10-01
"""

import argparse
import concurrent.futures
import csv
import io
import json
import os
import sys

import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Patch
from PIL import Image, ImageDraw, ImageFont

import zrotation_similarity as single  # also puts pipeline/ on sys.path
import build_embeddings  # noqa: E402
import embedding_run  # noqa: E402
import embeddings  # noqa: E402

LAB = os.path.dirname(single.WORKBENCH)
sys.path.insert(0, os.path.join(LAB, "tools", "bottle_rotation", "reconstruction"))
import render360  # noqa: E402

plots, plt = single.plots, single.plt
MODEL_DIR = os.path.join(LAB, "output", "bottle-reconstruction", "winemaker-selection", "model")
# The camera of `render_showcase.py`, with 2x supersampling.
CAMERA = {"elevation": 5.0, "orthographic": True, "ortho_height": 1.12, "target_height": 0.5,
          "shading": True, "antialias": 2, "size": (400, 1100)}
WINE = "winemaker-selection"
RENDER = plots.PALETTE[2]  # slot 3 of the palette, next to SINGLE and ZMAX
# The sequential ramp (blue) of the dataviz palette, light to dark.
RAMP = LinearSegmentedColormap.from_list("blue", ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab",
                                                  "#0d366b"])
_worker = {}


def render_input(yaw):
    """Return (yaw, PNG of the model input) of one render. Runs in a worker process."""
    if not _worker:
        with open(os.path.join(MODEL_DIR, "profile.json"), encoding="utf-8") as fh:
            profile = json.load(fh)["profile"]
        _worker["renderer"] = render360.BottleRenderer(
            profile, os.path.join(MODEL_DIR, "atlas.png"),
            os.path.join(MODEL_DIR, "material-mask.png"))
        _worker["steps"] = single.full_steps(
            embeddings.load_settings().find(single.ENTRIES[0]))
    image = _worker["renderer"].render(yaw=yaw, **CAMERA)
    steps = _worker["steps"]
    cuts = embedding_run.cuts_of(image, {"package"}, None)
    prepared, reason = embedding_run.view_input(image, steps, cuts)
    if prepared is None:
        raise SystemExit("yaw %s: %s" % (yaw, reason))
    return yaw, embeddings.png_bytes(prepared)


def wine_scores(items):
    """Return {wine: best cosine} of one photo over the `full` items (slug, cosine)."""
    best = {}
    for slug, score in items:
        if score > best.get(slug, -2.0):
            best[slug] = score
    return best


def rank_of(best, own):
    return 1 + sum(score > own for slug, score in best.items() if slug != WINE)


def compute(args):
    os.makedirs(os.path.join(args.out, "images"), exist_ok=True)
    os.makedirs(os.path.join(args.out, "vectors"), exist_ok=True)
    yaws = list(range(0, 360, args.yaw_step))
    with concurrent.futures.ProcessPoolExecutor(args.render_workers) as pool:
        rendered = dict(pool.map(render_input, yaws))
    images = [Image.open(io.BytesIO(rendered[yaw])).convert("RGB") for yaw in yaws]
    for yaw, image in zip(yaws, images):
        image.save(os.path.join(args.out, "images", "yaw_%03d.png" % yaw))
    print("rendered %d yaws, model input %s" % (len(yaws), images[0].size), flush=True)

    with open(os.path.join(args.photos_from, "results.csv"), encoding="utf-8") as fh:
        earlier = {(row["entry"], int(row["photo"])): row for row in csv.DictReader(fh)}
    settings = embeddings.load_settings()
    conn = embeddings.open_database(settings.db_path)
    wines, sources = embeddings.read_inputs(conn, settings.db_path)
    conn.close()
    sha_to_slug = {}
    for wine in wines:
        for _, sha in wine["columns"]:
            if sources.get(sha, {}).get("role") == "full":
                sha_to_slug.setdefault(sha, wine["slug"])
    rows, controls = [], []
    for name in args.entries:
        embedding, directory, index, vectors = single.load_entry(settings, name)
        backend = build_embeddings.OpenAIBackend(embedding)
        renders = single.embed_all(backend, images, args.batch)
        saved = np.load(os.path.join(args.photos_from, "vectors", "%s.npz" % name))
        photos, cut = saved["photos"], saved["stored"]
        np.savez(os.path.join(args.out, "vectors", "%s.npz" % name), yaws=yaws,
                 renders=renders.astype(np.float32), photos=photos, stored=cut)
        slugs, item_rows = single.wine_rows(index, sha_to_slug)
        catalogue = single.normalise(vectors[item_rows])
        for number, vector in enumerate(photos, 1):
            scores = renders @ vector
            top = int(np.argmax(scores))
            best = wine_scores(zip(slugs, catalogue @ vector))
            own = best.get(WINE, -2.0)
            row = earlier[(name, number)]
            rows.append({"entry": name, "photo": number, "cosine": row["cosine"],
                         "zmax_cosine": row["zmax_cosine"],
                         "render_cosine": round(float(scores[top]), 6),
                         "render_yaw": yaws[top],
                         "render_front_cosine": round(float(scores[0]), 6),
                         "rank": rank_of(best, own),
                         "rank_with_renders": rank_of(best, max(own, float(scores[top]))),
                         "best_other_cosine": row["best_other_cosine"],
                         "best_other_slug": row["best_other_slug"]})
        # The control: the gain of the renders for the catalogue images of the other wines.
        others = catalogue[np.asarray(slugs) != WINE]
        gain = (others @ renders.T).max(axis=1) - others @ cut
        controls.append({"entry": name, "images": len(others),
                         "mean_gain": round(float(gain.mean()), 4),
                         "p95_gain": round(float(np.percentile(gain, 95)), 4),
                         "max_gain": round(float(gain.max()), 4)})
        print("%s: %d renders, control %s" % (name, len(yaws), controls[-1]), flush=True)
    for file_name, table in (("results.csv", rows), ("control.csv", controls)):
        with open(os.path.join(args.out, file_name), "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(table[0]))
            writer.writeheader()
            writer.writerows(table)
    with open(os.path.join(args.photos_from, "meta.json"), encoding="utf-8") as fh:
        meta = json.load(fh)
    meta.update({"yaws": yaws, "camera": dict(CAMERA, size=list(CAMERA["size"])),
                 "model_dir": os.path.relpath(MODEL_DIR, LAB),
                 "photos_from": os.path.relpath(os.path.abspath(args.photos_from),
                                                single.WORKBENCH)})
    with open(os.path.join(args.out, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)


# --- the charts (Russian text, as the charts of `zrotation_similarity.py`) ----------------

def read_rows(directory):
    return single.read_rows(directory)


def chart_heatmap(meta, directory):
    """One panel for each entry: the cosine of each photo (x) to each render (y). A dot
    marks the best render of each photo."""
    entries = plots.entries_of([name.replace(plots.PREFIX, "") for name in single.ENTRIES])
    matrices = {}
    for entry in entries:
        saved = np.load(os.path.join(directory, "vectors", "%s%s.npz" % (plots.PREFIX, entry)))
        matrices[entry] = saved["renders"] @ saved["photos"].T  # yaws x photos
    yaws = meta["yaws"]
    values = np.concatenate([m.ravel() for m in matrices.values()])
    low, high = np.percentile(values, 2), values.max()
    fig, axes, height = plots.grid(len(entries), row_in=3.4, top_in=1.25, bottom_in=0.75)
    step = yaws[1] - yaws[0]
    for ax, entry in zip(axes.flat, entries):
        matrix = matrices[entry]
        shown = ax.imshow(matrix, aspect="auto", origin="lower", cmap=RAMP, vmin=low, vmax=high,
                          extent=(0.5, matrix.shape[1] + 0.5, -step / 2, 360 - step / 2))
        best = matrix.argmax(axis=0)
        ax.scatter(np.arange(1, matrix.shape[1] + 1), [yaws[i] for i in best], s=14,
                   color=plots.SURFACE, edgecolors=plots.INK, linewidths=0.8, zorder=3)
        ax.set_yticks(range(0, 361, 90))
        ax.yaxis.set_major_formatter(lambda value, _: "%d°" % value)
        ax.set_xticks(range(1, matrix.shape[1] + 1, 4))
        ax.tick_params(colors=plots.INK2, labelsize=8)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.set_title(plots.TITLES.get(entry, entry), loc="left", fontsize=11, color=plots.INK)
    for ax in axes[:, 0]:
        ax.set_ylabel("угол рендера (0° — лицевая сторона)", color=plots.INK2)
    for ax in axes[-1, :]:
        ax.set_xlabel("номер снимка", color=plots.INK2)
    top = lambda inches: 1 - inches / height  # noqa: E731
    fig.suptitle("%s: косинус каждого снимка к каждому рендеру реконструкции"
                 % plots.family(entries), x=0.01, y=top(0.086), ha="left", fontsize=13,
                 color=plots.INK)
    fig.text(0.01, top(0.36), "Реконструкция tools/bottle_rotation/reconstruction (издание "
             "2020) с шагом %d°. Точка — лучший рендер для снимка. Тёмнее — выше косинус."
             % step, fontsize=9.5, color=plots.INK2, va="top")
    fig.subplots_adjust(left=0.07, right=0.9, top=top(1.25), bottom=0.75 / height,
                        hspace=0.45, wspace=0.12)
    bar = fig.colorbar(shown, ax=axes.ravel().tolist(), fraction=0.02, pad=0.02)
    bar.ax.tick_params(colors=plots.INK2, labelsize=8)
    bar.set_label("косинус", color=plots.INK2)
    fig.savefig(os.path.join(directory, "chart-heatmap.png"), dpi=plots.DPI,
                facecolor=plots.SURFACE)
    plt.close(fig)


def chart_by_model(data, meta, directory, photos, step=4):
    """One panel for each entry: the cosine to the catalogue cut, the maximum over the
    ±30° copies, the maximum over the 360° renders, and the best other wine."""
    entries = plots.entries_of(data)
    numbers = sorted(photos)
    ticks = numbers[::step]
    fig, axes, height = plots.grid(len(entries), row_in=3.225, top_in=1.5, bottom_in=1.15)
    values = [float(data[e][n][key]) for e in entries for n in numbers
              for key in ("cosine", "zmax_cosine", "render_cosine", "best_other_cosine")]
    low, high = single.limits(values)
    thumbs = plots.thumbnails({n: photos[n] for n in ticks}, round(0.5 * plots.DPI))
    lines = (("best_other_cosine", single.OTHER, 1.2, "лучшее другое вино индекса"),
             ("cosine", single.SINGLE, 2, "вырез каталога (один вектор)"),
             ("zmax_cosine", single.ZMAX, 2, "максимум по копиям ±30° (rotate_bottle)"),
             ("render_cosine", RENDER, 2, "максимум по рендерам 360° (реконструкция)"))
    for ax, entry in zip(axes.flat, entries):
        single.style(ax, numbers, ticks)
        rows = data[entry]
        for key, color, width, label in lines:
            ax.plot(numbers, single.column(rows, numbers, key), color=color, lw=width,
                    label=label)
        ax.set_title(plots.TITLES.get(entry, entry), loc="left", fontsize=11, color=plots.INK)
        ax.set_ylim(low, high)
        plots.add_thumbnails(ax, thumbs, 0.5)
    for ax in axes[:, 0]:
        ax.set_ylabel("косинусное сходство", color=plots.INK2)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    top = lambda inches: 1 - inches / height  # noqa: E731
    fig.legend(handles[::-1], labels[::-1], loc="upper left", ncol=4, frameon=False,
               bbox_to_anchor=(0.01, top(0.8)), fontsize=9.5)
    fig.suptitle("%s: снимки против рендеров реконструкции 360°" % plots.family(entries),
                 x=0.01, y=top(0.086), ha="left", fontsize=13, color=plots.INK)
    fig.text(0.01, top(0.36), "Для каждого снимка — наибольший косинус по %d рендерам "
             "(0°…355°). Реконструкция — издание 2020 (золотая полоса), снимки — 2025 "
             "(зелёная полоса), вырез каталога — 2019." % len(meta["yaws"]), fontsize=9.5,
             color=plots.INK2, va="top")
    fig.text(0.01, 0.086 / height, "Под осью: вход модели для снимков %s."
             % ", ".join(str(n) for n in ticks), fontsize=9, color=plots.INK2)
    fig.subplots_adjust(left=0.06, right=0.985, top=top(1.5), bottom=1.15 / height,
                        hspace=0.55, wspace=0.12)
    fig.savefig(os.path.join(directory, "chart-by-model.png"), dpi=plots.DPI,
                facecolor=plots.SURFACE)
    plt.close(fig)


def chart_gain(data, controls, directory, photos, step=4):
    """One panel for each entry: the gain of the renders for each photo (the maximum over
    the renders minus the cosine to the catalogue cut, at least 0). A grey band marks a
    photo with rank 1 already; an orange bar marks a photo that gets rank 1 only with the
    renders (optimistic). A thin ink line marks the 95th percentile of the same gain for
    the catalogue images of the other wines (the control)."""
    entries = plots.entries_of(data)
    numbers = sorted(photos)
    ticks = numbers[::step]
    gains = {e: [max(0.0, float(data[e][n]["render_cosine"]) - float(data[e][n]["cosine"]))
                 for n in numbers] for e in entries}
    high = max(0.05, np.ceil(max(max(values) for values in gains.values()) * 20) / 20)
    fig, axes, height = plots.grid(len(entries), row_in=2.9, top_in=1.35, bottom_in=1.15)
    thumbs = plots.thumbnails({n: photos[n] for n in ticks}, round(0.5 * plots.DPI))
    for ax, entry in zip(axes.flat, entries):
        single.style(ax, numbers, ticks)
        rows = data[entry]
        for n in numbers:
            if int(rows[n]["rank"]) == 1:
                ax.axvspan(n - 0.5, n + 0.5, color=plots.BAND_COLOR, lw=0, zorder=0)
        new = [n for n in numbers if int(rows[n]["rank"]) > 1
               and int(rows[n]["rank_with_renders"]) == 1]
        ax.bar(numbers, gains[entry], width=0.62, zorder=2,
               color=[single.ZMAX if n in new else RENDER for n in numbers])
        control = controls[plots.PREFIX + entry]
        ax.axhline(control["p95_gain"], color=plots.INK, lw=0.9, zorder=3)
        ax.set_ylim(0, high)
        ax.yaxis.set_major_formatter(lambda value, _: "%+.2f" % value if value else "0")
        ax.set_title(plots.TITLES.get(entry, entry), loc="left", fontsize=11, color=plots.INK)
        ax.set_title("ср. %+.3f · новых первых: %d" % (float(np.mean(gains[entry])), len(new)),
                     loc="right", fontsize=9, color=plots.INK2)
        plots.add_thumbnails(ax, thumbs, 0.5)
    for ax in axes[:, 0]:
        ax.set_ylabel("прирост косинуса", color=plots.INK2)
    handles = [Patch(color=RENDER, label="прирост: максимум по рендерам − вырез каталога"),
               Patch(color=single.ZMAX, label="с рендерами вино становится первым (оптимистично)"),
               Patch(color=plots.BAND_COLOR, label="вино первое уже с вырезом"),
               single.Line2D([], [], color=plots.INK, lw=0.9,
                          label="95-й перцентиль прироста у других вин (контроль)")]
    top = lambda inches: 1 - inches / height  # noqa: E731
    fig.legend(handles=handles, loc="upper left", ncol=2, frameon=False,
               bbox_to_anchor=(0.01, top(0.62)), fontsize=9.5)
    fig.suptitle("%s: что дают рендеры реконструкции 360°" % plots.family(entries), x=0.01,
                 y=top(0.086), ha="left", fontsize=13, color=plots.INK)
    fig.text(0.01, top(0.36), "Контроль: тот же прирост для изображений каталога других вин. "
             "Прирост выше линии — больше, чем у 95 % чужих изображений.", fontsize=9.5,
             color=plots.INK2, va="top")
    fig.text(0.01, 0.086 / height, "Под осью: вход модели для снимков %s."
             % ", ".join(str(n) for n in ticks), fontsize=9, color=plots.INK2)
    fig.subplots_adjust(left=0.06, right=0.985, top=top(1.35), bottom=1.15 / height,
                        hspace=0.55, wspace=0.12)
    fig.savefig(os.path.join(directory, "chart-gain.png"), dpi=plots.DPI,
                facecolor=plots.SURFACE)
    plt.close(fig)


def draw(directory):
    data = read_rows(directory)
    with open(os.path.join(directory, "meta.json"), encoding="utf-8") as fh:
        meta = json.load(fh)
    with open(os.path.join(directory, "control.csv"), encoding="utf-8") as fh:
        controls = {row["entry"]: {key: float(value) for key, value in row.items()
                                   if key != "entry"} for row in csv.DictReader(fh)}
    plt.rcParams.update({"font.size": 9.5, "text.color": plots.INK,
                         "axes.labelcolor": plots.INK2})
    source = os.path.join(single.WORKBENCH, meta["photos_from"], "images")
    photos = {item["number"]: Image.open(os.path.join(
        source, "photo_%02d.png" % item["number"])).convert("RGB") for item in meta["photos"]}
    chart_heatmap(meta, directory)
    chart_by_model(data, meta, directory, photos)
    chart_gain(data, controls, directory, photos)
    renders = [("%d°" % yaw, Image.open(os.path.join(directory, "images", "yaw_%03d.png"
                                                    % yaw)).convert("RGB"))
               for yaw in meta["yaws"]]
    single.collage(os.path.join(directory, "collage-renders.png"), renders,
                   "Рендеры реконструкции: вход модели (альфа-обрезка, белый фон)",
                   "0° — лицевая сторона, 180° — задняя. Издание 2020. Общий масштаб, чёрная "
                   "рамка — граница входа модели.", columns=18, cell_h=300)
    print("wrote the charts to %s" % directory)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", required=True, help="the output directory")
    parser.add_argument("--photos-from", help="the output folder of zrotation_similarity.py")
    parser.add_argument("--yaw-step", type=int, default=5)
    parser.add_argument("--batch", type=int, default=8, help="images per request")
    parser.add_argument("--render-workers", type=int, default=8)
    parser.add_argument("--entries", nargs="*", default=list(single.ENTRIES))
    parser.add_argument("--plots-only", action="store_true")
    args = parser.parse_args(argv)
    if not args.plots_only:
        if not args.photos_from:
            parser.error("--photos-from is required without --plots-only")
        compute(args)
    draw(args.out)


if __name__ == "__main__":
    main()
