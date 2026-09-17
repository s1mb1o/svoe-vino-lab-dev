"""Driver. Runs stages 2, 3, and 4 in chunks until every searched wine is processed.

Stages 3 and 4 use different models on the same llama-swap host. The driver works in
large chunks so that the host swaps models a few times per hour, not once per wine.
"""
import argparse, os, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import db, log

HERE = os.path.dirname(os.path.abspath(__file__))


def run(script, *a):
    cmd = [sys.executable, os.path.join(HERE, script)] + [str(x) for x in a]
    p = subprocess.run(cmd, capture_output=True, text=True)
    tail = [l for l in (p.stdout or "").strip().splitlines() if l][-2:]
    for l in tail:
        log("   " + l)
    if p.returncode != 0:
        log("   FAILED %s rc=%d %s" % (script, p.returncode, (p.stderr or "")[-300:]))
    return p.returncode


def counts():
    c = db()
    q = lambda s: c.execute(s).fetchone()[0]
    return {
        "searched": q("SELECT COUNT(*) FROM wines WHERE searched=1"),
        "downloaded": q("SELECT COUNT(*) FROM wines WHERE downloaded=1"),
        "embedded": q("SELECT COUNT(*) FROM wines WHERE embedded=1"),
        "verified": q("SELECT COUNT(*) FROM wines WHERE verified=1"),
        "accepted": q("SELECT COUNT(*) FROM candidates WHERE vlm_same=1 AND vlm_studio=0 AND vlm_front=1"),
        "wines_with_3": q("SELECT COUNT(*) FROM (SELECT slug FROM candidates"
                          " WHERE vlm_same=1 AND vlm_studio=0 AND vlm_front=1 GROUP BY slug HAVING COUNT(*)>=3)"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunk", type=int, default=150)
    ap.add_argument("--per-wine", type=int, default=20)
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--dl-workers", type=int, default=16)
    ap.add_argument("--vlm-workers", type=int, default=6)
    ap.add_argument("--backends", default="local:12",
                    help="passed to stage 4, e.g. local:12,tokenplan:8,dashscope:6")
    ap.add_argument("--total", type=int, default=2018)
    ap.add_argument("--stages", default="234",
                    help="which stages this driver runs, e.g. 23 or 4")
    args = ap.parse_args()

    t0 = time.time()
    idle = 0
    while True:
        c = counts()
        log("state: searched=%d downloaded=%d embedded=%d verified=%d accepted=%d wines>=3: %d"
            % (c["searched"], c["downloaded"], c["embedded"], c["verified"],
               c["accepted"], c["wines_with_3"]))
        key = "verified" if "4" in args.stages else "embedded"
        if c[key] >= args.total:
            log("all wines %s" % key)
            break
        progressed = False
        if "2" in args.stages and c["searched"] > c["downloaded"]:
            log("stage 2 download ...")
            run("02_download.py", "--limit", args.chunk, "--per-wine", args.per_wine,
                "--workers", args.dl_workers)
            progressed = True
        if "3" in args.stages and counts()["downloaded"] > counts()["embedded"]:
            log("stage 3 embed ...")
            run("03_embed.py", "--limit", args.chunk)
            progressed = True
        if "4" in args.stages and counts()["embedded"] > counts()["verified"]:
            log("stage 4 verify ...")
            run("04_verify.py", "--limit", args.chunk, "--top", args.top,
                "--backends", args.backends)
            progressed = True
        if not progressed:
            idle += 1
            if idle > 240:
                log("no progress for a long time, stopping")
                break
            time.sleep(30)
        else:
            idle = 0
        log("elapsed %.1f min" % ((time.time() - t0) / 60))
    log("driver finished in %.1f min" % ((time.time() - t0) / 60))


if __name__ == "__main__":
    main()
