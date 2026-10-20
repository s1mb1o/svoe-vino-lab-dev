"""The diary lists of plan 07: the history of found wines and «Сохранённые».

The history (issue #71) keeps one date for each wine and calendar day in Europe/Moscow. The
site records a photo or shelf match. A linked Telegram or MAX chat records its own matches.
The saved list (issue #64) is independent: a wine stays saved when it leaves the history.

The API layer checks the slugs, the sources, the statuses, the wine snapshots, and the notes.
This module gets valid values and a snapshot as a dict of the fields that have a value.

A saved wine can have a personal note. A note is the person's own text: it never goes to the
log, not even at the debug level, and not to the application API.
"""

from __future__ import annotations

import base64
import binascii
import json
import logging
import re
import sqlite3
import unicodedata
from collections.abc import Callable
from datetime import datetime, timedelta, timezone, tzinfo
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .db import Database
from .service import AccountError, iso

LOG = logging.getLogger("chto_za_vino_account")

# At the history limits the oldest record goes, so the history never blocks a search (D9).
HISTORY_WINES_LIMIT = 2000
HISTORY_DAYS_LIMIT = 366
SAVED_LIMIT = 500
SNAPSHOT_BYTES = 2048
NOTE_LENGTH = 2000
NOTE_CONTROLS_ALLOWED = frozenset("\n\t")

SLUG_PATTERN = r"^[a-z0-9](?:[a-z0-9_-]{0,198}[a-z0-9])?$"
DAY_PATTERN = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$"
SLUG_RE = re.compile(SLUG_PATTERN)

# The history sources in display order.
HISTORY_SOURCES = ("photo", "shelf", "telegram", "max")
# A bot records with its messenger as the source and finds the person by that identity.
BOT_PROVIDERS = {"telegram-bot": "telegram", "max-bot": "max"}
# The time of a result card (`at`) that a bot sends with undo and `replaces`. A time outside
# this window gives today: a wrong bot clock cannot remove an old date.
CARD_PAST_SECONDS = 48 * 3600
CARD_FUTURE_SECONDS = 60

# The cursor of GET /v1/app/wines must fit in the 200 characters that the Nuxt server and the
# MCP server accept. Each slug character is a digit of base 39, so a slug of 200 characters
# needs 133 bytes. With the 5-byte time, the cursor has at most 184 characters.
CURSOR_ALPHABET = "-0123456789_abcdefghijklmnopqrstuvwxyz"
CURSOR_BASE = len(CURSOR_ALPHABET) + 1
CURSOR_TIME_BYTES = 5


def _moscow() -> tzinfo:
    try:
        return ZoneInfo("Europe/Moscow")
    except ZoneInfoNotFoundError:
        # A slim image can lack the time zone database. Moscow is UTC+3 without DST since 2014.
        return timezone(timedelta(hours=3), "MSK")


MOSCOW = _moscow()


def moscow_day(timestamp: int) -> str:
    """The calendar day of a time in Europe/Moscow, as YYYY-MM-DD."""
    return datetime.fromtimestamp(timestamp, MOSCOW).date().isoformat()


def card_day(at: int | None, now: int) -> str:
    """The Moscow day of a result card. A missing time or a time outside the window gives today."""
    if at is None or not now - CARD_PAST_SECONDS <= at <= now + CARD_FUTURE_SECONDS:
        return moscow_day(now)
    return moscow_day(at)


def normalize_note(value: str) -> str:
    """The note as stored: line breaks as "\\n", no whitespace at the ends.

    An empty result clears the note. Control characters other than a line break and a tab, and
    a note longer than NOTE_LENGTH characters, give ValueError. The message never holds the text.
    The check runs before the strip, so a control character at an end is refused, not removed.
    """
    text = value.replace("\r\n", "\n").replace("\r", "\n")
    if any(
        unicodedata.category(char) == "Cc" and char not in NOTE_CONTROLS_ALLOWED for char in text
    ):
        raise ValueError("The note has a control character")
    text = text.strip()
    if len(text) > NOTE_LENGTH:
        raise ValueError(f"The note has more than {NOTE_LENGTH} characters")
    return text


