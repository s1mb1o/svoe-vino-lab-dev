#!/usr/bin/env python3
"""Stage 9. Move the photos that the review tool marked for another wine slug.

The review tool does not move a file. A move is recorded in `review-labels.json`
as the field `reassign_to` of the photo entry. This script performs the moves.
The button `apply` in the page of the review tool does the same work through
`POST /api/apply-moves`, and both use the same functions of `review_server.py`.

A moved photo loses its label, because the label judged the old pair and the
photo MUST be reviewed again against the new wine. The comment is kept and gets
one line in front of it that states where the photo was.

The script is safe to run twice. A move that is already done is reported as done
and is not repeated. The default run only reports; `--apply` performs the moves.

Run:
    python3 scripts/09_apply_moves.py            # report only
    python3 scripts/09_apply_moves.py --apply    # move the files
"""
import argparse
import importlib.util
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def load_server():
    """Import `review_server.py` as a module, without starting the server."""
    spec = importlib.util.spec_from_file_location(
        "review_server", os.path.join(HERE, "review_server.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser(description="Apply the recorded photo moves")
    ap.add_argument("--apply", action="store_true", help="move the files")
    args = ap.parse_args()

    srv = load_server()
    if not os.path.exists(srv.LABEL_FILE):
        sys.exit(f"error: no label file: {srv.LABEL_FILE}")
    srv._state = srv.load_state()
    labels = srv._state["labels"]

    planned, done, bad = srv.plan_moves(labels)
    print(f"moves recorded : {len(planned) + len(done) + len(bad)}")
    print(f"  to perform   : {len(planned)}")
    print(f"  already done : {len(done)}")
    print(f"  cannot do    : {len(bad)}")
    for slug, fn, to, why in bad:
        print(f"    ! {slug}/{fn} -> {to}: {why}")
    for slug, fn, to, _src, _dst in planned:
        print(f"    {slug}/{fn} -> {to}/")

    if not args.apply:
        print("\nreport only. Add --apply to move the files.")
        return
    if not planned:
        print("\nnothing to move.")
        return

    moved, renamed = srv.perform_moves(planned, labels)
    srv.save_state()
    for old, new in renamed:
        print(f"    renamed on arrival: {old} -> {new}")
    print(f"\nmoved {len(moved)} file(s) at {time.strftime('%Y-%m-%dT%H:%M:%S%z')}")
    print("Each moved photo lost its label and MUST be reviewed again.")
    print("Its comment was kept and states where the photo was.")
    print("Restart the review tool, or press `reload` in the page, to rebuild the rows.")


if __name__ == "__main__":
    main()
