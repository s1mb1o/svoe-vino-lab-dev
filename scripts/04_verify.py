"""Stage 4. Confirm the wine identity of each shortlisted candidate with a vision model.

The model receives the catalogue reference photo and one candidate photo, plus the
producer and the wine name as text. It answers whether the candidate shows the same
wine, how sure it is, and whether the candidate is a studio catalogue render.
"""
import argparse, json, os, queue, re, sys, threading, time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import CONFIG, data_url, db, log

# The cache of the model calls is in `pipeline/`. Read docs/plans/25_model-call-cache.md.
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "pipeline"))
import model_cache  # noqa: E402
import vlm_config  # noqa: E402

PROMPT = (
    "\u041f\u0435\u0440\u0432\u043e\u0435 \u0444\u043e\u0442\u043e \u2014 \u044d\u0442\u0430\u043b\u043e\u043d \u0431\u0443\u0442\u044b\u043b\u043a\u0438 \u0438\u0437 \u043a\u0430\u0442\u0430\u043b\u043e\u0433\u0430. "
    "\u042d\u0442\u043e \u0432\u0438\u043d\u043e: \u043f\u0440\u043e\u0438\u0437\u0432\u043e\u0434\u0438\u0442\u0435\u043b\u044c \"%s\", \u043d\u0430\u0437\u0432\u0430\u043d\u0438\u0435 \"%s\". "
    "\u0412\u0442\u043e\u0440\u043e\u0435 \u0444\u043e\u0442\u043e \u2014 \u0438\u0437 \u0438\u043d\u0442\u0435\u0440\u043d\u0435\u0442\u0430.\n"
    "\u041e\u0442\u0432\u0435\u0442\u044c true \u0422\u041e\u041b\u042c\u041a\u041e \u0435\u0441\u043b\u0438 \u043d\u0430 \u0432\u0442\u043e\u0440\u043e\u043c \u0444\u043e\u0442\u043e \u0432\u0438\u0434\u043d\u0430 "
    "\u0431\u0443\u0442\u044b\u043b\u043a\u0430 \u0418\u041c\u0415\u041d\u041d\u041e \u044d\u0442\u043e\u0433\u043e \u0432\u0438\u043d\u0430 \u0441 \u0435\u0433\u043e \u043f\u0435\u0440\u0435\u0434\u043d\u0435\u0439 \u044d\u0442\u0438\u043a\u0435\u0442\u043a\u043e\u0439.\n"
    "\u041e\u0442\u0432\u0435\u0442\u044c false \u0435\u0441\u043b\u0438:\n"
    "- \u0432\u0438\u0434\u043d\u0430 \u0442\u043e\u043b\u044c\u043a\u043e \u0437\u0430\u0434\u043d\u044f\u044f \u044d\u0442\u0438\u043a\u0435\u0442\u043a\u0430 (\u043a\u043e\u043d\u0442\u0440\u044d\u0442\u0438\u043a\u0435\u0442\u043a\u0430) \u0431\u0435\u0437 \u043f\u0435\u0440\u0435\u0434\u043d\u0435\u0439;\n"
    "- \u0432\u0438\u0434\u043d\u0430 \u0442\u043e\u043b\u044c\u043a\u043e \u043f\u0440\u043e\u0431\u043a\u0430, \u043a\u043e\u0440\u043e\u0431\u043a\u0430, \u0431\u043e\u043a\u0430\u043b \u0438\u043b\u0438 \u0447\u0435\u043a;\n"
    "- \u044d\u0442\u043e \u0414\u0420\u0423\u0413\u041e\u0415 \u0432\u0438\u043d\u043e \u0442\u043e\u0433\u043e \u0436\u0435 \u043f\u0440\u043e\u0438\u0437\u0432\u043e\u0434\u0438\u0442\u0435\u043b\u044f "
    "(\u0434\u0440\u0443\u0433\u043e\u0439 \u0441\u043e\u0440\u0442, \u0434\u0440\u0443\u0433\u0430\u044f \u0441\u0435\u0440\u0438\u044f, \u0434\u0440\u0443\u0433\u043e\u0439 \u0446\u0432\u0435\u0442);\n"
    "- \u043d\u0430\u0437\u0432\u0430\u043d\u0438\u0435 \u043d\u0435\u043b\u044c\u0437\u044f \u043f\u0440\u043e\u0447\u0438\u0442\u0430\u0442\u044c \u0438 \u044d\u0442\u0438\u043a\u0435\u0442\u043a\u0430 \u0432\u0438\u0437\u0443\u0430\u043b\u044c\u043d\u043e \u043d\u0435 \u0441\u043e\u0432\u043f\u0430\u0434\u0430\u0435\u0442 \u0441 \u044d\u0442\u0430\u043b\u043e\u043d\u043e\u043c.\n"
    "\u041e\u0442\u0432\u0435\u0442\u044c \u0442\u043e\u043b\u044c\u043a\u043e JSON: "
    "{\"same_wine\":true|false,\"confidence\":0.0-1.0,\"studio\":true|false,\"front_label\":true|false}"
)

