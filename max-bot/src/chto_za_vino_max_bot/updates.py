"""The MAX updates that the bot handles, in a normalized form.

Reference: https://dev.max.ru/docs-api/objects/Update. The parser accepts only the fields that
the bot uses. An unknown update type gives `None`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DIALOG = "dialog"
MAX_IMAGES_PER_MESSAGE = 12
# A MAX client sends a `file` attachment when the user selects «Файл». The file name is the only
# type information in the update. The worker checks the downloaded bytes.
IMAGE_FILE_SUFFIXES = (".jpg", ".jpeg", ".png", ".webp")
# A message that contains only a forwarded message can have no body and no own `mid`
# (https://dev.max.ru/docs-api/objects/Message). The bot gives it a stable synthetic ID.
FORWARD_ID_PREFIX = "forward:"


def is_synthetic_message_id(message_id: str) -> bool:
    """A synthetic ID cannot be a reply target and cannot be read with GET /messages."""
    return message_id.startswith(FORWARD_ID_PREFIX)


def _forward_only_id(value: dict[str, Any]) -> str | None:
    recipient = value.get("recipient")
    link = value.get("link")
    if not isinstance(recipient, dict) or not isinstance(link, dict):
        return None
    original = link.get("message")
    if link.get("type") != "forward" or not isinstance(original, dict):
        return None
    chat_id = _int(recipient.get("chat_id"))
    timestamp = _int(value.get("timestamp"))
    original_mid = _text(original.get("mid"))
    if chat_id is None or timestamp is None or not original_mid:
        return None
    return f"{FORWARD_ID_PREFIX}{chat_id}:{timestamp}:{original_mid}"


@dataclass(frozen=True, slots=True)
class MaxUser:
    user_id: int
    first_name: str | None
    last_name: str | None
    username: str | None
    is_bot: bool = False


@dataclass(frozen=True, slots=True)
class ImageRef:
    """One `image` attachment of a message, or one `file` attachment with an image file name."""

    photo_id: int | None
    url: str
    token: str | None


@dataclass(frozen=True, slots=True)
class IncomingMessage:
    """A `message_created` update, or the message of a callback."""

    message_id: str
    chat_id: int
    chat_type: str
    sender: MaxUser | None
    text: str | None
    images: tuple[ImageRef, ...]
    has_other_attachments: bool = False
    timestamp: int = 0
    # The number of image and video attachments. Two or more make an album.
    media_count: int = 0
    # "body" for the message attachments, "forward" for the attachments of a forwarded message.
    photo_source: str = "body"

    @property
    def is_dialog(self) -> bool:
        return self.chat_type == DIALOG

    @property
    def is_album(self) -> bool:
        return self.media_count >= 2


@dataclass(frozen=True, slots=True)
class CallbackEvent:
    """A `message_callback` update."""

    callback_id: str
    payload: str
    user: MaxUser
    message: IncomingMessage | None
    timestamp: int = 0

    @property
    def chat_id(self) -> int | None:
        return self.message.chat_id if self.message is not None else None


@dataclass(frozen=True, slots=True)
class BotStarted:
    """A `bot_started` update. The user pressed «Начать» or opened a deep link."""

    chat_id: int
    user: MaxUser
    payload: str | None
    timestamp: int = 0


Update = IncomingMessage | CallbackEvent | BotStarted


@dataclass(frozen=True, slots=True)
class Command:
    name: str
    args: str | None


def _int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _text(value: object) -> str | None:
    return value if isinstance(value, str) else None


def parse_user(value: object) -> MaxUser | None:
    if not isinstance(value, dict):
        return None
    user_id = _int(value.get("user_id"))
    if user_id is None:
        return None
    first_name = _text(value.get("first_name"))
    last_name = _text(value.get("last_name"))
    if first_name is None and last_name is None:
        first_name = _text(value.get("name"))
    return MaxUser(
        user_id=user_id,
        first_name=first_name or None,
        last_name=last_name or None,
        username=_text(value.get("username")) or None,
        is_bot=value.get("is_bot") is True,
    )


def _attachments(body: object) -> list[dict[str, Any]]:
    if not isinstance(body, dict):
        return []
    raw = body.get("attachments")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _is_image_file(item: dict[str, Any]) -> bool:
    filename = _text(item.get("filename")) or ""
    return item.get("type") == "file" and filename.lower().endswith(IMAGE_FILE_SUFFIXES)


def _is_image(item: dict[str, Any]) -> bool:
    return item.get("type") == "image" or _is_image_file(item)


def _images(attachments: list[dict[str, Any]]) -> tuple[ImageRef, ...]:
    images: list[ImageRef] = []
    for item in attachments:
        if not _is_image(item):
            continue
        payload = item.get("payload")
        if not isinstance(payload, dict):
            continue
        url = _text(payload.get("url"))
        if not url:
            continue
        images.append(
            ImageRef(
                photo_id=_int(payload.get("photo_id")),
                url=url,
                token=_text(payload.get("token")) or None,
            )
        )
    return tuple(images)


def parse_message(value: object) -> IncomingMessage | None:
    if not isinstance(value, dict):
        return None
    recipient = value.get("recipient")
    body = value.get("body")
    if not isinstance(recipient, dict):
        return None
    if body is None:
        message_id = _forward_only_id(value)
        body = {}
    elif isinstance(body, dict):
        message_id = _text(body.get("mid"))
    else:
        return None
    chat_id = _int(recipient.get("chat_id"))
    chat_type = _text(recipient.get("chat_type")) or ""
    if chat_id is None or not message_id:
        return None
    attachments = _attachments(body)
    photo_source = "body"
    link = value.get("link")
    # A forwarded photo is a photo message, the same as in Telegram.
    if (
        not attachments
        and isinstance(link, dict)
        and link.get("type") == "forward"
        and isinstance(link.get("message"), dict)
    ):
        attachments = _attachments(link["message"])
        photo_source = "forward"
    images = _images(attachments)
    other = any(
        not _is_image(item) and item.get("type") != "inline_keyboard" for item in attachments
    )
    media_count = sum(_is_image(item) or item.get("type") == "video" for item in attachments)
    return IncomingMessage(
        message_id=message_id,
        chat_id=chat_id,
        chat_type=chat_type,
        sender=parse_user(value.get("sender")),
        text=_text(body.get("text")),
        images=images,
        has_other_attachments=other,
        timestamp=_int(value.get("timestamp")) or 0,
        media_count=media_count,
        photo_source=photo_source,
    )


def parse_update(value: object) -> Update | None:
    """Return the normalized update, or None for an update that the bot ignores."""
    if not isinstance(value, dict):
        return None
    update_type = value.get("update_type")
    timestamp = _int(value.get("timestamp")) or 0
    if update_type == "message_created":
        return parse_message(value.get("message"))
    if update_type == "message_callback":
        callback = value.get("callback")
        if not isinstance(callback, dict):
            return None
        callback_id = _text(callback.get("callback_id"))
        user = parse_user(callback.get("user"))
        if not callback_id or user is None:
            return None
        return CallbackEvent(
            callback_id=callback_id,
            payload=_text(callback.get("payload")) or "",
            user=user,
            message=parse_message(value.get("message")),
            timestamp=timestamp,
        )
    if update_type == "bot_started":
        chat_id = _int(value.get("chat_id"))
        user = parse_user(value.get("user"))
        if chat_id is None or user is None:
            return None
        return BotStarted(
            chat_id=chat_id,
            user=user,
            payload=_text(value.get("payload")) or None,
            timestamp=timestamp,
        )
    return None


def update_key(value: object) -> str | None:
    """Return the key of one update for the duplicate filter, or None for an unusable update.

    A repeated webhook delivery has the same key. The key contains the identity of the event,
    so two users who start the bot at the same millisecond do not collide.
    """
    if not isinstance(value, dict):
        return None
    update_type = value.get("update_type")
    if update_type == "message_created":
        message = value.get("message")
        if not isinstance(message, dict):
            return None
        body = message.get("body")
        mid = body.get("mid") if isinstance(body, dict) else None
        if body is None:
            mid = _forward_only_id(message)
        return f"message_created:{mid}" if isinstance(mid, str) and mid else None
    if update_type == "message_callback":
        callback = value.get("callback")
        callback_id = callback.get("callback_id") if isinstance(callback, dict) else None
        if isinstance(callback_id, str) and callback_id:
            return f"message_callback:{callback_id}"
        return None
    if update_type == "bot_started":
        user = value.get("user")
        user_id = user.get("user_id") if isinstance(user, dict) else None
        return (
            f"bot_started:{value.get('chat_id')}:{user_id}:"
            f"{value.get('timestamp')}:{value.get('payload') or ''}"
        )
    return None


def update_user_id(value: object) -> int | None:
    """Return the user ID of an update, for the user data deletion."""
    if not isinstance(value, dict):
        return None
    update_type = value.get("update_type")
    if update_type == "message_created":
        message = value.get("message")
        user = message.get("sender") if isinstance(message, dict) else None
    elif update_type == "message_callback":
        callback = value.get("callback")
        user = callback.get("user") if isinstance(callback, dict) else None
    else:
        user = value.get("user")
    return _int(user.get("user_id")) if isinstance(user, dict) else None


def parse_command(text: str | None) -> Command | None:
    """Parse `/name args` and `/name@bot args`. Return None for other text."""
    if not text or not text.startswith("/"):
        return None
    # The same split as aiogram: the arguments start after any whitespace.
    head, *rest = text.strip().split(maxsplit=1)
    name = head[1:].split("@", 1)[0].lower()
    if not name:
        return None
    args = rest[0].strip() if rest else None
    return Command(name=name, args=args or None)
