#!/usr/bin/env python3
"""Draw the charts and the collages of `scripts/rotation_similarity.py`, in Russian.

Owner message of 2026-09-29T01:23:58+0300. The script reads `results.csv`, `meta.json`,
and `images/` of an output directory of `rotation_similarity.py` and writes into it:

- `chart-by-model.png`: one panel for each entry, the white and the black background, with
  bottle thumbnails under the angle axis.
- `chart-models-white.png`, `chart-models-black.png`: the six entries in one panel for
  each background, with bottle thumbnails.
- `collage-white.png`, `collage-black.png`: each rotation step at one common scale. A black
  frame shows the border of each image.

    python3 scripts/rotation_similarity_plots.py docs/reports/rotation-similarity-2026-09-29
"""

import collections
import csv
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.offsetbox import AnnotationBbox, OffsetImage  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

PREFIX = "gx10-siglip2-so400m-patch16-"
# The entries in chart order. A name without PREFIX stays as it is (the DINOv3 entries).
ORDER = ["naflex-p256", "naflex-p512", "naflex-p1024", "256", "384", "512",
         "gx10-dinov3-vitb16", "gx10-dinov3-vitl16"]
TITLES = {"naflex-p256": "NaFlex p256", "naflex-p512": "NaFlex p512",
          "naflex-p1024": "NaFlex p1024", "256": "фиксированный 256",
          "384": "фиксированный 384", "512": "фиксированный 512",
          "gx10-dinov3-vitb16": "DINOv3 ViT-B/16", "gx10-dinov3-vitl16": "DINOv3 ViT-L/16"}
BG_NAMES = {"white": "белый фон", "black": "чёрный фон"}
BG_GENITIVE = {"white": "белом фоне", "black": "чёрном фоне"}

# The reference palette of the dataviz skill, light mode, slots in fixed order.
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BG_COLORS = {"white": "#2a78d6", "black": "#eb6834"}
# The series of the charts: the backgrounds and, for `rotation_refsets.py`, the white
# queries with an angle offset. Slot 3 of the palette (all-pairs valid with slots 1-2).
SERIES_NAMES = dict(BG_NAMES, white_offset="белый фон, сдвиг запроса")
SERIES_GENITIVE = dict(BG_GENITIVE, white_offset="белом фоне, сдвиг запроса")
SERIES_COLORS = dict(BG_COLORS, white_offset="#1baf7a")
# The categorical slots 1 to 6. A chart gives the slots to its entries in chart order.
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
FONT = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf",
                    "DejaVuSans.ttf")
DPI = 130


def entries_of(names):
    """Return the entry names in chart order: the known names first, then the others."""
    names = set(names)
    return [name for name in ORDER if name in names] + sorted(names - set(ORDER))


def model_color(entry, entries):
    return PALETTE[entries.index(entry) % len(PALETTE)]


def family(entries):
    """The model family for a title."""
    if entries and all("dinov3" in entry for entry in entries):
        return "DINOv3"
    return "SigLIP2 so400m"


def low_limit(values, default=0.68):
    """The lower limit of the cosine axis: `default`, or lower when a value is lower."""
    return min(default, np.floor((min(values) - 0.02) * 20) / 20)


