from __future__ import annotations

import html
import io
from urllib.parse import urlparse

import httpx
from PIL import Image, ImageChops, ImageFilter, ImageOps, UnidentifiedImageError

from .profile import LEGAL_NOTICE
from .wine import Wine


class CatalogImageUnavailable(RuntimeError):
    pass


RESULT_CANVAS_SIZE = (1024, 1280)
RESULT_CANVAS_PADDING = 0.05
ALPHA_FOREGROUND_THRESHOLD = 16
WHITE_FOREGROUND_THRESHOLD = 18


def _caption_value(value: str | None, limit: int) -> str:
    if not value:
        return "нет данных"
    normalized = " ".join(value.split())
    if len(normalized) > limit:
        normalized = normalized[: limit - 1].rstrip() + "…"
    return html.escape(normalized)


def format_result_caption(wine: Wine) -> str:
    color_values = []
    for value in (wine.category, wine.color):
        if value and value.casefold() not in {item.casefold() for item in color_values}:
            color_values.append(value)
    color = " · ".join(color_values) if color_values else None
    return (
        "Похоже, это:\n\n"
        f"<b>{_caption_value(wine.name, 140)}</b>\n\n"
        f"🍷 <b>Цвет:</b> {_caption_value(color, 120)}\n"
        f"🍬 <b>Сахар:</b> {_caption_value(wine.sugar, 60)}\n"
        f"🍇 <b>Виноград:</b> {_caption_value(wine.grapes, 180)}\n\n"
        f'<a href="{html.escape(wine.page_url, quote=True)}">Открыть страницу вина</a>\n\n'
        "Результат может быть неточным.\n\n"
        f"{LEGAL_NOTICE}"
    )


def normalize_result_photo(body: bytes, max_side: int = 1280) -> bytes:
    try:
        with Image.open(io.BytesIO(body)) as source:
            source.verify()
        with Image.open(io.BytesIO(body)) as source:
            image = ImageOps.exif_transpose(source)
            if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
                rgba = image.convert("RGBA")
                background = Image.new("RGB", rgba.size, "white")
                background.paste(rgba, mask=rgba.getchannel("A"))
                image = background
            else:
                image = image.convert("RGB")
            image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=90, optimize=True)
            return output.getvalue()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise CatalogImageUnavailable("result image is invalid") from exc


def _foreground_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    if "A" in image.getbands():
        alpha = image.getchannel("A")
        if alpha.getextrema()[0] < 255:
            mask = alpha.point(
                lambda value: 255 if value >= ALPHA_FOREGROUND_THRESHOLD else 0
            )
            if bbox := mask.getbbox():
                return bbox

    rgb = image.convert("RGB")
    difference = ImageChops.difference(rgb, Image.new("RGB", rgb.size, "white"))
    red, green, blue = difference.split()
    maximum = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    mask = maximum.point(
        lambda value: 255 if value >= WHITE_FOREGROUND_THRESHOLD else 0
    ).filter(ImageFilter.MedianFilter(5))
    return mask.getbbox() or (0, 0, image.width, image.height)


def _expand_bbox(
    bbox: tuple[int, int, int, int],
    image_size: tuple[int, int],
) -> tuple[int, int, int, int]:
    left, top, right, bottom = bbox
    margin = max(2, round(max(right - left, bottom - top) * 0.01))
    return (
        max(0, left - margin),
        max(0, top - margin),
        min(image_size[0], right + margin),
        min(image_size[1], bottom + margin),
    )


def prepare_catalog_result_photo(body: bytes) -> bytes:
    try:
        with Image.open(io.BytesIO(body)) as source:
            source.verify()
        with Image.open(io.BytesIO(body)) as source:
            image = ImageOps.exif_transpose(source).convert("RGBA")
            bbox = _expand_bbox(_foreground_bbox(image), image.size)
            foreground = image.crop(bbox)

            opaque = Image.new("RGB", foreground.size, "white")
            opaque.paste(foreground, mask=foreground.getchannel("A"))

            canvas_width, canvas_height = RESULT_CANVAS_SIZE
            inner_width = round(canvas_width * (1 - 2 * RESULT_CANVAS_PADDING))
            inner_height = round(canvas_height * (1 - 2 * RESULT_CANVAS_PADDING))
            scale = min(inner_width / opaque.width, inner_height / opaque.height)
            fitted_size = (
                max(1, round(opaque.width * scale)),
                max(1, round(opaque.height * scale)),
            )
            fitted = opaque.resize(fitted_size, Image.Resampling.LANCZOS)

            canvas = Image.new("RGB", RESULT_CANVAS_SIZE, "white")
            position = (
                (canvas_width - fitted.width) // 2,
                (canvas_height - fitted.height) // 2,
            )
            canvas.paste(fitted, position)

            output = io.BytesIO()
            canvas.save(output, format="JPEG", quality=90, optimize=True)
            return output.getvalue()
    except (UnidentifiedImageError, OSError, ValueError, ZeroDivisionError) as exc:
        raise CatalogImageUnavailable("result image is invalid") from exc


class CatalogImageLoader:
    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        allowed_host: str = "api.vino-svoe.ru",
        max_bytes: int = 15 * 1024 * 1024,
    ) -> None:
        self._client = client
        self._allowed_host = allowed_host
        self._max_bytes = max_bytes

    async def fetch(self, url: str) -> bytes:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != self._allowed_host:
            raise CatalogImageUnavailable("catalogue image URL is not allowed")
        try:
            async with self._client.stream("GET", url, timeout=30) as response:
                response.raise_for_status()
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > self._max_bytes:
                    raise CatalogImageUnavailable("catalogue image is too large")
                chunks: list[bytes] = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > self._max_bytes:
                        raise CatalogImageUnavailable("catalogue image is too large")
                    chunks.append(chunk)
        except CatalogImageUnavailable:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            raise CatalogImageUnavailable("catalogue image is unavailable") from exc
        return prepare_catalog_result_photo(b"".join(chunks))
