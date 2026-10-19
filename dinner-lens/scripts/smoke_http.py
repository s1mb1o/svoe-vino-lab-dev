#!/usr/bin/env python3
"""Real loopback HTTP smoke test; run with a clean wheel installation's Python."""
import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

from dinner_lens.paths import bundle_root


def run(args):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = dict(os.environ)
    env.update(DINNER_LENS_API_TOKEN=secrets.token_urlsafe(32), DINNER_LENS_CURSOR_SECRET=secrets.token_urlsafe(48),
               DINNER_LENS_INDEX=str(args.index.resolve()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    checks = []

    def request(path, payload=None, auth=True):
        headers = {"Content-Type": "application/json"}
        if auth:
            headers["Authorization"] = "Bearer " + env["DINNER_LENS_API_TOKEN"]
        req = urllib.request.Request(f"http://127.0.0.1:{port}" + path,
                                     data=json.dumps(payload).encode() if payload is not None else None, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as exc:
            return exc.code, json.load(exc)

    def check(name, passed):
        checks.append({"name": name, "passed": bool(passed)})

    with args.output.with_suffix(".server.log").open("w") as log:
        process = subprocess.Popen([sys.executable, "-m", "dinner_lens.cli", "serve", "--port", str(port)],
                                   env=env, cwd="/tmp", stdout=log, stderr=log)
        try:
            for _ in range(150):
                try:
                    status, health = request("/health", auth=False)
                    break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError("Server did not start")
            check("installed-wheel-health", status == 200 and health["catalog_wines"] == 2093)
            status, expanded = request("/v1/recommendations", {"confirmed_dish": "Хумус с тахини"})
            check("installed-expanded-dataset", status == 200 and expanded["resolved_node_id"] == "hummus_tahini" and len(expanded["results"]) == 3)
            status, ambiguous = request("/v1/recommendations", {"confirmed_dish": "роллы"})
            check("ambiguous-rolls-stay-general", status == 200 and ambiguous["resolved_node_id"] == "sushi_rolls" and ambiguous["needs_clarification"] and bool(ambiguous["clarification_question"]))
            check("missing-auth", request("/v1/recommendations", {"node_id": "meat"}, False)[0] == 401)
            status, first = request("/v1/recommendations", {"confirmed_dish": "Стейк рибай на гриле"})
            check("curated-initial-page", status == 200 and len(first["results"]) == 3 and all(r["selection_source"] == "curated" for r in first["results"]))
            status, more = request("/v1/recommendations/more", {"cursor": first["next_cursor"]})
            check("signed-continuation", status == 200 and not set(first["wine_slugs"]) & set(more["wine_slugs"]) and more["resolved_node_id"] == "ribeye_grilled")
            status, empty = request("/v1/recommendations", {"node_id": "ribeye_grilled", "user_constraints": {"max_price_rub": 1000}})
            check("unknown-price-fails-closed", status == 200 and empty["wine_slugs"] == [])
            check("invalid-photo", request("/v1/recognize-and-recommend", {"image_base64": "aW52YWxpZA=="})[0] == 422)
            check("huge-integer-limit", request("/v1/recommendations", {"node_id": "meat", "user_constraints": {"max_price_rub": 10 ** 400}})[0] == 422)
            check("unknown-food-invalid-attribute", request("/v1/recommendations", {"confirmed_dish": "неизвестное блюдо", "confirmed_attributes": {"bogus": 1}})[0] == 422)
            status, first = request("/v1/recommendations", {"node_id": "ribeye_grilled", "user_constraints": {"seen_wine_slugs": ["other-" + str(i) + "x" * 25 for i in range(2500)]}})
            check("large-valid-cursor", status == 200 and request("/v1/recommendations/more", {"cursor": first["next_cursor"]})[0] == 200)
        finally:
            process.terminate()
            process.wait(timeout=10)
    result = {"installed_bundle": str(bundle_root()), "transport": "real loopback TCP HTTP, cwd /tmp",
              "checks": checks, "passed": all(c["passed"] for c in checks)}
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())
