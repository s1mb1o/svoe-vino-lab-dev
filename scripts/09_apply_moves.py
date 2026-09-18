#!/usr/bin/env python3
"""Stage 9. Move and copy the photos that the review tool marked for another wine.

The review tool does not touch a file. A move is recorded in `review-labels.json`
as the field `reassign_to` of the photo entry, and a copy as the field `copy_to`.
This script performs both. The button `apply` in the page of the review tool does
the same work through `POST /api/apply-moves`, and both use the same functions of
`review_server.py`.

A moved photo loses its label, because the label judged the old pair and the
photo MUST be reviewed again against the new wine. The comment is kept and gets
one line in front of it that states where the photo was.

A copy leaves the source photo where it is, with its label and its comment. The
copy is a new candidate photo of the target wine. It carries no label and one
comment that names the wine it came from.

The copies run before the moves, because a move takes the source file away.

The script is safe to run twice. A move that is already done is reported as done
and is not repeated. A copy that is done no longer holds `copy_to`.
The default run only reports; `--apply` performs the work.

Run:
    python3 scripts/09_apply_moves.py            # report only
    python3 scripts/09_apply_moves.py --apply    # move and copy the files
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
    ap = argparse.ArgumentParser(
        description="Apply the recorded photo moves and photo copies")
    ap.add_argument("--apply", action="store_true", help="move and copy the files")
    args = ap.parse_args()

    srv = load_server()
    if not os.path.exists(srv.LABEL_FILE):
        sys.exit(f"error: no label file: {srv.LABEL_FILE}")
    srv._state = srv.load_state()
    labels = srv._state["labels"]

    cp_planned, cp_bad = srv.plan_copies(labels)
    print(f"copies recorded: {len(cp_planned) + len(cp_bad)}")
    print(f"  to perform   : {len(cp_planned)}")
    print(f"  cannot do    : {len(cp_bad)}")
    for slug, fn, to, why in cp_bad:
        print(f"    ! {slug}/{fn} => {to}: {why}")
    for slug, fn, to, _src, _dst in cp_planned:
        print(f"    {slug}/{fn} => {to}/")

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
        print("\nreport only. Add --apply to move and copy the files.")
        return
    if not planned and not cp_planned:
        print("\nnothing to move and nothing to copy.")
        return

    # The copies run first: a move takes the source file away.
    copied, cp_renamed = srv.perform_copies(cp_planned, labels)
    moved, renamed = srv.perform_moves(planned, labels)
    srv.save_state()
    for old, new in cp_renamed + renamed:
        print(f"    renamed on arrival: {old} -> {new}")
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    print(f"\ncopied {len(copied)} file(s) and moved {len(moved)} file(s) at {stamp}")
    print("Each copy carries no label and MUST be reviewed against its new wine.")
    print("Its comment states the wine it came from. The source photo did not change.")
    print("Each moved photo lost its label and MUST be reviewed again.")
    print("Its comment was kept and states where the photo was.")
    print("Restart the review tool, or press `reload` in the page, to rebuild the rows.")


if __name__ == "__main__":
    main()
