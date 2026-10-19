import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest

from chto_za_vino_bot.account import (
    CANCEL_DATA,
    CONFIRM_PREFIX,
    LINK_CANCELLED_TEXT,
    LINK_IN_USE_TEXT,
    LINK_INVALID_TEXT,
    LINK_OFF_TEXT,
    LINK_PRIVATE_TEXT,
    LINK_UNAVAILABLE_TEXT,
    UNLINK_DONE_TEXT,
    UNLINK_NONE_TEXT,
    AccountClient,
    BackgroundTasks,
    handle_link_callback,
    handle_link_start,
    handle_unlink_command,
    link_code,
)
from chto_za_vino_bot.config import Settings

CODE = "A" * 22
TOKEN = "t" * 40


class FakeMessage:
    def __init__(self, chat_type: str = "private", user_id: int = 501) -> None:
        self.chat = SimpleNamespace(id=user_id, type=chat_type)
        self.from_user = SimpleNamespace(id=user_id)
        self.answers: list[tuple[str, dict[str, object]]] = []
        self.edits: list[tuple[str, dict[str, object]]] = []

    async def answer(self, text: str, **kwargs: object) -> None:
        self.answers.append((text, kwargs))

    async def edit_text(self, text: str, **kwargs: object) -> None:
        self.edits.append((text, kwargs))


class FakeCallback:
    def __init__(self, data: str, message: FakeMessage, user_id: int = 501) -> None:
        self.data = data
        self.message = message
        self.from_user = SimpleNamespace(id=user_id)
        self.notifications: list[tuple[str | None, dict[str, object]]] = []

    async def answer(self, text: str | None = None, **kwargs: object) -> None:
        self.notifications.append((text, kwargs))


@pytest.fixture(autouse=True)
def message_type(monkeypatch):
    # The handlers edit only a real aiogram Message. The fake stands in for it.
    monkeypatch.setattr("chto_za_vino_bot.account.Message", FakeMessage)


