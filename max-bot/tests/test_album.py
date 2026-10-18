"""Album, queue receipt, and result delivery tests.

A MAX album is one message with two or more image or video attachments. The Telegram bot gets
one message for each album photo and needs an album receipt tracker. The MAX bot selects the
receipt owner inside one update: the first admitted image.
"""

import io
from types import SimpleNamespace

import pytest
from chto_za_vino_core.files import ArtifactStore
from chto_za_vino_core.result_card import format_result_caption
from chto_za_vino_core.wine import Wine
from chto_za_vino_core.work_queue import QueueCapacityError
from fakes import (
    DIALOG_CHAT_ID,
    USER_ID,
    FakeMaxApi,
    button_texts,
    image,
    keyboard_buttons,
    message,
)
from PIL import Image

from chto_za_vino_max_bot.app import (
    CONTENT_REJECTED_TEXT,
    QUEUE_FULL_TEXT,
    PhotoJob,
    PhotoProcessor,
    alternative_keyboard,
    enqueue_photo_message,
    moderation_appeal_keyboard,
    result_feedback_keyboard,
)
from chto_za_vino_max_bot.profile import AGE_GATE_TEXT
from chto_za_vino_max_bot.storage import Repository, SentMessage

ALBUM_RECEIPT = (
    "Фотографии приняты и поставлены в очередь.\nПозиция: 1; обработка начнётся сразу."
)
SINGLE_RECEIPT = (
    "Фотография принята и поставлена в очередь.\nПозиция: 1; обработка начнётся сразу."
)
ALBUM_STATUS = "Результаты альбома отправляются по мере готовности."
LINK_ONLY = [["Открыть страницу вина"]]


class FakeQueue:
    """The queue interface of `enqueue_photo_message`. `capacity` makes `submit` fail.

    `failures` makes that many submits fail before capacity becomes available again.
    """

    def __init__(
        self, *, at_capacity: bool = False, capacity: int | None = None, failures: int = 0
    ) -> None:
        self.at_capacity = at_capacity
        self.capacity = capacity
        self.failures = failures
        self.jobs: list[PhotoJob] = []

    @property
    def next_position(self) -> int:
        return len(self.jobs) + 1

    def estimate_wait_seconds(self, position: int) -> int:
        return max(0, position - 1) * 20

    def submit(self, job: PhotoJob) -> None:
        if self.failures:
            self.failures -= 1
            raise QueueCapacityError("queue capacity is full")
        if self.capacity is not None and len(self.jobs) >= self.capacity:
            raise QueueCapacityError("queue capacity is full")
        self.jobs.append(job)


@pytest.fixture
def repository(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    yield repository
    repository.close()


def queue_services(
    repository: Repository,
    *,
    rate_limit: int = 25,
    adult: bool = True,
) -> SimpleNamespace:
    if adult:
        repository.set_age_status(
            user_id=USER_ID,
            username="tester",
            first_name="Test",
            last_name=None,
            status="adult",
            now=1,
        )
    return SimpleNamespace(
        repository=repository,
        settings=SimpleNamespace(rate_limit=rate_limit, rate_window_seconds=3600),
    )


def total_requests(repository: Repository) -> int:
    return repository.stats(USER_ID, 2**31, 2**31).total


def counted_requests(repository: Repository) -> int:
    """The requests in the rate limit. A queue-capacity rejection is not counted."""
    return repository.stats(USER_ID, 2**31, 2**31).user_window


def request_states(repository: Repository) -> list[tuple[str, str | None]]:
    """The status and error code of each request, in reservation order."""
    records, _ = repository.list_admin_requests(page=1, page_size=20)
    return [(record.status, record.error_code) for record in reversed(records)]


def reserve(repository: Repository, *, message_id: str, photo_index: int = 0) -> str:
    photo = image(photo_index + 1)
    reservation = repository.reserve(
        chat_id=DIALOG_CHAT_ID,
        chat_type="dialog",
        message_id=message_id,
        photo_index=photo_index,
        user_id=USER_ID,
        username="tester",
        first_name="Test",
        last_name=None,
        photo_id=photo.photo_id,
        photo_url=photo.url,
        photo_token=photo.token,
        now=1000,
        limit=50,
        window_seconds=3600,
    )
    assert reservation.request_id is not None
    return reservation.request_id


def result_jpeg() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (32, 64), "white").save(buffer, format="JPEG")
    return buffer.getvalue()


