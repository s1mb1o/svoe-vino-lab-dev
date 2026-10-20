"""History of found wines on the site (plan 07, issue #71)."""

from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime

from conftest import START, TELEGRAM_TOKEN, WEB_TOKEN

from chto_za_vino_account import diary
from chto_za_vino_account.diary import decode_cursor, encode_cursor

SNAPSHOT = {
    "name": "Каберне Совиньон",
    "producer": "Шато Тамань",
    "color": "Красное",
    "sugar": "Сухое",
    "region": "Кубань",
    "grapes": ["Каберне Совиньон"],
}


def record(harness, session, slug, source="photo", snapshot=None):
    body = {"slug": slug, "source": source}
    if snapshot is not None:
        body["wine_snapshot"] = snapshot
    return harness.web("POST", "/v1/me/history", session=session, json=body)


def history(harness, session):
    response = harness.web("GET", "/v1/me/history", session=session)
    assert response.status_code == 200, response.text
    return response.json()


def item(harness, session, slug):
    return harness.web("GET", f"/v1/me/history/{slug}", session=session)


def app_get(harness, path, token):
    headers = {
        "Authorization": f"Bearer {WEB_TOKEN}",
        "X-Client-IP": "203.0.113.7",
        "X-App-Token": token,
    }
    return harness.client.get(path, headers=headers)


def test_the_first_match_is_recorded(harness):
    session = harness.email_session("anna@example.ru")
    response = record(harness, session, "kaberne-taman-2021", snapshot=SNAPSHOT)
    assert response.status_code == 200, response.text
    assert response.json() == {"status": "recorded", "met_on": "2027-01-15"}
    body = history(harness, session)
    assert body["save_history"] is True
    assert body["items"] == [
        {
            "slug": "kaberne-taman-2021",
            "wine": SNAPSHOT,
            "first_met_at": "2027-01-15T08:01:01Z",
            "last_met_at": "2027-01-15T08:01:01Z",
            "days_count": 1,
            "sources": ["photo"],
            "saved_status": None,
        }
    ]
    detail = item(harness, session, "kaberne-taman-2021").json()
    assert detail["days"] == [
        {"met_on": "2027-01-15", "source": "photo", "first_at": "2027-01-15T08:01:01Z"}
    ]


def test_the_same_day_changes_nothing_but_the_snapshot(harness):
    session = harness.email_session("anna@example.ru")
    assert record(harness, session, "wine-a").json()["status"] == "recorded"
    harness.clock.advance(3600)
    again = record(harness, session, "wine-a", source="shelf", snapshot={"name": "Новое имя"})
    assert again.json() == {"status": "already", "met_on": "2027-01-15"}
    detail = item(harness, session, "wine-a").json()
    assert detail["wine"] == {"name": "Новое имя"}
    assert detail["last_met_at"] == "2027-01-15T08:01:01Z"
    assert detail["days"] == [
        {"met_on": "2027-01-15", "source": "photo", "first_at": "2027-01-15T08:01:01Z"}
    ]
    # A repeat without a snapshot keeps the stored one.
    record(harness, session, "wine-a")
    assert item(harness, session, "wine-a").json()["wine"] == {"name": "Новое имя"}


def test_a_new_moscow_day_is_a_new_date(harness):
    session = harness.email_session("anna@example.ru")
    # START is 08:00 UTC: 11:00 in Moscow. Moscow midnight is 21:00 UTC.
    assert record(harness, session, "wine-a").json()["met_on"] == "2027-01-15"
    harness.clock.now = START + 13 * 3600 - 1
    assert record(harness, session, "wine-a").json() == {
        "status": "already",
        "met_on": "2027-01-15",
    }
    harness.clock.now = START + 13 * 3600 + 1
    assert datetime.fromtimestamp(harness.clock.now, UTC).date().isoformat() == "2027-01-15"
    response = record(harness, session, "wine-a", source="shelf")
    assert response.json() == {"status": "recorded", "met_on": "2027-01-16"}
    detail = item(harness, session, "wine-a").json()
    assert detail["days_count"] == 2
    assert detail["sources"] == ["photo", "shelf"]
    assert detail["first_met_at"] == "2027-01-15T08:01:01Z"
    assert detail["last_met_at"] == "2027-01-15T21:00:01Z"
    assert [day["met_on"] for day in detail["days"]] == ["2027-01-16", "2027-01-15"]
    harness.clock.advance(2 * 86400)
    assert record(harness, session, "wine-a").json()["met_on"] == "2027-01-18"


