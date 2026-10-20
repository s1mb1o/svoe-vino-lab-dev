"""Bounded, optional small-object recovery for the semantic selector.

Requests use RGB and primary detector masks only. No target, annotation or
selection policy is supplied to either model head.
"""

import base64
from io import BytesIO
import json
import math
from time import monotonic
import urllib.error
import urllib.request
import uuid

import numpy as np
from PIL import Image

from .group import (
    GroupMatchError,
    MAX_SAM3_RESPONSE_BYTES,
    _NoRedirect,
    _sam3_url,
    _validate_sam3,
    _instance_mask,
)

CENTRAL_NOUNS = ("wine bottle", "bottle", "bottle held in hand")


def _mask(item):
    with Image.open(
        BytesIO(base64.b64decode(item["mask_png_b64"], validate=True))
    ) as image:
        return np.asarray(image.convert("L")) >= 128


def _encoded(mask):
    stream = BytesIO()
    Image.fromarray(mask.astype("uint8") * 255).save(stream, "PNG")
    return base64.b64encode(stream.getvalue()).decode()


def small_scene(image, decision):
    bottles = [
        c
        for c in decision.candidates
        if c["eligible_for_selection"] and c["kind"] in ("wine bottle", "bottle")
    ]
    return (
        decision.selection_mode == "fallback"
        and bool(bottles)
        and max(c["box"][3] - c["box"][1] for c in bottles) <= 0.2 * max(image.size)
    )


def request_optional(image, endpoint, timeout, *, points=None, opener=None):
    """One bounded PNG request; optional failure is handled by the caller."""
    boundary = "selector-%s" % uuid.uuid4().hex
    stream = BytesIO()
    image.save(stream, "PNG")
    fields = (
        {
            "texts": ", ".join(CENTRAL_NOUNS),
            "threshold": "0.4",
            "mask_threshold": "0.5",
            "return_masks": "true",
        }
        if points is None
        else {
            "points": json.dumps(points),
            "labels": "[1,1,1]",
            "multimask": "true",
            "mask_threshold": "0.5",
        }
    )
    body = [
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="image"; filename="crop.png"\r\n',
        b"Content-Type: image/png\r\n\r\n",
        stream.getvalue(),
        b"\r\n",
    ]
    for name, value in fields.items():
        body.extend(
            (
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode(),
                b"\r\n",
            )
        )
    body.append(f"--{boundary}--\r\n".encode())
    url = _sam3_url(endpoint)
    if points is not None:
        url = url.removesuffix("/segment_multi") + "/segment_point"
    request = urllib.request.Request(
        url,
        data=b"".join(body),
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        },
    )
    client = opener or urllib.request.build_opener(_NoRedirect())
    try:
        with client.open(request, timeout=timeout) as response:
            payload = response.read(MAX_SAM3_RESPONSE_BYTES + 1)
        if len(payload) > MAX_SAM3_RESPONSE_BYTES:
            raise GroupMatchError(502, "SAM3 response is too large")
        answer = json.loads(payload)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise GroupMatchError(502, "Optional SAM3 refinement is unavailable") from exc
    if (
        points is not None
        and isinstance(answer, dict)
        and isinstance(answer.get("instances"), list)
    ):
        for item in answer["instances"]:
            if isinstance(item, dict):
                item["label"] = "bottle"
    validated = _validate_sam3(
        answer, *image.size, labels=("bottle",) if points is not None else CENTRAL_NOUNS
    )
    for item in validated:
        _instance_mask(image, item)
    return validated


def _project(item, roi, size):
    small = _mask(item)
    full = np.zeros((size[1], size[0]), dtype=bool)
    full[roi[1] : roi[3], roi[0] : roi[2]] = small
    return full


