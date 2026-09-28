"""Measure warm inference latency and throughput for one bootstrap model.

Run this client on the same host as the model service. This removes network
latency from the host comparison. The client sends the same generated image
and the same request fields for all benchmark runs.
"""

from __future__ import annotations

import argparse
import base64
import concurrent.futures
import json
import math
import platform
import socket
import statistics
import struct
import time
import zlib
from dataclasses import asdict, dataclass
from typing import Any

import httpx


MODELS = (
    "qr-scanner",
    "shieldgemma-2-4b-it",
    "siglip2-so400m-patch16-naflex",
    "siglip2-so400m-patch16-512",
    "sam3",
)

# This PNG contains a QR code for "svoe-vino-bootstrap". Keep this fixture
# static so the two hosts receive identical bytes without a qrcode dependency.
QR_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAUoAAAFKAQAAAABTUiuoAAACJklEQVR4nO1aQW4rMQh9"
    "EEtdTqUeoEdxblb1SL3BzFFyg86y0kRUYJzkV/qSu2hDNbBwxvZbIDBgP0KCQVl4FAkk"
    "lNNYyOMyLJxQpLGGhRMKFXIpwEIFdFyJgLUvH9NYMY5LaT911nF9AlUBZHnedOOw2SYF0"
    "ZUTiiarh5C8Pp4J9R2waYu3NFbY47KWPtxJgf8KY+/Q8mVOmv+ozlsRrL+hACcU3zbWJ"
    "CJau2SePgjLoy+LSKtdSLvi/icLotInB0F9vw59uSpmvruuvHtoMQtc6SfBeiZZnj9I4y"
    "2NFTK2ao8omacN7attyNYgkrGFIN4Se27BHKWFSlOf72o6zEwYy1tiTrFCNW161VAPti9"
    "3nmRsIYi30O6Ek/vNPdgzYXorGLSeiOjl5K+vRgwqY+gp8ucVGBHG3qHomdCvFS31aaj"
    "Zhb4HWGbCEN5yDv6IM9HxwjdVjTIrYwspGx9J1z1D0e+EBy1eflvve7aWsRUutl7sTn"
    "h6EGPjLTECcDY+lq57hhYbBdja0NOe97wI69MWRVdOKP7tHbewasyTlrFF211prFjHpV"
    "6eyFAO3ogopzYuZYyD6DoivI/eMRE9SH9v0U3vBHF0HRDeB1Su/a1GYyi1McfUdX/Q8"
    "mVOtlTf6KaLQu0/NvwjCnBCMS5yZSuM0GgvLxVvm2THJHTvGN4nMabXOv3JPIXtHUMnN"
    "23jHmq4u66cUKSxhoUTijTWsHBC8XeM9QmkCFNa+0//EgAAAABJRU5ErkJggg=="
)


def _png_chunk(name: bytes, body: bytes) -> bytes:
    content = name + body
    return struct.pack(">I", len(body)) + content + struct.pack(">I", zlib.crc32(content))


def sample_png() -> bytes:
    """Create the same 320 by 480 synthetic bottle image on each host."""
    width, height = 320, 480
    pixels = bytearray([255, 255, 255]) * width * height

    def rectangle(x1: int, y1: int, x2: int, y2: int, color: tuple[int, int, int]) -> None:
        row = bytes(color) * (x2 - x1)
        for y in range(y1, y2):
            start = 3 * (y * width + x1)
            pixels[start : start + len(row)] = row

    rectangle(90, 80, 230, 450, (55, 95, 45))
    rectangle(130, 20, 190, 110, (60, 80, 40))
    rectangle(100, 240, 220, 360, (245, 235, 205))
    raw = b"".join(b"\x00" + pixels[3 * y * width : 3 * (y + 1) * width] for y in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", header) + _png_chunk(
        b"IDAT", zlib.compress(raw, level=6)
    ) + _png_chunk(b"IEND", b"")


@dataclass(frozen=True)
class Result:
    concurrency: int
    requests: int
    successes: int
    failures: int
    wall_seconds: float
    requests_per_second: float
    latency_mean_ms: float | None
    latency_p50_ms: float | None
    latency_p95_ms: float | None
    latency_min_ms: float | None
    latency_max_ms: float | None
    errors: list[str]


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(fraction * len(ordered)) - 1)
    return ordered[index]


def _path(model: str, route_mode: str) -> str:
    if model.startswith("siglip2-"):
        return "/v1/embeddings"
    suffix = {
        "qr-scanner": "/scan",
        "shieldgemma-2-4b-it": "/classify",
        "sam3": "/segment",
    }[model]
    if route_mode == "gateway":
        return f"/upstream/{model}{suffix}"
    return suffix


