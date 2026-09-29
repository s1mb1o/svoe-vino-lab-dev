#!/usr/bin/env python3
"""Create one manual wine and activate it in the configured embedding index."""
import argparse
import base64
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

import lab_server  # noqa: E402
import manual_wines  # noqa: E402
import new_wine_workflow  # noqa: E402


def parser():
    value = argparse.ArgumentParser(
        description="Create one manual wine and update its embedding index.")
    value.add_argument("--slug", required=True, help="manual slug, with or without __")
    value.add_argument("--name", required=True)
    value.add_argument("--producer", required=True)
    value.add_argument("--beverage-type", choices=("4", "44"), default=None,
                       help="wine category: 4 is wine, 44 is sparkling wine")
    value.add_argument("--category", required=True)
    value.add_argument("--color", required=True)
    value.add_argument("--region", required=True)
    value.add_argument("--grapes", default="")
    value.add_argument("--description", default="")
    value.add_argument("--image", required=True, help="JPEG, PNG, or WebP file")
    value.add_argument("--config", default=lab_server.CONFIG_PATH)
    value.add_argument("--embedding", default=None,
                       help="replace new_wine_embedding for this operation")
    return value


def main(argv=None):
    args = parser().parse_args(argv)
    slug = args.slug if args.slug.startswith(manual_wines.MANUAL_PREFIX) \
        else manual_wines.MANUAL_PREFIX + args.slug
    try:
        image = Path(args.image).read_bytes()
        _config, db_path = lab_server.read_config(args.config)
        body = {
            "slug": slug,
            "name": args.name,
            "producer": args.producer,
            "beverage_type_code": args.beverage_type,
            "category": args.category,
            "color": args.color,
            "region": args.region,
            "grapes": args.grapes,
            "description": args.description,
            "image_name": os.path.basename(args.image),
            "image": base64.b64encode(image).decode("ascii"),
        }
        result = lab_server.add_wine(db_path, body, config_path=args.config,
                                     embedding=args.embedding)
    except (OSError, lab_server.ConfigError, manual_wines.WineError,
            new_wine_workflow.WorkflowError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0 if not result.get("index") or result["index"]["state"] == "active" else 1


if __name__ == "__main__":
    sys.exit(main())
