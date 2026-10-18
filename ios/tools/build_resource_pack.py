#!/usr/bin/env python3
"""Build the generated iPhone resource directory from the Android catalogue pack."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ANDROID_PACK = ROOT.parent / "android/app/src/main/assets/default_model_pack.zip"
DEFAULT_OUTPUT = ROOT / "ChtoZaVino/Resources/BuiltinPack"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))


def read_vectors(path: Path, dimension: int) -> list[list[float]]:
    data = path.read_bytes()
    row_bytes = dimension * 4
    if len(data) % row_bytes:
        raise ValueError(f"{path} has an invalid vector byte length")
    return [list(struct.unpack(f"<{dimension}f", data[offset : offset + row_bytes])) for offset in range(0, len(data), row_bytes)]


def write_vectors(path: Path, rows: list[list[float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as stream:
        for row in rows:
            stream.write(struct.pack(f"<{len(row)}f", *row))


def fixture_vectors(count: int, dimension: int) -> list[list[float]]:
    rows: list[list[float]] = []
    for index in range(count):
        row = [0.0] * dimension
        row[index % dimension] = 1.0
        rows.append(row)
    return rows


def normal_vectors(path: Path, dimension: int, count: int) -> list[list[float]]:
    rows = read_vectors(path, dimension)
    if len(rows) != count:
        raise ValueError(f"{path} has {len(rows)} rows instead of {count}")
    for row in rows:
        norm = sum(value * value for value in row) ** 0.5
        if not 0.999 <= norm <= 1.001:
            raise ValueError(f"{path} has a non-normalized vector")
    return rows


def build(args: argparse.Namespace) -> None:
    output = args.output.resolve()
    temporary = Path(tempfile.mkdtemp(prefix="iphone-pack-", dir=output.parent if output.parent.exists() else None))
    try:
        source = temporary / "android"
        with zipfile.ZipFile(args.android_pack) as archive:
            allowed = {"manifest.json", "vectors.f32", "candidates.jsonl", "wines.jsonl", "codes.jsonl", "images.zip"}
            source.mkdir(parents=True, exist_ok=True)
            for name in allowed:
                target = source / name
                with archive.open(name) as reader, target.open("wb") as writer:
                    shutil.copyfileobj(reader, writer)

        android_manifest = json.loads((source / "manifest.json").read_text())
        wines = read_jsonl(source / "wines.jsonl")
        candidates = [row for row in read_jsonl(source / "candidates.jsonl") if row.get("view") == "full"]
        codes = read_jsonl(source / "codes.jsonl")
        siglip_vectors = read_vectors(source / "vectors.f32", 768)
        if len(siglip_vectors) != android_manifest["vector_count"]:
            raise ValueError("Android vector count does not match its manifest")

        selected_wines = wines[: args.limit] if args.limit else wines
        selected_slugs = {row["wine_slug"] for row in selected_wines}
        selected_candidates = [row for row in candidates if row["wine_slug"] in selected_slugs]
        if len(selected_candidates) != len(selected_wines):
            raise ValueError("Each selected wine must have one full candidate")
        selected_candidates.sort(key=lambda row: row["wine_slug"])
        selected_wines.sort(key=lambda row: row["wine_slug"])
        if [row["wine_slug"] for row in selected_candidates] != [row["wine_slug"] for row in selected_wines]:
            raise ValueError("Selected wine and candidate rows do not align")

        if args.fixture:
            selected_siglip = fixture_vectors(len(selected_wines), 768)
            selected_naflex = fixture_vectors(len(selected_wines), 768)
            selected_mobileclip = fixture_vectors(len(selected_wines), 512)
        else:
            selected_siglip = [siglip_vectors[row["vector_row"]] for row in selected_candidates]
            if not args.mobileclip_vectors:
                raise ValueError("--mobileclip-vectors is required outside fixture mode")
            selected_mobileclip = normal_vectors(args.mobileclip_vectors, 512, len(selected_wines))
            if not args.naflex_vectors:
                raise ValueError("--naflex-vectors is required outside fixture mode")
            selected_naflex = normal_vectors(args.naflex_vectors, 768, len(selected_wines))

        rewritten_candidates = [
            {"vector_row": index, "wine_slug": row["wine_slug"], "view": "full"}
            for index, row in enumerate(selected_candidates)
        ]
        pack = temporary / "pack"
        write_jsonl(pack / "wines.jsonl", selected_wines)
        write_jsonl(pack / "codes.jsonl", [row for row in codes if row["wine_slug"] in selected_slugs])
        write_jsonl(pack / "siglip2/candidates.jsonl", rewritten_candidates)
        write_jsonl(pack / "siglip2-base-naflex-p512/candidates.jsonl", rewritten_candidates)
        write_jsonl(pack / "mobileclip2-s2/candidates.jsonl", rewritten_candidates)
        write_vectors(pack / "siglip2/vectors.f32", selected_siglip)
        write_vectors(pack / "siglip2-base-naflex-p512/vectors.f32", selected_naflex)
        write_vectors(pack / "mobileclip2-s2/vectors.f32", selected_mobileclip)

        with zipfile.ZipFile(source / "images.zip") as images:
            for wine in selected_wines:
                image_path = wine["image_path"]
                if image_path.startswith("/") or ".." in Path(image_path).parts:
                    raise ValueError(f"unsafe image path: {image_path}")
                target = pack / image_path
                target.parent.mkdir(parents=True, exist_ok=True)
                with images.open(image_path) as reader, target.open("wb") as writer:
                    shutil.copyfileobj(reader, writer)
                if sha256(target) != wine["image_sha256"]:
                    raise ValueError(f"image hash mismatch: {image_path}")

        file_paths = [
            "wines.jsonl",
            "codes.jsonl",
            "siglip2/candidates.jsonl",
            "siglip2/vectors.f32",
            "siglip2-base-naflex-p512/candidates.jsonl",
            "siglip2-base-naflex-p512/vectors.f32",
            "mobileclip2-s2/candidates.jsonl",
            "mobileclip2-s2/vectors.f32",
        ]
        files = {
            name: {"bytes": (pack / name).stat().st_size, "sha256": sha256(pack / name)}
            for name in file_paths
        }
        manifest = {
            "format": "svoe-vino-ios-resource-pack",
            "format_version": 1,
            "version": args.version,
            "wine_count": len(selected_wines),
            "image_count": len(selected_wines),
            "files": files,
            "encoder_indexes": {
                "siglip2-base-naflex-p512": {
                    "model": "google/siglip2-base-patch16-naflex",
                    "pipeline": "dis-white-square-siglip2-base-naflex-p512-v1",
                    "vector_dimension": 768,
                    "vector_count": len(selected_wines),
                    "vectors_path": "siglip2-base-naflex-p512/vectors.f32",
                    "candidates_path": "siglip2-base-naflex-p512/candidates.jsonl",
                },
                "siglip2": {
                    "model": "vit_base_patch16_siglip_224.v2_webli",
                    "pipeline": "dis-white-square-timm-crop090-v2",
                    "vector_dimension": 768,
                    "vector_count": len(selected_wines),
                    "vectors_path": "siglip2/vectors.f32",
                    "candidates_path": "siglip2/candidates.jsonl",
                },
                "mobileclip2-s2": {
                    "model": "apple/MobileCLIP2-S2",
                    "pipeline": "dis-white-square-mobileclip2-s2-v1",
                    "vector_dimension": 512,
                    "vector_count": len(selected_wines),
                    "vectors_path": "mobileclip2-s2/vectors.f32",
                    "candidates_path": "mobileclip2-s2/candidates.jsonl",
                },
            },
        }
        (pack / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        if output.exists():
            shutil.rmtree(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(pack, output)
        print(json.dumps({"output": str(output), "wines": len(selected_wines), "fixture": args.fixture}))
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--android-pack", type=Path, default=DEFAULT_ANDROID_PACK)
    parser.add_argument("--mobileclip-vectors", type=Path)
    parser.add_argument("--naflex-vectors", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--version", default="20261006-ios-naflex-production")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--fixture", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    build(parse_args())
