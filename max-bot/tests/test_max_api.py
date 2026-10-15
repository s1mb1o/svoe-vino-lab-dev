import asyncio
import hashlib
import itertools
import json
import ssl

import httpx
import pytest

from chto_za_vino_max_bot.max_api import (
    DEFAULT_CA_FILE,
    DEFAULT_CA_SHA256,
    MaxApi,
    MaxApiError,
    MaxTransportError,
    MediaTooLarge,
    MediaUnavailable,
    RateLimiter,
    callback_button,
    create_ssl_context,
    inline_keyboard,
    link_button,
)

TOKEN = "max-test-token-0123456789"
BASE = "https://platform-api2.max.example"


class Recorder:
    def __init__(self, *responses):
        self.requests: list[httpx.Request] = []
        self._responses = list(responses)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def make_api(handler, **options) -> tuple[MaxApi, list[float]]:
    """Return a client with a fake clock. Each sleep moves the clock forward."""
    sleeps: list[float] = []
    now = [1000.0]

    async def sleep(delay: float) -> None:
        # The global limiter of a test client waits microseconds. Only real waits are kept.
        if delay >= 0.001:
            sleeps.append(delay)
        now[0] += delay

    options.setdefault("global_rate", 1_000_000.0)
    options.setdefault("chat_rate", 1_000_000.0)
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    api = MaxApi(TOKEN, client, base_url=BASE, sleep=sleep, clock=lambda: now[0], **options)
    return api, sleeps


def message_answer(mid: str = "mid.1") -> httpx.Response:
    return httpx.Response(200, json={"message": {"body": {"mid": mid, "seq": 1}}})


def test_bundled_root_ca_is_the_mintsifry_root():
    pem = DEFAULT_CA_FILE.read_text(encoding="ascii")
    der = ssl.PEM_cert_to_DER_cert(pem)

    assert hashlib.sha256(der).hexdigest() == DEFAULT_CA_SHA256
    context = create_ssl_context()
    subjects = [dict(item[0] for item in cert["subject"]) for cert in context.get_ca_certs()]
    assert {"commonName": "Russian Trusted Root CA"}.items() <= {
        key: value
        for subject in subjects
        if subject.get("commonName") == "Russian Trusted Root CA"
        for key, value in subject.items()
    }.items()
    # The public roots stay trusted for the upload and download hosts.
    assert len(subjects) > 10


async def test_request_uses_raw_token_header_and_json_body():
    recorder = Recorder(message_answer("mid.42"))
    api, _ = make_api(recorder)

    message = await api.send_message(
        100,
        text="<b>Привет</b>",
        attachments=[inline_keyboard([[callback_button("Да", "yes")]])],
        reply_to="mid.source",
        disable_link_preview=True,
    )

    request = recorder.requests[0]
    assert message["body"]["mid"] == "mid.42"
    assert request.method == "POST"
    assert request.url.path == "/messages"
    assert request.headers["authorization"] == TOKEN
    assert "token" not in str(request.url).lower()
    assert request.url.params["chat_id"] == "100"
    assert request.url.params["disable_link_preview"] == "true"
    body = json.loads(request.content)
    assert body == {
        "text": "<b>Привет</b>",
        "attachments": [
            {
                "type": "inline_keyboard",
                "payload": {"buttons": [[{"type": "callback", "text": "Да", "payload": "yes"}]]},
            }
        ],
        "format": "html",
        "link": {"type": "reply", "mid": "mid.source"},
    }


async def test_link_preview_parameter_is_absent_by_default():
    recorder = Recorder(message_answer())
    api, _ = make_api(recorder)

    await api.send_message(100, text="text")

    assert "disable_link_preview" not in recorder.requests[0].url.params


async def test_error_answer_raises_without_token_or_url():
    recorder = Recorder(
        httpx.Response(401, json={"code": "verify.token", "message": "Invalid access_token"})
    )
    api, _ = make_api(recorder)

    with pytest.raises(MaxApiError) as error:
        await api.get_me()

    assert error.value.status == 401
    assert error.value.code == "verify.token"
    assert TOKEN not in str(error.value)
    assert BASE not in str(error.value)


