#!/usr/bin/env python3
"""Validate a standalone matcher bundle without the lab database."""

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import matcher_bundle  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", help="bundle directory")
    args = parser.parse_args(argv)
    try:
        result = matcher_bundle.validate_bundle(args.bundle)
    except (matcher_bundle.BundleError, OSError, ValueError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

