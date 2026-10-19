"""Grade the answers of scripts/api_crops.py against the wines read from the labels
(OUT/truth.json: bottle -> {"label", "producer", "slug" or null when the catalogue lacks
the wine, and optionally "slugs": every catalogue entry that is this wine}; bottles missing
from truth.json are left out) and write OUT/index.html with each crop marked: the right wine, only the right
producer, a wrong wine, or a wine the catalogue lacks.

    uv run python scripts/api_grade.py OUT
"""

from __future__ import annotations

import argparse
import html
import json
from collections import defaultdict
from pathlib import Path

GRADES = {"right": ("верно", "#43d07a"), "producer": ("только производитель", "#e3b04b"),
          "wrong": ("неверно", "#ff5c5c"), "absent": ("вина нет в каталоге", "#7d8794")}
HEIGHTS = [(0, 400), (400, 500), (500, 600), (600, 800), (800, 1000), (1000, 1300), (1300, 3000)]


def grade(truth: dict, top: dict | None) -> str:
    if truth["slug"] is None:
        return "absent"
    if top is None:
        return "wrong"
    if top["slug"] in truth.get("slugs", [truth["slug"]]):
        return "right"
    return "producer" if (top["wine"].get("producer") or "").lower() == truth["producer"].lower() else "wrong"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("out")
    args = parser.parse_args()
    out = Path(args.out)
    truth = {int(k): v for k, v in json.loads((out / "truth.json").read_text()).items()}
    manifest = json.loads((out / "manifest.json").read_text())
    rows = []
    for m in manifest:
        if m["bottle"] not in truth:
            continue
        answer = json.loads((out / "answers" / (m["file"] + ".json")).read_text())
        cands = answer.get("body", {}).get("candidates", [])
        t = truth[m["bottle"]]
        top = cands[0] if cands else None
        g = grade(t, top)
        in5 = t["slug"] is not None and any(c["slug"] in t.get("slugs", [t["slug"]]) for c in cands)
        rows.append({**m, "top": top, "grade": g, "in5": in5, "seconds": answer.get("seconds")})

    known = [r for r in rows if r["grade"] != "absent"]
    print(f"{len(rows)} crops of {len(truth)} bottles; the catalogue has the wine of "
          f"{sum(1 for t in truth.values() if t['slug'])} bottles ({len(known)} crops)")
    print(f"{'crop height':<14}{'crops':>6}{'right':>7}{'producer':>10}{'wrong':>7}{'in top-5':>10}")
    for lo, hi in HEIGHTS:
        sel = [r for r in known if lo <= r["height"] < hi]
        if sel:
            n = len(sel)
            print(f"{f'{lo}-{hi}':<14}{n:>6}{sum(r['grade'] == 'right' for r in sel) / n:>7.2f}"
                  f"{sum(r['grade'] == 'producer' for r in sel) / n:>10.2f}{sum(r['grade'] == 'wrong' for r in sel) / n:>7.2f}"
                  f"{sum(r['in5'] for r in sel) / n:>10.2f}")
    for g in ("right", "producer", "wrong", "absent"):
        s = sorted(r["top"]["score"] for r in rows if r["grade"] == g and r["top"])
        if s:
            print(f"score, {GRADES[g][0]}: {len(s)} crops, min {s[0]:.3f} median {s[len(s) // 2]:.3f} max {s[-1]:.3f}")

    by_bottle = defaultdict(list)
    for r in rows:
        by_bottle[r["bottle"]].append(r)
    order = sorted(by_bottle, key=lambda b: (truth[b]["slug"] is None, b))
    sections = []
    for b in order:
        t = truth[b]
        status = "в каталоге" if t["slug"] else "этого вина нет в каталоге"
        figs = []
        for r in sorted(by_bottle[b], key=lambda r: r["height"]):
            label, colour = GRADES[r["grade"]]
            top = r["top"]
            name = html.escape(f"{top['wine']['name']} ({top['wine'].get('producer') or '—'})") if top else "нет ответа"
            score = f"{top['score']:.3f}" if top else "—"
            extra = " · верное в топ-5" if r["in5"] and r["grade"] != "right" else ""
            figs.append(
                f'<figure style="border-color:{colour}"><a href="crops/{r["file"]}" target="_blank">'
                f'<img src="crops/{r["file"]}" width="{round(r["width"] * 0.4)}" height="{round(r["height"] * 0.4)}" alt=""></a>'
                f'<figcaption><b style="color:{colour}">{label}</b><span>{r["width"]}×{r["height"]} px · score {score}{extra}</span>'
                f'<span class="name">{name}</span></figcaption></figure>')
        sections.append(f'<section><h2>Бутылка {b}: {html.escape(t["label"])} <span>· {status}</span></h2>'
                        f'<div class="row">{"".join(figs)}</div></section>')
    legend = "".join(f'<span><i style="background:{c}"></i>{n}</span>' for n, c in GRADES.values())
    page = f"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>Распознавание по вырезкам</title>
<style>
body{{margin:0;padding:16px;background:#15181c;color:#e6e8eb;font:14px/1.4 system-ui,sans-serif}}
h1{{font-size:18px;margin:0 0 6px}} p{{color:#98a0aa;margin:0 0 10px;max-width:72em}}
.legend{{display:flex;gap:16px;flex-wrap:wrap;margin:0 0 16px;font-size:13px}}
.legend i{{display:inline-block;width:12px;height:12px;border-radius:2px;margin-right:6px;vertical-align:-1px}}
section{{margin:0 0 18px}} h2{{font-size:14px;font-weight:600;margin:0 0 8px}} h2 span{{color:#98a0aa;font-weight:400}}
.row{{display:flex;gap:10px;align-items:flex-end;overflow-x:auto;padding-bottom:4px}}
figure{{margin:0;flex:none;width:190px;border-top:4px solid;background:#1d2127;padding:6px;border-radius:4px}}
img{{display:block;margin:0 auto 6px;background:#000}}
figcaption{{display:flex;flex-direction:column;gap:2px;font-size:12px}} figcaption span{{color:#98a0aa}}
.name{{color:#e6e8eb!important}}
</style></head><body>
<h1>Распознавание отечественных вин по вырезкам (видео 115611)</h1>
<p>Каждая вырезка отправлена в /v1/match как есть: PNG без потерь из декодированного кадра 1080×1920.
Вырезки идут от самого дальнего вида бутылки к самому близкому и показаны в одном масштабе (0.4 от пикселей кадра).
Под каждой — первый ответ сервиса и его score. Нажатие открывает вырезку в полном размере.</p>
<div class="legend">{legend}</div>
{"".join(sections)}
</body></html>"""
    (out / "index.html").write_text(page, encoding="utf-8")


if __name__ == "__main__":
    main()
