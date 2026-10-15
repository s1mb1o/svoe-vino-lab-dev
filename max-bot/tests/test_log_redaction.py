"""Secret redaction in the logs of the MAX bot. Port of `telegram-bot/tests/test_log_redaction.py`.

MAX differences:
- The Telegram test uses an aiogram download error that contains the bot token in the file URL.
  The MAX client sends the token only in the `Authorization` header, and a `MaxApiError` text
  contains no token or URL. The MAX test injects a download error whose text repeats the secrets
  and checks the traceback of the processor log.
- The formatter also redacts the webhook secret.
- `configure_logging` installs the redacting handler and keeps the `httpx` and `httpcore` loggers
  at WARNING, because `httpx` logs each request URL at INFO and an attachment URL gives access to
  a user photo.
"""

import io
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from fakes import DIALOG_CHAT_ID, USER_ID, FakeMaxApi

from chto_za_vino_max_bot.app import (
    LOG_FORMAT,
    PhotoJob,
    PhotoProcessor,
    SecretRedactingFormatter,
    configure_logging,
)
from chto_za_vino_max_bot.storage import Repository

MAX_TOKEN = "max-token-for-redaction-check_0123456789"
API_TOKEN = "api-token-for-redaction-check-0123456789"
WEBHOOK_SECRET = "webhook-secret-for-redaction-check_0123456789"
SECRETS = (MAX_TOKEN, API_TOKEN, WEBHOOK_SECRET)
PHOTO_URL = "https://i.oneme.example/photo-1.jpg"
HTTP_CLIENT_LOGGERS = ("httpx", "httpcore")


class SecretEchoError(RuntimeError):
    """A library error that repeats secret values in its text."""


@contextmanager
def isolated_root_logger() -> Iterator[logging.Logger]:
    """Give `basicConfig` a root logger without handlers. Restore the logging state after."""
    root = logging.getLogger()
    saved_handlers = list(root.handlers)
    saved_level = root.level
    saved_levels = {name: logging.getLogger(name).level for name in HTTP_CLIENT_LOGGERS}
    for handler in saved_handlers:
        root.removeHandler(handler)
    for name in HTTP_CLIENT_LOGGERS:
        logging.getLogger(name).setLevel(logging.NOTSET)
    try:
        yield root
    finally:
        for handler in list(root.handlers):
            root.removeHandler(handler)
            handler.close()
        for handler in saved_handlers:
            root.addHandler(handler)
        root.setLevel(saved_level)
        for name, level in saved_levels.items():
            logging.getLogger(name).setLevel(level)


def logging_settings(*, webhook: bool, log_level: str = "DEBUG") -> SimpleNamespace:
    return SimpleNamespace(
        max_token=MAX_TOKEN,
        http_api_token=API_TOKEN,
        webhook=SimpleNamespace(secret=WEBHOOK_SECRET) if webhook else None,
        log_level=log_level,
    )


def configured_output(settings: SimpleNamespace, emit) -> str:
    """Run `configure_logging`, send the records of `emit`, and return the handler output."""
    stream = io.StringIO()
    with isolated_root_logger() as root:
        configure_logging(settings)
        [handler] = root.handlers
        assert isinstance(handler, logging.StreamHandler)
        assert isinstance(handler.formatter, SecretRedactingFormatter)
        handler.setStream(stream)
        emit()
    return stream.getvalue()


