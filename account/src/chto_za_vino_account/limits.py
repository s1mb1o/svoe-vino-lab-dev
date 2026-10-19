"""In-process sliding-window limits.

The service runs as one process (plan 03), so memory is enough. A restart clears the windows.
"""

from __future__ import annotations

import math
import threading
from collections import deque
from collections.abc import Callable


class SlidingWindow:
    def __init__(self, limit: int, window_seconds: int, clock: Callable[[], float]) -> None:
        self._limit = limit
        self._window = window_seconds
        self._clock = clock
        self._events: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def retry_after(self, key: str) -> int:
        """Return the seconds to wait, or 0 when the limit allows one more event."""
        now = self._clock()
        with self._lock:
            events = self._events.get(key)
            if not events:
                return 0
            while events and events[0] <= now - self._window:
                events.popleft()
            if len(events) >= self._limit:
                return max(1, math.ceil(events[0] + self._window - now))
            return 0

    def record(self, key: str) -> None:
        now = self._clock()
        with self._lock:
            self._events.setdefault(key, deque()).append(now)
            if len(self._events) > 50_000:
                self._prune(now)

    def _prune(self, now: float) -> None:
        for key in [k for k, v in self._events.items() if not v or v[-1] <= now - self._window]:
            del self._events[key]
