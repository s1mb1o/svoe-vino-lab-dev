from types import SimpleNamespace

from fastapi.testclient import TestClient

from chto_za_vino_bot.app import submit_http_image
from chto_za_vino_bot.http_api import (
    HttpQueueFull,
    HttpQueueUnavailable,
    HttpRecognitionResult,
    create_http_api_app,
)
from chto_za_vino_bot.storage import CandidateRecord, Repository
from chto_za_vino_bot.wine import Wine, unknown_wine, wine_card
from chto_za_vino_bot.work_queue import WorkQueue


def api(recognize, *, max_image_bytes=1024, networks=("127.0.0.1/32",)):
    return create_http_api_app(
        allowed_networks=networks,
        max_image_bytes=max_image_bytes,
        recognize=recognize,
    )


def test_recognition_api_accepts_one_in_memory_multipart_image():
    received = []

    async def recognize(body):
        received.append(body)
        return HttpRecognitionResult(
            200,
            {
                "request_id": "request-1",
                "status": "recognized",
                "recognition": {"wine": {"name": "Test wine"}},
            },
        )

    with TestClient(api(recognize), client=("127.0.0.1", 50000)) as client:
        response = client.post(
            "/api/v1/recognize",
            files={"image": ("wine.jpg", b"jpeg-body", "image/jpeg")},
        )
        openapi = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["status"] == "recognized"
    assert received == [b"jpeg-body"]
    request_body = openapi.json()["paths"]["/api/v1/recognize"]["post"]["requestBody"]
    assert "multipart/form-data" in request_body["content"]


def test_recognition_api_requires_exactly_one_image_field():
    async def recognize(body):
        raise AssertionError("recognition must not run")

    with TestClient(api(recognize), client=("127.0.0.1", 50000)) as client:
        missing = client.post(
            "/api/v1/recognize",
            files={"other": ("wine.jpg", b"jpeg-body", "image/jpeg")},
        )
        duplicate = client.post(
            "/api/v1/recognize",
            files=[
                ("image", ("one.jpg", b"one", "image/jpeg")),
                ("image", ("two.jpg", b"two", "image/jpeg")),
            ],
        )
        wrong_type = client.post(
            "/api/v1/recognize",
            content=b"jpeg-body",
            headers={"content-type": "image/jpeg"},
        )

    assert missing.status_code == 400
    assert duplicate.status_code == 400
    assert wrong_type.status_code == 415


def test_recognition_api_enforces_image_size_and_lan():
    async def recognize(body):
        raise AssertionError("recognition must not run")

    with TestClient(
        api(recognize, max_image_bytes=4),
        client=("127.0.0.1", 50000),
    ) as client:
        oversized = client.post(
            "/api/v1/recognize",
            files={"image": ("wine.jpg", b"12345", "image/jpeg")},
        )
    with TestClient(
        api(recognize),
        client=("10.0.0.20", 50000),
    ) as client:
        forbidden = client.get("/api/v1/healthz")

    assert oversized.status_code == 413
    assert forbidden.status_code == 403


def test_recognition_api_maps_queue_failures():
    async def full(body):
        raise HttpQueueFull("full")

    async def unavailable(body):
        raise HttpQueueUnavailable("stopped")

    with TestClient(api(full), client=("127.0.0.1", 50000)) as client:
        full_response = client.post(
            "/api/v1/recognize",
            files={"image": ("wine.jpg", b"body", "image/jpeg")},
        )
    with TestClient(api(unavailable), client=("127.0.0.1", 50000)) as client:
        unavailable_response = client.post(
            "/api/v1/recognize",
            files={"image": ("wine.jpg", b"body", "image/jpeg")},
        )

    assert full_response.status_code == 503
    assert full_response.json()["error"] == "queue_full"
    assert full_response.headers["retry-after"] == "20"
    assert unavailable_response.status_code == 503
    assert unavailable_response.json()["error"] == "queue_unavailable"


