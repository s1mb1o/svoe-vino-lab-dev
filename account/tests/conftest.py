from __future__ import annotations

import base64
import hashlib
import json
import re
from collections.abc import Iterator
from typing import Any
from urllib.parse import parse_qs, quote, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient

from chto_za_vino_account import max_launch
from chto_za_vino_account.api import create_app
from chto_za_vino_account.config import Settings
from chto_za_vino_account.mailer import ImmediateDispatcher, MemoryMailer

WEB_TOKEN = "web-" + "w" * 40
TELEGRAM_TOKEN = "tg-" + "t" * 40
MAX_BOT_TOKEN = "maxbot-" + "m" * 40
CODE_KEY = "key-" + "k" * 40
MAX_TOKEN = "max-platform-bot-token-for-tests"
REDIRECT_URI = "https://chtozavino.ru/api/account/yandex/callback"
CLIENT_IP = "203.0.113.7"
START = 1_800_000_000.0


class Clock:
    def __init__(self) -> None:
        self.now = START

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class FakeYandex:
    """Mock of oauth.yandex.ru and login.yandex.ru that checks PKCE and the client secret."""

    def __init__(self) -> None:
        self.codes: dict[str, tuple[str, str]] = {}
        self.tokens: dict[str, str] = {}
        self.fail_with: int | None = None
        self.requests: list[httpx.Request] = []
        # default_email by Yandex user ID, as login.yandex.ru returns it with login:email.
        self.emails: dict[str, str] = {}

    def authorize(self, authorize_url: str, yandex_id: str, code: str = "yandex-code") -> str:
        query = parse_qs(urlparse(authorize_url).query)
        self.codes[code] = (query["code_challenge"][0], yandex_id)
        return query["state"][0]

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.fail_with is not None:
            return httpx.Response(self.fail_with, json={"error": "failure"})
        if request.url.host == "oauth.yandex.ru" and request.url.path == "/token":
            expected = "Basic " + base64.b64encode(b"yandex-client:yandex-secret").decode()
            if request.headers.get("authorization") != expected:
                return httpx.Response(401, json={"error": "invalid_client"})
            form = parse_qs(request.content.decode())
            code = form["code"][0]
            if code not in self.codes:
                return httpx.Response(400, json={"error": "bad_verification_code"})
            challenge, yandex_id = self.codes.pop(code)
            digest = hashlib.sha256(form["code_verifier"][0].encode()).digest()
            if base64.urlsafe_b64encode(digest).rstrip(b"=").decode() != challenge:
                return httpx.Response(400, json={"error": "invalid_grant"})
            token = f"token-{yandex_id}"
            self.tokens[token] = yandex_id
            return httpx.Response(200, json={"access_token": token, "expires_in": 3600})
        if request.url.host == "login.yandex.ru" and request.url.path == "/info":
            token = request.headers.get("authorization", "").removeprefix("OAuth ")
            if token not in self.tokens:
                return httpx.Response(401, json={"error": "invalid_token"})
            info = {"id": self.tokens[token], "login": "someone"}
            if self.tokens[token] in self.emails:
                info["default_email"] = self.emails[self.tokens[token]]
            return httpx.Response(200, json=info)
        return httpx.Response(404)


def base_env(tmp_path: Any) -> dict[str, str]:
    return {
        "ACCOUNT_DATABASE": str(tmp_path / "account.sqlite3"),
        "ACCOUNT_WEB_TOKEN": WEB_TOKEN,
        "ACCOUNT_TELEGRAM_BOT_TOKEN": TELEGRAM_TOKEN,
        "ACCOUNT_MAX_BOT_TOKEN": MAX_BOT_TOKEN,
        "ACCOUNT_CODE_KEY": CODE_KEY,
        "ACCOUNT_CONSENT_VERSION": "consent-1",
        "ACCOUNT_TERMS_VERSION": "terms-1",
        "ACCOUNT_EMAIL_BACKEND": "memory",
        "YANDEX_CLIENT_ID": "yandex-client",
        "YANDEX_CLIENT_SECRET": "yandex-secret",
        "YANDEX_REDIRECT_URIS": REDIRECT_URI,
        "MAX_WEBAPP_KEY": max_launch.derive_key(MAX_TOKEN).hex(),
        "TELEGRAM_BOT_USERNAME": "ChtoZaVinoBot",
    }


