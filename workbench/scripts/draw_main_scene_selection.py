#!/usr/bin/env python3
"""Create the A4 decision map of the main-scene package selector."""
import os
from pathlib import Path

from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "main-scene-selection.pdf"

INK = HexColor("#182433")
MUTED = HexColor("#5D6976")
LINE = HexColor("#D9E0E7")
PANEL = HexColor("#F5F7FA")
TEAL = HexColor("#127C78")
TEAL_LIGHT = HexColor("#E4F5F2")
PURPLE = HexColor("#7257B7")
PURPLE_LIGHT = HexColor("#EEE9FA")
ORANGE = HexColor("#E56D3B")
ORANGE_LIGHT = HexColor("#FFF0E8")
GREEN = HexColor("#23865B")


def text(canvas, value, x, y, size=9, colour=INK, font="Helvetica"):
    canvas.setFillColor(colour)
    canvas.setFont(font, size)
    canvas.drawString(x, y, value)


def centered(canvas, value, x, y, width, size=9, colour=INK, font="Helvetica"):
    text(canvas, value, x + (width - stringWidth(value, font, size)) / 2, y,
         size, colour, font)


def wrapped(canvas, value, x, y, width, size=8.2, leading=10.5, colour=MUTED,
            font="Helvetica"):
    words = value.split()
    lines, line = [], ""
    for word in words:
        trial = word if not line else line + " " + word
        if stringWidth(trial, font, size) <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    for row in lines:
        text(canvas, row, x, y, size, colour, font)
        y -= leading
    return y


def box(canvas, x, y, width, height, fill=PANEL, stroke=LINE, radius=10, line_width=1):
    canvas.setLineWidth(line_width)
    canvas.setStrokeColor(stroke)
    canvas.setFillColor(fill)
    canvas.roundRect(x, y, width, height, radius, stroke=1, fill=1)


def arrow(canvas, x1, y1, x2, y2, colour=LINE, width=1.4):
    canvas.setStrokeColor(colour)
    canvas.setFillColor(colour)
    canvas.setLineWidth(width)
    canvas.line(x1, y1, x2, y2)
    angle = __import__("math").atan2(y2 - y1, x2 - x1)
    size = 5
    for delta in (2.55, -2.55):
        canvas.line(x2, y2, x2 + size * __import__("math").cos(angle + delta),
                    y2 + size * __import__("math").sin(angle + delta))


def number(canvas, value, x, y, colour):
    canvas.setFillColor(colour)
    canvas.circle(x, y, 10, stroke=0, fill=1)
    centered(canvas, str(value), x - 10, y - 3.4, 20, 9, white, "Helvetica-Bold")


def bottle(canvas, x, y, scale=1, colour=PURPLE):
    canvas.setFillColor(colour)
    canvas.roundRect(x + 5 * scale, y, 18 * scale, 42 * scale, 5 * scale, 0, 1)
    canvas.rect(x + 10 * scale, y + 39 * scale, 8 * scale, 12 * scale, 0, 1)
    canvas.roundRect(x + 8 * scale, y + 49 * scale, 12 * scale, 4 * scale, 2 * scale, 0, 1)


def can(canvas, x, y, scale=1, colour=ORANGE):
    canvas.setFillColor(colour)
    canvas.roundRect(x, y, 26 * scale, 50 * scale, 5 * scale, 0, 1)
    canvas.setFillColor(white)
    canvas.setFillAlpha(0.45)
    canvas.rect(x + 4 * scale, y + 4 * scale, 3 * scale, 42 * scale, 0, 1)
    canvas.setFillAlpha(1)


def hand(canvas, x, y, scale=1):
    colour = HexColor("#D39A77")
    canvas.setFillColor(colour)
    canvas.roundRect(x, y, 34 * scale, 17 * scale, 8 * scale, 0, 1)
    for index, height in enumerate((28, 34, 31, 24)):
        canvas.roundRect(x + (4 + index * 7) * scale, y + 10 * scale, 6 * scale,
                         height * scale, 3 * scale, 0, 1)


