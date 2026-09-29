"""Load one configured matcher pipeline and return its Top-1 or ranked wine slugs."""

from dataclasses import dataclass
import hashlib
from io import BytesIO
import math
import os
from pathlib import Path
import random
import re

from PIL import Image
import yaml

from .bundle import BundleError, load_bundle
from .cascade import (BarcodeConfig, Cascade, CascadeConfig, FastAnswer, RerankConfig,
                      Sam3Config)
from .catalog import NAME as EMBEDDING_NAME, CatalogError, load_catalog, load_codes
from .main_scene import select_main_package
from .rerank import RuleBook, RuleError
from .services import Services
from .siglip2 import VIEW as SIGLIP2_VIEW, Siglip2Backend, model_input


SHA256 = re.compile(r"^[0-9a-f]{64}$")
ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
ENV_REFERENCE = re.compile(r"^\{env:(%s)\}$" % ENV_NAME.pattern[1:-1])
READINESS_TIMEOUT_SECONDS = 8.0


def _readiness_image() -> bytes:
    """Return one small deterministic image for dependency probes."""
    with Image.new("RGB", (60, 40), "white") as image:
        image.paste((128, 0, 0), (5, 5, 25, 35))
        image.paste((0, 0, 128), (35, 5, 55, 35))
        output = BytesIO()
        image.save(output, "PNG")
    return output.getvalue()


READINESS_IMAGE = _readiness_image()

GROUP_LABEL_VIEW = "label"
GROUP_FULL_WEIGHT = 0.6
GROUP_LABEL_WEIGHT = 0.4
GROUP_VIEW_CANDIDATES = 5
GROUP_MIN_SCORE = 0.75
GROUP_MIN_FULL_SCORE = 0.78
GROUP_MIN_LABEL_SCORE = 0.75
GROUP_MIN_MARGIN = 0.015
GROUP_STRONG_FULL_SCORE = 0.925
GROUP_STRONG_LABEL_SCORE = 0.84


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

    @property
    def can_match_group(self) -> bool:
        """The mock group ranking reads no bundle view."""
        return True

    def predict(self, image: bytes) -> str:
        """Return the configured slug for one image body."""
        digest = hashlib.sha256(image).hexdigest()
        return self.answers.get(digest, self.unknown_slug)

    def check_ready(self) -> None:
        """Return immediately because this pipeline has no model dependency."""
        return None

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

    def match_group_many(self, images: list[bytes], labels: list[bytes],
                         k: int) -> list[list[tuple[str, float]]]:
        """Return mock group candidates without changing the mock contract."""
        if len(images) != len(labels):
            raise ValueError("group image and label counts differ")
        return self.match_many(images, k)