JSON_RE = re.compile(r"\{[^{}]*\}")


def parse(text):
    m = JSON_RE.search(text or "")
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except Exception:  # noqa: BLE001
        return None
    if "same_wine" not in d:
        return None
    return {
        "same": 1 if d.get("same_wine") else 0,
        "conf": float(d.get("confidence", 0) or 0),
        "studio": 1 if d.get("studio") else 0,
        "front": 1 if d.get("front_label") else 0,
    }


class Backend:
    """One vision endpoint. `name` is the name of its entry of the key `vlm`."""

    def __init__(self, name, url, model, key, workers):
        self.name = name
        self.url = url
        self.model = model
        self.key = key
        self.workers = workers
        self.calls = 0
        self.errors = 0
        self.hits = 0

    def ask(self, ref_url, cand_url, producer, title, timeout=240):
        payload = {"model": self.model, "max_tokens": 150, "temperature": 0,
                   "messages": [{"role": "user", "content": [
                       {"type": "image_url", "image_url": {"url": ref_url}},
                       {"type": "image_url", "image_url": {"url": cand_url}},
                       {"type": "text", "text": PROMPT % (producer, title)}]}]}
        # A repeated request reads the answer of `model_cache`. An answer with a choice
        # is stored.
        fields = model_cache.vlm_fields(self.url, payload)
        record = model_cache.lookup(fields) if fields else None
        if record is not None:
            self.hits += 1
            return record["answer"]["choices"][0]["message"]["content"]
        headers = {"Content-Type": "application/json"}
        if self.key:
            headers["Authorization"] = "Bearer " + self.key
        req = urllib.request.Request(self.url, data=json.dumps(payload).encode(),
                                     headers=headers)
        started = time.perf_counter()
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            out = json.load(resp)
        if fields and out.get("choices"):
            model_cache.store(fields, out, (time.perf_counter() - started) * 1000)
        return out["choices"][0]["message"]["content"]


def build_backends(spec, config=CONFIG):
    """spec: comma list of name:workers. A name is an entry of the key `vlm` of the
    configuration, e.g. qwen3-vl-32b:12,qwencloud-qwen3.8-flash:8,dashscope-qwen3.7-flash:6"""
    entries = vlm_config.entries(config)
    out = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        name, _, n = part.partition(":")
        entry = entries.get(name)
        if entry is None:
            log("unknown backend %s, ignored" % name)
            continue
        key = entry.api_key()
        if entry.key_env and not key:
            log("backend %s has no API key in the environment, ignored" % name)
            continue
        out.append(Backend(name, entry.url, entry.model, key, int(n or 4)))
    return out


REF_CACHE = {}
REF_LOCK = threading.Lock()


