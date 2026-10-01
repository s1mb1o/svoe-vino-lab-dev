"""Tests of `pipeline/local_images.py`: the local image of a drop from the Codex app."""
import json
import os
import sys
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import local_images as LI  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 16


class LocalImagesTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.home = Path(os.path.realpath(self.directory.name))
        self.images = self.home / ".codex-3" / "generated_images" / "run"
        self.images.mkdir(parents=True)
        (self.home / "other").mkdir()
        self.roots = LI.allowed_roots(str(self.home))

    def address(self, path):
        return "app://fs/@fs" + urllib.parse.quote(str(path))

    def test_allowed_roots_are_the_codex_image_folders(self):
        (self.home / ".codex" / "generated_images").mkdir(parents=True)
        (self.home / ".codex-9").mkdir()
        self.assertEqual(LI.allowed_roots(str(self.home)), sorted([
            str(self.home / ".codex" / "generated_images"),
            str(self.home / ".codex-3" / "generated_images")]))

    def test_path_of_the_app_and_file_addresses(self):
        self.assertEqual(LI.path_of("app://fs/@fs/Users/a/b%20c.png"), "/Users/a/b c.png")
        self.assertEqual(LI.path_of("file:///Users/a/b.png"), "/Users/a/b.png")
        self.assertEqual(LI.path_of("file://localhost/Users/a/b.png"), "/Users/a/b.png")
        for bad in ("", "https://example.com/a.png", "file://host/a.png", "app://fs/a.png"):
            with self.subTest(bad=bad), self.assertRaises(LI.LocalImageError) as caught:
                LI.path_of(bad)
            self.assertEqual(caught.exception.code, 400)

    def test_a_codex_image_is_read(self):
        path = self.images / "exec 1.png"
        path.write_bytes(PNG)
        data, name, content_type = LI.read_image(self.address(path), self.roots)
        self.assertEqual((data, name, content_type), (PNG, "exec 1.png", "image/png"))

    def test_a_path_out_of_the_codex_folders_is_refused(self):
        outside = self.home / "other" / "a.png"
        outside.write_bytes(PNG)
        link = self.images / "link.png"
        link.symlink_to(outside)
        climb = str(self.images) + "/../../../other/a.png"
        for address in (self.address(outside), self.address(link), "app://fs/@fs" + climb):
            with self.subTest(address=address), self.assertRaises(LI.LocalImageError) as caught:
                LI.read_image(address, self.roots)
            self.assertEqual(caught.exception.code, 403)

    def test_no_root_refuses_each_path(self):
        path = self.images / "a.png"
        path.write_bytes(PNG)
        with self.assertRaises(LI.LocalImageError) as caught:
            LI.read_image(self.address(path), [])
        self.assertEqual(caught.exception.code, 403)

    def test_the_extension_the_presence_and_the_size_are_checked(self):
        (self.images / "a.txt").write_bytes(b"text")
        (self.images / "big.png").write_bytes(PNG * 10)
        (self.images / "empty.png").write_bytes(b"")
        cases = (("a.txt", 400), ("missing.png", 404), ("big.png", 413), ("empty.png", 400))
        for name, code in cases:
            with self.subTest(name=name), self.assertRaises(LI.LocalImageError) as caught:
                LI.read_image(self.address(self.images / name), self.roots, limit=len(PNG))
            self.assertEqual(caught.exception.code, code)

    def test_respond_gives_the_bytes_or_a_json_error(self):
        path = self.images / "a.webp"
        path.write_bytes(PNG)
        query = urllib.parse.urlencode({"address": self.address(path)})
        with mock.patch.object(LI, "allowed_roots", return_value=self.roots):
            self.assertEqual(LI.respond("GET", LI.API + "?" + query),
                             (200, PNG, "image/webp", "no-store"))
            code, body, content_type, _ = LI.respond("GET", LI.API)
            self.assertEqual((code, content_type), (400, LI.JSON_TYPE))
            self.assertIn("error", json.loads(body))
            self.assertEqual(LI.respond("POST", LI.API + "?" + query)[0], 405)

    def test_handles_only_its_route(self):
        self.assertTrue(LI.handles("/api/local-image"))
        self.assertFalse(LI.handles("/api/local-image/x"))


if __name__ == "__main__":
    unittest.main()
