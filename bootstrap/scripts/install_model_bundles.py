"""Verify and install offline model tarballs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import shutil
import tarfile
import uuid
from pathlib import Path
from typing import Any


def _interrupt(signum: int, frame: object) -> None:
    """Enter the normal exception path so an interrupted install removes its temporary directory."""
    raise KeyboardInterrupt(f"received signal {signum}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def validate_members(archive: tarfile.TarFile, directory: str) -> None:
    prefix = directory + "/"
    for member in archive.getmembers():
        if member.name != directory and not member.name.startswith(prefix):
            raise ValueError(f"archive member is outside {directory}: {member.name}")
        path = Path(member.name)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"unsafe archive member: {member.name}")
        if member.issym() or member.islnk() or member.isdev():
            raise ValueError(f"archive member is not a regular file or directory: {member.name}")


def install(bundle_dir: Path, model_root: Path, entry: dict[str, Any]) -> str:
    archive_path = bundle_dir / entry["archive"]
    print(f"{entry['model_id']}: verifying {archive_path.name}", flush=True)
    if archive_path.stat().st_size != entry["bytes"]:
        raise ValueError(f"archive size mismatch: {archive_path}")
    actual_sha = sha256(archive_path)
    if actual_sha != entry["sha256"]:
        raise ValueError(f"archive SHA-256 mismatch: {archive_path}")

    destination = model_root / entry["directory"]
    marker = destination / ".bootstrap-bundle.json"
    if destination.exists():
        if marker.is_file():
            installed = json.loads(marker.read_text(encoding="utf-8"))
            if installed.get("sha256") == actual_sha:
                return "already-installed"
        raise FileExistsError(f"refusing to replace existing model directory {destination}")

    temporary = model_root / f".install-{entry['directory']}-{uuid.uuid4().hex}"
    temporary.mkdir(parents=True)
    try:
        print(f"{entry['model_id']}: extracting into a temporary directory", flush=True)
        with tarfile.open(archive_path, "r") as archive:
            validate_members(archive, entry["directory"])
            archive.extractall(temporary, filter="data")
        extracted = temporary / entry["directory"]
        if not extracted.is_dir():
            raise ValueError(f"archive did not create {entry['directory']}")
        marker_data = dict(entry, installed_from=str(archive_path.resolve()))
        (extracted / ".bootstrap-bundle.json").write_text(
            json.dumps(marker_data, indent=2) + "\n", encoding="utf-8"
        )
        os.replace(extracted, destination)
    finally:
        shutil.rmtree(temporary, ignore_errors=True)
    return "installed"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundles", type=Path, required=True)
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--model", action="append", help="install only this model ID")
    return parser.parse_args()


def select_entries(manifest: dict[str, Any], requested: list[str] | None) -> list[dict[str, Any]]:
    """Return all entries when no model was requested, or the exact requested subset."""
    selected = set(requested or [])
    entries = [
        entry
        for entry in manifest["bundles"]
        if not selected or entry["model_id"] in selected
    ]
    found = {entry["model_id"] for entry in entries}
    if selected and selected != found:
        raise ValueError(f"models are absent from manifest: {sorted(selected - found)}")
    return entries


def main() -> int:
    signal.signal(signal.SIGTERM, _interrupt)
    if hasattr(signal, "SIGHUP"):
        signal.signal(signal.SIGHUP, _interrupt)
    arguments = parse_args()
    bundle_dir = arguments.bundles.resolve()
    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise ValueError("unsupported model bundle manifest schema")
    entries = select_entries(manifest, arguments.model)
    arguments.model_root.mkdir(parents=True, exist_ok=True)
    for entry in entries:
        status = install(bundle_dir, arguments.model_root.resolve(), entry)
        print(f"{entry['model_id']}: {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
