from chto_za_vino_max_bot import probe


def test_probe_command_uses_the_bot_upload_name(monkeypatch):
    calls = []
    monkeypatch.setattr(probe, "core_main", lambda **kwargs: calls.append(kwargs))

    probe.main()

    assert calls == [{"upload_name": "max-photo"}]
