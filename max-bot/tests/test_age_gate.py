"""Age gate and /start of the MAX bot. Port of `telegram-bot/tests/test_age_gate.py`.

MAX differences:
- A photo is one `IncomingMessage` with image attachments. An album is one message.
- `/start` arrives as the text `/start [args]` or as a `bot_started` update with a payload.
- An age choice replaces the age gate in the same `POST /answers` call as the notification.
"""

import sqlite3
import time
from types import SimpleNamespace

import pytest
from fakes import (
    DIALOG_CHAT_ID,
    USER_ID,
    FakeMaxApi,
    callback,
    image,
    keyboard_buttons,
    message,
    user,
)

from chto_za_vino_max_bot.app import (
    AGE_CONFIRMATION_KEYBOARD,
    HELD_PHOTO_UNAVAILABLE_TEXT,
    BotHandlers,
    enqueue_photo_message,
    handle_age_confirmation,
)
from chto_za_vino_max_bot.max_api import MaxApiError
from chto_za_vino_max_bot.profile import (
    AGE_GATE_TEXT,
    MINOR_TEXT,
    START_CONFIRMED_TEXT,
    privacy_text,
)
from chto_za_vino_max_bot.storage import AGE_PENDING_SECONDS, Repository
from chto_za_vino_max_bot.updates import (
    FORWARD_ID_PREFIX,
    BotStarted,
    ImageRef,
    IncomingMessage,
    MaxUser,
)

BOT =MaxUser(user_id=1, first_name="Bot", last_name=None, username="bot", is_bot=True)


class RejectingQueue:
    at_capacity = False

    def submit(self, job: object) -> None:
        raise AssertionError("unconfirmed photo must not enter the queue")


def make_services(repository: Repository) -> SimpleNamespace:
    return SimpleNamespace(
        repository=repository,
        settings=SimpleNamespace(rate_limit=25, rate_window_seconds=3600, admin_user_id=777),
    )


def set_age(repository: Repository, status: str) -> None:
    repository.set_age_status(
        user_id=USER_ID,
        username="tester",
        first_name="Test",
        last_name=None,
        status=status,
        now=900,
    )


def chat_answer(
    text: str,
    *,
    attachments: list[dict[str, object]] | None = None,
    disable_link_preview: bool = False,
) -> dict[str, object]:
    """The `send_message` call of `message.answer(...)`: no reply link, HTML format."""
    return {
        "chat_id": DIALOG_CHAT_ID,
        "text": text,
        "attachments": attachments,
        "reply_to": None,
        "text_format": "html",
        "disable_link_preview": disable_link_preview,
    }


def notification_only(text: str | None) -> dict[str, object]:
    """The `answer_callback` call of a callback without a message."""
    return {
        "chat_id": None,
        "callback_id": "callback-1",
        "notification": text,
        "message": None,
        "disable_link_preview": False,
    }


def test_age_confirmation_keyboard_uses_the_age_buttons():
    assert keyboard_buttons([AGE_CONFIRMATION_KEYBOARD]) == [
        [
            {"type": "callback", "text": "Мне есть 18 лет", "payload": "age:adult"},
            {"type": "callback", "text": "Мне нет 18 лет", "payload": "age:minor"},
        ]
    ]


@pytest.mark.parametrize("age_status", [None, "minor"])
@pytest.mark.parametrize("image_count", [1, 3], ids=["photo", "album"])
async def test_unconfirmed_photo_does_not_enter_queue_or_use_limit(
    tmp_path, age_status, image_count
):
    repository = Repository(tmp_path / "bot.sqlite3")
    if age_status is not None:
        set_age(repository, age_status)
    api = FakeMaxApi()
    # A MAX album is one message with several image attachments. It gets one age gate reply.
    photo = message(images=tuple(image(index) for index in range(1, image_count + 1)))

    await enqueue_photo_message(photo, make_services(repository), api, RejectingQueue())

    # Telegram: message.reply(AGE_GATE_TEXT, reply_markup=..., link previews disabled).
    assert api.calls_of("send_message") == [
        {
            "chat_id": DIALOG_CHAT_ID,
            "text": AGE_GATE_TEXT,
            "attachments": [AGE_CONFIRMATION_KEYBOARD],
            "reply_to": "mid.source",
            "text_format": "html",
            "disable_link_preview": True,
        }
    ]
    assert [call.method for call in api.calls] == ["send_message"]
    assert repository.stats(USER_ID, 1000, 3600).total == 0
    repository.close()


