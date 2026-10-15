"""Administrator commands of the MAX bot. Port of `telegram-bot/tests/test_admin_commands.py`.

MAX differences:
- The administrator is `BOT_ADMIN_USER_ID` in a `dialog` chat. Telegram also compares the private
  chat ID with the user ID, but a MAX dialog chat ID is not the user ID. The tests use a dialog
  chat ID that differs from the administrator ID.
- The handlers answer through `Chat`: one `send_message` call with HTML and no reply link.
- `BotHandlers` takes the command arguments from the message text.
"""

from types import SimpleNamespace

import pytest
from fakes import ADMIN_ID, DIALOG_CHAT_ID, FakeMaxApi, message, user

from chto_za_vino_max_bot.app import (
    BotHandlers,
    Chat,
    handle_reset_limit_command,
    handle_stats_command,
    handle_users_command,
)
from chto_za_vino_max_bot.storage import Repository
from chto_za_vino_max_bot.updates import IncomingMessage, MaxUser

ADMIN = user(ADMIN_ID, username="s1mb1o", first_name="Shasa (ALOLA)")
ADMIN_ONLY = "Команда доступна только администратору."
GROUP_CHAT_ID = -100123456


def make_services(repository: Repository) -> SimpleNamespace:
    return SimpleNamespace(
        repository=repository,
        settings=SimpleNamespace(
            admin_user_id=ADMIN_ID,
            rate_limit=2,
            rate_window_seconds=3600,
        ),
    )


def add_request(
    repository: Repository,
    *,
    user_id: int,
    username: str,
    message_id: str,
    now: int,
) -> None:
    result = repository.reserve(
        # In MAX, the dialog chat ID is not the user ID.
        chat_id=10_000 + user_id,
        chat_type="dialog",
        message_id=message_id,
        photo_index=0,
        user_id=user_id,
        username=username,
        first_name=username.title(),
        last_name=None,
        photo_id=None,
        photo_url=f"https://i.oneme.example/{message_id}.jpg",
        photo_token=None,
        now=now,
        limit=2,
        window_seconds=3600,
    )
    assert result.allowed


def command(
    text: str,
    sender: MaxUser,
    *,
    chat_type: str = "dialog",
    chat_id: int = DIALOG_CHAT_ID,
) -> IncomingMessage:
    return message(
        message_id="mid.command",
        chat_id=chat_id,
        chat_type=chat_type,
        sender=sender,
        text=text,
    )


def chat_of(api: FakeMaxApi, source: IncomingMessage) -> Chat:
    return Chat(api, source.chat_id, message_id=source.message_id)


def answers(api: FakeMaxApi, *, chat_id: int = DIALOG_CHAT_ID) -> list[str]:
    """Return the texts of `message.answer(...)`: HTML messages to the chat without a reply."""
    calls = api.calls_of("send_message")
    for call in calls:
        assert call["chat_id"] == chat_id
        assert call["reply_to"] is None
        assert call["attachments"] is None
        assert call["text_format"] == "html"
    return [call["text"] for call in calls]


def reset_answer(username: str, user_id: int, count: int) -> str:
    return (
        f"Лимит пользователя @{username} (ID <code>{user_id}</code>) сброшен.\n"
        f"Исключено из текущего окна: {count}."
    )


