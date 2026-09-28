import copy
import io

import httpx
import pytest
from PIL import Image

from chto_za_vino_bot.matcher import (
    Matcher,
    RecognitionUnavailable,
    is_confident,
    parse_recognition_response,
)


def card(slug: str) -> dict[str, object]:
    return {
        "name": f"Вино {slug}",
        "page_url": f"https://vino-svoe.ru/wines/{slug}",
        "producer": "Винодельня",
        "category": "Красное",
        "region": "Крым",
        "color": "Рубиновый",
        "grapes": None,
        "sugar": "Сухое",
        "image_url": f"https://api.vino-svoe.ru/uploads/{slug}.webp",
        "qr_urls": [],
    }


def response() -> dict[str, object]:
    return {
        "pipeline": "test-pipeline",
        "latency_ms": 812.5,
        "candidates": [
            {"slug": slug, "score": score, "rank": rank, "wine": card(slug)}
            for rank, (slug, score) in enumerate(
                [("wine-a", 0.82), ("wine-b", 0.76), ("wine-c", 0.71), ("wine-d", 0.68)],
                start=1,
            )
        ],
    }


def image_bytes(image_format: str = "JPEG") -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (40, 60), "darkred").save(output, format=image_format)
    return output.getvalue()


def test_ranked_response_is_parsed_with_margin_and_cards():
    result = parse_recognition_response(response())

    assert result.pipeline == "test-pipeline"
    assert result.top.slug == "wine-a"
    assert result.top.score == 0.82
    assert result.margin == pytest.approx(0.06)
    assert [candidate.rank for candidate in result.candidates] == [1, 2, 3, 4]
    wine = result.top.wine
    assert wine.slug == "wine-a"
    assert wine.name == "Вино wine-a"
    assert wine.page_url == "https://vino-svoe.ru/wines/wine-a"
    assert wine.producer == "Винодельня"
    assert wine.category == "Красное"
    assert wine.color == "Рубиновый"
    assert wine.grapes is None
    assert wine.sugar == "Сухое"
    assert wine.image_url == "https://api.vino-svoe.ru/uploads/wine-a.webp"
    assert wine.qr_urls == ()


def test_confidence_requires_score_and_margin():
    result = parse_recognition_response(response())

    assert is_confident(result, min_score=0.80, min_margin=0.05)
    assert not is_confident(result, min_score=0.83, min_margin=0.05)
    assert not is_confident(result, min_score=0.80, min_margin=0.07)


def test_an_empty_answer_means_no_match_and_is_not_confident():
    result = parse_recognition_response({"pipeline": "test-pipeline", "candidates": []})

    assert result.candidates == ()
    assert result.margin == 0.0
    assert not is_confident(result, min_score=0.0, min_margin=0.0)


def test_fewer_candidates_are_accepted_and_one_candidate_has_no_margin():
    value = response()
    value["candidates"] = value["candidates"][:1]

    result = parse_recognition_response(value)

    assert [candidate.slug for candidate in result.candidates] == ["wine-a"]
    assert result.margin == 0.0
    assert not is_confident(result, min_score=0.5, min_margin=0.01)


def broken(change) -> dict[str, object]:
    value = copy.deepcopy(response())
    change(value)
    return value


@pytest.mark.parametrize(
    "value",
    [
        {"slug": "wine-a"},
        [],
        broken(lambda value: value.pop("pipeline")),
        broken(lambda value: value.update(pipeline="")),
        broken(lambda value: value.pop("candidates")),
        broken(lambda value: value["candidates"].append(dict(value["candidates"][-1]))),
        broken(lambda value: value["candidates"][0].update(rank=2)),
        broken(lambda value: value["candidates"][0].update(rank=True)),
        broken(lambda value: value["candidates"][1].update(score=0.9)),
        broken(lambda value: value["candidates"][1].update(slug="wine-a")),
        broken(lambda value: value["candidates"][1].update(slug="")),
        broken(lambda value: value["candidates"][0].update(score=float("nan"))),
        broken(lambda value: value["candidates"][0].update(score=True)),
        broken(lambda value: value["candidates"][0].pop("wine")),
        broken(lambda value: value["candidates"][0]["wine"].update(name="")),
        broken(lambda value: value["candidates"][0]["wine"].pop("page_url")),
        broken(
            lambda value: value["candidates"][0]["wine"].update(
                page_url="http://vino-svoe.ru/wines/wine-a"
            )
        ),
        broken(lambda value: value["candidates"][0]["wine"].update(color=5)),
        broken(lambda value: value["candidates"][0]["wine"].update(qr_urls="https://x.ru")),
        broken(lambda value: value["candidates"][0]["wine"].update(qr_urls=["ftp://x.ru/a"])),
    ],
)
def test_invalid_ranked_response_fails_closed(value):
    with pytest.raises(RecognitionUnavailable):
        parse_recognition_response(value)


async def test_matcher_requests_four_candidates_without_a_pipeline():
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/match"
        assert dict(request.url.params) == {"k": "4"}
        assert b'name="image"; filename="telegram-photo.jpg"' in request.content
        return httpx.Response(200, json=response())

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        result = await Matcher("http://matcher/v1/match", client).recognize(image_bytes())

    assert len(result.candidates) == 4


async def test_matcher_preserves_png_multipart_type():
    def respond(request: httpx.Request) -> httpx.Response:
        assert b'filename="telegram-photo.png"' in request.content
        assert b"Content-Type: image/png" in request.content
        return httpx.Response(200, json=response())

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        await Matcher("http://matcher/v1/match", client).recognize(image_bytes("PNG"))


@pytest.mark.parametrize(
    "reply",
    [
        httpx.Response(503, json={"detail": "the selected pipeline has no wine cards"}),
        httpx.Response(200, content=b"not json"),
    ],
)
async def test_matcher_errors_fail_closed(reply):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: reply)
    ) as client:
        with pytest.raises(RecognitionUnavailable):
            await Matcher("http://matcher/v1/match", client).recognize(image_bytes())
