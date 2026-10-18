#!/usr/bin/env python3
"""Export the official YOLO26n-seg checkpoint to Core ML."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import tempfile
from pathlib import Path

import coremltools as ct
import numpy as np
import torch
from PIL import Image
from ultralytics import YOLO
from ultralytics.nn.modules import Attention, Detect


INPUT_SIZE = 640
DETECTION_SHAPE = (1, 116, 8400)
PROTOTYPE_SHAPE = (1, 32, 160, 160)
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "ChtoZaVino/Resources/Models/YOLO26nSeg.mlpackage"
DEFAULT_SAMPLE = (
    ROOT.parent
    / "workbench/data/catalog/embeddings/android-siglip2-base-224-dis-white/images/"
    "eb582486c6c84c3b5cb857e3b81fe0d4c0caca12483c355889bcc9b08e68a3f8_full.png"
)


def input_tensor(path: Path) -> np.ndarray:
    image = Image.open(path).convert("RGB")
    scale = min(INPUT_SIZE / image.width, INPUT_SIZE / image.height)
    width = max(1, round(image.width * scale))
    height = max(1, round(image.height * scale))
    canvas = Image.new("RGB", (INPUT_SIZE, INPUT_SIZE), (114, 114, 114))
    resized = image.resize((width, height), Image.Resampling.BILINEAR)
    canvas.paste(resized, ((INPUT_SIZE - width) // 2, (INPUT_SIZE - height) // 2))
    pixels = np.asarray(canvas, dtype=np.float32) / 255.0
    return np.transpose(pixels, (2, 0, 1))[None]


def prepare_model(checkpoint: Path) -> torch.nn.Module:
    model = YOLO(str(checkpoint)).model.eval().float()
    model.end2end = False
    model = model.fuse(imgsz=[INPUT_SIZE, INPUT_SIZE])
    for parameter in model.parameters():
        parameter.requires_grad = False
    for module in model.modules():
        if isinstance(module, Attention):
            module.format = "coreml"
        if isinstance(module, Detect):
            module.dynamic = False
            module.export = True
            module.format = "coreml"
            module.xyxy = False
            module.shape = None
    return model


def ordered(values: list[np.ndarray]) -> list[np.ndarray]:
    return sorted((np.asarray(value) for value in values), key=np.size, reverse=True)


def cosine(left: np.ndarray, right: np.ndarray) -> float:
    left = left.astype(np.float32).reshape(-1)
    right = right.astype(np.float32).reshape(-1)
    return float(np.dot(left, right) / (np.linalg.norm(left) * np.linalg.norm(right)))


def verify(
    coreml_model: ct.models.MLModel,
    torch_model: torch.nn.Module,
    sample: Path,
) -> None:
    tensor = input_tensor(sample)
    with torch.inference_mode():
        expected = ordered([value.numpy() for value in torch_model(torch.from_numpy(tensor))])
    input_name = next(iter(coreml_model.input_description))
    actual = ordered(list(coreml_model.predict({input_name: tensor}).values()))
    expected_shapes = [DETECTION_SHAPE, PROTOTYPE_SHAPE]
    if [tuple(value.shape) for value in actual] != expected_shapes:
        raise SystemExit(f"Core ML YOLO outputs have wrong shapes: {[value.shape for value in actual]}")
    cosines = [cosine(left, right) for left, right in zip(expected, actual, strict=True)]
    print(f"YOLO26n-seg Core ML cosine: detection={cosines[0]:.8f} prototypes={cosines[1]:.8f}")
    if min(cosines) < 0.999:
        raise SystemExit("Core ML YOLO26n-seg does not match PyTorch")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    checkpoint = args.checkpoint.resolve()
    source = prepare_model(checkpoint)
    example = torch.zeros(1, 3, INPUT_SIZE, INPUT_SIZE)
    with torch.inference_mode():
        shapes = tuple(tuple(value.shape) for value in source(example))
    if shapes != (DETECTION_SHAPE, PROTOTYPE_SHAPE):
        raise SystemExit(f"PyTorch YOLO outputs have wrong shapes: {shapes}")
    exported = torch.export.export(source, (example,), strict=False).run_decompositions({})
    converted = ct.convert(
        exported,
        convert_to="mlprogram",
        minimum_deployment_target=ct.target.iOS17,
        compute_precision=ct.precision.FLOAT16,
    )
    converted.author = "Ultralytics YOLO26n-seg export for Что за вино?"
    converted.license = "AGPL-3.0. See ultralytics/ultralytics."
    converted.short_description = "YOLO26n-seg COCO instance segmentation"
    converted.user_defined_metadata["model_id"] = "ultralytics/yolo26n-seg"
    converted.user_defined_metadata["checkpoint_sha256"] = hashlib.sha256(checkpoint.read_bytes()).hexdigest()

    with tempfile.TemporaryDirectory(prefix="chtozavino-yolo26-") as temporary_text:
        local_output = Path(temporary_text) / args.output.name
        converted.save(str(local_output))
        loaded = ct.models.MLModel(str(local_output), compute_units=ct.ComputeUnit.CPU_ONLY)
        verify(loaded, source, args.sample.resolve())
        if args.output.exists():
            shutil.rmtree(args.output)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(local_output, args.output, copy_function=shutil.copyfile)
    print(args.output)


if __name__ == "__main__":
    main()