async def test_unsuccessful_simple_result_raises():
    recorder = Recorder(httpx.Response(200, json={"success": False, "message": "not allowed"}))
    api, _ = make_api(recorder)

    with pytest.raises(MaxApiError) as error:
        await api.edit_message(100, "mid.1", text="new", attachments=[])

    assert error.value.code == "unsuccessful"
    assert error.value.description == "not allowed"


async def test_edit_sends_complete_attachment_list():
    recorder = Recorder(
        httpx.Response(200, json={"success": True}),
        httpx.Response(200, json={"success": True}),
    )
    api, _ = make_api(recorder)

    await api.edit_message(100, "mid.1", text="без клавиатуры", attachments=[])
    await api.edit_message(100, "mid.1", text="без изменений вложений", attachments=None)

    first = json.loads(recorder.requests[0].content)
    second = json.loads(recorder.requests[1].content)
    assert recorder.requests[0].method == "PUT"
    assert recorder.requests[0].url.params["message_id"] == "mid.1"
    assert first["attachments"] == []
    assert "attachments" not in second


async def test_send_repeats_only_rate_limited_requests():
    recorder = Recorder(httpx.Response(429, json={"code": "too.many.requests"}), message_answer())
    api, sleeps = make_api(recorder)

    await api.send_message(100, text="text")

    assert len(recorder.requests) == 2
    assert sleeps == [1.0]


@pytest.mark.parametrize(
    "failure",
    [httpx.Response(502, json={"code": "internal"}), httpx.ReadTimeout("timeout")],
)
async def test_send_is_not_repeated_after_an_ambiguous_failure(failure):
    recorder = Recorder(failure, message_answer())
    api, sleeps = make_api(recorder)

    with pytest.raises(MaxApiError):
        await api.send_message(100, text="text")

    assert len(recorder.requests) == 1
    assert sleeps == []


async def test_read_requests_repeat_transient_failures():
    recorder = Recorder(
        httpx.ConnectError("refused"),
        httpx.Response(503, json={"code": "unavailable"}),
        httpx.Response(200, json={"user_id": 1, "is_bot": True}),
    )
    api, sleeps = make_api(recorder)

    me = await api.get_me()

    assert me["user_id"] == 1
    assert sleeps == [1.0, 2.0]


async def test_transport_error_hides_the_request_url():
    recorder = Recorder(*[httpx.ConnectError(f"cannot connect to {BASE}")] * 4)
    api, _ = make_api(recorder)

    with pytest.raises(MaxTransportError) as error:
        await api.get_me()

    assert BASE not in str(error.value)
    assert error.value.__cause__ is None
    assert error.value.__suppress_context__


async def test_attachment_not_ready_is_repeated_with_backoff():
    not_ready = httpx.Response(400, json={"code": "attachment.not.ready", "message": ""})
    recorder = Recorder(not_ready, not_ready, message_answer())
    api, sleeps = make_api(recorder)

    await api.send_message(100, text="photo", attachments=[{"type": "image", "payload": {}}])

    assert len(recorder.requests) == 3
    assert sleeps == [1.0, 2.0]


async def test_rejected_reply_is_sent_without_the_link():
    recorder = Recorder(
        httpx.Response(400, json={"code": "message.not.found", "message": "no such message"}),
        message_answer(),
    )
    api, _ = make_api(recorder)

    await api.send_message(100, text="result", reply_to="mid.deleted")

    assert json.loads(recorder.requests[0].content)["link"]["mid"] == "mid.deleted"
    assert "link" not in json.loads(recorder.requests[1].content)


async def test_failed_reply_after_a_server_error_is_not_sent_again():
    recorder = Recorder(httpx.Response(500, json={"code": "internal"}), message_answer())
    api, _ = make_api(recorder)

    with pytest.raises(MaxApiError):
        await api.send_message(100, text="result", reply_to="mid.source")

    assert len(recorder.requests) == 1


