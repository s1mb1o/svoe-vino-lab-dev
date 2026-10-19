"""Email delivery.

A request never waits for the mail server. The dispatcher sends from a background thread
with a few retries. A lost message is not stored: the person asks for a new code.
"""

from __future__ import annotations

import logging
import queue
import smtplib
import ssl
import sys
import threading
import time
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol

from .config import Settings, SmtpSettings

LOG = logging.getLogger("chto_za_vino_account.mail")
RETRY_DELAYS = (0, 5, 30)


@dataclass(frozen=True)
class Mail:
    to: str
    subject: str
    text: str


class Mailer(Protocol):
    def send(self, mail: Mail) -> None: ...


class SmtpMailer:
    def __init__(self, settings: SmtpSettings, sender: str) -> None:
        self._settings = settings
        self._sender = sender

    def send(self, mail: Mail) -> None:
        message = EmailMessage()
        message["From"] = self._sender
        message["To"] = mail.to
        message["Subject"] = mail.subject
        message.set_content(mail.text)
        context = ssl.create_default_context()
        settings = self._settings
        if settings.security == "ssl":
            client: smtplib.SMTP = smtplib.SMTP_SSL(
                settings.host, settings.port, timeout=10, context=context
            )
        else:
            client = smtplib.SMTP(settings.host, settings.port, timeout=10)
        with client:
            if settings.security == "starttls":
                client.starttls(context=context)
            if settings.username:
                client.login(settings.username, settings.password)
            client.send_message(message)


class ConsoleMailer:
    """Development only. Writes the message, including the code, to stderr."""

    def send(self, mail: Mail) -> None:
        print(f"[dev mail] to={mail.to} subject={mail.subject}\n{mail.text}", file=sys.stderr)


class MemoryMailer:
    """Tests only."""

    def __init__(self) -> None:
        self.sent: list[Mail] = []

    def send(self, mail: Mail) -> None:
        self.sent.append(mail)


class Dispatcher(Protocol):
    def submit(self, mail: Mail) -> None: ...

    def close(self) -> None: ...


class ImmediateDispatcher:
    def __init__(self, mailer: Mailer) -> None:
        self._mailer = mailer

    def submit(self, mail: Mail) -> None:
        self._mailer.send(mail)

    def close(self) -> None:
        return None


class ThreadDispatcher:
    def __init__(self, mailer: Mailer, capacity: int = 1000) -> None:
        self._mailer = mailer
        self._queue: queue.Queue[Mail | None] = queue.Queue(maxsize=capacity)
        self._thread = threading.Thread(target=self._run, name="account-mail", daemon=True)
        self._thread.start()

    def submit(self, mail: Mail) -> None:
        try:
            self._queue.put_nowait(mail)
        except queue.Full:
            LOG.error("Mail queue is full; a message was dropped")

    def close(self) -> None:
        self._queue.put(None)
        self._thread.join(timeout=15)

    def _run(self) -> None:
        while (mail := self._queue.get()) is not None:
            for attempt, delay in enumerate(RETRY_DELAYS, start=1):
                time.sleep(delay)
                try:
                    self._mailer.send(mail)
                    break
                except Exception as error:  # noqa: BLE001 - any delivery error is retried
                    LOG.warning(
                        "Mail delivery failed (attempt %d): %s", attempt, type(error).__name__
                    )
            else:
                LOG.error("Mail delivery failed after %d attempts", len(RETRY_DELAYS))


def build_mailer(settings: Settings) -> Mailer:
    if settings.email_backend == "smtp" and settings.smtp is not None:
        return SmtpMailer(settings.smtp, settings.email_from)
    if settings.email_backend == "memory":
        return MemoryMailer()
    return ConsoleMailer()


def code_mail(to: str, code: str, purpose: str, site_name: str) -> Mail:
    if purpose == "link":
        subject = "Код для привязки адреса к «Винному дневнику»"
        action = "привязать этот адрес к «Винному дневнику»"
    else:
        subject = "Код для входа в «Винный дневник»"
        action = "войти в «Винный дневник»"
    text = (
        f"Ваш код: {code}\n\n"
        f"Введите его на {site_name}, чтобы {action}. Код действует 10 минут.\n"
        "Никому не сообщайте этот код.\n"
        "Если вы не запрашивали код, просто удалите это письмо.\n\n"
        f"{site_name}\n"
    )
    return Mail(to=to, subject=subject, text=text)