def test_the_list_is_newest_first(harness):
    session = harness.email_session("anna@example.ru")
    for slug in ("wine-a", "wine-b", "wine-c"):
        record(harness, session, slug)
        harness.clock.advance(86400)
    record(harness, session, "wine-a")
    assert [i["slug"] for i in history(harness, session)["items"]] == [
        "wine-a",
        "wine-c",
        "wine-b",
    ]


def test_the_switch(harness):
    session = harness.email_session("anna@example.ru")
    me = harness.web("GET", "/v1/me", session=session).json()
    assert me["user"]["save_history"] is True
    off = harness.web("PATCH", "/v1/me", session=session, json={"save_history": False})
    assert off.status_code == 200, off.text
    assert off.json()["user"]["save_history"] is False
    assert off.json()["session"]["auth_method"] == "email"
    assert record(harness, session, "wine-a").json() == {"status": "off"}
    assert history(harness, session) == {"items": [], "save_history": False}
    on = harness.web("PATCH", "/v1/me", session=session, json={"save_history": True})
    assert on.json()["user"]["save_history"] is True
    assert record(harness, session, "wine-a").json()["status"] == "recorded"
    assert [i["slug"] for i in history(harness, session)["items"]] == ["wine-a"]


def test_the_switch_keeps_the_history(harness):
    session = harness.email_session("anna@example.ru")
    record(harness, session, "wine-a")
    harness.web("PATCH", "/v1/me", session=session, json={"save_history": False})
    assert [i["slug"] for i in history(harness, session)["items"]] == ["wine-a"]


def test_the_switch_accepts_only_a_boolean(harness):
    session = harness.email_session("anna@example.ru")
    for value in ("false", 0, None):
        response = harness.web("PATCH", "/v1/me", session=session, json={"save_history": value})
        assert response.status_code == 422, value
    extra = harness.web(
        "PATCH", "/v1/me", session=session, json={"save_history": True, "username": "x"}
    )
    assert extra.status_code == 422


def test_each_person_sees_only_their_history(harness):
    anna = harness.email_session("anna@example.ru")
    boris = harness.email_session("boris@example.ru", username="boris")
    record(harness, anna, "wine-a")
    assert history(harness, boris)["items"] == []
    assert item(harness, boris, "wine-a").status_code == 404
    assert harness.web("DELETE", "/v1/me/history/wine-a", session=boris).status_code == 404
    day = harness.web("DELETE", "/v1/me/history/wine-a/days/2027-01-15", session=boris)
    assert day.status_code == 404
    harness.web("DELETE", "/v1/me/history", session=boris)
    assert [i["slug"] for i in history(harness, anna)["items"]] == ["wine-a"]


def test_the_wine_limit_drops_the_oldest_wine(harness, monkeypatch):
    monkeypatch.setattr(diary, "HISTORY_WINES_LIMIT", 3)
    session = harness.email_session("anna@example.ru")
    for slug in ("wine-a", "wine-b", "wine-c"):
        record(harness, session, slug)
        harness.clock.advance(60)
    record(harness, session, "wine-a")  # the same day: wine-a stays the oldest
    assert record(harness, session, "wine-d").json()["status"] == "recorded"
    slugs = [i["slug"] for i in history(harness, session)["items"]]
    assert slugs == ["wine-d", "wine-c", "wine-b"]


