"""«Сохранённые» (plan 07, issue #64) and the operator merge of both lists."""

from __future__ import annotations

import logging

from conftest import Harness

from chto_za_vino_account import diary
from chto_za_vino_account.cli import merge


def save(harness, session, slug, status="not_tasted", source="photo", snapshot=None, **extra):
    body = {"status": status, "source": source, **extra}
    if snapshot is not None:
        body["wine_snapshot"] = snapshot
    return harness.web("PUT", f"/v1/me/saved/{slug}", session=session, json=body)


def record(harness, session, slug, source="photo", snapshot=None):
    body = {"slug": slug, "source": source}
    if snapshot is not None:
        body["wine_snapshot"] = snapshot
    response = harness.web("POST", "/v1/me/history", session=session, json=body)
    assert response.status_code == 200, response.text
    return response.json()


def saved(harness, session):
    response = harness.web("GET", "/v1/me/saved", session=session)
    assert response.status_code == 200, response.text
    return response.json()["items"]


def history(harness, session):
    return harness.web("GET", "/v1/me/history", session=session).json()["items"]


def test_add_change_and_remove(harness):
    session = harness.email_session("anna@example.ru")
    added = save(harness, session, "wine-a", source="lineup", snapshot={"name": "Вино А"})
    assert added.status_code == 201, added.text
    assert added.json() == {
        "slug": "wine-a",
        "wine": {"name": "Вино А"},
        "status": "not_tasted",
        "source": "lineup",
        "added_at": "2027-01-15T08:01:01Z",
        "updated_at": "2027-01-15T08:01:01Z",
        "in_history": False,
        "note": None,
    }
    harness.clock.advance(60)
    changed = save(harness, session, "wine-a", status="liked", source="dinner_lens")
    assert changed.status_code == 200, changed.text
    assert changed.json() == added.json() | {
        "status": "liked",
        "updated_at": "2027-01-15T08:02:01Z",
    }
    renamed = save(harness, session, "wine-a", status="liked", snapshot={"name": "Вино Б"})
    assert renamed.json()["wine"] == {"name": "Вино Б"}
    assert harness.web("DELETE", "/v1/me/saved/wine-a", session=session).status_code == 204
    again = harness.web("DELETE", "/v1/me/saved/wine-a", session=session)
    assert again.status_code == 404
    assert again.json()["error"] == "not_found"
    assert saved(harness, session) == []


def test_a_change_merges_the_snapshot(harness):
    session = harness.email_session("anna@example.ru")
    full = {"name": "Вино", "producer": "Завод", "sugar": "Сухое", "grapes": ["Мерло"]}
    save(harness, session, "wine-a", snapshot=full)
    changed = save(harness, session, "wine-a", status="liked", snapshot={"name": "Вино 2021"})
    assert changed.json()["wine"] == full | {"name": "Вино 2021"}
    kept = save(harness, session, "wine-a", status="want", snapshot={"grapes": []})
    assert kept.json()["wine"] == full | {"name": "Вино 2021"}


def test_a_note_on_a_saved_wine(harness):
    session = harness.email_session("anna@example.ru")
    added = save(harness, session, "wine-a", note="Купить к Новому году")
    assert added.status_code == 201
    assert added.json()["note"] == "Купить к Новому году"
    assert saved(harness, session)[0]["note"] == "Купить к Новому году"
    slugs = harness.web("GET", "/v1/me/saved/slugs", session=session).json()
    assert slugs == {"items": [{"slug": "wine-a", "status": "not_tasted"}]}
    # No note in the body keeps the stored note.
    kept = save(harness, session, "wine-a", status="liked")
    assert kept.json()["note"] == "Купить к Новому году"
    changed = save(harness, session, "wine-a", status="liked", note="Понравилось с уткой")
    assert changed.json()["note"] == "Понравилось с уткой"
    for empty in ("", "  \n\t ", None):
        save(harness, session, "wine-a", status="liked", note="временно")
        cleared = save(harness, session, "wine-a", status="liked", note=empty)
        assert cleared.status_code == 200, empty
        assert cleared.json()["note"] is None, empty
    assert save(harness, session, "wine-b", note="   ").json()["note"] is None


