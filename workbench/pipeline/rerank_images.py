"""Save sent re-rank PNGs. Recover older inputs from local caches alone."""
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile

from PIL import Image

import model_cache
from checked_read_cache import CheckedReadCache

DIGEST = re.compile(r"[0-9a-f]{64}\Z")
REQUESTS = CheckedReadCache(max_entries=4, max_bytes=16 * 1024 * 1024)


class ImageUnavailable(Exception):
    """The saved run has no verifiable VLM input image."""


def image_path(digest):
    if not isinstance(digest, str) or not DIGEST.fullmatch(digest):
        raise ImageUnavailable("The run recorded no valid VLM image hash.")
    root = Path(model_cache.ROOT).parent / "rerank-images"
    path = root / digest[:2] / (digest + ".png")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ImageUnavailable("The VLM image path is invalid.")
    return path


def metadata(png, kind, provenance="recorded"):
    with Image.open(io.BytesIO(png)) as image:
        if image.format != "PNG":
            raise ImageUnavailable("The VLM input is not a PNG.")
        width, height = image.size
    return {"sha256": hashlib.sha256(png).hexdigest(), "kind": kind,
            "width": width, "height": height, "provenance": provenance}


def save(png, kind):
    """Save the exact bytes before the VLM call. A write error does not stop ranking."""
    info = {"sha256": hashlib.sha256(png).hexdigest(), "kind": kind}
    temporary = None
    try:
        info.update(metadata(png, kind))
        path = image_path(info["sha256"])
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == info["sha256"]:
            return info
        fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=info["sha256"] + ".")
        with os.fdopen(fd, "wb") as stream:
            stream.write(png)
        os.replace(temporary, path)
        temporary = None
    except (OSError, ValueError, ImageUnavailable) as exc:
        info["error"] = "Cannot save the VLM input image: %s" % exc
    finally:
        if temporary:
            try:
                os.unlink(temporary)
            except OSError:
                pass
    return info


def saved(result):
    """Read a stored input and check its identity. Do not depend on the source photo."""
    info = result.get("input_image")
    if not isinstance(info, dict):
        return None
    try:
        png = image_path(info.get("sha256")).read_bytes()
        actual = metadata(png, info.get("kind") or result.get("picture"))
    except (OSError, ValueError, ImageUnavailable):
        return None
    if actual["sha256"] != info.get("sha256"):
        return None
    return png, actual


def evidence(row):
    """Use recorded trace or candidate evidence. Do not read current cluster rules."""
    for part in (row.get("trace") or {}).get("steps") or []:
        if part.get("id") == "cluster_rules" and isinstance(part.get("out"), dict):
            return part["out"]
    for candidate in row.get("candidates") or []:
        value = candidate.get("explain")
        if isinstance(value, dict) and value.get("kind") == "cluster_rules":
            return value
    return None


def _cache_images(result, spec):
    """Find sent hashes for this recorded evidence request and response."""
    import cluster_rerank
    questions = result.get("questions") or []
    if result.get("mode") != "evidence" or not questions:
        return set()
    prompt = cluster_rerank.SCORE_PROMPT % {"questions": "\n\n".join(
        "%s: %s\nOptions: %s" % (q["id"], q["question"], ", ".join(
            json.dumps(option, ensure_ascii=False) for option in q["options"]))
        for q in questions)}
    model = (result.get("model") or (spec.get("rerank") or {}).get("model")
             or (spec.get("rerank") or {}).get("vlm"))
    if not model:
        return set()
    directory = Path(model_cache.ROOT) / re.sub(r"[^A-Za-z0-9._-]", "-", model)
    responses = {a["raw_text"].strip() for a in result.get("attempts") or []
                 if isinstance(a.get("raw_text"), str)}
    scores = result.get("option_scores") or result.get("raw_option_scores")
    def load():
        index = {}
        for path in directory.glob("*/*.json"):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
                request = record["request"]
                if (request.get("model") != model or record.get("key") != model_cache.key_of(request)
                        or path.stem != record.get("key")):
                    continue
                content = request["prompt"][0]["content"]
                text = record["answer"]["choices"][0]["message"]["content"].strip()
                images = request.get("images") or []
                if len(images) != 1 or not DIGEST.fullmatch(images[0]):
                    continue
                for p in content:
                    if p.get("type") == "text":
                        key = (p.get("text"), model_cache.canonical(json.loads(text)))
                        index.setdefault(key, []).append((text, images[0]))
            except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError):
                continue
        return index
    paths = [directory, *(p for p in directory.glob("*") if p.is_dir())]
    index = REQUESTS.get((str(directory), model), paths, load, copy_value=False)
    return {digest for text, digest in index.get((prompt, model_cache.canonical(scores)), [])
            if not responses or text in responses}


