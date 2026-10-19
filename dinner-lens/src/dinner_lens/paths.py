"""Locate editable-checkout or installed-wheel reference assets."""
from pathlib import Path
import os
import sys

CURRENT_DATASET = "pairing-dataset.v4.json"
CURRENT_INDEX = "index.v4"


def bundle_root() -> Path:
    checkout = Path(__file__).resolve().parents[2]
    if (checkout / "data" / CURRENT_DATASET).is_file():
        return checkout
    installed = Path(sys.prefix) / "share/svoe-vino-dinner-lens"
    if not (installed / "data" / CURRENT_DATASET).is_file():
        raise RuntimeError("Dinner Lens reference assets are not installed")
    return installed


def default_dataset() -> Path:
    return bundle_root() / "data" / CURRENT_DATASET


def default_style() -> Path:
    return bundle_root() / "prompts/style-guidance.v2.en.json"


def default_index() -> Path:
    checkout = Path(__file__).resolve().parents[2]
    if (checkout / "data" / CURRENT_DATASET).is_file():
        return checkout / "data" / CURRENT_INDEX
    cache = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
    return cache / "svoe-vino-dinner-lens" / CURRENT_INDEX
