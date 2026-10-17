import os
from pathlib import Path

import pytest

from chto_za_vino_max_bot.config import (
    AdminWebSettings,
    ConfigError,
    EndpointSettings,
    Settings,
    WebhookSettings,
)
from chto_za_vino_max_bot.max_api import DEFAULT_CA_FILE

CONFIG_FILE = Path(__file__).parents[1] / "config.yaml"
ADMIN_PASSWORD = "b" * 32
MAX_TOKEN = "max-test-token"
HTTP_API_TOKEN = "a" * 32
WEBHOOK_URL = "https://bot.example/max/webhook"
WEBHOOK_SECRET = "Webhook_secret-0123456789abcdefXYZ"


@pytest.fixture(autouse=True)
def endpoint_environment(monkeypatch) -> None:
    # A bot variable of the developer shell must not change a result.
    for name in tuple(os.environ):
        if name.startswith(("BOT_", "MAX_")):
            monkeypatch.delenv(name)
    monkeypatch.setenv("BOT_CONFIG", str(CONFIG_FILE))
    monkeypatch.setenv(
        "MODERATION_ENDPOINT",
        "http://127.0.0.1:18081/upstream/shieldgemma-2-4b-it/classify",
    )
    monkeypatch.setenv("SAM3_ENDPOINT", "http://192.168.86.14:18081/upstream/sam3")
    monkeypatch.setenv("MATCHER_ENDPOINT", "http://192.168.86.14:28000/v1/match")
    monkeypatch.setenv("BOT_ADMIN_USER_ID", "123456789")
    monkeypatch.setenv("BOT_HTTP_API_TOKEN", HTTP_API_TOKEN)
    monkeypatch.setenv("MAX_BOT_TOKEN", MAX_TOKEN)
    # The webhook variables are set, but only updates.mode: webhook reads them.
    monkeypatch.setenv("MAX_WEBHOOK_URL", WEBHOOK_URL)
    monkeypatch.setenv("MAX_WEBHOOK_SECRET", WEBHOOK_SECRET)


def write_update_mode(tmp_path, monkeypatch, update_mode: object | None) -> Path:
    """Write config.yaml with another updates.mode. None removes the updates section."""
    text = CONFIG_FILE.read_text(encoding="utf-8")
    assert "updates:\n  mode: polling\n" in text
    section = "" if update_mode is None else f"updates:\n  mode: {update_mode}\n"
    path = tmp_path / "config.yaml"
    path.write_text(text.replace("updates:\n  mode: polling\n", section), encoding="utf-8")
    monkeypatch.setenv("BOT_CONFIG", str(path))
    return path


@pytest.fixture
def webhook_mode(tmp_path, monkeypatch) -> None:
    write_update_mode(tmp_path, monkeypatch, "webhook")


def test_default_rate_limit_is_50() -> None:
    settings = Settings.from_env()

    assert settings.max_token == MAX_TOKEN
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
    assert settings.http_api_port == 28004
    assert settings.http_api_allowed_networks == (
        "127.0.0.1/32",
        "::1/128",
        "192.168.86.0/24",
    )
    assert settings.http_api_token == HTTP_API_TOKEN
    assert settings.http_api_rate_limit == 10
    assert settings.http_api_rate_window_seconds == 3600
    assert settings.http_api_max_in_flight == 2
    assert settings.data_retention_days == 30
    assert settings.rejection_image_file.as_posix() == (
        "assets/content-rejected-monkey-640x640.png"
    )
    assert settings.max_api_base_url == "https://platform-api2.max.ru"
    assert settings.max_api_ca_file == DEFAULT_CA_FILE
    assert settings.update_mode == "polling"
    assert settings.webhook is None
    assert settings.poll_timeout_seconds == 30
    assert settings.media_allowed_hosts == ()


def test_bot_reads_the_max_token_not_the_telegram_token(monkeypatch) -> None:
    monkeypatch.delenv("MAX_BOT_TOKEN")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "telegram-token")

    with pytest.raises(ValueError, match="MAX_BOT_TOKEN is required"):
        Settings.from_env()


def test_admin_web_requires_password(monkeypatch) -> None:
    monkeypatch.delenv("BOT_ADMIN_WEB_PASSWORD", raising=False)

    with pytest.raises(ValueError, match="BOT_ADMIN_WEB_PASSWORD"):
        AdminWebSettings.from_env()


