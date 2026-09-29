import io
import json
import sqlite3
from types import SimpleNamespace

from PIL import Image

from chto_za_vino_bot.app import PhotoJob, PhotoProcessor, enqueue_admin_retries
from chto_za_vino_bot.matcher import RecognitionCandidate, RecognitionResult
from chto_za_vino_bot.moderation import DisabledModerator, ModerationResult
from chto_za_vino_bot.quality import QualityResult, QualityUnavailable
from chto_za_vino_bot.storage import ArtifactStore, ImageStore, Repository
from chto_za_vino_bot.wine import Wine


def jpeg() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (120, 240), "darkred").save(output, format="JPEG")
    return output.getvalue()


class FakeBot:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.photos: list[dict[str, object]] = []

    async def get_file(self, file_id: str):
        return SimpleNamespace(file_path=f"{file_id}.jpg")

    async def download_file(self, file_path: str, *, destination: io.BytesIO) -> None:
        destination.write(self.body)

    async def send_photo(self, **kwargs: object) -> None:
        self.photos.append(kwargs)


class SafeModerator:
    async def classify(self, body: bytes) -> ModerationResult:
        return ModerationResult(
            safe=True,
            category="safe",
            confidence=0.01,
            reason="dangerous=0.010000,sexual=0.001000,violence=0.001000",
            scores={"dangerous": 0.01, "sexual": 0.001, "violence": 0.001},
        )


class UnsafeModerator:
    async def classify(self, body: bytes) -> ModerationResult:
        return ModerationResult(
            safe=False,
            category="sexual",
            confidence=0.99,
            reason="dangerous=0.010000,sexual=0.990000,violence=0.001000",
            scores={"dangerous": 0.01, "sexual": 0.99, "violence": 0.001},
        )


class UnavailableQualityInspector:
    async def inspect(self, body: bytes) -> QualityResult:
        raise QualityUnavailable("invalid SAM3 response")


class AdvisoryQualityInspector:
    async def inspect(self, body: bytes) -> QualityResult:
        return QualityResult(
            acceptable=False,
            issues=("bottle_missing",),
            blur_variance=120.0,
            glare_ratio=0.01,
            bottle_area_ratio=0.0,
            label_area_ratio=0.04,
        )


def wine(slug: str = "wine-1") -> Wine:
    return Wine(
        slug=slug,
        name=f"Тестовое вино {slug}",
        page_url=f"https://vino-svoe.ru/wines/{slug}",
        producer=None,
        category="Красное",
        color="Рубиновый",
        grapes="Пино Нуар",
        sugar="Сухое",
        image_url=None,
    )


class FakeMatcher:
    def __init__(self, count: int = 4) -> None:
        self.calls = 0
        self.count = count

    async def recognize(self, body: bytes) -> RecognitionResult:
        self.calls += 1
        return RecognitionResult(
            tuple(
                RecognitionCandidate(
                    slug=f"wine-{rank}",
                    score=1.0 - rank / 10,
                    rank=rank,
                    wine=wine(f"wine-{rank}"),
                )
                for rank in range(1, self.count + 1)
            ),
            "test-pipeline",
        )


async def run_processor(
    tmp_path,
    quality_inspector,
    *,
    artifact_store=None,
    moderator=None,
    api_request=False,
    matcher=None,
):
    database = tmp_path / "bot.sqlite3"
    repository = Repository(database)
    if api_request:
        request_id = repository.create_api_request(now=1000)
    else:
        reservation = repository.reserve(
            chat_id=100,
            message_id=10,
            user_id=200,
            username="tester",
            first_name="Test",
            last_name=None,
            file_id="file-1",
            file_unique_id="unique-1",
            now=1000,
            limit=50,
            window_seconds=3600,
        )
        assert reservation.request_id is not None
        request_id = reservation.request_id
    matcher = matcher or FakeMatcher()
    bot = FakeBot(jpeg())
    services = SimpleNamespace(
        settings=SimpleNamespace(
            max_image_bytes=20 * 1024 * 1024,
            match_min_score=0.70,
            match_min_margin=0.015,
        ),
        repository=repository,
        store=ImageStore(tmp_path / "images"),
        artifact_store=artifact_store or ArtifactStore(tmp_path / "images"),
        moderator=moderator or SafeModerator(),
        quality_inspector=quality_inspector,
        matcher=matcher,
        image_loader=None,
        rejection_image=b"unused",
    )
    processor = PhotoProcessor(services, bot)

    await processor.process(
        PhotoJob(
            request_id=request_id,
            chat_id=100,
            source_message_id=10,
            received_at=1000,
            file_id="file-1",
            status_message_id=None,
            status_enabled=False,
            image_body=jpeg() if api_request else None,
            delivery_enabled=not api_request,
        )
    )

    timings = repository.step_timings(request_id)
    artifacts = repository.artifacts(request_id)
    repository.close()
    connection = sqlite3.connect(database)
    row = connection.execute(
        """
        SELECT status, error_code, quality_acceptable, quality_issues
        FROM requests WHERE request_id = ?
        """,
        (request_id,),
    ).fetchone()
    connection.close()
    return row, timings, matcher.calls, bot.photos, artifacts


