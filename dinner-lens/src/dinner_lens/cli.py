"""Build a real embedding artifact or serve the complete authenticated API."""
import argparse
import json
from pathlib import Path

from .data import Knowledge
from .embeddings import build_index
from .paths import bundle_root, default_dataset, default_index, default_style


def main():
    root = bundle_root()
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build-index")
    build.add_argument("--dataset", default=str(default_dataset()))
    build.add_argument("--index", default=str(default_index()))
    build.add_argument("--workers", type=int, default=4)
    serve = commands.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8176)
    args = parser.parse_args()
    if args.command == "build-index":
        k = Knowledge(args.dataset, default_style())
        manifest = build_index(k, args.index, args.workers)
        print(json.dumps({"model": manifest["model"], "wines": manifest["wine_documents"],
                          "queries": manifest["query_documents"], "dimensions": manifest["dimensions"]}))
    else:
        import uvicorn
        uvicorn.run("dinner_lens.api:app_from_environment", factory=True, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
