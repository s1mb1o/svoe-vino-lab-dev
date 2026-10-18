from chto_za_vino_core import probe


def test_probe_passes_the_upload_name_to_the_run(monkeypatch):
    calls = []

    async def run(args, upload_name):
        calls.append((args, upload_name))

    monkeypatch.setattr(probe, "parse_args", lambda: "arguments")
    monkeypatch.setattr(probe, "run", run)

    probe.main(upload_name="max-photo")

    assert calls == [("arguments", "max-photo")]
