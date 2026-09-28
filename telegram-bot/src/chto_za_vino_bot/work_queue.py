from __future__ import annotations

import asyncio
import logging
import math
import time
from collections.abc import Awaitable, Callable

LOG = logging.getLogger("chto_za_vino_bot.queue")

class QueueCapacityError(RuntimeError):
    pass


class QueueClosedError(RuntimeError):
    pass


class WorkQueue[Job]:
    def __init__(
        self,
        handler: Callable[[Job], Awaitable[None]],
        *,
        worker_count: int,
        capacity: int,
        initial_job_seconds: float = 20.0,
    ) -> None:
        if worker_count <= 0:
            raise ValueError("worker_count must be positive")
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if worker_count > capacity:
            raise ValueError("worker_count must not exceed capacity")
        if initial_job_seconds <= 0:
            raise ValueError("initial_job_seconds must be positive")
        self._handler = handler
        self._worker_count = worker_count
        self._capacity = capacity
        self._queue: asyncio.Queue[Job] = asyncio.Queue()
        self._workers: list[asyncio.Task[None]] = []
        self._active = 0
        self._accepting = False
        self._average_job_seconds = initial_job_seconds

    @property
    def active(self) -> int:
        return self._active

    @property
    def waiting(self) -> int:
        return self._queue.qsize()

    @property
    def depth(self) -> int:
        return self.active + self.waiting

    @property
    def at_capacity(self) -> bool:
        return self.depth >= self._capacity

    @property
    def next_position(self) -> int:
        return self.depth + 1

    def estimate_wait_seconds(self, position: int | None = None) -> int:
        queue_position = self.next_position if position is None else position
        if queue_position <= 0:
            raise ValueError("position must be positive")
        jobs_ahead_of_workers = max(0, queue_position - self._worker_count)
        waves = math.ceil(jobs_ahead_of_workers / self._worker_count)
        return math.ceil(waves * self._average_job_seconds)

    async def start(self) -> None:
        if self._workers:
            return
        self._accepting = True
        self._workers = [
            asyncio.create_task(self._worker(index), name=f"photo-worker-{index + 1}")
            for index in range(self._worker_count)
        ]

    def submit(self, job: Job, *, restore: bool = False) -> None:
        if not self._accepting:
            raise QueueClosedError("queue is not accepting jobs")
        if not restore and self.at_capacity:
            raise QueueCapacityError("queue capacity is full")
        self._queue.put_nowait(job)

    async def wait_idle(self) -> None:
        await self._queue.join()

    async def stop(self) -> None:
        self._accepting = False
        workers = self._workers
        self._workers = []
        for worker in workers:
            worker.cancel()
        if workers:
            await asyncio.gather(*workers, return_exceptions=True)

    async def _worker(self, index: int) -> None:
        LOG.info("Photo queue worker started", extra={"worker": index + 1})
        while True:
            job = await self._queue.get()
            self._active += 1
            started = time.monotonic()
            completed = False
            try:
                await self._handler(job)
                completed = True
            except asyncio.CancelledError:
                raise
            except Exception:
                LOG.exception("Photo queue job failed", extra={"worker": index + 1})
            finally:
                if completed:
                    elapsed = max(0.001, time.monotonic() - started)
                    self._average_job_seconds = 0.8 * self._average_job_seconds + 0.2 * elapsed
                self._active -= 1
                self._queue.task_done()