def test_the_day_limit_drops_the_oldest_date(harness, monkeypatch):
    monkeypatch.setattr(diary, "HISTORY_DAYS_LIMIT", 3)
    session = harness.email_session("anna@example.ru")
    for _ in range(4):
        assert record(harness, session, "wine-a").json()["status"] == "recorded"
        harness.clock.advance(86400)
    detail = item(harness, session, "wine-a").json()
    assert detail["days_count"] == 3
    assert [day["met_on"] for day in detail["days"]] == ["2027-01-18", "2027-01-17", "2027-01-16"]
    assert detail["first_met_at"] == "2027-01-16T08:01:01Z"


def test_the_limits_of_plan_07():
    assert diary.HISTORY_WINES_LIMIT == 2000
    assert diary.HISTORY_DAYS_LIMIT == 366
    assert diary.SAVED_LIMIT == 500


def test_remove_one_date(harness):
    session = harness.email_session("anna@example.ru")
    record(harness, session, "wine-a")
    harness.clock.advance(86400)
    record(harness, session, "wine-a", source="shelf")
    path = "/v1/me/history/wine-a/days/2027-01-16"
    assert harness.web("DELETE", path, session=session).status_code == 204
    detail = item(harness, session, "wine-a").json()
    assert detail["days_count"] == 1
    assert detail["sources"] == ["photo"]
    assert detail["last_met_at"] == "2027-01-15T08:01:01Z"
    missing = harness.web("DELETE", path, session=session)
    assert missing.status_code == 404
    assert missing.json()["error"] == "not_found"
    last = harness.web("DELETE", "/v1/me/history/wine-a/days/2027-01-15", session=session)
    assert last.status_code == 204
    assert item(harness, session, "wine-a").json()["error"] == "not_found"
    assert history(harness, session)["items"] == []


def test_remove_one_wine_and_clear(harness):
    session = harness.email_session("anna@example.ru")
    for slug in ("wine-a", "wine-b", "wine-c"):
        record(harness, session, slug)
    assert harness.web("DELETE", "/v1/me/history/wine-b", session=session).status_code == 204
    again = harness.web("DELETE", "/v1/me/history/wine-b", session=session)
    assert again.status_code == 404
    assert again.json()["error"] == "not_found"
    assert {i["slug"] for i in history(harness, session)["items"]} == {"wine-a", "wine-c"}
    assert harness.web("DELETE", "/v1/me/history", session=session).status_code == 204
    assert history(harness, session)["items"] == []
    assert harness.web("DELETE", "/v1/me/history", session=session).status_code == 204


def test_the_history_needs_a_session(harness):
    for method, path in (
        ("GET", "/v1/me/history"),
        ("POST", "/v1/me/history"),
        ("DELETE", "/v1/me/history"),
        ("PATCH", "/v1/me"),
    ):
        response = harness.web(method, path, json={"slug": "wine-a", "source": "photo"})
        assert response.status_code == 401, path


def test_a_bot_cannot_call_the_site_routes(harness):
    session = harness.email_session("anna@example.ru")
    headers = {"Authorization": f"Bearer {TELEGRAM_TOKEN}", "X-Session-Token": session}
    for method, path in (
        ("GET", "/v1/me/history"),
        ("POST", "/v1/me/history"),
        ("PUT", "/v1/me/saved/wine-a"),
        ("PATCH", "/v1/me"),
    ):
        response = harness.client.request(
            method, path, headers=headers, json={"slug": "wine-a", "source": "photo"}
        )
        assert response.status_code == 403, path
        assert response.json()["error"] == "forbidden"


def test_snapshot_rules(harness):
    session = harness.email_session("anna@example.ru")

    def check(snapshot, field):
        response = record(harness, session, "wine-a", snapshot=snapshot)
        assert response.status_code == 422, snapshot
        assert response.json() == {"error": "invalid_request", "fields": [field]}

    check({"name": "Вино", "price": "секрет-123"}, "unknown_field")
    check({"name": "я" * 201}, "wine_snapshot.name")
    check({"name": ""}, "wine_snapshot.name")
    check({"grapes": ["Мерло"] * 13}, "wine_snapshot.grapes")
    check({"grapes": ["м" * 81]}, "invalid_field")
    check({"name": 5}, "wine_snapshot.name")
    # Five fields of 200 Cyrillic letters are about 2,060 bytes of JSON.
    big = {key: "я" * 200 for key in ("name", "producer", "color", "sugar", "region")}
    check(big, "wine_snapshot")
    fits = {key: "a" * 200 for key in ("name", "producer", "color", "sugar", "region")}
    assert record(harness, session, "wine-a", snapshot=fits).json()["status"] == "recorded"
    assert item(harness, session, "wine-a").json()["wine"] == fits


