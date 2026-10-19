"""Link of a Telegram account to «Винный дневник» (issue #51).

Telegram is a linked messenger, never a login method (149-FZ art. 8 p. 10). The site gives a
deep link `https://t.me/<bot>?start=link_<code>`. The bot shows the diary name and links only
after «Привязать». The account service keeps the Telegram user ID; the bot keeps no link state.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Coroutine
from html import escape
from typing import Any

import httpx
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

LOG = logging.getLogger("chto_za_vino_bot.account")

DIARY_URL = "https://chtozavino.ru/account"
LINK_PREFIX = "link_"
# The service makes 22-character codes. A callback data value holds at most 64 bytes.
LINK_CODE = re.compile(r"[A-Za-z0-9_-]{16,59}")
CONFIRM_PREFIX = "lk:y:"
CANCEL_DATA = "lk:n"
ACCOUNT_TIMEOUT_SECONDS = 2.0
MAX_RESPONSE_BYTES = 16 * 1024

LINK_CONFIRM_TEXT = (
    "Привязать этот Telegram к дневнику «<b>{username}</b>»?\n\n"
    "Бот сможет сохранять ваши находки в дневник. Войти в дневник через Telegram нельзя: "
    "на сайте вход только по почте или через Яндекс ID."
)
LINK_DONE_TEXT = (
    "Готово: Telegram привязан к дневнику «<b>{username}</b>».\n\n"
    "Отвязать можно командой /unlink или на странице дневника."
)
LINK_CANCELLED_TEXT = "Привязка отменена."
LINK_INVALID_TEXT = (
    "Ссылка устарела или уже использована. Создайте новую на странице дневника: " + DIARY_URL
)
LINK_IN_USE_TEXT = (
    "Этот Telegram уже привязан к другому дневнику. Сначала отвяжите его командой /unlink."
)
LINK_UNAVAILABLE_TEXT = (
    "Дневник временно недоступен. Попробуйте позже. Распознавание вина по фото работает."
)
LINK_OFF_TEXT = "Привязка к дневнику сейчас выключена."
LINK_PRIVATE_TEXT = "Привязать дневник можно только в личном чате с ботом."
UNLINK_DONE_TEXT = "Telegram отвязан от дневника."
UNLINK_NONE_TEXT = "Этот Telegram не привязан к дневнику."


class AccountUnavailable(Exception):
    """The account service is down, slow, or refused the bot token."""


class AccountRejected(Exception):
    """The account service refused the request. `code` is its stable error code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class AccountClient:
    """Calls the bot routes of the account service with the `telegram-bot` consumer token."""

    def __init__(
        self,
        endpoint: str,
        token: str,
        client: httpx.AsyncClient,
        *,
        timeout_seconds: float = ACCOUNT_TIMEOUT_SECONDS,
    ) -> None:
        self._base = endpoint.rstrip("/")
        self._headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        self._client = client
        self._timeout = timeout_seconds

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        try:
            response = await self._client.post(
                f"{self._base}{path}",
                json=body,
                headers=self._headers,
                timeout=self._timeout,
                follow_redirects=False,
            )
        except httpx.HTTPError as exc:
            raise AccountUnavailable(type(exc).__name__) from None
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise AccountUnavailable("response too large")
        try:
            data = response.json()
        except ValueError:
            raise AccountUnavailable(f"HTTP {response.status_code}") from None
        if not isinstance(data, dict):
            raise AccountUnavailable(f"HTTP {response.status_code}")
        code = data.get("error") if isinstance(data.get("error"), str) else ""
        # A refused consumer token or network is a configuration fault, not a user error.
        if response.status_code >= 500 or code in {"unauthorized", "forbidden"}:
            raise AccountUnavailable(f"HTTP {response.status_code} {code}".strip())
        if response.status_code == 422:
            raise AccountRejected("invalid_link_code")
        if response.status_code >= 400:
            raise AccountRejected(code or "request_rejected")
        return data

    async def claim(self, code: str, telegram_user_id: int) -> str:
        data = await self._post(
            "/v1/bot/telegram/links/claim", {"code": code, "telegram_user_id": telegram_user_id}
        )
        return _username(data)

    async def confirm(self, code: str, telegram_user_id: int) -> str:
        data = await self._post(
            "/v1/bot/telegram/links/confirm",
            {"code": code, "telegram_user_id": telegram_user_id},
        )
        return _username(data)

    async def unlink(self, telegram_user_id: int) -> bool:
        data = await self._post("/v1/bot/telegram/unlink", {"telegram_user_id": telegram_user_id})
        return data.get("status") == "unlinked"