def grid(count, row_in, top_in, bottom_in, width=13):
    """Return (figure, axes as a 2-D array, height in inches) for `count` panels, at most
    3 in a row. The margins are in inches, so a figure with one row keeps the room of the
    title, the subtitle, and the legend. Panels that are not used are hidden."""
    columns = min(3, count)
    rows = -(-count // columns)
    height = top_in + bottom_in + row_in * rows
    fig, axes = plt.subplots(rows, columns, figsize=(width, height), sharey=True,
                             squeeze=False, facecolor=SURFACE)
    for ax in axes.flat[count:]:
        ax.set_visible(False)
    return fig, axes, height


def read_results(directory):
    data = collections.defaultdict(lambda: collections.defaultdict(dict))
    with open(os.path.join(directory, "results.csv"), encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            entry = row["entry"].replace(PREFIX, "")
            data[entry][row["background"]][int(row["angle"])] = (float(row["cosine"]),
                                                                  int(row["rank"]))
    return data


def framed(image, width=1):
    """Return the image with a black frame of `width` pixels around it."""
    out = Image.new("RGB", (image.width + 2 * width, image.height + 2 * width), (0, 0, 0))
    out.paste(image, (width, width))
    return out


def load_images(directory, background, angles):
    return {angle: Image.open(os.path.join(directory, "images", "%s_%03d.png"
                                           % (background, angle))).convert("RGB")
            for angle in angles}


def thumbnails(images, height_px):
    """Scale every image with one common factor: the largest side becomes `height_px`."""
    largest = max(max(image.size) for image in images.values())
    scale = height_px / largest
    return {angle: framed(image.resize((max(1, round(image.width * scale)),
                                        max(1, round(image.height * scale))),
                                       Image.Resampling.LANCZOS))
            for angle, image in images.items()}


def add_thumbnails(ax, thumbs, size_in, offset_pt=16):
    """Put the thumbnails under the angle axis of `ax`, centred on their angles. One zoom
    for all: the largest side of all thumbnails becomes `size_in` inches."""
    zoom = size_in * 72 / (max(max(thumb.size) for thumb in thumbs.values()) - 2)
    for angle, thumb in thumbs.items():
        box = AnnotationBbox(OffsetImage(np.asarray(thumb), zoom=zoom), (angle, 0),
                             xycoords=("data", "axes fraction"),
                             xybox=(0, -offset_pt), boxcoords="offset points",
                             box_alignment=(0.5, 1), frameon=False, annotation_clip=False)
        ax.add_artist(box)


def style(ax):
    ax.set_facecolor(SURFACE)
    ax.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK2)
    ax.set_xlim(0, 360)
    ax.set_xticks(range(0, 361, 45))
    ax.xaxis.set_major_formatter(lambda value, _: "%d°" % value)


def series(points):
    """Return the angles and the cosines. A series with 0° is closed at 360° with the
    value of 0°."""
    angles = sorted(points)
    cosines = [points[a][0] for a in angles]
    if 0 in points:
        return angles + [360], cosines + [points[0][0]]
    return angles, cosines


def subtitle(meta):
    return ("Вино: «%s». Поворот против часовой стрелки, шаг 5°. Холст растёт, бутылка "
            "не уменьшается. Вектор индекса построен на белом фоне." % meta["wine"]["name"])


TITLE_BY_MODEL = "{family}: сходство повёрнутой бутылки с её вектором в индексе"
YLABEL = "косинусное сходство с вектором индекса"
BAND_COLOR = "#ecebe6"


def shade(ax, band, legend=True):
    """Shade the angle range `band` (the angles of the reference vectors). With `legend`
    false, a label in the band replaces the legend entry."""
    if not band:
        return
    ax.axvspan(band[0], band[1], color=BAND_COLOR, zorder=0,
               label="углы опорных векторов (%d°–%d°)" % band if legend else None)
    if not legend:
        ax.text((band[0] + band[1]) / 2, 0.02, "углы опорных\nвекторов\n%d°–%d°" % band,
                ha="center", va="bottom", fontsize=9, color=INK2,
                transform=ax.get_xaxis_transform())


def chart_by_model(data, meta, directory, white, title=TITLE_BY_MODEL, text=None,
                   ylabel=YLABEL, rank=True, band=None, footer="", keys=("white", "black")):
    """`text` replaces the subtitle. `rank` false hides the circles of rank > 1. `footer`
    is added to the note under the chart. `title` may hold `{family}`."""
    thumb_angles = list(range(0, 361, 45))
    thumbs = thumbnails({a: white[a % 360] for a in thumb_angles}, round(0.5 * DPI))
    entries = entries_of(data)
    title = title.format(family=family(entries))
    fig, axes, height = grid(len(entries), row_in=3.225, top_in=1.2, bottom_in=0.95)
    low = low_limit([points[a][0] for entry in entries for key in keys
                     for points in [data[entry][key]] for a in points])
    for ax, entry in zip(axes.flat, entries):
        style(ax)
        shade(ax, band)
        for background in keys:
            points = data[entry][background]
            angles, cosines = series(points)
            ax.plot(angles, cosines, color=SERIES_COLORS[background], lw=2,
                    label=SERIES_NAMES[background])
            missed = [(a, points[a][0]) for a in sorted(points) if rank and points[a][1] > 1]
            if missed:
                ax.scatter(*zip(*missed), s=32, facecolors=SURFACE,
                           edgecolors=SERIES_COLORS[background], linewidths=1.5, zorder=3,
                           label="%s: вино не на 1-м месте" % SERIES_NAMES[background])
        ax.set_title(TITLES.get(entry, entry), loc="left", fontsize=11, color=INK)
        ax.set_ylim(low, 1.005)
        add_thumbnails(ax, thumbs, 0.5)
    for ax in axes[:, 0]:
        ax.set_ylabel(ylabel, color=INK2)
    handles, labels = [], []
    for ax in axes.flat:
        for handle, label in zip(*ax.get_legend_handles_labels()):
            if label not in labels:
                handles.append(handle)
                labels.append(label)
    top = lambda inches: 1 - inches / height  # noqa: E731
    fig.legend(handles, labels, loc="upper left", ncol=4, frameon=False,
               bbox_to_anchor=(0.01, top(0.516)), fontsize=9.5)
    fig.suptitle(title, x=0.01, y=top(0.086), ha="left", fontsize=13, color=INK)
    fig.text(0.01, top(0.387), text or subtitle(meta), fontsize=9.5, color=INK2)
    fig.text(0.01, 0.086 / height, "Под осью: положение бутылки при этом угле (общий масштаб, чёрная "
             "рамка — граница изображения)." + (" Кружок: другое вино ближе, чем это вино."
                                               if rank else "") + footer,
             fontsize=9, color=INK2)
    fig.subplots_adjust(left=0.06, right=0.985, top=top(1.2), bottom=0.95 / height,
                        hspace=0.55, wspace=0.12)
    fig.savefig(os.path.join(directory, "chart-by-model.png"), dpi=DPI, facecolor=SURFACE)
    plt.close(fig)


def spread(values, gap):
    """Return label heights near `values` with at least `gap` between neighbours. The
    group keeps the mean of `values`, so the labels move up and down."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = list(values)
    for previous, current in zip(order, order[1:]):
        out[current] = max(out[current], out[previous] + gap)
    shift = (sum(values) - sum(out)) / len(values)
    return [value + shift for value in out]


def chart_models(data, meta, directory, background, images, title=None, text=None,
                 ylabel=YLABEL, band=None, footer=""):
    """`title` may hold `{family}` and `{background}`; `text` replaces the subtitle;
    `footer` is added to the note under the chart."""
    thumb_angles = list(range(0, 361, 30))
    thumbs = thumbnails({a: images[a % 360] for a in thumb_angles}, round(0.8 * DPI))
    fig, ax = plt.subplots(figsize=(14, 7.2), facecolor=SURFACE)
    style(ax)
    shade(ax, band, legend=False)
    ax.set_xticks(range(0, 361, 15))
    ax.tick_params(axis="x", labelsize=8)
    entries = entries_of(data)
    ends, values = [], []
    for entry in entries:
        points = data[entry][background]
        angles = sorted(points)
        cosines = [points[a][0] for a in angles]
        ax.plot(angles, cosines, color=model_color(entry, entries), lw=2,
                label=TITLES.get(entry, entry))
        ends.append(cosines[-1])
        values.extend(cosines)
    low = low_limit(values)
    for entry, y in zip(entries, spread(ends, 0.014 * (1.005 - low) / 0.325)):
        last = max(data[entry][background])
        ax.annotate(TITLES.get(entry, entry), xy=(last + 1, data[entry][background][last][0]),
                    xytext=(364, y), textcoords="data", fontsize=9, color=INK,
                    va="center", annotation_clip=False,
                    arrowprops={"arrowstyle": "-", "color": INK2, "lw": 0.6,
                                "shrinkA": 0, "shrinkB": 2})
    ax.set_ylim(low, 1.005)
    ax.set_ylabel(ylabel, color=INK2)
    ax.legend(loc="upper center", ncol=len(entries), frameon=False, fontsize=9.5,
              bbox_to_anchor=(0.5, 1.09))
    title = (title or "{family}: сравнение моделей, бутылка на {background}").format(
        family=family(entries), background=SERIES_GENITIVE[background])
    fig.suptitle(title, x=0.01, y=0.985, ha="left", fontsize=13,
                 color=INK)
    fig.text(0.01, 0.925, text or subtitle(meta), fontsize=9.5, color=INK2)
    fig.text(0.01, 0.015, "Под осью: положение бутылки при этом угле (общий масштаб, чёрная "
             "рамка — граница изображения)." + footer, fontsize=9, color=INK2)
    add_thumbnails(ax, thumbs, 0.8, offset_pt=18)
    fig.subplots_adjust(left=0.055, right=0.885, top=0.84, bottom=0.24)
    fig.savefig(os.path.join(directory, "chart-models-%s.png" % background), dpi=DPI,
                facecolor=SURFACE)
    plt.close(fig)


def collage(meta, directory, background, images, columns=12, cell_px=210):
    """All rotation steps at one common scale; a black frame marks each image border."""
    largest = max(max(image.size) for image in images.values())
    scale = (cell_px - 8) / largest
    font = ImageFont.truetype(FONT, 18)
    title_font = ImageFont.truetype(FONT, 26)
    small = ImageFont.truetype(FONT, 17)
    angles = sorted(images)
    rows = -(-len(angles) // columns)
    label_h, head_h, pad = 28, 96, 12
    width = columns * cell_px + (columns + 1) * pad
    height = head_h + rows * (cell_px + label_h) + (rows + 1) * pad
    page = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(page)
    draw.text((pad, 12), "Шаги поворота бутылки: %s" % BG_NAMES[background],
              font=title_font, fill=(11, 11, 11))
    draw.text((pad, 50), "Вино: «%s». Поворот против часовой стрелки, шаг 5°. Масштаб у "
              "всех изображений один и тот же." % meta["wine"]["name"], font=small,
              fill=(82, 81, 78))
    draw.text((pad, 72), "Чёрная рамка — граница изображения, которое получает модель. "
              "Холст растёт с углом, бутылка не уменьшается.", font=small, fill=(82, 81, 78))
    for number, angle in enumerate(angles):
        image = images[angle]
        tile = framed(image.resize((max(1, round(image.width * scale)),
                                    max(1, round(image.height * scale))),
                                   Image.Resampling.LANCZOS), 2)
        column, row = number % columns, number // columns
        x0 = pad + column * (cell_px + pad)
        y0 = head_h + pad + row * (cell_px + label_h + pad)
        page.paste(tile, (x0 + (cell_px - tile.width) // 2, y0 + (cell_px - tile.height) // 2))
        text = "%d°" % angle
        text_w = draw.textlength(text, font=font)
        draw.text((x0 + (cell_px - text_w) / 2, y0 + cell_px + 4), text, font=font,
                  fill=(11, 11, 11))
    page.save(os.path.join(directory, "collage-%s.png" % background), optimize=True)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        raise SystemExit("usage: rotation_similarity_plots.py <output directory>")
    directory = argv[0]
    data = read_results(directory)
    with open(os.path.join(directory, "meta.json"), encoding="utf-8") as fh:
        meta = json.load(fh)
    angles = sorted(data[entries_of(data)[0]]["white"])
    plt.rcParams.update({"font.size": 9.5, "text.color": INK, "axes.labelcolor": INK2})
    images = {background: load_images(directory, background, angles)
              for background in BG_NAMES}
    chart_by_model(data, meta, directory, images["white"])
    for background in BG_NAMES:
        chart_models(data, meta, directory, background, images[background])
        collage(meta, directory, background, images[background])
    print("wrote the charts and the collages to %s" % directory)


if __name__ == "__main__":
    main()
