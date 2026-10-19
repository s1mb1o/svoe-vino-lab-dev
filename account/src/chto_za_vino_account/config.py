"""Settings from environment variables.

Production refuses an unsafe configuration: a missing or short secret, two equal secrets,
or an email backend that does not send real mail.
"""

from __future__ import annotations

import ipaddress
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field

MIN_SECRET_LENGTH = 32
EMAIL_BACKENDS = ("smtp", "console", "memory")
SMTP_SECURITY = ("ssl", "starttls")
# Old names of the bot consumer tokens. A value under an old name stops the start, so that a
# configuration made from old instructions does not turn a bot off without a message.
RENAMED = {
    "ACCOUNT_MAX_BOT_TOKEN": "ACCOUNT_MAX_TOKEN",
    "ACCOUNT_TELEGRAM_BOT_TOKEN": "ACCOUNT_TELEGRAM_TOKEN",
}


@dataclass(frozen=True)
class SmtpSettings:
    host: str
    port: int
    security: str
    username: str
    password: str = field(repr=False)


@dataclass(frozen=True)
class YandexSettings:
    client_id: str
    client_secret: str = field(repr=False)
    redirect_uris: tuple[str, ...]


@dataclass(frozen=True)
class MaxSettings:
    webapp_key: bytes = field(repr=False)
    login_enabled: bool
    require_ip_match: bool
    max_age_seconds: int


