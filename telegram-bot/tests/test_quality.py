import base64
import io

import httpx
import pytest
from PIL import Image, ImageDraw, ImageFilter

from chto_za_vino_bot.quality import (
    QualityInspector,
    QualityThresholds,
    QualityUnavailable,
    Segment,
    evaluate_quality,
    parse_sam3_response,
)

THRESHOLDS = QualityThresholds(
    blur_min_variance=80,
    glare_max_ratio=0.20,
    bottle_min_area_ratio=0.10,
    label_min_area_ratio=0.015,
)


def detailed_bottle() -> Image.Image:
    image = Image.new("RGB", (200, 300), (80, 40, 30))
    draw = ImageDraw.Draw(image)
    for offset in range(0, 80, 8):
        color = "black" if offset % 16 == 0 else (240, 240, 240)
        draw.rectangle((60 + offset, 120, 67 + offset, 190), fill=color)
    return image


def segments() -> tuple[Segment, ...]:
    return (
        Segment("wine bottle", 0.95, (30, 10, 170, 290)),
        Segment("label", 0.90, (55, 115, 145, 195)),
    )


def mask_base64(size=(200, 300), box=(30, 10, 170, 290)) -> str:
    mask = Image.new("1", size)
    ImageDraw.Draw(mask).rectangle(box, fill=1)
    output = io.BytesIO()
    mask.save(output, format="PNG")
    return base64.b64encode(output.getvalue()).decode("ascii")


def test_clear_bottle_and_label_pass_quality_check():
    result = evaluate_quality(detailed_bottle(), segments(), THRESHOLDS)

    assert result.acceptable
    assert result.issues == ()
    assert result.bottle_area_ratio > 0.10
    assert result.label_area_ratio > 0.015


def test_missing_bottle_and_tiny_label_are_reported():
    image = detailed_bottle()
    result = evaluate_quality(
        image,
        (Segment("label", 0.9, (1, 1, 10, 10)),),
        THRESHOLDS,
    )

    assert "bottle_missing" in result.issues
    assert "label_tiny" in result.issues


def test_blur_and_glare_are_reported():
    image = detailed_bottle().filter(ImageFilter.GaussianBlur(12))
    ImageDraw.Draw(image).rectangle((55, 115, 145, 195), fill="white")

    result = evaluate_quality(image, segments(), THRESHOLDS)

    assert "blur" in result.issues
    assert "glare" in result.issues


def test_sam3_response_parser_keeps_requested_instances():
    result = parse_sam3_response(
        {
            "width": 200,
            "height": 300,
            "instances": [
                {"label": "wine bottle", "score": 0.9, "box": [30, 10, 170, 290]},
                {"label": "label", "score": 0.8, "box": [55, 115, 145, 195]},
            ],
        },
        (200, 300),
    )

    assert [item.label for item in result] == ["wine bottle", "label"]


def test_sam3_response_parser_clamps_small_boundary_overflow():
    result = parse_sam3_response(
        {
            "width": 720,
            "height": 1280,
            "instances": [
                {"label": "wine bottle", "score": 0.9, "box": [131, -2, 724, 1235]},
                {"label": "label", "score": 0.8, "box": [131, 574, 595, 1146]},
            ],
        },
        (720, 1280),
    )

    assert result[0].box == (131, 0, 720, 1235)
    assert result[1].box == (131, 574, 595, 1146)


def test_sam3_response_parser_decodes_required_masks():
    result = parse_sam3_response(
        {
            "width": 200,
            "height": 300,
            "instances": [
                {
                    "label": "wine bottle",
                    "score": 0.9,
                    "box": [30, 10, 170, 290],
                    "mask_png_b64": mask_base64(),
                }
            ],
        },
        (200, 300),
        require_masks=True,
    )

    assert result[0].mask_png is not None
    assert result[0].mask_area > 0


def test_sam3_response_parser_rejects_missing_or_wrong_size_required_mask():
    without_mask = {
        "width": 200,
        "height": 300,
        "instances": [
            {"label": "wine bottle", "score": 0.9, "box": [30, 10, 170, 290]}
        ],
    }
    wrong_size = {
        "width": 200,
        "height": 300,
        "instances": [
            {
                "label": "wine bottle",
                "score": 0.9,
                "box": [30, 10, 170, 290],
                "mask_png_b64": mask_base64((20, 30), (1, 1, 10, 20)),
            }
        ],
    }

    with pytest.raises(QualityUnavailable):
        parse_sam3_response(without_mask, (200, 300), require_masks=True)
    with pytest.raises(QualityUnavailable):
        parse_sam3_response(wrong_size, (200, 300), require_masks=True)


def test_sam3_response_parser_rejects_non_png_mask():
    output = io.BytesIO()
    Image.new("L", (200, 300), 255).save(output, format="JPEG")
    value = {
        "width": 200,
        "height": 300,
        "instances": [
            {
                "label": "wine bottle",
                "score": 0.9,
                "box": [30, 10, 170, 290],
                "mask_png_b64": base64.b64encode(output.getvalue()).decode("ascii"),
            }
        ],
    }

    with pytest.raises(QualityUnavailable):
        parse_sam3_response(value, (200, 300), require_masks=True)


@pytest.mark.parametrize(
    "value",
    [
        {"width": 1, "height": 1, "instances": []},
        {"width": 200, "height": 300, "instances": "invalid"},
        {
            "width": 200,
            "height": 300,
            "instances": [{"label": "person", "score": 0.9, "box": [1, 1, 10, 10]}],
        },
    ],
)
def test_invalid_sam3_response_fails_closed(value):
    with pytest.raises(QualityUnavailable):
        parse_sam3_response(value, (200, 300))


async def test_quality_inspector_sends_multi_prompt_request():
    image = detailed_bottle()
    output = io.BytesIO()
    image.save(output, format="JPEG")

    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/upstream/sam3/segment_multi"
        assert b'name="image"; filename="quality.jpg"' in request.content
        assert b"wine bottle, label, wine bottle label" in request.content
        assert b'name="return_masks"' in request.content
        assert b"true" in request.content
        return httpx.Response(
            200,
            json={
                "width": 200,
                "height": 300,
                "instances": [
                    {
                        "label": "wine bottle",
                        "score": 0.95,
                        "box": [30, 10, 170, 290],
                        "mask_png_b64": mask_base64(),
                    },
                    {
                        "label": "label",
                        "score": 0.90,
                        "box": [55, 115, 145, 195],
                        "mask_png_b64": mask_base64(box=(55, 115, 145, 195)),
                    },
                ],
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        result = await QualityInspector(
            "http://service/upstream/sam3",
            client,
            THRESHOLDS,
        ).inspect(output.getvalue())

    assert result.acceptable
    assert len(result.segments) == 2
    assert result.selected_bottle is not None
    assert result.selected_label is not None
