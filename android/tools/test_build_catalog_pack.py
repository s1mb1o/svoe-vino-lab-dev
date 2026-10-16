import argparse
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest import mock
import zipfile

import numpy as np
from PIL import Image

from tools import build_catalog_pack


class BuildCatalogPackTest(unittest.TestCase):
    def test_builds_one_image_and_72_reference_vectors_per_wine(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            catalog, dis, siglip, yolo = self.make_sources(root)
            output = root / "default_model_pack.zip"
            result = self.build(catalog, dis, siglip, yolo, output)

            self.assertEqual(result["vectors"], 144)
            self.assertEqual(result["wines"], 2)
            self.assertEqual(result["images"], 2)
            self.assertEqual(result["omitted_wines"], 1)
            self.assertEqual(result["codes"], 1)
            self.assertEqual(result["omissions"][0]["wine_slug"], "missing")
            self.assertEqual(build_catalog_pack.validate_pack(output)["wines"], 2)

            with zipfile.ZipFile(output) as pack:
                manifest = json.loads(pack.read("manifest.json"))
                self.assertEqual(manifest["format_version"], 3)
                self.assertEqual(manifest["reference_rotation_step_degrees"], 5)
                self.assertEqual(manifest["reference_frames_per_image"], 72)
                self.assertIn(build_catalog_pack.build_model_pack.YOLO_MODEL_FILE, pack.namelist())
                self.assertEqual(
                    manifest["image_selection"], "package_cut_transparent_webp",
                )
                self.assertEqual(manifest["image_format"], "webp")
                self.assertEqual(manifest["image_max_side"], 1024)
                self.assertTrue(manifest["image_transparent"])
                wines = [json.loads(line) for line in pack.read("wines.jsonl").splitlines()]
                self.assertEqual(
                    [(row["wine_slug"], row["image_type"]) for row in wines],
                    [("main-only", "package_crop"), ("patched", "package_seg")],
                )
                self.assertEqual(
                    [row["image_source_type"] for row in wines],
                    ["main", "main_patched"],
                )
                with zipfile.ZipFile(pack.open("images.zip")) as images:
                    self.assertEqual(
                        images.namelist(),
                        ["images/main-only.webp", "images/patched.webp"],
                    )
                    for row in wines:
                        image_bytes = images.read(row["image_path"])
                        self.assertEqual(
                            hashlib.sha256(image_bytes).hexdigest(), row["image_sha256"],
                        )
                        with Image.open(io.BytesIO(image_bytes)) as image:
                            self.assertEqual(image.format, "WEBP")
                            self.assertLessEqual(max(image.size), 1024)
                            alpha_min = image.convert("RGBA").getchannel("A").getextrema()[0]
                            self.assertLess(alpha_min, 255)
                    with Image.open(images.open("images/main-only.webp")) as image:
                        self.assertEqual(max(image.size), 1024)
                vector_bytes = pack.read("vectors.f32")
                vectors = np.frombuffer(vector_bytes, dtype="<f4").reshape(-1, 768)
                self.assertEqual(int(np.argmax(vectors[0])), 0)
                self.assertEqual(int(np.argmax(vectors[71])), 0)
                self.assertEqual(int(np.argmax(vectors[72])), 2)
                candidates = [
                    json.loads(line)
                    for line in pack.read("candidates.jsonl").splitlines()
                ]
                self.assertEqual(len(candidates), 144)
                self.assertEqual(
                    [row["angle"] for row in candidates[:72]],
                    list(range(0, 360, 5)),
                )

    def test_refuses_an_opaque_package_cut(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "opaque.png"
            Image.new("RGB", (40, 80), "red").save(source)
            with self.assertRaisesRegex(
                build_catalog_pack.CatalogPackError,
                "no transparent background",
            ):
                build_catalog_pack.export_display_image(source, root / "output.webp")

    def test_refuses_an_incomplete_reference_rotation_sequence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            catalog, _, _, _ = self.make_sources(root)
            index_path = (
                catalog / "embeddings" / "android-siglip2-base-224-dis-white-rot5" /
                "index.json"
            )
            index = json.loads(index_path.read_text(encoding="utf-8"))
            index["items"][0]["angles"].pop()
            index_path.write_text(json.dumps(index), encoding="utf-8")

            with self.assertRaisesRegex(
                build_catalog_pack.CatalogPackError,
                "all 72 Android reference angles",
            ):
                build_catalog_pack.load_index(
                    catalog, "android-siglip2-base-224-dis-white-rot5")

    def test_refuses_to_replace_an_existing_pack_without_flag(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            catalog, dis, siglip, yolo = self.make_sources(root)
            output = root / "default_model_pack.zip"
            output.write_bytes(b"old")
            with self.assertRaisesRegex(build_catalog_pack.CatalogPackError, "--replace"):
                self.build(catalog, dis, siglip, yolo, output)

    def build(self, catalog, dis, siglip, yolo, output):
        args = argparse.Namespace(
            catalog=str(catalog),
            embedding="android-siglip2-base-224-dis-white-rot5",
            dis_model=str(dis),
            siglip_model=str(siglip),
            yolo_model=str(yolo),
            out=str(output),
            version="test",
            replace=False,
        )
        with mock.patch.multiple(
            build_catalog_pack.build_model_pack,
            DIS_MODEL_SHA256=build_catalog_pack.file_digest(dis),
            SIGLIP_MODEL_SHA256=build_catalog_pack.file_digest(siglip),
            YOLO_MODEL_SHA256=build_catalog_pack.file_digest(yolo),
        ):
            return build_catalog_pack.build(args)

    def make_sources(self, root):
        catalog = root / "catalog"
        (catalog / "images" / "main").mkdir(parents=True)
        (catalog / "images" / "patched").mkdir(parents=True)
        (catalog / "cuts").mkdir(parents=True)
        database = catalog / "catalog.sqlite3"
        connection = sqlite3.connect(database)
        connection.executescript(
            """
            CREATE TABLE wine_catalog (
                wine_slug TEXT PRIMARY KEY, name TEXT, producer TEXT, category TEXT,
                region TEXT, color TEXT, grapes TEXT, state TEXT
            );
            CREATE TABLE image (
                sha256 TEXT PRIMARY KEY, folder TEXT, extension TEXT
            );
            CREATE TABLE image_derivative (
                source_sha256 TEXT, method TEXT, sha256 TEXT, kind TEXT
            );
            CREATE TABLE wine_image (
                wine_slug TEXT, image_type TEXT, sha256 TEXT
            );
            CREATE TABLE wine_code (wine_slug TEXT, kind TEXT, value TEXT);
            """
        )
        for slug in ("main-only", "missing", "patched"):
            connection.execute(
                "INSERT INTO wine_catalog VALUES (?, ?, ?, ?, ?, ?, ?, 'Active')",
                (slug, slug, None, None, None, None, None),
            )
        sources = {}
        for label, data, folder, extension in (
            ("main-only", b"main only", "main", "jpg"),
            ("patched-main", b"old main", "main", "webp"),
            ("patched", b"patched image", "patched", "png"),
        ):
            digest = hashlib.sha256(data).hexdigest()
            sources[label] = digest
            path = build_catalog_pack.catalogue_image_path(
                catalog, folder, digest, extension,
            )
            path.write_bytes(data)
            connection.execute("INSERT INTO image VALUES (?, ?, ?)",
                               (digest, folder, extension))
        connection.execute("INSERT INTO wine_image VALUES ('main-only','main',?)",
                           (sources["main-only"],))
        connection.execute("INSERT INTO wine_image VALUES ('patched','main',?)",
                           (sources["patched-main"],))
        connection.execute("INSERT INTO wine_image VALUES ('patched','main_patched',?)",
                           (sources["patched"],))
        for label, source_label, method, size, color in (
            ("main-cut", "main-only", "crop", (1600, 800), (180, 30, 60, 255)),
            ("patched-cut", "patched", "seg", (240, 700), (20, 120, 170, 255)),
        ):
            image = Image.new("RGBA", size, (0, 0, 0, 0))
            image.paste(color, (20, 20, size[0] - 20, size[1] - 20))
            path = catalog / "cuts" / f"{label}.png"
            image.save(path)
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            final_path = catalog / "cuts" / f"{digest}.png"
            path.replace(final_path)
            connection.execute("INSERT INTO image VALUES (?, 'cropped', 'png')", (digest,))
            connection.execute(
                "INSERT INTO image_derivative VALUES (?, ?, ?, 'package')",
                (sources[source_label], method, digest),
            )
        connection.execute(
            "INSERT INTO wine_code VALUES ('patched','gtin','04631168664979')"
        )
        connection.commit()
        connection.close()

        embedding = catalog / "embeddings" / "android-siglip2-base-224-dis-white-rot5"
        embedding.mkdir(parents=True)
        angles = list(range(0, 360, 5))
        vectors = np.zeros((3 * len(angles), 768), dtype=np.float32)
        vectors[0:72, 0] = 1
        vectors[72:144, 1] = 1
        vectors[144:216, 2] = 1
        np.save(embedding / "vectors.npy", vectors, allow_pickle=False)
        (embedding / "index.json").write_text(
            json.dumps({
                "name": "android-siglip2-base-224-dis-white-rot5",
                "dim": 768,
                "vectors_file": "vectors.npy",
                "updated_at": "test",
                "config": {
                    "model": "vit_base_patch16_siglip_224.v2_webli",
                    "rotation_step": 5,
                },
                "items": [
                    {"source_sha256": sources["main-only"], "view": "full", "row": 0,
                     "angles": angles},
                    {"source_sha256": sources["patched-main"], "view": "full", "row": 72,
                     "angles": angles},
                    {"source_sha256": sources["patched"], "view": "full", "row": 144,
                     "angles": angles},
                ],
            }),
            encoding="utf-8",
        )
        dis = root / "dis.tflite"
        siglip = root / "siglip.tflite"
        yolo = root / "yolo.tflite"
        dis.write_bytes(b"dis")
        siglip.write_bytes(b"siglip")
        yolo.write_bytes(b"yolo")
        return catalog, dis, siglip, yolo


if __name__ == "__main__":
    unittest.main()
