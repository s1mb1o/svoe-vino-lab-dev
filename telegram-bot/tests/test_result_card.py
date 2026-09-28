import io

import httpx
import pytest
from PIL import Image, ImageChops, ImageDraw

from chto_za_vino_bot.result_card import (
    CatalogImageLoader,
    CatalogImageUnavailable,
    format_result_caption,
    normalize_result_photo,
    prepare_catalog_result_photo,
)
from chto_za_vino_bot.wine import Wine


def wine(**changes):
    values = {
        "slug": "test-wine-suhoe",
        "name": "Тестовое & вино",
        "page_url": "https://vino-svoe.ru/wines/test-wine-suhoe",
        "producer": "Винодельня",
        "category": "Красное",
        "color": "Рубиновый",
        "grapes": "Пино Нуар",
        "sugar": "Сухое",
        "image_url": "https://api.vino-svoe.ru/v1/img/test.webp",
    }
    values.update(changes)
    return Wine(**values)


def test_result_caption_has_image_card_parameters():
    caption = format_result_caption(wine())

    assert "Тестовое &amp; вино" in caption
    assert "Цвет:</b> Красное · Рубиновый" in caption
    assert "Сахар:</b> Сухое" in caption
    assert "Виноград:</b> Пино Нуар" in caption
    assert "https://vino-svoe.ru/wines/test-wine-suhoe" in caption
    assert "Справочно · не предложение о продаже." in caption
    assert "18+ · Чрезмерное употребление алкоголя вредит вашему здоровью." in caption
    assert "каталоге vino-svoe.ru" in caption
    assert len(caption) <= 1024


def test_result_caption_marks_missing_parameters():
    caption = format_result_caption(
        wine(category=None, color=None, grapes=None, sugar=None, image_url=None)
    )

    assert caption.count("нет данных") == 3


def test_result_caption_fits_telegram_limit_with_long_parameters():
    caption = format_result_caption(
        wine(
            name="Н" * 1000,
            category="К" * 1000,
            color="Ц" * 1000,
            sugar="С" * 1000,
            grapes="В" * 1000,
        )
    )

    assert len(caption) <= 1024


def test_result_photo_is_normalized_to_bounded_jpeg():
    source = Image.new("RGBA", (1800, 900), (120, 0, 40, 128))
    buffer = io.BytesIO()
    source.save(buffer, format="PNG")

    result = normalize_result_photo(buffer.getvalue())

    with Image.open(io.BytesIO(result)) as image:
        assert image.format == "JPEG"
        assert image.mode == "RGB"
        assert image.size == (1280, 640)


def test_catalog_result_photo_fits_transparent_bottle_on_4_by_5_canvas():
    source = Image.new("RGBA", (1200, 2400), (0, 0, 0, 0))
    ImageDraw.Draw(source).rounded_rectangle(
        (430, 20, 770, 2380),
        radius=100,
        fill=(120, 10, 40, 255),
    )
    buffer = io.BytesIO()
    source.save(buffer, format="PNG")

    result = prepare_catalog_result_photo(buffer.getvalue())

    with Image.open(io.BytesIO(result)) as image:
        assert image.format == "JPEG"
        assert image.mode == "RGB"
        assert image.size == (1024, 1280)
        difference = ImageChops.difference(image, Image.new("RGB", image.size, "white"))
        bbox = difference.getbbox()
        assert bbox is not None
        assert 50 <= bbox[1] <= 80
        assert 1200 <= bbox[3] <= 1230
        assert abs((bbox[0] + bbox[2]) / 2 - 512) <= 3


def test_catalog_result_photo_ignores_white_margin_noise():
    source = Image.new("RGB", (1800, 1800), "white")
    draw = ImageDraw.Draw(source)
    draw.rectangle((650, 100, 1150, 1700), fill=(40, 80, 120))
    draw.point((0, 0), fill="black")
    buffer = io.BytesIO()
    source.save(buffer, format="PNG")

    result = prepare_catalog_result_photo(buffer.getvalue())

    with Image.open(io.BytesIO(result)) as image:
        assert image.size == (1024, 1280)
        assert image.getpixel((0, 0)) == (255, 255, 255)


async def test_catalog_image_loader_rejects_untrusted_host():
    async with httpx.AsyncClient() as client:
        loader = CatalogImageLoader(client)
        with pytest.raises(CatalogImageUnavailable):
            await loader.fetch("https://example.com/image.jpg")


async def test_catalog_image_loader_downloads_and_prepares_preview_image():
    source = Image.new("RGB", (300, 600), "white")
    buffer = io.BytesIO()
    source.save(buffer, format="WEBP")

    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.vino-svoe.ru"
        return httpx.Response(200, content=buffer.getvalue())

    transport = httpx.MockTransport(respond)
    async with httpx.AsyncClient(transport=transport) as client:
        result = await CatalogImageLoader(client).fetch(
            "https://api.vino-svoe.ru/v1/img/test.webp"
        )

    with Image.open(io.BytesIO(result)) as image:
        assert image.format == "JPEG"
        assert image.size == (1024, 1280)