async def test_regular_stats_show_only_current_user(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    add_request(repository, user_id=100, username="first", message_id="mid.1", now=1000)
    add_request(repository, user_id=200, username="second", message_id="mid.2", now=1001)
    services = make_services(repository)
    api = FakeMaxApi()
    source = command("/stats", user(100, username="first", first_name="First"))

    await handle_stats_command(
        chat_of(api, source),
        source,
        services,
        SimpleNamespace(waiting=3, active=1),
        now=1100,
    )

    [text] = answers(api)
    assert "Ваша статистика" in text
    assert "Всего фотографий: 1" in text
    assert "Участников" not in text
    assert "В очереди" not in text
    repository.close()


async def test_admin_stats_show_aggregate_values(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    add_request(
        repository,
        user_id=ADMIN_ID,
        username="s1mb1o",
        message_id="mid.1",
        now=1000,
    )
    add_request(repository, user_id=200, username="second", message_id="mid.2", now=1001)
    services = make_services(repository)
    api = FakeMaxApi()
    source = command("/stats", ADMIN)
    assert source.chat_id != ADMIN_ID

    await handle_stats_command(
        chat_of(api, source),
        source,
        services,
        SimpleNamespace(waiting=3, active=1),
        now=1100,
    )

    [text] = answers(api)
    assert "Общая статистика" in text
    assert "Всего фотографий: 2" in text
    assert "Участников: 2" in text
    assert "В очереди: 3" in text
    assert "Обрабатывается: 1" in text
    assert "Ваши запросы за час: 1/2" in text
    repository.close()


async def test_admin_can_list_users_and_reset_by_username(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    add_request(
        repository,
        user_id=ADMIN_ID,
        username="s1mb1o",
        message_id="mid.1",
        now=1000,
    )
    add_request(repository, user_id=200, username="tester", message_id="mid.2", now=1001)
    add_request(repository, user_id=200, username="tester", message_id="mid.3", now=1002)
    services = make_services(repository)
    api = FakeMaxApi()
    source = command("/users", ADMIN)
    chat = chat_of(api, source)

    await handle_users_command(chat, source, None, services, now=1100)

    [listing] = answers(api)
    assert "Пользователи" in listing
    assert "@s1mb1o" in listing
    assert "@tester" in listing
    assert "User ID:" in listing
    assert "1 января 1970, 03:16:42 МСК" in listing
    # The user block names MAX instead of Telegram. The latest request is first.
    assert "<b>1. MAX:</b> @tester" in listing
    assert "<b>2. MAX:</b> @s1mb1o" in listing
    assert "Telegram" not in listing

    await handle_reset_limit_command(chat, source, "@tester", services, now=1100)

    assert "сброшен" in answers(api)[-1]
    assert answers(api)[-1] == reset_answer("tester", 200, 2)
    assert repository.stats(200, 1100, 3600).user_window == 0
    assert repository.stats(200, 1100, 3600).total == 2

    await handle_reset_limit_command(chat, source, None, services, now=1100)

    assert answers(api)[-1] == reset_answer("s1mb1o", ADMIN_ID, 1)
    assert repository.stats(ADMIN_ID, 1100, 3600).user_window == 0
    repository.close()


async def test_admin_commands_reject_regular_user(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    services = make_services(repository)
    api = FakeMaxApi()
    source = command("/users", user(200, username="tester", first_name="Tester"))
    chat = chat_of(api, source)

    await handle_users_command(chat, source, None, services, now=1100)
    await handle_reset_limit_command(chat, source, str(ADMIN_ID), services, now=1100)

    assert answers(api) == [ADMIN_ONLY, ADMIN_ONLY]
    repository.close()


@pytest.mark.parametrize("chat_type", ["chat", "channel"])
async def test_admin_commands_are_rejected_outside_the_dialog(tmp_path, chat_type):
    # Telegram: the private chat of the administrator. MAX: a chat of the `dialog` type.
    repository = Repository(tmp_path / "bot.sqlite3")
    add_request(
        repository,
        user_id=ADMIN_ID,
        username="s1mb1o",
        message_id="mid.1",
        now=1000,
    )
    add_request(repository, user_id=200, username="tester", message_id="mid.2", now=1001)
    services = make_services(repository)
    api = FakeMaxApi()
    source = command("/users", ADMIN, chat_type=chat_type, chat_id=GROUP_CHAT_ID)
    chat = chat_of(api, source)

    await handle_users_command(chat, source, None, services, now=1100)
    await handle_reset_limit_command(chat, source, None, services, now=1100)
    await handle_stats_command(
        chat,
        source,
        services,
        SimpleNamespace(waiting=3, active=1),
        now=1100,
    )

    users_answer, reset_limit_answer, stats_answer = answers(api, chat_id=GROUP_CHAT_ID)
    assert [users_answer, reset_limit_answer] == [ADMIN_ONLY, ADMIN_ONLY]
    assert repository.stats(ADMIN_ID, 1100, 3600).user_window == 1
    # Outside the dialog, /stats shows only the statistics of the administrator account.
    assert "Ваша статистика" in stats_answer
    assert "Всего фотографий: 1" in stats_answer
    assert "Участников" not in stats_answer
    assert "В очереди" not in stats_answer
    repository.close()


async def test_admin_commands_take_arguments_from_the_message_text(tmp_path, monkeypatch):
    monkeypatch.setattr("chto_za_vino_max_bot.app.time.time", lambda: 1100)
    repository = Repository(tmp_path / "bot.sqlite3")
    add_request(
        repository,
        user_id=ADMIN_ID,
        username="s1mb1o",
        message_id="mid.1",
        now=1000,
    )
    add_request(repository, user_id=200, username="tester", message_id="mid.2", now=1001)
    add_request(repository, user_id=200, username="tester", message_id="mid.3", now=1002)
    api = FakeMaxApi()
    handlers = BotHandlers(make_services(repository), api, SimpleNamespace(waiting=3, active=1))

    for text in (
        "/users",
        "/users 2",
        "/users два",
        "/reset_limit 200",
        "/reset_limit @TESTER",
        "/reset_limit @nobody",
        "/reset_limit two words",
        "/reset_limit@se14697933_bot",
        "/stats",
    ):
        await handlers.handle(command(text, ADMIN))

    texts = answers(api)
    assert len(texts) == 9
    assert texts[0].startswith("<b>Пользователи</b> · страница 1/1 · всего 2\n\n")
    assert texts[1] == "Страница не найдена. Доступно страниц: 1."
    assert texts[2] == "Использование: /users [номер страницы]"
    assert texts[3] == reset_answer("tester", 200, 2)
    assert texts[4] == reset_answer("tester", 200, 0)
    assert texts[5] == "Пользователь не найден."
    assert texts[6] == "Использование: /reset_limit [user_id или @username]"
    assert texts[7] == reset_answer("s1mb1o", ADMIN_ID, 1)
    assert "Общая статистика" in texts[8]
    assert "В очереди: 3" in texts[8]
    assert "Ваши запросы за час: 0/2" in texts[8]
    repository.close()


HUGE_NUMBER = "99999999999999999999"


async def test_users_with_a_huge_page_number_reports_a_missing_page(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    add_request(repository, user_id=ADMIN_ID, username="s1mb1o", message_id="mid.1", now=1000)
    api = FakeMaxApi()
    source = command(f"/users {HUGE_NUMBER}", ADMIN)

    try:
        await handle_users_command(
            chat_of(api, source),
            source,
            HUGE_NUMBER,
            make_services(repository),
            now=1100,
        )
    finally:
        repository.close()

    assert answers(api) == ["Страница не найдена. Доступно страниц: 1."]


async def test_reset_limit_with_a_huge_user_id_reports_an_unknown_user(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    api = FakeMaxApi()
    source = command(f"/reset_limit {HUGE_NUMBER}", ADMIN)

    try:
        await handle_reset_limit_command(
            chat_of(api, source),
            source,
            HUGE_NUMBER,
            make_services(repository),
            now=1100,
        )
    finally:
        repository.close()

    assert answers(api) == ["Пользователь не найден."]


async def test_command_arguments_after_a_line_break_are_read(tmp_path, monkeypatch):
    monkeypatch.setattr("chto_za_vino_max_bot.app.time.time", lambda: 1100)
    repository = Repository(tmp_path / "bot.sqlite3")
    add_request(repository, user_id=200, username="tester", message_id="mid.2", now=1001)
    api = FakeMaxApi()
    handlers = BotHandlers(make_services(repository), api, SimpleNamespace(waiting=0, active=0))

    try:
        await handlers.handle(command("/reset_limit\n@tester", ADMIN))
    finally:
        repository.close()

    assert answers(api) == [reset_answer("tester", 200, 1)]
