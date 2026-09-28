from types import SimpleNamespace

from chto_za_vino_bot.app import (
    AlbumReceiptTracker,
    enqueue_photo_message,
    handle_age_confirmation,
)
from chto_za_vino_bot.profile import AGE_GATE_TEXT
from chto_za_vino_bot.storage import Repository


class FakeMessage:
    def __init__(self) -> None:
        self.message_id = 10
        self.media_group_id = None
        self.chat = SimpleNamespace(id=100)
        self.from_user = SimpleNamespace(
            id=200,
            username="tester",
            first_name="Test",
            last_name=None,
        )
        self.photo = [SimpleNamespace(file_id="file-1", file_unique_id="unique-1")]
        self.replies: list[tuple[str, dict[str, object]]] = []

    async def reply(self, text: str, **kwargs: object) -> None:
        self.replies.append((text, kwargs))


class RejectingQueue:
    at_capacity = False

    def submit(self, job: object) -> None:
        raise AssertionError("unconfirmed photo must not enter the queue")


class FakeCallback:
    def __init__(self, data: str) -> None:
        self.data = data
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
