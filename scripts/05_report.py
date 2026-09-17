"""Stage 5. Copy the accepted photos into my/<slug>/ and build the review report.

A candidate is accepted when the vision model confirmed the same wine and judged the
photo not to be a studio render. Accepted photos are ranked by model confidence and
then by embedding similarity.
"""
import argparse, csv, html, json, os, shutil, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT, ROOT, db, log

THUMBS = os.path.join(ROOT, "work", "thumbs")
PAGE = "https://vino-svoe.ru/wines/%s"


def accepted_rows(conn, min_conf):
    rows = {}
    for r in conn.execute(
            "SELECT slug,id,local_path,vlm_conf,sim,host,page_url,url,bg_white,"
            " COALESCE(api_rank,-2) FROM candidates"
            " WHERE dl_status='ok' AND vlm_same=1 AND vlm_studio=0 AND vlm_front=1"
            "  AND vlm_conf>=? ORDER BY slug, vlm_conf DESC, sim DESC", (min_conf,)):
        rows.setdefault(r[0], []).append({
            "id": r[1], "path": r[2], "conf": r[3], "sim": r[4],
            "host": r[5], "page_url": r[6], "url": r[7], "bg": r[8], "api": r[9]})
    return rows


def thumb(src, key, size=260):
    from PIL import Image
    os.makedirs(THUMBS, exist_ok=True)
    dst = os.path.join(THUMBS, key + ".jpg")
    if os.path.exists(dst):
        return dst
    try:
        im = Image.open(src)
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[-1])
            im = bg
        else:
            im = im.convert("RGB")
        im.thumbnail((size, size))
        im.save(dst, "JPEG", quality=82)
        return dst
    except Exception:  # noqa: BLE001
        return None


