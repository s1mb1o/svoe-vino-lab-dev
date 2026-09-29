"""Segment wine bottles in one group photo and prepare matcher crops."""

import base64
import binascii
from dataclasses import dataclass, replace
from io import BytesIO
import json
import math
import socket
from time import monotonic
import urllib.error
import urllib.parse
import urllib.request
import uuid

from PIL import Image, ImageChops, ImageOps, UnidentifiedImageError


MAX_SIDE = 1600
MAX_INSTANCES = 500
MAX_BOTTLES = 100
MAX_MASK_BASE64_CHARS = 2 * 1024 * 1024
MAX_SAM3_RESPONSE_BYTES = 16 * 1024 * 1024
MAX_RESPONSE_MEDIA_BYTES = 6 * 1024 * 1024
SAM3_TIMEOUT_SECONDS = 300.0
DETECTION_THRESHOLD = 0.4
MASK_THRESHOLD = 128
DUPLICATE_IOU = 0.9
GROUP_PROMPTS = ("wine bottle", "wine label")
MIN_LABEL_CONTAINMENT = 0.8
MIN_LABEL_SHORT_SIDE_RATIO = 0.025
MIN_LABEL_AREA_RATIO = 0.0006
MIN_LABEL_CENTER_Y = 0.2
MAX_LABEL_CENTER_Y = 0.9
MAX_EDGE_FRAGMENT_TOP = 0.85
ROW_TOP_TOLERANCE = 0.15
MIN_ROW_HEIGHT_RATIO = 0.65


class GroupMatchError(RuntimeError):
    """A SAM3 dependency or response is not usable in group or single-image matching."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass(frozen=True)
class SegmentedBottle:
    """One validated bottle segment and its internal matcher crop."""

    id: str
    segmentation_score: float
    box: tuple[float, float, float, float]
    mask: str
    crop: bytes
    label_crop: bytes


@dataclass(frozen=True)
class SegmentedGroup:
    """The normalized group photo and its validated bottle segments."""

    width: int
    height: int
    preview: str
    bottles: tuple[SegmentedBottle, ...]
    detected_count: int
    truncated: bool


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Make every redirect an HTTP error."""

    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


def segment_group(image_bytes: bytes, endpoint: str | None,
                  timeout: float = SAM3_TIMEOUT_SECONDS,
                  opener=None) -> SegmentedGroup:
    """Return bottle segments that contain one usable visible label."""
    image, jpeg = _normalize_image(image_bytes)
    instances = _request_sam3(
        jpeg, image.width, image.height, endpoint, timeout=timeout, opener=opener)
    valid = sorted(
        (instance for instance in instances
         if instance["label"] == GROUP_PROMPTS[0]
         and instance["score"] >= DETECTION_THRESHOLD),
        key=lambda instance: instance["score"],
        reverse=True,
    )
    labels = []
    for instance in instances:
        if (instance["label"] != GROUP_PROMPTS[1]
                or instance["score"] < DETECTION_THRESHOLD):
            continue
        prepared = _instance_mask(image, instance)
        if prepared is not None and _label_has_information(image.size, prepared):
            labels.append((instance, prepared))
    preview = _data_url("image/jpeg", jpeg)
    media_bytes = len(preview.encode("ascii"))
    candidates = []
    for instance in valid:
        bottle_mask = _instance_mask(image, instance)
        best_label = None if bottle_mask is None else _best_label(bottle_mask, labels)
        if bottle_mask is None or best_label is None:
            continue
        prepared = _prepare_bottle(image, instance, bottle_mask)
        if prepared is None:
            continue
        box, mask, crop = prepared
        label_crop = _prepare_match_crop(
            image, best_label[1], padding_ratio=0.08, maximum_size=(640, 640))
        if box[1] >= MAX_EDGE_FRAGMENT_TOP:
            continue
        if any(_box_overlap(box, bottle.box) >= DUPLICATE_IOU
               for bottle in candidates):
            continue
        mask_url = _data_url("image/png", mask)
        candidates.append(SegmentedBottle(
            id="",
            segmentation_score=instance["score"],
            box=box,
            mask=mask_url,
            crop=crop,
            label_crop=label_crop,
        ))

    candidates = _filter_relative_scale(candidates)
    bottles = []
    truncated = False
    for bottle in candidates:
        if len(bottles) >= MAX_BOTTLES:
            truncated = True
            break
        mask_url = bottle.mask
        if media_bytes + len(mask_url.encode("ascii")) > MAX_RESPONSE_MEDIA_BYTES:
            truncated = True
            break
        media_bytes += len(mask_url.encode("ascii"))
        bottles.append(bottle)

    bottles.sort(key=lambda bottle: (
        math.floor(bottle.box[1] * 8), bottle.box[0]))
    bottles = [replace(bottle, id="b%d" % index)
               for index, bottle in enumerate(bottles, 1)]
    return SegmentedGroup(
        width=image.width,
        height=image.height,
        preview=preview,
        bottles=tuple(bottles),
        detected_count=len(valid),
        truncated=truncated,
    )


