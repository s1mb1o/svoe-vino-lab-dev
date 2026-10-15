import io
import sqlite3

import pytest
from PIL import Image

from chto_za_vino_max_bot.storage import (
    SQLITE_MAX_INTEGER,
    ArtifactStore,
    ArtifactWrite,
    CandidateRecord,
    ImageStore,
    PendingRequest,
    Repository,
    SentMessage,
    StepTiming,
)


@pytest.mark.parametrize(
    ("image_format", "suffix"),
    [("JPEG", ".jpg"), ("PNG", ".png"), ("WEBP", ".webp")],
)
def test_image_store_preserves_the_validated_image_format(tmp_path, image_format, suffix):
    output = io.BytesIO()
    Image.new("RGB", (20, 30), "darkred").save(output, format=image_format)
    store = ImageStore(tmp_path)

    relative_path, _ = store.save("request-1", 1000, output.getvalue(), True)

    assert relative_path.endswith(suffix)
    assert (tmp_path / relative_path).read_bytes() == output.getvalue()


@pytest.mark.parametrize("request_id", ["", ".", "..", "a/b", "../request-1"])
def test_request_copy_deletion_rejects_a_request_id_that_is_not_a_path_name(
    tmp_path, request_id
):
    with pytest.raises(ValueError):
        ImageStore(tmp_path).delete_accepted(request_id)
    with pytest.raises(ValueError):
        ArtifactStore(tmp_path).delete_request(request_id)


def photo_url(message_id, photo_index=0):
    return f"https://i.oneme.example/{message_id}/{photo_index}.jpg"


def photo_token(message_id, photo_index=0):
    return f"token-{message_id}-{photo_index}"


def reserve(
    repository,
    now,
    message_id="mid.1",
    *,
    photo_index=0,
    chat_id=100,
    chat_type="dialog",
    user_id=200,
    username="tester",
    first_name="Test",
    photo_id=9000,
    feedback_enabled=True,
    photo_source="body",
):
    return repository.reserve(
        chat_id=chat_id,
        chat_type=chat_type,
        message_id=message_id,
        photo_index=photo_index,
        user_id=user_id,
        username=username,
        first_name=first_name,
        last_name=None,
        photo_id=photo_id,
        photo_url=photo_url(message_id, photo_index),
        photo_token=photo_token(message_id, photo_index),
        now=now,
        limit=2,
        window_seconds=3600,
        feedback_enabled=feedback_enabled,
        photo_source=photo_source,
    )


def inbox_update(update_key, *, user_id=200, update_type="message_created", text="photo"):
    """Return one inbox row: (update_key, update_type, user_id, payload)."""
    payload = {"update_type": update_type, "timestamp": 1000, "text": text}
    return update_key, update_type, user_id, payload


def test_rate_limit_is_rolling_and_persistent(tmp_path):
    path = tmp_path / "bot.sqlite3"
    repository = Repository(path)
    assert reserve(repository, 1000, "mid.1").allowed
    assert reserve(repository, 1100, "mid.2").allowed
    limited = reserve(repository, 1200, "mid.3")
    assert not limited.allowed
    assert limited.retry_after_seconds == 3400
    repository.close()

    reopened = Repository(path)
    assert not reserve(reopened, 1200, "mid.4").allowed
    assert reserve(reopened, 4701, "mid.5").allowed
    reopened.close()


