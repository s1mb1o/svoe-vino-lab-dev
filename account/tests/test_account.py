from __future__ import annotations


def test_unlink_keeps_one_login_method(harness):
    token = harness.email_session("anna@example.ru")
    last = harness.web("DELETE", "/v1/me/identities/email", session=token)
    assert last.status_code == 409
    assert last.json()["error"] == "last_login_method"
    harness.yandex_login("777", session=token, purpose="link")
    assert harness.web("DELETE", "/v1/me/identities/email", session=token).status_code == 204
    missing = harness.web("DELETE", "/v1/me/identities/email", session=token)
    assert missing.json()["error"] == "not_linked"


def test_an_old_session_can_delete_the_account(harness):
    # No recent-login rule: the page asks for a confirmation instead.
    token = harness.email_session("anna@example.ru")
    harness.clock.advance(30 * 86400)
    assert harness.web("DELETE", "/v1/me", session=token).status_code == 204


def test_account_deletion_removes_everything(harness):
    token = harness.email_session("anna@example.ru")
    harness.yandex_login("777", session=token, purpose="link")
    assert harness.web("DELETE", "/v1/me", session=token).status_code == 204
    assert harness.web("GET", "/v1/me", session=token).status_code == 401
    again = harness.yandex_login("777").json()
    assert again["status"] == "signup_required"
    fresh = harness.email_session("anna@example.ru", username="anna_wine")
    me = harness.web("GET", "/v1/me", session=fresh).json()
    assert [i["provider"] for i in me["user"]["identities"]] == ["email"]
