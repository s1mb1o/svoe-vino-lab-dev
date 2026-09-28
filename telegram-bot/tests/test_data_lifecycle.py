import io

from PIL import Image

from chto_za_vino_bot.data_lifecycle import delete_user_data, purge_expired_data
from chto_za_vino_bot.storage import ArtifactStore, ArtifactWrite, ImageStore, Repository


def jpeg() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (20, 30), "darkred").save(output, format="JPEG")
    return output.getvalue()


def seed_request(repository: Repository, data_root, *, now: int, status: str = "recognized"):
    reservation = repository.reserve(
        chat_id=100,
        message_id=now,
        user_id=200,
        username="tester",
        first_name="Test",
        last_name=None,
        file_id=f"file-{now}",
        file_unique_id=f"unique-{now}",
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
