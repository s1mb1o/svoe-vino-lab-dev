from __future__ import annotations

import ipaddress
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import yaml

MATCH_PATH = "/v1/match"
DEFAULT_CONFIG_FILE = "config.yaml"
MINIMUM_SECRET_LENGTH = 32
DEFAULT_MAX_API_BASE_URL = "https://platform-api2.max.ru"
UPDATE_MODES = ("polling", "webhook")
# MAX accepts 5 to 256 characters in [A-Za-z0-9_-]. The bot requires at least 32.
WEBHOOK_SECRET = re.compile(r"[A-Za-z0-9_-]{32,256}\Z")
ENV_NAME = r"[A-Za-z_][A-Za-z0-9_]*"
ENV_REFERENCE = re.compile(rf"\{{env:({ENV_NAME})\}}\Z")


class ConfigError(ValueError):
    """The bot configuration is not valid."""


def _mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ConfigError(f"{label} MUST be a map")
    return value


def _resolve_endpoint(
    value: object,
    label: str,
    variables: Mapping[str, str],
) -> str:
    if not isinstance(value, str) or not value:
        raise ConfigError(f"{label} MUST be an HTTP URL or an exact {{env:NAME}} reference")
    match = ENV_REFERENCE.fullmatch(value)
    if match is None:
        if "{env:" in value:
            raise ConfigError(
                f"{label} MUST be an HTTP URL or an exact {{env:NAME}} reference"
            )
        endpoint = value.strip()
    else:
        name = match.group(1)
        endpoint = variables.get(name, "").strip()
        if not endpoint:
            raise ConfigError(f"{label} environment variable {name} MUST be set")
    try:
        parts = urlsplit(endpoint)
    except ValueError as exc:
        raise ConfigError(f"{label} MUST be an HTTP URL") from exc
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ConfigError(f"{label} MUST be an HTTP URL")
    if parts.query or parts.fragment:
        raise ConfigError(f"{label} MUST NOT contain a query or fragment")
    return endpoint


@dataclass(frozen=True, slots=True)
class EndpointSettings:
    moderation_enabled: bool
    moderation: str | None
    sam3: str
    matcher: str

    @classmethod
    def from_config(
        cls,
        config_file: str | Path | None = None,
        *,
        environ: Mapping[str, str] | None = None,
    ) -> EndpointSettings:
        """Load the service endpoints and resolve exact environment references."""
        variables = os.environ if environ is None else environ
        path_value = config_file or variables.get("BOT_CONFIG", DEFAULT_CONFIG_FILE)
        if not isinstance(path_value, (str, Path)) or not str(path_value).strip():
            raise ConfigError("BOT_CONFIG MUST name a configuration file")
        path = Path(path_value)
        try:
            configuration = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise ConfigError(f"cannot read bot configuration {path}: {exc}") from exc
        root = _mapping(configuration, "configuration")
        moderation_settings = _mapping(root.get("moderation", {}), "moderation")
        moderation_enabled = moderation_settings.get("enabled", True)
        if not isinstance(moderation_enabled, bool):
            raise ConfigError("moderation.enabled MUST be true or false")
        endpoints = _mapping(root.get("endpoints"), "endpoints")
        moderation_value = endpoints.get("moderation")
        if moderation_enabled:
            moderation = _resolve_endpoint(
                moderation_value, "endpoints.moderation", variables
            ).rstrip("/")
        else:
            _validate_optional_endpoint(moderation_value, "endpoints.moderation")
            moderation = None
        sam3 = _resolve_endpoint(endpoints.get("sam3"), "endpoints.sam3", variables)
        matcher = _resolve_endpoint(endpoints.get("matcher"), "endpoints.matcher", variables)
        matcher_parts = urlsplit(matcher)
        # A trailing slash gets a redirect. httpx does not follow it for POST.
        if not matcher_parts.path.endswith(MATCH_PATH):
            raise ConfigError(f"endpoints.matcher MUST name the matcher endpoint {MATCH_PATH}")
        return cls(
            moderation_enabled=moderation_enabled,
            moderation=moderation,
            sam3=sam3.rstrip("/"),
            matcher=matcher,
        )


def _validate_optional_endpoint(value: object, label: str) -> None:
    """Validate a disabled service endpoint without resolving its environment value."""
    if value is None or (isinstance(value, str) and ENV_REFERENCE.fullmatch(value)):
        return
    _resolve_endpoint(value, label, {})


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _required_positive_int(name: str) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        raise ValueError(f"{name} is required")
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _required_secret(name: str, *, minimum_length: int = MINIMUM_SECRET_LENGTH) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is required")
    if len(value) < minimum_length:
        raise ValueError(f"{name} must contain at least {minimum_length} characters")
    return value


