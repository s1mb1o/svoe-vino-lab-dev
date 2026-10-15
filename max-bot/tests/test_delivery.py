import asyncio
import json

import httpx
import pytest

from chto_za_vino_max_bot.delivery import (
    MARKER_KEY,
    Poller,
    UpdateDispatcher,
    create_webhook_app,
    stored_marker,
)
from chto_za_vino_max_bot.max_api import MaxApiError
from chto_za_vino_max_bot.storage import Repository
from chto_za_vino_max_bot.updates import BotStarted, IncomingMessage

SECRET = "webhook-secret-0123456789-abcdefghij"


def started(user_id: int, *, timestamp: int = 1, payload: str | None = None) -> dict[str, object]:
    return {
        "update_type": "bot_started",
        "timestamp": timestamp,
        "chat_id": 1000 + user_id,
        "user": {"user_id": user_id, "first_name": "User", "is_bot": False},
        "payload": payload,
    }


def created(mid: str, user_id: int = 5) -> dict[str, object]:
    return {
        "update_type": "message_created",
        "timestamp": 1,
        "message": {
            "recipient": {"chat_id": 99, "chat_type": "dialog"},
            "timestamp": 1,
            "body": {"mid": mid, "seq": 1, "text": "hello"},
            "sender": {"user_id": user_id, "first_name": "U", "is_bot": False},
        },
    }


class Collector:
    def __init__(self, *, fail_on: set[str] | None = None) -> None:
        self.seen: list[object] = []
        self._fail_on = fail_on or set()

    async def __call__(self, update) -> None:
        self.seen.append(update)
        if isinstance(update, IncomingMessage) and update.message_id in self._fail_on:
            raise RuntimeError("handler failure")


