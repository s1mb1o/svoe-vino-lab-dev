"""An image that the user sends as a file arrives as a Telegram document."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from aiogram.types import Chat, Document, Message, PhotoSize

from chto_za_vino_bot.app import (
    PHOTO_MESSAGE_FILTER,
    AlbumReceiptTracker,
    PhotoJob,
    enqueue_photo_message,
)
from chto_za_vino_bot.storage import Repository


def telegram_message(**kwargs: object) -> Message:
    return Message(
        message_id=1,
        date=datetime(2026, 10, 17, tzinfo=UTC),
        chat=Chat(id=100, type="private"),
        **kwargs,
    )


def document(mime_type: str | None, file_id: str = "document-1") -> Document:
    return Document(file_id=file_id, file_unique_id=f"unique-{file_id}", mime_type=mime_type)


@pytest.mark.parametrize(
    "mime_type", ["image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"]
)
def test_photo_filter_accepts_an_image_document(mime_type):
    assert PHOTO_MESSAGE_FILTER.resolve(telegram_message(document=document(mime_type)))


def test_photo_filter_accepts_a_photo():
    photo = PhotoSize(file_id="photo-1", file_unique_id="unique-photo-1", width=10, height=10)

    assert PHOTO_MESSAGE_FILTER.resolve(telegram_message(photo=[photo]))


@pytest.mark.parametrize("mime_type", ["application/pdf", "image/gif", "image/avif", None])
def test_photo_filter_rejects_another_document(mime_type):
    assert not PHOTO_MESSAGE_FILTER.resolve(telegram_message(document=document(mime_type)))


def test_photo_filter_rejects_text():
    assert not PHOTO_MESSAGE_FILTER.resolve(telegram_message(text="привет"))


class FakeStatus:
    def __init__(self, message_id: int) -> None:
        self.message_id = message_id


class FakeDocumentMessage:
    def __init__(self, mime_type: str) -> None:
        self.message_id = 10
        self.media_group_id = None
        self.chat = SimpleNamespace(id=100)
        self.from_user = SimpleNamespace(
            id=200,
            username="tester",
            first_name="Test",
            last_name=None,
        )
        self.photo = None
        self.document = SimpleNamespace(
            file_id="document-1",
            file_unique_id="unique-document-1",
            mime_type=mime_type,
        )
        self.replies: list[str] = []

    async def reply(self, text: str, **kwargs: object) -> FakeStatus:
        self.replies.append(text)
        return FakeStatus(1000 + len(self.replies))


class FakeQueue:
    def __init__(self) -> None:
        self.at_capacity = False
        self.jobs: list[PhotoJob] = []

    @property
    def next_position(self) -> int:
        return len(self.jobs) + 1

    def estimate_wait_seconds(self, position: int) -> int:
        return 0

    def submit(self, job: PhotoJob) -> None:
        self.jobs.append(job)


def services(tmp_path, *, adult: bool) -> SimpleNamespace:
    repository = Repository(tmp_path / "bot.sqlite3")
    if adult:
        repository.set_age_status(
            user_id=200,
            username="tester",
            first_name="Test",
            last_name=None,
            status="adult",
            now=1,
        )
    return SimpleNamespace(
        repository=repository,
        settings=SimpleNamespace(rate_limit=50, rate_window_seconds=3600),
    )


async def test_image_document_is_queued_as_a_photo(tmp_path):
    bot_services = services(tmp_path, adult=True)
    queue = FakeQueue()
    message = FakeDocumentMessage("image/png")

    await enqueue_photo_message(message, bot_services, queue, AlbumReceiptTracker())

    assert [job.file_id for job in queue.jobs] == ["document-1"]
    assert queue.jobs[0].feedback_enabled
    assert message.replies[0].startswith("Фотография принята и поставлена в очередь.")
    bot_services.repository.close()


async def test_another_document_is_not_queued(tmp_path):
    bot_services = services(tmp_path, adult=True)
    queue = FakeQueue()
    message = FakeDocumentMessage("application/pdf")

    await enqueue_photo_message(message, bot_services, queue, AlbumReceiptTracker())

    assert queue.jobs == []
    assert message.replies == []
    bot_services.repository.close()


async def test_age_gate_holds_the_document_file_reference(tmp_path):
    bot_services = services(tmp_path, adult=False)
    queue = FakeQueue()
    message = FakeDocumentMessage("image/jpeg")

    await enqueue_photo_message(message, bot_services, queue, AlbumReceiptTracker())

    assert queue.jobs == []
    held = bot_services.repository.age_pending_photos(200, 2)
    assert [(photo.file_id, photo.file_unique_id) for photo in held] == [
        ("document-1", "unique-document-1")
    ]
    bot_services.repository.close()


async def test_heic_document_is_recognized_and_stored_as_jpeg(tmp_path):
    from heic_images import heic_bytes
    from test_processor_quality import AdvisoryQualityInspector, FakeBot, run_processor

    row, *_ = await run_processor(tmp_path, AdvisoryQualityInspector(), bot=FakeBot(heic_bytes()))

    assert row[0] == "recognized"
    stored = list((tmp_path / "images" / "accepted").rglob("*"))
    files = [path for path in stored if path.is_file()]
    assert len(files) == 1
    assert files[0].read_bytes()[:3] == b"\xff\xd8\xff"


async def test_a_converted_heic_must_fit_the_size_limit(tmp_path):
    from chto_za_vino_core.moderation import prepare_source_image
    from heic_images import noisy_heic_bytes
    from test_processor_quality import AdvisoryQualityInspector, FakeBot, run_processor

    heic = noisy_heic_bytes()
    converted = len(prepare_source_image(heic))
    assert converted > len(heic)

    row, *_ = await run_processor(
        tmp_path,
        AdvisoryQualityInspector(),
        bot=FakeBot(heic),
        max_image_bytes=(len(heic) + converted) // 2,
    )

    assert row[0] == "invalid_image"
    assert not list((tmp_path / "images" / "accepted").rglob("*.jpg"))

