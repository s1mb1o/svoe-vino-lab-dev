import io
import json
import sqlite3
from types import SimpleNamespace

import pytest
from chto_za_vino_core.files import ArtifactStore, ImageStore
from chto_za_vino_core.matcher import RecognitionCandidate, RecognitionResult
from chto_za_vino_core.moderation import DisabledModerator, ModerationResult
from chto_za_vino_core.quality import QualityResult, QualityUnavailable
from chto_za_vino_core.wine import Wine
from fakes import DIALOG_CHAT_ID, USER_ID, Call, FakeMaxApi, button_texts, image
from PIL import Image

from chto_za_vino_max_bot.app import PhotoJob, PhotoProcessor, enqueue_admin_retries
from chto_za_vino_max_bot.max_api import MediaTooLarge, MediaUnavailable
from chto_za_vino_max_bot.storage import Repository
from chto_za_vino_max_bot.updates import ImageRef


def jpeg() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (120, 240), "darkred").save(output, format="JPEG")
    return output.getvalue()


ADMIN_USER_ID = 700
GROUP_CHAT_ID = 6000
SOURCE_MID = "mid.source"
PHOTO = image(1)
MAX_IMAGE_BYTES = 20 * 1024 * 1024
INVALID_SIZE_TEXT = "Не удалось прочитать фотографию. Отправьте другое изображение."
DOWNLOAD_FAILED_TEXT = "Не удалось загрузить фотографию. Попробуйте еще раз."


def max_api() -> FakeMaxApi:
    api = FakeMaxApi()
    api.downloads[PHOTO.url] = jpeg()
    return api


class MediaMaxApi(FakeMaxApi):
    """A download of a URL in `download_failures` raises the stored error."""

    def __init__(self) -> None:
        super().__init__()
        self.download_failures: dict[str, Exception] = {}

    async def download(self, url: str, *, max_bytes: int) -> bytes:
        failure = self.download_failures.get(url)
        if failure is None:
            return await super().download(url, max_bytes=max_bytes)
        self.calls.append(Call("download", {"url": url, "max_bytes": max_bytes}))
        raise failure


def max_message(*images: ImageRef) -> dict[str, object]:
    """The `GET /messages/{mid}` answer for the source message."""
    return {
        "sender": {"user_id": USER_ID, "first_name": "Test", "username": "tester"},
        "recipient": {"chat_id": DIALOG_CHAT_ID, "chat_type": "dialog"},
        "timestamp": 1000,
        "body": {
            "mid": SOURCE_MID,
            "text": None,
            "attachments": [
                {
                    "type": "image",
                    "payload": {"photo_id": item.photo_id, "url": item.url, "token": item.token},
                }
                for item in images
            ],
        },
    }


def photo_messages(api: FakeMaxApi) -> list[dict[str, object]]:
    """The sent messages with an image: results and rejection illustrations."""
    return [
        call
        for call in api.calls_of("send_message")
        if any(item.get("type") == "image" for item in call["attachments"] or [])
    ]


def sent_texts(api: FakeMaxApi) -> list[str]:
    return [str(call["text"]) for call in api.calls_of("send_message")]


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
    def __init__(self, count: int = 4, scores: tuple[float, ...] | None = None) -> None:
        self.calls = 0
        self.count = count
        self.scores = scores

    async def recognize(self, body: bytes) -> RecognitionResult:
        self.calls += 1
        return RecognitionResult(
            tuple(
                RecognitionCandidate(
                    slug=f"wine-{rank}",
                    score=self.scores[rank - 1] if self.scores else 1.0 - rank / 10,
                    rank=rank,
                    wine=wine(f"wine-{rank}"),
                )
                for rank in range(1, self.count + 1)
            ),
            "test-pipeline",
        )


