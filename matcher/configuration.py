"""Read public settings from YAML. Resolve secret values only at the caller."""

from dataclasses import dataclass, fields, replace
import math
from pathlib import Path
from urllib.parse import urlsplit

import yaml
from PIL import Image


class ConfigError(ValueError):
    """The matcher configuration is not valid."""


def minimum_score(document):
    """Read the inclusive single-image acceptance floor from public YAML."""
    value = document["matcher"].get("min_score", 0.7)
    if (type(value) not in (int, float) or not 0 <= value <= 1
            or not math.isfinite(value)):
        raise ConfigError("matcher.min_score MUST be a finite number from 0 to 1")
    return float(value)


@dataclass(frozen=True)
class RuntimeSettings:
    max_image_bytes: int = 20 * 1024 * 1024
    max_image_pixels: int = 40_000_000
    upload_timeout_seconds: float = 30.0
    max_inflight_requests: int = 8
    max_queued_requests: int = 16
    queue_timeout_seconds: float = 0.25

    def __post_init__(self):
        for field in fields(self):
            value = getattr(self, field.name)
            integer = field.name not in {"upload_timeout_seconds", "queue_timeout_seconds"}
            valid = (type(value) is int if integer else type(value) in (int, float))
            try:
                valid = valid and math.isfinite(value) and value > 0
            except OverflowError:
                valid = False
            if not valid:
                kind = "a positive integer" if integer else "a finite positive number"
                raise ConfigError("matcher.limits.%s MUST be %s" % (field.name, kind))
        if self.max_image_pixels > Image.MAX_IMAGE_PIXELS:
            raise ConfigError("matcher.limits.max_image_pixels MUST NOT exceed the Pillow limit %d"
                              % Image.MAX_IMAGE_PIXELS)

    def with_overrides(self, **values):
        """Allow explicit factory arguments for embedded callers and tests."""
        return replace(self, **{key: value for key, value in values.items() if value is not None})


def read_configuration(path):
    try:
        document = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        # YAML parser excerpts can contain a secret. Do not include the source body.
        raise ConfigError("cannot read matcher configuration %s" % path) from None
    if not isinstance(document, dict) or not isinstance(document.get("matcher"), dict):
        raise ConfigError("configuration and matcher MUST be mappings")
    return document


def runtime_settings(document):
    raw = document["matcher"].get("limits", {})
    if not isinstance(raw, dict):
        raise ConfigError("matcher.limits MUST be a mapping")
    unknown = set(raw) - {field.name for field in fields(RuntimeSettings)}
    if unknown:
        raise ConfigError("matcher.limits has an unknown setting")
    return RuntimeSettings(**raw)


def endpoint_url(value, label):
    """Endpoints are public YAML values. Authentication MUST use a secret setting."""
    if not isinstance(value, str) or not value.strip() or "{env:" in value:
        raise ConfigError("%s MUST be a literal http:// or https:// URL in YAML" % label)
    try:
        parsed = urlsplit(value)
        _ = parsed.port  # Validate a configured port before the first model call.
        valid = (parsed.scheme in {"http", "https"} and parsed.hostname
                 and parsed.username is None and parsed.password is None
                 and not parsed.query and not parsed.fragment
                 and not any(ch.isspace() for ch in value))
    except ValueError:
        valid = False
    if not valid:
        raise ConfigError("%s MUST be an http:// or https:// URL without credentials, query or fragment" % label)
    return value


def sam3_endpoint(document):
    value = document["matcher"].get("sam3_endpoint")
    return None if value is None else endpoint_url(value, "matcher.sam3_endpoint")
