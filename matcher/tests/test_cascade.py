"""Tests of the runtime of the backend `cascade`: the task graph, the time budget, and
the answer priority, with local fake services (plan 85 of the workbench)."""

import asyncio
import base64
from io import BytesIO
from time import monotonic, perf_counter
import time
import unittest

from PIL import Image

from matcher.cascade import BarcodeConfig, Cascade, CascadeConfig, RerankConfig, Sam3Config
from matcher.cascade_run import Budget
from matcher.protection import ImageRejected
from matcher.rerank import RuleBook
from matcher.services import Services

from cascade_fakes import (EAN_FULL, EAN_PACKAGE, EAN_SHARED, OTHER_PACKAGE, PACKAGE,
                           FakeServices, chat_body, colour_vector, dominant, make_bundle,
                           photo, rules, scene)


def gtin(ean):
    return "0" + ean


CODES = {
    ("gtin", gtin(EAN_PACKAGE)): ("wine-c",),
    ("gtin", gtin(EAN_FULL)): ("wine-d",),
    ("gtin", gtin(EAN_SHARED)): ("wine-a", "wine-b"),
    ("qr_url", "https://example.com/shared"): ("wine-b", "wine-c"),
}
NO_RERANK = CascadeConfig(whole_image=True, barcode=BarcodeConfig(), sam3=Sam3Config())
FULL = CascadeConfig(whole_image=True, barcode=BarcodeConfig(), sam3=Sam3Config(),
                     rerank=RerankConfig())


def scans(package=(), full=(), label=()):
    """Return a fake scanner that answers by the dominant colour of the scan image."""
    answers = {"red": package, "gray": full, "blue": label}

    def scan(image):
        return [{"text": text, "format": fmt} for text, fmt in answers.get(dominant(image), ())]
    return scan


def picture_of(payload):
    url = payload["messages"][0]["content"][0]["image_url"]["url"]
    return Image.open(BytesIO(base64.b64decode(url.split(",", 1)[1])))


class CascadeRunTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.fake = FakeServices()
        self.addCleanup(self.fake.close)

    async def cascade(self, config=NO_RERANK, codes=CODES, book=None):
        services = Services(
            siglip2=self.fake.siglip2,
            sam3=self.fake.sam3 if config.sam3 else None,
            scanner=self.fake.scanner if config.barcode else None,
            vlm=self.fake.vlm if config.rerank else None)
        if config.rerank is not None and book is None:
            book = RuleBook(*rules())
        cascade = Cascade(config, make_bundle(), services, codes=codes, rules=book)
        await cascade.start()
        self.addAsyncCleanup(cascade.close)
        return cascade

    @staticmethod
    def budget(answer_at=None, hard_at=None):
        now = perf_counter()
        return Budget(now, None if answer_at is None else now + answer_at,
                      None if hard_at is None else now + hard_at)

    async def timed_predict(self, cascade, body, budget):
        started = perf_counter()
        slug, trace = await cascade.predict(body, budget)
        return slug, trace, perf_counter() - started

    async def disconnected(self, route, wait=1.0):
        end = monotonic() + wait
        while monotonic() < end:
            if any(name == route for name, _ in self.fake.disconnects):
                return True
            await asyncio.sleep(0.02)
        return False

    # ---------------------------------------------------------------- the answers

    async def test_all_fast_answers_the_crop_ranking(self):
        cascade = await self.cascade()
        slug, trace = await cascade.predict(photo(), self.budget(2.0, 5.0))
        self.assertEqual(slug, "wine-a")
        self.assertEqual(trace["decision"]["source"], "crop")
        self.assertEqual(trace["decision"]["reason"], "done")
        self.assertEqual(trace["decision"]["package"]["label"], "wine bottle")
        self.assertEqual(trace["decision"]["label"]["method"], "seg")
        segment = self.fake.routes("segment")
        self.assertEqual(len(segment), 1)
        self.assertEqual(segment[0]["fields"]["texts"].decode(),
                         "wine bottle, can, packet, box, hand, label")
        self.assertEqual(segment[0]["fields"]["threshold"].decode(), "0.35")
        statuses = {stage["id"]: stage["status"] for stage in trace["stages"]}
        self.assertEqual(statuses["crop:1"], "ok")
        self.assertEqual(statuses["scan_package"], "ok")
        self.assertEqual(statuses["scan_label"], "ok")

    async def test_the_scans_see_the_photo_the_package_and_its_label(self):
        seen = []

        def scan(image):
            seen.append((dominant(image), max(image.size)))
            return []
        self.fake.scan = scan
        cascade = await self.cascade()
        await cascade.predict(photo(), self.budget(2.0, 5.0))
        self.assertCountEqual(seen, [("gray", 1600), ("red", 1600), ("blue", 1600)])
        engines = {request["fields"]["engine"].decode() for request in self.fake.routes("scan")}
        self.assertEqual(engines, {"zxing-cpp"})

    async def test_a_package_code_beats_the_full_photo_code(self):
        self.fake.scan = scans(package=[(EAN_PACKAGE, "EAN-13")], full=[(EAN_FULL, "EAN-13")])
        cascade = await self.cascade()
        slug, trace = await cascade.predict(photo(), self.budget(2.0, 5.0))
        self.assertEqual(slug, "wine-c")
        self.assertEqual(trace["decision"]["source"], "code_package")
        self.assertEqual(trace["decision"]["reason"], "final")
        self.assertEqual(trace["decision"]["code"]["code"], gtin(EAN_PACKAGE))

    async def test_a_label_code_answers_with_its_own_source(self):
        self.fake.scan = scans(label=[(EAN_PACKAGE, "EAN-13")])
        cascade = await self.cascade()
        slug, trace = await cascade.predict(photo(), self.budget(2.0, 5.0))
        self.assertEqual((slug, trace["decision"]["source"]), ("wine-c", "code_label"))

    async def test_the_full_photo_code_answers_when_the_crop_scans_find_none(self):
        self.fake.scan = scans(full=[(EAN_FULL, "EAN-13")])
        cascade = await self.cascade()
        slug, trace = await cascade.predict(photo(), self.budget(2.0, 5.0))
        self.assertEqual((slug, trace["decision"]["source"]), ("wine-d", "code_full"))
        ranked, _ = await cascade.match(photo(), 5, self.budget())
        self.assertEqual(ranked[0], ("wine-d", 1.0))
        self.assertEqual(ranked[1][0], "wine-a")

    async def test_the_full_photo_code_answers_at_answer_at_before_sam3(self):
        self.fake.scan = scans(full=[(EAN_FULL, "EAN-13")])
        self.fake.delays["segment"] = 1.5
        cascade = await self.cascade()
        slug, trace, elapsed = await self.timed_predict(cascade, photo(), self.budget(0.4, 5.0))
        self.assertEqual((slug, trace["decision"]["source"]), ("wine-d", "code_full"))
        self.assertEqual(trace["decision"]["reason"], "answer_at")
        self.assertLess(elapsed, 1.0)

    async def test_a_code128_that_is_not_a_gtin_and_other_formats_are_ignored(self):
        self.fake.scan = scans(full=[("ABC-123", "Code 128"), (EAN_FULL[:8], "EAN-8")])
        cascade = await self.cascade()
        slug, trace = await cascade.predict(photo(), self.budget(2.0, 5.0))
        self.assertEqual((slug, trace["decision"]["source"]), ("wine-a", "crop"))

    async def test_a_shared_gtin_puts_its_wines_first_in_ranking_order(self):
        self.fake.scan = scans(full=[(EAN_SHARED, "EAN-13")])
        cascade = await self.cascade()
        slug, trace = await cascade.predict(photo(), self.budget(2.0, 5.0))
        self.assertEqual((slug, trace["decision"]["source"]), ("wine-a", "gtin"))
        ranked, _ = await cascade.match(photo(), 5, self.budget())
        self.assertEqual(ranked[:2], [("wine-a", 1.0), ("wine-b", 1.0)])
        self.assertEqual(ranked[2][0], "wine-a2")

    async def test_a_shared_qr_url_never_decides(self):
        self.fake.scan = scans(full=[("https://example.com/shared", "QR Code")])
        cascade = await self.cascade()
        slug, trace = await cascade.predict(photo(), self.budget(2.0, 5.0))
        self.assertEqual((slug, trace["decision"]["source"]), ("wine-a", "crop"))

    async def test_a_verdict_reorders_the_cluster_and_keeps_the_position_scores(self):
        self.fake.chat = lambda payload: chat_body({"wine": "B"})
        cascade = await self.cascade(FULL)
        slug, trace = await cascade.predict(photo(), self.budget(2.0, 5.0))
        self.assertEqual((slug, trace["decision"]["source"]), ("wine-a2", "rerank"))
        self.assertTrue(trace["decision"]["rerank"]["changed"])
        payload = self.fake.routes("chat")[0]["fields"]
        self.assertEqual(payload["model"], "qwen3.5-9b-nvfp4")
        self.assertEqual((payload["temperature"], payload["max_tokens"]), (0, 256))
        self.assertEqual(payload["chat_template_kwargs"], {"enable_thinking": False})
        self.assertEqual(payload["response_format"]["type"], "json_schema")
        self.assertEqual(payload["response_format"]["json_schema"]["schema"]["properties"]
                         ["wine"]["enum"], ["A", "B", "unsure"])
        self.assertTrue(payload["messages"][0]["content"][1]["text"].startswith(
            "This is a photo of a wine bottle, or of its label. It shows one of these wines"))
        with picture_of(payload) as picture:
            self.assertEqual(max(picture.size), 1536)
            self.assertEqual(dominant(picture), "blue")
        ranked, _ = await cascade.match(photo(), 5, self.budget())
        self.assertEqual([slug for slug, _ in ranked[:2]], ["wine-a2", "wine-a"])
        self.assertAlmostEqual(ranked[0][1], 1.0, places=5)
        scores = [score for _, score in ranked]
        self.assertEqual(scores, sorted(scores, reverse=True))

    async def test_a_sheet_answer_scores_the_cards(self):
        self.fake.chat = lambda payload: chat_body({"q1": "Blue"})
        cascade = await self.cascade(FULL, book=RuleBook(*rules(mode="sheet")))
        slug, trace = await cascade.predict(photo(), self.budget(2.0, 5.0))
        self.assertEqual((slug, trace["decision"]["source"]), ("wine-a2", "rerank"))
        payload = self.fake.routes("chat")[0]["fields"]
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertIn('Options: "red", "blue", "other", "not visible"',
                      payload["messages"][0]["content"][1]["text"])

    async def test_a_cut_or_invalid_vlm_answer_keeps_the_base_order(self):
        for body in (chat_body({"wine": "B"}, "length"),
                     {"choices": [{"message": {"content": "no json"}}]}):
            with self.subTest(body=str(body)[:40]):
                self.fake.chat = lambda payload, body=body: body
                cascade = await self.cascade(FULL)
                slug, trace = await cascade.predict(photo(), self.budget(2.0, 5.0))
                self.assertEqual((slug, trace["decision"]["source"]), ("wine-a", "crop"))
                vlm = [stage for stage in trace["stages"] if stage["id"].startswith("vlm:")]
                self.assertEqual(vlm[0]["status"], "error")

    async def test_a_unique_code_needs_no_vlm(self):
        self.fake.scan = scans(package=[(EAN_PACKAGE, "EAN-13")])
        self.fake.chat = lambda payload: chat_body({"wine": "B"})
        # The code arrives before the crop ranking, so the trigger never holds.
        self.fake.delays["embed"] = 0.3
        cascade = await self.cascade(FULL)
        slug, _ = await cascade.predict(photo(), self.budget(2.0, 5.0))
        self.assertEqual(slug, "wine-c")
        await asyncio.sleep(0.1)
        self.assertEqual(self.fake.routes("chat"), [])

    # ---------------------------------------------------------------- the time budget

    async def test_slow_sam3_gives_the_whole_answer_at_answer_at(self):
        self.fake.delays["segment"] = 2.0
        cascade = await self.cascade()
        slug, trace, elapsed = await self.timed_predict(cascade, photo(), self.budget(0.4, 5.0))
        self.assertEqual((slug, trace["decision"]["source"]), ("wine-b", "whole"))
        self.assertEqual(trace["decision"]["reason"], "answer_at")
        self.assertGreaterEqual(elapsed, 0.38)
        self.assertLess(elapsed, 0.9)
        self.assertTrue(await self.disconnected("segment"))

    async def test_a_slow_vlm_is_cut_at_answer_at_and_its_connection_closes(self):
        self.fake.delays["chat"] = 3.0
        self.fake.chat = lambda payload: chat_body({"wine": "B"})
        cascade = await self.cascade(FULL)
        slug, trace, elapsed = await self.timed_predict(cascade, photo(), self.budget(0.8, 5.0))
        self.assertEqual((slug, trace["decision"]["source"]), ("wine-a", "crop"))
        self.assertEqual(trace["decision"]["reason"], "answer_at")
        self.assertLess(elapsed, 1.4)
        self.assertTrue(await self.disconnected("chat"))
        vlm = [stage for stage in trace["stages"] if stage["id"].startswith("vlm:")]
        self.assertEqual(vlm[0]["status"], "cancelled")

    async def test_with_no_answer_at_answer_at_the_first_answer_comes_after_it(self):
        self.fake.delays["segment"] = 0.8
        config = CascadeConfig(whole_image=False, barcode=BarcodeConfig(), sam3=Sam3Config())
        cascade = await self.cascade(config)
        slug, trace, elapsed = await self.timed_predict(cascade, photo(), self.budget(0.3, 5.0))
        self.assertEqual((slug, trace["decision"]["source"]), ("wine-a", "crop"))
        self.assertGreaterEqual(elapsed, 0.8)
        self.assertLess(elapsed, 2.0)

    async def test_everything_slow_gives_an_empty_slug_at_the_hard_limit(self):
        self.fake.delays.update(segment=5.0, scan=5.0)
        config = CascadeConfig(whole_image=False, barcode=BarcodeConfig(), sam3=Sam3Config())
        cascade = await self.cascade(config)
        slug, trace, elapsed = await self.timed_predict(cascade, photo(), self.budget(0.3, 0.8))
        self.assertEqual(slug, "")
        self.assertEqual(trace["decision"], {"source": "none", "reason": "timeout",
                                             "answered_ms": trace["decision"]["answered_ms"]})
        self.assertGreaterEqual(elapsed, 0.78)
        self.assertLess(elapsed, 1.5)

    async def test_match_has_no_cut_and_waits_for_the_vlm(self):
        self.fake.delays["chat"] = 0.8
        self.fake.chat = lambda payload: chat_body({"wine": "B"})
        cascade = await self.cascade(FULL)
        started = perf_counter()
        ranked, trace = await cascade.match(photo(), 3, self.budget())
        self.assertGreaterEqual(perf_counter() - started, 0.8)
        self.assertEqual([slug for slug, _ in ranked], ["wine-a2", "wine-a", "wine-b"])
        self.assertEqual(trace["decision"]["source"], "rerank")

    async def test_parallel_predicts_with_a_slow_vlm_return_near_answer_at(self):
        self.fake.delays["chat"] = 3.0
        self.fake.chat = lambda payload: chat_body({"wine": "B"})
        cascade = await self.cascade(FULL)
        started = perf_counter()
        results = await asyncio.gather(*(cascade.predict(photo(), self.budget(1.0, 5.0))
                                         for _ in range(4)))
        self.assertLess(perf_counter() - started, 2.0)
        self.assertEqual([slug for slug, _ in results], ["wine-a"] * 4)
        self.fake.delays["chat"] = 0.0
        slug, trace = await cascade.predict(photo(), self.budget(2.0, 5.0))
        self.assertEqual((slug, trace["decision"]["source"]), ("wine-a2", "rerank"))
        leftover = [task for task in asyncio.all_tasks()
                    if task is not asyncio.current_task() and not task.done()]
        self.assertEqual(leftover, [])

    # ---------------------------------------------------------------- SAM3 and errors

    async def test_packages_first_redoes_the_crop_for_another_package(self):
        def segment(nouns, size):
            if "label" in nouns:
                time.sleep(0.3)
                return scene(nouns, size, packages=(PACKAGE,))
            return scene(nouns, size, packages=(OTHER_PACKAGE,), label=None)
        self.fake.segment = segment
        config = CascadeConfig(whole_image=True, barcode=BarcodeConfig(),
                               sam3=Sam3Config(packages_first=True))
        cascade = await self.cascade(config)
        slug, trace = await cascade.predict(photo(packages=(PACKAGE, OTHER_PACKAGE)),
                                            self.budget(2.0, 5.0))
        self.assertEqual((slug, trace["decision"]["source"]), ("wine-a", "crop"))
        colours = []
        for request in self.fake.routes("embed"):
            raw = base64.b64decode(request["fields"]["input"][0].split(",", 1)[1])
            with Image.open(BytesIO(raw)) as image:
                colours.append(dominant(image))
        self.assertEqual(sorted(colours), ["gray", "green", "red"])
        texts = sorted(request["fields"]["texts"].decode() for request in self.fake.routes("segment"))
        self.assertEqual(texts, ["wine bottle, can, packet, box",
                                 "wine bottle, can, packet, box, hand, label"])

    async def test_the_same_package_in_both_answers_embeds_one_crop(self):
        config = CascadeConfig(whole_image=False, barcode=None,
                               sam3=Sam3Config(packages_first=True))
        cascade = await self.cascade(config)
        slug, _ = await cascade.predict(photo(), self.budget(2.0, 5.0))
        self.assertEqual(slug, "wine-a")
        self.assertEqual(len(self.fake.routes("embed")), 1)

    async def test_packages_first_keeps_the_whole_photo_until_the_package_is_final(self):
        # The provisional crop ranks before the whole photo. Then the full SAM3 answer
        # has no package, so the whole photo MUST answer.
        def embed(image):
            if dominant(image) == "gray":
                time.sleep(0.6)
            return colour_vector(image)

        def segment(nouns, size):
            if "label" in nouns:
                time.sleep(0.3)
                return scene(nouns, size, packages=())
            return scene(nouns, size, packages=(OTHER_PACKAGE,), label=None)
        self.fake.embed = embed
        self.fake.segment = segment
        config = CascadeConfig(whole_image=True, barcode=BarcodeConfig(),
                               sam3=Sam3Config(packages_first=True))
        cascade = await self.cascade(config)
        slug, trace = await cascade.predict(photo(packages=(PACKAGE, OTHER_PACKAGE)),
                                            self.budget(2.0, 5.0))
        self.assertEqual((slug, trace["decision"]["source"]), ("wine-b", "whole"))
        self.assertEqual([stage["status"] for stage in trace["stages"]
                          if stage["id"] == "whole"], ["ok"])

    async def test_a_close_up_with_no_package_uses_the_whole_ranking(self):
        self.fake.segment = lambda nouns, size: scene(nouns, size, packages=())
        config = CascadeConfig(whole_image=False, barcode=BarcodeConfig(), sam3=Sam3Config())
        cascade = await self.cascade(config)
        slug, trace = await cascade.predict(photo(), self.budget(2.0, 5.0))
        self.assertEqual((slug, trace["decision"]["source"]), ("wine-b", "whole"))
        self.assertNotIn("package", trace["decision"])
        self.assertEqual(trace["decision"]["label"]["method"], "seg")
        self.assertEqual(len(self.fake.routes("scan")), 1)

    async def test_failed_sam3_answers_from_the_whole_photo(self):
        self.fake.statuses["segment"] = 500
        cascade = await self.cascade()
        slug, trace = await cascade.predict(photo(), self.budget(2.0, 5.0))
        self.assertEqual((slug, trace["decision"]["source"]), ("wine-b", "whole"))
        # SAM3 gets one retry after HTTP 5xx.
        self.assertEqual(len(self.fake.routes("segment")), 2)

    async def test_when_every_service_fails_the_first_error_answers(self):
        self.fake.statuses.update(embed=500, segment=500, scan=500)
        cascade = await self.cascade()
        with self.assertRaises(Exception) as caught:
            await cascade.predict(photo(), self.budget(2.0, 5.0))
        self.assertEqual(caught.exception.status_code, 502)
        with self.assertRaises(Exception) as caught:
            await cascade.match(photo(), 5, self.budget())
        self.assertEqual(caught.exception.status_code, 502)

    async def test_a_damaged_image_is_422_and_calls_no_service(self):
        cascade = await self.cascade()
        with self.assertRaises(ImageRejected) as caught:
            await cascade.predict(b"\xff\xd8\xff\xe0" + b"0" * 64, self.budget(2.0, 5.0))
        self.assertEqual(caught.exception.status_code, 422)
        self.assertEqual(self.fake.requests, [])

    async def test_a_large_photo_gets_a_1600_copy_and_full_resolution_crops(self):
        # The photo is 4 times the base size; the SAM3 copy is 2 times the base size.
        big = tuple(4 * value for value in PACKAGE)
        body = photo(size=(2400, 3200), packages=(big,), label=None)
        seen = {}

        def segment(nouns, size):
            seen["size"] = size
            return scene(nouns, size, label=None)
        self.fake.segment = segment
        config = CascadeConfig(whole_image=False, barcode=None, sam3=Sam3Config(label=False))
        cascade = await self.cascade(config)
        slug, trace = await cascade.predict(body, self.budget(4.0, 8.0))
        self.assertEqual(slug, "wine-a")
        self.assertEqual(seen["size"], (1200, 1600))
        box = trace["decision"]["package"]["box"]
        # The refined mask grows by about half a blur sigma (16 px at this size).
        for got, want in zip(box, big):
            self.assertLessEqual(abs(got - want), 40)

    async def test_readiness_checks_siglip2_sam3_and_the_scanner_but_not_the_vlm(self):
        cascade = await self.cascade(FULL)
        await cascade.check_ready(photo(size=(60, 40)))
        routes = [(request["route"], request["path"]) for request in self.fake.requests]
        self.assertCountEqual(routes, [("embed", "/v1/embeddings"),
                                       ("health", "/sam3/health"),
                                       ("health", "/qr/health")])
        self.fake.statuses["health"] = 503
        with self.assertRaises(Exception) as caught:
            await cascade.check_ready(photo(size=(60, 40)))
        self.assertEqual(caught.exception.status_code, 502)


if __name__ == "__main__":
    unittest.main()