def test_note_normalization_and_length(harness):
    session = harness.email_session("anna@example.ru")
    lines = save(harness, session, "wine-a", note="\r\n Строка 1\r\nСтрока 2\rСтрока\t3 \n")
    assert lines.json()["note"] == "Строка 1\nСтрока 2\nСтрока\t3"
    longest = save(harness, session, "wine-a", note="я" * 2000)
    assert longest.json()["note"] == "я" * 2000
    padded = save(harness, session, "wine-a", note="  " + "я" * 2000 + "\r\n")
    assert padded.status_code == 200
    # 1,000 Windows line breaks are 1,000 characters after normalization.
    crlf = save(harness, session, "wine-a", note="я\r\n" * 1000)
    assert crlf.status_code == 200
    assert len(crlf.json()["note"]) == 1999
    too_long = save(harness, session, "wine-a", note="я" * 2001)
    assert too_long.status_code == 422
    assert too_long.json() == {"error": "invalid_request", "fields": ["note"]}
    assert saved(harness, session)[0]["note"] == "я\n" * 999 + "я"


def test_a_note_with_a_control_character_is_refused_without_echo(harness):
    session = harness.email_session("anna@example.ru")
    save(harness, session, "wine-a", note="Старая заметка")
    for char in ("\x00", "\x07", "\x0b", "\x1b", "\x7f", "\x85"):
        for note in (f"секрет{char}тайна", f"{char}секрет-тайна"):
            response = save(harness, session, "wine-a", note=note)
            assert response.status_code == 422, repr(note)
            assert response.json() == {"error": "invalid_request", "fields": ["note"]}
            assert "секрет" not in response.text
    assert saved(harness, session)[0]["note"] == "Старая заметка"
    other = save(harness, session, "wine-a", note=5)
    assert other.json() == {"error": "invalid_request", "fields": ["note"]}


def test_notes_never_go_to_the_log(harness, caplog):
    caplog.set_level(logging.DEBUG)
    session = harness.email_session("anna@example.ru")
    save(harness, session, "wine-a", note="секретная-заметка-1")
    save(harness, session, "wine-a", status="liked", note="секретная-заметка-2")
    save(harness, session, "wine-a", note="секретная\x07заметка-3")
    saved(harness, session)
    harness.web("DELETE", "/v1/me/saved/wine-a", session=session)
    assert "Saved wine added (photo)" in caplog.text
    assert "секретная" not in caplog.text


def test_list_and_slugs_are_newest_first(harness):
    session = harness.email_session("anna@example.ru")
    save(harness, session, "wine-a", status="want")
    harness.clock.advance(60)
    save(harness, session, "wine-b", status="disliked", source="shelf")
    harness.clock.advance(60)
    save(harness, session, "wine-a", status="liked")
    assert [i["slug"] for i in saved(harness, session)] == ["wine-a", "wine-b"]
    slugs = harness.web("GET", "/v1/me/saved/slugs", session=session)
    assert slugs.json() == {
        "items": [{"slug": "wine-a", "status": "liked"}, {"slug": "wine-b", "status": "disliked"}]
    }


def test_status_and_source_rules(harness):
    session = harness.email_session("anna@example.ru")
    bad_status = save(harness, session, "wine-a", status="favorite")
    assert bad_status.json() == {"error": "invalid_request", "fields": ["status"]}
    bad_source = save(harness, session, "wine-a", source="telegram")
    assert bad_source.json() == {"error": "invalid_request", "fields": ["source"]}
    for source in ("photo", "shelf", "lineup", "dinner_lens", "history"):
        response = save(harness, session, f"wine-{source.replace('_', '-')}", source=source)
        assert response.status_code == 201, source
    unknown = save(harness, session, "wine-a", snapshot={"note": "личное"})
    assert unknown.json() == {"error": "invalid_request", "fields": ["unknown_field"]}
    assert "личное" not in unknown.text


