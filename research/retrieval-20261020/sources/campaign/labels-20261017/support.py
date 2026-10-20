"""Keep label experiments and service caches inside their private directory."""
from pathlib import Path
import collections
import hashlib
import json
import subprocess
import sys
import time
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from common import OUT, WB, DB as BASE_DB, NAME, SSH, dump, sha, stamp
import alternatives
import bottle_orientation
import build_embeddings
import derive
import embeddings
import embedding_run
import model_cache
from geometry import best_angle, transform
from prepare import foreground

DB = HERE / "data/catalog/catalog.sqlite3"
PROFILES = json.loads((HERE / "profiles.json").read_text())
COUNTS = collections.Counter()
MINIMUM = float("inf")
LAST_GUARD = (0., 0.)


def guard(floor=20):
    global MINIMUM, LAST_GUARD
    if time.monotonic() - LAST_GUARD[0] < 5 and LAST_GUARD[1] >= floor:
        return LAST_GUARD[1]
    value = int(subprocess.check_output(SSH + ["awk '/MemAvailable:/ {print $2}' /proc/meminfo"], text=True)) / 1024**2
    MINIMUM = min(MINIMUM, value)
    LAST_GUARD = (time.monotonic(), value)
    if value < floor:
        raise RuntimeError(f"GPU memory reserve: {value:.2f} GiB available; need {floor} GiB")
    return value


def rgb(image):
    return embeddings.resize(embeddings.on_white(image), {"max_size": 1024, "aspect": "keep", "upscale": False})


def label_turn(image, mask=None):
    mask = mask or foreground(image)
    core = np.asarray(mask) >= 128
    hull = bottle_orientation._hull(core)
    if len(hull) < 3 or core.sum() < 16:
        return image, {"angle": 0., "reason": "empty_or_tiny_mask"}
    angle, aspect = bottle_orientation._angle(hull)
    angle = float((angle + 45) % 90 - 45)
    before = bottle_orientation._bounds(hull, np.array([0.]))
    after = bottle_orientation._bounds(hull, np.array([angle]))
    before_area, after_area = float(before[0][0] * before[1][0]), float(after[0][0] * after[1][0])
    assert after_area <= before_area * (1 + 1e-6)
    # The RGB image already has its segmentation on white. Rotate RGB and mask
    # together. Do not apply the soft alpha to the RGB image a second time.
    result = embeddings.on_white(image)
    if angle:
        result = result.rotate(angle, Image.Resampling.BICUBIC, expand=True, fillcolor="white")
        mask = mask.rotate(angle, Image.Resampling.BICUBIC, expand=True, fillcolor=0)
    box = mask.getbbox()
    result = result.crop(box) if box else result
    return result, {"angle": angle, "axis_aspect": aspect, "mask_area": int(core.sum()),
                    "crop_area_before": before_area, "crop_area_after": after_area,
                    "mask_crop_iou_before": int(core.sum()) / before_area,
                    "mask_crop_iou_after": int(core.sum()) / after_area,
                    "equivalent_orientation_rule": "smallest absolute turn modulo 90 degrees"}


def stage(image):
    data = embeddings.png_bytes(image.convert("RGB"))
    digest = hashlib.sha256(data).hexdigest()
    path = HERE / "model-inputs" / (digest + ".png")
    if not path.exists():
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(data)
        stamp(path)
    return {"path": str(path), "sha256": digest, "size": list(image.size)}


def package(query, item):
    image, _ = derive.open_image(query["abs_path"])
    cuts = embedding_run.cuts_of(image, {"package"}, embedding_run.CachedSam3(), scene_selection=True)
    cut = cuts["package"][1]
    expected = Image.open(OUT / "inputs" / item["image"]).convert("RGB")
    actual = rgb(cut)
    assert expected.size == actual.size and expected.tobytes() == actual.tobytes(), "Frozen bottle pixels changed."
    result = cut.convert("RGBA")
    result.putalpha(foreground(cut))
    return result


