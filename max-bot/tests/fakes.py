"""Test doubles of the MAX API and helpers that build normalized updates."""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any

from chto_za_vino_max_bot.max_api import MaxApiError
from chto_za_vino_max_bot.updates import (
    CallbackEvent,
    ImageRef,
    IncomingMessage,
    MaxUser,
)

ADMIN_ID = 777
USER_ID = 200
DIALOG_CHAT_ID = 5000


def user(
    user_id: int = USER_ID,
    *,
    username: str | None = "tester",
    first_name: str | None = "Test",
    last_name: str | None = None,
) -> MaxUser:
    return MaxUser(
        user_id=user_id,
        first_name=first_name,
        last_name=last_name,
        username=username,
    )


def image(index: int = 1, *, photo_id: int | None = None) -> ImageRef:
    return ImageRef(
        photo_id=photo_id if photo_id is not None else 9000 + index,
        url=f"https://i.oneme.example/photo-{index}.jpg",
        token=f"token-{index}",
    )


def message(
    *,
    message_id: str = "mid.source",
    chat_id: int = DIALOG_CHAT_ID,
    chat_type: str = "dialog",
    sender: MaxUser | None = None,
    text: str | None = None,
    images: tuple[ImageRef, ...] = (),
    media_count: int | None = None,
    photo_source: str = "body",
) -> IncomingMessage:
    return IncomingMessage(
        message_id=message_id,
        chat_id=chat_id,
        chat_type=chat_type,
        sender=sender if sender is not None else user(),
        text=text,
        images=images,
        media_count=len(images) if media_count is None else media_count,
        photo_source=photo_source,
    )


def callback(
    payload: str,
    *,
    from_user: MaxUser | None = None,
    source: IncomingMessage | None = None,
    callback_id: str = "callback-1",
    with_message: bool = True,
) -> CallbackEvent:
    if source is None and with_message:
        source = message(
            message_id="mid.bot-result",
            sender=MaxUser(user_id=1, first_name="Bot", last_name=None, username="bot", is_bot=True),
            text="Похоже, это: …",
            images=(image(50),),
        )
    return CallbackEvent(
        callback_id=callback_id,
        payload=payload,
        user=from_user if from_user is not None else user(),
        message=source if with_message else None,
    )


@dataclass
class Call:
    method: str
    args: dict[str, Any] = field(default_factory=dict)


class FakeMaxApi:
    """Records each call. A test can make a method fail with `fail_on`."""

    def __init__(self) -> None:
        self.calls: list[Call] = []
        self.fail_on: dict[str, Exception] = {}
        self.downloads: dict[str, bytes] = {}
        self.messages_by_id: dict[str, dict[str, Any]] = {}
        self._ids = itertools.count(1)
        self.upload_count = 0

    def _record(self, method: str, **args: Any) -> None:
        self.calls.append(Call(method, args))
        failure = self.fail_on.get(method)
        if failure is not None:
            raise failure

    def calls_of(self, method: str) -> list[dict[str, Any]]:
        return [call.args for call in self.calls if call.method == method]

    async def send_message(
        self,
        chat_id: int,
        *,
        text: str | None,
        attachments: list[dict[str, object]] | None = None,
        reply_to: str | None = None,
        text_format: str | None = "html",
        disable_link_preview: bool = False,
    ) -> dict[str, Any]:
        self._record(
            "send_message",
            chat_id=chat_id,
            text=text,
            attachments=attachments,
            reply_to=reply_to,
            text_format=text_format,
            disable_link_preview=disable_link_preview,
        )
        return {"body": {"mid": f"mid.bot-{next(self._ids)}", "text": text}}

    async def edit_message(
        self,
        chat_id: int,
        message_id: str,
        *,
        text: str | None,
        attachments: list[dict[str, object]] | None,
        text_format: str | None = "html",
    ) -> None:
        self._record(
            "edit_message",
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            attachments=attachments,
            text_format=text_format,
        )

    async def delete_message(self, chat_id: int, message_id: str) -> None:
        self._record("delete_message", chat_id=chat_id, message_id=message_id)

    async def answer_callback(
        self,
        chat_id: int | None,
        callback_id: str,
        *,
        notification: str | None = None,
        message: dict[str, object] | None = None,
        disable_link_preview: bool = False,
    ) -> None:
        self._record(
            "answer_callback",
            chat_id=chat_id,
            callback_id=callback_id,
            notification=notification,
            message=message,
            disable_link_preview=disable_link_preview,
        )

    async def upload_image(
        self,
        body: bytes,
        *,
        filename: str,
        content_type: str,
    ) -> tuple[dict[str, object], str | None]:
        self._record("upload_image", filename=filename, content_type=content_type, size=len(body))
        self.upload_count += 1
        token = f"uploaded-{self.upload_count}"
        return {"photos": {str(self.upload_count): {"token": token}}}, token

    async def download(self, url: str, *, max_bytes: int) -> bytes:
        self._record("download", url=url, max_bytes=max_bytes)
        return self.downloads[url]

    async def get_message(self, message_id: str) -> dict[str, Any]:
        self._record("get_message", message_id=message_id)
        if message_id not in self.messages_by_id:
            raise MaxApiError(404, "not.found", "message not found")
        return self.messages_by_id[message_id]

    async def set_commands(self, commands: list[dict[str, str]]) -> dict[str, Any]:
        self._record("set_commands", commands=commands)
        return {"commands": commands}

    async def get_me(self) -> dict[str, Any]:
        self._record("get_me")
        return {"user_id": 1, "username": "se14697933_bot", "is_bot": True}


def keyboard_buttons(attachments: list[dict[str, object]] | None) -> list[list[dict[str, Any]]]:
    """Return the button rows of the inline keyboard in an attachment list."""
    for item in attachments or []:
        if item.get("type") == "inline_keyboard":
            payload = item["payload"]
            assert isinstance(payload, dict)
            return payload["buttons"]  # type: ignore[return-value]
    return []


def button_texts(attachments: list[dict[str, object]] | None) -> list[list[str]]:
    return [[button["text"] for button in row] for row in keyboard_buttons(attachments)]
