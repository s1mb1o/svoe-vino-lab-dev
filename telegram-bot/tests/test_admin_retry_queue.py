from chto_za_vino_bot.app import PhotoJob, enqueue_admin_retries
from chto_za_vino_bot.storage import Repository


class FakeQueue:
    def __init__(self):
        self.at_capacity = False
        self.jobs = []

    def submit(self, job):
        self.jobs.append(job)


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
    assert repository.admin_request(reservation.request_id).status == "queued"
    assert enqueue_admin_retries(repository, queue) == 0
    repository.close()
