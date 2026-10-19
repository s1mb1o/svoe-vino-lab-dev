"""Validated public YAML settings. Secret values are read only from the environment."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from .paths import bundle_root, default_index


class ConfigError(ValueError):
    pass


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)


def validate_endpoint(value: str) -> str:
    try:
        url = urlsplit(value)
        valid = (url.scheme in {"http", "https"} and url.hostname and url.port != 0
                 and not url.username and not url.password and "?" not in value and "#" not in value
                 and not any(c.isspace() for c in value) and "{" not in value)
    except ValueError:
        valid = False
    if not valid:
        raise ValueError("Use a literal HTTP(S) URL without credentials, query or fragment")
    return value


class ServerSettings(Settings):
    host: str = Field(default="127.0.0.1", min_length=1, max_length=253)
    port: int = Field(default=8176, ge=1, le=65535)
    workers: int = Field(default=1, ge=1, le=4)
    log_level: Literal["debug", "info", "warning", "error", "critical"] = "info"
    access_log: bool = True


class AssetSettings(Settings):
    dataset: str = "bundle:data/pairing-dataset.v4.json"
    index: str | None = None
    style: str = "bundle:prompts/style-guidance.v2.en.json"


class LimitSettings(Settings):
    max_request_bytes: int = Field(default=8 * 1024 * 1024, ge=1, le=8 * 1024 * 1024)
    recognition_concurrency: int = Field(default=4, ge=1, le=32)
    recognition_queue_seconds: float = Field(default=1.0, gt=0, le=60)
    cursor_ttl_seconds: int = Field(default=3600, ge=1, le=86400)


class ImageSettings(Settings):
    max_bytes: int = Field(default=5 * 1024 * 1024, ge=1, le=5 * 1024 * 1024)
    max_pixels: int = Field(default=20_000_000, ge=1, le=40_000_000)
    max_side: int = Field(default=2048, ge=256, le=4096)


class ProviderSettings(Settings):
    endpoint: str = "https://maas.qwencloudapi.com/compatible-mode/v1/chat/completions"
    model: str = Field(default="qwen3.8-flash", min_length=1, max_length=200)
    response_model: str | None = Field(default=None, min_length=1, max_length=200)
    protocol: Literal["qwencloud", "vllm"] = "qwencloud"
    api_key_env: str | None = "QWENCLOUD_PAYGO_API_KEY"
    socket_timeout_seconds: float = Field(default=20.0, gt=0, le=300)
    budget_seconds: float = Field(default=50.0, gt=0, le=600)
    attempts: int = Field(default=3, ge=1, le=5)
    max_response_bytes: int = Field(default=1024 * 1024, ge=1, le=8 * 1024 * 1024)
    max_tokens: int = Field(default=768, ge=1, le=8192)
    temperature: float = Field(default=0.0, ge=0, le=2)
    enable_thinking: bool = False

    _endpoint = field_validator("endpoint")(validate_endpoint)

    @model_validator(mode="before")
    @classmethod
    def provider_credential_default(cls, value):
        # Selecting vLLM must not silently inherit a cloud secret reference.
        if type(value) is dict and value.get("protocol") == "vllm" and "api_key_env" not in value:
            return {**value, "api_key_env": None}
        return value

    @model_validator(mode="after")
    def credential_policy(self):
        if self.protocol == "qwencloud" and not self.api_key_env:
            raise ValueError("Cloud providers require an environment secret reference")
        return self



class RecognitionSettings(ProviderSettings):
    prompt: str = "bundle:prompts/image-system.en.txt"
    image: ImageSettings = Field(default_factory=ImageSettings)
    fallback: ProviderSettings | None = None


class EmbeddingSettings(Settings):
    endpoint: str = "https://maas.qwencloudapi.com/compatible-mode/v1/embeddings"
    model: str = Field(default="qwen3.7-text-embedding", min_length=1, max_length=200)
    dimensions: int = Field(default=1024, ge=1, le=8192)
    api_key_env: str = "QWENCLOUD_PAYGO_API_KEY"
    socket_timeout_seconds: float = Field(default=60.0, gt=0, le=300)
    attempts: int = Field(default=3, ge=1, le=5)
    workers: int = Field(default=4, ge=1, le=16)

    _endpoint = field_validator("endpoint")(validate_endpoint)


class AuthSettings(Settings):
    api_token_env: str = "DINNER_LENS_API_TOKEN"
    cursor_secret_env: str = "DINNER_LENS_CURSOR_SECRET"


class Configuration(Settings):
    server: ServerSettings = Field(default_factory=ServerSettings)
    assets: AssetSettings = Field(default_factory=AssetSettings)
    limits: LimitSettings = Field(default_factory=LimitSettings)
    recognition: RecognitionSettings = Field(default_factory=RecognitionSettings)
    embeddings: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)


def secret(env_name: str, *, required: bool = True) -> str | None:
    if not re.fullmatch(r"[A-Z][A-Z0-9_]*", env_name):
        raise ConfigError("Secret references must be environment variable names")
    value = os.environ.get(env_name)
    if required and not value:
        raise ConfigError("A required environment secret is missing: " + env_name)
    return value


def load_config(path: str | Path | None = None) -> tuple[Configuration, Path]:
    path = Path(path or os.environ.get("DINNER_LENS_CONFIG") or bundle_root() / "config.yaml").expanduser().resolve()
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        config = Configuration.model_validate(raw)
        for name in (config.auth.api_token_env, config.auth.cursor_secret_env,
                     config.recognition.api_key_env, config.embeddings.api_key_env,
                     config.recognition.fallback.api_key_env if config.recognition.fallback else None):
            if name is not None and not re.fullmatch(r"[A-Z][A-Z0-9_]*", name):
                raise ConfigError("Secret references must be environment variable names")
    except (OSError, UnicodeError, yaml.YAMLError):
        raise ConfigError("Cannot read valid YAML configuration: " + str(path)) from None
    except ValidationError as exc:
        # Pydantic input excerpts and YAML parser excerpts can contain misplaced secrets.
        fields = [".".join(str(p) for p in e["loc"]) for e in exc.errors()]
        raise ConfigError("Invalid configuration fields: " + ", ".join(fields)) from None
    return config, path


def asset_path(value: str | None, config_path: Path) -> Path:
    if value is None:
        return default_index()
    if value.startswith("bundle:"):
        return bundle_root() / value.removeprefix("bundle:")
    path = Path(value).expanduser()
    return path if path.is_absolute() else config_path.parent / path
