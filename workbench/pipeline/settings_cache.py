"""Reuse checked settings until the configuration file changes."""

from collections import OrderedDict
from copy import deepcopy
import os
import threading


class SettingsCache:
    """Keep bounded snapshots. Give each caller an independent settings object."""

    def __init__(self, max_entries=8, max_config_bytes=1024 * 1024):
        self.max_entries = max_entries
        self.max_config_bytes = max_config_bytes
        self._entries = OrderedDict()
        self._lock = threading.Lock()

    @staticmethod
    def _signature(path):
        value = os.stat(path)
        return (value.st_dev, value.st_ino, value.st_size,
                value.st_mtime_ns, value.st_ctime_ns)

    def get(self, path, loader):
        """Load current settings. Cache only a read whose file stays equal."""
        return self._read(path, loader, copy_value=True)

    def check(self, path, loader):
        """Validate current settings without exposing or copying a cached object."""
        self._read(path, loader, copy_value=False)

    def _read(self, path, loader, copy_value):
        path = os.path.abspath(path)
        key = (path, loader)
        with self._lock:
            try:
                signature = self._signature(path)
            except OSError:
                self._entries.pop(key, None)
                value = loader(path)
                return value if copy_value else None
            cached = self._entries.get(key)
            if cached is not None and cached[0] == signature:
                self._entries.move_to_end(key)
                return deepcopy(cached[1]) if copy_value else None
            self._entries.pop(key, None)
            value = loader(path)
            try:
                after = self._signature(path)
            except OSError:
                return value if copy_value else None
            if (after == signature and self.max_entries > 0
                    and after[2] <= self.max_config_bytes):
                self._entries[key] = (after, deepcopy(value))
                while len(self._entries) > self.max_entries:
                    self._entries.popitem(last=False)
            return value if copy_value else None


SETTINGS_CACHE = SettingsCache()
