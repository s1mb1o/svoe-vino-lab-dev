"""Experimental label crop checks and selection of one retrieval space.

Thresholds are trial settings, not calibrated probabilities. White padding does not
count as unrelated content. Blur is measured inside the mask at a fixed label scale.
Frame contact is recorded as a flag: it cannot prove that a close-up is incomplete.
"""
import base64
import io
import math

import numpy as np
from PIL import Image

import alternatives
from embeddings import ConfigError

SCORE = "label ranking when crop quality, top cosine and margin pass; otherwise bottle ranking"
DEFAULTS = {
    "min_score": 0.90,
    "min_margin": 0.01,
    "min_purity": 0.80,
    "min_detector_score": 0.70,
    "min_native_side": 128,
    "min_input_side": 128,
    "min_sharpness": 80.0,
    "min_package_overlap": 0.80,
}
QUALITY_VERSION = 1
NORMALIZED_WIDTH = 256
WHITE_CUTOFF = 245


def check_options(raw):
    if not isinstance(raw, dict):
        raise ConfigError("label_gate MUST be a mapping")
    unknown = sorted(set(raw) - set(DEFAULTS))
    if unknown:
        raise ConfigError("label_gate takes no %s" % ", ".join(unknown))
    out = dict(DEFAULTS, **raw)
    ranges = {"min_score": (-1, 1), "min_margin": (0, 2), "min_purity": (0, 1),
              "min_detector_score": (0, 1), "min_package_overlap": (0, 1)}
    for key, value in out.items():
        low, high = ranges.get(key, (0, float("inf")))
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or not low <= value <= high):
            raise ConfigError("label_gate.%s MUST be a finite number in [%s, %s]"
                              % (key, low, high))
        if key in ("min_native_side", "min_input_side"):
            if not isinstance(value, int) or value < 1:
                raise ConfigError("label_gate.%s MUST be a positive integer" % key)
    return out


def check_views(views):
    if set(views) != {"full", "label"}:
        raise ConfigError("label_gate requires both full and label query views")
    steps = views["label"]
    if not steps or steps[0] != {"step": "segment", "target": "label"}:
        raise ConfigError("label_gate requires a label view that starts with segment target label")
    # Direct mask mapping supports resize and colour changes. Padding and a separate
    # segmenter change the geometry, so they need a different mapping implementation.
    if any(step["step"] not in {"segment", "remove_background", "white_background", "resize"}
           for step in steps):
        raise ConfigError("label_gate supports label crop, background and resize steps only")


def _mask(item):
    with Image.open(io.BytesIO(base64.b64decode(item["mask_png_b64"]))) as image:
        return image.convert("L").point(lambda p: 255 if p >= 128 else 0)


def _prepared_mask(mask, source_size, box, size):
    sx, sy = mask.width / source_size[0], mask.height / source_size[1]
    bounds = (box[0] * sx, box[1] * sy, box[2] * sx, box[3] * sy)
    mapped = mask.transform(size, Image.Transform.EXTENT, bounds, Image.Resampling.NEAREST)
    return np.asarray(mapped) >= 128


def _bbox(mask):
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def _sharpness(rgb, mask, box):
    x1, y1, x2, y2 = box
    size = (NORMALIZED_WIDTH, min(4096, max(1, round((y2 - y1) * NORMALIZED_WIDTH / (x2 - x1)))))
    grey = Image.fromarray(rgb).crop(box).convert("L").resize(size, Image.Resampling.BOX)
    inside = np.asarray(Image.fromarray(mask.astype(np.uint8) * 255).crop(box)
                        .resize(size, Image.Resampling.NEAREST)) > 0
    # Erode by three pixels to exclude the artificial outline and padding.
    for _ in range(3):
        padded = np.pad(inside, 1, constant_values=False)
        inside = np.logical_and.reduce([
            padded[dy:dy + inside.shape[0], dx:dx + inside.shape[1]]
            for dy in range(3) for dx in range(3)])
    values = np.asarray(grey, dtype=np.float32)
    lap = (values[:-2, 1:-1] + values[2:, 1:-1] + values[1:-1, :-2]
           + values[1:-1, 2:] - 4 * values[1:-1, 1:-1])
    picked = lap[inside[1:-1, 1:-1]]
    return float(np.var(picked)) if picked.size else 0.0


