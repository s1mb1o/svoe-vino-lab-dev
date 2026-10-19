"""Regressions for the Codex review of commit 64545eb5."""

from __future__ import annotations

import threading

import pytest
from conftest import REDIRECT_URI, WEB_TOKEN, Harness, init_data

from chto_za_vino_account import max_launch
from chto_za_vino_account.api import EmailVerify, MaxLaunch
from chto_za_vino_account.config import Settings
from chto_za_vino_account.limits import SlidingWindow, take_all
from chto_za_vino_account.mailer import Mail
from chto_za_vino_account.service import SessionIssued, SignupRequired

# Computed with OpenSSL, not with this package:
#   secret = HMAC-SHA256(key="WebAppData", msg=token)
#   hash   = HMAC-SHA256(key=secret, msg=sorted decoded pairs joined by "\n")
# The decoded last_name is "User+%41": decode once, keep "+".
VECTOR_TOKEN = "vector-bot-token-2026"
VECTOR_KEY = "a48ffa46ea2864b883dcedda1ee5a84e097a763ca05f67a386a4b444f1360946"
VECTOR_INIT_DATA = (
    "auth_date=1771409719"
    "&chat=%7B%22id%22%3A12345%2C%22type%22%3A%22DIALOG%22%7D"
    "&ip=192.168.0.1"
    "&query_id=4c0ab423-342b-4e45-aea4-2747dbc500cd"
    "&user=%7B%22id%22%3A67890%2C%22first_name%22%3A%22Max%22%2C%22last_name%22%3A"
    "%22User%2B%2541%22%2C%22username%22%3Anull%2C%22language_code%22%3A%22ru%22%2C"
    "%22photo_url%22%3Anull%7D"
    "&hash=6a31bd0761706bdd1f604b1b3f02637c0b2f9cb1cc3104238bdf7a83ff82dd74"
)


def test_published_algorithm_vector():
    assert max_launch.derive_key(VECTOR_TOKEN).hex() == VECTOR_KEY
    launch = max_launch.verify(VECTOR_INIT_DATA, bytes.fromhex(VECTOR_KEY))
    assert launch.user_id == "67890"
    assert launch.last_name == "User+%41"
    assert launch.ip == "192.168.0.1"
    reordered = "&".join(reversed(VECTOR_INIT_DATA.split("&")))
    assert max_launch.verify(reordered, bytes.fromhex(VECTOR_KEY)).user_id == "67890"


def test_stale_session_cannot_add_a_login_method(harness):
    token = harness.email_session("anna@example.ru")
    harness.clock.advance(16 * 60)
    email = harness.web(
        "POST",
        "/v1/auth/email/start",
        session=token,
        json={"email": "evil@example.ru", "purpose": "link"},
    )
    assert email.json()["error"] == "reauth_required"
    yandex = harness.web(
        "POST",
        "/v1/auth/yandex/start",
        session=token,
        json={"redirect_uri": REDIRECT_URI, "purpose": "link"},
    )
    assert yandex.json()["error"] == "reauth_required"
    launch = init_data(auth_date=int(harness.clock()))
    max_link = harness.web(
        "POST", "/v1/me/identities/max", session=token, json={"init_data": launch}
    )
    assert max_link.json()["error"] == "reauth_required"


def test_link_must_finish_while_the_login_is_recent(harness):
    token = harness.email_session("anna@example.ru")
    harness.clock.advance(13 * 60)
    challenge = harness.web(
        "POST",
        "/v1/auth/email/start",
        session=token,
        json={"email": "new@example.ru", "purpose": "link"},
    ).json()["challenge_id"]
    harness.clock.advance(3 * 60)
    response = harness.web(
        "POST",
        "/v1/auth/email/verify",
        session=token,
        json={"challenge_id": challenge, "code": harness.last_code()},
    )
    assert response.json()["error"] == "reauth_required"


