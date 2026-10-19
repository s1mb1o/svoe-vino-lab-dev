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
from .configuration import ImageSettings, ProviderSettings, RecognitionSettings, secret

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


class ProviderFailure(RuntimeError):
    """Finite error codes only; never expose provider bodies, credentials or URLs."""
    def __init__(self, code: str, attempts: list | None = None):
        super().__init__(code)
        self.code = code
        self.attempts = attempts or []


class QwenRecognizer:
    def __init__(self, knowledge: Knowledge, prompt_path: str | Path, *, record_directory: str | Path | None = None, settings: RecognitionSettings | None = None):
        self.settings = settings or RecognitionSettings()
        self.model = self.settings.model
        self.fallback_model = self.settings.fallback.model if self.settings.fallback else None
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
        payload = {"model": self.model, "messages": [{"role": "system", "content": system},
                {"role": "user", "content": [{"type": "image_url", "image_url": {"url": "data:" + mime + ";base64," + base64.b64encode(image).decode()}}, {"type": "text", "text": IMAGE_REQUEST}]}],
                "response_format": {"type": "json_object"}, "enable_thinking": self.settings.enable_thinking,
                "max_tokens": self.settings.max_tokens, "temperature": int(self.settings.temperature) if self.settings.temperature.is_integer() else self.settings.temperature}

        return self._backend_payload(payload, self.settings)

    @staticmethod
    def _backend_payload(payload: dict, settings: ProviderSettings) -> dict:
        # Copy the request structure; both providers receive identical sanitized pixels and instructions.
        payload = dict(payload)
        payload.update(model=settings.model, max_tokens=settings.max_tokens,
                       temperature=int(settings.temperature) if settings.temperature.is_integer() else settings.temperature)
        payload.pop("chat_template_kwargs", None)
        payload["enable_thinking"] = settings.enable_thinking
        if settings.protocol == "vllm":
            payload.pop("enable_thinking")
            payload["chat_template_kwargs"] = {"enable_thinking": settings.enable_thinking}
        return payload

    def _recognize_provider(self, image: bytes, payload: dict, settings: ProviderSettings) -> tuple[dict, dict, dict]:
        key = secret(settings.api_key_env, required=False) if settings.api_key_env else None
        if settings.api_key_env and not key:
            raise ProviderFailure("credential_missing")
        body = json.dumps(payload, ensure_ascii=False).encode()
        started = time.monotonic()
        deadline = started + settings.budget_seconds
        attempts = []
        response = None
        for attempt in range(settings.attempts):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ProviderFailure("deadline_exceeded", attempts)
            try:
                req = urllib.request.Request(settings.endpoint, data=body, headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + key} if key else {})})
                with urllib.request.urlopen(req, timeout=min(settings.socket_timeout_seconds, remaining)) as result:
                    response = read_response(result, deadline, settings.max_response_bytes)
                attempts.append({"attempt": attempt + 1, "status": "ok"})
                break
            except urllib.error.HTTPError as exc:
                attempts.append({"attempt": attempt + 1, "http_status": exc.code})
                if exc.code not in {429, 500, 502, 503, 504} or attempt == settings.attempts - 1:
                    raise ProviderFailure("http_" + str(exc.code), attempts) from None
                time.sleep(min(2 ** (attempt + 1), max(0, deadline - time.monotonic())))
            except (OSError, TimeoutError, http.client.HTTPException, json.JSONDecodeError, UnicodeError, RecursionError):
                attempts.append({"attempt": attempt + 1, "status": "transport_error"})
                if attempt == settings.attempts - 1:
                    raise ProviderFailure("transport_failure", attempts) from None
                time.sleep(min(2 ** (attempt + 1), max(0, deadline - time.monotonic())))
            except RuntimeError:
                raise ProviderFailure("response_too_large", attempts) from None
        if type(response) is not dict:
            raise ProviderFailure("invalid_response", attempts)
        if not response or response.get("model") != (settings.response_model or settings.model):
            raise ProviderFailure("model_mismatch", attempts)
        try:
            if response["choices"][0].get("finish_reason") == "length":
                raise ProviderFailure("truncated_response", attempts)
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
        except (ValueError, TypeError, KeyError, IndexError, AttributeError, RecursionError):
            raise ProviderFailure("invalid_structured_response", attempts) from None
        meta = {"requested_model": settings.model, "returned_model": response["model"],
                "prompt_sha256": self.prompt_sha256, "request_sha256": hashlib.sha256(body).hexdigest(),
                "image_sha256": hashlib.sha256(image).hexdigest(), "usage": response.get("usage", {}),
                "sent_image_sha256": hashlib.sha256(base64.b64decode(payload["messages"][1]["content"][0]["image_url"]["url"].split(",", 1)[1])).hexdigest(),
                "image_preprocessing": "oriented-metadata-free-bounded-v2",
                "latency_seconds": round(time.monotonic() - started, 3), "attempts": attempts,
                "instruction_language": "en"}
        return parsed, meta, response

    def recognize(self, image: bytes) -> tuple[dict, dict]:
        # Invalid image input fails before fallback or any paid provider call.
        original_payload = self.payload(image)
        started = time.monotonic()
        receipts = []
        backends = [("primary", self.settings)]
        if self.settings.fallback:
            backends.append(("fallback", self.settings.fallback))
        for role, settings in backends:
            attempt_started = time.monotonic()
            payload = self._backend_payload(original_payload, settings)
            try:
                parsed, meta, response = self._recognize_provider(image, payload, settings)
            except ProviderFailure as exc:
                receipts.append({"role": role, "model": settings.model, "status": "failed",
                                 "error_code": exc.code, "attempts": exc.attempts,
                                 "latency_seconds": round(time.monotonic() - attempt_started, 3)})
                continue
            receipts.append({"role": role, "model": settings.model, "status": "ok",
                             "attempts": meta["attempts"], "latency_seconds": meta["latency_seconds"]})
            meta.update(primary_model=self.model, fallback_model=self.fallback_model,
                        selected_provider=role, fallback_used=role == "fallback",
                        provider_attempts=receipts, total_latency_seconds=round(time.monotonic() - started, 3))
            if self.record_directory:
                path = self.record_directory / (meta["image_sha256"] + ".json")
                path.write_text(json.dumps({"parsed": parsed, "response": response, **meta}, ensure_ascii=False, indent=2), encoding="utf-8")
            return parsed, meta
        error = ProviderFailure("all_providers_failed")
        error.provider_attempts = receipts
        raise error