@dataclass(frozen=True)
class Settings:
    environment: str
    database: str
    host: str
    port: int
    allowed_networks: tuple[str, ...]
    web_token: str = field(repr=False)
    max_bot_token: str = field(repr=False)
    telegram_bot_token: str = field(repr=False)
    code_key: bytes = field(repr=False)
    consent_version: str
    terms_version: str
    email_backend: str
    email_from: str
    site_name: str
    smtp: SmtpSettings | None
    yandex: YandexSettings | None
    max: MaxSettings | None
    telegram_bot_username: str
    consumers: dict[str, str] = field(default_factory=dict, repr=False)

    @property
    def production(self) -> bool:
        return self.environment == "production"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        source = os.environ if env is None else env

        def get(name: str, default: str = "") -> str:
            return source.get(name, default).strip()

        for old, new in RENAMED.items():
            if get(old):
                raise ValueError(f"{old} was renamed to {new}")

        environment = get("ACCOUNT_ENVIRONMENT", "development")
        if environment not in ("development", "production"):
            raise ValueError("ACCOUNT_ENVIRONMENT must be development or production")

        networks = tuple(
            item.strip()
            for item in get("ACCOUNT_ALLOWED_NETWORKS", "127.0.0.1/32,::1/128").split(",")
            if item.strip()
        )
        for item in networks:
            ipaddress.ip_network(item, strict=False)

        email_backend = get("ACCOUNT_EMAIL_BACKEND", "console")
        if email_backend not in EMAIL_BACKENDS:
            raise ValueError(f"ACCOUNT_EMAIL_BACKEND must be one of {', '.join(EMAIL_BACKENDS)}")
        smtp = None
        if email_backend == "smtp":
            security = get("SMTP_SECURITY", "ssl")
            if security not in SMTP_SECURITY:
                raise ValueError("SMTP_SECURITY must be ssl or starttls")
            smtp = SmtpSettings(
                host=_required(get("SMTP_HOST"), "SMTP_HOST"),
                port=_positive_int(get("SMTP_PORT", "465"), "SMTP_PORT"),
                security=security,
                username=get("SMTP_USERNAME"),
                password=get("SMTP_PASSWORD"),
            )

        yandex = None
        if get("YANDEX_CLIENT_ID"):
            uris = tuple(u.strip() for u in get("YANDEX_REDIRECT_URIS").split(",") if u.strip())
            if not uris:
                raise ValueError("YANDEX_REDIRECT_URIS is required with YANDEX_CLIENT_ID")
            for uri in uris:
                if not uri.startswith("https://") and environment == "production":
                    raise ValueError("YANDEX_REDIRECT_URIS must use https in production")
            yandex = YandexSettings(
                client_id=get("YANDEX_CLIENT_ID"),
                client_secret=_required(get("YANDEX_CLIENT_SECRET"), "YANDEX_CLIENT_SECRET"),
                redirect_uris=uris,
            )

        max_settings = None
        max_age = _positive_int(
            get("MAX_INITDATA_MAX_AGE_SECONDS", "300"), "MAX_INITDATA_MAX_AGE_SECONDS"
        )
        if max_age > 3600:
            raise ValueError("MAX_INITDATA_MAX_AGE_SECONDS must not exceed 3600")
        if get("MAX_WEBAPP_KEY"):
            key_hex = get("MAX_WEBAPP_KEY")
            if not re.fullmatch(r"[0-9a-fA-F]{64}", key_hex):
                raise ValueError("MAX_WEBAPP_KEY must be 64 hex characters")
            max_settings = MaxSettings(
                webapp_key=bytes.fromhex(key_hex),
                login_enabled=_bool(get("MAX_LOGIN_ENABLED", "false"), "MAX_LOGIN_ENABLED"),
                require_ip_match=_bool(
                    get("MAX_REQUIRE_IP_MATCH", "true"), "MAX_REQUIRE_IP_MATCH"
                ),
                max_age_seconds=max_age,
            )

        telegram_bot_username = get("TELEGRAM_BOT_USERNAME")
        if telegram_bot_username and not re.fullmatch(r"[A-Za-z0-9_]{5,64}", telegram_bot_username):
            raise ValueError("TELEGRAM_BOT_USERNAME is not a valid bot username")

        settings = cls(
            environment=environment,
            database=get("ACCOUNT_DATABASE", "data/account.sqlite3"),
            host=get("ACCOUNT_HOST", "127.0.0.1"),
            port=_positive_int(get("ACCOUNT_PORT", "28008"), "ACCOUNT_PORT"),
            allowed_networks=networks,
            web_token=get("ACCOUNT_WEB_TOKEN"),
            max_bot_token=get("ACCOUNT_MAX_TOKEN"),
            telegram_bot_token=get("ACCOUNT_TELEGRAM_TOKEN"),
            code_key=get("ACCOUNT_CODE_KEY").encode("utf-8"),
            consent_version=_required(get("ACCOUNT_CONSENT_VERSION"), "ACCOUNT_CONSENT_VERSION"),
            terms_version=_required(get("ACCOUNT_TERMS_VERSION"), "ACCOUNT_TERMS_VERSION"),
            email_backend=email_backend,
            email_from=get("ACCOUNT_EMAIL_FROM", "noreply@chtozavino.ru"),
            site_name=get("ACCOUNT_SITE_NAME", "chtozavino.ru"),
            smtp=smtp,
            yandex=yandex,
            max=max_settings,
            telegram_bot_username=telegram_bot_username,
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        secrets = {
            "ACCOUNT_WEB_TOKEN": self.web_token,
            "ACCOUNT_MAX_TOKEN": self.max_bot_token,
            "ACCOUNT_TELEGRAM_TOKEN": self.telegram_bot_token,
            "ACCOUNT_CODE_KEY": self.code_key.decode("utf-8"),
        }
        for name in ("ACCOUNT_WEB_TOKEN", "ACCOUNT_CODE_KEY"):
            if not secrets[name]:
                raise ValueError(f"{name} is required")
        for name, value in secrets.items():
            if value and len(value) < MIN_SECRET_LENGTH:
                raise ValueError(f"{name} must contain at least {MIN_SECRET_LENGTH} characters")
        present = [value for value in secrets.values() if value]
        if len(present) != len(set(present)):
            raise ValueError("Each account secret must be distinct")
        if self.production and self.email_backend != "smtp":
            raise ValueError("Production requires ACCOUNT_EMAIL_BACKEND=smtp")
        consumers = {"web": self.web_token}
        if self.max_bot_token:
            consumers["max-bot"] = self.max_bot_token
        if self.telegram_bot_token:
            consumers["telegram-bot"] = self.telegram_bot_token
        object.__setattr__(self, "consumers", consumers)


def _required(value: str, name: str) -> str:
    if not value:
        raise ValueError(f"{name} is required")
    return value


def _positive_int(value: str, name: str) -> int:
    try:
        number = int(value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer") from error
    if number <= 0:
        raise ValueError(f"{name} must be positive")
    return number


def _bool(value: str, name: str) -> bool:
    lowered = value.lower()
    if lowered in ("1", "true", "yes"):
        return True
    if lowered in ("0", "false", "no"):
        return False
    raise ValueError(f"{name} must be true or false")