async def test_dispatcher_handles_updates_in_arrival_order(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    collector = Collector()
    dispatcher = UpdateDispatcher(repository, collector)

    dispatcher.admit([created("mid.1"), started(7), created("mid.2")])
    handled = await dispatcher.run_once()

    assert handled == 3
    assert [type(update).__name__ for update in collector.seen] == [
        "IncomingMessage",
        "BotStarted",
        "IncomingMessage",
    ]
    assert repository.pending_updates() == []


async def test_dispatcher_drops_a_repeated_delivery(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    collector = Collector()
    dispatcher = UpdateDispatcher(repository, collector)

    assert dispatcher.admit([created("mid.1")]) == 1
    await dispatcher.run_once()
    assert dispatcher.admit([created("mid.1")]) == 0
    await dispatcher.run_once()

    assert len(collector.seen) == 1


async def test_two_users_starting_at_the_same_time_are_both_handled(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    collector = Collector()
    dispatcher = UpdateDispatcher(repository, collector)

    dispatcher.admit([started(1, timestamp=50), started(2, timestamp=50)])
    await dispatcher.run_once()

    assert [update.user.user_id for update in collector.seen] == [1, 2]


async def test_failed_update_does_not_stop_the_next_updates(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    collector = Collector(fail_on={"mid.bad"})
    dispatcher = UpdateDispatcher(repository, collector)

    dispatcher.admit([created("mid.bad"), created("mid.good")])
    await dispatcher.run_once()

    assert [update.message_id for update in collector.seen] == ["mid.bad", "mid.good"]
    assert repository.pending_updates() == []


async def test_unprocessed_updates_are_replayed_after_a_restart(tmp_path):
    database = tmp_path / "bot.sqlite3"
    repository = Repository(database)
    UpdateDispatcher(repository, Collector()).admit([created("mid.1"), created("mid.2")])
    repository.close()

    restarted = Repository(database)
    collector = Collector()
    await UpdateDispatcher(restarted, collector).run_once()

    assert [update.message_id for update in collector.seen] == ["mid.1", "mid.2"]


async def test_ignored_update_types_are_not_stored(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    dispatcher = UpdateDispatcher(repository, Collector())

    admitted = dispatcher.admit(
        [{"update_type": "dialog_muted", "timestamp": 1}, {"update_type": "message_created"}]
    )

    assert admitted == 0
    assert repository.pending_updates() == []


async def test_dispatcher_run_wakes_up_for_a_new_update(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    collector = Collector()
    dispatcher = UpdateDispatcher(repository, collector)
    task = asyncio.create_task(dispatcher.run())
    try:
        await asyncio.sleep(0)
        dispatcher.admit([started(3)])
        for _ in range(50):
            if collector.seen:
                break
            await asyncio.sleep(0.01)
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    assert isinstance(collector.seen[0], BotStarted)


class FakeUpdatesApi:
    def __init__(self, *results) -> None:
        self.results = list(results)
        self.markers: list[int | None] = []
        self.subscriptions: list[dict[str, object]] = []

    async def get_updates(self, *, marker, timeout, types):
        self.markers.append(marker)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    async def get_subscriptions(self):
        return self.subscriptions


async def test_poller_stores_the_marker_with_the_updates(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    dispatcher = UpdateDispatcher(repository, Collector())
    api = FakeUpdatesApi(([created("mid.1")], 77), ([], None))
    poller = Poller(api, dispatcher, repository)

    marker = await poller.poll_once(None)
    marker = await poller.poll_once(marker)

    assert api.markers == [None, 77]
    assert marker == 77
    assert stored_marker(repository) == 77
    assert repository.state(MARKER_KEY) == "77"
    assert [item.update_key for item in repository.pending_updates()] == [
        "message_created:mid.1"
    ]


async def test_poller_resumes_from_the_stored_marker(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    repository.set_state(MARKER_KEY, "12", 1)
    dispatcher = UpdateDispatcher(repository, Collector())
    stop = MaxApiError(401, "verify.token", "Invalid access_token")
    api = FakeUpdatesApi(stop)

    async def sleep(delay: float) -> None:
        return None

    with pytest.raises(MaxApiError):
        await Poller(api, dispatcher, repository, sleep=sleep).run()

    assert api.markers == [12]


async def test_poller_backs_off_after_errors(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    dispatcher = UpdateDispatcher(repository, Collector())
    api = FakeUpdatesApi(
        MaxApiError(503, "unavailable", None),
        MaxApiError(0, "transport", "ConnectError"),
        ([], 5),
        MaxApiError(401, "verify.token", None),
    )
    sleeps: list[float] = []
    now = [0.0]

    async def sleep(delay: float) -> None:
        sleeps.append(delay)
        now[0] += delay

    with pytest.raises(MaxApiError):
        await Poller(api, dispatcher, repository, sleep=sleep, clock=lambda: now[0]).run()

    backoff = [delay for delay in sleeps if delay >= 1]
    assert backoff == [1.0, 2.0]
    assert api.markers == [None, None, None, 5]


async def test_poller_refuses_to_run_with_an_active_webhook(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    api = FakeUpdatesApi()
    api.subscriptions = [{"url": "https://bot.example/max", "time": 1}]
    poller = Poller(api, UpdateDispatcher(repository, Collector()), repository)

    with pytest.raises(RuntimeError, match="webhook subscription is active"):
        await poller.check_no_webhook()


def webhook_client(dispatcher: UpdateDispatcher) -> httpx.AsyncClient:
    app = create_webhook_app(path="/max/webhook", secret=SECRET, dispatcher=dispatcher)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_webhook_stores_an_update_with_the_correct_secret(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    dispatcher = UpdateDispatcher(repository, Collector())

    async with webhook_client(dispatcher) as client:
        response = await client.post(
            "/max/webhook",
            content=json.dumps(created("mid.1")),
            headers={"X-Max-Bot-Api-Secret": SECRET, "Content-Type": "application/json"},
        )
        repeated = await client.post(
            "/max/webhook",
            content=json.dumps(created("mid.1")),
            headers={"X-Max-Bot-Api-Secret": SECRET},
        )

    assert response.status_code == 200
    assert repeated.status_code == 200
    assert [item.update_key for item in repository.pending_updates()] == [
        "message_created:mid.1"
    ]


@pytest.mark.parametrize("secret", [None, "", "wrong-secret-0123456789-abcdefghijk"])
async def test_webhook_rejects_a_missing_or_wrong_secret(tmp_path, secret):
    repository = Repository(tmp_path / "bot.sqlite3")
    headers = {} if secret is None else {"X-Max-Bot-Api-Secret": secret}

    async with webhook_client(UpdateDispatcher(repository, Collector())) as client:
        response = await client.post(
            "/max/webhook", content=json.dumps(created("mid.1")), headers=headers
        )

    assert response.status_code == 401
    assert repository.pending_updates() == []


@pytest.mark.parametrize("body", [b"not json", b"[1, 2]"])
async def test_webhook_rejects_an_invalid_body(tmp_path, body):
    repository = Repository(tmp_path / "bot.sqlite3")

    async with webhook_client(UpdateDispatcher(repository, Collector())) as client:
        response = await client.post(
            "/max/webhook", content=body, headers={"X-Max-Bot-Api-Secret": SECRET}
        )

    assert response.status_code == 400


async def test_webhook_rejects_a_large_body(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")

    async with webhook_client(UpdateDispatcher(repository, Collector())) as client:
        response = await client.post(
            "/max/webhook",
            content=b"{" + b" " * (1024 * 1024 + 10) + b"}",
            headers={"X-Max-Bot-Api-Secret": SECRET},
        )

    assert response.status_code == 413


async def test_webhook_answers_503_when_the_update_is_not_stored(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    dispatcher = UpdateDispatcher(repository, Collector())
    repository.close()

    async with webhook_client(dispatcher) as client:
        response = await client.post(
            "/max/webhook",
            content=json.dumps(created("mid.1")),
            headers={"X-Max-Bot-Api-Secret": SECRET},
        )

    # MAX repeats a delivery that did not get HTTP 200.
    assert response.status_code == 503


async def test_webhook_has_no_public_api_documentation(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")

    async with webhook_client(UpdateDispatcher(repository, Collector())) as client:
        docs = await client.get("/docs")
        schema = await client.get("/openapi.json")
        health = await client.get("/healthz")

    assert docs.status_code == 404
    assert schema.status_code == 404
    assert health.text == "ok"