def init_data(
    *,
    user_id: int = 777,
    query_id: str = "query-1",
    auth_date: int | None = None,
    ip: str | None = CLIENT_IP,
    token: str = MAX_TOKEN,
) -> str:
    user = json.dumps(
        {"id": user_id, "first_name": "Анна", "last_name": "Петрова", "username": None},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    pairs = {
        "auth_date": str(int(START) if auth_date is None else auth_date),
        "chat": '{"id":1,"type":"DIALOG"}',
        "query_id": query_id,
        "user": user,
    }
    if ip is not None:
        pairs["ip"] = ip
    signature = max_launch.sign(max_launch.derive_key(token), pairs)
    encoded = "&".join(f"{name}={quote(value, safe='')}" for name, value in pairs.items())
    return f"{encoded}&hash={signature}"


class Harness:
    def __init__(self, env: dict[str, str], client_host: str = "127.0.0.1") -> None:
        self.clock = Clock()
        self.mailer = MemoryMailer()
        self.yandex_server = FakeYandex()
        settings = Settings.from_env(env)
        app = create_app(
            settings,
            dispatcher=ImmediateDispatcher(self.mailer),
            http=httpx.Client(transport=httpx.MockTransport(self.yandex_server.handle)),
            clock=self.clock,
        )
        self.client = TestClient(app, client=(client_host, 50000))
        self.client.__enter__()

    def close(self) -> None:
        self.client.__exit__(None, None, None)

    def web(
        self,
        method: str,
        path: str,
        *,
        session: str | None = None,
        ip: str = CLIENT_IP,
        **kwargs: Any,
    ) -> httpx.Response:
        headers = {"Authorization": f"Bearer {WEB_TOKEN}", "X-Client-IP": ip}
        if session:
            headers["X-Session-Token"] = session
        return self.client.request(method, path, headers=headers, **kwargs)

    def bot(self, path: str, body: dict[str, Any], token: str = TELEGRAM_TOKEN) -> httpx.Response:
        return self.client.post(path, json=body, headers={"Authorization": f"Bearer {token}"})

    def last_code(self) -> str:
        match = re.search(r"Ваш код: (\d{6})", self.mailer.sent[-1].text)
        assert match
        return match.group(1)

    def signup(self, ticket: str, username: str) -> httpx.Response:
        return self.web(
            "POST",
            "/v1/auth/signup",
            json={
                "signup_ticket": ticket,
                "username": username,
                "consent_version": "consent-1",
                "terms_version": "terms-1",
            },
        )

    def email_session(self, email: str, username: str = "anna_wine") -> str:
        start = self.web("POST", "/v1/auth/email/start", json={"email": email})
        assert start.status_code == 200, start.text
        verify = self.web(
            "POST",
            "/v1/auth/email/verify",
            json={"challenge_id": start.json()["challenge_id"], "code": self.last_code()},
        )
        assert verify.status_code == 200, verify.text
        body = verify.json()
        if body["status"] == "signup_required":
            created = self.signup(body["signup_ticket"], username)
            assert created.status_code == 200, created.text
            body = created.json()
        self.clock.advance(61)
        return body["session"]["token"]

    def yandex_login(
        self, yandex_id: str, *, session: str | None = None, purpose: str = "login"
    ) -> httpx.Response:
        start = self.web(
            "POST",
            "/v1/auth/yandex/start",
            session=session,
            json={"redirect_uri": REDIRECT_URI, "purpose": purpose},
        )
        assert start.status_code == 200, start.text
        state = self.yandex_server.authorize(start.json()["authorize_url"], yandex_id)
        return self.web(
            "POST",
            "/v1/auth/yandex/finish",
            session=session,
            json={"flow_id": start.json()["flow_id"], "state": state, "code": "yandex-code"},
        )


@pytest.fixture
def env(tmp_path: Any) -> dict[str, str]:
    return base_env(tmp_path)


@pytest.fixture
def harness(env: dict[str, str]) -> Iterator[Harness]:
    instance = Harness(env)
    yield instance
    instance.close()
