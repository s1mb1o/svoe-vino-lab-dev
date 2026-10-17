"""One photo from a raw MAX update to the result and the feedback, with fake services."""

from types import SimpleNamespace

import httpx
from fakes import FakeMaxApi, button_texts, keyboard_buttons

from chto_za_vino_max_bot.app import BotHandlers, PhotoProcessor, Services
from chto_za_vino_max_bot.delivery import UpdateDispatcher
from chto_za_vino_max_bot.host_demo import BASE_URL, _demo_image, _respond
from chto_za_vino_max_bot.matcher import Matcher
from chto_za_vino_max_bot.moderation import Moderator
from chto_za_vino_max_bot.quality import QualityInspector, QualityThresholds
from chto_za_vino_max_bot.result_card import CatalogImageLoader
from chto_za_vino_max_bot.storage import ArtifactStore, ImageStore, Repository
from chto_za_vino_max_bot.updates import parse_update
from chto_za_vino_max_bot.work_queue import WorkQueue

PHOTO_URL = "https://i.oneme.example/i?r=photo"
USER = {"user_id": 200, "first_name": "Test", "username": "tester", "is_bot": False}


def created(attachments: list[dict[str, object]], mid: str = "mid.photo") -> dict[str, object]:
    return {
        "update_type": "message_created",
        "timestamp": 1775053255737,
        "message": {
            "recipient": {"chat_id": 5000, "chat_type": "dialog", "user_id": 1},
            "timestamp": 1775053255737,
            "body": {"mid": mid, "seq": 1, "attachments": attachments},
            "sender": USER,
        },
    }


def photo(photo_id: int, url: str = PHOTO_URL) -> dict[str, object]:
    return {"type": "image", "payload": {"photo_id": photo_id, "token": "t", "url": url}}


def callback(payload: str, message_id: str, callback_id: str) -> dict[str, object]:
    return {
        "update_type": "message_callback",
        "timestamp": 1775053300000,
        "callback": {
            "timestamp": 1775053300000,
            "callback_id": callback_id,
            "user": USER,
            "payload": payload,
        },
        "message": {
            "recipient": {"chat_id": 5000, "chat_type": "dialog", "user_id": 200},
            "timestamp": 1775053290000,
            "body": {"mid": message_id, "seq": 2, "text": "plain text"},
            "sender": {"user_id": 1, "first_name": "Bot", "is_bot": True},
        },
    }


