from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx

from model_proxy.app import create_app
from model_proxy.config import ProxyConfig
from tests.support import (
    GX10,
    RTX,
    SLEEPER,
    FakeHosts,
    connection_error,
    embeddings_answer,
    instances_answer,
    make_config,
    status_answer,
)


NAFLEX = "siglip2-so400m-patch16-naflex"
KIT = {"name": "kit", "kind": "bootstrap", "slots": 1, "models": ["sam3"],
       "ssh": {"target": "root@203.0.113.10", "local_port": 18191}}


def embed_body(text: str = "a", model: str = NAFLEX, **extra: Any) -> dict[str, Any]:
    return {"model": model, "input": [f"data:image/png;base64,{text}"], **extra}


def image(name: str = "a") -> dict[str, tuple[str, bytes, str]]:
    return {"image": ("image.png", f"PNG {name}".encode(), "image/png")}


@asynccontextmanager
async def running(config: ProxyConfig, fake: FakeHosts,
                  **options: Any) -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(config, transport=httpx.MockTransport(fake), background=False, **options)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                     base_url="http://proxy.test") as client:
            yield client


class AppTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._directory = tempfile.TemporaryDirectory()
        self.directory = self._directory.name

    def tearDown(self) -> None:
        self._directory.cleanup()

    def config(self, hosts: list[dict[str, Any]] | None = None, **limits: Any) -> ProxyConfig:
        return make_config(self.directory, hosts, **limits)


