"""Use an ArcFace-trained projection on frozen DINOv3 features.

Inference needs NumPy alone. The loss and class centers belong to training.
Both the catalogue build and the query runner use ProjectionBackend.
"""
import hashlib
import io
import json

import numpy as np

FORMAT = "dinov3-arcface-projection-v1"


def normalize(features):
    """Validate and L2-normalize an N x D feature matrix."""
    features = np.asarray(features, dtype=np.float32)
    if features.ndim != 2 or not np.isfinite(features).all():
        raise ValueError("features MUST be a finite matrix")
    norms = np.linalg.norm(features, axis=1, keepdims=True)
    if np.any(norms < 1e-12):
        raise ValueError("features MUST NOT contain a zero vector")
    return features / norms


class Projection:
    """A linear projection followed by L2 normalization."""

    def __init__(self, weight, bias, metadata, digest=None):
        self.weight = np.asarray(weight, dtype=np.float32)
        self.bias = np.asarray(bias, dtype=np.float32)
        if (self.weight.ndim != 2 or min(self.weight.shape) < 1
                or self.bias.shape != (self.weight.shape[0],)
                or not np.isfinite(self.weight).all() or not np.isfinite(self.bias).all()):
            raise ValueError("projection weights MUST have finite shapes D_out x D_in and D_out")
        if not isinstance(metadata, dict) or metadata.get("format") != FORMAT:
            raise ValueError("unsupported ArcFace checkpoint format")
        self.metadata = metadata
        self.digest = digest

    def transform(self, features):
        features = normalize(features)
        if features.shape[1] != self.weight.shape[1]:
            raise ValueError("DINOv3 feature dimension does not match the ArcFace checkpoint")
        return normalize(features @ self.weight.T + self.bias)

    def dumps(self):
        buffer = io.BytesIO()
        np.savez_compressed(buffer, weight=self.weight, bias=self.bias,
                            metadata=np.array(json.dumps(self.metadata, sort_keys=True)))
        return buffer.getvalue()

    @classmethod
    def load(cls, spec, model, extra_body):
        with open(spec["checkpoint"], "rb") as handle:
            data = handle.read()
        digest = hashlib.sha256(data).hexdigest()
        if digest != spec["sha256"]:
            raise ValueError("ArcFace checkpoint SHA-256 does not match the configuration")
        with np.load(io.BytesIO(data), allow_pickle=False) as archive:
            projection = cls(archive["weight"], archive["bias"],
                             json.loads(archive["metadata"].item()), digest)
        expected = {"model": model, "extra_body": extra_body}
        if projection.metadata.get("source_model") != expected:
            raise ValueError("ArcFace checkpoint requires a different DINOv3 model or extra_body")
        return projection


class ProjectionBackend:
    """Apply one checkpoint to catalogue vectors and query vectors."""

    def __init__(self, backend, projection):
        self.backend = backend
        self.projection = projection

    def software(self):
        return dict(self.backend.software(), arcface_sha256=self.projection.digest,
                    arcface_format=FORMAT, arcface_dim=self.projection.weight.shape[0])

    def embed(self, images):
        from build_embeddings import BackendError
        try:
            return self.projection.transform(self.backend.embed(images))
        except ValueError as exc:
            raise BackendError("ArcFace projection failed: %s" % exc) from exc