async def test_text_longer_than_the_limit_is_rejected_before_the_call():
    recorder = Recorder()
    api, _ = make_api(recorder)

    with pytest.raises(ValueError):
        await api.send_message(100, text="x" * 4001)

    assert recorder.requests == []


async def test_answer_callback_sends_notification_and_message():
    recorder = Recorder(httpx.Response(200, json={"success": True}))
    api, _ = make_api(recorder)

    await api.answer_callback(
        100,
        "callback-1",
        notification="Спасибо!",
        message={"text": "new", "attachments": []},
        disable_link_preview=True,
    )

    request = recorder.requests[0]
    assert request.url.path == "/answers"
    assert request.url.params["callback_id"] == "callback-1"
    assert request.url.params["disable_link_preview"] == "true"
    assert json.loads(request.content) == {
        "notification": "Спасибо!",
        "message": {"text": "new", "attachments": []},
    }


async def test_get_updates_returns_updates_and_marker():
    recorder = Recorder(
        httpx.Response(
            200,
            json={"updates": [{"update_type": "bot_started"}, "garbage"], "marker": 42},
        )
    )
    api, _ = make_api(recorder)

    updates, marker = await api.get_updates(marker=41, timeout=30)

    params = recorder.requests[0].url.params
    assert updates == [{"update_type": "bot_started"}]
    assert marker == 42
    assert params["marker"] == "41"
    assert params["timeout"] == "30"
    assert params["types"] == "message_created,message_callback,bot_started"


async def test_get_updates_without_marker_omits_the_parameter():
    recorder = Recorder(httpx.Response(200, json={"updates": [], "marker": None}))
    api, _ = make_api(recorder)

    updates, marker = await api.get_updates(marker=None, timeout=0)

    assert updates == []
    assert marker is None
    assert "marker" not in recorder.requests[0].url.params


async def test_upload_image_posts_data_field_without_the_bot_token():
    upload_url = "https://iu.oneme.example/uploadImage?apiToken=x"
    recorder = Recorder(
        httpx.Response(200, json={"url": upload_url}),
        httpx.Response(200, json={"photos": {"7": {"token": "photo-token"}}}),
    )
    api, _ = make_api(recorder)

    payload, token = await api.upload_image(
        b"jpeg-bytes", filename="wine-result.jpg", content_type="image/jpeg"
    )

    endpoint, upload = recorder.requests
    assert endpoint.url.path == "/uploads"
    assert endpoint.url.params["type"] == "image"
    assert str(upload.url) == upload_url
    assert "authorization" not in upload.headers
    assert b'name="data"; filename="wine-result.jpg"' in upload.content
    assert payload == {"photos": {"7": {"token": "photo-token"}}}
    assert token == "photo-token"


async def test_upload_rejects_a_plain_http_upload_url():
    recorder = Recorder(httpx.Response(200, json={"url": "http://iu.oneme.example/upload"}))
    api, _ = make_api(recorder)

    with pytest.raises(MaxApiError):
        await api.upload_image(b"x", filename="a.jpg", content_type="image/jpeg")


async def test_download_streams_the_file_without_the_bot_token():
    recorder = Recorder(httpx.Response(200, content=b"image-bytes"))
    api, _ = make_api(recorder)

    body = await api.download("https://i.oneme.example/i?r=abc", max_bytes=100)

    assert body == b"image-bytes"
    assert "authorization" not in recorder.requests[0].headers


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, content=b"x" * 11, headers={"content-length": "11"}),
        httpx.Response(200, content=b"x" * 11),
    ],
)
async def test_download_enforces_the_size_limit(response):
    api, _ = make_api(Recorder(response))

    with pytest.raises(MediaTooLarge):
        await api.download("https://i.oneme.example/i", max_bytes=10)


