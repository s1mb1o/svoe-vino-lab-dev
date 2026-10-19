"""History records from the Telegram and MAX chats (plan 07, D8 and D13)."""

from __future__ import annotations

import logging

from conftest import MAX_BOT_TOKEN, TELEGRAM_TOKEN, WEB_TOKEN, Harness, init_data

TELEGRAM_USER = 987654321
MAX_USER = 777


def link_telegram(harness, session, telegram_user_id=TELEGRAM_USER):
    code = harness.web("POST", "/v1/me/links/telegram", session=session).json()["code"]
    body = {"code": code, "telegram_user_id": telegram_user_id}
    assert harness.bot("/v1/bot/telegram/links/claim", body).status_code == 200
    assert harness.bot("/v1/bot/telegram/links/confirm", body).json()["status"] == "linked"


def link_max(harness, session):
    response = harness.web(
        "POST",
        "/v1/me/identities/max",
        session=session,
        json={"init_data": init_data(user_id=MAX_USER)},
    )
    assert response.json()["status"] == "linked", response.text


def bot_record(harness, slug, user_id=TELEGRAM_USER, token=TELEGRAM_TOKEN, **extra):
    return harness.bot("/v1/bot/history", {"user_id": user_id, "slug": slug, **extra}, token=token)


def bot_undo(harness, slug, user_id=TELEGRAM_USER, token=TELEGRAM_TOKEN):
    return harness.bot("/v1/bot/history/undo", {"user_id": user_id, "slug": slug}, token=token)


def history(harness, session):
    return harness.web("GET", "/v1/me/history", session=session).json()["items"]


def test_a_linked_telegram_chat_records(harness):
    session = harness.email_session("anna@example.ru")
    link_telegram(harness, session)
    response = bot_record(harness, "wine-a", wine_snapshot={"name": "Вино", "color": "Белое"})
    assert response.status_code == 200, response.text
    assert response.json() == {"status": "recorded", "met_on": "2027-01-15"}
    assert bot_record(harness, "wine-a").json() == {"status": "already", "met_on": "2027-01-15"}
    items = history(harness, session)
    assert [(i["slug"], i["sources"], i["wine"]) for i in items] == [
        ("wine-a", ["telegram"], {"name": "Вино", "color": "Белое"})
    ]


def test_a_linked_max_chat_records(harness):
    session = harness.email_session("anna@example.ru")
    link_max(harness, session)
    response = bot_record(harness, "wine-a", user_id=MAX_USER, token=MAX_BOT_TOKEN)
    assert response.json() == {"status": "recorded", "met_on": "2027-01-15"}
    assert history(harness, session)[0]["sources"] == ["max"]
    # The consumer gives the messenger: the same number from the Telegram bot is another person.
    other = bot_record(harness, "wine-b", user_id=MAX_USER, token=TELEGRAM_TOKEN)
    assert other.json() == {"status": "not_linked"}
    undo = bot_undo(harness, "wine-a", user_id=MAX_USER, token=MAX_BOT_TOKEN)
    assert undo.json() == {"status": "removed"}


def test_the_first_source_of_the_day_stays(harness):
    session = harness.email_session("anna@example.ru")
    link_telegram(harness, session)
    site = {"slug": "wine-a", "source": "photo"}
    harness.web("POST", "/v1/me/history", session=session, json=site)
    assert bot_record(harness, "wine-a").json()["status"] == "already"
    assert history(harness, session)[0]["sources"] == ["photo"]


def test_a_chat_without_a_link(harness):
    harness.email_session("anna@example.ru")
    assert bot_record(harness, "wine-a").json() == {"status": "not_linked"}
    assert bot_undo(harness, "wine-a").json() == {"status": "not_linked"}
    max_chat = bot_record(harness, "wine-a", user_id=MAX_USER, token=MAX_BOT_TOKEN)
    assert max_chat.status_code == 200
    assert max_chat.json() == {"status": "not_linked"}


def test_the_switch_applies_to_the_chats(harness):
    session = harness.email_session("anna@example.ru")
    link_telegram(harness, session)
    harness.web("PATCH", "/v1/me", session=session, json={"save_history": False})
    assert bot_record(harness, "wine-a").json() == {"status": "off"}
    assert history(harness, session) == []
    harness.web("PATCH", "/v1/me", session=session, json={"save_history": True})
    assert bot_record(harness, "wine-a").json()["status"] == "recorded"