def test_a_newer_snapshot_merges_into_the_stored_one(harness):
    session = harness.email_session("anna@example.ru")
    record(harness, session, "wine-a", snapshot=SNAPSHOT)
    record(harness, session, "wine-a", snapshot={"name": "Новое имя", "grapes": []})
    assert item(harness, session, "wine-a").json()["wine"] == SNAPSHOT | {"name": "Новое имя"}
    harness.clock.advance(86400)
    record(harness, session, "wine-a", source="shelf", snapshot={"sugar": "Полусухое"})
    assert item(harness, session, "wine-a").json()["wine"] == SNAPSHOT | {
        "name": "Новое имя",
        "sugar": "Полусухое",
    }


def test_a_merge_over_the_size_limit_keeps_the_newer_snapshot(harness):
    session = harness.email_session("anna@example.ru")
    old = {key: "я" * 200 for key in ("name", "producer", "color", "sugar")}
    new = {"region": "я" * 200, "grapes": ["м" * 80] * 3}
    record(harness, session, "wine-a", snapshot=old)
    record(harness, session, "wine-a", snapshot=new)
    assert item(harness, session, "wine-a").json()["wine"] == new


def test_an_empty_snapshot_keeps_the_stored_one(harness):
    session = harness.email_session("anna@example.ru")
    record(harness, session, "wine-a", snapshot={"name": "Вино"})
    record(harness, session, "wine-a", snapshot={})
    assert item(harness, session, "wine-a").json()["wine"] == {"name": "Вино"}


def test_slug_and_source_rules_do_not_echo_the_input(harness):
    session = harness.email_session("anna@example.ru")
    for slug in ("Secret-Slug", "-abc", "abc-", "a b", "a" * 201, "вино"):
        response = record(harness, session, slug)
        assert response.status_code == 422, slug
        assert response.json() == {"error": "invalid_request", "fields": ["slug"]}
    assert record(harness, session, "a" * 200).json()["status"] == "recorded"
    assert record(harness, session, "x").json()["status"] == "recorded"
    for source in ("lineup", "telegram", "max", "history"):
        response = record(harness, session, "wine-a", source=source)
        assert response.json() == {"error": "invalid_request", "fields": ["source"]}
    for path in (
        "/v1/me/history/Secret-Slug",
        "/v1/me/history/wine-a/days/2027-1-15",
        "/v1/me/history/wine-a/days/yesterday",
        "/v1/me/saved/Secret-Slug",
    ):
        response = harness.web("DELETE", path, session=session)
        assert response.status_code == 422, path
        assert "Secret" not in response.text
        assert "yesterday" not in response.text
    assert item(harness, session, "Secret-Slug").status_code == 422


def test_account_deletion_removes_both_lists(harness, env):
    session = harness.email_session("anna@example.ru")
    record(harness, session, "wine-a")
    harness.web(
        "PUT",
        "/v1/me/saved/wine-b",
        session=session,
        json={"status": "want", "source": "lineup", "note": "личная-заметка-анны"},
    )
    assert harness.web("DELETE", "/v1/me", session=session).status_code == 204
    with sqlite3.connect(env["ACCOUNT_DATABASE"]) as db:
        for table in ("history_wines", "history_days", "saved_wines"):
            assert db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0  # noqa: S608
        dump = "\n".join(db.iterdump())
    assert "личная-заметка-анны" not in dump