class CacheRouteTests(AppTestCase):
    async def test_embeddings_miss_then_hit_with_another_key_order(self) -> None:
        fake = FakeHosts()
        fake.on("gx10.test", embeddings_answer())
        async with running(self.config(), fake) as client:
            first = await client.post("/v1/embeddings", json=embed_body(max_num_patches=512))
            reordered = json.dumps({"max_num_patches": 512, **embed_body()})
            second = await client.post("/v1/embeddings", content=reordered,
                                       headers={"Content-Type": "application/json"})
        self.assertEqual(first.status_code, 200)
        self.assertEqual((first.headers["x-proxy-cache"], first.headers["x-proxy-host"]),
                         ("MISS", "gx10"))
        self.assertEqual((second.headers["x-proxy-cache"], second.headers["x-proxy-host"]),
                         ("HIT", "gx10"))
        self.assertIn("age", second.headers)
        self.assertEqual(first.content, second.content)
        calls = fake.inference_calls("gx10.test")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].content, first.request.content)  # the body is unchanged

    async def test_another_patch_budget_is_another_entry(self) -> None:
        fake = FakeHosts()
        fake.on("gx10.test", embeddings_answer())
        async with running(self.config(), fake) as client:
            for budget in (256, 512, 256):
                await client.post("/v1/embeddings", json=embed_body(max_num_patches=budget))
        self.assertEqual(len(fake.inference_calls("gx10.test")), 2)

    async def test_multipart_boundary_and_filename_share_one_entry(self) -> None:
        fake = FakeHosts()
        fake.on("gx10.test", instances_answer())
        async with running(self.config(), fake) as client:
            first = await client.post(
                "/upstream/sam3/segment_multi",
                data={"texts": "wine bottle", "threshold": "0.35"},
                files={"image": ("first.png", b"PNG", "image/png")},
            )
            second = await client.post(
                "/upstream/sam3/segment_multi",
                data={"threshold": "0.35", "texts": "wine bottle"},
                files={"image": ("renamed.png", b"PNG", "image/png")},
            )
        self.assertNotEqual(first.request.headers["content-type"],
                            second.request.headers["content-type"])
        self.assertEqual(first.headers["x-proxy-cache"], "MISS")
        self.assertEqual(second.headers["x-proxy-cache"], "HIT")
        calls = fake.inference_calls("gx10.test")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].content, first.request.read())  # the boundary stays
        self.assertEqual(calls[0].headers["content-type"], first.request.headers["content-type"])

    async def test_large_image_file_is_cached(self) -> None:
        # Starlette limits a non-file field to 1 MiB; a file part has no such limit.
        fake = FakeHosts()
        fake.on("gx10.test", instances_answer())
        big = {"image": ("image.png", b"\x89PNG" + b"x" * (3 * 1024 * 1024), "image/png")}
        async with running(self.config(), fake) as client:
            first = await client.post("/upstream/sam3/segment_multi", files=big,
                                      data={"texts": "wine bottle"})
            second = await client.post("/upstream/sam3/segment_multi", files=big,
                                       data={"texts": "wine bottle"})
        self.assertEqual((first.headers["x-proxy-cache"], second.headers["x-proxy-cache"]),
                         ("MISS", "HIT"))
        self.assertEqual(fake.inference_calls("gx10.test")[0].content, first.request.read())

    async def test_query_is_forwarded_and_is_part_of_the_key(self) -> None:
        fake = FakeHosts()
        fake.on("gx10.test", instances_answer())
        async with running(self.config(), fake) as client:
            await client.post("/upstream/sam3/segment?mode=a", files=image())
            await client.post("/upstream/sam3/segment?mode=b", files=image())
            again = await client.post("/upstream/sam3/segment?mode=a", files=image())
        calls = fake.inference_calls("gx10.test")
        self.assertEqual([call.url.query for call in calls], [b"mode=a", b"mode=b"])
        self.assertEqual(again.headers["x-proxy-cache"], "HIT")

    async def test_bypass_headers_skip_the_cache_and_reach_the_host(self) -> None:
        fake = FakeHosts()
        fake.on("gx10.test", embeddings_answer())
        async with running(self.config(), fake) as client:
            skipped = [
                await client.post("/v1/embeddings", json=embed_body(), headers=headers)
                for headers in ({"Cache-Control": "no-cache"}, {"X-GX10-Cache": "bypass"})
            ]
            first = await client.post("/v1/embeddings", json=embed_body())
            second = await client.post("/v1/embeddings", json=embed_body())
        self.assertEqual([r.headers["x-proxy-cache"] for r in skipped], ["BYPASS", "BYPASS"])
        calls = fake.inference_calls("gx10.test")
        self.assertEqual(calls[0].headers["cache-control"], "no-cache")
        self.assertEqual(calls[1].headers["x-gx10-cache"], "bypass")
        self.assertEqual((first.headers["x-proxy-cache"], second.headers["x-proxy-cache"]),
                         ("MISS", "HIT"))
        self.assertEqual(len(calls), 3)

    async def test_error_answers_are_not_stored(self) -> None:
        answers = iter([500, 200, 200])

        async def handler(_request: httpx.Request) -> httpx.Response:
            status = next(answers)
            body = {"instances": []} if status == 200 else {"error": "boom"}
            return httpx.Response(status, json=body)

        fake = FakeHosts()
        fake.on("gx10.test", handler)
        async with running(self.config(), fake) as client:
            statuses = []
            for _ in range(3):
                response = await client.post("/upstream/sam3/segment", files=image())
                statuses.append((response.status_code, response.headers["x-proxy-cache"]))
        self.assertEqual(statuses, [(500, "MISS"), (200, "MISS"), (200, "HIT")])

    async def test_concurrent_identical_misses_are_merged(self) -> None:
        fake = FakeHosts()
        fake.on("gx10.test", embeddings_answer(delay=0.03))
        async with running(self.config(), fake) as client:
            responses = await asyncio.gather(
                *(client.post("/v1/embeddings", json=embed_body()) for _ in range(3))
            )
        self.assertEqual(len(fake.inference_calls("gx10.test")), 1)
        self.assertEqual(sorted(r.headers["x-proxy-cache"] for r in responses),
                         ["HIT", "HIT", "MISS"])


