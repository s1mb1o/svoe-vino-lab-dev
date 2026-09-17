"""Stage 2. Rank the candidates of every wine and download the best ones.

Ranking uses cheap text signals only: whether the host is user-generated, whether
the producer name occurs in the result title, and how much of the wine name occurs
in the result title. Image content is judged later by stages 3 and 4.
"""
import argparse, hashlib, io, os, re, sys, threading, time
import urllib.error, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import RAW, UA, db, log

STOP = {
    "вино", "сухое", "красное",
    "белое", "розовое", "полусухое",
    "полусладкое", "игристое",
    "брют", "защищенного",
    "географического", "указания",
    "отзыв", "отзывы", "фото", "купить",
    "wine", "vino", "red", "white", "dry", "brut", "the", "and",
}
TOKEN_RE = re.compile(r"[а-яёa-z0-9]+")


def tokens(text):
    return {t for t in TOKEN_RE.findall((text or "").lower()) if len(t) > 2 and t not in STOP}


def score_candidate(cand, wine_toks, prod_toks):
    ct = tokens(cand["title"])
    s = 3.0 if cand["ugc"] else 0.0
    if prod_toks and (ct & prod_toks):
        s += 4.0
    if wine_toks:
        s += 3.0 * len(ct & wine_toks) / len(wine_toks)
    h = cand["host"]
    if "irecommend" in h or "otzovik" in h or "vivino" in h:
        s += 1.0
    q = cand["query"] or ""
    if q.startswith("site:"):
        s += 0.5
    return s


def pick(conn, slug, title, producer, per_wine, per_page):
    rows = [dict(zip(("id", "url", "host", "ugc", "title", "page_url", "query"), r))
            for r in conn.execute(
                "SELECT id,url,host,ugc,title,page_url,query FROM candidates"
                " WHERE slug=? AND (dl_status IS NULL OR dl_status='retry')", (slug,))]
    wine_toks = tokens(title)
    prod_toks = {t for t in tokens(producer) if len(t) > 3}
    for r in rows:
        r["score"] = score_candidate(r, wine_toks, prod_toks)
    rows.sort(key=lambda r: -r["score"])
    out, per_page_count = [], {}
    for r in rows:
        key = r["page_url"] or r["host"]
        if per_page_count.get(key, 0) >= per_page:
            continue
        per_page_count[key] = per_page_count.get(key, 0) + 1
        out.append(r)
        if len(out) >= per_wine:
            break
    return out


# irecommend.ru answers 521 to this host. Its CDN mirror serves the same paths.
MIRRORS = {"irecommend.ru": "cdn-irec.r-99.com", "www.irecommend.ru": "cdn-irec.r-99.com"}
# A transient block. A later pass retries these rows.
RETRY_CODES = {403, 429, 500, 502, 503, 521, 522, 523, 524}

_host_sem = {}
_host_sem_lock = threading.Lock()


def host_slot(host, limit=12):
    """At most `limit` requests in flight against one host."""
    with _host_sem_lock:
        sem = _host_sem.get(host)
        if sem is None:
            sem = _host_sem[host] = threading.Semaphore(limit)
    return sem


def fetch_url(cand):
    """Apply the mirror rewrite and return the URL to request."""
    url = cand["url"]
    m = MIRRORS.get(cand["host"])
    if m:
        parts = urllib.parse.urlsplit(url)
        url = urllib.parse.urlunsplit(("https", m, parts.path, parts.query, ""))
    return url


EXT_BY_TYPE = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
               "image/gif": ".gif", "image/bmp": ".bmp"}
MAX_BYTES = 12 * 1024 * 1024
MIN_SIDE = 200


