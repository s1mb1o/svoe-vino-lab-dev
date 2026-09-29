from pathlib import Path

import pytest

from chto_za_vino_bot.config import AdminWebSettings, ConfigError, EndpointSettings, Settings

CONFIG_FILE = Path(__file__).parents[1] / "config.yaml"
ADMIN_PASSWORD = "b" * 32


@pytest.fixture(autouse=True)
def endpoint_environment(monkeypatch) -> None:
    monkeypatch.setenv("BOT_CONFIG", str(CONFIG_FILE))
    monkeypatch.setenv(
        "MODERATION_ENDPOINT",
        "http://127.0.0.1:18081/upstream/shieldgemma-2-4b-it/classify",
    )
    monkeypatch.setenv("SAM3_ENDPOINT", "http://192.168.86.14:18081/upstream/sam3")
    monkeypatch.setenv("MATCHER_ENDPOINT", "http://192.168.86.14:28000/v1/match")
    monkeypatch.setenv("BOT_ADMIN_USER_ID", "123456789")
    monkeypatch.setenv("BOT_HTTP_API_TOKEN", "a" * 32)


def test_default_rate_limit_is_50(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.delenv("BOT_RATE_LIMIT", raising=False)
    monkeypatch.delenv("BOT_DATA_ROOT", raising=False)
    monkeypatch.delenv("BOT_DATABASE", raising=False)
    monkeypatch.delenv("BOT_REJECTION_IMAGE", raising=False)
    monkeypatch.delenv("BOT_HTTP_API_HOST", raising=False)
    monkeypatch.delenv("BOT_HTTP_API_PORT", raising=False)
    monkeypatch.delenv("BOT_HTTP_API_ALLOWED_NETWORKS", raising=False)

    settings = Settings.from_env()

    assert settings.rate_limit == 50
    assert settings.admin_user_id == 123456789
    assert settings.environment == "production"
    assert settings.data_root == Path("data")
    assert settings.database_file == Path("data/bot.sqlite3")
    assert settings.moderation_enabled is True
    assert settings.moderation_endpoint == (
        "http://127.0.0.1:18081/upstream/shieldgemma-2-4b-it/classify"
    )
    assert settings.sam3_endpoint == "http://192.168.86.14:18081/upstream/sam3"
    assert settings.matcher_endpoint == "http://192.168.86.14:28000/v1/match"
    assert settings.match_min_score == 0.70
    assert settings.match_min_margin == 0.015
    assert settings.queue_estimate_seconds == 20.0
    assert settings.http_api_host == "127.0.0.1"
    assert settings.http_api_port == 28002
    assert settings.http_api_allowed_networks == (
        "127.0.0.1/32",
        "::1/128",
        "192.168.86.0/24",
    )
    assert settings.http_api_token == "a" * 32
    assert settings.http_api_rate_limit == 10
    assert settings.http_api_rate_window_seconds == 3600
    assert settings.http_api_max_in_flight == 2
    assert settings.data_retention_days == 30
    assert settings.rejection_image_file.as_posix() == (
        "assets/content-rejected-monkey-640x640.png"
    )


def test_admin_web_requires_password(monkeypatch) -> None:
    monkeypatch.delenv("BOT_ADMIN_WEB_PASSWORD", raising=False)

    with pytest.raises(ValueError, match="BOT_ADMIN_WEB_PASSWORD"):
        AdminWebSettings.from_env()


def test_admin_web_defaults(monkeypatch) -> None:
    monkeypatch.setenv("BOT_ADMIN_WEB_PASSWORD", ADMIN_PASSWORD)
    monkeypatch.delenv("BOT_DATA_ROOT", raising=False)
    monkeypatch.delenv("BOT_DATABASE", raising=False)
    monkeypatch.delenv("BOT_ADMIN_WEB_HOST", raising=False)
    monkeypatch.delenv("BOT_ADMIN_WEB_PORT", raising=False)
    monkeypatch.delenv("BOT_ADMIN_WEB_ALLOWED_NETWORKS", raising=False)
    monkeypatch.delenv("BOT_ADMIN_WEB_BEHIND_TLS_PROXY", raising=False)
    monkeypatch.delenv("BOT_ADMIN_WEB_AUTH_RATE_LIMIT", raising=False)
    monkeypatch.delenv("BOT_ADMIN_WEB_AUTH_RATE_WINDOW_SECONDS", raising=False)

    settings = AdminWebSettings.from_env()

    assert settings.data_root == Path("data")
    assert settings.database_file == Path("data/bot.sqlite3")
    assert settings.host == "127.0.0.1"
    assert settings.port == 28003
    assert settings.allowed_networks == (
        "127.0.0.1/32",
        "::1/128",
    )
    assert settings.behind_tls_proxy is False
    assert settings.auth_rate_limit == 10
    assert settings.auth_rate_window_seconds == 300


def test_admin_web_rejects_a_short_password(monkeypatch) -> None:
    monkeypatch.setenv("BOT_ADMIN_WEB_PASSWORD", "short")

    with pytest.raises(ValueError, match="32 characters"):
        AdminWebSettings.from_env()


def test_admin_web_requires_a_tls_proxy_for_a_non_loopback_listener(monkeypatch) -> None:
    monkeypatch.setenv("BOT_ADMIN_WEB_PASSWORD", ADMIN_PASSWORD)
    monkeypatch.setenv("BOT_ADMIN_WEB_HOST", "0.0.0.0")
    monkeypatch.delenv("BOT_ADMIN_WEB_BEHIND_TLS_PROXY", raising=False)

    with pytest.raises(ValueError, match="BEHIND_TLS_PROXY"):
        AdminWebSettings.from_env()

    monkeypatch.setenv("BOT_ADMIN_WEB_BEHIND_TLS_PROXY", "true")
    assert AdminWebSettings.from_env().behind_tls_proxy is True


@pytest.mark.parametrize("name", ["BOT_ADMIN_USER_ID", "BOT_HTTP_API_TOKEN"])
def test_bot_requires_explicit_privileged_credentials(monkeypatch, name) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.delenv(name, raising=False)

    with pytest.raises(ValueError, match=name):
        Settings.from_env()


def test_bot_rejects_a_short_http_api_token(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("BOT_HTTP_API_TOKEN", "short")

    with pytest.raises(ValueError, match="32 characters"):
        Settings.from_env()


def test_production_requires_the_documented_retention_period(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("BOT_DATA_RETENTION_DAYS", "31")

    with pytest.raises(ValueError, match="BOT_DATA_RETENTION_DAYS=30"):
        Settings.from_env()


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
        "http://127.0.0.1:28000/v1/not-match",
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
    assert endpoints.moderation_enabled is True
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


def test_disabled_moderation_does_not_require_an_endpoint_variable(tmp_path) -> None:
    path = write_config(
        tmp_path,
        """moderation:
  enabled: false
endpoints:
  moderation: "{env:MODERATION_ENDPOINT}"
  sam3: http://sam3.example
  matcher: http://matcher.example/v1/match
""",
    )

    endpoints = EndpointSettings.from_config(path, environ={})

    assert endpoints.moderation_enabled is False
    assert endpoints.moderation is None


def test_disabled_moderation_allows_an_absent_endpoint(tmp_path) -> None:
    path = write_config(
        tmp_path,
        """moderation:
  enabled: false
endpoints:
  sam3: http://sam3.example
  matcher: http://matcher.example/v1/match
""",
    )

    endpoints = EndpointSettings.from_config(path, environ={})

    assert endpoints.moderation_enabled is False
    assert endpoints.moderation is None


def test_settings_allow_disabled_moderation_without_endpoint_variable(
    tmp_path, monkeypatch
) -> None:
    path = write_config(
        tmp_path,
        """moderation:
  enabled: false
endpoints:
  moderation: "{env:MODERATION_ENDPOINT}"
  sam3: "{env:SAM3_ENDPOINT}"
  matcher: "{env:MATCHER_ENDPOINT}"
""",
    )
    monkeypatch.setenv("BOT_CONFIG", str(path))
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("BOT_ENVIRONMENT", "development")
    monkeypatch.delenv("MODERATION_ENDPOINT", raising=False)

    settings = Settings.from_env()

    assert settings.moderation_enabled is False
    assert settings.moderation_endpoint is None


def test_production_rejects_disabled_moderation(tmp_path, monkeypatch) -> None:
    path = write_config(
        tmp_path,
        """moderation:
  enabled: false
endpoints:
  sam3: http://sam3.example
  matcher: http://matcher.example/v1/match
""",
    )
    monkeypatch.setenv("BOT_CONFIG", str(path))
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("BOT_ENVIRONMENT", "production")

    with pytest.raises(ValueError, match="production requires moderation.enabled=true"):
        Settings.from_env()


@pytest.mark.parametrize("rendered", ['"false"', "0", "null"])
def test_moderation_enabled_requires_a_boolean(tmp_path, rendered) -> None:
    path = write_config(
        tmp_path,
        f"""moderation:
  enabled: {rendered}
endpoints:
  sam3: http://sam3.example
  matcher: http://matcher.example/v1/match
""",
    )

    with pytest.raises(ConfigError, match="moderation.enabled MUST be true or false"):
        EndpointSettings.from_config(path, environ={})
