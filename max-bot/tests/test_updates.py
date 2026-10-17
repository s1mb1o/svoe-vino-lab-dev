"""The update shapes follow the fixtures of the official MAX Go client (`stabs/update.*.json`)."""

import pytest

from chto_za_vino_max_bot.updates import (
    BotStarted,
    CallbackEvent,
    ImageRef,
    IncomingMessage,
    parse_command,
    parse_update,
    update_key,
    update_user_id,
)

SENDER = {
    "user_id": 123456789,
    "first_name": "John",
    "last_name": "Doe",
    "is_bot": False,
    "last_activity_time": 1775053249000,
    "name": "John Doe",
}


def photo(photo_id: int) -> dict[str, object]:
    return {
        "type": "image",
        "payload": {
            "photo_id": photo_id,
            "token": f"token-{photo_id}",
            "url": f"https://i.oneme.ru/i?r={photo_id}",
        },
    }


def created(attachments=None, *, text=None, chat_type="dialog", link=None) -> dict[str, object]:
    body: dict[str, object] = {"mid": "mid.ffffbdb48e6c3775", "seq": 116327994376978687}
    if text is not None:
        body["text"] = text
    if attachments is not None:
        body["attachments"] = attachments
    message: dict[str, object] = {
        "recipient": {"chat_id": 182182182, "chat_type": chat_type, "user_id": 229229229},
        "timestamp": 1775053255737,
        "body": body,
        "sender": SENDER,
    }
    if link is not None:
        message["link"] = link
    return {"update_type": "message_created", "timestamp": 1775025604499, "message": message}


def test_message_with_photos_is_normalized():
    update = parse_update(created([photo(1), photo(2)], text="подпись"))

    assert isinstance(update, IncomingMessage)
    assert update.message_id == "mid.ffffbdb48e6c3775"
    assert update.chat_id == 182182182
    assert update.is_dialog
    assert update.sender is not None
    assert update.sender.user_id == 123456789
    assert update.sender.first_name == "John"
    assert update.sender.username is None
    assert update.text == "подпись"
    assert [image.photo_id for image in update.images] == [1, 2]
    assert update.images[0].token == "token-1"
    assert update.images[0].url == "https://i.oneme.ru/i?r=1"
    assert update.media_count == 2
    assert update.is_album
    assert update.photo_source == "body"


def test_single_photo_is_not_an_album():
    update = parse_update(created([photo(1)]))

    assert isinstance(update, IncomingMessage)
    assert not update.is_album


def test_photo_with_video_is_an_album():
    video = {"type": "video", "payload": {"token": "video", "url": "https://v.example/v"}}
    update = parse_update(created([photo(1), video]))

    assert isinstance(update, IncomingMessage)
    assert len(update.images) == 1
    assert update.media_count == 2
    assert update.is_album
    assert update.has_other_attachments


def test_forwarded_photo_uses_the_forwarded_attachments():
    link = {
        "type": "forward",
        "message": {"mid": "mid.original", "seq": 1, "attachments": [photo(5)]},
        "sender": SENDER,
        "chat_id": -695695695695,
    }
    update = parse_update(created(link=link))

    assert isinstance(update, IncomingMessage)
    assert [image.photo_id for image in update.images] == [5]
    assert update.photo_source == "forward"
    assert update.message_id == "mid.ffffbdb48e6c3775"


def test_reply_to_a_photo_is_not_a_photo_message():
    link = {"type": "reply", "message": {"mid": "mid.original", "seq": 1, "attachments": [photo(5)]}}
    update = parse_update(created(text="что это?", link=link))

    assert isinstance(update, IncomingMessage)
    assert update.images == ()


def file(filename: str | None) -> dict[str, object]:
    item: dict[str, object] = {
        "type": "file",
        "payload": {"token": "f", "url": "https://f.example/x"},
        "size": 1000,
    }
    if filename is not None:
        item["filename"] = filename
    return item


@pytest.mark.parametrize(
    "filename",
    ["bottle.jpg", "Bottle.JPEG", "label.png", "label.WebP", "IMG_0001.HEIC", "photo.heif"],
)
def test_image_file_attachment_is_a_photo(filename):
    update = parse_update(created([file(filename)]))

    assert isinstance(update, IncomingMessage)
    assert update.images == (ImageRef(photo_id=None, url="https://f.example/x", token="f"),)
    assert not update.has_other_attachments
    assert not update.is_album


def test_two_image_files_are_an_album():
    update = parse_update(created([file("a.jpg"), file("b.png")]))

    assert isinstance(update, IncomingMessage)
    assert len(update.images) == 2
    assert update.is_album


@pytest.mark.parametrize("filename", ["label.pdf", "bottle.gif", "jpg", None])
def test_other_file_attachment_is_not_a_photo(filename):
    update = parse_update(created([file(filename)]))

    assert isinstance(update, IncomingMessage)
    assert update.images == ()
    assert update.has_other_attachments


def test_group_chat_message_is_not_a_dialog():
    update = parse_update(created(text="/stats", chat_type="chat"))

    assert isinstance(update, IncomingMessage)
    assert not update.is_dialog


