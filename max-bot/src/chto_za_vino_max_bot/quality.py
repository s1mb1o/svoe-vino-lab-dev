from __future__ import annotations

import base64
import binascii
import io
import json
import math
from dataclasses import dataclass

import httpx
from PIL import Image, ImageOps, UnidentifiedImageError

PROMPTS = ("wine bottle", "label", "wine bottle label")
SAM3_THRESHOLD = 0.35
MAX_INSTANCES = 64
MAX_MASK_BYTES = 8 * 1024 * 1024
BOX_BOUNDARY_TOLERANCE_RATIO = 0.01


class QualityUnavailable(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class QualityThresholds:
    blur_min_variance: float
    glare_max_ratio: float
    bottle_min_area_ratio: float
    label_min_area_ratio: float


@dataclass(frozen=True, slots=True)
class QualityResult:
    acceptable: bool
    issues: tuple[str, ...]
    blur_variance: float
    glare_ratio: float
    bottle_area_ratio: float
    label_area_ratio: float
    segments: tuple[Segment, ...] = ()
    selected_bottle: Segment | None = None
    selected_label: Segment | None = None


@dataclass(frozen=True, slots=True)
class Segment:
    label: str
    score: float
    box: tuple[int, int, int, int]
    mask_png: bytes | None = None
    mask_area: int | None = None

    @property
    def area(self) -> int:
        return (self.box[2] - self.box[0]) * (self.box[3] - self.box[1])


def _box(value: object, width: int, height: int) -> tuple[int, int, int, int] | None:
    if not isinstance(value, list) or len(value) != 4:
        return None
    try:
        numbers = [float(item) for item in value]
    except (TypeError, ValueError):
        return None
    if not all(math.isfinite(item) for item in numbers):
        return None
    left, top, right, bottom = numbers
    tolerance = max(2.0, max(width, height) * BOX_BOUNDARY_TOLERANCE_RATIO)
    if (
        left < -tolerance
        or top < -tolerance
        or right > width + tolerance
        or bottom > height + tolerance
    ):
        return None
    left = max(0.0, min(float(width), left))
    top = max(0.0, min(float(height), top))
    right = max(0.0, min(float(width), right))
    bottom = max(0.0, min(float(height), bottom))
    if right <= left or bottom <= top:
        return None
    return math.floor(left), math.floor(top), math.ceil(right), math.ceil(bottom)


def _mask_png(value: object, expected_size: tuple[int, int]) -> tuple[bytes, int] | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > MAX_MASK_BYTES * 2:
        raise QualityUnavailable("SAM3 mask is invalid")
    try:
        raw = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise QualityUnavailable("SAM3 mask is invalid") from exc
    if not raw or len(raw) > MAX_MASK_BYTES:
        raise QualityUnavailable("SAM3 mask is invalid")
    try:
        with Image.open(io.BytesIO(raw)) as source:
            if source.format != "PNG":
                raise QualityUnavailable("SAM3 mask format is invalid")
            source.load()
            if source.size != expected_size:
                raise QualityUnavailable("SAM3 mask dimensions are invalid")
            gray = source.convert("L")
    except QualityUnavailable:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise QualityUnavailable("SAM3 mask is invalid") from exc
    binary = gray.point([0 if value < 128 else 255 for value in range(256)], mode="1")
    histogram = binary.histogram()
    area = histogram[255] if len(histogram) > 255 else 0
    output = io.BytesIO()
    binary.save(output, format="PNG", optimize=True)
    return output.getvalue(), area


def parse_sam3_response(
    value: object,
    expected_size: tuple[int, int],
    *,
    require_masks: bool = False,
) -> tuple[Segment, ...]:
    if not isinstance(value, dict):
        raise QualityUnavailable("SAM3 response is not an object")
    width, height = expected_size
    if value.get("width") != width or value.get("height") != height:
        raise QualityUnavailable("SAM3 response dimensions are invalid")
    instances = value.get("instances")
    if not isinstance(instances, list) or len(instances) > MAX_INSTANCES:
        raise QualityUnavailable("SAM3 response instances are invalid")
    segments: list[Segment] = []
    for item in instances:
        if not isinstance(item, dict):
            raise QualityUnavailable("SAM3 instance is not an object")
        label = item.get("label")
        score = item.get("score")
        box = _box(item.get("box"), width, height)
        mask = _mask_png(item.get("mask_png_b64"), expected_size)
        if (
            label not in PROMPTS
            or not isinstance(score, (int, float))
            or isinstance(score, bool)
            or not math.isfinite(float(score))
            or not 0 <= float(score) <= 1
            or box is None
        ):
            raise QualityUnavailable("SAM3 instance is invalid")
        if require_masks and mask is None:
            raise QualityUnavailable("SAM3 mask is missing")
        if float(score) >= SAM3_THRESHOLD:
            segments.append(
                Segment(
                    str(label),
                    float(score),
                    box,
                    mask[0] if mask is not None else None,
                    mask[1] if mask is not None else None,
                )
            )
    return tuple(segments)


def _intersection_share(inner: Segment, outer: Segment) -> float:
    intersection = max(0, min(inner.box[2], outer.box[2]) - max(inner.box[0], outer.box[0])) * max(
        0,
        min(inner.box[3], outer.box[3]) - max(inner.box[1], outer.box[1]),
    )
    return intersection / inner.area if inner.area else 0.0


def laplacian_variance(image: Image.Image) -> float:
    gray = image.convert("L")
    if max(gray.size) > 1024:
        gray.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
    width, height = gray.size
    if width < 3 or height < 3:
        return 0.0
    pixels = gray.load()
    total = 0.0
    total_squared = 0.0
    count = 0
    step = 2 if width * height > 500_000 else 1
    for y in range(1, height - 1, step):
        for x in range(1, width - 1, step):
            value = (
                4 * pixels[x, y]
                - pixels[x - 1, y]
                - pixels[x + 1, y]
                - pixels[x, y - 1]
                - pixels[x, y + 1]
            )
            total += value
            total_squared += value * value
            count += 1
    mean = total / count
    return max(0.0, total_squared / count - mean * mean)


def glare_ratio(image: Image.Image) -> float:
    rgb = image.convert("RGB")
    if max(rgb.size) > 512:
        rgb.thumbnail((512, 512), Image.Resampling.LANCZOS)
    pixels = list(rgb.get_flattened_data())
    if not pixels:
        return 0.0
    clipped = sum(
        1
        for red, green, blue in pixels
        if min(red, green, blue) >= 253 and max(red, green, blue) - min(red, green, blue) <= 4
    )
    return clipped / len(pixels)


def evaluate_quality(
    image: Image.Image,
    segments: tuple[Segment, ...],
    thresholds: QualityThresholds,
) -> QualityResult:
    image_area = image.width * image.height
    bottles = [segment for segment in segments if segment.label == "wine bottle"]
    bottle = max(bottles, key=lambda item: (item.area, item.score), default=None)
    bottle_ratio = bottle.area / image_area if bottle else 0.0

    labels = [segment for segment in segments if segment.label != "wine bottle"]
    if bottle is not None:
        labels = [
            label
            for label in labels
            if label.area < bottle.area * 0.7 and _intersection_share(label, bottle) >= 0.5
        ]
    label = max(labels, key=lambda item: (item.area, item.score), default=None)
    label_ratio = label.area / image_area if label else 0.0
    focus = image.crop(label.box) if label is not None else image
    blur = laplacian_variance(focus)
    glare = glare_ratio(focus)

    issues: list[str] = []
    if bottle is None or bottle_ratio < thresholds.bottle_min_area_ratio:
        issues.append("bottle_missing")
    if label is None or label_ratio < thresholds.label_min_area_ratio:
        issues.append("label_tiny")
    if blur < thresholds.blur_min_variance:
        issues.append("blur")
    if glare > thresholds.glare_max_ratio:
        issues.append("glare")
    return QualityResult(
        acceptable=not issues,
        issues=tuple(issues),
        blur_variance=blur,
        glare_ratio=glare,
        bottle_area_ratio=bottle_ratio,
        label_area_ratio=label_ratio,
        segments=segments,
        selected_bottle=bottle,
        selected_label=label,
    )


class QualityInspector:
    def __init__(
        self,
        endpoint: str,
        client: httpx.AsyncClient,
        thresholds: QualityThresholds,
    ) -> None:
        self._endpoint = f"{endpoint.rstrip('/')}/segment_multi"
        self._client = client
        self._thresholds = thresholds

    async def inspect(self, jpeg: bytes) -> QualityResult:
        try:
            with Image.open(io.BytesIO(jpeg)) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
                image.load()
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise QualityUnavailable("quality image is invalid") from exc
        try:
            response = await self._client.post(
                self._endpoint,
                files={"image": ("quality.jpg", jpeg, "image/jpeg")},
                data={
                    "texts": ", ".join(PROMPTS),
                    "threshold": str(SAM3_THRESHOLD),
                    "return_masks": "true",
                },
                timeout=120,
            )
            response.raise_for_status()
            segments = parse_sam3_response(
                response.json(),
                image.size,
                require_masks=True,
            )
        except QualityUnavailable:
            raise
        except (httpx.HTTPError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise QualityUnavailable("quality service is unavailable") from exc
        return evaluate_quality(image, segments, self._thresholds)
