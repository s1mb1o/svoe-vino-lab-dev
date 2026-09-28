import httpx
import pytest

from chto_za_vino_bot.moderation import (
    ModerationUnavailable,
    Moderator,
    parse_moderation_response,
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
