"""«Винный дневник» history records from the chat (plan `docs/plans/07_diary-history-and-saved.md`)."""

import json
import logging
from types import SimpleNamespace

import httpx
import pytest
from chto_za_vino_core.diary import DiaryHistory
from chto_za_vino_core.files import ArtifactStore, ImageStore
from test_feedback import FakeCallback, card, recognized_request
from test_image_document import FakeDocumentMessage, FakeQueue
from test_image_document import services as message_services
from test_processor_quality import (
    ADMIN_USER_ID,
    AdvisoryQualityInspector,
    FakeBot,
    FakeMatcher,
    SafeModerator,
    jpeg,
)

from chto_za_vino_bot.app import (
    AlbumReceiptTracker,
    PhotoJob,
    PhotoProcessor,
    _result_card_time,
    enqueue_photo_message,
    handle_alternative_feedback,
    handle_result_feedback,
)
from chto_za_vino_bot.storage import CandidateRecord, Repository

TOKEN = "t" * 40
USER_ID = 200
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


class SilentBot(FakeBot):
    """Telegram refuses every message."""

    async def send_message(self, chat_id: int, text: str, **kwargs: object):
        raise RuntimeError("Telegram is unavailable")

    async def send_photo(self, **kwargs: object) -> None:
        raise RuntimeError("Telegram is unavailable")


async def process(tmp_path, history, *, api_request=False, matcher=None, bot=None):
    repository = Repository(tmp_path / "bot.sqlite3")
    if api_request:
        request_id = repository.create_api_request(now=1000)
    else:
        reservation = repository.reserve(
            chat_id=100,
            message_id=10,
            user_id=USER_ID,
            username="tester",
            first_name="Test",
            last_name=None,
            file_id="file-1",
            file_unique_id="unique-1",
            now=1000,
            limit=50,
            window_seconds=3600,
        )
        request_id = reservation.request_id
    bot = bot or FakeBot(jpeg())
    services = SimpleNamespace(
        settings=SimpleNamespace(
            max_image_bytes=20 * 1024 * 1024,
            match_min_score=0.70,
            match_min_margin=0.015,
            admin_user_id=ADMIN_USER_ID,
        ),
        repository=repository,
        store=ImageStore(tmp_path / "images"),
        artifact_store=ArtifactStore(tmp_path / "images"),
        moderator=SafeModerator(),
        quality_inspector=AdvisoryQualityInspector(),
        matcher=matcher or FakeMatcher(),
        image_loader=None,
        rejection_image=b"unused",
        history=history,
    )
    await PhotoProcessor(services, bot).process(
        PhotoJob(
            request_id=request_id,
            chat_id=0 if api_request else 100,
            source_message_id=10,
            received_at=1000,
            file_id="file-1",
            status_message_id=None,
            user_id=0 if api_request else USER_ID,
            status_enabled=False,
            image_body=jpeg() if api_request else None,
            delivery_enabled=not api_request,
        )
    )
    status = repository.admin_request(request_id).status
    repository.close()
    if history is not None:
        await history.join()
    return status, bot


WINE_1_SNAPSHOT = {
    "name": "Тестовое вино wine-1",
    "color": "Красное",
    "sugar": "Сухое",
    "grapes": ["Пино Нуар"],
}


async def test_a_result_card_records_the_shown_wine(tmp_path, account):
    status, bot = await process(tmp_path, account.history)

    assert status == "recognized"
    assert len(bot.photos) == 1
    assert account.calls == [
        (
            RECORD,
            {"user_id": USER_ID, "slug": "wine-1", "wine_snapshot": WINE_1_SNAPSHOT},
            f"Bearer {TOKEN}",
        )
    ]


async def test_a_tentative_card_is_recorded_too(tmp_path, account):
    status, bot = await process(
        tmp_path, account.history, matcher=FakeMatcher(scores=(0.5, 0.49, 0.3, 0.2))
    )

    assert status == "abstained"
    assert "Пришлите еще фотографию" in bot.photos[0]["caption"]
    assert [(path, body["slug"]) for path, body, _ in account.calls] == [(RECORD, "wine-1")]


async def test_no_record_without_a_wine_card(tmp_path, account):
    status, _ = await process(tmp_path, account.history, matcher=FakeMatcher(count=0))

    assert status == "abstained"
    assert account.calls == []


async def test_an_http_api_request_records_nothing(tmp_path, account):
    status, bot = await process(tmp_path, account.history, api_request=True)

    assert status == "recognized"
    assert bot.photos == []
    assert account.calls == []


async def test_an_undelivered_card_records_nothing(tmp_path, account):
    status, _ = await process(tmp_path, account.history, bot=SilentBot(jpeg()))

    assert status == "recognized"
    assert account.calls == []


async def test_the_bot_works_without_the_account_service(tmp_path):
    status, bot = await process(tmp_path, None)

    assert status == "recognized"
    assert len(bot.photos) == 1


