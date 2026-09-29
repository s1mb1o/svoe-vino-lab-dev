#!/usr/bin/env python3
"""Build one verified Android model pack from a compatible matcher bundle."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import time
import zipfile

import numpy as np


PACK_FORMAT = "svoe-vino-android-model-pack"
PACK_VERSION = 1
PIPELINE = "dis-white-square-timm-crop090-v2"
MODEL = "vit_base_patch16_siglip_224.v2_webli"
DIMENSION = 768
DIS_MODEL_SHA256 = "0c3c93b6a2a65e7c69137ec82596944e6bfb97d982c75bab03acb0738dbaa087"
SIGLIP_MODEL_SHA256 = "a30ebb7b3ee15eaa68a18f9ab6a2ed740c15c343d25d898dc482317473320854"
PAYLOADS = (
    "dis.tflite",
    "siglip2_base_224_fp16.tflite",
    "vectors.f32",
    "candidates.jsonl",
    "wines.jsonl",
    "codes.jsonl",
)


class PackError(ValueError):
    """The source data does not satisfy the Android model-pack contract."""


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as source:
        for number, line in enumerate(source, 1):
            if not line.strip():
                raise PackError(f"{path.name} line {number} is empty")
            try:
                row = json.loads(line)
            except ValueError as error:
                raise PackError(f"{path.name} line {number} is invalid JSON: {error}") from error
            if not isinstance(row, dict):
                raise PackError(f"{path.name} line {number} is not an object")
            rows.append(row)
    return rows


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8", newline="\n") as target:
        for row in rows:
            target.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def validate_source_bundle(bundle):
    manifest_path = bundle / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise PackError(f"cannot read {manifest_path}: {error}") from error
    if manifest.get("format") != "svoe-vino-matcher-bundle":
        raise PackError("the source is not a matcher bundle")
    if manifest.get("format_version") != 2:
        raise PackError("the source matcher bundle must use format version 2")
    embedding = manifest.get("embedding") or {}
    if embedding.get("model") != MODEL:
        raise PackError(
            f"the bundle model must be {MODEL}; found {embedding.get('model')!r}"
        )
    for name in ("vectors.npy", "candidates.jsonl", "wines.jsonl"):
        if not (bundle / name).is_file():
            raise PackError(f"the source bundle has no {name}")
    return manifest


def load_vectors(path):
    vectors = np.load(path, allow_pickle=False)
    if vectors.dtype != np.float32 or vectors.ndim != 2 or vectors.shape[1] != DIMENSION:
        raise PackError(
            f"vectors.npy must be float32 [N,{DIMENSION}]; found {vectors.dtype} {vectors.shape}"
        )
    if len(vectors) == 0 or not np.isfinite(vectors).all():
        raise PackError("vectors.npy must contain finite vectors")
    norms = np.linalg.norm(vectors, axis=1)
    if not np.allclose(norms, 1.0, rtol=1e-5, atol=1e-6):
        raise PackError("each source vector must be L2-normalized")
    return np.ascontiguousarray(vectors)


def validate_catalogue(bundle, vector_count):
    candidates = read_jsonl(bundle / "candidates.jsonl")
    wines = read_jsonl(bundle / "wines.jsonl")
    slugs = set()
    for number, wine in enumerate(wines, 1):
        slug = wine.get("wine_slug")
        name = wine.get("name")
        page_url = wine.get("page_url")
        if not all(isinstance(value, str) and value for value in (slug, name, page_url)):
            raise PackError(f"wines.jsonl line {number} has invalid required fields")
        if not page_url.startswith("https://vino-svoe.ru/wines/"):
            raise PackError(f"wines.jsonl line {number} has an unsupported page_url")
        if slug in slugs:
            raise PackError(f"wines.jsonl repeats {slug}")
        slugs.add(slug)
    full_count = 0
    for number, candidate in enumerate(candidates, 1):
        row = candidate.get("vector_row")
        slug = candidate.get("wine_slug")
        view = candidate.get("view")
        if isinstance(row, bool) or not isinstance(row, int) or not 0 <= row < vector_count:
            raise PackError(f"candidates.jsonl line {number} has an invalid vector_row")
        if slug not in slugs or not isinstance(view, str):
            raise PackError(f"candidates.jsonl line {number} has an invalid wine or view")
        if view == "full":
            full_count += 1
    if full_count == 0:
        raise PackError("candidates.jsonl has no full view")
    return candidates, wines, slugs


def read_codes(database, slugs):
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            "SELECT wine_slug, kind, value FROM wine_code ORDER BY wine_slug, kind, value"
        ).fetchall()
    finally:
        connection.close()
    return [
        {"wine_slug": slug, "kind": kind, "value": value}
        for slug, kind, value in rows
        if slug in slugs
    ]


def build(args):
    bundle = Path(args.bundle).resolve()
    database = Path(args.catalog_db).resolve()
    dis_model = Path(args.dis_model).resolve()
    siglip_model = Path(args.siglip_model).resolve()
    output = Path(args.out).resolve()
    project = Path(__file__).resolve().parents[1]
    if output == project or project in output.parents:
        raise PackError("write the generated model pack outside the repository")
    if args.confirm_pipeline != PIPELINE:
        raise PackError(f"--confirm-pipeline must be {PIPELINE}")
    for path in (database, dis_model, siglip_model):
        if not path.is_file():
            raise PackError(f"file does not exist: {path}")
    if sha256_file(dis_model) != DIS_MODEL_SHA256:
        raise PackError("dis.tflite does not match the verified Android model")
    if sha256_file(siglip_model) != SIGLIP_MODEL_SHA256:
        raise PackError("siglip2_base_224_fp16.tflite does not match the verified Android model")

    validate_source_bundle(bundle)
    vectors = load_vectors(bundle / "vectors.npy")
    candidates, wines, slugs = validate_catalogue(bundle, len(vectors))
    codes = read_codes(database, slugs)

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="svoe-vino-android-pack-") as temporary:
        root = Path(temporary)
        shutil.copyfile(dis_model, root / "dis.tflite")
        shutil.copyfile(siglip_model, root / "siglip2_base_224_fp16.tflite")
        with open(root / "vectors.f32", "wb") as target:
            target.write(vectors.astype("<f4", copy=False).tobytes(order="C"))
        write_jsonl(root / "candidates.jsonl", candidates)
        write_jsonl(root / "wines.jsonl", wines)
        write_jsonl(root / "codes.jsonl", codes)

        files = {
            name: {"bytes": (root / name).stat().st_size, "sha256": sha256_file(root / name)}
            for name in PAYLOADS
        }
        manifest = {
            "format": PACK_FORMAT,
            "format_version": PACK_VERSION,
            "version": args.version,
            "created_at_epoch_ms": int(time.time() * 1000),
            "pipeline": PIPELINE,
            "model": MODEL,
            "vector_dim": DIMENSION,
            "vector_count": len(vectors),
            "wine_count": len(wines),
            "files": files,
        }
        (root / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
            archive.write(root / "manifest.json", "manifest.json")
            for name in PAYLOADS:
                archive.write(root / name, name)
    return {
        "output": str(output),
        "bytes": output.stat().st_size,
        "sha256": sha256_file(output),
        "vectors": len(vectors),
        "wines": len(wines),
        "codes": len(codes),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--catalog-db", required=True)
    parser.add_argument("--dis-model", required=True)
    parser.add_argument("--siglip-model", required=True)
    parser.add_argument("--confirm-pipeline", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--version", default=time.strftime("%Y%m%d"))
    args = parser.parse_args(argv)
    try:
        result = build(args)
    except (OSError, ValueError, sqlite3.Error) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
