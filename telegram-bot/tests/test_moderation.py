import io

import httpx
import pytest
from PIL import Image

from chto_za_vino_bot.moderation import (
    DisabledModerator,
    InvalidImage,
    ModerationUnavailable,
    Moderator,
    make_moderation_jpeg,
    make_moderator,
    parse_moderation_response,
    prepare_source_image,
)


def response(
    *,
    scores: dict[str, float] | None = None,
    flagged: list[str] | None = None,
) -> dict[str, object]:
    return {
        "model": "shieldgemma-2-4b-it",
        "width": 1024,
        "height": 1024,
        "threshold": 0.5,
        "scores": scores
        or {
            "dangerous": 0.01,
            "sexual": 0.02,
            "violence": 0.03,
        },
        "flagged": flagged or [],
    }


def test_parse_safe_response():
    result = parse_moderation_response(response())

    assert result.safe is True
    assert result.performed is True
    assert result.bypassed is False
    assert result.accepted is True
    assert result.category == "safe"
    assert result.confidence == 0.03
    assert result.scores == {
        "dangerous": 0.01,
        "sexual": 0.02,
        "violence": 0.03,
    }


def test_parse_multiple_flagged_policies_in_canonical_order():
    result = parse_moderation_response(
        response(
            scores={
                "dangerous": 0.8,
                "sexual": 0.7,
                "violence": 0.1,
            },
            flagged=["sexual", "dangerous"],
        )
    )

    assert result.safe is False
    assert result.category == "dangerous,sexual"
    assert result.confidence == 0.8
    assert result.reason == "dangerous=0.800000,sexual=0.700000,violence=0.100000"


@pytest.mark.parametrize(
    "value",
    [
        "not an object",
        {**response(), "model": "another-model"},
        {**response(), "threshold": 0.4},
        response(scores={"dangerous": 0.1, "sexual": 0.2}),
        response(
            scores={"dangerous": 0.1, "sexual": 0.2, "violence": 2.0}
        ),
        response(flagged=["unknown"]),
        response(flagged=["sexual"]),
    ],
)
def test_invalid_response_fails_closed(value):
    with pytest.raises(ModerationUnavailable):
        parse_moderation_response(value)


async def test_moderator_sends_multipart_image():
    jpeg = b"jpeg-image-body"

    def respond(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/upstream/shieldgemma-2-4b-it/classify"
        assert request.headers["content-type"].startswith("multipart/form-data; boundary=")
        assert b'name="image"; filename="moderation.jpg"' in request.content
        assert b"Content-Type: image/jpeg" in request.content
        assert jpeg in request.content
        return httpx.Response(200, json=response())

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        result = await Moderator(
            "http://moderation/upstream/shieldgemma-2-4b-it/classify",
            client,
        ).classify(jpeg)

    assert result.safe is True


async def test_moderator_transport_error_fails_closed():
    def fail(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "unavailable"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(fail)) as client:
        with pytest.raises(ModerationUnavailable):
            await Moderator("http://moderation/classify", client).classify(b"jpeg")


async def test_disabled_moderator_accepts_without_an_http_request():
    def fail_on_request(request: httpx.Request) -> httpx.Response:
        raise AssertionError("disabled moderation made an HTTP request")

    async with httpx.AsyncClient(transport=httpx.MockTransport(fail_on_request)) as client:
        moderator = make_moderator(False, None, client)
        result = await moderator.classify(b"jpeg")

    assert isinstance(moderator, DisabledModerator)
    assert result.safe is None
    assert result.performed is False
    assert result.bypassed is True
    assert result.accepted is True
    assert result.category == "disabled"
    assert result.confidence == 0.0
    assert result.reason == "moderation_disabled"
    assert result.scores == {}


async def test_enabled_moderation_requires_an_endpoint():
    async with httpx.AsyncClient() as client:
        with pytest.raises(ValueError, match="moderation endpoint"):
            make_moderator(True, None, client)


def image_bytes(image_format: str, *, frames: int = 1) -> bytes:
    images = [Image.new("RGB", (16, 16), color) for color in ("white", "red", "blue")[:frames]]
    buffer = io.BytesIO()
    if frames == 1:
        images[0].save(buffer, format=image_format)
    else:
        images[0].save(buffer, format=image_format, save_all=True, append_images=images[1:])
    return buffer.getvalue()


@pytest.mark.parametrize("image_format", ["JPEG", "PNG", "WEBP"])
def test_moderation_jpeg_accepts_a_still_image(image_format):
    with Image.open(io.BytesIO(make_moderation_jpeg(image_bytes(image_format)))) as image:
        assert image.format == "JPEG"


@pytest.mark.parametrize("image_format", ["PNG", "WEBP"])
def test_moderation_jpeg_rejects_an_animated_image(image_format):
    # Moderation sees only one frame, so a later frame could hide unsafe content.
    with pytest.raises(InvalidImage):
        make_moderation_jpeg(image_bytes(image_format, frames=2))


def heic_bytes() -> bytes:
    """A 40 by 20 HEIC image, left half red, with EXIF rotation 6 and a GPS tag."""
    image = Image.new("RGB", (40, 20), "white")
    image.paste((255, 0, 0), (0, 0, 20, 20))
    exif = Image.Exif()
    exif[0x0112] = 6
    exif[0x8825] = {2: (55.0, 45.0, 0.0)}
    buffer = io.BytesIO()
    image.save(buffer, format="HEIF", exif=exif.tobytes())
    return buffer.getvalue()


def test_heic_becomes_an_upright_jpeg_without_exif():
    with Image.open(io.BytesIO(prepare_source_image(heic_bytes()))) as image:
        assert image.format == "JPEG"
        assert image.size == (20, 40)
        assert image.getpixel((10, 2))[0] > 200
        assert image.getpixel((10, 2))[1] < 50
        assert image.getpixel((10, 37)) == (255, 255, 255)
        assert "exif" not in image.info


def test_heic_is_moderated_as_its_jpeg_copy():
    with Image.open(io.BytesIO(make_moderation_jpeg(prepare_source_image(heic_bytes())))) as image:
        assert image.format == "JPEG"


@pytest.mark.parametrize("image_format", ["JPEG", "PNG", "WEBP"])
def test_another_image_is_not_converted(image_format):
    body = image_bytes(image_format)
    assert prepare_source_image(body) is body


def test_raw_heic_is_not_a_supported_pipeline_image():
    # Each path converts HEIC with prepare_source_image first. A raw HEIC fails closed.
    with pytest.raises(InvalidImage):
        make_moderation_jpeg(heic_bytes())


def test_invalid_heic_is_an_invalid_image():
    with pytest.raises(InvalidImage):
        prepare_source_image(b"\x00\x00\x00\x18ftypheic" + bytes(40))


def noisy_heic_bytes(size: tuple[int, int] = (300, 300)) -> bytes:
    """A HEIC image whose JPEG copy is larger than the HEIC file."""
    image = Image.frombytes("RGB", size, bytes((index * 7919) % 251 for index in range(size[0] * size[1] * 3)))
    buffer = io.BytesIO()
    image.save(buffer, format="HEIF")
    return buffer.getvalue()


def test_a_large_heic_is_scaled_to_the_maximum_side():
    image = Image.new("RGB", (5000, 100), "white")
    buffer = io.BytesIO()
    image.save(buffer, format="HEIF")

    with Image.open(io.BytesIO(prepare_source_image(buffer.getvalue()))) as converted:
        assert converted.size == (4096, 82)