async def test_quality_service_failure_continues_to_recognition(tmp_path):
    row, timings, matcher_calls, photos, artifacts = await run_processor(
        tmp_path,
        UnavailableQualityInspector(),
    )

    assert row == ("recognized", None, None, "check_unavailable")
    assert matcher_calls == 1
    assert len(photos) == 1
    assert [item.artifact_key for item in artifacts] == [
        "matcher_input",
        "moderation_input",
        "telegram_result",
    ]
    assert next(item for item in timings if item.step == "quality").outcome == "failed"
    assert next(item for item in timings if item.step == "recognition").outcome == "ok"


async def test_quality_issue_continues_to_recognition(tmp_path):
    row, timings, matcher_calls, photos, artifacts = await run_processor(
        tmp_path,
        AdvisoryQualityInspector(),
    )

    assert row == ("recognized", None, 0, "bottle_missing")
    assert matcher_calls == 1
    assert len(photos) == 1
    assert len(artifacts) == 3
    assert next(item for item in timings if item.step == "quality").outcome == "ok"
    assert next(item for item in timings if item.step == "recognition").outcome == "ok"


async def test_disabled_moderation_continues_and_records_bypass(tmp_path):
    row, timings, matcher_calls, photos, _ = await run_processor(
        tmp_path,
        AdvisoryQualityInspector(),
        moderator=DisabledModerator(),
    )

    assert row[0] == "recognized"
    assert matcher_calls == 1
    assert len(photos) == 1
    assert next(item for item in timings if item.step == "moderation").outcome == "ok"
    connection = sqlite3.connect(tmp_path / "bot.sqlite3")
    moderation = connection.execute(
        "SELECT moderation_safe, moderation_category, moderation_confidence, "
        "moderation_reason FROM requests"
    ).fetchone()
    connection.close()
    assert moderation == (None, "disabled", 0.0, "moderation_disabled")


async def test_artifact_failure_continues_to_recognition(tmp_path):
    class FailingArtifactStore:
        def save(self, *args, **kwargs):
            raise OSError("artifact disk unavailable")

    row, _, matcher_calls, photos, artifacts = await run_processor(
        tmp_path,
        AdvisoryQualityInspector(),
        artifact_store=FailingArtifactStore(),
    )

    assert row[0] == "recognized"
    assert matcher_calls == 1
    assert len(photos) == 1
    assert artifacts == []


async def test_unsafe_request_stores_only_censored_artifact(tmp_path):
    row, timings, matcher_calls, photos, artifacts = await run_processor(
        tmp_path,
        AdvisoryQualityInspector(),
        moderator=UnsafeModerator(),
    )

    assert row[0] == "quarantined"
    assert matcher_calls == 0
    assert len(photos) == 1
    assert [item.artifact_key for item in artifacts] == ["censored_preview"]
    assert artifacts[0].exposure == "censored"
    assert next(item for item in timings if item.step == "artifact_censored").outcome == "ok"


async def test_http_api_request_uses_same_pipeline_without_telegram_delivery(tmp_path):
    row, timings, matcher_calls, photos, artifacts = await run_processor(
        tmp_path,
        AdvisoryQualityInspector(),
        api_request=True,
    )

    assert row[0] == "recognized"
    assert matcher_calls == 1
    assert photos == []
    assert any(item.step == "http_input" for item in timings)
    assert not any(item.step == "telegram_download" for item in timings)
    assert [item.artifact_key for item in artifacts] == [
        "matcher_input",
        "moderation_input",
        "telegram_result",
    ]