def test_the_saved_limit(harness, monkeypatch):
    monkeypatch.setattr(diary, "SAVED_LIMIT", 2)
    session = harness.email_session("anna@example.ru")
    assert save(harness, session, "wine-a").status_code == 201
    assert save(harness, session, "wine-b").status_code == 201
    full = save(harness, session, "wine-c")
    assert full.status_code == 409
    assert full.json()["error"] == "saved_full"
    assert save(harness, session, "wine-a", status="want").status_code == 200
    harness.web("DELETE", "/v1/me/saved/wine-b", session=session)
    assert save(harness, session, "wine-c").status_code == 201


def test_a_saved_wine_stays_when_it_leaves_the_history(harness):
    session = harness.email_session("anna@example.ru")
    record(harness, session, "wine-a", snapshot={"name": "Вино А"})
    record(harness, session, "wine-b")
    save(harness, session, "wine-a", status="want", source="history")
    save(harness, session, "wine-b", status="liked", source="history")
    assert {i["slug"]: i["in_history"] for i in saved(harness, session)} == {
        "wine-a": True,
        "wine-b": True,
    }
    assert {i["slug"]: i["saved_status"] for i in history(harness, session)} == {
        "wine-a": "want",
        "wine-b": "liked",
    }
    harness.web("DELETE", "/v1/me/history/wine-a", session=session)
    items = {i["slug"]: i for i in saved(harness, session)}
    assert items["wine-a"]["in_history"] is False
    assert items["wine-a"]["status"] == "want"
    assert items["wine-b"]["in_history"] is True
    harness.web("DELETE", "/v1/me/history", session=session)
    assert [i["in_history"] for i in saved(harness, session)] == [False, False]
    harness.web("DELETE", "/v1/me/saved/wine-b", session=session)
    record(harness, session, "wine-b")
    assert history(harness, session)[0]["saved_status"] is None


def test_a_list_without_a_snapshot_shows_the_snapshot_of_the_other_list(harness):
    session = harness.email_session("anna@example.ru")
    record(harness, session, "wine-a", snapshot={"name": "Из истории"})
    save(harness, session, "wine-a", source="history")
    assert saved(harness, session)[0]["wine"] == {"name": "Из истории"}
    save(harness, session, "wine-b", snapshot={"name": "Из сохранённых"})
    record(harness, session, "wine-b")
    by_slug = {i["slug"]: i["wine"] for i in history(harness, session)}
    assert by_slug["wine-b"] == {"name": "Из сохранённых"}


def test_each_person_sees_only_their_saved_wines(harness):
    anna = harness.email_session("anna@example.ru")
    boris = harness.email_session("boris@example.ru", username="boris")
    save(harness, anna, "wine-a", status="liked")
    assert saved(harness, boris) == []
    assert harness.web("GET", "/v1/me/saved/slugs", session=boris).json() == {"items": []}
    assert harness.web("DELETE", "/v1/me/saved/wine-a", session=boris).status_code == 404
    created = save(harness, boris, "wine-a", status="disliked")
    assert created.status_code == 201
    assert saved(harness, anna)[0]["status"] == "liked"


# -------------------------------------------------------------------- operator merge


