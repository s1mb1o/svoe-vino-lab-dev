import io
from types import SimpleNamespace

import pytest
from fakes import DIALOG_CHAT_ID, USER_ID, FakeMaxApi, image
from PIL import Image

from chto_za_vino_max_bot.app import (
    PhotoJob,
    PhotoProcessor,
    enqueue_admin_retries,
    restore_pending_jobs,
)
from chto_za_vino_max_bot.matcher import RecognitionCandidate, RecognitionResult
from chto_za_vino_max_bot.moderation import ModerationResult
from chto_za_vino_max_bot.quality import QualityResult, QualityUnavailable
from chto_za_vino_max_bot.storage import ArtifactStore, ImageStore, Repository
from chto_za_vino_max_bot.wine import Wine
from chto_za_vino_max_bot.work_queue import QueueCapacityError

GROUP_CHAT_ID = 6000
FRESH_URL = "https://i.oneme.example/photo-2-fresh.jpg"


class FakeQueue:
    def __init__(self, *, capacity=None):
        self.at_capacity = False
        self.capacity = capacity
        self.jobs = []
        self.restore_flags = []

    def submit(self, job, *, restore=False):
        if self.capacity is not None and len(self.jobs) >= self.capacity:
            raise QueueCapacityError("queue capacity is full")
        self.jobs.append(job)
        self.restore_flags.append(restore)


