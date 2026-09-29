"""A live check of a running model proxy: one miss and one hit for each model family.

Usage, in the project directory, while the proxy runs:
    .venv/bin/python scripts/smoke.py [--proxy http://127.0.0.1:18092] [--load-models]

The check reads `GET /running` of gx10 through the proxy. By default it calls only a model
that runs now: a request to a model that does not run makes llama-swap load it, and the
load can stop a model that a job uses. `--load-models` calls each model.

Each run sends a new file: the photo of the lab smoke test with random bytes after the
JPEG end marker. A decoder ignores these bytes, so the image stays the same, but the cache
key is new. So the first call reaches a host, and the second call must be a cache hit.
"""

from __future__ import annotations

import argparse
import base64
import os
import sys
import time
from pathlib import Path

import httpx


LAB = Path(__file__).resolve().parents[2]
BOTTLE = LAB / "workbench" / "tests" / "data" / "smoke" / "bottle.jpg"
TIMEOUT = 600  # s; a cold start of SAM3 takes 45 to 85 s
FAMILIES = (
    ("sam3", "sam3"),
    ("grounding-dino-base", "grounding-dino-base"),
    ("siglip2-naflex-p512", "siglip2-so400m-patch16-naflex"),
    ("siglip2-512", "siglip2-so400m-patch16-512"),
)


def unique_photo() -> bytes:
    return BOTTLE.read_bytes() + b"smoke" + os.urandom(16)


def call(client: httpx.Client, family: str, model: str, photo: bytes) -> httpx.Response:
    files = {"image": ("bottle.jpg", photo, "image/jpeg")}
    if family == "sam3":
        return client.post("/upstream/sam3/segment_multi", files=files,
                           data={"texts": "wine bottle", "threshold": "0.35",
                                 "mask_threshold": "0.5", "return_masks": "false"})
    if family == "grounding-dino-base":
        return client.post(f"/upstream/{model}/detect", files=files,
                           data={"texts": "wine bottle", "threshold": "0.25",
                                 "text_threshold": "0.25"})
    body = {"model": model,
            "input": ["data:image/jpeg;base64," + base64.b64encode(photo).decode("ascii")]}
    if family == "siglip2-naflex-p512":
        body["max_num_patches"] = 512
    return client.post("/v1/embeddings", json=body)


def check_answer(family: str, response: httpx.Response) -> str:
    """Return an empty text for a good answer, or the problem."""
    if response.status_code != 200:
        return f"HTTP {response.status_code}: {response.text[:200]}"
    payload = response.json()
    if family in ("sam3", "grounding-dino-base"):
        if not isinstance(payload.get("instances"), list):
            return "no list `instances`"
        return ""
    data = payload.get("data")
    if not isinstance(data, list) or len(data) != 1 or len(data[0].get("embedding", [])) != 1152:
        return "no vector of 1,152 values"
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--proxy", default="http://127.0.0.1:18092")
    parser.add_argument("--load-models", action="store_true",
                        help="also call a model that does not run on gx10 now")
    args = parser.parse_args()

    failures = 0
    with httpx.Client(base_url=args.proxy.rstrip("/"), timeout=TIMEOUT) as client:
        status = client.get("/_proxy/status").json()
        for host in status["hosts"]:
            state = "up" if host["up"] else f"down ({host['reason']})"
            if not host["enabled"]:
                state = "disabled"
            print(f"host  {host['name']:<10} {state}")
        running = client.get("/running").json().get("running") or []
        ready = {item.get("model") for item in running if item.get("state") == "ready"}
        for family, model in FAMILIES:
            if model not in status["pooled_models"]:
                print(f"SKIP  {family:<20} no enabled host lists {model}")
                continue
            if model not in ready and not args.load_models:
                print(f"IDLE  {family:<20} {model} does not run on gx10; use --load-models")
                continue
            photo = unique_photo()
            started = time.perf_counter()
            first = call(client, family, model, photo)
            first_ms = (time.perf_counter() - started) * 1000
            started = time.perf_counter()
            second = call(client, family, model, photo)
            second_ms = (time.perf_counter() - started) * 1000
            problem = check_answer(family, first)
            if not problem and first.headers.get("x-proxy-cache") != "MISS":
                problem = f"first call: X-Proxy-Cache {first.headers.get('x-proxy-cache')}"
            if not problem and second.headers.get("x-proxy-cache") != "HIT":
                problem = f"second call: X-Proxy-Cache {second.headers.get('x-proxy-cache')}"
            if not problem and first.content != second.content:
                problem = "the hit differs from the miss"
            if problem:
                failures += 1
                print(f"FAIL  {family:<20} {problem}")
                continue
            count = len(first.json().get("instances") or first.json().get("data") or [])
            gx10_cache = first.headers.get("x-gx10-cache", "-")
            print(f"PASS  {family:<20} miss {first_ms:7.0f} ms on {first.headers['x-proxy-host']}"
                  f" (gx10 cache {gx10_cache}), hit {second_ms:5.0f} ms, {count} item(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
