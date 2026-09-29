import argparse
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest import mock
import zipfile

import numpy as np

from tools import build_model_pack


class BuildModelPackTest(unittest.TestCase):
    def test_builds_verified_pack(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle, database, dis, siglip = self.make_sources(root, 768)
            output = root / "out" / "pack.zip"

            result = self.build_with_test_models(
                argparse.Namespace(
                    bundle=str(bundle),
                    catalog_db=str(database),
                    dis_model=str(dis),
                    siglip_model=str(siglip),
                    confirm_pipeline="dis-white-square-timm-crop090-v2",
                    out=str(output),
                    version="test",
                ),
                dis,
                siglip,
            )

            self.assertEqual(result["vectors"], 2)
            self.assertEqual(result["wines"], 1)
            self.assertEqual(result["codes"], 1)
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(
                    set(archive.namelist()),
                    {"manifest.json", *build_model_pack.PAYLOADS},
                )
                manifest = json.loads(archive.read("manifest.json"))
                self.assertEqual(manifest["vector_dim"], 768)
                self.assertEqual(
                    manifest["pipeline"],
                    "dis-white-square-timm-crop090-v2",
                )

    def test_rejects_gx10_vector_dimension(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle, database, dis, siglip = self.make_sources(root, 1152)
            with self.assertRaisesRegex(build_model_pack.PackError, r"\[N,768\]"):
                self.build_with_test_models(
                    argparse.Namespace(
                        bundle=str(bundle),
                        catalog_db=str(database),
                        dis_model=str(dis),
                        siglip_model=str(siglip),
                        confirm_pipeline="dis-white-square-timm-crop090-v2",
                        out=str(root / "pack.zip"),
                        version="test",
                    ),
                    dis,
                    siglip,
                )

    def test_rejects_a_different_siglip_model(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle, database, dis, siglip = self.make_sources(root, 768)
            with mock.patch.object(
                build_model_pack,
                "DIS_MODEL_SHA256",
                build_model_pack.sha256_file(dis),
            ):
                with self.assertRaisesRegex(
                    build_model_pack.PackError,
                    "does not match the verified Android model",
                ):
                    build_model_pack.build(
                        argparse.Namespace(
                            bundle=str(bundle),
                            catalog_db=str(database),
                            dis_model=str(dis),
                            siglip_model=str(siglip),
                            confirm_pipeline="dis-white-square-timm-crop090-v2",
                            out=str(root / "pack.zip"),
                            version="test",
                        )
                    )

    def build_with_test_models(self, args, dis, siglip):
        with mock.patch.multiple(
            build_model_pack,
            DIS_MODEL_SHA256=build_model_pack.sha256_file(dis),
            SIGLIP_MODEL_SHA256=build_model_pack.sha256_file(siglip),
        ):
            return build_model_pack.build(args)

    def make_sources(self, root, dimension):
        bundle = root / "bundle"
        bundle.mkdir()
        (bundle / "manifest.json").write_text(
            json.dumps(
                {
                    "format": "svoe-vino-matcher-bundle",
                    "format_version": 2,
                    "embedding": {"model": "vit_base_patch16_siglip_224.v2_webli"},
                }
            ),
            encoding="utf-8",
        )
        vectors = np.zeros((2, dimension), dtype=np.float32)
        vectors[0, 0] = 1
        vectors[1, 1] = 1
        np.save(bundle / "vectors.npy", vectors, allow_pickle=False)
        (bundle / "candidates.jsonl").write_text(
            '{"vector_row":0,"wine_slug":"wine","view":"full"}\n'
            '{"vector_row":1,"wine_slug":"wine","view":"full"}\n',
            encoding="utf-8",
        )
        (bundle / "wines.jsonl").write_text(
            '{"wine_slug":"wine","name":"Вино","page_url":'
            '"https://vino-svoe.ru/wines/wine"}\n',
            encoding="utf-8",
        )
        database = root / "catalog.sqlite3"
        connection = sqlite3.connect(database)
        connection.execute("CREATE TABLE wine_code (wine_slug, kind, value)")
        connection.execute(
            "INSERT INTO wine_code VALUES (?, ?, ?)",
            ("wine", "gtin", "04631168664979"),
        )
        connection.commit()
        connection.close()
        dis = root / "dis.tflite"
        siglip = root / "siglip.tflite"
        dis.write_bytes(b"dis")
        siglip.write_bytes(b"siglip")
        return bundle, database, dis, siglip


if __name__ == "__main__":
    unittest.main()