@pytest.fixture
def repository(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    yield repository
    repository.close()


def reserve(
    repository,
    *,
    message_id="mid.source",
    photo_index=0,
    chat_id=DIALOG_CHAT_ID,
    chat_type="dialog",
    now=1000,
    feedback_enabled=True,
    photo_source="body",
):
    photo = image(photo_index + 1)
    reservation = repository.reserve(
        chat_id=chat_id,
        chat_type=chat_type,
        message_id=message_id,
        photo_index=photo_index,
        user_id=USER_ID,
        username="tester",
        first_name="Test",
        last_name=None,
        photo_id=photo.photo_id,
        photo_url=photo.url,
        photo_token=photo.token,
        now=now,
        limit=50,
        window_seconds=3600,
        feedback_enabled=feedback_enabled,
        photo_source=photo_source,
    )
    assert reservation.request_id is not None
    return reservation.request_id


def request_retry(repository, request_id, now=1200):
    repository.update(request_id, status="recognized", moderation_safe=1)
    assert repository.request_retry(request_id, now) == "requested"


def test_admin_retry_enters_bot_queue(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    reservation = repository.reserve(
        chat_id=DIALOG_CHAT_ID,
        chat_type="dialog",
        message_id="mid.source",
        photo_index=0,
        user_id=USER_ID,
        username="tester",
        first_name="Test",
        last_name=None,
        photo_id=9001,
        photo_url="https://i.oneme.example/photo-1.jpg",
        photo_token="token-1",
        now=1000,
        limit=50,
        window_seconds=3600,
    )
    assert reservation.request_id is not None
    repository.update(
        reservation.request_id,
        status="recognized",
        moderation_safe=1,
    )
    assert repository.request_retry(reservation.request_id, 1200) == "requested"
    queue = FakeQueue()

    assert enqueue_admin_retries(repository, queue) == 1
    assert len(queue.jobs) == 1
    assert isinstance(queue.jobs[0], PhotoJob)
    assert queue.jobs[0].request_id == reservation.request_id
    assert queue.jobs[0].received_at == 1200
    assert repository.admin_request(reservation.request_id).status == "queued"
    assert enqueue_admin_retries(repository, queue) == 0
    repository.close()


def test_admin_retry_job_keeps_the_max_source_and_asks_for_the_local_copy(repository):
    request_id = reserve(
        repository,
        message_id="mid.album",
        photo_index=1,
        chat_id=GROUP_CHAT_ID,
        chat_type="chat",
        feedback_enabled=False,
        photo_source="forward",
    )
    request_retry(repository, request_id)
    queue = FakeQueue()

    assert enqueue_admin_retries(repository, queue) == 1

    assert queue.jobs == [
        PhotoJob(
            request_id=request_id,
            chat_id=GROUP_CHAT_ID,
            chat_type="chat",
            user_id=USER_ID,
            source_message_id="mid.album",
            photo_index=1,
            received_at=1200,
            photo_id=9002,
            photo_url=image(2).url,
            photo_source="forward",
            status_message_id=None,
            feedback_enabled=False,
            status_enabled=True,
            # The test request has no accepted copy, so the retry downloads the image.
            local_path=None,
            # The files keep the date of the first receipt (1000), not the retry time (1200).
            stored_at=1000,
        )
    ]
    assert queue.restore_flags == [False]


def test_admin_retry_waits_while_the_queue_is_full(repository):
    request_id = reserve(repository)
    request_retry(repository, request_id)
    queue = FakeQueue()
    queue.at_capacity = True

    assert enqueue_admin_retries(repository, queue) == 0
    assert queue.jobs == []
    assert repository.admin_request(request_id).status == "retry_requested"


def test_admin_retry_is_released_when_the_queue_rejects_it(repository):
    request_id = reserve(repository)
    request_retry(repository, request_id)
    queue = FakeQueue(capacity=0)

    assert enqueue_admin_retries(repository, queue) == 0
    assert repository.admin_request(request_id).status == "retry_requested"

    queue.capacity = None
    assert enqueue_admin_retries(repository, queue) == 1
    assert repository.admin_request(request_id).status == "queued"


def test_restart_restores_pending_max_requests(repository):
    single = reserve(repository, message_id="mid.single", now=1000)
    album = reserve(
        repository,
        message_id="mid.album",
        photo_index=1,
        chat_id=GROUP_CHAT_ID,
        chat_type="chat",
        now=1001,
        feedback_enabled=False,
        photo_source="forward",
    )
    received = reserve(repository, message_id="mid.received", now=1002)
    finished = reserve(repository, message_id="mid.finished", now=1003)
    repository.update(single, status="queued")
    repository.update(album, status="processing")
    repository.update(finished, status="recognized")
    # A message refresh after an expired URL stores the new URL. The restored job uses it.
    repository.set_photo_url(album, FRESH_URL)
    queue = FakeQueue()

    assert restore_pending_jobs(repository, queue) == 3

    assert queue.restore_flags == [True, True, True]
    assert queue.jobs == [
        PhotoJob(
            request_id=single,
            chat_id=DIALOG_CHAT_ID,
            chat_type="dialog",
            user_id=USER_ID,
            source_message_id="mid.single",
            photo_index=0,
            received_at=1000,
            photo_id=9001,
            photo_url=image(1).url,
            photo_source="body",
            status_message_id=None,
            feedback_enabled=True,
            status_enabled=True,
            stored_at=1000,
        ),
        PhotoJob(
            request_id=album,
            chat_id=GROUP_CHAT_ID,
            chat_type="chat",
            user_id=USER_ID,
            source_message_id="mid.album",
            photo_index=1,
            received_at=1001,
            photo_id=9002,
            photo_url=FRESH_URL,
            photo_source="forward",
            status_message_id=None,
            feedback_enabled=False,
            status_enabled=False,
            stored_at=1001,
        ),
        PhotoJob(
            request_id=received,
            chat_id=DIALOG_CHAT_ID,
            chat_type="dialog",
            user_id=USER_ID,
            source_message_id="mid.received",
            photo_index=0,
            received_at=1002,
            photo_id=9001,
            photo_url=image(1).url,
            photo_source="body",
            status_message_id=None,
            feedback_enabled=True,
            status_enabled=True,
            stored_at=1002,
        ),
    ]


# The retry pipeline: the processor reads the accepted local copy and moderates it again.


def jpeg():
    output = io.BytesIO()
    Image.new("RGB", (120, 240), "darkred").save(output, format="JPEG")
    return output.getvalue()


def wine(slug):
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


class CountingSafeModerator:
    def __init__(self):
        self.calls = 0

    async def classify(self, body):
        self.calls += 1
        return ModerationResult(
            safe=True,
            category="safe",
            confidence=0.01,
            reason="dangerous=0.010000,sexual=0.001000,violence=0.001000",
            scores={"dangerous": 0.01, "sexual": 0.001, "violence": 0.001},
        )


class UnavailableQualityInspector:
    async def inspect(self, body) -> QualityResult:
        raise QualityUnavailable("invalid SAM3 response")


class ConfidentMatcher:
    async def recognize(self, body):
        return RecognitionResult(
            tuple(
                RecognitionCandidate(
                    slug=f"wine-{rank}",
                    score=1.0 - rank / 10,
                    rank=rank,
                    wine=wine(f"wine-{rank}"),
                )
                for rank in range(1, 5)
            ),
            "test-pipeline",
        )


async def test_admin_retry_moderates_the_accepted_copy_without_a_download(repository, tmp_path):
    request_id = reserve(repository)
    api = FakeMaxApi()
    api.downloads[image(1).url] = jpeg()
    moderator = CountingSafeModerator()
    services = SimpleNamespace(
        settings=SimpleNamespace(
            max_image_bytes=20 * 1024 * 1024,
            match_min_score=0.70,
            match_min_margin=0.015,
            admin_user_id=700,
        ),
        repository=repository,
        store=ImageStore(tmp_path / "images"),
        artifact_store=ArtifactStore(tmp_path / "images"),
        moderator=moderator,
        quality_inspector=UnavailableQualityInspector(),
        matcher=ConfidentMatcher(),
        image_loader=None,
        rejection_image=b"unused",
    )
    processor = PhotoProcessor(services, api)
    await processor.process(
        PhotoJob(
            request_id=request_id,
            chat_id=DIALOG_CHAT_ID,
            user_id=USER_ID,
            source_message_id="mid.source",
            received_at=1000,
            photo_id=9001,
            photo_url=image(1).url,
            status_enabled=False,
        )
    )
    assert repository.admin_request(request_id).status == "recognized"
    assert repository.safe_source(request_id) is not None
    assert len(api.calls_of("download")) == 1
    first_attempt_steps = len(repository.step_timings(request_id))

    assert repository.request_retry(request_id, 1200) == "requested"
    queue = FakeQueue()
    assert enqueue_admin_retries(repository, queue) == 1
    assert queue.jobs[0].local_path == repository.safe_source(request_id)[1]
    await processor.process(queue.jobs[0])

    retry_steps = [item.step for item in repository.step_timings(request_id)]
    retry_steps = retry_steps[first_attempt_steps:]
    assert repository.admin_request(request_id).status == "recognized"
    assert moderator.calls == 2
    assert "accepted_source" in retry_steps
    assert "max_download" not in retry_steps
    assert len(api.calls_of("download")) == 1


def test_restart_restores_an_interrupted_retry_with_its_local_copy(repository):
    request_id = reserve(repository)
    repository.update(
        request_id,
        status="recognized",
        moderation_safe=1,
        storage_path="accepted/2026/10/15/request.jpg",
    )
    assert repository.request_retry(request_id, 1200) == "requested"
    queue = FakeQueue()
    assert enqueue_admin_retries(repository, queue) == 1
    assert queue.jobs[0].local_path == "accepted/2026/10/15/request.jpg"
    # The processing starts and clears the moderation fields. Then the process stops.
    repository.update(request_id, status="processing", moderation_safe=None)

    restored = FakeQueue()
    assert restore_pending_jobs(repository, restored) == 1

    assert restored.jobs[0].local_path == "accepted/2026/10/15/request.jpg"
    assert restored.restore_flags == [True]


def test_restart_downloads_an_interrupted_first_attempt_again(repository):
    request_id = reserve(repository)
    repository.update(
        request_id,
        status="processing",
        moderation_safe=1,
        storage_path="accepted/2026/10/15/request.jpg",
    )
    queue = FakeQueue()

    restore_pending_jobs(repository, queue)

    # The same as the Telegram bot: a first attempt downloads the image again.
    assert queue.jobs[0].local_path is None


async def test_admin_retry_on_another_day_keeps_the_date_directory_of_the_files(
    repository, tmp_path
):
    request_id = reserve(repository)
    api = FakeMaxApi()
    api.downloads[image(1).url] = jpeg()
    services = SimpleNamespace(
        settings=SimpleNamespace(
            max_image_bytes=20 * 1024 * 1024,
            match_min_score=0.70,
            match_min_margin=0.015,
            admin_user_id=700,
        ),
        repository=repository,
        store=ImageStore(tmp_path / "images"),
        artifact_store=ArtifactStore(tmp_path / "images"),
        moderator=CountingSafeModerator(),
        quality_inspector=UnavailableQualityInspector(),
        matcher=ConfidentMatcher(),
        image_loader=None,
        rejection_image=b"unused",
    )
    processor = PhotoProcessor(services, api)
    await processor.process(
        PhotoJob(
            request_id=request_id,
            chat_id=DIALOG_CHAT_ID,
            user_id=USER_ID,
            source_message_id="mid.source",
            received_at=1000,
            photo_id=9001,
            photo_url=image(1).url,
            status_enabled=False,
        )
    )
    first_path = repository.safe_source(request_id)[1]
    retry_time = 1000 + 3 * 86400

    assert repository.request_retry(request_id, retry_time) == "requested"
    queue = FakeQueue()
    assert enqueue_admin_retries(repository, queue) == 1
    job = queue.jobs[0]
    assert (job.received_at, job.stored_at) == (retry_time, 1000)
    await processor.process(job)

    # Retention and user deletion use the first receipt date. The retry writes no file under
    # the retry date, so no copy escapes them.
    assert repository.safe_source(request_id)[1] == first_path
    assert first_path.startswith("accepted/1970/01/01/")
    assert not (tmp_path / "images" / "accepted" / "1970" / "01" / "04").exists()
    assert not (tmp_path / "images" / "artifacts" / "1970" / "01" / "04").exists()
    assert (tmp_path / "images" / "artifacts" / "1970" / "01" / "01" / request_id).is_dir()