@dataclass(frozen=True, eq=False)
class Siglip2Matcher(_MatcherSettings):
    """A matcher that ranks one SigLIP2 vector of the photo in one bundle."""

    pipeline: str
    backend: Siglip2Backend
    output_dir: str | None = None
    token: str | None = None
    hand_selection: bool = False

    @property
    def cards(self) -> dict | None:
        return self.backend.bundle.cards

    @property
    def can_match_group(self) -> bool:
        """Tell whether the bundle holds the view `label` that group matching ranks."""
        return GROUP_LABEL_VIEW in self.backend.bundle.views

    def predict(self, image: bytes) -> str:
        """Return the Top-1 slug for one image body."""
        return self.backend.predict(self._single_image(image))

    def check_ready(self) -> None:
        """Run one small request through each dependency of this pipeline."""
        image = READINESS_IMAGE
        if self.hand_selection:
            image = select_main_package(
                image,
                os.environ.get("SAM3_ENDPOINT"),
                timeout=READINESS_TIMEOUT_SECONDS,
            )
        self.backend.embed(
            model_input(image),
            timeout=READINESS_TIMEOUT_SECONDS,
        )

    def match(self, image: bytes, k: int) -> list[tuple[str, float]]:
        """Return the `k` best `(slug, cosine)` pairs of wines with a card."""
        vector = self.backend.embed(model_input(self._single_image(image)))
        return self._rank(vector, k)

    def match_many(self, images: list[bytes], k: int) -> list[list[tuple[str, float]]]:
        """Match every group crop. Never run single-image hand selection here."""
        vectors = self.backend.embed_many([model_input(image) for image in images])
        return [self._rank(vector, k) for vector in vectors]

    def match_group_many(self, images: list[bytes], labels: list[bytes],
                         k: int) -> list[list[tuple[str, float]]]:
        """Rank group crops by their bottle and visible-label views."""
        if len(images) != len(labels):
            raise ValueError("group image and label counts differ")
        if not images:
            return []
        if GROUP_LABEL_VIEW not in self.backend.bundle.views:
            return [[] for _ in images]
        inputs = [model_input(image) for image in images]
        inputs.extend(model_input(label) for label in labels)
        vectors = self.backend.embed_many(inputs)
        count = len(images)
        return [self._rank_group(full, label, k)
                for full, label in zip(vectors[:count], vectors[count:])]

    def _single_image(self, image: bytes) -> bytes:
        if self.hand_selection:
            return select_main_package(image, os.environ.get("SAM3_ENDPOINT"))
        return image

    def _rank(self, vector, k: int) -> list[tuple[str, float]]:
        """Rank one normalized vector against wines that have cards."""
        cards = self.cards
        ranked = self.backend.bundle.ranked(SIGLIP2_VIEW, vector)
        return [pair for pair in ranked if pair[0] in cards][:k]

    def _rank_group(self, full_vector, label_vector,
                    k: int) -> list[tuple[str, float]]:
        """Return a group match only when bottle and label views agree."""
        cards = self.cards
        full_ranked = [pair for pair in self.backend.bundle.ranked(
            SIGLIP2_VIEW, full_vector) if pair[0] in cards][:GROUP_VIEW_CANDIDATES]
        label_ranked = [pair for pair in self.backend.bundle.ranked(
            GROUP_LABEL_VIEW, label_vector) if pair[0] in cards][:GROUP_VIEW_CANDIDATES]
        full = dict(full_ranked)
        label = dict(label_ranked)
        full_positions = {slug: index for index, (slug, _) in enumerate(full_ranked, 1)}
        label_positions = {slug: index for index, (slug, _) in enumerate(label_ranked, 1)}
        combined = [
            (slug, (GROUP_FULL_WEIGHT * full[slug]
                    + GROUP_LABEL_WEIGHT * label[slug]))
            for slug in full.keys() & label.keys()
        ]
        combined.sort(key=lambda pair: (-pair[1], pair[0]))
        if not combined:
            return []
        slug, score = combined[0]
        margin = score - combined[1][1] if len(combined) > 1 else 1.0
        views_align = (
            (full_positions[slug] == 1 and label_positions[slug] <= 3)
            or (label_positions[slug] == 1 and full_positions[slug] <= 3)
        )
        margin_is_clear = margin >= GROUP_MIN_MARGIN
        views_are_strong = (
            full[slug] >= GROUP_STRONG_FULL_SCORE
            and label[slug] >= GROUP_STRONG_LABEL_SCORE
        )
        if (not views_align or score < GROUP_MIN_SCORE
                or full[slug] < GROUP_MIN_FULL_SCORE
                or label[slug] < GROUP_MIN_LABEL_SCORE
                or not (margin_is_clear or views_are_strong)):
            return []
        return combined[:k]


