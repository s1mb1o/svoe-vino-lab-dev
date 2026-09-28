#!/usr/bin/env python3
"""Copy the catalogue directory for the matcher: the database, the embeddings, the images.

The copy replaces the bundle build (plan 75, stage 2). Send it with
`rsync -a --delete <out>/ <host>:<path>/`; rsync sends the changed files alone.
"""

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import catalog_copy  # noqa: E402
import embeddings  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="new output directory")
    parser.add_argument("--embedding", action="append", default=[],
                        help="name in config.yaml embeddings; repeat it for more names. "
                             "Default: each embedding that has an index")
    parser.add_argument("--no-images", action="store_true",
                        help="do not copy images/ and cuts/; the matcher does not need them")
    parser.add_argument("--config", default=str(ROOT / "config.yaml"))
    args = parser.parse_args(argv)
    try:
        result = catalog_copy.copy_catalog(args.config, args.out, args.embedding,
                                           images=not args.no_images)
    except (catalog_copy.CopyError, embeddings.ConfigError, OSError, ValueError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
