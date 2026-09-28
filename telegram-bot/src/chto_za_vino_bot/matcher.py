from __future__ import annotations

import json
import math
from dataclasses import dataclass

import httpx

from .wine import Wine, wine_from_card

MATCH_CANDIDATES = 4


class RecognitionUnavailable(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RecognitionCandidate:
    slug: str
    score: float
    rank: int
    wine: Wine


@dataclass(frozen=True, slots=True)
class RecognitionResult:
    candidates: tuple[RecognitionCandidate, ...]
    pipeline: str

    @property
    def top(self) -> RecognitionCandidate:
        return self.candidates[0]

    @property
    def margin(self) -> float:
        if len(self.candidates) < 2:
            return 0.0
        return self.candidates[0].score - self.candidates[1].score


def parse_recognition_response(value: object) -> RecognitionResult:
    """Parse one `/v1/match` answer. Raise RecognitionUnavailable for a broken answer."""
    if not isinstance(value, dict):
        raise RecognitionUnavailable("matcher response is not an object")
    pipeline = value.get("pipeline")
    if not isinstance(pipeline, str) or not pipeline:
        raise RecognitionUnavailable("matcher response has no pipeline name")
    raw_candidates = value.get("candidates")
    if not isinstance(raw_candidates, list) or len(raw_candidates) > MATCH_CANDIDATES:
        raise RecognitionUnavailable(
            f"matcher must return at most {MATCH_CANDIDATES} candidates"
        )

    candidates: list[RecognitionCandidate] = []
    seen_slugs: set[str] = set()
    previous_score = math.inf
    for expected_rank, item in enumerate(raw_candidates, start=1):
        if not isinstance(item, dict):
            raise RecognitionUnavailable("matcher candidate is not an object")
        slug = item.get("slug")
        score = item.get("score")
        rank = item.get("rank")
        if not isinstance(slug, str) or not slug or slug in seen_slugs:
            raise RecognitionUnavailable("matcher candidate slug is invalid")
        if (
            not isinstance(score, (int, float))
            or isinstance(score, bool)
            or not math.isfinite(float(score))
        ):
            raise RecognitionUnavailable("matcher candidate score is invalid")
        if rank != expected_rank or isinstance(rank, bool) or float(score) > previous_score:
            raise RecognitionUnavailable("matcher candidate order is invalid")
        try:
            wine = wine_from_card(slug, item.get("wine"))
        except (TypeError, ValueError) as exc:
            raise RecognitionUnavailable("matcher candidate wine card is invalid") from exc
        candidates.append(
            RecognitionCandidate(slug=slug, score=float(score), rank=expected_rank, wine=wine)
        )
        seen_slugs.add(slug)
        previous_score = float(score)
    return RecognitionResult(tuple(candidates), pipeline)


def is_confident(
    result: RecognitionResult,
    *,
    min_score: float,
    min_margin: float,
) -> bool:
    if not result.candidates:
        return False
    return result.top.score >= min_score and result.margin >= min_margin


class Matcher:
    def __init__(self, endpoint: str, client: httpx.AsyncClient) -> None:
        self._endpoint = endpoint
        self._client = client

    async def recognize(self, body: bytes) -> RecognitionResult:
        try:
            response = await self._client.post(
                self._endpoint,
                files={"image": ("telegram-photo.jpg", body, "image/jpeg")},
                params={"k": MATCH_CANDIDATES},
                timeout=180,
            )
            response.raise_for_status()
            return parse_recognition_response(response.json())
        except RecognitionUnavailable:
            raise
        except (httpx.HTTPError, json.JSONDecodeError, TypeError) as exc:
            raise RecognitionUnavailable("matcher is unavailable") from exc
