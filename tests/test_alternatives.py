import base64
import hashlib
import io
import json
import shutil
import sqlite3
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import alternatives  # noqa: E402
import derive  # noqa: E402
import lab_server as LAB  # noqa: E402
import labdb  # noqa: E402

WINES = [
    ("wine-b", "Вино b", "Винодельня", "Белое", "Соломенный", "Крым",
     "Алиготе", "Описание b", "b.webp", "Active", None),
    ("wine-a", "Вино a", "Винодельня", "Красное", "Рубиновый", "Кубань",
     None, "Описание a", "a.webp", "Removed", "import"),
]
SIZE = (40, 80)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def picture(transparent=True, colour=(90, 30, 20)):
    """The PNG bytes of a bottle box on a transparent or a white canvas."""
    image = Image.new("RGBA" if transparent else "RGB", SIZE,
                      (255, 255, 255, 0) if transparent else (255, 255, 255))
    ImageDraw.Draw(image).rectangle((10, 10, 29, 69), fill=colour)
    out = io.BytesIO()
    image.save(out, "PNG")
    return out.getvalue()


def mask_b64(box, size=SIZE):
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rectangle(box, fill=255)
    out = io.BytesIO()
    mask.save(out, "PNG")
    return base64.b64encode(out.getvalue()).decode()


def instance(label, box, score=0.9, masked=True):
    item = {"label": label, "box": list(box), "score": score,
            "area": (box[2] - box[0]) * (box[3] - box[1])}
    if masked:
        item["mask_png_b64"] = mask_b64((box[0], box[1], box[2] - 1, box[3] - 1))
    return item


# A full bottle: a bottle box and a real neck inside it, in the upper half.
FULL = [instance("bottle", (10, 10, 30, 70)), instance("bottle neck", (16, 12, 24, 30)),
        instance("label", (10, 40, 30, 60))]
# A close-up: the bottle fills the frame and has no neck; the label is the middle band.
CLOSE_UP = [instance("bottle", (0, 0, 40, 80)), instance("label", (4, 20, 36, 60)),
            instance("wine bottle label", (4, 20, 36, 60), score=0.8)]
# A close-up whose label is close to the bottle box (IoU 0.81) and holds a small sticker,
# as the photo `d9f847bd…` of the owner message of 2026-09-26T19:38:53+0300.
STICKER_CLOSE_UP = [instance("bottle", (0, 0, 40, 80)), instance("label", (2, 4, 38, 76)),
                    instance("label", (24, 10, 34, 30), score=0.4)]


class FakeSam3:
    """A SAM3 client with no network. `answer` is the answer of `instances`."""

    def __init__(self, answer=None, scale=1.0, package_answer=None):
        self.answer = FULL if answer is None else answer
        self.package_answer = package_answer
        self.scale = scale
        self.instances_calls = []
        self.segment_calls = 0

    def instances(self, image, texts, masks=True):
        self.instances_calls.append(texts)
        answer = (self.package_answer if texts == derive.SAM3_TEXTS
                  and self.package_answer is not None else self.answer)
        return list(answer), self.scale

    def segment(self, image):
        self.segment_calls += 1
        mask = Image.new("L", image.size, 0)
        ImageDraw.Draw(mask).rectangle((10, 10, 29, 69), fill=255)
        return mask


class DownSam3:
    def instances(self, image, texts, masks=True):
        raise derive.Sam3Unavailable("connection refused")

    def segment(self, image):
        raise derive.Sam3Unavailable("connection refused")


class DetectTest(unittest.TestCase):
    def test_a_real_neck_inside_the_bottle_is_a_full_package(self):
        self.assertEqual(alternatives.detect(FULL, *SIZE), "full")

    def test_a_close_up_is_a_label(self):
        self.assertEqual(alternatives.detect(CLOSE_UP, *SIZE), "label")

    def test_the_neck_of_a_bottle_behind_does_not_count(self):
        answer = [instance("bottle", (0, 0, 28, 80)), instance("bottle", (30, 5, 40, 30)),
                  instance("bottle neck", (32, 8, 38, 20))]
        self.assertEqual(alternatives.detect(answer, *SIZE), "label")

    def test_a_neck_at_the_top_edge_is_a_cut_bottle(self):
        answer = [instance("bottle", (10, 0, 30, 80)), instance("bottle neck", (16, 0, 24, 30))]
        self.assertEqual(alternatives.detect(answer, *SIZE), "label")

    def test_a_tall_can_is_a_full_package(self):
        self.assertEqual(alternatives.detect([instance("can", (0, 1, 40, 79))], *SIZE), "full")
        self.assertEqual(alternatives.detect([instance("can", (0, 1, 40, 79))], 60, 80), "label")

    def test_no_instance_is_a_label(self):
        self.assertEqual(alternatives.detect([], *SIZE), "label")

    def test_a_low_or_wide_neck_is_no_real_neck(self):
        low = [instance("bottle", (10, 10, 30, 70)), instance("bottle neck", (16, 30, 24, 50))]
        wide = [instance("bottle", (10, 10, 30, 70)), instance("bottle neck", (10, 12, 30, 30))]
        self.assertEqual(alternatives.detect(low, *SIZE), "label")
        self.assertEqual(alternatives.detect(wide, *SIZE), "label")