async def test_an_account_failure_changes_nothing_in_the_chat(tmp_path, account, caplog):
    account.answer = httpx.ConnectError("refused")

    status, bot = await process(tmp_path, account.history)

    assert status == "recognized"
    assert len(bot.photos) == 1
    assert len(account.calls) == 1
    assert "Diary history record failed: ConnectError" in caplog.text
    assert str(USER_ID) not in caplog.text
    assert "wine-1" not in caplog.text


async def test_a_photo_job_carries_the_sender(tmp_path):
    bot_services = message_services(tmp_path, adult=True)
    queue = FakeQueue()

    await enqueue_photo_message(
        FakeDocumentMessage("image/jpeg"), bot_services, queue, AlbumReceiptTracker()
    )

    assert queue.jobs[0].user_id == USER_ID
    bot_services.repository.close()


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


async def test_a_mismatch_removes_the_shown_wine(repository, account):
    request_id = shown_request(repository)
    callback = FakeCallback(f"feedback:no:{request_id}", USER_ID)

    await handle_result_feedback(
        callback, SimpleNamespace(repository=repository, history=account.history)
    )
    await account.history.join()

    assert callback.answers == [("Спасибо! Выберите возможный вариант.", False)]
    # The request has no delivery step: the card time is the receipt time.
    assert account.calls == [
        (UNDO, {"user_id": USER_ID, "slug": "wine-1", "at": 1000}, f"Bearer {TOKEN}")
    ]


async def test_a_mismatch_of_another_user_sends_nothing(repository, account):
    request_id = shown_request(repository)
    callback = FakeCallback(f"feedback:no:{request_id}", USER_ID + 1)

    await handle_result_feedback(
        callback, SimpleNamespace(repository=repository, history=account.history)
    )
    await account.history.join()

    assert callback.answers == [("Эта оценка недоступна.", True)]
    assert account.calls == []


@pytest.mark.parametrize(
    ("presses", "calls"),
    [(("yes",), []), (("yes", "no"), []), (("no", "no"), [UNDO])],
)
async def test_only_the_first_mismatch_removes_the_wine(repository, account, presses, calls):
    request_id = shown_request(repository)
    services = SimpleNamespace(repository=repository, history=account.history)
    for press in presses:
        await handle_result_feedback(
            FakeCallback(f"feedback:{press}:{request_id}", USER_ID), services
        )
    await account.history.join()

    assert [path for path, _, _ in account.calls] == calls


async def test_a_selected_alternative_replaces_the_shown_wine(repository, account):
    request_id = shown_request(repository)
    services = SimpleNamespace(repository=repository, history=account.history)
    await handle_result_feedback(FakeCallback(f"feedback:no:{request_id}", USER_ID), services)
    callback = FakeCallback(f"alternative:3:{request_id}", USER_ID)

    await handle_alternative_feedback(callback, services)
    await account.history.join()

    assert callback.answers == [("Спасибо! Ответ сохранён.", False)]
    assert account.calls[-1] == (
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


async def test_nothing_of_these_sends_nothing(repository, account):
    request_id = shown_request(repository)
    services = SimpleNamespace(repository=repository, history=account.history)
    await handle_result_feedback(FakeCallback(f"feedback:no:{request_id}", USER_ID), services)
    await account.history.join()
    account.calls.clear()
    callback = FakeCallback(f"alternative:0:{request_id}", USER_ID)

    await handle_alternative_feedback(callback, services)
    await account.history.join()

    assert callback.answers == [("Спасибо! Ответ сохранён.", False)]
    assert account.calls == []


async def test_feedback_answers_as_usual_when_the_account_service_fails(
    repository, account, caplog
):
    caplog.set_level(logging.WARNING)
    account.answer = httpx.Response(503, json={"error": "unavailable"})
    request_id = shown_request(repository)
    services = SimpleNamespace(repository=repository, history=account.history)
    rejection = FakeCallback(f"feedback:no:{request_id}", USER_ID)
    selection = FakeCallback(f"alternative:2:{request_id}", USER_ID)

    await handle_result_feedback(rejection, services)
    await handle_alternative_feedback(selection, services)
    await account.history.join()

    assert rejection.answers == [("Спасибо! Выберите возможный вариант.", False)]
    assert selection.answers == [("Спасибо! Ответ сохранён.", False)]
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
    services = SimpleNamespace(repository=repository, history=account.history)

    await handle_result_feedback(FakeCallback(f"feedback:no:{request_id}", USER_ID), services)
    await handle_alternative_feedback(
        FakeCallback(f"alternative:2:{request_id}", USER_ID), services
    )
    await account.history.join()

    assert [(path, body["at"]) for path, body, _ in account.calls] == [
        (UNDO, 1_792_090_001),
        (RECORD, 1_792_090_001),
    ]


def test_an_unknown_card_time_is_omitted():
    services = SimpleNamespace(repository=SimpleNamespace(step_timings=lambda request_id: []))

    assert _result_card_time(services, SimpleNamespace(request_id="r", received_at=0)) is None
