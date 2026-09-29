"""The command line of the model proxy.

Usage, in the project directory:
    .venv/bin/python -m model_proxy [--config config.yaml] [--verbose]
    .venv/bin/python -m model_proxy --check
    .venv/bin/python -m model_proxy --purge
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

import uvicorn

from .app import create_app
from .cache import CacheStore
from .config import ConfigError, ProxyConfig, load


DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "config.yaml"


def describe(config: ProxyConfig) -> str:
    lines = [
        f"listen: {config.listen_host}:{config.listen_port}",
        f"passthrough: {config.passthrough}",
        f"cache: {config.cache_path} (namespace {config.namespace})",
        f"pooled models: {', '.join(sorted(config.pooled_models))}",
    ]
    for host in config.hosts:
        state = "enabled" if host.enabled else "disabled"
        route = f"ssh {host.ssh.target} -> {host.url}" if host.ssh else host.url
        lines.append(f"host {host.name}: {state}, {host.kind}, {route}, {host.slots} slots, "
                     f"models {', '.join(host.models)}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="model_proxy", description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG,
                        help="the configuration file (default: %(default)s)")
    parser.add_argument("--check", action="store_true",
                        help="check the configuration, print the hosts, and exit")
    parser.add_argument("--purge", action="store_true",
                        help="delete each cache entry and exit; stop the proxy first")
    parser.add_argument("--verbose", action="store_true",
                        help="log one line for each pooled request")
    args = parser.parse_args(argv)
    try:
        config = load(args.config)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.check:
        print(describe(config))
        return 0
    if args.purge:
        store = CacheStore(config.cache_path, ttl_seconds=config.ttl_seconds,
                           max_bytes=config.max_cache_bytes)
        try:
            print(f"purged {store.purge()} cache entries from {config.cache_path}")
        finally:
            store.close()
        return 0
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # httpx logs each request at INFO: each probe and each forwarded request.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    uvicorn.run(
        create_app(config, verbose=args.verbose),
        host=config.listen_host,
        port=config.listen_port,
        log_level="info",
        access_log=False,
        proxy_headers=False,
        server_header=False,
        date_header=False,
        timeout_graceful_shutdown=10,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
