import asyncio
import json
import logging

import httpx
import pytest

from chto_za_vino_core.diary import (
    RECORD_PATH,
    SNAPSHOT_BYTES,
    UNDO_PATH,
    DiaryHistory,
    wine_snapshot,
)
from chto_za_vino_core.wine import Wine, unknown_wine

TOKEN = "d" * 40
USER_ID = 501


def wine(slug: str = "wine-1", **changes: object) -> Wine:
    values: dict[str, object] = {
        "slug": slug,
        "name": "  Тестовое   вино ",
        "page_url": f"https://vino-svoe.ru/wines/{slug}",
        "producer": "Винодельня",
        "category": "Красное",
        "color": "Рубиновый",
        "grapes": "Каберне Совиньон, Мерло;  Саперави ,Мерло",
        "sugar": "Сухое",
        "image_url": None,
        "region": "Крым",
    }
    values.update(changes)
    return Wine(**values)  # type: ignore[arg-type]


class FakeService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object], str | None]] = []
        self.answer: httpx.Response | Exception = httpx.Response(200, json={"status": "recorded"})

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(
            (request.url.path, json.loads(request.content), request.headers.get("authorization"))
        )
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


@pytest.fixture
async def service():
    fake = FakeService()
    async with httpx.AsyncClient(transport=httpx.MockTransport(fake.handler)) as client:
        fake.history = DiaryHistory("http://account.test/", TOKEN, client)
        yield fake


def test_snapshot_takes_the_card_data():
    assert wine_snapshot(wine()) == {
        "name": "Тестовое вино",
        "producer": "Винодельня",
        "color": "Красное",
        "sugar": "Сухое",
        "region": "Крым",
        "grapes": ["Каберне Совиньон", "Мерло", "Саперави"],
    }


def test_snapshot_omits_empty_fields_and_uses_the_tint_without_a_category():
    snapshot = wine_snapshot(
        wine(producer=None, category=None, grapes=" , ", sugar="  ", region=None)
    )

    assert snapshot == {"name": "Тестовое вино", "color": "Рубиновый"}


def test_snapshot_of_a_card_without_data_is_none():
    assert wine_snapshot(unknown_wine("wine-1")) is None


def test_snapshot_keeps_the_service_limits():
    snapshot = wine_snapshot(
        wine(
            name="Я" * 500,
            producer="П" * 300,
            grapes=", ".join(f"{index}{'B' * 100}" for index in range(20)),
        )
    )

    assert snapshot is not None
    assert len(snapshot["name"]) == 200
    assert len(snapshot["producer"]) == 200
    assert len(snapshot["grapes"]) == 12
    assert all(len(item) == 80 for item in snapshot["grapes"])
    compact = json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"))
    assert len(compact.encode("utf-8")) <= SNAPSHOT_BYTES


def test_snapshot_drops_the_grapes_and_the_region_first_when_it_is_too_large():
    # Four-byte characters: 200 of them take 800 bytes. Three such fields exceed 2,048 bytes.
    snapshot = wine_snapshot(
        wine(name="🍷" * 200, producer="🍇" * 200, region="🍷" * 200, grapes="Мерло")
    )

    assert snapshot is not None
    assert set(snapshot) == {"name", "producer", "color", "sugar"}
    assert snapshot["name"] == "🍷" * 200
    assert len(json.dumps(snapshot, ensure_ascii=False).encode("utf-8")) <= SNAPSHOT_BYTES


async def test_record_sends_the_wine_and_the_snapshot(service):
    service.history.record(USER_ID, wine())
    await service.history.join()

    path, body, authorization = service.calls[0]
    assert path == RECORD_PATH
    assert authorization == f"Bearer {TOKEN}"
    assert body == {"user_id": USER_ID, "slug": "wine-1", "wine_snapshot": wine_snapshot(wine())}


