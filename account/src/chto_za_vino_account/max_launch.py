"""MAX mini-app launch data (initData) check.

Algorithm: https://dev.max.ru/docs/webapps/validation (wiki/raw/dev.max.ru/docs/webapps/
validation.md). The service gets the derived key HMAC_SHA256(key="WebAppData", msg=bot_token)
and never the bot token.

Freshness, single use of query_id, and the client address are checked by the caller, because
they need the database and the request.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
from dataclasses import dataclass
from urllib.parse import unquote


class LaunchInvalid(Exception):
    """The launch data is malformed or its signature does not match."""


@dataclass(frozen=True)
class Launch:
    user_id: str
    auth_date: int
    query_id: str
    ip: str | None
    first_name: str
    last_name: str


def derive_key(bot_token: str) -> bytes:
    """The operator runs this once to compute MAX_WEBAPP_KEY (as hex)."""
    return hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()


def sign(key: bytes, pairs: dict[str, str]) -> str:
    launch_params = "\n".join(f"{name}={pairs[name]}" for name in sorted(pairs))
    return hmac.new(key, launch_params.encode("utf-8"), hashlib.sha256).hexdigest()


def verify(init_data: str, key: bytes) -> Launch:
    pairs: dict[str, str] = {}
    for part in init_data.split("&"):
        name, separator, value = part.partition("=")
        if not separator or not name or name in pairs:
            raise LaunchInvalid("malformed launch data")
        try:
            pairs[name] = unquote(value, errors="strict")
        except UnicodeDecodeError:
            raise LaunchInvalid("malformed launch data encoding") from None
    supplied = pairs.pop("hash", "")
    if not supplied:
        raise LaunchInvalid("launch data has no hash")
    if not hmac.compare_digest(sign(key, pairs).encode(), supplied.lower().encode()):
        raise LaunchInvalid("launch data signature mismatch")
    try:
        user = json.loads(pairs["user"])
        user_id = user["id"]
        auth_date = int(pairs["auth_date"])
        query_id = pairs["query_id"]
    except (KeyError, ValueError, TypeError) as error:
        raise LaunchInvalid("launch data misses user, auth_date, or query_id") from error
    if not isinstance(user_id, int) or isinstance(user_id, bool) or user_id <= 0:
        raise LaunchInvalid("launch data has no valid user id")
    if not query_id or len(query_id) > 128:
        raise LaunchInvalid("launch data has no valid query_id")
    ip = pairs.get("ip") or None
    if ip is not None:
        try:
            ip = str(ipaddress.ip_address(ip))
        except ValueError as error:
            raise LaunchInvalid("launch data has an invalid ip") from error
    return Launch(
        user_id=str(user_id),
        auth_date=auth_date,
        query_id=query_id,
        ip=ip,
        first_name=str(user.get("first_name") or "")[:64],
        last_name=str(user.get("last_name") or "")[:64],
    )
