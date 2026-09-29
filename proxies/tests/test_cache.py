from __future__ import annotations

import asyncio
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

from model_proxy import cache


GX10_SERVER = Path("/Users/ashmelev/Admin/gx10/scripts/inference/vlm_response_cache/server.py")


def store(directory: str, *, ttl: int = 10**10, max_bytes: int = 1024) -> cache.CacheStore:
    # The store prunes with the real clock when it opens. The long default TTL keeps the
    # entries of the fake times alive, so that only the test of the TTL sees an expiry.
    return cache.CacheStore(Path(directory) / "cache.db", ttl_seconds=ttl, max_bytes=max_bytes)


def put(target: cache.CacheStore, key: str, body: bytes, now: float, host: str = "gx10") -> None:
    target.put(key, route="sam3", model="sam3", host=host, status=200,
               content_type="application/json", body=body, now=now)


class KeyTests(unittest.TestCase):
    def test_json_key_order_does_not_change_bytes(self) -> None:
        left = cache.canonical_json({"model": "siglip2", "input": ["a"]})
        right = cache.canonical_json({"input": ["a"], "model": "siglip2"})
        self.assertEqual(left, right)

    def test_multipart_boundary_filename_and_order_do_not_matter(self) -> None:
        left = [
            cache.MultipartPart("image", "file", b"PNG", "image/png"),
            cache.MultipartPart("texts", "field", b"bottle, label"),
        ]
        right = [
            cache.MultipartPart("texts", "field", b"bottle, label"),
            cache.MultipartPart("image", "file", b"PNG", "image/png"),
        ]
        self.assertEqual(cache.canonical_multipart(left), cache.canonical_multipart(right))

    def test_query_order_does_not_change_key(self) -> None:
        first = cache.build_cache_key(namespace="v1", method="POST", path="/x",
                                      query="b=2&a=1", semantic_body=b"x")
        second = cache.build_cache_key(namespace="v1", method="POST", path="/x",
                                       query="a=1&b=2", semantic_body=b"x")
        self.assertEqual(first, second)

    @unittest.skipUnless(GX10_SERVER.is_file(), "the gx10 cache source is not on this host")
    def test_key_equals_the_gx10_key(self) -> None:
        spec = importlib.util.spec_from_file_location("gx10_cache_server", GX10_SERVER)
        assert spec is not None and spec.loader is not None
        gx10 = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = gx10
        spec.loader.exec_module(gx10)
        parts = [cache.MultipartPart("image", "file", b"PNG", "image/png"),
                 cache.MultipartPart("texts", "field", b"wine bottle")]
        gx10_parts = [gx10.MultipartPart(p.name, p.kind, p.value, p.content_type) for p in parts]
        for semantic, gx10_semantic in (
            (cache.canonical_multipart(parts), gx10.canonical_multipart(gx10_parts)),
            (cache.canonical_json({"model": "m", "input": ["x"], "max_num_patches": 512}),
             gx10.canonical_json({"model": "m", "input": ["x"], "max_num_patches": 512})),
        ):
            arguments = dict(namespace="n", method="POST", path="/upstream/sam3/segment_multi",
                             query="a=1")
            self.assertEqual(cache.build_cache_key(semantic_body=semantic, **arguments),
                             gx10.build_cache_key(semantic_body=gx10_semantic, **arguments))

    def test_bypass_headers(self) -> None:
        self.assertTrue(cache.request_bypasses_cache({"cache-control": "max-age=0, no-cache"}))
        self.assertTrue(cache.request_bypasses_cache({"x-gx10-cache": "BYPASS"}))
        self.assertFalse(cache.request_bypasses_cache({"cache-control": "max-age=0"}))
        self.assertFalse(cache.request_bypasses_cache({}))


