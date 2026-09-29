from __future__ import annotations

import asyncio
import unittest

import httpx

from model_proxy.config import HostConfig
from model_proxy.pool import (
    ClientGone,
    HealthMonitor,
    Host,
    NoHost,
    Pool,
    QueueFull,
    QueueTimeout,
)


def host(name: str, *, slots: int = 1, models: tuple[str, ...] = ("sam3",),
         kind: str = "llama-swap", up: bool = True) -> Host:
    item = Host(HostConfig(name=name, kind=kind, url=f"http://{name}.test", slots=slots,
                           models=models))
    item.up = up
    return item


class AcquireTests(unittest.IsolatedAsyncioTestCase):
    async def test_lowest_busy_share_wins_and_tie_keeps_the_order(self) -> None:
        a, b = host("a", slots=2), host("b", slots=4)
        pool = Pool([a, b], queue_limit=8)
        self.assertIs(await pool.acquire("sam3", timeout=1), a)  # tie at 0: the first host
        self.assertIs(await pool.acquire("sam3", timeout=1), b)  # a 1/2, b 0/4
        self.assertIs(await pool.acquire("sam3", timeout=1), b)  # a 1/2, b 1/4
        self.assertIs(await pool.acquire("sam3", timeout=1), a)  # a 1/2, b 2/4: tie
        self.assertEqual((a.inflight["sam3"], b.inflight["sam3"]), (2, 2))

    async def test_request_waits_for_a_released_slot(self) -> None:
        a = host("a")
        pool = Pool([a], queue_limit=8)
        await pool.acquire("sam3", timeout=1)
        waiter = asyncio.create_task(pool.acquire("sam3", timeout=5))
        await asyncio.sleep(0.02)
        self.assertFalse(waiter.done())
        self.assertEqual(pool.waiting["sam3"], 1)
        pool.release(a, "sam3")
        self.assertIs(await asyncio.wait_for(waiter, 1), a)
        self.assertEqual(pool.waiting["sam3"], 0)

    async def test_waiting_requests_get_slots_in_arrival_order(self) -> None:
        a = host("a")
        pool = Pool([a], queue_limit=8)
        await pool.acquire("sam3", timeout=1)
        order: list[int] = []

        async def wait(number: int) -> None:
            await pool.acquire("sam3", timeout=5)
            order.append(number)
            await asyncio.sleep(0.01)
            pool.release(a, "sam3")

        tasks = [asyncio.create_task(wait(number)) for number in range(4)]
        await asyncio.sleep(0.02)
        pool.release(a, "sam3")
        await asyncio.wait_for(asyncio.gather(*tasks), 2)
        self.assertEqual(order, [0, 1, 2, 3])

    async def test_other_models_and_excluded_hosts_are_not_used(self) -> None:
        a, b = host("a", models=("siglip",)), host("b")
        pool = Pool([a, b], queue_limit=8)
        self.assertIs(await pool.acquire("sam3", timeout=1), b)
        with self.assertRaises(NoHost):
            await pool.acquire("sam3", exclude={"b"}, timeout=1)

    async def test_down_host_and_no_host(self) -> None:
        a = host("a", up=False)
        pool = Pool([a], queue_limit=8)
        with self.assertRaises(NoHost):
            await pool.acquire("sam3", timeout=1)

    async def test_waiter_fails_when_its_last_host_goes_down(self) -> None:
        a = host("a")
        pool = Pool([a], queue_limit=8)
        await pool.acquire("sam3", timeout=1)
        waiter = asyncio.create_task(pool.acquire("sam3", timeout=5))
        await asyncio.sleep(0.02)
        pool.mark_down(a, "test")
        with self.assertRaises(NoHost):
            await asyncio.wait_for(waiter, 1)

    async def test_queue_limit_and_timeout(self) -> None:
        a = host("a")
        pool = Pool([a], queue_limit=1)
        await pool.acquire("sam3", timeout=1)
        waiter = asyncio.create_task(pool.acquire("sam3", timeout=0.2))
        await asyncio.sleep(0.02)
        with self.assertRaises(QueueFull):
            await pool.acquire("sam3", timeout=1)
        with self.assertRaises(QueueTimeout):
            await waiter
        self.assertEqual(pool.waiting["sam3"], 0)

    async def test_disconnected_client_leaves_the_queue(self) -> None:
        a = host("a")
        pool = Pool([a], queue_limit=8)
        await pool.acquire("sam3", timeout=1)

        async def gone() -> bool:
            return True

        waiter = asyncio.create_task(pool.acquire("sam3", timeout=5, gone=gone))
        await asyncio.sleep(0.02)
        pool.wake()
        with self.assertRaises(ClientGone):
            await asyncio.wait_for(waiter, 2)
        self.assertEqual(pool.waiting["sam3"], 0)

    async def test_bootstrap_host_serves_only_active_models(self) -> None:
        rtx = host("rtx", models=("sam3", "siglip"), kind="bootstrap")
        rtx.active_models = frozenset({"siglip"})
        pool = Pool([rtx], queue_limit=8)
        self.assertIs(await pool.acquire("siglip", timeout=1), rtx)
        with self.assertRaises(NoHost):
            await pool.acquire("sam3", timeout=1)


class HealthTests(unittest.IsolatedAsyncioTestCase):
    async def probe(self, item: Host, handler) -> Host:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            monitor = HealthMonitor(Pool([item], queue_limit=1), client, interval=60, timeout=1)
            await monitor.probe(item)
        return item

    async def test_llama_swap_probe_reads_running_only(self) -> None:
        paths: list[str] = []

        async def handler(request: httpx.Request) -> httpx.Response:
            paths.append(request.url.path)
            return httpx.Response(200, json={"running": [{"model": "sam3", "state": "ready"}]})

        item = await self.probe(host("gx10", up=False), handler)
        self.assertTrue(item.up)
        self.assertIsNone(item.active_models)
        self.assertEqual(paths, ["/running"])

    async def test_llama_swap_probe_failures(self) -> None:
        async def refused(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("refused", request=request)

        async def not_llama_swap(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"status": "ok"})

        for handler in (refused, not_llama_swap):
            with self.subTest(handler=handler.__name__):
                item = await self.probe(host("gx10"), handler)
                self.assertFalse(item.up)

    async def test_bootstrap_probe_reads_active_models_and_failures(self) -> None:
        async def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, json={
                "status": "not-ready",
                "active_models": ["sam3", "siglip", "qr-scanner"],
                "failures": {"sam3": "health returned HTTP 503"},
            })

        item = await self.probe(host("rtx", models=("sam3", "siglip"), kind="bootstrap",
                                     up=False), handler)
        self.assertTrue(item.up)
        self.assertEqual(item.active_models, frozenset({"siglip", "qr-scanner"}))
        self.assertFalse(item.serves("sam3"))
        self.assertTrue(item.serves("siglip"))

    async def test_bootstrap_probe_without_a_configured_model_is_down(self) -> None:
        async def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"status": "ok", "active_models": ["qr-scanner"],
                                             "failures": {}})

        item = await self.probe(host("rtx", kind="bootstrap"), handler)
        self.assertFalse(item.up)

    async def test_host_with_a_stopped_tunnel_is_down_without_a_probe(self) -> None:
        calls = 0

        async def handler(_request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            return httpx.Response(200, json={"running": []})

        class Stopped:
            running = False

        item = host("rtx")
        item.tunnel = Stopped()
        await self.probe(item, handler)
        self.assertFalse(item.up)
        self.assertEqual(calls, 0)


if __name__ == "__main__":
    unittest.main()
