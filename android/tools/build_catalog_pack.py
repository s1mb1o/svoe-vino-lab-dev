#!/usr/bin/env python3
"""Build the built-in Android pack from the workbench catalogue and DIS index."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import tempfile
import time
from urllib.parse import quote
import zipfile

import numpy as np

try:
    from . import build_model_pack
except ImportError:  # Direct script execution.
    import build_model_pack


ANDROID_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ANDROID_ROOT.parent / "workbench" / "data" / "catalog"
DEFAULT_EMBEDDING = "android-siglip2-base-224-dis-white"
DEFAULT_OUTPUT = ANDROID_ROOT / "app" / "src" / "main" / "assets" / "default_model_pack.zip"
DEFAULT_DIS_MODEL = (
    Path.home() / ".cache" / "huggingface" / "hub" /
    "models--litert-community--DIS-ISNet-LiteRT" / "snapshots" /
    "1b966dbe2f33bd5ca1299cf94fbab59265210b6b" / "dis.tflite"
)
DEFAULT_SIGLIP_MODEL = (
    Path.home() / ".cache" / "huggingface" / "hub" /
    "models--litert-community--SigLIP2-base-patch16-224" / "snapshots" /
    "509b5cbcf1a849f37696be08f8297c6cd3050bf4" /
    "siglip2_base_224_fp16.tflite"
)
PACK_VERSION = 2
IMAGE_SELECTION = "main_patched_else_main"
IMAGE_ARCHIVE = "images.zip"
PAYLOADS = build_model_pack.PAYLOADS + (IMAGE_ARCHIVE,)
SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class CatalogPackError(ValueError):
    """The catalogue or embedding index cannot make a valid Android pack."""


def json_file(path):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise CatalogPackError(f"cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise CatalogPackError(f"{path} must contain a JSON object")
    return value


def source_rows(database):
    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        wines = connection.execute(
            """
            SELECT w.wine_slug, w.name, w.producer, w.category, w.region, w.color,
                   w.grapes,
                   COALESCE(p.sha256, m.sha256) AS image_sha256,
                   COALESCE(pi.folder, mi.folder) AS image_folder,
                   COALESCE(pi.extension, mi.extension) AS image_extension,
                   CASE WHEN p.sha256 IS NOT NULL THEN 'main_patched' ELSE 'main' END
                       AS image_type
            FROM wine_catalog w
            LEFT JOIN wine_image p
              ON p.wine_slug = w.wine_slug AND p.image_type = 'main_patched'
            LEFT JOIN image pi ON pi.sha256 = p.sha256
            LEFT JOIN wine_image m
              ON m.wine_slug = w.wine_slug AND m.image_type = 'main'
            LEFT JOIN image mi ON mi.sha256 = m.sha256
            WHERE w.state = 'Active'
            ORDER BY w.wine_slug
            """
        ).fetchall()
        codes = connection.execute(
            """
            SELECT wine_slug, kind, value
            FROM wine_code
            ORDER BY wine_slug, kind, value
            """
        ).fetchall()
    finally:
        connection.close()
    return wines, codes


def load_index(catalog, embedding_name):
    root = catalog / "embeddings" / embedding_name
    index = json_file(root / "index.json")
    if index.get("name") != embedding_name:
        raise CatalogPackError("the embedding index name does not match the requested name")
    if index.get("dim") != build_model_pack.DIMENSION:
        raise CatalogPackError(
            f"the embedding dimension must be {build_model_pack.DIMENSION}"
        )
    config = index.get("config") or {}
    if config.get("model") != build_model_pack.MODEL:
        raise CatalogPackError(f"the embedding model must be {build_model_pack.MODEL}")
    vector_name = index.get("vectors_file")
    if not isinstance(vector_name, str) or Path(vector_name).name != vector_name:
        raise CatalogPackError("the embedding index has an invalid vectors_file")
    vectors = np.load(root / vector_name, allow_pickle=False)
    if (vectors.dtype != np.float32 or vectors.ndim != 2 or
            vectors.shape[1] != build_model_pack.DIMENSION):
        raise CatalogPackError(
            f"the embedding vectors must be float32 [N,{build_model_pack.DIMENSION}]"
        )
    if not np.isfinite(vectors).all():
        raise CatalogPackError("the embedding vectors contain a non-finite value")
    norms = np.linalg.norm(vectors, axis=1)
    if not np.allclose(norms, 1.0, rtol=1e-5, atol=1e-6):
        raise CatalogPackError("the embedding vectors are not L2-normalized")
    items = {}
    for number, item in enumerate(index.get("items") or [], 1):
        if not isinstance(item, dict):
            raise CatalogPackError(f"embedding item {number} is not an object")
        key = (item.get("source_sha256"), item.get("view"))
        row = item.get("row")
        if (isinstance(row, bool) or not isinstance(row, int) or not 0 <= row < len(vectors)):
            raise CatalogPackError(f"embedding item {number} has an invalid vector row")
        if key in items:
            raise CatalogPackError(f"the embedding index repeats item {key}")
        items[key] = row
    return root, index, vectors, items


def file_digest(path):
    return build_model_pack.sha256_file(path)


def verify_model(path, expected, label):
    if not path.is_file():
        raise CatalogPackError(f"{label} does not exist: {path}")
    if file_digest(path) != expected:
        raise CatalogPackError(f"{label} does not match the verified model")


def catalogue_image_path(catalog, folder, digest, extension):
    base = catalog / "cuts" if folder == "cropped" else catalog / "images" / folder
    return base / f"{digest}.{extension}"


def archive_digest(archive, name):
    digest = hashlib.sha256()
    with archive.open(name) as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_pack(path):
    """Validate one completed version 2 pack and return its summary."""
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        expected = {"manifest.json", *PAYLOADS}
        if len(names) != len(set(names)) or set(names) != expected:
            raise CatalogPackError("the pack root payload list is invalid")
        manifest = json.loads(archive.read("manifest.json"))
        if (manifest.get("format") != build_model_pack.PACK_FORMAT or
                manifest.get("format_version") != PACK_VERSION):
            raise CatalogPackError("the pack format is invalid")
        if set(manifest.get("files") or {}) != set(PAYLOADS):
            raise CatalogPackError("manifest.files does not match the pack payloads")
        for name in PAYLOADS:
            record = manifest["files"][name]
            info = archive.getinfo(name)
            if record.get("bytes") != info.file_size:
                raise CatalogPackError(f"the byte length of {name} is invalid")
            if record.get("sha256") != archive_digest(archive, name):
                raise CatalogPackError(f"the SHA-256 of {name} is invalid")
        vector_bytes = manifest["vector_count"] * build_model_pack.DIMENSION * 4
        if archive.getinfo("vectors.f32").file_size != vector_bytes:
            raise CatalogPackError("vectors.f32 has an invalid byte length")
        wine_rows = [json.loads(line) for line in archive.read("wines.jsonl").splitlines()]
        if len(wine_rows) != manifest["wine_count"]:
            raise CatalogPackError("wines.jsonl does not match wine_count")
        image_paths = [row.get("image_path") for row in wine_rows]
        with zipfile.ZipFile(archive.open(IMAGE_ARCHIVE)) as images:
            image_names = images.namelist()
            if len(image_names) != len(set(image_names)) or set(image_names) != set(image_paths):
                raise CatalogPackError("images.zip does not match wines.jsonl")
            if any(PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts
                   for name in image_names):
                raise CatalogPackError("images.zip contains an unsafe path")
        return {
            "vectors": manifest["vector_count"],
            "wines": manifest["wine_count"],
            "images": manifest["image_count"],
            "omitted_wines": manifest["omitted_wine_count"],
        }


def build(args):
    catalog = Path(args.catalog).resolve()
    database = catalog / "catalog.sqlite3"
    output = Path(args.out).resolve()
    dis_model = Path(args.dis_model).resolve()
    siglip_model = Path(args.siglip_model).resolve()
    if not database.is_file():
        raise CatalogPackError(f"catalog database does not exist: {database}")
    verify_model(dis_model, build_model_pack.DIS_MODEL_SHA256, "DIS model")
    verify_model(siglip_model, build_model_pack.SIGLIP_MODEL_SHA256, "SigLIP2 model")
    _, index, vectors, items = load_index(catalog, args.embedding)
    wines, codes = source_rows(database)

    selected_vectors = []
    candidate_rows = []
    wine_rows = []
    included_slugs = set()
    omitted = []
    image_sources = []
    for wine in wines:
        slug = wine["wine_slug"]
        digest = wine["image_sha256"]
        extension = wine["image_extension"]
        folder = wine["image_folder"]
        if not isinstance(slug, str) or not SLUG.fullmatch(slug):
            raise CatalogPackError(f"wine_slug is not safe for an image path: {slug!r}")
        reason = None
        if not digest or not folder or not extension:
            reason = "no main_patched or main image"
        elif (digest, "full") not in items:
            reason = "no current full vector in the DIS index"
        source = catalogue_image_path(catalog, str(folder), digest, str(extension))
        if reason is None and (source.is_symlink() or not source.is_file()):
            reason = "selected image file is absent"
        if reason is not None:
            omitted.append({"wine_slug": slug, "reason": reason})
            continue
        if file_digest(source) != digest:
            raise CatalogPackError(f"the selected image SHA-256 does not match for {slug}")
        row = len(selected_vectors)
        selected_vectors.append(vectors[items[(digest, "full")]])
        candidate_rows.append({"vector_row": row, "wine_slug": slug, "view": "full"})
        image_path = f"images/{slug}.{extension}"
        wine_rows.append({
            "wine_slug": slug,
            "name": wine["name"],
            "page_url": "https://vino-svoe.ru/wines/" + quote(slug, safe=""),
            "producer": wine["producer"],
            "category": wine["category"],
            "region": wine["region"],
            "color": wine["color"],
            "grapes": wine["grapes"],
            "image_path": image_path,
            "image_type": wine["image_type"],
            "image_sha256": digest,
        })
        image_sources.append((image_path, source))
        included_slugs.add(slug)
    if not selected_vectors:
        raise CatalogPackError("the catalogue selection has no wine")
    code_rows = [
        {"wine_slug": row["wine_slug"], "kind": row["kind"], "value": row["value"]}
        for row in codes if row["wine_slug"] in included_slugs
    ]
    matrix = np.ascontiguousarray(np.vstack(selected_vectors), dtype="<f4")

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and not args.replace:
        raise CatalogPackError(f"output exists; use --replace: {output}")
    with tempfile.TemporaryDirectory(prefix="svoe-vino-android-catalog-") as temporary:
        root = Path(temporary)
        shutil.copyfile(dis_model, root / "dis.tflite")
        shutil.copyfile(siglip_model, root / "siglip2_base_224_fp16.tflite")
        (root / "vectors.f32").write_bytes(matrix.tobytes(order="C"))
        build_model_pack.write_jsonl(root / "candidates.jsonl", candidate_rows)
        build_model_pack.write_jsonl(root / "wines.jsonl", wine_rows)
        build_model_pack.write_jsonl(root / "codes.jsonl", code_rows)
        with zipfile.ZipFile(root / IMAGE_ARCHIVE, "w", compression=zipfile.ZIP_STORED) as images:
            for image_path, source in image_sources:
                images.write(source, image_path)
        files = {
            name: {"bytes": (root / name).stat().st_size, "sha256": file_digest(root / name)}
            for name in PAYLOADS
        }
        manifest = {
            "format": build_model_pack.PACK_FORMAT,
            "format_version": PACK_VERSION,
            "version": args.version,
            "created_at_epoch_ms": int(time.time() * 1000),
            "pipeline": build_model_pack.PIPELINE,
            "model": build_model_pack.MODEL,
            "vector_dim": build_model_pack.DIMENSION,
            "vector_count": len(matrix),
            "wine_count": len(wine_rows),
            "image_count": len(image_sources),
            "omitted_wine_count": len(omitted),
            "image_selection": IMAGE_SELECTION,
            "source": {
                "embedding": args.embedding,
                "index_updated_at": index.get("updated_at"),
                "vectors_file": index.get("vectors_file"),
            },
            "files": files,
        }
        (root / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary_output = output.with_name(f".{output.name}.{os.getpid()}.tmp")
        try:
            with zipfile.ZipFile(temporary_output, "w", compression=zipfile.ZIP_STORED) as pack:
                pack.write(root / "manifest.json", "manifest.json")
                for name in PAYLOADS:
                    pack.write(root / name, name)
            summary = validate_pack(temporary_output)
            if output.exists() and not args.replace:
                raise CatalogPackError(f"output appeared during the build: {output}")
            os.replace(temporary_output, output)
        finally:
            try:
                temporary_output.unlink()
            except FileNotFoundError:
                pass
    return {
        **summary,
        "output": str(output),
        "bytes": output.stat().st_size,
        "sha256": file_digest(output),
        "codes": len(code_rows),
        "omissions": omitted,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG))
    parser.add_argument("--embedding", default=DEFAULT_EMBEDDING)
    parser.add_argument("--dis-model", default=str(DEFAULT_DIS_MODEL))
    parser.add_argument("--siglip-model", default=str(DEFAULT_SIGLIP_MODEL))
    parser.add_argument("--out", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--version", default=time.strftime("%Y%m%d"))
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = build(args)
    except (CatalogPackError, OSError, ValueError, sqlite3.Error, zipfile.BadZipFile) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
