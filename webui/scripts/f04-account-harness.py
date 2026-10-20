"""Run the actual account service with isolated SQLite and an in-memory mail sink.

This helper never connects to SMTP. It does not prove real email delivery.
All addresses, consumer tokens, and sessions belong to the disposable test environment.
"""
from __future__ import annotations

import json
import os
import re
import socket
import sys
from pathlib import Path

import uvicorn
from chto_za_vino_account.api import create_app
from chto_za_vino_account.config import Settings
from chto_za_vino_account.mailer import ImmediateDispatcher, MemoryMailer
from chto_za_vino_account.service import SignupRequired

directory = Path(sys.argv[1])
directory.mkdir(parents=True, exist_ok=True)
os.umask(0o077)

class CaptureMailer(MemoryMailer):
    def send(self, mail):
        super().send(mail)
        # Only generated test addresses and challenge codes enter this private test file.
        codes = {item.to: re.search(r"\b\d{6}\b", item.text).group() for item in self.sent}
        (directory / "outbox.json").write_text(json.dumps(codes))

mailer = CaptureMailer()
settings = Settings.from_env({
    "ACCOUNT_DATABASE": str(directory / "account.sqlite3"),
    "ACCOUNT_WEB_TOKEN": "f04-local-web-" + "w" * 40,
    "ACCOUNT_CODE_KEY": "f04-local-code-" + "c" * 40,
    "ACCOUNT_EMAIL_BACKEND": "memory",
    "ACCOUNT_CONSENT_VERSION": "f04-consent",
    "ACCOUNT_TERMS_VERSION": "f04-terms",
    "ACCOUNT_TEST_CODE": "",
})
assert not settings.test_code
app = create_app(settings, dispatcher=ImmediateDispatcher(mailer))
sessions = {}
for name in ("a", "b"):
    service = app.state.service
    challenge, _ = service.email_start(f"f04-{name}@example.invalid", "login", "127.0.0.1", None)
    code = re.search(r"\b\d{6}\b", mailer.sent[-1].text).group()
    result = service.email_verify(challenge, code, None)
    assert isinstance(result, SignupRequired)
    issued = service.signup(result.ticket, f"f04_{name}", settings.consent_version, settings.terms_version)
    sessions[name] = {"token": issued.token, "userId": issued.user_id}
(directory / "sessions.json").write_text(json.dumps(sessions))

sock = socket.socket()
sock.bind(("127.0.0.1", 0))
(directory / "account-port.json").write_text(json.dumps({"port": sock.getsockname()[1]}))
server = uvicorn.Server(uvicorn.Config(app, log_level="warning", access_log=False))
server.run(sockets=[sock])