async def test_record_of_an_alternative_names_the_rejected_wine(service):
    service.history.record(USER_ID, wine("wine-2"), replaces="wine-1")
    service.history.record(USER_ID, wine("wine-3"), replaces="wine-3")
    service.history.record(USER_ID, wine("wine-4"), replaces="Not A Slug")
    await service.history.join()

    assert [body.get("replaces") for _, body, _ in service.calls] == ["wine-1", None, None]


async def test_record_without_a_snapshot(service):
    service.history.record(USER_ID, unknown_wine("old-wine"))
    await service.history.join()

    assert service.calls[0][1] == {"user_id": USER_ID, "slug": "old-wine"}


async def test_undo_sends_the_rejected_wine(service):
    service.answer = httpx.Response(200, json={"status": "removed"})
    service.history.undo(USER_ID, "wine-1")
    await service.history.join()

    assert service.calls == [
        (UNDO_PATH, {"user_id": USER_ID, "slug": "wine-1"}, f"Bearer {TOKEN}")
    ]


@pytest.mark.parametrize("user_id", [0, -5, True])
async def test_no_call_without_a_person(service, user_id):
    service.history.record(user_id, wine())
    service.history.undo(user_id, "wine-1")
    await service.history.join()

    assert service.calls == []


async def test_no_call_for_an_invalid_slug(service):
    service.history.record(USER_ID, wine("Wine One"))
    service.history.undo(USER_ID, "-wine")
    await service.history.join()

    assert service.calls == []


@pytest.mark.parametrize(
    "answer",
    [
        httpx.ConnectError("refused"),
        httpx.ReadTimeout("slow"),
        httpx.Response(401, json={"error": "unauthorized"}),
        httpx.Response(422, json={"error": "invalid_request"}),
        httpx.Response(503, text="<html>down</html>"),
        httpx.Response(200, json=["recorded"]),
        httpx.Response(200, json={"status": None}),
        httpx.Response(200, content=b"{" + b" " * 20000 + b"}"),
    ],
)
async def test_failures_are_logged_without_personal_data(service, answer, caplog):
    service.answer = answer
    caplog.set_level(logging.INFO, logger="chto_za_vino_core.diary")

    service.history.record(USER_ID, wine("secret-wine"))
    await service.history.join()

    assert len(service.calls) == 1
    assert [record.levelno for record in caplog.records] == [logging.WARNING]
    text = caplog.text
    assert str(USER_ID) not in text
    assert "secret-wine" not in text
    assert TOKEN not in text


async def test_a_slow_service_stops_after_the_timeout(caplog):
    async def handler(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(5)
        return httpx.Response(200, json={"status": "recorded"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        history = DiaryHistory("http://account.test", TOKEN, client, timeout_seconds=0.05)
        history.record(USER_ID, wine())
        await asyncio.wait_for(history.join(), 1)

    assert "Diary history record failed: TimeoutError" in caplog.text


async def test_success_logs_only_the_status(service, caplog):
    service.answer = httpx.Response(200, json={"status": "not_linked"})
    caplog.set_level(logging.INFO, logger="chto_za_vino_core.diary")

    service.history.record(USER_ID, wine())
    await service.history.join()

    assert caplog.messages == ["Diary history record answered status=not_linked"]


async def test_calls_do_not_block_the_caller_and_have_a_limit():
    started = 0
    release = asyncio.Event()

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal started
        started += 1
        await release.wait()
        return httpx.Response(200, json={"status": "recorded"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        history = DiaryHistory("http://account.test", TOKEN, client, max_tasks=2)
        for _ in range(5):
            history.record(USER_ID, wine())
        for _ in range(20):
            await asyncio.sleep(0)
        assert started == 2
        release.set()
        await asyncio.wait_for(history.join(), 1)
    assert started == 5


def test_repr_has_no_token():
    history = DiaryHistory("http://account.test", TOKEN, httpx.AsyncClient())

    assert TOKEN not in repr(history)


def test_record_without_a_running_loop_does_not_raise(caplog):
    history = DiaryHistory("http://account.test", TOKEN, httpx.AsyncClient())

    history.record(USER_ID, wine())

    assert "Diary history record failed: RuntimeError" in caplog.text