def test_undo_removes_the_date_of_today(harness):
    session = harness.email_session("anna@example.ru")
    link_telegram(harness, session)
    bot_record(harness, "wine-a")
    assert bot_undo(harness, "wine-a").json() == {"status": "removed"}
    assert history(harness, session) == []
    assert bot_undo(harness, "wine-a").json() == {"status": "absent"}
    # An earlier date stays: only today's date goes.
    bot_record(harness, "wine-b")
    harness.clock.advance(86400)
    bot_record(harness, "wine-b")
    assert bot_undo(harness, "wine-b").json() == {"status": "removed"}
    items = history(harness, session)
    assert [(i["slug"], i["days_count"], i["last_met_at"]) for i in items] == [
        ("wine-b", 1, "2027-01-15T08:01:01Z")
    ]
    assert bot_undo(harness, "wine-b").json() == {"status": "absent"}


def test_an_alternative_replaces_the_rejected_wine(harness):
    session = harness.email_session("anna@example.ru")
    link_telegram(harness, session)
    bot_record(harness, "wine-wrong")
    response = bot_record(harness, "wine-right", replaces="wine-wrong")
    assert response.json() == {"status": "recorded", "met_on": "2027-01-15"}
    assert [i["slug"] for i in history(harness, session)] == ["wine-right"]
    # A rejected wine without a date today changes nothing.
    again = bot_record(harness, "wine-other", replaces="wine-unknown")
    assert again.json()["status"] == "recorded"
    # The same slug in both fields keeps the date.
    same = bot_record(harness, "wine-right", replaces="wine-right")
    assert same.json() == {"status": "already", "met_on": "2027-01-15"}
    # The rejected wine goes also when the switch is off.
    harness.web("PATCH", "/v1/me", session=session, json={"save_history": False})
    off = bot_record(harness, "wine-new", replaces="wine-other")
    assert off.json() == {"status": "off"}
    assert [i["slug"] for i in history(harness, session)] == ["wine-right"]


def test_body_rules(harness):
    for body in (
        {"user_id": 0, "slug": "wine-a"},
        {"user_id": 2**53, "slug": "wine-a"},
        {"user_id": 5, "slug": "Wine-A"},
        {"user_id": 5, "slug": "wine-a", "replaces": "Bad Slug"},
        {"user_id": 5, "slug": "wine-a", "wine_snapshot": {"rating": 5}},
        {"user_id": 5, "slug": "wine-a", "chat_id": 5},
    ):
        response = harness.bot("/v1/bot/history", body)
        assert response.status_code == 422, body
        assert "Bad Slug" not in response.text
        assert "Wine-A" not in response.text
    undo = harness.bot("/v1/bot/history/undo", {"user_id": 5, "slug": "wine-a", "replaces": "b"})
    assert undo.status_code == 422


def test_only_the_bots_can_record_for_a_chat(harness):
    for path in ("/v1/bot/history", "/v1/bot/history/undo"):
        web = harness.bot(path, {"user_id": 5, "slug": "wine-a"}, token=WEB_TOKEN)
        assert web.status_code == 403, path
        assert web.json()["error"] == "forbidden"
        nobody = harness.client.post(path, json={"user_id": 5, "slug": "wine-a"})
        assert nobody.status_code == 401
    # The Telegram link routes stay with the Telegram bot.
    unlink = harness.bot("/v1/bot/telegram/unlink", {"telegram_user_id": 5}, token=MAX_BOT_TOKEN)
    assert unlink.status_code == 403


def test_the_max_bot_needs_its_token(env):
    del env["ACCOUNT_MAX_TOKEN"]
    harness = Harness(env)
    try:
        response = bot_record(harness, "wine-a", user_id=MAX_USER, token=MAX_BOT_TOKEN)
        assert response.status_code == 401
    finally:
        harness.close()


def test_no_chat_user_id_in_the_log(harness, caplog):
    caplog.set_level(logging.DEBUG)
    session = harness.email_session("anna@example.ru")
    link_telegram(harness, session)
    bot_record(harness, "wine-a")
    bot_undo(harness, "wine-a")
    bot_record(harness, "wine-a", user_id=123456789)
    text = "\n".join(
        entry.getMessage() for entry in caplog.records if entry.name == "chto_za_vino_account"
    )
    assert "History recorded (telegram)" in text
    assert "History record for a chat without a linked diary (telegram)" in text
    assert str(TELEGRAM_USER) not in text
    assert "123456789" not in text
