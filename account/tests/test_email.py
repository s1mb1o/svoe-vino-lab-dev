from __future__ import annotations

import pytest
from conftest import WEB_TOKEN, Harness

from chto_za_vino_account.config import Settings
from chto_za_vino_account.mailer import build_message


def start(harness, email="Anna@Example.ru", **kwargs):
    return harness.web("POST", "/v1/auth/email/start", json={"email": email}, **kwargs)


def verify(harness, challenge_id, code, **kwargs):
    return harness.web(
        "POST",
        "/v1/auth/email/verify",
        json={"challenge_id": challenge_id, "code": code},
        **kwargs,
    )


def test_test_code_opens_the_email_login_of_any_address(env, caplog):
    env["ACCOUNT_TEST_CODE"] = "111111"
    harness = Harness(env)
    try:
        with caplog.at_level("WARNING", logger="chto_za_vino_account"):
            challenge = start(harness).json()["challenge_id"]
            assert harness.last_code() != "111111"
            result = verify(harness, challenge, "111111").json()
        assert result["status"] == "signup_required"
        assert "Email login with ACCOUNT_TEST_CODE" in caplog.text
        assert "anna@example.ru" not in caplog.text.lower()
        challenge = start(harness, email="boris@example.ru").json()["challenge_id"]
        wrong = verify(harness, challenge, "222222").json()
        assert wrong["error"] == "invalid_code"
    finally:
        harness.close()


def test_test_code_is_off_by_default_and_checked(harness, env):
    challenge = start(harness).json()["challenge_id"]
    if harness.last_code() != "111111":
        assert verify(harness, challenge, "111111").json()["error"] == "invalid_code"
    env["ACCOUNT_TEST_CODE"] = "11111a"
    with pytest.raises(ValueError, match="ACCOUNT_TEST_CODE"):
        Settings.from_env(env)


def test_code_mail_has_a_large_code_in_html(harness):
    start(harness)
    mail = harness.mailer.sent[-1]
    code = harness.last_code()
    grouped = f"{code[:3]} {code[3:]}"
    assert mail.subject == f"{grouped} — код для входа в «Винный дневник»"
    assert mail.html is not None
    assert f">{code[:3]}</span>" in mail.html and f">{code[3:]}</span>" in mail.html
    assert "font-size:40px" in mail.html
    assert "<img" not in mail.html and "href=" not in mail.html
    message = build_message(mail, "noreply@chtozavino.ru")
    assert message.get_content_type() == "multipart/alternative"
    assert [part.get_content_type() for part in message.iter_parts()] == ["text/plain", "text/html"]


def test_new_email_signs_up_and_gets_a_session(harness):
    challenge = start(harness).json()["challenge_id"]
    mail = harness.mailer.sent[-1]
    assert mail.to == "anna@example.ru"
    assert "Никому не сообщайте этот код" in mail.text
    result = verify(harness, challenge, harness.last_code()).json()
    assert result["status"] == "signup_required"
    assert result["email"] == "anna@example.ru"
    created = harness.signup(result["signup_ticket"], "Anna_Wine").json()
    assert created["status"] == "session"
    assert created["user"]["username"] == "anna_wine"
    assert created["user"]["identities"][0] == {
        "provider": "email",
        "linked_at": "2027-01-15T08:00:00Z",
        "email": "anna@example.ru",
    }
    me = harness.web("GET", "/v1/me", session=created["session"]["token"]).json()
    assert me["session"]["auth_method"] == "email"


def test_known_email_logs_in_without_signup(harness):
    harness.email_session("anna@example.ru")
    challenge = start(harness).json()["challenge_id"]
    result = verify(harness, challenge, harness.last_code()).json()
    assert result["status"] == "session"
    assert result["user"]["username"] == "anna_wine"


def test_code_works_once(harness):
    challenge = start(harness).json()["challenge_id"]
    code = harness.last_code()
    assert verify(harness, challenge, code).status_code == 200
    again = verify(harness, challenge, code)
    assert again.status_code == 400
    assert again.json()["error"] == "invalid_challenge"


def test_wrong_codes_lock_the_challenge(harness):
    challenge = start(harness).json()["challenge_id"]
    code = harness.last_code()
    wrong = "000000" if code != "000000" else "111111"
    for left in (4, 3, 2, 1, 0):
        response = verify(harness, challenge, wrong)
        assert response.json() == {
            "error": "invalid_code",
            "detail": "The code is wrong",
            "attempts_left": left,
        }
    locked = verify(harness, challenge, code)
    assert locked.status_code == 429
    assert locked.json()["error"] == "too_many_attempts"


def test_code_expires_after_ten_minutes(harness):
    challenge = start(harness).json()["challenge_id"]
    harness.clock.advance(601)
    response = verify(harness, challenge, harness.last_code())
    assert response.json()["error"] == "invalid_challenge"


