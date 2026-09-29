import io
import logging
from types import SimpleNamespace

import aiohttp
from multidict import CIMultiDict, CIMultiDictProxy
from yarl import URL

from chto_za_vino_bot.app import LOG_FORMAT, PhotoJob, PhotoProcessor, SecretRedactingFormatter
from chto_za_vino_bot.storage import Repository

BOT_TOKEN = "123456789:AAtest-token_value_for_redaction_check"
API_TOKEN = "api-token-for-redaction-check-0123456789"


class FailingDownloadBot:
    async def get_file(self, file_id: str):
        return SimpleNamespace(file_path="photos/file_1.jpg")

    async def download_file(self, file_path: str, *, destination: io.BytesIO) -> None:
        # aiogram downloads from this URL with raise_for_status=True.
        url = URL(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}")
        raise aiohttp.ClientResponseError(
            aiohttp.RequestInfo(url, "GET", CIMultiDictProxy(CIMultiDict()), url),
            (),
            status=404,
            message="Not Found",
        )


async def test_a_download_failure_log_does_not_contain_the_bot_token(tmp_path, caplog):
    repository = Repository(tmp_path / "bot.sqlite3")
    reservation = repository.reserve(
        chat_id=100,
        message_id=10,
        user_id=200,
        username="tester",
        first_name="Test",
        last_name=None,
        file_id="file-1",
        file_unique_id="unique-1",
        now=1000,
        limit=50,
        window_seconds=3600,
    )
    assert reservation.request_id is not None
    services = SimpleNamespace(
        settings=SimpleNamespace(max_image_bytes=20 * 1024 * 1024),
        repository=repository,
    )
    processor = PhotoProcessor(services, FailingDownloadBot())

    with caplog.at_level(logging.ERROR, logger="chto_za_vino_bot"):
        await processor.process(
            PhotoJob(
                reservation.request_id,
                100,
                10,
                1000,
                "file-1",
                None,
                status_enabled=False,
            )
        )

    assert repository.admin_request(reservation.request_id).status == "download_failed"
    repository.close()
    records = [
        record
        for record in caplog.records
        if record.getMessage() == "Telegram image download failed"
    ]
    assert len(records) == 1
    assert BOT_TOKEN in logging.Formatter(LOG_FORMAT).format(records[0])
    formatted = SecretRedactingFormatter(LOG_FORMAT, (BOT_TOKEN, API_TOKEN)).format(records[0])
    assert BOT_TOKEN not in formatted
    assert "ClientResponseError" in formatted


def test_the_formatter_redacts_every_secret_and_ignores_an_empty_secret():
    record = logging.LogRecord(
        "chto_za_vino_bot",
        logging.INFO,
        __file__,
        1,
        "bot=%s api=%s",
        (BOT_TOKEN, API_TOKEN),
        None,
    )

    formatted = SecretRedactingFormatter(LOG_FORMAT, (BOT_TOKEN, API_TOKEN, "")).format(record)

    assert formatted.endswith("bot=[REDACTED] api=[REDACTED]")