def rel(path, base):
    try:
        return os.path.relpath(path, base)
    except Exception:  # noqa: BLE001
        return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-conf", type=float, default=0.6)
    ap.add_argument("--keep", type=int, default=4, help="photos copied per wine")
    ap.add_argument("--show", type=int, default=3, help="photos shown per row")
    ap.add_argument("--no-copy", action="store_true")
    args = ap.parse_args()

    conn = db()
    wines = {r[0]: {"slug": r[0], "title": r[1], "producer": r[2], "ref": r[3]}
             for r in conn.execute("SELECT slug,title,producer,ref_path FROM wines")}
    acc = accepted_rows(conn, args.min_conf)
    log("wines with at least one accepted photo: %d" % len(acc))

    report = []
    for slug, items in acc.items():
        w = wines.get(slug)
        if not w:
            continue
        keep = items[:args.keep]
        if not args.no_copy:
            d = os.path.join(OUT, slug)
            os.makedirs(d, exist_ok=True)
            for i, it in enumerate(keep, 1):
                ext = os.path.splitext(it["path"])[1] or ".jpg"
                dst = os.path.join(d, "%02d_conf%03d%s" % (i, round(it["conf"] * 100), ext))
                if not os.path.exists(dst):
                    try:
                        shutil.copy2(it["path"], dst)
                    except Exception as exc:  # noqa: BLE001
                        log("copy failed", slug, exc)
                it["out"] = dst
        top = keep[:args.show]
        confs = [it["conf"] for it in top]
        report.append({
            "slug": slug, "title": w["title"], "producer": w["producer"],
            "page": PAGE % slug, "ref": w["ref"], "items": keep,
            "n": len(keep), "n_shown": len(top),
            "min_conf": min(confs) if confs else 0.0,
            "avg_conf": sum(confs) / len(confs) if confs else 0.0,
            "min_sim": min(it["sim"] for it in top) if top else 0.0,
        })

    # Weakest evidence first: the rows that need human review most.
    report.sort(key=lambda r: (r["n_shown"] < 3, r["min_conf"], r["avg_conf"]))

    with_3 = sum(1 for r in report if r["n"] >= 3)
    log("wines with 3 or more accepted photos: %d" % with_3)

    # CSV
    csv_path = os.path.join(ROOT, "report.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["slug", "title", "producer", "page_url", "n_accepted",
                     "min_conf", "avg_conf", "ref_path",
                     "img1", "img1_conf", "img1_api_rank", "img1_src",
                     "img2", "img2_conf", "img2_api_rank", "img2_src",
                     "img3", "img3_conf", "img3_api_rank", "img3_src"])
        for r in report:
            row = [r["slug"], r["title"], r["producer"], r["page"], r["n"],
                   "%.2f" % r["min_conf"], "%.2f" % r["avg_conf"], r["ref"]]
            for i in range(3):
                if i < len(r["items"]):
                    it = r["items"][i]
                    row += [it.get("out") or it["path"], "%.2f" % it["conf"],
                            it.get("api", -2), it["page_url"] or it["url"]]
                else:
                    row += ["", "", "", ""]
            wr.writerow(row)
    log("wrote %s" % csv_path)

    # Markdown
    md = [
        "# Svoe Vino test photo set",
        "",
        "Each row is one wine from `wines.jsonl`.",
        "The found photos are real-world photos. Studio catalogue renders are excluded.",
        "`conf` is the confidence of the vision model that the photo shows the same wine.",
        "Rows are sorted by the lowest confidence first, then by the average.",
        "Review the top rows first.",
        "",
        "| # | Wine | Slug / page | min conf | avg conf | Original | 1st found | 2nd found | 3rd found |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for n, r in enumerate(report, 1):
        cells = []
        for i in range(3):
            if i < len(r["items"]):
                it = r["items"][i]
                p = rel(it.get("out") or it["path"], ROOT)
                cells.append("[%.2f](%s)<br>%s" % (it["conf"], p, it["host"]))
            else:
                cells.append("—")
        md.append("| %d | %s<br><sub>%s</sub> | [`%s`](%s) | %.2f | %.2f | [ref](%s) | %s | %s | %s |"
                  % (n, r["title"], r["producer"], r["slug"], r["page"],
                     r["min_conf"], r["avg_conf"], rel(r["ref"], ROOT), *cells))
    md_path = os.path.join(ROOT, "REPORT.md")
    open(md_path, "w", encoding="utf-8").write("\n".join(md) + "\n")
    log("wrote %s" % md_path)

    # HTML with thumbnails for visual review
    base = ROOT
    h = ["""<!doctype html><meta charset="utf-8"><title>Svoe Vino test photo set</title>
<style>
:root{color-scheme:light dark}
body{font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;margin:0;padding:24px;
     background:#fbfbfa;color:#1a1a1a}
@media (prefers-color-scheme:dark){body{background:#17181a;color:#e8e8e6}
  td,th{border-color:#33353a !important} .meta{color:#9b9ea5 !important} thead th{background:#1f2124 !important}}
h1{font-size:20px;margin:0 0 6px} p.lead{margin:0 0 18px;max-width:900px;color:#666}
table{border-collapse:collapse;width:100%}
th,td{border:1px solid #e2e2df;padding:8px;vertical-align:top;text-align:left}
thead th{position:sticky;top:0;background:#f0f0ee;z-index:2}
img{display:block;border-radius:4px;background:#fff}
.meta{font-size:11px;color:#777;margin-top:4px}
.bad{color:#c0392b;font-weight:600}.mid{color:#b8860b;font-weight:600}.good{color:#2d7a3e;font-weight:600}
a{color:inherit}
</style>
<h1>Svoe Vino test photo set</h1>
<p class="lead">Real-world photos only; studio catalogue renders are excluded.
<b>conf</b> is the vision model confidence that the photo shows the same wine.
Rows with fewer than three photos come first, then the lowest confidence, then the average.
Review the top rows first.</p>
<table><thead><tr><th>#</th><th>Wine</th><th>min / avg</th><th>Original</th>
<th>1st found</th><th>2nd found</th><th>3rd found</th></tr></thead><tbody>"""]

    def cls(c):
        return "bad" if c < 0.75 else ("mid" if c < 0.9 else "good")

    for n, r in enumerate(report, 1):
        t = thumb(r["ref"], "ref_" + r["slug"])
        refcell = ('<img src="%s" height="150">' % html.escape(rel(t, base))) if t else "—"
        cells = []
        for i in range(3):
            if i < len(r["items"]):
                it = r["items"][i]
                src = it.get("out") or it["path"]
                tt = thumb(src, "c_%d" % it["id"])
                img = ('<a href="%s"><img src="%s" height="150"></a>'
                       % (html.escape(rel(src, base)), html.escape(rel(tt, base)))) if tt else "—"
                api = it.get("api", -2)
                api_txt = {-2: "api n/a", -1: "api err", 0: "api miss"}.get(
                    api, "api #%s" % api)
                cells.append('%s<div class="meta"><span class="%s">conf %.2f</span> · sim %.2f · %s<br>'
                             '<a href="%s">%s</a></div>'
                             % (img, cls(it["conf"]), it["conf"], it["sim"], api_txt,
                                html.escape(it["page_url"] or it["url"]), html.escape(it["host"])))
            else:
                cells.append('<span class="bad">missing</span>')
        h.append('<tr><td>%d</td><td><b>%s</b><div class="meta">%s<br><a href="%s">%s</a></div></td>'
                 '<td><span class="%s">%.2f</span><br>%.2f<div class="meta">%d kept</div></td>'
                 '<td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>'
                 % (n, html.escape(r["title"]), html.escape(r["producer"]),
                    r["page"], r["slug"], cls(r["min_conf"]), r["min_conf"], r["avg_conf"],
                    r["n"], refcell, cells[0], cells[1], cells[2]))
    h.append("</tbody></table>")
    html_path = os.path.join(ROOT, "report.html")
    open(html_path, "w", encoding="utf-8").write("\n".join(h))
    log("wrote %s" % html_path)

    api_vals = [it.get("api", -2) for r in report for it in r["items"]]
    api_checked = [v for v in api_vals if v is not None and v >= 0]
    stats = {
        "official_api_checked": len(api_checked),
        "official_api_top1": sum(1 for v in api_checked if v == 1),
        "official_api_topN": sum(1 for v in api_checked if v > 0),
        "wines_total": len(wines),
        "wines_with_any": len(report),
        "wines_with_3plus": with_3,
        "photos_kept": sum(r["n"] for r in report),
        "min_conf_threshold": args.min_conf,
    }
    open(os.path.join(ROOT, "work", "report_stats.json"), "w").write(json.dumps(stats, indent=2))
    log("stats: %s" % json.dumps(stats))


if __name__ == "__main__":
    main()
