"""Reuse bounded read results while every source identity stays equal."""
from collections import OrderedDict
from copy import deepcopy
from concurrent.futures import Future
import os
import sys
import threading


def signature(path):
    """Detect writes, replacement, and directory membership changes."""
    value = os.stat(path)
    return (value.st_dev, value.st_ino, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns)


def _size(value, seen=None):
    seen = set() if seen is None else seen
    if id(value) in seen:
        return 0
    seen.add(id(value))
    total = sys.getsizeof(value)
    if isinstance(value, dict):
        total += sum(_size(k, seen) + _size(v, seen) for k, v in value.items())
    elif isinstance(value, (list, tuple, set, frozenset)):
        total += sum(_size(v, seen) for v in value)
    return total


class ReadFlights:
    """Share in-progress reads, with bounded ownership and no global loader lock."""

    def __init__(self, max_pending=32):
        self.max_pending = max_pending
        self._pending = {}
        self._lock = threading.Lock()

    def run(self, key, loader):
        owner = threading.get_ident()
        with self._lock:
            item = self._pending.get(key)
            if item is not None and item[1] != owner:
                future, _ = item
                lead = False
            elif item is not None or len(self._pending) >= self.max_pending:
                future = None
                lead = True
            else:
                future = Future()
                self._pending[key] = (future, owner)
                lead = True
        if not lead:
            return future.result()
        if future is None:
            return loader()
        try:
            value = loader()
        except BaseException as exc:
            future.set_exception(exc)
            raise
        else:
            future.set_result(value)
            return value
        finally:
            with self._lock:
                self._pending.pop(key, None)


class CheckedReadCache:
    """Keep an LRU with entry and byte limits. Do not cache failed or unstable reads."""

    def __init__(self, max_entries=8, max_bytes=32 * 1024 * 1024):
        self.max_entries, self.max_bytes = max_entries, max_bytes
        self._entries = OrderedDict()
        self._bytes = 0
        self._lock = threading.Lock()
        self._epoch = 0
        self._flights = ReadFlights()

    def clear(self):
        with self._lock:
            self._epoch += 1
            self._entries.clear()
            self._bytes = 0

    def _remove(self, key):
        entry = self._entries.pop(key, None)
        if entry is not None:
            self._bytes -= entry[2]

    def get(self, key, paths, loader, *, copy_value=True):
        """Give an independent value by default. A read-only caller MAY borrow it."""
        paths = tuple(paths)
        def state():
            try:
                return tuple(signature(path) for path in paths)
            except OSError:
                return None

        before = state()
        with self._lock:
            epoch = self._epoch
        value = self._flights.run((key, before, epoch, copy_value),
                                 lambda: self._get(key, state, loader, copy_value, epoch))
        return deepcopy(value) if copy_value else value

    def _get(self, key, state, loader, copy_value, epoch):
        before = state()
        with self._lock:
            cached = self._entries.get(key)
            if before is not None and cached is not None and cached[0] == before:
                self._entries.move_to_end(key)
                value = cached[1]
                if state() == before:
                    return value
            self._remove(key)
        # Load outside the lock. A slow image read MUST NOT block unrelated hits.
        value = loader()
        if before is None or state() != before or self.max_entries <= 0:
            return value
        size = _size(value)
        if size > self.max_bytes:
            return value
        stored = deepcopy(value) if copy_value else value
        with self._lock:
            if self._epoch != epoch or state() != before:
                return value
            self._remove(key)
            self._entries[key] = (before, stored, size)
            self._bytes += size
            while len(self._entries) > self.max_entries or self._bytes > self.max_bytes:
                oldest = next(iter(self._entries))
                self._remove(oldest)
        return value