def sample_wine() -> Wine:
    return Wine(
        slug="test-wine",
        name="Тестовое вино",
        page_url="https://vino-svoe.ru/wines/test-wine",
        producer=None,
        category="Красное",
        color="Рубиновый",
        grapes="Пино Нуар",
        sugar="Сухое",
        image_url=None,
    )


def photo_job(request_id: str, **fields: object) -> PhotoJob:
    values: dict[str, object] = {
        "chat_id": DIALOG_CHAT_ID,
        "source_message_id": "mid.source",
        "received_at": 1000,
        "photo_url": image(1).url,
        "status_message_id": "mid.status",
    }
    values.update(fields)
    return PhotoJob(request_id=request_id, **values)


def uploaded(number: int) -> dict[str, object]:
    """The image attachment of upload number `number` of FakeMaxApi."""
    return {
        "type": "image",
        "payload": {"photos": {str(number): {"token": f"uploaded-{number}"}}},
    }


def status_edit(text: str, attachments: list[dict[str, object]] | None = None):
    return {
        "chat_id": DIALOG_CHAT_ID,
        "message_id": "mid.status",
        "text": text,
        "attachments": attachments or [],
        "text_format": "html",
    }


# Queue admission


async def test_album_photos_create_separate_ordered_jobs(repository):
    services = queue_services(repository)
    api = FakeMaxApi()
    queue = FakeQueue()
    album = message(message_id="mid.album", images=(image(1), image(2)))

    await enqueue_photo_message(album, services, api, queue)

    assert [job.photo_url for job in queue.jobs] == [image(1).url, image(2).url]
    assert [job.photo_id for job in queue.jobs] == [9001, 9002]
    assert [job.photo_index for job in queue.jobs] == [0, 1]
    assert [job.source_message_id for job in queue.jobs] == ["mid.album", "mid.album"]
    assert [job.status_message_id for job in queue.jobs] == ["mid.bot-1", None]
    assert [job.feedback_enabled for job in queue.jobs] == [False, False]
    assert [job.status_enabled for job in queue.jobs] == [True, False]
    assert [job.keep_status for job in queue.jobs] == [True, False]
    assert {(job.chat_id, job.chat_type, job.user_id) for job in queue.jobs} == {
        (DIALOG_CHAT_ID, "dialog", USER_ID)
    }
    replies = api.calls_of("send_message")
    assert len(replies) == 1
    assert replies[0]["text"].startswith("Фотографии приняты")
    assert "Позиция: 1" in replies[0]["text"]
    assert replies[0]["reply_to"] == "mid.album"
    assert total_requests(repository) == 2
    assert request_states(repository) == [("queued", None), ("queued", None)]
    assert [item.feedback_enabled for item in repository.pending_requests()] == [False, False]


async def test_each_album_message_gets_its_own_receipt(repository):
    # Replaces the Telegram receipt tracker expiry test: a new album is a new message.
    services = queue_services(repository)
    api = FakeMaxApi()
    queue = FakeQueue()

    await enqueue_photo_message(
        message(message_id="mid.album-1", images=(image(1), image(2))), services, api, queue
    )
    await enqueue_photo_message(
        message(message_id="mid.album-2", images=(image(3), image(4))), services, api, queue
    )

    replies = api.calls_of("send_message")
    assert [reply["reply_to"] for reply in replies] == ["mid.album-1", "mid.album-2"]
    assert replies[0]["text"] == ALBUM_RECEIPT
    assert replies[1]["text"] == (
        "Фотографии приняты и поставлены в очередь.\n"
        "Позиция: 3; примерное ожидание: около 40 сек."
    )
    assert [job.status_message_id for job in queue.jobs] == ["mid.bot-1", None, "mid.bot-2", None]
    assert [job.keep_status for job in queue.jobs] == [True, False, True, False]


