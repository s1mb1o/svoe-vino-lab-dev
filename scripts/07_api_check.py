"""Stage 7. Ask the official Svoe Vino recognizer what it makes of each accepted photo.

Endpoint: POST https://api.vino-svoe.ru/v1/wines/search-by-photo
It is documented at https://api.vino-svoe.ru/docs and needs no token.

This is not ground truth. It is the baseline recognizer that the task asks to improve.
The value is recorded per photo so that the test set shows which photos the baseline
already handles and which ones it misses.
"""
import argparse, io, json, os, sys, threading, time, urllib.request, uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import db, log

ENDPOINT = "https://api.vino-svoe.ru/v1/wines/search-by-photo?limit=%d"


def post_image(path, limit, timeout=40):
    """Send one image as multipart/form-data. Returns the list of slugs."""
    with open(path, "rb") as fh:
        data = fh.read()
    boundary = "----testset%s" % uuid.uuid4().hex
    name = os.path.basename(path)
    body = io.BytesIO()
    body.write(("--%s\r\n" % boundary).encode())
    body.write(('Content-Disposition: form-data; name="image"; filename="%s"\r\n' % name).encode())
    body.write(b"Content-Type: application/octet-stream\r\n\r\n")
    body.write(data)
    body.write(("\r\n--%s--\r\n" % boundary).encode())
    req = urllib.request.Request(
        ENDPOINT % limit, data=body.getvalue(),
        headers={"Content-Type": "multipart/form-data; boundary=%s" % boundary,
                 "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        out = json.load(resp)
    if isinstance(out, dict):
        out = out.get("data") or out.get("items") or []
    return [r.get("slug") for r in out if isinstance(r, dict)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=5, help="top-N asked from the API")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--max", type=int, default=0, help="stop after this many photos")
    args = ap.parse_args()

    conn = db()
    try:
        conn.execute("ALTER TABLE candidates ADD COLUMN api_rank INTEGER")
        conn.commit()
    except Exception:  # noqa: BLE001
        pass

    rows = conn.execute(
        "SELECT id,slug,local_path FROM candidates"
        " WHERE vlm_same=1 AND vlm_studio=0 AND vlm_front=1 AND api_rank IS NULL"
        " AND local_path IS NOT NULL ORDER BY slug").fetchall()
    rows = [r for r in rows if os.path.exists(r[2])]
    if args.max:
        rows = rows[:args.max]
    log("photos to send to the official recognizer: %d" % len(rows))

    from concurrent.futures import ThreadPoolExecutor
    t0, n, lock = time.time(), [0], threading.Lock()
    pace = threading.Semaphore(args.workers)

    def run(r):
        cid, slug, path = r
        with pace:
            try:
                slugs = post_image(path, args.limit)
                rank = slugs.index(slug) + 1 if slug in slugs else 0
            except Exception:  # noqa: BLE001
                rank = -1
            time.sleep(0.2)
        with lock:
            n[0] += 1
            if n[0] % 100 == 0:
                el = time.time() - t0
                log("  %d/%d  %.2f s/photo  eta %.0f min"
                    % (n[0], len(rows), el / n[0], (len(rows) - n[0]) * el / n[0] / 60))
        return (rank, cid)

    with ThreadPoolExecutor(args.workers) as ex:
        out = list(ex.map(run, rows))
    conn.executemany("UPDATE candidates SET api_rank=? WHERE id=?", out)
    conn.commit()

    hit1 = sum(1 for r, _ in out if r == 1)
    hitn = sum(1 for r, _ in out if r and r > 0)
    err = sum(1 for r, _ in out if r == -1)
    log("official recognizer: top-1 %d/%d (%.0f%%), top-%d %d (%.0f%%), errors %d"
        % (hit1, len(out), hit1 / max(1, len(out)) * 100, args.limit,
           hitn, hitn / max(1, len(out)) * 100, err))


if __name__ == "__main__":
    main()
