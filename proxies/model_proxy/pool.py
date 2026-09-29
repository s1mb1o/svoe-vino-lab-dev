"""The work hosts of the proxy: their slots, the queue of each model, and the health probes.

Read docs/plans/01_multi-host-model-proxy.md, sections "Dispatch", "Retry", and "Health".
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from typing import Any

import httpx

from .config import HostConfig


log = logging.getLogger("model_proxy.pool")

# A waiting request checks this often whether its client disconnected.
DISCONNECT_POLL = 1.0
# While a host is down, the probes come this often, so that a host that is back, or a
# tunnel that connected after the start, is used again soon.
DOWN_PROBE_INTERVAL = 2.0


class NoHost(Exception):
    """No eligible host is up for the model."""


class QueueFull(Exception):
    """The queue of the model is full."""


class QueueTimeout(Exception):
    """The request waited too long for a free slot."""


class ClientGone(Exception):
    """The client disconnected while the request waited."""


@dataclass
class Counter:
    requests: int = 0
    errors: int = 0
    total_ms: float = 0.0


class Host:
    """One work host and its state."""

    def __init__(self, config: HostConfig) -> None:
        self.config = config
        self.name = config.name
        self.url = config.url
        self.up = False
        self.reason = "not probed yet" if config.enabled else "disabled"
        self.checked_at: float | None = None
        # None means that each configured model is active: llama-swap loads a model on
        # demand. A bootstrap host reports its active models in GET /health.
        self.active_models: frozenset[str] | None = None
        self.inflight: dict[str, int] = {model: 0 for model in config.models}
        self.counters: dict[str, Counter] = {model: Counter() for model in config.models}
        self.tunnel: Any = None  # a tunnels.Tunnel for a host with an ssh entry

    def serves(self, model: str) -> bool:
        if model not in self.inflight:
            return False
        return self.active_models is None or model in self.active_models

    def has_free_slot(self, model: str) -> bool:
        return self.inflight[model] < self.config.slots

    def busy_share(self, model: str) -> float:
        return self.inflight[model] / self.config.slots

    def record(self, model: str, milliseconds: float, *, error: bool) -> None:
        counter = self.counters[model]
        counter.requests += 1
        counter.total_ms += milliseconds
        if error:
            counter.errors += 1

    def status(self) -> dict[str, Any]:
        models = {}
        for model in self.config.models:
            counter = self.counters[model]
            models[model] = {
                "active": self.serves(model),
                "inflight": self.inflight[model],
                "requests": counter.requests,
                "errors": counter.errors,
                "avg_ms": (round(counter.total_ms / counter.requests, 1)
                           if counter.requests else None),
            }
        return {
            "name": self.name,
            "kind": self.config.kind,
            "url": self.url,
            "enabled": self.config.enabled,
            "up": self.up,
            "reason": self.reason,
            "checked_at": self.checked_at,
            "slots": self.config.slots,
            "tunnel": self.tunnel.status() if self.tunnel is not None else None,
            "models": models,
        }


class Pool:
    """The slots of the hosts and the queue of each model.

    The event loop runs in one thread, so a check and a change of the slots without an
    await between them cannot race. A released slot wakes each waiting request, in the
    order of arrival, and each such request checks the hosts again.
    """

    def __init__(self, hosts: Iterable[Host], *, queue_limit: int) -> None:
        self.hosts = list(hosts)
        self.queue_limit = queue_limit
        self.waiting: dict[str, int] = defaultdict(int)
        self._waiters: deque[asyncio.Future[None]] = deque()

    def host(self, name: str) -> Host:
        for host in self.hosts:
            if host.name == name:
                return host
        raise KeyError(name)

    def _eligible(self, host: Host, model: str, exclude: frozenset[str] | set[str]) -> bool:
        return host.config.enabled and host.up and host.serves(model) and host.name not in exclude

    def _pick(self, model: str, exclude: frozenset[str] | set[str]) -> Host | None:
        free = [
            host
            for host in self.hosts
            if self._eligible(host, model, exclude) and host.has_free_slot(model)
        ]
        if not free:
            return None
        # min() keeps the first host of equal hosts, so a tie goes to the configuration order.
        return min(free, key=lambda host: host.busy_share(model))

    async def acquire(
        self,
        model: str,
        *,
        exclude: frozenset[str] | set[str] = frozenset(),
        timeout: float,
        gone: Callable[[], Awaitable[bool]] | None = None,
    ) -> Host:
        """Take one slot of an eligible host for `model`, and return the host. Wait while
        each eligible host is busy. Raise NoHost, QueueFull, QueueTimeout, or ClientGone."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        if not any(self._eligible(host, model, exclude) for host in self.hosts):
            raise NoHost(model)
        if self.waiting[model] >= self.queue_limit:
            raise QueueFull(model)
        self.waiting[model] += 1
        try:
            while True:
                host = self._pick(model, exclude)
                if host is not None:
                    host.inflight[model] += 1
                    return host
                if not any(self._eligible(item, model, exclude) for item in self.hosts):
                    raise NoHost(model)
                remaining = deadline - loop.time()
                if remaining <= 0:
                    raise QueueTimeout(model)
                waiter: asyncio.Future[None] = loop.create_future()
                self._waiters.append(waiter)
                try:
                    await asyncio.wait_for(waiter, min(remaining, DISCONNECT_POLL))
                except TimeoutError:
                    pass
                finally:
                    try:
                        self._waiters.remove(waiter)
                    except ValueError:
                        pass
                if gone is not None and await gone():
                    raise ClientGone(model)
        finally:
            self.waiting[model] -= 1

    def release(self, host: Host, model: str) -> None:
        """Give back one slot. The call is synchronous, so a cancelled request cannot keep
        its slot."""
        host.inflight[model] -= 1
        self.wake()

    def wake(self) -> None:
        """Wake each waiting request, so that it checks the hosts again."""
        waiters, self._waiters = self._waiters, deque()
        for waiter in waiters:
            if not waiter.done():
                waiter.set_result(None)

    def mark_down(self, host: Host, reason: str) -> None:
        """Take `host` out until its next good probe."""
        if host.up:
            log.warning("host %s is down: %s", host.name, reason)
        host.up = False
        host.reason = reason
        self.wake()


