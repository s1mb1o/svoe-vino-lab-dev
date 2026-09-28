from __future__ import annotations

import io
import json
from dataclasses import dataclass

import httpx
from PIL import Image, ImageOps, UnidentifiedImageError

from .image_types import UnsupportedImage, detect_image_type

MODEL_NAME = "shieldgemma-2-4b-it"
POLICIES = ("dangerous", "sexual", "violence")
MODERATION_THRESHOLD = 0.5


class InvalidImage(ValueError):
    pass


class ModerationUnavailable(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ModerationResult:
    safe: bool | None
    category: str
    confidence: float
    reason: str
    scores: dict[str, float]
    bypassed: bool = False

    @property
    def performed(self) -> bool:
        return not self.bypassed

    @property
    def accepted(self) -> bool:
        return self.safe is True or self.bypassed


def make_moderation_jpeg(body: bytes, max_side: int = 1024) -> bytes:
    try:
        detect_image_type(body)
        with Image.open(io.BytesIO(body)) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=88, optimize=True)
            return output.getvalue()
    except (UnsupportedImage, UnidentifiedImageError, OSError, ValueError) as exc:
        raise InvalidImage("Telegram file is not a supported image") from exc


def parse_moderation_response(value: object) -> ModerationResult:
    if not isinstance(value, dict):
        raise ModerationUnavailable("moderation response is not an object")
    if value.get("model") != MODEL_NAME:
        raise ModerationUnavailable("moderation response has an unexpected model")
    threshold = value.get("threshold")
    if (
        not isinstance(threshold, (int, float))
        or isinstance(threshold, bool)
        or float(threshold) != MODERATION_THRESHOLD
    ):
        raise ModerationUnavailable("moderation threshold is invalid")
    raw_scores = value.get("scores")
    if not isinstance(raw_scores, dict) or set(raw_scores) != set(POLICIES):
        raise ModerationUnavailable("moderation scores have invalid policies")
    scores: dict[str, float] = {}
    for policy in POLICIES:
        score = raw_scores[policy]
        if (
            not isinstance(score, (int, float))
            or isinstance(score, bool)
            or not 0 <= float(score) <= 1
        ):
            raise ModerationUnavailable("moderation score is invalid")
        scores[policy] = float(score)
    flagged = value.get("flagged")
    if (
        not isinstance(flagged, list)
        or any(not isinstance(policy, str) for policy in flagged)
        or len(flagged) != len(set(flagged))
        or not set(flagged) <= set(POLICIES)
    ):
        raise ModerationUnavailable("moderation flagged list is invalid")
    expected_flagged = {
        policy for policy, score in scores.items() if score >= MODERATION_THRESHOLD
    }
    if set(flagged) != expected_flagged:
        raise ModerationUnavailable("moderation scores and flagged list disagree")
    ordered_flagged = [policy for policy in POLICIES if policy in expected_flagged]
    reason = ",".join(f"{policy}={scores[policy]:.6f}" for policy in POLICIES)
    return ModerationResult(
        safe=not ordered_flagged,
        category=",".join(ordered_flagged) if ordered_flagged else "safe",
        confidence=max(scores.values()),
        reason=reason,
        scores=scores,
    )


class Moderator:
    def __init__(self, endpoint: str, client: httpx.AsyncClient) -> None:
        self._endpoint = endpoint
        self._client = client

    async def classify(self, jpeg: bytes) -> ModerationResult:
        try:
            response = await self._client.post(
                self._endpoint,
                files={"image": ("moderation.jpg", jpeg, "image/jpeg")},
                timeout=120,
            )
            response.raise_for_status()
            return parse_moderation_response(response.json())
        except ModerationUnavailable:
            raise
        except (httpx.HTTPError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ModerationUnavailable("moderation service is unavailable") from exc


class DisabledModerator:
    """Accept a valid image without a call to a moderation service."""

    async def classify(self, jpeg: bytes) -> ModerationResult:
        return ModerationResult(
            safe=None,
            category="disabled",
            confidence=0.0,
            reason="moderation_disabled",
            scores={},
            bypassed=True,
        )


def make_moderator(
    enabled: bool,
    endpoint: str | None,
    client: httpx.AsyncClient,
) -> Moderator | DisabledModerator:
    if not enabled:
        return DisabledModerator()
    if endpoint is None:
        raise ValueError("the moderation endpoint is required when moderation is enabled")
    return Moderator(endpoint, client)