async def test_album_replay_skips_the_admitted_images(repository):
    # Replaces the Telegram receipt tracker capacity test: a repeated update is idempotent.
    services = queue_services(repository)
    api = FakeMaxApi()
    queue = FakeQueue()
    album = message(message_id="mid.album", images=(image(1), image(2)))

    await enqueue_photo_message(album, services, api, queue)
    await enqueue_photo_message(album, services, api, queue)

    assert [job.photo_index for job in queue.jobs] == [0, 1]
    assert len(api.calls_of("send_message")) == 1
    assert total_requests(repository) == 2


async def test_album_replay_admits_only_the_missing_images(repository):
    services = queue_services(repository, rate_limit=2)
    api = FakeMaxApi()
    queue = FakeQueue()
    album = message(message_id="mid.album", images=(image(1), image(2), image(3)))

    await enqueue_photo_message(album, services, api, queue)
    services.settings.rate_limit = 3
    await enqueue_photo_message(album, services, api, queue)

    assert [job.photo_index for job in queue.jobs] == [0, 1, 2]
    assert [job.photo_url for job in queue.jobs] == [image(1).url, image(2).url, image(3).url]
    assert total_requests(repository) == 3
    texts = [reply["text"] for reply in api.calls_of("send_message")]
    assert texts[0] == ALBUM_RECEIPT
    assert texts[1].startswith("Лимит — 2 фотографий за один час.")
    # The first admitted image of the second handling owns its receipt.
    assert texts[2].startswith("Фотографии приняты")
    assert len(texts) == 3
    assert (queue.jobs[2].status_message_id, queue.jobs[2].keep_status) == ("mid.bot-3", True)


async def test_single_image_message_gets_a_single_photo_receipt(repository):
    services = queue_services(repository)
    api = FakeMaxApi()
    queue = FakeQueue()

    await enqueue_photo_message(
        message(message_id="mid.single", images=(image(1),)), services, api, queue
    )

    assert [(reply["text"], reply["reply_to"]) for reply in api.calls_of("send_message")] == [
        (SINGLE_RECEIPT, "mid.single")
    ]
    (job,) = queue.jobs
    assert job.status_message_id == "mid.bot-1"
    assert (job.feedback_enabled, job.status_enabled, job.keep_status) == (True, True, False)
    assert (job.photo_index, job.photo_source) == (0, "body")
    assert [item.feedback_enabled for item in repository.pending_requests()] == [True]


async def test_image_and_video_message_is_an_album(repository):
    services = queue_services(repository)
    api = FakeMaxApi()
    queue = FakeQueue()
    mixed = message(
        message_id="mid.mixed", images=(image(1),), media_count=2, photo_source="forward"
    )

    await enqueue_photo_message(mixed, services, api, queue)

    assert [reply["text"] for reply in api.calls_of("send_message")] == [ALBUM_RECEIPT]
    (job,) = queue.jobs
    assert (job.feedback_enabled, job.status_enabled, job.keep_status) == (False, True, True)
    assert job.photo_source == "forward"
    (pending,) = repository.pending_requests()
    assert (pending.feedback_enabled, pending.photo_source) == (False, "forward")


async def test_rate_limit_in_the_middle_of_an_album_gives_one_reply_per_photo(repository):
    services = queue_services(repository, rate_limit=2)
    api = FakeMaxApi()
    queue = FakeQueue()
    album = message(message_id="mid.album", images=tuple(image(index) for index in range(1, 5)))

    await enqueue_photo_message(album, services, api, queue)

    assert [job.photo_index for job in queue.jobs] == [0, 1]
    replies = api.calls_of("send_message")
    limit = "Лимит — 2 фотографий за один час. Попробуйте снова примерно через 60 мин."
    # As in Telegram, each rejected image gets its own reply. MAX has one album message.
    assert [(reply["text"], reply["reply_to"]) for reply in replies] == [
        (ALBUM_RECEIPT, "mid.album"),
        (limit, "mid.album"),
        (limit, "mid.album"),
    ]
    # The admitted images keep their requests. The remaining images use no quota.
    assert total_requests(repository) == 2
    assert request_states(repository) == [("queued", None), ("queued", None)]


