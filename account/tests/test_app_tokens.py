from __future__ import annotations

import logging
import re
import sqlite3

from conftest import WEB_TOKEN

TOKEN_FORMAT = re.compile(r"^cvpat_[A-Za-z0-9_-]{43}$")


def create(harness, session, name="Claude на ноутбуке", days=90):
    return harness.web(
        "POST", "/v1/me/app-tokens", session=session, json={"name": name, "lifetime_days": days}
    )


def app(harness, path, token, ip="203.0.113.7"):
    headers = {"Authorization": f"Bearer {WEB_TOKEN}", "X-Client-IP": ip, "X-App-Token": token}
    return harness.client.get(path, headers=headers)


def test_create_shows_the_token_once_and_stores_only_its_hash(harness, env):
    session = harness.email_session("anna@example.ru")
    response = create(harness, session)
    assert response.status_code == 201, response.text
    body = response.json()
    assert TOKEN_FORMAT.match(body["token"])
    assert body["app_token"]["name"] == "Claude на ноутбуке"
    assert body["app_token"]["last_used_at"] is None
    listed = harness.web("GET", "/v1/me/app-tokens", session=session).json()["tokens"]
    assert [item["id"] for item in listed] == [body["app_token"]["id"]]
    assert "token" not in listed[0]
    with sqlite3.connect(env["ACCOUNT_DATABASE"]) as db:
        dump = "\n".join(db.iterdump())
    assert body["token"] not in dump


def test_a_token_reads_only_its_owner_profile(harness):
    session = harness.email_session("anna@example.ru")
    token = create(harness, session).json()["token"]
    harness.email_session("other@example.ru", username="other")
    profile = app(harness, "/v1/app/profile", token)
    assert profile.status_code == 200
    body = profile.json()
    assert body == {"username": "anna_wine", "created_at": body["created_at"], "preferences": None}
    assert "anna@example.ru" not in profile.text
    wines = app(harness, "/v1/app/wines?limit=50", token)
    assert wines.json() == {"items": [], "next_cursor": None}


def test_an_old_session_can_create_a_token(harness):
    session = harness.email_session("anna@example.ru")
    harness.clock.advance(30 * 86400)
    assert create(harness, session).status_code == 201


def test_a_sixth_active_token_is_refused(harness):
    session = harness.email_session("anna@example.ru")
    for number in range(5):
        assert create(harness, session, name=f"t{number}").status_code == 201
    sixth = create(harness, session, name="t5")
    assert sixth.status_code == 409
    assert sixth.json()["error"] == "too_many_tokens"


def test_lifetime_and_name_rules(harness):
    session = harness.email_session("anna@example.ru")
    assert create(harness, session, days=7).status_code == 422
    assert create(harness, session, name="   ").json()["error"] == "invalid_name"
    assert create(harness, session, name="a\x07b").json()["error"] == "invalid_name"
    assert create(harness, session, name="x" * 65).json()["error"] == "invalid_name"
    created = create(harness, session, name="  two   words ", days=30).json()["app_token"]
    assert created["name"] == "two words"


def test_refusals_are_the_same_401(harness):
    session = harness.email_session("anna@example.ru")
    revoked = create(harness, session, name="revoked").json()
    harness.web("DELETE", f"/v1/me/app-tokens/{revoked['app_token']['id']}", session=session)
    expiring = create(harness, session, name="short", days=30).json()["token"]
    harness.clock.advance(30 * 86400 + 1)
    for token in ("", "cvpat_short", "cvpat_" + "A" * 43, revoked["token"], expiring, session):
        response = app(harness, "/v1/app/profile", token)
        assert response.status_code == 401
        assert response.json()["error"] == "app_token_invalid"


def test_account_deletion_ends_the_tokens(harness):
    session = harness.email_session("anna@example.ru")
    token = create(harness, session).json()["token"]
    assert harness.web("DELETE", "/v1/me", session=session).status_code == 204
    assert app(harness, "/v1/app/profile", token).json()["error"] == "app_token_invalid"


def test_logout_keeps_the_tokens(harness):
    session = harness.email_session("anna@example.ru")
    token = create(harness, session).json()["token"]
    harness.web("DELETE", "/v1/sessions/current", session=session)
    assert app(harness, "/v1/app/profile", token).status_code == 200