def test_admin_web_defaults(monkeypatch) -> None:
    monkeypatch.setenv("BOT_ADMIN_WEB_PASSWORD", ADMIN_PASSWORD)

    settings = AdminWebSettings.from_env()

    assert settings.data_root == Path("data")
    assert settings.database_file == Path("data/bot.sqlite3")
    assert settings.host == "127.0.0.1"
    assert settings.port == 28005
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


@pytest.mark.parametrize("name", ["MAX_BOT_TOKEN", "BOT_ADMIN_USER_ID", "BOT_HTTP_API_TOKEN"])
def test_bot_requires_explicit_privileged_credentials(monkeypatch, name) -> None:
    monkeypatch.delenv(name, raising=False)

    with pytest.raises(ValueError, match=name):
        Settings.from_env()


def test_bot_rejects_a_short_http_api_token(monkeypatch) -> None:
    monkeypatch.setenv("BOT_HTTP_API_TOKEN", "short")

    with pytest.raises(ValueError, match="32 characters"):
        Settings.from_env()


def test_production_requires_the_documented_retention_period(monkeypatch) -> None:
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


def test_max_api_base_url_accepts_an_https_url(monkeypatch) -> None:
    monkeypatch.setenv("MAX_API_BASE_URL", " https://max-proxy.example/api/ ")

    assert Settings.from_env().max_api_base_url == "https://max-proxy.example/api"


@pytest.mark.parametrize(
    "value",
    [
        "http://platform-api2.max.ru",
        "platform-api2.max.ru",
        "https://",
        "https://platform-api2.max.ru?access_token=secret",
        "https://platform-api2.max.ru#fragment",
        "https://user:password@platform-api2.max.ru",
    ],
)
def test_max_api_base_url_must_be_an_https_url(monkeypatch, value) -> None:
    monkeypatch.setenv("MAX_API_BASE_URL", value)

    with pytest.raises(ValueError, match="MAX_API_BASE_URL must"):
        Settings.from_env()


@pytest.mark.parametrize("value", ["", "   "])
def test_blank_max_api_ca_file_selects_the_bundled_root(monkeypatch, value) -> None:
    monkeypatch.setenv("MAX_API_CA_FILE", value)

    settings = Settings.from_env()

    assert settings.max_api_ca_file == DEFAULT_CA_FILE
    assert DEFAULT_CA_FILE.is_file()


@pytest.mark.parametrize("value", ["none", "None", " NONE "])
def test_max_api_ca_file_none_selects_only_the_public_trust_store(monkeypatch, value) -> None:
    monkeypatch.setenv("MAX_API_CA_FILE", value)

    assert Settings.from_env().max_api_ca_file is None


def test_max_api_ca_file_accepts_an_existing_file(tmp_path, monkeypatch) -> None:
    ca_file = tmp_path / "extra-root.pem"
    ca_file.write_text("-----BEGIN CERTIFICATE-----\n", encoding="ascii")
    monkeypatch.setenv("MAX_API_CA_FILE", str(ca_file))

    assert Settings.from_env().max_api_ca_file == ca_file


@pytest.mark.parametrize("name", ["missing.pem", "."])
def test_max_api_ca_file_must_name_an_existing_file(tmp_path, monkeypatch, name) -> None:
    monkeypatch.setenv("MAX_API_CA_FILE", str(tmp_path / name))

    with pytest.raises(ValueError, match="MAX_API_CA_FILE must name a readable PEM file"):
        Settings.from_env()


def test_production_uses_long_polling_from_config_yaml() -> None:
    # Owner decision for the hackathon (issue #10). A webhook is issue #23.
    settings = Settings.from_env()

    assert settings.environment == "production"
    assert settings.update_mode == "polling"
    assert settings.webhook is None


@pytest.mark.usefixtures("webhook_mode")
def test_config_yaml_selects_a_webhook() -> None:
    settings = Settings.from_env()

    assert settings.update_mode == "webhook"
    assert settings.webhook == WebhookSettings(
        url=WEBHOOK_URL,
        secret=WEBHOOK_SECRET,
        host="127.0.0.1",
        port=28006,
        path="/max/webhook",
        subscribe=True,
    )


@pytest.mark.parametrize("environment", ["development", "test"])
def test_polling_does_not_read_the_webhook_settings(monkeypatch, environment) -> None:
    monkeypatch.setenv("BOT_ENVIRONMENT", environment)
    monkeypatch.setenv("MAX_WEBHOOK_URL", "http://bot.example:8080/hook")
    monkeypatch.setenv("MAX_WEBHOOK_SECRET", "short")

    settings = Settings.from_env()

    assert settings.update_mode == "polling"
    assert settings.webhook is None


