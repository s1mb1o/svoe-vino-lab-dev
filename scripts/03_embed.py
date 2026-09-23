"""Stage 3. Score every downloaded candidate against the catalogue reference photo.

Two values are written per candidate:
  sim      cosine similarity of SigLIP2 embeddings against the reference image
  bg_white fraction of border pixels that are near white, a cheap studio-cutout signal

The reference is the picture that the review tool shows: the cropped catalogue
photo, then the patch, then `ref_path` of the database. `common.catalogue_picture`
states the rule. The stage scores only the candidates that have no `sim` yet, so
a score that an earlier run wrote against an older reference stays as it is.
"""
import argparse, io, math, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402
from common import EMBED_MODEL, WORK, data_url, db, log, post_json

REF_CACHE = os.path.join(WORK, "ref_emb.npy")
REF_INDEX = os.path.join(WORK, "ref_emb.index")
# slug -> cropped catalogue photo, and slug -> corrected catalogue photo.
CROPS = common.load_cropped_bottles()
PATCHES = common.load_patches()


def embed_batch(paths, maxside=384):
    urls = [data_url(p, maxside=maxside) for p in paths]
    r = post_json("/v1/embeddings", {"model": EMBED_MODEL, "input": urls})
    return [d["embedding"] for d in r["data"]]


def bg_white(path):
    """Fraction of border pixels close to white. A catalogue cutout scores near 1."""
    from PIL import Image
    import numpy as np
    try:
        im = Image.open(path)
        if im.mode in ("RGBA", "LA"):
            alpha = np.asarray(im.convert("RGBA"))[:, :, 3]
            if (alpha < 16).mean() > 0.2:
                return 1.0
        im = im.convert("RGB")
        im.thumbnail((160, 160))
        a = np.asarray(im).astype(np.float32)
    except Exception:  # noqa: BLE001
        return -1.0
    h, w = a.shape[:2]
    k = max(2, min(h, w) // 12)
    border = np.concatenate([a[:k].reshape(-1, 3), a[-k:].reshape(-1, 3),
                             a[:, :k].reshape(-1, 3), a[:, -k:].reshape(-1, 3)])
    spread = border.max(axis=1) - border.min(axis=1)
    near = (border.min(axis=1) > 228) & (spread < 22)
    return float(near.mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--limit", type=int, default=0, help="number of wines")
    ap.add_argument("--maxside", type=int, default=384)
    args = ap.parse_args()

    import numpy as np
    conn = db()
    wines = [dict(zip(("slug", "ref_path"), r)) for r in conn.execute(
        "SELECT slug,ref_path FROM wines WHERE downloaded=1 AND embedded=0 ORDER BY slug")]
    if args.limit:
        wines = wines[:args.limit]
    log("wines to embed: %d" % len(wines))

    t0, n_img = time.time(), 0
    for i, w in enumerate(wines, 1):
        rows = conn.execute(
            "SELECT id,local_path FROM candidates WHERE slug=? AND dl_status='ok' AND sim IS NULL",
            (w["slug"],)).fetchall()
        present = [(cid, p) for cid, p in rows if p and os.path.exists(p)]
        ref_path = common.catalogue_picture(
            w["slug"], {"local_path": w["ref_path"]}, CROPS, PATCHES)
        if not os.path.exists(ref_path or ""):
            # A missing reference is a storage problem. Leave the wine open.
            log("skip %s: reference photo missing" % w["slug"])
            continue
        if len(present) < len(rows):
            log("skip %s: %d of %d candidate files missing"
                % (w["slug"], len(rows) - len(present), len(rows)))
            continue
        rows = present
        if not rows:
            conn.execute("UPDATE wines SET embedded=1 WHERE slug=?", (w["slug"],))
            conn.commit()
            continue
        try:
            ref = np.array(embed_batch([ref_path], args.maxside)[0], dtype=np.float32)
        except Exception as exc:  # noqa: BLE001
            log("ref embed failed", w["slug"], type(exc).__name__)
            continue
        ref /= (np.linalg.norm(ref) + 1e-9)
        updates = []
        failed = False
        for s2 in range(0, len(rows), args.batch):
            chunk = rows[s2:s2 + args.batch]
            try:
                embs = embed_batch([p for _, p in chunk], args.maxside)
            except Exception as exc:  # noqa: BLE001
                log("batch failed", w["slug"], type(exc).__name__, str(exc)[:80])
                failed = True
                continue
            for (cid, path), e in zip(chunk, embs):
                v = np.array(e, dtype=np.float32)
                v /= (np.linalg.norm(v) + 1e-9)
                updates.append((float(ref @ v), bg_white(path), cid))
            n_img += len(chunk)
        if updates:
            conn.executemany("UPDATE candidates SET sim=?,bg_white=? WHERE id=?", updates)
        if not failed:
            conn.execute("UPDATE wines SET embedded=1 WHERE slug=?", (w["slug"],))
        conn.commit()
        if i % 25 == 0 or i == len(wines):
            el = time.time() - t0
            log("%d/%d wines  %d images  %.0f img/s  eta %.0f min"
                % (i, len(wines), n_img, n_img / el if el else 0,
                   (len(wines) - i) / (i / el) / 60 if el else 0))
    log("stage 3 done in %.1f min" % ((time.time() - t0) / 60))


if __name__ == "__main__":
    main()