def _measure(image, prepared, context, options):
    """Return serializable measurements and rejection reasons, with no model call."""
    out = {"version": QUALITY_VERSION, "passed": False, "reasons": [], "signals": {}}
    if prepared is None or not context or not context.get("cut"):
        out["reasons"] = [context.get("error", "no_label") if context else "no_label"]
        return out
    instances = context["instances"]
    on_main_bottle = context.get("on_main_bottle", True)
    main = alternatives.label_instance(instances, on_main_bottle=on_main_bottle)
    if main is None:
        out["reasons"] = ["no_label"]
        return out
    _, _, box = context["cut"]
    main_mask = _mask(main)
    raw_box = main_mask.getbbox()
    if raw_box is None:
        out["reasons"] = ["empty_label_mask"]
        return out
    sx, sy = main_mask.width / image.width, main_mask.height / image.height
    native_box = (raw_box[0] / sx, raw_box[1] / sy, raw_box[2] / sx, raw_box[3] / sy)
    native_size = [native_box[2] - native_box[0], native_box[3] - native_box[1]]
    mapped_main = _prepared_mask(main_mask, image.size, box, prepared.size)
    input_box = _bbox(mapped_main)
    if input_box is None:
        out["reasons"] = ["main_label_outside_crop"]
        return out
    labels = mapped_main.copy()
    scale = alternatives._copy_scale(image, main)
    for item in alternatives.body_labels(instances, main, image.width * scale,
                                         image.height * scale, on_main_bottle=on_main_bottle):
        labels |= _prepared_mask(_mask(item), image.size, box, prepared.size)
    rgb = np.asarray(prepared.convert("RGB"))
    content = rgb.min(axis=2) < WHITE_CUTOFF
    content_count = int(content.sum())
    purity = float((labels & content).sum() / content_count) if content_count else 0.0
    input_size = [input_box[2] - input_box[0], input_box[3] - input_box[1]]
    sharpness = _sharpness(rgb, mapped_main, input_box)
    package_box = context.get("package_box")
    overlap = None
    if package_box is not None:
        width = max(0, min(native_box[2], package_box[2]) - max(native_box[0], package_box[0]))
        height = max(0, min(native_box[3], package_box[3]) - max(native_box[1], package_box[1]))
        overlap = width * height / (native_size[0] * native_size[1])
    detector = float(main["score"])
    edges = sum((native_box[0] <= 1, native_box[1] <= 1,
                 native_box[2] >= image.width - 1, native_box[3] >= image.height - 1))
    out["signals"] = {
        "detector_score": round(detector, 6) if math.isfinite(detector) else None,
        "purity": round(purity, 6),
        "native_label_size": [round(v, 2) for v in native_size],
        "input_label_size": input_size, "sharpness": round(sharpness, 4),
        "sharpness_width": NORMALIZED_WIDTH, "white_cutoff": WHITE_CUTOFF,
        "package_overlap": round(overlap, 6) if overlap is not None else None,
        "source_frame_edges": int(edges),
    }
    checks = [
        (content_count == 0, "empty_content"),
        (not math.isfinite(detector) or detector < options["min_detector_score"], "weak_detection"),
        (min(native_size) < options["min_native_side"], "insufficient_native_detail"),
        (min(input_size) < options["min_input_side"], "insufficient_input_detail"),
        (purity < options["min_purity"], "unrelated_content"),
        (sharpness < options["min_sharpness"], "insufficient_sharpness"),
        (overlap is not None and overlap < options["min_package_overlap"], "label_on_other_package"),
    ]
    out["reasons"] = [reason for rejected, reason in checks if rejected]
    out["passed"] = not out["reasons"]
    return out


def measure(image, prepared, context, options):
    """Invalid cached label data rejects the label without breaking bottle fallback."""
    try:
        return _measure(image, prepared, context, options)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return {"version": QUALITY_VERSION, "passed": False, "reasons": ["invalid_label_data"],
                "signals": {}, "error": str(exc)}


def choose(available, label_top, quality, options):
    """Select an entire ranking; cosine values from different spaces are never mixed."""
    score = label_top[0]["cosine"] if label_top else None
    margin = score - label_top[1]["cosine"] if len(label_top) >= 2 else None
    reasons = []
    if not quality or not quality["passed"]:
        reasons.append("label_quality_rejected")
    elif "label" not in available or score is None:
        reasons.append("no_label_ranking")
    else:
        if score < options["min_score"]:
            reasons.append("label_score_below_threshold")
        if margin is None or margin + 1e-8 < options["min_margin"]:
            reasons.append("label_margin_below_threshold")
    selected = "full" if reasons else "label"
    if selected not in available:
        selected = None
        reasons.append("no_fallback_ranking")
    return {"selected_view": selected, "reasons": reasons,
            "label_score": score, "label_margin": round(margin, 6) if margin is not None else None,
            "quality": quality}
