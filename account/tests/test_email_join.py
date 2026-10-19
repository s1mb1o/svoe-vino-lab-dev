"""Accounts with the same email join (owner request, 2026-10-19, issue #48)."""

from __future__ import annotations

import sqlite3
from typing import Any

from conftest import Harness

from chto_za_vino_account.cli import merge


def identities(harness: Harness, token: str) -> dict[str, Any]:
    me = harness.web("GET", "/v1/me", session=token)
    assert me.status_code == 200, me.text
    return {item["provider"]: item for item in me.json()["user"]["identities"]}


def email_login(harness: Harness, email: str) -> Any:
    start = harness.web("POST", "/v1/auth/email/start", json={"email": email})
    assert start.status_code == 200, start.text
    return harness.web(
        "POST",
        "/v1/auth/email/verify",
        json={"challenge_id": start.json()["challenge_id"], "code": harness.last_code()},
    )


def test_yandex_login_joins_the_account_with_the_same_email(harness: Harness) -> None:
    token = harness.email_session("Owner@Yandex.ru", "alex")
    harness.yandex_server.emails["5551"] = "owner@yandex.RU"
    result = harness.yandex_login("5551")
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["status"] == "session"
    assert body["user"]["username"] == "alex"
    assert set(identities(harness, token)) == {"email", "yandex"}


def test_email_login_joins_the_account_of_a_yandex_identity(harness: Harness) -> None:
    harness.yandex_server.emails["5552"] = "s1mb1o@yandex.ru"
    first = harness.yandex_login("5552")
    assert first.json()["status"] == "signup_required"
    created = harness.signup(first.json()["signup_ticket"], "alex")
    assert created.status_code == 200, created.text
    harness.clock.advance(61)
    joined = email_login(harness, "S1MB1O@yandex.ru")
    assert joined.status_code == 200, joined.text
    assert joined.json()["status"] == "session"
    assert joined.json()["user"]["username"] == "alex"
    assert set(identities(harness, joined.json()["session"]["token"])) == {"email", "yandex"}


def test_a_different_email_still_signs_up(harness: Harness) -> None:
    harness.email_session("anna@example.com", "anna")
    harness.yandex_server.emails["5553"] = "other@example.com"
    assert harness.yandex_login("5553").json()["status"] == "signup_required"


def test_no_email_from_yandex_still_signs_up(harness: Harness) -> None:
    harness.email_session("anna@example.com", "anna")
    assert harness.yandex_login("5554").json()["status"] == "signup_required"


def test_no_join_when_the_account_has_another_yandex_identity(harness: Harness) -> None:
    harness.yandex_server.emails["5555"] = "anna@example.com"
    harness.yandex_server.emails["5556"] = "anna@example.com"
    token = harness.email_session("anna@example.com", "anna")
    assert harness.yandex_login("5555").json()["status"] == "session"
    assert harness.yandex_login("5556").json()["status"] == "signup_required"
    assert identities(harness, token)["yandex"]


def test_no_join_when_two_accounts_have_the_email(harness: Harness, env: dict[str, str]) -> None:
    harness.email_session("anna@example.com", "anna")
    harness.yandex_server.emails["5557"] = "other@example.com"
    ticket = harness.yandex_login("5557").json()["signup_ticket"]
    assert harness.signup(ticket, "anna2").status_code == 200
    db = sqlite3.connect(env["ACCOUNT_DATABASE"])
    db.execute("UPDATE identities SET email = 'anna@example.com' WHERE provider = 'yandex'")
    db.commit()
    db.close()
    harness.yandex_server.emails["5558"] = "anna@example.com"
    assert harness.yandex_login("5558").json()["status"] == "signup_required"


def test_the_operator_merge_joins_two_accounts(harness: Harness, env: dict[str, str]) -> None:
    yandex_first = harness.yandex_login("5559").json()
    assert harness.signup(yandex_first["signup_ticket"], "alex").status_code == 200
    harness.clock.advance(61)
    harness.email_session("s1mb1o@yandex.ru", "alex22")
    assert merge(env["ACCOUNT_DATABASE"], "alex", "alex22") == 0
    db = sqlite3.connect(env["ACCOUNT_DATABASE"])
    rows = db.execute(
        "SELECT u.username, i.provider FROM identities i JOIN users u ON u.id = i.user_id "
        "ORDER BY i.provider"
    ).fetchall()
    users = [row[0] for row in db.execute("SELECT username FROM users")]
    sessions = db.execute(
        "SELECT count(*) FROM sessions s JOIN users u ON u.id = s.user_id "
        "WHERE u.username = 'alex22'"
    ).fetchone()[0]
    db.close()
    assert rows == [("alex", "email"), ("alex", "yandex")]
    assert users == ["alex"]
    assert sessions == 0
    harness.clock.advance(61)
    again = email_login(harness, "s1mb1o@yandex.ru")
    assert again.json()["user"]["username"] == "alex"


def test_the_operator_merge_refuses_a_provider_clash(harness: Harness, env: dict[str, str]) -> None:
    harness.email_session("a@example.com", "anna")
    harness.clock.advance(61)
    harness.email_session("b@example.com", "boris")
    assert merge(env["ACCOUNT_DATABASE"], "anna", "boris") == 1
    db = sqlite3.connect(env["ACCOUNT_DATABASE"])
    assert db.execute("SELECT count(*) FROM users").fetchone()[0] == 2
    db.close()
    assert merge(env["ACCOUNT_DATABASE"], "anna", "nobody") == 1