@dataclass(frozen=True, eq=False)
class CascadeMatcher(_MatcherSettings):
    """A matcher of the backend `cascade` (plan 85 of the workbench).

    The single-image endpoints use the async runtime `cascade`. `POST /v1/group/match`
    uses `group`: the SigLIP2 group ranking of the group embedding, unchanged.
    """

    pipeline: str
    cascade: Cascade
    group: Siglip2Matcher
    output_dir: str | None = None
    token: str | None = None
    fast_answer: FastAnswer | None = None

    @property
    def cards(self) -> dict:
        return {**(self.group.cards or {}), **self.cascade.cards}

    @property
    def can_match_group(self) -> bool:
        return self.group.can_match_group

    async def startup(self) -> None:
        await self.cascade.start()

    async def shutdown(self) -> None:
        await self.cascade.close()

    async def predict_async(self, image: bytes, started_at: float) -> tuple[str, dict]:
        """Return the Top-1 slug and the audit fields. The time budget of
        `matcher.fast_answer` counts from `started_at`."""
        return await self.cascade.predict(
            image, self.cascade.budget(started_at, self.fast_answer))

    async def match_async(self, image: bytes, k: int,
                          started_at: float) -> tuple[list[tuple[str, float]], dict]:
        """Return at most `k` ranked pairs with no time budget, and the audit fields."""
        return await self.cascade.match(image, k, self.cascade.budget(started_at))

    async def check_ready_async(self) -> None:
        await self.cascade.check_ready(model_input(READINESS_IMAGE))

    def match_many(self, images: list[bytes], k: int) -> list[list[tuple[str, float]]]:
        return self.group.match_many(images, k)

    def match_group_many(self, images: list[bytes], labels: list[bytes],
                         k: int) -> list[list[tuple[str, float]]]:
        return self.group.match_group_many(images, labels, k)


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
    fast_answer = _fast_answer(matcher.get("fast_answer"))

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
    hand_selection = entry.get("hand_selection", False)
    if type(hand_selection) is not bool:
        raise ConfigError("pipeline %s hand_selection MUST be a boolean" % selected)
    if hand_selection and entry.get("backend") != "siglip2":
        raise ConfigError("pipeline %s hand_selection requires backend siglip2" % selected)
    if fast_answer is not None and entry.get("backend") != "cascade":
        raise ConfigError("matcher.fast_answer requires a pipeline of the backend cascade")
    if entry.get("backend") == "cascade":
        return _load_cascade(selected, entry, output_dir, token, fast_answer)
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
    source = _load_source(selected, entry, required=False)
    cards = source[1].cards if source else None
    return MockMatcher(
        pipeline=selected,
        answers=normalized,
        unknown_slug=unknown,
        output_dir=output_dir,
        token=token,
        cards=cards,
    )


def _endpoint(value, selected, key="endpoint"):
    """Return the endpoint URL of a plain value or of an exact {env:NAME} reference."""
    label = "pipeline %s %s" % (selected, key)
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


def _load_source(selected, entry, required):
    """Return (label, Bundle) of the vector source of one pipeline entry, or None.

    The source is a bundle (`bundle`) or one embedding of a catalogue directory of the
    lab (`catalog` and `embedding`, plan 75 of the workbench).
    """
    if "bundle" in entry and "catalog" in entry:
        raise ConfigError("pipeline %s MUST name either bundle or catalog, not both"
                          % selected)
    if "catalog" in entry:
        path, name = entry["catalog"], entry.get("embedding")
        if not isinstance(path, str) or not path:
            raise ConfigError("pipeline %s catalog MUST be a non-empty path" % selected)
        if not isinstance(name, str) or not name:
            raise ConfigError("pipeline %s embedding MUST name an embedding of the catalog"
                              % selected)
        try:
            return "catalog", load_catalog(path, name)
        except CatalogError as exc:
            raise ConfigError("pipeline %s catalog: %s" % (selected, exc)) from exc
    if "embedding" in entry:
        raise ConfigError("pipeline %s embedding needs catalog" % selected)
    if "bundle" not in entry and not required:
        return None
    path = entry.get("bundle")
    if not isinstance(path, str) or not path:
        raise ConfigError("pipeline %s bundle MUST be a non-empty path" % selected)
    try:
        return "bundle", load_bundle(path)
    except BundleError as exc:
        raise ConfigError("pipeline %s bundle: %s" % (selected, exc)) from exc


