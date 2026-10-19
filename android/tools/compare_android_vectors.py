#!/usr/bin/env python3
"""Compare CPU and GPU vectors from the Android debug embedding endpoint."""

from __future__ import annotations

import argparse
import base64
import json
import math
from pathlib import Path
import struct

try:
    from .run_pixel8_pilot import multipart_request
except ImportError:
    from run_pixel8_pilot import multipart_request


def decode_vector(response: dict) -> list[float]:
    dimension = response.get("embedding_dim")
    data = base64.b64decode(response["embedding_base64_f32le"], validate=True)
    if dimension != 768 or len(data) != dimension * 4:
        raise ValueError("the endpoint returned an invalid embedding payload")
    values = list(struct.unpack(f"<{dimension}f", data))
    if not all(math.isfinite(value) for value in values):
        raise ValueError("the endpoint returned a non-finite embedding")
    return values


def build(args) -> dict:
    image = Path(args.image).resolve()
    output = Path(args.output).resolve()
    responses = {}
    vectors = {}
    for accelerator in ("cpu", "gpu"):
        status, response, wall_ms = multipart_request(
            image,
            {
                "k": "5",
                "aggregation": "max",
                "dis_accelerator": "cpu",
                "siglip2_accelerator": accelerator,
            },
            args.timeout,
        )
        if status != 200:
            raise ValueError(f"{accelerator} request failed with HTTP {status}: {response}")
        response["client_wall_ms"] = wall_ms
        responses[accelerator] = response
        vectors[accelerator] = decode_vector(response)
    left = vectors["cpu"]
    right = vectors["gpu"]
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    cosine = dot / (left_norm * right_norm)
    maximum_error = max(abs(a - b) for a, b in zip(left, right))
    result = {
        "image": str(image),
        "cpu": {
            key: value for key, value in responses["cpu"].items()
            if key != "embedding_base64_f32le"
        },
        "gpu": {
            key: value for key, value in responses["gpu"].items()
            if key != "embedding_base64_f32le"
        },
        "cosine": cosine,
        "maximum_absolute_error": maximum_error,
        "passes": cosine >= args.minimum_cosine and maximum_error <= args.maximum_error,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--minimum-cosine", type=float, default=0.99999)
    parser.add_argument("--maximum-error", type=float, default=0.001)
    parser.add_argument("--timeout", type=float, default=300.0)
    args = parser.parse_args(argv)
    try:
        result = build(args)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
