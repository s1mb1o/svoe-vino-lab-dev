#!/usr/bin/env python3
"""Build SigLIP2 Base NaFlex p512 vectors in the iPhone catalogue order."""

from __future__ import annotations

import argparse
import io
import json
import zipfile
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModel


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACK = ROOT.parent / "android/app/src/main/assets/default_model_pack.zip"
DEFAULT_OUTPUT = ROOT / "build/siglip2-base-naflex-p512-vectors.f32"
MODEL_ID = "google/siglip2-base-patch16-naflex"
MODEL_CACHE = Path.home() / ".cache/huggingface/hub/models--google--siglip2-base-patch16-naflex/snapshots"


def square_image(data: bytes) -> Image.Image:
    source = Image.open(io.BytesIO(data)).convert("RGBA")
    side = max(source.size)
    result = Image.new("RGB", (side, side), "white")
    result.paste(source, ((side - source.width) // 2, (side - source.height) // 2), source)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--android-pack", type=Path, default=DEFAULT_PACK)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--device", choices=("auto", "cpu", "mps"), default="auto")
    args = parser.parse_args()
    if args.batch_size <= 0:
        parser.error("--batch-size must be positive")
    device = args.device
    if device == "auto":
        device = "mps" if torch.backends.mps.is_available() else "cpu"

    snapshots = sorted(path for path in MODEL_CACHE.glob("*") if path.is_dir())
    source_id: str | Path = snapshots[-1] if snapshots else MODEL_ID
    processor = AutoImageProcessor.from_pretrained(source_id, local_files_only=bool(snapshots))
    model = AutoModel.from_pretrained(source_id, local_files_only=bool(snapshots), attn_implementation="eager")
    vision = model.vision_model.eval().to(device)
    del model

    with zipfile.ZipFile(args.android_pack) as outer:
        wines = sorted(
            (json.loads(line) for line in outer.read("wines.jsonl").decode().splitlines() if line),
            key=lambda row: row["wine_slug"],
        )
        with zipfile.ZipFile(io.BytesIO(outer.read("images.zip"))) as images:
            vectors: list[np.ndarray] = []
            with torch.inference_mode():
                for offset in range(0, len(wines), args.batch_size):
                    batch = [square_image(images.read(row["image_path"])) for row in wines[offset : offset + args.batch_size]]
                    inputs = processor(images=batch, return_tensors="pt", max_num_patches=512)
                    inputs = {name: value.to(device) for name, value in inputs.items()}
                    values = vision(**inputs).pooler_output
                    values = values / values.norm(dim=-1, keepdim=True)
                    vectors.append(values.float().cpu().numpy())
                    print(f"{min(offset + args.batch_size, len(wines))}/{len(wines)}", flush=True)

    matrix = np.concatenate(vectors).astype("<f4", copy=False)
    if matrix.shape != (len(wines), 768) or not np.isfinite(matrix).all():
        raise SystemExit(f"invalid NaFlex matrix shape: {matrix.shape}")
    if float(np.max(np.abs(np.linalg.norm(matrix, axis=1) - 1))) > 0.001:
        raise SystemExit("NaFlex vector normalization failed")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(matrix.tobytes(order="C"))
    print(args.output)


if __name__ == "__main__":
    main()
