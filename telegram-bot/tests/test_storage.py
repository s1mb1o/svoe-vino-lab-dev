import sqlite3

import pytest

from chto_za_vino_bot.storage import ArtifactWrite, CandidateRecord, Repository, StepTiming


def reserve(repository, now, message_id=1):
    return repository.reserve(
        chat_id=100,
        message_id=message_id,
        user_id=200,
        username="tester",
        first_name="Test",
        last_name=None,
        file_id=f"file-{message_id}",
        file_unique_id=f"unique-{message_id}",
        now=now,
        limit=2,
        window_seconds=3600,
    )


def test_rate_limit_is_rolling_and_persistent(tmp_path):
    path = tmp_path / "bot.sqlite3"
    repository = Repository(path)
    assert reserve(repository, 1000, 1).allowed
    assert reserve(repository, 1100, 2).allowed
    limited = reserve(repository, 1200, 3)
    assert not limited.allowed
    assert limited.retry_after_seconds == 3400
    repository.close()

    reopened = Repository(path)
    assert not reserve(reopened, 1200, 4).allowed
    assert reserve(reopened, 4701, 5).allowed
    reopened.close()


def test_duplicate_message_does_not_use_quota(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    assert reserve(repository, 1000, 1).allowed
    duplicate = reserve(repository, 1001, 1)
    assert duplicate.duplicate
    assert reserve(repository, 1002, 2).allowed
    repository.close()


def test_step_timings_are_append_only_and_persistent(tmp_path):
    path = tmp_path / "bot.sqlite3"
    repository = Repository(path)
    reservation = reserve(repository, 1000, 1)
    assert reservation.request_id is not None

    repository.record_step_timing(
        request_id=reservation.request_id,
        step="moderation",
        started_at_ms=1_000_100,
        duration_ms=240,
        outcome="ok",
    )
    repository.record_step_timing(
        request_id=reservation.request_id,
        step="moderation",
        started_at_ms=1_000_400,
        duration_ms=80,
        outcome="failed",
    )
    repository.close()

    reopened = Repository(path)
    assert reopened.step_timings(reservation.request_id) == [
        StepTiming("moderation", 1_000_100, 240, "ok"),
        StepTiming("moderation", 1_000_400, 80, "failed"),
    ]
    reopened.close()


def test_step_timing_rejects_invalid_outcome(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    reservation = reserve(repository, 1000, 1)
    assert reservation.request_id is not None

    with pytest.raises(ValueError):
        repository.record_step_timing(
            request_id=reservation.request_id,
            step="moderation",
            started_at_ms=1_000_100,
            duration_ms=240,
            outcome="unknown",
        )
    repository.close()


def test_artifacts_are_ordered_safe_only_and_replaced_on_retry(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    reservation = reserve(repository, 1000, 1)
    assert reservation.request_id is not None
    request_id = reservation.request_id
    repository.update(request_id, status="recognized", moderation_safe=1)
    artifacts = [
        ArtifactWrite(
            artifact_key="second",
            step="quality",
            title="Second",
            description="Second artifact.",
            mime_type="image/png",
            relative_path="artifacts/second.png",
            width=20,
            height=30,
            ordinal=20,
            metadata={"score": 0.8},
        ),
        ArtifactWrite(
            artifact_key="first",
            step="input",
            title="First",
            description="First artifact.",
            mime_type="image/jpeg",
            relative_path="artifacts/first.jpg",
            width=10,
            height=15,
            ordinal=10,
            metadata={},
        ),
    ]
    repository.replace_artifacts(request_id, artifacts, 1100)

    assert [item.artifact_key for item in repository.artifacts(request_id)] == [
        "first",
        "second",
    ]
    assert repository.visible_artifact(request_id, "first") is not None
    repository.update(
        request_id,
        moderation_safe=None,
        moderation_category="disabled",
    )
    assert repository.visible_artifact(request_id, "first") is not None
    repository.update(request_id, moderation_safe=0)
    assert repository.visible_artifact(request_id, "first") is None
    repository.upsert_artifacts(
        request_id,
        [
            ArtifactWrite(
                artifact_key="censored_preview",
                step="censored",
                title="Censored",
                description="Blurred preview.",
                mime_type="image/jpeg",
                relative_path="artifacts/censored.jpg",
                width=10,
                height=15,
                ordinal=1,
                metadata={},
                exposure="censored",
            )
        ],
        1150,
    )
    assert [item.artifact_key for item in repository.visible_artifacts(request_id)] == [
        "censored_preview"
    ]
    assert repository.visible_artifact(request_id, "censored_preview") is not None
    repository.update(request_id, moderation_safe=1)
    assert repository.visible_artifact(request_id, "censored_preview") is None
    assert repository.request_retry(request_id, 1200) == "requested"
    assert repository.artifacts(request_id) == []
    repository.close()


def test_queue_rejection_does_not_use_quota(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    rejected = reserve(repository, 1000, 1)
    assert rejected.request_id is not None
    repository.update(rejected.request_id, status="queue_rejected")

    assert reserve(repository, 1001, 2).allowed
    assert reserve(repository, 1002, 3).allowed
    repository.close()


def test_rate_limit_reset_preserves_history_and_survives_restart(tmp_path):
    path = tmp_path / "bot.sqlite3"
    repository = Repository(path)
    assert reserve(repository, 1000, 1).allowed
    assert reserve(repository, 1100, 2).allowed
    assert not reserve(repository, 1200, 3).allowed

    assert repository.reset_rate_limit(200, 1200, 3600) == 2
    stats = repository.stats(200, 1200, 3600)
    assert stats.total == 2
    assert stats.user_window == 0
    repository.close()

    reopened = Repository(path)
    assert reserve(reopened, 1201, 4).allowed
    assert reopened.stats(200, 1201, 3600).total == 3
    reopened.close()


def test_stats_are_personal_unless_global_scope_is_requested(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    assert reserve(repository, 1000, 1).allowed
    second_user = repository.reserve(
        chat_id=101,
        message_id=2,
        user_id=201,
        username="other",
        first_name="Other",
        last_name=None,
        file_id="file-other",
        file_unique_id="unique-other",
        now=1001,
        limit=2,
        window_seconds=3600,
    )
    assert second_user.allowed

    assert repository.stats(200, 1100, 3600).total == 1
    assert repository.stats(200, 1100, 3600, include_all=True).total == 2
    repository.close()


def test_user_listing_and_username_lookup(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    assert reserve(repository, 1000, 1).allowed

    users, total = repository.list_users(
        page=1,
        page_size=20,
        now=1200,
        window_seconds=3600,
    )

    assert total == 1
    assert users[0].user_id == 200
    assert users[0].username == "tester"
    assert users[0].total_requests == 1
    assert users[0].window_requests == 1
    assert users[0].last_request_at == 1000
    assert repository.user_by_username("TESTER").user_id == 200
    repository.close()


def test_pending_requests_are_restored_in_received_order(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    first = reserve(repository, 1000, 1)
    second = reserve(repository, 1001, 2)
    assert first.request_id is not None
    assert second.request_id is not None
    repository.update(first.request_id, status="queued")
    repository.update(second.request_id, status="processing")

    pending = repository.pending_requests()

    assert [request.request_id for request in pending] == [
        first.request_id,
        second.request_id,
    ]
    assert [request.file_id for request in pending] == ["file-1", "file-2"]
    assert [request.message_id for request in pending] == [1, 2]
    assert [request.feedback_enabled for request in pending] == [True, True]
    repository.close()


def test_api_requests_are_exempt_hidden_from_users_and_not_restored(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    request_id = repository.create_api_request(now=1000)
    record = repository.admin_request(request_id)

    assert record is not None
    assert record.request_source == "api"
    assert repository.pending_requests() == []
    users, total = repository.list_users(
        page=1,
        page_size=20,
        now=1100,
        window_seconds=3600,
    )
    assert users == []
    assert total == 0
    assert repository.admin_overview(1100).users == 0

    repository.update(request_id, status="recognized", moderation_safe=1)
    assert repository.request_retry(request_id, 1200) == "unavailable"
    repository.update(request_id, status="processing")
    assert repository.fail_interrupted_api_requests() == 1
    failed = repository.admin_request(request_id)
    assert failed is not None
    assert failed.status == "internal_failed"
    assert failed.error_code == "interrupted"
    repository.close()


def test_admin_overview_and_request_listing(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    first = reserve(repository, 1000, 1)
    second = repository.reserve(
        chat_id=101,
        message_id=2,
        user_id=201,
        username="other",
        first_name="Other",
        last_name=None,
        file_id="file-other",
        file_unique_id="unique-other",
        now=1001,
        limit=2,
        window_seconds=3600,
    )
    assert first.request_id is not None
    assert second.request_id is not None
    repository.update(
        first.request_id,
        status="recognized",
        moderation_safe=1,
        recognition_name="Test wine",
    )
    repository.update(second.request_id, status="quarantined", moderation_safe=0)
    assert (
        repository.save_moderation_appeal(
            request_id=second.request_id,
            user_id=201,
            now=1100,
        )
        == "saved"
    )

    overview = repository.admin_overview(1200)
    requests, total = repository.list_admin_requests(page=1, page_size=25)
    appeals, appeal_total = repository.list_admin_requests(
        page=1,
        page_size=25,
        appeals_only=True,
    )

    assert overview.total == 2
    assert overview.users == 2
    assert overview.recognized == 1
    assert overview.quarantined == 1
    assert overview.moderation_appeals == 1
    assert total == 2
    assert requests[0].request_id == second.request_id
    assert requests[1].recognition_name == "Test wine"
    assert appeal_total == 1
    assert appeals[0].request_id == second.request_id
    repository.close()


def test_safe_admin_retry_is_persistent_and_claimed_once(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    reservation = reserve(repository, 1000, 1)
    assert reservation.request_id is not None
    repository.update(
        reservation.request_id,
        status="recognized",
        moderation_safe=1,
        recognition_name="Old result",
    )
    assert (
        repository.save_feedback(
            request_id=reservation.request_id,
            user_id=200,
            matched=False,
            now=1100,
        )
        == "saved"
    )

    assert repository.request_retry(reservation.request_id, 1200) == "requested"
    assert repository.request_retry(reservation.request_id, 1201) == "already_requested"
    pending = repository.retry_requests()
    assert len(pending) == 1
    assert pending[0].received_at == 1200
    assert repository.admin_request(reservation.request_id).recognition_name is None
    assert repository.admin_request(reservation.request_id).feedback_match is None
    assert repository.claim_retry_request(reservation.request_id)
    assert not repository.claim_retry_request(reservation.request_id)
    assert repository.release_retry_request(reservation.request_id)
    assert repository.admin_request(reservation.request_id).retry_count == 1
    repository.close()


def test_bypassed_admin_retry_is_persistent_and_claimed_once(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    reservation = reserve(repository, 1000, 1)
    assert reservation.request_id is not None
    repository.update(
        reservation.request_id,
        status="recognized",
        moderation_safe=None,
        moderation_category="disabled",
    )

    assert repository.request_retry(reservation.request_id, 1200) == "requested"
    assert [item.request_id for item in repository.retry_requests()] == [
        reservation.request_id
    ]
    assert repository.claim_retry_request(reservation.request_id)
    repository.close()


def test_admin_retry_rejects_unsafe_or_unmoderated_request(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    unsafe = reserve(repository, 1000, 1)
    unmoderated = reserve(repository, 1001, 2)
    assert unsafe.request_id is not None
    assert unmoderated.request_id is not None
    repository.update(unsafe.request_id, status="quarantined", moderation_safe=0)
    repository.update(unmoderated.request_id, status="moderation_failed")

    assert repository.request_retry(unsafe.request_id, 1200) == "unavailable"
    assert repository.request_retry(unmoderated.request_id, 1200) == "unavailable"
    assert repository.retry_requests() == []
    repository.close()


def test_feedback_is_saved_once_and_survives_restart(tmp_path):
    path = tmp_path / "bot.sqlite3"
    repository = Repository(path)
    reservation = reserve(repository, 1000, 1)
    assert reservation.request_id is not None
    repository.update(reservation.request_id, status="recognized")

    assert (
        repository.save_feedback(
            request_id=reservation.request_id,
            user_id=200,
            matched=True,
            now=1200,
        )
        == "saved"
    )
    repository.close()

    reopened = Repository(path)
    assert (
        reopened.save_feedback(
            request_id=reservation.request_id,
            user_id=200,
            matched=False,
            now=1300,
        )
        == "already_saved"
    )
    reopened.close()

    connection = sqlite3.connect(path)
    stored = connection.execute(
        "SELECT feedback_match, feedback_at FROM requests WHERE request_id = ?",
        (reservation.request_id,),
    ).fetchone()
    connection.close()
    assert stored == (1, 1200)


def test_feedback_rejects_another_user_and_album_request(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    single = reserve(repository, 1000, 1)
    assert single.request_id is not None
    repository.update(single.request_id, status="recognized")
    assert (
        repository.save_feedback(
            request_id=single.request_id,
            user_id=201,
            matched=True,
            now=1200,
        )
        == "unavailable"
    )

    album = repository.reserve(
        chat_id=100,
        message_id=2,
        user_id=200,
        username="tester",
        first_name="Test",
        last_name=None,
        file_id="file-2",
        file_unique_id="unique-2",
        now=1001,
        limit=2,
        window_seconds=3600,
        feedback_enabled=False,
    )
    assert album.request_id is not None
    repository.update(album.request_id, status="recognized")
    assert (
        repository.save_feedback(
            request_id=album.request_id,
            user_id=200,
            matched=False,
            now=1200,
        )
        == "unavailable"
    )
    repository.close()


def test_age_status_is_persistent(tmp_path):
    path = tmp_path / "bot.sqlite3"
    repository = Repository(path)
    assert repository.age_status(200) is None

    repository.set_age_status(
        user_id=200,
        username="tester",
        first_name="Test",
        last_name=None,
        status="adult",
        now=1000,
    )
    assert repository.age_status(200) == "adult"
    repository.close()

    reopened = Repository(path)
    assert reopened.age_status(200) == "adult"
    reopened.close()


def test_age_status_rejects_unknown_value(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    with pytest.raises(ValueError):
        repository.set_age_status(
            user_id=200,
            username=None,
            first_name=None,
            last_name=None,
            status="unknown",
            now=1000,
        )
    repository.close()


def test_existing_database_gets_age_columns(tmp_path):
    path = tmp_path / "bot.sqlite3"
    connection = sqlite3.connect(path)
    connection.execute(
        """
        CREATE TABLE users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            first_seen_at INTEGER NOT NULL,
            last_seen_at INTEGER NOT NULL
        )
        """
    )
    connection.commit()
    connection.close()

    repository = Repository(path)
    repository.set_age_status(
        user_id=200,
        username=None,
        first_name=None,
        last_name=None,
        status="minor",
        now=1000,
    )
    assert repository.age_status(200) == "minor"
    repository.close()


def test_existing_database_gets_request_control_columns(tmp_path):
    path = tmp_path / "bot.sqlite3"
    connection = sqlite3.connect(path)
    connection.execute(
        """
        CREATE TABLE users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            first_seen_at INTEGER NOT NULL,
            last_seen_at INTEGER NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE requests (
            request_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            received_at INTEGER NOT NULL,
            status TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE request_artifacts (
            request_id TEXT NOT NULL,
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
            PRIMARY KEY(request_id, artifact_key)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE request_candidates (
            request_id TEXT NOT NULL,
            rank INTEGER NOT NULL,
            slug TEXT NOT NULL,
            score REAL NOT NULL,
            PRIMARY KEY(request_id, rank),
            UNIQUE(request_id, slug)
        )
        """
    )
    connection.execute(
        "INSERT INTO request_candidates(request_id, rank, slug, score) "
        "VALUES ('old', 1, 'wine-a', 0.9)"
    )
    connection.commit()
    connection.close()

    repository = Repository(path)
    old_candidates = repository.candidates("old")
    repository.close()

    connection = sqlite3.connect(path)
    columns = {row[1] for row in connection.execute("PRAGMA table_info(requests)")}
    artifact_columns = {
        row[1] for row in connection.execute("PRAGMA table_info(request_artifacts)")
    }
    candidate_columns = {
        row[1] for row in connection.execute("PRAGMA table_info(request_candidates)")
    }
    connection.close()
    assert "matcher_pipeline" in columns
    assert "wine_json" in candidate_columns
    assert old_candidates == [CandidateRecord(1, "wine-a", 0.9, None)]
    assert {
        "rate_limit_exempt",
        "feedback_enabled",
        "feedback_match",
        "feedback_at",
        "image_phash",
        "image_dhash",
        "moderation_appeal_at",
        "quality_acceptable",
        "recognition_score",
        "recognition_margin",
        "feedback_selected_slug",
        "feedback_selected_rank",
        "feedback_alternative_at",
    } <= columns
    assert "exposure" in artifact_columns


def test_candidates_and_alternative_feedback_are_persistent(tmp_path):
    path = tmp_path / "bot.sqlite3"
    repository = Repository(path)
    reservation = reserve(repository, 1000, 1)
    assert reservation.request_id is not None
    request_id = reservation.request_id
    repository.update(request_id, status="recognized")
    repository.replace_candidates(
        request_id,
        [
            CandidateRecord(1, "wine-a", 0.9),
            CandidateRecord(2, "wine-b", 0.8),
            CandidateRecord(3, "wine-c", 0.7),
            CandidateRecord(4, "wine-d", 0.6),
        ],
    )
    assert repository.save_feedback(
        request_id=request_id,
        user_id=200,
        matched=False,
        now=1200,
    ) == "saved"

    assert [item.slug for item in repository.candidates(request_id)] == [
        "wine-a",
        "wine-b",
        "wine-c",
        "wine-d",
    ]
    assert repository.save_alternative_feedback(
        request_id=request_id,
        user_id=200,
        rank=3,
        now=1300,
    ) == "saved"
    assert repository.save_alternative_feedback(
        request_id=request_id,
        user_id=200,
        rank=2,
        now=1400,
    ) == "already_saved"
    repository.close()

    connection = sqlite3.connect(path)
    stored = connection.execute(
        """
        SELECT feedback_selected_rank, feedback_selected_slug, feedback_alternative_at
        FROM requests WHERE request_id = ?
        """,
        (request_id,),
    ).fetchone()
    connection.close()
    assert stored == (3, "wine-c", 1300)


def test_moderation_appeal_is_source_user_only_and_saved_once(tmp_path):
    path = tmp_path / "bot.sqlite3"
    repository = Repository(path)
    reservation = reserve(repository, 1000, 1)
    assert reservation.request_id is not None
    request_id = reservation.request_id
    repository.update(request_id, status="quarantined")

    assert repository.save_moderation_appeal(
        request_id=request_id,
        user_id=201,
        now=1100,
    ) == "unavailable"
    assert repository.save_moderation_appeal(
        request_id=request_id,
        user_id=200,
        now=1200,
    ) == "saved"
    assert repository.save_moderation_appeal(
        request_id=request_id,
        user_id=200,
        now=1300,
    ) == "already_saved"
    repository.close()

    connection = sqlite3.connect(path)
    stored = connection.execute(
        "SELECT moderation_appeal_at FROM requests WHERE request_id = ?",
        (request_id,),
    ).fetchone()
    connection.close()
    assert stored == (1200,)


def test_nothing_from_alternatives_is_stored_as_rank_zero(tmp_path):
    path = tmp_path / "bot.sqlite3"
    repository = Repository(path)
    reservation = reserve(repository, 1000, 1)
    assert reservation.request_id is not None
    request_id = reservation.request_id
    repository.update(request_id, status="recognized")
    assert repository.save_feedback(
        request_id=request_id,
        user_id=200,
        matched=False,
        now=1200,
    ) == "saved"

    assert repository.save_alternative_feedback(
        request_id=request_id,
        user_id=200,
        rank=0,
        now=1300,
    ) == "saved"
    repository.close()

    connection = sqlite3.connect(path)
    stored = connection.execute(
        """
        SELECT feedback_selected_rank, feedback_selected_slug
        FROM requests WHERE request_id = ?
        """,
        (request_id,),
    ).fetchone()
    connection.close()
    assert stored == (0, None)


def test_candidate_cards_are_stored_and_an_empty_list_clears_them(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    reservation = reserve(repository, 1000, 1)
    assert reservation.request_id is not None
    request_id = reservation.request_id
    card = {"name": "Вино А", "page_url": "https://vino-svoe.ru/wines/wine-a", "qr_urls": []}
    repository.replace_candidates(
        request_id,
        [CandidateRecord(1, "wine-a", 0.9, card), CandidateRecord(2, "wine-b", 0.8)],
    )

    assert repository.candidates(request_id) == [
        CandidateRecord(1, "wine-a", 0.9, card),
        CandidateRecord(2, "wine-b", 0.8, None),
    ]

    repository.replace_candidates(request_id, [])
    assert repository.candidates(request_id) == []
    with pytest.raises(ValueError, match="consecutive ranks"):
        repository.replace_candidates(request_id, [CandidateRecord(2, "wine-b", 0.8)])
    repository.close()


def test_matcher_pipeline_is_stored_and_reset_by_an_admin_retry(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    reservation = reserve(repository, 1000, 1)
    assert reservation.request_id is not None
    request_id = reservation.request_id
    repository.update(
        request_id,
        status="recognized",
        moderation_safe=1,
        matcher_pipeline="test-pipeline",
    )
    repository.replace_candidates(request_id, [CandidateRecord(1, "wine-a", 0.9)])

    assert repository.admin_request(request_id).matcher_pipeline == "test-pipeline"
    assert repository.request_retry(request_id, 1200) == "requested"
    assert repository.admin_request(request_id).matcher_pipeline is None
    assert repository.candidates(request_id) == []
    repository.close()
