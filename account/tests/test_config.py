from __future__ import annotations

import pytest

from chto_za_vino_account.config import Settings


def test_production_requires_smtp(env):
    env["ACCOUNT_ENVIRONMENT"] = "production"
    with pytest.raises(ValueError, match="ACCOUNT_EMAIL_BACKEND=smtp"):
        Settings.from_env(env)
    env.update(
        {
            "ACCOUNT_EMAIL_BACKEND": "smtp",
            "SMTP_HOST": "smtp.example.ru",
            "SMTP_USERNAME": "noreply@chtozavino.ru",
            "SMTP_PASSWORD": "secret",
        }
    )
    assert Settings.from_env(env).production


def test_secrets_must_be_long_and_distinct(env):
    short = dict(env, ACCOUNT_WEB_TOKEN="short")
    with pytest.raises(ValueError, match="at least 32"):
        Settings.from_env(short)
    same = dict(env, ACCOUNT_TELEGRAM_TOKEN=env["ACCOUNT_WEB_TOKEN"])
    with pytest.raises(ValueError, match="distinct"):
        Settings.from_env(same)
    missing = dict(env, ACCOUNT_CODE_KEY="")
    with pytest.raises(ValueError, match="ACCOUNT_CODE_KEY is required"):
        Settings.from_env(missing)


def test_old_bot_token_names_stop_the_start(env):
    old = dict(env, ACCOUNT_TELEGRAM_BOT_TOKEN="t" * 40)
    with pytest.raises(ValueError, match="renamed to ACCOUNT_TELEGRAM_TOKEN"):
        Settings.from_env(old)
    assert Settings.from_env(dict(env, ACCOUNT_MAX_BOT_TOKEN="")).consumers


def test_provider_settings_are_checked(env):
    with pytest.raises(ValueError, match="MAX_WEBAPP_KEY"):
        Settings.from_env(dict(env, MAX_WEBAPP_KEY="not-hex"))
    with pytest.raises(ValueError, match="YANDEX_REDIRECT_URIS"):
        Settings.from_env(dict(env, YANDEX_REDIRECT_URIS=""))
    with pytest.raises(ValueError, match="TELEGRAM_BOT_USERNAME"):
        Settings.from_env(dict(env, TELEGRAM_BOT_USERNAME="bad name"))
    production = dict(
        env,
        ACCOUNT_ENVIRONMENT="production",
        ACCOUNT_EMAIL_BACKEND="smtp",
        SMTP_HOST="smtp.example.ru",
        YANDEX_REDIRECT_URIS="http://chtozavino.ru/cb",
    )
    with pytest.raises(ValueError, match="https"):
        Settings.from_env(production)


def test_consumers_and_secret_free_repr(env):
    env.update(
        {
            "ACCOUNT_EMAIL_BACKEND": "smtp",
            "SMTP_HOST": "smtp.example.ru",
            "SMTP_PASSWORD": "smtp-password-value",
        }
    )
    settings = Settings.from_env(env)
    assert set(settings.consumers) == {"web", "max-bot", "telegram-bot"}
    text = repr(settings)
    for name in (
        "ACCOUNT_WEB_TOKEN",
        "ACCOUNT_TELEGRAM_TOKEN",
        "ACCOUNT_MAX_TOKEN",
        "ACCOUNT_CODE_KEY",
        "YANDEX_CLIENT_SECRET",
        "SMTP_PASSWORD",
        "MAX_WEBAPP_KEY",
    ):
        assert env[name] not in text, name
    assert "consumers=" not in text
