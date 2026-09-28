import asyncio

import pytest

from chto_za_vino_bot.work_queue import QueueCapacityError, WorkQueue


async def test_queue_processes_jobs_in_fifo_order():
    processed: list[int] = []

    async def process(value: int) -> None:
        processed.append(value)

    queue = WorkQueue(process, worker_count=1, capacity=10)
    await queue.start()
    queue.submit(1)
    queue.submit(2)
    queue.submit(3)

    await queue.wait_idle()
    await queue.stop()

    assert processed == [1, 2, 3]
    assert queue.active == 0
    assert queue.waiting == 0


async def test_queue_enforces_total_capacity():
    started = asyncio.Event()
    release = asyncio.Event()

    async def process(value: int) -> None:
        started.set()
        await release.wait()

    queue = WorkQueue(process, worker_count=1, capacity=2)
    await queue.start()
    queue.submit(1)
    await started.wait()
    queue.submit(2)

    with pytest.raises(QueueCapacityError):
        queue.submit(3)

    assert queue.active == 1
    assert queue.waiting == 1
    release.set()
    await queue.wait_idle()
    await queue.stop()


async def test_queue_worker_continues_after_job_failure():
    processed: list[int] = []

    async def process(value: int) -> None:
        if value == 1:
            raise RuntimeError("test failure")
        processed.append(value)

    queue = WorkQueue(process, worker_count=1, capacity=10)
    await queue.start()
    queue.submit(1)
    queue.submit(2)

    await queue.wait_idle()
    await queue.stop()

    assert processed == [2]


def test_queue_estimates_wait_by_worker_wave():
    async def process(value: int) -> None:
        return None

    queue = WorkQueue(process, worker_count=2, capacity=10, initial_job_seconds=20)

    assert queue.estimate_wait_seconds(1) == 0
    assert queue.estimate_wait_seconds(2) == 0
    assert queue.estimate_wait_seconds(3) == 20
    assert queue.estimate_wait_seconds(5) == 40
