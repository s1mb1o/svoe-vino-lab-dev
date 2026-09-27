"""Tests of the barcode step of the lab pipelines (plan 42): `pipeline/barcode.py`, the key
`barcode` of `pipeline/pipelines.py`, and the notes of a code answer in
`pipeline/embedding_run.py`.

A fake decoder and a fake embedding backend test the lookup and the answers. The tests of
the real decoder need zxing-cpp; they are skipped in a Python with no zxing-cpp. Run them
with `embedding_python`, for example `~/.venvs/svoe-vino-lab/bin/python`.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import barcode  # noqa: E402
import embedding_run  # noqa: E402
import embeddings  # noqa: E402
import labdb  # noqa: E402
import pipelines  # noqa: E402

try:
    import zxingcpp
except ModuleNotFoundError:
    zxingcpp = None


def options(**keys):
    return barcode.check_options(keys)


class OptionsTest(unittest.TestCase):
    def test_an_empty_mapping_takes_the_defaults(self):
        self.assertEqual(options(), {"formats": ["EAN13", "EAN8", "UPCA", "Code128"],
                                     "qr": True, "tile_scan": True, "max_side": 1600,
                                     "upscale": False, "code128_gtin_only": False})

    def test_the_options_of_the_matcher_are_kept(self):
        got = options(formats=["EAN13", "Code128"], code128_gtin_only=True, upscale=True)
        self.assertEqual(got["formats"], ["EAN13", "Code128"])
        self.assertTrue(got["code128_gtin_only"])
        self.assertTrue(got["upscale"])

    def test_bad_options_are_refused(self):
        cases = [(None, "MUST be a mapping"), ({"gtin_map": "x"}, "unknown option gtin_map"),
                 ({"formats": ["UPCE"]}, "unknown format UPCE"),
                 ({"formats": []}, "at least one format"),
                 ({"formats": "EAN13"}, "at least one format"),
                 ({"formats": ["EAN13", "EAN13"]}, "one time"),
                 ({"qr": "yes"}, "qr MUST be true or false"),
                 ({"max_side": 10}, "max_side MUST"), ({"max_side": True}, "max_side MUST")]
        for raw, message in cases:
            with self.subTest(raw=raw), self.assertRaisesRegex(embeddings.ConfigError, message):
                barcode.check_options(raw)

    def test_the_gtin13_check(self):
        self.assertTrue(barcode.is_gtin13("4630171630094"))
        self.assertFalse(barcode.is_gtin13("4630171630095"))
        self.assertFalse(barcode.is_gtin13("463017163009"))
        self.assertFalse(barcode.is_gtin13("LOT-2021-0094"))


EMBED = {"name": "gw", "backend": "openai", "base_url": "http://x/v1", "model": "m",
         "views": {"full": {"steps": [{"step": "segment", "target": "package"}]}}}


class PipelineKeyTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.path = self.root / "config.yaml"

    def tearDown(self):
        self.directory.cleanup()

    def load(self, *entries):
        config = {"rootdir": str(self.root), "database_file": "lab.sqlite3",
                  "embeddings": [EMBED], "pipeline": list(entries)}
        self.path.write_text(json.dumps(config), encoding="utf-8")
        return pipelines.load(str(self.path))

    def test_a_pipeline_of_the_backend_embedding_takes_the_key_barcode(self):
        settings = self.load({"name": "plain", "backend": "embedding", "embedding": "gw"},
                             {"name": "codes", "backend": "embedding", "embedding": "gw",
                              "barcode": {"upscale": True}})
        self.assertIsNone(settings.find("plain").barcode)
        self.assertEqual(settings.find("codes").barcode, options(upscale=True))

    def test_a_bad_barcode_key_keeps_its_error(self):
        settings = self.load({"name": "codes", "backend": "embedding", "embedding": "gw",
                              "barcode": {"formats": ["UPCE"]}})
        with self.assertRaisesRegex(embeddings.ConfigError, "unknown format UPCE"):
            settings.find("codes")

    def test_the_remote_backend_takes_no_key_barcode(self):
        settings = self.load({"name": "remote", "backend": "svoe-vino-ru",
                              "url": "https://api.example.test/v1", "barcode": {}})
        with self.assertRaisesRegex(embeddings.ConfigError, "takes no barcode"):
            settings.find("remote")

    def test_the_project_config_holds_a_barcode_twin_of_each_embedding_pipeline(self):
        settings = pipelines.load(str(ROOT / "config.yaml"))
        entries = {name: (pipeline, error) for name, pipeline, error in settings.entries}
        plain = [name for name, (pipeline, error) in entries.items()
                 if pipeline and pipeline.backend == "embedding" and pipeline.barcode is None]
        self.assertEqual(len(plain), 26)
        for name in plain:
            with self.subTest(name=name):
                twin, error = entries["barcode-" + name]
                self.assertIsNone(error)
                self.assertEqual(twin.embedding, entries[name][0].embedding)
                self.assertEqual(twin.views, entries[name][0].views)
                self.assertEqual(twin.barcode, options(
                    formats=["EAN13", "Code128"], code128_gtin_only=True, qr=True,
                    tile_scan=True, max_side=1600, upscale=True))


class LookupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "lab.sqlite3")
        conn = labdb.connect(self.db, create=True)
        with conn:
            conn.executemany(
                "INSERT INTO wine_catalog (wine_slug, name, producer, category, color, "
                "region, description, csv_photo_name) "
                "VALUES (?, 'n', 'p', 'c', 'co', 'r', 'd', 'x.webp')",
                [(slug,) for slug in ("wine-a", "wine-b", "wine-c", "wine-off")])
            conn.execute("UPDATE wine_catalog SET state = 'Disabled' "
                         "WHERE wine_slug = 'wine-off'")
            conn.executemany("INSERT INTO wine_code (wine_slug, kind, value) VALUES (?, ?, ?)", [
                ("wine-a", "gtin", "04631168664979"),
                ("wine-b", "gtin", "00012345678905"),
                ("wine-c", "qr_url", "https://producer.example/wine/1"),
                ("wine-b", "qr_url", "https://producer.example/wine/1"),
                ("wine-off", "gtin", "04630171630094"),
                ("wine-c", "barcode", "LOT-1")])
        conn.close()
        self.lookup = barcode.CodeLookup.load(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def code(text, kind="barcode", fmt="EAN13"):
        return {"kind": kind, "format": fmt, "text": text}

    def test_the_lookup_holds_the_gtins_and_the_qr_urls_of_the_active_wines(self):
        self.assertEqual(self.lookup.counts, {"gtin": 2, "qr_url": 1})

    def test_an_ean13_finds_its_gtin14(self):
        hit = self.lookup.find([self.code("4631168664979")])
        self.assertEqual(hit, {"source": "gtin", "code": "04631168664979",
                               "read": "4631168664979", "format": "EAN13",
                               "slugs": ["wine-a"]})

    def test_a_upca_finds_its_gtin14(self):
        hit = self.lookup.find([self.code("012345678905", fmt="UPCA")])
        self.assertEqual(hit["slugs"], ["wine-b"])

    def test_a_shared_qr_url_gives_each_wine_in_slug_order(self):
        found = [self.code("URL:https://PRODUCER.example:443/wine/1#label",
                           kind="qr_code", fmt="QRCode")]
        [hit] = self.lookup.hits(found)
        self.assertEqual(hit["source"], "qr_url")
        self.assertEqual(hit["slugs"], ["wine-b", "wine-c"])
        # A shared QR URL never decides the answer (plan 58).
        self.assertIsNone(self.lookup.find(found))

    def test_no_hit_for_a_disabled_wine_a_bad_value_or_the_kind_barcode(self):
        for text in ("4630171630094", "4631168664970", "LOT-1", "hello"):
            with self.subTest(text=text):
                self.assertIsNone(self.lookup.find([self.code(text, fmt="Code128")]))

    def test_the_first_code_with_a_hit_wins(self):
        hit = self.lookup.find([self.code("4600000000000"), self.code("012345678905"),
                                self.code("4631168664979")])
        self.assertEqual(hit["slugs"], ["wine-b"])


class FakeInner:
    def __init__(self, answer):
        self.answer = answer
        self.id, self.top_k = "twin", 10
        self.catalogue = type("C", (), {"state": {"index_file": "x"}})()
        self.spec = {"id": "twin", "kind": "embedding", "label": "lab pipeline twin"}
        self.paths = []

    def ask(self, path):
        self.paths.append(path)
        return self.answer


class FakeDecoder:
    def __init__(self, found=(), hit=None, error=None):
        self.found, self.hit, self.error = list(found), hit, error
        self.scans = 0

    def scan(self, image, lookup):
        self.scans += 1
        if self.error:
            raise self.error
        return self.found, self.hit


HIT = {"source": "gtin", "code": "04631168664979", "read": "4631168664979",
       "format": "EAN13", "slugs": ["wine-a"]}
FOUND = [{"kind": "barcode", "format": "EAN13", "text": "4631168664979"}]
INNER_TRACE = {"v": 1, "steps": [{"id": "input", "start_ms": 0.0, "ms": 2.0},
                                 {"id": "embed", "start_ms": 2.0, "ms": 5.0}]}


class CodeFirstTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.photo = str(Path(self.tmp.name) / "photo.png")
        Image.new("RGB", (40, 30), "white").save(self.photo)
        self.lookup = barcode.CodeLookup({("gtin", "04631168664979"): ["wine-a"]})

    def tearDown(self):
        self.tmp.cleanup()

    def backend(self, decoder, inner=None, lookup=None):
        inner = inner or FakeInner(([{"slug": "wine-z", "score": 0.5, "rank": 1}], 40, 200,
                                    None, INNER_TRACE))
        return barcode.CodeFirst(inner, options(), None, decoder=decoder,
                                 lookup=self.lookup if lookup is None else lookup), inner

    def test_a_hit_answers_with_each_wine_of_the_code_and_no_embedding(self):
        backend, inner = self.backend(FakeDecoder(FOUND, HIT))
        cands, ms, status, error, trace = backend.ask(self.photo)
        self.assertEqual(inner.paths, [])
        self.assertEqual((status, error), (200, None))
        self.assertEqual([(c["slug"], c["score"], c["rank"]) for c in cands],
                         [("wine-a", 1.0, 1)])
        self.assertEqual({k: cands[0][k] for k in ("source", "code", "read", "format")},
                         {k: HIT[k] for k in ("source", "code", "read", "format")})
        self.assertEqual([step["id"] for step in trace["steps"]], ["barcode"])
        self.assertEqual(trace["steps"][0]["out"], {"codes": FOUND, "hit": HIT,
                                                    "mode": "answer"})

    def test_a_hit_keeps_top_k_wines(self):
        backend, inner = self.backend(FakeDecoder(FOUND, HIT))
        inner.top_k = backend.top_k = 1
        self.assertEqual([c["slug"] for c in backend.ask(self.photo)[0]], ["wine-a"])

    def test_a_miss_gives_the_answer_of_the_embedding_after_the_barcode_step(self):
        backend, inner = self.backend(FakeDecoder(FOUND, None))
        cands, ms, status, error, trace = backend.ask(self.photo)
        self.assertEqual(inner.paths, [self.photo])
        self.assertEqual([c["slug"] for c in cands], ["wine-z"])
        self.assertGreaterEqual(ms, 40)
        steps = trace["steps"]
        self.assertEqual([step["id"] for step in steps], ["barcode", "input", "embed"])
        self.assertEqual(steps[0]["out"], {"codes": FOUND, "hit": None})
        self.assertEqual(steps[1]["start_ms"], steps[0]["ms"])
        self.assertAlmostEqual(steps[2]["start_ms"] - steps[1]["start_ms"], 2.0, places=1)
        self.assertEqual(INNER_TRACE["steps"][1]["start_ms"], 2.0)

    def test_a_miss_of_an_inner_backend_with_no_trace_gets_the_barcode_step_alone(self):
        inner = FakeInner(([], 10, 200, None))
        backend, _ = self.backend(FakeDecoder(), inner)
        trace = backend.ask(self.photo)[4]
        self.assertEqual([step["id"] for step in trace["steps"]], ["barcode"])

    def test_a_decoder_error_is_recorded_and_the_embedding_answers(self):
        backend, inner = self.backend(FakeDecoder(error=RuntimeError("broken")))
        cands, _ms, _status, error, trace = backend.ask(self.photo)
        self.assertEqual(inner.paths, [self.photo])
        self.assertIsNone(error)
        self.assertEqual(trace["steps"][0]["error"], "RuntimeError: broken")

    def test_no_decode_when_the_lookup_is_empty(self):
        decoder = FakeDecoder(FOUND, HIT)
        backend, inner = self.backend(decoder, lookup=barcode.CodeLookup({}))
        trace = backend.ask(self.photo)[4]
        self.assertEqual(decoder.scans, 0)
        self.assertEqual(inner.paths, [self.photo])
        self.assertIn("skipped", trace["steps"][0]["out"])

    def test_the_spec_records_the_options_and_the_codes(self):
        backend, _ = self.backend(FakeDecoder())
        self.assertEqual(backend.spec["kind"], "embedding")
        self.assertEqual(backend.spec["barcode"]["engine"], "zxing-cpp")
        self.assertEqual(backend.spec["barcode"]["codes"], {"gtin": 1, "qr_url": 0})
        self.assertEqual(backend.spec["barcode"]["max_side"], 1600)


class CodeAnswerNotesTest(unittest.TestCase):
    CAND = {"slug": "wine-a", "score": 1.0, "rank": 1, "source": "gtin",
            "code": "04631168664979", "read": "4631168664979", "format": "EAN13"}

    def test_the_model_inputs_of_a_code_answer(self):
        answer = embedding_run.model_inputs({"views": {}}, "/no/such/photo.png", [self.CAND])
        self.assertEqual(answer["inputs"], [])
        self.assertIn("The code lookup answered this photo: gtin 04631168664979",
                      answer["notes"][0])

    def test_the_items_of_a_code_candidate(self):
        answer = embedding_run.candidate_items({"embedding": "x"}, self.CAND, "/no/db")
        self.assertEqual((answer["score"], answer["items"], answer["views"]), (1.0, [], {}))
        self.assertIn("The code lookup gave this wine", answer["notes"][0])


L = ["0001101", "0011001", "0010011", "0111101", "0100011",
     "0110001", "0101111", "0111011", "0110111", "0001011"]
G = ["0100111", "0110011", "0011011", "0100001", "0011101",
     "0111001", "0000101", "0010001", "0001001", "0010111"]
R = ["1110010", "1100110", "1101100", "1000010", "1011100",
     "1001110", "1010000", "1000100", "1001000", "1110100"]
PARITY = ["LLLLLL", "LLGLGG", "LLGGLG", "LLGGGL", "LGLLGG",
          "LGGLLG", "LGGGLL", "LGLGLG", "LGLGGL", "LGGLGL"]


def ean13(code, module=4, height=220, quiet=12):
    """Draw a valid EAN-13, as `svoe-vino-matcher/scripts/barcode_control.py` does. The
    writer of zxing-cpp is not the control: the test MUST NOT trust the code under test."""
    first, left, right = int(code[0]), code[1:7], code[7:]
    bits = "101"
    for parity, digit in zip(PARITY[first], left):
        bits += (L if parity == "L" else G)[int(digit)]
    bits += "01010" + "".join(R[int(digit)] for digit in right) + "101"
    pixels = np.full((height, (len(bits) + 2 * quiet) * module), 255, dtype=np.uint8)
    for number, bit in enumerate(bits):
        if bit == "1":
            x = (quiet + number) * module
            pixels[20:height - 20, x:x + module] = 0
    return Image.fromarray(pixels).convert("RGB")


@unittest.skipIf(zxingcpp is None, "zxing-cpp is not installed; use embedding_python")
class DecoderTest(unittest.TestCase):
    """The control of the decoder: it MUST read a code that is known to be there."""

    def setUp(self):
        self.lookup = barcode.CodeLookup({("gtin", "04600682000181"): ["wine-a"],
                                          ("qr_url", "https://producer.example/wine/1"):
                                              ["wine-q"]})

    def test_the_decoder_reads_drawn_ean13_codes(self):
        decoder = barcode.Decoder(options(tile_scan=False))
        for code in ("4600682000181", "5901234123457", "9780201379624"):
            with self.subTest(code=code):
                found, _hit = decoder.scan(ean13(code), barcode.CodeLookup({}))
                self.assertIn({"kind": "barcode", "format": "EAN13", "text": code}, found)

    def test_a_drawn_ean13_on_a_photo_is_a_hit(self):
        photo = Image.new("RGB", (1200, 900), (180, 150, 120))
        photo.paste(ean13("4600682000181", module=3), (700, 500))
        found, hit = barcode.Decoder(options()).scan(photo, self.lookup)
        self.assertEqual(hit["slugs"], ["wine-a"])
        self.assertEqual(hit["code"], "04600682000181")

    def test_a_qr_code_is_a_hit(self):
        code = zxingcpp.write_barcode(zxingcpp.BarcodeFormat.QRCode,
                                      "https://PRODUCER.example/wine/1", 300, 300)
        image = Image.fromarray(np.asarray(code)).convert("RGB")
        _found, hit = barcode.Decoder(options()).scan(image, self.lookup)
        self.assertEqual((hit["source"], hit["slugs"]), ("qr_url", ["wine-q"]))

    def test_code128_is_kept_only_as_a_gtin13(self):
        decoder = barcode.Decoder(options(formats=["EAN13", "Code128"],
                                          code128_gtin_only=True, tile_scan=False))

        def read(text):
            code = zxingcpp.write_barcode(zxingcpp.BarcodeFormat.Code128, text, 400, 160)
            image = Image.fromarray(np.asarray(code)).convert("RGB")
            return [item["text"] for item in decoder.read(image)]

        self.assertEqual(read("4630171630094"), ["4630171630094", "4630171630094"])
        self.assertEqual(read("4630171630095"), [])
        self.assertEqual(read("LOT-2021-0094"), [])

    def test_upscale_scales_a_small_photo_up_to_max_side(self):
        small = Image.new("RGB", (600, 800), "white")
        self.assertEqual(barcode.Decoder(options()).scaled(small).size, (600, 800))
        self.assertEqual(barcode.Decoder(options(upscale=True)).scaled(small).size,
                         (1200, 1600))
        big = Image.new("RGBA", (4000, 3000), (0, 0, 0, 0))
        scaled = barcode.Decoder(options()).scaled(big)
        self.assertEqual((scaled.size, scaled.mode), ((1600, 1200), "RGB"))
        self.assertEqual(scaled.getpixel((0, 0)), (255, 255, 255))


if __name__ == "__main__":
    unittest.main()
