"""Load one configured matcher pipeline and return its Top-1 wine slug."""

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re

import yaml


SHA256 = re.compile(r"^[0-9a-f]{64}$")
ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
ENV_REFERENCE = re.compile(r"^\{env:(%s)\}$" % ENV_NAME.pattern[1:-1])


class ConfigError(ValueError):
    """The matcher configuration is not valid."""


@dataclass(frozen=True)
class MockMatcher:
    """A matcher that maps image SHA-256 values to configured slugs."""

    pipeline: str
    answers: dict[str, str]
    unknown_slug: str = ""
    output_dir: str | None = None
    token: str | None = None

    def predict(self, image: bytes) -> str:
        """Return the configured slug for one image body."""
        digest = hashlib.sha256(image).hexdigest()
        return self.answers.get(digest, self.unknown_slug)

    def resolved_output_dir(self, environ=None) -> str | None:
        """Resolve the configured output directory without exposing other variables."""
        if self.output_dir is None:
            return None
        match = ENV_REFERENCE.fullmatch(self.output_dir)
        if match is None:
            return self.output_dir
        variables = os.environ if environ is None else environ
        name = match.group(1)
        value = variables.get(name)
        if not isinstance(value, str) or not value:
            raise ConfigError("matcher.output_dir environment variable %s MUST be set"
                              % name)
        return value

    def resolved_token(self, environ=None) -> str | None:
        """Read the optional bearer token without storing it in YAML."""
        if self.token is None:
            return None
        match = ENV_REFERENCE.fullmatch(self.token)
        if match is None:
            raise ConfigError(
                "matcher.token MUST be an exact {env:NAME} reference")
        variables = os.environ if environ is None else environ
        name = match.group(1)
        value = variables.get(name)
        if not isinstance(value, str) or not value:
            raise ConfigError("matcher.token environment variable %s MUST be set"
                              % name)
        return value


def _mapping(value, label):
    if not isinstance(value, dict):
        raise ConfigError("%s MUST be a map" % label)
    return value


def _output_dir(value):
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ConfigError(
            "matcher.output_dir MUST be a non-empty path or exact {env:NAME} reference")
    if "{env:" in value and ENV_REFERENCE.fullmatch(value) is None:
        raise ConfigError(
            "matcher.output_dir MUST be a non-empty path or exact {env:NAME} reference")
    return value


def _token(value):
    if value is None:
        return None
    if not isinstance(value, str) or ENV_REFERENCE.fullmatch(value) is None:
        raise ConfigError(
            "matcher.token MUST be an exact {env:NAME} reference")
    return value


def load_matcher(config_path) -> MockMatcher:
    """Load and validate the selected mock pipeline."""
    path = Path(config_path)
    try:
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError("cannot read matcher configuration %s: %s" % (path, exc)) from exc
    config = _mapping(config, "configuration")

    matcher = _mapping(config.get("matcher"), "matcher")
    selected = matcher.get("pipeline")
    if not isinstance(selected, str) or not selected:
        raise ConfigError("matcher.pipeline MUST name one pipeline")
    output_dir = _output_dir(matcher.get("output_dir"))
    if "token_env" in matcher:
        raise ConfigError("matcher.token_env was replaced by matcher.token")
    token = _token(matcher.get("token"))

    entries = config.get("pipeline")
    if not isinstance(entries, list) or not entries:
        raise ConfigError("pipeline MUST be a non-empty list")
    by_name = {}
    for index, value in enumerate(entries):
        entry = _mapping(value, "pipeline[%d]" % index)
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            raise ConfigError("pipeline[%d].name MUST be a non-empty string" % index)
        if name in by_name:
            raise ConfigError("duplicate pipeline name: %s" % name)
        by_name[name] = entry

    entry = by_name.get(selected)
    if entry is None:
        raise ConfigError("matcher.pipeline names an unknown pipeline: %s" % selected)
    if entry.get("backend") != "mock":
        raise ConfigError("pipeline %s uses unsupported backend: %s"
                          % (selected, entry.get("backend")))

    answers = _mapping(entry.get("answers"), "pipeline %s answers" % selected)
    normalized = {}
    for digest, slug in answers.items():
        if not isinstance(digest, str) or not SHA256.fullmatch(digest):
            raise ConfigError("pipeline %s has an invalid SHA-256: %s" % (selected, digest))
        if not isinstance(slug, str):
            raise ConfigError("pipeline %s answer for %s MUST be a string"
                              % (selected, digest))
        normalized[digest] = slug

    unknown = entry.get("unknown_slug", "")
    if not isinstance(unknown, str):
        raise ConfigError("pipeline %s unknown_slug MUST be a string" % selected)
    return MockMatcher(
        pipeline=selected,
        answers=normalized,
        unknown_slug=unknown,
        output_dir=output_dir,
        token=token,
    )
