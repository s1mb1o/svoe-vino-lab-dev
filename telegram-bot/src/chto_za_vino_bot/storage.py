from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class Reservation:
    allowed: bool
    request_id: str | None
    used: int
    remaining: int
    retry_after_seconds: int
    duplicate: bool = False


@dataclass(frozen=True, slots=True)
class Stats:
    total: int
    last_day: int
    users: int
    recognized: int
    failed: int
    quarantined: int
    abstained: int
    user_window: int


@dataclass(frozen=True, slots=True)
class UserIdentity:
    user_id: int
    username: str | None
    first_name: str | None
    last_name: str | None


@dataclass(frozen=True, slots=True)
class UserSummary:
    user_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    total_requests: int
    window_requests: int
    last_request_at: int | None


@dataclass(frozen=True, slots=True)
class PendingRequest:
    request_id: str
    chat_id: int
    message_id: int
    received_at: int
    file_id: str
    feedback_enabled: bool


@dataclass(frozen=True, slots=True)
class CandidateRecord:
    rank: int
    slug: str
    score: float
    # The wine card of the matcher answer. A request of an old version has no card.
    card: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class StepTiming:
    step: str
    started_at_ms: int
    duration_ms: int
    outcome: str


@dataclass(frozen=True, slots=True)
class ArtifactRecord:
    artifact_key: str
    step: str
    title: str
    description: str
    mime_type: str
    relative_path: str
    width: int
    height: int
    ordinal: int
    metadata_json: str
    created_at: int
    exposure: str


@dataclass(frozen=True, slots=True)
class ArtifactWrite:
    artifact_key: str
    step: str
    title: str
    description: str
    mime_type: str
    relative_path: str
    width: int
    height: int
    ordinal: int
    metadata: dict[str, object]
    exposure: str = "safe"


@dataclass(frozen=True, slots=True)
class AdminOverview:
    total: int
    last_day: int
    users: int
    recognized: int
    abstained: int
    quarantined: int
    failed: int
    pending: int
    moderation_appeals: int
    positive_feedback: int
    negative_feedback: int


@dataclass(frozen=True, slots=True)
class AdminRequestRecord:
    request_id: str
    request_source: str
    user_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    received_at: int
    status: str
    error_code: str | None
    duration_ms: int | None
    image_bytes: int | None
    image_sha256: str | None
    image_phash: str | None
    image_dhash: str | None
    moderation_safe: bool | None
    moderation_category: str | None
    moderation_confidence: float | None
    moderation_reason: str | None
    moderation_appeal_at: int | None
    quality_acceptable: bool | None
    quality_issues: str | None
    quality_blur_variance: float | None
    quality_glare_ratio: float | None
    quality_bottle_area_ratio: float | None
    quality_label_area_ratio: float | None
    recognition_slug: str | None
    recognition_name: str | None
    recognition_page_url: str | None
    recognition_score: float | None
    recognition_margin: float | None
    feedback_match: bool | None
    feedback_at: int | None
    feedback_selected_slug: str | None
    feedback_selected_rank: int | None
    feedback_alternative_at: int | None
    retry_count: int
    retry_requested_at: int | None
    matcher_pipeline: str | None = None


