"""Read the answers of scripts/api_crops.py: how often a crop of each size names the same
wine as the bottle's best crop, and how the score tells right answers from wrong ones.
Writes OUT/index.html, a gallery of every crop sent with its answer.

    uv run python scripts/api_report.py OUT
"""

from __future__ import annotations

import argparse
import html
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

KINDS = ["best", "bin600", "bin450", "bin350", "bin250", "shrink240", "shrink160", "shrink120", "shrink80"]
TITLES = {"best": "лучшая", "bin600": "рамка 600+", "bin450": "рамка 450–600", "bin350": "рамка 350–450",
          "bin250": "рамка 250–350", "shrink240": "ужата до 240", "shrink160": "ужата до 160",
          "shrink120": "ужата до 120", "shrink80": "ужата до 80"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("out")
    args = parser.parse_args()
    out = Path(args.out)
    manifest = json.loads((out / "manifest.json").read_text())
    rows = []
    for m in manifest:
        answer = json.loads((out / "answers" / (m["file"] + ".json")).read_text())
        cands = answer.get("body", {}).get("candidates", []) if answer.get("status") == 200 else []
        rows.append({**m, "seconds": answer.get("seconds"), "cands": cands})
    by_bottle = defaultdict(dict)
    for r in rows:
        by_bottle[r["bottle"]][r["kind"]] = r
    reference = {b: (k["best"]["cands"][0]["slug"] if k["best"]["cands"] else None) for b, k in by_bottle.items()}

    print(f"{len(by_bottle)} bottles, {len(rows)} answers, median time {np.median([r['seconds'] for r in rows]):.2f} s")
    print(f"{'crop':<14}{'n':>4}{'height':>8}{'same top-1':>12}{'in top-5':>10}{'score':>8}")
    scored = []   # (score, same as the reference)
    for kind in KINDS:
        sel = [r for r in rows if r["kind"] == kind]
        if not sel:
            continue
        same = [bool(r["cands"]) and r["cands"][0]["slug"] == reference[r["bottle"]] for r in sel]
        top5 = [any(c["slug"] == reference[r["bottle"]] for c in r["cands"]) for r in sel]
        scores = [r["cands"][0]["score"] for r in sel if r["cands"]]
        if kind != "best":
            scored += [(r["cands"][0]["score"], s) for r, s in zip(sel, same) if r["cands"]]
        print(f"{kind:<14}{len(sel):>4}{np.median([r['height'] for r in sel]):>8.0f}{np.mean(same):>12.2f}"
              f"{np.mean(top5):>10.2f}{np.median(scores) if scores else float('nan'):>8.3f}")
    best_scores = sorted(r["cands"][0]["score"] for r in rows if r["kind"] == "best" and r["cands"])
    print("best crops, top-1 score: min %.3f p25 %.3f median %.3f" % (best_scores[0], np.percentile(best_scores, 25),
                                                                     np.median(best_scores)))
    if scored:
        s = np.array(scored, dtype=float)
        for t in (0.70, 0.75, 0.80, 0.85):
            keep = s[:, 0] >= t
            print(f"smaller crops with score >= {t:.2f}: {keep.mean():.2f} of them, "
                  f"same as the reference {s[keep, 1].mean() if keep.any() else float('nan'):.2f} "
                  f"(below: {s[~keep, 1].mean() if (~keep).any() else float('nan'):.2f})")

    cells = []
    for b in sorted(by_bottle):
        ref = by_bottle[b]["best"]["cands"][0] if by_bottle[b]["best"]["cands"] else None
        title = html.escape(f"{ref['wine']['name']} — {ref['wine'].get('producer') or ''}") if ref else "нет ответа"
        items = []
        for kind in KINDS:
            r = by_bottle[b].get(kind)
            if not r:
                continue
            top = r["cands"][0] if r["cands"] else None
            ok = top is not None and ref is not None and top["slug"] == ref["slug"]
            name = html.escape(top["wine"]["name"]) if top else "нет ответа"
            score = f"{top['score']:.3f}" if top else "—"
            mark = "same" if ok or kind == "best" else "other"
            items.append(f'<figure class="{mark}"><img src="crops/{r["file"]}" alt="" loading="lazy">'
                         f'<figcaption><b>{TITLES[kind]}</b><span>{r["width"]}×{r["height"]} px</span>'
                         f'<span class="name">{name}</span><span class="score">score {score}</span></figcaption></figure>')
        cells.append(f'<section><h2>Бутылка {b}: {title}</h2><div class="row">{"".join(items)}</div></section>')
    page = f"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>Вырезки для распознавания</title>
<style>
body{{margin:0;padding:16px;background:#15181c;color:#e6e8eb;font:14px/1.4 system-ui,sans-serif}}
h1{{font-size:18px;margin:0 0 4px}} p{{color:#98a0aa;margin:0 0 16px}}
section{{margin:0 0 22px}} h2{{font-size:14px;font-weight:600;margin:0 0 8px}}
.row{{display:flex;gap:10px;align-items:flex-end;overflow-x:auto;padding-bottom:4px}}
figure{{margin:0;flex:none;width:150px;border-top:3px solid #43d07a;background:#1d2127;padding:6px;border-radius:4px}}
figure.other{{border-top-color:#ff5c5c}}
img{{display:block;height:300px;max-width:138px;object-fit:contain;image-rendering:auto;margin:0 auto 6px;background:#000}}
figcaption{{display:flex;flex-direction:column;gap:2px;font-size:12px}} figcaption span{{color:#98a0aa}}
.name{{color:#e6e8eb!important}} .other .name{{color:#ff8a8a!important}}
</style></head><body>
<h1>Вырезки, отправленные в /v1/match (видео 115611)</h1>
<p>Зелёная полоса — то же вино, что по лучшей вырезке бутылки; красная — другое. Все вырезки показаны одной высоты,
настоящий размер подписан. «Рамка N» — естественная вырезка из кадра, где рамка бутылки такой высоты (из 1920);
«ужата до N» — лучшая вырезка, уменьшенная до N px по высоте.</p>
{"".join(cells)}
</body></html>"""
    (out / "index.html").write_text(page, encoding="utf-8")


if __name__ == "__main__":
    main()