class FakeService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object], str | None]] = []
        self.answers: dict[str, httpx.Response | Exception] = {}

    def handler(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        self.calls.append((request.url.path, body, request.headers.get("authorization")))
        answer = self.answers.get(request.url.path)
        if isinstance(answer, Exception):
            raise answer
        if answer is not None:
            return answer
        if request.url.path.endswith("/claim"):
            return httpx.Response(200, json={"username": "anna_wine"})
        if request.url.path.endswith("/confirm"):
            return httpx.Response(200, json={"status": "linked", "username": "anna_wine"})
        return httpx.Response(200, json={"status": "unlinked"})


@pytest.fixture
async def service():
    fake = FakeService()
    async with httpx.AsyncClient(transport=httpx.MockTransport(fake.handler)) as client:
        fake.client = AccountClient("http://account.test/", TOKEN, client)
        yield fake


def test_link_code_reads_only_the_link_payload():
    assert link_code(f"link_{CODE}") == CODE
    assert link_code("privacy") is None
    assert link_code(None) is None


async def test_start_link_asks_for_confirmation(service):
    message = FakeMessage()
    await handle_link_start(message, CODE, service.client)
    path, body, authorization = service.calls[0]
    assert path == "/v1/bot/telegram/links/claim"
    assert body == {"code": CODE, "telegram_user_id": 501}
    assert authorization == f"Bearer {TOKEN}"
    text, kwargs = message.answers[0]
    assert "«<b>anna_wine</b>»" in text
    assert "Войти в дневник через Telegram нельзя" in text
    buttons = kwargs["reply_markup"].inline_keyboard[0]
    assert [button.text for button in buttons] == ["Привязать", "Отмена"]
    assert buttons[0].callback_data == f"{CONFIRM_PREFIX}{CODE}"
    assert len(buttons[0].callback_data.encode()) <= 64


async def test_confirm_links_the_sender(service):
    message = FakeMessage()
    callback = FakeCallback(f"{CONFIRM_PREFIX}{CODE}", message, user_id=501)
    await handle_link_callback(callback, service.client)
    assert service.calls[0][0] == "/v1/bot/telegram/links/confirm"
    assert service.calls[0][1] == {"code": CODE, "telegram_user_id": 501}
    text, kwargs = message.edits[0]
    assert text.startswith("Готово: Telegram привязан к дневнику «<b>anna_wine</b>»")
    assert kwargs["reply_markup"] is None


async def test_cancel_makes_no_service_call(service):
    message = FakeMessage()
    await handle_link_callback(FakeCallback(CANCEL_DATA, message), service.client)
    assert service.calls == []
    assert message.edits[0][0] == LINK_CANCELLED_TEXT


@pytest.mark.parametrize(
    ("error", "text"),
    [
        ("invalid_link_code", LINK_INVALID_TEXT),
        ("identity_in_use", LINK_IN_USE_TEXT),
        ("provider_disabled", LINK_OFF_TEXT),
    ],
)
async def test_claim_refusals(service, error, text):
    status = 409 if error == "identity_in_use" else 400
    service.answers["/v1/bot/telegram/links/claim"] = httpx.Response(status, json={"error": error})
    message = FakeMessage()
    await handle_link_start(message, CODE, service.client)
    assert message.answers == [(text, {})]


async def test_an_outage_keeps_the_buttons(service):
    service.answers["/v1/bot/telegram/links/confirm"] = httpx.ConnectError("refused")
    message = FakeMessage()
    callback = FakeCallback(f"{CONFIRM_PREFIX}{CODE}", message)
    await handle_link_callback(callback, service.client)
    assert message.edits == []
    assert callback.notifications == [(LINK_UNAVAILABLE_TEXT, {"show_alert": True})]


@pytest.mark.parametrize(
    "answer",
    [
        httpx.Response(503, json={"error": "unavailable"}),
        httpx.Response(401, json={"error": "unauthorized"}),
        httpx.Response(200, text="not json"),
        httpx.ReadTimeout("slow"),
    ],
)
async def test_service_faults_are_unavailable(service, answer):
    service.answers["/v1/bot/telegram/links/claim"] = answer
    message = FakeMessage()
    await handle_link_start(message, CODE, service.client)
    assert message.answers == [(LINK_UNAVAILABLE_TEXT, {})]


async def test_link_only_in_a_private_chat(service):
    message = FakeMessage(chat_type="group")
    await handle_link_start(message, CODE, service.client)
    assert service.calls == []
    assert message.answers == [(LINK_PRIVATE_TEXT, {})]


async def test_malformed_code_makes_no_service_call(service):
    message = FakeMessage()
    await handle_link_start(message, "short", service.client)
    assert service.calls == []
    assert message.answers == [(LINK_INVALID_TEXT, {})]


async def test_link_off_without_endpoint():
    message = FakeMessage()
    await handle_link_start(message, CODE, None)
    assert message.answers == [(LINK_OFF_TEXT, {})]


async def test_unlink(service):
    message = FakeMessage()
    await handle_unlink_command(message, service.client)
    assert service.calls[0][:2] == ("/v1/bot/telegram/unlink", {"telegram_user_id": 501})
    assert message.answers == [(UNLINK_DONE_TEXT, {})]
    service.answers["/v1/bot/telegram/unlink"] = httpx.Response(200, json={"status": "not_linked"})
    await handle_unlink_command(message, service.client)
    assert message.answers[-1] == (UNLINK_NONE_TEXT, {})


async def test_background_tasks_free_the_dispatcher():
    started = asyncio.Event()
    release = asyncio.Event()

    async def slow() -> None:
        started.set()
        await release.wait()

    async def broken() -> None:
        raise RuntimeError("boom")

    tasks = BackgroundTasks()
    tasks.spawn(slow())
    tasks.spawn(broken())
    await asyncio.wait_for(started.wait(), 1)
    release.set()
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    assert not tasks._tasks


def test_settings_read_the_account_endpoint(monkeypatch, tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text(
        "moderation: {enabled: false}\n"
        "endpoints:\n"
        "  sam3: http://sam3.test\n"
        "  matcher: http://matcher.test/v1/match\n",
        encoding="utf-8",
    )
    for name, value in {
        "TELEGRAM_BOT_TOKEN": "123:abc",
        "BOT_CONFIG": str(config),
        "BOT_ENVIRONMENT": "test",
        "BOT_ADMIN_USER_ID": "1",
        "BOT_HTTP_API_TOKEN": "h" * 40,
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("BOT_ACCOUNT_ENDPOINT", raising=False)
    assert Settings.from_env().account_endpoint == ""
    monkeypatch.setenv("BOT_ACCOUNT_ENDPOINT", "http://192.168.86.14:28008/")
    with pytest.raises(ValueError, match="BOT_ACCOUNT_TOKEN"):
        Settings.from_env()
    monkeypatch.setenv("BOT_ACCOUNT_TOKEN", TOKEN)
    settings = Settings.from_env()
    assert (settings.account_endpoint, settings.account_token) == (
        "http://192.168.86.14:28008",
        TOKEN,
    )
    monkeypatch.setenv("BOT_ACCOUNT_ENDPOINT", "http://user:pw@account.test/")
    with pytest.raises(ValueError, match="BOT_ACCOUNT_ENDPOINT"):
        Settings.from_env()
