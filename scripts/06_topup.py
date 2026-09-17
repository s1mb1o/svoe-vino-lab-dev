"""Top-up pass. Gives a second chance to every wine that has fewer than 3 accepted photos.

It reopens those wines so that stage 2 downloads deeper candidates, stage 3 scores them,
and stage 4 verifies them. Candidates that failed with a transport error are retried too,
because their verdict was never recorded.
"""
import argparse, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import db, log

SHORT = """SELECT slug FROM wines WHERE (
    SELECT COUNT(*) FROM candidates c
    WHERE c.slug = wines.slug AND c.vlm_same = 1 AND c.vlm_studio = 0 AND c.vlm_front = 1
  ) < ?"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--need", type=int, default=3, help="target photos per wine")
    ap.add_argument("--redownload", action="store_true",
                    help="also reopen stage 2 so deeper candidates are fetched")
    args = ap.parse_args()

    conn = db()
    short = [r[0] for r in conn.execute(SHORT, (args.need,))]
    log("wines below the target of %d photos: %d" % (args.need, len(short)))

    # Transport errors left no verdict. Clear them so stage 4 asks again.
    n_err = conn.execute(
        "UPDATE candidates SET vlm_raw=NULL WHERE vlm_same IS NULL AND vlm_raw LIKE 'ERR:%'").rowcount
    log("cleared %d failed verification attempts" % n_err)

    q = ",".join("?" * len(short))
    if short:
        conn.execute("UPDATE wines SET verified=0 WHERE slug IN (%s)" % q, short)
        if args.redownload:
            # Reopen the download and embedding stages for these wines.
            conn.execute("UPDATE wines SET downloaded=0, embedded=0 WHERE slug IN (%s)" % q, short)
            n_retry = conn.execute(
                "UPDATE candidates SET dl_status=NULL WHERE dl_status='retry' AND slug IN (%s)" % q,
                short).rowcount
            log("reopened stage 2 and freed %d retryable candidates" % n_retry)
    conn.commit()
    log("reopened %d wines. Run the drivers again with a larger --top and --per-wine." % len(short))


if __name__ == "__main__":
    main()