def snapshot_json(snapshot: dict[str, Any]) -> str:
    """Compact JSON text of a snapshot, as stored and as measured against SNAPSHOT_BYTES."""
    return json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"))


def merged_snapshot(stored: str | None, new: dict[str, Any] | None) -> str | None:
    """The stored snapshot updated with a newer one.

    The keys of the newer snapshot override. Keys that it does not have keep the stored values,
    so a card with less data does not erase a richer snapshot. When the union is larger than
    SNAPSHOT_BYTES, the newer snapshot replaces the stored one.
    """
    if not new:
        return stored
    union = snapshot_json((_wine(stored) or {}) | new)
    if len(union.encode("utf-8")) > SNAPSHOT_BYTES:
        return snapshot_json(new)
    return union


def encode_cursor(last_met_at: int, slug: str) -> str:
    number = 0
    for char in reversed(slug):
        number = number * CURSOR_BASE + CURSOR_ALPHABET.index(char) + 1
    raw = last_met_at.to_bytes(CURSOR_TIME_BYTES, "big") + number.to_bytes(
        (number.bit_length() + 7) // 8, "big"
    )
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def decode_cursor(cursor: str) -> tuple[int, str]:
    invalid = AccountError("invalid_cursor", 400, "Read the list again from the start")
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
    except (binascii.Error, ValueError):
        raise invalid from None
    number = int.from_bytes(raw[CURSOR_TIME_BYTES:], "big")
    chars = []
    while number:
        number, digit = divmod(number, CURSOR_BASE)
        if digit == 0:
            raise invalid
        chars.append(CURSOR_ALPHABET[digit - 1])
    slug = "".join(chars)
    if not SLUG_RE.fullmatch(slug):
        raise invalid
    return int.from_bytes(raw[:CURSOR_TIME_BYTES], "big"), slug


def _wine(text: str | None) -> dict[str, Any] | None:
    if not text:
        return None
    try:
        value = json.loads(text)
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def _sources(text: str | None) -> list[str]:
    found = set((text or "").split(",")) - {""}
    known = [source for source in HISTORY_SOURCES if source in found]
    return known + sorted(found - set(HISTORY_SOURCES))


# One query for the history list, one wine, and a page of the application API. The saved
# snapshot fills in when the history has none.
HISTORY_QUERY = (
    "SELECT w.wine_slug, COALESCE(w.wine_snapshot, s.wine_snapshot) AS snapshot, "
    "w.first_met_at, w.last_met_at, s.status AS saved_status, "
    "COUNT(d.met_on) AS days_count, GROUP_CONCAT(DISTINCT d.source) AS sources "
    "FROM history_wines w "
    "LEFT JOIN history_days d ON d.user_id = w.user_id AND d.wine_slug = w.wine_slug "
    "LEFT JOIN saved_wines s ON s.user_id = w.user_id AND s.wine_slug = w.wine_slug "
    "WHERE w.user_id = :user AND (:slug IS NULL OR w.wine_slug = :slug) "
    "AND (:after_at IS NULL OR w.last_met_at < :after_at "
    "OR (w.last_met_at = :after_at AND w.wine_slug > :after_slug)) "
    "GROUP BY w.user_id, w.wine_slug "
    "ORDER BY w.last_met_at DESC, w.wine_slug "
    "LIMIT :limit"
)

# The history snapshot fills in when the saved wine has none.
SAVED_QUERY = (
    "SELECT s.wine_slug, COALESCE(s.wine_snapshot, w.wine_snapshot) AS snapshot, s.status, "
    "s.source, s.added_at, s.updated_at, w.wine_slug IS NOT NULL AS in_history, s.note "
    "FROM saved_wines s "
    "LEFT JOIN history_wines w ON w.user_id = s.user_id AND w.wine_slug = s.wine_slug "
    "WHERE s.user_id = :user AND (:slug IS NULL OR s.wine_slug = :slug) "
    "ORDER BY s.updated_at DESC, s.wine_slug"
)


