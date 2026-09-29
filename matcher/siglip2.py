"""The backend `siglip2`: one SigLIP2 vector of the photo against one bundle.

The photo gets the steps of the lab pipeline `siglip2-p512-as-is`: the EXIF orientation,
a white background, and a resize to 1024 pixels on the long side with the aspect ratio
kept. A smaller photo keeps its size. The backend does not segment the photo. The vector
ranks the catalogue vectors of the bundle view `full`. The wine with the best cosine is
the Top-1 match.

The model name and `extra_body` come from the bundle manifest, so the query vector and the
catalogue vectors use the same model settings.
"""

import base64
import io
import json
import socket
import urllib.error
import urllib.request

import numpy as np
from PIL import Image, ImageOps


VIEW = "full"
MAX_SIZE = 1024
TIMEOUT_SECONDS = 60
MAX_BATCH_SIZE = 64


class Siglip2Error(RuntimeError):
    """The SigLIP2 endpoint did not return one valid vector."""

    def __init__(self, status_code: int, message: str, detail: str):
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


def model_input(image_bytes):
    """Return the PNG bytes of one photo after the steps of the lab pipeline."""
    with Image.open(io.BytesIO(image_bytes)) as opened:
        opened.seek(0)
        image = ImageOps.exif_transpose(opened)
        alpha = image.mode in ("RGBA", "LA", "PA") or (
            image.mode == "P" and "transparency" in image.info)
        image = image.convert("RGBA" if alpha else "RGB")
    if image.mode == "RGBA":
        white = Image.new("RGBA", image.size, (255, 255, 255, 255))
        image = Image.alpha_composite(white, image).convert("RGB")
    if max(image.size) > MAX_SIZE:
        scale = MAX_SIZE / max(image.size)
        size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
        if size != image.size:
            image = image.resize(size, Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


class Siglip2Backend:
    """Embed one photo on an OpenAI-compatible endpoint and rank it in one bundle.

    `endpoint` is the root URL of the gateway, as in the variable SIGLIP2_ENDPOINT, for
    example http://192.168.86.14:18081. The backend sends POST <endpoint>/v1/embeddings.
    """

    def __init__(self, bundle, endpoint):
        self.bundle = bundle
        self.url = endpoint.rstrip("/") + "/v1/embeddings"
        self.model = bundle.embedding["model"]
        self.extra_body = dict(bundle.embedding.get("extra_body") or {})

    def predict(self, image):
        """Return the Top-1 slug of one image body."""
        return self.bundle.top1(VIEW, self.embed(model_input(image)))[0]

    def embed(self, png, timeout=TIMEOUT_SECONDS):
        """Return the L2-normalized vector of one PNG file. Raise Siglip2Error."""
        return self.embed_many([png], timeout=timeout)[0]

    def embed_many(self, pngs, timeout=TIMEOUT_SECONDS):
        """Return one L2-normalized vector for each PNG in bounded requests."""
        if not pngs:
            return []
        if len(pngs) > MAX_BATCH_SIZE:
            vectors = []
            for start in range(0, len(pngs), MAX_BATCH_SIZE):
                vectors.extend(self.embed_many(
                    pngs[start:start + MAX_BATCH_SIZE], timeout=timeout))
            return vectors
        inputs = [
            "data:image/png;base64," + base64.b64encode(png).decode("ascii")
            for png in pngs
        ]
        body = dict(self.extra_body, model=self.model, input=inputs)
        request = urllib.request.Request(
            self.url, data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                answer = json.load(response)
        except urllib.error.HTTPError as exc:
            with exc:
                detail = exc.read(300).decode("utf-8", "replace").strip()
            raise Siglip2Error(
                502,
                "HTTP %d from %s: %s" % (exc.code, self.url, detail),
                "SigLIP2 service returned HTTP %d" % exc.code,
            ) from exc
        except (TimeoutError, socket.timeout) as exc:
            raise Siglip2Error(
                504,
                "request to %s timed out" % self.url,
                "SigLIP2 request timed out",
            ) from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, (TimeoutError, socket.timeout)):
                raise Siglip2Error(
                    504,
                    "request to %s timed out" % self.url,
                    "SigLIP2 request timed out",
                ) from exc
            raise Siglip2Error(
                502,
                "cannot reach %s: %s" % (self.url, exc),
                "SigLIP2 service is unavailable",
            ) from exc
        except (OSError, ValueError) as exc:
            raise Siglip2Error(
                502,
                "no valid answer from %s: %s" % (self.url, exc),
                "SigLIP2 service returned invalid data",
            ) from exc
        try:
            data = answer["data"]
            if len(data) != len(inputs):
                raise ValueError("%d vectors for %d images" % (len(data), len(inputs)))
            ordered = [None] * len(inputs)
            for position, item in enumerate(data):
                index = item.get("index", position)
                if (type(index) is not int or index < 0 or index >= len(inputs)
                        or ordered[index] is not None):
                    raise ValueError("invalid or duplicate vector index %s" % index)
                ordered[index] = np.asarray(item["embedding"], dtype=np.float32)
        except (AttributeError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise Siglip2Error(
                502,
                "the answer of %s is not one embedding per image: %s" % (self.url, exc),
                "SigLIP2 service returned invalid embedding data",
            ) from exc
        vectors = []
        for vector in ordered:
            if vector.shape != (self.bundle.dimension,):
                raise Siglip2Error(
                    502,
                    "%s sent a vector of shape %s; the bundle holds %d values"
                    % (self.url, vector.shape, self.bundle.dimension),
                    "SigLIP2 service returned an embedding with an invalid shape",
                )
            norm = float(np.linalg.norm(vector))
            if not np.isfinite(norm) or norm == 0.0:
                raise Siglip2Error(
                    502,
                    "%s sent a vector of length %s" % (self.url, norm),
                    "SigLIP2 service returned an invalid embedding",
                )
            vectors.append(vector / norm)
        return vectors