def download_one(slug, cand):
    """Fetch one candidate. Returns a row update tuple."""
    from PIL import Image
    url = fetch_url(cand)
    ref = cand["page_url"] or ("https://" + cand["host"] + "/")
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Referer": ref,
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"})
    sem = host_slot(urllib.parse.urlparse(url).netloc.lower())
    with sem:
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
                data = resp.read(MAX_BYTES + 1)
        except urllib.error.HTTPError as exc:
            st = "retry" if exc.code in RETRY_CODES else "http:%d" % exc.code
            return (cand["id"], st, None, None, 0, 0, 0)
        except Exception as exc:  # noqa: BLE001
            return (cand["id"], "retry", None, None, 0, 0, 0)
    if len(data) > MAX_BYTES:
        return (cand["id"], "too-big", None, None, 0, 0, len(data))
    if not ctype.startswith("image/"):
        return (cand["id"], "not-image", None, None, 0, 0, len(data))
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
        w, h = im.size
    except Exception:  # noqa: BLE001
        return (cand["id"], "decode-fail", None, None, 0, 0, len(data))
    if min(w, h) < MIN_SIDE:
        return (cand["id"], "too-small", None, None, w, h, len(data))
    sha = hashlib.sha256(data).hexdigest()
    ext = EXT_BY_TYPE.get(ctype) or os.path.splitext(urllib.parse.urlparse(url).path)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"):
        ext = ".jpg"
    d = os.path.join(RAW, slug)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, sha[:16] + ext)
    if not os.path.exists(path):
        with open(path, "wb") as fh:
            fh.write(data)
    return (cand["id"], "ok", path, sha, w, h, len(data))


WRITE_LOCK = threading.Lock()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="number of wines")
    ap.add_argument("--per-wine", type=int, default=24)
    ap.add_argument("--per-page", type=int, default=3, help="max images from one source page")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--min-ok", type=int, default=0,
                    help="skip wines that already have this many downloaded images")
    args = ap.parse_args()

    conn = db()
    wines = [dict(zip(("slug", "title", "producer"), r)) for r in conn.execute(
        "SELECT w.slug,w.title,w.producer FROM wines w"
        " WHERE w.searched=1 AND w.downloaded=0 ORDER BY w.slug")]
    if args.limit:
        wines = wines[:args.limit]
    log("wines to download: %d" % len(wines))

    from concurrent.futures import ThreadPoolExecutor
    t0 = time.time()

    # One flat task list over many wines. A slow host then stalls its own requests
    # only, never a whole wine, and never the whole chunk.
    tasks, plan = [], []
    for w in wines:
        have = conn.execute("SELECT COUNT(*) FROM candidates WHERE slug=? AND dl_status='ok'",
                            (w["slug"],)).fetchone()[0]
        if args.min_ok and have >= args.min_ok:
            plan.append(w["slug"])
            continue
        chosen = pick(conn, w["slug"], w["title"], w["producer"],
                      max(0, args.per_wine - have), args.per_page)
        plan.append(w["slug"])
        for c in chosen:
            tasks.append((w["slug"], c))
    log("candidates to fetch: %d over %d wines" % (len(tasks), len(plan)))

    done = [0]
    lock = threading.Lock()

    def work(t):
        slug, cand = t
        r = download_one(slug, cand)
        with lock:
            done[0] += 1
            if done[0] % 200 == 0:
                el = time.time() - t0
                log("  %d/%d images  %.1f img/s  eta %.0f min"
                    % (done[0], len(tasks), done[0] / el,
                       (len(tasks) - done[0]) / (done[0] / el) / 60))
        return r

    results = []
    if tasks:
        with ThreadPoolExecutor(args.workers) as ex:
            results = list(ex.map(work, tasks))
    with WRITE_LOCK:
        if results:
            conn.executemany(
                "UPDATE candidates SET dl_status=?,local_path=?,sha256=?,width=?,height=?,bytes=?"
                " WHERE id=?",
                [(r[1], r[2], r[3], r[4], r[5], r[6], r[0]) for r in results])
        for slug in plan:
            conn.execute(
                "UPDATE candidates SET dl_status='dup' WHERE slug=? AND dl_status='ok'"
                " AND id NOT IN (SELECT MIN(id) FROM candidates WHERE slug=? AND dl_status='ok'"
                "                GROUP BY sha256)", (slug, slug))
            conn.execute("UPDATE wines SET downloaded=1 WHERE slug=?", (slug,))
        conn.commit()
    ok = sum(1 for r in results if r[1] == "ok")
    log("fetched ok=%d of %d" % (ok, len(results)))
    log("stage 2 done in %.1f min" % ((time.time() - t0) / 60))


if __name__ == "__main__":
    main()
