"""Stage 1. Collect candidate image URLs for every wine from several search engines.

Yandex Images is the primary engine. DuckDuckGo is secondary and disables itself
when the service rate-limits this host. The stage is resumable: a wine is marked
searched only after every planned query for it was attempted.
"""
import argparse, html, http.cookiejar, json, os, re, sys, threading, time
import urllib.error, urllib.parse, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import UA, db, init_wines, host_of, is_studio_host, is_ugc_host, log


class Engine:
    """One search engine with its own session, rate limit, and health state."""

    def __init__(self, name, min_interval, cooldown):
        self.name = name
        self.min_interval = min_interval
        self.cooldown = cooldown
        self.lock = threading.Lock()
        self.next_at = 0.0
        self.disabled_until = 0.0
        self.fails = 0
        cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        self.opener.addheaders = [
            ("User-Agent", UA),
            ("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
            ("Accept-Language", "ru,en;q=0.9"),
        ]

    def healthy(self):
        return time.time() >= self.disabled_until

    def wait(self):
        with self.lock:
            due = max(self.next_at, time.time())
            self.next_at = due + self.min_interval
        d = due - time.time()
        if d > 0:
            time.sleep(d)

    def fail(self, hard=False):
        with self.lock:
            self.fails += 1
            if hard or self.fails >= 3:
                self.disabled_until = time.time() + self.cooldown
                self.fails = 0
                log("engine %s disabled for %ds" % (self.name, self.cooldown))

    def good(self):
        with self.lock:
            self.fails = 0

    def get(self, url, headers=None, timeout=30):
        req = urllib.request.Request(url)
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        with self.opener.open(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", "ignore")


YANDEX = Engine("yandex", 1.3, 180)
DDG = Engine("ddg", 3.0, 900)


def yandex_images(query, page=0):
    if not YANDEX.healthy():
        return [], "disabled"
    params = {"text": query}
    if page:
        params["p"] = page
    YANDEX.wait()
    try:
        s = YANDEX.get("https://yandex.ru/images/search?" + urllib.parse.urlencode(params))
    except urllib.error.HTTPError as exc:
        YANDEX.fail(hard=exc.code in (403, 429))
        return [], "http:%d" % exc.code
    except Exception as exc:  # noqa: BLE001
        YANDEX.fail()
        return [], "net:%s" % type(exc).__name__
    low = s.lower()
    if "smartcaptcha" in low or "showcaptcha" in low or "checkcaptcha" in low:
        YANDEX.fail(hard=True)
        return [], "captcha"
    YANDEX.good()
    d = html.unescape(s)
    out, seen = [], set()
    for m in re.finditer(r'"img_href":"(https?://[^"]+)"', d):
        u = m.group(1)
        if u in seen:
            continue
        seen.add(u)
        # The snippet block with the source page title and URL precedes img_href.
        head = d[max(0, m.start() - 4000): m.start()]
        cut = head.rfind('"snippet":{')
        title = page = ""
        if cut >= 0:
            blk = head[cut:]
            t = re.search(r'"title":"((?:[^"\\]|\\.)*)"', blk)
            p = re.search(r'"url":"(https?://[^"]+)"', blk)
            title = t.group(1) if t else ""
            page = p.group(1) if p else ""
        out.append({"url": u, "page_url": page, "title": title})
    return out, None


def ddg_images(query):
    if not DDG.healthy():
        return [], "disabled"
    DDG.wait()
    try:
        page = DDG.get("https://duckduckgo.com/?" + urllib.parse.urlencode(
            {"q": query, "iax": "images", "ia": "images"}))
    except urllib.error.HTTPError as exc:
        DDG.fail(hard=exc.code in (202, 403, 429))
        return [], "http:%d" % exc.code
    except Exception as exc:  # noqa: BLE001
        DDG.fail()
        return [], "net:%s" % type(exc).__name__
    m = re.search(r'vqd=["\']?([\w-]+)', page)
    if not m:
        DDG.fail(hard=True)
        return [], "no-vqd"
    DDG.wait()
    api = "https://duckduckgo.com/i.js?" + urllib.parse.urlencode(
        {"l": "ru-ru", "o": "json", "q": query, "vqd": m.group(1), "f": ",,,", "p": "1"})
    try:
        data = json.loads(DDG.get(api, {"Referer": "https://duckduckgo.com/"}))
    except urllib.error.HTTPError as exc:
        DDG.fail(hard=exc.code in (403, 429))
        return [], "http:%d" % exc.code
    except Exception as exc:  # noqa: BLE001
        DDG.fail()
        return [], "net:%s" % type(exc).__name__
    DDG.good()
    out = []
    for it in data.get("results", []):
        u = it.get("image") or ""
        if u.startswith("http"):
            out.append({"url": u, "page_url": it.get("url") or "", "title": it.get("title") or ""})
    return out, None


def clean(s):
    return re.sub(r"\s+", " ", re.sub(r'["«»“”]', " ", s or "")).strip()


WINE = "вино"
OTZYV = "отзыв"
FOTO = "фото"


def build_queries(w):
    base = clean(w["producer"] + " " + w["title"]) or w["slug"].replace("-", " ")
    return [
        ("yandex", "site:irecommend.ru %s" % base, 0),
        ("yandex", "site:otzovik.com %s" % base, 0),
        ("yandex", "%s %s %s" % (base, WINE, OTZYV), 0),
        ("ddg", "%s %s %s %s" % (base, WINE, OTZYV, FOTO), 0),
    ]


WRITE_LOCK = threading.Lock()


def process(w, done):
    conn = db()
    rows, qrows, attempted, skipped = [], [], 0, 0
    for engine, query, page in build_queries(w):
        key = (w["slug"], engine, query + ("#%d" % page if page else ""))
        if key in done:
            continue
        if engine == "yandex":
            items, err = yandex_images(query, page)
        else:
            items, err = ddg_images(query)
        if err == "disabled":
            skipped += 1
            continue
        attempted += 1
        qrows.append((key[0], key[1], key[2], len(items), err or "", time.time()))
        for it in items:
            host = host_of(it["url"])
            if not host or is_studio_host(host):
                continue
            rows.append((w["slug"], it["url"], host, engine, query,
                         (it["page_url"] or "")[:500], (it["title"] or "")[:200],
                         1 if is_ugc_host(host) else 0))
    with WRITE_LOCK:
        if rows:
            conn.executemany(
                "INSERT OR IGNORE INTO candidates (slug,url,host,engine,query,page_url,title,ugc)"
                " VALUES (?,?,?,?,?,?,?,?)", rows)
        if qrows:
            conn.executemany(
                "INSERT OR REPLACE INTO queries (slug,engine,query,n,err,ts) VALUES (?,?,?,?,?,?)",
                qrows)
        # Only a wine whose yandex queries all ran counts as searched.
        if attempted:
            conn.execute("UPDATE wines SET searched=1 WHERE slug=?", (w["slug"],))
        conn.commit()
    return len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--redo", action="store_true")
    args = ap.parse_args()

    init_wines()
    conn = db()
    q = "SELECT slug,title,producer FROM wines"
    if not args.redo:
        q += " WHERE searched=0"
    todo = [dict(zip(("slug", "title", "producer"), r)) for r in conn.execute(q + " ORDER BY slug")]
    if args.limit:
        todo = todo[:args.limit]
    done = {(a, b, c) for a, b, c in
            conn.execute("SELECT slug,engine,query FROM queries WHERE err='' OR err='disabled'")}
    log("wines to search: %d  workers=%d  queries already done: %d" % (len(todo), args.workers, len(done)))

    from concurrent.futures import ThreadPoolExecutor
    t0, n, lock = time.time(), [0], threading.Lock()

    def run(w):
        try:
            process(w, done)
        except Exception as exc:  # noqa: BLE001
            log("ERR", w["slug"], type(exc).__name__, exc)
        with lock:
            n[0] += 1
            if n[0] % 20 == 0 or n[0] == len(todo):
                el = time.time() - t0
                rate = n[0] / el if el else 0
                c2 = db()
                total = c2.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
                ugc = c2.execute("SELECT COUNT(*) FROM candidates WHERE ugc=1").fetchone()[0]
                log("%d/%d  cands=%d (ugc %d)  %.2f w/s  eta %.0f min  [ya %s | ddg %s]"
                    % (n[0], len(todo), total, ugc, rate,
                       (len(todo) - n[0]) / rate / 60 if rate else 0,
                       "ok" if YANDEX.healthy() else "cooldown",
                       "ok" if DDG.healthy() else "cooldown"))

    with ThreadPoolExecutor(args.workers) as ex:
        list(ex.map(run, todo))
    log("stage 1 done in %.1f min" % ((time.time() - t0) / 60))


if __name__ == "__main__":
    main()
