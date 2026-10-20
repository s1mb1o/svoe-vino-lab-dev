"""Build the two measured complete Base p512 pipelines without changing source packs."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import tempfile
import time
import zipfile

from tools import build_verified_naflex_pack as standard

CUSTOM_HASHES = {
    "base-p512-weighted.tflite": "6d626149ec6460ef3c57efd671d75691a7f98628f0d1eddefc8c203f818d5ab7",
    "base-p512-weighted.manifest.json": "a74907ca301be4a8f8dd8a89673b631efc02e8d69e0b7bfaede3d50cba234a51",
    "dis.tflite": "b8ede77d06da09f9220d40d8c0735eebbd474d443915d48e2c5f44855b596c94",
    "base-p512-fractional-bg010.f32": "684be34d3d200b6b130bb8192060799036d57ced096e25f2a955be1cf384286b",
}
SOURCE_MANIFEST_SHA256 = "ae6205fb4579530470d5213113d1e9b2b5d1d2234a4d3a28d53731dfe0f07338"
STANDARD_PACK_SHA256 = "4307a92be20fc53bec18f922ae80b60d92fc219c2a8e22f981f8c8778117a128"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def vectors_valid(data, count):
    if len(data) != count * 768 * 4:
        raise ValueError("Wrong custom vector count")
    for row in struct.iter_unpack("<768f", data):
        if not all(math.isfinite(value) for value in row) or abs(sum(v * v for v in row) - 1) > .002:
            raise ValueError("Custom vectors must be finite and normalized")


def build(args):
    source = Path(args.standard_pack).resolve()
    custom = Path(args.custom_dir).resolve()
    target = Path(args.out).resolve()
    if target == source or target.is_relative_to(custom):
        raise ValueError("Output must not replace a source")
    if target.exists():
        raise ValueError("Output already exists; choose a new versioned path")
    if standard.sha256_file(source) != STANDARD_PACK_SHA256:
        raise ValueError("Standard source is not the measured production pack")
    if standard.sha256_file(custom / "manifest.json") != SOURCE_MANIFEST_SHA256:
        raise ValueError("Custom source manifest is not the audited DIS-768 pack")
    source_manifest = json.loads((custom / "manifest.json").read_text())
    slugs = source_manifest["slugs"]
    if len(slugs) != len(set(slugs)):
        raise ValueError("Duplicate custom wine slug")
    additions = {}
    for name, expected in CUSTOM_HASHES.items():
        data = (custom / name).read_bytes()
        if digest(data) != expected:
            raise ValueError(f"Custom source hash mismatch: {name}")
        output_name = {"dis.tflite": "dis768.tflite",
                       "base-p512-fractional-bg010.f32": "custom_vectors.f32"}.get(name, name)
        additions[output_name] = data
    vectors_valid(additions["custom_vectors.f32"], len(slugs))
    additions["custom_candidates.jsonl"] = ("".join(json.dumps({
        "vector_row": row, "wine_slug": slug, "view": "full", "angle": 0,
    }, ensure_ascii=False) + "\n" for row, slug in enumerate(slugs))).encode()
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source) as old:
        names = old.namelist()
        if len(names) != len(set(names)) or any("/" in name or "\\" in name for name in names):
            raise ValueError("Unsafe standard pack entries")
        manifest = json.loads(old.read("manifest.json"))
        if (manifest["format_version"] != 6 or manifest["pipeline"] != standard.PIPELINE
                or manifest["profile_sha256"] != standard.PROFILE_SHA256):
            raise ValueError("Standard source is not the verified format 6 pack")
        wines = [json.loads(line)["wine_slug"] for line in old.read("wines.jsonl").splitlines() if line]
        if set(wines) != set(slugs) or len(wines) != len(slugs) or manifest["vector_count"] != len(slugs):
            raise ValueError("The two pipelines must cover exactly the same wines")
        expected = manifest["files"]
        if set(names) != set(expected) | {"manifest.json"}:
            raise ValueError("Standard file list mismatch")
        # Verify and preserve every standard payload, including its existing row order.
        for name, record in expected.items():
            with old.open(name) as handle:
                sha = hashlib.sha256(); size = 0
                while block := handle.read(1024 * 1024):
                    sha.update(block); size += len(block)
            if sha.hexdigest() != record["sha256"] or size != record["bytes"]:
                raise ValueError(f"Standard source hash mismatch: {name}")
        for name, sha in {standard.MODEL_FILE: standard.MODEL_SHA256,
                          standard.MODEL_MANIFEST: standard.MANIFEST_SHA256,
                          standard.POSITIONS_FILE: standard.POSITIONS_SHA256,
                          "dis.tflite": standard.DIS_MODEL_SHA256}.items():
            if expected[name]["sha256"] != sha:
                raise ValueError(f"Unverified standard model: {name}")
        manifest.update(format_version=7, version=args.version,
                        default_pipeline="DIS768_CUSTOM", created_at_epoch_ms=int(time.time() * 1000))
        manifest["files"] = {name: record for name, record in expected.items()
                             if name != "yolo26n-seg_w8a32.tflite"}
        manifest["yolo_available"] = False
        for name, data in additions.items():
            manifest["files"][name] = {"bytes": len(data), "sha256": digest(data)}
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".dual-pack-", suffix=".zip", delete=False) as handle:
            temporary = Path(handle.name)
        try:
            with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as out:
                for name in names:
                    if name in {"manifest.json", "yolo26n-seg_w8a32.tflite"}:
                        continue
                    with old.open(name) as input_file, out.open(name, "w", force_zip64=True) as output_file:
                        while block := input_file.read(1024 * 1024):
                            output_file.write(block)
                for name, data in additions.items():
                    out.writestr(name, data)
                out.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            with zipfile.ZipFile(temporary) as check:
                for name, record in manifest["files"].items():
                    with check.open(name) as handle:
                        sha = hashlib.sha256(); size = 0
                        while block := handle.read(1024 * 1024):
                            sha.update(block); size += len(block)
                    if sha.hexdigest() != record["sha256"] or size != record["bytes"]:
                        raise ValueError(f"Output verification failed: {name}")
            temporary.rename(target)
        finally:
            temporary.unlink(missing_ok=True)
    return {"path": str(target), "sha256": standard.sha256_file(target),
            "bytes": target.stat().st_size, "wines_per_pipeline": len(slugs),
            "default_pipeline": "DIS768_CUSTOM", "format_version": 7}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--standard-pack", required=True)
    parser.add_argument("--custom-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--version", default="20261020-dis768-custom-and-standard-v1")
    print(json.dumps(build(parser.parse_args()), indent=2))


if __name__ == "__main__":
    main()