@pytest.mark.usefixtures("webhook_mode")
def test_development_can_use_a_webhook(monkeypatch) -> None:
    monkeypatch.setenv("BOT_ENVIRONMENT", "development")

    settings = Settings.from_env()

    assert settings.update_mode == "webhook"
    assert settings.webhook is not None
    assert settings.webhook.url == WEBHOOK_URL


def test_config_yaml_without_updates_selects_polling(tmp_path, monkeypatch) -> None:
    write_update_mode(tmp_path, monkeypatch, None)

    assert Settings.from_env().update_mode == "polling"


@pytest.mark.parametrize("value", ["long-polling", "websocket", "Webhook", "true", "[polling]"])
def test_update_mode_must_be_polling_or_webhook(tmp_path, monkeypatch, value) -> None:
    write_update_mode(tmp_path, monkeypatch, value)

    with pytest.raises(ConfigError, match="updates.mode MUST be polling or webhook"):
        Settings.from_env()


@pytest.mark.parametrize("name", ["MAX_UPDATE_MODE", "MAX_ALLOW_PRODUCTION_POLLING"])
def test_removed_update_variables_stop_the_start(monkeypatch, name) -> None:
    # A stale variable from an old environment file must not be ignored silently.
    monkeypatch.setenv(name, "webhook")

    with pytest.raises(ValueError, match=f"{name} is removed; set updates.mode in config.yaml"):
        Settings.from_env()


@pytest.mark.parametrize("value", ["0", "90"])
def test_poll_timeout_accepts_the_documented_range(monkeypatch, value) -> None:
    monkeypatch.setenv("BOT_ENVIRONMENT", "development")
    monkeypatch.setenv("MAX_POLL_TIMEOUT_SECONDS", value)

    assert Settings.from_env().poll_timeout_seconds == int(value)


@pytest.mark.parametrize("value", ["-1", "91"])
def test_poll_timeout_rejects_a_value_outside_the_range(monkeypatch, value) -> None:
    monkeypatch.setenv("BOT_ENVIRONMENT", "development")
    monkeypatch.setenv("MAX_POLL_TIMEOUT_SECONDS", value)

    with pytest.raises(ValueError, match="MAX_POLL_TIMEOUT_SECONDS must be from 0 to 90"):
        Settings.from_env()


def test_poll_timeout_must_be_an_integer(monkeypatch) -> None:
    monkeypatch.setenv("BOT_ENVIRONMENT", "development")
    monkeypatch.setenv("MAX_POLL_TIMEOUT_SECONDS", "30s")

    with pytest.raises(ValueError, match="MAX_POLL_TIMEOUT_SECONDS must be an integer"):
        Settings.from_env()


@pytest.mark.usefixtures("webhook_mode")
def test_webhook_listener_settings_are_configurable(monkeypatch) -> None:
    monkeypatch.setenv("MAX_WEBHOOK_HOST", "0.0.0.0")
    monkeypatch.setenv("MAX_WEBHOOK_PORT", "8443")
    monkeypatch.setenv("MAX_WEBHOOK_PATH", "/internal/max")
    monkeypatch.setenv("MAX_WEBHOOK_SUBSCRIBE", "false")

    assert Settings.from_env().webhook == WebhookSettings(
        url=WEBHOOK_URL,
        secret=WEBHOOK_SECRET,
        host="0.0.0.0",
        port=8443,
        path="/internal/max",
        subscribe=False,
    )


@pytest.mark.usefixtures("webhook_mode")
def test_webhook_path_of_a_url_without_a_path_is_the_root(monkeypatch) -> None:
    monkeypatch.setenv("MAX_WEBHOOK_URL", "https://bot.example")

    webhook = Settings.from_env().webhook

    assert webhook is not None
    assert webhook.path == "/"


@pytest.mark.usefixtures("webhook_mode")
@pytest.mark.parametrize(
    "value",
    [
        "",
        "http://bot.example/max/webhook",
        "bot.example/max/webhook",
        "https://bot.example/max/webhook?key=value",
        "https://bot.example/max/webhook#fragment",
        "https://user:password@bot.example/max/webhook",
        "https://bot.example:99999/max/webhook",
    ],
)
def test_webhook_url_must_be_an_https_url(monkeypatch, value) -> None:
    monkeypatch.setenv("MAX_WEBHOOK_URL", value)

    with pytest.raises(ValueError, match="MAX_WEBHOOK_URL must"):
        Settings.from_env()


