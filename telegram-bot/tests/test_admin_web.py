import re

from fastapi.testclient import TestClient

from chto_za_vino_bot.admin_web import create_app
from chto_za_vino_bot.config import AdminWebSettings
from chto_za_vino_bot.storage import ArtifactStore, ArtifactWrite, Repository


def settings(tmp_path):
    return AdminWebSettings(
        data_root=tmp_path / "data",
        database_file=tmp_path / "bot.sqlite3",
        username="admin",
        password="correct-horse",
        host="127.0.0.1",
        port=8172,
        allowed_networks=("127.0.0.1/32",),
        rate_limit=50,
        rate_window_seconds=3600,
        log_level="INFO",
    )


def seed_request(path, *, safe=True):
    repository = Repository(path)
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
        status="recognized" if safe else "quarantined",
        moderation_safe=int(safe),
        storage_path="accepted/private.jpg" if safe else "quarantine/private.jpg",
        recognition_name="Test wine" if safe else None,
    )
    repository.close()
    return reservation.request_id


def csrf_from(body):
    match = re.search(r'name="csrf" value="([^"]+)"', body)
    assert match is not None
    return match.group(1)


def test_admin_requires_lan_address_and_password(tmp_path):
    app = create_app(settings(tmp_path))
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        response = client.get("/")
        assert response.status_code == 401
        assert response.headers["www-authenticate"].startswith("Basic")
        assert response.headers["x-frame-options"] == "DENY"
        assert client.get("/", auth=("admin", "wrong")).status_code == 401
        assert client.get("/", auth=("admin", "correct-horse")).status_code == 200

    blocked_app = create_app(settings(tmp_path / "blocked"))
    with TestClient(blocked_app, client=("10.0.0.10", 50000)) as client:
        assert client.get("/healthz").status_code == 403


def test_admin_pages_do_not_disclose_source_image_paths(tmp_path):
    web_settings = settings(tmp_path)
    request_id = seed_request(web_settings.database_file)
    app = create_app(web_settings)
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        response = client.get(f"/requests/{request_id}", auth=("admin", "correct-horse"))
        assert response.status_code == 200
        assert "Test wine" in response.text
        assert 'class="detail-grid"' in response.text
        assert "minmax(min(100%,480px),1fr)" in response.text
        assert "overflow-wrap:anywhere" in response.text
        assert "Визуальные этапы" in response.text
        assert "Артефакты не сохранены" in response.text
        assert "accepted/private.jpg" not in response.text
        assert "quarantine/private.jpg" not in response.text


def test_admin_serves_only_indexed_artifacts_for_safe_requests(tmp_path):
    web_settings = settings(tmp_path)
    request_id = seed_request(web_settings.database_file)
    body = b"safe-artifact"
    relative_path = ArtifactStore(web_settings.data_root).save(
        request_id,
        1000,
        "sam3_overlay",
        "image/png",
        body,
    )
    repository = Repository(web_settings.database_file)
    repository.replace_artifacts(
        request_id,
        [
            ArtifactWrite(
                artifact_key="sam3_overlay",
                step="quality",
                title="SAM3 overlay",
                description="Masks and boxes.",
                mime_type="image/png",
                relative_path=relative_path,
                width=10,
                height=20,
                ordinal=30,
                metadata={"segments": 2},
            )
        ],
        1100,
    )
    repository.close()
    app = create_app(web_settings)
    auth = ("admin", "correct-horse")
    url = f"/requests/{request_id}/artifacts/sam3_overlay"
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        assert client.get(url).status_code == 401
        detail = client.get(f"/requests/{request_id}", auth=auth)
        assert "SAM3 overlay" in detail.text
        assert "img-src 'self'" in detail.headers["content-security-policy"]
        response = client.get(url, auth=auth)
        assert response.status_code == 200
        assert response.content == body
        app.state.repository.update(request_id, moderation_safe=0)
        assert client.get(url, auth=auth).status_code == 404


