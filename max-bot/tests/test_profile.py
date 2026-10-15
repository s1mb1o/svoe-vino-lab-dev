import ast
import re
from pathlib import Path

import pytest

from chto_za_vino_max_bot import profile
from chto_za_vino_max_bot.max_api import TEXT_LIMIT
from chto_za_vino_max_bot.profile import (
    ADMIN_COMMANDS,
    AGE_GATE_TEXT,
    COMMANDS,
    DESCRIPTION,
    HELP_TEXT,
    LEGAL_NOTICE,
    PRIVACY_TEXT,
    SHORT_DESCRIPTION,
    privacy_text,
)

TELEGRAM_PROFILE = (
    Path(__file__).resolve().parents[2] / "telegram-bot/src/chto_za_vino_bot/profile.py"
)
TEXT_NAMES = (
    "SHORT_DESCRIPTION",
    "DESCRIPTION",
    "LEGAL_NOTICE",
    "START_TEXT",
    "AGE_GATE_TEXT",
    "START_CONFIRMED_TEXT",
    "MINOR_TEXT",
    "HELP_TEXT",
    "PRIVACY_TEXT",
)
MESSAGE_TEXT_NAMES = (
    "START_TEXT",
    "AGE_GATE_TEXT",
    "START_CONFIRMED_TEXT",
    "MINOR_TEXT",
    "HELP_TEXT",
    "PRIVACY_TEXT",
)


def test_profile_text_fits_max_limits():
    # The bot card on business.max.ru accepts a description of at most 200 characters.
    assert 1 <= len(SHORT_DESCRIPTION) <= 200
    # The long description is the Telegram text. It keeps the Telegram limit.
    assert 1 <= len(DESCRIPTION) <= 512
    for name in MESSAGE_TEXT_NAMES:
        assert 1 <= len(getattr(profile, name)) <= TEXT_LIMIT, name
    assert len(privacy_text(9_223_372_036_854_775_807)) <= TEXT_LIMIT


def test_expected_commands_exist():
    assert [command["name"] for command in COMMANDS] == ["start", "help", "stats", "privacy"]
    assert [command["name"] for command in ADMIN_COMMANDS] == [
        "start",
        "help",
        "stats",
        "privacy",
        "users",
        "reset_limit",
    ]


def test_commands_are_plain_max_bot_commands():
    # PATCH /me/commands takes up to 32 BotCommand objects: name 1-64, description 1-128.
    assert len(ADMIN_COMMANDS) <= 32
    assert ADMIN_COMMANDS[: len(COMMANDS)] == COMMANDS
    for command in ADMIN_COMMANDS:
        assert type(command) is dict
        assert set(command) == {"name", "description"}
        assert re.fullmatch(r"[a-z][a-z_]{0,63}", command["name"])
        assert 1 <= len(command["description"]) <= 128


def test_age_gate_contains_required_notice():
    assert "Подтвердите, что вам уже исполнилось 18 лет." in AGE_GATE_TEXT
    assert "Справочно · не предложение о продаже." in LEGAL_NOTICE
    assert "18+ · Чрезмерное употребление алкоголя вредит вашему здоровью." in LEGAL_NOTICE
    assert "каталоге vino-svoe.ru" in LEGAL_NOTICE


def test_help_explains_single_photo_and_album_support():
    assert "одно фото или альбом" in HELP_TEXT
    assert "Каждая фотография обрабатывается отдельно" in HELP_TEXT


def test_privacy_text_names_the_max_user_id():
    assert "MAX user ID" in PRIVACY_TEXT
    assert "укажите MAX user ID." in PRIVACY_TEXT
    for name in TEXT_NAMES:
        assert "Telegram" not in getattr(profile, name), name
    assert privacy_text(None) == PRIVACY_TEXT
    assert privacy_text(123456789) == (
        f"{PRIVACY_TEXT}\n\nВаш MAX user ID: <code>123456789</code>"
    )


def _render(node: ast.expr, names: dict[str, str]) -> str:
    """Render a string constant or an f-string that refers to earlier constants."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(_render(value, names) for value in node.values)
    if (
        isinstance(node, ast.FormattedValue)
        and isinstance(node.value, ast.Name)
        and node.conversion == -1
        and node.format_spec is None
    ):
        return names[node.value.id]
    raise TypeError(f"unsupported profile expression: {ast.dump(node)}")


def _telegram_profile() -> tuple[dict[str, str], list[dict[str, str]]]:
    """Read the Telegram texts and commands without an import of aiogram."""
    tree = ast.parse(TELEGRAM_PROFILE.read_text(encoding="utf-8"))
    texts: dict[str, str] = {}
    commands: list[dict[str, str]] = []
    for node in tree.body:
        if not (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            continue
        if isinstance(node.value, (ast.Constant, ast.JoinedStr)):
            texts[node.targets[0].id] = _render(node.value, texts)
        elif isinstance(node.value, ast.List):
            # COMMANDS, then the administrator commands after `*COMMANDS`, in source order.
            commands.extend(
                {keyword.arg: ast.literal_eval(keyword.value) for keyword in item.keywords}
                for item in node.value.elts
                if isinstance(item, ast.Call)
                and isinstance(item.func, ast.Name)
                and item.func.id == "BotCommand"
            )
    return texts, commands


@pytest.mark.skipif(not TELEGRAM_PROFILE.is_file(), reason="../telegram-bot is not present")
def test_profile_text_is_the_telegram_text_with_max_names():
    texts, commands = _telegram_profile()

    for name in TEXT_NAMES:
        assert getattr(profile, name) == texts[name].replace("Telegram", "MAX"), name
    assert [
        {"name": item["command"], "description": item["description"]} for item in commands
    ] == ADMIN_COMMANDS
