from __future__ import annotations

from conftest import TELEGRAM_TOKEN, WEB_TOKEN, Harness


def test_health_is_open_from_any_network(env):
    outside = Harness(env, client_host="198.51.100.20")
    try:
        assert outside.client.get("/healthz").json() == {"status": "ok"}
        assert outside.client.get("/readyz").status_code == 200
        response = outside.web("GET", "/v1/config")
        assert response.status_code == 403
        assert response.json()["error"] == "forbidden"
    finally:
        outside.close()


def test_consumer_token_is_required(harness):
    assert harness.client.get("/v1/config").status_code == 401
    wrong = harness.client.get("/v1/config", headers={"Authorization": "Bearer " + "x" * 40})
    assert wrong.status_code == 401


def test_consumer_is_limited_to_its_routes(harness):
    bot_on_web = harness.client.get(
        "/v1/config", headers={"Authorization": f"Bearer {TELEGRAM_TOKEN}"}
    )
    assert bot_on_web.status_code == 403
    web_on_bot = harness.bot(
        "/v1/bot/telegram/unlink", {"telegram_user_id": 1}, token=WEB_TOKEN
    )
    assert web_on_bot.status_code == 403


def test_large_body_is_refused(harness):
    response = harness.client.post(
        "/v1/auth/email/start",
        content=b"x" * 20000,
        headers={"Authorization": f"Bearer {WEB_TOKEN}", "Content-Type": "text/plain"},
    )
    assert response.status_code == 413


def test_validation_errors_do_not_echo_input(harness):
    response = harness.web(
        "POST",
        "/v1/auth/email/verify",
        json={"challenge_id": "c" * 30, "code": "secret-value-123"},
    )
    assert response.status_code == 422
    assert response.json() == {"error": "invalid_request", "fields": ["code"]}
    assert "secret-value-123" not in response.text


def test_responses_are_not_cached(harness):
    response = harness.web("GET", "/v1/config")
    assert response.headers["cache-control"] == "no-store"
    config = response.json()
    assert config["providers"] == {
        "email": True,
        "yandex": True,
        "max_link": True,
        "max_login": False,
        "telegram_link": True,
    }