def test_limits_are_checked_and_recorded_atomically():
    window = SlidingWindow(1, 60, lambda: 1000.0)
    barrier = threading.Barrier(8)
    results: list[int] = []

    def worker() -> None:
        barrier.wait()
        results.append(take_all(((window, "same"),)))

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert results.count(0) == 1


def test_yandex_start_needs_client_ip_and_is_limited(harness):
    missing = harness.client.post(
        "/v1/auth/yandex/start",
        json={"redirect_uri": REDIRECT_URI},
        headers={"Authorization": f"Bearer {WEB_TOKEN}"},
    )
    assert missing.json()["error"] == "client_ip_required"
    for _ in range(30):
        ok = harness.web("POST", "/v1/auth/yandex/start", json={"redirect_uri": REDIRECT_URI})
        assert ok.status_code == 200
    limited = harness.web("POST", "/v1/auth/yandex/start", json={"redirect_uri": REDIRECT_URI})
    assert limited.status_code == 429


def test_telegram_link_codes_are_limited(harness):
    token = harness.email_session("anna@example.ru")
    for _ in range(10):
        assert harness.web("POST", "/v1/me/links/telegram", session=token).status_code == 200
    limited = harness.web("POST", "/v1/me/links/telegram", session=token)
    assert limited.json()["error"] == "rate_limited"


def test_max_login_does_not_replace_email_or_yandex(env):
    env["MAX_LOGIN_ENABLED"] = "true"
    harness = Harness(env)
    try:
        token = harness.email_session("anna@example.ru")
        harness.web("POST", "/v1/me/identities/max", session=token, json={"init_data": init_data()})
        response = harness.web("DELETE", "/v1/me/identities/email", session=token)
        assert response.json()["error"] == "last_login_method"
    finally:
        harness.close()


def test_launch_id_is_kept_while_the_launch_is_valid(env):
    env["MAX_LOGIN_ENABLED"] = "true"
    env["MAX_INITDATA_MAX_AGE_SECONDS"] = "3600"
    harness = Harness(env)
    try:
        launch = init_data(auth_date=int(harness.clock()), query_id="long-lived")
        first = harness.web("POST", "/v1/auth/max/session", json={"init_data": launch})
        assert first.json() == {"status": "not_linked"}
        harness.clock.advance(3000)
        harness.client.app.state.service.purge()
        again = harness.web("POST", "/v1/auth/max/session", json={"init_data": launch})
        assert again.json()["error"] == "launch_reused"
    finally:
        harness.close()
    with pytest.raises(ValueError, match="3600"):
        Settings.from_env(dict(env, MAX_INITDATA_MAX_AGE_SECONDS="7200"))


def test_malformed_launch_encoding_is_a_normal_error(harness):
    token = harness.email_session("anna@example.ru")
    response = harness.web(
        "POST", "/v1/me/identities/max", session=token, json={"init_data": "user=%FF&hash=00"}
    )
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_launch"


def test_unknown_keys_are_not_echoed(harness):
    response = harness.web(
        "POST",
        "/v1/auth/email/verify",
        json={"challenge_id": "c" * 30, "code": "123456", "secret-value-in-key": 1},
    )
    assert response.json() == {"error": "invalid_request", "fields": ["unknown_field"]}
    assert "secret-value-in-key" not in response.text


def test_secret_bearing_objects_hide_secrets_in_repr():
    issued = SessionIssued("session-secret-token", 1, "email", "user-1")
    signup = SignupRequired("ticket-secret", "email", "anna@example.ru")
    mail = Mail("anna@example.ru", "Код", "Ваш код: 123456")
    verify = EmailVerify(challenge_id="challenge-secret-0000000", code="654321")
    launch = MaxLaunch(init_data="user=secret-launch-data")
    text = " ".join(repr(item) for item in (issued, signup, mail, verify, launch))
    for secret in (
        "session-secret-token",
        "ticket-secret",
        "anna@example.ru",
        "123456",
        "challenge-secret",
        "654321",
        "secret-launch-data",
    ):
        assert secret not in text, secret