async def test_a_download_failure_log_does_not_contain_the_secrets(tmp_path, caplog):
    repository = Repository(tmp_path / "bot.sqlite3")
    reservation = repository.reserve(
        chat_id=DIALOG_CHAT_ID,
        chat_type="dialog",
        message_id="mid.source",
        photo_index=0,
        user_id=USER_ID,
        username="tester",
        first_name="Test",
        last_name=None,
        photo_id=9001,
        photo_url=PHOTO_URL,
        photo_token="token-1",
        now=1000,
        limit=50,
        window_seconds=3600,
    )
    assert reservation.request_id is not None
    services = SimpleNamespace(
        settings=SimpleNamespace(max_image_bytes=20 * 1024 * 1024),
        repository=repository,
    )
    api = FakeMaxApi()
    api.fail_on["download"] = SecretEchoError(
        f"download failed: Authorization={MAX_TOKEN} api={API_TOKEN} webhook={WEBHOOK_SECRET}"
    )
    processor = PhotoProcessor(services, api)

    with caplog.at_level(logging.ERROR, logger="chto_za_vino_max_bot"):
        await processor.process(
            PhotoJob(
                request_id=reservation.request_id,
                chat_id=DIALOG_CHAT_ID,
                source_message_id="mid.source",
                received_at=1000,
                photo_url=PHOTO_URL,
                status_enabled=False,
            )
        )

    assert repository.admin_request(reservation.request_id).status == "download_failed"
    repository.close()
    assert [call["text"] for call in api.calls_of("send_message")] == [
        "Не удалось загрузить фотографию. Попробуйте еще раз."
    ]
    records = [
        record
        for record in caplog.records
        if record.getMessage() == "MAX image download failed"
    ]
    assert len(records) == 1
    plain = logging.Formatter(LOG_FORMAT).format(records[0])
    assert all(secret in plain for secret in SECRETS)
    formatted = SecretRedactingFormatter(LOG_FORMAT, SECRETS).format(records[0])
    assert all(secret not in formatted for secret in SECRETS)
    assert "SecretEchoError" in formatted
    assert "Authorization=[REDACTED] api=[REDACTED] webhook=[REDACTED]" in formatted


def test_the_formatter_redacts_every_secret_and_ignores_an_empty_secret():
    record = logging.LogRecord(
        "chto_za_vino_max_bot",
        logging.INFO,
        __file__,
        1,
        "token=%s api=%s webhook=%s",
        SECRETS,
        None,
    )

    formatted = SecretRedactingFormatter(LOG_FORMAT, (*SECRETS, "")).format(record)

    assert formatted.endswith("token=[REDACTED] api=[REDACTED] webhook=[REDACTED]")


@pytest.mark.parametrize("webhook", [True, False], ids=["webhook", "polling"])
def test_configure_logging_redacts_the_configured_secrets(webhook):
    def emit() -> None:
        log = logging.getLogger("chto_za_vino_max_bot")
        try:
            raise SecretEchoError(f"token={MAX_TOKEN} webhook={WEBHOOK_SECRET}")
        except SecretEchoError:
            log.exception("api=%s", API_TOKEN)
        log.info("plain message")

    output = configured_output(logging_settings(webhook=webhook), emit)

    assert MAX_TOKEN not in output
    assert API_TOKEN not in output
    assert "api=[REDACTED]" in output
    if webhook:
        assert WEBHOOK_SECRET not in output
        assert "SecretEchoError: token=[REDACTED] webhook=[REDACTED]" in output
    else:
        # Polling has no webhook secret. The empty secret value does not change the text.
        assert f"SecretEchoError: token=[REDACTED] webhook={WEBHOOK_SECRET}" in output
    assert output.rstrip("\n").endswith(" INFO chto_za_vino_max_bot plain message")


def test_configure_logging_keeps_the_http_client_loggers_at_warning():
    def emit() -> None:
        logging.getLogger("httpx").info('HTTP Request: GET %s "HTTP/1.1 200 OK"', PHOTO_URL)
        logging.getLogger("httpcore.http11").debug("send_request_headers.started %s", PHOTO_URL)
        logging.getLogger("httpx").warning("httpx warning")
        logging.getLogger("chto_za_vino_max_bot").debug("bot debug")

    output = configured_output(logging_settings(webhook=True, log_level="DEBUG"), emit)

    # BOT_LOG_LEVEL=DEBUG applies to the bot loggers, but not to the HTTP client loggers.
    assert PHOTO_URL not in output
    assert " WARNING httpx httpx warning" in output
    assert " DEBUG chto_za_vino_max_bot bot debug" in output


def test_configure_logging_sets_the_http_client_logger_levels():
    with isolated_root_logger() as root:
        configure_logging(logging_settings(webhook=False, log_level="INFO"))

        assert root.level == logging.INFO
        for name in HTTP_CLIENT_LOGGERS:
            assert logging.getLogger(name).level == logging.WARNING
            assert not logging.getLogger(name).isEnabledFor(logging.INFO)