async def test_full_queue_rejects_an_album_with_one_reply_per_photo(repository):
    services = queue_services(repository)
    api = FakeMaxApi()
    queue = FakeQueue(at_capacity=True)

    await enqueue_photo_message(
        message(message_id="mid.album", images=(image(1), image(2))), services, api, queue
    )

    assert queue.jobs == []
    assert [(reply["text"], reply["reply_to"]) for reply in api.calls_of("send_message")] == [
        (QUEUE_FULL_TEXT, "mid.album"),
        (QUEUE_FULL_TEXT, "mid.album"),
    ]
    assert total_requests(repository) == 0


async def test_queue_rejection_of_the_receipt_owner_edits_the_receipt(repository):
    services = queue_services(repository)
    api = FakeMaxApi()
    queue = FakeQueue(capacity=0)

    await enqueue_photo_message(
        message(message_id="mid.album", images=(image(1), image(2))), services, api, queue
    )

    assert queue.jobs == []
    # The failed receipt owner releases the receipt, so the next image claims a new one.
    assert [reply["text"] for reply in api.calls_of("send_message")] == [
        ALBUM_RECEIPT,
        ALBUM_RECEIPT,
    ]
    assert api.calls_of("edit_message") == [
        {
            "chat_id": DIALOG_CHAT_ID,
            "message_id": message_id,
            "text": QUEUE_FULL_TEXT,
            "attachments": [],
            "text_format": "html",
        }
        for message_id in ("mid.bot-1", "mid.bot-2")
    ]
    # Each image gets its own rejection. A rejected image does not use the rate limit.
    assert request_states(repository) == [
        ("queue_rejected", "queue_capacity"),
        ("queue_rejected", "queue_capacity"),
    ]
    assert counted_requests(repository) == 0


async def test_next_image_claims_a_new_receipt_after_a_failed_receipt_owner(repository):
    services = queue_services(repository)
    api = FakeMaxApi()
    queue = FakeQueue(failures=1)

    await enqueue_photo_message(
        message(message_id="mid.album", images=(image(1), image(2))), services, api, queue
    )

    # The first receipt shows the rejection. The second image gets its own receipt and status.
    assert [reply["text"] for reply in api.calls_of("send_message")] == [
        ALBUM_RECEIPT,
        ALBUM_RECEIPT,
    ]
    assert [call["text"] for call in api.calls_of("edit_message")] == [QUEUE_FULL_TEXT]
    (job,) = queue.jobs
    assert job.photo_index == 1
    assert job.status_message_id == "mid.bot-2"
    assert job.status_enabled is True
    assert job.keep_status is True


async def test_a_failed_receipt_edit_does_not_stop_the_album(repository):
    from chto_za_vino_max_bot.max_api import MaxApiError

    services = queue_services(repository)
    api = FakeMaxApi()
    api.fail_on["edit_message"] = MaxApiError(500, "internal", "temporary failure")
    queue = FakeQueue(failures=1)

    await enqueue_photo_message(
        message(message_id="mid.album", images=(image(1), image(2), image(3))),
        services,
        api,
        queue,
    )

    # The rejection edit of the first receipt fails. The next image claims a new receipt.
    assert [job.photo_index for job in queue.jobs] == [1, 2]
    assert [reply["text"] for reply in api.calls_of("send_message")] == [
        ALBUM_RECEIPT,
        ALBUM_RECEIPT,
    ]
    assert queue.jobs[0].status_message_id == "mid.bot-2"


