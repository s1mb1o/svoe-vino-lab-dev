from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ADMIN_VALUES = {
    "BOT_ADMIN_WEB_USERNAME": "admin",
    "BOT_ADMIN_WEB_HOST": "0.0.0.0",
    "BOT_ADMIN_WEB_PORT": "8172",
    "BOT_ADMIN_WEB_ALLOWED_NETWORKS": "127.0.0.1/32,::1/128,192.168.86.0/24",
}


def update_environment(path: Path, password: str) -> None:
    if len(password) < 24 or "\n" in password or "\r" in password:
        raise ValueError("the administration password must contain at least 24 characters")
    existing = path.read_text(encoding="utf-8").splitlines()
    managed = {*ADMIN_VALUES, "BOT_ADMIN_WEB_PASSWORD"}
    kept = [line for line in existing if line.split("=", 1)[0] not in managed]
    values = {**ADMIN_VALUES, "BOT_ADMIN_WEB_PASSWORD": password}
    updated = [*kept, "", "# Private administration web interface"]
    updated.extend(f"{key}={value}" for key, value in values.items())
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        text=True,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as target:
            target.write("\n".join(updated).rstrip() + "\n")
            target.flush()
            os.fsync(target.fileno())
        temporary.chmod(0o600)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: configure_admin_env.py ENV_FILE")
    password = sys.stdin.read().strip()
    update_environment(Path(sys.argv[1]), password)


if __name__ == "__main__":
    main()