def test_unknown_challenge_is_rejected(harness):
    response = verify(harness, "z" * 43, "123456")
    assert response.json()["error"] == "invalid_challenge"


def test_send_limits(harness):
    assert start(harness).status_code == 200
    soon = start(harness)
    assert soon.status_code == 429
    assert int(soon.headers["retry-after"]) <= 60
    harness.clock.advance(61)
    assert start(harness).status_code == 200
    harness.clock.advance(61)
    assert start(harness).status_code == 200
    harness.clock.advance(61)
    hourly = start(harness)
    assert hourly.status_code == 429
    assert hourly.json()["error"] == "rate_limited"


def test_send_limit_per_client_address(harness):
    for number in range(20):
        assert start(harness, f"person{number}@example.ru").status_code == 200
    assert start(harness, "late@example.ru").status_code == 429
    assert start(harness, "late@example.ru", ip="198.51.100.9").status_code == 200


def test_invalid_email_and_missing_client_ip(harness):
    assert start(harness, "not-an-email").json()["error"] == "invalid_email"
    response = harness.client.post(
        "/v1/auth/email/start",
        json={"email": "anna@example.ru"},
        headers={"Authorization": f"Bearer {WEB_TOKEN}"},
    )
    assert response.json()["error"] == "client_ip_required"


def test_signup_rules(harness):
    challenge = start(harness).json()["challenge_id"]
    ticket = verify(harness, challenge, harness.last_code()).json()["signup_ticket"]
    assert harness.signup(ticket, "ab").json()["error"] == "invalid_username"
    assert harness.signup(ticket, "admin").json()["error"] == "username_reserved"
    outdated = harness.web(
        "POST",
        "/v1/auth/signup",
        json={
            "signup_ticket": ticket,
            "username": "anna",
            "consent_version": "consent-0",
            "terms_version": "terms-1",
        },
    )
    assert outdated.json()["error"] == "consent_outdated"
    harness.email_session("other@example.ru", username="taken_name")
    assert harness.signup(ticket, "taken_name").json()["error"] == "username_taken"
    assert harness.signup(ticket, "anna").status_code == 200
    assert harness.signup(ticket, "anna2").json()["error"] == "invalid_ticket"


def test_signup_ticket_expires(harness):
    challenge = start(harness).json()["challenge_id"]
    ticket = verify(harness, challenge, harness.last_code()).json()["signup_ticket"]
    harness.clock.advance(1801)
    assert harness.signup(ticket, "anna").json()["error"] == "invalid_ticket"


def test_logout_and_session_lifetime(harness):
    token = harness.email_session("anna@example.ru")
    assert harness.web("GET", "/v1/me", session=token).status_code == 200
    harness.clock.advance(29 * 86400)
    assert harness.web("GET", "/v1/me", session=token).status_code == 200
    harness.clock.advance(29 * 86400)
    assert harness.web("GET", "/v1/me", session=token).status_code == 200, "sliding expiry"
    assert harness.web("DELETE", "/v1/sessions/current", session=token).status_code == 204
    gone = harness.web("GET", "/v1/me", session=token)
    assert gone.status_code == 401
    assert gone.json()["error"] == "session_invalid"


def test_session_does_not_expire(harness):
    # Owner rule of 2026-10-19: a session ends only at logout or account deletion.
    token = harness.email_session("anna@example.ru")
    harness.clock.advance(400 * 86400)
    assert harness.web("GET", "/v1/me", session=token).status_code == 200
    harness.web("DELETE", "/v1/sessions/current", session=token)
    assert harness.web("GET", "/v1/me", session=token).status_code == 401


def test_link_email_to_account_changes_the_address(harness):
    token = harness.email_session("anna@example.ru")
    challenge = harness.web(
        "POST",
        "/v1/auth/email/start",
        session=token,
        json={"email": "new@example.ru", "purpose": "link"},
    ).json()["challenge_id"]
    assert "привязки" in harness.mailer.sent[-1].subject
    linked = verify(harness, challenge, harness.last_code(), session=token).json()
    assert linked["status"] == "linked"
    emails = [i.get("email") for i in linked["user"]["identities"]]
    assert emails == ["new@example.ru"]


def test_link_challenge_needs_the_same_session(harness):
    token = harness.email_session("anna@example.ru")
    other = harness.email_session("other@example.ru", username="other")
    challenge = harness.web(
        "POST",
        "/v1/auth/email/start",
        session=token,
        json={"email": "new@example.ru", "purpose": "link"},
    ).json()["challenge_id"]
    response = verify(harness, challenge, harness.last_code(), session=other)
    assert response.json()["error"] == "invalid_challenge"
    no_session = harness.web(
        "POST", "/v1/auth/email/start", json={"email": "x@example.ru", "purpose": "link"}
    )
    assert no_session.json()["error"] == "session_required"
