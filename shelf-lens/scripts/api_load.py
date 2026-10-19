"""The throughput of /v1/match at several numbers of requests in flight: for each level, a
fresh set of bottle crops (none sent twice, so a cache on the server cannot help), sent with
that many requests at a time and the retries of the app (1, 2, 4 s after 502, 503, 504).
Per level: the wall time, crops a second, the time of a request as the client sees it and as
the server reports it (latency_ms), and the answers 503 (busy). The last level repeats the
first to show whether the server's load changed during the test. The password comes from
CHTOZAVINO_API_PASSWORD.

    uv run python scripts/api_load.py CROPS_DIR OUT.json [--levels 1,2,4,8,12,16] [--per-level 40]
"""

from __future__ import annotations

import argparse
import json
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import requests

API = "https://api.chtozavino.ru/v1/match"


def send(path: Path, auth) -> dict:
    """One crop until it is answered or the retries run out; every attempt timed."""
    attempts = []
    started = time.perf_counter()
    for wait in (1, 2, 4, None):
        t = time.perf_counter()
        try:
            with path.open("rb") as photo:
                r = requests.post(API, params={"k": 5}, auth=auth, timeout=120,
                                  files={"image": (path.name, photo, "image/png")})
            status, body = r.status_code, (r.json() if r.status_code == 200 else None)
        except requests.RequestException:
            status, body = None, None
        attempts.append({"status": status, "seconds": round(time.perf_counter() - t, 3),
                         "server_ms": body.get("latency_ms") if body else None})
        if status not in (502, 503, 504, None) or wait is None:
            break
        time.sleep(wait)
    return {"crop": path.name, "attempts": attempts, "total": round(time.perf_counter() - started, 3)}


def pct(values, q):
    return float(np.percentile(values, q)) if values else float("nan")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("crops")
    parser.add_argument("out")
    parser.add_argument("--levels", default="1,2,4,8,12,16")
    parser.add_argument("--per-level", type=int, default=40, help="crops a level (at least 4 x the level)")
    args = parser.parse_args()
    auth = ("evaluator", os.environ["CHTOZAVINO_API_PASSWORD"])
    pool = [p for p in sorted(Path(args.crops).glob("*.png")) if cv2.imread(str(p)).shape[0] >= 360]
    random.Random(0).shuffle(pool)
    levels = [int(x) for x in args.levels.split(",")]
    levels.append(levels[0])   # the first again: did the server's load change meanwhile?
    report = []
    print(f"{'in flight':>9} {'crops':>5} {'wall s':>7} {'crops/s':>8} {'client p50':>10} {'p95':>6} "
          f"{'server p50':>10} {'p95':>6} {'503':>4} {'failed':>6}")
    for level in levels:
        n = max(args.per_level, 4 * level)
        crops, pool = pool[:n], pool[n:]
        if len(crops) < n:
            print(f"not enough crops for level {level}")
            break
        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=level) as executor:
            results = list(executor.map(lambda p: send(p, auth), crops))
        wall = time.perf_counter() - started
        done = [r for r in results if r["attempts"][-1]["status"] == 200]
        client = [r["attempts"][-1]["seconds"] for r in done]
        server = [r["attempts"][-1]["server_ms"] / 1000 for r in done if r["attempts"][-1]["server_ms"]]
        busy = sum(a["status"] == 503 for r in results for a in r["attempts"])
        row = {"level": level, "crops": n, "wall": round(wall, 1), "per_second": round(len(done) / wall, 3),
               "client_p50": pct(client, 50), "client_p95": pct(client, 95), "server_p50": pct(server, 50),
               "server_p95": pct(server, 95), "busy": busy, "failed": n - len(done),
               "at": datetime.now().isoformat(timespec="seconds"), "results": results}
        report.append(row)
        print(f"{level:>9} {n:>5} {wall:>7.1f} {row['per_second']:>8.2f} {row['client_p50']:>10.2f} "
              f"{row['client_p95']:>6.2f} {row['server_p50']:>10.2f} {row['server_p95']:>6.2f} {busy:>4} "
              f"{row['failed']:>6}", flush=True)
        Path(args.out).write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