async def test_download_accepts_only_https_and_allowed_hosts():
    api, _ = make_api(Recorder(), media_allowed_hosts=("oneme.example",))

    with pytest.raises(MediaUnavailable):
        await api.download("http://i.oneme.example/i", max_bytes=10)
    with pytest.raises(MediaUnavailable):
        await api.download("https://evil.example/i", max_bytes=10)
    with pytest.raises(MediaUnavailable):
        await api.download("https://notoneme.example/i", max_bytes=10)


async def test_download_error_does_not_carry_the_url():
    url = "https://i.oneme.example/i?r=secret-capability"
    api, _ = make_api(Recorder(httpx.ConnectError(f"failed {url}")))

    with pytest.raises(MediaUnavailable) as error:
        await api.download(url, max_bytes=10)

    assert "secret-capability" not in str(error.value)
    assert error.value.__cause__ is None


async def test_rate_limiter_spaces_operations():
    now = [0.0]
    sleeps: list[float] = []

    async def sleep(delay: float) -> None:
        sleeps.append(delay)
        now[0] += delay

    limiter = RateLimiter(2, clock=lambda: now[0], sleep=sleep)

    for _ in range(3):
        await limiter.acquire()

    assert sleeps == [pytest.approx(0.5), pytest.approx(0.5)]


async def test_chat_limiter_applies_per_chat():
    recorder = Recorder(*[message_answer(f"mid.{index}") for index in range(4)])
    api, sleeps = make_api(recorder, chat_rate=2)

    await api.send_message(1, text="a")
    await api.send_message(1, text="b")
    await api.send_message(2, text="c")

    # Two operations in one chat are 0.5 s apart. Another chat has its own limiter.
    assert sleeps == [pytest.approx(0.5, abs=1e-3)]


def test_api_requires_https_base_url_and_token():
    client = httpx.AsyncClient()
    with pytest.raises(ValueError):
        MaxApi("", client)
    with pytest.raises(ValueError):
        MaxApi(TOKEN, client, base_url="http://platform-api2.max.ru")


def test_keyboard_builders_produce_max_json():
    keyboard = inline_keyboard(
        [[link_button("Открыть страницу вина", "https://vino-svoe.ru/wines/x")]]
    )

    assert keyboard == {
        "type": "inline_keyboard",
        "payload": {
            "buttons": [
                [
                    {
                        "type": "link",
                        "text": "Открыть страницу вина",
                        "url": "https://vino-svoe.ru/wines/x",
                    }
                ]
            ]
        },
    }
    assert len(callback_button("x" * 200, "p")["text"]) == 128


async def test_download_follows_a_redirect_to_an_allowed_host():
    recorder = Recorder(
        httpx.Response(302, headers={"location": "https://cdn.oneme.example/file?x=1"}),
        httpx.Response(200, content=b"image-bytes"),
    )
    api, _ = make_api(recorder, media_allowed_hosts=("oneme.example",))

    body = await api.download("https://i.oneme.example/i?r=abc", max_bytes=100)

    assert body == b"image-bytes"
    assert str(recorder.requests[1].url) == "https://cdn.oneme.example/file?x=1"


@pytest.mark.parametrize(
    "location",
    ["http://cdn.oneme.example/file", "https://evil.example/file", ""],
)
async def test_download_rejects_an_unsafe_redirect(location):
    recorder = Recorder(httpx.Response(302, headers={"location": location}))
    api, _ = make_api(recorder, media_allowed_hosts=("oneme.example",))

    with pytest.raises(MediaUnavailable):
        await api.download("https://i.oneme.example/i", max_bytes=100)

    assert len(recorder.requests) == 1


async def test_download_stops_after_too_many_redirects():
    redirect = httpx.Response(302, headers={"location": "https://i.oneme.example/again"})
    recorder = Recorder(*[redirect] * 4)
    api, _ = make_api(recorder)

    with pytest.raises(MediaUnavailable):
        await api.download("https://i.oneme.example/i", max_bytes=100)

    assert len(recorder.requests) == 4