async def test_age_confirmation_saves_each_choice(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    services = SimpleNamespace(repository=repository)
    api = FakeMaxApi()

    # The callbacks have no message, so the bot sends only the notification.
    await handle_age_confirmation(callback("age:adult", with_message=False), services, api)
    assert repository.age_status(USER_ID) == "adult"

    await handle_age_confirmation(callback("age:minor", with_message=False), services, api)
    assert repository.age_status(USER_ID) == "minor"

    assert api.calls_of("answer_callback") == [
        notification_only("Возраст подтверждён."),
        notification_only("Бот доступен только пользователям старше 18 лет."),
    ]
    assert [call.method for call in api.calls] == ["answer_callback", "answer_callback"]
    repository.close()


@pytest.mark.parametrize(
    ("payload", "status", "notification", "text"),
    [
        ("age:adult", "adult", "Возраст подтверждён.", START_CONFIRMED_TEXT),
        (
            "age:minor",
            "minor",
            "Бот доступен только пользователям старше 18 лет.",
            MINOR_TEXT,
        ),
    ],
    ids=["adult", "minor"],
)
async def test_age_choice_replaces_the_age_gate_in_one_answer(
    tmp_path, payload, status, notification, text
):
    repository = Repository(tmp_path / "bot.sqlite3")
    api = FakeMaxApi()
    gate = message(
        message_id="mid.age-gate",
        sender=BOT,
        text="Подтвердите, что вам уже исполнилось 18 лет.",
    )

    await handle_age_confirmation(
        callback(payload, source=gate),
        SimpleNamespace(repository=repository),
        api,
    )

    assert repository.age_status(USER_ID) == status
    # Telegram: callback.answer(notification), then edit_text(text, reply_markup=None) with
    # link previews disabled. MAX: one answer with the notification and the new message body.
    assert api.calls_of("answer_callback") == [
        {
            "chat_id": DIALOG_CHAT_ID,
            "callback_id": "callback-1",
            "notification": notification,
            "message": {"text": text, "attachments": [], "format": "html"},
            "disable_link_preview": True,
        }
    ]
    assert [call.method for call in api.calls] == ["answer_callback"]
    repository.close()


async def test_unknown_age_payload_is_answered_without_a_decision(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    api = FakeMaxApi()

    await handle_age_confirmation(
        callback("age:unknown", with_message=False),
        SimpleNamespace(repository=repository),
        api,
    )

    assert repository.age_status(USER_ID) is None
    assert api.calls_of("answer_callback") == [notification_only(None)]
    repository.close()


START_UPDATES = {
    "text": message(text="/start"),
    "text-with-bot-name": message(text="/start@se14697933_bot"),
    "bot-started": BotStarted(chat_id=DIALOG_CHAT_ID, user=user(), payload=None),
    "bot-started-other-payload": BotStarted(chat_id=DIALOG_CHAT_ID, user=user(), payload="ad"),
}


@pytest.mark.parametrize("update", list(START_UPDATES.values()), ids=list(START_UPDATES))
async def test_start_shows_the_age_gate_until_the_age_is_confirmed(tmp_path, update):
    repository = Repository(tmp_path / "bot.sqlite3")
    api = FakeMaxApi()
    handlers = BotHandlers(make_services(repository), api, RejectingQueue())

    await handlers.handle(update)
    set_age(repository, "minor")
    await handlers.handle(update)
    set_age(repository, "adult")
    await handlers.handle(update)

    gate = chat_answer(
        AGE_GATE_TEXT,
        attachments=[AGE_CONFIRMATION_KEYBOARD],
        disable_link_preview=True,
    )
    assert api.calls_of("send_message") == [
        gate,
        gate,
        chat_answer(START_CONFIRMED_TEXT, disable_link_preview=True),
    ]
    assert [call.method for call in api.calls] == ["send_message"] * 3
    repository.close()


PRIVACY_UPDATES = {
    "start-text": message(text="/start privacy"),
    "bot-started-deep-link": BotStarted(chat_id=DIALOG_CHAT_ID, user=user(), payload="privacy"),
    "privacy-command": message(text="/privacy"),
}


@pytest.mark.parametrize("update", list(PRIVACY_UPDATES.values()), ids=list(PRIVACY_UPDATES))
async def test_privacy_notice_shows_the_max_user_id_without_the_age_gate(tmp_path, update):
    repository = Repository(tmp_path / "bot.sqlite3")
    api = FakeMaxApi()
    handlers = BotHandlers(make_services(repository), api, RejectingQueue())

    await handlers.handle(update)

    expected = privacy_text(USER_ID)
    # A MAX user has no simple way to find the own user ID, so the notice includes it.
    assert expected.endswith("Ваш MAX user ID: <code>200</code>")
    assert api.calls_of("send_message") == [chat_answer(expected)]
    assert repository.age_status(USER_ID) is None
    repository.close()


# A photo that arrives before the age confirmation


class RecordingQueue:
    """The queue interface of `enqueue_photo_message`."""

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


def raw_photo_message(
    message_id: str, *images: ImageRef, sender_id: int = USER_ID
) -> dict[str, object]:
    """A message body of `GET /messages/{messageId}`."""
    return {
        "sender": {"user_id": sender_id, "first_name": "Test", "username": "tester"},
        "recipient": {"chat_id": DIALOG_CHAT_ID, "chat_type": "dialog"},
        "timestamp": 1_000,
        "body": {
            "mid": message_id,
            "attachments": [
                {
                    "type": "image",
                    "payload": {"photo_id": item.photo_id, "url": item.url, "token": item.token},
                }
                for item in images
            ],
        },
    }


def age_gate_message() -> IncomingMessage:
    return message(message_id="mid.age-gate", sender=BOT, text=AGE_GATE_TEXT)


async def test_photo_before_the_age_confirmation_is_queued_after_the_adult_choice(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    services = make_services(repository)
    api = FakeMaxApi()
    queue = RecordingQueue()
    handlers = BotHandlers(services, api, queue)
    photo = image(1)

    await handlers.handle(message(message_id="mid.photo", images=(photo,)))

    # The age gate holds the photo back: no request, no download, no queue entry.
    (gate,) = api.calls_of("send_message")
    assert gate["text"] == AGE_GATE_TEXT
    assert gate["reply_to"] == "mid.photo"
    assert queue.jobs == []
    assert repository.stats(USER_ID, 2**31, 2**31).total == 0

    api.messages_by_id["mid.photo"] = raw_photo_message("mid.photo", photo)
    await handlers.handle(callback("age:adult", source=age_gate_message()))

    assert repository.age_status(USER_ID) == "adult"
    assert [call.method for call in api.calls] == [
        "send_message",
        "answer_callback",
        "get_message",
        "send_message",
    ]
    receipt = api.calls_of("send_message")[1]
    assert receipt["text"].startswith("Фотография принята и поставлена")
    assert receipt["reply_to"] == "mid.photo"
    (job,) = queue.jobs
    assert job.source_message_id == "mid.photo"
    assert job.photo_url == photo.url
    assert job.user_id == USER_ID

    # A second adult choice does not queue the photo again.
    await handlers.handle(callback("age:adult", source=age_gate_message()))
    assert len(api.calls_of("get_message")) == 1
    assert len(queue.jobs) == 1
    repository.close()


async def test_held_album_and_photos_are_queued_in_their_order(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    services = make_services(repository)
    api = FakeMaxApi()
    queue = RecordingQueue()

    await enqueue_photo_message(
        message(message_id="mid.first", images=(image(1),)), services, api, queue
    )
    await enqueue_photo_message(
        message(message_id="mid.album", images=(image(2), image(3))), services, api, queue
    )
    api.messages_by_id["mid.first"] = raw_photo_message("mid.first", image(1))
    api.messages_by_id["mid.album"] = raw_photo_message("mid.album", image(2), image(3))

    await handle_age_confirmation(
        callback("age:adult", source=age_gate_message()), services, api, queue
    )

    assert [call["message_id"] for call in api.calls_of("get_message")] == [
        "mid.first",
        "mid.album",
    ]
    assert [(job.source_message_id, job.photo_index) for job in queue.jobs] == [
        ("mid.first", 0),
        ("mid.album", 0),
        ("mid.album", 1),
    ]
    repository.close()


async def test_minor_choice_forgets_the_held_photo(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    services = make_services(repository)
    api = FakeMaxApi()
    queue = RecordingQueue()
    api.messages_by_id["mid.photo"] = raw_photo_message("mid.photo", image(1))

    await enqueue_photo_message(
        message(message_id="mid.photo", images=(image(1),)), services, api, queue
    )
    await handle_age_confirmation(
        callback("age:minor", source=age_gate_message()), services, api, queue
    )
    await handle_age_confirmation(
        callback("age:adult", source=age_gate_message()), services, api, queue
    )

    assert api.calls_of("get_message") == []
    assert queue.jobs == []
    repository.close()


@pytest.mark.parametrize(
    "stored",
    [None, raw_photo_message("mid.photo", image(1), sender_id=USER_ID + 1)],
    ids=["not-readable", "other-sender"],
)
async def test_held_photo_that_cannot_be_read_again_asks_for_a_new_photo(tmp_path, stored):
    repository = Repository(tmp_path / "bot.sqlite3")
    services = make_services(repository)
    api = FakeMaxApi()
    queue = RecordingQueue()
    if stored is not None:
        api.messages_by_id["mid.photo"] = stored

    await enqueue_photo_message(
        message(message_id="mid.photo", images=(image(1),)), services, api, queue
    )
    await handle_age_confirmation(
        callback("age:adult", source=age_gate_message()), services, api, queue
    )

    assert api.calls_of("send_message")[-1] == chat_answer(HELD_PHOTO_UNAVAILABLE_TEXT)
    assert queue.jobs == []
    repository.close()


async def test_forwarded_photo_without_own_id_is_not_held(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    services = make_services(repository)
    api = FakeMaxApi()
    queue = RecordingQueue()

    await enqueue_photo_message(
        message(message_id=f"{FORWARD_ID_PREFIX}5000:1", images=(image(1),)),
        services,
        api,
        queue,
    )

    assert repository.age_pending_photos(USER_ID, 1_000) == []
    repository.close()


def test_held_photos_expire_and_follow_the_user_data_deletion(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    day = AGE_PENDING_SECONDS

    repository.add_age_pending_photo(
        user_id=USER_ID, chat_id=DIALOG_CHAT_ID, message_id="mid.old", now=1_000
    )
    assert repository.age_pending_photos(USER_ID, 1_000 + day + 1) == []

    repository.add_age_pending_photo(
        user_id=USER_ID, chat_id=DIALOG_CHAT_ID, message_id="mid.new", now=5_000
    )
    repository.delete_user_data(USER_ID)
    assert repository.age_pending_photos(USER_ID, 5_000) == []
    repository.close()


def test_scheduled_retention_removes_held_photos_after_a_day(tmp_path):
    database = tmp_path / "bot.sqlite3"
    repository = Repository(database)
    now = int(time.time())
    for message_id, age in (("mid.stale", AGE_PENDING_SECONDS + 60), ("mid.fresh", 60)):
        repository.add_age_pending_photo(
            user_id=USER_ID, chat_id=DIALOG_CHAT_ID, message_id=message_id, now=now - age
        )

    # The request retention cutoff is much older than one day.
    repository.delete_expired_data(0, lambda plan: 0)

    rows = sqlite3.connect(database).execute(
        "SELECT message_id FROM age_pending_photos"
    ).fetchall()
    assert rows == [("mid.fresh",)]
    repository.close()


class CrashingQueue(RecordingQueue):
    def submit(self, job: object) -> None:
        raise RuntimeError("process stopped")


async def test_held_photo_stays_held_until_the_bot_admits_it(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    services = make_services(repository)
    api = FakeMaxApi()
    api.messages_by_id["mid.photo"] = raw_photo_message("mid.photo", image(1))

    await enqueue_photo_message(
        message(message_id="mid.photo", images=(image(1),)), services, api, RecordingQueue()
    )
    with pytest.raises(RuntimeError):
        await handle_age_confirmation(
            callback("age:adult", source=age_gate_message()), services, api, CrashingQueue()
        )

    assert repository.age_pending_photos(USER_ID, int(time.time())) == [
        (DIALOG_CHAT_ID, "mid.photo")
    ]
    repository.close()


@pytest.mark.parametrize(
    ("payload", "queued"), [("age:adult", 1), ("age:minor", 0)], ids=["adult", "minor"]
)
async def test_held_photos_follow_the_choice_when_the_callback_answer_fails(
    tmp_path, payload, queued
):
    repository = Repository(tmp_path / "bot.sqlite3")
    services = make_services(repository)
    api = FakeMaxApi()
    queue = RecordingQueue()
    api.messages_by_id["mid.photo"] = raw_photo_message("mid.photo", image(1))
    await enqueue_photo_message(
        message(message_id="mid.photo", images=(image(1),)), services, api, queue
    )
    api.fail_on["answer_callback"] = MaxApiError(500, "internal", "answer failed")

    with pytest.raises(MaxApiError):
        await handle_age_confirmation(
            callback(payload, source=age_gate_message()), services, api, queue
        )

    assert len(queue.jobs) == queued
    assert repository.age_pending_photos(USER_ID, int(time.time())) == []
    repository.close()


class ClosedChatApi(FakeMaxApi):
    """The bot can no longer send messages to one chat."""

    def __init__(self, closed_chat_id: int) -> None:
        super().__init__()
        self.closed_chat_id = closed_chat_id

    async def send_message(self, chat_id: int, **kwargs: object) -> dict[str, object]:
        if chat_id == self.closed_chat_id:
            self._record("send_message", chat_id=chat_id, **kwargs)
            raise MaxApiError(403, "chat.denied", "chat is closed")
        return await super().send_message(chat_id, **kwargs)


async def test_a_closed_chat_does_not_stop_the_replay_of_other_held_photos(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    services = make_services(repository)
    closed_chat = DIALOG_CHAT_ID + 1
    api = ClosedChatApi(closed_chat)
    queue = RecordingQueue()
    # The first held photo is in the closed chat and cannot be read again.
    repository.add_age_pending_photo(
        user_id=USER_ID, chat_id=closed_chat, message_id="mid.closed", now=int(time.time())
    )
    await enqueue_photo_message(
        message(message_id="mid.photo", images=(image(1),)), services, api, queue
    )
    api.messages_by_id["mid.photo"] = raw_photo_message("mid.photo", image(1))

    await handle_age_confirmation(
        callback("age:adult", source=age_gate_message()), services, api, queue
    )

    assert [job.source_message_id for job in queue.jobs] == ["mid.photo"]
    assert repository.age_pending_photos(USER_ID, int(time.time())) == []
    repository.close()
