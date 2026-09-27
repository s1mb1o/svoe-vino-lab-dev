"""Tests of the shared codes of the barcode step (plan 58): `pipeline/barcode.py`, `only` of
`embedding_run.Catalogue.rank` and `embedding_run.EmbeddingBackend.ask`, and `only` of
`cluster_rerank.ClusterRerank.ask`.

A shared code is a GTIN or a QR URL of 2 or more Active wines. A unique code answers the
photo. A shared GTIN limits the match to its wines. A shared QR URL never decides.
"""
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import test_embedding_run as ER  # the catalogue fixtures (puts pipeline/ on sys.path)
import barcode  # noqa: E402
import cluster_rerank  # noqa: E402
import embedding_run  # noqa: E402

GTIN_ONE, GTIN_TWO = "04631168664979", "04630171632036"
QR_ONE, QR_TWO = "https://producer.example/wine/1", "https://belmaswinery.com/"
LOOKUP = {("gtin", GTIN_ONE): ["wine-a"], ("gtin", GTIN_TWO): ["wine-b", "wine-c"],
          ("qr_url", QR_ONE): ["wine-d"], ("qr_url", QR_TWO): ["wine-b", "wine-c"]}


def ean(value):
    return {"kind": "barcode", "format": "EAN13", "text": value.lstrip("0")}


def qr(value):
    return {"kind": "qr_code", "format": "QRCode", "text": value}


class PriorityTest(unittest.TestCase):
    def setUp(self):
        self.lookup = barcode.CodeLookup(LOOKUP)

    def test_a_unique_code_wins_over_a_shared_gtin_that_came_first(self):
        hit = self.lookup.find([ean(GTIN_TWO), qr(QR_ONE)])
        self.assertEqual((hit["code"], hit["slugs"]), (QR_ONE, ["wine-d"]))

    def test_a_shared_gtin_wins_over_a_shared_qr_url_that_came_first(self):
        hit = self.lookup.find([qr(QR_TWO), ean(GTIN_TWO)])
        self.assertEqual((hit["source"], hit["slugs"]), ("gtin", ["wine-b", "wine-c"]))

    def test_a_shared_qr_url_alone_decides_nothing(self):
        self.assertIsNone(self.lookup.find([qr(QR_TWO)]))
        self.assertEqual([h["code"] for h in barcode.shared_qr(self.lookup.hits([qr(QR_TWO)]))],
                         [QR_TWO])

    def test_hits_give_one_hit_for_each_stored_value(self):
        hits = self.lookup.hits([ean(GTIN_ONE), ean(GTIN_ONE), ean("4600000000000")])
        self.assertEqual([h["code"] for h in hits], [GTIN_ONE])


class ScanStopTest(unittest.TestCase):
    """Only a unique code stops the tile scan. `tiles` gives 9 + 25 tiles."""

    def decoder(self, whole, tile_codes):
        decoder = object.__new__(barcode.Decoder)
        decoder.options = barcode.check_options({})
        decoder.scaled = lambda image: image
        reads = []

        def read(image):
            reads.append(image.size)
            if len(reads) == 1:
                return list(whole)
            return list(tile_codes.get(len(reads) - 1, ()))

        decoder.read = read
        return decoder, reads

    def scan(self, whole, tile_codes):
        decoder, reads = self.decoder(whole, tile_codes)
        found, hit = decoder.scan(Image.new("RGB", (300, 200), "white"),
                                  barcode.CodeLookup(LOOKUP))
        return found, hit, len(reads)

    def test_a_unique_code_of_the_whole_photo_stops_the_scan(self):
        _found, hit, reads = self.scan([ean(GTIN_ONE)], {})
        self.assertEqual((hit["code"], reads), (GTIN_ONE, 1))

    def test_a_shared_gtin_does_not_stop_the_scan(self):
        _found, hit, reads = self.scan([ean(GTIN_TWO)], {3: [qr(QR_ONE)]})
        self.assertEqual((hit["code"], reads), (QR_ONE, 4))

    def test_shared_codes_alone_read_every_tile(self):
        found, hit, reads = self.scan([ean(GTIN_TWO), qr(QR_TWO)], {})
        self.assertEqual((hit["code"], reads), (GTIN_TWO, 1 + 9 + 25))
        self.assertEqual(len(found), 2)


class FakeInner:
    def __init__(self, answer):
        self.answer = answer
        self.id, self.top_k = "twin", 10
        self.catalogue = type("C", (), {"state": {"index_file": "x"}})()
        self.spec = {"id": "twin", "kind": "embedding", "label": "lab pipeline twin"}
        self.calls = []

    def ask(self, path, only=None):
        self.calls.append(only)
        return self.answer


class FakeDecoder:
    def __init__(self, found):
        self.found = list(found)

    def scan(self, image, lookup):
        return self.found, lookup.find(self.found)


TRACE = {"v": 1, "steps": [{"id": "embed", "start_ms": 0.0, "ms": 5.0}]}


class LimitTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.photo = str(Path(self.tmp.name) / "photo.png")
        Image.new("RGB", (40, 30), "white").save(self.photo)

    def tearDown(self):
        self.tmp.cleanup()

    def ask(self, found, answer, top_k=10):
        inner = FakeInner(answer)
        inner.top_k = top_k
        backend = barcode.CodeFirst(inner, barcode.check_options({}), None,
                                    decoder=FakeDecoder(found),
                                    lookup=barcode.CodeLookup(LOOKUP))
        return backend.ask(self.photo), inner

    def test_a_shared_gtin_limits_the_match_to_its_wines(self):
        (cands, _ms, status, error, trace), inner = self.ask(
            [ean(GTIN_TWO)], ([{"slug": "wine-c", "score": 0.8, "rank": 1}], 30, 200, None,
                              TRACE))
        self.assertEqual(inner.calls, [["wine-b", "wine-c"]])
        self.assertEqual((status, error), (200, None))
        self.assertEqual([(c["slug"], c["score"], c["rank"]) for c in cands],
                         [("wine-c", 0.8, 1), ("wine-b", None, 2)])
        # The ranked wine keeps the keys of the embedding; the wine with no vector is a
        # code candidate.
        self.assertNotIn("code", cands[0])
        self.assertEqual(cands[1]["code"], GTIN_TWO)
        step = trace["steps"][0]
        self.assertEqual((step["id"], step["out"]["mode"], step["out"]["hit"]["code"]),
                         ("barcode", "limit", GTIN_TWO))
        self.assertEqual([s["id"] for s in trace["steps"]], ["barcode", "embed"])

    def test_the_limited_answer_keeps_top_k(self):
        (cands, *_), _inner = self.ask(
            [ean(GTIN_TWO)], ([{"slug": "wine-b", "score": 0.7, "rank": 1}], 30, 200, None,
                              TRACE), top_k=1)
        self.assertEqual([c["slug"] for c in cands], ["wine-b"])

    def test_an_error_of_the_limited_match_stays_an_error(self):
        (cands, _ms, _status, error, _trace), _inner = self.ask(
            [ean(GTIN_TWO)], ([], 30, None, "SAM3 is down", TRACE))
        self.assertEqual((cands, error), ([], "SAM3 is down"))

    def test_a_shared_qr_url_gives_the_normal_match(self):
        (cands, *_rest, trace), inner = self.ask(
            [qr(QR_TWO)], ([{"slug": "wine-z", "score": 0.5, "rank": 1}], 30, 200, None,
                           TRACE))
        self.assertEqual(inner.calls, [None])
        self.assertEqual([c["slug"] for c in cands], ["wine-z"])
        out = trace["steps"][0]["out"]
        self.assertIsNone(out["hit"])
        self.assertNotIn("mode", out)
        self.assertEqual([h["code"] for h in out["shared_qr"]], [QR_TWO])

    def test_a_unique_code_still_answers_with_no_embedding(self):
        (cands, *_rest, trace), inner = self.ask([ean(GTIN_TWO), qr(QR_ONE)],
                                                 ([], 30, 200, None, TRACE))
        self.assertEqual(inner.calls, [])
        self.assertEqual([(c["slug"], c["score"]) for c in cands], [("wine-d", 1.0)])
        self.assertEqual(trace["steps"][0]["out"]["mode"], "answer")


class RankOnlyTest(ER.Temporary):
    def setUp(self):
        super().setUp()
        self.lab = ER.catalogue_lab(self.root)
        self.embedding = ER.build(self.lab)
        self.catalogue = embedding_run.Catalogue(self.embedding, self.lab.db_path)

    def test_the_rank_gives_only_the_wines_of_only(self):
        query = ER.vectors_of(self.catalogue, "green")
        trace = embedding_run.Trace()
        cands = self.catalogue.rank(query, 10, trace, only=["red", "blue"])
        self.assertEqual(sorted(c["slug"] for c in cands), ["blue", "red"])
        self.assertEqual([c["rank"] for c in cands], [1, 2])
        for step in trace.value()["steps"]:
            if step["id"] == "search":
                self.assertNotIn("green", [t["slug"] for t in step["out"]["top"]])
        self.assertEqual(self.catalogue.rank(query, 10, only=[]), [])
        self.assertEqual(self.catalogue.rank(query, 10, only=["nope"]), [])
        self.assertEqual(self.catalogue.rank(query, 10)[0]["slug"], "green")

    def test_the_backend_passes_only_to_the_rank(self):
        backend = embedding_run.build_backend(self.embedding, self.lab.db_path,
                                              make_model=lambda e: ER.ColourModel(),
                                              segmenter=ER.FakeSam3())
        path = str(self.root / "red.png")
        ER.query_photo("red").save(path)
        self.assertEqual(backend.ask(path)[0][0]["slug"], "red")
        cands, _ms, status, error, _trace = backend.ask(path, only=["green", "blue"])
        self.assertEqual((status, error), (200, None))
        self.assertEqual(sorted(c["slug"] for c in cands), ["blue", "green"])


class RerankOnlyTest(unittest.TestCase):
    def test_the_rerank_passes_only_to_its_inner_backend(self):
        inner = FakeInner(([{"slug": "wine-b", "score": 0.7, "rank": 1}], 30, 200, None,
                           TRACE))
        backend = object.__new__(cluster_rerank.ClusterRerank)
        backend.inner = inner
        backend.options = {"window": 3}
        backend.book = type("Book", (), {"trigger": lambda self, cands, window: (None, None)})()
        backend.ask("photo.jpg", only=["wine-b", "wine-c"])
        backend.ask("photo.jpg")
        self.assertEqual(inner.calls, [["wine-b", "wine-c"], None])


if __name__ == "__main__":
    unittest.main()
