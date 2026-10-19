from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from conftest import REDIRECT_URI, Harness


def test_authorize_url_uses_pkce_and_state(harness):
    start = harness.web("POST", "/v1/auth/yandex/start", json={"redirect_uri": REDIRECT_URI})
    url = urlparse(start.json()["authorize_url"])
    query = parse_qs(url.query)
    assert url.netloc == "oauth.yandex.ru" and url.path == "/authorize"
    assert query["response_type"] == ["code"]
    assert query["client_id"] == ["yandex-client"]
    assert query["redirect_uri"] == [REDIRECT_URI]
    assert query["code_challenge_method"] == ["S256"]
    assert len(query["state"][0]) >= 40
    assert "scope" not in query


def test_new_yandex_user_signs_up_then_logs_in(harness):
    first = harness.yandex_login("1130000012345").json()
    assert first["status"] == "signup_required"
    assert first["provider"] == "yandex"
    assert "email" not in first
    created = harness.signup(first["signup_ticket"], "yandex_person").json()
    assert created["session"]["auth_method"] == "yandex"
    assert [i["provider"] for i in created["user"]["identities"]] == ["yandex"]
    again = harness.yandex_login("1130000012345").json()
    assert again["status"] == "session"
    assert again["user"]["username"] == "yandex_person"
    token_request = next(r for r in harness.yandex_server.requests if r.url.path == "/token")
    assert b"redirect_uri" not in token_request.content


def test_state_mismatch_and_flow_reuse(harness):
    start = harness.web("POST", "/v1/auth/yandex/start", json={"redirect_uri": REDIRECT_URI})
    flow = start.json()["flow_id"]
    harness.yandex_server.authorize(start.json()["authorize_url"], "42")
    wrong = harness.web(
        "POST",
        "/v1/auth/yandex/finish",
        json={"flow_id": flow, "state": "forged", "code": "yandex-code"},
    )
    assert wrong.json()["error"] == "invalid_flow"
    reused = harness.web(
        "POST",
        "/v1/auth/yandex/finish",
        json={"flow_id": flow, "state": "forged", "code": "yandex-code"},
    )
    assert reused.json()["error"] == "invalid_flow"


def test_flow_expires(harness):
    start = harness.web("POST", "/v1/auth/yandex/start", json={"redirect_uri": REDIRECT_URI})
    state = harness.yandex_server.authorize(start.json()["authorize_url"], "42")
    harness.clock.advance(601)
    response = harness.web(
        "POST",
        "/v1/auth/yandex/finish",
        json={"flow_id": start.json()["flow_id"], "state": state, "code": "yandex-code"},
    )
    assert response.json()["error"] == "invalid_flow"


def test_unregistered_redirect_uri(harness):
    response = harness.web(
        "POST", "/v1/auth/yandex/start", json={"redirect_uri": "https://evil.example/cb"}
    )
    assert response.json()["error"] == "invalid_redirect_uri"


def test_provider_failures(harness):
    harness.yandex_server.fail_with = 503
    unavailable = harness.yandex_login("42")
    assert unavailable.status_code == 502
    assert unavailable.json()["error"] == "provider_unavailable"
    harness.yandex_server.fail_with = 400
    rejected = harness.yandex_login("42")
    assert rejected.status_code == 400
    assert rejected.json()["error"] == "provider_rejected"


def test_link_yandex_to_email_account(harness):
    token = harness.email_session("anna@example.ru")
    linked = harness.yandex_login("777", session=token, purpose="link").json()
    assert linked["status"] == "linked"
    assert {i["provider"] for i in linked["user"]["identities"]} == {"email", "yandex"}
    login = harness.yandex_login("777").json()
    assert login["status"] == "session"
    assert login["user"]["username"] == "anna_wine"


def test_yandex_identity_of_another_account_is_not_linked(harness):
    first = harness.yandex_login("777").json()
    harness.signup(first["signup_ticket"], "first_user")
    token = harness.email_session("anna@example.ru")
    response = harness.yandex_login("777", session=token, purpose="link")
    assert response.status_code == 409
    assert response.json()["error"] == "identity_in_use"


def test_yandex_disabled_without_client_id(env):
    del env["YANDEX_CLIENT_ID"]
    harness = Harness(env)
    try:
        response = harness.web(
            "POST", "/v1/auth/yandex/start", json={"redirect_uri": REDIRECT_URI}
        )
        assert response.status_code == 404
        assert response.json()["error"] == "provider_disabled"
    finally:
        harness.close()
