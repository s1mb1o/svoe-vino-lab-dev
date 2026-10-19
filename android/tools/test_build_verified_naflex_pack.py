import argparse
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import numpy as np

from tools import build_verified_naflex_pack as tool


class VerifiedNaFlexPackTest(unittest.TestCase):
    def sources(self, root):
        model = root / "model"
        model.mkdir()
        (model / tool.MODEL_FILE).write_bytes(b"verified model fixture")
        (model / tool.POSITIONS_FILE).write_bytes(bytes(786432))
        model_hash = tool.sha256_file(model / tool.MODEL_FILE)
        metadata = {
            "model_file": tool.MODEL_FILE, "model_sha256": model_hash,
            "profile_sha256": tool.PROFILE_SHA256,
            "profile": {"model_revision": tool.REVISION},
            "position_table": {"file": tool.POSITIONS_FILE},
        }
        (model / tool.MODEL_MANIFEST).write_text(json.dumps(metadata))
        catalogue = root / "catalogue.zip"
        payloads = {name: b"fixture" for name in tool.RETAINED_FILES}
        # Use reverse catalogue order to test the slug-to-vector mapping.
        payloads["wines.jsonl"] = b'{"wine_slug":"b"}\n{"wine_slug":"a"}\n'
        manifest = {
            "format": "svoe-vino-android-model-pack", "wine_count": 2, "image_count": 2,
            "files": {name: {"bytes": len(data),
                              "sha256": tool.hashlib.sha256(data).hexdigest()}
                      for name, data in payloads.items()},
        }
        with zipfile.ZipFile(catalogue, "w") as archive:
            archive.writestr("manifest.json", json.dumps(manifest))
            for name, data in payloads.items():
                archive.writestr(name, data)
        index = root / "index"
        index.mkdir()
        vectors = np.zeros((3, 768), dtype="<f4")
        for row in range(3):
            vectors[row, row] = 1
        vector_file = index / "catalogue_embeddings.bin"
        vectors.tofile(vector_file)
        index_json = {
            "schema_version": 1, "dimension": 768, "wines": ["a", "b", "unused"],
            "model_sha256": model_hash, "profile_sha256": tool.PROFILE_SHA256,
            "dataset_sha256": "fixture",
            "embeddings": {"file": vector_file.name, "byte_count": vector_file.stat().st_size,
                           "dtype": "float32", "byte_order": "little", "shape": [3, 768],
                           "sha256": tool.sha256_file(vector_file)},
        }
        (index / "index.json").write_text(json.dumps(index_json))
        args = argparse.Namespace(catalogue_pack=str(catalogue), model_dir=str(model),
                                  index_dir=str(index), out=str(root / "result.zip"),
                                  replace=False, version="test")
        hashes = {
            "MODEL_SHA256": model_hash,
            "POSITIONS_SHA256": tool.sha256_file(model / tool.POSITIONS_FILE),
            "MANIFEST_SHA256": tool.sha256_file(model / tool.MODEL_MANIFEST),
            "DIS_MODEL_SHA256": tool.hashlib.sha256(b"fixture").hexdigest(),
            "YOLO_MODEL_SHA256": tool.hashlib.sha256(b"fixture").hexdigest(),
        }
        return args, hashes

    def test_reuses_only_catalogue_metadata_and_selects_exact_vectors_by_slug(self):
        with tempfile.TemporaryDirectory() as temporary:
            args, hashes = self.sources(Path(temporary))
            with patch.multiple(tool, **hashes):
                result = tool.build(args)
            self.assertEqual(result["wines"], 2)
            with zipfile.ZipFile(args.out) as archive:
                manifest = json.loads(archive.read("manifest.json"))
                self.assertEqual(manifest["format_version"], 6)
                self.assertEqual(manifest["reference_frames_per_image"], 1)
                self.assertEqual(manifest["pipeline"], tool.PIPELINE)
                self.assertNotIn("siglip2_base_224_fp16.tflite", archive.namelist())
                vectors = np.frombuffer(archive.read("vectors.f32"), dtype="<f4").reshape(-1, 768)
                self.assertEqual(np.argmax(vectors, axis=1).tolist(), [1, 0])
                self.assertEqual(archive.read("codes.jsonl"), b"fixture")
                self.assertEqual(archive.read("images.zip"), b"fixture")

    def test_rejects_an_index_from_another_model(self):
        with tempfile.TemporaryDirectory() as temporary:
            args, hashes = self.sources(Path(temporary))
            path = Path(args.index_dir) / "index.json"
            index = json.loads(path.read_text())
            index["model_sha256"] = "other"
            path.write_text(json.dumps(index))
            with patch.multiple(tool, **hashes), self.assertRaisesRegex(tool.PackError, "does not match"):
                tool.build(args)
            self.assertFalse(Path(args.out).exists())

    def test_rejects_corrupt_vectors_and_keeps_existing_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            args, hashes = self.sources(Path(temporary))
            (Path(args.index_dir) / "catalogue_embeddings.bin").write_bytes(b"corrupt")
            Path(args.out).write_bytes(b"previous pack")
            args.replace = True
            with patch.multiple(tool, **hashes), self.assertRaisesRegex(tool.PackError, "hash or length"):
                tool.build(args)
            self.assertEqual(Path(args.out).read_bytes(), b"previous pack")

    def test_rejects_missing_wine_without_silent_catalogue_loss(self):
        with tempfile.TemporaryDirectory() as temporary:
            args, hashes = self.sources(Path(temporary))
            path = Path(args.index_dir) / "index.json"
            index = json.loads(path.read_text())
            index["wines"][0] = "not-a"
            path.write_text(json.dumps(index))
            with patch.multiple(tool, **hashes), self.assertRaisesRegex(tool.PackError, "misses 1"):
                tool.build(args)

    def test_rejects_changed_model_and_does_not_replace_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            args, hashes = self.sources(Path(temporary))
            (Path(args.model_dir) / tool.MODEL_FILE).write_bytes(b"different model")
            with patch.multiple(tool, **hashes), self.assertRaisesRegex(tool.PackError, "verified release"):
                tool.build(args)
            args.out = args.catalogue_pack
            args.replace = True
            with self.assertRaisesRegex(tool.PackError, "must not replace the source"):
                tool.build(args)


if __name__ == "__main__":
    unittest.main()