class Repository:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._initialize()

    def _initialize(self) -> None:
        with self._connection:
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA foreign_keys=ON")
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    first_seen_at INTEGER NOT NULL,
                    last_seen_at INTEGER NOT NULL,
                    age_status TEXT,
                    age_decided_at INTEGER
                );

                CREATE TABLE IF NOT EXISTS requests (
                    request_id TEXT PRIMARY KEY,
                    request_source TEXT NOT NULL DEFAULT 'telegram',
                    chat_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL REFERENCES users(user_id),
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    received_at INTEGER NOT NULL,
                    telegram_file_id TEXT NOT NULL,
                    telegram_file_unique_id TEXT NOT NULL,
                    image_bytes INTEGER,
                    image_sha256 TEXT,
                    image_phash TEXT,
                    image_dhash TEXT,
                    moderation_safe INTEGER,
                    moderation_category TEXT,
                    moderation_confidence REAL,
                    moderation_reason TEXT,
                    moderation_appeal_at INTEGER,
                    storage_path TEXT,
                    quality_acceptable INTEGER,
                    quality_issues TEXT,
                    quality_blur_variance REAL,
                    quality_glare_ratio REAL,
                    quality_bottle_area_ratio REAL,
                    quality_label_area_ratio REAL,
                    recognition_slug TEXT,
                    recognition_name TEXT,
                    recognition_page_url TEXT,
                    recognition_score REAL,
                    recognition_margin REAL,
                    matcher_pipeline TEXT,
                    status TEXT NOT NULL,
                    error_code TEXT,
                    duration_ms INTEGER,
                    rate_limit_exempt INTEGER NOT NULL DEFAULT 0,
                    feedback_enabled INTEGER NOT NULL DEFAULT 0,
                    feedback_match INTEGER,
                    feedback_at INTEGER,
                    feedback_selected_slug TEXT,
                    feedback_selected_rank INTEGER,
                    feedback_alternative_at INTEGER,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    retry_requested_at INTEGER,
                    UNIQUE(chat_id, message_id)
                );

                CREATE TABLE IF NOT EXISTS request_candidates (
                    request_id TEXT NOT NULL REFERENCES requests(request_id) ON DELETE CASCADE,
                    rank INTEGER NOT NULL,
                    slug TEXT NOT NULL,
                    score REAL NOT NULL,
                    wine_json TEXT,
                    PRIMARY KEY(request_id, rank),
                    UNIQUE(request_id, slug)
                );

                CREATE TABLE IF NOT EXISTS request_step_timings (
                    timing_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT NOT NULL REFERENCES requests(request_id) ON DELETE CASCADE,
                    step TEXT NOT NULL,
                    started_at_ms INTEGER NOT NULL,
                    duration_ms INTEGER NOT NULL,
                    outcome TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS request_step_timings_request
                ON request_step_timings(request_id, timing_id);

                CREATE TABLE IF NOT EXISTS request_artifacts (
                    request_id TEXT NOT NULL REFERENCES requests(request_id) ON DELETE CASCADE,
                    artifact_key TEXT NOT NULL,
                    step TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    width INTEGER NOT NULL,
                    height INTEGER NOT NULL,
                    ordinal INTEGER NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    exposure TEXT NOT NULL DEFAULT 'safe',
                    PRIMARY KEY(request_id, artifact_key)
                );

                CREATE INDEX IF NOT EXISTS request_artifacts_order
                ON request_artifacts(request_id, ordinal, artifact_key);

                CREATE INDEX IF NOT EXISTS requests_user_time
                ON requests(user_id, received_at);

                CREATE INDEX IF NOT EXISTS requests_status_time
                ON requests(status, received_at);
                """
            )
            user_columns = {
                row["name"] for row in self._connection.execute("PRAGMA table_info(users)")
            }
            if "age_status" not in user_columns:
                self._connection.execute("ALTER TABLE users ADD COLUMN age_status TEXT")
            if "age_decided_at" not in user_columns:
                self._connection.execute("ALTER TABLE users ADD COLUMN age_decided_at INTEGER")
            request_columns = {
                row["name"]
                for row in self._connection.execute("PRAGMA table_info(requests)")
            }
            if "request_source" not in request_columns:
                self._connection.execute(
                    "ALTER TABLE requests "
                    "ADD COLUMN request_source TEXT NOT NULL DEFAULT 'telegram'"
                )
            if "rate_limit_exempt" not in request_columns:
                self._connection.execute(
                    "ALTER TABLE requests "
                    "ADD COLUMN rate_limit_exempt INTEGER NOT NULL DEFAULT 0"
                )
            if "feedback_enabled" not in request_columns:
                self._connection.execute(
                    "ALTER TABLE requests "
                    "ADD COLUMN feedback_enabled INTEGER NOT NULL DEFAULT 0"
                )
            if "feedback_match" not in request_columns:
                self._connection.execute(
                    "ALTER TABLE requests ADD COLUMN feedback_match INTEGER"
                )
            if "feedback_at" not in request_columns:
                self._connection.execute(
                    "ALTER TABLE requests ADD COLUMN feedback_at INTEGER"
                )
            new_columns = {
                "image_phash": "TEXT",
                "image_dhash": "TEXT",
                "moderation_appeal_at": "INTEGER",
                "quality_acceptable": "INTEGER",
                "quality_issues": "TEXT",
                "quality_blur_variance": "REAL",
                "quality_glare_ratio": "REAL",
                "quality_bottle_area_ratio": "REAL",
                "quality_label_area_ratio": "REAL",
                "recognition_score": "REAL",
                "recognition_margin": "REAL",
                "feedback_selected_slug": "TEXT",
                "feedback_selected_rank": "INTEGER",
                "feedback_alternative_at": "INTEGER",
                "retry_count": "INTEGER NOT NULL DEFAULT 0",
                "retry_requested_at": "INTEGER",
                "matcher_pipeline": "TEXT",
            }
            for name, column_type in new_columns.items():
                if name not in request_columns:
                    self._connection.execute(
                        f"ALTER TABLE requests ADD COLUMN {name} {column_type}"
                    )
            candidate_columns = {
                row["name"]
                for row in self._connection.execute(
                    "PRAGMA table_info(request_candidates)"
                )
            }
            if "wine_json" not in candidate_columns:
                self._connection.execute(
                    "ALTER TABLE request_candidates ADD COLUMN wine_json TEXT"
                )
            artifact_columns = {
                row["name"]
                for row in self._connection.execute(
                    "PRAGMA table_info(request_artifacts)"
                )
            }
            if "exposure" not in artifact_columns:
                self._connection.execute(
                    "ALTER TABLE request_artifacts "
                    "ADD COLUMN exposure TEXT NOT NULL DEFAULT 'safe'"
                )

    def age_status(self, user_id: int) -> str | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT age_status FROM users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        if row is None:
            return None
        value = row["age_status"]
        return value if value in {"adult", "minor"} else None

    def set_age_status(
        self,
        *,
        user_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        status: str,
        now: int,
    ) -> None:
        if status not in {"adult", "minor"}:
            raise ValueError("age status must be adult or minor")
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO users(
                    user_id, username, first_name, last_name, first_seen_at, last_seen_at,
                    age_status, age_decided_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    last_name = excluded.last_name,
                    last_seen_at = excluded.last_seen_at,
                    age_status = excluded.age_status,
                    age_decided_at = excluded.age_decided_at
                """,
                (
                    user_id,
                    username,
                    first_name,
                    last_name,
                    now,
                    now,
                    status,
                    now,
                ),
            )

    def reserve(
        self,
        *,
        chat_id: int,
        message_id: int,
        user_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        file_id: str,
        file_unique_id: str,
        now: int,
        limit: int,
        window_seconds: int,
        feedback_enabled: bool = True,
    ) -> Reservation:
        cutoff = now - window_seconds
        with self._lock, self._connection:
            existing = self._connection.execute(
                "SELECT request_id FROM requests WHERE chat_id = ? AND message_id = ?",
                (chat_id, message_id),
            ).fetchone()
            if existing:
                return Reservation(False, existing["request_id"], 0, 0, 0, duplicate=True)

            self._connection.execute(
                """
                INSERT INTO users(user_id, username, first_name, last_name, first_seen_at, last_seen_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    last_name = excluded.last_name,
                    last_seen_at = excluded.last_seen_at
                """,
                (user_id, username, first_name, last_name, now, now),
            )
            rows = self._connection.execute(
                """
                SELECT received_at FROM requests
                WHERE user_id = ?
                  AND received_at > ?
                  AND status != 'queue_rejected'
                  AND rate_limit_exempt = 0
                ORDER BY received_at ASC
                """,
                (user_id, cutoff),
            ).fetchall()
            used = len(rows)
            if used >= limit:
                retry_after = max(1, rows[0]["received_at"] + window_seconds - now)
                return Reservation(False, None, used, 0, retry_after)

            request_id = str(uuid.uuid4())
            self._connection.execute(
                """
                INSERT INTO requests(
                    request_id, chat_id, message_id, user_id, username, first_name,
                    last_name, received_at, telegram_file_id, telegram_file_unique_id,
                    status, feedback_enabled
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'received', ?)
                """,
                (
                    request_id,
                    chat_id,
                    message_id,
                    user_id,
                    username,
                    first_name,
                    last_name,
                    now,
                    file_id,
                    file_unique_id,
                    int(feedback_enabled),
                ),
            )
            return Reservation(True, request_id, used + 1, limit - used - 1, 0)

    def create_api_request(self, *, now: int) -> str:
        request_id = str(uuid.uuid4())
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO users(
                    user_id, username, first_name, last_name, first_seen_at, last_seen_at,
                    age_status, age_decided_at
                ) VALUES (0, 'http_api', 'HTTP API', NULL, ?, ?, 'adult', ?)
                ON CONFLICT(user_id) DO UPDATE SET last_seen_at = excluded.last_seen_at
                """,
                (now, now, now),
            )
            message_id = int(
                self._connection.execute(
                    "SELECT COALESCE(MIN(message_id), 0) - 1 FROM requests WHERE chat_id = 0"
                ).fetchone()[0]
            )
            self._connection.execute(
                """
                INSERT INTO requests(
                    request_id, request_source, chat_id, message_id, user_id,
                    username, first_name, last_name, received_at, telegram_file_id,
                    telegram_file_unique_id, status, rate_limit_exempt, feedback_enabled
                ) VALUES (?, 'api', 0, ?, 0, 'http_api', 'HTTP API', NULL, ?, '', '',
                          'received', 1, 0)
                """,
                (request_id, message_id, now),
            )
        return request_id

    def update(self, request_id: str, **fields: object) -> None:
        allowed = {
            "image_bytes",
            "image_sha256",
            "image_phash",
            "image_dhash",
            "moderation_safe",
            "moderation_category",
            "moderation_confidence",
            "moderation_reason",
            "storage_path",
            "quality_acceptable",
            "quality_issues",
            "quality_blur_variance",
            "quality_glare_ratio",
            "quality_bottle_area_ratio",
            "quality_label_area_ratio",
            "recognition_slug",
            "recognition_name",
            "recognition_page_url",
            "recognition_score",
            "recognition_margin",
            "matcher_pipeline",
            "status",
            "error_code",
            "duration_ms",
        }
        unknown = set(fields) - allowed
        if unknown:
            raise ValueError(f"unknown request fields: {sorted(unknown)}")
        if not fields:
            return
        assignments = ", ".join(f"{name} = ?" for name in fields)
        values = list(fields.values()) + [request_id]
        with self._lock, self._connection:
            self._connection.execute(
                f"UPDATE requests SET {assignments} WHERE request_id = ?",
                values,
            )

    def stats(
        self,
        user_id: int,
        now: int,
        window_seconds: int,
        *,
        include_all: bool = False,
    ) -> Stats:
        cutoff_day = now - 86400
        cutoff_window = now - window_seconds
        with self._lock:
            if include_all:
                row = self._connection.execute(
                    """
                    SELECT
                        COUNT(*) AS total,
                        SUM(received_at > ?) AS last_day,
                        COUNT(DISTINCT CASE WHEN user_id != 0 THEN user_id END) AS users,
                        SUM(status = 'recognized') AS recognized,
                        SUM(status = 'abstained') AS abstained,
                        SUM(status IN (
                            'recognition_failed', 'moderation_failed', 'invalid_image',
                            'download_failed', 'internal_failed', 'queue_rejected',
                            'quality_failed', 'quality_rejected'
                        )) AS failed,
                        SUM(status = 'quarantined') AS quarantined
                    FROM requests
                    """,
                    (cutoff_day,),
                ).fetchone()
            else:
                row = self._connection.execute(
                    """
                    SELECT
                        COUNT(*) AS total,
                        SUM(received_at > ?) AS last_day,
                        COUNT(DISTINCT CASE WHEN user_id != 0 THEN user_id END) AS users,
                        SUM(status = 'recognized') AS recognized,
                        SUM(status = 'abstained') AS abstained,
                        SUM(status IN (
                            'recognition_failed', 'moderation_failed', 'invalid_image',
                            'download_failed', 'internal_failed', 'queue_rejected',
                            'quality_failed', 'quality_rejected'
                        )) AS failed,
                        SUM(status = 'quarantined') AS quarantined
                    FROM requests
                    WHERE user_id = ?
                    """,
                    (cutoff_day, user_id),
                ).fetchone()
            user_window = self._connection.execute(
                """
                SELECT COUNT(*) FROM requests
                WHERE user_id = ?
                  AND received_at > ?
                  AND status != 'queue_rejected'
                  AND rate_limit_exempt = 0
                """,
                (user_id, cutoff_window),
            ).fetchone()[0]
        return Stats(
            total=int(row["total"] or 0),
            last_day=int(row["last_day"] or 0),
            users=int(row["users"] or 0),
            recognized=int(row["recognized"] or 0),
            failed=int(row["failed"] or 0),
            quarantined=int(row["quarantined"] or 0),
            abstained=int(row["abstained"] or 0),
            user_window=int(user_window),
        )

    def user_by_id(self, user_id: int) -> UserIdentity | None:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT user_id, username, first_name, last_name
                FROM users
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
        return self._identity(row)

    def user_by_username(self, username: str) -> UserIdentity | None:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT user_id, username, first_name, last_name
                FROM users
                WHERE username IS NOT NULL AND lower(username) = lower(?)
                ORDER BY last_seen_at DESC, user_id DESC
                LIMIT 1
                """,
                (username,),
            ).fetchone()
        return self._identity(row)

    @staticmethod
    def _identity(row: sqlite3.Row | None) -> UserIdentity | None:
        if row is None:
            return None
        return UserIdentity(
            user_id=int(row["user_id"]),
            username=row["username"],
            first_name=row["first_name"],
            last_name=row["last_name"],
        )

    def reset_rate_limit(self, user_id: int, now: int, window_seconds: int) -> int:
        cutoff = now - window_seconds
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                UPDATE requests
                SET rate_limit_exempt = 1
                WHERE user_id = ?
                  AND received_at > ?
                  AND status != 'queue_rejected'
                  AND rate_limit_exempt = 0
                """,
                (user_id, cutoff),
            )
        return cursor.rowcount

    def save_feedback(
        self,
        *,
        request_id: str,
        user_id: int,
        matched: bool,
        now: int,
    ) -> str:
        with self._lock, self._connection:
            row = self._connection.execute(
                """
                SELECT user_id, status, feedback_enabled, feedback_match
                FROM requests
                WHERE request_id = ?
                """,
                (request_id,),
            ).fetchone()
            if (
                row is None
                or int(row["user_id"]) != user_id
                or row["status"] != "recognized"
                or not bool(row["feedback_enabled"])
            ):
                return "unavailable"
            if row["feedback_match"] is not None:
                return "already_saved"
            self._connection.execute(
                """
                UPDATE requests
                SET feedback_match = ?, feedback_at = ?
                WHERE request_id = ? AND feedback_match IS NULL
                """,
                (int(matched), now, request_id),
            )
        return "saved"

    def replace_candidates(
        self,
        request_id: str,
        candidates: list[CandidateRecord],
    ) -> None:
        if any(item.rank != index for index, item in enumerate(candidates, 1)):
            raise ValueError("candidates must have consecutive ranks")
        with self._lock, self._connection:
            self._connection.execute(
                "DELETE FROM request_candidates WHERE request_id = ?",
                (request_id,),
            )
            self._connection.executemany(
                """
                INSERT INTO request_candidates(request_id, rank, slug, score, wine_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        request_id,
                        item.rank,
                        item.slug,
                        item.score,
                        (
                            json.dumps(item.card, ensure_ascii=False, sort_keys=True)
                            if item.card is not None
                            else None
                        ),
                    )
                    for item in candidates
                ],
            )

    def candidates(self, request_id: str) -> list[CandidateRecord]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT rank, slug, score, wine_json
                FROM request_candidates
                WHERE request_id = ?
                ORDER BY rank
                """,
                (request_id,),
            ).fetchall()
        return [
            CandidateRecord(
                int(row["rank"]),
                row["slug"],
                float(row["score"]),
                self._stored_card(row["wine_json"]),
            )
            for row in rows
        ]

    @staticmethod
    def _stored_card(value: str | None) -> dict[str, object] | None:
        if value is None:
            return None
        try:
            card = json.loads(value)
        except ValueError:
            return None
        return card if isinstance(card, dict) else None

    def record_step_timing(
        self,
        *,
        request_id: str,
        step: str,
        started_at_ms: int,
        duration_ms: int,
        outcome: str,
    ) -> None:
        if not step or len(step) > 64:
            raise ValueError("step must contain 1 to 64 characters")
        if started_at_ms < 0 or duration_ms < 0:
            raise ValueError("timing values must not be negative")
        if outcome not in {"ok", "failed", "cancelled"}:
            raise ValueError("timing outcome is invalid")
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO request_step_timings(
                    request_id, step, started_at_ms, duration_ms, outcome
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (request_id, step, started_at_ms, duration_ms, outcome),
            )

    def step_timings(self, request_id: str) -> list[StepTiming]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT step, started_at_ms, duration_ms, outcome
                FROM request_step_timings
                WHERE request_id = ?
                ORDER BY timing_id
                """,
                (request_id,),
            ).fetchall()
        return [
            StepTiming(
                step=row["step"],
                started_at_ms=int(row["started_at_ms"]),
                duration_ms=int(row["duration_ms"]),
                outcome=row["outcome"],
            )
            for row in rows
        ]

    def save_alternative_feedback(
        self,
        *,
        request_id: str,
        user_id: int,
        rank: int,
        now: int,
    ) -> str:
        if rank not in {0, 2, 3, 4}:
            return "unavailable"
        with self._lock, self._connection:
            row = self._connection.execute(
                """
                SELECT user_id, status, feedback_enabled, feedback_match,
                       feedback_alternative_at
                FROM requests
                WHERE request_id = ?
                """,
                (request_id,),
            ).fetchone()
            if (
                row is None
                or int(row["user_id"]) != user_id
                or row["status"] != "recognized"
                or not bool(row["feedback_enabled"])
                or row["feedback_match"] != 0
            ):
                return "unavailable"
            if row["feedback_alternative_at"] is not None:
                return "already_saved"
            slug = None
            if rank:
                candidate = self._connection.execute(
                    """
                    SELECT slug FROM request_candidates
                    WHERE request_id = ? AND rank = ?
                    """,
                    (request_id, rank),
                ).fetchone()
                if candidate is None:
                    return "unavailable"
                slug = candidate["slug"]
            self._connection.execute(
                """
                UPDATE requests
                SET feedback_selected_slug = ?, feedback_selected_rank = ?,
                    feedback_alternative_at = ?
                WHERE request_id = ? AND feedback_alternative_at IS NULL
                """,
                (slug, rank, now, request_id),
            )
        return "saved"

    def save_moderation_appeal(
        self,
        *,
        request_id: str,
        user_id: int,
        now: int,
    ) -> str:
        with self._lock, self._connection:
            row = self._connection.execute(
                """
                SELECT user_id, status, moderation_appeal_at
                FROM requests
                WHERE request_id = ?
                """,
                (request_id,),
            ).fetchone()
            if row is None or int(row["user_id"]) != user_id or row["status"] != "quarantined":
                return "unavailable"
            if row["moderation_appeal_at"] is not None:
                return "already_saved"
            self._connection.execute(
                """
                UPDATE requests SET moderation_appeal_at = ?
                WHERE request_id = ? AND moderation_appeal_at IS NULL
                """,
                (now, request_id),
            )
        return "saved"

    def list_users(
        self,
        *,
        page: int,
        page_size: int,
        now: int,
        window_seconds: int,
    ) -> tuple[list[UserSummary], int]:
        if page <= 0:
            raise ValueError("page must be positive")
        if page_size <= 0:
            raise ValueError("page size must be positive")
        cutoff = now - window_seconds
        offset = (page - 1) * page_size
        with self._lock:
            total = int(
                self._connection.execute(
                    "SELECT COUNT(*) FROM users WHERE user_id != 0"
                ).fetchone()[0]
            )
            rows = self._connection.execute(
                """
                SELECT
                    users.user_id,
                    users.username,
                    users.first_name,
                    users.last_name,
                    COUNT(requests.request_id) AS total_requests,
                    SUM(
                        requests.received_at > ?
                        AND requests.status != 'queue_rejected'
                        AND requests.rate_limit_exempt = 0
                    ) AS window_requests,
                    MAX(requests.received_at) AS last_request_at
                FROM users
                LEFT JOIN requests ON requests.user_id = users.user_id
                WHERE users.user_id != 0
                GROUP BY users.user_id
                ORDER BY
                    COALESCE(MAX(requests.received_at), users.last_seen_at) DESC,
                    users.user_id DESC
                LIMIT ? OFFSET ?
                """,
                (cutoff, page_size, offset),
            ).fetchall()
        users = [
            UserSummary(
                user_id=int(row["user_id"]),
                username=row["username"],
                first_name=row["first_name"],
                last_name=row["last_name"],
                total_requests=int(row["total_requests"] or 0),
                window_requests=int(row["window_requests"] or 0),
                last_request_at=(
                    int(row["last_request_at"])
                    if row["last_request_at"] is not None
                    else None
                ),
            )
            for row in rows
        ]
        return users, total

    def pending_requests(self) -> list[PendingRequest]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT
                    request_id,
                    chat_id,
                    message_id,
                    received_at,
                    telegram_file_id,
                    feedback_enabled
                FROM requests
                WHERE status IN ('received', 'queued', 'processing')
                  AND request_source = 'telegram'
                ORDER BY received_at ASC, rowid ASC
                """
            ).fetchall()
        return [
            PendingRequest(
                request_id=row["request_id"],
                chat_id=int(row["chat_id"]),
                message_id=int(row["message_id"]),
                received_at=int(row["received_at"]),
                file_id=row["telegram_file_id"],
                feedback_enabled=bool(row["feedback_enabled"]),
            )
            for row in rows
        ]

    def fail_interrupted_api_requests(self) -> int:
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                UPDATE requests
                SET status = 'internal_failed', error_code = 'interrupted'
                WHERE request_source = 'api'
                  AND status IN ('received', 'queued', 'processing')
                """
            )
        return cursor.rowcount

    def admin_overview(self, now: int) -> AdminOverview:
        cutoff_day = now - 86400
        with self._lock:
            row = self._connection.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(received_at > ?) AS last_day,
                    COUNT(DISTINCT CASE WHEN user_id != 0 THEN user_id END) AS users,
                    SUM(status = 'recognized') AS recognized,
                    SUM(status = 'abstained') AS abstained,
                    SUM(status = 'quarantined') AS quarantined,
                    SUM(status IN (
                        'recognition_failed', 'moderation_failed', 'invalid_image',
                        'download_failed', 'internal_failed', 'queue_rejected',
                        'quality_failed', 'quality_rejected'
                    )) AS failed,
                    SUM(status IN (
                        'received', 'queued', 'processing', 'retry_requested'
                    )) AS pending,
                    SUM(moderation_appeal_at IS NOT NULL) AS moderation_appeals,
                    SUM(feedback_match = 1) AS positive_feedback,
                    SUM(feedback_match = 0) AS negative_feedback
                FROM requests
                """,
                (cutoff_day,),
            ).fetchone()
        return AdminOverview(
            total=int(row["total"] or 0),
            last_day=int(row["last_day"] or 0),
            users=int(row["users"] or 0),
            recognized=int(row["recognized"] or 0),
            abstained=int(row["abstained"] or 0),
            quarantined=int(row["quarantined"] or 0),
            failed=int(row["failed"] or 0),
            pending=int(row["pending"] or 0),
            moderation_appeals=int(row["moderation_appeals"] or 0),
            positive_feedback=int(row["positive_feedback"] or 0),
            negative_feedback=int(row["negative_feedback"] or 0),
        )

    def list_admin_requests(
        self,
        *,
        page: int,
        page_size: int,
        status: str | None = None,
        appeals_only: bool = False,
    ) -> tuple[list[AdminRequestRecord], int]:
        if page <= 0:
            raise ValueError("page must be positive")
        if page_size <= 0:
            raise ValueError("page size must be positive")
        conditions: list[str] = []
        values: list[object] = []
        if status:
            conditions.append("status = ?")
            values.append(status)
        if appeals_only:
            conditions.append("moderation_appeal_at IS NOT NULL")
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        offset = (page - 1) * page_size
        with self._lock:
            total = int(
                self._connection.execute(
                    f"SELECT COUNT(*) FROM requests {where}", values
                ).fetchone()[0]
            )
            rows = self._connection.execute(
                f"""
                SELECT {self._admin_request_columns()}
                FROM requests
                {where}
                ORDER BY received_at DESC, rowid DESC
                LIMIT ? OFFSET ?
                """,
                [*values, page_size, offset],
            ).fetchall()
        return [self._admin_request_record(row) for row in rows], total

    def admin_request(self, request_id: str) -> AdminRequestRecord | None:
        with self._lock:
            row = self._connection.execute(
                f"""
                SELECT {self._admin_request_columns()}
                FROM requests
                WHERE request_id = ?
                """,
                (request_id,),
            ).fetchone()
        return self._admin_request_record(row) if row is not None else None

    def replace_artifacts(
        self,
        request_id: str,
        artifacts: list[ArtifactWrite],
        now: int,
    ) -> None:
        with self._lock, self._connection:
            self._connection.execute(
                "DELETE FROM request_artifacts WHERE request_id = ?",
                (request_id,),
            )
            self._insert_artifacts(request_id, artifacts, now)

    def upsert_artifacts(
        self,
        request_id: str,
        artifacts: list[ArtifactWrite],
        now: int,
    ) -> None:
        with self._lock, self._connection:
            self._insert_artifacts(request_id, artifacts, now)

    def _insert_artifacts(
        self,
        request_id: str,
        artifacts: list[ArtifactWrite],
        now: int,
    ) -> None:
        invalid_exposures = {
            item.exposure for item in artifacts if item.exposure not in {"safe", "censored"}
        }
        if invalid_exposures:
            raise ValueError(f"invalid artifact exposures: {sorted(invalid_exposures)}")
        self._connection.executemany(
            """
            INSERT INTO request_artifacts(
                request_id, artifact_key, step, title, description, mime_type,
                relative_path, width, height, ordinal, metadata_json, created_at,
                exposure
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(request_id, artifact_key) DO UPDATE SET
                step = excluded.step,
                title = excluded.title,
                description = excluded.description,
                mime_type = excluded.mime_type,
                relative_path = excluded.relative_path,
                width = excluded.width,
                height = excluded.height,
                ordinal = excluded.ordinal,
                metadata_json = excluded.metadata_json,
                created_at = excluded.created_at,
                exposure = excluded.exposure
            """,
            [
                (
                    request_id,
                    item.artifact_key,
                    item.step,
                    item.title,
                    item.description,
                    item.mime_type,
                    item.relative_path,
                    item.width,
                    item.height,
                    item.ordinal,
                    json.dumps(item.metadata, ensure_ascii=False, sort_keys=True),
                    now,
                    item.exposure,
                )
                for item in artifacts
            ],
        )

    def artifacts(self, request_id: str) -> list[ArtifactRecord]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT artifact_key, step, title, description, mime_type,
                       relative_path, width, height, ordinal, metadata_json, created_at,
                       exposure
                FROM request_artifacts
                WHERE request_id = ?
                ORDER BY ordinal ASC, artifact_key ASC
                """,
                (request_id,),
            ).fetchall()
        return [ArtifactRecord(**dict(row)) for row in rows]

    def visible_artifacts(self, request_id: str) -> list[ArtifactRecord]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT a.artifact_key, a.step, a.title, a.description, a.mime_type,
                       a.relative_path, a.width, a.height, a.ordinal,
                       a.metadata_json, a.created_at, a.exposure
                FROM request_artifacts AS a
                JOIN requests AS r ON r.request_id = a.request_id
                WHERE a.request_id = ? AND (
                    (r.moderation_safe = 1 AND a.exposure = 'safe') OR
                    (r.moderation_safe = 0 AND a.exposure = 'censored')
                )
                ORDER BY a.ordinal ASC, a.artifact_key ASC
                """,
                (request_id,),
            ).fetchall()
        return [ArtifactRecord(**dict(row)) for row in rows]

    def visible_artifact(
        self,
        request_id: str,
        artifact_key: str,
    ) -> ArtifactRecord | None:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT a.artifact_key, a.step, a.title, a.description, a.mime_type,
                       a.relative_path, a.width, a.height, a.ordinal,
                       a.metadata_json, a.created_at, a.exposure
                FROM request_artifacts AS a
                JOIN requests AS r ON r.request_id = a.request_id
                WHERE a.request_id = ? AND a.artifact_key = ?
                  AND (
                    (r.moderation_safe = 1 AND a.exposure = 'safe') OR
                    (r.moderation_safe = 0 AND a.exposure = 'censored')
                  )
                """,
                (request_id, artifact_key),
            ).fetchone()
        return ArtifactRecord(**dict(row)) if row is not None else None

    def safe_source(self, request_id: str) -> tuple[int, str] | None:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT received_at, storage_path
                FROM requests
                WHERE request_id = ? AND moderation_safe = 1
                  AND storage_path LIKE 'accepted/%'
                """,
                (request_id,),
            ).fetchone()
        if row is None:
            return None
        return int(row["received_at"]), str(row["storage_path"])

    def censored_source(self, request_id: str) -> tuple[int, str] | None:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT received_at, storage_path
                FROM requests
                WHERE request_id = ? AND moderation_safe = 0
                  AND storage_path LIKE 'quarantine/%'
                """,
                (request_id,),
            ).fetchone()
        if row is None:
            return None
        return int(row["received_at"]), str(row["storage_path"])

    @staticmethod
    def _admin_request_columns() -> str:
        return """
            request_id, request_source, user_id, username, first_name, last_name, received_at,
            status, error_code, duration_ms, image_bytes, image_sha256,
            image_phash, image_dhash, moderation_safe, moderation_category,
            moderation_confidence, moderation_reason, moderation_appeal_at,
            quality_acceptable, quality_issues, quality_blur_variance,
            quality_glare_ratio, quality_bottle_area_ratio,
            quality_label_area_ratio, recognition_slug, recognition_name,
            recognition_page_url, recognition_score, recognition_margin,
            feedback_match, feedback_at, feedback_selected_slug,
            feedback_selected_rank, feedback_alternative_at, retry_count,
            retry_requested_at, matcher_pipeline
        """

    @staticmethod
    def _admin_request_record(row: sqlite3.Row) -> AdminRequestRecord:
        moderation_safe = row["moderation_safe"]
        quality_acceptable = row["quality_acceptable"]
        feedback_match = row["feedback_match"]
        return AdminRequestRecord(
            request_id=row["request_id"],
            request_source=row["request_source"],
            user_id=int(row["user_id"]),
            username=row["username"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            received_at=int(row["received_at"]),
            status=row["status"],
            error_code=row["error_code"],
            duration_ms=row["duration_ms"],
            image_bytes=row["image_bytes"],
            image_sha256=row["image_sha256"],
            image_phash=row["image_phash"],
            image_dhash=row["image_dhash"],
            moderation_safe=(
                bool(moderation_safe) if moderation_safe is not None else None
            ),
            moderation_category=row["moderation_category"],
            moderation_confidence=row["moderation_confidence"],
            moderation_reason=row["moderation_reason"],
            moderation_appeal_at=row["moderation_appeal_at"],
            quality_acceptable=(
                bool(quality_acceptable) if quality_acceptable is not None else None
            ),
            quality_issues=row["quality_issues"],
            quality_blur_variance=row["quality_blur_variance"],
            quality_glare_ratio=row["quality_glare_ratio"],
            quality_bottle_area_ratio=row["quality_bottle_area_ratio"],
            quality_label_area_ratio=row["quality_label_area_ratio"],
            recognition_slug=row["recognition_slug"],
            recognition_name=row["recognition_name"],
            recognition_page_url=row["recognition_page_url"],
            recognition_score=row["recognition_score"],
            recognition_margin=row["recognition_margin"],
            feedback_match=(
                bool(feedback_match) if feedback_match is not None else None
            ),
            feedback_at=row["feedback_at"],
            feedback_selected_slug=row["feedback_selected_slug"],
            feedback_selected_rank=row["feedback_selected_rank"],
            feedback_alternative_at=row["feedback_alternative_at"],
            retry_count=int(row["retry_count"] or 0),
            retry_requested_at=row["retry_requested_at"],
            matcher_pipeline=row["matcher_pipeline"],
        )

    def request_retry(self, request_id: str, now: int) -> str:
        with self._lock, self._connection:
            row = self._connection.execute(
                """
                SELECT status, moderation_safe, request_source
                FROM requests
                WHERE request_id = ?
                """,
                (request_id,),
            ).fetchone()
            if (
                row is None
                or row["moderation_safe"] != 1
                or row["request_source"] != "telegram"
            ):
                return "unavailable"
            if row["status"] in {"retry_requested", "queued", "processing", "received"}:
                return "already_requested"
            self._connection.execute(
                """
                UPDATE requests
                SET status = 'retry_requested', error_code = NULL, duration_ms = NULL,
                    quality_acceptable = NULL, quality_issues = NULL,
                    quality_blur_variance = NULL, quality_glare_ratio = NULL,
                    quality_bottle_area_ratio = NULL, quality_label_area_ratio = NULL,
                    recognition_slug = NULL, recognition_name = NULL,
                    recognition_page_url = NULL, recognition_score = NULL,
                    recognition_margin = NULL, matcher_pipeline = NULL,
                    feedback_match = NULL,
                    feedback_at = NULL, feedback_selected_slug = NULL,
                    feedback_selected_rank = NULL, feedback_alternative_at = NULL,
                    retry_count = retry_count + 1, retry_requested_at = ?
                WHERE request_id = ?
                """,
                (now, request_id),
            )
            self._connection.execute(
                "DELETE FROM request_candidates WHERE request_id = ?",
                (request_id,),
            )
            self._connection.execute(
                "DELETE FROM request_artifacts WHERE request_id = ?",
                (request_id,),
            )
        return "requested"

    def retry_requests(self, *, limit: int = 100) -> list[PendingRequest]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT
                    request_id, chat_id, message_id,
                    COALESCE(retry_requested_at, received_at) AS received_at,
                    telegram_file_id, feedback_enabled
                FROM requests
                WHERE status = 'retry_requested' AND moderation_safe = 1
                  AND request_source = 'telegram'
                ORDER BY retry_requested_at ASC, rowid ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            PendingRequest(
                request_id=row["request_id"],
                chat_id=int(row["chat_id"]),
                message_id=int(row["message_id"]),
                received_at=int(row["received_at"]),
                file_id=row["telegram_file_id"],
                feedback_enabled=bool(row["feedback_enabled"]),
            )
            for row in rows
        ]

    def claim_retry_request(self, request_id: str) -> bool:
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                UPDATE requests SET status = 'queued'
                WHERE request_id = ?
                  AND status = 'retry_requested'
                  AND moderation_safe = 1
                """,
                (request_id,),
            )
        return cursor.rowcount == 1

    def release_retry_request(self, request_id: str) -> bool:
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                UPDATE requests SET status = 'retry_requested'
                WHERE request_id = ? AND status = 'queued'
                """,
                (request_id,),
            )
        return cursor.rowcount == 1

    def close(self) -> None:
        with self._lock:
            self._connection.close()


