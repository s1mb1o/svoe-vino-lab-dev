"""Build an embedding index or serve the API with public YAML settings."""
import argparse
import json
from pathlib import Path

from .configuration import asset_path, load_config
from .data import Knowledge
from .embeddings import build_index


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, help="Public YAML configuration file")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("build-index")
    commands.add_parser("serve")
    args = parser.parse_args()
    config, path = load_config(args.config)
    if args.command == "build-index":
        knowledge = Knowledge(asset_path(config.assets.dataset, path), asset_path(config.assets.style, path))
        manifest = build_index(knowledge, asset_path(config.assets.index, path), settings=config.embeddings)
        print(json.dumps({"model": manifest["model"], "wines": manifest["wine_documents"],
                          "queries": manifest["query_documents"], "dimensions": manifest["dimensions"]}))
    else:
        import os
        import uvicorn
        # Workers import the factory independently. This variable selects the YAML only.
        os.environ["DINNER_LENS_CONFIG"] = str(path)
        uvicorn.run("dinner_lens.api:app_from_environment", factory=True,
                    host=config.server.host, port=config.server.port, workers=config.server.workers,
                    log_level=config.server.log_level, access_log=config.server.access_log)


if __name__ == "__main__":
    main()
