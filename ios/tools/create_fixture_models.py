#!/usr/bin/env python3
"""Create deterministic Core ML models for iOS simulator integration tests."""

from __future__ import annotations

import shutil
from pathlib import Path

import coremltools as ct
import numpy as np
from coremltools.converters.mil import Builder as mb


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "ChtoZaVino/Resources/Models"


def save_constant_model(name: str, input_shape: tuple[int, ...], output: np.ndarray) -> None:
    @mb.program(
        input_specs=[mb.TensorSpec(shape=input_shape, dtype=ct.converters.mil.mil.types.fp32)],
        opset_version=ct.target.iOS17,
    )
    def program(image):
        return mb.const(val=output, name="output")

    model = ct.convert(
        program,
        convert_to="mlprogram",
        minimum_deployment_target=ct.target.iOS17,
        compute_precision=ct.precision.FLOAT16,
    )
    target = OUTPUT / f"{name}.mlpackage"
    if target.exists():
        shutil.rmtree(target)
    model.save(target)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    coordinates = np.linspace(-1.0, 1.0, 1024, dtype=np.float32)
    yy, xx = np.meshgrid(coordinates, coordinates, indexing="ij")
    mask = np.exp(-((xx / 0.38) ** 8 + (yy / 0.82) ** 8)).astype(np.float32)[None, None]
    save_constant_model("DIS", (1, 3, 1024, 1024), mask)

    siglip = np.zeros((1, 768), dtype=np.float32)
    siglip[0, 0] = 1.0
    save_constant_model("SigLIP2ImageEncoder", (1, 3, 224, 224), siglip)

    mobileclip = np.zeros((1, 512), dtype=np.float32)
    mobileclip[0, 0] = 1.0
    save_constant_model("MobileCLIP2S2ImageEncoder", (1, 3, 256, 256), mobileclip)
    print(OUTPUT)


if __name__ == "__main__":
    main()