async def test_a_failed_rejection_reply_does_not_stop_the_album(repository):
    from chto_za_vino_max_bot.max_api import MaxApiError

    services = queue_services(repository)
    api = FakeMaxApi()
    api.fail_on["send_message"] = MaxApiError(500, "internal", "temporary failure")

    await enqueue_photo_message(
        message(message_id="mid.album", images=(image(1), image(2), image(3))),
        services,
        api,
        FakeQueue(at_capacity=True),
    )

    # Each image still gets its own attempt after a failed reply.
    assert [reply["text"] for reply in api.calls_of("send_message")] == [QUEUE_FULL_TEXT] * 3


async def test_queue_rejection_in_the_middle_of_an_album_gives_one_reply_per_photo(repository):
    services = queue_services(repository)
    api = FakeMaxApi()
    queue = FakeQueue(capacity=1)
    album = message(message_id="mid.album", images=(image(1), image(2), image(3)))

    await enqueue_photo_message(album, services, api, queue)

    assert [job.photo_index for job in queue.jobs] == [0]
    assert [(reply["text"], reply["reply_to"]) for reply in api.calls_of("send_message")] == [
        (ALBUM_RECEIPT, "mid.album"),
        (QUEUE_FULL_TEXT, "mid.album"),
        (QUEUE_FULL_TEXT, "mid.album"),
    ]
    assert api.calls_of("edit_message") == []
    assert request_states(repository) == [
        ("queued", None),
        ("queue_rejected", "queue_capacity"),
        ("queue_rejected", "queue_capacity"),
    ]
    assert counted_requests(repository) == 1


async def test_age_gate_gives_one_reply_per_album_photo(repository):
    services = queue_services(repository, adult=False)
    api = FakeMaxApi()
    queue = FakeQueue()

    await enqueue_photo_message(
        message(message_id="mid.album", images=(image(1), image(2))), services, api, queue
    )

    replies = api.calls_of("send_message")
    assert len(replies) == 2
    for reply in replies:
        assert reply["text"] == AGE_GATE_TEXT
        assert reply["reply_to"] == "mid.album"
        assert reply["disable_link_preview"] is True
        assert button_texts(reply["attachments"]) == [["Мне есть 18 лет", "Мне нет 18 лет"]]
    assert queue.jobs == []
    assert total_requests(repository) == 0


# Result delivery


async def test_album_results_reply_to_the_source_message():
    api = FakeMaxApi()
    processor = PhotoProcessor(SimpleNamespace(image_loader=None), api)
    jobs = [
        photo_job(
            "request-1",
            source_message_id="mid.album",
            photo_index=0,
            status_message_id="mid.status-1",
            feedback_enabled=False,
        ),
        photo_job(
            "request-2",
            source_message_id="mid.album",
            photo_index=1,
            photo_url=image(2).url,
            status_message_id="mid.status-2",
            feedback_enabled=False,
        ),
    ]

    for job in jobs:
        await processor._send_result(job, sample_wine(), result_jpeg())

    sends = api.calls_of("send_message")
    assert len(sends) == 2
    assert [send["reply_to"] for send in sends] == ["mid.album", "mid.album"]
    assert [send["attachments"][0] for send in sends] == [uploaded(1), uploaded(2)]
    assert [button_texts(send["attachments"]) for send in sends] == [LINK_ONLY, LINK_ONLY]
    assert api.calls_of("delete_message") == [
        {"chat_id": DIALOG_CHAT_ID, "message_id": "mid.status-1"},
        {"chat_id": DIALOG_CHAT_ID, "message_id": "mid.status-2"},
    ]


async def test_album_receipt_owner_keeps_its_status_for_the_other_results():
    api = FakeMaxApi()
    processor = PhotoProcessor(SimpleNamespace(image_loader=None), api)
    job = photo_job(
        "request-1", source_message_id="mid.album", feedback_enabled=False, keep_status=True
    )

    await processor._send_result(job, sample_wine(), result_jpeg())

    (send,) = api.calls_of("send_message")
    assert send["reply_to"] == "mid.album"
    assert button_texts(send["attachments"]) == LINK_ONLY
    assert api.calls_of("delete_message") == []
    assert api.calls_of("edit_message") == [status_edit(ALBUM_STATUS)]
    assert job.status_message_id == "mid.status"


