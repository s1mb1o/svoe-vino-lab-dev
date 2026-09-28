from types import SimpleNamespace

from chto_za_vino_bot.app import (
    handle_reset_limit_command,
    handle_stats_command,
    handle_users_command,
)
from chto_za_vino_bot.storage import Repository

ADMIN_USER_ID = 207286210


class FakeMessage:
    def __init__(
        self,
        user_id: int,
        *,
        username: str | None,
        first_name: str,
    ) -> None:
        self.from_user = SimpleNamespace(
            id=user_id,
            username=username,
            first_name=first_name,
            last_name=None,
        )
        self.chat = SimpleNamespace(id=user_id)
        self.answers: list[str] = []

    async def answer(self, text: str, **kwargs: object) -> None:
        self.answers.append(text)


def make_services(repository: Repository) -> SimpleNamespace:
    return SimpleNamespace(
        repository=repository,
        settings=SimpleNamespace(
            admin_user_id=ADMIN_USER_ID,
            rate_limit=2,
            rate_window_seconds=3600,
        ),
    )


def add_request(
    repository: Repository,
    *,
    user_id: int,
    username: str,
    message_id: int,
    now: int,
) -> None:
    result = repository.reserve(
        chat_id=user_id,
        message_id=message_id,
        user_id=user_id,
        username=username,
        first_name=username.title(),
        last_name=None,
        file_id=f"file-{message_id}",
        file_unique_id=f"unique-{message_id}",
        now=now,
        limit=2,
        window_seconds=3600,
    )
    assert result.allowed


async def test_regular_stats_show_only_current_user(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    add_request(repository, user_id=100, username="first", message_id=1, now=1000)
    add_request(repository, user_id=200, username="second", message_id=2, now=1001)
    services = make_services(repository)
    message = FakeMessage(100, username="first", first_name="First")

    await handle_stats_command(
        message,
        services,
        SimpleNamespace(waiting=3, active=1),
        now=1100,
    )

    assert "Ваша статистика" in message.answers[0]
    assert "Всего фотографий: 1" in message.answers[0]
    assert "Участников" not in message.answers[0]
    assert "В очереди" not in message.answers[0]
    repository.close()


async def test_admin_stats_show_aggregate_values(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    add_request(
        repository,
        user_id=ADMIN_USER_ID,
        username="s1mb1o",
        message_id=1,
        now=1000,
    )
    add_request(repository, user_id=200, username="second", message_id=2, now=1001)
    services = make_services(repository)
    message = FakeMessage(ADMIN_USER_ID, username="s1mb1o", first_name="Shasa (ALOLA)")

    await handle_stats_command(
        message,
        services,
        SimpleNamespace(waiting=3, active=1),
        now=1100,
    )

    assert "Общая статистика" in message.answers[0]
    assert "Всего фотографий: 2" in message.answers[0]
    assert "Участников: 2" in message.answers[0]
    assert "В очереди: 3" in message.answers[0]
    repository.close()


async def test_admin_can_list_users_and_reset_by_username(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    add_request(
        repository,
        user_id=ADMIN_USER_ID,
        username="s1mb1o",
        message_id=1,
        now=1000,
    )
    add_request(repository, user_id=200, username="tester", message_id=2, now=1001)
    add_request(repository, user_id=200, username="tester", message_id=3, now=1002)
    services = make_services(repository)
    message = FakeMessage(ADMIN_USER_ID, username="s1mb1o", first_name="Shasa (ALOLA)")

    await handle_users_command(message, SimpleNamespace(args=None), services, now=1100)

    assert "Пользователи" in message.answers[0]
    assert "@s1mb1o" in message.answers[0]
    assert "@tester" in message.answers[0]
    assert "User ID:" in message.answers[0]
    assert "1 января 1970, 03:16:42 МСК" in message.answers[0]

    await handle_reset_limit_command(
        message,
        SimpleNamespace(args="@tester"),
        services,
        now=1100,
    )

    assert "сброшен" in message.answers[-1]
    assert repository.stats(200, 1100, 3600).user_window == 0
    assert repository.stats(200, 1100, 3600).total == 2

    await handle_reset_limit_command(
        message,
        SimpleNamespace(args=None),
        services,
        now=1100,
    )

    assert repository.stats(ADMIN_USER_ID, 1100, 3600).user_window == 0
    repository.close()


async def test_admin_commands_reject_regular_user(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    services = make_services(repository)
    message = FakeMessage(200, username="tester", first_name="Tester")

    await handle_users_command(message, SimpleNamespace(args=None), services, now=1100)
    await handle_reset_limit_command(
        message,
        SimpleNamespace(args=str(ADMIN_USER_ID)),
        services,
        now=1100,
    )

    assert message.answers == [
        "Команда доступна только администратору.",
        "Команда доступна только администратору.",
    ]
    repository.close()


async def test_admin_commands_are_rejected_outside_private_chat(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    services = make_services(repository)
    message = FakeMessage(ADMIN_USER_ID, username="s1mb1o", first_name="Shasa (ALOLA)")
    message.chat.id = -100123456

    await handle_users_command(message, SimpleNamespace(args=None), services, now=1100)

    assert message.answers == ["Команда доступна только администратору."]
    repository.close()
