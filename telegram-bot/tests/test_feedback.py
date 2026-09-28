from types import SimpleNamespace

from chto_za_vino_bot.app import (
    handle_alternative_feedback,
    handle_moderation_appeal,
    handle_result_feedback,
)
from chto_za_vino_bot.storage import CandidateRecord, Repository


class FakeCallbackMessage:
    def __init__(self) -> None:
        self.markups = []
        self.answers = []

    async def edit_reply_markup(self, *, reply_markup) -> None:
        self.markups.append(reply_markup)

    async def answer(self, text: str, *, reply_markup) -> None:
        self.answers.append((text, reply_markup))


class FailingEditCallbackMessage(FakeCallbackMessage):
    async def edit_reply_markup(self, *, reply_markup) -> None:
        raise RuntimeError("Telegram edit failure")


class FakeCallback:
    def __init__(self, data: str, user_id: int) -> None:
        self.data = data
        self.from_user = SimpleNamespace(id=user_id)
        self.message = None
        self.answers: list[tuple[str | None, bool]] = []

    async def answer(
        self,
        text: str | None = None,
        *,
        show_alert: bool = False,
    ) -> None:
        self.answers.append((text, show_alert))


def card(slug: str, name: str | None = None) -> dict[str, object]:
    return {
        "name": name or slug,
        "page_url": f"https://vino-svoe.ru/wines/{slug}",
        "producer": None,
        "category": None,
        "color": None,
        "grapes": None,
        "sugar": None,
        "image_url": None,
        "qr_urls": [],
    }


def recognized_request(repository: Repository) -> str:
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
    repository.update(reservation.request_id, status="recognized")
    return reservation.request_id


async def test_result_feedback_is_saved_for_source_user(tmp_path, monkeypatch):
    repository = Repository(tmp_path / "bot.sqlite3")
    request_id = recognized_request(repository)
    callback = FakeCallback(f"feedback:yes:{request_id}", 200)
    monkeypatch.setattr("chto_za_vino_bot.app.time.time", lambda: 1200)

    await handle_result_feedback(callback, SimpleNamespace(repository=repository))

    assert callback.answers == [("Спасибо! Оценка сохранена.", False)]
    assert (
        repository.save_feedback(
            request_id=request_id,
            user_id=200,
            matched=False,
            now=1300,
        )
        == "already_saved"
    )
    repository.close()


