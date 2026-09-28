"""Compare vision models on the pairwise task: is this photo the wine of this slug?

The benchmark uses the shared prompt of `pipeline/wine_identity_vlm.py` without a change.
The ground truth is `review-labels.json`, the manual labels of the reviewer.
The script writes one JSONL line for each call, so a stopped run keeps its results.

The key comes from the environment variable DASHSCOPE_API_KEY. The script never
writes the key to a file or to the log.

Usage:
    python3 scripts/bench_vlm_models.py --limit 3        # smoke run
    python3 scripts/bench_vlm_models.py                  # full run
"""
import argparse
import json
import os
import random
import sqlite3
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import data_url  # noqa: E402

# The cache of the model calls is in `pipeline/`. Read docs/plans/25_model-call-cache.md.
sys.path.append(str(Path(__file__).resolve().parent.parent / "pipeline"))
import model_cache  # noqa: E402
import wine_identity_vlm  # noqa: E402

PROMPT = wine_identity_vlm.PROMPT
parse = wine_identity_vlm.parse

ROOT = Path(__file__).resolve().parent.parent
ENDPOINT = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions"
MODELS = ["qwen3.7-flash", "qwen3.8-flash", "qwen3.8-max", "qwen3-vl-flash"]
MAXSIDE = 448
SEED = 20260915

# Ground truth. 'positive' means the photo shows the wine of this slug.
# Every other label means the photo must not be accepted for this slug.
STRATA = {"positive": 150, "negative": 100, "unusable": 50}

_print_lock = threading.Lock()
_write_lock = threading.Lock()


def log(msg):
    with _print_lock:
        print(msg, flush=True)


def build_sample(limit_per_stratum=None):
    """Return a deterministic stratified sample of (slug, file, label) triples."""
    labels = json.loads((ROOT / "review-labels.json").read_text())["labels"]
    conn = sqlite3.connect(ROOT / "work" / "state.db")
    wines = {
        r[0]: {"producer": r[1], "title": r[2], "ref_path": r[3]}
        for r in conn.execute("SELECT slug,producer,title,ref_path FROM wines")
    }
    conn.close()

    pools = {k: [] for k in STRATA}
    skipped = {"no_wine_row": 0, "no_ref_file": 0, "no_photo_file": 0, "other_label": 0}
    for slug, files in sorted(labels.items()):
        w = wines.get(slug)
        if not w:
            skipped["no_wine_row"] += len(files)
            continue
        if not w["ref_path"] or not Path(w["ref_path"]).is_file():
            skipped["no_ref_file"] += len(files)
            continue
        for fname, entry in sorted(files.items()):
            label = entry.get("label")
            if label not in pools:
                skipped["other_label"] += 1
                continue
            photo = ROOT / "my" / slug / fname
            if not photo.is_file():
                skipped["no_photo_file"] += 1
                continue
            pools[label].append(
                {
                    "slug": slug,
                    "file": fname,
                    "label": label,
                    "producer": w["producer"],
                    "title": w["title"],
                    "ref_path": w["ref_path"],
                    "photo_path": str(photo),
                }
            )

    rng = random.Random(SEED)
    sample = []
    for label, want in STRATA.items():
        pool = pools[label]
        rng.shuffle(pool)
        take = want if limit_per_stratum is None else min(want, limit_per_stratum)
        sample.extend(pool[:take])
    log("pool sizes: %s" % {k: len(v) for k, v in pools.items()})
    log("skipped: %s" % skipped)
    log("sample: %d pairs" % len(sample))
    return sample


def call(model, item, ref_url, cand_url, key, timeout=180):
    payload = {
        "model": model,
        "max_tokens": 150,
        "temperature": 0,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": ref_url}},
                    {"type": "image_url", "image_url": {"url": cand_url}},
                    {"type": "text", "text": PROMPT % (item["producer"], item["title"])},
                ],
            }
        ],
    }
    # A repeated request reads the answer of `model_cache`. The line of such an answer
    # holds `"cached": true`, and the latency of the first call.
    fields = model_cache.vlm_fields(ENDPOINT, payload)
    record = model_cache.lookup(fields) if fields else None
    if record is not None:
        out = record["answer"]
        return {
            "ok": True,
            "http": 200,
            "latency_s": round(record["ms"] / 1000.0, 2),
            "raw": out["choices"][0]["message"]["content"],
            "usage": out.get("usage", {}),
            "cached": True,
        }
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            out = json.load(resp)
        dt = time.time() - t0
        if fields and out.get("choices"):
            model_cache.store(fields, out, dt * 1000)
        text = out["choices"][0]["message"]["content"]
        return {
            "ok": True,
            "http": 200,
            "latency_s": round(dt, 2),
            "raw": text,
            "usage": out.get("usage", {}),
        }
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:300]
        return {"ok": False, "http": e.code, "latency_s": round(time.time() - t0, 2),
                "error": body}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "http": 0, "latency_s": round(time.time() - t0, 2),
                "error": "%s: %s" % (type(e).__name__, e)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None,
                    help="take at most N pairs from each stratum (smoke run)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", default=str(ROOT / "work" / "vlm_bench.jsonl"))
    ap.add_argument("--models", default=",".join(MODELS))
    ap.add_argument("--retries", type=int, default=3)
    args = ap.parse_args()

    key = os.environ.get("DASHSCOPE_API_KEY")
    if not key:
        sys.exit("DASHSCOPE_API_KEY is not set")

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    sample = build_sample(args.limit)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out_path.exists():
        for line in out_path.read_text().splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            done.add((r["model"], r["slug"], r["file"]))
        log("resume: %d calls already recorded" % len(done))

    tasks = [(m, it) for it in sample for m in models
             if (m, it["slug"], it["file"]) not in done]
    log("todo: %d calls (%d models x %d pairs)" % (len(tasks), len(models), len(sample)))
    if not tasks:
        return

    url_cache = {}
    cache_lock = threading.Lock()

    def get_url(path):
        with cache_lock:
            if path in url_cache:
                return url_cache[path]
        u = data_url(path, maxside=MAXSIDE)
        with cache_lock:
            url_cache[path] = u
        return u

    fh = out_path.open("a")
    counter = {"n": 0}
    lock = threading.Lock()
    q = list(tasks)

    def worker():
        while True:
            with lock:
                if not q:
                    return
                model, item = q.pop()
            ref_url = get_url(item["ref_path"])
            cand_url = get_url(item["photo_path"])
            for attempt in range(args.retries):
                res = call(model, item, ref_url, cand_url, key)
                if res["ok"] or res["http"] not in (0, 429, 500, 502, 503, 504):
                    break
                time.sleep(2 * (attempt + 1))
            rec = dict(item)
            rec.pop("ref_path", None)
            rec.pop("photo_path", None)
            rec["model"] = model
            rec.update(res)
            rec["parsed"] = parse(res.get("raw", "")) if res.get("ok") else None
            with _write_lock:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fh.flush()
            with lock:
                counter["n"] += 1
                n = counter["n"]
            if n % 25 == 0 or n == len(tasks):
                log("  %d/%d" % (n, len(tasks)))

    threads = [threading.Thread(target=worker) for _ in range(args.workers)]
    t0 = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    fh.close()
    log("done in %.1f s -> %s" % (time.time() - t0, out_path))


if __name__ == "__main__":
    main()
