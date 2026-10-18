#!/usr/bin/env python3
"""Export the official IS-Net general-use DIS model to Core ML."""

from __future__ import annotations

import argparse
import importlib
import shutil
import sys
import tempfile
from pathlib import Path

import coremltools as ct
import numpy as np
import torch
from PIL import Image


INPUT_SIZE = 1024
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "ChtoZaVino/Resources/Models/DIS.mlpackage"
DEFAULT_SAMPLE = ROOT.parent / "workbench/data/catalog/embeddings/android-siglip2-base-224-dis-white/images/9253bb7435cabe995db0bd29d288ceae00ebc2735a88607db423e2decfc82cf4_full.png"


class SegmentationModel(torch.nn.Module):
    def __init__(self, model: torch.nn.Module) -> None:
        super().__init__()
        self.model = model

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        predictions, _ = self.model(image)
        return predictions[0]


def tensor_for_image(path: Path) -> np.ndarray:
    image = Image.open(path).convert("RGB").resize(
        (INPUT_SIZE, INPUT_SIZE), Image.Resampling.BILINEAR
    )
    pixels = np.asarray(image, dtype=np.float32) / 255.0 - 0.5
    return np.transpose(pixels, (2, 0, 1))[None]


def import_isnet(source: Path) -> type[torch.nn.Module]:
    source = source.resolve()
    if not (source / "models/isnet.py").is_file():
        raise SystemExit(f"IS-Net source is missing: {source}")
    sys.path.insert(0, str(source))
    return importlib.import_module("models.isnet").ISNetDIS


def verify(
    coreml_model: ct.models.MLModel,
    torch_model: torch.nn.Module,
    sample_path: Path,
) -> None:
    tensor = tensor_for_image(sample_path)
    with torch.inference_mode():
        expected = torch_model(torch.from_numpy(tensor)).numpy().reshape(-1)
    input_name = next(iter(coreml_model.input_description))
    actual = np.asarray(next(iter(coreml_model.predict({input_name: tensor}).values()))).reshape(-1)
    difference = np.abs(actual.astype(np.float32) - expected.astype(np.float32))
    print(f"DIS Core ML difference: mean={difference.mean():.8f} max={difference.max():.8f}")
    if not np.isfinite(difference).all() or float(difference.mean()) > 0.005:
        raise SystemExit("Core ML DIS does not match PyTorch")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Path to the official DIS/IS-Net directory")
    parser.add_argument("--weights", type=Path, required=True, help="Path to isnet-general-use.pth")
    parser.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    model_type = import_isnet(args.source)
    source = model_type()
    source.load_state_dict(torch.load(args.weights, map_location="cpu", weights_only=True))
    wrapped = SegmentationModel(source.eval()).eval()
    example = torch.zeros(1, 3, INPUT_SIZE, INPUT_SIZE)
    traced = torch.jit.trace(wrapped, example, strict=True, check_trace=False)
    model = ct.convert(
        traced,
        convert_to="mlprogram",
        minimum_deployment_target=ct.target.iOS17,
        compute_precision=ct.precision.FLOAT16,
        inputs=[ct.TensorType(name="image", shape=example.shape, dtype=np.float32)],
        outputs=[ct.TensorType(name="mask", dtype=np.float32)],
    )
    model.author = "Official xuebinqin/DIS export for Что за вино?"
    model.license = "Apache-2.0. See xuebinqin/DIS."
    model.short_description = "IS-Net general-use dichotomous image segmentation"
    model.user_defined_metadata["model_id"] = "xuebinqin/DIS isnet-general-use"
    if args.output.exists():
        shutil.rmtree(args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    model.save(str(args.output))
    with tempfile.TemporaryDirectory(prefix="chtozavino-dis-") as temporary_text:
        local_model = Path(temporary_text) / args.output.name
        shutil.copytree(args.output, local_model, copy_function=shutil.copyfile)
        loaded = ct.models.MLModel(str(local_model), compute_units=ct.ComputeUnit.CPU_ONLY)
        verify(loaded, wrapped, args.sample.resolve())
    print(args.output)


if __name__ == "__main__":
    main()
