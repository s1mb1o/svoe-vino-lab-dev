import io
import sqlite3

import pytest
from PIL import Image

from chto_za_vino_max_bot.data_lifecycle import delete_user_data, purge_expired_data
from chto_za_vino_max_bot.storage import ArtifactStore, ArtifactWrite, ImageStore, Repository


def jpeg() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (20, 30), "darkred").save(output, format="JPEG")
    return output.getvalue()


def seed_request(repository: Repository, data_root, *, now: int, status: str = "recognized"):
    reservation = repository.reserve(
        chat_id=100,
        chat_type="dialog",
        message_id=f"mid.{now}",
        photo_index=0,
        user_id=200,
        username="tester",
        first_name="Test",
        last_name=None,
        photo_id=now,
        photo_url=f"https://i.oneme.example/photo-{now}.jpg",
        photo_token=f"token-{now}",
        now=now,
        limit=50,
        window_seconds=3600,
    )
    assert reservation.request_id is not None
    source_path, _ = ImageStore(data_root).save(
        reservation.request_id,
        now,
        jpeg(),
        True,
    )
    artifact_path = ArtifactStore(data_root).save(
        reservation.request_id,
        now,
        "matcher_input",
        "image/jpeg",
        jpeg(),
    )
    repository.update(
        reservation.request_id,
        status=status,
        moderation_safe=1,
        storage_path=source_path,
    )
    repository.replace_artifacts(
        reservation.request_id,
        [
            ArtifactWrite(
                artifact_key="matcher_input",
                step="input",
                title="Input",
                description="Input",
                mime_type="image/jpeg",
                relative_path=artifact_path,
                width=20,
                height=30,
                ordinal=1,
                metadata={},
            )
        ],
        now,
    )
    return reservation.request_id, source_path, artifact_path


def inbox_update(update_key: str, user_id: int | None):
    update_type = update_key.split(":", 1)[0]
    return update_key, update_type, user_id, {"update_type": update_type}


def inbox_keys(path) -> list[str]:
    """Return all inbox keys, processed or not."""
    connection = sqlite3.connect(path)
    rows = connection.execute("SELECT update_key FROM update_inbox ORDER BY inbox_id").fetchall()
    connection.close()
    return [row[0] for row in rows]


def test_retention_deletes_terminal_requests_files_and_inactive_users(tmp_path):
    data_root = tmp_path / "data"
    repository = Repository(data_root / "bot.sqlite3")
    request_id, source_path, artifact_path = seed_request(repository, data_root, now=1000)
    unindexed_artifact = (
        data_root / "artifacts/1970/01/01" / request_id / "old-retry-artifact.png"
    )
    unindexed_artifact.write_bytes(b"old")

    result = purge_expired_data(repository, data_root, cutoff=2000)

    assert result.requests == 1
    assert result.users == 1
    assert result.files == 3
    assert not (data_root / source_path).exists()
    assert not (data_root / artifact_path).exists()
    assert not unindexed_artifact.exists()
    assert repository.user_by_id(200) is None
    repository.close()


def test_retention_keeps_active_requests(tmp_path):
    data_root = tmp_path / "data"
    repository = Repository(data_root / "bot.sqlite3")
    request_id, source_path, _ = seed_request(
        repository,
        data_root,
        now=1000,
        status="processing",
    )

    result = purge_expired_data(repository, data_root, cutoff=2000)

    assert result.requests == 0
    assert (data_root / source_path).is_file()
    assert repository.admin_request(request_id) is not None
    repository.close()


def test_manual_user_deletion_removes_database_rows_and_files(tmp_path):
    data_root = tmp_path / "data"
    repository = Repository(data_root / "bot.sqlite3")
    request_id, source_path, artifact_path = seed_request(repository, data_root, now=1000)

    result = delete_user_data(repository, data_root, user_id=200)

    assert result.requests == 1
    assert result.files == 2
    assert repository.admin_request(request_id) is None
    assert repository.user_by_id(200) is None
    assert not (data_root / source_path).exists()
    assert not (data_root / artifact_path).exists()
    repository.close()


