from __future__ import annotations

import asyncio

from aiogram import Bot
from aiogram.types import BotCommandScopeChat

from .config import Settings
from .profile import DESCRIPTION, SHORT_DESCRIPTION, menu_commands


async def run() -> None:
    settings = Settings.from_env()
    commands, admin_commands = menu_commands(bool(settings.account_endpoint))
    bot = Bot(token=settings.telegram_token)
    try:
        await bot.set_my_short_description(short_description=SHORT_DESCRIPTION)
        await bot.set_my_description(description=DESCRIPTION)
        await bot.set_my_commands(commands)
        await bot.set_my_commands(
            admin_commands,
            scope=BotCommandScopeChat(chat_id=settings.admin_user_id),
        )
    finally:
        await bot.session.close()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
