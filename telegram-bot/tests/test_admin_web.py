import re
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from chto_za_vino_bot.admin_web import create_app
from chto_za_vino_bot.config import AdminWebSettings
from chto_za_vino_bot.storage import ArtifactStore, ArtifactWrite, Repository

ADMIN_PASSWORD = "correct-horse-battery-staple-1234"


def settings(tmp_path):
    return AdminWebSettings(
        data_root=tmp_path / "data",
        database_file=tmp_path / "bot.sqlite3",
        username="admin",
        password=ADMIN_PASSWORD,
        host="127.0.0.1",
        port=28003,
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
        assert client.get("/", auth=("admin", ADMIN_PASSWORD)).status_code == 200
        assert client.get("/readyz").status_code == 200

    blocked_app = create_app(settings(tmp_path / "blocked"))
    with TestClient(blocked_app, client=("10.0.0.10", 50000)) as client:
        assert client.get("/healthz").status_code == 403


def test_admin_rejects_a_short_password_before_opening_the_database(tmp_path):
    web_settings = replace(settings(tmp_path), password="short")

    with pytest.raises(ValueError, match="32 characters"):
        create_app(web_settings)

    assert not web_settings.database_file.exists()


def test_admin_throttles_failed_authentication_per_client(tmp_path):
    web_settings = replace(
        settings(tmp_path),
        auth_rate_limit=2,
        auth_rate_window_seconds=60,
    )
    app = create_app(web_settings)
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        assert client.get("/").status_code == 401
        assert client.get("/", auth=("admin", "wrong-1")).status_code == 401
        assert client.get("/", auth=("admin", ADMIN_PASSWORD)).status_code == 200

        assert client.get("/", auth=("admin", "wrong-1")).status_code == 401
        assert client.get("/", auth=("admin", "wrong-2")).status_code == 401

        blocked = client.get("/", auth=("admin", "wrong-3"))
        assert blocked.status_code == 429
        assert 1 <= int(blocked.headers["retry-after"]) <= 60

        correct_during_cooldown = client.get("/", auth=("admin", ADMIN_PASSWORD))
        assert correct_during_cooldown.status_code == 429


@pytest.mark.parametrize("path", ["/users", "/requests", "/appeals"])
def test_admin_list_pages_reject_an_excessive_page_number(tmp_path, path):
    app = create_app(settings(tmp_path))
    auth = ("admin", ADMIN_PASSWORD)
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        response = client.get(
            path,
            params={"page": "999999999999999999"},
            auth=auth,
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "Page number is too large"}


@pytest.mark.parametrize("page", ["0", "-1"])
def test_admin_request_page_clamps_non_positive_page_numbers(tmp_path, page):
    app = create_app(settings(tmp_path))
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        response = client.get(
            "/requests",
            params={"page": page},
            auth=("admin", ADMIN_PASSWORD),
        )

    assert response.status_code == 200
    assert "Страница 1 из 1" in response.text


def test_admin_request_page_rejects_a_non_numeric_page_number(tmp_path):
    app = create_app(settings(tmp_path))
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        response = client.get(
            "/requests",
            params={"page": "invalid"},
            auth=("admin", ADMIN_PASSWORD),
        )

    assert response.status_code == 422


def test_admin_pages_do_not_disclose_source_image_paths(tmp_path):
    web_settings = settings(tmp_path)
    request_id = seed_request(web_settings.database_file)
    app = create_app(web_settings)
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        response = client.get(f"/requests/{request_id}", auth=("admin", ADMIN_PASSWORD))
        assert response.status_code == 200
        assert "Test wine" in response.text
        assert 'class="detail-grid"' in response.text
        assert "minmax(min(100%,480px),1fr)" in response.text
        assert "overflow-wrap:anywhere" in response.text
        assert "Визуальные этапы" in response.text
        assert "Артефакты не сохранены" in response.text
        assert "accepted/private.jpg" not in response.text
        assert "quarantine/private.jpg" not in response.text


@pytest.mark.parametrize(
    ("artifact_key", "mime_type"),
    [("sam3_overlay", "image/png"), ("matcher_input", "image/webp")],
)
def test_admin_serves_only_indexed_artifacts_for_safe_requests(
    tmp_path,
    artifact_key,
    mime_type,
):
    web_settings = settings(tmp_path)
    request_id = seed_request(web_settings.database_file)
    body = b"safe-artifact"
    relative_path = ArtifactStore(web_settings.data_root).save(
        request_id,
        1000,
        artifact_key,
        mime_type,
        body,
    )
    repository = Repository(web_settings.database_file)
    repository.replace_artifacts(
        request_id,
        [
            ArtifactWrite(
                artifact_key=artifact_key,
                step="quality",
                title="Artifact preview",
                description="Masks and boxes.",
                mime_type=mime_type,
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
    auth = ("admin", ADMIN_PASSWORD)
    url = f"/requests/{request_id}/artifacts/{artifact_key}"
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        assert client.get(url).status_code == 401
        detail = client.get(f"/requests/{request_id}", auth=auth)
        assert "Artifact preview" in detail.text
        assert "img-src 'self'" in detail.headers["content-security-policy"]
        response = client.get(url, auth=auth)
        assert response.status_code == 200
        assert response.headers["content-type"] == mime_type
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
    auth = ("admin", ADMIN_PASSWORD)
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
    auth = ("admin", ADMIN_PASSWORD)
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
            auth=("admin", ADMIN_PASSWORD),
        )
        assert detail.status_code == 200
        assert "Повторить обработку" not in detail.text


def test_admin_shows_bypassed_moderation_as_not_checked(tmp_path):
    web_settings = settings(tmp_path)
    request_id = seed_request(web_settings.database_file)
    repository = Repository(web_settings.database_file)
    repository.update(
        request_id,
        moderation_safe=None,
        moderation_category="disabled",
        moderation_confidence=0.0,
        moderation_reason="moderation_disabled",
    )
    repository.close()
    app = create_app(web_settings)

    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        detail = client.get(
            f"/requests/{request_id}",
            auth=("admin", ADMIN_PASSWORD),
        )

    assert detail.status_code == 200
    assert "Проверка выполнена</dt><dd>нет" in detail.text
    assert "Проверка пропущена</dt><dd>да" in detail.text
    assert "Безопасно</dt><dd>не проверено" in detail.text
    assert "Повторить обработку" in detail.text


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
            auth=("admin", ADMIN_PASSWORD),
        )
        requests = client.get("/requests", auth=("admin", ADMIN_PASSWORD))

    assert detail.status_code == 200
    assert "HTTP API" in detail.text
    assert "Повторить обработку" not in detail.text
    assert "HTTP API" in requests.text
