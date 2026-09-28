"""Verify the standalone matcher bundle builder and validator."""

import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np

import embedding_lab  # noqa: F401  (puts pipeline/ on sys.path)
from embedding_lab import FakeGateway, standard_lab

import build_embeddings  # noqa: E402
import embeddings  # noqa: E402
import matcher_bundle  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]


class MatcherBundleTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.gateway = FakeGateway()
        self.lab = standard_lab(self.root / "lab", self.gateway.base_url)
        settings = embeddings.load_settings(self.lab.config_path)
        embedding = settings.find("gw")
        directory = Path(self.lab.entry_dir())
        directory.mkdir(parents=True)
        with contextlib.redirect_stdout(io.StringIO()):
            build_embeddings.run(
                embedding, settings.db_path, directory,
                make_backend=lambda value: build_embeddings.OpenAIBackend(
                    value, waits=(), timeout=10))

    def tearDown(self):
        self.gateway.close()
        self.lab.close()
        self.temporary.cleanup()

    def build(self, name="bundle", images=False):
        path = self.root / name
        result = matcher_bundle.build_bundle(
            self.lab.config_path, "gw", path, include_images=images)
        return path, result

    def rewrite(self, path, name, rows):
        """Replace one JSONL payload and its manifest record."""
        payload = path / name
        payload.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                                   for row in rows), encoding="utf-8")
        manifest_path = path / matcher_bundle.MANIFEST
        manifest = json.loads(manifest_path.read_text())
        manifest["files"][name] = matcher_bundle.file_record(payload)
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        return manifest

    def wines(self, path):
        return [json.loads(line) for line in
                (path / matcher_bundle.WINES).read_text(encoding="utf-8").splitlines()]

    def test_version_2_wines_hold_the_card_fields(self):
        for value in ("https://Example.COM:443/a", "http://example.com",
                      "https://example.com/a#part"):
            self.lab.conn.execute(
                "INSERT INTO wine_code (wine_slug, kind, value) VALUES ('grey', 'qr_url', ?)",
                (value,))
        self.lab.conn.commit()
        path, result = self.build()
        self.assertEqual(result["format_version"], 2)
        wines = {wine["wine_slug"]: wine for wine in self.wines(path)}
        grey = wines["grey"]
        self.assertEqual(set(grey), matcher_bundle.WINE_KEYS)
        self.assertEqual(grey["name"], "Name grey")
        self.assertEqual(grey["color"], "красное")
        self.assertIsNone(grey["grapes"])
        self.assertEqual(grey["page_url"], "https://vino-svoe.ru/wines/grey")
        self.assertEqual(grey["image_url"],
                         matcher_bundle.IMAGE_URL_PREFIX + self.lab.grey[:8] + ".png")
        self.assertEqual(grey["qr_urls"], ["http://example.com/", "https://example.com/a"])
        # The official image of `patched` is its `main`, not the lab `main_patched`.
        self.assertEqual(wines["patched"]["image_url"],
                         matcher_bundle.IMAGE_URL_PREFIX + self.lab.patched_main[:8] + ".png")
        self.assertEqual(wines["transparent"]["qr_urls"], [])

    def test_validator_accepts_a_version_1_bundle(self):
        path, _ = self.build()
        rows = [{key: wine[key] for key in matcher_bundle.WINE_KEYS_V1}
                for wine in self.wines(path)]
        manifest = self.rewrite(path, matcher_bundle.WINES, rows)
        manifest["format_version"] = 1
        (path / matcher_bundle.MANIFEST).write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        self.assertEqual(matcher_bundle.validate_bundle(path)["format_version"], 1)

    def test_validator_rejects_a_version_2_wine_without_a_card_field(self):
        path, _ = self.build()
        rows = self.wines(path)
        del rows[0]["qr_urls"]
        self.rewrite(path, matcher_bundle.WINES, rows)
        with self.assertRaisesRegex(matcher_bundle.BundleError, "missing: qr_urls"):
            matcher_bundle.validate_bundle(path)

    def test_validator_rejects_a_qr_url_that_is_not_normalized(self):
        path, _ = self.build()
        rows = self.wines(path)
        rows[0]["qr_urls"] = ["HTTPS://Example.COM/a"]
        self.rewrite(path, matcher_bundle.WINES, rows)
        with self.assertRaisesRegex(matcher_bundle.BundleError, "normalized"):
            matcher_bundle.validate_bundle(path)

    def test_validator_rejects_a_page_url_that_is_not_https(self):
        path, _ = self.build()
        rows = self.wines(path)
        rows[0]["page_url"] = "http://vino-svoe.ru/wines/x"
        self.rewrite(path, matcher_bundle.WINES, rows)
        with self.assertRaisesRegex(matcher_bundle.BundleError, "page_url"):
            matcher_bundle.validate_bundle(path)

    def test_bundle_without_images_is_self_contained_metadata(self):
        path, result = self.build()
        self.assertEqual(result["items"], 4)
        self.assertEqual(result["candidates"], 5)
        self.assertEqual(result["wines"], 4)
        self.assertEqual(result["omissions"], 5)
        self.assertEqual(result["images"], 0)
        self.assertFalse((path / "images").exists())
        vectors = np.load(path / matcher_bundle.VECTORS, allow_pickle=False)
        self.assertEqual(vectors.shape, (4, 8))
        items = [json.loads(line) for line in
                 (path / matcher_bundle.ITEMS).read_text().splitlines()]
        shared_row = next(row["vector_row"] for row in items
                          if row["source_sha256"] == self.lab.transparent
                          and row["view"] == "full")
        candidates = [json.loads(line) for line in
                      (path / matcher_bundle.CANDIDATES).read_text().splitlines()]
        owners = [row["wine_slug"] for row in candidates
                  if row["vector_row"] == shared_row]
        self.assertEqual(owners, ["transparent", "shared"])
        self.assertEqual(matcher_bundle.validate_bundle(path)["dimension"], 8)

    def test_bundle_with_images_validates_each_prepared_image(self):
        path, result = self.build(images=True)
        self.assertEqual(result["images"], 4)
        images = [json.loads(line) for line in
                  (path / matcher_bundle.IMAGE_MANIFEST).read_text().splitlines()]
        self.assertEqual(len(images), 4)
        self.assertTrue(all((path / row["path"]).is_file() for row in images))
        Path(self.lab.db_path).rename(self.root / "source-database-hidden")
        Path(self.lab.entry_dir()).rename(self.root / "source-embedding-hidden")
        matcher_bundle.validate_bundle(path)

    def test_validator_rejects_a_modified_vector_file(self):
        path, _ = self.build()
        with open(path / matcher_bundle.VECTORS, "ab") as target:
            target.write(b"changed")
        with self.assertRaisesRegex(matcher_bundle.BundleError, "does not match"):
            matcher_bundle.validate_bundle(path)

    def test_validator_rejects_fortran_order_vectors(self):
        path, _ = self.build()
        vector_path = path / matcher_bundle.VECTORS
        vectors = np.load(vector_path, allow_pickle=False)
        np.save(vector_path, np.asfortranarray(vectors), allow_pickle=False)
        manifest_path = path / matcher_bundle.MANIFEST
        manifest = json.loads(manifest_path.read_text())
        manifest["files"][matcher_bundle.VECTORS] = matcher_bundle.file_record(vector_path)
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        with self.assertRaisesRegex(matcher_bundle.BundleError, "C-contiguous"):
            matcher_bundle.validate_bundle(path)

    def test_validator_rejects_an_unknown_candidate_wine(self):
        path, _ = self.build()
        candidate_path = path / matcher_bundle.CANDIDATES
        rows = [json.loads(line) for line in candidate_path.read_text().splitlines()]
        rows[0]["wine_slug"] = "not-in-wines"
        candidate_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n"
                                          for row in rows))
        manifest_path = path / matcher_bundle.MANIFEST
        manifest = json.loads(manifest_path.read_text())
        manifest["files"][matcher_bundle.CANDIDATES] = matcher_bundle.file_record(candidate_path)
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        with self.assertRaisesRegex(matcher_bundle.BundleError, "unknown wine_slug"):
            matcher_bundle.validate_bundle(path)

    def test_validator_rejects_a_modified_prepared_image(self):
        path, _ = self.build(images=True)
        image = json.loads((path / matcher_bundle.IMAGE_MANIFEST).read_text().splitlines()[0])
        with open(path / image["path"], "ab") as target:
            target.write(b"changed")
        with self.assertRaisesRegex(matcher_bundle.BundleError, "prepared image"):
            matcher_bundle.validate_bundle(path)

    def test_validator_rejects_a_symbolic_link_image_directory(self):
        path, _ = self.build(images=True)
        image_dir = path / "images"
        moved = path / "moved-images"
        image_dir.rename(moved)
        image_dir.symlink_to(moved.name, target_is_directory=True)
        with self.assertRaisesRegex(matcher_bundle.BundleError, "symbolic link"):
            matcher_bundle.validate_bundle(path)

    def test_builder_refuses_an_existing_output(self):
        output = self.root / "exists"
        output.mkdir()
        with self.assertRaisesRegex(matcher_bundle.BundleError, "output path exists"):
            matcher_bundle.build_bundle(self.lab.config_path, "gw", output)

    def test_builder_and_validator_scripts(self):
        output = self.root / "from-cli"
        built = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "build_matcher_bundle.py"),
             "--config", self.lab.config_path, "--embedding", "gw", "--out", str(output)],
            cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertEqual(built.returncode, 0, built.stderr)
        self.assertEqual(json.loads(built.stdout)["items"], 4)
        checked = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "validate_matcher_bundle.py"),
             str(output)], cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertEqual(json.loads(checked.stdout)["format_version"], 2)


if __name__ == "__main__":
    unittest.main()
