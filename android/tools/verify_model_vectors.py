#!/usr/bin/env python3
"""Compare a workbench GPU index with the Android SigLIP2 LiteRT model."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


INPUT_SIZE = 224
TIMM_RESIZE_SIZE = 248
VECTOR_DIMENSION = 768


class VerificationError(ValueError):
    """The verification input does not satisfy the required contract."""


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize(vector):
    vector = np.asarray(vector, dtype=np.float32).reshape(-1)
    norm = np.linalg.norm(vector)
    if not np.isfinite(norm) or norm <= 0:
        raise VerificationError("the model returned an invalid vector")
    return vector / norm


def model_tensor(image):
    image = image.convert("RGB")
    if image.size != (INPUT_SIZE, INPUT_SIZE):
        raise VerificationError(f"the prepared image is {image.size}, not 224x224")
    resized = image.resize(
        (TIMM_RESIZE_SIZE, TIMM_RESIZE_SIZE),
        Image.Resampling.BICUBIC,
    )
    offset = (TIMM_RESIZE_SIZE - INPUT_SIZE) // 2
    cropped = resized.crop((offset, offset, offset + INPUT_SIZE, offset + INPUT_SIZE))
    array = np.asarray(cropped, dtype=np.float32)
    return np.transpose(array / 127.5 - 1.0, (2, 0, 1))[None]


def direct_tensor(image):
    image = image.convert("RGB")
    if image.size != (INPUT_SIZE, INPUT_SIZE):
        raise VerificationError(f"the prepared image is {image.size}, not 224x224")
    array = np.asarray(image, dtype=np.float32)
    return np.transpose(array / 127.5 - 1.0, (2, 0, 1))[None]


def summarize(values):
    return {
        "minimum": float(np.min(values)),
        "mean": float(np.mean(values)),
        "maximum": float(np.max(values)),
    }


def verify(index_path, model_path, sample_size):
    try:
        from ai_edge_litert.interpreter import Interpreter
    except ImportError as error:
        raise VerificationError("install ai-edge-litert before this test") from error

    index = json.loads(index_path.read_text(encoding="utf-8"))
    items = index.get("items") or []
    if not items:
        raise VerificationError("the index has no items")
    vectors_path = index_path.parent / index["vectors_file"]
    vectors = np.load(vectors_path, allow_pickle=False)
    if vectors.shape != (len(items), VECTOR_DIMENSION):
        raise VerificationError(
            f"the vector matrix has shape {vectors.shape}, not ({len(items)}, 768)"
        )
    sample_size = min(sample_size, len(items))
    rows = np.linspace(0, len(items) - 1, sample_size, dtype=int)

    interpreter = Interpreter(model_path=str(model_path))
    interpreter.allocate_tensors()
    input_detail = interpreter.get_input_details()[0]
    output_detail = interpreter.get_output_details()[0]
    if list(input_detail["shape"]) != [1, 3, INPUT_SIZE, INPUT_SIZE]:
        raise VerificationError(f"unexpected input shape: {input_detail['shape'].tolist()}")
    if list(output_detail["shape"]) != [1, VECTOR_DIMENSION]:
        raise VerificationError(f"unexpected output shape: {output_detail['shape'].tolist()}")

    matching_cosines = []
    control_cosines = []
    output_norms = []
    for row in rows:
        item = items[int(row)]
        image = Image.open(index_path.parent / item["image"])
        expected = normalize(vectors[int(row)])
        for make_tensor, target in (
            (model_tensor, matching_cosines),
            (direct_tensor, control_cosines),
        ):
            interpreter.set_tensor(input_detail["index"], make_tensor(image))
            interpreter.invoke()
            raw = interpreter.get_tensor(output_detail["index"])
            actual = normalize(raw)
            target.append(float(np.dot(expected, actual)))
            if make_tensor is model_tensor:
                output_norms.append(float(np.linalg.norm(raw)))

    return {
        "index": index.get("name"),
        "population": len(items),
        "sample_size": sample_size,
        "rows": [int(row) for row in rows],
        "model_sha256": sha256_file(model_path),
        "model_input_shape": [int(value) for value in input_detail["shape"]],
        "model_output_shape": [int(value) for value in output_detail["shape"]],
        "catalogue_vs_litert_timm_preprocessing": summarize(matching_cosines),
        "catalogue_vs_litert_direct_control": summarize(control_cosines),
        "litert_raw_output_norm": summarize(output_norms),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", required=True, type=Path)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--sample-size", type=int, default=32)
    args = parser.parse_args()
    if args.sample_size <= 0:
        parser.error("--sample-size must be positive")
    result = verify(args.index.resolve(), args.model.resolve(), args.sample_size)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
