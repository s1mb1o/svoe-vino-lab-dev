"""Check that image processing runs outside the bot event-loop thread."""

import threading

import httpx
import pytest
from chto_za_vino_core import result_card
from test_processor_quality import AdvisoryQualityInspector, jpeg, run_processor

from chto_za_vino_max_bot import app


@pytest.mark.parametrize(
    "name",
    [
        "make_moderation_jpeg",
        "image_hashes",
        "base_artifacts",
        "quality_artifacts",
        "normalize_result_photo",
        "result_artifact",
    ],
)
async def test_processor_dispatches_image_cpu_work(tmp_path, monkeypatch, name):
    original = getattr(app, name)
    worker_ids = []

    def checked(*args, **kwargs):
        worker_ids.append(threading.get_ident())
        return original(*args, **kwargs)

    monkeypatch.setattr(app, name, checked)
    row, _, _, photos, _ = await run_processor(tmp_path, AdvisoryQualityInspector())
    assert row[0] == "recognized"
    assert len(photos) == 1
    assert worker_ids
    assert all(identifier != threading.get_ident() for identifier in worker_ids)


async def test_catalogue_result_preparation_runs_outside_event_loop(monkeypatch):
    original = result_card.prepare_catalog_result_photo
    worker_ids = []

    def checked(body):
        worker_ids.append(threading.get_ident())
        return original(body)

    monkeypatch.setattr(result_card, "prepare_catalog_result_photo", checked)
    body = jpeg()
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=body))
    async with httpx.AsyncClient(transport=transport) as client:
        prepared = await result_card.CatalogImageLoader(client).fetch(
            "https://api.vino-svoe.ru/uploads/test.jpg"
        )
    assert prepared == original(body)
    assert worker_ids == [worker_ids[0]]
    assert worker_ids[0] != threading.get_ident()
