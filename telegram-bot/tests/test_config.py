from pathlib import Path

import pytest

from chto_za_vino_bot.config import AdminWebSettings, ConfigError, EndpointSettings, Settings

CONFIG_FILE = Path(__file__).parents[1] / "config.yaml"


@pytest.fixture(autouse=True)
def endpoint_environment(monkeypatch) -> None:
    monkeypatch.setenv("BOT_CONFIG", str(CONFIG_FILE))
    monkeypatch.setenv(
        "MODERATION_ENDPOINT",
        "http://127.0.0.1:18081/upstream/shieldgemma-2-4b-it/classify",
    )
    monkeypatch.setenv("SAM3_ENDPOINT", "http://192.168.86.14:18081/upstream/sam3")
    monkeypatch.setenv("MATCHER_ENDPOINT", "http://192.168.86.14:28000/v1/match")


def test_default_rate_limit_is_50(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.delenv("BOT_RATE_LIMIT", raising=False)
    monkeypatch.delenv("BOT_ADMIN_USER_ID", raising=False)
    monkeypatch.delenv("BOT_REJECTION_IMAGE", raising=False)
    monkeypatch.delenv("BOT_HTTP_API_HOST", raising=False)
    monkeypatch.delenv("BOT_HTTP_API_PORT", raising=False)
    monkeypatch.delenv("BOT_HTTP_API_ALLOWED_NETWORKS", raising=False)

    settings = Settings.from_env()

    assert settings.rate_limit == 50
    assert settings.admin_user_id == 207286210
    assert settings.moderation_endpoint == (
        "http://127.0.0.1:18081/upstream/shieldgemma-2-4b-it/classify"
    )
    assert settings.sam3_endpoint == "http://192.168.86.14:18081/upstream/sam3"
    assert settings.matcher_endpoint == "http://192.168.86.14:28000/v1/match"
    assert settings.match_min_score == 0.70
    assert settings.match_min_margin == 0.015
    assert settings.queue_estimate_seconds == 20.0
    assert settings.http_api_host == "127.0.0.1"
    assert settings.http_api_port == 8180
    assert settings.http_api_allowed_networks == (
        "127.0.0.1/32",
        "::1/128",
        "192.168.86.0/24",
    )
    assert settings.rejection_image_file.as_posix() == (
        "/mnt/projects/chto-za-vino-bot/assets/content-rejected-monkey-640x640.png"
    )


def test_admin_web_requires_password(monkeypatch) -> None:
    monkeypatch.delenv("BOT_ADMIN_WEB_PASSWORD", raising=False)

    with pytest.raises(ValueError, match="BOT_ADMIN_WEB_PASSWORD"):
        AdminWebSettings.from_env()


def test_admin_web_defaults(monkeypatch) -> None:
    monkeypatch.setenv("BOT_ADMIN_WEB_PASSWORD", "secret")
    monkeypatch.delenv("BOT_ADMIN_WEB_HOST", raising=False)
    monkeypatch.delenv("BOT_ADMIN_WEB_PORT", raising=False)
    monkeypatch.delenv("BOT_ADMIN_WEB_ALLOWED_NETWORKS", raising=False)

    settings = AdminWebSettings.from_env()

    assert settings.host == "127.0.0.1"
    assert settings.port == 8172
    assert settings.allowed_networks == (
        "127.0.0.1/32",
        "::1/128",
        "192.168.86.0/24",
    )


@pytest.mark.parametrize(
    "value",
    [
        "http://127.0.0.1:28000/v1/match",
        "https://matcher.example/prefix/v1/match",
    ],
)
def test_matcher_endpoint_accepts_the_match_path(monkeypatch, value) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("MATCHER_ENDPOINT", value)

    assert Settings.from_env().matcher_endpoint == value


@pytest.mark.parametrize(
    "value",
    [
        "http://127.0.0.1:8158/v1/eval/predict",
        "http://127.0.0.1:28000/v1/match/",
        "http://127.0.0.1:28000/v1/match?k=4",
        "http://127.0.0.1:28000",
        "ftp://127.0.0.1/v1/match",
        "127.0.0.1:28000/v1/match",
    ],
)
def test_matcher_endpoint_must_name_the_match_path(monkeypatch, value) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("MATCHER_ENDPOINT", value)

    with pytest.raises(ValueError, match="endpoints.matcher"):
        Settings.from_env()


def write_config(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def test_endpoint_config_resolves_exact_environment_references() -> None:
    endpoints = EndpointSettings.from_config(
        CONFIG_FILE,
        environ={
            "MODERATION_ENDPOINT": "https://models.example/moderate",
            "SAM3_ENDPOINT": "https://models.example/sam3/",
            "MATCHER_ENDPOINT": "https://matcher.example/v1/match",
        },
    )

    assert endpoints.moderation == "https://models.example/moderate"
    assert endpoints.sam3 == "https://models.example/sam3"
    assert endpoints.matcher == "https://matcher.example/v1/match"


def test_endpoint_config_accepts_literal_urls(tmp_path) -> None:
    path = write_config(
        tmp_path,
        """endpoints:
  moderation: http://moderation.example/classify
  sam3: http://sam3.example
  matcher: http://matcher.example/v1/match
""",
    )

    endpoints = EndpointSettings.from_config(path, environ={})

    assert endpoints.moderation == "http://moderation.example/classify"
    assert endpoints.sam3 == "http://sam3.example"
    assert endpoints.matcher == "http://matcher.example/v1/match"


def test_endpoint_config_requires_referenced_environment_variable(tmp_path) -> None:
    path = write_config(
        tmp_path,
        """endpoints:
  moderation: "{env:MISSING_ENDPOINT}"
  sam3: http://sam3.example
  matcher: http://matcher.example/v1/match
""",
    )

    with pytest.raises(ConfigError, match="MISSING_ENDPOINT MUST be set"):
        EndpointSettings.from_config(path, environ={})


@pytest.mark.parametrize(
    "value",
    ["{env:}", "{env:9BAD}", "prefix{env:ENDPOINT}", "{env:ENDPOINT}suffix"],
)
def test_endpoint_config_rejects_malformed_environment_reference(tmp_path, value) -> None:
    path = write_config(
        tmp_path,
        f"""endpoints:
  moderation: "{value}"
  sam3: http://sam3.example
  matcher: http://matcher.example/v1/match
""",
    )

    with pytest.raises(ConfigError, match=r"exact \{env:NAME\} reference"):
        EndpointSettings.from_config(path, environ={"ENDPOINT": "http://example.test"})


def test_endpoint_config_requires_all_endpoints(tmp_path) -> None:
    path = write_config(
        tmp_path,
        """endpoints:
  moderation: http://moderation.example/classify
  sam3: http://sam3.example
""",
    )

    with pytest.raises(ConfigError, match="endpoints.matcher"):
        EndpointSettings.from_config(path, environ={})
