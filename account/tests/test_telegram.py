from __future__ import annotations

from conftest import Harness


def link_code(harness, token):
    response = harness.web("POST", "/v1/me/links/telegram", session=token)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["deep_link"] == f"https://t.me/ChtoZaVinoBot?start=link_{body['code']}"
    assert len("link_" + body["code"]) <= 64
    return body["code"]


def test_link_telegram_with_confirmation(harness):
    token = harness.email_session("anna@example.ru")
    code = link_code(harness, token)
    claim = harness.bot("/v1/bot/telegram/links/claim", {"code": code, "telegram_user_id": 501})
    assert claim.json() == {"username": "anna_wine"}
    confirm = harness.bot(
        "/v1/bot/telegram/links/confirm", {"code": code, "telegram_user_id": 501}
    )
    assert confirm.json() == {"status": "linked", "username": "anna_wine"}
    me = harness.web("GET", "/v1/me", session=token).json()
    assert {i["provider"] for i in me["user"]["identities"]} == {"email", "telegram"}
    reused = harness.bot(
        "/v1/bot/telegram/links/confirm", {"code": code, "telegram_user_id": 501}
    )
    assert reused.json()["error"] == "invalid_link_code"
    again = harness.web("POST", "/v1/me/links/telegram", session=token)
    assert again.json()["error"] == "provider_already_linked"


def test_link_code_expires(harness):
    token = harness.email_session("anna@example.ru")
    code = link_code(harness, token)
    harness.clock.advance(601)
    response = harness.bot("/v1/bot/telegram/links/claim", {"code": code, "telegram_user_id": 5})
    assert response.json()["error"] == "invalid_link_code"


def test_telegram_of_another_diary(harness):
    first = harness.email_session("anna@example.ru")
    code = link_code(harness, first)
    harness.bot("/v1/bot/telegram/links/confirm", {"code": code, "telegram_user_id": 501})
    second = harness.email_session("other@example.ru", username="other")
    other_code = link_code(harness, second)
    claim = harness.bot(
        "/v1/bot/telegram/links/claim", {"code": other_code, "telegram_user_id": 501}
    )
    assert claim.status_code == 409
    assert claim.json()["error"] == "identity_in_use"


def test_bot_unlink(harness):
    token = harness.email_session("anna@example.ru")
    code = link_code(harness, token)
    harness.bot("/v1/bot/telegram/links/confirm", {"code": code, "telegram_user_id": 501})
    first = harness.bot("/v1/bot/telegram/unlink", {"telegram_user_id": 501})
    assert first.json() == {"status": "unlinked"}
    second = harness.bot("/v1/bot/telegram/unlink", {"telegram_user_id": 501})
    assert second.json() == {"status": "not_linked"}


def test_telegram_disabled(env):
    del env["TELEGRAM_BOT_USERNAME"]
    harness = Harness(env)
    try:
        token = harness.email_session("anna@example.ru")
        response = harness.web("POST", "/v1/me/links/telegram", session=token)
        assert response.json()["error"] == "provider_disabled"
    finally:
        harness.close()
