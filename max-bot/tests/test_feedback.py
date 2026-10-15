"""Result feedback, alternatives, and moderation appeals of the MAX bot.

Port of `telegram-bot/tests/test_feedback.py`. MAX differences:
- `callback.answer(text, show_alert=True)` is `POST /answers` with `notification`. MAX has no
  alert dialog, so the alert tests check a notification.
- `callback.message.edit_reply_markup(markup)` is `PUT /messages` on the clicked message. MAX
  replaces the text and the complete attachment list. The edit uses the stored text, format, and
  image token of the message (`sent_messages`). When that row is absent, the edit uses the plain
  text and the image tokens of the callback message, without a format.
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
    ALTERNATIVES_TEXT,
    CONTENT_REJECTED_TEXT,
    BotHandlers,
    handle_alternative_feedback,
    handle_moderation_appeal,
    handle_result_feedback,
)
from chto_za_vino_max_bot.max_api import MaxApiError
from chto_za_vino_max_bot.storage import CandidateRecord, Repository, SentMessage
from chto_za_vino_max_bot.updates import IncomingMessage, MaxUser

BOT = MaxUser(user_id=1, first_name="Bot", last_name=None, username="bot", is_bot=True)
OTHER_USER = user(201, username="other", first_name="Other")

RESULT_MID = "mid.bot-result"
# The plain text of the result message in the callback. MAX gives no HTML for it.
RESULT_PLAIN_TEXT = "Название wine-1\nОткрыть страницу вина"
RESULT_IMAGE = image(50)
# The stored body of the result message, as the photo processor records it.
RESULT_CAPTION = '<b>Название wine-1</b>\n<a href="https://vino-svoe.ru/wines/wine-1">wine-1</a>'
RESULT_TOKEN = "uploaded-result-token"

REJECTION_MID = "mid.bot-rejection"
REJECTION_TOKEN = "uploaded-rejection-token"


def card(slug: str, name: str | None = None) -> dict[str, object]:
    return {
        "name": name or slug,
        "page_url": f"https://vino-svoe.ru/wines/{slug}",
        "producer": None,
        "category": None,
        "color": None,
        "grapes": None,
        "sugar": None,
        "image_url": None,
        "qr_urls": [],
    }


def make_services(repository: Repository) -> SimpleNamespace:
    return SimpleNamespace(repository=repository)


def reserve_request(repository: Repository, *, message_id: str, now: int) -> str:
    reservation = repository.reserve(
        chat_id=DIALOG_CHAT_ID,
        chat_type="dialog",
        message_id=message_id,
        photo_index=0,
        user_id=USER_ID,
        username="tester",
        first_name="Test",
        last_name=None,
        photo_id=9001,
        photo_url="https://i.oneme.example/photo-1.jpg",
        photo_token="token-1",
        now=now,
        limit=50,
        window_seconds=3600,
    )
    assert reservation.request_id is not None
    return reservation.request_id


def recognized_request(repository: Repository) -> str:
    request_id = reserve_request(repository, message_id="mid.source", now=1000)
    repository.update(request_id, status="recognized")
    return request_id


def add_candidates(repository: Repository, request_id: str, count: int = 4) -> None:
    repository.replace_candidates(
        request_id,
        [
            CandidateRecord(rank, f"wine-{rank}", 1.0 - rank / 10, card(f"wine-{rank}"))
            for rank in range(1, count + 1)
        ],
    )


def remember_result(repository: Repository, request_id: str) -> None:
    repository.record_sent_message(
        message_id=RESULT_MID,
        request_id=request_id,
        chat_id=DIALOG_CHAT_ID,
        text=RESULT_CAPTION,
        text_format="html",
        photo_token=RESULT_TOKEN,
        now=1000,
    )


def result_message() -> IncomingMessage:
    """The bot result message with the photo and the feedback keyboard, as MAX sends it back."""
    return message(
        message_id=RESULT_MID,
        sender=BOT,
        text=RESULT_PLAIN_TEXT,
        images=(RESULT_IMAGE,),
    )


def photo(token: str | None) -> dict[str, object]:
    return {"type": "image", "payload": {"token": token}}


def edit(
    text: str,
    attachments: list[dict[str, object]],
    text_format: str | None,
    *,
    message_id: str = RESULT_MID,
) -> dict[str, object]:
    return {
        "chat_id": DIALOG_CHAT_ID,
        "message_id": message_id,
        "text": text,
        "attachments": attachments,
        "text_format": text_format,
    }


def kept_body(stored: bool) -> tuple[str, list[dict[str, object]], str | None]:
    """The text, the image attachments, and the format of the edited result message."""
    if stored:
        return RESULT_CAPTION, [photo(RESULT_TOKEN)], "html"
    return RESULT_PLAIN_TEXT, [photo(RESULT_IMAGE.token)], None


def notifications(api: FakeMaxApi) -> list[str | None]:
    """Return the notifications. Feedback answers never replace the message in the answer."""
    calls = api.calls_of("answer_callback")
    for call in calls:
        assert call["message"] is None
        assert call["callback_id"].startswith("callback-")
    return [call["notification"] for call in calls]


def methods(api: FakeMaxApi) -> list[str]:
    return [call.method for call in api.calls]


def button_rows(attachments: list[dict[str, object]] | None) -> list[list[tuple[str, str]]]:
    return [
        [(button["text"], button["payload"]) for button in row]
        for row in keyboard_buttons(attachments)
    ]


def alternative_rows(request_id: str, labels: list[tuple[int, str]]) -> list[list[tuple[str, str]]]:
    rows = [[(f"{rank}. {label}", f"alternative:{rank}:{request_id}")] for rank, label in labels]
    rows.append([("Ничего из этого", f"alternative:0:{request_id}")])
    return rows


STORED_CASES = pytest.mark.parametrize("stored", [True, False], ids=["stored", "not-stored"])


async def test_result_feedback_is_saved_for_source_user(tmp_path, monkeypatch):
    repository = Repository(tmp_path / "bot.sqlite3")
    request_id = recognized_request(repository)
    api = FakeMaxApi()
    monkeypatch.setattr("chto_za_vino_max_bot.app.time.time", lambda: 1200)

    await handle_result_feedback(
        callback(f"feedback:yes:{request_id}", with_message=False),
        make_services(repository),
        api,
    )

    assert notifications(api) == ["Спасибо! Оценка сохранена."]
    assert api.calls_of("answer_callback")[0]["chat_id"] is None
    assert methods(api) == ["answer_callback"]
    record = repository.admin_request(request_id)
    assert (record.feedback_match, record.feedback_at) == (True, 1200)
    assert (
        repository.save_feedback(
            request_id=request_id,
            user_id=USER_ID,
            matched=False,
            now=1300,
        )
        == "already_saved"
    )
    repository.close()


@STORED_CASES
async def test_positive_feedback_removes_the_keyboard_of_the_clicked_message(tmp_path, stored):
    repository = Repository(tmp_path / "bot.sqlite3")
    request_id = recognized_request(repository)
    if stored:
        remember_result(repository, request_id)
    api = FakeMaxApi()

    await handle_result_feedback(
        callback(f"feedback:yes:{request_id}", source=result_message()),
        make_services(repository),
        api,
    )

    assert notifications(api) == ["Спасибо! Оценка сохранена."]
    text, images, text_format = kept_body(stored)
    # Telegram: edit_reply_markup(reply_markup=None). MAX: the same body without the keyboard.
    assert api.calls_of("edit_message") == [edit(text, images, text_format)]
    assert methods(api) == ["answer_callback", "edit_message"]
    repository.close()


async def test_result_feedback_rejects_another_user(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    request_id = recognized_request(repository)
    add_candidates(repository, request_id)
    api = FakeMaxApi()

    await handle_result_feedback(
        callback(f"feedback:no:{request_id}", from_user=OTHER_USER, source=result_message()),
        make_services(repository),
        api,
    )

    # Telegram shows an alert. MAX has no alert dialog and shows a notification.
    assert notifications(api) == ["Эта оценка недоступна."]
    assert methods(api) == ["answer_callback"]
    # The press of another user does not use the feedback of the source user.
    assert (
        repository.save_feedback(request_id=request_id, user_id=USER_ID, matched=True, now=1300)
        == "saved"
    )
    repository.close()


@STORED_CASES
async def test_negative_feedback_shows_three_alternatives(tmp_path, stored):
    repository = Repository(tmp_path / "bot.sqlite3")
    request_id = recognized_request(repository)
    repository.replace_candidates(
        request_id,
        [
            CandidateRecord(
                rank,
                f"wine-{rank}",
                1.0 - rank / 10,
                card(f"wine-{rank}", f"Название wine-{rank}"),
            )
            for rank in range(1, 5)
        ],
    )
    if stored:
        remember_result(repository, request_id)
    api = FakeMaxApi()

    await handle_result_feedback(
        callback(f"feedback:no:{request_id}", source=result_message()),
        make_services(repository),
        api,
    )

    assert notifications(api) == ["Спасибо! Выберите возможный вариант."]
    [edited] = api.calls_of("edit_message")
    assert button_rows(edited["attachments"]) == alternative_rows(
        request_id,
        [(2, "Название wine-2"), (3, "Название wine-3"), (4, "Название wine-4")],
    )
    assert all(
        button["type"] == "callback"
        for row in keyboard_buttons(edited["attachments"])
        for button in row
    )
    text, images, text_format = kept_body(stored)
    keyboard = edited["attachments"][-1]
    # The edit targets the clicked message and keeps its text and photo.
    assert edited == edit(text, [*images, keyboard], text_format)
    assert methods(api) == ["answer_callback", "edit_message"]
    repository.close()


async def test_negative_feedback_retry_restores_alternatives(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    request_id = recognized_request(repository)
    add_candidates(repository, request_id)
    remember_result(repository, request_id)
    assert (
        repository.save_feedback(
            request_id=request_id,
            user_id=USER_ID,
            matched=False,
            now=1100,
        )
        == "saved"
    )
    api = FakeMaxApi()

    await handle_result_feedback(
        callback(f"feedback:no:{request_id}", source=result_message()),
        make_services(repository),
        api,
    )

    assert notifications(api) == ["Оценка уже сохранена. Показываю варианты."]
    [edited] = api.calls_of("edit_message")
    assert len(keyboard_buttons(edited["attachments"])) == 4
    assert edited["message_id"] == RESULT_MID
    repository.close()


async def test_negative_feedback_sends_fallback_when_edit_fails(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    request_id = recognized_request(repository)
    add_candidates(repository, request_id)
    remember_result(repository, request_id)
    api = FakeMaxApi()
    api.fail_on["edit_message"] = MaxApiError(400, "edit.failed", "message is not editable")

    await handle_result_feedback(
        callback(f"feedback:no:{request_id}", source=result_message()),
        make_services(repository),
        api,
    )

    assert methods(api) == ["answer_callback", "edit_message", "send_message"]
    [fallback] = api.calls_of("send_message")
    assert fallback["text"] == "Возможные варианты:"
    assert len(keyboard_buttons(fallback["attachments"])) == 4
    # Telegram: message.answer(text, reply_markup=...). MAX: a new HTML message in the chat.
    assert fallback == {
        "chat_id": DIALOG_CHAT_ID,
        "text": ALTERNATIVES_TEXT,
        "attachments": [api.calls_of("edit_message")[0]["attachments"][-1]],
        "reply_to": None,
        "text_format": "html",
        "disable_link_preview": False,
    }
    # The fallback message has a callback keyboard, so its body is stored for the next edit.
    assert repository.sent_message("mid.bot-1") == SentMessage(
        message_id="mid.bot-1",
        request_id=request_id,
        chat_id=DIALOG_CHAT_ID,
        text=ALTERNATIVES_TEXT,
        text_format="html",
        photo_token=None,
    )

    # A choice in the fallback message edits that message from its stored body.
    api.fail_on.clear()
    fallback_message = message(message_id="mid.bot-1", sender=BOT, text=ALTERNATIVES_TEXT)
    await handle_alternative_feedback(
        callback(
            f"alternative:3:{request_id}",
            source=fallback_message,
            callback_id="callback-2",
        ),
        make_services(repository),
        api,
    )

    assert notifications(api)[-1] == "Спасибо! Ответ сохранён."
    assert api.calls_of("edit_message")[-1] == edit(
        ALTERNATIVES_TEXT,
        [],
        "html",
        message_id="mid.bot-1",
    )
    assert repository.admin_request(request_id).feedback_selected_rank == 3
    repository.close()


async def test_negative_feedback_uses_the_slug_for_a_candidate_without_a_card(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    request_id = recognized_request(repository)
    repository.replace_candidates(
        request_id,
        [CandidateRecord(rank, f"wine-{rank}", 1.0 - rank / 10) for rank in range(1, 5)],
    )
    api = FakeMaxApi()

    await handle_result_feedback(
        callback(f"feedback:no:{request_id}", source=result_message()),
        make_services(repository),
        api,
    )

    [edited] = api.calls_of("edit_message")
    assert button_rows(edited["attachments"]) == alternative_rows(
        request_id,
        [(2, "wine-2"), (3, "wine-3"), (4, "wine-4")],
    )
    repository.close()


async def test_negative_feedback_shows_the_available_alternatives(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    request_id = recognized_request(repository)
    repository.replace_candidates(
        request_id,
        [
            CandidateRecord(1, "wine-1", 0.9, card("wine-1")),
            CandidateRecord(2, "wine-2", 0.8, card("wine-2", "Второе вино")),
        ],
    )
    api = FakeMaxApi()

    await handle_result_feedback(
        callback(f"feedback:no:{request_id}", source=result_message()),
        make_services(repository),
        api,
    )

    [edited] = api.calls_of("edit_message")
    assert button_rows(edited["attachments"]) == alternative_rows(
        request_id,
        [(2, "Второе вино")],
    )
    repository.close()


async def test_negative_feedback_without_alternatives_shows_a_notification(tmp_path):
    # Telegram: test_negative_feedback_without_alternatives_shows_an_alert.
    repository = Repository(tmp_path / "bot.sqlite3")
    request_id = recognized_request(repository)
    repository.replace_candidates(
        request_id,
        [CandidateRecord(1, "wine-1", 0.9, card("wine-1"))],
    )
    api = FakeMaxApi()

    await handle_result_feedback(
        callback(f"feedback:no:{request_id}", source=result_message()),
        make_services(repository),
        api,
    )

    assert notifications(api) == [
        "Оценка сохранена, но альтернативы для этого результата недоступны."
    ]
    assert methods(api) == ["answer_callback"]
    assert repository.admin_request(request_id).feedback_match is False
    repository.close()


async def test_negative_feedback_without_a_callback_message_only_answers(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    request_id = recognized_request(repository)
    add_candidates(repository, request_id)
    api = FakeMaxApi()

    await handle_result_feedback(
        callback(f"feedback:no:{request_id}", with_message=False),
        make_services(repository),
        api,
    )

    assert notifications(api) == ["Спасибо! Выберите возможный вариант."]
    assert methods(api) == ["answer_callback"]
    repository.close()


async def test_alternative_and_moderation_callbacks_are_saved(tmp_path, monkeypatch):
    monkeypatch.setattr("chto_za_vino_max_bot.app.time.time", lambda: 1250)
    repository = Repository(tmp_path / "bot.sqlite3")
    request_id = recognized_request(repository)
    repository.replace_candidates(
        request_id,
        [
            CandidateRecord(1, "wine-1", 0.9),
            CandidateRecord(2, "wine-2", 0.8),
        ],
    )
    assert (
        repository.save_feedback(
            request_id=request_id,
            user_id=USER_ID,
            matched=False,
            now=1100,
        )
        == "saved"
    )
    remember_result(repository, request_id)
    api = FakeMaxApi()

    await handle_alternative_feedback(
        callback(f"alternative:2:{request_id}", source=result_message()),
        make_services(repository),
        api,
    )

    assert notifications(api) == ["Спасибо! Ответ сохранён."]
    # Telegram: edit_reply_markup(reply_markup=None). MAX: the stored body without a keyboard.
    assert api.calls_of("edit_message") == [edit(RESULT_CAPTION, [photo(RESULT_TOKEN)], "html")]
    record = repository.admin_request(request_id)
    assert (
        record.feedback_selected_rank,
        record.feedback_selected_slug,
        record.feedback_alternative_at,
    ) == (2, "wine-2", 1250)

    quarantined_id = reserve_request(repository, message_id="mid.source-2", now=1200)
    repository.update(quarantined_id, status="quarantined")
    repository.record_sent_message(
        message_id=REJECTION_MID,
        request_id=quarantined_id,
        chat_id=DIALOG_CHAT_ID,
        text=CONTENT_REJECTED_TEXT,
        text_format="html",
        photo_token=REJECTION_TOKEN,
        now=1200,
    )
    rejection = message(
        message_id=REJECTION_MID,
        sender=BOT,
        text="Контент признан неподходящим и не передан в распознавание.",
        images=(image(60),),
    )
    api = FakeMaxApi()

    await handle_moderation_appeal(
        callback(f"moderation_error:{quarantined_id}", source=rejection),
        make_services(repository),
        api,
    )

    assert notifications(api) == ["Спасибо! Проверим срабатывание фильтра."]
    assert api.calls_of("edit_message") == [
        edit(CONTENT_REJECTED_TEXT, [photo(REJECTION_TOKEN)], "html", message_id=REJECTION_MID)
    ]
    assert repository.admin_request(quarantined_id).moderation_appeal_at == 1250
    repository.close()


async def test_repeated_choices_remove_the_keyboard_again_and_foreign_choices_do_not(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    request_id = recognized_request(repository)
    add_candidates(repository, request_id)
    assert (
        repository.save_feedback(request_id=request_id, user_id=USER_ID, matched=False, now=1100)
        == "saved"
    )
    quarantined_id = reserve_request(repository, message_id="mid.source-2", now=1200)
    repository.update(quarantined_id, status="quarantined")
    rejection = message(message_id=REJECTION_MID, sender=BOT, text="…", images=(image(60),))
    services = make_services(repository)
    api = FakeMaxApi()

    for event in (
        callback(f"alternative:2:{request_id}", from_user=OTHER_USER, source=result_message()),
        callback(f"alternative:2:{request_id}", source=result_message()),
        callback(f"alternative:3:{request_id}", source=result_message()),
    ):
        await handle_alternative_feedback(event, services, api)
    for event in (
        callback(f"moderation_error:{quarantined_id}", from_user=OTHER_USER, source=rejection),
        callback(f"moderation_error:{quarantined_id}", source=rejection),
        callback(f"moderation_error:{quarantined_id}", source=rejection),
    ):
        await handle_moderation_appeal(event, services, api)

    # Telegram shows an alert for an unavailable choice. MAX shows a notification.
    assert notifications(api) == [
        "Этот вариант недоступен.",
        "Спасибо! Ответ сохранён.",
        "Ответ уже сохранён.",
        "Это обращение недоступно.",
        "Спасибо! Проверим срабатывание фильтра.",
        "Обращение уже сохранено.",
    ]
    # A foreign choice changes nothing. A repeated choice removes the keyboard again, so a
    # failed earlier edit is repaired (CLAUDE.md, "Common mistakes").
    assert [call["message_id"] for call in api.calls_of("edit_message")] == [
        RESULT_MID,
        RESULT_MID,
        REJECTION_MID,
        REJECTION_MID,
    ]
    assert repository.admin_request(request_id).feedback_selected_rank == 2
    repository.close()


@pytest.mark.parametrize(
    ("payload", "notification"),
    [
        ("feedback:maybe:request", "Некорректная оценка."),
        ("alternative:two:request", "Некорректный вариант."),
        ("moderation_error:", "Некорректное обращение."),
        ("unknown:payload", None),
    ],
    ids=["feedback", "alternative", "moderation-appeal", "unknown"],
)
async def test_callbacks_are_routed_by_payload_prefix(tmp_path, payload, notification):
    repository = Repository(tmp_path / "bot.sqlite3")
    api = FakeMaxApi()
    handlers = BotHandlers(make_services(repository), api, SimpleNamespace())

    await handlers.handle(callback(payload, source=result_message()))

    assert api.calls_of("answer_callback") == [
        {
            "chat_id": DIALOG_CHAT_ID,
            "callback_id": "callback-1",
            "notification": notification,
            "message": None,
            "disable_link_preview": False,
        }
    ]
    assert methods(api) == ["answer_callback"]
    repository.close()


async def test_feedback_callback_is_handled_through_the_router(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    request_id = recognized_request(repository)
    remember_result(repository, request_id)
    api = FakeMaxApi()
    handlers = BotHandlers(make_services(repository), api, SimpleNamespace())

    await handlers.handle(callback(f"feedback:yes:{request_id}", source=result_message()))

    assert notifications(api) == ["Спасибо! Оценка сохранена."]
    assert api.calls_of("edit_message") == [edit(RESULT_CAPTION, [photo(RESULT_TOKEN)], "html")]
    assert repository.admin_request(request_id).feedback_match is True
    repository.close()