def _direct_cache(png, result, spec):
    """Try current endpoint addresses only as cache locators. Verify saved responses."""
    import cluster_rerank
    import embeddings
    import label_rules
    import vlm_config
    questions = result.get("questions") or []
    if result.get("mode") != "evidence" or not questions:
        return False
    try:
        _, config, _ = embeddings.read_config()
        entry = vlm_config.entry(config, (spec.get("rerank") or {}).get("vlm"))
    except (OSError, embeddings.ConfigError, vlm_config.VlmConfigError):
        return False
    prompt = cluster_rerank.SCORE_PROMPT % {"questions": "\n\n".join(
        "%s: %s\nOptions: %s" % (q["id"], q["question"], ", ".join(
            json.dumps(o, ensure_ascii=False) for o in q["options"])) for q in questions)}
    schema = {"type": "object", "additionalProperties": False, "properties": {
        q["id"]: {"type": "object", "additionalProperties": False, "properties": {
            option: {"type": "integer", "minimum": 0, "maximum": 100} for option in q["options"]},
            "required": q["options"]} for q in questions}, "required": [q["id"] for q in questions]}
    options = spec.get("rerank") or {}
    content = [{"type": "image_url", "image_url": {"url": label_rules.data_url(png)}},
               {"type": "text", "text": prompt}]
    payload = {"model": entry.model, "temperature": 0, "max_tokens": options.get("max_tokens"),
               "response_format": {"type": "json_schema", "json_schema": {"name": "answer", "schema": schema}},
               "messages": [{"role": "user", "content": content}]}
    if entry.thinking_field == "top_level":
        payload["enable_thinking"] = options.get("thinking")
    else:
        payload["chat_template_kwargs"] = {"enable_thinking": options.get("thinking")}
    fields = model_cache.vlm_fields(entry.url, payload)
    try:
        record = json.loads(Path(model_cache.path_of(fields)).read_text(encoding="utf-8"))
        if record.get("request") != fields or record.get("key") != model_cache.key_of(fields):
            return False
        text = record["answer"]["choices"][0]["message"]["content"].strip()
        responses = {a["raw_text"].strip() for a in result.get("attempts") or []
                     if isinstance(a.get("raw_text"), str)}
        return (text in responses if responses else json.loads(text) ==
                (result.get("option_scores") or result.get("raw_option_scores")))
    except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError):
        return False


def resolve(result, spec, photo_path):
    """Return exact stored or hash-verified reconstructed bytes. Never call a model."""
    hit = saved(result)
    if hit:
        return hit
    info = result.get("input_image") if isinstance(result.get("input_image"), dict) else {}
    expected = {info["sha256"]} if DIGEST.fullmatch(str(info.get("sha256", ""))) else None
    if not photo_path:
        raise ImageUnavailable("The original photo is unavailable for VLM input recovery.")
    import cluster_rerank
    import derive
    import embedding_run
    image, _icc = derive.open_image(photo_path)
    side = (spec.get("rerank") or {}).get("side")
    if isinstance(side, bool) or not isinstance(side, int) or side < 64:
        raise ImageUnavailable("The run recorded no VLM input size.")
    kind = info.get("kind") or result.get("picture")
    candidates = []
    if kind == "photo":
        png = cluster_rerank.png_of(image, side)
        candidates.append(png)
    elif kind == "label":
        endpoint = (spec.get("sam3") or {}).get("endpoint") or derive.SAM3_ENDPOINT
        client = embedding_run.CachedSam3(endpoint)
        try:
            # Old runs used different label selection rules. Accept only sent bytes.
            for on_bottle, union in ((True, True), (False, True), (False, False), (True, False)):
                try:
                    cut = embedding_run.cuts_of(image, {"label"}, client,
                        label_on_main_bottle=on_bottle, label_mask_union=union).get("label")
                except (derive.Sam3Unavailable, OSError, ValueError):
                    continue
                if cut:
                    png = cluster_rerank.png_of(cut[1], side)
                    candidates.append(png)
                    if (hashlib.sha256(png).hexdigest() in expected if expected is not None
                            else _direct_cache(png, result, spec)):
                        return png, metadata(png, kind, "cache")
        finally:
            client.session.close()
    if expected is None:
        for png in candidates:
            if _direct_cache(png, result, spec):
                return png, metadata(png, kind, "cache")
        expected = _cache_images(result, spec)
    if not expected:
        raise ImageUnavailable("The VLM input image was not saved and no matching cached request is available.")
    for png in candidates:
        if hashlib.sha256(png).hexdigest() in expected:
            return png, metadata(png, kind, "cache")
    raise ImageUnavailable("The cached crop does not match the image sent to the VLM.")
