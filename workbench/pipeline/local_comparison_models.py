"""Pinned local visual engines, shared with the benchmark's verified algorithms."""
# ruff: noqa: E402
import json
import os
from pathlib import Path
from functools import lru_cache
from types import SimpleNamespace
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "work/main-label-pairwise"
sys.path.insert(0, str(PACKAGE_ROOT / "packages"))
os.environ.update(HF_HOME=str(PACKAGE_ROOT / "hf"), TORCH_HOME=str(PACKAGE_ROOT / "torch"),
                  HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
import cv2
import numpy as np
from PIL import Image
import torch
import torch.nn.functional as F  # noqa: F401 (worker uses this alias)
torch.set_num_threads(4)
torch.set_num_interop_threads(1)
cv2.setNumThreads(1)
RUNTIME = ROOT / "work/local-comparison"
DEVICE = os.environ.get("PAIRWISE_DEVICE", "mps")
MODELS = json.loads((RUNTIME / "models.json").read_text())["models"]


def dump(path, value):
    path.write_text(json.dumps(value, allow_nan=False))


def sync():
    if DEVICE == "mps":
        torch.mps.synchronize()

def foreground(image):
    mask = (np.asarray(image).min(axis=2) < 250).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    output = np.zeros_like(mask)
    if contours:
        cv2.drawContours(output, [max(contours, key=cv2.contourArea)], -1, 1, cv2.FILLED)
    assert output.sum() > 100
    return output

def canvas(path, size):
    image = Image.open(path).convert("RGB")
    original_mask = Image.fromarray(foreground(image) * 255)
    scale = (size - 16) / max(image.size)
    shape = tuple(max(1, round(n * scale)) for n in image.size)
    image = image.resize(shape, Image.Resampling.LANCZOS)
    original_mask = original_mask.resize(shape, Image.Resampling.NEAREST)
    result = Image.new("RGB", (size, size), "white")
    mask = Image.new("L", (size, size), 0)
    offset = ((size - shape[0]) // 2, (size - shape[1]) // 2)
    result.paste(image, offset)
    mask.paste(original_mask, offset)
    return result, np.asarray(mask) > 0

def tensor(image):
    return torch.from_numpy(np.array(image).transpose(2, 0, 1)).float().unsqueeze(0) / 255

def coverage(points, mask):
    if len(points) < 3:
        return 0.0
    return min(1.0, float(cv2.contourArea(cv2.convexHull(points.astype(np.float32)))) / mask.sum())

def geometry(points0, points1, scores, mask0, mask1):
    points0 = np.asarray(points0, np.float32).reshape(-1, 2)
    points1 = np.asarray(points1, np.float32).reshape(-1, 2)
    scores = np.asarray(scores, np.float32).reshape(-1)
    assert len(points0) == len(points1) == len(scores)
    keep = np.isfinite(points0).all(1) & np.isfinite(points1).all(1) & np.isfinite(scores)
    for points, mask in [(points0, mask0), (points1, mask1)]:
        xy = points.round().astype(int).clip(0, mask.shape[0] - 1)
        keep &= (points >= 0).all(1) & (points < mask.shape[0]).all(1) & mask[xy[:, 1], xy[:, 0]]
    points0, points1, scores = points0[keep], points1[keep], scores[keep]
    base = {"raw_matches": len(keep), "foreground_matches": len(points0), "inliers": 0,
            "inlier_ratio": 0.0, "coverage_query": 0.0, "coverage_reference": 0.0,
            "homography": None, "valid": False, "median_error_px": None,
            "points0": points0.tolist(), "points1": points1.tolist(), "confidence": scores.tolist(), "inlier_mask": []}
    if len(points0) < 4:
        return base
    cv2.setRNGSeed(20261008)
    homography, inliers = cv2.findHomography(points0, points1, cv2.RANSAC, 3.0, maxIters=5000, confidence=.999)
    if homography is None or not np.isfinite(homography).all():
        return base
    if np.linalg.cond(homography) > 1e7:
        return base
    corners = np.float32([[0, 0], [512, 0], [512, 512], [0, 512]]).reshape(-1, 1, 2)
    warped = cv2.perspectiveTransform(corners, homography).reshape(-1, 2)
    area = cv2.contourArea(warped, oriented=True)
    if not np.isfinite(warped).all() or not .1 * 512**2 < area < 10 * 512**2 or not cv2.isContourConvex(warped):
        return base
    inliers = inliers.ravel().astype(bool)
    projected = cv2.perspectiveTransform(points0[:, None], homography).reshape(-1, 2)
    count = int(inliers.sum())
    if count < 4:
        return base
    base.update(inliers=count, inlier_ratio=count / len(points0),
                coverage_query=coverage(points0[inliers], mask0),
                coverage_reference=coverage(points1[inliers], mask1),
                homography=homography.tolist(), valid=True,
                median_error_px=float(np.median(np.linalg.norm(projected[inliers] - points1[inliers], axis=1))),
                inlier_mask=inliers.tolist())
    return base
canvas = lru_cache(maxsize=128)(canvas)
_raw_geometry = geometry

def compact_geometry(*args):
    value = _raw_geometry(*args)
    for key in ("points0", "points1", "confidence", "inlier_mask"):
        value.pop(key)
    return value

common = SimpleNamespace(MODELS=MODELS, DEVICE=DEVICE, RUNTIME=RUNTIME, OUT=RUNTIME,
                         sync=sync, dump=dump, geometry=compact_geometry,
                         pilot=SimpleNamespace(tensor=tensor, RUNTIME=PACKAGE_ROOT))


class Matcher:
    def __init__(self, method):
        from transformers import (
            AutoImageProcessor,
            LightGlueForKeypointMatching,
            SuperGlueForKeypointMatching,
        )

        self.method = method
        repo = (
            "ETH-CVG/lightglue_superpoint"
            if method == "lightglue"
            else "magic-leap-community/superglue_outdoor"
        )
        path = common.MODELS[repo]["path"]
        self.processor = AutoImageProcessor.from_pretrained(path, local_files_only=True)
        cls = (
            LightGlueForKeypointMatching
            if method == "lightglue"
            else SuperGlueForKeypointMatching
        )
        self.model = (
            cls.from_pretrained(path, local_files_only=True).eval().to(common.DEVICE)
        )
        self.model.keypoint_detector.config.max_keypoints = 1024
        self.model.keypoint_detector.max_keypoints = 1024
        self.model.keypoint_detector.keypoint_decoder.max_keypoints = 1024
        self.feature_times = {}
        self.feature_directory = common.RUNTIME / method / "features"
        self.feature_directory.mkdir(exist_ok=True)

    @lru_cache(maxsize=128)
    def features(self, digest, path):
        file = self.feature_directory / (digest + ".npz")
        if file.exists():
            with np.load(file, allow_pickle=False) as saved:
                arrays = {key: saved[key] for key in saved.files}
            meta = file.with_suffix(".json")
            if meta.exists():
                self.feature_times[digest] = json.loads(meta.read_text())
            return arrays
        start = time.perf_counter()
        image, _ = canvas(path, 512)
        pixels = self.processor([image, image], do_resize=False, return_tensors="pt")[
            "pixel_values"
        ][:, 0].to(common.DEVICE)
        with torch.inference_mode():
            output = self.model.keypoint_detector(pixels)
            keys, scores, descriptors, mask = output[:4]
        count = int(mask.sum().item())
        assert count <= 1024, (
            f"SuperPoint returned {count} keypoints above the configured limit"
        )
        arrays = {
            key: value[0].cpu().numpy()
            for key, value in zip(
                ["keypoints", "scores", "descriptors", "mask"],
                [keys, scores, descriptors, mask],
            )
        }
        np.savez_compressed(file, **arrays)
        self.feature_times[digest] = {
            "inference_s": time.perf_counter() - start,
            "path": path,
            "count": count,
        }
        common.dump(file.with_suffix(".json"), self.feature_times[digest])
        return arrays

    def __call__(self, query, reference):
        return self.batch([(query, reference)])[0]

    def batch(self, pairs):
        features = [
            (
                self.features(q["sha256"], q["path"]),
                self.features(r["sha256"], r["path"]),
            )
            for q, r in pairs
        ]
        count = max(len(f["mask"]) for pair in features for f in pair)
        batch = {}
        for key in features[0][0]:
            groups = []
            for pair in features:
                rows = []
                for feature in pair:
                    padding = [(0, count - len(feature[key]))] + [(0, 0)] * (
                        feature[key].ndim - 1
                    )
                    rows.append(np.pad(feature[key], padding))
                groups.append(np.stack(rows))
            batch[key] = torch.from_numpy(np.stack(groups)).to(common.DEVICE)
        absolute = batch["keypoints"] * 512
        with torch.inference_mode():
            if self.method == "lightglue":
                matched = self.model._match_image_pair(
                    absolute,
                    batch["descriptors"],
                    512,
                    512,
                    mask=batch["mask"],
                    output_attentions=False,
                    output_hidden_states=False,
                )
            else:
                matched = self.model._match_image_pair(
                    absolute,
                    batch["descriptors"],
                    batch["scores"],
                    512,
                    512,
                    mask=batch["mask"],
                    output_attentions=False,
                    output_hidden_states=False,
                )
            output = SimpleNamespace(
                matches=matched[0],
                matching_scores=matched[1],
                keypoints=batch["keypoints"],
                mask=batch["mask"],
            )
            answers = self.processor.post_process_keypoint_matching(
                output, [[(512, 512), (512, 512)]] * len(pairs), threshold=0.0
            )
        result = []
        for (query, reference), answer in zip(pairs, answers):
            _, m0 = canvas(query["path"], 512)
            _, m1 = canvas(reference["path"], 512)
            result.append(
                common.geometry(
                    *[
                        answer[k].cpu().numpy()
                        for k in ["keypoints0", "keypoints1", "matching_scores"]
                    ],
                    m0,
                    m1,
                )
            )
        return result

    def parity(self, query, reference):
        cached = self(query, reference)
        i0, m0 = canvas(query["path"], 512)
        i1, m1 = canvas(reference["path"], 512)
        with torch.inference_mode():
            data = self.processor([i0, i1], do_resize=False, return_tensors="pt").to(
                common.DEVICE
            )
            output = self.model(**data)
            result = self.processor.post_process_keypoint_matching(
                output, [[(512, 512), (512, 512)]], threshold=0.0
            )[0]
        direct = common.geometry(
            *[
                result[k].cpu().numpy()
                for k in ["keypoints0", "keypoints1", "matching_scores"]
            ],
            m0,
            m1,
        )
        assert (
            cached["inliers"] == direct["inliers"]
            and cached["valid"] == direct["valid"]
        ), "Cached SuperPoint features differ from direct model inference"
        return {
            "cached_inliers": cached["inliers"],
            "direct_inliers": direct["inliers"],
            "passed": True,
        }

class DenseMatcher:
    def __init__(self):
        from kornia.feature import LoFTR

        self.model = LoFTR(pretrained=None).eval()
        state = torch.load(
            common.MODELS["loftr_outdoor.ckpt"]["path"],
            map_location="cpu",
            weights_only=True,
        )
        self.model.load_state_dict(state["state_dict"])
        self.model.to(common.DEVICE)
        self.feature_times = {}
        self.memory_stats = {}
        previous = []
        for name in ("loftr-status.json", "loftr-progress.json"):
            path = common.OUT / name
            if path.exists():
                previous.append(json.loads(path.read_text()))
        if previous:
            self.feature_times = max(
                previous, key=lambda value: value.get("scored_pairs", 0)
            ).get("feature_times", {})

    @lru_cache(maxsize=32)
    def features(self, digest, path):
        from kornia.color import rgb_to_grayscale

        image, _ = canvas(path, 512)
        started = time.perf_counter()
        with torch.inference_mode():
            result = self.model.backbone(
                rgb_to_grayscale(common.pilot.tensor(image)).to(common.DEVICE)
            )
        common.sync()
        self.feature_times.setdefault(
            digest, {"inference_s": time.perf_counter() - started, "path": path}
        )
        return result

    def __call__(self, query, reference):
        return self.batch([(query, reference)])[0]

    def batch(self, pairs):
        f0 = [self.features(q["sha256"], q["path"]) for q, _ in pairs]
        f1 = [self.features(r["sha256"], r["path"]) for _, r in pairs]
        c0, c1 = torch.cat([f[0] for f in f0]), torch.cat([f[0] for f in f1])
        ff0, ff1 = torch.cat([f[1] for f in f0]), torch.cat([f[1] for f in f1])
        data = {
            "bs": len(pairs),
            "hw0_i": (512, 512),
            "hw1_i": (512, 512),
            "hw0_c": c0.shape[2:],
            "hw1_c": c1.shape[2:],
            "hw0_f": ff0.shape[2:],
            "hw1_f": ff1.shape[2:],
        }
        with torch.inference_mode():
            a = (
                self.model.pos_encoding(c0)
                .permute(0, 2, 3, 1)
                .reshape(len(pairs), -1, c0.shape[1])
            )
            b = (
                self.model.pos_encoding(c1)
                .permute(0, 2, 3, 1)
                .reshape(len(pairs), -1, c1.shape[1])
            )
            a, b = self.model.loftr_coarse(a, b, None, None)
            self.model.coarse_matching(a, b, data, mask_c0=None, mask_c1=None)
            fa, fb = self.model.fine_preprocess(ff0, ff1, a, b, data)
            if fa.size(0):
                fa, fb = self.model.loftr_fine(fa, fb)
            self.model.fine_matching(fa, fb, data)
        raw = [data[k].cpu().numpy() for k in ["mkpts0_f", "mkpts1_f", "mconf"]]
        ids = data["b_ids"].cpu().numpy()
        result = []
        for index, (query, reference) in enumerate(pairs):
            _, m0 = canvas(query["path"], 512)
            _, m1 = canvas(reference["path"], 512)
            result.append(
                common.geometry(*[value[ids == index] for value in raw], m0, m1)
            )
        # Variable fine-match counts create large scratch allocations on Metal.
        # Release every batch's tensors before returning unused allocator buffers.
        del c0, c1, ff0, ff1, a, b, fa, fb, data
        if common.DEVICE == "mps":
            torch.mps.synchronize()
            before = torch.mps.driver_allocated_memory()
            torch.mps.empty_cache()
            self.memory_stats = {
                "max_driver_before_cleanup_bytes": max(
                    before,
                    self.memory_stats.get("max_driver_before_cleanup_bytes", 0),
                ),
                "current_allocated_bytes": torch.mps.current_allocated_memory(),
                "driver_after_cleanup_bytes": torch.mps.driver_allocated_memory(),
            }
        return result

    def parity(self, query, reference):
        from kornia.color import rgb_to_grayscale

        cached = self(query, reference)
        i0, m0 = canvas(query["path"], 512)
        i1, m1 = canvas(reference["path"], 512)
        with torch.inference_mode():
            output = self.model(
                {
                    "image0": rgb_to_grayscale(common.pilot.tensor(i0)).to(
                        common.DEVICE
                    ),
                    "image1": rgb_to_grayscale(common.pilot.tensor(i1)).to(
                        common.DEVICE
                    ),
                }
            )
        direct = common.geometry(
            *[
                output[k].cpu().numpy()
                for k in ["keypoints0", "keypoints1", "confidence"]
            ],
            m0,
            m1,
        )
        assert (
            cached["inliers"] == direct["inliers"]
            and cached["valid"] == direct["valid"]
        ), "Cached LoFTR backbone differs from direct model inference"
        return {
            "cached_inliers": cached["inliers"],
            "direct_inliers": direct["inliers"],
            "passed": True,
        }

class Perceptual:
    def __init__(self, method):
        self.method = method
        if method == "lpips":
            import lpips

            self.model = (
                lpips.LPIPS(net="alex", version="0.1", verbose=False)
                .eval()
                .to(common.DEVICE)
            )
        else:
            from DISTS_pytorch import DISTS

            self.model = DISTS(load_weights=False).eval().to(common.DEVICE)
            weights = torch.load(
                common.pilot.RUNTIME / "packages/DISTS_pytorch/weights.pt",
                map_location="cpu",
                weights_only=True,
            )
            with torch.no_grad():
                self.model.alpha.copy_(weights["alpha"])
                self.model.beta.copy_(weights["beta"])
        self.feature_times = {}

    def extract(self, image):
        return self.extract_batch([image])

    def extract_batch(self, images):
        value = torch.cat([common.pilot.tensor(image) for image in images]).to(
            common.DEVICE
        )
        with torch.inference_mode():
            if self.method == "dists":
                return self.model.forward_once(value)
            import lpips

            outputs = self.model.net.forward(self.model.scaling_layer(value * 2 - 1))
            return [lpips.normalize_tensor(output) for output in outputs]

    @lru_cache(maxsize=32)
    def features(self, digest, path):
        started = time.perf_counter()
        image, _ = canvas(path, 256)
        result = self.extract(image)
        common.sync()
        self.feature_times.setdefault(
            digest, {"inference_s": time.perf_counter() - started, "path": path}
        )
        return result

    def distance_batch(self, a, b):
        with torch.inference_mode():
            if self.method == "lpips":
                values = [
                    self.model.lins[k]((a[k] - b[k]) ** 2).mean((2, 3), keepdim=True)
                    for k in range(len(a))
                ]
                return sum(values).reshape(-1).cpu().numpy().tolist()
            total = self.model.alpha.sum() + self.model.beta.sum()
            alpha = torch.split(self.model.alpha / total, self.model.chns, dim=1)
            beta = torch.split(self.model.beta / total, self.model.chns, dim=1)
            d1 = d2 = 0
            for k in range(len(a)):
                am, bm = (
                    a[k].mean((2, 3), keepdim=True),
                    b[k].mean((2, 3), keepdim=True),
                )
                s1 = (2 * am * bm + 1e-6) / (am**2 + bm**2 + 1e-6)
                av, bv = (
                    ((a[k] - am) ** 2).mean((2, 3), keepdim=True),
                    ((b[k] - bm) ** 2).mean((2, 3), keepdim=True),
                )
                cov = (a[k] * b[k]).mean((2, 3), keepdim=True) - am * bm
                s2 = (2 * cov + 1e-6) / (av + bv + 1e-6)
                d1 = d1 + (alpha[k] * s1).sum(1, keepdim=True)
                d2 = d2 + (beta[k] * s2).sum(1, keepdim=True)
            return (1 - (d1 + d2).squeeze()).reshape(-1).cpu().numpy().tolist()

    def distance(self, a, b):
        return float(self.distance_batch(a, b)[0])

    def parity(self, query, reference):
        i0, _ = canvas(query["path"], 256)
        i1, _ = canvas(reference["path"], 256)
        a, b = (
            common.pilot.tensor(i0).to(common.DEVICE),
            common.pilot.tensor(i1).to(common.DEVICE),
        )
        with torch.inference_mode():
            direct = float(
                self.model(a * 2 - 1, b * 2 - 1).item()
                if self.method == "lpips"
                else self.model(a, b).item()
            )
        cached = self.distance(
            self.features(query["sha256"], query["path"]),
            self.features(reference["sha256"], reference["path"]),
        )
        assert abs(direct - cached) < 1e-5, (
            "Cached perceptual features differ from the public metric"
        )
        return {"direct": direct, "cached": cached, "passed": True}
