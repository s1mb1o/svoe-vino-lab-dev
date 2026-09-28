"""Create self-contained model tarballs from a Hugging Face cache."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tarfile
from datetime import UTC, datetime
from pathlib import Path


MODELS = {
    "facebook/sam3": "facebook--sam3",
    "google/shieldgemma-2-4b-it": "google--shieldgemma-2-4b-it",
    "google/siglip2-so400m-patch16-naflex": "google--siglip2-so400m-patch16-naflex",
    "google/siglip2-so400m-patch16-512": "google--siglip2-so400m-patch16-512",
}


WEIGHT_SUFFIXES = (".safetensors", ".bin", ".pt", ".pth")


def snapshot(cache: Path, model_id: str) -> tuple[Path, str]:
    repository = cache / f"models--{model_id.replace('/', '--')}"
    reference = repository / "refs" / "main"
    if reference.is_file():
        revision = reference.read_text(encoding="utf-8").strip()
        candidate = repository / "snapshots" / revision
        if candidate.is_dir():
            validate_snapshot(candidate, model_id)
            return candidate, revision
    candidates = sorted((repository / "snapshots").glob("*"))
    candidates = [candidate for candidate in candidates if candidate.is_dir()]
    if len(candidates) != 1:
        raise FileNotFoundError(
            f"cannot select one local snapshot for {model_id} in {repository}"
        )
    validate_snapshot(candidates[0], model_id)
    return candidates[0], candidates[0].name


def validate_snapshot(path: Path, model_id: str) -> None:
    """Reject a metadata-only or interrupted cache snapshot."""
    weights = [
        item
        for item in path.rglob("*")
        if item.is_file() and item.name.endswith(WEIGHT_SUFFIXES)
    ]
    if not weights:
        raise ValueError(f"snapshot for {model_id} has no model weight file: {path}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def create_archive(source: Path, archive: Path, slug: str) -> None:
    temporary = archive.with_suffix(archive.suffix + ".partial")
    if archive.exists() or temporary.exists():
        raise FileExistsError(f"refusing to overwrite {archive} or {temporary}")
    try:
        with tarfile.open(temporary, "w", dereference=True) as output:
            output.add(source, arcname=slug, recursive=True)
        temporary.chmod(0o600)
        os.replace(temporary, archive)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True, help="Hugging Face hub cache")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", action="append", choices=sorted(MODELS))
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    arguments.output.mkdir(parents=True, exist_ok=True)
    selected = arguments.model or list(MODELS)
    bundles = []
    for model_id in selected:
        slug = MODELS[model_id]
        source, revision = snapshot(arguments.cache.resolve(), model_id)
        archive = arguments.output / f"{slug}.tar"
        print(f"Creating {archive} from {source}", flush=True)
        create_archive(source, archive, slug)
        bundles.append(
            {
                "model_id": model_id,
                "revision": revision,
                "directory": slug,
                "archive": archive.name,
                "bytes": archive.stat().st_size,
                "sha256": sha256(archive),
            }
        )
    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "bundles": bundles,
    }
    manifest_path = arguments.output / "manifest.json"
    temporary = manifest_path.with_suffix(".json.partial")
    temporary.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, manifest_path)
    print(f"Wrote {manifest_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
