"""Tests of the shared codes of the barcode step (plans 58 and 64): `pipeline/barcode.py`,
`first` of `embedding_run.Catalogue.rank` and `embedding_run.EmbeddingBackend.ask`, and
`first` of `cluster_rerank.ClusterRerank` and `cluster_rerank.RuleBook.trigger`.

A shared code is a GTIN or a QR URL of 2 or more Active wines. A unique code answers the
photo. A shared GTIN puts its wines first, and the other wines stay below them (plan 64).
The cluster re-rank then compares only the wines of the GTIN. A shared QR URL never
decides.
"""
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import test_cluster_rerank as CR  # the rule fixtures; a module, so no test runs twice
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

    def ask(self, path, first=None):
        self.calls.append(first)
        return self.answer


class FakeDecoder:
    def __init__(self, found):
        self.found = list(found)

    def scan(self, image, lookup):
        return self.found, lookup.find(self.found)


TRACE = {"v": 1, "steps": [{"id": "embed", "start_ms": 0.0, "ms": 5.0}]}


def ranked(*pairs):
    """Return the candidates of an inner answer: (slug, score) in rank order."""
    return [{"slug": slug, "score": score, "rank": rank}
            for rank, (slug, score) in enumerate(pairs, 1)]


class FirstTest(unittest.TestCase):
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

    def test_a_shared_gtin_puts_its_wines_first_and_keeps_the_other_wines(self):
        # The inner rank puts the ranked wine of the GTIN first (Catalogue.rank).
        (cands, _ms, status, error, trace), inner = self.ask(
            [ean(GTIN_TWO)], (ranked(("wine-c", 0.6), ("wine-x", 0.9), ("wine-y", 0.8)),
                              30, 200, None, TRACE))
        self.assertEqual(inner.calls, [["wine-b", "wine-c"]])
        self.assertEqual((status, error), (200, None))
        # The wine of the GTIN with no vector goes after the ranked wine of the GTIN.
        # Each candidate keeps its own score.
        self.assertEqual([(c["slug"], c["score"], c["rank"]) for c in cands],
                         [("wine-c", 0.6, 1), ("wine-b", None, 2), ("wine-x", 0.9, 3),
                          ("wine-y", 0.8, 4)])
        # The ranked wines keep the keys of the embedding; the wine with no vector is a
        # code candidate.
        self.assertNotIn("code", cands[0])
        self.assertEqual(cands[1]["code"], GTIN_TWO)
        self.assertNotIn("code", cands[2])
        step = trace["steps"][0]
        self.assertEqual((step["id"], step["out"]["mode"], step["out"]["hit"]["code"]),
                         ("barcode", "first", GTIN_TWO))
        self.assertEqual([s["id"] for s in trace["steps"]], ["barcode", "embed"])

    def test_the_ranked_wines_of_the_gtin_keep_their_order(self):
        (cands, *_), _inner = self.ask(
            [ean(GTIN_TWO)], (ranked(("wine-b", 0.7), ("wine-c", 0.6), ("wine-x", 0.9)),
                              30, 200, None, TRACE))
        self.assertEqual([(c["slug"], c["rank"]) for c in cands],
                         [("wine-b", 1), ("wine-c", 2), ("wine-x", 3)])
        self.assertFalse(any("code" in c for c in cands))

    def test_the_answer_keeps_top_k(self):
        (cands, *_), _inner = self.ask(
            [ean(GTIN_TWO)], (ranked(("wine-c", 0.6), ("wine-x", 0.9)), 30, 200, None,
                              TRACE), top_k=2)
        self.assertEqual([c["slug"] for c in cands], ["wine-c", "wine-b"])
        (cands, *_), _inner = self.ask(
            [ean(GTIN_TWO)], (ranked(("wine-b", 0.7)), 30, 200, None, TRACE), top_k=1)
        self.assertEqual([c["slug"] for c in cands], ["wine-b"])

    def test_an_error_of_the_match_stays_an_error(self):
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


class RankFirstTest(ER.Temporary):
    def setUp(self):
        super().setUp()
        self.lab = ER.catalogue_lab(self.root)
        self.embedding = ER.build(self.lab)
        self.catalogue = embedding_run.Catalogue(self.embedding, self.lab.db_path)
        self.query = ER.vectors_of(self.catalogue, "green")

    def test_the_wines_of_first_go_first_with_their_own_scores(self):
        normal = self.catalogue.rank(self.query, 10)
        self.assertEqual(normal[0]["slug"], "green")
        trace = embedding_run.Trace()
        cands = self.catalogue.rank(self.query, 10, trace, first=["red", "blue"])
        others = [c["slug"] for c in normal if c["slug"] != "green"]
        self.assertEqual([c["slug"] for c in cands], others + ["green"])
        self.assertEqual([c["rank"] for c in cands], [1, 2, 3])
        self.assertEqual({c["slug"]: c["score"] for c in cands},
                         {c["slug"]: c["score"] for c in normal})
        # The rank limits no wine: each search step still sees the best wine.
        tops = [[t["slug"] for t in step["out"]["top"]]
                for step in trace.value()["steps"] if step["id"] == "search"]
        self.assertTrue(tops)
        for top in tops:
            self.assertIn("green", top)

    def test_a_wine_of_first_outside_the_top_k_comes_back(self):
        self.assertEqual([c["slug"] for c in self.catalogue.rank(self.query, 1)], ["green"])
        self.assertEqual([c["slug"] for c in self.catalogue.rank(self.query, 1,
                                                                 first=["blue"])], ["blue"])

    def test_an_empty_or_unknown_first_gives_the_normal_rank(self):
        normal = self.catalogue.rank(self.query, 10)
        self.assertEqual(self.catalogue.rank(self.query, 10, first=[]), normal)
        self.assertEqual(self.catalogue.rank(self.query, 10, first=["nope"]), normal)

    def test_the_backend_passes_first_to_the_rank(self):
        backend = embedding_run.build_backend(self.embedding, self.lab.db_path,
                                              make_model=lambda e: ER.ColourModel(),
                                              segmenter=ER.FakeSam3())
        path = str(self.root / "red.png")
        ER.query_photo("red").save(path)
        self.assertEqual(backend.ask(path)[0][0]["slug"], "red")
        cands, _ms, status, error, _trace = backend.ask(path, first=["green", "blue"])
        self.assertEqual((status, error), (200, None))
        self.assertEqual(sorted(c["slug"] for c in cands[:2]), ["blue", "green"])
        self.assertEqual(cands[2]["slug"], "red")


