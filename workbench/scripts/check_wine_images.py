#!/usr/bin/env python3
"""Check the static wine images against a catalogue database (plan 06 of the repository).

`--release` checks a release directory: the manifest, each file, and `SHA256SUMS`.
`--url` checks a published release: the manifest, a sample of the files, and HTTP 404 for
each wine with no image. The database can be the lab database or a matcher catalogue copy
with no image files. Exit code 1 means a difference; a deploy MUST stop.
"""

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import wine_images  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="the catalogue database")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--release", help="a release directory")
    target.add_argument("--url", help="the published release, for example "
                                      "https://chtozavino.ru/img/wines/")
    parser.add_argument("--sample", type=int, default=50,
                        help="the number of random files that --url downloads")
    parser.add_argument("--catalog-update", action="store_true",
                        help="a manifest wine that is not Active in the database is a "
                             "warning: use it before a catalogue update of the matcher")
    args = parser.parse_args(argv)
    if args.sample < 0:
        parser.error("--sample must not be negative")
    try:
        if args.release:
            errors, warnings = wine_images.check_release(args.db, args.release,
                                                         args.catalog_update)
        else:
            errors, warnings = wine_images.check_url(args.db, args.url, args.sample,
                                                     args.catalog_update)
    except (wine_images.ImageError, OSError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    for line in warnings:
        print("warning: %s" % line)
    for line in errors:
        print("difference: %s" % line)
    print(json.dumps({"ok": not errors, "differences": len(errors),
                      "warnings": len(warnings)}, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