class Sam3(derive.Sam3Client):
    def __init__(self, allow_network):
        super().__init__()
        self.allow_network = allow_network

    def _post(self, data, texts=derive.SAM3_TEXTS, return_masks=True):
        form = {"texts": texts, "threshold": str(derive.SAM3_THRESHOLD),
                "mask_threshold": str(derive.SAM3_MASK_THRESHOLD), "return_masks": "true" if return_masks else "false"}
        fields = model_cache.request_fields(self.endpoint + "/segment_multi", derive.SAM3_MODEL,
            {key: value for key, value in form.items() if key != "texts"}, texts, [data])
        key = model_cache.key_of(fields)
        path = HERE / "sam3" / (key + ".json")
        if path.exists():
            record = json.loads(path.read_text())
            assert record["fields"] == fields
            self._last.cached = True
            COUNTS["private_sam3_hits"] += 1
            return record["answer"]
        shared = model_cache.lookup(fields)
        if shared is not None:
            self._last.cached = True
            COUNTS["shared_sam3_hits"] += 1
            return shared["answer"]
        if not self.allow_network:
            raise derive.Sam3Unavailable("Private label input needs a new SAM3 request.")
        guard()
        sent = HERE / "sam3-inputs" / (hashlib.sha256(data).hexdigest() + ".png")
        sent.parent.mkdir(exist_ok=True)
        if not sent.exists():
            sent.write_bytes(data)
            stamp(sent)
        started = time.perf_counter()
        answer = self._send(data, form)
        COUNTS["sam3_requests"] += 1
        COUNTS["sam3_seconds"] += time.perf_counter() - started
        dump(path, {"fields": fields, "answer": answer, "seconds": time.perf_counter() - started})
        self._last.cached = False
        return answer


class Encoder:
    def __init__(self, allow_network):
        self.allow_network = allow_network
        settings = embeddings.load_settings(str(OUT / "config.yaml"))
        self.entry = settings.find(NAME)
        self.model = build_embeddings.OpenAIBackend(self.entry)

    def batch(self, inputs):
        identity = {"endpoint": self.model.url, "model": self.model.model,
                    "extra_body": self.model.extra_body, "images": [r["sha256"] for r in inputs],
                    "batch_size": len(inputs), "recipe": "label7-standard-pooling-v1"}
        key = embeddings.sha256_json(identity)
        path = HERE / "vector-batches" / (key + ".npz")
        if path.exists():
            with np.load(path, allow_pickle=False) as record:
                vectors = record["vectors"]
            COUNTS["batch_cache_inputs"] += len(inputs)
        else:
            if not self.allow_network:
                raise RuntimeError("Label vectors need a new encoder request.")
            guard()
            data = [Path(r["path"]).read_bytes() for r in inputs]
            assert all(hashlib.sha256(raw).hexdigest() == spec["sha256"] for raw, spec in zip(data, inputs))
            started = time.perf_counter()
            vectors = np.asarray(self.model.embed(data), np.float32)
            vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
            COUNTS["encoder_requests"] += 1
            COUNTS["encoder_inputs"] += len(inputs)
            COUNTS["encoder_seconds"] += time.perf_counter() - started
            path.parent.mkdir(exist_ok=True)
            temporary = path.with_suffix(".tmp.npz")
            np.savez_compressed(temporary, vectors=vectors)
            temporary.replace(path)
            dump(path.with_suffix(".json"), identity)
        assert vectors.shape == (len(inputs), 1152) and np.isfinite(vectors).all()
        assert np.all(np.abs(np.linalg.norm(vectors, axis=1) - 1) < .001)
        return vectors


def install_identity():
    original = embeddings.Embedding.view_config_hash
    def hashed(self, view, role="full"):
        base = original(self, view, role)
        if self.name.startswith("exp-my-failed2-label7-"):
            return embeddings.sha256_json({"base": base, "label_geometry": self.name,
                                          "recipe": "label7-standard-pooling-v1"})
        return base
    embeddings.Embedding.view_config_hash = hashed


def checks():
    from PIL import ImageDraw
    image = Image.new("RGBA", (280, 180), (255, 255, 255, 0))
    ImageDraw.Draw(image).rectangle((30, 30, 250, 150), fill=(20, 40, 80, 255))
    values = []
    for angle in (0, 2, 20, 43, 87, 90, 180, 270):
        source = image.rotate(angle, Image.Resampling.NEAREST, expand=True)
        output, audit = label_turn(source)
        assert -45 <= audit["angle"] <= 45
        assert audit["crop_area_after"] <= audit["crop_area_before"] * 1.000001
        assert output.width > 0 and output.height > 0
        values.append({"input_angle": angle, **audit})
    assert len(PROFILES) == 8 and len({tuple(v.values()) for v in PROFILES.values()}) == 8
    dump(HERE / "geometry-checks.json", {"passed": True, "cases": values, "profiles": PROFILES})
