"""The planogram of a shot as a picture: the shelves of the tracker's map (replay
--planogram, planogram.hpp), the bottom one numbered 1, each facing drawn as the packshot of
its wine (the `image_url` of the recognition API's answer, public) in a box of its size.

`label`: the wine of each bottle of the planogram: its best crop (the sharpest of its
largest views, whole in the frame) goes to /v1/match (at most 4 requests at a time, the
retries of the API guide; the password from CHTOZAVINO_API_PASSWORD). OUT/labels.json:
bottle -> slug, name, producer, image_url, score, crop height.

`render`: the picture; neighbours of one wine make a block (a frame around, the bottles
alike); a bottle without a wine, or whose wine has no face (the server's image proxy fails
on some), is a grey bottle with a question mark on its label.

    uv run python scripts/planogram.py label VIDEO TRACK.jsonl PLANOGRAM.json OUT
    uv run python scripts/planogram.py render PLANOGRAM.json OUT.png [--labels OUT/labels.json]
"""

from __future__ import annotations

import argparse
import io
import json
import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from api_crops import cut, send_one, sharpness
from shelfreid.video import Preprocess, Video

FACES = Path(__file__).resolve().parents[1] / "out/planogram/faces"
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
UNIT = 260            # px per bottle height
MARGIN, LEFT = 40, 110
BAR, GAP = 14, 48     # the shelf's bar, the space above the tallest bottle of a shelf
BLOCK_GAP = 0.3       # neighbours of one wine further apart than this share of a width: two blocks


def label(args):
    out = Path(args.out)
    (out / "crops").mkdir(parents=True, exist_ok=True)
    plan = json.loads(Path(args.planogram).read_text())
    wanted = {f["bottle"] for s in plan["shelves"] for f in s["facings"]}
    views = defaultdict(list)   # bottle -> [(frame, box)]
    for line in open(args.track):
        number, shown = json.loads(line)
        for x in shown:
            if x[5] in wanted:
                views[x[5]].append((number, tuple(x[:4])))
    by_frame = defaultdict(list)
    for b, seen in views.items():
        top = max(box[3] - box[1] for _, box in seen)
        for number, box in seen:
            if box[3] - box[1] >= 0.85 * top:
                by_frame[number].append((b, box))
    best = {}   # bottle -> (sharpness, frame, crop)
    for number, frame in Video(args.video, Preprocess()).stream(step=3):
        for b, box in by_frame.get(number, []):
            if box[0] < 4 or box[1] < 4 or box[2] > frame.shape[1] - 4 or box[3] > frame.shape[0] - 4:
                continue
            crop = cut(frame, box)
            sharp = sharpness(crop)
            if b not in best or sharp > best[b][0]:
                best[b] = (sharp, number, crop.copy())
    files = {}
    for b, (_, number, crop) in best.items():
        files[b] = out / "crops" / f"b{b:03d}_f{number:05d}.png"
        cv2.imwrite(str(files[b]), crop)
    auth = ("evaluator", os.environ["CHTOZAVINO_API_PASSWORD"])
    with ThreadPoolExecutor(max_workers=4) as pool:
        answers = dict(zip(files, pool.map(lambda b: send_one(files[b], auth), files)))
    labels = {}
    for b, answer in sorted(answers.items()):
        cands = answer.get("body", {}).get("candidates", []) if answer.get("status") == 200 else []
        if not cands:
            continue
        wine = cands[0]["wine"]
        labels[b] = {"slug": cands[0]["slug"], "name": wine.get("name"), "producer": wine.get("producer"),
                     "image_url": wine.get("image_url"), "score": cands[0]["score"],
                     "crop_height": int(cv2.imread(str(files[b])).shape[0])}
    (out / "labels.json").write_text(json.dumps(labels, ensure_ascii=False, indent=1))
    print(f"{len(wanted)} bottles, {len(files)} crops, {len(labels)} answered")


def face(slug: str, url: str | None) -> Image.Image | None:
    """The packshot, cut to its opaque part; kept in FACES."""
    path = FACES / f"{slug}.webp"
    if not path.exists():
        if not url:
            return None
        r = requests.get(url, timeout=30)
        if r.status_code != 200:
            return None
        FACES.mkdir(parents=True, exist_ok=True)
        path.write_bytes(r.content)
    image = Image.open(io.BytesIO(path.read_bytes()))
    if "A" in image.getbands():
        mask = image.getchannel("A").point(lambda a: 255 if a > 16 else 0)
    else:   # a packshot on white: the part that is not white
        mask = image.convert("L").point(lambda v: 255 if v < 235 else 0)
    image = image.convert("RGBA")
    box = mask.filter(ImageFilter.MinFilter(9)).getbbox()   # not a thin line along an edge
    if box:
        image = image.crop(box)
        if "A" not in Image.open(path).getbands():   # white to transparent, so the box's frame shows
            image.putalpha(mask.crop(box))
    return image


def stand_in(draw: ImageDraw.ImageDraw, x0, y0, x1, y1, font):
    """A grey bottle with a question mark on its label: no wine, or no face for it."""
    w, h = x1 - x0, y1 - y0
    cx = (x0 + x1) / 2
    body, neck = min(0.4 * w, 0.14 * h), min(0.13 * w, 0.045 * h)
    top, shoulder, waist = y0 + 0.02 * h, y0 + 0.40 * h, y0 + 0.30 * h
    grey, light = "#bdc1c6", "#eceef0"
    draw.rounded_rectangle([cx - neck - 2, top, cx + neck + 2, top + 0.09 * h], radius=3, fill="#9aa0a6")   # the cap
    draw.polygon([(cx - neck, top + 0.09 * h), (cx + neck, top + 0.09 * h), (cx + neck, waist),
                  (cx + body, shoulder), (cx - body, shoulder), (cx - neck, waist)], fill=grey)
    draw.rounded_rectangle([cx - body, shoulder - 2, cx + body, y1 - 1], radius=max(2, body * 0.25), fill=grey)
    label = [cx - body + 3, y0 + 0.55 * h, cx + body - 3, y0 + 0.82 * h]
    draw.rectangle(label, fill=light)
    draw.text((cx, (label[1] + label[3]) / 2), "?", fill="#5f6368", font=font, anchor="mm")


