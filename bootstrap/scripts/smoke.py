"""Send one real request to a running bootstrap model."""

from __future__ import annotations

import argparse
import base64
import io
import json
import math

import httpx
import qrcode
from PIL import Image, ImageDraw


def sample_image() -> bytes:
    image = Image.new("RGB", (320, 480), "white")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((90, 80, 230, 450), radius=28, fill=(55, 95, 45))
    draw.rectangle((130, 20, 190, 110), fill=(60, 80, 40))
    draw.rectangle((100, 240, 220, 360), fill=(245, 235, 205))
    draw.text((125, 285), "WINE", fill="black")
    output = io.BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


def qr_image(text: str) -> bytes:
    output = io.BytesIO()
    qrcode.make(text).save(output, "PNG")
    return output.getvalue()


def embedding(client: httpx.Client, base: str, model: str) -> dict[str, object]:
    uri = "data:image/png;base64," + base64.b64encode(sample_image()).decode("ascii")
    body: dict[str, object] = {"model": model, "input": [uri]}
    if model.endswith("naflex"):
        body["max_num_patches"] = 256
    response = client.post(f"{base}/v1/embeddings", json=body)
    response.raise_for_status()
    result = response.json()
    vector = result["data"][0]["embedding"]
    if len(vector) != 1152 or not all(math.isfinite(value) for value in vector):
        raise AssertionError("SigLIP2 did not return one finite 1,152-value vector")
    norm = math.sqrt(sum(value * value for value in vector))
    if abs(norm - 1.0) > 0.01:
        raise AssertionError(f"SigLIP2 vector norm is {norm}")
    return {"dimension": len(vector), "norm": norm}


def qr(client: httpx.Client, base: str) -> dict[str, object]:
    expected = "svoe-vino-bootstrap"
    response = client.post(
        f"{base}/upstream/qr-scanner/scan",
        files={"image": ("qr.png", qr_image(expected), "image/png")},
        data={"engine": "auto"},
    )
    response.raise_for_status()
    result = response.json()
    values = [instance["text"] for instance in result["instances"]]
    if expected not in values:
        raise AssertionError(f"QR response does not contain {expected!r}: {values}")
    return {"decoded": values}


def shieldgemma(client: httpx.Client, base: str) -> dict[str, object]:
    response = client.post(
        f"{base}/upstream/shieldgemma-2-4b-it/classify",
        files={"image": ("bottle.png", sample_image(), "image/png")},
        data={"policies": "dangerous,sexual,violence", "threshold": "0.5"},
    )
    response.raise_for_status()
    result = response.json()
    expected = {"dangerous", "sexual", "violence"}
    if set(result["scores"]) != expected:
        raise AssertionError(f"ShieldGemma policy keys differ: {result['scores']}")
    return {"scores": result["scores"], "flagged": result["flagged"]}


def sam3(client: httpx.Client, base: str) -> dict[str, object]:
    response = client.post(
        f"{base}/upstream/sam3/segment",
        files={"image": ("bottle.png", sample_image(), "image/png")},
        data={"text": "wine bottle", "threshold": "0.1", "return_masks": "false"},
    )
    response.raise_for_status()
    result = response.json()
    if result["width"] != 320 or result["height"] != 480:
        raise AssertionError(f"SAM3 response has wrong dimensions: {result}")
    if not isinstance(result["instances"], list):
        raise AssertionError("SAM3 instances is not a list")
    return {"count": result["count"], "width": result["width"], "height": result["height"]}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:18090")
    parser.add_argument(
        "--model",
        required=True,
        choices=[
            "qr-scanner",
            "shieldgemma-2-4b-it",
            "siglip2-so400m-patch16-naflex",
            "siglip2-so400m-patch16-512",
            "sam3",
        ],
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    functions = {
        "qr-scanner": qr,
        "shieldgemma-2-4b-it": shieldgemma,
        "siglip2-so400m-patch16-naflex": embedding,
        "siglip2-so400m-patch16-512": embedding,
        "sam3": sam3,
    }
    with httpx.Client(timeout=900.0) as client:
        if arguments.model.startswith("siglip2-"):
            result = functions[arguments.model](client, arguments.base_url, arguments.model)
        else:
            result = functions[arguments.model](client, arguments.base_url)
    print(json.dumps({"model": arguments.model, "result": result}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

