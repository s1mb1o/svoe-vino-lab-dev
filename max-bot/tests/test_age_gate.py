"""Age gate and /start of the MAX bot. Port of `telegram-bot/tests/test_age_gate.py`.

MAX differences:
- A photo is one `IncomingMessage` with image attachments. An album is one message.
- `/start` arrives as the text `/start [args]` or as a `bot_started` update with a payload.
- An age choice replaces the age gate in the same `POST /answers` call as the notification.
"""

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
    BotHandlers,
    enqueue_photo_message,
    handle_age_confirmation,
)
from chto_za_vino_max_bot.profile import (
    AGE_GATE_TEXT,
    MINOR_TEXT,
    START_CONFIRMED_TEXT,
    privacy_text,
)
from chto_za_vino_max_bot.storage import Repository
from chto_za_vino_max_bot.updates import BotStarted, MaxUser

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
