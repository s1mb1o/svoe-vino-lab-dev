"""An add or a remove of a code of a wine deletes the barcode scans of its test photos
(owner answers of 2026-09-27T16:49:57+0300)."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

import lab_server as LAB  # noqa: E402
import labdb  # noqa: E402
import model_cache  # noqa: E402

WINES = [
    ("wine-b", "Вино b", "Винодельня", "Белое", "Соломенный", "Крым",
     "Алиготе", "Описание b", "b.webp", "Active", None),
    ("wine-a", "Вино a", "Винодельня", "Красное", "Рубиновый", "Кубань",
     None, "Описание a", "a.webp", "Active", None),
]
PHOTO_B, PHOTO_B2, PHOTO_A = "b" * 64, "c" * 64, "a" * 64


class CodeCacheForgetTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.db = str(self.root / "lab.sqlite3")
        conn = labdb.connect(self.db, create=True)
        with conn:
            conn.executemany("INSERT INTO wine_catalog (%s) VALUES (?,?,?,?,?,?,?,?,?,?,?)"
                             % ", ".join(LAB.CATALOG_COLUMNS), WINES)
            conn.executemany("INSERT INTO image (sha256, folder, extension) "
                             "VALUES (?, 'testset', 'jpg')",
                             [(PHOTO_B,), (PHOTO_B2,), (PHOTO_A,)])
            conn.execute("INSERT INTO test_set (set_name, source_dir) VALUES ('s', 'd')")
            conn.executemany("INSERT INTO test_photo (set_name, place, file_name, sha256) "
                             "VALUES ('s', ?, ?, ?)",
                             [("wine-b", "1.jpg", PHOTO_B), ("wine-b", "2.jpg", PHOTO_B2),
                              ("wine-a", "1.jpg", PHOTO_A)])
        conn.close()
        patcher = mock.patch.object(model_cache, "ROOT", str(self.root / "cache"))
        patcher.start()
        self.addCleanup(patcher.stop)

    def scan(self, photo, options=None):
        """Store one barcode scan record of the photo with the sha256 `photo`."""
        fields = model_cache.request_fields("local://barcode/scan", "barcode",
                                            {"options": options or {}}, "", [])
        fields["images"] = [photo]
        model_cache.store(fields, {"batches": [[]]}, 1)
        return fields

    def test_an_add_and_a_remove_delete_the_scans_of_the_photos_of_the_wine(self):
        b1, b1_qr, b2 = self.scan(PHOTO_B), self.scan(PHOTO_B, {"qr": False}), self.scan(PHOTO_B2)
        a = self.scan(PHOTO_A)
        answer = LAB.add_code(self.db, "/api/dataset-gtin", "wine-b", "4631168664979")
        self.assertNotIn("barcode_cache_deleted", answer)
        for fields in (b1, b1_qr, b2):
            self.assertIsNone(model_cache.lookup(fields))
        self.assertIsNotNone(model_cache.lookup(a))

        b1 = self.scan(PHOTO_B)
        LAB.remove_code(self.db, "/api/dataset-gtin", "wine-b", "04631168664979")
        self.assertIsNone(model_cache.lookup(b1))

        LAB.add_code(self.db, "/api/dataset-qr-url", "wine-a", "https://a.ru/w")
        self.assertIsNone(model_cache.lookup(a))

    def test_a_refused_change_deletes_no_scan(self):
        LAB.add_code(self.db, "/api/dataset-gtin", "wine-b", "4631168664979")
        b1 = self.scan(PHOTO_B)
        for call in (lambda: LAB.add_code(self.db, "/api/dataset-gtin", "wine-b",
                                          "4631168664979"),
                     lambda: LAB.remove_code(self.db, "/api/dataset-gtin", "wine-b",
                                             "04600682000181"),
                     lambda: LAB.add_code(self.db, "/api/dataset-gtin", "wine-none",
                                          "4631168664979")):
            with self.assertRaises(LAB.StateError):
                call()
        self.assertIsNotNone(model_cache.lookup(b1))

    def test_a_wine_with_no_test_photo_deletes_nothing(self):
        conn = labdb.connect(self.db)
        with conn:
            conn.execute("DELETE FROM test_photo WHERE place = 'wine-a'")
        conn.close()
        a = self.scan(PHOTO_A)
        LAB.add_code(self.db, "/api/dataset-gtin", "wine-a", "4631168664979")
        self.assertIsNotNone(model_cache.lookup(a))
        self.assertEqual(LAB.forget_scans(self.db, "wine-a"), 0)

    def test_forget_scans_counts_the_deleted_records(self):
        self.scan(PHOTO_B)
        self.scan(PHOTO_B2)
        self.assertEqual(LAB.forget_scans(self.db, "wine-b"), 2)
        self.assertEqual(LAB.forget_scans(self.db, "wine-b"), 0)


if __name__ == "__main__":
    unittest.main()
