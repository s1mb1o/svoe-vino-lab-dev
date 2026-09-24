import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "review_server_for_inbox_upload_tests", ROOT / "scripts" / "review_server.py")
SERVER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SERVER)

PNG = b"\x89PNG\r\n\x1a\nsmall-test-body"


class InboxUploadTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.old_my = SERVER.MY
        SERVER.MY = self.directory.name

    def tearDown(self):
        SERVER.MY = self.old_my
        self.directory.cleanup()

    def test_store_keeps_safe_source_name_and_content_extension(self):
        name = SERVER.store_inbox_image(
            PNG, "folder\\Wine bottle.jpg")

        self.assertEqual(name, "Wine bottle.png")
        self.assertEqual(SERVER.scan_inbox(), ["Wine bottle.png"])
        self.assertEqual((Path(self.directory.name) / name).read_bytes(), PNG)

    def test_duplicate_name_does_not_replace_the_first_file(self):
        first = SERVER.store_inbox_image(PNG, "wine.png")
        second = SERVER.store_inbox_image(PNG + b"2", "wine.png")

        self.assertEqual(first, "wine.png")
        self.assertEqual(second, "wine_inbox2.png")
        self.assertEqual((Path(self.directory.name) / first).read_bytes(), PNG)

    def test_unsafe_name_is_reduced_to_one_file_name(self):
        name = SERVER.store_inbox_image(PNG, "../../.wine?.jpeg")

        self.assertEqual(name, "wine_.png")
        self.assertNotIn("/", name)
        self.assertNotIn("\\", name)

    def test_non_image_body_is_refused(self):
        with self.assertRaisesRegex(ValueError, "not an image type"):
            SERVER.store_inbox_image(b"plain text", "fake.png")

        self.assertEqual(SERVER.scan_inbox(), [])


if __name__ == "__main__":
    unittest.main()
