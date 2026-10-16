import io
from types import SimpleNamespace

import pytest
from PIL import Image

from chto_za_vino_bot.app import (
    AlbumReceiptTracker,
    PhotoJob,
    PhotoProcessor,
    _queue_receipt_text,
    enqueue_photo_message,
)
from chto_za_vino_bot.result_card import format_result_caption
from chto_za_vino_bot.storage import Repository
from chto_za_vino_bot.wine import Wine


class FakeStatus:
    def __init__(self, message_id: int, text: str) -> None:
        self.message_id = message_id
        self.text = text
        self.edits: list[str] = []

    async def edit_text(self, text: str) -> None:
        self.edits.append(text)


class FakeMessage:
    def __init__(self, message_id: int, file_id: str, media_group_id: str) -> None:
        self.message_id = message_id
        self.media_group_id = media_group_id
        self.chat = SimpleNamespace(id=100)
        self.from_user = SimpleNamespace(
            id=200,
            username="tester",
            first_name="Test",
            last_name=None,
        )
        self.photo = [
            SimpleNamespace(file_id=file_id, file_unique_id=f"unique-{file_id}")
        ]
        self.replies: list[FakeStatus] = []

    async def reply(self, text: str, **kwargs: object) -> FakeStatus:
        status = FakeStatus(1000 + self.message_id, text)
        self.replies.append(status)
        return status


class FakeQueue:
    def __init__(self) -> None:
        self.at_capacity = False
        self.jobs: list[PhotoJob] = []

    @property
    def next_position(self) -> int:
        return len(self.jobs) + 1

    def estimate_wait_seconds(self, position: int) -> int:
        return max(0, position - 1) * 20

    def submit(self, job: PhotoJob) -> None:
        self.jobs.append(job)


class FakeBot:
    def __init__(self) -> None:
        self.photos: list[dict[str, object]] = []
        self.deleted: list[tuple[int, int]] = []
        self.edits: list[dict[str, object]] = []
        self.messages: list[dict[str, object]] = []

    async def send_photo(self, **kwargs: object) -> None:
        self.photos.append(kwargs)

    async def send_message(self, chat_id: int, text: str, **kwargs: object):
        self.messages.append({"chat_id": chat_id, "text": text, **kwargs})
        return SimpleNamespace(message_id=2000 + len(self.messages))

    async def delete_message(self, chat_id: int, message_id: int) -> None:
        self.deleted.append((chat_id, message_id))

    async def edit_message_text(self, text: str, **kwargs: object) -> None:
        self.edits.append({"text": text, **kwargs})


class FailingPhotoBot(FakeBot):
    async def send_photo(self, **kwargs: object) -> None:
        raise RuntimeError("Telegram photo failure")


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


