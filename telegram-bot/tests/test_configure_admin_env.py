import importlib.util
from pathlib import Path


def load_module():
    path = Path(__file__).parents[1] / "deploy" / "configure_admin_env.py"
    spec = importlib.util.spec_from_file_location("configure_admin_env", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_configure_admin_env_replaces_managed_values(tmp_path):
    module = load_module()
    path = tmp_path / "env"
    path.write_text(
        "TELEGRAM_BOT_TOKEN=keep-me\n"
        "BOT_ADMIN_WEB_PASSWORD=old-password-that-is-long\n"
        "BOT_ADMIN_WEB_PORT=9999\n",
        encoding="utf-8",
    )

    module.update_environment(path, "new-password-that-is-long-enough")
    body = path.read_text(encoding="utf-8")

    assert "TELEGRAM_BOT_TOKEN=keep-me" in body
    assert "old-password" not in body
    assert "BOT_ADMIN_WEB_PASSWORD=new-password-that-is-long-enough" in body
    assert "BOT_ADMIN_WEB_PORT=8172" in body
    assert path.stat().st_mode & 0o777 == 0o600
