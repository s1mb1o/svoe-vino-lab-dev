import argparse
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from tools import build_dual_pipeline_pack as tool


class DualPipelinePackTest(unittest.TestCase):
    def sources(self, root):
        custom = root / "custom"
        custom.mkdir()
        (custom / "manifest.json").write_text(json.dumps({"slugs": ["a", "b"]}))
        for name in tool.CUSTOM_HASHES:
            (custom / name).write_bytes(name.encode())
        vector = [1.0] + [0.0] * 767
        (custom / "base-p512-fractional-bg010.f32").write_bytes(struct.pack("<1536f", *(vector * 2)))
        payloads = {name: name.encode() for name in ["dis.tflite", "yolo26n-seg_w8a32.tflite",
            tool.standard.MODEL_FILE, tool.standard.MODEL_MANIFEST, tool.standard.POSITIONS_FILE,
            "vectors.f32", "candidates.jsonl", "codes.jsonl", "images.zip"]}
        payloads["wines.jsonl"] = b'{"wine_slug":"b"}\n{"wine_slug":"a"}\n'
        source = root / "standard.zip"
        manifest = {"format_version": 6, "pipeline": tool.standard.PIPELINE,
            "profile_sha256": tool.standard.PROFILE_SHA256, "wine_count": 2, "vector_count": 2,
            "files": {name: {"bytes": len(data), "sha256": tool.digest(data)} for name, data in payloads.items()}}
        with zipfile.ZipFile(source, "w") as archive:
            archive.writestr("manifest.json", json.dumps(manifest))
            for name, data in payloads.items():
                archive.writestr(name, data)
        hashes = {name: tool.standard.sha256_file(custom / name) for name in tool.CUSTOM_HASHES}
        args = argparse.Namespace(standard_pack=source, custom_dir=custom, out=root / "result.zip", version="fixture")
        return args, payloads, hashes

    def build_fixture(self, args, payloads, hashes):
        with patch.object(tool, "CUSTOM_HASHES", hashes), patch.object(tool, "SOURCE_MANIFEST_SHA256",
                tool.standard.sha256_file(args.custom_dir / "manifest.json")), patch.object(tool,
                "STANDARD_PACK_SHA256", tool.standard.sha256_file(args.standard_pack)), patch.multiple(tool.standard,
                MODEL_SHA256=tool.digest(payloads[tool.standard.MODEL_FILE]),
                MANIFEST_SHA256=tool.digest(payloads[tool.standard.MODEL_MANIFEST]),
                POSITIONS_SHA256=tool.digest(payloads[tool.standard.POSITIONS_FILE]),
                DIS_MODEL_SHA256=tool.digest(payloads["dis.tflite"])):
            return tool.build(args)

    def test_preserves_standard_payloads_omits_yolo_and_maps_custom_rows(self):
        with tempfile.TemporaryDirectory() as temporary:
            args, payloads, hashes = self.sources(Path(temporary))
            result = self.build_fixture(args, payloads, hashes)
            self.assertEqual(result["format_version"], 7)
            with zipfile.ZipFile(args.out) as archive:
                self.assertNotIn("yolo26n-seg_w8a32.tflite", archive.namelist())
                for name, data in payloads.items():
                    if name != "yolo26n-seg_w8a32.tflite":
                        self.assertEqual(archive.read(name), data)
                rows = [json.loads(line) for line in archive.read("custom_candidates.jsonl").splitlines()]
                self.assertEqual([row["wine_slug"] for row in rows], ["a", "b"])
                self.assertEqual(archive.read("custom_vectors.f32"),
                    (args.custom_dir / "base-p512-fractional-bg010.f32").read_bytes())

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            args, payloads, hashes = self.sources(Path(temporary))
            args.out.write_bytes(b"preserve")
            with self.assertRaisesRegex(ValueError, "already exists"):
                self.build_fixture(args, payloads, hashes)
            self.assertEqual(args.out.read_bytes(), b"preserve")

    def test_wrong_reference_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            args, payloads, hashes = self.sources(Path(temporary))
            (args.custom_dir / "base-p512-fractional-bg010.f32").write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                self.build_fixture(args, payloads, hashes)
            self.assertFalse(args.out.exists())

    def test_missing_catalogue_wine_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            args, payloads, hashes = self.sources(Path(temporary))
            (args.custom_dir / "manifest.json").write_text(json.dumps({"slugs": ["a", "different"]}))
            with self.assertRaisesRegex(ValueError, "same wines"):
                self.build_fixture(args, payloads, hashes)

    def test_nonfinite_or_nonunit_vectors_are_rejected(self):
        for vector in [[float("nan")] * 768, [0.0] * 768]:
            with self.assertRaisesRegex(ValueError, "finite and normalized"):
                tool.vectors_valid(struct.pack("<768f", *vector), 1)


if __name__ == "__main__":
    unittest.main()