async def test_album_photos_create_separate_ordered_jobs(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    services = SimpleNamespace(
        repository=repository,
        settings=SimpleNamespace(rate_limit=25, rate_window_seconds=3600),
    )
    repository.set_age_status(
        user_id=200,
        username="tester",
        first_name="Test",
        last_name=None,
        status="adult",
        now=1,
    )
    queue = FakeQueue()
    receipts = AlbumReceiptTracker()
    first = FakeMessage(10, "file-1", "album-1")
    second = FakeMessage(11, "file-2", "album-1")

    await enqueue_photo_message(first, services, queue, receipts)
    await enqueue_photo_message(second, services, queue, receipts)

    assert [job.file_id for job in queue.jobs] == ["file-1", "file-2"]
    assert [job.source_message_id for job in queue.jobs] == [10, 11]
    assert [job.status_message_id for job in queue.jobs] == [1010, None]
    assert [job.feedback_enabled for job in queue.jobs] == [False, False]
    assert [job.status_enabled for job in queue.jobs] == [True, False]
    assert [job.keep_status for job in queue.jobs] == [True, False]
    assert len(first.replies) == 1
    assert first.replies[0].text.startswith("Фотографии приняты")
    assert "Позиция: 1" in first.replies[0].text
    assert len(second.replies) == 0
    assert repository.stats(200, 2**31, 2**31).total == 2
    repository.close()


def test_album_receipt_tracker_expires_old_groups():
    receipts = AlbumReceiptTracker(ttl_seconds=10)

    assert receipts.claim("album-1", now=100)
    assert not receipts.claim("album-1", now=105)
    assert receipts.claim("album-1", now=116)


def test_album_receipt_tracker_evicts_oldest_group_at_capacity():
    receipts = AlbumReceiptTracker(capacity=1)

    assert receipts.claim("album-1", now=100)
    assert receipts.claim("album-2", now=101)
    assert receipts.claim("album-1", now=102)


async def test_album_results_reply_to_each_source_photo():
    bot = FakeBot()
    processor = PhotoProcessor(SimpleNamespace(image_loader=None), bot)
    wine = Wine(
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
    jobs = [
        PhotoJob("request-1", 100, 10, 1000, "file-1", 1010, feedback_enabled=False),
        PhotoJob("request-2", 100, 11, 1000, "file-2", 1011, feedback_enabled=False),
    ]

    for job in jobs:
        await processor._send_result(job, wine, result_jpeg())

    assert len(bot.photos) == 2
    assert [
        photo["reply_parameters"].message_id for photo in bot.photos
    ] == [10, 11]
    assert [
        photo["reply_markup"].inline_keyboard[0][0].text for photo in bot.photos
    ] == ["Открыть страницу вина", "Открыть страницу вина"]
    assert bot.deleted == [(100, 1010), (100, 1011)]


async def test_single_photo_result_has_feedback_buttons():
    bot = FakeBot()
    processor = PhotoProcessor(SimpleNamespace(image_loader=None), bot)
    wine = Wine(
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

    await processor._send_result(
        PhotoJob("request-1", 100, 10, 1000, "file-1", 1010),
        wine,
        result_jpeg(),
    )

    markup = bot.photos[0]["reply_markup"].inline_keyboard
    assert markup[0][0].text == "Открыть страницу вина"
    assert markup[0][0].url == "https://vino-svoe.ru/wines/test-wine"
    buttons = markup[1]
    assert [button.text for button in buttons] == ["✅ Совпало", "❌ Не совпало"]
    assert [button.callback_data for button in buttons] == [
        "feedback:yes:request-1",
        "feedback:no:request-1",
    ]


def test_alternative_keyboard_has_three_candidates_and_none():
    from chto_za_vino_bot.app import alternative_keyboard

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

    rows = alternative_keyboard("request-1", wines).inline_keyboard

    assert [row[0].text for row in rows] == [
        "2. Вино 2",
        "3. Вино 3",
        "4. Вино 4",
        "Ничего из этого",
    ]


async def test_rejection_uses_illustration_and_replies_to_source_photo():
    bot = FakeBot()
    processor = PhotoProcessor(SimpleNamespace(rejection_image=b"rejection-png"), bot)
    job = PhotoJob("request-1", 100, 10, 1000, "file-1", 1010)

    await processor._send_rejection(job)

    assert len(bot.photos) == 1
    assert bot.photos[0]["photo"].filename == "content-rejected.png"
    assert "Контент признан неподходящим" in bot.photos[0]["caption"]
    appeal = bot.photos[0]["reply_markup"].inline_keyboard[0][0]
    assert appeal.text == "Сообщить об ошибке фильтра"
    assert appeal.callback_data == "moderation_error:request-1"
    assert bot.photos[0]["reply_parameters"].message_id == 10
    assert bot.deleted == [(100, 1010)]
    assert job.status_message_id is None


async def test_rejection_photo_failure_falls_back_to_status_text():
    bot = FailingPhotoBot()
    processor = PhotoProcessor(SimpleNamespace(rejection_image=b"rejection-png"), bot)
    job = PhotoJob("request-1", 100, 10, 1000, "file-1", 1010)

    await processor._send_rejection(job)

    assert len(bot.edits) == 1
    assert "Контент признан неподходящим" in bot.edits[0]["text"]


@pytest.mark.parametrize(
    ("album", "wait_seconds", "subject", "wait"),
    [
        (False, 0, "Фотография принята и поставлена", "обработка начнётся сразу."),
        (True, 40, "Фотографии приняты и поставлены", "примерное ожидание: около 40 сек."),
        (False, 90, "Фотография принята и поставлена", "примерное ожидание: около 2 мин."),
    ],
)
def test_queue_receipt_ends_with_one_point(album, wait_seconds, subject, wait):
    assert _queue_receipt_text(album=album, position=1, wait_seconds=wait_seconds) == (
        f"{subject} в очередь.\nПозиция: 1; {wait}"
    )


async def test_result_photo_failure_falls_back_to_the_status_text():
    bot = FailingPhotoBot()
    processor = PhotoProcessor(SimpleNamespace(image_loader=None), bot)

    await processor._send_result(
        PhotoJob("request-1", 100, 10, 1000, "file-1", 1010),
        sample_wine(),
        result_jpeg(),
    )

    assert [edit["text"] for edit in bot.edits] == [format_result_caption(sample_wine())]
    assert bot.edits[0]["message_id"] == 1010
    assert bot.edits[0]["link_preview_options"].is_disabled
    assert [button.callback_data for button in bot.edits[0]["reply_markup"].inline_keyboard[1]] == [
        "feedback:yes:request-1",
        "feedback:no:request-1",
    ]
    assert bot.messages == []
    assert bot.deleted == []


@pytest.mark.parametrize("failure", ["send_photo", "result_image"])
async def test_album_result_failure_without_a_status_still_reaches_the_user(failure):
    bot = FailingPhotoBot() if failure == "send_photo" else FakeBot()
    submitted_body = result_jpeg() if failure == "send_photo" else b"not an image"
    processor = PhotoProcessor(SimpleNamespace(image_loader=None), bot)
    job = PhotoJob(
        "request-2",
        100,
        11,
        1000,
        "file-2",
        None,
        feedback_enabled=False,
        status_enabled=False,
    )

    await processor._send_result(job, sample_wine(), submitted_body)

    assert bot.photos == []
    assert [message["text"] for message in bot.messages] == [
        format_result_caption(sample_wine())
    ]
    reply = bot.messages[0]
    assert reply["chat_id"] == 100
    assert reply["reply_parameters"].message_id == 11
    assert reply["link_preview_options"].is_disabled
    assert [row[0].text for row in reply["reply_markup"].inline_keyboard] == [
        "Открыть страницу вина"
    ]
