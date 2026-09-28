from __future__ import annotations

import argparse
import asyncio
import logging
import time
from dataclasses import replace

import httpx

from .config import Settings
from .moderation import make_moderation_jpeg, make_moderator
from .pipeline_artifacts import (
    base_artifacts,
    censored_artifact,
    persist_artifacts,
    quality_artifacts,
)
from .quality import QualityInspector, QualityThresholds
from .storage import ArtifactStore, ImageStore, Repository

LOG = logging.getLogger("chto_za_vino_bot.artifact_backfill")


async def reconstruct(request_id: str, settings: Settings) -> int:
    repository = Repository(settings.database_file)
    image_store = ImageStore(settings.data_root)
    artifact_store = ArtifactStore(settings.data_root)
    try:
        safe_source = repository.safe_source(request_id)
        if safe_source is None:
            censored_source = repository.censored_source(request_id)
            if censored_source is None:
                raise RuntimeError("request does not have an artifact source")
            received_at, relative_path = censored_source
            body = image_store.read_quarantine(relative_path)
            generated = [censored_artifact(body)]
        else:
            received_at, relative_path = safe_source
            body = image_store.read_accepted(relative_path)
            moderation_jpeg = make_moderation_jpeg(body)
            async with httpx.AsyncClient() as client:
                moderation = await make_moderator(
                    settings.moderation_enabled,
                    settings.moderation_endpoint,
                    client,
                ).classify(moderation_jpeg)
                if not moderation.accepted:
                    raise RuntimeError("current moderation did not approve the source")
                quality = await QualityInspector(
                    settings.sam3_endpoint,
                    client,
                    QualityThresholds(
                        blur_min_variance=settings.quality_blur_min_variance,
                        glare_max_ratio=settings.quality_glare_max_ratio,
                        bottle_min_area_ratio=settings.quality_bottle_min_area_ratio,
                        label_min_area_ratio=settings.quality_label_min_area_ratio,
                    ),
                ).inspect(moderation_jpeg)
            generated = base_artifacts(body, moderation_jpeg) + quality_artifacts(
                moderation_jpeg,
                quality,
            )
        generated = [
            replace(item, metadata={**item.metadata, "reconstructed": True})
            for item in generated
        ]
        rows = persist_artifacts(
            artifact_store,
            request_id=request_id,
            received_at=received_at,
            artifacts=generated,
        )
        repository.replace_artifacts(request_id, rows, int(time.time()))
        return len(rows)
    finally:
        repository.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reconstruct visual pipeline artifacts without Telegram output."
    )
    parser.add_argument("request_id")
    arguments = parser.parse_args()
    settings = Settings.from_env()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    count = asyncio.run(reconstruct(arguments.request_id, settings))
    print(f"Stored {count} artifacts for request {arguments.request_id}")


if __name__ == "__main__":
    main()
