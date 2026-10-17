"""Learned keypoints (ALIKED or DISK) and the LightGlue matcher.

torch and lightglue are optional (`uv sync --extra deep`) and imported on first use.
Licences: LightGlue Apache-2.0, ALIKED BSD-3-Clause, DISK Apache-2.0. SuperPoint is left
out: its weights are for non-commercial use only.
"""

from __future__ import annotations

import os

import numpy as np

KINDS = {"aliked": "ALIKED", "disk": "DISK"}
_models: dict = {}


def _environment():
    # The python.org builds of Python ship without CA certificates, and the first use
    # downloads the weights from GitHub. Use the system bundle of macOS.
    if "SSL_CERT_FILE" not in os.environ and os.path.exists("/etc/ssl/cert.pem"):
        os.environ["SSL_CERT_FILE"] = "/etc/ssl/cert.pem"
    os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")


def device() -> str:
    import torch

    if torch.backends.mps.is_available():
        return "mps"
    return "cuda" if torch.cuda.is_available() else "cpu"


def models(kind: str, max_keypoints: int):
    """Return (the extractor, the matcher, the device), loaded once."""
    key = (kind, max_keypoints)
    if key not in _models:
        _environment()
        import lightglue

        where = device()
        extractor = getattr(lightglue, KINDS[kind])(max_num_keypoints=max_keypoints)
        matcher = lightglue.LightGlue(features=kind)
        _models[key] = (extractor.eval().to(where), matcher.eval().to(where), where)
    return _models[key]


def extract(image_bgr: np.ndarray, kind: str, max_keypoints: int, max_side: int):
    """Return (points (N, 2) in pixels of the frame, descriptors (N, D)) float32."""
    import torch

    extractor, _, where = models(kind, max_keypoints)
    rgb = np.ascontiguousarray(image_bgr[..., ::-1])
    tensor = torch.from_numpy(rgb).permute(2, 0, 1).float().div(255).to(where)
    with torch.no_grad():
        features = extractor.extract(tensor, resize=max_side)
    points = features["keypoints"][0].float().cpu().numpy()
    descriptors = features["descriptors"][0].float().cpu().numpy()
    return points, descriptors


def match(points_a, descriptors_a, size_a, points_b, descriptors_b, size_b, kind: str,
          max_keypoints: int):
    """Return the matched indices (into A, into B)."""
    import torch

    _, matcher, where = models(kind, max_keypoints)

    def pack(points, descriptors, size):
        return {"keypoints": torch.from_numpy(points)[None].to(where),
                "descriptors": torch.from_numpy(descriptors)[None].to(where),
                "image_size": torch.tensor([size], dtype=torch.float32, device=where)}

    with torch.no_grad():
        out = matcher({"image0": pack(points_a, descriptors_a, size_a),
                       "image1": pack(points_b, descriptors_b, size_b)})
    matches = out["matches"][0].cpu().numpy().reshape(-1, 2)
    return matches[:, 0], matches[:, 1]
