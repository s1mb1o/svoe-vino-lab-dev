"""Email delivery.

A request never waits for the mail server. The dispatcher sends from a background thread
with a few retries. A lost message is not stored: the person asks for a new code.
"""

from __future__ import annotations

import html
import logging
import queue
import smtplib
import ssl
import sys
import threading
import time
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Protocol

from .config import Settings, SmtpSettings

LOG = logging.getLogger("chto_za_vino_account.mail")
RETRY_DELAYS = (0, 5, 30)


@dataclass(frozen=True)
class Mail:
    to: str = field(repr=False)
    subject: str
    text: str = field(repr=False)
    # Optional HTML alternative. The text stays the fallback for clients without HTML.
    html: str | None = field(default=None, repr=False)


def build_message(mail: Mail, sender: str) -> EmailMessage:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = mail.to
    message["Subject"] = mail.subject
    message.set_content(mail.text)
    if mail.html:
        message.add_alternative(mail.html, subtype="html")
    return message


class Mailer(Protocol):
    def send(self, mail: Mail) -> None: ...


class SmtpMailer:
    def __init__(self, settings: SmtpSettings, sender: str) -> None:
        self._settings = settings
        self._sender = sender

    def send(self, mail: Mail) -> None:
        message = build_message(mail, self._sender)
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
    grouped = f"{code[:3]} {code[3:]}" if len(code) == 6 else code
    if purpose == "link":
        subject = f"{grouped} — код для привязки адреса к «Винному дневнику»"
        title = "Код для привязки адреса"
        action = "привязать этот адрес к «Винному дневнику»"
    else:
        subject = f"{grouped} — код для входа в «Винный дневник»"
        title = "Код для входа"
        action = "войти в «Винный дневник»"
    text = (
        f"Ваш код: {code}\n\n"
        f"Введите его на {site_name}, чтобы {action}. Код действует 10 минут.\n"
        "Никому не сообщайте этот код.\n"
        "Если вы не запрашивали код, просто удалите это письмо.\n\n"
        f"{site_name}\n"
    )
    return Mail(to=to, subject=subject, text=text, html=_code_html(code, title, action, site_name))


def _code_html(code: str, title: str, action: str, site_name: str) -> str:
    """The code email in HTML: one card, a short text, and the code in large type.

    Layout by tables and inline styles, as mail clients need. No images and no links: the
    message works offline and gives nothing to track. The code is two spans with a margin, so a
    copy gives the digits without a space.
    """
    esc = html.escape
    halves = (code[:3], code[3:]) if len(code) == 6 else (code, "")
    digits = (
        f'<span style="white-space:nowrap;">{esc(halves[0])}</span>'
        + (f'<span style="white-space:nowrap;margin-left:0.3em;">{esc(halves[1])}</span>' if halves[1] else "")
    )
    font = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif"
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<meta name="viewport" content="width=device-width">
<meta name="color-scheme" content="light">
<title>{esc(title)}</title>
</head>
<body style="margin:0;padding:0;background:#f4efe9;">
<div style="display:none;max-height:0;overflow:hidden;">{esc(halves[0] + " " + halves[1])} — код действует 10 минут.</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f4efe9;">
<tr><td align="center" style="padding:32px 16px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:480px;">
<tr><td align="center" style="padding:0 0 20px;font-family:{font};font-size:13px;letter-spacing:0.12em;text-transform:uppercase;color:#7b3528;">Что за вино? · Винный дневник</td></tr>
<tr><td align="center" style="background:#fefdfa;border:1px solid #e8e1d8;border-radius:20px;padding:36px 28px;">
<div style="font-family:{font};font-size:22px;line-height:28px;font-weight:600;color:#2c2a28;">{esc(title)}</div>
<div style="font-family:{font};font-size:15px;line-height:22px;color:#6b635d;padding:12px 0 24px;">Введите его на {esc(site_name)}, чтобы {esc(action)}. Код действует 10&nbsp;минут и подходит один раз. Никому не сообщайте этот код.</div>
<div style="font-family:{font};font-size:40px;line-height:48px;font-weight:600;letter-spacing:0.06em;color:#2c2a28;background:#f4efe9;border-radius:14px;padding:16px 8px;">{digits}</div>
</td></tr>
<tr><td align="center" style="padding:20px 8px 0;font-family:{font};font-size:13px;line-height:19px;color:#857e79;">Если вы не запрашивали код, просто удалите это письмо.<br>{esc(site_name)}</td></tr>
</table>
</td></tr>
</table>
</body>
</html>
"""