class Diary:
    def __init__(self, db: Database, clock: Callable[[], float]) -> None:
        self.db = db
        self.clock = clock

    def _now(self) -> int:
        return int(self.clock())

    # ----------------------------------------------------------------- helpers

    @staticmethod
    def _save_history(db: sqlite3.Connection, user_id: str) -> bool:
        """The switch of the account. A missing account is a session error."""
        row = db.execute("SELECT save_history FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            raise AccountError("session_invalid", 401, "The account no longer exists")
        return bool(row["save_history"])

    @staticmethod
    def _history_rows(
        db: sqlite3.Connection,
        user_id: str,
        *,
        slug: str | None = None,
        after: tuple[int, str] | None = None,
        limit: int = -1,
    ) -> list[sqlite3.Row]:
        after_at, after_slug = after if after else (None, None)
        return db.execute(
            HISTORY_QUERY,
            {
                "user": user_id,
                "slug": slug,
                "after_at": after_at,
                "after_slug": after_slug,
                "limit": limit,
            },
        ).fetchall()

    @staticmethod
    def _history_view(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "slug": row["wine_slug"],
            "wine": _wine(row["snapshot"]),
            "first_met_at": iso(row["first_met_at"]),
            "last_met_at": iso(row["last_met_at"]),
            "days_count": row["days_count"],
            "sources": _sources(row["sources"]),
            "saved_status": row["saved_status"],
        }

    @staticmethod
    def _saved_view(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "slug": row["wine_slug"],
            "wine": _wine(row["snapshot"]),
            "status": row["status"],
            "source": row["source"],
            "added_at": iso(row["added_at"]),
            "updated_at": iso(row["updated_at"]),
            "in_history": bool(row["in_history"]),
            "note": row["note"],
        }

    @staticmethod
    def _refresh(db: sqlite3.Connection, user_id: str, slug: str) -> None:
        """Set the first and last times from the dates. A wine without dates goes."""
        row = db.execute(
            "SELECT MIN(first_at) AS first, MAX(first_at) AS last FROM history_days "
            "WHERE user_id = ? AND wine_slug = ?",
            (user_id, slug),
        ).fetchone()
        if row["first"] is None:
            db.execute(
                "DELETE FROM history_wines WHERE user_id = ? AND wine_slug = ?", (user_id, slug)
            )
            return
        db.execute(
            "UPDATE history_wines SET first_met_at = ?, last_met_at = ? "
            "WHERE user_id = ? AND wine_slug = ?",
            (row["first"], row["last"], user_id, slug),
        )

    def _remove_day(
        self,
        db: sqlite3.Connection,
        user_id: str,
        slug: str,
        met_on: str,
        source: str | None = None,
    ) -> bool:
        """Remove one date. With `source`, only a date of that source goes."""
        cursor = db.execute(
            "DELETE FROM history_days WHERE user_id = ? AND wine_slug = ? AND met_on = ? "
            "AND (? IS NULL OR source = ?)",
            (user_id, slug, met_on, source, source),
        )
        if cursor.rowcount == 0:
            return False
        self._refresh(db, user_id, slug)
        return True

    def _record(
        self,
        db: sqlite3.Connection,
        user_id: str,
        slug: str,
        source: str,
        snapshot: dict[str, Any] | None,
        now: int,
    ) -> dict[str, str]:
        met_on = moscow_day(now)
        known = db.execute(
            "SELECT wine_snapshot FROM history_wines WHERE user_id = ? AND wine_slug = ?",
            (user_id, slug),
        ).fetchone()
        if known is None:
            excess = (
                db.execute(
                    "SELECT COUNT(*) FROM history_wines WHERE user_id = ?", (user_id,)
                ).fetchone()[0]
                - HISTORY_WINES_LIMIT
                + 1
            )
            if excess > 0:
                db.execute(
                    "DELETE FROM history_wines WHERE user_id = ? AND wine_slug IN ("
                    "SELECT wine_slug FROM history_wines WHERE user_id = ? "
                    "ORDER BY last_met_at, wine_slug DESC LIMIT ?)",
                    (user_id, user_id, excess),
                )
                LOG.info("History limit: the oldest wines were removed")
            db.execute(
                "INSERT INTO history_wines (user_id, wine_slug, wine_snapshot, first_met_at, "
                "last_met_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, slug, merged_snapshot(None, snapshot), now, now),
            )
        else:
            if snapshot:
                db.execute(
                    "UPDATE history_wines SET wine_snapshot = ? "
                    "WHERE user_id = ? AND wine_slug = ?",
                    (merged_snapshot(known["wine_snapshot"], snapshot), user_id, slug),
                )
            today = db.execute(
                "SELECT 1 FROM history_days WHERE user_id = ? AND wine_slug = ? AND met_on = ?",
                (user_id, slug, met_on),
            ).fetchone()
            if today is not None:
                return {"status": "already", "met_on": met_on}
            excess = (
                db.execute(
                    "SELECT COUNT(*) FROM history_days WHERE user_id = ? AND wine_slug = ?",
                    (user_id, slug),
                ).fetchone()[0]
                - HISTORY_DAYS_LIMIT
                + 1
            )
            if excess > 0:
                db.execute(
                    "DELETE FROM history_days WHERE user_id = ? AND wine_slug = ? AND met_on IN ("
                    "SELECT met_on FROM history_days WHERE user_id = ? AND wine_slug = ? "
                    "ORDER BY met_on LIMIT ?)",
                    (user_id, slug, user_id, slug, excess),
                )
                LOG.info("History limit: the oldest dates of a wine were removed")
        db.execute(
            "INSERT INTO history_days (user_id, wine_slug, met_on, source, first_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, slug, met_on, source, now),
        )
        self._refresh(db, user_id, slug)
        return {"status": "recorded", "met_on": met_on}

    # ----------------------------------------------------------------- switch

    def set_save_history(self, user_id: str, enabled: bool) -> None:
        with self.db.transaction() as db:
            cursor = db.execute(
                "UPDATE users SET save_history = ? WHERE id = ?", (int(enabled), user_id)
            )
        if cursor.rowcount == 0:
            raise AccountError("session_invalid", 401, "The account no longer exists")
        LOG.info("History recording turned %s", "on" if enabled else "off")

    # ---------------------------------------------------------------- history

    def history(self, user_id: str) -> dict[str, Any]:
        with self.db.transaction() as db:
            enabled = self._save_history(db, user_id)
            rows = self._history_rows(db, user_id)
        return {"items": [self._history_view(row) for row in rows], "save_history": enabled}

    def history_item(self, user_id: str, slug: str) -> dict[str, Any]:
        with self.db.transaction() as db:
            rows = self._history_rows(db, user_id, slug=slug)
            days = db.execute(
                "SELECT met_on, source, first_at FROM history_days "
                "WHERE user_id = ? AND wine_slug = ? ORDER BY met_on DESC",
                (user_id, slug),
            ).fetchall()
        if not rows:
            raise AccountError("not_found", 404, "The wine is not in the history")
        view = self._history_view(rows[0])
        view["days"] = [
            {"met_on": day["met_on"], "source": day["source"], "first_at": iso(day["first_at"])}
            for day in days
        ]
        return view

    def record(
        self, user_id: str, slug: str, source: str, snapshot: dict[str, Any] | None
    ) -> dict[str, str]:
        now = self._now()
        with self.db.transaction() as db:
            if not self._save_history(db, user_id):
                return {"status": "off"}
            result = self._record(db, user_id, slug, source, snapshot, now)
        if result["status"] == "recorded":
            LOG.info("History recorded (%s)", source)
            LOG.debug("History recorded: %s", slug)
        return result

    def remove_day(self, user_id: str, slug: str, met_on: str) -> None:
        with self.db.transaction() as db:
            removed = self._remove_day(db, user_id, slug, met_on)
        if not removed:
            raise AccountError("not_found", 404, "The date is not in the history")
        LOG.info("History date removed")

    def remove_wine(self, user_id: str, slug: str) -> None:
        with self.db.transaction() as db:
            cursor = db.execute(
                "DELETE FROM history_wines WHERE user_id = ? AND wine_slug = ?", (user_id, slug)
            )
        if cursor.rowcount == 0:
            raise AccountError("not_found", 404, "The wine is not in the history")
        LOG.info("History wine removed")

    def clear_history(self, user_id: str) -> None:
        with self.db.transaction() as db:
            db.execute("DELETE FROM history_wines WHERE user_id = ?", (user_id,))
        LOG.info("History cleared")

    # ------------------------------------------------------------------ saved

    def saved(self, user_id: str) -> dict[str, Any]:
        with self.db.transaction() as db:
            rows = db.execute(SAVED_QUERY, {"user": user_id, "slug": None}).fetchall()
        return {"items": [self._saved_view(row) for row in rows]}

    def saved_slugs(self, user_id: str) -> dict[str, Any]:
        with self.db.transaction() as db:
            rows = db.execute(
                "SELECT wine_slug, status FROM saved_wines WHERE user_id = ? "
                "ORDER BY updated_at DESC, wine_slug",
                (user_id,),
            ).fetchall()
        return {"items": [{"slug": row["wine_slug"], "status": row["status"]} for row in rows]}

    def save(
        self,
        user_id: str,
        slug: str,
        status: str,
        source: str,
        snapshot: dict[str, Any] | None,
        note: str | None = None,
    ) -> tuple[dict[str, Any], bool]:
        """Add a wine or change its status. Returns the saved wine and True for a new wine.

        A change keeps the source and the time of the addition. `note` is a normalized note:
        None keeps the stored note, an empty string clears it.
        """
        now = self._now()
        with self.db.transaction() as db:
            self._save_history(db, user_id)  # Refuses a deleted account before the insert.
            current = db.execute(
                "SELECT wine_snapshot, note FROM saved_wines WHERE user_id = ? AND wine_slug = ?",
                (user_id, slug),
            ).fetchone()
            created = current is None
            if created:
                count = db.execute(
                    "SELECT COUNT(*) FROM saved_wines WHERE user_id = ?", (user_id,)
                ).fetchone()[0]
                if count >= SAVED_LIMIT:
                    raise AccountError(
                        "saved_full", 409, f"Remove a saved wine first: at most {SAVED_LIMIT}"
                    )
                db.execute(
                    "INSERT INTO saved_wines (user_id, wine_slug, status, source, wine_snapshot, "
                    "added_at, updated_at, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        user_id,
                        slug,
                        status,
                        source,
                        merged_snapshot(None, snapshot),
                        now,
                        now,
                        note or None,
                    ),
                )
            else:
                merged = merged_snapshot(current["wine_snapshot"], snapshot)
                kept_note = current["note"] if note is None else note or None
                db.execute(
                    "UPDATE saved_wines SET status = ?, updated_at = ?, wine_snapshot = ?, "
                    "note = ? WHERE user_id = ? AND wine_slug = ?",
                    (status, now, merged, kept_note, user_id, slug),
                )
            row = db.execute(SAVED_QUERY, {"user": user_id, "slug": slug}).fetchone()
        if created:
            LOG.info("Saved wine added (%s)", source)
        else:
            LOG.info("Saved wine changed")
        LOG.debug("Saved wine: %s", slug)
        return self._saved_view(row), created

    def unsave(self, user_id: str, slug: str) -> None:
        with self.db.transaction() as db:
            cursor = db.execute(
                "DELETE FROM saved_wines WHERE user_id = ? AND wine_slug = ?", (user_id, slug)
            )
        if cursor.rowcount == 0:
            raise AccountError("not_found", 404, "The wine is not saved")
        LOG.info("Saved wine removed")

    # ------------------------------------------------------------------- bots

    @staticmethod
    def _linked_user(db: sqlite3.Connection, provider: str, subject: int) -> str | None:
        row = db.execute(
            "SELECT user_id FROM identities WHERE provider = ? AND subject = ?",
            (provider, str(subject)),
        ).fetchone()
        return None if row is None else row["user_id"]

    def bot_record(
        self,
        consumer: str,
        subject: int,
        slug: str,
        snapshot: dict[str, Any] | None,
        replaces: str | None,
        at: int | None = None,
    ) -> dict[str, str]:
        """Record a wine that a chat showed today.

        `replaces` is the wine that the person rejected before they selected this one. Its date
        of the card day (`at`, see card_day) goes when the chat recorded that date; a date that
        another source recorded stays. The removal also runs when the switch is off: a removal
        is always allowed.
        """
        provider = BOT_PROVIDERS[consumer]
        now = self._now()
        with self.db.transaction() as db:
            user_id = self._linked_user(db, provider, subject)
            if user_id is None:
                result = {"status": "not_linked"}
            else:
                if replaces is not None and replaces != slug:
                    self._remove_day(db, user_id, replaces, card_day(at, now), provider)
                if self._save_history(db, user_id):
                    result = self._record(db, user_id, slug, provider, snapshot, now)
                else:
                    result = {"status": "off"}
        if result["status"] == "recorded":
            LOG.info("History recorded (%s)", provider)
            LOG.debug("History recorded: %s", slug)
        elif result["status"] == "not_linked":
            LOG.info("History record for a chat without a linked diary (%s)", provider)
        return result

    def bot_undo(
        self, consumer: str, subject: int, slug: str, at: int | None = None
    ) -> dict[str, str]:
        """Remove the date of a wine after «❌ Не совпало». The last date removes the wine.

        The date is the Moscow day of the result card (`at`, see card_day). Only a date that
        this chat recorded goes. A date of another source stays, and the answer is `absent`.
        """
        provider = BOT_PROVIDERS[consumer]
        now = self._now()
        with self.db.transaction() as db:
            user_id = self._linked_user(db, provider, subject)
            if user_id is None:
                return {"status": "not_linked"}
            removed = self._remove_day(db, user_id, slug, card_day(at, now), provider)
        if removed:
            LOG.info("History date removed by the chat (%s)", provider)
        return {"status": "removed" if removed else "absent"}

    # --------------------------------------------------- application tokens

    def app_wines(self, user_id: str, cursor: str | None, limit: int) -> dict[str, Any]:
        """The history for an MCP client, newest first, with an opaque cursor."""
        after = decode_cursor(cursor) if cursor else None
        with self.db.transaction() as db:
            user = db.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone()
            if user is None:
                raise AccountError("app_token_invalid", 401, "The application token is not valid")
            rows = self._history_rows(db, user_id, after=after, limit=limit + 1)
        page = rows[:limit]
        items = []
        for row in page:
            wine = _wine(row["snapshot"]) or {}
            items.append(
                {
                    "slug": row["wine_slug"],
                    "name": wine.get("name"),
                    "producer": wine.get("producer"),
                    "color": wine.get("color"),
                    "sugar": wine.get("sugar"),
                    "first_met_at": iso(row["first_met_at"]),
                    "last_met_at": iso(row["last_met_at"]),
                    "days": row["days_count"],
                    "sources": _sources(row["sources"]),
                    "saved_status": row["saved_status"],
                }
            )
        next_cursor = None
        if len(rows) > limit:
            next_cursor = encode_cursor(page[-1]["last_met_at"], page[-1]["wine_slug"])
        return {"items": items, "next_cursor": next_cursor}