def test_callback_is_normalized_with_its_message():
    update = parse_update(
        {
            "update_type": "message_callback",
            "timestamp": 1775025604499,
            "user_locale": "ru",
            "callback": {
                "timestamp": 1775026702210,
                "callback_id": "f9LHodD0cOJf4",
                "user": SENDER,
                "payload": "feedback:yes:request-1",
            },
            "message": {
                "recipient": {"chat_id": 182182182, "chat_type": "dialog", "user_id": 123456789},
                "timestamp": 1775026671403,
                "body": {"mid": "mid.bot", "seq": 1, "text": "Похоже, это:", "attachments": [
                    photo(9),
                    {"type": "inline_keyboard", "payload": {"buttons": [[]]}},
                ]},
                "sender": {"user_id": 229229229, "first_name": "UniBot", "is_bot": True},
            },
        }
    )

    assert isinstance(update, CallbackEvent)
    assert update.callback_id == "f9LHodD0cOJf4"
    assert update.payload == "feedback:yes:request-1"
    assert update.user.user_id == 123456789
    assert update.chat_id == 182182182
    assert update.message is not None
    assert update.message.message_id == "mid.bot"
    assert update.message.sender is not None and update.message.sender.is_bot
    assert [image.token for image in update.message.images] == ["token-9"]
    assert not update.message.has_other_attachments


def test_callback_without_message_has_no_chat():
    update = parse_update(
        {
            "update_type": "message_callback",
            "timestamp": 1,
            "callback": {"timestamp": 1, "callback_id": "c", "user": SENDER, "payload": "age:adult"},
            "message": None,
        }
    )

    assert isinstance(update, CallbackEvent)
    assert update.message is None
    assert update.chat_id is None


def test_bot_started_keeps_the_deep_link_payload():
    update = parse_update(
        {
            "update_type": "bot_started",
            "timestamp": 1775025604499,
            "chat_id": 182182182,
            "user": {**SENDER, "username": "john"},
            "user_locale": "ru",
            "payload": "privacy",
        }
    )

    assert isinstance(update, BotStarted)
    assert update.chat_id == 182182182
    assert update.user.username == "john"
    assert update.payload == "privacy"


def test_user_without_first_name_uses_the_display_name():
    update = parse_update(
        {
            "update_type": "bot_started",
            "timestamp": 1,
            "chat_id": 1,
            "user": {"user_id": 5, "name": "Display Name", "is_bot": False},
        }
    )

    assert isinstance(update, BotStarted)
    assert update.user.first_name == "Display Name"
    assert update.payload is None


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        {"update_type": "message_removed", "timestamp": 1},
        {"update_type": "message_created", "timestamp": 1, "message": {"body": {"mid": "m"}}},
        {"update_type": "message_callback", "timestamp": 1, "callback": {"payload": "x"}},
        {"update_type": "bot_started", "timestamp": 1, "user": SENDER},
    ],
)
def test_unusable_updates_are_ignored(value):
    assert parse_update(value) is None


def test_update_keys_identify_the_event():
    assert update_key(created([photo(1)])) == "message_created:mid.ffffbdb48e6c3775"
    callback = {
        "update_type": "message_callback",
        "timestamp": 1,
        "callback": {"callback_id": "cb-1", "user": SENDER},
    }
    assert update_key(callback) == "message_callback:cb-1"
    first = {"update_type": "bot_started", "timestamp": 5, "chat_id": 1, "user": {"user_id": 10}}
    second = {**first, "chat_id": 2, "user": {"user_id": 20}}
    # Two users who start the bot in the same millisecond have different keys.
    assert update_key(first) != update_key(second)
    assert update_key({"update_type": "message_created", "timestamp": 1}) is None
    assert update_key({"update_type": "dialog_muted", "timestamp": 1}) is None


def test_update_user_id_reads_each_update_type():
    assert update_user_id(created([photo(1)])) == 123456789
    callback = {"update_type": "message_callback", "callback": {"user": {"user_id": 7}}}
    assert update_user_id(callback) == 7
    assert update_user_id({"update_type": "bot_started", "user": {"user_id": 9}}) == 9
    assert update_user_id({"update_type": "bot_started"}) is None


@pytest.mark.parametrize(
    ("text", "name", "args"),
    [
        ("/start", "start", None),
        ("/start privacy", "start", "privacy"),
        ("/users 2", "users", "2"),
        ("/Users@se14697933_bot 3", "users", "3"),
        ("/reset_limit @name", "reset_limit", "@name"),
        ("  /help  ", "help", None),
    ],
)
def test_commands_are_parsed(text, name, args):
    command = parse_command(text.strip() if text.startswith(" ") else text)

    assert command is not None
    assert command.name == name
    assert command.args == args


@pytest.mark.parametrize("text", [None, "", "hello", "/", "/@bot"])
def test_other_text_is_not_a_command(text):
    assert parse_command(text) is None


def test_forward_only_message_without_body_gets_a_stable_synthetic_id():
    value = {
        "update_type": "message_created",
        "timestamp": 1775025604499,
        "message": {
            "recipient": {"chat_id": 182182182, "chat_type": "dialog"},
            "timestamp": 1775053255737,
            "body": None,
            "sender": SENDER,
            "link": {
                "type": "forward",
                "message": {"mid": "mid.original", "seq": 1, "attachments": [photo(5)]},
                "sender": SENDER,
                "chat_id": -695695695695,
            },
        },
    }

    update = parse_update(value)

    assert isinstance(update, IncomingMessage)
    assert update.message_id == "forward:182182182:1775053255737:mid.original"
    assert [image.photo_id for image in update.images] == [5]
    assert update.photo_source == "forward"
    assert update_key(value) == "message_created:forward:182182182:1775053255737:mid.original"
    # A repeated delivery has the same key. Another forward of the same photo is another key.
    later = {**value, "message": {**value["message"], "timestamp": 1775053299999}}
    assert update_key(later) != update_key(value)


def test_message_without_body_and_without_forward_is_ignored():
    value = created(text="x")
    value["message"]["body"] = None

    assert parse_update(value) is None
    assert update_key(value) is None