class EligibilityTests(unittest.TestCase):
    def test_expected_shapes(self) -> None:
        ok = cache.response_is_cacheable
        self.assertTrue(ok("visual-embeddings", 200, "application/json", b'{"data":[]}'))
        self.assertTrue(ok("sam3", 200, "application/json; charset=utf-8", b'{"instances":[]}'))
        self.assertTrue(ok("grounding-dino", 200, "application/json", b'{"instances":[]}'))
        self.assertFalse(ok("sam3", 503, "application/json", b'{"instances":[]}'))
        self.assertFalse(ok("sam3", 200, "text/html", b'{"instances":[]}'))
        self.assertFalse(ok("sam3", 200, "application/json", b'{"data":[]}'))
        self.assertFalse(ok("visual-embeddings", 200, "application/json", b"not json"))
        self.assertFalse(ok("other", 200, "application/json", b'{"data":[]}'))


class StoreTests(unittest.TestCase):
    def test_hit_keeps_host_and_body(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = store(directory)
            try:
                put(target, "k", b'{"instances":[]}', 100, host="rtx")
                entry = target.get("k", now=101)
                self.assertIsNotNone(entry)
                self.assertEqual((entry.host, entry.body, entry.status),
                                 ("rtx", b'{"instances":[]}', 200))
            finally:
                target.close()

    def test_ttl_removes_expired_entry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = store(directory, ttl=10)
            try:
                put(target, "old", b"123", 100)
                self.assertIsNone(target.get("old", now=111))
                self.assertEqual(target.stats()["entries"], 0)
            finally:
                target.close()

    def test_lru_limit_evicts_oldest_entry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = store(directory, max_bytes=5)
            try:
                put(target, "old", b"123", 100)
                put(target, "new", b"123", 101)
                self.assertIsNone(target.get("old", now=102))
                self.assertIsNotNone(target.get("new", now=102))
            finally:
                target.close()

    def test_replace_keeps_the_total_right(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = store(directory, max_bytes=8)
            try:
                put(target, "a", b"1234", 100)
                put(target, "a", b"1234", 101)  # the same key again: the total stays 4
                put(target, "b", b"1234", 102)  # 8 bytes in total: no eviction
                self.assertIsNotNone(target.get("a", now=103))
                self.assertIsNotNone(target.get("b", now=103))
            finally:
                target.close()

    def test_total_survives_a_reopen(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = store(directory, max_bytes=8)
            put(target, "a", b"1234", 100)
            target.close()
            target = store(directory, max_bytes=8)
            try:
                put(target, "b", b"12345", 101)  # 9 bytes in total: "a" goes
                self.assertIsNone(target.get("a", now=102))
                self.assertIsNotNone(target.get("b", now=102))
            finally:
                target.close()

    def test_purge_and_stats(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = store(directory)
            try:
                put(target, "a", b"12", 100, host="gx10")
                put(target, "b", b"34", 100, host="rtx")
                stats = target.stats()
                self.assertEqual((stats["entries"], stats["body_bytes"]), (2, 4))
                self.assertEqual({row["host"] for row in stats["by_target"]}, {"gx10", "rtx"})
                self.assertEqual(target.purge(), 2)
                self.assertEqual(target.stats()["entries"], 0)
            finally:
                target.close()


class KeyedLockTests(unittest.IsolatedAsyncioTestCase):
    async def test_same_key_runs_one_holder_at_a_time(self) -> None:
        locks = cache.KeyedLocks()
        active = 0
        peak = 0

        async def worker() -> None:
            nonlocal active, peak
            async with locks.hold("same"):
                active += 1
                peak = max(peak, active)
                await asyncio.sleep(0.01)
                active -= 1

        await asyncio.gather(worker(), worker(), worker())
        self.assertEqual(peak, 1)
        self.assertEqual(locks.size, 0)

    async def test_cancelled_waiter_gives_back_its_reference(self) -> None:
        locks = cache.KeyedLocks()
        release = asyncio.Event()

        async def holder() -> None:
            async with locks.hold("same"):
                await release.wait()

        async def waiter() -> None:
            async with locks.hold("same"):
                pass

        first = asyncio.create_task(holder())
        await asyncio.sleep(0)
        second = asyncio.create_task(waiter())
        await asyncio.sleep(0.01)
        second.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await second
        release.set()
        await first
        self.assertEqual(locks.size, 0)


if __name__ == "__main__":
    unittest.main()