def test_admin_serves_only_censored_derivative_for_quarantined_request(tmp_path):
    web_settings = settings(tmp_path)
    request_id = seed_request(web_settings.database_file, safe=False)
    relative_path = ArtifactStore(web_settings.data_root).save(
        request_id,
        1000,
        "censored_preview",
        "image/jpeg",
        b"blurred-preview",
    )
    repository = Repository(web_settings.database_file)
    repository.replace_artifacts(
        request_id,
        [
            ArtifactWrite(
                artifact_key="censored_preview",
                step="censored",
                title="Цензурированное изображение",
                description="Сильно размытый preview.",
                mime_type="image/jpeg",
                relative_path=relative_path,
                width=100,
                height=200,
                ordinal=10,
                metadata={"blur_radius": 18},
                exposure="censored",
            ),
            ArtifactWrite(
                artifact_key="unsafe_full",
                step="input",
                title="Unsafe full image",
                description="Must not be visible.",
                mime_type="image/jpeg",
                relative_path="quarantine/private.jpg",
                width=100,
                height=200,
                ordinal=20,
                metadata={},
                exposure="safe",
            ),
        ],
        1100,
    )
    repository.close()
    app = create_app(web_settings)
    auth = ("admin", "correct-horse")
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        detail = client.get(f"/requests/{request_id}", auth=auth)
        assert detail.status_code == 200
        assert "Цензурированное изображение" in detail.text
        assert "Unsafe full image" not in detail.text
        assert client.get(
            f"/requests/{request_id}/artifacts/censored_preview",
            auth=auth,
        ).status_code == 200
        assert client.get(
            f"/requests/{request_id}/artifacts/unsafe_full",
            auth=auth,
        ).status_code == 404


def test_admin_reset_and_retry_require_csrf(tmp_path):
    web_settings = settings(tmp_path)
    request_id = seed_request(web_settings.database_file)
    app = create_app(web_settings)
    auth = ("admin", "correct-horse")
    with TestClient(app, client=("127.0.0.1", 50000), follow_redirects=False) as client:
        users = client.get("/users", auth=auth)
        token = csrf_from(users.text)
        assert client.post(
            "/users/200/reset",
            auth=auth,
            data={"csrf": "wrong"},
        ).status_code == 403
        reset = client.post(
            "/users/200/reset",
            auth=auth,
            data={"csrf": token},
        )
        assert reset.status_code == 303

        detail = client.get(f"/requests/{request_id}", auth=auth)
        retry_token = csrf_from(detail.text)
        retry = client.post(
            f"/requests/{request_id}/retry",
            auth=auth,
            data={"csrf": retry_token},
        )
        assert retry.status_code == 303
        assert app.state.repository.admin_request(request_id).status == "retry_requested"


def test_admin_does_not_offer_retry_for_quarantine(tmp_path):
    web_settings = settings(tmp_path)
    request_id = seed_request(web_settings.database_file, safe=False)
    app = create_app(web_settings)
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        detail = client.get(
            f"/requests/{request_id}",
            auth=("admin", "correct-horse"),
        )
        assert detail.status_code == 200
        assert "Повторить обработку" not in detail.text


def test_admin_shows_api_source_without_telegram_retry(tmp_path):
    web_settings = settings(tmp_path)
    repository = Repository(web_settings.database_file)
    request_id = repository.create_api_request(now=1000)
    repository.update(request_id, status="recognized", moderation_safe=1)
    repository.close()
    app = create_app(web_settings)

    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        detail = client.get(
            f"/requests/{request_id}",
            auth=("admin", "correct-horse"),
        )
        requests = client.get("/requests", auth=("admin", "correct-horse"))

    assert detail.status_code == 200
    assert "HTTP API" in detail.text
    assert "Повторить обработку" not in detail.text
    assert "HTTP API" in requests.text
