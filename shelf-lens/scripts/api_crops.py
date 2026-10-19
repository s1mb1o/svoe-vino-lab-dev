"""How big a bottle crop the wine recognition API needs.

`make`: for a sample of the bottles a tracker dump carries, cut crops from the video: the
best one (large and sharp), the sharpest one in each size bin the bottle passes through,
and the best one shrunk to fixed heights (a shelf seen from farther away).

`send`: send each crop to /v1/match (at most 4 requests at a time, retries after 502, 503
and 504 as the API guide asks) and keep each answer next to the crop. The password comes
from CHTOZAVINO_API_PASSWORD.

`candidates`: every bottle of a dump (or those of --only) with its sharpest crop in each of
--steps size steps (5) between its farthest and nearest view, lossless PNG of the decoded
frame, and a page to pick bottles on; `serve` shows the page and keeps the picks in
selection.json.

    uv run python scripts/api_crops.py make VIDEO DUMP.jsonl OUT [--bottles 30]
    uv run python scripts/api_crops.py send OUT
    uv run python scripts/api_crops.py candidates VIDEO DUMP.jsonl OUT
    uv run python scripts/api_crops.py serve OUT [--port 8767]
"""

from __future__ import annotations

import argparse
import json
import os
import random
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np
import requests

from shelfreid.video import Preprocess, Video

API = "https://api.chtozavino.ru/v1/match"
BINS = [(250, 350), (350, 450), (450, 600), (600, 2000)]
SHRINK = [240, 160, 120, 80]
MARGIN = 0.06


def cut(frame: np.ndarray, box) -> np.ndarray:
    x1, y1, x2, y2 = box
    mx, my = MARGIN * (x2 - x1), MARGIN * (y2 - y1)
    h, w = frame.shape[:2]
    x1, y1 = max(0, int(x1 - mx)), max(0, int(y1 - my))
    x2, y2 = min(w, int(x2 + mx)), min(h, int(y2 + my))
    return frame[y1:y2, x1:x2]


def sharpness(crop: np.ndarray) -> float:
    """Laplacian variance at a common height, so crops of different sizes compare."""
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (max(8, round(gray.shape[1] * 300 / gray.shape[0])), 300), interpolation=cv2.INTER_AREA)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def make(args):
    out = Path(args.out)
    (out / "crops").mkdir(parents=True, exist_ok=True)
    obs = defaultdict(list)   # bottle -> [(frame, box)]
    for line in open(args.dump):
        number, shown = json.loads(line)
        for x in shown:
            if x[5] is not None:
                obs[x[5]].append((number, tuple(x[:4])))
    # Bottles whose largest view is whole and not at the frame edge, sampled across the clip.
    rng = random.Random(0)
    bottles = sorted(b for b, v in obs.items() if len(v) >= 20)
    bottles = sorted(rng.sample(bottles, min(args.bottles, len(bottles))))
    # The box heights are known from the dump, so each crop goes to its group at once and
    # only the sharpest crop of each (bottle, group) is kept.
    top = {b: max(box[3] - box[1] for _, box in obs[b]) for b in bottles}

    def groups(b, height):
        if height >= 0.85 * top[b]:
            yield "best"
        for lo, hi in BINS:
            if lo <= height < hi:
                yield f"bin{lo}"

    wanted = defaultdict(list)   # frame -> [(bottle, box)]
    for b in bottles:
        for number, box in obs[b]:
            wanted[number].append((b, box))
    kept = {}   # (bottle, group) -> (sharpness, frame, crop)
    for number, frame in Video(args.video, Preprocess()).stream(step=3):
        for b, box in wanted.get(number, []):
            if box[0] < 4 or box[2] > frame.shape[1] - 4 or box[1] < 4 or box[3] > frame.shape[0] - 4:
                continue   # cut by the frame
            crop = cut(frame, box)
            sharp = sharpness(crop)
            for g in groups(b, box[3] - box[1]):
                if (b, g) not in kept or sharp > kept[(b, g)][0]:
                    kept[(b, g)] = (sharp, number, crop.copy())
    manifest = []
    for b in bottles:
        if (b, "best") not in kept:
            continue
        best = kept[(b, "best")]
        picks = [("best", best)] + [(f"bin{lo}", kept[(b, f"bin{lo}")]) for lo, _ in BINS
                                    if (b, f"bin{lo}") in kept and kept[(b, f"bin{lo}")][1] != best[1]]
        for kind, (sharp, number, crop) in picks:
            file = f"b{b:03d}_{kind}_f{number:05d}.jpg"
            cv2.imwrite(str(out / "crops" / file), crop, [cv2.IMWRITE_JPEG_QUALITY, 92])
            manifest.append({"bottle": b, "kind": kind, "frame": number, "height": int(crop.shape[0]),
                             "width": int(crop.shape[1]), "sharpness": round(sharp, 1), "file": file})
        sharp, number, crop = best
        for target in SHRINK:
            if target >= crop.shape[0]:
                continue
            small = cv2.resize(crop, (max(4, round(crop.shape[1] * target / crop.shape[0])), target),
                               interpolation=cv2.INTER_AREA)
            file = f"b{b:03d}_shrink{target}_f{number:05d}.jpg"
            cv2.imwrite(str(out / "crops" / file), small, [cv2.IMWRITE_JPEG_QUALITY, 92])
            manifest.append({"bottle": b, "kind": f"shrink{target}", "frame": number, "height": target,
                             "width": int(small.shape[1]), "sharpness": None, "file": file})
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"{len(bottles)} bottles, {len(manifest)} crops")


