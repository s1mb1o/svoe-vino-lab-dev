#!/usr/bin/env python3
"""Build one standalone matcher bundle from a lab embedding index."""

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import matcher_bundle  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--embedding", required=True, help="name in config.yaml embeddings")
    parser.add_argument("--out", required=True, help="new output directory")
    parser.add_argument("--config", default=str(ROOT / "config.yaml"))
    parser.add_argument("--include-images", action="store_true",
                        help="copy the prepared catalogue images into the bundle")
    args = parser.parse_args(argv)
    try:
        result = matcher_bundle.build_bundle(
            args.config, args.embedding, args.out, include_images=args.include_images)
    except (matcher_bundle.BundleError, OSError, ValueError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

