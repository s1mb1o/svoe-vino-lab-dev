#!/usr/bin/env python3
"""Compile Core ML packages outside the external workspace volume."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "ChtoZaVino/Resources/Models"
OUTPUT = ROOT / "ChtoZaVino/Resources/CompiledModels"
MODEL_NAMES = (
    "DIS",
    "YOLO26nSeg",
    "SigLIP2BaseNaFlexP512ImageEncoder",
    "SigLIP2ImageEncoder",
    "MobileCLIP2S2ImageEncoder",
)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="chtozavino-coreml-") as temporary_text:
        temporary = Path(temporary_text)
        for name in MODEL_NAMES:
            source = SOURCE / f"{name}.mlpackage"
            if not source.is_dir():
                raise SystemExit(f"Core ML package is missing: {source}")
            local_source = temporary / source.name
            shutil.copytree(source, local_source, copy_function=shutil.copyfile)
            subprocess.run(
                ["xcrun", "coremlc", "compile", str(local_source), str(temporary)],
                check=True,
            )
            compiled = temporary / f"{name}.mlmodelc"
            target = OUTPUT / compiled.name
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(compiled, target, copy_function=shutil.copyfile)
    print(OUTPUT)


if __name__ == "__main__":
    main()
