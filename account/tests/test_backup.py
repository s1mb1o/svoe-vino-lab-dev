from __future__ import annotations

import sqlite3
import stat

from chto_za_vino_account import cli
from chto_za_vino_account.db import Database


def test_backup_copies_the_live_database(tmp_path, capsys):
    source = tmp_path / "account.sqlite3"
    db = Database(str(source))
    with db.transaction() as connection:
        connection.execute(
            "INSERT INTO users (id, username, created_at, consent_version, consent_at, "
            "terms_version, terms_at) VALUES ('u1', 'anna', 1, 'c', 1, 't', 1)"
        )
    target = tmp_path / "backups" / "account-1.sqlite3"
    assert cli.backup(str(source), str(target)) == 0
    db.close()
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    copy = sqlite3.connect(target)
    assert copy.execute("SELECT username FROM users").fetchall() == [("anna",)]
    copy.close()
    assert capsys.readouterr().out.strip() == str(target)


def test_backup_never_overwrites_and_needs_a_database(tmp_path):
    source = tmp_path / "account.sqlite3"
    Database(str(source)).close()
    target = tmp_path / "copy.sqlite3"
    target.write_text("keep")
    assert cli.backup(str(source), str(target)) == 1
    assert target.read_text() == "keep"
    assert cli.backup(str(tmp_path / "missing.sqlite3"), str(tmp_path / "new.sqlite3")) == 1


def test_concurrent_backups_never_overwrite(tmp_path):
    import threading

    source = tmp_path / "account.sqlite3"
    Database(str(source)).close()
    target = tmp_path / "backups" / "same-name.sqlite3"
    barrier = threading.Barrier(4)
    results: list[int] = []

    def worker() -> None:
        barrier.wait()
        results.append(cli.backup(str(source), str(target)))

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(results) == [0, 1, 1, 1]
    assert target.is_file()
    assert [p.name for p in target.parent.iterdir()] == ["same-name.sqlite3"]


def test_failed_backup_leaves_no_temporary_file(tmp_path):
    source = tmp_path / "not-a-database.sqlite3"
    source.write_bytes(b"this is not sqlite" * 100)
    target = tmp_path / "backups" / "account-x.sqlite3"
    assert cli.backup(str(source), str(target)) == 1
    assert not target.exists()
    assert list(target.parent.iterdir()) == []
