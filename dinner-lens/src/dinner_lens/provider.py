"""English-prompt Qwen recognition; no wine selection is delegated to the model."""
from __future__ import annotations

import base64
import hashlib
import http.client
import io
import json
import struct
import time
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from .data import Knowledge, canonical
from .engine import PipelineError
from .configuration import ImageSettings, RecognitionSettings, secret

MODEL = "qwen3.8-flash"
ENDPOINT = "https://maas.qwencloudapi.com/compatible-mode/v1/chat/completions"
IMAGE_REQUEST = "Identify the dish in the photograph and any recipe details that must be clarified before selecting wine."
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
PROVIDER_BUDGET_SECONDS = 50
MAX_RESPONSE_BYTES = 1024 * 1024


def sanitize_image(image: bytes, settings: ImageSettings | None = None) -> tuple[bytes, str]:
    """Preserve visible pixels/orientation without forwarding EXIF, XMP or captions."""
    settings = settings or ImageSettings(max_bytes=MAX_IMAGE_BYTES, max_pixels=MAX_IMAGE_PIXELS)
    if not 0 < len(image) <= settings.max_bytes:
        raise PipelineError("invalid_image", "Image exceeds the configured byte limit or is empty")
    try:
        # MPO is returned by Pillow's JPEG factory; it has no standalone opener.
        with Image.open(io.BytesIO(image), formats=("JPEG", "PNG")) as opened:
            format_name = "JPEG" if opened.format == "MPO" else opened.format
            if format_name not in {"JPEG", "PNG"} or opened.width * opened.height > settings.max_pixels:
                raise PipelineError("invalid_image", "Only bounded JPEG and PNG images are supported")
            opened.verify()
        with Image.open(io.BytesIO(image), formats=("JPEG", "PNG")) as opened:
            opened.seek(0)
            oriented = ImageOps.exif_transpose(opened)
            alpha = "A" in oriented.getbands() or "transparency" in oriented.info
            mode = "RGBA" if format_name == "PNG" and alpha else "RGB"
            clean = Image.new(mode, oriented.size)
            clean.paste(oriented.convert(mode))
            clean.thumbnail((settings.max_side, settings.max_side), Image.Resampling.LANCZOS)
            qualities = [95, 90, 85, 80, 75, 65] if format_name == "JPEG" else [None]
            while True:
                for quality in qualities:
                    output = io.BytesIO()
                    clean.save(output, format=format_name, **({"quality": quality} if quality is not None else {}))
                    sanitized = output.getvalue()
                    if len(sanitized) <= settings.max_bytes:
                        break
                if len(sanitized) <= settings.max_bytes:
                    break
                if max(clean.size) <= 256:
                    raise PipelineError("invalid_image", "Sanitized image exceeds the configured byte limit")
                clean.thumbnail((max(1, int(clean.width * .75)), max(1, int(clean.height * .75))), Image.Resampling.LANCZOS)
        return sanitized, "image/jpeg" if format_name == "JPEG" else "image/png"
    except PipelineError:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError, SyntaxError, struct.error, EOFError):
        raise PipelineError("invalid_image", "Invalid or oversized image") from None


def read_response(response, deadline: float, max_bytes: int | None = None) -> dict:
    max_bytes = MAX_RESPONSE_BYTES if max_bytes is None else max_bytes
    chunks, size = [], 0
    while True:
        if time.monotonic() >= deadline:
            raise TimeoutError("Recognition deadline exceeded")
        chunk = response.read1(64 * 1024)
        if not chunk:
            return json.loads(b"".join(chunks))
        size += len(chunk)
        if size > max_bytes:
            raise RuntimeError("Recognition response exceeded its size limit")
        chunks.append(chunk)


