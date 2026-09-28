from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageOps, UnidentifiedImageError

from .quality import QualityResult, Segment
from .storage import ArtifactStore, ArtifactWrite


@dataclass(frozen=True, slots=True)
class GeneratedArtifact:
    artifact_key: str
    step: str
    title: str
    description: str
    mime_type: str
    body: bytes
    width: int
    height: int
    ordinal: int
    metadata: dict[str, object]
    exposure: str = "safe"


COLORS = ("#e53935", "#1e88e5", "#43a047", "#f9a825", "#8e24aa", "#00acc1")
CENSORED_SAMPLE_MAX = 24
CENSORED_OUTPUT_MAX = 768
CENSORED_BLUR_RADIUS = 18
IMAGE_MIME_TYPES = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


def _open_rgb(body: bytes) -> Image.Image:
    try:
        with Image.open(io.BytesIO(body)) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.load()
            return image
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError("artifact image is invalid") from exc


def _open_matcher_input(body: bytes) -> tuple[Image.Image, str]:
    try:
        with Image.open(io.BytesIO(body)) as source:
            mime_type = IMAGE_MIME_TYPES.get(source.format or "")
            if mime_type is None:
                raise ValueError("matcher input image format is unsupported")
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.load()
            return image, mime_type
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError("artifact image is invalid") from exc


def _encode(image: Image.Image, mime_type: str) -> bytes:
    output = io.BytesIO()
    if mime_type == "image/jpeg":
        image.convert("RGB").save(output, format="JPEG", quality=92, optimize=True)
    elif mime_type == "image/png":
        image.save(output, format="PNG", optimize=True)
    else:
        raise ValueError("artifact MIME type is invalid")
    return output.getvalue()


def base_artifacts(matcher_input: bytes, moderation_jpeg: bytes) -> list[GeneratedArtifact]:
    matcher_image, matcher_mime_type = _open_matcher_input(matcher_input)
    moderation_image = _open_rgb(moderation_jpeg)
    return [
        GeneratedArtifact(
            "matcher_input",
            "input",
            "Вход распознавания",
            "Точное изображение, переданное в wine matcher.",
            matcher_mime_type,
            matcher_input,
            matcher_image.width,
            matcher_image.height,
            10,
            {"byte_exact": True},
        ),
        GeneratedArtifact(
            "moderation_input",
            "moderation",
            "Вход модерации и SAM3",
            "Нормализованный JPEG после EXIF-поворота и ограничения размера.",
            "image/jpeg",
            moderation_jpeg,
            moderation_image.width,
            moderation_image.height,
            20,
            {},
        ),
    ]


def _mask_image(segment: Segment, size: tuple[int, int]) -> Image.Image:
    if segment.mask_png is None:
        raise ValueError("segment mask is missing")
    with Image.open(io.BytesIO(segment.mask_png)) as source:
        source.load()
        if source.size != size:
            raise ValueError("segment mask dimensions are invalid")
        return source.convert("L")


def _segment_metadata(segment: Segment) -> dict[str, object]:
    return {
        "prompt": segment.label,
        "score": round(segment.score, 6),
        "box": list(segment.box),
        "mask_area": segment.mask_area,
    }


def _overlay(image: Image.Image, segments: tuple[Segment, ...]) -> Image.Image:
    result = image.convert("RGBA")
    for index, segment in enumerate(segments):
        color = ImageColor.getrgb(COLORS[index % len(COLORS)])
        mask = _mask_image(segment, image.size)
        layer = Image.new("RGBA", image.size, (*color, 0))
        layer.putalpha(mask.point(lambda value: 92 if value >= 128 else 0))
        result = Image.alpha_composite(result, layer)
    draw = ImageDraw.Draw(result)
    stroke = max(2, round(max(image.size) / 350))
    for index, segment in enumerate(segments):
        color = COLORS[index % len(COLORS)]
        draw.rectangle(segment.box, outline=color, width=stroke)
        label = f"{index + 1}. {segment.label} {segment.score:.3f}"
        left, top, _, _ = segment.box
        text_box = draw.textbbox((left, top), label, stroke_width=1)
        height = text_box[3] - text_box[1] + 6
        label_top = max(0, top - height)
        label_right = min(image.width, left + text_box[2] - text_box[0] + 8)
        draw.rectangle((left, label_top, label_right, top), fill="#111111cc")
        draw.text((left + 4, label_top + 2), label, fill="white", stroke_width=1)
    return result