class SideTest(unittest.TestCase):
    def test_a_barcode_on_the_bottle_is_the_back(self):
        answer = FULL + [instance("barcode", (14, 50, 26, 58))]
        self.assertEqual(alternatives.side(answer, *SIZE), "back")

    def test_no_barcode_is_the_front(self):
        self.assertEqual(alternatives.side(FULL, *SIZE), "front")

    def test_a_barcode_beside_the_bottle_does_not_count(self):
        answer = FULL + [instance("barcode", (32, 72, 39, 79))]
        self.assertEqual(alternatives.side(answer, *SIZE), "front")

    def test_a_barcode_on_a_can_is_the_back(self):
        answer = [instance("can", (0, 1, 40, 79)), instance("barcode", (5, 60, 20, 70))]
        self.assertEqual(alternatives.side(answer, *SIZE), "back")

    def test_a_faint_or_narrow_barcode_does_not_count(self):
        faint = FULL + [instance("barcode", (14, 50, 26, 58), score=0.5)]
        narrow = FULL + [instance("barcode", (19, 50, 20, 58))]
        self.assertEqual(alternatives.side(faint, *SIZE), "front")
        self.assertEqual(alternatives.side(narrow, *SIZE), "front")

    def test_a_barcode_with_no_package_is_the_back(self):
        self.assertEqual(alternatives.side([instance("barcode", (5, 5, 20, 12))], *SIZE),
                         "back")


class LabelInstanceTest(unittest.TestCase):
    def test_a_label_that_is_the_bottle_gives_way_to_a_smaller_label(self):
        answer = [instance("bottle", (0, 0, 40, 80)), instance("label", (0, 0, 40, 80)),
                  instance("label", (4, 20, 36, 60))]
        self.assertEqual(alternatives.label_instance(answer)["box"], [4, 20, 36, 60])

    def test_a_close_up_keeps_the_largest_label_when_each_label_is_the_bottle(self):
        answer = [instance("bottle", (0, 0, 40, 80)), instance("label", (0, 0, 40, 80))]
        self.assertEqual(alternatives.label_instance(answer)["box"], [0, 0, 40, 80])

    def test_a_label_close_up_keeps_the_largest_label_with_no_bottle_test(self):
        self.assertEqual(alternatives.label_instance(STICKER_CLOSE_UP)["box"],
                         [24, 10, 34, 30])
        self.assertEqual(alternatives.label_instance(STICKER_CLOSE_UP, close_up=True)["box"],
                         [2, 4, 38, 76])

    def test_no_label_gives_none(self):
        self.assertIsNone(alternatives.label_instance([instance("bottle", (0, 0, 40, 80))]))

    def test_a_packet_or_box_makes_the_label_not_applicable(self):
        self.assertEqual(
            alternatives.label_absence_reason([instance("packet", (0, 0, 40, 80))]),
            "the packet has no separate label")
        self.assertEqual(
            alternatives.label_absence_reason([instance("box", (0, 0, 40, 80))]),
            "the box has no separate label")
        self.assertIsNone(
            alternatives.label_absence_reason([instance("wine bottle", (0, 0, 40, 80))]))


