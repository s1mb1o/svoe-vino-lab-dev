"""Portable QR and barcode scanner service.

This service uses the maintained ``zxing-cpp`` Python wheel.
It keeps the response fields that the GX10 ``qr-scanner`` clients use.
The portable service does not use the optional BoofCV, super-resolution, SAM3,
or VLM fallbacks of the larger GX10 service.
"""

from __future__ import annotations

import argparse
import io
import time
from importlib.metadata import version
from threading import Lock
from typing import Any

import numpy as np
import uvicorn
import zxingcpp
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from PIL import Image, ImageOps
from pydantic import BaseModel, Field


scan_lock = Lock()


class EngineRun(BaseModel):
    name: str
    count: int
    elapsed_ms: float
    error: str | None


class Instance(BaseModel):
    text: str
    format: str
    engine: str
    found_by: list[str]
    quad: list[list[float]]
    box: list[float]
    area: float
    details: dict[str, Any]
    printed: None = Field(default=None)


class ScanResponse(BaseModel):
    count: int
    width: int
    height: int
    engine: str
    elapsed_ms: float
    engines: list[EngineRun]
    instances: list[Instance]


app = FastAPI(
    title="Portable QR scanner",
    version="1.0.0",
    description=(
        "Decode QR codes and common one-dimensional and two-dimensional barcodes. "
        "The portable bootstrap uses zxing-cpp."
    ),
)


def _format_name(value: object) -> str:
    name = str(value)
    return "QR Code" if name in {"QRCode", "QRCODE", "QR_CODE"} else name


def _quad(position: object) -> list[list[float]]:
    points = (
        position.top_left,
        position.top_right,
        position.bottom_right,
        position.bottom_left,
    )
    return [[round(float(point.x), 1), round(float(point.y), 1)] for point in points]


def _area(quad: list[list[float]]) -> float:
    return round(
        0.5
        * abs(
            sum(
                quad[index][0] * quad[index - 1][1]
                - quad[index - 1][0] * quad[index][1]
                for index in range(len(quad))
            )
        ),
        1,
    )


def _instance(result: object) -> dict[str, Any]:
    quad = _quad(result.position)
    xs = [point[0] for point in quad]
    ys = [point[1] for point in quad]
    details: dict[str, Any] = {
        "symbology": str(getattr(result, "symbology", "")),
        "symbology_identifier": str(getattr(result, "symbology_identifier", "")),
        "content_type": str(getattr(result, "content_type", "")).split(".")[-1],
        "orientation": int(getattr(result, "orientation", 0)),
    }
    error_correction = getattr(result, "ec_level", "")
    if error_correction:
        details["ec_level"] = str(error_correction)
    return {
        "text": result.text,
        "format": _format_name(result.format),
        "engine": "zxing-cpp",
        "found_by": ["zxing-cpp"],
        "quad": quad,
        "box": [min(xs), min(ys), max(xs), max(ys)],
        "area": _area(quad),
        "details": details,
        "printed": None,
    }


def _image(data: bytes) -> tuple[np.ndarray, int, int]:
    try:
        image = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))
        if image.mode in {"RGBA", "LA", "PA"} or (
            image.mode == "P" and "transparency" in image.info
        ):
            background = Image.new("RGBA", image.size, (255, 255, 255, 255))
            image = Image.alpha_composite(background, image.convert("RGBA"))
        image = image.convert("L")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"bad image: {exc}") from exc
    return np.asarray(image), image.width, image.height


@app.get("/")
def info() -> dict[str, object]:
    return {"service": "qr-scanner", "engine": "zxing-cpp", "docs": "/docs"}


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "device": "cpu",
        "workers": 1,
        "engines": {"zxing-cpp": version("zxing-cpp")},
        "opencv": "not-installed",
        "wechat_models": False,
    }


@app.post("/scan", response_model=ScanResponse)
def scan(
    image: UploadFile = File(...),
    engine: str = Form("auto"),
) -> dict[str, object]:
    requested = engine.strip().lower()
    if requested not in {"auto", "zxing-cpp"}:
        raise HTTPException(
            status_code=400,
            detail="the portable service supports engine=auto or engine=zxing-cpp",
        )
    pixels, width, height = _image(image.file.read())
    started = time.perf_counter()
    try:
        with scan_lock:
            results = zxingcpp.read_barcodes(pixels)
        instances = [_instance(result) for result in results if result.valid]
        error = None
    except Exception as exc:
        instances = []
        error = str(exc)
    elapsed = round(1000 * (time.perf_counter() - started), 1)
    if error:
        raise HTTPException(status_code=500, detail=f"zxing-cpp: {error}")
    return {
        "count": len(instances),
        "width": width,
        "height": height,
        "engine": requested,
        "elapsed_ms": elapsed,
        "engines": [
            {
                "name": "zxing-cpp",
                "count": len(instances),
                "elapsed_ms": elapsed,
                "error": None,
            }
        ],
        "instances": instances,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    arguments = parser.parse_args()
    uvicorn.run(app, host=arguments.host, port=arguments.port, log_level="info")