async def make_bot(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    client = httpx.AsyncClient(transport=httpx.MockTransport(_respond))
    settings = SimpleNamespace(
        max_image_bytes=20 * 1024 * 1024,
        match_min_score=0.70,
        match_min_margin=0.015,
        admin_user_id=777,
        rate_limit=50,
        rate_window_seconds=3600,
    )
    services = Services(
        settings,
        repository,
        ImageStore(tmp_path / "data"),
        ArtifactStore(tmp_path / "data"),
        Moderator(f"{BASE_URL}/moderate", client),
        QualityInspector(f"{BASE_URL}/sam3", client, QualityThresholds(80.0, 0.20, 0.10, 0.015)),
        Matcher(f"{BASE_URL}/v1/match", client),
        CatalogImageLoader(client),
        b"rejection-png",
    )
    api = FakeMaxApi()
    api.downloads[PHOTO_URL] = _demo_image()
    processor = PhotoProcessor(services, api)
    queue = WorkQueue(processor.process, worker_count=1, capacity=10)
    await queue.start()
    repository.set_age_status(
        user_id=200, username="tester", first_name="Test", last_name=None, status="adult", now=1
    )
    handlers = BotHandlers(services, api, queue)
    dispatcher = UpdateDispatcher(repository, handlers.handle)
    return repository, api, queue, dispatcher, client, handlers


async def test_photo_update_gives_a_result_and_feedback_flow(tmp_path):
    repository, api, queue, dispatcher, client, _ = await make_bot(tmp_path)
    try:
        dispatcher.admit([created([photo(10)])])
        await dispatcher.run_once()
        await queue.wait_idle()

        sends = api.calls_of("send_message")
        receipt, result = sends[0], sends[-1]
        assert receipt["reply_to"] == "mid.photo"
        assert receipt["text"].startswith("Фотография принята и поставлена в очередь.")
        status_texts = [call["text"] for call in api.calls_of("edit_message")]
        assert status_texts == ["Проверяю фотографию…", "Проверяю качество фотографии…",
                                "Ищу вино в каталоге…"]
        assert api.calls_of("download")[0]["url"] == PHOTO_URL
        assert result["reply_to"] == "mid.photo"
        assert "Демонстрационное вино" in result["text"]
        assert result["attachments"][0]["type"] == "image"
        assert button_texts(result["attachments"]) == [
            ["Открыть страницу вина"],
            ["✅ Совпало", "❌ Не совпало"],
        ]
        assert api.calls_of("delete_message") == [{"chat_id": 5000, "message_id": "mid.bot-1"}]

        request_id = keyboard_buttons(result["attachments"])[1][1]["payload"].split(":")[2]
        record = repository.admin_request(request_id)
        assert record is not None and record.status == "recognized"
        result_mid = "mid.bot-2"
        stored = repository.sent_message(result_mid)
        assert stored is not None and stored.photo_token == "uploaded-1"

        dispatcher.admit([callback(f"feedback:no:{request_id}", result_mid, "cb-1")])
        await dispatcher.run_once()
        answer = api.calls_of("answer_callback")[-1]
        assert answer["notification"] == "Спасибо! Выберите возможный вариант."
        edit = api.calls_of("edit_message")[-1]
        assert edit["message_id"] == result_mid
        assert edit["text"] == stored.text
        assert edit["text_format"] == "html"
        assert edit["attachments"][0] == {"type": "image", "payload": {"token": "uploaded-1"}}
        assert button_texts(edit["attachments"]) == [
            ["2. Второе вино"],
            ["3. Третье вино"],
            ["4. Четвёртое вино"],
            ["Ничего из этого"],
        ]

        dispatcher.admit([callback(f"alternative:3:{request_id}", result_mid, "cb-2")])
        await dispatcher.run_once()
        assert api.calls_of("answer_callback")[-1]["notification"] == "Спасибо! Ответ сохранён."
        final_edit = api.calls_of("edit_message")[-1]
        assert final_edit["attachments"] == [{"type": "image", "payload": {"token": "uploaded-1"}}]
        record = repository.admin_request(request_id)
        assert record is not None
        assert record.feedback_match is False
        assert record.feedback_selected_rank == 3
        assert record.feedback_selected_slug == "third-wine"
    finally:
        await queue.stop()
        await client.aclose()
        repository.close()


FILE_URL = "https://fd.oneme.example/file?r=bottle"


def image_file(filename: str) -> dict[str, object]:
    # The shape follows the attachment of the official MAX Go client: the file name and size
    # are next to the payload.
    return {
        "type": "file",
        "payload": {"token": "f", "url": FILE_URL},
        "filename": filename,
        "size": 1000,
    }


async def test_image_sent_as_a_file_gives_a_result(tmp_path):
    repository, api, queue, dispatcher, client, _ = await make_bot(tmp_path)
    api.downloads[FILE_URL] = _demo_image()
    try:
        dispatcher.admit([created([image_file("Bottle.JPG")])])
        await dispatcher.run_once()
        await queue.wait_idle()

        result = api.calls_of("send_message")[-1]
        assert api.calls_of("download")[0]["url"] == FILE_URL
        assert result["reply_to"] == "mid.photo"
        assert "Демонстрационное вино" in result["text"]
        assert result["attachments"][0]["type"] == "image"
        requests, total = repository.list_admin_requests(page=1, page_size=10)
        assert total == 1
        assert requests[0].status == "recognized"
    finally:
        await queue.stop()
        await client.aclose()
        repository.close()


async def test_heic_sent_as_a_file_gives_a_result_from_its_jpeg_copy(tmp_path):
    from test_moderation import heic_bytes

    repository, api, queue, dispatcher, client, _ = await make_bot(tmp_path)
    api.downloads[FILE_URL] = heic_bytes()
    try:
        dispatcher.admit([created([image_file("IMG_0001.HEIC")])])
        await dispatcher.run_once()
        await queue.wait_idle()

        result = api.calls_of("send_message")[-1]
        assert "Демонстрационное вино" in result["text"]
        requests, total = repository.list_admin_requests(page=1, page_size=10)
        assert total == 1
        assert requests[0].status == "recognized"
        stored = [path for path in (tmp_path / "data").rglob("*") if path.is_file()]
        accepted = [path for path in stored if "accepted" in path.parts]
        assert len(accepted) == 1
        assert accepted[0].read_bytes()[:3] == b"\xff\xd8\xff"
    finally:
        await queue.stop()
        await client.aclose()
        repository.close()


async def test_other_file_gets_the_photo_request(tmp_path):
    repository, api, queue, dispatcher, client, _ = await make_bot(tmp_path)
    try:
        dispatcher.admit([created([image_file("label.pdf")])])
        await dispatcher.run_once()
        await queue.wait_idle()

        sends = api.calls_of("send_message")
        assert [call["text"] for call in sends] == [
            "Пришлите фотографию бутылки или этикетки. Помощь: /help"
        ]
        assert api.calls_of("download") == []
        assert repository.list_admin_requests(page=1, page_size=10)[1] == 0
    finally:
        await queue.stop()
        await client.aclose()
        repository.close()


async def test_repeated_delivery_of_a_photo_creates_one_request(tmp_path):
    repository, _, queue, _, client, handlers = await make_bot(tmp_path)
    try:
        update = parse_update(created([photo(10)]))
        assert update is not None
        # A crash before the inbox row is marked replays the same update at the next start.
        await handlers.handle(update)
        await handlers.handle(update)
        await queue.wait_idle()

        requests, total = repository.list_admin_requests(page=1, page_size=10)
        assert total == 1
        assert requests[0].status == "recognized"
    finally:
        await queue.stop()
        await client.aclose()
        repository.close()


async def test_album_message_gives_one_receipt_and_results_without_feedback(tmp_path):
    second_url = "https://i.oneme.example/i?r=second"
    repository, api, queue, dispatcher, client, _ = await make_bot(tmp_path)
    api.downloads[second_url] = _demo_image()
    try:
        dispatcher.admit([created([photo(10), photo(11, second_url)], mid="mid.album")])
        await dispatcher.run_once()
        await queue.wait_idle()

        sends = api.calls_of("send_message")
        receipts = [call for call in sends if call["text"].startswith("Фотографии приняты")]
        results = [call for call in sends if "Демонстрационное вино" in (call["text"] or "")]
        assert len(receipts) == 1
        assert len(results) == 2
        assert all(call["reply_to"] == "mid.album" for call in results)
        assert all(button_texts(call["attachments"]) == [["Открыть страницу вина"]]
                   for call in results)
        assert api.calls_of("edit_message")[-1]["text"] == (
            "Результаты альбома отправляются по мере готовности."
        )
    finally:
        await queue.stop()
        await client.aclose()
        repository.close()
