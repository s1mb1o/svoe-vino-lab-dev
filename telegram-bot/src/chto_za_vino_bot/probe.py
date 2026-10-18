"""Probe command of the Telegram bot.

The matcher stores the upload name, so the probe sends the same name as the bot.
"""

from chto_za_vino_core.probe import main as core_main

UPLOAD_NAME = "telegram-photo"


def main() -> None:
    core_main(upload_name=UPLOAD_NAME)