async def test_global_slot_is_taken_after_the_chat_wait():
    now = [0.0]
    dispatched: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        dispatched.append(now[0])
        return message_answer()

    async def sleep(delay: float) -> None:
        now[0] += delay

    api = MaxApi(
        TOKEN,
        httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        base_url=BASE,
        global_rate=2.0,
        chat_rate=1.0,
        sleep=sleep,
        clock=lambda: now[0],
    )

    await api.send_message(1, text="a")
    await api.send_message(1, text="b")
    await api.send_message(2, text="c")

    # "b" waits for its chat. "c" then still keeps the global interval of 0.5 s after "b".
    assert dispatched == [0.0, 1.0, 1.5]


async def test_chat_spacing_holds_when_the_global_limit_is_busy():
    now = [0.0]
    dispatched: list[tuple[str, float]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        dispatched.append((request.url.params["chat_id"], now[0]))
        return message_answer()

    async def sleep(delay: float) -> None:
        now[0] += delay

    api = MaxApi(
        TOKEN,
        httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        base_url=BASE,
        global_rate=2.5,
        chat_rate=2.0,
        sleep=sleep,
        clock=lambda: now[0],
    )

    for chat_id in (1, 2, 1, 1):
        await api.send_message(chat_id, text="x")

    chat_one = [moment for chat, moment in dispatched if chat == "1"]
    every = [moment for _, moment in dispatched]
    # Chat 1 keeps 0.5 s between its operations, and all operations keep 0.4 s.
    assert chat_one == pytest.approx([0.0, 0.8, 1.3])
    assert all(b - a >= 0.4 - 1e-9 for a, b in itertools.pairwise(every))


async def test_late_wakeup_moves_the_deadline_from_the_actual_time():
    now = [0.0]

    async def late_sleep(delay: float) -> None:
        now[0] += delay + 0.3

    limiter = RateLimiter(2, clock=lambda: now[0], sleep=late_sleep)

    await limiter.acquire()
    await limiter.acquire()
    marked = now[0]

    # The second operation woke up late, at 0.8 s. The next one waits until 0.8 + 0.5.
    assert marked == pytest.approx(0.8)
    assert limiter.wait_time(marked) == pytest.approx(0.5)


class VirtualTime:
    """A clock that moves only when the test moves it. A sleeper waits for its wake time."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleepers: list[tuple[float, asyncio.Future[None]]] = []

    async def sleep(self, delay: float) -> None:
        future = asyncio.get_running_loop().create_future()
        self.sleepers.append((self.now + delay, future))
        await future

    def advance(self, moment: float) -> None:
        self.now = moment
        for wake, future in list(self.sleepers):
            if wake <= moment:
                self.sleepers.remove((wake, future))
                future.set_result(None)


async def test_a_waiting_request_is_not_overtaken_by_a_new_request():
    clock = VirtualTime()
    order: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        order.append(request.url.params["chat_id"])
        return message_answer()

    api = MaxApi(
        TOKEN,
        httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        base_url=BASE,
        global_rate=10.0,
        chat_rate=1000.0,
        sleep=clock.sleep,
        clock=lambda: clock.now,
    )
    await api.send_message(1, text="first")
    waiter = asyncio.create_task(api.send_message(2, text="waits for the global slot"))
    for _ in range(20):
        await asyncio.sleep(0)
    assert len(clock.sleepers) == 1

    async def drive_time() -> None:
        while True:
            await asyncio.sleep(0)
            if clock.sleepers:
                clock.advance(min(wake for wake, _ in clock.sleepers))

    # The global slot is free again, but the waiter has not run yet. A new request arrives
    # in this moment, as after synchronous work that held the event loop.
    clock.advance(0.1)
    driver = asyncio.create_task(drive_time())
    try:
        await api.send_message(3, text="new request")
        await waiter
    finally:
        driver.cancel()

    assert order == ["1", "2", "3"]
