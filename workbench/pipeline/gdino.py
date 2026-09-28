"""The client of `POST /detect` of the Grounding DINO services of gx10.

Usage:
    python3 pipeline/gdino.py <image> [--texts "wine bottle, label"]
        [--model grounding-dino-base] [--threshold 0.25] [--text-threshold 0.25]

The command line prints one JSON object: the cache state (`hit` or `miss`), the scale
of the sent copy, and the instances. Read docs/plans/25_model-call-cache.md.

Rules:
- The gateway serves `grounding-dino-base`, `mm-gdino-base`, and `mm-gdino-base-all`.
  One process serves one checkpoint, at `<gateway>/upstream/<model>/detect`.
- The sent copy lies on white and has a long side of at most `GDINO_MAX_SIDE`, as the
  copy of `derive.Sam3Client`. The box of an instance is in the pixels of the sent copy:
  divide it by `scale` for the pixels of the image.
- The client waits and asks again after HTTP 429, HTTP 5xx, and a network error.
- A repeated request reads the answer of `model_cache`. Only an answer of HTTP 200 is
  stored.
"""
import argparse
import io
import json
import os
import random
import sys
import time

import requests
from PIL import Image, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model_cache  # noqa: E402

GATEWAY = "http://192.168.86.14:18081"
GDINO_MODEL = "grounding-dino-base"
# The defaults of the service.
GDINO_THRESHOLD = 0.25
GDINO_TEXT_THRESHOLD = 0.25
GDINO_MAX_SIDE = 1536
GDINO_TIMEOUT = 120
GDINO_RETRIES = 4
GDINO_RETRY_WAIT = 2.0
GDINO_MAX_RETRY_WAIT = 30.0


class GdinoUnavailable(Exception):
    """The Grounding DINO service did not answer."""


def sent_copy(image, max_side=GDINO_MAX_SIDE):
    """Return (the PNG bytes of the copy that goes to the service, the scale of the
    copy). The copy lies on white and has a long side of at most `max_side`."""
    flat = image.convert("RGB")
    if image.mode == "RGBA":
        flat = Image.new("RGB", image.size, "white")
        flat.paste(image, mask=image.getchannel("A"))
    scale = min(1.0, max_side / float(max(flat.size)))
    if scale < 1.0:
        flat = flat.resize((max(1, round(flat.width * scale)),
                            max(1, round(flat.height * scale))), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    flat.save(buffer, "PNG")
    return buffer.getvalue(), scale


class GdinoClient:
    """The client of one Grounding DINO model of the gateway."""

    def __init__(self, model=GDINO_MODEL, gateway=GATEWAY):
        self.model = model
        self.endpoint = "%s/upstream/%s" % (gateway.rstrip("/"), model)
        self.session = requests.Session()
        self.hits = 0

    def _post(self, data, texts, threshold, text_threshold):
        form = {"texts": texts, "threshold": str(threshold),
                "text_threshold": str(text_threshold)}
        params = {key: value for key, value in form.items() if key != "texts"}
        fields = model_cache.request_fields(self.endpoint + "/detect", self.model, params,
                                            texts, [data])
        record = model_cache.lookup(fields)
        if record is not None:
            self.hits += 1
            return record["answer"]
        started = time.perf_counter()
        answer = self._send(data, form)
        model_cache.store(fields, answer, (time.perf_counter() - started) * 1000)
        return answer

    def _send(self, data, form):
        last = None
        for attempt in range(GDINO_RETRIES + 1):
            wait = 0.0
            try:
                response = self.session.post(
                    self.endpoint + "/detect",
                    files={"image": ("image.png", data, "image/png")},
                    data=form, timeout=GDINO_TIMEOUT)
                if response.status_code == 200:
                    return response.json()
                last = "HTTP %d: %s" % (response.status_code, response.text[:200])
                retryable = response.status_code == 429 or response.status_code >= 500
                try:
                    wait = float(response.headers.get("Retry-After") or 0)
                except ValueError:
                    wait = 0.0
            except (requests.RequestException, ValueError) as exc:
                last = str(exc)
                retryable = True
            if attempt >= GDINO_RETRIES or not retryable:
                break
            if wait <= 0:
                wait = min(GDINO_RETRY_WAIT * (2 ** attempt), GDINO_MAX_RETRY_WAIT)
            time.sleep(wait + random.uniform(0, 0.5))
        raise GdinoUnavailable("the Grounding DINO service at %s did not answer: %s"
                               % (self.endpoint, last))

    def detect(self, image, texts, threshold=GDINO_THRESHOLD,
               text_threshold=GDINO_TEXT_THRESHOLD):
        """Send `image` with the nouns `texts`. Return (instances, scale).

        Each instance is the dict of the service as it comes. Raise `GdinoUnavailable`.
        """
        data, scale = sent_copy(image)
        answer = self._post(data, texts, threshold, text_threshold)
        return list(answer.get("instances") or []), scale


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("image", help="the image file")
    parser.add_argument("--texts", default="wine bottle",
                        help="comma-separated nouns (default: %(default)s)")
    parser.add_argument("--model", default=GDINO_MODEL,
                        help="the served name of the gateway (default: %(default)s)")
    parser.add_argument("--gateway", default=GATEWAY, help="default: %(default)s")
    parser.add_argument("--threshold", type=float, default=GDINO_THRESHOLD)
    parser.add_argument("--text-threshold", type=float, default=GDINO_TEXT_THRESHOLD)
    args = parser.parse_args(argv)
    with Image.open(args.image) as opened:
        image = ImageOps.exif_transpose(opened)
        alpha = image.mode in ("RGBA", "LA", "PA") or (
            image.mode == "P" and "transparency" in image.info)
        image = image.convert("RGBA" if alpha else "RGB")
    client = GdinoClient(args.model, args.gateway)
    try:
        instances, scale = client.detect(image, args.texts, args.threshold,
                                         args.text_threshold)
    except GdinoUnavailable as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    print(json.dumps({"cache": "hit" if client.hits else "miss", "model": args.model,
                      "scale": scale, "count": len(instances), "instances": instances},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
