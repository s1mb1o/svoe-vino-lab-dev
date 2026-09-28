from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote, urlsplit

OPTIONAL_TEXT_FIELDS = ("producer", "category", "color", "grapes", "sugar", "image_url")


@dataclass(frozen=True, slots=True)
class Wine:
    slug: str
    name: str
    page_url: str
    producer: str | None
    category: str | None
    color: str | None
    grapes: str | None
    sugar: str | None
    image_url: str | None
    qr_urls: tuple[str, ...] = ()


def unknown_wine(slug: str) -> Wine:
    """Return the minimal card of a slug that has no stored card."""
    return Wine(
        slug=slug,
        name=slug,
        page_url=f"https://vino-svoe.ru/wines/{quote(slug, safe='-')}",
        producer=None,
        category=None,
        color=None,
        grapes=None,
        sugar=None,
        image_url=None,
    )


def _optional_text(card: dict[str, object], field: str) -> str | None:
    value = card.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"wine card {field} must be a string or null")
    return value.strip() or None


def _is_web_url(value: str, schemes: tuple[str, ...]) -> bool:
    try:
        parts = urlsplit(value)
    except ValueError:
        return False
    return parts.scheme in schemes and bool(parts.hostname)


def wine_from_card(slug: str, card: object) -> Wine:
    """Return the wine of one matcher card.

    Raise TypeError or ValueError for an invalid card.
    """
    if not isinstance(card, dict):
        raise TypeError("wine card must be an object")
    name = card.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("wine card name must be a non-empty string")
    page_url = card.get("page_url")
    if not isinstance(page_url, str) or not _is_web_url(page_url, ("https",)):
        raise ValueError("wine card page_url must be an HTTPS URL")
    raw_qr_urls = card.get("qr_urls", [])
    if not isinstance(raw_qr_urls, list) or not all(
        isinstance(url, str) and _is_web_url(url, ("http", "https")) for url in raw_qr_urls
    ):
        raise ValueError("wine card qr_urls must be a list of HTTP or HTTPS URLs")
    values = {field: _optional_text(card, field) for field in OPTIONAL_TEXT_FIELDS}
    return Wine(
        slug=slug,
        name=name.strip(),
        page_url=page_url,
        qr_urls=tuple(dict.fromkeys(raw_qr_urls)),
        **values,
    )


def wine_card(wine: Wine) -> dict[str, object]:
    """Return the stored card of a wine. `wine_from_card` reads it back."""
    return {
        "name": wine.name,
        "page_url": wine.page_url,
        "producer": wine.producer,
        "category": wine.category,
        "color": wine.color,
        "grapes": wine.grapes,
        "sugar": wine.sugar,
        "image_url": wine.image_url,
        "qr_urls": list(wine.qr_urls),
    }
