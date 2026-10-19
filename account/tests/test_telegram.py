from __future__ import annotations

from conftest import Harness


def link_code(harness, token):
    response = harness.web("POST", "/v1/me/links/telegram", session=token)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["deep_link"] == f"https://t.me/ChtoZaVinoBot?start=link_{body['code']}"
    assert len("link_" + body["code"]) <= 64
    return body["code"]


def link(harness, token, telegram_user_id=501):
    code = link_code(harness, token)
    claim = harness.bot(
        "/v1/bot/telegram/links/claim", {"code": code, "telegram_user_id": telegram_user_id}
    )
    assert claim.status_code == 200, claim.text
    confirm = harness.bot(
        "/v1/bot/telegram/links/confirm", {"code": code, "telegram_user_id": telegram_user_id}
    )
    assert confirm.json()["status"] == "linked"
    return code


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
    # A second tap of the same person gets the same answer.
    repeated = harness.bot(
        "/v1/bot/telegram/links/confirm", {"code": code, "telegram_user_id": 501}
    )
    assert repeated.json() == {"status": "linked", "username": "anna_wine"}
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
    link(harness, first)
    second = harness.email_session("other@example.ru", username="other")
    other_code = link_code(harness, second)
    claim = harness.bot(
        "/v1/bot/telegram/links/claim", {"code": other_code, "telegram_user_id": 501}
    )
    assert claim.status_code == 409
    assert claim.json()["error"] == "identity_in_use"


def test_bot_unlink(harness):
    token = harness.email_session("anna@example.ru")
    link(harness, token)
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


def test_site_unlink_of_a_messenger_needs_no_recent_login(harness):
    token = harness.email_session("anna@example.ru")
    link(harness, token)
    harness.clock.advance(15 * 60)
    response = harness.web("DELETE", "/v1/me/identities/telegram", session=token)
    assert response.status_code == 204
    me = harness.web("GET", "/v1/me", session=token).json()
    assert {i["provider"] for i in me["user"]["identities"]} == {"email"}


def test_site_unlink_of_a_login_method_needs_no_recent_login(harness):
    token = harness.email_session("anna@example.ru")
    harness.yandex_login("777", session=token, purpose="link")
    harness.clock.advance(30 * 86400)
    response = harness.web("DELETE", "/v1/me/identities/yandex", session=token)
    assert response.status_code == 204


def test_a_code_belongs_to_the_first_claimer(harness):
    token = harness.email_session("anna@example.ru")
    code = link_code(harness, token)
    assert harness.bot(
        "/v1/bot/telegram/links/claim", {"code": code, "telegram_user_id": 501}
    ).status_code == 200
    for path in ("claim", "confirm"):
        other = harness.bot(
            f"/v1/bot/telegram/links/{path}", {"code": code, "telegram_user_id": 502}
        )
        assert other.json()["error"] == "invalid_link_code"
    me = harness.web("GET", "/v1/me", session=token).json()
    assert {i["provider"] for i in me["user"]["identities"]} == {"email"}


def test_confirm_needs_a_claim(harness):
    token = harness.email_session("anna@example.ru")
    code = link_code(harness, token)
    response = harness.bot(
        "/v1/bot/telegram/links/confirm", {"code": code, "telegram_user_id": 501}
    )
    assert response.json()["error"] == "invalid_link_code"


def test_a_new_code_replaces_the_open_one(harness):
    token = harness.email_session("anna@example.ru")
    old = link_code(harness, token)
    link_code(harness, token)
    response = harness.bot("/v1/bot/telegram/links/claim", {"code": old, "telegram_user_id": 501})
    assert response.json()["error"] == "invalid_link_code"


def test_a_used_code_does_not_answer_after_unlink(harness):
    token = harness.email_session("anna@example.ru")
    code = link(harness, token)
    harness.bot("/v1/bot/telegram/unlink", {"telegram_user_id": 501})
    response = harness.bot(
        "/v1/bot/telegram/links/confirm", {"code": code, "telegram_user_id": 501}
    )
    assert response.json()["error"] == "invalid_link_code"


def test_an_old_session_can_start_a_link(harness):
    token = harness.email_session("anna@example.ru")
    harness.clock.advance(30 * 86400)
    response = harness.web("POST", "/v1/me/links/telegram", session=token)
    assert response.status_code == 200