def _normalize_image(image_bytes: bytes) -> tuple[Image.Image, bytes]:
    try:
        with Image.open(BytesIO(image_bytes)) as opened:
            opened.seek(0)
            image = ImageOps.exif_transpose(opened)
            alpha = image.mode in ("RGBA", "LA", "PA") or (
                image.mode == "P" and "transparency" in image.info)
            image = image.convert("RGBA" if alpha else "RGB")
    except (OSError, UnidentifiedImageError) as exc:
        raise GroupMatchError(400, "image cannot be decoded") from exc
    if image.mode == "RGBA":
        white = Image.new("RGBA", image.size, (255, 255, 255, 255))
        image = Image.alpha_composite(white, image).convert("RGB")
    if max(image.size) > MAX_SIDE:
        scale = MAX_SIDE / max(image.size)
        size = (max(1, round(image.width * scale)),
                max(1, round(image.height * scale)))
        image = image.resize(size, Image.Resampling.LANCZOS)
    output = BytesIO()
    image.save(output, "JPEG", quality=86)
    return image, output.getvalue()


def _request_sam3(jpeg: bytes, width: int, height: int, endpoint: str | None,
                  timeout: float, opener=None, *, text=None,
                  require_labels=False) -> list[dict]:
    """Send one SAM3 request and return its validated instances.

    With no `text`, the request sends the group nouns to `/segment_multi`, and each
    instance MUST carry one of the group labels. With `text`, the request sends one
    `/segment` prompt; `require_labels` then asks each instance for a label.
    """
    multi = text is None
    url = _sam3_url(endpoint, multi=multi)
    body, content_type = _multipart(jpeg, text)
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": content_type, "Accept": "application/json"},
        method="POST",
    )
    client = opener or urllib.request.build_opener(_NoRedirect())
    deadline = monotonic() + timeout
    for attempt in range(2):
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise GroupMatchError(504, "SAM3 request timed out")
        try:
            with client.open(request, timeout=remaining) as response:
                declared = response.headers.get("Content-Length")
                if declared is not None:
                    try:
                        if int(declared) > MAX_SAM3_RESPONSE_BYTES:
                            raise GroupMatchError(502, "SAM3 response is too large")
                    except ValueError as exc:
                        raise GroupMatchError(502, "SAM3 response has invalid headers") from exc
                payload = response.read(MAX_SAM3_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as exc:
            exc.close()
            if exc.code >= 500 and attempt == 0:
                continue
            raise GroupMatchError(502, "SAM3 service returned HTTP %d" % exc.code) from exc
        except (TimeoutError, socket.timeout) as exc:
            if attempt == 0 and monotonic() < deadline:
                continue
            raise GroupMatchError(504, "SAM3 request timed out") from exc
        except (urllib.error.URLError, OSError) as exc:
            if attempt == 0 and monotonic() < deadline:
                continue
            if monotonic() >= deadline:
                raise GroupMatchError(504, "SAM3 request timed out") from exc
            raise GroupMatchError(502, "SAM3 service is unavailable") from exc
        if len(payload) > MAX_SAM3_RESPONSE_BYTES:
            raise GroupMatchError(502, "SAM3 response is too large")
        if not payload:
            if attempt == 0:
                continue
            raise GroupMatchError(502, "SAM3 service returned an empty response")
        try:
            answer = json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GroupMatchError(502, "SAM3 service returned invalid JSON") from exc
        return _validate_sam3(
            answer, width, height, labels=GROUP_PROMPTS if multi else None,
            require_labels=require_labels)
    raise GroupMatchError(502, "SAM3 service is unavailable")


def _sam3_url(endpoint: str | None, *, multi=False) -> str:
    if not isinstance(endpoint, str) or not endpoint:
        raise GroupMatchError(503, "SAM3_ENDPOINT is not configured")
    try:
        parsed = urllib.parse.urlsplit(endpoint)
        _ = parsed.port
        if (parsed.scheme not in ("http", "https") or not parsed.netloc
                or parsed.username is not None or parsed.password is not None
                or parsed.query or parsed.fragment):
            raise ValueError("invalid endpoint")
    except ValueError as exc:
        raise GroupMatchError(503, "SAM3_ENDPOINT is not configured correctly") from exc
    return endpoint.rstrip("/") + ("/segment_multi" if multi else "/segment")


def _multipart(jpeg: bytes, text=None) -> tuple[bytes, str]:
    boundary = "svoe-vino-%s" % uuid.uuid4().hex
    fields = (
        ("texts", ", ".join(GROUP_PROMPTS).encode("utf-8")) if text is None
        else ("text", text.encode("utf-8")),
        ("threshold", b"0.4"),
        ("mask_threshold", b"0.5"),
        ("return_masks", b"true"),
    )
    parts = [
        ("--%s\r\n" % boundary).encode("ascii"),
        b'Content-Disposition: form-data; name="image"; filename="shelf.jpg"\r\n',
        b"Content-Type: image/jpeg\r\n\r\n",
        jpeg,
        b"\r\n",
    ]
    for name, value in fields:
        parts.extend((
            ("--%s\r\n" % boundary).encode("ascii"),
            ('Content-Disposition: form-data; name="%s"\r\n\r\n' % name).encode("ascii"),
            value,
            b"\r\n",
        ))
    parts.append(("--%s--\r\n" % boundary).encode("ascii"))
    return b"".join(parts), "multipart/form-data; boundary=%s" % boundary


def _validate_sam3(answer, width: int, height: int, *, labels=None,
                   require_labels=False) -> list[dict]:
    if not isinstance(answer, dict):
        raise GroupMatchError(502, "SAM3 response MUST be an object")
    instances = answer.get("instances")
    if (type(answer.get("width")) is not int or answer["width"] != width
            or type(answer.get("height")) is not int or answer["height"] != height
            or not isinstance(instances, list)
            or len(instances) > MAX_INSTANCES
            or type(answer.get("count")) is not int
            or answer["count"] != len(instances)):
        raise GroupMatchError(502, "SAM3 response has invalid dimensions or count")
    validated = []
    for instance in instances:
        if not isinstance(instance, dict):
            raise GroupMatchError(502, "SAM3 response has an invalid instance")
        score = instance.get("score")
        box = instance.get("box")
        mask = instance.get("mask_png_b64")
        if (isinstance(score, bool) or not isinstance(score, (int, float))
                or not math.isfinite(score) or score < 0 or score > 1
                or not isinstance(box, list) or len(box) != 4
                or any(isinstance(value, bool) or not isinstance(value, (int, float))
                       or not math.isfinite(value) for value in box)
                or box[2] <= box[0] or box[3] <= box[1]
                or not isinstance(mask, str)
                or len(mask) > MAX_MASK_BASE64_CHARS):
            raise GroupMatchError(502, "SAM3 response has an invalid instance")
        result = {
            "score": float(score),
            "box": tuple(float(value) for value in box),
            "mask_png_b64": mask,
        }
        if labels is not None or require_labels:
            label = instance.get("label")
            if (not isinstance(label, str) or not label.strip()
                    or (labels is not None and label.strip().lower() not in labels)):
                raise GroupMatchError(502, "SAM3 response has an invalid label")
            result["label"] = label.strip().lower()
        if require_labels:
            area = instance.get("area")
            if area is not None and (
                    isinstance(area, bool) or not isinstance(area, (int, float))
                    or not math.isfinite(area) or not 0 <= area <= width * height):
                raise GroupMatchError(502, "SAM3 response has an invalid area")
            result["area"] = area
        validated.append(result)
    return validated


def _instance_mask(image: Image.Image, instance: dict):
    """Return one clamped pixel box and its binary cropped mask, or None for an
    empty segment."""
    width, height = image.size
    raw_box = instance["box"]
    left = max(0, min(width, math.floor(raw_box[0])))
    top = max(0, min(height, math.floor(raw_box[1])))
    right = max(0, min(width, math.ceil(raw_box[2])))
    bottom = max(0, min(height, math.ceil(raw_box[3])))
    if right <= left or bottom <= top:
        return None
    try:
        mask_bytes = base64.b64decode(instance["mask_png_b64"], validate=True)
        with Image.open(BytesIO(mask_bytes)) as opened:
            if opened.format != "PNG" or opened.size != image.size:
                raise GroupMatchError(502, "SAM3 mask dimensions are invalid")
            mask = opened.convert("L")
    except (binascii.Error, OSError, UnidentifiedImageError) as exc:
        raise GroupMatchError(502, "SAM3 mask is not a valid PNG") from exc
    mask = mask.crop((left, top, right, bottom)).point(
        lambda value: 255 if value >= MASK_THRESHOLD else 0)
    if mask.getbbox() is None:
        return None
    return (left, top, right, bottom), mask


def _label_has_information(image_size, prepared) -> bool:
    """Reject a label that is too small for useful visual recognition."""
    width, height = image_size
    (left, top, right, bottom), mask = prepared
    short_side = min(right - left, bottom - top)
    area = mask.histogram()[255]
    return (short_side >= min(width, height) * MIN_LABEL_SHORT_SIDE_RATIO
            and area >= width * height * MIN_LABEL_AREA_RATIO)


def _mask_intersection_area(first, second) -> int:
    first_box, first_mask = first
    second_box, second_mask = second
    left = max(first_box[0], second_box[0])
    top = max(first_box[1], second_box[1])
    right = min(first_box[2], second_box[2])
    bottom = min(first_box[3], second_box[3])
    if right <= left or bottom <= top:
        return 0
    first_part = first_mask.crop((
        left - first_box[0], top - first_box[1],
        right - first_box[0], bottom - first_box[1],
    ))
    second_part = second_mask.crop((
        left - second_box[0], top - second_box[1],
        right - second_box[0], bottom - second_box[1],
    ))
    return ImageChops.multiply(first_part, second_part).histogram()[255]


def _best_label(bottle, labels):
    """Return the best visible label inside one bottle mask, or None."""
    bottle_box, bottle_mask = bottle
    bottle_height = bottle_box[3] - bottle_box[1]
    best = None
    best_score = -1.0
    for instance, label in labels:
        label_box, label_mask = label
        center_x = (label_box[0] + label_box[2]) / 2
        center_y = (label_box[1] + label_box[3]) / 2
        if not (bottle_box[0] <= center_x < bottle_box[2]
                and bottle_box[1] <= center_y < bottle_box[3]):
            continue
        bottle_x = min(bottle_mask.width - 1, max(0, int(center_x - bottle_box[0])))
        bottle_y = min(bottle_mask.height - 1, max(0, int(center_y - bottle_box[1])))
        if bottle_mask.getpixel((bottle_x, bottle_y)) < MASK_THRESHOLD:
            continue
        relative_y = (center_y - bottle_box[1]) / max(1, bottle_height)
        if not MIN_LABEL_CENTER_Y <= relative_y <= MAX_LABEL_CENTER_Y:
            continue
        label_area = label_mask.histogram()[255]
        containment = _mask_intersection_area(bottle, label) / max(1, label_area)
        if containment < MIN_LABEL_CONTAINMENT:
            continue
        score = instance["score"] * containment
        if score > best_score:
            best = (instance, label)
            best_score = score
    return best


def _filter_relative_scale(bottles):
    """Reject a rear or reflected fragment that is small for its shelf row."""
    rows = []
    for bottle in sorted(bottles, key=lambda item: item.box[1]):
        row = next((items for items in rows
                    if abs(bottle.box[1] - _median([item.box[1]
                                                   for item in items]))
                    <= ROW_TOP_TOLERANCE), None)
        if row is None:
            row = []
            rows.append(row)
        row.append(bottle)
    kept = []
    for row in rows:
        median_height = _median([item.box[3] - item.box[1] for item in row])
        kept.extend(item for item in row
                    if item.box[3] - item.box[1]
                    >= median_height * MIN_ROW_HEIGHT_RATIO)
    return kept


def _median(values):
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def _prepare_bottle(image: Image.Image, instance: dict, prepared=None):
    if prepared is None:
        prepared = _instance_mask(image, instance)
    if prepared is None:
        return None
    (left, top, right, bottom), mask = prepared
    width, height = image.size
    overlay = Image.new("RGBA", mask.size, (237, 217, 170, 0))
    overlay.putalpha(mask)
    mask_output = BytesIO()
    overlay.save(mask_output, "PNG")

    crop = _prepare_match_crop(
        image, prepared, padding_ratio=0.05, maximum_size=(640, 960))
    return (
        (left / width, top / height, right / width, bottom / height),
        mask_output.getvalue(),
        crop,
    )


def _prepare_match_crop(image: Image.Image, prepared, *, padding_ratio, maximum_size):
    """Return one masked JPEG crop for matching."""
    (left, top, right, bottom), mask = prepared
    width, height = image.size
    padding = max(2, round((right - left) * padding_ratio))
    crop_box = (
        max(0, left - padding),
        max(0, top - padding),
        min(width, right + padding),
        min(height, bottom + padding),
    )
    crop = image.crop(crop_box)
    crop_mask = Image.new("L", crop.size, 0)
    crop_mask.paste(mask, (left - crop_box[0], top - crop_box[1]))
    crop = Image.composite(crop, Image.new("RGB", crop.size, "white"), crop_mask)
    if crop.width > maximum_size[0] or crop.height > maximum_size[1]:
        crop.thumbnail(maximum_size, Image.Resampling.LANCZOS)
    crop_output = BytesIO()
    crop.save(crop_output, "JPEG", quality=92)
    return crop_output.getvalue()


def _box_overlap(a, b) -> float:
    intersection = (max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
                    * max(0.0, min(a[3], b[3]) - max(a[1], b[1])))
    union = ((a[2] - a[0]) * (a[3] - a[1])
             + (b[2] - b[0]) * (b[3] - b[1]) - intersection)
    return intersection / union if union else 0.0


def _data_url(media_type: str, body: bytes) -> str:
    return "data:%s;base64,%s" % (media_type, base64.b64encode(body).decode("ascii"))
