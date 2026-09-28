from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import httpx

from .matcher import Matcher, is_confident
from .moderation import Moderator, make_moderation_jpeg
from .quality import QualityInspector, QualityThresholds


async def run(args: argparse.Namespace) -> None:
    body = args.image.read_bytes()
    async with httpx.AsyncClient() as client:
        moderation_jpeg = make_moderation_jpeg(body)
        moderation = await Moderator(args.moderation_endpoint, client).classify(moderation_jpeg)
        result: dict[str, object] = {
            "moderation": {
                "safe": moderation.safe,
                "category": moderation.category,
                "confidence": moderation.confidence,
                "reason": moderation.reason,
                "scores": moderation.scores,
            }
        }
        if moderation.safe and not args.moderation_only:
            quality = await QualityInspector(
                args.sam3_endpoint,
                client,
                QualityThresholds(
                    blur_min_variance=args.blur_min_variance,
                    glare_max_ratio=args.glare_max_ratio,
                    bottle_min_area_ratio=args.bottle_min_area_ratio,
                    label_min_area_ratio=args.label_min_area_ratio,
                ),
            ).inspect(moderation_jpeg)
            result["quality"] = {
                "acceptable": quality.acceptable,
                "issues": quality.issues,
                "blur_variance": quality.blur_variance,
                "glare_ratio": quality.glare_ratio,
                "bottle_area_ratio": quality.bottle_area_ratio,
                "label_area_ratio": quality.label_area_ratio,
            }
            if not quality.acceptable:
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return
            recognition = await Matcher(args.matcher_endpoint, client).recognize(body)
            result["recognition"] = {
                "pipeline": recognition.pipeline,
                "margin": recognition.margin,
                "confident": is_confident(
                    recognition,
                    min_score=args.match_min_score,
                    min_margin=args.match_min_margin,
                ),
                "candidates": [
                    {
                        "rank": candidate.rank,
                        "slug": candidate.slug,
                        "name": candidate.wine.name,
                        "page_url": candidate.wine.page_url,
                        "score": candidate.score,
                    }
                    for candidate in recognition.candidates
                ],
            }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe the live moderation and matcher services.")
    parser.add_argument("image", type=Path)
    parser.add_argument(
        "--moderation-endpoint",
        default="http://127.0.0.1:18081/upstream/shieldgemma-2-4b-it/classify",
    )
    parser.add_argument(
        "--sam3-endpoint",
        default="http://192.168.86.14:18081/upstream/sam3",
    )
    parser.add_argument(
        "--matcher-endpoint",
        default="http://192.168.86.14:28000/v1/match",
    )
    parser.add_argument("--match-min-score", type=float, default=0.70)
    parser.add_argument("--match-min-margin", type=float, default=0.015)
    parser.add_argument("--blur-min-variance", type=float, default=80.0)
    parser.add_argument("--glare-max-ratio", type=float, default=0.20)
    parser.add_argument("--bottle-min-area-ratio", type=float, default=0.10)
    parser.add_argument("--label-min-area-ratio", type=float, default=0.015)
    parser.add_argument("--moderation-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    asyncio.run(run(parse_args()))


if __name__ == "__main__":
    main()
