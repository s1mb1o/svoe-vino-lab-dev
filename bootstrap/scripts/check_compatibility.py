#!/usr/bin/env python3
"""Check the external ML endpoint contracts used by the project."""

from __future__ import annotations

import argparse
import base64
import json
import math
import os
import time
from dataclasses import dataclass
from typing import Any, Callable

import httpx

if __package__:
    from .smoke import qr_image, sample_image
else:
    from smoke import qr_image, sample_image


NAFLEX_MODEL = "siglip2-so400m-patch16-naflex"
NAFLEX_PATCH_BUDGET = 512
VECTOR_DIMENSION = 1152


@dataclass(frozen=True)
class Settings:
    qr_scanner_endpoint: str | None
    sam3_endpoint: str | None
    siglip2_endpoint: str | None
    vlm_endpoint: str | None
    vlm_model: str | None
    shieldgemma_endpoint: str | None
    vlm_api_key: str | None


def _url(endpoint: str, path: str) -> str:
    return endpoint.rstrip("/") + path


def _object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AssertionError(f"{label} is not a JSON object")
    return value


def _list(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise AssertionError(f"{label} is not a JSON array")
    return value


def check_qr(client: httpx.Client, endpoint: str) -> dict[str, object]:
    expected = "svoe-vino-compatibility"
    response = client.post(
        _url(endpoint, "/scan"),
        files={"image": ("qr.png", qr_image(expected), "image/png")},
        data={"engine": "auto"},
    )
    response.raise_for_status()
    result = _object(response.json(), "QR response")
    instances = _list(result.get("instances"), "QR instances")
    values = [item.get("text") for item in instances if isinstance(item, dict)]
    if expected not in values:
        raise AssertionError(f"QR response does not contain {expected!r}")
    return {"decoded": expected, "count": result.get("count")}


def check_sam3(client: httpx.Client, endpoint: str) -> dict[str, object]:
    response = client.post(
        _url(endpoint, "/segment"),
        files={"image": ("bottle.png", sample_image(), "image/png")},
        data={"text": "wine bottle", "threshold": "0.1", "return_masks": "false"},
    )
    response.raise_for_status()
    result = _object(response.json(), "SAM3 response")
    instances = _list(result.get("instances"), "SAM3 instances")
    if result.get("width") != 320 or result.get("height") != 480:
        raise AssertionError("SAM3 response dimensions do not match the input image")
    count = result.get("count")
    if count != len(instances):
        raise AssertionError("SAM3 count does not match the instance list")
    if not isinstance(count, int) or count < 1:
        raise AssertionError("SAM3 did not find the generated wine bottle")
    return {"count": count, "width": 320, "height": 480}


def check_siglip2(client: httpx.Client, endpoint: str) -> dict[str, object]:
    uri = "data:image/png;base64," + base64.b64encode(sample_image()).decode("ascii")
    response = client.post(
        _url(endpoint, "/v1/embeddings"),
        json={
            "model": NAFLEX_MODEL,
            "input": [uri],
            "max_num_patches": NAFLEX_PATCH_BUDGET,
        },
    )
    response.raise_for_status()
    result = _object(response.json(), "SigLIP2 response")
    data = _list(result.get("data"), "SigLIP2 data")
    if len(data) != 1 or not isinstance(data[0], dict):
        raise AssertionError("SigLIP2 response does not contain one embedding")
    vector = _list(data[0].get("embedding"), "SigLIP2 embedding")
    if len(vector) != VECTOR_DIMENSION:
        raise AssertionError(f"SigLIP2 vector dimension is {len(vector)}, expected {VECTOR_DIMENSION}")
    if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in vector):
        raise AssertionError("SigLIP2 vector contains a non-finite value")
    norm = math.sqrt(sum(float(value) * float(value) for value in vector))
    if abs(norm - 1.0) > 0.01:
        raise AssertionError(f"SigLIP2 vector norm is {norm}")
    return {
        "model": NAFLEX_MODEL,
        "max_num_patches": NAFLEX_PATCH_BUDGET,
        "dimension": len(vector),
        "norm": norm,
    }


def check_qwen(
    client: httpx.Client,
    endpoint: str,
    model: str,
    api_key: str | None,
) -> dict[str, object]:
    image_uri = "data:image/png;base64," + base64.b64encode(sample_image()).decode("ascii")
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    response = client.post(
        _url(endpoint, "/chat/completions"),
        headers=headers,
        json={
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_uri}},
                        {
                            "type": "text",
                            "text": (
                                "Return only this JSON object: "
                                '{"status":"ready"}. Do not use Markdown.'
                            ),
                        },
                    ],
                }
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
            "max_tokens": 64,
            "stream": False,
        },
    )
    response.raise_for_status()
    result = _object(response.json(), "Qwen response")
    choices = _list(result.get("choices"), "Qwen choices")
    if not choices or not isinstance(choices[0], dict):
        raise AssertionError("Qwen response does not contain a choice")
    message = _object(choices[0].get("message"), "Qwen message")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise AssertionError("Qwen response does not contain assistant text")
    try:
        parsed = _object(json.loads(content), "Qwen assistant content")
    except json.JSONDecodeError as exc:
        raise AssertionError("Qwen assistant content is not valid JSON") from exc
    if parsed.get("status") != "ready":
        raise AssertionError("Qwen assistant content does not contain status=ready")
    return {"model": model, "content": parsed}