class MigrationTest(unittest.TestCase):
    def test_a_version_9_database_keeps_its_rows_through_the_renames_and_the_cut_kind(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = Path(tmp) / "schema-9"
            old.mkdir()
            for number, path in labdb.schema_files():
                if number <= 9:
                    shutil.copy(path, old)
            db = str(Path(tmp) / "lab.sqlite3")
            conn = labdb.connect(db, create=True, directory=str(old))
            a, b, cut = sha(b"a"), sha(b"b"), sha(b"cut")
            with conn:
                conn.execute("INSERT INTO wine_catalog VALUES (?,?,?,?,?,?,?,?,?,?,?)", WINES[0])
                conn.executemany("INSERT INTO image (sha256, folder, extension) VALUES (?, ?, ?)",
                                 [(a, "additional", "png"), (b, "additional", "png"),
                                  (cut, "cropped", "png")])
                conn.executemany("INSERT INTO wine_image VALUES ('wine-b', ?, ?, 'x', 'manual')",
                                 [("front", a), ("label_back", b)])
                conn.executemany("INSERT INTO image_derivative VALUES (?, 'seg', ?, ?, 0, 0, 5, 5)",
                                 [(a, derive.SETTINGS_SEG, cut),
                                  (b, alternatives.SETTINGS_LABEL, cut)])
            conn.close()
            conn = labdb.connect(db)
            try:
                self.assertEqual(conn.execute("SELECT image_type, sha256 FROM wine_image "
                                              "ORDER BY rowid").fetchall(),
                                 [("full_front", a), ("label_back", b)])
                self.assertEqual(dict(conn.execute("SELECT source_sha256, kind FROM "
                                                   "image_derivative")),
                                 {a: "package", b: "label"})
                self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])
            finally:
                conn.close()


class AlternativeRouteTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.db = str(self.root / "lab.sqlite3")
        conn = labdb.connect(self.db, create=True)
        with conn:
            conn.executemany(
                "INSERT INTO wine_catalog (wine_slug, name, producer, category, color, region, grapes, description, csv_photo_name, state, removed_by) VALUES (?,?,?,?,?,?,?,?,?,?,?)", WINES)
        conn.close()
        self.sam3 = FakeSam3()
        self.server = LAB.make_server(self.db, port=0, segmenter=self.sam3)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = "http://127.0.0.1:%d" % self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.directory.cleanup()

    def request(self, path, method="GET", body=None, ctype="application/octet-stream"):
        req = urllib.request.Request(self.base + path, method=method, data=body,
                                     headers={"Content-Type": ctype})
        try:
            with urllib.request.urlopen(req) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def upload(self, slug, data, name="photo.png"):
        query = urllib.parse.urlencode({"slug": slug, "name": name})
        return self.request("/api/dataset-alternative?" + query, "POST", data)

    def set_type(self, slug, digest, image_type):
        body = json.dumps({"slug": slug, "sha256": digest, "type": image_type}).encode()
        return self.request("/api/dataset-alternative-type", "POST", body, "application/json")

    def remove(self, slug, digest):
        query = urllib.parse.urlencode({"slug": slug, "sha256": digest})
        return self.request("/api/dataset-alternative?" + query, "DELETE")

    def rows(self):
        conn = sqlite3.connect(self.db)
        try:
            return [row for row in conn.execute(
                "SELECT wine_slug, image_type, sha256, source_name, match_method "
                "FROM wine_image WHERE image_type NOT IN ('main', 'main_patched') "
                "ORDER BY rowid")]
        finally:
            conn.close()

    def settings(self, digest, kind="package"):
        conn = sqlite3.connect(self.db)
        try:
            row = conn.execute("SELECT method, settings FROM image_derivative "
                               "WHERE source_sha256 = ? AND kind = ?", (digest, kind)).fetchone()
            return row
        finally:
            conn.close()

    def test_the_schema_holds_the_new_type_names(self):
        conn = sqlite3.connect(self.db)
        try:
            sql = conn.execute("SELECT sql FROM sqlite_schema WHERE name = 'wine_image'"
                               ).fetchone()[0]
        finally:
            conn.close()
        for name in alternatives.TYPES:
            self.assertIn("'%s'" % name, sql)
        for name in ("front_full", "back_label", "front", "back"):
            self.assertNotIn("'%s'" % name, sql)

    def test_a_full_bottle_gets_full_front_and_the_package_cut(self):
        data = picture()
        status, out = self.upload("wine-b", data, "Буковинка.png")
        self.assertEqual(status, 200, out)
        self.assertEqual((out["type"], out["changed"], out["alternatives"]),
                         ("full_front", True, 1))
        photo, = out["record"]["_alternatives"]
        self.assertEqual((photo["sha256"], photo["type"], photo["url"], photo["derivation"]),
                         (sha(data), "full_front", "/images/additional/%s.png" % sha(data),
                          "crop"))
        self.assertTrue(photo["image_url"].startswith("/images/cropped/"))
        self.assertEqual(self.sam3.instances_calls, [alternatives.DETECT_TEXTS])
        self.assertEqual(self.rows(),
                         [("wine-b", "full_front", sha(data), "Буковинка.png", "manual")])
        self.assertEqual(self.settings(sha(data))[0], "crop")
        self.assertTrue((self.root / "images" / "additional" / (sha(data) + ".png")).exists())
        view = self.request("/api/dataset")[1]
        self.assertEqual((view["alternative_editor"], view["alternatives"]), (True, 1))
        self.assertNotIn("alternative_dir", view)

    def test_a_close_up_gets_label_front_and_the_label_cut(self):
        self.sam3.answer = CLOSE_UP
        data = picture(transparent=False)
        status, out = self.upload("wine-b", data)
        self.assertEqual(status, 200, out)
        photo, = out["record"]["_alternatives"]
        self.assertEqual((photo["type"], photo["derivation"]), ("label_front", "seg"))
        self.assertEqual(self.settings(sha(data), "label"),
                         ("seg", alternatives.SETTINGS_LABEL_CLOSE_UP))
        self.assertIsNone(self.settings(sha(data)))
        self.assertEqual(self.sam3.segment_calls, 0)
        cut = Image.open(self.root / photo["image_url"].lstrip("/"))
        self.assertEqual(cut.mode, "RGBA")
        self.assertLess(cut.height, SIZE[1])

    def test_a_close_up_cuts_the_largest_label_and_not_a_sticker_on_it(self):
        self.sam3.answer = STICKER_CLOSE_UP
        data = picture(transparent=False)
        status, out = self.upload("wine-b", data)
        self.assertEqual(status, 200, out)
        photo, = out["record"]["_alternatives"]
        self.assertEqual((photo["type"], photo["derivation"]), ("label_front", "seg"))
        cut = Image.open(self.root / photo["image_url"].lstrip("/"))
        self.assertGreaterEqual(cut.width, 36)
        self.assertGreaterEqual(cut.height, 72)

    def test_a_close_up_cut_of_the_full_photo_rule_is_cut_again(self):
        self.sam3.answer = STICKER_CLOSE_UP
        data = picture(transparent=False)
        self.upload("wine-b", data)
        conn = sqlite3.connect(self.db)
        with conn:
            conn.execute("UPDATE image_derivative SET settings = ? WHERE source_sha256 = ? "
                         "AND kind = 'label'", (alternatives.SETTINGS_LABEL, sha(data)))
        conn.close()
        calls = len(self.sam3.instances_calls)
        status, out = self.set_type("wine-b", sha(data), "label_front")
        self.assertEqual(status, 200, out)
        self.assertEqual(len(self.sam3.instances_calls), calls + 1)
        self.assertEqual(self.settings(sha(data), "label")[1],
                         alternatives.SETTINGS_LABEL_CLOSE_UP)

    def test_a_barcode_gives_the_back_types(self):
        self.sam3.answer = FULL + [instance("barcode", (14, 50, 26, 58))]
        status, out = self.upload("wine-b", picture())
        self.assertEqual((status, out["type"]), (200, "full_back"))
        self.sam3.answer = CLOSE_UP + [instance("barcode", (10, 62, 30, 72))]
        status, out = self.upload("wine-b", picture(colour=(20, 30, 90)))
        self.assertEqual((status, out["type"]), (200, "label_back"))

    def test_no_sam3_gives_full_front_with_a_warning(self):
        self.server.segmenter = DownSam3()
        status, out = self.upload("wine-b", picture(transparent=False))
        self.assertEqual(status, 200, out)
        self.assertEqual(out["type"], "full_front")
        self.assertIn("no detection", out["warning"])
        self.assertIn(alternatives.NO_PROCESSED_FILE, out["warning"])
        self.assertIsNone(out["record"]["_alternatives"][0]["derivation"])

    def test_the_same_photo_twice_changes_nothing(self):
        data = picture()
        self.upload("wine-b", data)
        status, out = self.upload("wine-b", data, "again.png")
        self.assertEqual((status, out["changed"], out["alternatives"]), (200, False, 1))
        self.assertEqual(len(self.rows()), 1)
        second = picture(colour=(20, 30, 90))
        status, out = self.upload("wine-b", second)
        self.assertEqual([p["sha256"] for p in out["record"]["_alternatives"]],
                         [sha(data), sha(second)])

    def test_front_to_back_keeps_the_processed_file(self):
        data = picture()
        self.upload("wine-b", data)
        before = self.settings(sha(data))
        calls = len(self.sam3.instances_calls)
        status, out = self.set_type("wine-b", sha(data), "full_back")
        self.assertEqual((status, out["type"], out["changed"]), (200, "full_back", True))
        self.assertEqual(self.settings(sha(data)), before)
        self.assertEqual(len(self.sam3.instances_calls), calls)
        self.assertEqual(self.rows()[0][1], "full_back")

    def test_full_to_label_and_back_segments_again(self):
        data = picture(transparent=False)
        self.upload("wine-b", data)
        self.assertEqual(self.settings(sha(data))[0], "seg")
        self.assertNotEqual(self.settings(sha(data))[1], alternatives.SETTINGS_LABEL)
        self.sam3.answer = CLOSE_UP
        status, out = self.set_type("wine-b", sha(data), "label_back")
        self.assertEqual((status, out["type"]), (200, "label_back"))
        self.assertEqual(self.settings(sha(data), "label")[1],
                         alternatives.SETTINGS_LABEL_CLOSE_UP)
        status, out = self.set_type("wine-b", sha(data), "full_front")
        self.assertEqual((status, out["type"]), (200, "full_front"))
        self.assertEqual(self.settings(sha(data))[1], derive.SETTINGS_SEG)

    def test_the_same_type_changes_nothing(self):
        data = picture()
        self.upload("wine-b", data)
        status, out = self.set_type("wine-b", sha(data), "full_front")
        self.assertEqual((status, out["changed"]), (200, False))

    def test_remove_deletes_the_row_and_keeps_the_file(self):
        data = picture()
        self.upload("wine-b", data)
        status, out = self.remove("wine-b", sha(data))
        self.assertEqual((status, out["alternatives"], out["record"]["_alternatives"]),
                         (200, 0, []))
        self.assertEqual(self.rows(), [])
        self.assertTrue((self.root / "images" / "additional" / (sha(data) + ".png")).exists())
        self.assertEqual(self.remove("wine-b", sha(data))[0], 404)

    def test_bad_requests_are_refused(self):
        data = picture()
        self.upload("wine-b", data)
        self.assertEqual(self.set_type("wine-b", sha(data), "front")[0], 400)
        self.assertEqual(self.set_type("wine-b", "0" * 64, "full_back")[0], 404)
        self.assertEqual(self.set_type("wine-x", sha(data), "full_back")[0], 404)
        self.assertEqual(self.upload("wine-x", data)[0], 404)
        self.assertEqual(self.upload("wine-b", b"not an image")[0], 400)
        self.assertEqual(self.remove("wine-b", "")[0], 400)
        self.assertEqual(len(self.rows()), 1)

    def image_size(self, digest):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute("SELECT width, height FROM image WHERE sha256 = ?",
                                (digest,)).fetchone()
        finally:
            conn.close()

    def cuts(self, digest):
        conn = sqlite3.connect(self.db)
        try:
            return dict(conn.execute("SELECT kind, method FROM image_derivative "
                                     "WHERE source_sha256 = ?", (digest,)))
        finally:
            conn.close()

    def test_the_image_row_holds_the_size_of_the_file_not_of_the_sam3_copy(self):
        self.sam3.scale = 0.5
        data = picture()
        self.assertEqual(self.upload("wine-b", data)[0], 200)
        self.assertEqual(self.image_size(sha(data)), SIZE)

    def test_one_file_keeps_a_package_cut_and_a_label_cut(self):
        data = picture()
        query = urllib.parse.urlencode({"slug": "wine-b", "name": "patch.png"})
        status, out = self.request("/api/dataset-patch?" + query, "POST", data)
        self.assertEqual((status, out["record"]["_patch_derivation"]), (200, "crop"))
        self.sam3.answer = CLOSE_UP
        status, out = self.upload("wine-b", data)
        self.assertEqual((status, out["type"]), (200, "label_front"))
        record = out["record"]
        self.assertEqual((record["_patch_derivation"], record["_alternatives"][0]["derivation"]),
                         ("crop", "seg"))
        self.assertEqual(self.cuts(sha(data)), {"package": "crop", "label": "seg"})

    def test_a_type_change_with_no_sam3_shows_the_photo_and_a_change_back_reuses_the_cut(self):
        data = picture(transparent=False)
        self.upload("wine-b", data)
        self.assertEqual(self.cuts(sha(data)), {"package": "seg"})
        self.server.segmenter = DownSam3()
        status, out = self.set_type("wine-b", sha(data), "label_back")
        self.assertEqual(status, 200)
        self.assertIn(alternatives.NO_NEW_CUT, out["warning"])
        photo = out["record"]["_alternatives"][0]
        self.assertEqual((photo["type"], photo["derivation"], photo["image_url"]),
                         ("label_back", None, photo["url"]))
        status, out = self.set_type("wine-b", sha(data), "full_front")
        self.assertEqual((status, out.get("warning")), (200, None))
        self.assertEqual(out["record"]["_alternatives"][0]["derivation"], "seg")

    def test_the_same_photo_again_processes_a_missing_cut(self):
        self.server.segmenter = DownSam3()
        data = picture(transparent=False)
        self.upload("wine-b", data)
        self.assertEqual(self.cuts(sha(data)), {})
        self.server.segmenter = self.sam3
        status, out = self.upload("wine-b", data)
        self.assertEqual((status, out["changed"]), (200, False))
        self.assertEqual(out["record"]["_alternatives"][0]["derivation"], "seg")

    def test_a_removed_wine_gets_a_photo(self):
        status, out = self.upload("wine-a", picture())
        self.assertEqual((status, out["type"]), (200, "full_front"))


    # A second body label gives the box of the labels (owner answer of 2026-09-25T19:16:44).

    def test_two_body_labels_give_the_box_of_the_labels_with_no_mask(self):
        self.sam3.answer = TWO_LABELS
        data = picture(transparent=False)
        status, out = self.upload("wine-b", data)
        self.assertEqual(status, 200, out)
        photo, = out["record"]["_alternatives"]
        self.assertEqual((photo["type"], photo["derivation"]), ("label_front", "crop"))
        self.assertEqual(self.settings(sha(data), "label"),
                         ("crop", alternatives.SETTINGS_LABEL_CLOSE_UP))
        cut = Image.open(self.root / photo["image_url"].lstrip("/"))
        self.assertEqual((cut.mode, cut.size), ("RGBA", (32, 62)))
        self.assertEqual(cut.getchannel("A").getextrema(), (255, 255))