async def test_http_submission_uses_work_queue_and_returns_full_result(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    wine = Wine(
        slug="wine-1",
        name="Тестовое вино",
        page_url="https://vino-svoe.ru/wines/wine-1",
        producer="Test producer",
        category="Тихое",
        color="Красное",
        grapes="Пино Нуар",
        sugar="Сухое",
        image_url="https://api.vino-svoe.ru/test.jpg",
        qr_urls=("https://producer.example/wine-1",),
    )
    services = SimpleNamespace(repository=repository)

    async def handler(job):
        repository.update(
            job.request_id,
            status="recognized",
            moderation_safe=1,
            moderation_category="safe",
            moderation_confidence=0.01,
            moderation_reason="dangerous=0.010000,sexual=0.001000,violence=0.001000",
            quality_acceptable=1,
            quality_issues="",
            recognition_slug="wine-1",
            recognition_name=wine.name,
            recognition_page_url=wine.page_url,
            recognition_score=0.91,
            recognition_margin=0.12,
            matcher_pipeline="test-pipeline",
            duration_ms=1500,
        )
        repository.replace_candidates(
            job.request_id,
            [CandidateRecord(1, "wine-1", 0.9, wine_card(wine))]
            + [
                CandidateRecord(
                    rank, f"wine-{rank}", 1.0 - rank / 10, wine_card(unknown_wine(f"wine-{rank}"))
                )
                for rank in range(2, 5)
            ],
        )
        job.completion.set_result(None)

    queue = WorkQueue(handler, worker_count=1, capacity=2)
    await queue.start()
    try:
        result = await submit_http_image(services, queue, b"image")
    finally:
        await queue.stop()
        repository.close()

    assert result.status_code == 200
    assert result.body["status"] == "recognized"
    assert result.body["matcher_pipeline"] == "test-pipeline"
    assert result.body["moderation"]["performed"] is True
    assert result.body["moderation"]["bypassed"] is False
    assert result.body["moderation"]["safe"] is True
    assert result.body["recognition"]["wine"]["color"] == "Красное"
    assert result.body["recognition"]["wine"]["name"] == "Тестовое вино"
    assert result.body["recognition"]["wine"]["qr_urls"] == [
        "https://producer.example/wine-1"
    ]
    assert len(result.body["recognition"]["candidates"]) == 4
    assert result.body["recognition"]["candidates"][0]["wine"]["qr_urls"] == [
        "https://producer.example/wine-1"
    ]
    assert "qr_urls" not in result.body["recognition"]["candidates"][1]["wine"]
    assert result.body["timings"][-1]["step"] == "http_response_build"


async def test_http_result_exposes_moderation_bypass_without_claiming_safe(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    services = SimpleNamespace(repository=repository)

    async def handler(job):
        repository.update(
            job.request_id,
            status="abstained",
            moderation_safe=None,
            moderation_category="disabled",
            moderation_confidence=0.0,
            moderation_reason="moderation_disabled",
        )
        job.completion.set_result(None)

    queue = WorkQueue(handler, worker_count=1, capacity=2)
    await queue.start()
    try:
        result = await submit_http_image(services, queue, b"image")
    finally:
        await queue.stop()
        repository.close()

    assert result.body["moderation"] == {
        "performed": False,
        "bypassed": True,
        "safe": None,
        "category": "disabled",
        "confidence": 0.0,
        "scores": {},
    }


async def test_http_result_of_an_old_request_uses_minimal_cards(tmp_path):
    repository = Repository(tmp_path / "bot.sqlite3")
    services = SimpleNamespace(repository=repository)

    async def handler(job):
        repository.update(job.request_id, status="recognized", recognition_slug="wine-1")
        repository.replace_candidates(
            job.request_id,
            [CandidateRecord(1, "wine-1", 0.9), CandidateRecord(2, "wine-2", 0.8)],
        )
        job.completion.set_result(None)

    queue = WorkQueue(handler, worker_count=1, capacity=2)
    await queue.start()
    try:
        result = await submit_http_image(services, queue, b"image")
    finally:
        await queue.stop()
        repository.close()

    assert result.body["matcher_pipeline"] is None
    assert result.body["recognition"]["wine"]["name"] == "wine-1"
    assert result.body["recognition"]["wine"]["page_url"] == "https://vino-svoe.ru/wines/wine-1"
    assert [item["wine"]["name"] for item in result.body["recognition"]["candidates"]] == [
        "wine-1",
        "wine-2",
    ]