class FirstInner(CR.Inner):
    """The base backend of the re-rank tests, with `first` (plan 64)."""

    def __init__(self, answer):
        super().__init__(answer)
        self.calls = []

    def ask(self, path, first=None):
        self.calls.append(first)
        return self.answer


class RerankFirstTest(unittest.TestCase):
    """The window of a shared GTIN (plan 64). The rule `CR.sheet_rule()` expects
    A 30/70, B 50/50, and C 70/30. A and B are the wines of the GTIN."""

    def make(self, rules, answer, vlm):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        fixture = CR.Fixture(self.tmp.name, rules)
        options = cluster_rerank.check_options({"rules": "rules", "vlm": "fake-vlm"})
        self.inner = FirstInner(answer)
        backend = cluster_rerank.ClusterRerank(self.inner, options, fixture.config_path,
                                               fixture.db_path, ask_fn=vlm)
        backend.picture = lambda path: (b"png", "label")
        return backend

    def test_the_rerank_passes_first_to_its_inner_backend(self):
        backend = self.make([CR.sheet_rule()], (CR.cands(CR.D), 30, 200, None, TRACE),
                            CR.FakeVlm())
        backend.ask("photo.jpg", first=[CR.A, CR.B])
        backend.ask("photo.jpg")
        self.assertEqual(self.inner.calls, [[CR.A, CR.B], None])

    def test_a_card_that_is_not_a_wine_of_the_gtin_does_not_move(self):
        answer = (CR.cands(CR.A, CR.B, CR.C, CR.D), 30, 200, None, TRACE)
        # The answer 70/30 fits C alone. With no GTIN, C moves up (plan 48).
        backend = self.make([CR.sheet_rule()], answer, CR.FakeVlm('{"q1": "70/30"}'))
        self.assertEqual([c["slug"] for c in backend.ask("p")[0]], [CR.C, CR.A, CR.B, CR.D])
        # With the GTIN of A and B, the window holds A and B alone, so C stays.
        out = backend.ask("p", first=[CR.A, CR.B])[0]
        self.assertEqual([c["slug"] for c in out], [CR.A, CR.B, CR.C, CR.D])
        self.assertEqual(out[0]["explain"]["window"], [CR.A, CR.B])
        self.assertFalse(out[0]["explain"]["changed"])

    def test_the_rule_orders_the_wines_of_the_gtin(self):
        answer = (CR.cands(CR.A, CR.B, CR.C, CR.D), 30, 200, None, TRACE)
        backend = self.make([CR.sheet_rule()], answer, CR.FakeVlm('{"q1": "50/50"}'))
        out, _ms, status, error, trace = backend.ask("p", first=[CR.A, CR.B])
        self.assertEqual([c["slug"] for c in out], [CR.B, CR.A, CR.C, CR.D])
        self.assertEqual((status, error), (200, None))
        self.assertEqual(trace["steps"][-1]["out"]["window"], [CR.A, CR.B])

    def test_a_verdict_for_a_card_outside_the_window_keeps_the_base_order(self):
        vlm = CR.FakeVlm('{"wine": "C"}')
        backend = self.make([CR.verdict_rule((CR.A, CR.B, CR.C))],
                            (CR.cands(CR.A, CR.B, CR.C), 30, 200, None, TRACE), vlm)
        out = backend.ask("p", first=[CR.A, CR.B])[0]
        self.assertEqual([c["slug"] for c in out], [CR.A, CR.B, CR.C])
        # The prompt still lists every card of the cluster.
        self.assertIn("Name wine-c-12", vlm.calls[0]["content"][1]["text"])

    def test_one_wine_of_the_gtin_in_the_cluster_calls_no_vlm(self):
        vlm = CR.FakeVlm()
        answer = (CR.cands(CR.A, CR.B, CR.C), 30, 200, None, TRACE)
        backend = self.make([CR.sheet_rule((CR.A, CR.C))], answer, vlm)
        self.assertIs(backend.ask("p", first=[CR.A, CR.B]), answer)
        self.assertEqual(vlm.calls, [])

    def test_the_rank_1_card_must_be_a_wine_of_the_gtin(self):
        backend = self.make([CR.sheet_rule()], (CR.cands(CR.D), 30, 200, None, TRACE),
                            CR.FakeVlm())
        book = backend.book
        self.assertEqual(book.trigger(CR.cands(CR.C, CR.A, CR.B), 5, [CR.A, CR.B]),
                         (None, []))
        rule, positions = book.trigger(CR.cands(CR.A, CR.C, CR.B), 5, [CR.A, CR.B])
        self.assertEqual((rule["key"], positions), (CR.sheet_rule()["key"], [0, 2]))
        rule, positions = book.trigger(CR.cands(CR.A, CR.C, CR.B), 5)
        self.assertEqual(positions, [0, 1, 2])


if __name__ == "__main__":
    unittest.main()