def _tracker_choice(original, responses, roi, size):
    seed = _mask(original)
    bounds = Image.fromarray(seed).getbbox()
    limit = max(4, min(bounds[2] - bounds[0], bounds[3] - bounds[1]) * 0.1)
    choices = []
    for item in responses:
        if item["score"] < 0.4:
            continue
        full = _project(item, roi, size)
        box = Image.fromarray(full).getbbox()
        if box is None or any(
            abs(a - bottom) > limit for a, bottom in zip(bounds, box)
        ):
            continue
        iou = float((full & seed).sum() / max(1, (full | seed).sum()))
        if iou >= 0.5:
            choices.append((item["score"], iou, full, box))
    if not choices:
        return None
    _, _, full, box = max(choices, key=lambda c: (c[0], c[1]))
    # Refined geometry drives selection; the old complete rectangle still drives
    # conservative RGB retention in the crop, including undetected paper.
    return dict(
        original,
        box=box,
        mask_png_b64=_encoded(full),
        primary_box=list(original["box"]),
        preserve_box=[
            max(0, math.floor(original["box"][0])),
            max(0, math.floor(original["box"][1])),
            min(size[0], math.ceil(original["box"][2])),
            min(size[1], math.ceil(original["box"][3])),
        ],
        geometry_source="local_tracker",
    )


def enhance(image, instances, decision, request, *, deadline):
    """At most two localizations and one central scan, sharing one deadline.

    The scan only adds complete interior detections. A crop-edge fragment cannot
    stand in for the full bottle's geometry. Supplied caches call this function
    explicitly during collection; normal supplied-instance replay never does.
    """
    if not small_scene(image, decision):
        return instances, None
    effective = list(instances)
    audit = {"profile": "small-bottle-localization-20261020", "requests": []}
    bottles = [
        c
        for c in decision.candidates
        if c["eligible_for_selection"] and c["kind"] in ("wine bottle", "bottle")
    ]

    def distance(candidate):
        return math.hypot(
            (candidate["box"][0] + candidate["box"][2] - image.width) / 2,
            (candidate["box"][1] + candidate["box"][3] - image.height) / 2,
        )

    bottles.sort(key=lambda c: (distance(c), c["source_index"]))

    def call(roi, points, source_index=None):
        remaining = deadline - monotonic()
        record = {"roi": list(roi), "points": points, "source_index": source_index}
        audit["requests"].append(record)
        if remaining <= 0:
            record["status"] = "budget_exhausted"
            return []
        try:
            result = request(image.crop(roi), points=points, timeout=remaining)
            record.update(status="ok", returned=len(result))
            return result
        except GroupMatchError:
            record["status"] = "unavailable"
            return []

    if len(bottles) >= 2 and distance(bottles[1]) - distance(bottles[0]) <= 5:
        for candidate in bottles[:2]:
            index = candidate["source_index"]
            left, top, right, bottom = candidate["box"]
            margin = round(max(right - left, bottom - top) * 0.2)
            roi = (
                max(0, left - margin),
                max(0, top - margin),
                min(image.width, right + margin),
                min(image.height, bottom + margin),
            )
            mask = _mask(effective[index])
            ys, _ = np.nonzero(mask)
            points = []
            for quantile in (0.1, 0.5, 0.9):
                y = int(np.quantile(ys, quantile))
                xs = np.flatnonzero(mask[y])
                points.append([int(np.median(xs)) - roi[0], y - roi[1]])
            responses = call(roi, points, index)
            refined = _tracker_choice(effective[index], responses, roi, image.size)
            audit["requests"][-1]["accepted"] = refined is not None
            if refined is not None:
                effective[index] = refined

    side = min(160, *image.size)
    x, y = (image.width - side) // 2, (image.height - side) // 2
    roi = (x, y, x + side, y + side)
    added = 0
    edge_context = max(2, round(side * 0.05))
    for item in call(roi, None):
        small = _mask(item)
        bounds = Image.fromarray(small).getbbox()
        if bounds is None:
            continue
        left, top, right, bottom = bounds
        if (
            (x > 0 and left <= edge_context)
            or (y > 0 and top <= edge_context)
            or (x + side < image.width and right >= side - edge_context)
            or (y + side < image.height and bottom >= side - edge_context)
        ):
            continue
        full = _project(item, roi, image.size)
        effective.append(
            dict(
                item,
                label="bottle",
                box=Image.fromarray(full).getbbox(),
                mask_png_b64=_encoded(full),
                geometry_source="central_recovery",
            )
        )
        added += 1
    audit["requests"][-1]["accepted"] = added
    return effective, audit