@pytest.mark.usefixtures("webhook_mode")
@pytest.mark.parametrize(
    "value",
    ["https://bot.example:443/max/webhook", "https://bot.example:8443/max/webhook"],
)
def test_webhook_url_must_not_name_a_port(monkeypatch, value) -> None:
    monkeypatch.setenv("MAX_WEBHOOK_URL", value)

    with pytest.raises(ValueError, match="MAX_WEBHOOK_URL must not contain a port"):
        Settings.from_env()


@pytest.mark.usefixtures("webhook_mode")
@pytest.mark.parametrize(
    "value",
    [
        "",
        "a" * 31,
        "a" * 257,
        "a" * 31 + "!",
        "a" * 16 + " " + "a" * 16,
        "секрет" * 6,
    ],
)
def test_webhook_secret_must_have_32_to_256_allowed_characters(monkeypatch, value) -> None:
    monkeypatch.setenv("MAX_WEBHOOK_SECRET", value)

    with pytest.raises(ValueError, match="MAX_WEBHOOK_SECRET must contain 32 to 256"):
        Settings.from_env()


@pytest.mark.usefixtures("webhook_mode")
@pytest.mark.parametrize("value", ["A" * 32, "Az09_-" * 42 + "abcd"])
def test_webhook_secret_accepts_the_boundary_lengths(monkeypatch, value) -> None:
    monkeypatch.setenv("MAX_WEBHOOK_SECRET", value)

    webhook = Settings.from_env().webhook

    assert webhook is not None
    assert webhook.secret == value


@pytest.mark.usefixtures("webhook_mode")
def test_webhook_path_must_start_with_a_slash(monkeypatch) -> None:
    monkeypatch.setenv("MAX_WEBHOOK_PATH", "max/webhook")

    with pytest.raises(ValueError, match="MAX_WEBHOOK_PATH must start with /"):
        Settings.from_env()


@pytest.mark.usefixtures("webhook_mode")
def test_webhook_host_must_not_be_blank(monkeypatch) -> None:
    monkeypatch.setenv("MAX_WEBHOOK_HOST", "   ")

    with pytest.raises(ValueError, match="MAX_WEBHOOK_HOST is required"):
        Settings.from_env()


@pytest.mark.usefixtures("webhook_mode")
@pytest.mark.parametrize("value", ["0", "65536", "port"])
def test_webhook_port_must_be_a_tcp_port(monkeypatch, value) -> None:
    monkeypatch.setenv("MAX_WEBHOOK_PORT", value)

    with pytest.raises(ValueError, match="MAX_WEBHOOK_PORT"):
        Settings.from_env()


@pytest.mark.usefixtures("webhook_mode")
@pytest.mark.parametrize(
    ("max_token", "http_api_token", "webhook_secret"),
    [
        ("s" * 32, "s" * 32, WEBHOOK_SECRET),
        (MAX_TOKEN, "s" * 32, "s" * 32),
        ("s" * 32, HTTP_API_TOKEN, "s" * 32),
    ],
)
def test_bot_token_http_api_token_and_webhook_secret_must_differ(
    monkeypatch, max_token, http_api_token, webhook_secret
) -> None:
    monkeypatch.setenv("MAX_BOT_TOKEN", max_token)
    monkeypatch.setenv("BOT_HTTP_API_TOKEN", http_api_token)
    monkeypatch.setenv("MAX_WEBHOOK_SECRET", webhook_secret)

    with pytest.raises(ValueError, match="must differ"):
        Settings.from_env()


def test_polling_mode_does_not_compare_an_unused_webhook_secret(monkeypatch) -> None:
    monkeypatch.setenv("BOT_ENVIRONMENT", "development")
    monkeypatch.setenv("MAX_WEBHOOK_SECRET", HTTP_API_TOKEN)

    settings = Settings.from_env()

    assert settings.update_mode == "polling"
    assert settings.webhook is None


def test_media_allowed_hosts_are_normalized_host_suffixes(monkeypatch) -> None:
    monkeypatch.setenv("MAX_MEDIA_ALLOWED_HOSTS", " .OneMe.RU, ,cdn.Example.com ,")

    assert Settings.from_env().media_allowed_hosts == ("oneme.ru", "cdn.example.com")