def ref_data_url(path, maxside):
    with REF_LOCK:
        u = REF_CACHE.get(path)
    if u is None:
        u = data_url(path, maxside=maxside)
        with REF_LOCK:
            REF_CACHE[path] = u
            if len(REF_CACHE) > 400:
                REF_CACHE.clear()
                REF_CACHE[path] = u
    return u


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--top", type=int, default=8, help="candidates verified per wine")
    ap.add_argument("--backends", default="qwen3-vl-32b:12",
                    help="comma list of name:workers; a name is an entry of the key vlm, "
                         "e.g. qwen3-vl-32b:12,qwencloud-qwen3.8-flash:8")
    ap.add_argument("--maxside", type=int, default=448)
    ap.add_argument("--bg-max", type=float, default=0.55)
    ap.add_argument("--sim-min", type=float, default=0.25)
    ap.add_argument("--wine-batch", type=int, default=60,
                    help="wines whose candidates are dispatched together")
    args = ap.parse_args()

    backends = build_backends(args.backends)
    if not backends:
        log("no usable backend")
        return
    total_workers = sum(b.workers for b in backends)
    log("backends: %s (total %d workers)"
        % (", ".join("%s:%d" % (b.name, b.workers) for b in backends), total_workers))

    conn = db()
    wines = [dict(zip(("slug", "title", "producer", "ref_path"), r)) for r in conn.execute(
        "SELECT slug,title,producer,ref_path FROM wines WHERE embedded=1 AND verified=0"
        " ORDER BY slug")]
    if args.limit:
        wines = wines[:args.limit]
    log("wines to verify: %d" % len(wines))
    if not wines:
        return

    t0 = time.time()
    n_calls = [0]
    stat_lock = threading.Lock()

    for base in range(0, len(wines), args.wine_batch):
        group = wines[base:base + args.wine_batch]
        tasks, ready = [], []
        for w in group:
            rows = conn.execute(
                "SELECT id,local_path FROM candidates WHERE slug=? AND dl_status='ok'"
                " AND vlm_same IS NULL AND sim>=? AND (bg_white IS NULL OR bg_white<=?)"
                " ORDER BY sim DESC LIMIT ?",
                (w["slug"], args.sim_min, args.bg_max, args.top)).fetchall()
            present = [(cid, p) for cid, p in rows if p and os.path.exists(p)]
            if not os.path.exists(w["ref_path"] or ""):
                log("skip %s: reference photo missing" % w["slug"])
                continue
            if len(present) < len(rows):
                log("skip %s: %d of %d candidate files missing"
                    % (w["slug"], len(rows) - len(present), len(rows)))
                continue
            if not present:
                conn.execute("UPDATE wines SET verified=1 WHERE slug=?", (w["slug"],))
                continue
            ready.append(w["slug"])
            for cid, path in present:
                tasks.append((cid, path, w))
        conn.commit()
        if not tasks:
            continue

        q = queue.Queue()
        for t in tasks:
            q.put(t)
        results = []
        res_lock = threading.Lock()

        def worker(backend):
            while True:
                try:
                    cid, path, w = q.get_nowait()
                except queue.Empty:
                    return
                try:
                    ref_url = ref_data_url(w["ref_path"], args.maxside)
                    cand_url = data_url(path, maxside=args.maxside)
                    txt = backend.ask(ref_url, cand_url, w["producer"], w["title"])
                    res = parse(txt)
                    with stat_lock:
                        backend.calls += 1
                        n_calls[0] += 1
                except Exception as exc:  # noqa: BLE001
                    with stat_lock:
                        backend.errors += 1
                    res, txt = None, "ERR:%s" % type(exc).__name__
                with res_lock:
                    results.append((cid, res, (txt or "")[:300], backend.name))
                q.task_done()

        threads = []
        for b in backends:
            for _ in range(b.workers):
                th = threading.Thread(target=worker, args=(b,), daemon=True)
                th.start()
                threads.append(th)
        for th in threads:
            th.join()

        ups = []
        for cid, res, txt, bname in results:
            if res is None:
                ups.append((None, None, None, None, txt, bname, cid))
            else:
                ups.append((res["same"], res["conf"], res["studio"], res["front"],
                            txt, bname, cid))
        conn.executemany(
            "UPDATE candidates SET vlm_same=?,vlm_conf=?,vlm_studio=?,vlm_front=?,vlm_raw=?,"
            "vlm_model=? WHERE id=?", ups)
        # Close only wines whose candidates all carry a verdict now.
        for slug in ready:
            left = conn.execute(
                "SELECT COUNT(*) FROM candidates WHERE slug=? AND dl_status='ok'"
                " AND vlm_same IS NULL AND vlm_raw LIKE 'ERR:%'", (slug,)).fetchone()[0]
            if left == 0:
                conn.execute("UPDATE wines SET verified=1 WHERE slug=?", (slug,))
        conn.commit()

        done = base + len(group)
        el = time.time() - t0
        acc = conn.execute("SELECT COUNT(*) FROM candidates WHERE vlm_same=1"
                           " AND vlm_studio=0 AND vlm_front=1").fetchone()[0]
        log("%d/%d wines  %d calls  %.2f s/call  accepted=%d  eta %.0f min  [%s]"
            % (done, len(wines), n_calls[0], el / max(1, n_calls[0]), acc,
               (len(wines) - done) / (done / el) / 60 if el and done else 0,
               " ".join("%s %d/%de" % (b.name, b.calls, b.errors) for b in backends)))
    log("stage 4 done in %.1f min" % ((time.time() - t0) / 60))


if __name__ == "__main__":
    main()