def test_a_token_is_not_a_session_and_cannot_manage_tokens(harness):
    session = harness.email_session("anna@example.ru")
    token = create(harness, session).json()["token"]
    for method, path in (
        ("GET", "/v1/me"),
        ("GET", "/v1/me/app-tokens"),
        ("POST", "/v1/me/app-tokens"),
    ):
        response = harness.web(method, path, session=token, json={"name": "x"})
        assert response.status_code == 401, path
    headers = {
        "Authorization": f"Bearer {WEB_TOKEN}",
        "X-Client-IP": "203.0.113.7",
        "X-App-Token": token,
    }
    assert harness.client.get("/v1/me", headers=headers).status_code == 401


def test_revoke_only_own_tokens(harness):
    first = harness.email_session("anna@example.ru")
    token_id = create(harness, first).json()["app_token"]["id"]
    second = harness.email_session("other@example.ru", username="other")
    other = harness.web("DELETE", f"/v1/me/app-tokens/{token_id}", session=second)
    assert other.status_code == 404
    assert harness.web("DELETE", f"/v1/me/app-tokens/{token_id}", session=first).status_code == 204
    assert harness.web("GET", "/v1/me/app-tokens", session=first).json() == {"tokens": []}


def test_the_61st_request_in_a_minute_is_limited(harness):
    session = harness.email_session("anna@example.ru")
    token = create(harness, session).json()["token"]
    for _ in range(60):
        assert app(harness, "/v1/app/profile", token).status_code == 200
    limited = app(harness, "/v1/app/profile", token)
    assert limited.status_code == 429
    assert int(limited.headers["retry-after"]) >= 1
    harness.clock.advance(61)
    assert app(harness, "/v1/app/profile", token).status_code == 200


def test_failed_checks_are_limited_per_client(harness):
    for _ in range(20):
        assert app(harness, "/v1/app/profile", "cvpat_wrong", ip="203.0.113.9").status_code == 401
    assert app(harness, "/v1/app/profile", "cvpat_wrong", ip="203.0.113.9").status_code == 429
    assert app(harness, "/v1/app/profile", "cvpat_wrong", ip="203.0.113.10").status_code == 401


def test_last_use_is_written_at_most_once_a_minute(harness):
    session = harness.email_session("anna@example.ru")
    token = create(harness, session).json()["token"]
    app(harness, "/v1/app/profile", token)
    first = harness.web("GET", "/v1/me/app-tokens", session=session).json()["tokens"][0]
    harness.clock.advance(30)
    app(harness, "/v1/app/profile", token)
    second = harness.web("GET", "/v1/me/app-tokens", session=session).json()["tokens"][0]
    assert first["last_used_at"] == second["last_used_at"]
    harness.clock.advance(31)
    app(harness, "/v1/app/profile", token)
    third = harness.web("GET", "/v1/me/app-tokens", session=session).json()["tokens"][0]
    assert third["last_used_at"] != first["last_used_at"]


def test_wines_validates_its_query(harness):
    session = harness.email_session("anna@example.ru")
    token = create(harness, session).json()["token"]
    assert app(harness, "/v1/app/wines?limit=51", token).status_code == 422
    assert app(harness, "/v1/app/wines?cursor=a%20b", token).status_code == 422


def test_no_token_in_the_logs(harness, caplog):
    caplog.set_level(logging.DEBUG)
    session = harness.email_session("anna@example.ru")
    token = create(harness, session).json()["token"]
    app(harness, "/v1/app/profile", token)
    app(harness, "/v1/app/profile", token[:-1] + "x")
    assert token not in caplog.text
    assert token[6:] not in caplog.text


def test_ipv6_clients_share_the_limit_of_their_64(harness):
    for number in range(20):
        response = app(harness, "/v1/app/profile", "cvpat_wrong", ip=f"2001:db8:1:2::{number + 1}")
        assert response.status_code == 401
    same_network = app(harness, "/v1/app/profile", "cvpat_wrong", ip="2001:db8:1:2::ffff")
    assert same_network.status_code == 429
    assert app(harness, "/v1/app/profile", "cvpat_wrong", ip="2001:db8:1:3::1").status_code == 401


def test_a_global_budget_limits_failures_from_many_addresses(harness):
    for number in range(600):
        ip = f"198.51.{number // 250}.{number % 250 + 1}"
        assert app(harness, "/v1/app/profile", "cvpat_wrong", ip=ip).status_code == 401
    assert app(harness, "/v1/app/profile", "cvpat_wrong", ip="203.0.113.200").status_code == 429
    harness.clock.advance(61)
    assert app(harness, "/v1/app/profile", "cvpat_wrong", ip="203.0.113.200").status_code == 401
