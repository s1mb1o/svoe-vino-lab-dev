"""Keep fixed paths and atomic records for the retrieval extension."""
from pathlib import Path
import hashlib
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
AXM = ROOT / "axial-matrix-20261018"
AX = ROOT / "axial-20261018"
PYTHON = "/Users/ashmelev/.venvs/svoe-vino-lab/bin/python"
REMOTE_BASE = "/home/ashmelev/.cache/codex-bench/my-failed2-eight-20261017-01a148d5"
REMOTE = REMOTE_BASE + "/retrieval-extensions-20261018"
REMOTE_PYTHON = "/home/ashmelev/comfyui-env/bin/python"
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "ashmelev@192.168.86.14"]
CUTOFF = 1790596800
POOLS = ["u", "5a", "5b", "6a", "6b", "6c", "6d"]
QUERIES = ["original", "iou", "min5", "card5", "crop", "mean-iou", "mean-card5"]
GALLERIES = {"zero": [0], "cardinal": [0, 90, 180, 270], "rot5": list(range(0, 360, 5))}
FOLDERS = {"my": "my-matrix-20261017", "my-failed-2": "matrix-20261017"}

def now():
    return datetime.now(ZoneInfo("Europe/Moscow")).isoformat(timespec="seconds")

def read(path):
    return json.loads(Path(path).read_text())

def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + str(os.getpid()) + ".tmp")
    temp.write_text(json.dumps(value, indent=2) + "\n")
    temp.replace(path)

def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            h.update(block)
    return h.hexdigest()

def profiles():
    result = {"u": dict(uniform=True)}
    for background, bcode in ((.1, "010"), (0., "000")):
        for gamma in (.5, 1., 2.):
            for boost in (1., 1.25, 1.5, 2., 3.):
                # Cross gamma with boost 1 and 2. Isolate the other label boosts at gamma 1.
                if gamma != 1 and boost not in (1., 2.):
                    continue
                key = f"g{gamma:g}-bg{bcode}-l{boost:g}"
                for coverage in ("legacy", "exact"):
                    result[key + "-" + coverage] = dict(background=background, gamma=gamma, boost=boost, coverage=coverage)
    result["6c"] = dict(background=.1, gamma=1., boost=2., coverage="whole")
    result["6d"] = dict(background=0., gamma=1., boost=2., coverage="whole")
    return result

ALIASES = {"u": "u", "5a": "g1-bg010-l1-legacy", "5b": "g1-bg000-l1-legacy",
           "6a": "g1-bg010-l2-legacy", "6b": "g1-bg000-l2-legacy", "6c": "6c", "6d": "6d"}
