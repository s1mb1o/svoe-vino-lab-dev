"""Load one configured matcher pipeline and return its Top-1 or ranked wine slugs."""

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import random
import re

import yaml

from .bundle import BundleError, load_bundle
from .siglip2 import VIEW as SIGLIP2_VIEW, Siglip2Backend, model_input


SHA256 = re.compile(r"^[0-9a-f]{64}$")
ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
ENV_REFERENCE = re.compile(r"^\{env:(%s)\}$" % ENV_NAME.pattern[1:-1])


class ConfigError(ValueError):
    """The matcher configuration is not valid."""


class _MatcherSettings:
    """The output directory and token resolution that every backend shares."""

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


@dataclass(frozen=True)
class MockMatcher(_MatcherSettings):
    """A matcher that maps image SHA-256 values to configured slugs."""

    pipeline: str
    answers: dict[str, str]
    unknown_slug: str = ""
    output_dir: str | None = None
    token: str | None = None
    # slug -> wine card of the optional bundle, or None without a version 2 bundle.
    cards: dict | None = None

    def predict(self, image: bytes) -> str:
        """Return the configured slug for one image body."""
        digest = hashlib.sha256(image).hexdigest()
        return self.answers.get(digest, self.unknown_slug)

    def match(self, image: bytes, k: int) -> list[tuple[str, float]]:
        """Return up to `k` `(slug, score)` pairs of wines with a card.

        A known image gives its configured slug first with score 1.0. The other pairs
        are random wines with random scores in [0, 1), the best score first.
        """
        known = self.answers.get(hashlib.sha256(image).hexdigest())
        ranked = [(known, 1.0)] if known in self.cards else []
        others = [slug for slug in self.cards if slug != known]
        picked = random.sample(others, min(k - len(ranked), len(others)))
        ranked.extend(sorted(((slug, random.random()) for slug in picked),
                             key=lambda pair: pair[1], reverse=True))
        return ranked

    def match_many(self, images: list[bytes], k: int) -> list[list[tuple[str, float]]]:
        """Return ranked candidates for each image."""
        return [self.match(image, k) for image in images]


@dataclass(frozen=True, eq=False)
class Siglip2Matcher(_MatcherSettings):
    """A matcher that ranks one SigLIP2 vector of the photo in one bundle."""

    pipeline: str
    backend: Siglip2Backend
    output_dir: str | None = None
    token: str | None = None

    @property
    def cards(self) -> dict | None:
        return self.backend.bundle.cards

    def predict(self, image: bytes) -> str:
        """Return the Top-1 slug for one image body."""
        return self.backend.predict(image)

    def match(self, image: bytes, k: int) -> list[tuple[str, float]]:
        """Return the `k` best `(slug, cosine)` pairs of wines with a card."""
        vector = self.backend.embed(model_input(image))
        return self._rank(vector, k)

    def match_many(self, images: list[bytes], k: int) -> list[list[tuple[str, float]]]:
        """Return ranked candidates for all images after one embedding request."""
        vectors = self.backend.embed_many([model_input(image) for image in images])
        return [self._rank(vector, k) for vector in vectors]

    def _rank(self, vector, k: int) -> list[tuple[str, float]]:
        """Rank one normalized vector against wines that have cards."""
        cards = self.cards
        ranked = self.backend.bundle.ranked(SIGLIP2_VIEW, vector)
        return [pair for pair in ranked if pair[0] in cards][:k]


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


def load_matcher(config_path) -> MockMatcher | Siglip2Matcher:
    """Load and validate the selected pipeline."""
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
    if entry.get("backend") == "siglip2":
        return _load_siglip2(selected, entry, output_dir, token)
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
    cards = None
    if "bundle" in entry:
        path = entry["bundle"]
        if not isinstance(path, str) or not path:
            raise ConfigError("pipeline %s bundle MUST be a non-empty path" % selected)
        try:
            cards = load_bundle(path).cards
        except BundleError as exc:
            raise ConfigError("pipeline %s bundle: %s" % (selected, exc)) from exc
    return MockMatcher(
        pipeline=selected,
        answers=normalized,
        unknown_slug=unknown,
        output_dir=output_dir,
        token=token,
        cards=cards,
    )


def _endpoint(value, selected):
    """Return the endpoint URL of a plain value or of an exact {env:NAME} reference."""
    label = "pipeline %s endpoint" % selected
    if not isinstance(value, str) or not value:
        raise ConfigError("%s MUST be a URL or an exact {env:NAME} reference" % label)
    match = ENV_REFERENCE.fullmatch(value)
    if match is None:
        if "{env:" in value:
            raise ConfigError("%s MUST be a URL or an exact {env:NAME} reference" % label)
        url = value
    else:
        url = os.environ.get(match.group(1))
        if not isinstance(url, str) or not url:
            raise ConfigError("%s environment variable %s MUST be set"
                              % (label, match.group(1)))
    if not url.startswith(("http://", "https://")):
        raise ConfigError("%s MUST start with http:// or https://" % label)
    return url


def _load_siglip2(selected, entry, output_dir, token):
    """Load the bundle of one siglip2 pipeline and check it against the backend."""
    path = entry.get("bundle")
    if not isinstance(path, str) or not path:
        raise ConfigError("pipeline %s bundle MUST be a non-empty path" % selected)
    endpoint = _endpoint(entry.get("endpoint"), selected)
    try:
        bundle = load_bundle(path)
    except BundleError as exc:
        raise ConfigError("pipeline %s bundle: %s" % (selected, exc)) from exc
    embedding = bundle.embedding
    if embedding.get("backend") != "openai" or not isinstance(embedding.get("model"), str):
        raise ConfigError("pipeline %s bundle MUST come from an openai embedding with a "
                          "model name" % selected)
    if not isinstance(embedding.get("extra_body") or {}, dict):
        raise ConfigError("pipeline %s bundle extra_body MUST be an object" % selected)
    if SIGLIP2_VIEW not in bundle.views:
        raise ConfigError("pipeline %s bundle holds no vector of the view %s"
                          % (selected, SIGLIP2_VIEW))
    return Siglip2Matcher(
        pipeline=selected,
        backend=Siglip2Backend(bundle, endpoint),
        output_dir=output_dir,
        token=token,
    )
