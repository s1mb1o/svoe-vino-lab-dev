"""Check draft recognition, identity decisions and transactional creation guards."""
import base64
import io
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "tests"))
import wine_draft as D  # noqa: E402
import lab_server as LAB  # noqa: E402
import labdb  # noqa: E402
import manual_wines  # noqa: E402
import atlas_import  # noqa: E402
from test_manual_wines import form, picture  # noqa: E402
from test_patches import FakeSam3  # noqa: E402


def wine(**changes):
    return {"slug": "__existing", "name": "Graphite 2023", "producer": "High Coast",
            "grapes": "Merlot, Syrah", "sweetness": "dry", "category": "Красное",
            "_beverage_type_code": "4", "state": "Active", **changes}


def draft(**changes):
    return {"name": "Graphite", "producer": "High Coast", "grapes": "Сира; Мерло",
            "sweetness": "dry", "vintage": "2023", "category": "Красное",
            "beverage_type_code": "4", **changes}


class IdentityTest(unittest.TestCase):
    def relation(self, left=None, right=None):
        out = D.compare(left or draft(), [right or wine()])
        return out["matches"][0]["relation"]

    def test_exact_translated_reordered_grapes_and_year_removed_from_name(self):
        self.assertEqual(self.relation(), "exact")

    def test_different_vintage_and_one_missing_vintage(self):
        self.assertEqual(self.relation(draft(vintage="2024")), "different_vintage")
        self.assertEqual(self.relation(draft(vintage="")), "unknown_vintage")
        self.assertEqual(self.relation(draft(vintage=""), wine(name="Graphite")), "exact")

    def test_unknown_or_conflicting_attributes_stay_similar(self):
        for changes in ({"grapes": ""}, {"sweetness": ""}, {"sweetness": "sweet"},
                        {"producer": "Another winery"}, {"category": "Белое"},
                        {"beverage_type_code": "44"}, {"grapes": "Sauvignon"}):
            with self.subTest(changes=changes):
                self.assertEqual(self.relation(draft(**changes)), "similar")
        self.assertEqual(self.relation(right=wine(name="Graphite 2022 2023")), "similar")

    def test_similar_name_is_not_exact(self):
        self.assertEqual(self.relation(draft(name="Graphite Reserve")), "similar")
        self.assertEqual(D.compare(draft(name="Unrelated"), [wine()])["total"], 0)

    def test_short_label_name_still_finds_long_catalogue_titles(self):
        out = D.compare(draft(name="Сира"), [wine(name="Высокий Берег Графит Сира 2023")])
        self.assertEqual(out["total"], 1)
        self.assertEqual(out["matches"][0]["relation"], "similar")

    def test_title_descriptors_legal_producer_forms_and_grape_aliases(self):
        self.assertEqual(self.relation(draft(name="Мерло", grapes="Merlot", producer='ООО «High Coast»'),
                         wine(name="Вино Мерло красное сухое урожай 2023 г.", grapes="Мерло")), "exact")
        self.assertEqual(self.relation(draft(grapes="Shiraz, Pinot Grigio"), wine(grapes="Сира, Пино Гри")), "exact")
        self.assertEqual(self.relation(draft(grapes="Merlot"), wine(grapes="Merlot, Unknown Grape")), "similar")
        self.assertEqual(self.relation(draft(grapes="Мерло, X"), wine(grapes="X; Merlot")), "exact")
        self.assertEqual(self.relation(draft(grapes="Cabernet Sauvignon"), wine(grapes="Sauvignon Blanc")), "similar")
        self.assertEqual(self.relation(draft(grapes="Каберне Фран"), wine(grapes="Каберне Совиньон")), "similar")

    def test_multiple_tags_are_ambiguous_and_title_year_conflict_is_invalid(self):
        self.assertEqual(self.relation(right=wine(sweetness=None, _tags=["sweetness:dry", "sweetness:sweet"])), "similar")
        self.assertEqual(self.relation(right=wine(_tags=["vintage:2022", "vintage:2023"])), "similar")
        with self.assertRaisesRegex(D.DraftError, "Year differs"):
            D.read_values(draft(name="Graphite 2022", vintage="2023"))

    def test_cached_identity_changes_when_tags_or_metadata_change(self):
        record = wine(name="Graphite", sweetness=None, _tags=["sweetness:dry", "vintage:2023"])
        self.assertEqual(self.relation(right=record), "exact")
        record["_tags"] = ["sweetness:dry", "vintage:2022"]
        self.assertEqual(self.relation(right=record), "different_vintage")
        unsafe = D.identity(record)
        unsafe["grapes"].append("poison")
        self.assertNotIn("poison", D.identity(record)["grapes"])
        record["grapes"] = "Sauvignon Blanc"
        self.assertEqual(self.relation(right=record), "similar")

    def test_tags_persist_identity_without_changing_name(self):
        record = wine(name="Graphite", sweetness=None, _tags=["sweetness:dry", "vintage:2023"])
        self.assertEqual(self.relation(right=record), "exact")
        self.assertEqual(D.values_for_record(record)["vintage"], "2023")
        record["_tags"] = ["vintage:2023"]
        record["color"] = "Сухое"
        self.assertEqual(self.relation(right=record), "exact")
        record["color"] = "Сладкое"
        self.assertEqual(self.relation(right=record), "similar")
        self.assertEqual(D.read_values(draft(name="Vision 2099", vintage="2023"))["vintage"], "2023")

    def test_all_states_and_conflicts_outside_display_limit(self):
        records = [wine(slug=str(i), state=state) for i, state in enumerate(
            ["Active", "Disabled", "Removed"] * 8)]
        out = D.compare(draft(), records, limit=2)
        self.assertEqual(len(out["matches"]), 2)
        self.assertEqual(len(out["conflicts"]), 24)
        self.assertEqual(out["total"], 24)
        self.assertNotEqual(out["acknowledgement"], D.compare(draft(vintage="2024"), records)["acknowledgement"])
        self.assertNotEqual(out["acknowledgement"], D.compare(draft(), records[:-1])["acknowledgement"])

    def test_bounded_fields_and_year_validation(self):
        for changes in ({"vintage": "2300"}, {"vintage": "abc"}, {"vintage": 2024},
                        {"name": []}, {"name": "x" * 4001}, {"sweetness": "guess"},
                        {"name": "\ud800"}, {"beverage_type_code": "7"}):
            with self.subTest(changes=changes), self.assertRaises(D.DraftError):
                D.read_values(draft(**changes))


class RecognitionTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.config = Path(self.directory.name) / "config.yaml"
        self.config.write_text("{}")
        self.entry = SimpleNamespace(protocol="openai", max_tokens=1024, model="test-vlm")

    def tearDown(self):
        self.directory.cleanup()

    def test_recognition_uses_image_only_and_schema(self):
        answer = {key: None for key in D.FIELDS}
        answer.update(name="Graphite", vintage="2023", sweetness="dry")
        with mock.patch("vlm_config.entries", return_value={"test": self.entry}), \
             mock.patch("describe_images.settings", return_value={"vlm": "test", "detail_max_side": 1280}), \
             mock.patch("describe_images.payload_of", return_value={"test": True}) as payload, \
             mock.patch("describe_images.post", return_value={"choices": [
                 {"message": {"content": json.dumps(answer)}, "finish_reason": "stop"}],
                 "model": "test-vlm"}) as transport:
            result = D.recognize({"image": base64.b64encode(picture()).decode()}, self.config)
        self.assertEqual(result["values"]["vintage"], "2023")
        self.assertEqual(result["values"]["producer"], "")
        self.assertTrue(payload.call_args.args[1].startswith("data:image/jpeg;base64,"))
        self.assertIs(payload.call_args.args[4], D.SCHEMA)
        self.assertEqual(transport.call_args.kwargs["timeout"], 45)

    def test_invalid_model_outputs_and_timeout_leave_no_files(self):
        import describe_images
        valid = {key: None for key in D.FIELDS}
        cases = ["not JSON", json.dumps({**valid, "vintage": "2300"}),
                 json.dumps({**valid, "sweetness": "guess"}), json.dumps({"name": "Only name"})]
        before = sorted(str(p.relative_to(self.config.parent)) for p in self.config.parent.rglob("*"))
        with mock.patch("vlm_config.entries", return_value={"test": self.entry}), \
             mock.patch("describe_images.settings", return_value={"vlm": "test", "detail_max_side": 1280}), \
             mock.patch("describe_images.payload_of", return_value={}):
            for text in cases:
                with self.subTest(text=text), mock.patch("describe_images.post", return_value={
                        "choices": [{"message": {"content": text}}]}), self.assertRaises(D.DraftError):
                    D.recognize({"image": base64.b64encode(picture()).decode()}, self.config)
            with mock.patch("describe_images.post", side_effect=describe_images.DescribeError("timeout")), \
                 self.assertRaises(D.DraftError):
                D.recognize({"image": base64.b64encode(picture()).decode()}, self.config)
        self.assertEqual(before, sorted(str(p.relative_to(self.config.parent)) for p in self.config.parent.rglob("*")))

    def test_pixel_limit_and_recognition_capacity(self):
        import patches
        body = {"image": base64.b64encode(picture()).decode()}
        with mock.patch.object(patches, "MAX_PIXELS", 1), self.assertRaises(D.DraftError) as caught:
            D.recognize(body, self.config)
        self.assertEqual(caught.exception.code, 413)
        with mock.patch.object(Image, "MAX_IMAGE_PIXELS", 1), self.assertRaises(D.DraftError) as caught:
            D.recognize(body, self.config)
        self.assertEqual(caught.exception.code, 413)
        D.RECOGNITION_SLOTS.acquire()
        try:
            with self.assertRaises(D.DraftError) as caught:
                D.recognize(body, self.config)
            self.assertEqual(caught.exception.code, 429)
        finally:
            D.RECOGNITION_SLOTS.release()

    def test_bad_model_year_keeps_other_recognized_fields(self):
        for name, year in (("Graphite", "2099"), ("1924 Double Gold Merlot", "2019")):
            answer = {key: None for key in D.FIELDS}
            answer.update(name=name, grapes="Merlot", vintage=year)
            with self.subTest(name=name), \
                 mock.patch("vlm_config.entries", return_value={"test": self.entry}), \
                 mock.patch("describe_images.settings", return_value={"vlm": "test", "detail_max_side": 1280}), \
                 mock.patch("describe_images.payload_of", return_value={}), \
                 mock.patch("describe_images.post", return_value={"choices": [
                     {"message": {"content": json.dumps(answer)}, "finish_reason": "stop"}]}):
                result = D.recognize({"image": base64.b64encode(picture()).decode()}, self.config)
                self.assertEqual(result["values"]["vintage"], "")
                self.assertEqual(result["values"]["name"], name)
                self.assertEqual(result["values"]["grapes"], "Merlot")

    def test_bad_image_and_missing_config(self):
        for image in ("bad base64", base64.b64encode(b"not an image").decode()):
            with self.assertRaises(manual_wines.WineError):
                D.recognize({"image": image}, self.config)
        with self.assertRaisesRegex(D.DraftError, "configuration"):
            D.recognize({"image": base64.b64encode(picture()).decode()}, None)
        buffer = io.BytesIO()
        Image.new("RGB", (5, 5)).save(buffer, "GIF")
        with self.assertRaises(manual_wines.WineError):
            D.recognize({"image": base64.b64encode(buffer.getvalue()).decode()}, self.config)


class RouteTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.db = str(Path(self.directory.name) / "catalog.sqlite3")
        self.conn = labdb.connect(self.db, create=True)
        self.conn.close()
        self.server = LAB.make_server(self.db, port=0, segmenter=FakeSam3())
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = "http://127.0.0.1:%d" % self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.directory.cleanup()

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as exc:
            with exc:
                return exc.code, json.loads(exc.read())

    def test_read_only_similarity_and_recognition_routes(self):
        self.assertEqual(self.post("/api/wine-draft-similar", draft())[0], 200)
        with mock.patch.object(D, "recognize", return_value={"values": draft()}):
            status, out = self.post("/api/wine-draft-recognize", {"image": "test"})
            self.assertEqual(status, 200)
            self.assertEqual(out["values"]["name"], "Graphite")
        self.assertEqual(self.post("/api/wine-draft-similar", {"vintage": 2023})[0], 400)
        self.assertEqual(self.post("/api/wine-draft-recognize", {"image": "bad"})[0], 400)
        with labdb.connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT count(*) FROM wine_catalog").fetchone()[0], 0)

    def test_transactional_guard_and_tag_persistence(self):
        first = form(name="Graphite", grapes="Merlot", sweetness="dry", vintage="2023")
        self.assertEqual(self.post("/api/wine", first)[0], 200)
        second = {**first, "slug": "__second", "check_duplicates": True}
        status, out = self.post("/api/wine", second)
        self.assertEqual(status, 409, out)
        _, comparison = self.post("/api/wine-draft-similar", second)
        self.assertEqual(comparison["conflicts"][0]["relation"], "exact")
        second["duplicate_acknowledgement"] = comparison["acknowledgement"]
        self.assertEqual(self.post("/api/wine", second)[0], 200)
        third = {**second, "slug": "__third"}
        self.assertEqual(self.post("/api/wine", third)[0], 409)
        with labdb.connect(self.db) as conn:
            self.assertEqual(conn.execute("SELECT tag FROM wine_tag WHERE wine_slug='__my-wine' ORDER BY tag").fetchall(),
                             [("sweetness:dry",), ("vintage:2023",)])
            self.assertEqual(conn.execute("SELECT count(*) FROM wine_catalog").fetchone()[0], 2)

    def test_atlas_transaction_accepts_optional_attributes(self):
        with labdb.connect(self.db) as conn:
            conn.isolation_level = None
            atlas_import.insert_wine(conn, "00000000-0000-0000-0000-000000000001", "__atlas",
                manual_wines.read_fields(form()), "4", draft=form(sweetness="brut", vintage="2022"))
            self.assertEqual(conn.execute("SELECT count(*) FROM wine_tag WHERE wine_slug='__atlas'").fetchone()[0], 2)
