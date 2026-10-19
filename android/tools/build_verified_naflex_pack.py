#!/usr/bin/env python3
"""Build format 6 from the verified complete Base p512 model and its index.

Reuse only metadata, display images, codes, DIS, and YOLO from the catalogue pack.
Never reuse its encoder or reference vectors.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
import zipfile

import numpy as np

try:
    from tools.build_model_pack import (
        BASE_NAFLEX_MODEL, DIS_MODEL_SHA256, PackError, YOLO_MODEL_SHA256, sha256_file,
    )
except ModuleNotFoundError:
    from build_model_pack import (
        BASE_NAFLEX_MODEL, DIS_MODEL_SHA256, PackError, YOLO_MODEL_SHA256, sha256_file,
    )

MODEL_FILE = "base-p512-gpu-fp16.tflite"
MODEL_MANIFEST = "base-p512-gpu-fp16.manifest.json"
POSITIONS_FILE = "position_table.bin"
MODEL_SHA256 = "9cd7a00df9818bebe9e505e7a84647334587f88101300dd14b4bce1e39165005"
PROFILE_SHA256 = "1ac1a7a3a88074c04fc1559c9d0ae350820a8f681bc84f6176ef2aaed786683c"
POSITIONS_SHA256 = "3ba1ba032ad8d97e0a1afebf4513615fbfedb56f646c14dcdb83d3c228c12860"
MANIFEST_SHA256 = "8a45409f227794572e8fea98bbfc39266d558f0d759ba1e5774219340d4c36ec"
REVISION = "b53b807d3a2d5e2b3911292f2d69e5341cdc064c"
PIPELINE = "raw-native-naflex-base-p512-v1"
RETAINED_FILES = (
    "dis.tflite", "yolo26n-seg_w8a32.tflite", "images.zip", "wines.jsonl", "codes.jsonl",
)


def read_verified_index(directory):
    index = json.loads((directory / "index.json").read_text())
    if (index.get("schema_version") != 1 or index.get("dimension") != 768
            or index.get("model_sha256") != MODEL_SHA256
            or index.get("profile_sha256") != PROFILE_SHA256):
        raise PackError("the index does not match the verified complete Base p512 graph")
    record = index["embeddings"]
    if (record.get("file") != "catalogue_embeddings.bin"
            or record.get("dtype") != "float32" or record.get("byte_order") != "little"
            or record.get("shape") != [len(index["wines"]), 768]):
        raise PackError("the index has an invalid embedding contract")
    source = directory / record["file"]
    if source.stat().st_size != record["byte_count"] or sha256_file(source) != record["sha256"]:
        raise PackError("the index vector hash or length does not match")
    vectors = np.fromfile(source, dtype="<f4")
    if vectors.size != len(index["wines"]) * 768:
        raise PackError("the index vector shape does not match")
    vectors = vectors.reshape(-1, 768)
    if not np.isfinite(vectors).all() or not np.allclose(
            np.linalg.norm(vectors, axis=1), 1.0, atol=1e-5, rtol=1e-5):
        raise PackError("the index vectors must be finite and normalized")
    # This frozen index has exactly one reference per wine. Do not invent angles.
    if not all(isinstance(slug, str) and slug for slug in index["wines"]) or len(
            set(index["wines"])) != len(index["wines"]):
        raise PackError("the frozen index must contain one unique reference per wine")
    return index, vectors


def copy_verified_models(directory, target):
    expected = {MODEL_FILE: MODEL_SHA256, POSITIONS_FILE: POSITIONS_SHA256,
                MODEL_MANIFEST: MANIFEST_SHA256}
    for name, digest in expected.items():
        if sha256_file(directory / name) != digest:
            raise PackError(f"{name} does not match the verified release")
        shutil.copyfile(directory / name, target / name)
    metadata = json.loads((directory / MODEL_MANIFEST).read_text())
    if (metadata.get("model_file") != MODEL_FILE or metadata.get("model_sha256") != MODEL_SHA256
            or metadata.get("profile_sha256") != PROFILE_SHA256
            or metadata.get("profile", {}).get("model_revision") != REVISION
            or metadata.get("position_table", {}).get("file") != POSITIONS_FILE):
        raise PackError("the model manifest does not match the verified release")
    if (target / POSITIONS_FILE).stat().st_size != 786432:
        raise PackError("the position table size does not match")


def copy_catalogue(source, target):
    with zipfile.ZipFile(source) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or any("/" in name or "\\" in name for name in names):
            raise PackError("the source pack has duplicate or unsafe root paths")
        manifest = json.loads(archive.read("manifest.json"))
        if manifest.get("format") != "svoe-vino-android-model-pack":
            raise PackError("the source is not an Android catalogue pack")
        for name in RETAINED_FILES:
            record = manifest["files"][name]
            with archive.open(name) as input_file, (target / name).open("wb") as output:
                shutil.copyfileobj(input_file, output)
            if ((target / name).stat().st_size != record["bytes"]
                    or sha256_file(target / name) != record["sha256"]):
                raise PackError(f"source catalogue payload {name} failed verification")
        for name, expected in (("dis.tflite", DIS_MODEL_SHA256),
                               ("yolo26n-seg_w8a32.tflite", YOLO_MODEL_SHA256)):
            if sha256_file(target / name) != expected:
                raise PackError(f"source catalogue uses a different {name}")
    return manifest


def validate_output(path):
    with zipfile.ZipFile(path) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        if set(archive.namelist()) != {*manifest["files"], "manifest.json"}:
            raise PackError("output payloads do not match the manifest")
        for name, record in manifest["files"].items():
            digest = hashlib.sha256()
            size = 0
            with archive.open(name) as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
                    size += len(block)
            if size != record["bytes"] or digest.hexdigest() != record["sha256"]:
                raise PackError(f"output payload {name} failed verification")
        vectors = np.frombuffer(archive.read("vectors.f32"), dtype="<f4")
        if vectors.size != manifest["vector_count"] * 768 or not np.isfinite(vectors).all():
            raise PackError("output vectors failed verification")
    return manifest


def build(args):
    output = Path(args.out).resolve()
    if output.exists() and not args.replace:
        raise PackError("the output exists; use --replace to replace this exact file")
    project = Path(__file__).resolve().parents[1]
    if project == output or project in output.parents:
        raise PackError("write generated packs outside the Android source directory")
    if output == Path(args.catalogue_pack).resolve():
        raise PackError("the output must not replace the source catalogue pack")
    index_dir = Path(args.index_dir).resolve()
    index, vectors = read_verified_index(index_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="base-p512-pack-", dir=output.parent) as temporary:
        root = Path(temporary)
        old_manifest = copy_catalogue(Path(args.catalogue_pack), root)
        copy_verified_models(Path(args.model_dir), root)
        wines = [json.loads(line) for line in (root / "wines.jsonl").read_text().splitlines()]
        slugs = [wine["wine_slug"] for wine in wines]
        if len(set(slugs)) != len(slugs) or len(slugs) != old_manifest["wine_count"]:
            raise PackError("the catalogue wine count does not match")
        lookup = {slug: row for row, slug in enumerate(index["wines"])}
        missing = set(slugs) - lookup.keys()
        if missing:
            raise PackError(f"the verified index misses {len(missing)} catalogue wines")
        selected = vectors[[lookup[slug] for slug in slugs]]
        selected.astype("<f4", copy=False).tofile(root / "vectors.f32")
        with (root / "candidates.jsonl").open("w", encoding="utf-8") as target:
            for row, slug in enumerate(slugs):
                target.write(json.dumps({"vector_row": row, "wine_slug": slug,
                                         "view": "full", "angle": 0}) + "\n")
        files = {path.name: {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
                 for path in root.iterdir() if path.is_file()}
        manifest = {
            "format": "svoe-vino-android-model-pack", "format_version": 6,
            "version": args.version, "created_at_epoch_ms": int(time.time() * 1000),
            "pipeline": PIPELINE, "model": BASE_NAFLEX_MODEL, "model_revision": REVISION,
            "profile_sha256": PROFILE_SHA256, "siglip2_runtime": "naflex-complete",
            "vector_dim": 768, "patch_size": 16, "max_num_patches": 512,
            "position_embedding_grid": 16, "pooling_mode": "standard",
            "reference_aggregation": "max", "gpu_compatible": True,
            "reference_rotation_step_degrees": 360, "reference_frames_per_image": 1,
            "vector_count": len(slugs), "wine_count": len(slugs),
            "image_count": old_manifest["image_count"],
            "image_selection": "package_cut_transparent_webp", "files": files,
            "source": {"catalogue_pack_sha256": sha256_file(Path(args.catalogue_pack)),
                       "index_sha256": sha256_file(index_dir / "index.json"),
                       "index_vectors_sha256": index["embeddings"]["sha256"],
                       "dataset_sha256": index["dataset_sha256"],
                       "reference_input": "frozen package cuts; one unrotated reference"},
        }
        (root / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        pending = root / "pack.zip"
        with zipfile.ZipFile(pending, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for name in ["manifest.json", *sorted(files)]:
                archive.write(root / name, name)
        validate_output(pending)
        os.replace(pending, output)
    return {"out": str(output), "bytes": output.stat().st_size, "sha256": sha256_file(output),
            "wines": len(slugs), "vectors": len(slugs), "format_version": 6}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalogue-pack", required=True)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--index-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--version", default="20261019-base-naflex-p512-complete")
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(build(args), indent=2))
    except (PackError, OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        parser.exit(1, f"error: {error}\n")


if __name__ == "__main__":
    # Allow direct execution from the Android directory and module execution in tests.
    main()