class Requester:
    def __init__(self, base_url: str, model: str, route_mode: str, timeout: float) -> None:
        self.model = model
        self.path = _path(model, route_mode)
        self.image = sample_png()
        limits = httpx.Limits(max_connections=64, max_keepalive_connections=64)
        self.client = httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout, limits=limits)

    def close(self) -> None:
        self.client.close()

    def send(self) -> None:
        if self.model == "qr-scanner":
            response = self.client.post(
                self.path,
                files={"image": ("qr.png", QR_PNG, "image/png")},
                data={"engine": "zxing-cpp"},
            )
        elif self.model == "shieldgemma-2-4b-it":
            response = self.client.post(
                self.path,
                files={"image": ("bottle.png", self.image, "image/png")},
                data={"policies": "dangerous,sexual,violence", "threshold": "0.5"},
            )
        elif self.model == "sam3":
            response = self.client.post(
                self.path,
                files={"image": ("bottle.png", self.image, "image/png")},
                data={"text": "wine bottle", "threshold": "0.1", "return_masks": "false"},
            )
        else:
            uri = "data:image/png;base64," + base64.b64encode(self.image).decode("ascii")
            body: dict[str, Any] = {"model": self.model, "input": [uri]}
            if self.model.endswith("naflex"):
                body["max_num_patches"] = 256
            response = self.client.post(self.path, json=body)
        response.raise_for_status()
        self._validate(response.json())

    def _validate(self, body: dict[str, Any]) -> None:
        if self.model == "qr-scanner":
            if "svoe-vino-bootstrap" not in [item["text"] for item in body["instances"]]:
                raise ValueError("QR response did not contain the expected text")
        elif self.model == "shieldgemma-2-4b-it":
            if set(body["scores"]) != {"dangerous", "sexual", "violence"}:
                raise ValueError("ShieldGemma response has unexpected policy keys")
        elif self.model == "sam3":
            if (body["width"], body["height"]) != (320, 480):
                raise ValueError("SAM3 response has unexpected dimensions")
        elif len(body["data"][0]["embedding"]) != 1152:
            raise ValueError("SigLIP2 response has an unexpected vector size")


def _one(requester: Requester) -> tuple[float | None, str | None]:
    started = time.perf_counter()
    try:
        requester.send()
    except Exception as exc:  # noqa: BLE001 - record each failed request in the result.
        return None, f"{type(exc).__name__}: {exc}"
    return time.perf_counter() - started, None


def measure(requester: Requester, concurrency: int, request_count: int) -> Result:
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        outcomes = list(pool.map(lambda _: _one(requester), range(request_count)))
    wall = time.perf_counter() - started
    latencies = [seconds for seconds, error in outcomes if seconds is not None and error is None]
    errors = [error for _, error in outcomes if error is not None]
    return Result(
        concurrency=concurrency,
        requests=request_count,
        successes=len(latencies),
        failures=len(errors),
        wall_seconds=round(wall, 6),
        requests_per_second=round(len(latencies) / wall, 6),
        latency_mean_ms=round(1000 * statistics.mean(latencies), 3) if latencies else None,
        latency_p50_ms=round(1000 * _percentile(latencies, 0.50), 3) if latencies else None,
        latency_p95_ms=round(1000 * _percentile(latencies, 0.95), 3) if latencies else None,
        latency_min_ms=round(1000 * min(latencies), 3) if latencies else None,
        latency_max_ms=round(1000 * max(latencies), 3) if latencies else None,
        errors=errors[:10],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True, choices=MODELS)
    parser.add_argument("--route-mode", choices=["direct", "gateway"], default="direct")
    parser.add_argument("--concurrency", default="1,2,4,8")
    parser.add_argument("--requests", type=int, default=16)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=900.0)
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    concurrencies = [int(value) for value in arguments.concurrency.split(",")]
    if not concurrencies or any(value < 1 for value in concurrencies):
        raise SystemExit("--concurrency must contain positive integers")
    if arguments.requests < max(concurrencies):
        raise SystemExit("--requests must be at least the largest concurrency")

    requester = Requester(arguments.base_url, arguments.model, arguments.route_mode, arguments.timeout)
    try:
        for _ in range(arguments.warmup):
            requester.send()
        results = [measure(requester, value, arguments.requests) for value in concurrencies]
    finally:
        requester.close()

    output = {
        "schema_version": 1,
        "host": socket.gethostname(),
        "platform": platform.platform(),
        "model": arguments.model,
        "base_url": arguments.base_url,
        "route_mode": arguments.route_mode,
        "warmup_requests": arguments.warmup,
        "requests_per_scenario": arguments.requests,
        "concurrencies": concurrencies,
        "results": [asdict(result) for result in results],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 1 if any(result.failures for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