async def test_result_feedback_rejects_another_user(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    request_id = recognized_request(repository)
    callback = FakeCallback(f"feedback:no:{request_id}", 201)

    await handle_result_feedback(callback, SimpleNamespace(repository=repository))

    assert callback.answers == [("Эта оценка недоступна.", True)]
    repository.close()


async def test_negative_feedback_shows_three_alternatives(tmp_path, monkeypatch):
    repository = Repository(tmp_path / "bot.sqlite3")
    request_id = recognized_request(repository)
    repository.replace_candidates(
        request_id,
        [
            CandidateRecord(
                rank,
                f"wine-{rank}",
                1.0 - rank / 10,
                card(f"wine-{rank}", f"Название wine-{rank}"),
            )
            for rank in range(1, 5)
        ],
    )
    callback = FakeCallback(f"feedback:no:{request_id}", 200)
    callback.message = FakeCallbackMessage()
    monkeypatch.setattr("chto_za_vino_bot.app.Message", FakeCallbackMessage)
    await handle_result_feedback(
        callback,
        SimpleNamespace(repository=repository),
    )

    assert callback.answers == [("Спасибо! Выберите возможный вариант.", False)]
    rows = callback.message.markups[0].inline_keyboard
    assert [row[0].text for row in rows] == [
        "2. Название wine-2",
        "3. Название wine-3",
        "4. Название wine-4",
        "Ничего из этого",
    ]
    repository.close()


async def test_negative_feedback_retry_restores_alternatives(tmp_path, monkeypatch):
    repository = Repository(tmp_path / "bot.sqlite3")
    request_id = recognized_request(repository)
    repository.replace_candidates(
        request_id,
        [
            CandidateRecord(rank, f"wine-{rank}", 1.0 - rank / 10, card(f"wine-{rank}"))
            for rank in range(1, 5)
        ],
    )
    assert repository.save_feedback(
        request_id=request_id,
        user_id=200,
        matched=False,
        now=1100,
    ) == "saved"
    callback = FakeCallback(f"feedback:no:{request_id}", 200)
    callback.message = FakeCallbackMessage()
    monkeypatch.setattr("chto_za_vino_bot.app.Message", FakeCallbackMessage)
    await handle_result_feedback(
        callback,
        SimpleNamespace(repository=repository),
    )

    assert callback.answers == [
        ("Оценка уже сохранена. Показываю варианты.", False)
    ]
    assert len(callback.message.markups[0].inline_keyboard) == 4
    repository.close()


async def test_negative_feedback_sends_fallback_when_edit_fails(tmp_path, monkeypatch):
    repository = Repository(tmp_path / "bot.sqlite3")
    request_id = recognized_request(repository)
    repository.replace_candidates(
        request_id,
        [
            CandidateRecord(rank, f"wine-{rank}", 1.0 - rank / 10, card(f"wine-{rank}"))
            for rank in range(1, 5)
        ],
    )
    callback = FakeCallback(f"feedback:no:{request_id}", 200)
    callback.message = FailingEditCallbackMessage()
    monkeypatch.setattr(
        "chto_za_vino_bot.app.Message",
        FailingEditCallbackMessage,
    )
    await handle_result_feedback(
        callback,
        SimpleNamespace(repository=repository),
    )

    assert callback.message.answers[0][0] == "Возможные варианты:"
    assert len(callback.message.answers[0][1].inline_keyboard) == 4
    repository.close()


async def test_negative_feedback_uses_the_slug_for_a_candidate_without_a_card(
    tmp_path, monkeypatch
):
    repository = Repository(tmp_path / "bot.sqlite3")
    request_id = recognized_request(repository)
    repository.replace_candidates(
        request_id,
        [CandidateRecord(rank, f"wine-{rank}", 1.0 - rank / 10) for rank in range(1, 5)],
    )
    callback = FakeCallback(f"feedback:no:{request_id}", 200)
    callback.message = FakeCallbackMessage()
    monkeypatch.setattr("chto_za_vino_bot.app.Message", FakeCallbackMessage)

    await handle_result_feedback(callback, SimpleNamespace(repository=repository))

    rows = callback.message.markups[0].inline_keyboard
    assert [row[0].text for row in rows] == [
        "2. wine-2",
        "3. wine-3",
        "4. wine-4",
        "Ничего из этого",
    ]
    repository.close()


async def test_negative_feedback_shows_the_available_alternatives(tmp_path, monkeypatch):
    repository = Repository(tmp_path / "bot.sqlite3")
    request_id = recognized_request(repository)
    repository.replace_candidates(
        request_id,
        [
            CandidateRecord(1, "wine-1", 0.9, card("wine-1")),
            CandidateRecord(2, "wine-2", 0.8, card("wine-2", "Второе вино")),
        ],
    )
    callback = FakeCallback(f"feedback:no:{request_id}", 200)
    callback.message = FakeCallbackMessage()
    monkeypatch.setattr("chto_za_vino_bot.app.Message", FakeCallbackMessage)

    await handle_result_feedback(callback, SimpleNamespace(repository=repository))

    rows = callback.message.markups[0].inline_keyboard
    assert [row[0].text for row in rows] == ["2. Второе вино", "Ничего из этого"]
    repository.close()


async def test_negative_feedback_without_alternatives_shows_an_alert(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    request_id = recognized_request(repository)
    repository.replace_candidates(
        request_id,
        [CandidateRecord(1, "wine-1", 0.9, card("wine-1"))],
    )
    callback = FakeCallback(f"feedback:no:{request_id}", 200)

    await handle_result_feedback(callback, SimpleNamespace(repository=repository))

    assert callback.answers == [
        ("Оценка сохранена, но альтернативы для этого результата недоступны.", True)
    ]
    repository.close()


async def test_alternative_and_moderation_callbacks_are_saved(tmp_path, monkeypatch):
    repository = Repository(tmp_path / "bot.sqlite3")
    request_id = recognized_request(repository)
    repository.replace_candidates(
        request_id,
        [
            CandidateRecord(1, "wine-1", 0.9),
            CandidateRecord(2, "wine-2", 0.8),
        ],
    )
    assert repository.save_feedback(
        request_id=request_id,
        user_id=200,
        matched=False,
        now=1100,
    ) == "saved"
    alternative = FakeCallback(f"alternative:2:{request_id}", 200)
    alternative.message = FakeCallbackMessage()
    monkeypatch.setattr("chto_za_vino_bot.app.Message", FakeCallbackMessage)

    await handle_alternative_feedback(
        alternative,
        SimpleNamespace(repository=repository),
    )

    assert alternative.answers == [("Спасибо! Ответ сохранён.", False)]
    assert alternative.message.markups == [None]

    quarantined = repository.reserve(
        chat_id=100,
        message_id=11,
        user_id=200,
        username="tester",
        first_name="Test",
        last_name=None,
        file_id="file-2",
        file_unique_id="unique-2",
        now=1200,
        limit=50,
        window_seconds=3600,
    )
    assert quarantined.request_id is not None
    repository.update(quarantined.request_id, status="quarantined")
    appeal = FakeCallback(f"moderation_error:{quarantined.request_id}", 200)
    appeal.message = FakeCallbackMessage()

    await handle_moderation_appeal(appeal, SimpleNamespace(repository=repository))

    assert appeal.answers == [("Спасибо! Проверим срабатывание фильтра.", False)]
    assert appeal.message.markups == [None]
    repository.close()
