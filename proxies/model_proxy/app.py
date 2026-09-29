"""The HTTP app of the model proxy.

Read docs/plans/01_multi-host-model-proxy.md. A pooled request goes to one work host with
a free slot, and its answer can come from the cache. Each other request goes to the
passthrough host without a change.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

from .cache import (
    CacheEntry,
    CacheStore,
    KeyedLocks,
    build_cache_key,
    canonical_json,
    request_bypasses_cache,
    response_is_cacheable,
    semantic_body,
)
from .config import ProxyConfig, SshTunnel
from .pool import ClientGone, HealthMonitor, Host, NoHost, Pool, QueueFull, QueueTimeout
from .tunnels import Tunnel, ssh_command


log = logging.getLogger("model_proxy")

SAM3_ROUTES = frozenset({"segment", "segment_multi", "segment_verify", "segment_point"})
RETRY_STATUSES = frozenset({429, 502, 503, 504})
HOP_BY_HOP_HEADERS = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailer",
        "transfer-encoding",
        "upgrade",
    }
)


@dataclass(frozen=True)
class Target:
    model: str
    route: str  # the cache route: visual-embeddings, sam3, or grounding-dino


@dataclass(frozen=True)
class Answer:
    """An HTTP answer of a work host."""

    status: int
    headers: dict[str, str]
    body: bytes
    content_type: str
    host: str


@dataclass(frozen=True)
class ProxyError:
    """An error answer of the proxy itself."""

    status: int
    error: str
    detail: str
    retry_after: int | None = None


def upstream_target(path: str, pooled_models: frozenset[str]) -> Target | None:
    """Return the target of a pooled `POST /upstream/<model>/<route>`, or None."""
    parts = path.split("/")
    if len(parts) != 4 or parts[0] or parts[1] != "upstream" or parts[2] not in pooled_models:
        return None
    model, route = parts[2], parts[3]
    if model == "sam3":
        return Target(model, "sam3") if route in SAM3_ROUTES else None
    return Target(model, "grounding-dino") if route == "detect" else None


def embedding_request(
    body: bytes, pooled_models: frozenset[str], want_key: bool
) -> tuple[str | None, bytes | None]:
    """Return (the model, the semantic body) of `POST /v1/embeddings`. The model is None
    when the request is not pooled. The semantic body is None when the request cannot use
    the cache. A worker thread runs this function: a batch of 64 images is a large JSON
    text, and the text is parsed only one time."""
    try:
        payload = json.loads(body)
    except (UnicodeError, ValueError):
        return None, None
    model = payload.get("model") if isinstance(payload, dict) else None
    if not isinstance(model, str) or model not in pooled_models:
        return None, None
    if not want_key:
        return model, None
    try:
        return model, canonical_json(payload)
    except (ValueError, TypeError):
        return model, None


def forward_headers(request: Request) -> dict[str, str]:
    """The request headers for a host. `Cache-Control` and `X-GX10-Cache` stay, so that a
    bypass also skips the gx10 cache."""
    return {
        key: value
        for key, value in request.headers.items()
        if key.casefold() not in HOP_BY_HOP_HEADERS
        and key.casefold() not in {"host", "content-length", "accept-encoding"}
    }


def answer_headers(response: httpx.Response, *, decoded: bool) -> dict[str, str]:
    excluded = set(HOP_BY_HOP_HEADERS) | {"content-length"}
    if decoded:
        excluded.add("content-encoding")
    return {
        key: value
        for key, value in response.headers.items()
        if key.casefold() not in excluded
    }


def _milliseconds(started: float) -> float:
    return (time.perf_counter() - started) * 1000


class ProxyState:
    def __init__(
        self, config: ProxyConfig, tunnel_command: Callable[[SshTunnel], Sequence[str]]
    ) -> None:
        self.config = config
        self.pooled_models = config.pooled_models
        self.cache = CacheStore(
            config.cache_path,
            ttl_seconds=config.ttl_seconds,
            max_bytes=config.max_cache_bytes,
        )
        self.locks = KeyedLocks()
        self.pool = Pool([Host(host) for host in config.hosts], queue_limit=config.queue_limit)
        self.tunnels: list[Tunnel] = []
        for host in self.pool.hosts:
            if host.config.enabled and host.config.ssh is not None:
                host.tunnel = Tunnel(host.name, tunnel_command(host.config.ssh))
                self.tunnels.append(host.tunnel)
        self.client: httpx.AsyncClient | None = None
        self.monitor: HealthMonitor | None = None
        self.started_at = time.time()
        self.hits = 0
        self.misses = 0
        self.bypasses = 0
        self.stores = 0
        self.passthrough = 0

    def store_if_eligible(self, key: str, target: Target, answer: Answer) -> bool:
        """Store `answer` when the cache rules allow it. A worker thread runs this
        function, because the check parses the JSON answer."""
        if len(answer.body) > self.config.max_response_bytes:
            return False
        if not response_is_cacheable(target.route, answer.status, answer.content_type, answer.body):
            return False
        self.cache.put(
            key,
            route=target.route,
            model=target.model,
            host=answer.host,
            status=answer.status,
            content_type=answer.content_type,
            body=answer.body,
        )
        return True


def create_app(
    config: ProxyConfig,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    tunnel_command: Callable[[SshTunnel], Sequence[str]] = ssh_command,
    background: bool = True,
    verbose: bool = False,
) -> FastAPI:
    """Return the app. Tests pass a fake `transport` and a fake `tunnel_command`.
    `background` False runs the first health probe but no later probes."""
    state = ProxyState(config, tunnel_command)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        timeout = httpx.Timeout(
            connect=10.0,
            read=config.upstream_timeout,
            write=300.0,
            pool=10.0,
        )
        state.client = httpx.AsyncClient(
            timeout=timeout,
            transport=transport,
            limits=httpx.Limits(max_connections=None, max_keepalive_connections=64),
        )
        state.monitor = HealthMonitor(
            state.pool,
            state.client,
            interval=config.health_interval,
            timeout=config.health_timeout,
        )
        monitor_task: asyncio.Task[None] | None = None
        try:
            for tunnel in state.tunnels:
                tunnel.start()
            if state.tunnels:
                # The first probe checks whether each tunnel process runs. An ssh process
                # needs about one more second to open its forward; a failed first probe
                # comes again after DOWN_PROBE_INTERVAL.
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(
                        asyncio.gather(*(tunnel.spawned.wait() for tunnel in state.tunnels)), 3
                    )
            await state.monitor.probe_all()
            if background:
                monitor_task = asyncio.create_task(state.monitor.run(), name="health-monitor")
            for host in state.pool.hosts:
                if host.config.enabled:
                    log.info("host %s (%s, %s): %s", host.name, host.config.kind, host.url,
                             "up" if host.up else f"down: {host.reason}")
            yield
        finally:
            if monitor_task is not None:
                monitor_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await monitor_task
            for tunnel in state.tunnels:
                await tunnel.stop()
            await state.client.aclose()
            state.cache.close()

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.proxy = state

    def cached_response(entry: CacheEntry) -> Response:
        return Response(
            content=entry.body,
            status_code=entry.status,
            headers={
                "Content-Type": entry.content_type,
                "X-Proxy-Cache": "HIT",
                "X-Proxy-Host": entry.host,
                "Age": str(max(0, int(time.time() - entry.created_at))),
            },
        )

    def respond(result: Answer | ProxyError, cache_status: str) -> Response:
        if isinstance(result, ProxyError):
            headers = {"X-Proxy-Cache": "BYPASS"}
            if result.retry_after is not None:
                headers["Retry-After"] = str(result.retry_after)
            return JSONResponse(
                {"error": result.error, "detail": result.detail},
                status_code=result.status,
                headers=headers,
            )
        headers = dict(result.headers)
        headers["X-Proxy-Cache"] = cache_status
        headers["X-Proxy-Host"] = result.host
        return Response(content=result.body, status_code=result.status, headers=headers)

    async def forward(request: Request, body: bytes, model: str) -> Answer | ProxyError:
        """Send one pooled request to a host with a free slot. Try the next host after a
        transport error or a retryable HTTP status."""
        assert state.client is not None
        headers = forward_headers(request)
        suffix = request.url.path + (f"?{request.url.query}" if request.url.query else "")
        tried: set[str] = set()
        last_answer: Answer | None = None
        last_error = ""
        for _attempt in range(config.attempts):
            try:
                host = await state.pool.acquire(
                    model,
                    exclude=tried,
                    timeout=config.queue_timeout,
                    gone=request.is_disconnected,
                )
            except NoHost:
                break
            except QueueFull:
                return ProxyError(429, "queue_full",
                                  f"{config.queue_limit} requests for {model} wait already", 1)
            except QueueTimeout:
                return ProxyError(503, "queue_timeout",
                                  f"no free slot for {model} in {config.queue_timeout:g} s", 5)
            except ClientGone:
                return ProxyError(503, "client_disconnected",
                                  "the client disconnected while the request waited")
            tried.add(host.name)
            started = time.perf_counter()
            try:
                upstream = await state.client.post(host.url + suffix, content=body,
                                                   headers=headers)
            except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                host.record(model, _milliseconds(started), error=True)
                state.pool.mark_down(host, f"connection failed: {type(exc).__name__}: {exc}")
                last_error = f"{host.name}: {type(exc).__name__}: {exc}"
                continue
            except httpx.HTTPError as exc:
                host.record(model, _milliseconds(started), error=True)
                last_error = f"{host.name}: {type(exc).__name__}: {exc}"
                log.warning("request for %s failed on %s: %s", model, host.name, last_error)
                continue
            finally:
                state.pool.release(host, model)
            elapsed = _milliseconds(started)
            retry = upstream.status_code in RETRY_STATUSES
            host.record(model, elapsed, error=retry or upstream.status_code >= 500)
            if verbose:
                log.info("%s %s -> %s HTTP %d in %.0f ms", model, request.url.path, host.name,
                         upstream.status_code, elapsed)
            answer = Answer(
                status=upstream.status_code,
                headers=answer_headers(upstream, decoded=True),
                body=upstream.content,
                content_type=upstream.headers.get("content-type", ""),
                host=host.name,
            )
            if retry:
                last_answer = answer
                continue
            return answer
        if last_answer is not None:
            return last_answer
        if tried:
            return ProxyError(502, "upstream_unavailable", last_error)
        return ProxyError(503, "no_host_available", f"no host serves {model} now", 5)

    async def pooled(
        request: Request, body: bytes, target: Target, semantic: bytes | None
    ) -> Response:
        if semantic is None:
            state.bypasses += 1
            return respond(await forward(request, body, target.model), "BYPASS")
        key = build_cache_key(
            namespace=config.namespace,
            method=request.method,
            path=request.url.path,
            query=request.url.query,
            semantic_body=semantic,
        )
        entry = await asyncio.to_thread(state.cache.get, key)
        if entry is not None:
            state.hits += 1
            return cached_response(entry)
        async with state.locks.hold(key):
            entry = await asyncio.to_thread(state.cache.get, key)
            if entry is not None:
                state.hits += 1
                return cached_response(entry)
            state.misses += 1
            result = await forward(request, body, target.model)
            if isinstance(result, Answer) and await asyncio.to_thread(
                state.store_if_eligible, key, target, result
            ):
                state.stores += 1
            return respond(result, "MISS")

    async def passthrough(request: Request, body: bytes) -> Response:
        assert state.client is not None
        host = state.pool.host(config.passthrough)
        url = host.url + request.url.path + (f"?{request.url.query}" if request.url.query else "")
        state.passthrough += 1
        upstream_request = state.client.build_request(
            request.method, url, content=body, headers=forward_headers(request)
        )
        try:
            upstream = await state.client.send(upstream_request, stream=True)
        except httpx.HTTPError as exc:
            return JSONResponse(
                {"error": "upstream_unavailable",
                 "detail": f"{host.name}: {type(exc).__name__}: {exc}"},
                status_code=502,
                headers={"X-Proxy-Cache": "BYPASS", "X-Proxy-Host": host.name},
            )

        async def chunks() -> AsyncIterator[bytes]:
            # aiter_bytes() decodes a Content-Encoding, so the header does not go back.
            # The request has no Accept-Encoding, so a host seldom encodes an answer.
            try:
                async for chunk in upstream.aiter_bytes():
                    yield chunk
            except httpx.HTTPError as exc:
                log.warning("passthrough stream %s ended early: %s", request.url.path, exc)
            finally:
                await upstream.aclose()

        headers = answer_headers(upstream, decoded=True)
        headers["X-Proxy-Cache"] = "BYPASS"
        headers["X-Proxy-Host"] = host.name
        return StreamingResponse(chunks(), status_code=upstream.status_code, headers=headers)

    async def classify(
        request: Request, body: bytes, bypass: bool
    ) -> tuple[Target | None, bytes | None]:
        """Return (the target, the semantic body) of a pooled request, or (None, None)."""
        if request.method != "POST":
            return None, None
        path = request.url.path
        if path == "/v1/embeddings":
            content_type = request.headers.get("content-type", "")
            if content_type.split(";", 1)[0].strip().casefold() != "application/json":
                return None, None
            model, semantic = await asyncio.to_thread(
                embedding_request, body, state.pooled_models, not bypass
            )
            if model is None:
                return None, None
            return Target(model, "visual-embeddings"), semantic
        target = upstream_target(path, state.pooled_models)
        if target is None:
            return None, None
        return target, (None if bypass else await semantic_body(request, body))

    @app.get("/_proxy/health")
    async def proxy_health() -> dict[str, Any]:
        return {"status": "ok"}

    @app.get("/_proxy/status")
    async def proxy_status() -> dict[str, Any]:
        storage = await asyncio.to_thread(state.cache.stats)
        return {
            "status": "ok",
            "uptime_seconds": round(time.time() - state.started_at, 1),
            "listen": f"{config.listen_host}:{config.listen_port}",
            "passthrough": config.passthrough,
            "pooled_models": sorted(state.pooled_models),
            "hosts": [host.status() for host in state.pool.hosts],
            "queues": {model: state.pool.waiting.get(model, 0)
                       for model in sorted(state.pooled_models)},
            "cache": {
                "path": str(config.cache_path),
                "namespace": config.namespace,
                "ttl_seconds": config.ttl_seconds,
                "max_cache_bytes": config.max_cache_bytes,
                "process": {
                    "hits": state.hits,
                    "misses": state.misses,
                    "bypasses": state.bypasses,
                    "stores": state.stores,
                    "passthrough": state.passthrough,
                    "inflight_keys": state.locks.size,
                },
                "storage": storage,
            },
        }

    @app.api_route(
        "/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
    )
    async def proxy(request: Request, path: str) -> Response:
        del path
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > config.max_request_bytes:
                    return JSONResponse({"error": "request_too_large"}, status_code=413)
            except ValueError:
                return JSONResponse({"error": "invalid_content_length"}, status_code=400)
        body = await request.body()
        if len(body) > config.max_request_bytes:
            return JSONResponse({"error": "request_too_large"}, status_code=413)
        bypass = request_bypasses_cache(request.headers)
        target, semantic = await classify(request, body, bypass)
        if target is None:
            return await passthrough(request, body)
        return await pooled(request, body, target, semantic)

    return app