# A close-up with two labels one above the other, as wide as each other.
TWO_LABELS = [instance("bottle", (0, 0, 40, 80)), instance("label", (4, 10, 36, 44)),
              instance("label", (6, 48, 34, 72))]


class BodyLabelsTest(unittest.TestCase):
    def others(self, answer, size=SIZE):
        main = alternatives.label_instance(answer)
        return [item["box"] for item in alternatives.body_labels(answer, main, *size)]

    def test_a_second_label_of_the_same_width_counts(self):
        self.assertEqual(self.others(TWO_LABELS), [[6, 48, 34, 72]])

    def test_a_neck_label_and_a_part_of_the_main_label_do_not_count(self):
        answer = [instance("bottle", (0, 0, 40, 80)), instance("label", (4, 10, 36, 44)),
                  instance("label", (15, 0, 25, 9)), instance("label", (4, 10, 36, 30))]
        self.assertEqual(self.others(answer), [])

    def test_a_narrow_or_small_label_does_not_count(self):
        answer = [instance("bottle", (0, 0, 40, 80)), instance("label", (4, 10, 36, 44)),
                  instance("label", (14, 48, 30, 78)), instance("label", (4, 60, 36, 68))]
        self.assertEqual(self.others(answer), [])

    def test_a_label_on_another_bottle_does_not_count(self):
        answer = [instance("bottle", (0, 0, 24, 80)), instance("bottle", (26, 0, 40, 60)),
                  instance("label", (2, 10, 22, 40)), instance("label", (27, 20, 39, 50))]
        self.assertEqual(self.others(answer), [])

    def test_with_no_bottle_each_label_can_count(self):
        answer = [instance("label", (4, 10, 36, 44)), instance("label", (6, 48, 34, 72))]
        self.assertEqual(self.others(answer), [[6, 48, 34, 72]])

    def test_the_box_is_in_the_pixels_of_the_image(self):
        image = Image.new("RGB", (80, 160), "white")
        cut, box = alternatives.label_box_cut(image, TWO_LABELS[1:], 0.5)
        self.assertEqual((box, cut.size, cut.mode), ((8, 20, 72, 144), (64, 124), "RGBA"))



