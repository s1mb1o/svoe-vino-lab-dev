from __future__ import annotations

import io
import re
import sys
from urllib.parse import quote

import pytest
from conftest import CLIENT_IP, MAX_TOKEN, START, Harness, init_data

from chto_za_vino_account import cli, max_launch


def test_signature_check():
    key = max_launch.derive_key(MAX_TOKEN)
    launch = max_launch.verify(init_data(), key)
    assert launch.user_id == "777"
    assert launch.ip == CLIENT_IP
    assert launch.first_name == "Анна"
    with pytest.raises(max_launch.LaunchInvalid):
        max_launch.verify(init_data(token="another-bot-token"), key)
    tampered = init_data().replace("777", "778")
    with pytest.raises(max_launch.LaunchInvalid):
        max_launch.verify(tampered, key)
    with pytest.raises(max_launch.LaunchInvalid):
        max_launch.verify(init_data() + "&hash=00", key)
    with pytest.raises(max_launch.LaunchInvalid):
        max_launch.verify(init_data().rsplit("&hash=", 1)[0], key)


def test_link_max_to_account(harness):
    token = harness.email_session("anna@example.ru")
    linked = harness.web(
        "POST", "/v1/me/identities/max", session=token, json={"init_data": init_data()}
    )
    assert linked.status_code == 200, linked.text
    assert {i["provider"] for i in linked.json()["user"]["identities"]} == {"email", "max"}


def test_launch_checks(harness):
    token = harness.email_session("anna@example.ru")

    def link(data, ip=CLIENT_IP):
        return harness.web(
            "POST", "/v1/me/identities/max", session=token, ip=ip, json={"init_data": data}
        ).json()

    assert link(init_data(), ip="198.51.100.1")["error"] == "launch_ip_mismatch"
    assert link(init_data(ip=None))["error"] == "launch_ip_mismatch"
    assert link(init_data(auth_date=int(START) - 301))["error"] == "launch_expired"
    assert link(init_data(auth_date=int(START) + 200))["error"] == "launch_expired"
    assert link(init_data(token="wrong"))["error"] == "invalid_launch"
    assert link(init_data())["status"] == "linked"
    assert link(init_data())["error"] == "launch_reused"


def test_launch_date_in_milliseconds(harness, caplog):
    token = harness.email_session("anna@example.ru")

    def link(data):
        return harness.web(
            "POST", "/v1/me/identities/max", session=token, json={"init_data": data}
        ).json()

    with caplog.at_level("INFO", logger="chto_za_vino_account"):
        assert link(init_data(auth_date=int(START) - 4000))["error"] == "launch_expired"
    assert re.search(r"MAX launch refused: expired, age 40\d\d s", caplog.text)
    assert "query-1" not in caplog.text
    assert link(init_data(auth_date=int(START) * 1000))["status"] == "linked"


def test_launch_forms_of_max_clients(harness):
    token = harness.email_session("anna@example.ru")
    key = max_launch.derive_key(MAX_TOKEN)
    plain = init_data(query_id="query-fragment")
    fragment = "WebAppData=" + quote(plain, safe="") + "&WebAppPlatform=web&WebAppVersion=26.2.8"
    assert max_launch.verify(fragment, key).query_id == "query-fragment"
    assert max_launch.verify("#" + fragment, key).query_id == "query-fragment"
    encoded = quote(init_data(query_id="query-encoded"), safe="")
    assert max_launch.verify(encoded, key).query_id == "query-encoded"
    with pytest.raises(max_launch.LaunchInvalid, match=r"no hash \(keys: WebAppPlatform, a\)"):
        max_launch.verify("a=1&WebAppPlatform=web", key)
    linked = harness.web(
        "POST", "/v1/me/identities/max", session=token, json={"init_data": fragment}
    ).json()
    assert linked["status"] == "linked"


def test_ip_check_can_be_turned_off(env):
    env["MAX_REQUIRE_IP_MATCH"] = "false"
    harness = Harness(env)
    try:
        token = harness.email_session("anna@example.ru")
        response = harness.web(
            "POST",
            "/v1/me/identities/max",
            session=token,
            json={"init_data": init_data(ip=None)},
        )
        assert response.json()["status"] == "linked"
    finally:
        harness.close()


def test_max_identity_of_another_account(harness):
    first = harness.email_session("anna@example.ru")
    harness.web("POST", "/v1/me/identities/max", session=first, json={"init_data": init_data()})
    second = harness.email_session("other@example.ru", username="other")
    response = harness.web(
        "POST",
        "/v1/me/identities/max",
        session=second,
        json={"init_data": init_data(query_id="query-2")},
    )
    assert response.status_code == 409
    assert response.json()["error"] == "identity_in_use"


def test_max_login_is_off_by_default(harness):
    response = harness.web("POST", "/v1/auth/max/session", json={"init_data": init_data()})
    assert response.status_code == 404
    assert response.json()["error"] == "provider_disabled"


def test_max_login_when_enabled(env):
    env["MAX_LOGIN_ENABLED"] = "true"
    harness = Harness(env)
    try:
        unknown = harness.web("POST", "/v1/auth/max/session", json={"init_data": init_data()})
        assert unknown.json() == {"status": "not_linked"}
        token = harness.email_session("anna@example.ru")
        harness.web(
            "POST",
            "/v1/me/identities/max",
            session=token,
            json={"init_data": init_data(query_id="query-2")},
        )
        session = harness.web(
            "POST", "/v1/auth/max/session", json={"init_data": init_data(query_id="query-3")}
        ).json()
        assert session["status"] == "session"
        assert session["session"]["auth_method"] == "max"
        max_token = session["session"]["token"]
        harness.clock.advance(86401)
        assert harness.web("GET", "/v1/me", session=max_token).status_code == 401
    finally:
        harness.close()


def test_max_key_command(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO(MAX_TOKEN + "\n"))
    assert cli.main(["max-key"]) == 0
    assert capsys.readouterr().out.strip() == max_launch.derive_key(MAX_TOKEN).hex()