class PassthroughTests(AppTestCase):
    async def test_other_requests_go_to_the_passthrough_host_unchanged(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(207, json={"method": request.method, "path": request.url.path,
                                             "query": request.url.query.decode(),
                                             "body": request.content.decode()},
                                  headers={"X-GX10-Cache": "BYPASS"})

        fake = FakeHosts()
        fake.on("gx10.test", handler)
        async with running(self.config(), fake) as client:
            models = await client.get("/v1/models?x=1")
            health = await client.get("/upstream/sam3/health")
            other = await client.post("/upstream/sam3/unknown", content=b"raw")
            running_models = await client.get("/running")
        self.assertEqual(models.status_code, 207)
        self.assertEqual(models.json(), {"method": "GET", "path": "/v1/models", "query": "x=1",
                                         "body": ""})
        self.assertEqual((models.headers["x-proxy-cache"], models.headers["x-proxy-host"]),
                         ("BYPASS", "gx10"))
        self.assertEqual(models.headers["x-gx10-cache"], "BYPASS")
        self.assertEqual(health.json()["path"], "/upstream/sam3/health")
        self.assertEqual(other.json()["body"], "raw")
        self.assertEqual(running_models.json(), {"running": []})

    async def test_model_that_no_host_lists_is_not_cached(self) -> None:
        fake = FakeHosts()
        fake.on("gx10.test", embeddings_answer())
        async with running(self.config(), fake) as client:
            responses = [
                await client.post("/v1/embeddings",
                                  json=embed_body(model="dinov3-vitb16-pretrain-lvd1689m"))
                for _ in range(2)
            ]
        self.assertEqual([r.headers["x-proxy-cache"] for r in responses], ["BYPASS", "BYPASS"])
        self.assertEqual(len(fake.inference_calls("gx10.test")), 2)

    async def test_passthrough_host_down_gives_502(self) -> None:
        fake = FakeHosts()
        fake.down.add("gx10.test")
        async with running(self.config(), fake) as client:
            response = await client.get("/v1/models")
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["error"], "upstream_unavailable")


