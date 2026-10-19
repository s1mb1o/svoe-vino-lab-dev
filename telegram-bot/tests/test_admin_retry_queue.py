from chto_za_vino_bot.app import PhotoJob, enqueue_admin_retries, restore_pending_jobs
from chto_za_vino_bot.storage import Repository


class FakeQueue:
    def __init__(self):
        self.at_capacity = False
        self.jobs = []
        self.restore_flags = []

    def submit(self, job, *, restore=False):
        self.jobs.append(job)
        self.restore_flags.append(restore)


def test_admin_retry_enters_bot_queue(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    reservation = repository.reserve(
        chat_id=100,
        message_id=1,
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
    assert queue.jobs[0].stored_at == 1000
    assert queue.jobs[0].user_id == 200
    assert repository.admin_request(reservation.request_id).status == "queued"
    assert enqueue_admin_retries(repository, queue) == 0
    repository.close()


def test_restart_restores_an_interrupted_retry_with_the_first_receipt_date(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    reservation = repository.reserve(
        chat_id=100,
        message_id=1,
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
    repository.update(request_id, status="recognized", moderation_safe=1)
    assert repository.request_retry(request_id, 1000 + 3 * 86400) == "requested"
    assert enqueue_admin_retries(repository, FakeQueue()) == 1
    # The bot stops before the claimed retry finishes.
    queue = FakeQueue()

    assert restore_pending_jobs(repository, queue) == 1

    assert queue.restore_flags == [True]
    assert queue.jobs[0].request_id == request_id
    assert queue.jobs[0].stored_at == 1000
    assert queue.jobs[0].user_id == 200
    repository.close()