def _username(data: dict[str, Any]) -> str:
    username = data.get("username")
    if not isinstance(username, str) or not username:
        raise AccountUnavailable("answer without a username")
    return username


def link_code(args: str | None) -> str | None:
    """Returns the code of a `/start link_<code>` payload, or None for another payload."""
    if not args or not args.startswith(LINK_PREFIX):
        return None
    return args.removeprefix(LINK_PREFIX)


def confirm_keyboard(code: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Привязать", callback_data=f"{CONFIRM_PREFIX}{code}"),
                InlineKeyboardButton(text="Отмена", callback_data=CANCEL_DATA),
            ]
        ]
    )


def _rejection_text(code: str) -> str:
    if code == "identity_in_use":
        return LINK_IN_USE_TEXT
    if code == "provider_disabled":
        return LINK_OFF_TEXT
    return LINK_INVALID_TEXT


def _private(message: Message) -> bool:
    return getattr(message.chat, "type", None) == "private"


async def handle_link_start(message: Message, code: str, account: AccountClient | None) -> None:
    """Answers `/start link_<code>`: shows the diary name and asks for confirmation."""
    if message.from_user is None:
        return
    if not _private(message):
        await message.answer(LINK_PRIVATE_TEXT)
        return
    if account is None:
        await message.answer(LINK_OFF_TEXT)
        return
    if not LINK_CODE.fullmatch(code):
        await message.answer(LINK_INVALID_TEXT)
        return
    try:
        username = await account.claim(code, message.from_user.id)
    except AccountRejected as exc:
        await message.answer(_rejection_text(exc.code))
        return
    except AccountUnavailable as exc:
        LOG.warning("Diary link claim failed: %s", exc)
        await message.answer(LINK_UNAVAILABLE_TEXT)
        return
    await message.answer(
        LINK_CONFIRM_TEXT.format(username=escape(username)),
        reply_markup=confirm_keyboard(code),
    )


async def _replace_text(callback: CallbackQuery, text: str) -> None:
    if not isinstance(callback.message, Message):
        return
    try:
        await callback.message.edit_text(text, reply_markup=None)
    except TelegramAPIError:
        LOG.warning("Diary link message edit failed")
        await callback.message.answer(text)


async def handle_link_callback(callback: CallbackQuery, account: AccountClient | None) -> None:
    """Handles «Привязать» and «Отмена» under the confirmation message."""
    data = callback.data or ""
    if data == CANCEL_DATA:
        await callback.answer()
        await _replace_text(callback, LINK_CANCELLED_TEXT)
        return
    code = data.removeprefix(CONFIRM_PREFIX)
    if not data.startswith(CONFIRM_PREFIX) or not LINK_CODE.fullmatch(code):
        await callback.answer("Некорректное обращение.")
        return
    if account is None:
        await callback.answer()
        await _replace_text(callback, LINK_OFF_TEXT)
        return
    try:
        username = await account.confirm(code, callback.from_user.id)
    except AccountRejected as exc:
        await callback.answer()
        await _replace_text(callback, _rejection_text(exc.code))
        return
    except AccountUnavailable as exc:
        LOG.warning("Diary link confirmation failed: %s", exc)
        # Keep the buttons: the person can try again while the code is valid.
        await callback.answer(LINK_UNAVAILABLE_TEXT, show_alert=True)
        return
    LOG.info("Diary link confirmed")
    await callback.answer("Telegram привязан.")
    await _replace_text(callback, LINK_DONE_TEXT.format(username=escape(username)))


async def handle_unlink_command(message: Message, account: AccountClient | None) -> None:
    """Answers `/unlink`: removes the link of this Telegram account."""
    if message.from_user is None:
        return
    if not _private(message):
        await message.answer(LINK_PRIVATE_TEXT)
        return
    if account is None:
        await message.answer(LINK_OFF_TEXT)
        return
    try:
        removed = await account.unlink(message.from_user.id)
    except (AccountRejected, AccountUnavailable) as exc:
        LOG.warning("Diary unlink failed: %s", exc)
        await message.answer(LINK_UNAVAILABLE_TEXT)
        return
    if removed:
        LOG.info("Diary link removed")
    await message.answer(UNLINK_DONE_TEXT if removed else UNLINK_NONE_TEXT)


class BackgroundTasks:
    """Runs account calls outside the update dispatcher, which handles one update at a time."""

    def __init__(self) -> None:
        self._tasks: set[asyncio.Task[None]] = set()

    def spawn(self, work: Coroutine[Any, Any, None]) -> None:
        task = asyncio.create_task(self._guarded(work))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    @staticmethod
    async def _guarded(work: Coroutine[Any, Any, None]) -> None:
        try:
            await work
        except Exception:
            LOG.exception("Diary link handler failed")