def weight_rows(canvas, x, y, width, rows, colour):
    maximum = max(value for _, value in rows)
    for label, value in rows:
        text(canvas, label, x, y, 7.7, INK)
        track_x = x + 86
        track_w = width - 115
        canvas.setFillColor(HexColor("#E2E7EC"))
        canvas.roundRect(track_x, y - 1, track_w, 5, 2.5, 0, 1)
        canvas.setFillColor(colour)
        canvas.roundRect(track_x, y - 1, track_w * value / maximum, 5, 2.5, 0, 1)
        text(canvas, f"{value:.2f}", x + width - 24, y - 0.3, 7.5, MUTED,
             "Helvetica-Bold")
        y -= 14


def score_chip(canvas, label, score, x, y, width, selected=False):
    fill = ORANGE_LIGHT if selected else PANEL
    stroke = ORANGE if selected else LINE
    box(canvas, x, y, width, 34, fill, stroke, 7, 1.2 if selected else 1)
    text(canvas, label, x + 10, y + 20, 8.2, INK, "Helvetica-Bold")
    text(canvas, "selected" if selected else "background", x + 10, y + 8, 7, MUTED)
    text(canvas, f"{score:.3f}", x + width - 47, y + 13, 10, stroke, "Helvetica-Bold")


def draw():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    canvas = Canvas(str(OUTPUT), pagesize=A4)
    width, height = A4
    canvas.setTitle("Main-scene package selection")
    canvas.setAuthor("svoe-vino-lab")

    # Header.
    text(canvas, "HOW THE RECOGNIZER SELECTS THE MAIN PACKAGE", 34, 806, 18, INK,
         "Helvetica-Bold")
    text(canvas, "A4 decision map - hybrid query-photo ranking - selector v1", 34, 786,
         9, MUTED)
    canvas.setStrokeColor(ORANGE)
    canvas.setLineWidth(3)
    canvas.line(34, 775, 561, 775)

    # Detection stage.
    box(canvas, 34, 680, 527, 78, white, LINE, 12)
    number(canvas, 1, 55, 737, TEAL)
    text(canvas, "Detect all scene objects once", 76, 732, 12, INK, "Helvetica-Bold")
    text(canvas, "SAM3 prompt: wine bottle, can, packet, box, hand", 76, 715, 8.4, MUTED)
    bottle(canvas, 402, 691, 0.8, PURPLE)
    bottle(canvas, 432, 691, 0.8, PURPLE)
    can(canvas, 469, 690, 0.82, ORANGE)
    hand(canvas, 511, 692, 0.75)
    text(canvas, "Keep every package mask and box", 76, 696, 8.4, TEAL,
         "Helvetica-Bold")
    arrow(canvas, 297, 680, 297, 658, TEAL)

    # Decision diamond.
    canvas.setFillColor(INK)
    canvas.setStrokeColor(INK)
    path = canvas.beginPath()
    path.moveTo(297, 658)
    path.lineTo(345, 633)
    path.lineTo(297, 608)
    path.lineTo(249, 633)
    path.close()
    canvas.drawPath(path, stroke=1, fill=1)
    centered(canvas, "HAND?", 258, 630, 78, 9, white, "Helvetica-Bold")
    arrow(canvas, 249, 633, 198, 633, PURPLE)
    arrow(canvas, 345, 633, 396, 633, TEAL)
    text(canvas, "YES", 211, 640, 7.5, PURPLE, "Helvetica-Bold")
    text(canvas, "NO", 365, 640, 7.5, TEAL, "Helvetica-Bold")

    # Two weighting branches.
    box(canvas, 34, 440, 253, 178, PURPLE_LIGHT, PURPLE, 12, 1.2)
    number(canvas, "2A", 55, 597, PURPLE)
    text(canvas, "Held-product weights", 76, 592, 11, INK, "Helvetica-Bold")
    text(canvas, "Hand overlap is strong, but relative area gates it.", 50, 573, 7.7, MUTED)
    weight_rows(canvas, 50, 552, 221, [
        ("hand contact", 0.40), ("relative area", 0.22), ("center", 0.14),
        ("sharpness", 0.08), ("confidence", 0.06), ("mask fill", 0.04),
        ("shelf isolation", 0.04), ("edge visibility", 0.02)], PURPLE)

    box(canvas, 308, 440, 253, 178, TEAL_LIGHT, TEAL, 12, 1.2)
    number(canvas, "2B", 329, 597, TEAL)
    text(canvas, "Main-scene weights", 350, 592, 11, INK, "Helvetica-Bold")
    text(canvas, "Use this branch when SAM3 finds no hand.", 324, 573, 7.7, MUTED)
    weight_rows(canvas, 324, 552, 221, [
        ("relative area", 0.28), ("center", 0.24), ("confidence", 0.14),
        ("sharpness", 0.12), ("shelf isolation", 0.10), ("mask fill", 0.08),
        ("edge visibility", 0.04)], TEAL)

    # Ranking stage.
    arrow(canvas, 160, 440, 160, 421, PURPLE)
    arrow(canvas, 435, 440, 435, 421, TEAL)
    box(canvas, 34, 368, 527, 45, INK, INK, 10)
    number(canvas, 3, 55, 390, ORANGE)
    text(canvas, "Score every package", 76, 389, 11, white, "Helvetica-Bold")
    text(canvas, "scene score = sum(signal x weight)   |   no bottle or can class bonus",
         215, 389, 8.2, HexColor("#DDE5EC"))
    arrow(canvas, 297, 368, 297, 350, ORANGE)

    # Observed examples.
    box(canvas, 34, 260, 527, 82, white, LINE, 10)
    text(canvas, "Observed on the two Abrau Fizz photos", 50, 322, 9.5, INK,
         "Helvetica-Bold")
    score_chip(canvas, "Photo 1 - can", 0.973, 50, 276, 142, True)
    score_chip(canvas, "best shelf bottle", 0.392, 201, 276, 142, False)
    score_chip(canvas, "Photo 2 - can", 0.977, 352, 276, 142, True)
    text(canvas, "The area gate stops tiny shelf bottles from winning through hand-box overlap.",
         50, 264, 7.4, MUTED)
    arrow(canvas, 297, 260, 297, 242, ORANGE)

    # Selection and observability.
    box(canvas, 34, 136, 527, 98, ORANGE_LIGHT, ORANGE, 12, 1.2)
    number(canvas, 4, 55, 213, ORANGE)
    text(canvas, "Choose rank 1 and use its mask", 76, 208, 11.5, INK,
         "Helvetica-Bold")
    can(canvas, 61, 148, 0.75, ORANGE)
    arrow(canvas, 100, 172, 132, 172, ORANGE)
    canvas.setStrokeColor(ORANGE)
    canvas.setDash(3, 2)
    canvas.rect(142, 147, 54, 54, 1, 0)
    canvas.setDash()
    text(canvas, "crop", 155, 137, 7.2, MUTED)
    text(canvas, "Step result records:", 222, 188, 8.5, INK, "Helvetica-Bold")
    text(canvas, "weights - signals - contributions - candidate order", 222, 172, 8, MUTED)
    text(canvas, "selected label - selected box - scene score - hand count", 222, 157, 8, MUTED)
    box(canvas, 438, 151, 105, 45, white, ORANGE, 6)
    centered(canvas, "RESULT", 438, 179, 105, 7.2, ORANGE, "Helvetica-Bold")
    centered(canvas, "observable", 438, 164, 105, 8.5, INK, "Helvetica-Bold")

    # Fallbacks and footer.
    box(canvas, 34, 65, 527, 54, PANEL, LINE, 8)
    text(canvas, "FALLBACKS", 48, 99, 7.5, MUTED, "Helvetica-Bold")
    text(canvas, "Transparent photo -> alpha crop", 48, 82, 8, INK)
    text(canvas, "No package -> white-background crop", 222, 82, 8, INK)
    text(canvas, "Old trace -> old selector", 420, 82, 8, INK)
    canvas.setStrokeColor(LINE)
    canvas.line(34, 49, 561, 49)
    text(canvas, "Catalogue images keep their existing bottle-first processing rule.",
         34, 34, 7.4, MUTED)
    text(canvas, "svoe-vino-lab / plan 69 / 2026-09-28", 384, 34, 7.4, MUTED)

    canvas.showPage()
    canvas.save()
    print(os.fspath(OUTPUT))


if __name__ == "__main__":
    draw()
