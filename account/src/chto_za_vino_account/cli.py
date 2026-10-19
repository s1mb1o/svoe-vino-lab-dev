"""Command line entry points.

  chto-za-vino-account            run the service
  chto-za-vino-account max-key    read the MAX bot token from stdin and print MAX_WEBAPP_KEY
"""

from __future__ import annotations

import logging
import sys

import uvicorn

from .api import create_app
from .config import Settings
from .max_launch import derive_key


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args == ["max-key"]:
        token = sys.stdin.readline().strip()
        if not token:
            print("Send the MAX bot token on stdin", file=sys.stderr)
            return 2
        print(derive_key(token).hex())
        return 0
    if args:
        print(__doc__, file=sys.stderr)
        return 2
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    settings = Settings.from_env()
    uvicorn.run(
        create_app(settings),
        host=settings.host,
        port=settings.port,
        access_log=False,
        proxy_headers=False,
        server_header=False,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