async def test_single_photo_result_has_feedback_buttons():
    api = FakeMaxApi()
    processor = PhotoProcessor(SimpleNamespace(image_loader=None), api)

    await processor._send_result(photo_job("request-1"), sample_wine(), result_jpeg())

    rows = keyboard_buttons(api.calls_of("send_message")[0]["attachments"])
    assert rows[0] == [
        {
            "type": "link",
            "text": "Открыть страницу вина",
            "url": "https://vino-svoe.ru/wines/test-wine",
        }
    ]
    buttons = rows[1]
    assert [button["text"] for button in buttons] == ["✅ Совпало", "❌ Не совпало"]
    assert [button["payload"] for button in buttons] == [
        "feedback:yes:request-1",
        "feedback:no:request-1",
    ]
    assert [button["type"] for button in buttons] == ["callback", "callback"]


async def test_result_is_stored_for_the_callback_rebuild(repository, tmp_path):
    request_id = reserve(repository, message_id="mid.source")
    api = FakeMaxApi()
    services = SimpleNamespace(
        image_loader=None,
        repository=repository,
        artifact_store=ArtifactStore(tmp_path / "images"),
    )
    processor = PhotoProcessor(services, api)
    job = photo_job(request_id)

    await processor._send_result(job, sample_wine(), result_jpeg())

    caption = format_result_caption(sample_wine())
    (upload,) = api.calls_of("upload_image")
    assert (upload["filename"], upload["content_type"]) == ("wine-result.jpg", "image/jpeg")
    (send,) = api.calls_of("send_message")
    assert send["text"] == caption
    assert send["text_format"] == "html"
    assert send["reply_to"] == "mid.source"
    assert send["attachments"] == [
        uploaded(1),
        result_feedback_keyboard(request_id, "https://vino-svoe.ru/wines/test-wine"),
    ]
    assert repository.sent_message("mid.bot-1") == SentMessage(
        message_id="mid.bot-1",
        request_id=request_id,
        chat_id=DIALOG_CHAT_ID,
        text=caption,
        text_format="html",
        photo_token="uploaded-1",
    )
    assert [item.artifact_key for item in repository.artifacts(request_id)] == ["max_result"]
    assert api.calls_of("delete_message") == [
        {"chat_id": DIALOG_CHAT_ID, "message_id": "mid.status"}
    ]
    assert job.status_message_id is None


async def test_status_shows_done_when_its_removal_fails():
    api = FakeMaxApi()
    api.fail_on["delete_message"] = RuntimeError("MAX delete failure")
    processor = PhotoProcessor(SimpleNamespace(image_loader=None), api)
    job = photo_job("request-1")

    await processor._send_result(job, sample_wine(), result_jpeg())

    assert api.calls_of("delete_message") == [
        {"chat_id": DIALOG_CHAT_ID, "message_id": "mid.status"}
    ]
    assert api.calls_of("edit_message") == [status_edit("Готово.")]


@pytest.mark.parametrize("method", ["upload_image", "send_message"])
async def test_result_photo_failure_falls_back_to_the_status_text(method):
    api = FakeMaxApi()
    api.fail_on[method] = RuntimeError("MAX photo failure")
    processor = PhotoProcessor(SimpleNamespace(image_loader=None), api)

    await processor._send_result(photo_job("request-1"), sample_wine(), result_jpeg())

    assert api.calls_of("edit_message") == [
        status_edit(
            format_result_caption(sample_wine()),
            [result_feedback_keyboard("request-1", "https://vino-svoe.ru/wines/test-wine")],
        )
    ]
    assert api.calls_of("delete_message") == []