class HealthMonitor:
    """The probes of the enabled hosts. A probe never loads a model on gx10."""

    def __init__(
        self,
        pool: Pool,
        client: httpx.AsyncClient,
        *,
        interval: float,
        timeout: float,
    ) -> None:
        self.pool = pool
        self.client = client
        self.interval = interval
        self.timeout = timeout

    def _set(self, host: Host, up: bool, reason: str, active: frozenset[str] | None) -> None:
        changed = host.up != up or host.active_models != active
        host.up = up
        host.reason = reason
        host.active_models = active
        host.checked_at = time.time()
        if changed:
            level = logging.INFO if up else logging.WARNING
            log.log(level, "host %s is %s: %s", host.name, "up" if up else "down", reason)
            self.pool.wake()

    async def probe(self, host: Host) -> None:
        if host.tunnel is not None and not host.tunnel.running:
            self._set(host, False, "the tunnel is down", host.active_models)
            return
        try:
            if host.config.kind == "llama-swap":
                await self._probe_llama_swap(host)
            else:
                await self._probe_bootstrap(host)
        except (httpx.HTTPError, ValueError) as exc:
            self._set(host, False, f"probe failed: {type(exc).__name__}: {exc}",
                      host.active_models)

    async def _probe_llama_swap(self, host: Host) -> None:
        # GET /running loads no model. GET /upstream/<model>/health would load it.
        response = await self.client.get(host.url + "/running", timeout=self.timeout)
        payload = response.json() if response.status_code == 200 else None
        if isinstance(payload, dict) and isinstance(payload.get("running"), list):
            self._set(host, True, "ok", None)
        else:
            self._set(host, False, f"GET /running returned HTTP {response.status_code}", None)

    async def _probe_bootstrap(self, host: Host) -> None:
        response = await self.client.get(host.url + "/health", timeout=self.timeout)
        payload = response.json() if response.status_code in (200, 503) else None
        models = payload.get("active_models") if isinstance(payload, dict) else None
        if not isinstance(models, list):
            self._set(host, False, f"GET /health returned HTTP {response.status_code}",
                      host.active_models)
            return
        failures = payload.get("failures") or {}
        active = frozenset(str(model) for model in models) - frozenset(str(m) for m in failures)
        if not active & frozenset(host.config.models):
            self._set(host, False, "no configured model is active", active)
        elif failures:
            self._set(host, True, "not ready: " + ", ".join(sorted(map(str, failures))), active)
        else:
            self._set(host, True, "ok", active)

    async def probe_all(self) -> None:
        await asyncio.gather(
            *(self.probe(host) for host in self.pool.hosts if host.config.enabled)
        )

    async def run(self) -> None:
        while True:
            enabled = [host for host in self.pool.hosts if host.config.enabled]
            down = any(not host.up for host in enabled)
            await asyncio.sleep(min(self.interval, DOWN_PROBE_INTERVAL) if down else self.interval)
            await self.probe_all()