def _selection_artifacts(
    image: Image.Image,
    segment: Segment | None,
    *,
    prefix: str,
    title: str,
    ordinal: int,
) -> list[GeneratedArtifact]:
    if segment is None:
        return []
    crop = image.crop(segment.box)
    mask = _mask_image(segment, image.size).crop(segment.box)
    cutout = crop.convert("RGBA")
    cutout.putalpha(mask)
    metadata = _segment_metadata(segment)
    return [
        GeneratedArtifact(
            f"{prefix}_box_crop",
            "quality",
            f"{title}: box crop",
            "Кроп по выбранному SAM3 box.",
            "image/jpeg",
            _encode(crop, "image/jpeg"),
            crop.width,
            crop.height,
            ordinal,
            metadata,
        ),
        GeneratedArtifact(
            f"{prefix}_masked_cutout",
            "quality",
            f"{title}: masked cutout",
            "Кроп с прозрачностью по выбранной SAM3 mask.",
            "image/png",
            _encode(cutout, "image/png"),
            cutout.width,
            cutout.height,
            ordinal + 1,
            metadata,
        ),
    ]


def quality_artifacts(
    moderation_jpeg: bytes,
    quality: QualityResult,
) -> list[GeneratedArtifact]:
    image = _open_rgb(moderation_jpeg)
    values: list[GeneratedArtifact] = []
    if quality.segments:
        overlay = _overlay(image, quality.segments)
        values.append(
            GeneratedArtifact(
                "sam3_overlay",
                "quality",
                "SAM3 overlay",
                "Все принятые маски, box, prompt и score.",
                "image/png",
                _encode(overlay, "image/png"),
                image.width,
                image.height,
                30,
                {"segments": len(quality.segments)},
            )
        )
    for index, segment in enumerate(quality.segments, start=1):
        if segment.mask_png is None:
            continue
        values.append(
            GeneratedArtifact(
                f"sam3_mask_{index:02d}",
                "quality",
                f"SAM3 mask {index}",
                f"Маска для prompt «{segment.label}».",
                "image/png",
                segment.mask_png,
                image.width,
                image.height,
                40 + index,
                _segment_metadata(segment),
            )
        )
    values.extend(
        _selection_artifacts(
            image,
            quality.selected_bottle,
            prefix="selected_bottle",
            title="Выбранная бутылка",
            ordinal=120,
        )
    )
    values.extend(
        _selection_artifacts(
            image,
            quality.selected_label,
            prefix="selected_label",
            title="Выбранная этикетка",
            ordinal=130,
        )
    )
    return values


def result_artifact(body: bytes) -> GeneratedArtifact:
    image = _open_rgb(body)
    return GeneratedArtifact(
        "telegram_result",
        "result",
        "Результат Telegram",
        "Изображение, подготовленное для ответа пользователю.",
        "image/jpeg",
        body,
        image.width,
        image.height,
        200,
        {},
    )


def censored_artifact(body: bytes) -> GeneratedArtifact:
    source = _open_rgb(body)
    output_size = source.size
    if max(output_size) > CENSORED_OUTPUT_MAX:
        scale = CENSORED_OUTPUT_MAX / max(output_size)
        output_size = (
            max(1, round(output_size[0] * scale)),
            max(1, round(output_size[1] * scale)),
        )
    sample_size = output_size
    if max(sample_size) > CENSORED_SAMPLE_MAX:
        scale = CENSORED_SAMPLE_MAX / max(sample_size)
        sample_size = (
            max(1, round(sample_size[0] * scale)),
            max(1, round(sample_size[1] * scale)),
        )
    reduced = source.resize(sample_size, Image.Resampling.BOX)
    preview = reduced.resize(output_size, Image.Resampling.BILINEAR)
    preview = preview.filter(ImageFilter.GaussianBlur(CENSORED_BLUR_RADIUS))
    return GeneratedArtifact(
        "censored_preview",
        "censored",
        "Цензурированное изображение",
        "Необратимо уменьшенный и сильно размытый preview карантинного изображения.",
        "image/jpeg",
        _encode(preview, "image/jpeg"),
        preview.width,
        preview.height,
        10,
        {
            "sample_max": CENSORED_SAMPLE_MAX,
            "output_max": CENSORED_OUTPUT_MAX,
            "blur_radius": CENSORED_BLUR_RADIUS,
        },
        "censored",
    )


def persist_artifacts(
    store: ArtifactStore,
    *,
    request_id: str,
    received_at: int,
    artifacts: list[GeneratedArtifact],
) -> list[ArtifactWrite]:
    rows: list[ArtifactWrite] = []
    for item in artifacts:
        relative_path = store.save(
            request_id,
            received_at,
            item.artifact_key,
            item.mime_type,
            item.body,
        )
        rows.append(
            ArtifactWrite(
                artifact_key=item.artifact_key,
                step=item.step,
                title=item.title,
                description=item.description,
                mime_type=item.mime_type,
                relative_path=relative_path,
                width=item.width,
                height=item.height,
                ordinal=item.ordinal,
                metadata=item.metadata,
                exposure=item.exposure,
            )
        )
    return rows