class ImageStore:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._accepted = root / "accepted"
        self._quarantine = root / "quarantine"
        self._accepted.mkdir(parents=True, exist_ok=True, mode=0o750)
        self._quarantine.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self._quarantine, 0o700)

    def save(self, request_id: str, received_at: int, body: bytes, safe: bool) -> tuple[str, str]:
        date = datetime.fromtimestamp(received_at, tz=UTC)
        base = self._accepted if safe else self._quarantine
        directory = base / date.strftime("%Y/%m/%d")
        directory.mkdir(parents=True, exist_ok=True, mode=0o750 if safe else 0o700)
        if not safe:
            os.chmod(directory, 0o700)
        final = directory / f"{request_id}.jpg"
        temporary = directory / f".{request_id}.{uuid.uuid4().hex}.tmp"
        with temporary.open("xb") as target:
            target.write(body)
            target.flush()
            os.fsync(target.fileno())
        os.chmod(temporary, 0o640 if safe else 0o600)
        os.replace(temporary, final)
        relative = final.relative_to(self._root).as_posix()
        return relative, hashlib.sha256(body).hexdigest()

    def read_accepted(self, relative_path: str) -> bytes:
        return self._read_within(relative_path, self._accepted, "accepted")

    def read_quarantine(self, relative_path: str) -> bytes:
        return self._read_within(relative_path, self._quarantine, "quarantine")

    def _read_within(self, relative_path: str, root: Path, label: str) -> bytes:
        candidate = (self._root / relative_path).resolve()
        resolved_root = root.resolve()
        if candidate == resolved_root or resolved_root not in candidate.parents:
            raise ValueError(f"{label} image path is invalid")
        return candidate.read_bytes()


