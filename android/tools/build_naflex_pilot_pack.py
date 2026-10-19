#!/usr/bin/env python3
"""Build a non-production Base NaFlex pilot pack with the fixed-224 catalogue payloads."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
import zipfile


MODEL_FILES = (
    "siglip2_naflex_backbone.tflite",
    "siglip2_naflex_pooling.tflite",
    "siglip2_naflex_position_embeddings.f32",
)
LEGACY_MODEL = "siglip2_base_224_fp16.tflite"


class PilotPackError(ValueError):
    """The source data cannot make a valid pilot pack."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build(args) -> dict:
    source_pack = Path(args.source_pack).resolve()
    model_root = Path(args.model_dir).resolve()
    output = Path(args.output).resolve()
    metadata = json.loads((model_root / "metadata.json").read_text(encoding="utf-8"))
    if (
        metadata.get("format") != "svoe-vino-siglip2-naflex-split"
        or metadata.get("model") != "google/siglip2-base-patch16-naflex"
        or metadata.get("vector_dim") != 768
        or metadata.get("max_num_patches") not in {256, 512}
        or metadata.get("pooling_mode") not in {
            "standard",
            "foreground-1.0-background-0.1",
        }
    ):
        raise PilotPackError("the split export is not a supported Base NaFlex pilot model")
    for name in MODEL_FILES:
        record = (metadata.get("files") or {}).get(name) or {}
        path = model_root / name
        if (
            not path.is_file()
            or record.get("bytes") != path.stat().st_size
            or record.get("sha256") != sha256_file(path)
        ):
            raise PilotPackError(f"the split export file is invalid: {name}")
    if output.exists() and not args.replace:
        raise PilotPackError(f"output exists; use --replace: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="svoe-vino-naflex-pilot-") as temporary:
        root = Path(temporary)
        with zipfile.ZipFile(source_pack) as archive:
            archive.extractall(root)
        manifest_path = root / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (
            manifest.get("format") != "svoe-vino-android-model-pack"
            or manifest.get("format_version") != 3
            or manifest.get("vector_dim") != 768
        ):
            raise PilotPackError("the source pack is not the fixed Base/224 control pack")
        (root / LEGACY_MODEL).unlink()
        for name in MODEL_FILES:
            shutil.copyfile(model_root / name, root / name)
        payloads = sorted(
            path.name for path in root.iterdir()
            if path.is_file() and path.name != "manifest.json"
        )
        files = {
            name: {
                "bytes": (root / name).stat().st_size,
                "sha256": sha256_file(root / name),
            }
            for name in payloads
        }
        manifest.update({
            "format_version": 5,
            "version": args.version,
            "created_at_epoch_ms": int(time.time() * 1000),
            "pipeline": "foreground-white-native-naflex-v1",
            "model": metadata["model"],
            "siglip2_runtime": "naflex-exact-split",
            "vector_dim": 768,
            "patch_size": metadata["patch_size"],
            "max_num_patches": metadata["max_num_patches"],
            "position_embedding_grid": metadata["position_embedding_grid"],
            "model_revision": metadata["revision"],
            "pooling_mode": metadata["pooling_mode"],
            "reference_aggregation": "max",
            "gpu_compatible": False,
            "pilot_only": True,
            "pilot_catalogue_vector_space": "fixed-base-224-control",
            "files": files,
        })
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary_output = output.with_name(f".{output.name}.{os.getpid()}.tmp")
        try:
            with zipfile.ZipFile(temporary_output, "w", compression=zipfile.ZIP_STORED) as archive:
                archive.write(manifest_path, "manifest.json")
                for name in payloads:
                    archive.write(root / name, name)
            os.replace(temporary_output, output)
        finally:
            temporary_output.unlink(missing_ok=True)
    return {
        "output": str(output),
        "bytes": output.stat().st_size,
        "sha256": sha256_file(output),
        "version": args.version,
        "max_num_patches": metadata["max_num_patches"],
        "pooling_mode": metadata["pooling_mode"],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-pack", required=True)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = build(args)
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
