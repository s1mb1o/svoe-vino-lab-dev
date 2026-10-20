"""Native cascade selection, protected evidence, and budget fallback."""

import asyncio
import json
from dataclasses import replace
from time import perf_counter
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import httpx

from matcher.cascade import BarcodeConfig, Cascade, CascadeConfig
from matcher.cascade_run import Answer, Budget, Run
from matcher.ocr import OCRError, OCRResult, OCRConfig, Reader
from matcher.selective_ocr import SelectiveOCRConfig, config, evidence, rank, trigger
from cascade_fakes import EAN_FULL, photo


class FakeReader:
    def __init__(self, text="River Cellar Cabernet", delay=0, fail=False):
        self.text, self.delay, self.fail = text, delay, fail
        self.calls = 0
        self.cancelled = False
    async def read(self, image, deadline):
        self.calls += 1
        try:
            await asyncio.sleep(self.delay)
            if self.fail:
                raise OCRError(502, "test reader failed", "OCR unavailable")
            return OCRResult(self.text)
        except asyncio.CancelledError:
            self.cancelled = True
            raise


class Services:
    async def start(self): pass
    async def close(self): pass
    async def embed(self, images, **kwargs): return [[1, 0]]
    async def scan(self, image, **kwargs): return [{"format": "EAN_13", "text": EAN_FULL}]


async def instant_cpu(run, function, *args):
    """Keep deadline tests independent of OS thread-start scheduling."""
    return function(*args)


class SelectiveTests(unittest.IsolatedAsyncioTestCase):
    def make(self, reader=None, settings=None, pairs=None, barcode=False):
        pairs = pairs or [("oak", .76), ("river", .75)]
        cards = {slug: {"name": "Oak Estate Chardonnay", "producer": "Oak Estate"}
                 for slug, _ in pairs}
        cards["river"] = {"name": "River Cellar Cabernet", "producer": "River Cellar", "grapes": "Cabernet"}
        bundle = SimpleNamespace(cards=cards, embedding={"model": "test"}, dimension=2,
                                 ranked=lambda view, vector: list(pairs))
        cfg = CascadeConfig(barcode=BarcodeConfig(crops=False) if barcode else None,
                            selective_ocr=settings or SelectiveOCRConfig())
        codes = {("gtin", "0" + EAN_FULL): ("oak",)} if barcode else None
        cascade = Cascade(cfg, bundle, Services(), codes=codes)
        cascade.ocr = reader or FakeReader()
        self.addAsyncCleanup(cascade.close)
        return cascade

    async def test_uncertain_answer_reads_once_and_changes_ranking_with_audit(self):
        cascade = self.make()
        pairs, trace = await cascade.match(photo(), 2, Budget(perf_counter()))
        self.assertEqual(pairs[0][0], "river")
        self.assertEqual(cascade.ocr.calls, 1)
        self.assertEqual(trace["decision"]["source"], "selective_ocr")
        audit = trace["decision"]["selective_ocr"]
        self.assertTrue(audit["changed"])
        self.assertEqual(audit["original_top1"], "oak")
        self.assertEqual(audit["status"], "applied")
        self.assertEqual(audit["pool_count"], 2)
        self.assertGreaterEqual(pairs[0][1], pairs[1][1])

    async def test_pool_can_recover_a_wine_outside_the_first_ten(self):
        pairs = [("other-%d" % i, .76 - .001 * i) for i in range(10)] + [("river", .745)]
        cascade = self.make(pairs=pairs)
        slug, trace = await cascade.predict(photo(), Budget(perf_counter()))
        self.assertEqual(slug, "river")
        self.assertEqual(trace["decision"]["selective_ocr"]["pool_count"], 11)

    async def test_http_reader_runs_through_cascade_without_an_extra_embedding(self):
        from matcher.services import Services as HttpServices
        requests = []
        async def handler(request):
            requests.append(request.url.path)
            if request.url.path == "/v1/embeddings":
                return httpx.Response(200, json={"data": [{"embedding": [1, 0]}]})
            body = json.loads(request.content)
            self.assertEqual(body["mime_type"], "image/png")
            return httpx.Response(200, json={"text": "River Cellar Cabernet"})
        cfg = replace(SelectiveOCRConfig(), ocr=OCRConfig(backend="http", endpoint="http://reader/read"))
        cascade = self.make(settings=cfg)
        services = HttpServices(siglip2="http://embedding")
        services.client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        cascade.services = services
        cascade.ocr = Reader(cfg.ocr, services)
        for _ in range(2):
            slug, trace = await cascade.predict(photo(), Budget(perf_counter()))
            self.assertEqual(slug, "river")
        self.assertEqual(requests.count("/v1/embeddings"), 2)
        self.assertEqual(requests.count("/read"), 1)
        self.assertTrue(trace["decision"]["selective_ocr"]["cached"])

    async def test_strong_answer_and_unique_code_do_not_read(self):
        cascade = self.make(pairs=[("oak", .90), ("river", .70)])
        slug, trace = await cascade.predict(photo(), Budget(perf_counter()))
        self.assertEqual(slug, "oak")
        self.assertEqual(cascade.ocr.calls, 0)
        self.assertFalse(trace["decision"]["selective_ocr"]["triggered"])
        cascade = self.make(barcode=True)
        slug, trace = await cascade.predict(photo(), Budget(perf_counter()))
        self.assertEqual(slug, "oak")
        self.assertEqual(cascade.ocr.calls, 0)

    async def test_empty_failed_and_timeout_readers_keep_original(self):
        for reader, status in ((FakeReader(text=""), "empty"), (FakeReader(text="xyzxyzxyz"), "no_match"),
                               (FakeReader(fail=True), "error"),
                               (FakeReader(delay=10), "error")):
            cascade = self.make(reader, replace(SelectiveOCRConfig(), timeout_seconds=.3))
            started = perf_counter()
            slug, trace = await cascade.predict(photo(size=(64, 64), packages=(), label=None), Budget(started))
            self.assertEqual(slug, "oak")
            self.assertEqual(trace["decision"]["selective_ocr"]["status"], status)
            self.assertLess(perf_counter() - started, 2)

    @patch.object(Run, "cpu", instant_cpu)
    async def test_soft_and_hard_limits_cancel_ocr_and_keep_original(self):
        for soft, hard in ((.3, 1), (None, .3)):
            reader = FakeReader(delay=10)
            cascade = self.make(reader)
            now = perf_counter()
            slug, trace = await cascade.predict(photo(size=(64, 64), packages=(), label=None),
                                               Budget(now, now + soft if soft else None, now + hard))
            self.assertEqual(slug, "oak")
            self.assertTrue(reader.cancelled)
            self.assertLess(perf_counter() - now, 1)
            self.assertIn(trace["decision"]["selective_ocr"]["status"], ("cancelled", "error"))

    async def test_disabled_stage_has_no_reader_and_no_trace_extension(self):
        cascade = self.make()
        cascade.ocr = None
        slug, trace = await cascade.predict(photo(), Budget(perf_counter()))
        self.assertEqual(slug, "oak")
        self.assertNotIn("selective_ocr", trace["decision"])

    async def test_shared_gtin_limits_the_ocr_candidate_pool(self):
        cascade = self.make()
        run = Run(cascade, photo(), Budget(perf_counter()), "match")
        from matcher.photo import decode
        run.photo = decode(photo())
        run.whole_ranking = [("oak", .76), ("river", .75), ("outsider", .74)]
        answer = Answer("gtin", [("oak", 1), ("river", 1), ("outsider", .74)],
                        code={"slugs": ["oak", "river"]})
        run.ocr_audit = {}
        result = await run._selective_ocr(answer, perf_counter() + 1)
        self.assertEqual(result[0][0], "river")
        self.assertEqual(run.ocr_audit["pool_count"], 2)


