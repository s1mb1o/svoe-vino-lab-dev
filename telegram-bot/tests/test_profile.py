from chto_za_vino_bot.profile import (
    ADMIN_COMMANDS,
    AGE_GATE_TEXT,
    COMMANDS,
    DESCRIPTION,
    HELP_TEXT,
    LEGAL_NOTICE,
    SHORT_DESCRIPTION,
    menu_commands,
)


def test_profile_text_fits_telegram_limits():
    assert 1 <= len(SHORT_DESCRIPTION) <= 120
    assert 1 <= len(DESCRIPTION) <= 512


def test_expected_commands_exist():
    assert [command.command for command in COMMANDS] == ["start", "help", "stats", "privacy"]
    assert [command.command for command in ADMIN_COMMANDS] == [
        "start",
        "help",
        "stats",
        "privacy",
        "users",
        "reset_limit",
    ]


def test_menu_shows_unlink_only_with_the_account_link():
    assert menu_commands(False) == (COMMANDS, ADMIN_COMMANDS)
    commands, admin_commands = menu_commands(True)
    assert [command.command for command in commands] == ["start", "help", "stats", "privacy", "unlink"]
    assert [command.command for command in admin_commands] == [
        "start",
        "help",
        "stats",
        "privacy",
        "unlink",
        "users",
        "reset_limit",
    ]
    assert all(1 <= len(command.description) <= 256 for command in admin_commands)


def test_sync_profile_sends_the_unlink_menu_when_the_link_is_on():
    import asyncio

    from chto_za_vino_bot.app import sync_profile

    class FakeBot:
        def __init__(self):
            self.menus = []

        async def set_my_short_description(self, **_):
            pass

        async def set_my_description(self, **_):
            pass

        async def set_my_commands(self, commands, scope=None):
            self.menus.append(([command.command for command in commands], scope))

    bot = FakeBot()
    asyncio.run(sync_profile(bot, 42, account_link=True))
    assert "unlink" in bot.menus[0][0] and bot.menus[0][1] is None
    assert "unlink" in bot.menus[1][0] and bot.menus[1][1].chat_id == 42
    bot = FakeBot()
    asyncio.run(sync_profile(bot, 42))
    assert all("unlink" not in menu for menu, _ in bot.menus)


def test_age_gate_contains_required_notice():
    assert "Подтвердите, что вам уже исполнилось 18 лет." in AGE_GATE_TEXT
    assert "Справочно · не предложение о продаже." in LEGAL_NOTICE
    assert "18+ · Чрезмерное употребление алкоголя вредит вашему здоровью." in LEGAL_NOTICE
    assert "каталоге vino-svoe.ru" in LEGAL_NOTICE


def test_help_explains_single_photo_and_album_support():
    assert "одно фото или альбом" in HELP_TEXT
    assert "Каждая фотография обрабатывается отдельно" in HELP_TEXT
