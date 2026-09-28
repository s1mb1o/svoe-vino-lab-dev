import pytest

from chto_za_vino_bot.wine import Wine, unknown_wine, wine_card, wine_from_card


def card(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "name": "  Тестовое вино ",
        "page_url": "https://vino-svoe.ru/wines/test-wine",
        "producer": "Тестовая винодельня",
        "category": "Красное",
        "region": "Кубань",
        "color": "Рубиновый",
        "grapes": " ",
        "sugar": "Сухое",
        "image_url": "https://api.vino-svoe.ru/v1/img/test.webp",
        "qr_urls": ["https://producer.example/a", "https://producer.example/a"],
    }
    value.update(changes)
    return value


def test_matcher_card_gives_the_wine():
    wine = wine_from_card("test-wine", card())

    assert wine == Wine(
        slug="test-wine",
        name="Тестовое вино",
        page_url="https://vino-svoe.ru/wines/test-wine",
        producer="Тестовая винодельня",
        category="Красное",
        color="Рубиновый",
        grapes=None,
        sugar="Сухое",
        image_url="https://api.vino-svoe.ru/v1/img/test.webp",
        qr_urls=("https://producer.example/a",),
    )


def test_missing_optional_card_fields_are_empty():
    wine = wine_from_card("x", {"name": "X", "page_url": "https://vino-svoe.ru/wines/x"})

    assert (wine.producer, wine.category, wine.color, wine.grapes) == (None, None, None, None)
    assert (wine.sugar, wine.image_url, wine.qr_urls) == (None, None, ())


@pytest.mark.parametrize(
    "value",
    [
        None,
        "not a card",
        card(name=""),
        card(name=None),
        card(page_url="vino-svoe.ru/wines/test-wine"),
        card(page_url="http://vino-svoe.ru/wines/test-wine"),
        card(page_url="https://attacker.example/wines/test-wine"),
        card(page_url="https://vino-svoe.ru@attacker.example/wines/test-wine"),
        card(page_url="https://vino-svoe.ru:8443/wines/test-wine"),
        card(page_url=None),
        card(producer=1),
        card(image_url=["https://api.vino-svoe.ru/a.webp"]),
        card(qr_urls="https://producer.example/a"),
        card(qr_urls=["javascript:alert(1)"]),
        card(qr_urls=[None]),
    ],
)
def test_invalid_card_is_rejected(value):
    with pytest.raises((TypeError, ValueError)):
        wine_from_card("test-wine", value)


def test_stored_card_reads_back_to_the_same_wine():
    wine = wine_from_card("test-wine", card())

    assert wine_from_card("test-wine", wine_card(wine)) == wine


def test_catalogue_page_accepts_the_www_host():
    wine = wine_from_card(
        "test-wine",
        card(page_url="https://www.vino-svoe.ru/wines/test-wine"),
    )

    assert wine.page_url == "https://www.vino-svoe.ru/wines/test-wine"


def test_unknown_wine_is_a_safe_minimal_card():
    wine = unknown_wine("unknown slug")

    assert wine.name == "unknown slug"
    assert wine.page_url == "https://vino-svoe.ru/wines/unknown%20slug"
    assert wine.image_url is None
    assert wine.sugar is None
    assert wine.qr_urls == ()