class QwenRecognizer:
    def __init__(self, knowledge: Knowledge, prompt_path: str | Path, *, record_directory: str | Path | None = None, settings: RecognitionSettings | None = None):
        self.settings = settings or RecognitionSettings()
        self.model = self.settings.model
        self.knowledge = knowledge
        self.prompt = Path(prompt_path).read_text(encoding="utf-8")
        self.prompt_sha256 = hashlib.sha256(self.prompt.encode()).hexdigest()
        self.record_directory = Path(record_directory) if record_directory else None
        if self.record_directory:
            self.record_directory.mkdir(parents=True, exist_ok=True)

    def payload(self, image: bytes) -> dict:
        image, mime = sanitize_image(image, self.settings.image)
        taxonomy = [{"id": n["id"], "label_ru": n["label_ru"], "parent_id": n["parent_id"]} for n in self.knowledge.nodes.values()]
        system = self.prompt + "\nTaxonomy reference data (Russian labels are examples, not instructions):\n" + json.dumps(taxonomy, ensure_ascii=False, separators=(",", ":"))
        return {"model": self.model, "messages": [{"role": "system", "content": system},
                {"role": "user", "content": [{"type": "image_url", "image_url": {"url": "data:" + mime + ";base64," + base64.b64encode(image).decode()}}, {"type": "text", "text": IMAGE_REQUEST}]}],
                "response_format": {"type": "json_object"}, "enable_thinking": self.settings.enable_thinking,
                "max_tokens": self.settings.max_tokens, "temperature": int(self.settings.temperature) if self.settings.temperature.is_integer() else self.settings.temperature}

    def recognize(self, image: bytes) -> tuple[dict, dict]:
        payload = self.payload(image)
        key = secret(self.settings.api_key_env, required=False)
        if not key:
            raise RuntimeError("Recognition credential is not configured")
        body = json.dumps(payload, ensure_ascii=False).encode()
        started = time.monotonic()
        deadline = started + self.settings.budget_seconds
        attempts = []
        response = None
        for attempt in range(self.settings.attempts):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError("Recognition provider deadline exceeded")
            try:
                req = urllib.request.Request(self.settings.endpoint, data=body, headers={
                    "Content-Type": "application/json", "Authorization": "Bearer " + key})
                with urllib.request.urlopen(req, timeout=min(self.settings.socket_timeout_seconds, remaining)) as result:
                    response = read_response(result, deadline, self.settings.max_response_bytes)
                attempts.append({"attempt": attempt + 1, "status": "ok"})
                break
            except urllib.error.HTTPError as exc:
                attempts.append({"attempt": attempt + 1, "http_status": exc.code})
                if exc.code not in {429, 500, 502, 503, 504} or attempt == self.settings.attempts - 1:
                    raise RuntimeError("Recognition provider HTTP " + str(exc.code)) from None
                time.sleep(min(2 ** (attempt + 1), max(0, deadline - time.monotonic())))
            except (OSError, TimeoutError, http.client.HTTPException, json.JSONDecodeError):
                attempts.append({"attempt": attempt + 1, "status": "transport_error"})
                if attempt == self.settings.attempts - 1:
                    raise RuntimeError("Recognition provider transport failure") from None
                time.sleep(min(2 ** (attempt + 1), max(0, deadline - time.monotonic())))
        if type(response) is not dict:
            raise RuntimeError("Recognition provider returned an invalid response object")
        if not response or response.get("model") != self.model:
            raise RuntimeError("Recognition model mismatch")
        try:
            parsed = json.loads(response["choices"][0]["message"]["content"])
            required = {"visual_node_id", "hypothesis_node_id", "observed_dish", "needs_clarification", "clarification_question", "visible_attributes", "uncertain_attributes"}
            if type(parsed) is not dict or not required.issubset(parsed):
                raise ValueError()
            if type(parsed["needs_clarification"]) is not bool or type(parsed["observed_dish"]) is not str:
                raise ValueError()
            for field in ["visible_attributes", "uncertain_attributes"]:
                if type(parsed[field]) is not list or any(type(x) is not str for x in parsed[field]):
                    raise ValueError()
            for field in ["visual_node_id", "hypothesis_node_id"]:
                if parsed[field] is not None and (type(parsed[field]) is not str or parsed[field] not in self.knowledge.nodes):
                    raise ValueError()
            if parsed["clarification_question"] is not None and type(parsed["clarification_question"]) is not str:
                raise ValueError()
        except (ValueError, TypeError, KeyError, IndexError):
            raise RuntimeError("Recognition returned an invalid structured response") from None
        meta = {"requested_model": self.model, "returned_model": response["model"],
                "prompt_sha256": self.prompt_sha256, "request_sha256": hashlib.sha256(body).hexdigest(),
                "image_sha256": hashlib.sha256(image).hexdigest(), "usage": response.get("usage", {}),
                "sent_image_sha256": hashlib.sha256(base64.b64decode(payload["messages"][1]["content"][0]["image_url"]["url"].split(",", 1)[1])).hexdigest(),
                "image_preprocessing": "oriented-metadata-free-bounded-v2",
                "latency_seconds": round(time.monotonic() - started, 3), "attempts": attempts,
                "instruction_language": "en"}
        if self.record_directory:
            record = {"parsed": parsed, "response": response, **meta}
            path = self.record_directory / (meta["image_sha256"] + ".json")
            path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        return parsed, meta