def _load_siglip2(selected, entry, output_dir, token):
    """Load the vectors of one siglip2 pipeline and check them against the backend."""
    if "bundle" not in entry and "catalog" not in entry:
        raise ConfigError("pipeline %s bundle MUST be a non-empty path" % selected)
    endpoint = _endpoint(entry.get("endpoint"), selected)
    label, bundle = _load_source(selected, entry, required=True)
    _check_siglip2_source(selected, label, bundle)
    return Siglip2Matcher(
        pipeline=selected,
        backend=Siglip2Backend(bundle, endpoint),
        output_dir=output_dir,
        token=token,
        hand_selection=entry.get("hand_selection", False),
    )


def _check_siglip2_source(selected, label, bundle):
    """The vectors MUST come from an openai embedding with a model name and hold the
    view `full`."""
    embedding = bundle.embedding
    if embedding.get("backend") != "openai" or not isinstance(embedding.get("model"), str):
        raise ConfigError("pipeline %s %s MUST come from an openai embedding with a "
                          "model name" % (selected, label))
    if not isinstance(embedding.get("extra_body") or {}, dict):
        raise ConfigError("pipeline %s %s extra_body MUST be an object" % (selected, label))
    if SIGLIP2_VIEW not in bundle.views:
        raise ConfigError("pipeline %s %s holds no vector of the view %s"
                          % (selected, label, SIGLIP2_VIEW))


FAST_ANSWER_KEYS = ("enabled", "answer_at_seconds", "timeout_seconds")
CASCADE_KEYS = ("name", "backend", "catalog", "embedding", "group_embedding", "endpoint",
                "whole_image", "barcode", "sam3", "rerank")
BARCODE_KEYS = ("endpoint", "engine", "crops")
SAM3_KEYS = ("endpoint", "threshold", "hand", "label", "packages_first")
RERANK_KEYS = ("clusters", "endpoint", "model", "window", "side", "max_tokens",
               "timeout_seconds")
SCANNER_ENGINES = ("zxing-cpp", "zxing-cpp-sr", "boofcv-qr-cpp")


def _keys(value, allowed, label):
    value = _mapping(value, label)
    unknown = sorted(str(key) for key in set(value) - set(allowed))
    if unknown:
        raise ConfigError("%s has the unknown key %s" % (label, ", ".join(unknown)))
    return value


def _flag(mapping, key, default, label):
    value = mapping.get(key, default)
    if type(value) is not bool:
        raise ConfigError("%s %s MUST be true or false" % (label, key))
    return value


def _positive(mapping, key, default, label):
    value = mapping.get(key, default)
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value <= 0):
        raise ConfigError("%s %s MUST be a number above 0" % (label, key))
    return float(value)


def _integer(mapping, key, default, label, low, high=None):
    value = mapping.get(key, default)
    if (isinstance(value, bool) or not isinstance(value, int) or value < low
            or (high is not None and value > high)):
        limits = "from %d to %d" % (low, high) if high is not None else "of at least %d" % low
        raise ConfigError("%s %s MUST be an integer %s" % (label, key, limits))
    return value


def _fast_answer(raw):
    """Return the checked `matcher.fast_answer`, or None when the key is absent."""
    if raw is None:
        return None
    label = "matcher.fast_answer"
    raw = _keys(raw, FAST_ANSWER_KEYS, label)
    answer_at = _positive(raw, "answer_at_seconds", FastAnswer.answer_at_seconds, label)
    timeout = _positive(raw, "timeout_seconds", FastAnswer.timeout_seconds, label)
    if answer_at >= timeout:
        raise ConfigError("%s answer_at_seconds MUST be less than timeout_seconds" % label)
    return FastAnswer(_flag(raw, "enabled", True, label), answer_at, timeout)