def blocks(facings: list[dict], slug_of) -> list[list[dict]]:
    """The facings of a shelf in blocks: neighbours of one wine with no empty place between them
    (a gap under BLOCK_GAP of their width), resized alike: the block keeps its place, each
    facing gets an equal share of its width and the median height. A facing of an unknown
    wine is a block of its own."""
    out = []
    for f in facings:
        last = out[-1][-1] if out else None
        slug = slug_of(f)
        if (last is not None and slug and slug_of(last) == slug
                and f["x"] - (last["x"] + last["width"]) < BLOCK_GAP * min(f["width"], last["width"])):
            out[-1].append(f)
        else:
            out.append([f])
    resized = []
    for block in out:
        if len(block) > 1:
            left, right = block[0]["x"], block[-1]["x"] + block[-1]["width"]
            share = (right - left) / len(block)
            height = sorted(f["height"] for f in block)[len(block) // 2]
            block = [{**f, "x": left + i * share, "width": share, "height": height} for i, f in enumerate(block)]
        resized.append(block)
    return resized


def render(args):
    plan = json.loads(Path(args.planogram).read_text())
    labels = json.loads(Path(args.labels).read_text()) if args.labels else {}
    shelves = plan["shelves"]
    widest = max(s["width"] for s in shelves)   # the right edge of the rightmost facing
    width = LEFT + widest * UNIT + MARGIN
    bands = [max(f["height"] for f in s["facings"]) * UNIT + GAP + BAR for s in shelves]
    picture = Image.new("RGB", (round(width), round(sum(bands) + 2 * MARGIN + 40)), "white")
    draw = ImageDraw.Draw(picture)
    small, number = ImageFont.truetype(FONT, 15), ImageFont.truetype(FONT, 30)
    faces = {}
    blanks = 0
    y = MARGIN
    for k in range(len(shelves) - 1, -1, -1):   # the top shelf at the top, numbered from the bottom
        shelf, band = shelves[k], bands[k]
        floor = y + band - BAR
        draw.rectangle([LEFT - 8, floor, LEFT + widest * UNIT + 8, floor + BAR], fill="#a7adb3")
        draw.rectangle([20, floor - 60, 70, floor - 10], outline="#5f6368", width=2)
        draw.text((45, floor - 35), str(k + 1), fill="#202124", font=number, anchor="mm")
        for block in blocks(shelf["facings"], lambda f: (labels.get(str(f["bottle"])) or {}).get("slug")):
            if len(block) > 1:   # one wine side by side: a frame around, the bottles alike
                x0, x1 = LEFT + block[0]["x"] * UNIT, LEFT + (block[-1]["x"] + block[-1]["width"]) * UNIT
                top = floor - block[0]["height"] * UNIT
                draw.rectangle([x0 - 2, top - 4, x1 + 2, floor - 1], outline="#80868b", width=2)
            for f in block:
                x0, x1 = LEFT + f["x"] * UNIT, LEFT + (f["x"] + f["width"]) * UNIT
                y0 = floor - f["height"] * UNIT
                if len(block) == 1:
                    draw.rectangle([x0 + 1, y0, x1 - 1, floor - 1], outline="#d0d4d8", width=1)
                wine = labels.get(str(f["bottle"]))
                image = None
                if wine:
                    if wine["slug"] not in faces:
                        faces[wine["slug"]] = face(wine["slug"], wine.get("image_url"))
                    image = faces[wine["slug"]]
                if image is not None:
                    k_fit = min((x1 - x0 - 4) / image.width, (floor - y0 - 4) / image.height)
                    fitted = image.resize((max(1, round(image.width * k_fit)), max(1, round(image.height * k_fit))),
                                          Image.LANCZOS)
                    picture.paste(fitted, (round((x0 + x1 - fitted.width) / 2), round(floor - 2 - fitted.height)), fitted)
                else:
                    stand_in(draw, x0 + 3, y0 + 3, x1 - 3, floor - 1, number)
                    blanks += 1
                draw.text(((x0 + x1) / 2, floor + BAR + 4), str(f["bottle"]), fill="#80868b", font=small, anchor="ma")
        y += band
    known = sum(1 for s in shelves for f in s["facings"] if str(f["bottle"]) in labels)
    total = sum(len(s["facings"]) for s in shelves)
    draw.text((LEFT, y + 22), f"Полок {len(shelves)}, фейсингов {total}, распознано {known}, заглушек {blanks}",
              fill="#5f6368", font=ImageFont.truetype(FONT, 20))
    picture.save(args.out)
    print(f"{args.out}: {picture.width}x{picture.height}, {total} facings, {known} with a wine")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    lab = sub.add_parser("label")
    lab.add_argument("video")
    lab.add_argument("track")
    lab.add_argument("planogram")
    lab.add_argument("out")
    ren = sub.add_parser("render")
    ren.add_argument("planogram")
    ren.add_argument("out")
    ren.add_argument("--labels")
    args = parser.parse_args()
    {"label": label, "render": render}[args.command](args)


if __name__ == "__main__":
    main()
