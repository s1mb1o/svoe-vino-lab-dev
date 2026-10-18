# Context im-core

This project is the shared core of the bots in `../telegram-bot` and `../max-bot`.
Read `README.md` and `../docs/plans/01_im-core-package.md` before a change.

## Rules

1. Keep this package free of messenger code. Do not import `aiogram`, a MAX API client, or a
   module of a bot.
2. Pass a platform value as a parameter. Do not write `Telegram` or `MAX` in a code path.
3. Keep stored values stable: the artifact keys `telegram_result` and `max_result` and the matcher
   upload names `telegram-photo` and `max-photo` come from the bots.
4. Keep user-visible text in Russian and technical documentation in English (STE style).
5. After a change, run the checks of this package and of both bots:
   `uv run pytest -q` in `im-core/`, `telegram-bot/`, and `max-bot/`.
6. Update `ChangeLog.md` for each meaningful change.
