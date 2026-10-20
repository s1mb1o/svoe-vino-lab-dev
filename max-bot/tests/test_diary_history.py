"""«Винный дневник» history records from the chat (plan `docs/plans/07_diary-history-and-saved.md`).

Port of `telegram-bot/tests/test_diary_history.py`. MAX differences: the job of a MAX photo
already carries the sender user ID, and a callback answer is a notification.
"""

import json
import logging
from types import SimpleNamespace

import httpx
import pytest
from chto_za_vino_core.diary import DiaryHistory
from fakes import DIALOG_CHAT_ID, USER_ID, FakeMaxApi, callback
from test_feedback import OTHER_USER, card, make_services, recognized_request
from test_processor_quality import (
    PHOTO,
    SOURCE_MID,
    AdvisoryQualityInspector,
    FakeMatcher,
    jpeg,
    max_api,
    processor_services,
)

from chto_za_vino_max_bot.app import (
    BotHandlers,
    PhotoJob,
    PhotoProcessor,
    _result_card_time,
    handle_alternative_feedback,
    handle_result_feedback,
)
from chto_za_vino_max_bot.storage import CandidateRecord, Repository

TOKEN = "m" * 40
RECORD = "/v1/bot/history"
UNDO = "/v1/bot/history/undo"


class FakeAccount:
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
async def account():
    fake = FakeAccount()
    async with httpx.AsyncClient(transport=httpx.MockTransport(fake.handler)) as client:
        fake.history = DiaryHistory("http://account.test", TOKEN, client)
        yield fake


async def process(tmp_path, history, *, api_request=False, matcher=None, api=None):
    repository = Repository(tmp_path / "bot.sqlite3")
    if api_request:
        request_id = repository.create_api_request(now=1000)
    else:
        reservation = repository.reserve(
            chat_id=DIALOG_CHAT_ID,
            chat_type="dialog",
            message_id=SOURCE_MID,
            photo_index=0,
            user_id=USER_ID,
            username="tester",
            first_name="Test",
            last_name=None,
            photo_id=PHOTO.photo_id,
            photo_url=PHOTO.url,
            photo_token=PHOTO.token,
            now=1000,
            limit=50,
            window_seconds=3600,
        )
        request_id = reservation.request_id
    api = api or max_api()
    services = processor_services(
        tmp_path, repository, AdvisoryQualityInspector(), matcher=matcher
    )
    services.history = history
    if api_request:
        job = PhotoJob(
            request_id=request_id,
            chat_id=0,
            chat_type="api",
            source_message_id="",
            received_at=1000,
            photo_url="",
            feedback_enabled=False,
            status_enabled=False,
            image_body=jpeg(),
            delivery_enabled=False,
        )
    else:
        job = PhotoJob(
            request_id=request_id,
            chat_id=DIALOG_CHAT_ID,
            chat_type="dialog",
            user_id=USER_ID,
            source_message_id=SOURCE_MID,
            received_at=1000,
            photo_id=PHOTO.photo_id,
            photo_url=PHOTO.url,
            status_enabled=False,
        )
    await PhotoProcessor(services, api).process(job)
    status = repository.admin_request(request_id).status
    repository.close()
    if history is not None:
        await history.join()
    return status, api


def photo_count(api: FakeMaxApi) -> int:
    return len(api.calls_of("upload_image"))


WINE_1_SNAPSHOT = {
    "name": "Тестовое вино wine-1",
    "color": "Красное",
    "sugar": "Сухое",
    "grapes": ["Пино Нуар"],
}


async def test_a_result_card_records_the_shown_wine(tmp_path, account):
    status, api = await process(tmp_path, account.history)

    assert status == "recognized"
    assert photo_count(api) == 1
    assert account.calls == [
        (
            RECORD,
            {"user_id": USER_ID, "slug": "wine-1", "wine_snapshot": WINE_1_SNAPSHOT},
            f"Bearer {TOKEN}",
        )
    ]


