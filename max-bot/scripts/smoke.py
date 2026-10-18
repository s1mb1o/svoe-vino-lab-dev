"""Check a running MAX bot. Credentials come from the environment or a protected file.

The check creates one invalid request and one optional recognition request.
It never polls MAX updates or sends a MAX message.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from chto_za_vino_max_bot.max_api import create_ssl_context
from chto_za_vino_max_bot.profile import COMMANDS

FIXTURE = Path(__file__).resolve().parents[1] / "tests/data/smoke-wine.webp"
EXPECTED_SLUG = "massandra-muskatel-belyy-belye-sorta-vinograda-beloe-sladkoe-16"


def load_environment(path: Path | None) -> dict[str, str]:
    values = dict(os.environ)
    if path is not None:
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            name, separator, value = line.partition("=")
            if not separator:
                raise ValueError("Invalid environment file")
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            values[name.strip()] = value
    return values


def require(condition: bool, label: str) -> None:
    if not condition:
        raise RuntimeError(label)
    print(f"PASS {label}")


def run(args: argparse.Namespace) -> None:
    values = load_environment(args.env_file)
    token = values.get("BOT_HTTP_API_TOKEN", "")
    require(len(token) >= 32, "API credential is configured")
    headers = {"Authorization": f"Bearer {token}"}
    result = None
    with httpx.Client(base_url=args.api_url, timeout=180, trust_env=False) as client:
        response = client.get("/healthz")
        require(response.status_code == 200 and response.text == "ok", "API liveness")
        response = client.get("/readyz")
        readiness = response.json()
        checks = readiness.get("checks", {})
        require(
            response.status_code == 200 and readiness.get("ready") is True
            and {"database", "queue", "moderation", "sam3", "matcher"} <= checks.keys()
            and all(value is True for value in checks.values()),
            "database, queue, and upstream readiness",
        )
        require(client.post("/api/v1/recognize").status_code == 401, "missing bearer rejected")
        require(
            client.post("/api/v1/recognize", headers={"Authorization": "Bearer wrong"})
            .status_code == 401,
            "wrong bearer rejected",
        )
        response = client.post(
            "/api/v1/recognize", headers=headers,
            files={"image": ("invalid.jpg", b"invalid-image", "image/jpeg")},
        )
        require(
            response.status_code == 422 and response.json().get("status") == "invalid_image",
            "invalid image rejected",
        )
        if not args.no_recognition:
            response = client.post(
                "/api/v1/recognize", headers=headers,
                files={"image": ("smoke-wine.webp", FIXTURE.read_bytes(), "image/webp")},
            )
            require(response.status_code == 200, "live recognition HTTP response")
            result = response.json()
            moderation = result["moderation"]
            require(
                moderation.get("safe") is True and moderation.get("performed") is True,
                "live moderation accepted the fixture",
            )
            recognition = result["recognition"]
            candidates = recognition["candidates"]
            require(
                result["source"] == "api" and result["status"] in {"recognized", "abstained"}
                and recognition["confident"] == (result["status"] == "recognized")
                and 1 <= len(candidates) <= 4
                and candidates[0]["slug"] == EXPECTED_SLUG
                and recognition["wine"]["slug"] == EXPECTED_SLUG,
                "expected Top-1 wine and accurate confidence state",
            )
            require(
                all(item["rank"] == rank for rank, item in enumerate(candidates, 1))
                and all(
                    urlsplit(item["wine"]["page_url"]).hostname in
                    {"vino-svoe.ru", "www.vino-svoe.ru"} for item in candidates
                ),
                "ranked candidates and catalogue links",
            )
            timings = {item["step"] for item in result["timings"] if item["outcome"] == "ok"}
            require(
                {"image_prepare", "moderation", "quality", "recognition", "candidate_storage"}
                <= timings,
                "pipeline step timings",
            )
            print(json.dumps({
                "request_id": result["request_id"], "status": result["status"],
                "slug": candidates[0]["slug"], "duration_ms": result["duration_ms"],
            }))
    if args.admin_url:
        auth = (values.get("BOT_ADMIN_WEB_USERNAME", "admin"),
                values.get("BOT_ADMIN_WEB_PASSWORD", ""))
        require(len(auth[1]) >= 32, "administration credential is configured")
        with httpx.Client(base_url=args.admin_url, timeout=10, trust_env=False) as client:
            require(client.get("/readyz").status_code == 200, "administration readiness")
            require(client.get("/").status_code == 401, "administration requires authentication")
            require(
                client.get("/", auth=(auth[0], "wrong")).status_code == 401,
                "wrong administration password rejected",
            )
            response = client.get("/", auth=auth)
            require(
                response.status_code == 200 and "prefers-color-scheme" in response.text
                and "content-security-policy" in response.headers,
                "administration authentication, dark theme, and security headers",
            )
            for route in ("/users", "/requests", "/appeals"):
                require(client.get(route, auth=auth).status_code == 200, f"administration {route}")
            if result:
                route = f"/requests/{result['request_id']}"
                require(client.get(route, auth=auth).status_code == 200, "request inspector")
                require(
                    client.post(
                        f"{route}/retry", auth=auth, content="",
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                    ).status_code == 403,
                    "administration retry requires CSRF token",
                )
    if args.check_max:
        max_token = values.get("MAX_BOT_TOKEN", "")
        require(bool(max_token), "MAX credential is configured")
        with httpx.Client(
            base_url=values.get("MAX_API_BASE_URL", "https://platform-api2.max.ru"),
            headers={"Authorization": max_token}, verify=create_ssl_context(), timeout=30,
        ) as client:
            response = client.get("/me")
            require(
                response.status_code == 200 and response.json().get("user_id") == 520798340,
                "live MAX identity and trusted TLS",
            )
            require(
                response.json().get("commands") == COMMANDS,
                "live MAX command menu",
            )
            response = client.get("/subscriptions")
            require(
                response.status_code == 200 and response.json().get("subscriptions") == [],
                "no active MAX webhook",
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--api-url", default="http://127.0.0.1:28004")
    parser.add_argument("--admin-url")
    parser.add_argument("--no-recognition", action="store_true")
    parser.add_argument("--check-max", action="store_true")
    arguments = parser.parse_args()
    try:
        run(arguments)
    except (RuntimeError, ValueError, KeyError, OSError, httpx.HTTPError) as exc:
        # HTTP error text can contain an attachment URL. Print the exception type only.
        print(f"FAIL {exc if type(exc) is RuntimeError else type(exc).__name__}")
        raise SystemExit(1) from None
