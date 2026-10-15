"""The shared modules MUST stay equal to the Telegram modules after the name substitutions.

A logic change belongs in telegram-bot first. Then `python scripts/sync_shared.py` copies it.
The test skips when telegram-bot is absent, for example in a Docker build context.
"""

import importlib.util
from pathlib import Path

import pytest

MAX_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = MAX_ROOT / "scripts" / "sync_shared.py"


def _sync_module():
    spec = importlib.util.spec_from_file_location("sync_shared", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sync_shared = _sync_module()
pytestmark = pytest.mark.skipif(
    not sync_shared.TELEGRAM_ROOT.is_dir(), reason="telegram-bot is not available"
)


@pytest.mark.parametrize(
    ("source", "target"),
    sync_shared.shared_pairs(),
    ids=[target.name for _, target in sync_shared.shared_pairs()],
)
def test_shared_file_matches_the_telegram_file(source, target):
    expected = sync_shared.to_max(source.read_text(encoding="utf-8"))

    assert target.read_text(encoding="utf-8") == expected, (
        f"{target.relative_to(MAX_ROOT)} differs from {source}; "
        "change telegram-bot first, then run scripts/sync_shared.py"
    )


def test_max_transport_modules_are_not_shared():
    shared = set(sync_shared.SHARED_MODULES)

    assert not {"app.py", "storage.py", "config.py", "profile.py", "max_api.py"} & shared
