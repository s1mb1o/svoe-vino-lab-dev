from __future__ import annotations

import asyncio

from aiogram import Bot
from aiogram.types import BotCommandScopeChat

from .config import Settings
from .profile import ADMIN_COMMANDS, COMMANDS, DESCRIPTION, SHORT_DESCRIPTION


async def run() -> None:
    settings = Settings.from_env()
    bot = Bot(token=settings.telegram_token)
    try:
        await bot.set_my_short_description(short_description=SHORT_DESCRIPTION)
        await bot.set_my_description(description=DESCRIPTION)
        await bot.set_my_commands(COMMANDS)
        await bot.set_my_commands(
            ADMIN_COMMANDS,
            scope=BotCommandScopeChat(chat_id=settings.admin_user_id),
        )
    finally:
        await bot.session.close()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