async def test_a_tentative_card_is_recorded_too(tmp_path, account):
    status, _ = await process(
        tmp_path, account.history, matcher=FakeMatcher(scores=(0.5, 0.49, 0.3, 0.2))
    )

    assert status == "abstained"
    assert [(path, body["slug"]) for path, body, _ in account.calls] == [(RECORD, "wine-1")]


async def test_no_record_without_a_wine_card(tmp_path, account):
    status, _ = await process(tmp_path, account.history, matcher=FakeMatcher(count=0))

    assert status == "abstained"
    assert account.calls == []


async def test_an_http_api_request_records_nothing(tmp_path, account):
    status, api = await process(tmp_path, account.history, api_request=True)

    assert status == "recognized"
    assert api.calls_of("send_message") == []
    assert account.calls == []


async def test_an_undelivered_card_records_nothing(tmp_path, account):
    api = max_api()
    api.fail_on["upload_image"] = RuntimeError("MAX is unavailable")
    api.fail_on["send_message"] = RuntimeError("MAX is unavailable")

    status, _ = await process(tmp_path, account.history, api=api)

    assert status == "recognized"
    assert account.calls == []


async def test_the_bot_works_without_the_account_service(tmp_path):
    status, api = await process(tmp_path, None)

    assert status == "recognized"
    assert photo_count(api) == 1


async def test_an_account_failure_changes_nothing_in_the_chat(tmp_path, account, caplog):
    account.answer = httpx.ConnectError("refused")

    status, api = await process(tmp_path, account.history)

    assert status == "recognized"
    assert photo_count(api) == 1
    assert len(account.calls) == 1
    assert "Diary history record failed: ConnectError" in caplog.text
    assert str(USER_ID) not in caplog.text
    assert "wine-1" not in caplog.text


def shown_request(repository: Repository) -> str:
    request_id = recognized_request(repository)
    repository.update(request_id, recognition_slug="wine-1")
    repository.replace_candidates(
        request_id,
        [
            CandidateRecord(
                rank, f"wine-{rank}", 1.0 - rank / 10, card(f"wine-{rank}", f"Вино {rank}")
            )
            for rank in range(1, 5)
        ],
    )
    return request_id


@pytest.fixture
def repository(tmp_path):
    value = Repository(tmp_path / "bot.sqlite3")
    yield value
    value.close()


def services_with(repository: Repository, account: FakeAccount):
    services = make_services(repository)
    services.history = account.history
    return services


def notifications(api: FakeMaxApi) -> list[str | None]:
    return [call["notification"] for call in api.calls_of("answer_callback")]


async def test_a_mismatch_removes_the_shown_wine(repository, account):
    request_id = shown_request(repository)
    api = FakeMaxApi()

    await handle_result_feedback(
        callback(f"feedback:no:{request_id}", with_message=False),
        services_with(repository, account),
        api,
    )
    await account.history.join()

    assert notifications(api) == ["Спасибо! Выберите возможный вариант."]
    # The request has no delivery step: the card time is the receipt time.
    assert account.calls == [
        (UNDO, {"user_id": USER_ID, "slug": "wine-1", "at": 1000}, f"Bearer {TOKEN}")
    ]


async def test_a_mismatch_of_another_user_sends_nothing(repository, account):
    request_id = shown_request(repository)
    api = FakeMaxApi()

    await handle_result_feedback(
        callback(f"feedback:no:{request_id}", from_user=OTHER_USER, with_message=False),
        services_with(repository, account),
        api,
    )
    await account.history.join()

    assert notifications(api) == ["Эта оценка недоступна."]
    assert account.calls == []


@pytest.mark.parametrize(
    ("presses", "calls"),
    [(("yes",), []), (("yes", "no"), []), (("no", "no"), [UNDO])],
)
async def test_only_the_first_mismatch_removes_the_wine(repository, account, presses, calls):
    request_id = shown_request(repository)
    services = services_with(repository, account)
    for press in presses:
        await handle_result_feedback(
            callback(f"feedback:{press}:{request_id}", with_message=False), services, FakeMaxApi()
        )
    await account.history.join()

    assert [path for path, _, _ in account.calls] == calls