class DispatchTests(AppTestCase):
    async def test_requests_spread_over_hosts_within_their_slots(self) -> None:
        fake = FakeHosts()
        fake.active["rtx.test"] = RTX["models"]
        fake.on("gx10.test", instances_answer(delay=0.05, tag="gx10"))
        fake.on("rtx.test", instances_answer(delay=0.05, tag="rtx"))
        config = self.config([dict(GX10, slots=1), dict(RTX, slots=1)])
        async with running(config, fake) as client:
            responses = await asyncio.gather(
                *(client.post("/upstream/sam3/segment", files=image(str(i))) for i in range(6))
            )
        self.assertEqual({r.status_code for r in responses}, {200})
        self.assertEqual(len(fake.inference_calls("gx10.test")) +
                         len(fake.inference_calls("rtx.test")), 6)
        self.assertGreater(len(fake.inference_calls("rtx.test")), 0)
        self.assertGreater(len(fake.inference_calls("gx10.test")), 0)
        self.assertEqual((fake.peak["gx10.test"], fake.peak["rtx.test"]), (1, 1))
        hosts = {r.headers["x-proxy-host"] for r in responses}
        self.assertEqual(hosts, {"gx10", "rtx"})

    async def test_grounding_dino_goes_only_to_the_host_that_lists_it(self) -> None:
        fake = FakeHosts()
        fake.active["rtx.test"] = RTX["models"]
        fake.on("gx10.test", instances_answer(delay=0.02))
        fake.on("rtx.test", instances_answer(delay=0.02))
        config = self.config([dict(GX10, slots=1), dict(RTX, slots=4)])
        async with running(config, fake) as client:
            responses = await asyncio.gather(
                *(client.post("/upstream/grounding-dino-base/detect", files=image(str(i)),
                              data={"texts": "wine bottle"})
                  for i in range(4))
            )
        self.assertEqual({r.headers["x-proxy-host"] for r in responses}, {"gx10"})
        self.assertEqual(fake.inference_calls("rtx.test"), [])

    async def test_bootstrap_host_gets_only_its_active_models(self) -> None:
        fake = FakeHosts()
        fake.active["rtx.test"] = [NAFLEX]  # sam3 is configured but not running
        fake.on("gx10.test", instances_answer())
        fake.on("rtx.test", embeddings_answer())
        config = self.config([dict(RTX), dict(GX10)])
        async with running(config, fake) as client:
            sam3 = await client.post("/upstream/sam3/segment", files=image())
            naflex = await client.post("/v1/embeddings", json=embed_body())
        self.assertEqual(sam3.headers["x-proxy-host"], "gx10")
        self.assertEqual(naflex.headers["x-proxy-host"], "rtx")

    async def test_connection_error_tries_the_next_host_and_marks_the_host_down(self) -> None:
        fake = FakeHosts()
        fake.active["rtx.test"] = RTX["models"]
        fake.on("rtx.test", connection_error())
        fake.on("gx10.test", instances_answer())
        config = self.config([dict(RTX), dict(GX10)])
        async with running(config, fake) as client:
            response = await client.post("/upstream/sam3/segment", files=image())
            status = (await client.get("/_proxy/status")).json()
        self.assertEqual((response.status_code, response.headers["x-proxy-host"]), (200, "gx10"))
        rtx = next(host for host in status["hosts"] if host["name"] == "rtx")
        self.assertFalse(rtx["up"])
        self.assertIn("connection failed", rtx["reason"])
        self.assertEqual(rtx["models"]["sam3"]["errors"], 1)

    async def test_retryable_status_tries_the_next_host(self) -> None:
        fake = FakeHosts()
        fake.active["rtx.test"] = RTX["models"]
        fake.on("rtx.test", status_answer(503))
        fake.on("gx10.test", instances_answer())
        config = self.config([dict(RTX), dict(GX10)])
        async with running(config, fake) as client:
            response = await client.post("/upstream/sam3/segment", files=image())
        self.assertEqual((response.status_code, response.headers["x-proxy-host"]), (200, "gx10"))
        self.assertEqual(len(fake.inference_calls("rtx.test")), 1)

    async def test_last_answer_comes_back_when_each_host_fails(self) -> None:
        fake = FakeHosts()
        fake.active["rtx.test"] = RTX["models"]
        fake.on("rtx.test", status_answer(503, {"error": "rtx busy"}))
        fake.on("gx10.test", status_answer(429, {"error": "gx10 busy"}))
        config = self.config([dict(RTX), dict(GX10)])
        async with running(config, fake) as client:
            first = await client.post("/upstream/sam3/segment", files=image())
            second = await client.post("/upstream/sam3/segment", files=image())
        self.assertEqual((first.status_code, first.json()), (429, {"error": "gx10 busy"}))
        self.assertEqual(first.headers["x-proxy-host"], "gx10")
        self.assertEqual(second.headers["x-proxy-cache"], "MISS")
        self.assertEqual(len(fake.inference_calls("rtx.test")), 2)

    async def test_non_retryable_status_comes_back_at_once(self) -> None:
        fake = FakeHosts()
        fake.active["rtx.test"] = RTX["models"]
        fake.on("rtx.test", status_answer(422, {"detail": "bad image"}))
        fake.on("gx10.test", instances_answer())
        config = self.config([dict(RTX), dict(GX10)])
        async with running(config, fake) as client:
            response = await client.post("/upstream/sam3/segment", files=image())
        self.assertEqual((response.status_code, response.headers["x-proxy-host"]), (422, "rtx"))
        self.assertEqual(fake.inference_calls("gx10.test"), [])

    async def test_no_host_available(self) -> None:
        fake = FakeHosts()
        fake.down.add("gx10.test")
        async with running(self.config(), fake) as client:
            response = await client.post("/upstream/sam3/segment", files=image())
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"], "no_host_available")
        self.assertEqual(response.headers["retry-after"], "5")
        self.assertEqual(response.headers["x-proxy-cache"], "BYPASS")

    async def test_full_queue_gives_429(self) -> None:
        fake = FakeHosts()
        fake.on("gx10.test", instances_answer(delay=0.2))
        config = self.config([dict(GX10, slots=1)], queue_limit=1)
        async with running(config, fake) as client:
            responses = await asyncio.gather(
                *(client.post("/upstream/sam3/segment", files=image(str(i))) for i in range(3))
            )
        statuses = sorted(r.status_code for r in responses)
        self.assertEqual(statuses, [200, 200, 429])
        full = next(r for r in responses if r.status_code == 429)
        self.assertEqual((full.json()["error"], full.headers["retry-after"]), ("queue_full", "1"))

    async def test_request_too_large(self) -> None:
        fake = FakeHosts()
        async with running(self.config(max_request_size=16), fake) as client:
            response = await client.post("/v1/embeddings", json=embed_body("x" * 64))
        self.assertEqual(response.status_code, 413)
        self.assertEqual(fake.inference_calls("gx10.test"), [])


