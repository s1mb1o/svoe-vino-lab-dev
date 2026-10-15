from __future__ import annotations

import asyncio

import httpx

from .config import Settings
from .max_api import MaxApi, create_ssl_context
from .profile import COMMANDS, SHORT_DESCRIPTION


async def run() -> None:
    """Set the command menu and compare the bot card description.

    MAX has no API for the bot description. The owner edits the card on business.max.ru, and
    the change passes the platform moderation.
    """
    settings = Settings.from_env()
    async with httpx.AsyncClient(verify=create_ssl_context(settings.max_api_ca_file)) as client:
        api = MaxApi(settings.max_token, client, base_url=settings.max_api_base_url)
        await api.set_commands(COMMANDS)
        me = await api.get_me()
    print(f"Commands set: {', '.join('/' + item['name'] for item in COMMANDS)}")
    description = me.get("description")
    if description != SHORT_DESCRIPTION:
        print("The bot card description differs. Set it on business.max.ru:")
        print(SHORT_DESCRIPTION)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
