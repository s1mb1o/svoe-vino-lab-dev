from __future__ import annotations

import asyncio
import base64
import io
import json

import httpx
from PIL import Image, ImageDraw

from .matcher import Matcher, is_confident
from .moderation import Moderator, make_moderation_jpeg
from .quality import QualityInspector, QualityThresholds

BASE_URL = "http://host-demo.invalid"


def _demo_image() -> bytes:
    image = Image.new("RGB", (200, 300), "#6f777f")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((30, 10, 170, 290), radius=20, fill="#5b1425", outline="white", width=3)
    draw.rectangle((55, 115, 145, 195), fill="#e8d8ad", outline="#3a2a20", width=3)
    draw.line((65, 140, 135, 140), fill="#3a2a20", width=3)
    draw.line((65, 160, 125, 160), fill="#3a2a20", width=3)
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=92)
    return output.getvalue()


def _mask(box: tuple[int, int, int, int]) -> str:
    image = Image.new("1", (200, 300))
    ImageDraw.Draw(image).rectangle(box, fill=1)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return base64.b64encode(output.getvalue()).decode("ascii")


def _wine(slug: str, name: str) -> dict[str, object]:
    return {
        "name": name,
        "page_url": f"https://vino-svoe.ru/wines/{slug}",
        "producer": "Демонстрационная винодельня",
        "category": "Тихое",
        "color": "Красное",
        "grapes": "Каберне Совиньон",
        "sugar": "Сухое",
        "image_url": None,
        "qr_urls": [],
    }


def _respond(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/moderate":
        return httpx.Response(
            200,
            json={
                "model": "shieldgemma-2-4b-it",
                "threshold": 0.5,
                "scores": {"dangerous": 0.01, "sexual": 0.02, "violence": 0.01},
                "flagged": [],
            },
        )
    if request.url.path == "/sam3/segment_multi":
        return httpx.Response(
            200,
            json={
                "width": 200,
                "height": 300,
                "instances": [
                    {
                        "label": "wine bottle",
                        "score": 0.97,
                        "box": [30, 10, 170, 290],
                        "mask_png_b64": _mask((30, 10, 170, 290)),
                    },
                    {
                        "label": "label",
                        "score": 0.94,
                        "box": [55, 115, 145, 195],
                        "mask_png_b64": _mask((55, 115, 145, 195)),
                    },
                ],
            },
        )
    if request.url.path == "/v1/match":
        candidates = [
            ("demo-wine", "Демонстрационное вино", 0.92),
            ("second-wine", "Второе вино", 0.77),
            ("third-wine", "Третье вино", 0.70),
            ("fourth-wine", "Четвёртое вино", 0.64),
        ]
        return httpx.Response(
            200,
            json={
                "pipeline": "host-demo",
                "candidates": [
                    {
                        "rank": rank,
                        "slug": slug,
                        "score": score,
                        "wine": _wine(slug, name),
                    }
                    for rank, (slug, name, score) in enumerate(candidates, start=1)
                ],
            },
        )
    return httpx.Response(404)


async def run_demo() -> dict[str, object]:
    body = _demo_image()
    async with httpx.AsyncClient(transport=httpx.MockTransport(_respond)) as client:
        moderation_jpeg = make_moderation_jpeg(body)
        moderation = await Moderator(f"{BASE_URL}/moderate", client).classify(
            moderation_jpeg
        )
        quality = await QualityInspector(
            f"{BASE_URL}/sam3",
            client,
            QualityThresholds(80.0, 0.20, 0.10, 0.015),
        ).inspect(moderation_jpeg)
        recognition = await Matcher(f"{BASE_URL}/v1/match", client).recognize(body)
    confident = is_confident(recognition, min_score=0.70, min_margin=0.015)
    return {
        "demo": "self-contained",
        "moderation": {"performed": moderation.performed, "safe": moderation.safe},
        "quality": {"acceptable": quality.acceptable, "issues": list(quality.issues)},
        "recognition": {
            "confident": confident,
            "pipeline": recognition.pipeline,
            "wine": recognition.top.wine.name,
            "page_url": recognition.top.wine.page_url,
            "score": recognition.top.score,
            "margin": recognition.margin,
        },
    }


def main() -> None:
    print(json.dumps(asyncio.run(run_demo()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