class TunnelHostTests(AppTestCase):
    async def test_ssh_host_is_used_while_its_tunnel_runs(self) -> None:
        fake = FakeHosts()
        fake.active["127.0.0.1:18191"] = ["sam3"]
        fake.on("127.0.0.1:18191", instances_answer(tag="kit"))
        fake.on("gx10.test", instances_answer(tag="gx10"))
        config = self.config([dict(KIT), dict(GX10)])
        async with running(config, fake, tunnel_command=lambda _ssh: SLEEPER) as client:
            response = await client.post("/upstream/sam3/segment", files=image())
            status = (await client.get("/_proxy/status")).json()
        self.assertEqual(response.headers["x-proxy-host"], "kit")
        kit = next(host for host in status["hosts"] if host["name"] == "kit")
        self.assertTrue(kit["tunnel"]["running"])
        self.assertEqual(kit["url"], "http://127.0.0.1:18191")

    async def test_ssh_host_is_down_while_its_tunnel_is_down(self) -> None:
        fake = FakeHosts()
        fake.active["127.0.0.1:18191"] = ["sam3"]
        fake.on("127.0.0.1:18191", instances_answer(tag="kit"))
        fake.on("gx10.test", instances_answer(tag="gx10"))
        config = self.config([dict(KIT), dict(GX10)])
        async with running(config, fake,
                           tunnel_command=lambda _ssh: ["/nonexistent/ssh"]) as client:
            response = await client.post("/upstream/sam3/segment", files=image())
            status = (await client.get("/_proxy/status")).json()
        self.assertEqual(response.headers["x-proxy-host"], "gx10")
        self.assertEqual(fake.inference_calls("127.0.0.1:18191"), [])
        kit = next(host for host in status["hosts"] if host["name"] == "kit")
        self.assertFalse(kit["up"])
        self.assertIn("cannot start", kit["tunnel"]["last_error"])

    async def test_disabled_host_gets_no_tunnel_and_no_request(self) -> None:
        fake = FakeHosts()
        fake.on("gx10.test", instances_answer())
        started: list[object] = []

        def command(ssh: object) -> list[str]:
            started.append(ssh)
            return SLEEPER

        config = self.config([dict(KIT, enabled=False), dict(GX10)])
        async with running(config, fake, tunnel_command=command) as client:
            response = await client.post("/upstream/sam3/segment", files=image())
        self.assertEqual(started, [])
        self.assertEqual(response.headers["x-proxy-host"], "gx10")


class StatusTests(AppTestCase):
    async def test_status_route(self) -> None:
        fake = FakeHosts()
        fake.on("gx10.test", embeddings_answer())
        async with running(self.config(), fake) as client:
            await client.post("/v1/embeddings", json=embed_body())
            await client.post("/v1/embeddings", json=embed_body())
            health = await client.get("/_proxy/health")
            status = (await client.get("/_proxy/status")).json()
        self.assertEqual(health.json(), {"status": "ok"})
        gx10 = status["hosts"][0]
        self.assertTrue(gx10["up"])
        self.assertEqual(gx10["models"][NAFLEX]["requests"], 1)
        self.assertEqual(status["cache"]["process"]["misses"], 1)
        self.assertEqual(status["cache"]["process"]["hits"], 1)
        self.assertEqual(status["cache"]["storage"]["entries"], 1)
        self.assertEqual(status["cache"]["storage"]["by_target"][0]["host"], "gx10")
        self.assertIn(NAFLEX, status["pooled_models"])


if __name__ == "__main__":
    unittest.main()
