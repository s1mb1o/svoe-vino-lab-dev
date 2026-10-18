#!/usr/bin/env python3
"""Export the production MobileCLIP2-S2 image encoder to Core ML."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path

import coremltools as ct
import numpy as np
import open_clip
import torch
from PIL import Image
from timm.utils.model import reparameterize_model


MODEL_ID = "MobileCLIP2-S2"
PRETRAINED = "dfndr2b"
INPUT_SIZE = 256
VECTOR_DIMENSION = 512
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX = ROOT.parent / "workbench/data/catalog/embeddings/android-siglip2-base-224-dis-white/index.json"
DEFAULT_OUTPUT = ROOT / "ChtoZaVino/Resources/Models/MobileCLIP2S2ImageEncoder.mlpackage"


class ImageEncoder(torch.nn.Module):
    def __init__(self, visual: torch.nn.Module) -> None:
        super().__init__()
        self.visual = visual

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        return self.visual(image)


def tensor_for_image(path: Path) -> np.ndarray:
    image = Image.open(path).convert("RGB")
    image = image.resize((INPUT_SIZE, INPUT_SIZE), Image.Resampling.BILINEAR)
    pixels = np.asarray(image, dtype=np.float32) / 255.0
    return np.transpose(pixels, (2, 0, 1))[None]


def normalized(vector: np.ndarray) -> np.ndarray:
    vector = np.asarray(vector, dtype=np.float32).reshape(-1)
    norm = np.linalg.norm(vector)
    if not np.isfinite(norm) or norm <= 0:
        raise ValueError("model returned an invalid vector")
    return vector / norm


def verify(
    coreml_model: ct.models.MLModel,
    torch_model: torch.nn.Module,
    index_path: Path,
    sample_count: int,
) -> None:
    index = json.loads(index_path.read_text(encoding="utf-8"))
    rows = np.linspace(0, len(index["items"]) - 1, min(sample_count, len(index["items"])), dtype=int)
    input_name = next(iter(coreml_model.input_description))
    cosines: list[float] = []
    for row in rows:
        item = index["items"][int(row)]
        tensor = tensor_for_image(index_path.parent / item["image"])
        with torch.inference_mode():
            expected = torch_model(torch.from_numpy(tensor)).numpy()
        result = coreml_model.predict({input_name: tensor})
        actual = normalized(next(iter(result.values())))
        cosines.append(float(np.dot(actual, normalized(expected))))
    minimum = min(cosines)
    print(f"MobileCLIP2-S2 Core ML cosine: min={minimum:.8f} mean={np.mean(cosines):.8f}")
    if minimum < 0.999:
        raise SystemExit("Core ML MobileCLIP2-S2 does not match PyTorch")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--verify-samples", type=int, default=3)
    args = parser.parse_args()

    torch.manual_seed(0)
    source = open_clip.create_model(MODEL_ID, pretrained=PRETRAINED).eval()
    visual = reparameterize_model(source.visual, inplace=False).eval()
    wrapped = ImageEncoder(visual).eval()
    example = torch.zeros(1, 3, INPUT_SIZE, INPUT_SIZE)
    exported = torch.export.export(wrapped, (example,)).run_decompositions({})
    model = ct.convert(
        exported,
        convert_to="mlprogram",
        minimum_deployment_target=ct.target.iOS17,
        compute_precision=ct.precision.FLOAT16,
    )
    model.author = "Apple MobileCLIP2 export for Что за вино?"
    model.license = "Research use only. See apple/ml-mobileclip LICENSE_MODELS."
    model.short_description = "MobileCLIP2-S2 image encoder"
    model.user_defined_metadata["model_id"] = "apple/MobileCLIP2-S2"
    model.user_defined_metadata["vector_dimension"] = str(VECTOR_DIMENSION)
    if args.output.exists():
        shutil.rmtree(args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    model.save(str(args.output))
    with tempfile.TemporaryDirectory(prefix="chtozavino-mobileclip2-") as temporary_text:
        local_model = Path(temporary_text) / args.output.name
        shutil.copytree(args.output, local_model, copy_function=shutil.copyfile)
        loaded = ct.models.MLModel(str(local_model), compute_units=ct.ComputeUnit.CPU_ONLY)
        verify(loaded, wrapped, args.index.resolve(), args.verify_samples)
    print(args.output)


if __name__ == "__main__":
    main()
