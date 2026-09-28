"""Rebuild the image inputs of one recorded matcher result.

The match run stores the source image, the backend URL, and the ranked answer.
The matcher configuration stores the pipeline graph. The label crop cache stores
the exact derived crop by source bytes and crop settings. This module joins those
records without running an embedding model or a VLM.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import re
import sys
import urllib.parse
from functools import lru_cache
from pathlib import Path

import yaml
from PIL import Image


class InputRebuildError(Exception):
    """The recorded model inputs cannot be rebuilt."""


def _matcher_modules(matcher_root: Path):
    root = str(matcher_root)
    if root not in sys.path:
        sys.path.insert(0, root)
    from svm import config as config_module  # noqa: PLC0415
    from svm import images, labelcrop  # noqa: PLC0415

    return config_module, images, labelcrop


def _pipeline_from_url(url: str) -> str:
    path = urllib.parse.urlsplit(url).path
    match = re.search(r"/v1/pipelines/([^/]+)/predict$", path)
    return urllib.parse.unquote(match.group(1)) if match else ""


def _port_of(url: str) -> int | None:
    try:
        return urllib.parse.urlsplit(url).port
    except ValueError:
        return None


@lru_cache(maxsize=16)
def _config_header(path: str, mtime_ns: int) -> dict:
    del mtime_ns
    try:
        return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    except (OSError, ValueError, yaml.YAMLError):
        return {}


def find_matcher_config(matcher_root: Path, backend_url: str) -> tuple[Path, str]:
    """Find the local matcher configuration and pipeline of a backend URL."""
    pipeline = _pipeline_from_url(backend_url)
    port = _port_of(backend_url)
    candidates = []
    for path in sorted(matcher_root.glob("config*.yaml")):
        try:
            stat = path.stat()
        except OSError:
            continue
        document = _config_header(str(path), stat.st_mtime_ns)
        pipelines = document.get("pipelines") or {}
        name = pipeline or str(document.get("default_pipeline") or "")
        if name not in pipelines:
            continue
        configured_port = int(((document.get("server") or {}).get("port") or 8158))
        candidates.append((configured_port == port, path, name))
    exact = [item for item in candidates if item[0]]
    selected = exact or candidates
    if len(selected) != 1:
        reason = "no matching configuration" if not selected else "more than one configuration matches"
        raise InputRebuildError(f"{reason} for backend {backend_url}")
    return selected[0][1], selected[0][2]


@lru_cache(maxsize=8)
def _load_config(path: str, mtime_ns: int):
    del mtime_ns
    config_module, _images, _labelcrop = _matcher_modules(Path(path).parent)
    return config_module.load(path)


def _config(path: Path):
    return _load_config(str(path), path.stat().st_mtime_ns)


def _png_bytes(image: Image.Image) -> bytes:
    output = io.BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


def _jpeg_bytes(image: Image.Image, quality: int = 92) -> bytes:
    output = io.BytesIO()
    image.save(output, "JPEG", quality=quality)
    return output.getvalue()


def _encoded_input(image: Image.Image, mime: str = "image/png") -> tuple[bytes, str]:
    body = _jpeg_bytes(image) if mime == "image/jpeg" else _png_bytes(image)
    return body, "data:%s;base64,%s" % (mime, base64.b64encode(body).decode("ascii"))


def _resize_long_side(image: Image.Image, side: int, upscale: bool) -> Image.Image:
    if side <= 0:
        return image
    scale = side / float(max(image.size))
    if scale >= 1.0 and not upscale:
        return image
    if abs(scale - 1.0) <= 1e-3:
        return image
    return image.resize(
        (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
        Image.Resampling.LANCZOS,
    )


def _walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _has_explain(candidates: list[dict], kind: str) -> bool:
    return any(item.get("kind") == kind for item in _walk(candidates))


@lru_cache(maxsize=8)
def _card_producers(path: str, mtime_ns: int) -> dict[str, str]:
    del mtime_ns
    out = {}
    with open(path, encoding="utf-8") as source:
        for line in source:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            slug = str(row.get("slug") or "")
            if slug:
                out[slug] = str(row.get("producer") or "").strip().lower()
    return out


def _difference_ran(cfg, spec, candidates: list[dict]) -> bool:
    if _has_explain(candidates, "difference"):
        return True
    if len(candidates) < 2:
        return False
    try:
        stat = cfg.catalog_file.stat()
        producers = _card_producers(str(cfg.catalog_file), stat.st_mtime_ns)
        top = candidates[0]
        producer = producers.get(str(top.get("slug") or ""), "")
        top_score = float(top.get("score"))
        max_gap = float((spec.raw.get("group") or {})["max_gap"])
    except (OSError, KeyError, TypeError, ValueError):
        return False
    group = []
    for candidate in candidates:
        try:
            score = float(candidate.get("score"))
        except (TypeError, ValueError):
            continue
        if (producers.get(str(candidate.get("slug") or ""), "") == producer
                and top_score - score <= max_gap):
            group.append(candidate)
    return bool(producer) and len(group) >= 2


def _query_crop(cfg, pipeline_name: str, image: Image.Image, matcher_root: Path):
    _config_module, _images, labelcrop = _matcher_modules(matcher_root)
    spec = cfg.pipelines[pipeline_name]
    query = dict(spec.raw.get("query") or {})
    cache_dir = str(query.get("cache_dir") or "")
    if cache_dir and not Path(cache_dir).is_absolute():
        query["cache_dir"] = str(cfg.source.parent / cache_dir)
    # A preview MUST NOT call SAM3. A cache miss means that the exact crop is
    # unavailable on this host.
    if query.get("mode", "none") != "none":
        query["cache_only"] = True
    cropper = labelcrop.build(query)
    try:
        return cropper.crop(image) if cropper is not None else image
    except labelcrop.CropUnavailable as exc:
        raise InputRebuildError(str(exc)) from exc
    finally:
        if cropper is not None:
            cropper.close()


class _Collector:
    def __init__(self, cfg, image: Image.Image, candidates: list[dict], matcher_root: Path):
        self.cfg = cfg
        self.image = image
        self.candidates = candidates
        self.matcher_root = matcher_root
        self.items: list[dict] = []
        self.notes: list[str] = []
        self._seen_pipelines: set[str] = set()

    def add(self, image: Image.Image, use: str, pipeline: str, label: str,
            model: str, mime: str = "image/png") -> None:
        body, data_url = _encoded_input(image, mime)
        digest = hashlib.sha256(body).hexdigest()
        for item in self.items:
            if item["sha256"] == digest:
                if use not in item["uses"]:
                    item["uses"].append(use)
                if pipeline not in item["pipelines"]:
                    item["pipelines"].append(pipeline)
                return
        self.items.append({
            "sha256": digest,
            "uses": [use],
            "pipelines": [pipeline],
            "label": label,
            "model": model,
            "width": image.width,
            "height": image.height,
            "mime": mime,
            "src": data_url,
        })

    def embedding(self, name: str, spec) -> None:
        if name in self._seen_pipelines:
            return
        self._seen_pipelines.add(name)
        _config_module, images, _labelcrop = _matcher_modules(self.matcher_root)
        try:
            source = _query_crop(self.cfg, name, self.image, self.matcher_root)
        except InputRebuildError as exc:
            self.notes.append(f"{name}: {exc}")
            return
        prepared = images.prepare(source, self.cfg.resize_mode, self.cfg.background)
        path_name = spec.path
        settings = spec.settings
        mime = "image/png"
        if path_name in ("siglip2", "dinov3") and settings.get("input_size"):
            side = int(settings["input_size"])
            prepared = prepared.resize((side, side), Image.Resampling.BICUBIC)
        elif path_name == "gateway":
            prepared = _resize_long_side(prepared, int(settings.get("max_side", 768)), False)
            mime = "image/jpeg"
        model = str(settings.get("model") or settings.get("repo") or path_name)
        self.add(prepared.convert("RGB"), "Embedding", name, spec.label, model, mime)

    def vlm_crop(self, name: str, crop_ref: str, raw: dict, cluster: bool) -> None:
        try:
            picture = _query_crop(self.cfg, crop_ref, self.image, self.matcher_root)
        except InputRebuildError as exc:
            self.notes.append(f"{name}: {exc}")
            return
        picture = picture.convert("RGB")
        settings = raw.get("vlm") or raw.get("ocr") or {}
        model = str(settings.get("model") or ("VLM" if cluster else "PaddleOCR-VL"))
        if cluster:
            picture = _resize_long_side(picture, int(settings.get("side", 1536)), True)
        else:
            picture = _resize_long_side(picture, int(settings.get("max_side", 1024)), False)
        self.add(picture, "VLM", name, self.cfg.pipelines[name].label, model)

    def collect(self, name: str) -> None:
        spec = self.cfg.pipelines.get(name)
        if spec is None:
            self.notes.append(f"pipeline `{name}` is not in {self.cfg.source.name}")
            return
        kind = spec.kind
        raw = spec.raw
        if kind == "embed":
            self.embedding(name, spec)
            return
        if kind == "ensemble":
            for member in spec.members:
                self.collect(str(member.get("pipeline") or ""))
            return
        if kind == "barcode":
            # A mapped code returns one exact candidate with score 1.0 and does
            # not call the visual base.
            if (len(self.candidates) == 1
                    and float(self.candidates[0].get("score") or 0.0) == 1.0):
                self.notes.append("The barcode or QR lookup answered this photo. No embedding model ran.")
                return
            self.collect(str((raw.get("base") or raw.get("embed") or {}).get("pipeline") or ""))
            return
        if kind in ("rerank", "text"):
            self.collect(str((raw.get("embed") or {}).get("pipeline") or ""))
            return
        if kind == "ocr":
            self.collect(str((raw.get("embed") or {}).get("pipeline") or ""))
            detector = raw.get("detector") or {}
            if detector.get("enabled", True):
                self.notes.append(
                    f"{name}: the run did not store the temporary detector crop that PaddleOCR-VL read.")
            elif self.candidates:
                settings = raw.get("ocr") or {}
                picture = _resize_long_side(
                    self.image.convert("RGB"), int(settings.get("max_side", 1024)), False)
                self.add(picture, "VLM", name, spec.label,
                         str(settings.get("model") or "PaddleOCR-VL"))
            return
        if kind == "vlm_rerank":
            self.collect(str((raw.get("embed") or {}).get("pipeline") or ""))
            if self.candidates:
                model = str((raw.get("model") or {}).get("repo") or "VLM reranker")
                self.add(self.image.convert("RGB"), "VLM", name, spec.label, model)
                self.notes.append(
                    f"{name}: the run did not store the exact catalogue image item IDs that the VLM compared.")
            return
        if kind == "difference":
            self.collect(str((raw.get("base") or {}).get("pipeline") or ""))
            if _difference_ran(self.cfg, spec, self.candidates):
                crop_ref = str((raw.get("crop") or {}).get("pipeline") or "")
                if crop_ref:
                    self.vlm_crop(name, crop_ref, raw, False)
            return
        if kind == "cluster_rules":
            self.collect(str((raw.get("base") or {}).get("pipeline") or ""))
            if _has_explain(self.candidates, "cluster_rules"):
                crop_ref = str((raw.get("crop") or {}).get("pipeline") or "")
                if crop_ref:
                    self.vlm_crop(name, crop_ref, raw, True)
            return
        if kind == "remote":
            self.notes.append(f"{name}: this remote pipeline reports no local embedding or VLM input.")
            return
        self.notes.append(f"{name}: input previews are not implemented for pipeline kind `{kind}`.")


def build_model_inputs(matcher_root: Path, backend_url: str, image_path: Path,
                       image_sha256: str, candidates: list[dict]) -> dict:
    """Return data-URL previews of the model-bound images of one run result."""
    body = image_path.read_bytes()
    digest = hashlib.sha256(body).hexdigest()
    if image_sha256 and digest != image_sha256:
        raise InputRebuildError(
            "the source image changed after the run; exact model inputs cannot be rebuilt")
    config_path, pipeline = find_matcher_config(matcher_root, backend_url)
    cfg = _config(config_path)
    _config_module, images, _labelcrop = _matcher_modules(matcher_root)
    image = images.load_bytes(body, cfg.background)
    collector = _Collector(cfg, image, candidates or [], matcher_root)
    collector.collect(pipeline)
    return {
        "pipeline": pipeline,
        "config": config_path.name,
        "inputs": collector.items,
        "notes": collector.notes,
    }
