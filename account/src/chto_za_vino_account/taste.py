"""Stated preferences and tasting ratings. Saved-wine notes remain private to the site.

Tasting notes are shared with the owner's application tokens. Never log their contents.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .db import Database
from .diary import normalize_note, snapshot_json
from .service import AccountError, iso


class Preferences(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal[1] = 1
    colors: list[Literal["white", "red", "rose", "orange"]] = Field(
        default_factory=list, max_length=4
    )
    sparkling: bool | None = None
    sweetness: list[Literal["dry", "semi_dry", "semi_sweet", "sweet"]] = Field(
        default_factory=list, max_length=4
    )
    body: Literal["light", "medium", "full", "any"] = "any"
    freshness: Literal["fresh", "soft", "any"] = "any"
    grapes: list[Annotated[str, Field(min_length=1, max_length=80)]] = Field(
        default_factory=list, max_length=16
    )

    @field_validator("grapes")
    @classmethod
    def clean_grapes(cls, values: list[str]) -> list[str]:
        cleaned = [normalize_note(value) for value in values]
        if any(not value or "\n" in value or "\t" in value for value in cleaned):
            raise ValueError("Invalid grape name")
        return cleaned

    @model_validator(mode="after")
    def distinct(self) -> Self:
        for values in (self.colors, self.sweetness, self.grapes):
            if len({value.casefold() for value in values}) != len(values):
                raise ValueError("Preference choices must be distinct")
        return self


class TasteData:
    def __init__(self, db: Database, clock: Callable[[], float]) -> None:
        self.db = db
        self.clock = clock

    def preferences(self, user_id: str) -> dict | None:
        with self.db.transaction() as db:
            row = db.execute("SELECT preferences FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            raise AccountError("session_invalid", 401, "The account no longer exists")
        return json.loads(row["preferences"]) if row["preferences"] else None

    def set_preferences(self, user_id: str, preferences: dict | None) -> None:
        with self.db.transaction() as db:
            db.execute(
                "UPDATE users SET preferences = ? WHERE id = ?",
                (snapshot_json(preferences) if preferences is not None else None, user_id),
            )

    def ratings(self, user_id: str) -> list[dict]:
        with self.db.transaction() as db:
            rows = db.execute(
                "SELECT wine_slug, rating, note, wine_snapshot, updated_at FROM wine_ratings "
                "WHERE user_id = ? ORDER BY updated_at DESC, wine_slug",
                (user_id,),
            ).fetchall()
        return [self.view(row) for row in rows]

    @staticmethod
    def view(row) -> dict:
        return {
            "slug": row["wine_slug"],
            "rating": row["rating"],
            "note": row["note"],
            "updated_at": iso(row["updated_at"]),
            "wine": json.loads(row["wine_snapshot"]) if row["wine_snapshot"] else None,
        }

    def rate(self, user_id: str, slug: str, rating: int, note: str | None, snapshot: dict | None):
        with self.db.transaction() as db:
            exists = db.execute(
                "SELECT 1 FROM wine_ratings WHERE user_id = ? AND wine_slug = ?", (user_id, slug)
            ).fetchone()
            count = db.execute(
                "SELECT COUNT(*) FROM wine_ratings WHERE user_id = ?", (user_id,)
            ).fetchone()[0]
            if not exists and count >= 5000:
                raise AccountError("ratings_limit", 409, "Remove a rating before adding another")
            db.execute(
                "INSERT INTO wine_ratings (user_id, wine_slug, rating, note, wine_snapshot, "
                "updated_at) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (user_id, wine_slug) "
                "DO UPDATE SET rating = excluded.rating, note = excluded.note, "
                "wine_snapshot = COALESCE(excluded.wine_snapshot, wine_ratings.wine_snapshot), "
                "updated_at = excluded.updated_at",
                (
                    user_id,
                    slug,
                    rating,
                    note,
                    snapshot_json(snapshot) if snapshot else None,
                    int(self.clock()),
                ),
            )
            row = db.execute(
                "SELECT * FROM wine_ratings WHERE user_id = ? AND wine_slug = ?", (user_id, slug)
            ).fetchone()
        return self.view(row)

    def remove_rating(self, user_id: str, slug: str) -> None:
        with self.db.transaction() as db:
            db.execute(
                "DELETE FROM wine_ratings WHERE user_id = ? AND wine_slug = ?", (user_id, slug)
            )
