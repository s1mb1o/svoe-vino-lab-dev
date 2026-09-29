"""Persist submitted images and request metadata for matcher audit."""

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path


IMAGE_SUFFIXES = frozenset({
    ".avif", ".bmp", ".gif", ".heic", ".jpeg", ".jpg", ".png", ".tif", ".tiff",
    ".webp",
})
SENSITIVE_HEADERS = frozenset({
    "authorization", "cookie", "proxy-authorization", "x-api-key", "x-auth-token",
})


@dataclass(frozen=True)
class SavedImage:
    """One archived request image."""

    directory: Path
    path: Path
    relative_path: str
    sha256: str
    size_bytes: int


def safe_headers(raw_headers):
    """Return all request headers and redact secret values."""
    headers = []
    for raw_name, raw_value in raw_headers:
        name = raw_name.decode("latin-1")
        value = raw_value.decode("latin-1")
        if name.lower() in SENSITIVE_HEADERS:
            value = "<redacted>"
        headers.append({"name": name, "value": value})
    return headers


class RequestArchive:
    """Write one private directory for each submitted image."""

    def __init__(self, root):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not self.root.is_dir():
            raise RuntimeError("matcher output path is not a directory: %s" % self.root)

    def save_image(self, request_id, received_at, filename, body):
        """Save image bytes and return their audit properties."""
        directory = self.root / received_at.strftime("%Y-%m-%d") / request_id
        directory.mkdir(mode=0o700, parents=True, exist_ok=False)
        suffix = Path(filename or "").suffix.lower()
        if suffix not in IMAGE_SUFFIXES:
            suffix = ".bin"
        path = directory / ("image" + suffix)
        self._write_private(path, body)
        return SavedImage(
            directory=directory,
            path=path,
            relative_path=path.relative_to(self.root).as_posix(),
            sha256=hashlib.sha256(body).hexdigest(),
            size_bytes=len(body),
        )

    def save_record(self, saved_image, record):
        """Save the JSON metadata beside its archived image."""
        path = saved_image.directory / "request.json"
        body = (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        self._write_private(path, body)
        return path

    @staticmethod
    def _write_private(path, body):
        temporary = path.with_name(".%s.tmp" % path.name)
        temporary.write_bytes(body)
        temporary.chmod(0o600)
        os.replace(temporary, path)