def test_manual_user_deletion_removes_the_update_inbox_rows_of_the_user(tmp_path):
    data_root = tmp_path / "data"
    database = data_root / "bot.sqlite3"
    repository = Repository(database)
    seed_request(repository, data_root, now=1000)
    repository.admit_updates(
        [
            inbox_update("message_created:mid.processed", 200),
            inbox_update("message_callback:callback-1", 200),
            inbox_update("bot_started:5000:200:1000:", 200),
            inbox_update("message_created:mid.other", 201),
            inbox_update("message_created:mid.unknown", None),
        ],
        now=1100,
    )
    processed = repository.pending_updates()[0]
    repository.mark_update_processed(processed.inbox_id, 1200)

    delete_user_data(repository, data_root, user_id=200)

    assert inbox_keys(database) == [
        "message_created:mid.other",
        "message_created:mid.unknown",
    ]
    repository.close()


def test_manual_user_deletion_of_a_user_without_requests_removes_inbox_rows(tmp_path):
    data_root = tmp_path / "data"
    database = data_root / "bot.sqlite3"
    repository = Repository(database)
    # The user pressed «Начать» and answered the age gate, but sent no photo.
    repository.set_age_status(
        user_id=200,
        username="tester",
        first_name="Test",
        last_name=None,
        status="adult",
        now=1000,
    )
    repository.admit_updates(
        [
            inbox_update("bot_started:5000:200:1000:", 200),
            inbox_update("message_callback:age-callback", 200),
        ],
        now=1000,
    )

    result = delete_user_data(repository, data_root, user_id=200)

    assert (result.requests, result.users, result.files) == (0, 1, 0)
    assert repository.user_by_id(200) is None
    assert inbox_keys(database) == []
    repository.close()


def test_manual_user_deletion_refuses_active_requests_and_keeps_the_inbox(tmp_path):
    data_root = tmp_path / "data"
    database = data_root / "bot.sqlite3"
    repository = Repository(database)
    request_id, source_path, _ = seed_request(repository, data_root, now=1000, status="queued")
    repository.admit_updates([inbox_update("message_created:mid.1000", 200)], now=1000)

    with pytest.raises(ValueError, match="active requests"):
        delete_user_data(repository, data_root, user_id=200)

    assert repository.admin_request(request_id) is not None
    assert (data_root / source_path).is_file()
    assert inbox_keys(database) == ["message_created:mid.1000"]
    repository.close()


def test_retention_deletes_update_inbox_rows_older_than_the_cutoff(tmp_path):
    data_root = tmp_path / "data"
    database = data_root / "bot.sqlite3"
    repository = Repository(database)
    repository.admit_updates([inbox_update("message_created:mid.processed", 200)], now=1000)
    repository.mark_update_processed(repository.pending_updates()[0].inbox_id, 1100)
    repository.admit_updates([inbox_update("message_created:mid.pending", 201)], now=1500)
    repository.admit_updates([inbox_update("message_created:mid.new", 200)], now=2500)

    purge_expired_data(repository, data_root, cutoff=2000)

    assert inbox_keys(database) == ["message_created:mid.new"]
    assert [item.update_key for item in repository.pending_updates()] == [
        "message_created:mid.new"
    ]
    repository.close()


def test_retention_deletes_the_sent_messages_of_expired_requests(tmp_path):
    data_root = tmp_path / "data"
    repository = Repository(data_root / "bot.sqlite3")
    expired_id, _, _ = seed_request(repository, data_root, now=1000)
    current_id, _, _ = seed_request(repository, data_root, now=3000)
    for message_id, request_id in (("mid.bot-old", expired_id), ("mid.bot-new", current_id)):
        repository.record_sent_message(
            message_id=message_id,
            request_id=request_id,
            chat_id=100,
            text="<b>Похоже, это:</b> Вино",
            text_format="html",
            photo_token="photo-token",
            now=3000,
        )

    result = purge_expired_data(repository, data_root, cutoff=2000)

    assert result.requests == 1
    assert repository.sent_message("mid.bot-old") is None
    assert repository.sent_message("mid.bot-new") is not None
    repository.close()
