"""Make the label cut of each full original of the lab database.

Usage:
    python3 pipeline/seed_label_cuts.py --db data/lab.sqlite3 [--limit N]

A full original is a file of `wine_image` of the type `main`, `main_patched`,
`full_front`, or `full_back`. Its label cut is the row of `image_derivative` of the kind
`label`, next to the row of the kind `package`. The view `label` of the Embeddings page
starts with this cut. Read docs/plans/22_label-cut.md.

Rules:
- The label rule is the rule of an alternative label photo: SAM3 with the nouns
  `alternatives.DETECT_TEXTS`, then `alternatives.label_instance` (the rule of
  `build_labels.py`). `alternatives.label_derivatives` writes the file and gives the rows.
- An original whose label cut has the present settings (`alternatives.SETTINGS_LABEL`)
  gets no request. So a second run continues the first one.
- SAM3 runs outside the write transaction. Each original gets its own short transaction,
  so a stop keeps the finished cuts.
- An original with no label in the SAM3 answer gets no row. The next run asks again.
- The run stops at the first time that SAM3 does not answer.

Exit status: 0 when each original has its label cut or no label. 1 when the run cannot
start, when SAM3 does not answer, or when a file gave an error.
"""
import argparse
import os
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alternatives  # noqa: E402
import derive  # noqa: E402
import labdb  # noqa: E402

FULL_TYPES = ("main", "main_patched", "full_front", "full_back")
PROGRESS_EVERY = 50


class Report:
    def __init__(self):
        self.originals = 0    # full originals in the database
        self.present = 0      # originals with a label cut of the present settings
        self.written = 0      # label cuts written in this run
        self.no_label = []    # sha256 of originals with no label in the SAM3 answer
        self.unreadable = []  # sha256 of originals that Pillow cannot read
        self.errors = 0       # store errors
        self.unavailable = None  # the message of SAM3 when it did not answer
        self.seconds = 0.0


def full_originals(conn, db_path):
    """Return [(sha256, path)] of the full originals, in the order of their sha256."""
    rows = conn.execute(
        "SELECT DISTINCT i.sha256, i.folder, i.extension FROM wine_image wi "
        "JOIN image i ON i.sha256 = wi.sha256 WHERE wi.image_type IN (%s) "
        "ORDER BY i.sha256" % ", ".join("?" for _ in FULL_TYPES), FULL_TYPES)
    return [(digest, alternatives.file_path(db_path, folder, digest, extension))
            for digest, folder, extension in rows]


def seed_label_cuts(db_path, log=print, segmenter=None, limit=None):
    """Make the missing label cuts. Return a `Report`. `segmenter` is the SAM3 client;
    None means `derive.SAM3_ENDPOINT`. `limit` is the most originals to ask SAM3 for."""
    segmenter = segmenter or derive.Sam3Client()
    report = Report()
    start = time.time()
    conn = labdb.connect(db_path)
    conn.isolation_level = None
    try:
        originals = full_originals(conn, db_path)
        report.originals = len(originals)
        present = {row[0] for row in conn.execute(
            "SELECT source_sha256 FROM image_derivative WHERE kind = 'label' AND "
            "settings = ?", (alternatives.SETTINGS_LABEL,))}
        todo = [(digest, path) for digest, path in originals if digest not in present]
        report.present = len(originals) - len(todo)
        if limit is not None:
            todo = todo[:limit]
        log("full originals: %d; with a label cut: %d; to do: %d"
            % (report.originals, report.present, len(todo)))
        for number, (digest, path) in enumerate(todo, 1):
            try:
                image, icc_profile = derive.open_image(path)
            except OSError as exc:
                report.unreadable.append(digest)
                log("unreadable: %s: %s" % (path, exc))
                continue
            try:
                instances, _scale = segmenter.instances(image, alternatives.DETECT_TEXTS)
            except derive.Sam3Unavailable as exc:
                report.unavailable = str(exc)
                log("stop: SAM3 does not answer: %s" % exc)
                break
            messages = []
            out = alternatives.label_derivatives(conn, db_path, digest, image, icc_profile,
                                                 instances, messages.append)
            if out.links:
                conn.execute("BEGIN IMMEDIATE")
                try:
                    derive.write_rows(conn, out)
                    conn.execute("COMMIT")
                except BaseException:
                    conn.execute("ROLLBACK")
                    raise
                report.written += 1
            elif out.present:
                report.present += 1
            elif out.errors:
                report.errors += out.errors
                log("error: %s: %s" % (digest, "; ".join(messages)))
            else:
                report.no_label.append(digest)
                log("no label: %s" % digest)
            if number % PROGRESS_EVERY == 0 or number == len(todo):
                elapsed = time.time() - start
                log("progress: %d/%d · written %d · no label %d · %.2f s each"
                    % (number, len(todo), report.written, len(report.no_label),
                       elapsed / number))
    finally:
        conn.close()
    report.seconds = time.time() - start
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Make the label cut (image_derivative, kind label) of each full "
                    "original of the lab database.")
    parser.add_argument("--db", required=True, help="path of the lab database")
    parser.add_argument("--sam3", default=derive.SAM3_ENDPOINT,
                        help="the SAM3 service (default: %(default)s)")
    parser.add_argument("--limit", type=int, default=None,
                        help="ask SAM3 for at most this number of originals")
    args = parser.parse_args(argv)

    def log(message):
        print(message, flush=True)

    try:
        report = seed_label_cuts(args.db, log, derive.Sam3Client(args.sam3), args.limit)
    except (labdb.SchemaError, sqlite3.Error, OSError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    print("full originals: %d" % report.originals)
    print("label cuts present: %d" % report.present)
    print("label cuts written: %d" % report.written)
    print("no label: %d" % len(report.no_label))
    print("unreadable: %d" % len(report.unreadable))
    print("errors: %d" % report.errors)
    print("seconds: %.0f" % report.seconds)
    if report.unavailable:
        print("result: stopped; SAM3 does not answer: %s" % report.unavailable)
        return 1
    if report.errors or report.unreadable:
        print("result: errors")
        return 1
    print("result: done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