class ScoringTests(unittest.TestCase):
    def test_supported_evidence_overrides_thresholds(self):
        cfg = SelectiveOCRConfig()
        pairs = [("a", .6), ("b", .599)]
        self.assertFalse(trigger(pairs, "supported", cfg))
        self.assertFalse(trigger(pairs, "unique-code", cfg))
        self.assertFalse(trigger([], "error", cfg))
        self.assertTrue(trigger(pairs, "untriggered", cfg))
        self.assertTrue(trigger([("a", .9), ("b", .6)], "contradicted", cfg))

    def test_existing_vlm_verdict_is_preserved(self):
        rule = {"mode": "verdict"}
        run = SimpleNamespace(stages=[], cascade=SimpleNamespace(rules=SimpleNamespace(by_slug={"a": rule})),
                              vlm={"cluster": {"choice": "a"}})
        from unittest.mock import patch
        with patch("matcher.selective_ocr.rerank.verdict_choice", return_value="a"):
            self.assertEqual(evidence(run, Answer("rerank", [("a", .6)], rerank={"cluster": "cluster"})), "supported")

    def test_russian_normalization_and_structured_conflicts(self):
        cards = {"white": {"name": "Estate Cabernet", "producer": "Estate", "color": "white"},
                 "red": {"name": "Estate Cabernet", "producer": "Estate", "color": "red"}}
        pairs, details = rank([("white", .8), ("red", .8)], "Estate Cabernet red", cards, SelectiveOCRConfig())
        self.assertEqual(pairs[0][0], "red")
        self.assertEqual(next(d for d in details if d["slug"] == "white")["conflicts"], 1)
        from matcher.selective_ocr import tokens
        self.assertEqual(tokens("Каберне"), ["kaberne"])

    def test_config_bounds(self):
        for raw in ({"pool": 0}, {"side": 1}, {"timeout_seconds": float("nan")}, {"extra": 1}, {"enabled": 1}):
            with self.assertRaises(ValueError):
                config(raw)

    def test_cpu_scoring_stops_at_its_deadline(self):
        with self.assertRaises(TimeoutError):
            rank([("a", .8)], "label text", {"a": {"name": "label"}},
                 SelectiveOCRConfig(), perf_counter() - 1)
