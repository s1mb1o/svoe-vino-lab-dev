"""Recognize the rerank label with local PaddleOCR; evaluate its text with Laya."""
import base64
import binascii
import io
import json
import math
from pathlib import Path
import subprocess
import threading
import time

from PIL import Image

import label_ocr
import laya_v
import model_cache

VERSION = 1
CACHE_DIR = Path(model_cache.ROOT).parent / "laya-ocr-paddle"
OCR_LOCK = threading.Lock()
TEXT_CONTEXT = (
    "Use only the supplied PaddleOCR label transcription. "
    "Use other for a different explicit value; not visible for missing or unreadable text. "
    "Do not infer visual colour or design from OCR. Do not select a wine."
)


def reader():
    # Reuse the pinned CPU OCR environment and its image/engine-aware raw-line cache.
    from main_label_match import PaddleTextReader
    return PaddleTextReader(CACHE_DIR)


def recognize(png):
    """Serialize cold local CPU recognition; successful warm reads remain cached."""
    try:
        with OCR_LOCK:
            return reader().read(png)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        raise laya_v.LayaVError("PaddleOCR label recognition failed: %s" % exc) from exc


def text_state(png, words):
    """Preserve raw text and confidence, with line positions relative to the image."""
    if not isinstance(words, list):
        raise laya_v.LayaVError("PaddleOCR returned an invalid line list")
    with Image.open(io.BytesIO(png)) as image:
        width, height = image.size
    lines = []
    for word in words:
        if (not isinstance(word, dict) or not isinstance(word.get("text"), str)
                or isinstance(word.get("confidence"), bool)
                or not isinstance(word.get("confidence"), (int, float))
                or not math.isfinite(word["confidence"])
                or not 0 <= word["confidence"] <= 100):
            raise laya_v.LayaVError("PaddleOCR returned an invalid text line")
        line = {"text": word["text"], "confidence": word["confidence"]}
        if "polygon" in word:
            polygon = word["polygon"]
            if (not isinstance(polygon, list) or len(polygon) != 4
                    or any(not isinstance(point, list) or len(point) != 2
                           or any(isinstance(v, bool) or not isinstance(v, (int, float))
                                  or not math.isfinite(v) for v in point) for point in polygon)):
                raise laya_v.LayaVError("PaddleOCR returned an invalid line polygon")
            xs, ys = [p[0] for p in polygon], [p[1] for p in polygon]
            line["box_per_mille"] = [round(1000 * min(xs) / width),
                                     round(1000 * min(ys) / height),
                                     round(1000 * max(xs) / width),
                                     round(1000 * max(ys) / height)]
        lines.append(line)
    return {"paddleocr_label_lines": lines, "context": TEXT_CONTEXT}


def request_payload(entry, content, schema, words):
    image_request, options = laya_v.request_payload(content, schema)
    uri = image_request["state"]["image"]
    try:
        png = base64.b64decode(uri.partition(",")[2], validate=True)
        state = text_state(png, words)
    except (ValueError, OSError, binascii.Error) as exc:
        raise laya_v.LayaVError("OCR reranking requires a valid label image") from exc
    questions = image_request["questions"]
    for question in questions.values():
        question["instructions"] = question["instructions"].removesuffix(
            " " + laya_v.CONTEXT) + " " + TEXT_CONTEXT
    return {"model": entry.model, "state": state, "questions": questions}, options, png


def ask(entry, content, timeout, schema, cache_read=True, cache_validator=None):
    """Return option scores through the existing bounded cluster scoring policy."""
    started = time.perf_counter()
    image_request, _ = laya_v.request_payload(content, schema)
    try:
        png = base64.b64decode(image_request["state"]["image"].partition(",")[2], validate=True)
    except (ValueError, binascii.Error) as exc:
        raise laya_v.LayaVError("OCR reranking requires a valid image data URI") from exc
    words = recognize(png)
    payload, options, _ = request_payload(entry, content, schema, words)
    fields = model_cache.request_fields(
        entry.url, "laya-multilingual", {"laya_ocr_adapter": VERSION,
                                       "ocr": label_ocr.IDENTITY, "schema": schema,
                                       "served_model": entry.model}, payload, [png])
    record = model_cache.lookup(fields) if cache_read else None
    if record is None:
        body = laya_v.post(entry, payload, timeout)
        ms, cached = (time.perf_counter() - started) * 1000, False
    else:
        body, ms, cached = record["answer"], record["ms"], True
    scores = laya_v.scores_of(body, options, expected_model="laya-rl-agent")
    if cache_validator is not None and not cache_validator(scores):
        raise laya_v.LayaVError("Laya OCR scores failed the rerank validator")
    if not cached:
        model_cache.store(fields, body, ms)
    return {"text": json.dumps(scores, ensure_ascii=False), "ms": round(ms),
            "usage": body["usage"], "finish_reason": "stop", "model": entry.model,
            "cached": cached}
