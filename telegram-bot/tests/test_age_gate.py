import sqlite3
import time
from types import SimpleNamespace

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import SendMessage

from chto_za_vino_bot.app import (
    HELD_PHOTO_UNAVAILABLE_TEXT,
    AlbumReceiptTracker,
    enqueue_photo_message,
    handle_age_confirmation,
)
from chto_za_vino_bot.profile import AGE_GATE_TEXT
from chto_za_vino_bot.storage import AGE_PENDING_SECONDS, HeldPhoto, Repository


class FakeMessage:
    def __init__(self, message_id: int = 10, *, media_group_id: str | None = None) -> None:
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
            SimpleNamespace(file_id=f"small-{message_id}", file_unique_id=f"small-u-{message_id}"),
            SimpleNamespace(file_id=f"file-{message_id}", file_unique_id=f"unique-{message_id}"),
        ]
        self.replies: list[tuple[str, dict[str, object]]] = []

    async def reply(self, text: str, **kwargs: object) -> None:
        self.replies.append((text, kwargs))


class RejectingQueue:
    at_capacity = False

    def submit(self, job: object) -> None:
        raise AssertionError("unconfirmed photo must not enter the queue")


class FakeCallback:
    def __init__(self, data: str, bot: object | None = None) -> None:
        self.data = data
        self.bot = bot
        self.from_user = SimpleNamespace(
            id=200,
            username="tester",
            first_name="Test",
            last_name=None,
        )
        self.message = None
        self.notifications: list[str | None] = []

    async def answer(self, text: str | None = None) -> None:
        self.notifications.append(text)
        if getattr(self, "fail_answer", False):
            raise RuntimeError("callback answer failed")


