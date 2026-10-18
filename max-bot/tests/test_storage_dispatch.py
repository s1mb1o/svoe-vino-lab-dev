"""Check persistence threads, moderation order, and cancellation barriers."""

import asyncio
import threading

import pytest
from chto_za_vino_core.files import ArtifactStore, ImageStore
from fakes import image
from test_processor_quality import (
    PHOTO,
    SOURCE_MID,
    AdvisoryQualityInspector,
    MediaMaxApi,
    UnsafeModerator,
    jpeg,
    max_message,
    run_processor,
)

from chto_za_vino_max_bot.app import PhotoProcessor
from chto_za_vino_max_bot.max_api import MediaUnavailable
from chto_za_vino_max_bot.storage import Repository
from chto_za_vino_max_bot.updates import ImageRef


@pytest.mark.parametrize(
    ("store_class", "method"),
    [
        (ImageStore, "save"),
        (ArtifactStore, "save"),
        (Repository, "update"),
        (Repository, "record_step_timing"),
        (Repository, "replace_candidates"),
        (Repository, "replace_artifacts"),
        (Repository, "upsert_artifacts"),
        (Repository, "record_sent_message"),
    ],
)
async def test_photo_persistence_runs_outside_event_loop(tmp_path, monkeypatch, store_class, method):
    original = getattr(store_class, method)
    threads = []

    def checked(self, *args, **kwargs):
        threads.append(threading.get_ident())
        return original(self, *args, **kwargs)

    monkeypatch.setattr(store_class, method, checked)
    row, _, _, photos, artifacts = await run_processor(tmp_path, AdvisoryQualityInspector())
    assert row[0] == "recognized"
    assert photos and artifacts
    assert threads
    assert all(identifier != threading.get_ident() for identifier in threads)


async def test_moderation_precedes_image_writes_and_unsafe_cleanup(tmp_path, monkeypatch):
    approved = False
    events = []
    original_image = ImageStore.save
    original_artifact = ArtifactStore.save
    original_delete = ImageStore.delete_accepted
    original_delete_artifacts = ArtifactStore.delete_request

    class Moderator(UnsafeModerator):
        async def classify(self, body):
            nonlocal approved
            result = await super().classify(body)
            approved = True
            events.append("moderated")
            return result

    def image(self, *args):
        assert approved
        assert threading.get_ident() != loop_thread
        assert args[-1] is False
        events.append("quarantine")
        return original_image(self, *args)

    def artifact(self, *args):
        assert approved
        assert threading.get_ident() != loop_thread
        assert args[2] == "censored_preview"
        events.append("censored")
        return original_artifact(self, *args)

    def delete(self, *args):
        assert threading.get_ident() != loop_thread
        events.append("delete_accepted")
        return original_delete(self, *args)

    def delete_artifacts(self, *args):
        assert threading.get_ident() != loop_thread
        events.append("delete_artifacts")
        return original_delete_artifacts(self, *args)

    loop_thread = threading.get_ident()
    monkeypatch.setattr(ImageStore, "save", image)
    monkeypatch.setattr(ArtifactStore, "save", artifact)
    monkeypatch.setattr(ImageStore, "delete_accepted", delete)
    monkeypatch.setattr(ArtifactStore, "delete_request", delete_artifacts)
    row, _, calls, _, artifacts = await run_processor(
        tmp_path, AdvisoryQualityInspector(), moderator=Moderator(),
    )
    assert row[0] == "quarantined"
    assert calls == 0
    assert len(artifacts) == 1
    assert events == ["moderated", "quarantine", "delete_accepted", "delete_artifacts", "censored"]


async def test_slow_fsync_keeps_loop_responsive_and_final_file_atomic(tmp_path, monkeypatch):
    # The file stores of the core write and synchronize the photo files.
    from chto_za_vino_core import files

    original = files.os.fsync
    started = asyncio.Event()
    release = threading.Event()
    loop = asyncio.get_running_loop()
    first = True

    def blocked(descriptor):
        nonlocal first
        if first:
            first = False
            loop.call_soon_threadsafe(started.set)
            if not release.wait(2):
                raise TimeoutError("Test did not release fsync")
        return original(descriptor)

    monkeypatch.setattr(files.os, "fsync", blocked)
    task = asyncio.create_task(run_processor(tmp_path, AdvisoryQualityInspector()))
    try:
        await asyncio.wait_for(started.wait(), 1)
        await asyncio.sleep(0)
        assert not task.done()
        accepted = tmp_path / "images" / "accepted"
        assert list(accepted.rglob("*.tmp"))
        assert not list(accepted.rglob("*.jpg"))
    finally:
        release.set()
        row, _, _, _, _ = await task
    assert row[0] == "recognized"
    assert len(list(accepted.rglob("*.jpg"))) == 1
    assert not list(accepted.rglob("*.tmp"))


async def test_cancelled_write_finishes_before_next_persistence_operation():
    processor = PhotoProcessor(None, None)
    started = asyncio.Event()
    release = threading.Event()
    loop = asyncio.get_running_loop()
    events = []

    def first():
        events.append("first_started")
        loop.call_soon_threadsafe(started.set)
        if not release.wait(2):
            raise TimeoutError("Test did not release persistence")
        events.append("first_finished")

    def second():
        events.append("second_started")
        return "ok"

    writer = asyncio.create_task(processor._persist(first))
    await asyncio.wait_for(started.wait(), 1)
    successor = asyncio.create_task(processor._persist(second))
    try:
        writer.cancel()
        await asyncio.sleep(0)
        writer.cancel()
        await asyncio.sleep(0)
        assert not writer.done()
        assert not successor.done()
        assert events == ["first_started"]
    finally:
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await writer
        assert await successor == "ok"
    assert events == ["first_started", "first_finished", "second_started"]


async def test_cancellation_while_waiting_does_not_start_another_write():
    processor = PhotoProcessor(None, None)
    async with processor._persistence_lock:
        calls = []
        task = asyncio.create_task(processor._persist(lambda: calls.append("write")))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert calls == []
    assert await processor._persist(lambda: "next") == "next"


async def test_storage_failure_propagates_and_releases_serialization_lock():
    processor = PhotoProcessor(None, None)

    def fail():
        raise OSError("storage failed")

    with pytest.raises(OSError, match="storage failed"):
        await processor._persist(fail)
    assert await processor._persist(lambda: "next") == "next"


async def test_a_refreshed_photo_url_is_stored_outside_event_loop(tmp_path, monkeypatch):
    # MAX only: the download retry stores the fresh attachment URL.
    original = Repository.set_photo_url
    threads = []

    def checked(self, *args, **kwargs):
        threads.append(threading.get_ident())
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Repository, "set_photo_url", checked)
    fresh = ImageRef(photo_id=PHOTO.photo_id, url=f"{PHOTO.url}?fresh", token=PHOTO.token)
    api = MediaMaxApi()
    api.download_failures[PHOTO.url] = MediaUnavailable("attachment download status 403")
    api.downloads[fresh.url] = jpeg()
    api.messages_by_id[SOURCE_MID] = max_message(fresh, image(2))

    row, *_ = await run_processor(tmp_path, AdvisoryQualityInspector(), api=api)

    assert row[0] == "recognized"
    assert threads
    assert all(identifier != threading.get_ident() for identifier in threads)