def test_duplicate_message_does_not_use_quota(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    first = reserve(repository, 1000, "mid.1")
    assert first.allowed
    duplicate = reserve(repository, 1001, "mid.1")
    assert duplicate.duplicate
    assert not duplicate.allowed
    assert duplicate.request_id == first.request_id
    assert reserve(repository, 1002, "mid.2").allowed
    repository.close()


def test_album_images_of_one_message_are_separate_requests(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    first = reserve(repository, 1000, "mid.album", photo_index=0, feedback_enabled=False)
    second = reserve(repository, 1000, "mid.album", photo_index=1, feedback_enabled=False)
    limited = reserve(repository, 1000, "mid.album", photo_index=2, feedback_enabled=False)

    assert first.allowed
    assert second.allowed
    assert first.request_id != second.request_id
    # The limit is reached in the middle of the album. The remaining image uses no quota.
    assert not limited.allowed
    assert not limited.duplicate
    assert limited.request_id is None

    # A replay of the update admits only the image that does not have a request yet.
    replay = [
        reserve(repository, 4601, "mid.album", photo_index=index, feedback_enabled=False)
        for index in range(3)
    ]
    assert [item.duplicate for item in replay] == [True, True, False]
    assert [item.request_id for item in replay[:2]] == [first.request_id, second.request_id]
    assert replay[2].allowed

    # The same message ID in another chat is another message.
    other_chat = reserve(repository, 4602, "mid.album", photo_index=0, chat_id=101)
    assert other_chat.allowed
    assert not other_chat.duplicate
    assert repository.stats(200, 4602, 3600).total == 4
    repository.close()


def test_reserve_stores_the_max_photo_reference(tmp_path):
    path = tmp_path / "bot.sqlite3"
    repository = Repository(path)
    reservation = reserve(
        repository,
        1000,
        "mid.forwarded",
        photo_index=2,
        chat_type="chat",
        photo_id=None,
        photo_source="forward",
    )
    assert reservation.request_id is not None
    record = repository.admin_request(reservation.request_id)
    assert record is not None
    assert record.request_source == "max"
    repository.close()

    connection = sqlite3.connect(path)
    stored = connection.execute(
        """
        SELECT request_source, chat_id, chat_type, message_id, photo_index, max_photo_id,
               max_photo_url, max_photo_token, photo_source, status
        FROM requests WHERE request_id = ?
        """,
        (reservation.request_id,),
    ).fetchone()
    connection.close()
    assert stored == (
        "max",
        100,
        "chat",
        "mid.forwarded",
        2,
        None,
        photo_url("mid.forwarded", 2),
        photo_token("mid.forwarded", 2),
        "forward",
        "received",
    )


def test_reserve_rejects_an_unknown_photo_source(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")

    with pytest.raises(ValueError, match="photo source"):
        reserve(repository, 1000, "mid.1", photo_source="link")

    assert repository.user_by_id(200) is None
    assert repository.pending_requests() == []
    repository.close()


def test_step_timings_are_append_only_and_persistent(tmp_path):
    path = tmp_path / "bot.sqlite3"
    repository = Repository(path)
    reservation = reserve(repository, 1000, "mid.1")
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
    reservation = reserve(repository, 1000, "mid.1")
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
    reservation = reserve(repository, 1000, "mid.1")
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
    rejected = reserve(repository, 1000, "mid.1")
    assert rejected.request_id is not None
    repository.update(rejected.request_id, status="queue_rejected")

    assert reserve(repository, 1001, "mid.2").allowed
    assert reserve(repository, 1002, "mid.3").allowed
    repository.close()


def test_rate_limit_reset_preserves_history_and_survives_restart(tmp_path):
    path = tmp_path / "bot.sqlite3"
    repository = Repository(path)
    assert reserve(repository, 1000, "mid.1").allowed
    assert reserve(repository, 1100, "mid.2").allowed
    assert not reserve(repository, 1200, "mid.3").allowed

    assert repository.reset_rate_limit(200, 1200, 3600) == 2
    stats = repository.stats(200, 1200, 3600)
    assert stats.total == 2
    assert stats.user_window == 0
    repository.close()

    reopened = Repository(path)
    assert reserve(reopened, 1201, "mid.4").allowed
    assert reopened.stats(200, 1201, 3600).total == 3
    reopened.close()


def test_stats_are_personal_unless_global_scope_is_requested(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    assert reserve(repository, 1000, "mid.1").allowed
    second_user = reserve(
        repository,
        1001,
        "mid.2",
        chat_id=101,
        user_id=201,
        username="other",
        first_name="Other",
    )
    assert second_user.allowed

    assert repository.stats(200, 1100, 3600).total == 1
    assert repository.stats(200, 1100, 3600, include_all=True).total == 2
    repository.close()


def test_user_listing_and_username_lookup(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    assert reserve(repository, 1000, "mid.1").allowed

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
    path = tmp_path / "bot.sqlite3"
    repository = Repository(path)
    first = reserve(repository, 1000, "mid.1", photo_id=9001)
    second = reserve(
        repository,
        1001,
        "mid.2",
        photo_index=1,
        chat_id=300,
        chat_type="chat",
        photo_id=None,
        photo_source="forward",
    )
    assert first.request_id is not None
    assert second.request_id is not None
    repository.update(first.request_id, status="queued")
    repository.update(second.request_id, status="processing")
    repository.close()

    # The string message ID, the photo source, the user, and the chat type survive a restart.
    reopened = Repository(path)
    pending = reopened.pending_requests()

    assert pending == [
        PendingRequest(
            request_id=first.request_id,
            chat_id=100,
            chat_type="dialog",
            user_id=200,
            message_id="mid.1",
            photo_index=0,
            received_at=1000,
            photo_id=9001,
            photo_url=photo_url("mid.1"),
            photo_source="body",
            feedback_enabled=True,
            stored_at=1000,
        ),
        PendingRequest(
            request_id=second.request_id,
            chat_id=300,
            chat_type="chat",
            user_id=200,
            message_id="mid.2",
            photo_index=1,
            received_at=1001,
            photo_id=None,
            photo_url=photo_url("mid.2", 1),
            photo_source="forward",
            feedback_enabled=True,
            stored_at=1001,
        ),
    ]
    reopened.close()


def test_refreshed_photo_url_is_restored_with_the_pending_request(tmp_path):
    path = tmp_path / "bot.sqlite3"
    repository = Repository(path)
    reservation = reserve(repository, 1000, "mid.1", photo_id=9001)
    assert reservation.request_id is not None

    repository.set_photo_url(reservation.request_id, "https://i.oneme.example/renewed.jpg")
    repository.close()

    reopened = Repository(path)
    [pending] = reopened.pending_requests()
    assert pending.photo_url == "https://i.oneme.example/renewed.jpg"
    assert pending.photo_id == 9001
    assert pending.message_id == "mid.1"
    reopened.close()


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


def test_api_requests_use_an_api_message_id_and_chat_type(tmp_path):
    path = tmp_path / "bot.sqlite3"
    repository = Repository(path)
    first = repository.create_api_request(now=1000)
    second = repository.create_api_request(now=1000)
    repository.close()

    connection = sqlite3.connect(path)
    stored = connection.execute(
        """
        SELECT request_id, request_source, chat_id, chat_type, message_id, photo_index
        FROM requests ORDER BY rowid
        """
    ).fetchall()
    connection.close()
    assert stored == [
        (first, "api", 0, "api", f"api:{first}", 0),
        (second, "api", 0, "api", f"api:{second}", 0),
    ]


def test_admin_overview_and_request_listing(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    first = reserve(repository, 1000, "mid.1")
    second = reserve(
        repository,
        1001,
        "mid.2",
        chat_id=101,
        user_id=201,
        username="other",
        first_name="Other",
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
    assert {item.request_source for item in requests} == {"max"}
    assert appeal_total == 1
    assert appeals[0].request_id == second.request_id
    repository.close()


def test_admin_lists_reject_a_pagination_offset_outside_the_sqlite_integer_range(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    excessive_page = SQLITE_MAX_INTEGER // 25 + 2

    with pytest.raises(ValueError, match="SQLite integer range"):
        repository.list_users(
            page=excessive_page,
            page_size=25,
            now=1000,
            window_seconds=3600,
        )
    with pytest.raises(ValueError, match="SQLite integer range"):
        repository.list_admin_requests(page=excessive_page, page_size=25)

    repository.close()


def test_safe_admin_retry_is_persistent_and_claimed_once(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    reservation = reserve(repository, 1000, "mid.1")
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
    assert pending[0].message_id == "mid.1"
    assert pending[0].photo_index == 0
    assert pending[0].chat_type == "dialog"
    assert pending[0].user_id == 200
    assert pending[0].photo_source == "body"
    assert repository.admin_request(reservation.request_id).recognition_name is None
    assert repository.admin_request(reservation.request_id).feedback_match is None
    assert repository.claim_retry_request(reservation.request_id)
    assert not repository.claim_retry_request(reservation.request_id)
    assert repository.release_retry_request(reservation.request_id)
    assert repository.admin_request(reservation.request_id).retry_count == 1
    repository.close()


def test_bypassed_admin_retry_is_persistent_and_claimed_once(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    reservation = reserve(repository, 1000, "mid.1")
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
    unsafe = reserve(repository, 1000, "mid.1")
    unmoderated = reserve(repository, 1001, "mid.2")
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
    reservation = reserve(repository, 1000, "mid.1")
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
    single = reserve(repository, 1000, "mid.1")
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

    # A MAX album is one message with several image attachments.
    album = reserve(repository, 1001, "mid.album", photo_index=0, feedback_enabled=False)
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


# The MAX bot starts with its own database, so it has no migration of an older schema.
# The Telegram migration tests are replaced by checks of the schema that a new database gets.
def test_new_database_has_age_columns_and_reopens_without_changes(tmp_path):
    path = tmp_path / "bot.sqlite3"
    repository = Repository(path)
    repository.set_age_status(
        user_id=200,
        username=None,
        first_name=None,
        last_name=None,
        status="minor",
        now=1000,
    )
    repository.close()

    reopened = Repository(path)
    assert reopened.age_status(200) == "minor"
    reopened.close()

    connection = sqlite3.connect(path)
    columns = {row[1] for row in connection.execute("PRAGMA table_info(users)")}
    connection.close()
    assert {"age_status", "age_decided_at"} <= columns


def test_new_database_has_max_request_columns_and_no_telegram_file_fields(tmp_path):
    path = tmp_path / "bot.sqlite3"
    Repository(path).close()

    connection = sqlite3.connect(path)
    # A candidate row without a stored wine card, as an older matcher answer would leave.
    connection.execute(
        "INSERT INTO request_candidates(request_id, rank, slug, score) "
        "VALUES ('old', 1, 'wine-a', 0.9)"
    )
    connection.commit()
    columns = {row[1]: row[2] for row in connection.execute("PRAGMA table_info(requests)")}
    artifact_columns = {
        row[1] for row in connection.execute("PRAGMA table_info(request_artifacts)")
    }
    candidate_columns = {
        row[1] for row in connection.execute("PRAGMA table_info(request_candidates)")
    }
    tables = {
        row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    unique_indexes = [
        [column[2] for column in connection.execute(f"PRAGMA index_info('{index[1]}')")]
        for index in connection.execute("PRAGMA index_list(requests)").fetchall()
        if index[2]
    ]
    connection.close()

    repository = Repository(path)
    old_candidates = repository.candidates("old")
    repository.close()

    assert old_candidates == [CandidateRecord(1, "wine-a", 0.9, None)]
    assert columns["message_id"] == "TEXT"
    assert {
        "request_source",
        "chat_type",
        "message_id",
        "photo_index",
        "max_photo_id",
        "max_photo_url",
        "max_photo_token",
        "photo_source",
        "matcher_pipeline",
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
        "retry_count",
        "retry_requested_at",
    } <= set(columns)
    assert not {"telegram_file_id", "telegram_file_unique_id"} & set(columns)
    assert ["chat_id", "message_id", "photo_index"] in unique_indexes
    assert "wine_json" in candidate_columns
    assert "exposure" in artifact_columns
    assert {"sent_messages", "update_inbox", "bot_state"} <= tables


def test_candidates_and_alternative_feedback_are_persistent(tmp_path):
    path = tmp_path / "bot.sqlite3"
    repository = Repository(path)
    reservation = reserve(repository, 1000, "mid.1")
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
    reservation = reserve(repository, 1000, "mid.1")
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
    reservation = reserve(repository, 1000, "mid.1")
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
    reservation = reserve(repository, 1000, "mid.1")
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
    reservation = reserve(repository, 1000, "mid.1")
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


def test_sent_message_is_stored_by_message_id_and_replaced(tmp_path):
    path = tmp_path / "bot.sqlite3"
    repository = Repository(path)
    reservation = reserve(repository, 1000, "mid.1")
    assert reservation.request_id is not None
    request_id = reservation.request_id
    assert repository.sent_message("mid.bot-1") is None

    repository.record_sent_message(
        message_id="mid.bot-1",
        request_id=request_id,
        chat_id=100,
        text="<b>Похоже, это:</b> Вино А",
        text_format="html",
        photo_token="photo-token-1",
        now=1100,
    )
    repository.record_sent_message(
        message_id="mid.bot-2",
        request_id=None,
        chat_id=100,
        text=None,
        text_format=None,
        photo_token=None,
        now=1101,
    )
    repository.close()

    reopened = Repository(path)
    assert reopened.sent_message("mid.bot-1") == SentMessage(
        message_id="mid.bot-1",
        request_id=request_id,
        chat_id=100,
        text="<b>Похоже, это:</b> Вино А",
        text_format="html",
        photo_token="photo-token-1",
    )
    assert reopened.sent_message("mid.bot-2") == SentMessage(
        "mid.bot-2", None, 100, None, None, None
    )

    # A second record of the same message ID replaces the stored body.
    reopened.record_sent_message(
        message_id="mid.bot-1",
        request_id=request_id,
        chat_id=100,
        text="Спасибо за оценку.",
        text_format=None,
        photo_token=None,
        now=1200,
    )
    assert reopened.sent_message("mid.bot-1") == SentMessage(
        "mid.bot-1", request_id, 100, "Спасибо за оценку.", None, None
    )
    reopened.close()


def test_user_deletion_removes_sent_messages_and_inbox_rows_of_the_user(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    own = reserve(repository, 1000, "mid.1")
    other = reserve(repository, 1001, "mid.2", chat_id=101, user_id=201, username="other")
    assert own.request_id is not None
    assert other.request_id is not None
    repository.update(own.request_id, status="recognized")
    repository.update(other.request_id, status="recognized")
    for message_id, request_id, chat_id in (
        ("mid.bot-own", own.request_id, 100),
        ("mid.bot-other", other.request_id, 101),
    ):
        repository.record_sent_message(
            message_id=message_id,
            request_id=request_id,
            chat_id=chat_id,
            text="Результат",
            text_format="html",
            photo_token=None,
            now=1100,
        )
    repository.admit_updates(
        [
            inbox_update("message_created:mid.1", user_id=200),
            inbox_update("message_created:mid.2", user_id=201),
            inbox_update("message_callback:callback-1", user_id=200),
        ],
        now=1100,
    )

    assert repository.delete_user_data(200) == (1, 1)

    assert repository.sent_message("mid.bot-own") is None
    assert repository.sent_message("mid.bot-other") is not None
    assert [item.update_key for item in repository.pending_updates()] == [
        "message_created:mid.2"
    ]
    repository.close()


def test_update_inbox_admits_each_update_key_once(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    first = inbox_update("message_created:mid.1", text="first")

    assert repository.admit_updates([first, first], now=1000) == 1
    repeated = inbox_update("message_created:mid.1", text="repeated delivery")
    assert repository.admit_updates([repeated], now=1001) == 0

    [pending] = repository.pending_updates()
    assert pending.update_key == "message_created:mid.1"
    assert pending.payload == first[3]

    # A processed row keeps dropping a repeated delivery until it is purged.
    repository.mark_update_processed(pending.inbox_id, 1002)
    assert repository.admit_updates([first], now=1003) == 0
    assert repository.pending_updates() == []
    repository.close()


def test_update_inbox_returns_pending_updates_in_arrival_order(tmp_path):
    path = tmp_path / "bot.sqlite3"
    repository = Repository(path)
    keys = [f"message_created:mid.{index}" for index in range(3)]
    callback_key = "message_callback:callback-1"
    payload = {
        "update_type": "message_created",
        "message": {"body": {"mid": "mid.0", "text": "Что за вино?"}},
    }

    assert repository.admit_updates(
        [(keys[0], "message_created", 200, payload)]
        + [inbox_update(key) for key in keys[1:]],
        now=1000,
    ) == 3
    assert repository.admit_updates(
        [inbox_update(callback_key, update_type="message_callback")],
        now=1001,
    ) == 1

    pending = repository.pending_updates()
    assert [item.update_key for item in pending] == [*keys, callback_key]
    assert [item.inbox_id for item in pending] == sorted(item.inbox_id for item in pending)
    assert pending[0].payload == payload
    assert [item.update_key for item in repository.pending_updates(limit=2)] == keys[:2]
    with pytest.raises(ValueError):
        repository.pending_updates(limit=0)

    repository.mark_update_processed(pending[1].inbox_id, 1002)
    repository.close()

    # An unprocessed row is handled again after a restart.
    reopened = Repository(path)
    assert [item.update_key for item in reopened.pending_updates()] == [
        keys[0],
        keys[2],
        callback_key,
    ]
    reopened.close()


def test_update_inbox_stores_the_polling_marker_with_the_batch(tmp_path):
    path = tmp_path / "bot.sqlite3"
    repository = Repository(path)
    assert repository.state("polling_marker") is None

    assert repository.admit_updates(
        [inbox_update("message_created:mid.1")],
        now=1000,
        marker=41,
    ) == 1
    assert repository.state("polling_marker") == "41"

    # A webhook batch has no marker and keeps the stored marker.
    repository.admit_updates([inbox_update("message_created:mid.2")], now=1001)
    assert repository.state("polling_marker") == "41"

    # A poll without updates still advances the marker.
    assert repository.admit_updates([], now=1002, marker=42) == 0
    repository.close()

    reopened = Repository(path)
    assert reopened.state("polling_marker") == "42"
    reopened.close()


def test_update_inbox_batch_and_marker_are_written_in_one_transaction(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    repository.admit_updates([], now=1000, marker=10)
    unserializable = ("message_created:mid.2", "message_created", 200, {"body": object()})

    with pytest.raises(TypeError):
        repository.admit_updates(
            [inbox_update("message_created:mid.1"), unserializable],
            now=1001,
            marker=11,
        )

    # The failed batch left no update and did not advance the marker.
    assert repository.pending_updates() == []
    assert repository.state("polling_marker") == "10"
    assert repository.admit_updates(
        [inbox_update("message_created:mid.1")],
        now=1002,
        marker=11,
    ) == 1
    assert repository.state("polling_marker") == "11"
    repository.close()


def test_processed_updates_are_purged_before_the_cutoff(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    keys = ["message_created:mid.old", "message_created:mid.recent", "message_created:mid.new"]
    repository.admit_updates([inbox_update(key) for key in keys], now=1000)
    old, recent, _ = repository.pending_updates()
    repository.mark_update_processed(old.inbox_id, 1100)
    repository.mark_update_processed(recent.inbox_id, 1300)

    assert repository.purge_processed_updates(1200) == 1

    # The unprocessed row stays pending. The recent processed row still drops a repetition.
    assert [item.update_key for item in repository.pending_updates()] == [keys[2]]
    assert repository.admit_updates(
        [inbox_update(keys[0]), inbox_update(keys[1])],
        now=1400,
    ) == 1
    assert [item.update_key for item in repository.pending_updates()] == [keys[2], keys[0]]
    repository.close()


def test_unreadable_inbox_payload_is_returned_as_an_empty_payload(tmp_path):
    path = tmp_path / "bot.sqlite3"
    Repository(path).close()
    connection = sqlite3.connect(path)
    connection.executemany(
        """
        INSERT INTO update_inbox(update_key, update_type, user_id, payload_json, received_at)
        VALUES (?, 'message_created', 200, ?, 1000)
        """,
        [("broken", "not json"), ("list", "[1, 2]")],
    )
    connection.commit()
    connection.close()

    repository = Repository(path)
    assert [(item.update_key, item.payload) for item in repository.pending_updates()] == [
        ("broken", {}),
        ("list", {}),
    ]
    repository.close()


def test_bot_state_is_persistent_and_replaced(tmp_path):
    path = tmp_path / "bot.sqlite3"
    repository = Repository(path)
    assert repository.state("webhook_subscription") is None

    repository.set_state("webhook_subscription", "https://bot.example/first", 1000)
    repository.set_state("webhook_subscription", "https://bot.example/second", 1001)
    assert repository.state("webhook_subscription") == "https://bot.example/second"
    repository.close()

    reopened = Repository(path)
    assert reopened.state("webhook_subscription") == "https://bot.example/second"
    # The polling marker of the inbox uses the same store.
    reopened.set_state("polling_marker", "77", 1002)
    reopened.admit_updates([], now=1003, marker=78)
    assert reopened.state("polling_marker") == "78"
    assert reopened.state("webhook_subscription") == "https://bot.example/second"
    reopened.close()