def _port(name: str, default: int) -> int:
    value = _positive_int(name, default)
    if value > 65535:
        raise ValueError(f"{name} must not exceed 65535")
    return value


def _boolean(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be true or false")


def _ratio(name: str, default: float, *, allow_zero: bool = True) -> float:
    raw = os.getenv(name, str(default))
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc
    if value < 0.0 or value > 1.0 or (not allow_zero and value == 0.0):
        qualifier = "between zero and one" if allow_zero else "greater than zero and at most one"
        raise ValueError(f"{name} must be {qualifier}")
    return value


def _positive_float(name: str, default: float) -> float:
    raw = os.getenv(name, str(default))
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _https_url(name: str, value: str) -> tuple[str, int | None]:
    """Validate an HTTPS URL. Return the URL and its explicit port, if any."""
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError as exc:
        raise ValueError(f"{name} must be an HTTPS URL") from exc
    if parts.scheme != "https" or not parts.hostname:
        raise ValueError(f"{name} must be an HTTPS URL")
    if parts.query or parts.fragment or parts.username or parts.password:
        raise ValueError(f"{name} must not contain a query, a fragment, or credentials")
    return value, port


def _ca_file(value: str | None) -> Path | None:
    """Return the extra CA file. An empty value selects the bundled Минцифры root."""
    from .max_api import DEFAULT_CA_FILE

    raw = (value or "").strip()
    if not raw:
        return DEFAULT_CA_FILE
    if raw.lower() == "none":
        return None
    path = Path(raw).expanduser()
    if not path.is_file():
        raise ValueError("MAX_API_CA_FILE must name a readable PEM file or 'none'")
    return path


def _host_suffixes(value: str | None) -> tuple[str, ...]:
    hosts = tuple(item.strip().lower().lstrip(".") for item in (value or "").split(","))
    return tuple(host for host in hosts if host)


@dataclass(frozen=True, slots=True)
class WebhookSettings:
    url: str
    secret: str
    host: str
    port: int
    path: str
    subscribe: bool


def _webhook_settings() -> WebhookSettings:
    url, port = _https_url("MAX_WEBHOOK_URL", os.getenv("MAX_WEBHOOK_URL", "").strip())
    # MAX delivers a webhook only to port 443, and the URL must not name a port.
    if port is not None:
        raise ValueError("MAX_WEBHOOK_URL must not contain a port; MAX uses port 443")
    secret = os.getenv("MAX_WEBHOOK_SECRET", "").strip()
    if not WEBHOOK_SECRET.fullmatch(secret):
        raise ValueError(
            "MAX_WEBHOOK_SECRET must contain 32 to 256 characters of A-Z, a-z, 0-9, _ and -"
        )
    path = os.getenv("MAX_WEBHOOK_PATH", "").strip() or urlsplit(url).path or "/"
    if not path.startswith("/"):
        raise ValueError("MAX_WEBHOOK_PATH must start with /")
    host = os.getenv("MAX_WEBHOOK_HOST", "127.0.0.1").strip()
    if not host:
        raise ValueError("MAX_WEBHOOK_HOST is required")
    return WebhookSettings(
        url=url,
        secret=secret,
        host=host,
        port=_port("MAX_WEBHOOK_PORT", 28006),
        path=path,
        subscribe=_boolean("MAX_WEBHOOK_SUBSCRIBE", True),
    )


@dataclass(frozen=True, slots=True)
class Settings:
    max_token: str
    environment: str
    moderation_enabled: bool
    moderation_endpoint: str | None
    sam3_endpoint: str
    matcher_endpoint: str
    data_root: Path
    database_file: Path
    rejection_image_file: Path
    admin_user_id: int
    rate_limit: int
    rate_window_seconds: int
    queue_workers: int
    queue_capacity: int
    queue_estimate_seconds: float
    max_image_bytes: int
    match_min_score: float
    match_min_margin: float
    quality_blur_min_variance: float
    quality_glare_max_ratio: float
    quality_bottle_min_area_ratio: float
    quality_label_min_area_ratio: float
    http_api_host: str
    http_api_port: int
    http_api_allowed_networks: tuple[str, ...]
    http_api_token: str
    http_api_rate_limit: int
    http_api_rate_window_seconds: int
    http_api_max_in_flight: int
    data_retention_days: int
    sync_profile: bool
    log_level: str
    max_api_base_url: str = DEFAULT_MAX_API_BASE_URL
    max_api_ca_file: Path | None = None
    update_mode: str = "polling"
    poll_timeout_seconds: int = 30
    webhook: WebhookSettings | None = None
    media_allowed_hosts: tuple[str, ...] = ()

    @classmethod
    def from_env(cls) -> Settings:
        token = os.getenv("MAX_BOT_TOKEN", "").strip()
        if not token:
            raise ValueError("MAX_BOT_TOKEN is required")
        endpoints = EndpointSettings.from_config()
        environment = os.getenv("BOT_ENVIRONMENT", "production").strip().lower()
        if environment not in {"production", "development", "test"}:
            raise ValueError("BOT_ENVIRONMENT must be production, development, or test")
        if environment == "production" and not endpoints.moderation_enabled:
            raise ValueError("production requires moderation.enabled=true")

        data_root = Path(os.getenv("BOT_DATA_ROOT", "data")).expanduser()
        database_file = Path(os.getenv("BOT_DATABASE", str(data_root / "bot.sqlite3"))).expanduser()

        queue_workers = _positive_int("BOT_QUEUE_WORKERS", 1)
        queue_capacity = _positive_int("BOT_QUEUE_CAPACITY", 100)
        if queue_workers > queue_capacity:
            raise ValueError("BOT_QUEUE_WORKERS must not exceed BOT_QUEUE_CAPACITY")
        http_api_host = os.getenv("BOT_HTTP_API_HOST", "127.0.0.1").strip()
        if not http_api_host:
            raise ValueError("BOT_HTTP_API_HOST is required")
        http_api_allowed_networks = tuple(
            item.strip()
            for item in os.getenv(
                "BOT_HTTP_API_ALLOWED_NETWORKS",
                "127.0.0.1/32,::1/128,192.168.86.0/24",
            ).split(",")
            if item.strip()
        )
        if not http_api_allowed_networks:
            raise ValueError("BOT_HTTP_API_ALLOWED_NETWORKS is required")
        retention_days = _positive_int("BOT_DATA_RETENTION_DAYS", 30)
        if environment == "production" and retention_days != 30:
            raise ValueError("production requires BOT_DATA_RETENTION_DAYS=30")

        base_url, _ = _https_url(
            "MAX_API_BASE_URL",
            os.getenv("MAX_API_BASE_URL", DEFAULT_MAX_API_BASE_URL).strip().rstrip("/"),
        )
        # MAX requires a webhook for production. Long polling is for development and tests.
        default_mode = "webhook" if environment == "production" else "polling"
        update_mode = os.getenv("MAX_UPDATE_MODE", default_mode).strip().lower()
        if update_mode not in UPDATE_MODES:
            raise ValueError("MAX_UPDATE_MODE must be polling or webhook")
        if (
            environment == "production"
            and update_mode == "polling"
            and not _boolean("MAX_ALLOW_PRODUCTION_POLLING", False)
        ):
            raise ValueError(
                "production requires MAX_UPDATE_MODE=webhook; "
                "set MAX_ALLOW_PRODUCTION_POLLING=true to use long polling"
            )
        raw_poll_timeout = os.getenv("MAX_POLL_TIMEOUT_SECONDS", "30").strip()
        try:
            poll_timeout = int(raw_poll_timeout)
        except ValueError as exc:
            raise ValueError("MAX_POLL_TIMEOUT_SECONDS must be an integer") from exc
        if not 0 <= poll_timeout <= 90:
            raise ValueError("MAX_POLL_TIMEOUT_SECONDS must be from 0 to 90")
        webhook = _webhook_settings() if update_mode == "webhook" else None
        http_api_token = _required_secret("BOT_HTTP_API_TOKEN")
        secrets_in_use = [token, http_api_token] + ([webhook.secret] if webhook else [])
        if len(set(secrets_in_use)) != len(secrets_in_use):
            raise ValueError(
                "MAX_BOT_TOKEN, BOT_HTTP_API_TOKEN, and MAX_WEBHOOK_SECRET must differ"
            )

        return cls(
            max_token=token,
            environment=environment,
            moderation_enabled=endpoints.moderation_enabled,
            moderation_endpoint=endpoints.moderation,
            sam3_endpoint=endpoints.sam3,
            matcher_endpoint=endpoints.matcher,
            data_root=data_root,
            database_file=database_file,
            rejection_image_file=Path(
                os.getenv(
                    "BOT_REJECTION_IMAGE",
                    "assets/content-rejected-monkey-640x640.png",
                )
            ).expanduser(),
            admin_user_id=_required_positive_int("BOT_ADMIN_USER_ID"),
            rate_limit=_positive_int("BOT_RATE_LIMIT", 50),
            rate_window_seconds=_positive_int("BOT_RATE_WINDOW_SECONDS", 3600),
            queue_workers=queue_workers,
            queue_capacity=queue_capacity,
            queue_estimate_seconds=_positive_float("BOT_QUEUE_ESTIMATE_SECONDS", 20.0),
            max_image_bytes=_positive_int("BOT_MAX_IMAGE_BYTES", 20 * 1024 * 1024),
            match_min_score=_ratio("BOT_MATCH_MIN_SCORE", 0.70),
            match_min_margin=_ratio("BOT_MATCH_MIN_MARGIN", 0.015),
            quality_blur_min_variance=_positive_float(
                "BOT_QUALITY_BLUR_MIN_VARIANCE", 80.0
            ),
            quality_glare_max_ratio=_ratio("BOT_QUALITY_GLARE_MAX_RATIO", 0.20),
            quality_bottle_min_area_ratio=_ratio(
                "BOT_QUALITY_BOTTLE_MIN_AREA_RATIO", 0.10,
                allow_zero=False,
            ),
            quality_label_min_area_ratio=_ratio(
                "BOT_QUALITY_LABEL_MIN_AREA_RATIO", 0.015,
                allow_zero=False,
            ),
            http_api_host=http_api_host,
            http_api_port=_port("BOT_HTTP_API_PORT", 28004),
            http_api_allowed_networks=http_api_allowed_networks,
            http_api_token=http_api_token,
            http_api_rate_limit=_positive_int("BOT_HTTP_API_RATE_LIMIT", 10),
            http_api_rate_window_seconds=_positive_int(
                "BOT_HTTP_API_RATE_WINDOW_SECONDS", 3600
            ),
            http_api_max_in_flight=_positive_int("BOT_HTTP_API_MAX_IN_FLIGHT", 2),
            data_retention_days=retention_days,
            sync_profile=_boolean("BOT_SYNC_PROFILE", True),
            log_level=os.getenv("BOT_LOG_LEVEL", "INFO").upper(),
            max_api_base_url=base_url,
            max_api_ca_file=_ca_file(os.getenv("MAX_API_CA_FILE")),
            update_mode=update_mode,
            poll_timeout_seconds=poll_timeout,
            webhook=webhook,
            media_allowed_hosts=_host_suffixes(os.getenv("MAX_MEDIA_ALLOWED_HOSTS")),
        )


@dataclass(frozen=True, slots=True)
class AdminWebSettings:
    data_root: Path
    database_file: Path
    username: str
    password: str
    host: str
    port: int
    allowed_networks: tuple[str, ...]
    rate_limit: int
    rate_window_seconds: int
    log_level: str
    behind_tls_proxy: bool = False
    auth_rate_limit: int = 10
    auth_rate_window_seconds: int = 300

    @classmethod
    def from_env(cls) -> AdminWebSettings:
        data_root = Path(os.getenv("BOT_DATA_ROOT", "data")).expanduser()
        username = os.getenv("BOT_ADMIN_WEB_USERNAME", "admin").strip()
        password = _required_secret("BOT_ADMIN_WEB_PASSWORD")
        if not username:
            raise ValueError("BOT_ADMIN_WEB_USERNAME is required")
        networks = tuple(
            item.strip()
            for item in os.getenv(
                "BOT_ADMIN_WEB_ALLOWED_NETWORKS",
                "127.0.0.1/32,::1/128",
            ).split(",")
            if item.strip()
        )
        if not networks:
            raise ValueError("BOT_ADMIN_WEB_ALLOWED_NETWORKS is required")
        host = os.getenv("BOT_ADMIN_WEB_HOST", "127.0.0.1").strip()
        if not host:
            raise ValueError("BOT_ADMIN_WEB_HOST is required")
        behind_tls_proxy = _boolean("BOT_ADMIN_WEB_BEHIND_TLS_PROXY", False)
        try:
            loopback_host = ipaddress.ip_address(host).is_loopback
        except ValueError:
            loopback_host = host.casefold() == "localhost"
        if not loopback_host and not behind_tls_proxy:
            raise ValueError(
                "a non-loopback BOT_ADMIN_WEB_HOST requires "
                "BOT_ADMIN_WEB_BEHIND_TLS_PROXY=true"
            )
        return cls(
            data_root=data_root,
            database_file=Path(
                os.getenv("BOT_DATABASE", str(data_root / "bot.sqlite3"))
            ).expanduser(),
            username=username,
            password=password,
            host=host,
            port=_port("BOT_ADMIN_WEB_PORT", 28005),
            allowed_networks=networks,
            rate_limit=_positive_int("BOT_RATE_LIMIT", 50),
            rate_window_seconds=_positive_int("BOT_RATE_WINDOW_SECONDS", 3600),
            log_level=os.getenv("BOT_LOG_LEVEL", "INFO").upper(),
            behind_tls_proxy=behind_tls_proxy,
            auth_rate_limit=_positive_int("BOT_ADMIN_WEB_AUTH_RATE_LIMIT", 10),
            auth_rate_window_seconds=_positive_int(
                "BOT_ADMIN_WEB_AUTH_RATE_WINDOW_SECONDS", 300
            ),
        )