async def test_album_result_failure_without_a_status_still_reaches_the_user():
    api = FakeMaxApi()
    api.fail_on["upload_image"] = RuntimeError("MAX upload failure")
    processor = PhotoProcessor(SimpleNamespace(image_loader=None), api)
    job = photo_job(
        "request-2",
        source_message_id="mid.album",
        photo_index=1,
        status_message_id=None,
        feedback_enabled=False,
        status_enabled=False,
    )

    await processor._send_result(job, sample_wine(), result_jpeg())

    replies = api.calls_of("send_message")
    assert [reply["text"] for reply in replies] == [format_result_caption(sample_wine())]
    assert replies[0]["reply_to"] == "mid.album"
    assert button_texts(replies[0]["attachments"]) == LINK_ONLY


def test_alternative_keyboard_has_three_candidates_and_none():
    wines = [
        (
            rank,
            Wine(
                slug=f"wine-{rank}",
                name=f"Вино {rank}",
                page_url=f"https://vino-svoe.ru/wines/wine-{rank}",
                producer=None,
                category=None,
                color=None,
                grapes=None,
                sugar=None,
                image_url=None,
            ),
        )
        for rank in (2, 3, 4)
    ]

    rows = keyboard_buttons([alternative_keyboard("request-1", wines)])

    assert [row[0]["text"] for row in rows] == [
        "2. Вино 2",
        "3. Вино 3",
        "4. Вино 4",
        "Ничего из этого",
    ]
    assert [row[0]["payload"] for row in rows] == [
        "alternative:2:request-1",
        "alternative:3:request-1",
        "alternative:4:request-1",
        "alternative:0:request-1",
    ]


# Rejection delivery


async def test_rejection_uses_illustration_and_replies_to_source_photo():
    api = FakeMaxApi()
    processor = PhotoProcessor(SimpleNamespace(rejection_image=b"rejection-png"), api)
    job = photo_job("request-1")

    await processor._send_rejection(job)

    assert api.calls_of("upload_image") == [
        {
            "filename": "content-rejected.png",
            "content_type": "image/png",
            "size": len(b"rejection-png"),
        }
    ]
    sends = api.calls_of("send_message")
    assert len(sends) == 1
    assert sends[0]["text"] == CONTENT_REJECTED_TEXT
    assert "Контент признан неподходящим" in sends[0]["text"]
    assert sends[0]["attachments"][0] == uploaded(1)
    appeal = keyboard_buttons(sends[0]["attachments"])[0][0]
    assert appeal["text"] == "Сообщить об ошибке фильтра"
    assert appeal["payload"] == "moderation_error:request-1"
    assert sends[0]["reply_to"] == "mid.source"
    assert api.calls_of("delete_message") == [
        {"chat_id": DIALOG_CHAT_ID, "message_id": "mid.status"}
    ]
    assert job.status_message_id is None


@pytest.mark.parametrize("method", ["upload_image", "send_message"])
async def test_rejection_photo_failure_falls_back_to_status_text(method):
    api = FakeMaxApi()
    api.fail_on[method] = RuntimeError("MAX photo failure")
    processor = PhotoProcessor(SimpleNamespace(rejection_image=b"rejection-png"), api)
    job = photo_job("request-1")

    await processor._send_rejection(job)

    edits = api.calls_of("edit_message")
    assert len(edits) == 1
    assert "Контент признан неподходящим" in edits[0]["text"]
    assert edits[0] == status_edit(CONTENT_REJECTED_TEXT, [moderation_appeal_keyboard("request-1")])
    assert api.calls_of("delete_message") == []