def send_one(path: Path, auth) -> dict:
    for wait in (1, 2, 4, None):
        started = time.perf_counter()
        try:
            with path.open("rb") as photo:
                kind = "image/png" if path.suffix == ".png" else "image/jpeg"
                r = requests.post(API, params={"k": 5}, auth=auth, timeout=120,
                                  files={"image": (path.name, photo, kind)})
        except requests.RequestException as e:
            r, error = None, str(e)
        seconds = time.perf_counter() - started
        if r is not None and r.status_code not in (502, 503, 504):
            body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {"text": r.text}
            return {"status": r.status_code, "seconds": round(seconds, 2), "body": body}
        if wait is None:
            return {"status": r.status_code if r is not None else None, "seconds": round(seconds, 2),
                    "error": error if r is None else r.text[:200]}
        time.sleep(wait)


def send(args):
    out = Path(args.out)
    auth = ("evaluator", os.environ["CHTOZAVINO_API_PASSWORD"])
    manifest = json.loads((out / "manifest.json").read_text())
    (out / "answers").mkdir(exist_ok=True)
    todo = [m for m in manifest if not (out / "answers" / (m["file"] + ".json")).exists()]

    def run(m):
        answer = send_one(out / "crops" / m["file"], auth)
        (out / "answers" / (m["file"] + ".json")).write_text(json.dumps(answer, ensure_ascii=False))
        return answer["status"]

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=4) as pool:
        statuses = list(pool.map(run, todo))
    print(f"sent {len(todo)} crops in {time.perf_counter() - started:.0f} s; statuses",
          {s: statuses.count(s) for s in set(statuses)})


PAGE = """<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>Кандидаты для распознавания</title>
<style>
body{margin:0;padding:16px;background:#15181c;color:#e6e8eb;font:14px/1.4 system-ui,sans-serif}
header{position:sticky;top:0;background:#15181c;padding:8px 0 10px;z-index:2;display:flex;gap:16px;align-items:baseline;flex-wrap:wrap}
h1{font-size:18px;margin:0} p{color:#98a0aa;margin:0 0 14px;max-width:70em} #state{color:#e3b04b}
section{margin:0 0 10px;padding:8px;border:2px solid transparent;border-radius:6px;cursor:pointer;background:#1b1f24}
section.on{border-color:#43d07a;background:#1d2a22}
section h2{font-size:13px;font-weight:600;margin:0 0 6px} section h2 span{color:#98a0aa;font-weight:400}
.row{display:flex;gap:10px;align-items:flex-end;overflow-x:auto}
figure{margin:0;flex:none;text-align:center} figure img{display:block;background:#000}
figcaption{font-size:11px;color:#98a0aa;margin-top:3px}
</style></head><body>
<header><h1>__TITLE__</h1><span id="state">отмечено 0</span></header>
<p>Нажмите на ряд, чтобы отметить бутылку для проверки (отечественное вино, бутылка переднего ряда); ещё раз — снять.
В ряду настоящие вырезки из кадров, от самого дальнего вида к самому близкому, все в масштабе 0.4 от пикселей кадра:
так видно, насколько бутылка мельче издалека. Подпись — размер вырезки в пикселях кадра 1080×1920 и номер кадра.
Нажатие на вырезку с клавишей Cmd открывает её в полном размере.</p>
<main id="list"></main>
<script>
const data = __DATA__;
let picked = new Set();
const list = document.getElementById("list");
function save() {
  document.getElementById("state").textContent = "отмечено " + picked.size + " · сохраняю…";
  fetch("selection", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify([...picked])})
    .then(r => document.getElementById("state").textContent = "отмечено " + picked.size + (r.ok ? " · сохранено" : " · не сохранилось"))
    .catch(() => document.getElementById("state").textContent = "отмечено " + picked.size + " · сервер не отвечает");
}
for (const b of data) {
  const sec = document.createElement("section");
  sec.dataset.bottle = b.bottle;
  const h = document.createElement("h2");
  h.textContent = "Бутылка " + b.bottle + (b.name ? " — " + b.name : "");
  const info = document.createElement("span");
  info.textContent = " · видна в " + b.frames + " кадрах · рамка " + b.min + "–" + b.max + " px по высоте";
  h.append(info);
  const row = document.createElement("div");
  row.className = "row";
  for (const c of b.crops) {
    const f = document.createElement("figure");
    const a = document.createElement("a");
    a.href = "candidates/" + c.file; a.target = "_blank";
    a.addEventListener("click", e => { if (!e.metaKey) e.preventDefault(); });
    const img = document.createElement("img");
    img.src = "candidates/" + c.file; img.loading = "lazy";
    img.width = Math.round(c.width * 0.4); img.height = Math.round(c.height * 0.4);
    a.append(img);
    const cap = document.createElement("figcaption");
    cap.textContent = c.width + "×" + c.height + " · кадр " + c.frame;
    f.append(a, cap);
    row.append(f);
  }
  sec.append(h, row);
  sec.addEventListener("click", () => {
    const id = b.bottle;
    picked.has(id) ? picked.delete(id) : picked.add(id);
    sec.classList.toggle("on", picked.has(id));
    save();
  });
  list.append(sec);
}
fetch("selection").then(r => r.json()).then(ids => {
  picked = new Set(ids);
  document.querySelectorAll("section").forEach(s => s.classList.toggle("on", picked.has(Number(s.dataset.bottle))));
  document.getElementById("state").textContent = "отмечено " + picked.size;
}).catch(() => {});
</script></body></html>"""