def test_no_user_id_or_slug_in_the_info_log(harness, caplog):
    caplog.set_level(logging.INFO)
    session = harness.email_session("anna@example.ru")
    user_id = harness.web("GET", "/v1/me", session=session).json()["user"]["id"]
    record(harness, session, "secret-wine-slug")
    harness.web("DELETE", "/v1/me/history/secret-wine-slug", session=session)
    harness.web("PATCH", "/v1/me", session=session, json={"save_history": False})
    # The test client logs request URLs through httpx; the service turns that logger down.
    text = "\n".join(
        entry.getMessage() for entry in caplog.records if entry.name == "chto_za_vino_account"
    )
    assert "History recorded (photo)" in text
    assert "History wine removed" in text
    assert "History recording turned off" in text
    assert user_id not in text
    assert "secret-wine-slug" not in text


# ------------------------------------------------------------- application tokens


def test_app_wines_pages_through_the_history(harness):
    session = harness.email_session("anna@example.ru")
    token = harness.web(
        "POST", "/v1/me/app-tokens", session=session, json={"name": "MCP", "lifetime_days": 30}
    ).json()["token"]
    record(harness, session, "wine-a", snapshot=SNAPSHOT)
    harness.clock.advance(60)
    # Three wines in the same second: the slug orders them.
    for slug in ("tie-c", "tie-a", "tie-b"):
        record(harness, session, slug)
    harness.clock.advance(86400)
    record(harness, session, "wine-a", source="shelf")
    harness.web(
        "PUT",
        "/v1/me/saved/wine-a",
        session=session,
        json={"status": "liked", "source": "history"},
    )
    expected = [i["slug"] for i in history(harness, session)["items"]]
    assert expected == ["wine-a", "tie-a", "tie-b", "tie-c"]

    seen = []
    cursor = None
    for _ in range(3):
        path = "/v1/app/wines?limit=3" + (f"&cursor={cursor}" if cursor else "")
        page = app_get(harness, path, token)
        assert page.status_code == 200, page.text
        body = page.json()
        seen.extend(i["slug"] for i in body["items"])
        cursor = body["next_cursor"]
        if cursor is None:
            break
    assert seen == expected

    first = app_get(harness, "/v1/app/wines?limit=1", token).json()
    assert first["items"] == [
        {
            "slug": "wine-a",
            "name": "Каберне Совиньон",
            "producer": "Шато Тамань",
            "color": "Красное",
            "sugar": "Сухое",
            "first_met_at": "2027-01-15T08:01:01Z",
            "last_met_at": "2027-01-16T08:02:01Z",
            "days": 2,
            "sources": ["photo", "shelf"],
            "saved_status": "liked",
        }
    ]
    plain = app_get(harness, "/v1/app/wines?limit=50", token).json()["items"][1]
    assert plain["name"] is None and plain["saved_status"] is None


def test_app_wines_cursor_rules(harness):
    session = harness.email_session("anna@example.ru")
    token = harness.web(
        "POST", "/v1/me/app-tokens", session=session, json={"name": "MCP", "lifetime_days": 30}
    ).json()["token"]
    long_slug = "z" + "-_9" * 66 + "y"
    assert len(long_slug) == 200
    record(harness, session, "wine-b")
    harness.clock.advance(60)
    record(harness, session, long_slug)
    body = app_get(harness, "/v1/app/wines?limit=1", token).json()
    assert [i["slug"] for i in body["items"]] == [long_slug]
    assert len(body["next_cursor"]) <= 200
    rest = app_get(harness, f"/v1/app/wines?limit=1&cursor={body['next_cursor']}", token).json()
    assert rest == {"items": [rest["items"][0]], "next_cursor": None}
    assert rest["items"][0]["slug"] == "wine-b"
    for cursor in ("AAAA", "A", "AAAAAAAAAA"):
        response = app_get(harness, f"/v1/app/wines?cursor={cursor}", token)
        assert response.status_code == 400, cursor
        assert response.json()["error"] == "invalid_cursor"


def test_the_cursor_round_trip():
    for slug in ("a", "0", "a-b_c", "z" * 200, "-".join(["ab"] * 60)[:199] + "9"):
        cursor = encode_cursor(1_800_000_000, slug)
        assert len(cursor) <= 200
        assert decode_cursor(cursor) == (1_800_000_000, slug)