async def test_unconfirmed_photo_does_not_enter_queue_or_use_limit(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    services = SimpleNamespace(
        repository=repository,
        settings=SimpleNamespace(rate_limit=25, rate_window_seconds=3600),
    )
    message = FakeMessage()

    await enqueue_photo_message(
        message,
        services,
        RejectingQueue(),
        AlbumReceiptTracker(),
    )

    assert len(message.replies) == 1
    assert message.replies[0][0] == AGE_GATE_TEXT
    assert message.replies[0][1]["reply_markup"] is not None
    assert repository.stats(200, 1000, 3600).total == 0
    repository.close()


async def test_age_confirmation_saves_each_choice(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    services = SimpleNamespace(repository=repository)

    adult = FakeCallback("age:adult")
    await handle_age_confirmation(adult, services)
    assert repository.age_status(200) == "adult"
    assert adult.notifications == ["Возраст подтверждён."]

    minor = FakeCallback("age:minor")
    await handle_age_confirmation(minor, services)
    assert repository.age_status(200) == "minor"
    assert minor.notifications == ["Бот доступен только пользователям старше 18 лет."]
    repository.close()


# A photo that arrives before the age confirmation


class RecordingQueue:
    at_capacity = False

    def __init__(self) -> None:
        self.jobs: list[object] = []

    @property
    def next_position(self) -> int:
        return len(self.jobs) + 1

    def estimate_wait_seconds(self, position: int) -> int:
        return max(0, position - 1) * 20

    def submit(self, job: object) -> None:
        self.jobs.append(job)


class FakeBot:
    def __init__(self, *, fail_first: bool = False, closed_chat_id: int | None = None) -> None:
        self.sent: list[tuple[int, str, dict[str, object]]] = []
        self._fail_first = fail_first
        self._closed_chat_id = closed_chat_id

    async def send_message(self, chat_id: int, text: str, **kwargs: object) -> object:
        if chat_id == self._closed_chat_id:
            raise TelegramBadRequest(SendMessage(chat_id=chat_id, text=text), "Forbidden")
        if self._fail_first:
            self._fail_first = False
            raise TelegramBadRequest(SendMessage(chat_id=chat_id, text=text), "Bad Request")
        self.sent.append((chat_id, text, kwargs))
        return SimpleNamespace(message_id=1000 + len(self.sent))


def photo_services(repository: Repository) -> SimpleNamespace:
    return SimpleNamespace(
        repository=repository,
        settings=SimpleNamespace(rate_limit=25, rate_window_seconds=3600),
    )


async def test_photo_before_the_age_confirmation_is_queued_after_the_adult_choice(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    services = photo_services(repository)
    queue = RecordingQueue()
    receipts = AlbumReceiptTracker()
    bot = FakeBot()
    photo = FakeMessage(10)

    await enqueue_photo_message(photo, services, queue, receipts)
    assert [text for text, _ in photo.replies] == [AGE_GATE_TEXT]
    assert queue.jobs == []
    assert repository.stats(200, 1000, 3600).total == 0

    await handle_age_confirmation(FakeCallback("age:adult", bot), services, queue, receipts)

    (job,) = queue.jobs
    assert job.source_message_id == 10
    assert job.chat_id == 100
    # The largest photo size, the same as for a photo after the confirmation.
    assert job.file_id == "file-10"
    ((chat_id, text, kwargs),) = bot.sent
    assert chat_id == 100
    assert text.startswith("Фотография принята и поставлена")
    assert kwargs["reply_parameters"].message_id == 10
    assert kwargs["reply_parameters"].allow_sending_without_reply is True
    assert repository.stats(200, 2**31, 2**31).total == 1

    # A second adult choice does not queue the photo again.
    await handle_age_confirmation(FakeCallback("age:adult", bot), services, queue, receipts)
    assert len(queue.jobs) == 1
    repository.close()


async def test_held_album_gets_one_receipt_after_the_adult_choice(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    services = photo_services(repository)
    queue = RecordingQueue()
    receipts = AlbumReceiptTracker()
    bot = FakeBot()

    for message_id in (21, 22):
        await enqueue_photo_message(
            FakeMessage(message_id, media_group_id="album-1"), services, queue, receipts
        )
    await handle_age_confirmation(FakeCallback("age:adult", bot), services, queue, receipts)

    assert [job.source_message_id for job in queue.jobs] == [21, 22]
    assert len(bot.sent) == 1
    assert bot.sent[0][1].startswith("Фотографии приняты и поставлены")
    repository.close()


async def test_minor_choice_forgets_the_held_photo(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    services = photo_services(repository)
    queue = RecordingQueue()
    receipts = AlbumReceiptTracker()
    bot = FakeBot()

    await enqueue_photo_message(FakeMessage(10), services, queue, receipts)
    await handle_age_confirmation(FakeCallback("age:minor", bot), services, queue, receipts)
    await handle_age_confirmation(FakeCallback("age:adult", bot), services, queue, receipts)

    assert queue.jobs == []
    assert bot.sent == []
    repository.close()


async def test_held_photo_with_a_failed_receipt_asks_for_a_new_photo(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    services = photo_services(repository)
    queue = RecordingQueue()
    receipts = AlbumReceiptTracker()
    bot = FakeBot(fail_first=True)

    await enqueue_photo_message(FakeMessage(10), services, queue, receipts)
    await handle_age_confirmation(FakeCallback("age:adult", bot), services, queue, receipts)

    assert queue.jobs == []
    assert bot.sent == [(100, HELD_PHOTO_UNAVAILABLE_TEXT, {})]
    repository.close()


def test_held_photos_expire_and_follow_the_user_data_deletion(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    held = HeldPhoto(
        chat_id=100, message_id=10, media_group_id=None, file_id="f", file_unique_id="u"
    )

    repository.add_age_pending_photo(user_id=200, photo=held, now=1_000)
    assert repository.age_pending_photos(200, 1_000 + AGE_PENDING_SECONDS + 1) == []

    repository.add_age_pending_photo(user_id=200, photo=held, now=5_000)
    repository.delete_user_data(200)
    assert repository.age_pending_photos(200, 5_000) == []
    repository.close()


def test_scheduled_retention_removes_held_photos_after_a_day(tmp_path):
    database = tmp_path / "bot.sqlite3"
    repository = Repository(database)
    now = int(time.time())
    for message_id, age in ((10, AGE_PENDING_SECONDS + 60), (11, 60)):
        repository.add_age_pending_photo(
            user_id=200,
            photo=HeldPhoto(
                chat_id=100,
                message_id=message_id,
                media_group_id=None,
                file_id="f",
                file_unique_id=f"u{message_id}",
            ),
            now=now - age,
        )

    # The request retention cutoff is much older than one day.
    repository.delete_expired_data(0, lambda plan: 0)

    rows = sqlite3.connect(database).execute(
        "SELECT message_id FROM age_pending_photos"
    ).fetchall()
    assert rows == [(11,)]
    repository.close()


class CrashingQueue(RecordingQueue):
    def submit(self, job: object) -> None:
        raise RuntimeError("process stopped")


async def test_held_photo_stays_held_until_the_bot_admits_it(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    services = photo_services(repository)
    receipts = AlbumReceiptTracker()

    await enqueue_photo_message(FakeMessage(10), services, RecordingQueue(), receipts)
    with pytest.raises(RuntimeError):
        await handle_age_confirmation(
            FakeCallback("age:adult", FakeBot()), services, CrashingQueue(), receipts
        )

    (held,) = repository.age_pending_photos(200, int(time.time()))
    assert held.message_id == 10
    repository.close()


@pytest.mark.parametrize(
    ("data", "queued"), [("age:adult", 1), ("age:minor", 0)], ids=["adult", "minor"]
)
async def test_held_photos_follow_the_choice_when_the_callback_answer_fails(
    tmp_path, data, queued
):
    repository = Repository(tmp_path / "bot.sqlite3")
    services = photo_services(repository)
    queue = RecordingQueue()
    receipts = AlbumReceiptTracker()
    await enqueue_photo_message(FakeMessage(10), services, queue, receipts)
    callback = FakeCallback(data, FakeBot())
    callback.fail_answer = True

    with pytest.raises(RuntimeError):
        await handle_age_confirmation(callback, services, queue, receipts)

    assert len(queue.jobs) == queued
    assert repository.age_pending_photos(200, int(time.time())) == []
    repository.close()


async def test_a_closed_chat_does_not_stop_the_replay_of_other_held_photos(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    services = photo_services(repository)
    queue = RecordingQueue()
    receipts = AlbumReceiptTracker()
    closed = FakeMessage(5)
    closed.chat = SimpleNamespace(id=300)
    await enqueue_photo_message(closed, services, queue, receipts)
    await enqueue_photo_message(FakeMessage(10), services, queue, receipts)

    await handle_age_confirmation(
        FakeCallback("age:adult", FakeBot(closed_chat_id=300)), services, queue, receipts
    )

    assert [(job.chat_id, job.source_message_id) for job in queue.jobs] == [(100, 10)]
    assert repository.age_pending_photos(200, int(time.time())) == []
    repository.close()


def test_held_photos_with_the_same_time_keep_their_arrival_order(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    for chat_id, message_id in ((100, 50), (300, 10)):
        repository.add_age_pending_photo(
            user_id=200,
            photo=HeldPhoto(
                chat_id=chat_id,
                message_id=message_id,
                media_group_id=None,
                file_id="f",
                file_unique_id=f"u{message_id}",
            ),
            now=1_000,
        )

    held = repository.age_pending_photos(200, 1_000)

    assert [(photo.chat_id, photo.message_id) for photo in held] == [(100, 50), (300, 10)]
    repository.close()