class ArtifactStore:
    _KEY = re.compile(r"^[a-z0-9][a-z0-9_-]{0,79}$")
    _EXTENSIONS: ClassVar[dict[str, str]] = {"image/jpeg": "jpg", "image/png": "png"}

    def __init__(self, root: Path) -> None:
        self._data_root = root.resolve()
        self._root = root / "artifacts"
        self._root.mkdir(parents=True, exist_ok=True, mode=0o750)

    def save(
        self,
        request_id: str,
        received_at: int,
        artifact_key: str,
        mime_type: str,
        body: bytes,
    ) -> str:
        if not self._KEY.fullmatch(artifact_key):
            raise ValueError("artifact key is invalid")
        extension = self._EXTENSIONS.get(mime_type)
        if extension is None:
            raise ValueError("artifact MIME type is invalid")
        date = datetime.fromtimestamp(received_at, tz=UTC)
        directory = self._root / date.strftime("%Y/%m/%d") / request_id
        directory.mkdir(parents=True, exist_ok=True, mode=0o750)
        final = directory / f"{artifact_key}.{extension}"
        temporary = directory / f".{artifact_key}.{uuid.uuid4().hex}.tmp"
        with temporary.open("xb") as target:
            target.write(body)
            target.flush()
            os.fsync(target.fileno())
        os.chmod(temporary, 0o640)
        os.replace(temporary, final)
        return final.relative_to(self._data_root).as_posix()

    def resolve(self, relative_path: str) -> Path:
        candidate = (self._data_root / relative_path).resolve()
        root = self._root.resolve()
        if candidate == root or root not in candidate.parents:
            raise ValueError("artifact path is invalid")
        return candidate