def candidates(args):
    """Every bottle: its sharpest crop in each of up to five size steps, lossless PNG."""
    out = Path(args.out)
    (out / "candidates").mkdir(parents=True, exist_ok=True)
    obs = defaultdict(list)
    for line in open(args.dump):
        number, shown = json.loads(line)
        for x in shown:
            if x[5] is not None:
                obs[x[5]].append((number, tuple(x[:4])))
    if args.only:
        keep = {int(b) for b in args.only.split(",") if b.strip()}
        obs = {b: v for b, v in obs.items() if b in keep}
    steps = {}
    for b, views in obs.items():
        heights = np.array([box[3] - box[1] for _, box in views])
        edges = np.linspace(heights.min(), heights.max() + 1e-6, args.steps + 1)
        steps[b] = edges
    wanted = defaultdict(list)
    for b, views in obs.items():
        for number, box in views:
            wanted[number].append((b, box))
    kept = {}   # (bottle, step) -> (sharpness, frame, crop)
    for number, frame in Video(args.video, Preprocess()).stream(step=3):
        for b, box in wanted.get(number, []):
            if box[0] < 4 or box[2] > frame.shape[1] - 4 or box[1] < 4 or box[3] > frame.shape[0] - 4:
                continue
            step = int(np.searchsorted(steps[b], box[3] - box[1], side="right")) - 1
            crop = cut(frame, box)
            sharp = sharpness(crop)
            if (b, step) not in kept or sharp > kept[(b, step)][0]:
                kept[(b, step)] = (sharp, number, crop.copy())
    data = []
    for b in sorted(obs):
        crops = []
        for step in range(args.steps):
            if (b, step) not in kept:
                continue
            sharp, number, crop = kept[(b, step)]
            file = f"b{b:03d}_f{number:05d}.png"
            cv2.imwrite(str(out / "candidates" / file), crop)   # PNG: lossless
            crops.append({"file": file, "frame": number, "width": int(crop.shape[1]), "height": int(crop.shape[0]),
                          "sharpness": round(sharp, 1)})
        if crops:
            heights = [box[3] - box[1] for _, box in obs[b]]
            data.append({"bottle": b, "frames": len(obs[b]), "min": int(min(heights)), "max": int(max(heights)),
                         "crops": crops})
    (out / "candidates.json").write_text(json.dumps(data, indent=1))
    page = PAGE.replace("__DATA__", json.dumps(data, ensure_ascii=False)).replace("__TITLE__", f"Бутылки {Path(args.video).stem}")
    (out / "candidates.html").write_text(page, encoding="utf-8")
    print(f"{len(data)} bottles, {sum(len(d['crops']) for d in data)} crops")


def serve(args):
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

    out = Path(args.out).resolve()
    selection = out / "selection.json"

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(out), **k)

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self.path = "/candidates.html"
            if self.path == "/selection":
                body = selection.read_bytes() if selection.exists() else b"[]"
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
                return
            super().do_GET()

        def do_POST(self):
            if self.path != "/selection":
                self.send_error(404)
                return
            ids = sorted({int(i) for i in json.loads(self.rfile.read(int(self.headers["Content-Length"])))})
            selection.write_text(json.dumps(ids))
            self.send_response(200)
            self.end_headers()

        def log_message(self, *a):
            pass

    print(f"http://localhost:{args.port}/", flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    m = sub.add_parser("make")
    m.add_argument("video")
    m.add_argument("dump")
    m.add_argument("out")
    m.add_argument("--bottles", type=int, default=30)
    s = sub.add_parser("send")
    s.add_argument("out")
    c = sub.add_parser("candidates")
    c.add_argument("video")
    c.add_argument("dump")
    c.add_argument("out")
    c.add_argument("--steps", type=int, default=5, help="size steps between the farthest and the nearest view")
    c.add_argument("--only", default="", help="bottle ids, comma separated")
    v = sub.add_parser("serve")
    v.add_argument("out")
    v.add_argument("--port", type=int, default=8767)
    args = parser.parse_args()
    {"make": make, "send": send, "candidates": candidates, "serve": serve}[args.command](args)


if __name__ == "__main__":
    main()
