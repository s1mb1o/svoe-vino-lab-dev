"""JSON-lines local model worker. Offline weights; no hosted inference calls."""
import contextlib
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import sys
import time

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "work/local-comparison"
CHECKPOINT = (Path.home() / ".cache/huggingface/hub/models--google--siglip2-so400m-patch16-naflex"
              / "snapshots/cc24074f717b612951c2dead130904ab9b65a81e")


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


class Engine:
    def __init__(self):
        self.models = {}
        self.conn = sqlite3.connect(RUNTIME / "scores.sqlite3")
        self.conn.execute("CREATE TABLE IF NOT EXISTS score (method TEXT, key TEXT, value TEXT, "
                          "PRIMARY KEY(method,key))")
        self.identity = json.loads((RUNTIME / "identity.json").read_text())
        if (digest(Path(__file__).with_name("local_comparison_models.py")) !=
                self.identity["model_code_sha256"]):
            raise RuntimeError("local model implementation changed; refresh cache identity")
        self.features = {}

    def get(self, method, key, use_cache=True):
        if use_cache:
            row = self.conn.execute("SELECT value FROM score WHERE method=? AND key=?",
                                    (method, key)).fetchone()
            if row:
                value = json.loads(row[0])
                if not value.get("error"):
                    return dict(value, cached=True)
        return None

    def put(self, method, key, value):
        self.conn.execute("INSERT OR REPLACE INTO score VALUES (?,?,?)",
                          (method, key, json.dumps(value, allow_nan=False)))
        self.conn.commit()
        return dict(value, cached=False)

    def module(self):
        import local_comparison_models as engines
        return engines

    def model(self, method):
        if method not in self.models:
            e = self.module()
            if method in ("lightglue", "superglue"):
                self.models[method] = e.Matcher(method)
            elif method == "loftr":
                self.models[method] = e.DenseMatcher()
            elif method in ("lpips", "dists"):
                self.models[method] = e.Perceptual(method)
            elif method in ("dinov2", "dinov3", "siglip"):
                from transformers import AutoImageProcessor, AutoModel, AutoProcessor
                repo = ("facebook/dinov2-base" if method == "dinov2" else
                        "facebook/dinov3-vitl16-pretrain-lvd1689m")
                path = str(CHECKPOINT) if method == "siglip" else e.MODELS[repo]["path"]
                processor = (AutoProcessor if method == "siglip" else AutoImageProcessor)
                self.models[method] = (
                    AutoModel.from_pretrained(path, local_files_only=True,
                                              dtype=e.torch.float32).eval().to(e.DEVICE),
                    processor.from_pretrained(path, local_files_only=True))
            else:
                raise ValueError("unsupported local model")
        return self.models[method]

    def feature(self, method, item, use_cache=True):
        key = (method, item["sha256"])
        if use_cache and key in self.features:
            return self.features[key]
        directory = RUNTIME / method / "features"
        path = directory / (item["sha256"] + (".npy" if method == "siglip" else ".npz"))
        if use_cache and not path.is_file():
            imported = Path(self.identity["imported_feature_root"]) / method
            imported = (imported / path.name if method == "siglip" else imported / "features" / path.name)
            if imported.is_file():
                path = imported  # Read only. New feature writes always use the live directory.
        if use_cache and path.is_file():
            if method == "siglip":
                result = np.load(path, allow_pickle=False)
            else:
                with np.load(path, allow_pickle=False) as saved:
                    result = {k: saved[k] for k in saved.files}
        else:
            path = directory / path.name
            e = self.module()
            model, processor = self.model(method)
            if method == "siglip":
                with Image.open(item["path"]) as image:
                    batch = processor(images=image.convert("RGB"), max_num_patches=512,
                                      return_tensors="pt").to(e.DEVICE)
                with e.torch.inference_mode():
                    value = model.get_image_features(**batch)
                    value = value if isinstance(value, e.torch.Tensor) else value.pooler_output
                    result = e.F.normalize(value.float(), dim=-1)[0].cpu().numpy()
                np.save(path, result, allow_pickle=False)
            else:
                image, mask = e.canvas(item["path"], 448)
                with e.torch.inference_mode():
                    batch = processor(image, do_resize=False, do_center_crop=False,
                                      return_tensors="pt").to(e.DEVICE)
                    output = model(**batch).last_hidden_state[0]
                    cls = e.F.normalize(output[0], dim=-1)
                    prefix = 1 + getattr(model.config, "num_register_tokens", 0)
                    patches = e.F.normalize(output[prefix:], dim=-1)
                    size = model.config.patch_size
                    grid = 448 // size
                    weights = e.torch.from_numpy(mask.astype(np.float32)).reshape(
                        grid, size, grid, size).mean((1, 3))
                    patches = patches[(weights.reshape(-1) > .5).to(e.DEVICE)]
                result = {"cls": cls.cpu().numpy(), "patches": patches.cpu().numpy()}
                np.savez_compressed(path, **result)
        if len(self.features) >= 128:
            self.features.pop(next(iter(self.features)))
        self.features[key] = result
        return result

    def aligned(self, model, q, r, detail):
        e = self.module()
        if not (detail.get("valid") and detail["inliers"] >= 12 and
                min(detail["coverage_query"], detail["coverage_reference"]) >= .2):
            return None, None
        im0, mask0 = e.canvas(q["path"], 512)
        im1, mask1 = e.canvas(r["path"], 512)
        h = np.asarray(detail["homography"])
        warped = e.cv2.warpPerspective(np.asarray(im0), h, (512, 512),
                                       borderValue=(255, 255, 255))
        wm = e.cv2.warpPerspective(mask0.astype(np.uint8), h, (512, 512),
                                   flags=e.cv2.INTER_NEAREST) > 0
        overlap = wm & mask1
        fraction = float(overlap.sum() / mask1.sum())
        if fraction < .5:
            return None, fraction
        ref = np.asarray(im1).copy()
        warped[~overlap] = ref[~overlap] = 255
        a = Image.fromarray(warped).resize((256, 256), Image.Resampling.LANCZOS)
        b = Image.fromarray(ref).resize((256, 256), Image.Resampling.LANCZOS)
        return model.distance(model.extract(a), model.extract(b)), fraction

    def pair(self, method, q, r, use_cache=True):
        key = q["sha256"] + ":" + r["sha256"]
        cached = self.get(method, key, use_cache)
        if cached is not None:
            return cached
        started = time.perf_counter()
        if method in ("lightglue", "superglue", "loftr"):
            detail = self.model(method)(q, r)
            value = {"score": detail["inliers"] if detail["valid"] else 0,
                     "geometry": detail}
        elif method in ("dinov2", "dinov3", "siglip"):
            a, b = self.feature(method, q, use_cache), self.feature(method, r, use_cache)
            if method == "siglip":
                value = {"score": float(a @ b)}
            else:
                value = {"score": float(a["cls"] @ b["cls"]), "patch_score": None}
                if min(len(a["patches"]), len(b["patches"])) > 8:
                    similarities = a["patches"] @ b["patches"].T
                    value["patch_score"] = float((similarities.max(1).mean() +
                                                   similarities.max(0).mean()) / 2)
        elif method in ("lpips", "dists"):
            model = self.model(method)
            value = {"score": model.distance(model.features(q["sha256"], q["path"]),
                                              model.features(r["sha256"], r["path"]))}
            match = self.pair("lightglue", q, r, use_cache)
            distance, fraction = self.aligned(model, q, r, match["geometry"])
            value.update(aligned_distance=distance, overlap_fraction=fraction)
        else:
            raise ValueError("unsupported pair method")
        if any(isinstance(v, float) and not math.isfinite(v) for v in value.values()):
            raise ValueError("nonfinite local score")
        value.update(inference_s=time.perf_counter() - started, error=None)
        return self.put(method, key, value)

    def handle(self, request):
        method = request["method"]
        q = request["query"]
        refs = request.get("references", [])
        # Hash actual pixels before trusting cache keys from the caller.
        for item in [q, *refs]:
            if digest(item["path"]) != item["sha256"]:
                raise ValueError("local comparison input changed")
        use_cache = request.get("use_cache", True)
        if method == "siglip-vector":
            return {"vector": self.feature("siglip", q, use_cache).tolist()}
        return {"rows": [self.pair(method, q, r, use_cache) for r in refs]}


def main():
    engine = Engine()
    for line in sys.stdin:
        try:
            with contextlib.redirect_stdout(sys.stderr):
                answer = engine.handle(json.loads(line))
            answer["identity"] = engine.identity
        except Exception as exc:
            answer = {"error": type(exc).__name__ + ": " + str(exc)[:500]}
        print(json.dumps(answer, allow_nan=False), flush=True)


if __name__ == "__main__":
    main()
