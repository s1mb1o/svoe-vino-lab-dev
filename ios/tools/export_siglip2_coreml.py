#!/usr/bin/env python3
"""Export the production SigLIP2 image encoder to Core ML."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path

import coremltools as ct
import numpy as np
import timm
import torch
from PIL import Image


MODEL_ID = "vit_base_patch16_siglip_224.v2_webli"
INPUT_SIZE = 224
RESIZE_SIZE = 248
VECTOR_DIMENSION = 768
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX = ROOT.parent / "workbench/data/catalog/embeddings/android-siglip2-base-224-dis-white/index.json"
DEFAULT_OUTPUT = ROOT / "ChtoZaVino/Resources/Models/SigLIP2ImageEncoder.mlpackage"


class ImageEncoder(torch.nn.Module):
    def __init__(self, model: torch.nn.Module) -> None:
        super().__init__()
        self.model = model

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        return self.model(image)


def tensor_for_image(path: Path) -> np.ndarray:
    image = Image.open(path).convert("RGB")
    if image.size != (INPUT_SIZE, INPUT_SIZE):
        raise ValueError(f"prepared image has size {image.size}: {path}")
    image = image.resize((RESIZE_SIZE, RESIZE_SIZE), Image.Resampling.BICUBIC)
    offset = (RESIZE_SIZE - INPUT_SIZE) // 2
    image = image.crop((offset, offset, offset + INPUT_SIZE, offset + INPUT_SIZE))
    pixels = np.asarray(image, dtype=np.float32) / 127.5 - 1.0
    return np.transpose(pixels, (2, 0, 1))[None]


def normalized(vector: np.ndarray) -> np.ndarray:
    vector = np.asarray(vector, dtype=np.float32).reshape(-1)
    norm = np.linalg.norm(vector)
    if not np.isfinite(norm) or norm <= 0:
        raise ValueError("model returned an invalid vector")
    return vector / norm


def verify(model: ct.models.MLModel, index_path: Path, sample_count: int) -> None:
    index = json.loads(index_path.read_text(encoding="utf-8"))
    vectors = np.load(index_path.parent / index["vectors_file"], allow_pickle=False)
    rows = np.linspace(0, len(index["items"]) - 1, min(sample_count, len(index["items"])), dtype=int)
    input_name = next(iter(model.input_description))
    cosines: list[float] = []
    for row in rows:
        item = index["items"][int(row)]
        tensor = tensor_for_image(index_path.parent / item["image"])
        result = model.predict({input_name: tensor})
        actual = normalized(next(iter(result.values())))
        expected = normalized(vectors[int(row)])
        cosines.append(float(np.dot(actual, expected)))
    minimum = min(cosines)
    print(f"SigLIP2 Core ML cosine: min={minimum:.8f} mean={np.mean(cosines):.8f}")
    if minimum < 0.999:
        raise SystemExit("Core ML SigLIP2 does not match the Android index")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--verify-samples", type=int, default=3)
    parser.add_argument("--precision", choices=("mixed", "fp16", "fp32"), default="fp32")
    args = parser.parse_args()

    torch.manual_seed(0)
    source = timm.create_model(MODEL_ID, pretrained=True, num_classes=0).eval()
    wrapped = ImageEncoder(source).eval()
    example = torch.zeros(1, 3, INPUT_SIZE, INPUT_SIZE)
    traced = torch.jit.trace(wrapped, example, strict=True)
    if args.precision == "fp16":
        compute_precision = ct.precision.FLOAT16
    elif args.precision == "fp32":
        compute_precision = ct.precision.FLOAT32
    else:
        compute_precision = ct.transform.FP16ComputePrecision(
            op_selector=lambda operation: operation.op_type not in {"layer_norm", "softmax"}
        )
    model = ct.convert(
        traced,
        convert_to="mlprogram",
        minimum_deployment_target=ct.target.iOS17,
        compute_precision=compute_precision,
        inputs=[ct.TensorType(name="image", shape=example.shape, dtype=np.float32)],
        outputs=[ct.TensorType(name="embedding", dtype=np.float32)],
    )
    model.author = "Apple timm model export for Что за вино?"
    model.license = "Apache-2.0 model license. See the upstream model card."
    model.short_description = f"{MODEL_ID} image encoder"
    model.user_defined_metadata["model_id"] = MODEL_ID
    model.user_defined_metadata["vector_dimension"] = str(VECTOR_DIMENSION)
    if args.output.exists():
        shutil.rmtree(args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    model.save(str(args.output))
    with tempfile.TemporaryDirectory(prefix="chtozavino-siglip2-") as temporary_text:
        local_model = Path(temporary_text) / args.output.name
        shutil.copytree(args.output, local_model, copy_function=shutil.copyfile)
        loaded = ct.models.MLModel(str(local_model), compute_units=ct.ComputeUnit.CPU_ONLY)
        verify(loaded, args.index.resolve(), args.verify_samples)
    print(args.output)


if __name__ == "__main__":
    main()
