#!/usr/bin/env python3
"""Build MobileCLIP2-S2 vectors in the iPhone catalogue row order."""

from __future__ import annotations

import argparse
import io
import json
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import open_clip
import torch
from PIL import Image
from timm.utils.model import reparameterize_model


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ANDROID_PACK = ROOT.parent / "android/app/src/main/assets/default_model_pack.zip"
DEFAULT_INDEX = ROOT.parent / "workbench/data/catalog/embeddings/android-siglip2-base-224-dis-white/index.json"
DEFAULT_OUTPUT = ROOT / "build/mobileclip2-s2-vectors.f32"


def read_wines(path: Path) -> list[dict]:
    with zipfile.ZipFile(path) as archive:
        rows = [json.loads(line) for line in archive.read("wines.jsonl").decode().splitlines() if line]
    return sorted(rows, key=lambda row: row["wine_slug"])


def image_paths(index_path: Path, wines: list[dict], android_pack: Path, fallback: Path) -> list[Path]:
    index = json.loads(index_path.read_text(encoding="utf-8"))
    by_source = {
        item["source_sha256"]: index_path.parent / item["image"]
        for item in index["items"]
        if item.get("view") == "full"
    }
    paths: list[Path] = []
    missing: list[tuple[int, dict]] = []
    for position, wine in enumerate(wines):
        path = by_source.get(wine.get("image_source_sha256"))
        if path is None or not path.is_file():
            path = fallback / wine["image_path"]
            missing.append((position, wine))
        paths.append(path)
    if missing:
        with zipfile.ZipFile(android_pack) as outer:
            with zipfile.ZipFile(io.BytesIO(outer.read("images.zip"))) as images:
                for _, wine in missing:
                    target = fallback / wine["image_path"]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(images.read(wine["image_path"]))
        print(f"used {len(missing)} package images because prepared images were absent", flush=True)
    return paths


def load_batch(paths: list[Path]) -> torch.Tensor:
    rows: list[np.ndarray] = []
    for path in paths:
        source = Image.open(path).convert("RGBA")
        white = Image.new("RGBA", source.size, "white")
        white.alpha_composite(source)
        image = white.convert("RGB").resize((256, 256), Image.Resampling.BILINEAR)
        pixels = np.asarray(image, dtype=np.float32) / 255.0
        rows.append(np.transpose(pixels, (2, 0, 1)))
    return torch.from_numpy(np.stack(rows))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--android-pack", type=Path, default=DEFAULT_ANDROID_PACK)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--device", choices=("auto", "cpu", "mps"), default="auto")
    args = parser.parse_args()
    if args.batch_size <= 0:
        parser.error("--batch-size must be positive")

    device = args.device
    if device == "auto":
        device = "mps" if torch.backends.mps.is_available() else "cpu"
    wines = read_wines(args.android_pack.resolve())
    vectors: list[np.ndarray] = []
    with tempfile.TemporaryDirectory(prefix="chtozavino-mobileclip-images-") as temporary_text:
        paths = image_paths(args.index.resolve(), wines, args.android_pack.resolve(), Path(temporary_text))
        source = open_clip.create_model("MobileCLIP2-S2", pretrained="dfndr2b").eval()
        visual = reparameterize_model(source.visual, inplace=False).eval().to(device)
        with torch.inference_mode():
            for offset in range(0, len(paths), args.batch_size):
                batch = load_batch(paths[offset : offset + args.batch_size]).to(device)
                values = visual(batch)
                values = values / values.norm(dim=-1, keepdim=True)
                vectors.append(values.float().cpu().numpy())
                print(f"{min(offset + args.batch_size, len(paths))}/{len(paths)}", flush=True)
    matrix = np.concatenate(vectors).astype("<f4", copy=False)
    if matrix.shape != (len(wines), 512) or not np.isfinite(matrix).all():
        raise SystemExit(f"invalid MobileCLIP2 matrix shape: {matrix.shape}")
    norms = np.linalg.norm(matrix, axis=1)
    if float(np.max(np.abs(norms - 1))) > 0.001:
        raise SystemExit("MobileCLIP2 vector normalization failed")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(matrix.tobytes(order="C"))
    print(args.output)


if __name__ == "__main__":
    main()