def test_the_operator_merge_moves_both_lists(harness: Harness, env: dict[str, str]) -> None:
    first = harness.yandex_login("5560").json()
    keep = harness.signup(first["signup_ticket"], "alex").json()["session"]["token"]
    remove = harness.email_session("alex@example.ru", "alex22")
    # Day 1: both find wine-a; keep first. Both find wine-b; remove first.
    record(harness, keep, "wine-a")
    harness.clock.advance(10)
    record(harness, remove, "wine-a", source="shelf", snapshot={"name": "А из второго"})
    record(harness, remove, "wine-b", source="shelf", snapshot={"name": "Б из второго"})
    harness.clock.advance(10)
    record(harness, keep, "wine-b", snapshot={"name": "Б из первого"})
    # Saved: wine-x changes last in remove, wine-y changes last in keep.
    save(harness, keep, "wine-x", status="liked", source="photo")
    save(harness, remove, "wine-y", status="want", source="lineup")
    harness.clock.advance(10)
    save(harness, remove, "wine-x", status="disliked", source="shelf")
    save(harness, keep, "wine-y", status="liked", source="history")
    save(harness, remove, "wine-z", status="want", source="dinner_lens")
    # Day 2: only remove finds wine-a and wine-c.
    harness.clock.advance(86400)
    record(harness, remove, "wine-a", source="shelf")
    record(harness, remove, "wine-c", source="shelf")
    harness.web("PATCH", "/v1/me", session=keep, json={"save_history": False})

    assert merge(env["ACCOUNT_DATABASE"], "alex", "alex22") == 0

    me = harness.web("GET", "/v1/me", session=keep).json()["user"]
    assert me["save_history"] is False
    wines = {i["slug"]: i for i in history(harness, keep)}
    assert set(wines) == {"wine-a", "wine-b", "wine-c"}
    a = harness.web("GET", "/v1/me/history/wine-a", session=keep).json()
    assert [(d["met_on"], d["source"]) for d in a["days"]] == [
        ("2027-01-16", "shelf"),
        ("2027-01-15", "photo"),
    ]
    assert a["wine"] == {"name": "А из второго"}
    assert a["first_met_at"] == "2027-01-15T08:01:01Z"
    assert a["last_met_at"] == "2027-01-16T08:01:31Z"
    b = harness.web("GET", "/v1/me/history/wine-b", session=keep).json()
    assert [(d["met_on"], d["source"]) for d in b["days"]] == [("2027-01-15", "shelf")]
    assert b["wine"] == {"name": "Б из первого"}
    # The later visit of keep on that day is gone with its date: the times follow the dates.
    assert b["first_met_at"] == "2027-01-15T08:01:11Z"
    assert b["last_met_at"] == "2027-01-15T08:01:11Z"
    for slug in wines:
        detail = harness.web("GET", f"/v1/me/history/{slug}", session=keep).json()
        assert detail["last_met_at"] == max(day["first_at"] for day in detail["days"])
        assert detail["first_met_at"] == min(day["first_at"] for day in detail["days"])
    assert wines["wine-c"]["sources"] == ["shelf"]
    lists = {i["slug"]: i for i in saved(harness, keep)}
    assert {slug: (i["status"], i["source"]) for slug, i in lists.items()} == {
        "wine-x": ("disliked", "shelf"),
        "wine-y": ("liked", "history"),
        "wine-z": ("want", "dinner_lens"),
    }
    assert harness.web("GET", "/v1/me", session=remove).status_code == 401


def test_the_operator_merge_keeps_the_notes(harness: Harness, env: dict[str, str]) -> None:
    first = harness.yandex_login("5561").json()
    keep = harness.signup(first["signup_ticket"], "alex").json()["session"]["token"]
    remove = harness.email_session("alex@example.ru", "alex22")
    # Older rows first, then the rows that win: (winner, its note, the other note).
    save(harness, keep, "both-notes", note="старое keep")
    save(harness, remove, "winner-silent", note="заметка remove")
    save(harness, keep, "keep-wins-silent")
    save(harness, keep, "no-notes")
    harness.clock.advance(10)
    save(harness, remove, "both-notes", note="новое remove")
    save(harness, keep, "winner-silent", status="liked")
    save(harness, remove, "keep-wins-silent", note="заметка remove 2")
    harness.clock.advance(10)
    save(harness, keep, "keep-wins-silent", status="want")
    save(harness, remove, "no-notes", status="want")
    save(harness, remove, "only-remove", note="перенесено")

    assert merge(env["ACCOUNT_DATABASE"], "alex", "alex22") == 0

    notes = {i["slug"]: (i["status"], i["note"]) for i in saved(harness, keep)}
    assert notes == {
        "both-notes": ("not_tasted", "новое remove"),
        "winner-silent": ("liked", "заметка remove"),
        "keep-wins-silent": ("want", "заметка remove 2"),
        "no-notes": ("want", None),
        "only-remove": ("not_tasted", "перенесено"),
    }