async def test_a_selected_alternative_replaces_the_shown_wine(repository, account):
    request_id = shown_request(repository)
    services = services_with(repository, account)
    await handle_result_feedback(
        callback(f"feedback:no:{request_id}", with_message=False), services, FakeMaxApi()
    )
    api = FakeMaxApi()

    await handle_alternative_feedback(
        callback(f"alternative:3:{request_id}", with_message=False), services, api
    )
    await handle_alternative_feedback(
        callback(f"alternative:3:{request_id}", with_message=False), services, api
    )
    await account.history.join()

    assert notifications(api) == ["Спасибо! Ответ сохранён.", "Ответ уже сохранён."]
    assert account.calls[1:] == [
        (
            RECORD,
            {
                "user_id": USER_ID,
                "slug": "wine-3",
                "wine_snapshot": {"name": "Вино 3"},
                "replaces": "wine-1",
                "at": 1000,
            },
            f"Bearer {TOKEN}",
        )
    ]


async def test_nothing_of_these_sends_nothing(repository, account):
    request_id = shown_request(repository)
    services = services_with(repository, account)
    await handle_result_feedback(
        callback(f"feedback:no:{request_id}", with_message=False), services, FakeMaxApi()
    )
    await account.history.join()
    account.calls.clear()
    api = FakeMaxApi()

    await handle_alternative_feedback(
        callback(f"alternative:0:{request_id}", with_message=False), services, api
    )
    await account.history.join()

    assert notifications(api) == ["Спасибо! Ответ сохранён."]
    assert account.calls == []


async def test_feedback_through_the_router_answers_as_usual_when_the_account_fails(
    repository, account, caplog
):
    caplog.set_level(logging.WARNING)
    account.answer = httpx.Response(503, json={"error": "unavailable"})
    request_id = shown_request(repository)
    api = FakeMaxApi()
    handlers = BotHandlers(services_with(repository, account), api, work_queue=None)

    await handlers.on_callback(callback(f"feedback:no:{request_id}", with_message=False))
    await handlers.on_callback(callback(f"alternative:2:{request_id}", with_message=False))
    await account.history.join()

    assert notifications(api) == ["Спасибо! Выберите возможный вариант.", "Спасибо! Ответ сохранён."]
    assert [path for path, _, _ in account.calls] == [UNDO, RECORD]
    assert caplog.text.count("HTTP 503 unavailable") == 2


async def test_the_card_time_is_the_end_of_the_last_delivery(repository, account):
    # A card at 23:58 and a press after midnight (Moscow) must change the day of the card.
    request_id = shown_request(repository)
    for step, started_at_ms, duration_ms, outcome in (
        ("result_delivery", 1_792_000_000_000, 900, "ok"),
        ("result_delivery", 1_792_090_000_000, 1_500, "ok"),
        ("result_delivery", 1_792_095_000_000, 100, "failed"),
        ("quality", 1_792_099_000_000, 10, "ok"),
    ):
        repository.record_step_timing(
            request_id=request_id,
            step=step,
            started_at_ms=started_at_ms,
            duration_ms=duration_ms,
            outcome=outcome,
        )
    services = services_with(repository, account)

    await handle_result_feedback(
        callback(f"feedback:no:{request_id}", with_message=False), services, FakeMaxApi()
    )
    await handle_alternative_feedback(
        callback(f"alternative:2:{request_id}", with_message=False), services, FakeMaxApi()
    )
    await account.history.join()

    assert [(path, body["at"]) for path, body, _ in account.calls] == [
        (UNDO, 1_792_090_001),
        (RECORD, 1_792_090_001),
    ]


def test_an_unknown_card_time_is_omitted():
    services = SimpleNamespace(repository=SimpleNamespace(step_timings=lambda request_id: []))

    assert _result_card_time(services, SimpleNamespace(request_id="r", received_at=0)) is None
