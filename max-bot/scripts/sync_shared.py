"""Copy the shared modules and tests of telegram-bot into max-bot.

The MAX bot keeps the processing core of the Telegram bot unchanged. This script is the only
place that defines which files are shared and which names change. The test
`tests/test_shared_modules.py` uses the same table to detect a drift.

Usage, from the max-bot directory:

    python scripts/sync_shared.py          # write the copies
    python scripts/sync_shared.py --check  # exit 1 when a copy differs
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

MAX_ROOT = Path(__file__).resolve().parents[1]
TELEGRAM_ROOT = MAX_ROOT.parent / "telegram-bot"

TELEGRAM_PACKAGE = "src/chto_za_vino_bot"
MAX_PACKAGE = "src/chto_za_vino_max_bot"

# Each shared module is the Telegram module after SUBSTITUTIONS. A logic change MUST be made in
# telegram-bot first and then copied with this script.
SHARED_MODULES = (
    "admin_web.py",
    "artifact_backfill.py",
    "data_lifecycle.py",
    "fingerprints.py",
    "host_demo.py",
    "http_api.py",
    "image_types.py",
    "matcher.py",
    "moderation.py",
    "pipeline_artifacts.py",
    "probe.py",
    "quality.py",
    "result_card.py",
    "wine.py",
    "work_queue.py",
)

SHARED_TESTS = (
    "test_artifact_png.py",
    "test_assets.py",
    "test_fingerprint_parity.py",
    "test_fingerprints.py",
    "test_host_demo.py",
    "test_matcher.py",
    "test_moderation.py",
    "test_quality.py",
    "test_quality_performance.py",
    "test_result_card.py",
    "test_wine.py",
    "test_work_queue.py",
)

# The order is significant: the package name changes before the platform name.
SUBSTITUTIONS = (
    ("chto_za_vino_bot", "chto_za_vino_max_bot"),
    ("Telegram", "MAX"),
    ("telegram", "max"),
)


def to_max(text: str) -> str:
    """Return the MAX form of one Telegram source text."""
    for old, new in SUBSTITUTIONS:
        text = text.replace(old, new)
    return text


def shared_pairs() -> list[tuple[Path, Path]]:
    pairs = [
        (TELEGRAM_ROOT / TELEGRAM_PACKAGE / name, MAX_ROOT / MAX_PACKAGE / name)
        for name in SHARED_MODULES
    ]
    pairs += [
        (TELEGRAM_ROOT / "tests" / name, MAX_ROOT / "tests" / name) for name in SHARED_TESTS
    ]
    return pairs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="Report differences only.")
    arguments = parser.parse_args()
    if not TELEGRAM_ROOT.is_dir():
        print(f"telegram-bot is not available at {TELEGRAM_ROOT}", file=sys.stderr)
        return 2
    changed = []
    for source, target in shared_pairs():
        expected = to_max(source.read_text(encoding="utf-8"))
        current = target.read_text(encoding="utf-8") if target.exists() else None
        if current == expected:
            continue
        changed.append(target.relative_to(MAX_ROOT))
        if not arguments.check:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(expected, encoding="utf-8")
    for path in changed:
        print(("differs: " if arguments.check else "updated: ") + str(path))
    return 1 if arguments.check and changed else 0


if __name__ == "__main__":
    raise SystemExit(main())
