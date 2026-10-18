from pathlib import Path

from chto_za_vino_core.files import ArtifactStore

RECEIVED_AT = 1_760_000_000  # 2025-10-09 UTC


def test_artifact_store_accepts_a_relative_data_root(tmp_path, monkeypatch):
    # .env.example sets BOT_DATA_ROOT=./data.
    monkeypatch.chdir(tmp_path)
    store = ArtifactStore(Path("data"))

    relative = store.save("request-1", RECEIVED_AT, "matcher_input", "image/jpeg", b"jpeg")

    assert relative == "artifacts/2025/10/09/request-1/matcher_input.jpg"
    assert (tmp_path / "data" / relative).read_bytes() == b"jpeg"
    assert store.delete_request("request-1") == 1
