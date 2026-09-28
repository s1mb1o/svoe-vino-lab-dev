from chto_za_vino_bot.profile import (
    ADMIN_COMMANDS,
    AGE_GATE_TEXT,
    COMMANDS,
    DESCRIPTION,
    LEGAL_NOTICE,
    SHORT_DESCRIPTION,
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


def test_age_gate_contains_required_notice():
    assert "Подтвердите, что вам уже исполнилось 18 лет." in AGE_GATE_TEXT
    assert "Справочно · не предложение о продаже." in LEGAL_NOTICE
    assert "18+ · Чрезмерное употребление алкоголя вредит вашему здоровью." in LEGAL_NOTICE
    assert "каталоге vino-svoe.ru" in LEGAL_NOTICE
