"""Negotiate gzip and reuse bounded compressed variants of immutable JSON bytes."""
from collections import OrderedDict
import gzip
import threading


def accepts_gzip(header):
    choices = {}
    for entry in header.split(","):
        fields = [field.strip() for field in entry.split(";")]
        name = fields[0].lower()
        quality = 1.0
        for field in fields[1:]:
            if field.lower().startswith("q="):
                try:
                    quality = float(field[2:])
                except ValueError:
                    quality = 0.0
        choices[name] = quality if 0 <= quality <= 1 else 0.0
    return choices.get("gzip", choices.get("*", 0.0)) > 0


class GzipResponseCache:
    """Bound the retained original and compressed bytes. Changed bytes get a new key."""

    def __init__(self, max_entries=8, max_bytes=48 * 1024 * 1024):
        self.max_entries, self.max_bytes = max_entries, max_bytes
        self._entries = OrderedDict()
        self._bytes = 0
        self._lock = threading.Lock()

    def get(self, data, accept_encoding):
        if not accepts_gzip(accept_encoding):
            return data, False
        with self._lock:
            saved = self._entries.get(data)
            if saved is not None:
                self._entries.move_to_end(data)
                return saved, True
        compressed = gzip.compress(data, compresslevel=1, mtime=0)
        if len(compressed) >= len(data):
            return data, False
        size = len(data) + len(compressed)
        if size <= self.max_bytes and self.max_entries > 0:
            with self._lock:
                previous = self._entries.pop(data, None)
                if previous is not None:
                    self._bytes -= len(data) + len(previous)
                self._entries[data] = compressed
                self._bytes += size
                while len(self._entries) > self.max_entries or self._bytes > self.max_bytes:
                    original, saved = self._entries.popitem(last=False)
                    self._bytes -= len(original) + len(saved)
        return compressed, True


RESPONSE_CACHE = GzipResponseCache()