def check_shieldgemma(client: httpx.Client, endpoint: str) -> dict[str, object]:
    policies = {"dangerous", "sexual", "violence"}
    response = client.post(
        _url(endpoint, "/classify"),
        files={"image": ("bottle.png", sample_image(), "image/png")},
        data={"policies": ",".join(sorted(policies)), "threshold": "0.5"},
    )
    response.raise_for_status()
    result = _object(response.json(), "ShieldGemma response")
    scores = _object(result.get("scores"), "ShieldGemma scores")
    if set(scores) != policies:
        raise AssertionError("ShieldGemma response has unexpected policy keys")
    if not all(
        isinstance(value, (int, float)) and math.isfinite(value) and 0.0 <= value <= 1.0
        for value in scores.values()
    ):
        raise AssertionError("ShieldGemma response has an invalid policy score")
    _list(result.get("flagged"), "ShieldGemma flagged")
    return {"scores": scores, "flagged": result["flagged"]}


def _run_check(function: Callable[[], dict[str, object]]) -> dict[str, object]:
    started = time.perf_counter()
    try:
        details = function()
    except Exception as exc:
        return {
            "status": "failed",
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "error": f"{type(exc).__name__}: {exc}",
        }
    return {
        "status": "ok",
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "details": details,
    }


def run_checks(client: httpx.Client, settings: Settings) -> dict[str, object]:
    configured: list[tuple[str, str | None, Callable[[str], dict[str, object]], bool]] = [
        ("qr-scanner", settings.qr_scanner_endpoint, lambda url: check_qr(client, url), True),
        ("sam3", settings.sam3_endpoint, lambda url: check_sam3(client, url), True),
        ("siglip2-naflex-512", settings.siglip2_endpoint, lambda url: check_siglip2(client, url), True),
        (
            "qwen",
            settings.vlm_endpoint,
            lambda url: check_qwen(client, url, settings.vlm_model or "", settings.vlm_api_key),
            True,
        ),
        (
            "shieldgemma",
            settings.shieldgemma_endpoint,
            lambda url: check_shieldgemma(client, url),
            False,
        ),
    ]
    checks: dict[str, dict[str, object]] = {}
    for name, endpoint, function, required in configured:
        if not endpoint:
            checks[name] = (
                {"status": "failed", "error": "required endpoint is not configured"}
                if required
                else {"status": "skipped", "reason": "optional endpoint is not configured"}
            )
            continue
        if name == "qwen" and not settings.vlm_model:
            checks[name] = {"status": "failed", "error": "VLM_MODEL is not configured"}
            continue
        checks[name] = _run_check(lambda endpoint=endpoint, function=function: function(endpoint))
    failed = [name for name, result in checks.items() if result["status"] == "failed"]
    return {"status": "failed" if failed else "ok", "failed": failed, "checks": checks}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qr-scanner-endpoint", default=os.environ.get("QR_SCANNER_ENDPOINT"))
    parser.add_argument("--sam3-endpoint", default=os.environ.get("SAM3_ENDPOINT"))
    parser.add_argument("--siglip2-endpoint", default=os.environ.get("SIGLIP2_ENDPOINT"))
    parser.add_argument("--vlm-endpoint", default=os.environ.get("VLM_ENDPOINT"))
    parser.add_argument("--vlm-model", default=os.environ.get("VLM_MODEL"))
    parser.add_argument("--shieldgemma-endpoint", default=os.environ.get("SHIELDGEMMA_ENDPOINT"))
    parser.add_argument("--timeout", type=float, default=900.0)
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    settings = Settings(
        qr_scanner_endpoint=arguments.qr_scanner_endpoint,
        sam3_endpoint=arguments.sam3_endpoint,
        siglip2_endpoint=arguments.siglip2_endpoint,
        vlm_endpoint=arguments.vlm_endpoint,
        vlm_model=arguments.vlm_model,
        shieldgemma_endpoint=arguments.shieldgemma_endpoint,
        vlm_api_key=os.environ.get("VLM_API_KEY"),
    )
    with httpx.Client(timeout=arguments.timeout) as client:
        report = run_checks(client, settings)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