async def test_recognition_stores_the_cards_and_the_pipeline(tmp_path):
    row, _, _, photos, _ = await run_processor(tmp_path, AdvisoryQualityInspector())

    assert row[0] == "recognized"
    assert "Тестовое вино wine-1" in photos[0]["caption"]
    connection = sqlite3.connect(tmp_path / "bot.sqlite3")
    request = connection.execute(
        "SELECT recognition_slug, recognition_name, matcher_pipeline FROM requests"
    ).fetchone()
    cards = connection.execute(
        "SELECT rank, slug, wine_json FROM request_candidates ORDER BY rank"
    ).fetchall()
    connection.close()
    assert request == ("wine-1", "Тестовое вино wine-1", "test-pipeline")
    assert [(rank, slug) for rank, slug, _ in cards] == [
        (1, "wine-1"),
        (2, "wine-2"),
        (3, "wine-3"),
        (4, "wine-4"),
    ]
    assert json.loads(cards[1][2])["name"] == "Тестовое вино wine-2"
    assert json.loads(cards[1][2])["page_url"] == "https://vino-svoe.ru/wines/wine-2"


async def test_an_empty_matcher_answer_abstains(tmp_path):
    row, timings, matcher_calls, photos, _ = await run_processor(
        tmp_path,
        AdvisoryQualityInspector(),
        matcher=FakeMatcher(count=0),
    )

    assert row[0] == "abstained"
    assert matcher_calls == 1
    assert photos == []
    assert next(item for item in timings if item.step == "recognition").outcome == "ok"
    connection = sqlite3.connect(tmp_path / "bot.sqlite3")
    request = connection.execute(
        "SELECT recognition_slug, recognition_score, recognition_margin, matcher_pipeline "
        "FROM requests"
    ).fetchone()
    candidates = connection.execute("SELECT COUNT(*) FROM request_candidates").fetchone()
    connection.close()
    assert request == (None, None, None, "test-pipeline")
    assert candidates == (0,)


async def test_one_matcher_candidate_abstains_because_the_margin_is_zero(tmp_path):
    row, _, _, photos, _ = await run_processor(
        tmp_path,
        AdvisoryQualityInspector(),
        matcher=FakeMatcher(count=1),
    )

    assert row[0] == "abstained"
    assert photos == []


async def test_unsafe_retry_removes_the_earlier_safe_copies(tmp_path):
    class RetryQueue:
        at_capacity = False

        def __init__(self) -> None:
            self.jobs: list[PhotoJob] = []

        def submit(self, job: PhotoJob) -> None:
            self.jobs.append(job)

    class StatusBot(FakeBot):
        async def send_message(self, chat_id: int, text: str, **kwargs: object):
            return SimpleNamespace(message_id=500)

        async def edit_message_text(self, text: str, **kwargs: object) -> None:
            return None

        async def delete_message(self, chat_id: int, message_id: int) -> None:
            return None

    data_root = tmp_path / "images"
    repository = Repository(tmp_path / "bot.sqlite3")
    reservation = repository.reserve(
        chat_id=100,
        message_id=10,
        user_id=200,
        username="tester",
        first_name="Test",
        last_name=None,
        file_id="file-1",
        file_unique_id="unique-1",
        now=1000,
        limit=50,
        window_seconds=3600,
    )
    request_id = reservation.request_id
    assert request_id is not None
    services = SimpleNamespace(
        settings=SimpleNamespace(
            max_image_bytes=20 * 1024 * 1024,
            match_min_score=0.70,
            match_min_margin=0.015,
        ),
        repository=repository,
        store=ImageStore(data_root),
        artifact_store=ArtifactStore(data_root),
        moderator=SafeModerator(),
        quality_inspector=AdvisoryQualityInspector(),
        matcher=FakeMatcher(),
        image_loader=None,
        rejection_image=b"unused",
    )
    processor = PhotoProcessor(services, StatusBot(jpeg()))
    await processor.process(
        PhotoJob(request_id, 100, 10, 1000, "file-1", None, status_enabled=False)
    )
    assert repository.admin_request(request_id).status == "recognized"
    assert len(list((data_root / "accepted").rglob(f"{request_id}.*"))) == 1

    # The retry comes two days later, so its job uses another date directory.
    assert repository.request_retry(request_id, 1000 + 2 * 86400) == "requested"
    queue = RetryQueue()
    assert enqueue_admin_retries(repository, queue) == 1
    services.moderator = UnsafeModerator()
    await processor.process(queue.jobs[0])

    assert repository.admin_request(request_id).status == "quarantined"
    assert list((data_root / "accepted").rglob(f"{request_id}.*")) == []
    assert len(list((data_root / "quarantine").rglob(f"{request_id}.*"))) == 1
    artifact_files = [
        path.name for path in (data_root / "artifacts").rglob("*") if path.is_file()
    ]
    assert artifact_files == ["censored_preview.jpg"]
    assert [item.artifact_key for item in repository.artifacts(request_id)] == [
        "censored_preview"
    ]
    repository.close()
