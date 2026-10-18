"""File stores of the bots: accepted and quarantined source images, and pipeline artifacts.

Both bots use the same directory layout under BOT_DATA_ROOT. The database rows stay in the
Repository of each bot.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar

from .image_types import SUPPORTED_IMAGE_TYPES, detect_image_type


@dataclass(frozen=True, slots=True)
class ArtifactRecord:
    artifact_key: str
    step: str
    title: str
    description: str
    mime_type: str
    relative_path: str
    width: int
    height: int
    ordinal: int
    metadata_json: str
    created_at: int
    exposure: str


@dataclass(frozen=True, slots=True)
class ArtifactWrite:
    artifact_key: str
    step: str
    title: str
    description: str
    mime_type: str
    relative_path: str
    width: int
    height: int
    ordinal: int
    metadata: dict[str, object]
    exposure: str = "safe"


def _request_path_name(request_id: str) -> str:
    if request_id in {"", ".", ".."} or Path(request_id).name != request_id:
        raise ValueError("request ID is not a valid path name")
    return request_id


class ImageStore:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._accepted = root / "accepted"
        self._quarantine = root / "quarantine"
        self._accepted.mkdir(parents=True, exist_ok=True, mode=0o750)
        self._quarantine.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self._quarantine, 0o700)

    def save(self, request_id: str, received_at: int, body: bytes, safe: bool) -> tuple[str, str]:
        image_type = detect_image_type(body)
        date = datetime.fromtimestamp(received_at, tz=UTC)
        base = self._accepted if safe else self._quarantine
        directory = base / date.strftime("%Y/%m/%d")
        directory.mkdir(parents=True, exist_ok=True, mode=0o750 if safe else 0o700)
        if not safe:
            os.chmod(directory, 0o700)
        final = directory / f"{request_id}.{image_type.extension}"
        temporary = directory / f".{request_id}.{uuid.uuid4().hex}.tmp"
        with temporary.open("xb") as target:
            target.write(body)
            target.flush()
            os.fsync(target.fileno())
        os.chmod(temporary, 0o640 if safe else 0o600)
        os.replace(temporary, final)
        relative = final.relative_to(self._root).as_posix()
        return relative, hashlib.sha256(body).hexdigest()

    def delete_accepted(self, request_id: str) -> int:
        """Delete the accepted copies of one request. Earlier attempts can use other dates."""
        name = _request_path_name(request_id)
        deleted = 0
        for directory in self._accepted.glob("*/*/*"):
            if not directory.is_dir():
                continue
            for image_type in SUPPORTED_IMAGE_TYPES.values():
                try:
                    (directory / f"{name}.{image_type.extension}").unlink()
                except FileNotFoundError:
                    continue
                deleted += 1
        return deleted

    def read_accepted(self, relative_path: str) -> bytes:
        return self._read_within(relative_path, self._accepted, "accepted")

    def read_quarantine(self, relative_path: str) -> bytes:
        return self._read_within(relative_path, self._quarantine, "quarantine")

    def _read_within(self, relative_path: str, root: Path, label: str) -> bytes:
        candidate = (self._root / relative_path).resolve()
        resolved_root = root.resolve()
        if candidate == resolved_root or resolved_root not in candidate.parents:
            raise ValueError(f"{label} image path is invalid")
        return candidate.read_bytes()


class ArtifactStore:
    _KEY = re.compile(r"^[a-z0-9][a-z0-9_-]{0,79}$")
    _EXTENSIONS: ClassVar[dict[str, str]] = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
    }

    def __init__(self, root: Path) -> None:
        self._data_root = root.resolve()
        # save() returns a path relative to _data_root, so _root must be absolute too.
        self._root = self._data_root / "artifacts"
        self._root.mkdir(parents=True, exist_ok=True, mode=0o750)

    def save(
        self,
        request_id: str,
        received_at: int,
        artifact_key: str,
        mime_type: str,
        body: bytes,
    ) -> str:
        if not self._KEY.fullmatch(artifact_key):
            raise ValueError("artifact key is invalid")
        extension = self._EXTENSIONS.get(mime_type)
        if extension is None:
            raise ValueError("artifact MIME type is invalid")
        date = datetime.fromtimestamp(received_at, tz=UTC)
        directory = self._root / date.strftime("%Y/%m/%d") / request_id
        directory.mkdir(parents=True, exist_ok=True, mode=0o750)
        final = directory / f"{artifact_key}.{extension}"
        temporary = directory / f".{artifact_key}.{uuid.uuid4().hex}.tmp"
        with temporary.open("xb") as target:
            target.write(body)
            target.flush()
            os.fsync(target.fileno())
        os.chmod(temporary, 0o640)
        os.replace(temporary, final)
        return final.relative_to(self._data_root).as_posix()

    def delete_request(self, request_id: str) -> int:
        """Delete the artifact directories of one request. Earlier attempts can use other dates."""
        name = _request_path_name(request_id)
        deleted = 0
        for directory in self._root.glob("*/*/*"):
            candidate = directory / name
            if candidate.is_dir():
                shutil.rmtree(candidate)
                deleted += 1
        return deleted

    def resolve(self, relative_path: str) -> Path:
        candidate = (self._data_root / relative_path).resolve()
        root = self._root.resolve()
        if candidate == root or root not in candidate.parents:
            raise ValueError("artifact path is invalid")
        return candidate