# A polygon inside the photo of `SIZE`: a trapezium around the bottle.
POLYGON = [[6, 6], [34, 6], [36, 76], [4, 76]]


class ManualCutTest(unittest.TestCase):
    """The manual cut of plan 56: a polygon replaces the SAM3 cut of the kind of the
    current type, and no automatic run replaces it."""
    setUp, tearDown = AlternativeRouteTest.setUp, AlternativeRouteTest.tearDown
    request, upload = AlternativeRouteTest.request, AlternativeRouteTest.upload
    set_type, settings = AlternativeRouteTest.set_type, AlternativeRouteTest.settings

    def cut(self, slug, digest, points):
        body = json.dumps({"slug": slug, "sha256": digest, "points": points}).encode()
        return self.request("/api/dataset-alternative-cut", "POST", body, "application/json")

    def reset(self, slug, digest):
        query = urllib.parse.urlencode({"slug": slug, "sha256": digest})
        return self.request("/api/dataset-alternative-cut?" + query, "DELETE")

    def manual(self, points=POLYGON):
        return ("seg", alternatives.MANUAL_HEAD + json.dumps(points, separators=(",", ":")))

    def test_a_manual_cut_replaces_the_package_cut(self):
        data = picture(transparent=False)
        self.upload("wine-b", data)
        self.assertEqual(self.settings(sha(data)), ("seg", derive.SETTINGS_SEG))
        status, out = self.cut("wine-b", sha(data), POLYGON)
        self.assertEqual(status, 200, out)
        self.assertEqual((out["type"], out["kind"], out["changed"]),
                         ("full_front", "package", True))
        photo, = out["record"]["_alternatives"]
        self.assertEqual((photo["derivation"], photo["manual"], photo["manual_points"]),
                         ("seg", True, POLYGON))
        self.assertEqual(self.settings(sha(data)), self.manual())
        self.assertTrue(derive.is_manual(self.settings(sha(data))[1]))
        with Image.open(self.root / photo["image_url"].lstrip("/")) as cut:
            self.assertEqual(cut.mode, "RGBA")
            # The box of the polygon (4, 6, 36, 76), with the soft edge of about 3 sigma
            # of `derive.EDGE_BLUR` around it.
            self.assertTrue(32 <= cut.width <= 40 and 70 <= cut.height <= 80, cut.size)
            self.assertEqual(cut.getpixel((0, 0))[3], 0)

    def test_no_automatic_run_replaces_the_manual_cut(self):
        data = picture(transparent=False)
        self.upload("wine-b", data)
        self.cut("wine-b", sha(data), POLYGON)
        calls = (len(self.sam3.instances_calls), self.sam3.segment_calls)
        self.assertEqual(self.upload("wine-b", data)[1]["changed"], False)
        self.assertEqual(self.set_type("wine-b", sha(data), "full_back")[0], 200)
        conn = labdb.connect(self.db)
        try:
            path = alternatives.file_path(self.db, "additional", sha(data), "png")
            report = derive.derive_all(conn, self.db, {sha(data): path}, self.sam3,
                                       lambda text: None)
        finally:
            conn.close()
        self.assertEqual((report.present, report.links), (1, []))
        self.assertEqual((len(self.sam3.instances_calls), self.sam3.segment_calls), calls)
        self.assertEqual(self.settings(sha(data)), self.manual())

    def test_the_other_kind_keeps_its_own_cut_and_a_change_back_reuses_the_manual_cut(self):
        data = picture(transparent=False)
        self.upload("wine-b", data)
        self.cut("wine-b", sha(data), POLYGON)
        self.sam3.answer = CLOSE_UP
        status, out = self.set_type("wine-b", sha(data), "label_front")
        self.assertEqual(status, 200, out)
        photo, = out["record"]["_alternatives"]
        self.assertEqual((photo["manual"], photo["manual_points"]), (False, None))
        self.assertEqual(self.settings(sha(data), "label"),
                         ("seg", alternatives.SETTINGS_LABEL_CLOSE_UP))
        calls = len(self.sam3.instances_calls)
        status, out = self.set_type("wine-b", sha(data), "full_front")
        photo, = out["record"]["_alternatives"]
        self.assertEqual((photo["manual"], photo["manual_points"]), (True, POLYGON))
        self.assertEqual(len(self.sam3.instances_calls), calls)

    def test_a_manual_label_cut_clears_the_absence_marker_and_stays(self):
        self.sam3.answer = CLOSE_UP
        data = picture(transparent=False)
        self.upload("wine-b", data)
        conn = sqlite3.connect(self.db)
        try:
            with conn:
                conn.execute("INSERT INTO image_derivative_absence (source_sha256, kind, "
                             "settings, reason) VALUES (?, 'label', ?, 'the box has no "
                             "separate label')", (sha(data), alternatives.SETTINGS_LABEL_ABSENCE))
        finally:
            conn.close()
        status, out = self.cut("wine-b", sha(data), POLYGON)
        self.assertEqual((status, out["kind"]), (200, "label"), out)
        self.assertEqual(self.settings(sha(data), "label"), self.manual())
        conn = labdb.connect(self.db)
        try:
            self.assertIsNone(alternatives.current_absence(conn, sha(data)))
            path = alternatives.file_path(self.db, "additional", sha(data), "png")
            out = alternatives.process_image(conn, self.db, sha(data), path, "label",
                                             DownSam3(), [], close_up=True)
        finally:
            conn.close()
        self.assertEqual((out.present, out.unavailable, out.links), (1, 0, []))

    def test_reset_removes_the_manual_cut_and_sam3_cuts_again(self):
        data = picture(transparent=False)
        self.upload("wine-b", data)
        self.cut("wine-b", sha(data), POLYGON)
        status, out = self.reset("wine-b", sha(data))
        self.assertEqual((status, out["changed"], out["kind"]), (200, True, "package"), out)
        photo, = out["record"]["_alternatives"]
        self.assertEqual((photo["derivation"], photo["manual"]), ("seg", False))
        self.assertEqual(self.settings(sha(data)), ("seg", derive.SETTINGS_SEG))
        status, out = self.reset("wine-b", sha(data))
        self.assertEqual((status, out["changed"]), (200, False))

    def test_reset_with_no_sam3_shows_the_photo_and_warns(self):
        data = picture(transparent=False)
        self.upload("wine-b", data)
        self.cut("wine-b", sha(data), POLYGON)
        self.server.segmenter = DownSam3()
        status, out = self.reset("wine-b", sha(data))
        self.assertEqual((status, out["changed"]), (200, True), out)
        self.assertIn(alternatives.NO_PROCESSED_FILE, out["warning"])
        photo, = out["record"]["_alternatives"]
        self.assertEqual((photo["derivation"], photo["image_url"]), (None, photo["url"]))
        self.assertIsNone(self.settings(sha(data)))

    def test_points_outside_the_photo_are_clamped(self):
        data = picture(transparent=False)
        self.upload("wine-b", data)
        status, out = self.cut("wine-b", sha(data), [[-5, -5.4], [50.2, 0], [20, 90]])
        self.assertEqual(status, 200, out)
        photo, = out["record"]["_alternatives"]
        self.assertEqual(photo["manual_points"], [[0, 0], [40, 0], [20, 80]])

    def test_bad_cut_requests_are_refused(self):
        data = picture(transparent=False)
        self.upload("wine-b", data)
        for points in (None, [[1, 1], [30, 30]], [[1, 1], [30, "x"], [5, 60]],
                       [[1, 1], [30, True], [5, 60]], [[1, 1, 1], [30, 1], [5, 60]],
                       [[10, 1], [10, 40], [11, 70]], [[0, 0]] * 1001):
            self.assertEqual(self.cut("wine-b", sha(data), points)[0], 400, points)
        self.assertEqual(self.cut("wine-b", "0" * 64, POLYGON)[0], 404)
        self.assertEqual(self.cut("wine-x", sha(data), POLYGON)[0], 404)
        self.assertEqual(self.cut("", sha(data), POLYGON)[0], 400)
        self.assertEqual(self.reset("wine-b", "0" * 64)[0], 404)
        self.assertEqual(self.settings(sha(data)), ("seg", derive.SETTINGS_SEG))

    def test_the_alpha_of_the_original_limits_the_cut(self):
        image = Image.open(io.BytesIO(picture(transparent=True))).convert("RGBA")
        cut, box = alternatives.polygon_cut(image, [[0, 0], [40, 0], [40, 80], [0, 80]])
        self.assertEqual((box, cut.size), ((10, 10, 30, 70), (20, 60)))

    def test_manual_points_reads_a_manual_cut_alone(self):
        self.assertEqual(alternatives.manual_points(self.manual()[1]), POLYGON)
        self.assertIsNone(alternatives.manual_points(derive.SETTINGS_SEG))
        self.assertIsNone(alternatives.manual_points(None))
        self.assertIsNone(alternatives.manual_points(alternatives.MANUAL_HEAD + "[bad"))


if __name__ == "__main__":
    unittest.main()