async def test_rejection_without_a_status_replies_with_the_appeal_keyboard(repository):
    request_id = reserve(repository, message_id="mid.album", photo_index=1)
    api = FakeMaxApi()
    api.fail_on["upload_image"] = RuntimeError("MAX upload failure")
    services = SimpleNamespace(rejection_image=b"rejection-png", repository=repository)
    processor = PhotoProcessor(services, api)
    job = photo_job(
        request_id,
        source_message_id="mid.album",
        photo_index=1,
        status_message_id=None,
        feedback_enabled=False,
        status_enabled=False,
    )

    await processor._send_rejection(job)

    assert api.calls_of("send_message") == [
        {
            "chat_id": DIALOG_CHAT_ID,
            "text": CONTENT_REJECTED_TEXT,
            "attachments": [moderation_appeal_keyboard(request_id)],
            "reply_to": "mid.album",
            "text_format": "html",
            "disable_link_preview": False,
        }
    ]
    stored = repository.sent_message("mid.bot-1")
    assert stored is not None
    assert (stored.request_id, stored.text, stored.photo_token) == (
        request_id,
        CONTENT_REJECTED_TEXT,
        None,
    )


async def test_rejection_illustration_is_uploaded_once_until_a_send_fails(repository):
    request_ids = [reserve(repository, message_id=f"mid.source-{index}") for index in range(4)]
    api = FakeMaxApi()
    services = SimpleNamespace(rejection_image=b"rejection-png", repository=repository)
    processor = PhotoProcessor(services, api)

    def job(index: int) -> PhotoJob:
        return photo_job(
            request_ids[index],
            source_message_id=f"mid.source-{index}",
            status_message_id=None,
            status_enabled=False,
        )

    await processor._send_rejection(job(0))
    await processor._send_rejection(job(1))
    api.fail_on["send_message"] = RuntimeError("MAX send failure")
    await processor._send_rejection(job(2))
    del api.fail_on["send_message"]
    await processor._send_rejection(job(3))

    # A failed send can mean an invalid cached upload, so the next rejection uploads again.
    assert len(api.calls_of("upload_image")) == 2
    illustrations = [
        send["attachments"][0]
        for send in api.calls_of("send_message")
        if send["attachments"][0]["type"] == "image"
    ]
    assert illustrations == [uploaded(1), uploaded(1), uploaded(1), uploaded(2)]
    assert [repository.sent_message(f"mid.bot-{number}").photo_token for number in (1, 2, 3)] == [
        "uploaded-1",
        "uploaded-1",
        "uploaded-2",
    ]


class FlakySendApi(FakeMaxApi):
    """The first `failures` sends fail. Later sends succeed."""

    def __init__(self, failures: int) -> None:
        super().__init__()
        self.failures = failures

    async def send_message(self, chat_id, **fields):
        if self.failures:
            self.failures -= 1
            raise RuntimeError("MAX send failure")
        return await super().send_message(chat_id, **fields)


async def test_receipt_failure_loses_only_its_image_and_the_next_image_owns_the_receipt(
    repository,
):
    services = queue_services(repository)
    api = FlakySendApi(failures=1)
    queue = FakeQueue()
    album = message(message_id="mid.album", images=(image(1), image(2), image(3)))

    await enqueue_photo_message(album, services, api, queue)

    # The Telegram bot loses one photo and releases the receipt claim for the next photo.
    assert request_states(repository) == [
        ("queue_rejected", "max_status"),
        ("queued", None),
        ("queued", None),
    ]
    assert [job.photo_index for job in queue.jobs] == [1, 2]
    assert [job.status_enabled for job in queue.jobs] == [True, False]
    assert [job.keep_status for job in queue.jobs] == [True, False]
    assert queue.jobs[0].status_message_id == "mid.bot-1"


async def test_forward_only_message_is_answered_without_a_reply_link(repository):
    services = queue_services(repository)
    api = FakeMaxApi()
    queue = FakeQueue()
    forwarded = message(
        message_id="forward:5000:1775053255737:mid.original",
        images=(image(1),),
        photo_source="forward",
    )

    await enqueue_photo_message(forwarded, services, api, queue)

    (receipt,) = api.calls_of("send_message")
    assert receipt["reply_to"] is None
    assert queue.jobs[0].source_message_id == "forward:5000:1775053255737:mid.original"
    assert queue.jobs[0].photo_source == "forward"