def _load_cascade(selected, entry, output_dir, token, fast_answer):
    """Load one pipeline of the backend `cascade` (plan 85 of the workbench)."""
    label = "pipeline %s" % selected
    entry = _keys(entry, CASCADE_KEYS, label)
    catalog, name = entry.get("catalog"), entry.get("embedding")
    if not isinstance(catalog, str) or not catalog:
        raise ConfigError("%s catalog MUST be a non-empty path" % label)
    if not isinstance(name, str) or not name:
        raise ConfigError("%s embedding MUST name an embedding of the catalog" % label)
    group_name = entry.get("group_embedding", name)
    if not isinstance(group_name, str) or not group_name:
        raise ConfigError("%s group_embedding MUST name an embedding of the catalog" % label)
    endpoint = _endpoint(entry.get("endpoint"), selected)
    whole_image = _flag(entry, "whole_image", True, label)

    barcode = scanner = None
    if "barcode" in entry:
        part = label + " barcode"
        raw = _keys(entry["barcode"], BARCODE_KEYS, part)
        scanner = _endpoint(raw.get("endpoint"), selected, "barcode endpoint")
        engine = raw.get("engine", BarcodeConfig.engine)
        if engine == "auto":
            raise ConfigError("%s engine MUST NOT be auto: auto runs SAM3 and the VLM "
                              "for 8 to 15 s" % part)
        if engine not in SCANNER_ENGINES:
            raise ConfigError("%s engine MUST be one of %s" % (part, ", ".join(SCANNER_ENGINES)))
        barcode = BarcodeConfig(engine, _flag(raw, "crops", True, part))

    sam3 = sam3_url = None
    if "sam3" in entry:
        part = label + " sam3"
        raw = _keys(entry["sam3"], SAM3_KEYS, part)
        sam3_url = _endpoint(raw.get("endpoint"), selected, "sam3 endpoint")
        threshold = _positive(raw, "threshold", Sam3Config.threshold, part)
        if threshold >= 1:
            raise ConfigError("%s threshold MUST be below 1" % part)
        sam3 = Sam3Config(threshold, _flag(raw, "hand", True, part),
                          _flag(raw, "label", True, part),
                          _flag(raw, "packages_first", False, part))
    if barcode is not None and barcode.crops and sam3 is None:
        raise ConfigError("%s barcode crops requires sam3" % label)

    rerank = vlm_url = rules = None
    if "rerank" in entry:
        part = label + " rerank"
        raw = _keys(entry["rerank"], RERANK_KEYS, part)
        clusters = raw.get("clusters")
        if not isinstance(clusters, str) or not EMBEDDING_NAME.match(clusters):
            raise ConfigError("%s clusters MUST name an embedding directory of the catalog"
                              % part)
        vlm_url = _endpoint(raw.get("endpoint"), selected, "rerank endpoint")
        model = raw.get("model", RerankConfig.model)
        if not isinstance(model, str) or not model.strip():
            raise ConfigError("%s model MUST be a non-empty string" % part)
        rerank = RerankConfig(
            model.strip(),
            _integer(raw, "window", RerankConfig.window, part, 2),
            _integer(raw, "side", RerankConfig.side, part, 64, 4096),
            _integer(raw, "max_tokens", RerankConfig.max_tokens, part, 1),
            _positive(raw, "timeout_seconds", RerankConfig.timeout_seconds, part))
        try:
            rules = RuleBook.load(Path(catalog) / "embeddings" / clusters)
        except RuleError as exc:
            raise ConfigError("%s: %s" % (part, exc)) from exc

    try:
        bundle = load_catalog(catalog, name)
        group_bundle = bundle if group_name == name else load_catalog(catalog, group_name)
        codes = load_codes(catalog) if barcode is not None else None
    except CatalogError as exc:
        raise ConfigError("%s catalog: %s" % (label, exc)) from exc
    _check_siglip2_source(selected, "catalog embedding", bundle)
    _check_siglip2_source(selected, "catalog group_embedding", group_bundle)
    return CascadeMatcher(
        pipeline=selected,
        cascade=Cascade(CascadeConfig(whole_image, barcode, sam3, rerank), bundle,
                        Services(siglip2=endpoint, sam3=sam3_url, scanner=scanner,
                                 vlm=vlm_url),
                        codes=codes, rules=rules),
        group=Siglip2Matcher(pipeline=selected,
                             backend=Siglip2Backend(group_bundle, endpoint)),
        output_dir=output_dir,
        token=token,
        fast_answer=fast_answer,
    )
