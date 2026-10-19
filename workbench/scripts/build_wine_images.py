#!/usr/bin/env python3
"""Build one release of the static wine images of chtozavino.ru (plan 06 of the repository).

The release holds `1600/<slug>.webp`, `400/<slug>.webp`, `manifest.json`, and `SHA256SUMS`.
Check it with `check_wine_images.py --release` before you send it to the server.
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
    parser.add_argument("--db", required=True, help="the lab catalogue database")
    parser.add_argument("--out", required=True, help="new output directory")
    args = parser.parse_args(argv)
    try:
        result = wine_images.build(args.db, args.out)
    except (wine_images.ImageError, OSError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