def processor_services(
    tmp_path,
    repository,
    quality_inspector,
    *,
    artifact_store=None,
    moderator=None,
    matcher=None,
    max_image_bytes=MAX_IMAGE_BYTES,
):
    return SimpleNamespace(
        settings=SimpleNamespace(
            max_image_bytes=max_image_bytes,
            match_min_score=0.70,
            match_min_margin=0.015,
            admin_user_id=ADMIN_USER_ID,
        ),
        repository=repository,
        store=ImageStore(tmp_path / "images"),
        artifact_store=artifact_store or ArtifactStore(tmp_path / "images"),
        moderator=moderator or SafeModerator(),
        quality_inspector=quality_inspector,
        matcher=matcher or FakeMatcher(),
        image_loader=None,
        rejection_image=b"unused",
    )


async def run_processor(
    tmp_path,
    quality_inspector,
    *,
    artifact_store=None,
    moderator=None,
    api_request=False,
    matcher=None,
    user_id=USER_ID,
    chat_id=DIALOG_CHAT_ID,
    chat_type="dialog",
    api=None,
    photo=PHOTO,
    photo_index=0,
    max_image_bytes=MAX_IMAGE_BYTES,
):
    database = tmp_path / "bot.sqlite3"
    repository = Repository(database)
    if api_request:
        request_id = repository.create_api_request(now=1000)
    else:
        reservation = repository.reserve(
            chat_id=chat_id,
            chat_type=chat_type,
            message_id=SOURCE_MID,
            photo_index=photo_index,
            user_id=user_id,
            username="tester",
            first_name="Test",
            last_name=None,
            photo_id=photo.photo_id,
            photo_url=photo.url,
            photo_token=photo.token,
            now=1000,
            limit=50,
            window_seconds=3600,
        )
        assert reservation.request_id is not None
        request_id = reservation.request_id
    matcher = matcher or FakeMatcher()
    if api is None:
        api = max_api()
    services = processor_services(
        tmp_path,
        repository,
        quality_inspector,
        artifact_store=artifact_store,
        moderator=moderator,
        matcher=matcher,
        max_image_bytes=max_image_bytes,
    )
    processor = PhotoProcessor(services, api)

    await processor.process(
        PhotoJob(
            request_id=request_id,
            chat_id=0 if api_request else chat_id,
            chat_type="api" if api_request else chat_type,
            user_id=0 if api_request else user_id,
            source_message_id="" if api_request else SOURCE_MID,
            photo_index=0 if api_request else photo_index,
            received_at=1000,
            photo_id=None if api_request else photo.photo_id,
            photo_url="" if api_request else photo.url,
            status_message_id=None,
            feedback_enabled=not api_request,
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
    return row, timings, matcher.calls, photo_messages(api), artifacts


def stored_photo_url(tmp_path) -> str:
    connection = sqlite3.connect(tmp_path / "bot.sqlite3")
    (url,) = connection.execute("SELECT max_photo_url FROM requests").fetchone()
    connection.close()
    return url


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
        "max_result",
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


async def test_http_api_request_uses_same_pipeline_without_max_delivery(tmp_path):
    api = FakeMaxApi()

    row, timings, matcher_calls, photos, artifacts = await run_processor(
        tmp_path,
        AdvisoryQualityInspector(),
        api_request=True,
        api=api,
    )

    assert row[0] == "recognized"
    assert matcher_calls == 1
    assert photos == []
    assert api.calls == []
    assert any(item.step == "http_input" for item in timings)
    assert not any(item.step == "max_download" for item in timings)
    assert [item.artifact_key for item in artifacts] == [
        "matcher_input",
        "moderation_input",
        "max_result",
    ]


async def test_recognition_stores_the_cards_and_the_pipeline(tmp_path):
    row, _, _, photos, _ = await run_processor(tmp_path, AdvisoryQualityInspector())

    assert row[0] == "recognized"
    assert "Тестовое вино wine-1" in photos[0]["text"]
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


async def test_one_matcher_candidate_has_a_tentative_wine_card(tmp_path):
    row, _, _, photos, _ = await run_processor(
        tmp_path,
        AdvisoryQualityInspector(),
        matcher=FakeMatcher(count=1),
    )

    assert row[0] == "abstained"
    assert len(photos) == 1
    assert photos[0]["text"].startswith("У меня есть пара вариантов, скорей всего это:")
    assert "Тестовое вино wine-1" in photos[0]["text"]


@pytest.mark.parametrize(
    ("scores", "status", "introduction"),
    [
        ((0.90, 0.89), "abstained", "У меня есть пара вариантов, скорей всего это:"),
        ((0.69, 0.50), "abstained", "Пришлите еще фотографию, но скорее всего, это:"),
        ((0.69, 0.68), "abstained", "Пришлите еще фотографию, но скорее всего, это:"),
        ((0.70, 0.60), "recognized", "Похоже, это:"),
        ((0.90, 0.885), "recognized", "Похоже, это:"),
    ],
)
async def test_confidence_changes_the_wording_and_keeps_the_wine_card(
    tmp_path, scores, status, introduction,
):
    row, _, _, photos, _ = await run_processor(
        tmp_path,
        AdvisoryQualityInspector(),
        matcher=FakeMatcher(count=2, scores=scores),
    )

    assert row[0] == status
    assert len(photos) == 1
    assert photos[0]["text"].startswith(introduction + "\n\n")
    assert "Тестовое вино wine-1" in photos[0]["text"]
    buttons = [text for row in button_texts(photos[0]["attachments"]) for text in row]
    assert "Открыть страницу вина" in buttons
    assert "❌ Не совпало" in buttons


async def test_an_api_low_confidence_answer_keeps_its_status_without_max_delivery(tmp_path):
    row, _, _, photos, _ = await run_processor(
        tmp_path,
        AdvisoryQualityInspector(),
        matcher=FakeMatcher(count=2, scores=(0.90, 0.89)),
        api_request=True,
    )

    assert row[0] == "abstained"
    assert photos == []


async def test_the_admin_chat_result_shows_the_confidence_values(tmp_path):
    # In MAX, the dialog ID is not the user ID: the administrator is found by the user ID.
    row, _, _, photos, _ = await run_processor(
        tmp_path,
        AdvisoryQualityInspector(),
        user_id=ADMIN_USER_ID,
    )

    assert row[0] == "recognized"
    assert photos[0]["text"].endswith(
        "\n\nОценка: 0.9000 (порог 0.7) · отрыв: 0.1000 (порог 0.015)"
    )


async def test_the_admin_chat_tentative_card_shows_the_confidence_values(tmp_path):
    row, _, _, photos, _ = await run_processor(
        tmp_path,
        AdvisoryQualityInspector(),
        matcher=FakeMatcher(count=1),
        user_id=ADMIN_USER_ID,
    )

    assert row[0] == "abstained"
    assert photos[0]["text"].endswith(
        "\n\nОценка: 0.9000 (порог 0.7) · отрыв: 0.0000 (порог 0.015)"
    )


async def test_the_admin_chat_empty_answer_shows_the_confidence_values(tmp_path):
    api = max_api()

    row, *_ = await run_processor(
        tmp_path,
        AdvisoryQualityInspector(),
        matcher=FakeMatcher(count=0),
        user_id=ADMIN_USER_ID,
        api=api,
    )

    assert row[0] == "abstained"
    assert sent_texts(api)[-1].startswith("Не уверен")
    assert sent_texts(api)[-1].endswith("\n\nОценка: нет кандидатов")


@pytest.mark.parametrize("count", [4, 1])
async def test_another_chat_does_not_show_the_confidence_values(tmp_path, count):
    api = max_api()

    await run_processor(
        tmp_path,
        AdvisoryQualityInspector(),
        matcher=FakeMatcher(count=count),
        api=api,
    )

    texts = sent_texts(api)
    assert texts
    assert not any("Оценка" in text for text in texts)


@pytest.mark.parametrize("count", [4, 1])
@pytest.mark.parametrize(
    ("user_id", "chat_id", "chat_type"),
    [
        pytest.param(ADMIN_USER_ID, GROUP_CHAT_ID, "chat", id="admin-in-a-group-chat"),
        pytest.param(USER_ID, ADMIN_USER_ID, "dialog", id="dialog-id-equal-to-the-admin-id"),
    ],
)
async def test_the_confidence_values_need_the_admin_user_in_a_dialog(
    tmp_path, count, user_id, chat_id, chat_type
):
    api = max_api()

    await run_processor(
        tmp_path,
        AdvisoryQualityInspector(),
        matcher=FakeMatcher(count=count),
        user_id=user_id,
        chat_id=chat_id,
        chat_type=chat_type,
        api=api,
    )

    texts = sent_texts(api)
    assert texts
    assert not any("Оценка" in text for text in texts)


async def test_unsafe_retry_removes_the_earlier_safe_copies(tmp_path):
    class RetryQueue:
        at_capacity = False

        def __init__(self) -> None:
            self.jobs: list[PhotoJob] = []

        def submit(self, job: PhotoJob) -> None:
            self.jobs.append(job)

    data_root = tmp_path / "images"
    repository = Repository(tmp_path / "bot.sqlite3")
    reservation = repository.reserve(
        chat_id=DIALOG_CHAT_ID,
        chat_type="dialog",
        message_id=SOURCE_MID,
        photo_index=0,
        user_id=USER_ID,
        username="tester",
        first_name="Test",
        last_name=None,
        photo_id=PHOTO.photo_id,
        photo_url=PHOTO.url,
        photo_token=PHOTO.token,
        now=1000,
        limit=50,
        window_seconds=3600,
    )
    request_id = reservation.request_id
    assert request_id is not None
    services = processor_services(tmp_path, repository, AdvisoryQualityInspector())
    processor = PhotoProcessor(services, max_api())
    await processor.process(
        PhotoJob(
            request_id=request_id,
            chat_id=DIALOG_CHAT_ID,
            user_id=USER_ID,
            source_message_id=SOURCE_MID,
            received_at=1000,
            photo_id=PHOTO.photo_id,
            photo_url=PHOTO.url,
            status_enabled=False,
        )
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


# MAX image download: the job keeps the URL and the worker downloads the image.


async def test_the_worker_downloads_the_image_url_with_the_size_limit(tmp_path):
    api = max_api()

    row, timings, *_ = await run_processor(tmp_path, AdvisoryQualityInspector(), api=api)

    assert row[0] == "recognized"
    assert api.calls_of("download") == [{"url": PHOTO.url, "max_bytes": MAX_IMAGE_BYTES}]
    assert api.calls_of("get_message") == []
    assert next(item for item in timings if item.step == "max_download").outcome == "ok"


async def test_a_too_large_image_is_invalid_without_a_message_refresh(tmp_path):
    api = MediaMaxApi()
    api.download_failures[PHOTO.url] = MediaTooLarge("attachment is too large")

    row, timings, matcher_calls, photos, _ = await run_processor(
        tmp_path, AdvisoryQualityInspector(), api=api
    )

    assert row[:2] == ("invalid_image", "invalid_size")
    assert matcher_calls == 0
    assert photos == []
    assert api.calls_of("get_message") == []
    assert [(call["text"], call["reply_to"]) for call in api.calls_of("send_message")] == [
        (INVALID_SIZE_TEXT, SOURCE_MID)
    ]
    assert next(item for item in timings if item.step == "max_download").outcome == "failed"


@pytest.mark.parametrize("body", [b"", b"x" * 101], ids=["empty", "over-the-limit"])
async def test_an_empty_or_oversized_download_is_invalid(tmp_path, body):
    api = FakeMaxApi()
    api.downloads[PHOTO.url] = body

    row, _, matcher_calls, _, _ = await run_processor(
        tmp_path, AdvisoryQualityInspector(), api=api, max_image_bytes=100
    )

    assert row[:2] == ("invalid_image", "invalid_size")
    assert matcher_calls == 0
    assert api.calls_of("download") == [{"url": PHOTO.url, "max_bytes": 100}]
    assert sent_texts(api) == [INVALID_SIZE_TEXT]


async def test_a_converted_heic_must_fit_the_size_limit(tmp_path):
    from chto_za_vino_core.moderation import prepare_source_image
    from heic_images import noisy_heic_bytes

    heic = noisy_heic_bytes()
    converted = len(prepare_source_image(heic))
    assert converted > len(heic)
    api = max_api()
    api.downloads[PHOTO.url] = heic

    row, _, matcher_calls, photos, _ = await run_processor(
        tmp_path, AdvisoryQualityInspector(), api=api, max_image_bytes=(len(heic) + converted) // 2
    )

    # The stored copy would fail the limit at an administration retry, so it is never stored.
    assert row[:2] == ("invalid_image", "decode")
    assert matcher_calls == 0
    assert photos == []
    assert not list((tmp_path / "images" / "accepted").rglob("*.jpg"))


async def test_an_expired_url_is_refreshed_from_the_source_message(tmp_path):
    fresh = ImageRef(photo_id=PHOTO.photo_id, url=f"{PHOTO.url}?fresh", token=PHOTO.token)
    api = MediaMaxApi()
    api.download_failures[PHOTO.url] = MediaUnavailable("attachment download status 403")
    api.downloads[fresh.url] = jpeg()
    api.messages_by_id[SOURCE_MID] = max_message(fresh, image(2))

    row, timings, matcher_calls, photos, _ = await run_processor(
        tmp_path, AdvisoryQualityInspector(), api=api
    )

    assert row[0] == "recognized"
    assert matcher_calls == 1
    assert len(photos) == 1
    assert api.calls_of("get_message") == [{"message_id": SOURCE_MID}]
    assert [call["url"] for call in api.calls_of("download")] == [PHOTO.url, fresh.url]
    assert stored_photo_url(tmp_path) == fresh.url
    assert next(item for item in timings if item.step == "max_download").outcome == "ok"


async def test_the_refresh_selects_the_image_by_its_photo_id(tmp_path):
    second = image(2)
    fresh_first = ImageRef(photo_id=PHOTO.photo_id, url=f"{PHOTO.url}?fresh", token=None)
    fresh_second = ImageRef(photo_id=second.photo_id, url=f"{second.url}?fresh", token=None)
    api = MediaMaxApi()
    api.download_failures[second.url] = MediaUnavailable("attachment download status 403")
    api.downloads[fresh_first.url] = jpeg()
    api.downloads[fresh_second.url] = jpeg()
    # The refreshed message lists the images in another order.
    api.messages_by_id[SOURCE_MID] = max_message(fresh_second, fresh_first)

    row, *_ = await run_processor(
        tmp_path, AdvisoryQualityInspector(), api=api, photo=second, photo_index=1
    )

    assert row[0] == "recognized"
    assert [call["url"] for call in api.calls_of("download")] == [second.url, fresh_second.url]
    assert stored_photo_url(tmp_path) == fresh_second.url


FRESH_PHOTO = ImageRef(photo_id=PHOTO.photo_id, url=f"{PHOTO.url}?fresh", token=PHOTO.token)


@pytest.mark.parametrize(
    ("source_message", "fresh_failure"),
    [
        pytest.param(None, None, id="message-not-found"),
        pytest.param(max_message(), None, id="no-image-at-the-index"),
        pytest.param(max_message(image(7)), None, id="no-image-with-the-photo-id"),
        pytest.param(
            max_message(FRESH_PHOTO),
            MediaUnavailable("attachment download status 404"),
            id="new-url-also-fails",
        ),
    ],
)
async def test_a_failed_refresh_reports_a_download_failure(
    tmp_path, source_message, fresh_failure
):
    api = MediaMaxApi()
    api.download_failures[PHOTO.url] = MediaUnavailable("attachment download status 403")
    if source_message is not None:
        api.messages_by_id[SOURCE_MID] = source_message
    if fresh_failure is not None:
        api.download_failures[FRESH_PHOTO.url] = fresh_failure

    row, timings, matcher_calls, photos, _ = await run_processor(
        tmp_path, AdvisoryQualityInspector(), api=api
    )

    assert row[:2] == ("download_failed", "max")
    assert matcher_calls == 0
    assert photos == []
    assert api.calls_of("get_message") == [{"message_id": SOURCE_MID}]
    assert [(call["text"], call["reply_to"]) for call in api.calls_of("send_message")] == [
        (DOWNLOAD_FAILED_TEXT, SOURCE_MID)
    ]
    assert next(item for item in timings if item.step == "max_download").outcome == "failed"
