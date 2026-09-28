"""The button ↻ of an alternative photo: `POST /api/dataset-alternative-recut` (owner
message of 2026-09-27T00:51:44+0300). SAM3 gets the photo again with no cache read, and
the photo is cut again from the fresh answers."""
import json
import sqlite3
import sys
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "tests"))
import alternatives  # noqa: E402
import derive  # noqa: E402
import test_alternatives as TA  # noqa: E402


class RecutRouteTest(unittest.TestCase):
    setUp, tearDown = TA.AlternativeRouteTest.setUp, TA.AlternativeRouteTest.tearDown
    request, upload = TA.AlternativeRouteTest.request, TA.AlternativeRouteTest.upload
    settings = TA.AlternativeRouteTest.settings

    def recut(self, slug, digest):
        body = json.dumps({"slug": slug, "sha256": digest}).encode()
        return self.request("/api/dataset-alternative-recut", "POST", body, "application/json")

    def box(self, digest, kind):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute("SELECT box_left, box_top, box_right, box_bottom FROM "
                                "image_derivative WHERE source_sha256 = ? AND kind = ?",
                                (digest, kind)).fetchone()
        finally:
            conn.close()

    def forget_calls(self):
        self.sam3.instances_calls, self.sam3.segment_calls = [], 0

    def test_a_full_photo_asks_sam3_again_and_gets_a_new_package_cut(self):
        data = TA.picture(transparent=False)
        self.upload("wine-b", data)
        self.forget_calls()
        status, out = self.recut("wine-b", TA.sha(data))
        self.assertEqual(status, 200, out)
        self.assertEqual((out["type"], out["kind"], out["changed"]),
                         ("full_front", "package", True))
        # The first step asks the package nouns; the second cuts from the answer.
        self.assertEqual(self.sam3.instances_calls, [derive.SAM3_TEXTS])
        self.assertEqual(self.sam3.segment_calls, 1)
        self.assertEqual(self.settings(TA.sha(data)), ("seg", derive.SETTINGS_SEG))
        photo, = out["record"]["_alternatives"]
        self.assertEqual((photo["derivation"], photo["manual"]), ("seg", False))

    def test_a_label_close_up_keeps_the_close_up_rule(self):
        # The condition of session 4f: a close-up is cut with `close_up`, not with the
        # bottle test of a full photo, so the sticker does not win.
        self.sam3.answer = TA.STICKER_CLOSE_UP
        data = TA.picture(transparent=False)
        self.upload("wine-b", data)
        before = self.box(TA.sha(data), "label")
        self.forget_calls()
        status, out = self.recut("wine-b", TA.sha(data))
        self.assertEqual(status, 200, out)
        self.assertEqual((out["type"], out["kind"]), ("label_front", "label"))
        self.assertEqual(self.sam3.instances_calls[:2],
                         [alternatives.DETECT_TEXTS, derive.SAM3_TEXTS])
        self.assertEqual(self.settings(TA.sha(data), "label"),
                         ("seg", alternatives.SETTINGS_LABEL_CLOSE_UP))
        self.assertEqual(self.box(TA.sha(data), "label"), before)
        photo, = out["record"]["_alternatives"]
        with Image.open(self.root / photo["image_url"].lstrip("/")) as cut:
            self.assertGreaterEqual(cut.width, 36)
            self.assertGreaterEqual(cut.height, 72)

    def test_a_transparent_full_photo_sends_no_sam3_request(self):
        data = TA.picture(transparent=True)
        self.upload("wine-b", data)
        self.forget_calls()
        status, out = self.recut("wine-b", TA.sha(data))
        self.assertEqual(status, 200, out)
        self.assertEqual((self.sam3.segment_calls, self.settings(TA.sha(data))),
                         (0, ("crop", derive.SETTINGS_ALPHA)))
        # Only the detection of the type asked SAM3; the recut asked nothing.
        self.assertEqual(self.sam3.instances_calls, [])

    def test_a_manual_cut_is_refused_and_stays(self):
        data = TA.picture(transparent=False)
        self.upload("wine-b", data)
        body = json.dumps({"slug": "wine-b", "sha256": TA.sha(data),
                           "points": TA.POLYGON}).encode()
        status, out = self.request("/api/dataset-alternative-cut", "POST", body,
                                   "application/json")
        self.assertEqual(status, 200, out)
        manual = self.settings(TA.sha(data))
        self.forget_calls()
        status, out = self.recut("wine-b", TA.sha(data))
        self.assertEqual(status, 409, out)
        self.assertIn("manual cut", out["error"])
        self.assertEqual(self.settings(TA.sha(data)), manual)
        self.assertEqual((self.sam3.instances_calls, self.sam3.segment_calls), ([], 0))

    def test_sam3_down_keeps_the_old_cut(self):
        data = TA.picture(transparent=False)
        self.upload("wine-b", data)
        before = (self.settings(TA.sha(data)), self.box(TA.sha(data), "package"))
        self.server.segmenter = TA.DownSam3()
        status, out = self.recut("wine-b", TA.sha(data))
        self.assertEqual(status, 503, out)
        self.assertIn("the cut stays", out["error"])
        self.assertEqual((self.settings(TA.sha(data)), self.box(TA.sha(data), "package")),
                         before)

    def test_an_unknown_photo_is_404(self):
        status, out = self.recut("wine-b", TA.sha(b"no photo"))
        self.assertEqual(status, 404, out)

    def test_a_get_is_not_a_route(self):
        status, _out = self.request("/api/dataset-alternative-recut")
        self.assertNotEqual(status, 200)


if __name__ == "__main__":
    unittest.main()
