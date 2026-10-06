"""Reuse job status while log files, lock files, and runner identity stay equal."""

from collections import OrderedDict
import os
import sys
import threading


class JobStatusCache:
    """Cache completed status reads. Check the runner on every request."""

    def __init__(self, max_entries=256, max_entry_bytes=64 * 1024):
        self.max_entries = max_entries
        self.max_entry_bytes = max_entry_bytes
        self._entries = OrderedDict()
        self._lock = threading.Lock()

    @staticmethod
    def _files(directory, filenames):
        values = []
        for name in filenames:
            try:
                state = os.stat(os.path.join(directory, name))
            except FileNotFoundError:
                values.append(None)
            else:
                values.append((state.st_dev, state.st_ino, state.st_size,
                               state.st_mtime_ns, state.st_ctime_ns))
        return tuple(values)

    def get(self, directory, read_state, running_pid, filenames):
        """Return a private status dict. Do not cache a read if its inputs change."""
        key = (os.fspath(directory), read_state, tuple(filenames))
        with self._lock:
            try:
                signature = (self._files(directory, filenames), running_pid(directory))
            except OSError:
                self._entries.pop(key, None)
                return read_state(directory)
            cached = self._entries.get(key)
            if cached is not None and cached[0] == signature:
                self._entries.move_to_end(key)
                return dict(cached[1])
            value = read_state(directory)
            try:
                after = (self._files(directory, filenames), running_pid(directory))
            except OSError:
                self._entries.pop(key, None)
                return value
            if (signature == after and value.get("pid") == after[1]
                    and self.max_entries > 0 and self._cacheable(value)):
                self._entries[key] = (after, dict(value))
                self._entries.move_to_end(key)
                while len(self._entries) > self.max_entries:
                    self._entries.popitem(last=False)
            else:
                self._entries.pop(key, None)
            return value

    def _cacheable(self, value):
        # Status fields are scalar values. Do not retain large diagnostic messages.
        if not all(isinstance(item, (str, int, float, bool, type(None)))
                   for item in value.values()):
            return False
        size = sys.getsizeof(value) + sum(sys.getsizeof(key) + sys.getsizeof(item)
                                         for key, item in value.items())
        return size <= self.max_entry_bytes


STATUS_CACHE = JobStatusCache()
