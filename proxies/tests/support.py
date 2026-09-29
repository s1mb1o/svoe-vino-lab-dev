"""Shared helpers of the tests: a configuration and fake work hosts."""

from __future__ import annotations

import asyncio
import json
import sys
from collections import defaultdict
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import httpx

from model_proxy.config import ProxyConfig, parse


# A tunnel command that runs until the test stops it, and one that exits at once.
SLEEPER = [sys.executable, "-c", "import time; time.sleep(60)"]
QUITTER = [sys.executable, "-c", "import sys; sys.exit(3)"]

GX10 = {
    "name": "gx10",
    "kind": "llama-swap",
    "url": "http://gx10.test",
    "slots": 4,
    "models": ["sam3", "grounding-dino-base", "siglip2-so400m-patch16-naflex",
               "siglip2-so400m-patch16-512"],
}
RTX = {
    "name": "rtx",
    "kind": "bootstrap",
    "url": "http://rtx.test",
    "slots": 4,
    "models": ["sam3", "siglip2-so400m-patch16-naflex", "siglip2-so400m-patch16-512"],
}


def make_config(directory: str, hosts: list[dict[str, Any]] | None = None,
                **limits: Any) -> ProxyConfig:
    raw = {
        "listen": {"host": "127.0.0.1", "port": 18092},
        "passthrough": "gx10",
        "cache": {"path": str(Path(directory) / "cache.sqlite3"), "namespace": "test-v1"},
        "limits": {"queue_timeout": 5, "upstream_timeout": 5, "attempts": 3, **limits},
        "health": {"interval": 60, "timeout": 1},
        "hosts": hosts if hosts is not None else [dict(GX10)],
    }
    return parse(raw)


Handler = Callable[[httpx.Request], Awaitable[httpx.Response]]


class FakeHosts:
    """Fake work hosts behind one httpx.MockTransport. The key of a host is the host
    part of its URL, for example `gx10.test`. Each host answers its probe by default."""

    def __init__(self) -> None:
        self.handlers: dict[str, Handler] = {}
        self.calls: dict[str, list[httpx.Request]] = defaultdict(list)
        self.active: dict[str, list[str]] = {}
        self.inflight: dict[str, int] = defaultdict(int)
        self.peak: dict[str, int] = defaultdict(int)
        self.down: set[str] = set()  # hosts that refuse each connection

    def on(self, host: str, handler: Handler) -> None:
        self.handlers[host] = handler

    def inference_calls(self, host: str) -> list[httpx.Request]:
        return [request for request in self.calls[host]
                if request.url.path not in {"/running", "/health"}]

    async def __call__(self, request: httpx.Request) -> httpx.Response:
        host = request.url.host if request.url.port in (None, 80) else \
            f"{request.url.host}:{request.url.port}"
        if host in self.down:
            raise httpx.ConnectError("connection refused", request=request)
        if request.url.path == "/running" and request.method == "GET":
            self.calls[host].append(request)
            return httpx.Response(200, json={"running": []})
        if request.url.path == "/health" and request.method == "GET" and host in self.active:
            self.calls[host].append(request)
            return httpx.Response(200, json={"status": "ok", "active_models": self.active[host],
                                             "failures": {}})
        self.calls[host].append(request)
        self.inflight[host] += 1
        self.peak[host] = max(self.peak[host], self.inflight[host])
        try:
            handler = self.handlers.get(host)
            if handler is None:
                return httpx.Response(404, json={"detail": f"no fake handler for {host}"})
            return await handler(request)
        finally:
            self.inflight[host] -= 1


def embeddings_answer(delay: float = 0.0) -> Handler:
    async def handler(request: httpx.Request) -> httpx.Response:
        if delay:
            await asyncio.sleep(delay)
        payload = json.loads(request.content)
        items = payload["input"] if isinstance(payload["input"], list) else [payload["input"]]
        return httpx.Response(200, json={
            "object": "list",
            "model": payload["model"],
            "data": [{"object": "embedding", "index": i, "embedding": [0.1, 0.2]}
                     for i, _ in enumerate(items)],
        })
    return handler


def instances_answer(delay: float = 0.0, tag: str = "") -> Handler:
    async def handler(request: httpx.Request) -> httpx.Response:
        if delay:
            await asyncio.sleep(delay)
        return httpx.Response(200, json={"instances": [{"label": tag or "bottle", "score": 0.9}],
                                         "count": 1})
    return handler


def status_answer(status: int, body: dict[str, Any] | None = None) -> Handler:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=body or {"error": f"status {status}"})
    return handler


def connection_error() -> Handler:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)
    return handler
