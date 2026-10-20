"""Fixed paths, pooling identities, and atomic campaign records."""
from pathlib import Path
import hashlib
import json
import os
import sys

OUT = Path(__file__).resolve().parent
LAB = OUT.parents[1]
WB = LAB / "workbench"
DB = OUT / "data/catalog/catalog.sqlite3"
NAME = "gx10-siglip2-so400m-patch16-naflex-p512-rot5"
SET = "my-failed-2"
CUTOFF = 1790596800
REMOTE = "/home/ashmelev/.cache/codex-bench/my-failed2-eight-20261017-01a148d5"
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "ashmelev@192.168.86.14"]
PYTHON = "/home/ashmelev/comfyui-env/bin/python"
PROFILES = {
    "pool-bg010": {"background": .1, "bottle": 1., "label": 1.},
    "pool-bg000": {"background": 0., "bottle": 1., "label": 1.},
    "pool-bg010-label2": {"background": .1, "bottle": 1., "label": 2.},
    "pool-bg000-label2": {"background": 0., "bottle": 1., "label": 2.},
}
sys.path.insert(0, str(WB / "pipeline"))


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            h.update(block)
    return h.hexdigest()


def stamp(path):
    os.utime(path, (CUTOFF, CUTOFF))


def profile_name(profile):
    return "exp-my-failed2-" + profile


def install_pooling_identity():
    import embeddings
    if getattr(embeddings, "_campaign_pooling_identity", False):
        return
    original = embeddings.Embedding.view_config_hash
    def hashed(self, view, role="full"):
        base = original(self, view, role)
        profile = next((v for k, v in PROFILES.items() if profile_name(k) == self.name), None)
        return embeddings.sha256_json({"base": base, "native_attention_pooling": profile, "version": 1}) if profile else base
    embeddings.Embedding.view_config_hash = hashed
    embeddings._campaign_pooling_identity = True
