"""Static INT8 quantization (QDQ) of a bottle detector for the phone's accelerator,
calibrated on frames prepared exactly as scripts/detect_onnx.py prepares them.

    uv run --extra detect python scripts/quantize_onnx.py MODEL.onnx IMAGES_DIR OUT.onnx [--count 100]
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

import cv2
from onnxruntime.quantization import CalibrationDataReader, QuantFormat, QuantType, quantize_static
from onnxruntime.quantization.shape_inference import quant_pre_process

sys.path.insert(0, str(Path(__file__).parent))
from detect_onnx import Detector  # noqa: E402


class Frames(CalibrationDataReader):
    def __init__(self, detector: Detector, files: list[Path]):
        self.detector, self.files = detector, iter(files)

    def get_next(self):
        path = next(self.files, None)
        return None if path is None else {self.detector.name: self.detector.prepare(cv2.imread(str(path)))[0]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("model")
    parser.add_argument("images")
    parser.add_argument("out")
    parser.add_argument("--count", type=int, default=100)
    args = parser.parse_args()
    files = sorted(Path(args.images).glob("*.jpg"))
    files = sorted(random.Random(0).sample(files, min(args.count, len(files))))
    prepared = Path(args.out).with_suffix(".pre.onnx")
    quant_pre_process(args.model, str(prepared))
    quantize_static(str(prepared), args.out, Frames(Detector(args.model), files), quant_format=QuantFormat.QDQ,
                    activation_type=QuantType.QUInt8, weight_type=QuantType.QUInt8, per_channel=False)
    prepared.unlink()
    print(f"{args.out}: calibrated on {len(files)} frames")


if __name__ == "__main__":
    main()
