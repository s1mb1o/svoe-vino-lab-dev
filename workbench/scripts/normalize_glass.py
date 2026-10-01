#!/usr/bin/env python3
"""Build non-destructive catalogue images with canonical dark bottle glass.

The database remains read-only.  The utility uses the existing `package` derivative as
the bottle silhouette and the existing `label` derivative as a protection mask.  It
does not call SAM3 and it never changes an image in the catalogue store.
"""
import argparse
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

import labdb  # noqa: E402

DEFAULT_DB = ROOT / "data" / "catalog" / "catalog.sqlite3"
DEFAULT_TARGET = "#13271f"
DEFAULT_STRENGTH = 0.92
DEFAULT_LABEL_MARGIN = 0.003
MANIFEST_NAME = "manifest.json"


class NormalizeError(Exception):
    """The requested normalization cannot be completed."""


def parse_colour(value):
    """Return an RGB tuple for a `#rrggbb` command-line value."""
    text = value.strip()
    if len(text) != 7 or not text.startswith("#"):
        raise argparse.ArgumentTypeError("the colour MUST have the form #rrggbb")
    try:
        colour = tuple(int(text[index:index + 2], 16) for index in (1, 3, 5))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("the colour MUST have the form #rrggbb") from exc
    return colour


def _readonly(path):
    absolute = os.path.abspath(path)
    return sqlite3.connect("file:%s?mode=ro" % quote(absolute), uri=True)


def _stored(db_path, folder, digest, extension):
    return os.path.join(labdb.image_dir(db_path, folder), "%s.%s" % (digest, extension))


def records(db_path, slugs=(), categories=(), all_states=False, limit=None):
    """Return the selected `main` images and their existing derivative paths."""
    where = ["wi.image_type = 'main'"]
    values = []
    if not all_states:
        where.append("w.state = 'Active'")
    if slugs:
        where.append("w.wine_slug IN (%s)" % ",".join("?" for _ in slugs))
        values.extend(slugs)
    if categories:
        where.append("w.category IN (%s)" % ",".join("?" for _ in categories))
        values.extend(categories)
    query = """
        SELECT w.wine_slug, w.category, wi.sha256, src.folder, src.extension,
               p.sha256, pi.folder, pi.extension,
               p.box_left, p.box_top, p.box_right, p.box_bottom,
               l.sha256, li.folder, li.extension,
               l.box_left, l.box_top, l.box_right, l.box_bottom
          FROM wine_catalog w
          JOIN wine_image wi ON wi.wine_slug = w.wine_slug
          JOIN image src ON src.sha256 = wi.sha256
          LEFT JOIN image_derivative p
                 ON p.source_sha256 = wi.sha256 AND p.kind = 'package'
          LEFT JOIN image pi ON pi.sha256 = p.sha256
          LEFT JOIN image_derivative l
                 ON l.source_sha256 = wi.sha256 AND l.kind = 'label'
          LEFT JOIN image li ON li.sha256 = l.sha256
         WHERE %s
         ORDER BY w.rowid, wi.sha256
    """ % " AND ".join(where)
    if limit is not None:
        query += " LIMIT ?"
        values.append(limit)
    with _readonly(db_path) as conn:
        rows = conn.execute(query, values).fetchall()
    result = []
    for row in rows:
        (slug, category, source_sha, source_folder, source_extension,
         package_sha, package_folder, package_extension, *tail) = row
        package_box = tuple(tail[:4]) if package_sha else None
        label_sha, label_folder, label_extension = tail[4:7]
        label_box = tuple(tail[7:11]) if label_sha else None
        result.append({
            "slug": slug,
            "category": category,
            "source_sha256": source_sha,
            "source": _stored(db_path, source_folder, source_sha, source_extension),
            "package_sha256": package_sha,
            "package": (_stored(db_path, package_folder, package_sha, package_extension)
                        if package_sha else None),
            "package_box": package_box,
            "label_sha256": label_sha,
            "label": (_stored(db_path, label_folder, label_sha, label_extension)
                      if label_sha else None),
            "label_box": label_box,
        })
    return result


def placed_alpha(path, box, size):
    """Place the alpha channel of a derivative back on its original canvas."""
    if not path or not box:
        raise NormalizeError("the derivative is absent")
    left, top, right, bottom = box
    if min(left, top) < 0 or right > size[0] or bottom > size[1]:
        raise NormalizeError("the derivative box %r lies outside %r" % (box, size))
    with Image.open(path) as stored:
        derivative = ImageOps.exif_transpose(stored).convert("RGBA")
    expected = (right - left, bottom - top)
    if derivative.size != expected:
        raise NormalizeError("the derivative is %r, its database box is %r"
                             % (derivative.size, expected))
    canvas = Image.new("L", size, 0)
    canvas.paste(derivative.getchannel("A"), (left, top))
    return canvas


def _smoothstep(low, high, value):
    scaled = np.clip((value - low) / (high - low), 0.0, 1.0)
    return scaled * scaled * (3.0 - 2.0 * scaled)


def protect_label(label_mask, long_side, margin_ratio=DEFAULT_LABEL_MARGIN):
    """Grow and feather a label mask so its antialiased edge stays untouched."""
    margin = max(1, int(round(long_side * margin_ratio)))
    # OpenCV's morphology is linear in the pixel count for this rectangular kernel;
    # Pillow's generic MaxFilter becomes prohibitively slow on the 60 MP catalogue files.
    kernel_size = min(101, margin * 2 + 1)
    alpha = np.asarray(label_mask, dtype=np.uint8)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    protected = cv2.dilate(alpha, kernel)
    protected = cv2.GaussianBlur(protected, (0, 0), sigmaX=max(0.75, margin / 3))
    return Image.fromarray(protected, "L")


def normalize_image(source, package_mask, label_mask, target=(19, 39, 31),
                    strength=DEFAULT_STRENGTH, label_margin=DEFAULT_LABEL_MARGIN,
                    chunk_rows=512):
    """Return `(image, statistics)` after changing bottle pixels outside the label.

    Local luminance becomes shading of the canonical colour.  Bright neutral pixels are
    protected so a white cap, foil, and specular highlights stay recognisable.  The
    original alpha channel and all pixels under the grown label mask remain unchanged.
    """
    source = source.convert("RGBA")
    if package_mask.size != source.size or label_mask.size != source.size:
        raise NormalizeError("the source and both masks MUST have one size")
    if not 0.0 <= strength <= 1.0:
        raise NormalizeError("strength MUST be between 0 and 1")
    if chunk_rows < 1:
        raise NormalizeError("chunk_rows MUST be positive")

    rgba = np.asarray(source, dtype=np.uint8)
    package = np.asarray(package_mask, dtype=np.uint8)
    protected_image = protect_label(label_mask, max(source.size), label_margin)
    protected = np.asarray(protected_image, dtype=np.uint8)
    base = np.asarray(target, dtype=np.float32).reshape(1, 1, 3) / 255.0
    result = np.array(rgba, copy=True)
    normalized_pixels = 0
    strength_sum = 0.0
    for top in range(0, source.height, chunk_rows):
        bottom = min(source.height, top + chunk_rows)
        block = rgba[top:bottom]
        rgb = block[:, :, :3].astype(np.float32) / 255.0
        alpha = block[:, :, 3].astype(np.float32) / 255.0
        package_block = package[top:bottom].astype(np.float32) / 255.0
        protected_block = protected[top:bottom].astype(np.float32) / 255.0

        maximum = rgb.max(axis=2)
        minimum = rgb.min(axis=2)
        saturation = np.divide(maximum - minimum, np.maximum(maximum, 1.0 / 255.0))
        luminance = (rgb[:, :, 0] * 0.2126 + rgb[:, :, 1] * 0.7152
                     + rgb[:, :, 2] * 0.0722)
        shade = np.clip(0.42 + 1.45 * luminance, 0.42, 1.55)[:, :, None]
        canonical = np.clip(base * shade, 0.0, 1.0)

        # Rebuild bright reflections as neutral highlights over the canonical glass.
        highlight = ((_smoothstep(0.42, 0.92, luminance) ** 1.25) * 0.88)[:, :, None]
        canonical = (canonical * (1.0 - highlight)
                     + luminance[:, :, None] * highlight)

        # A bright, low-saturation surface is usually a cap, foil, paper, or white
        # background in an old crop; reduce the effect there.  Coloured glass is not
        # protected by this rule.
        bright = _smoothstep(0.55, 0.88, luminance)
        neutral = 1.0 - _smoothstep(0.05, 0.32, saturation)
        material_protection = np.clip(bright * neutral * 1.25, 0.0, 1.0)
        mix = (strength * package_block * alpha * (1.0 - protected_block)
               * (1.0 - material_protection))
        result_rgb = rgb * (1.0 - mix[:, :, None]) + canonical * mix[:, :, None]
        result[top:bottom, :, :3] = np.clip(
            result_rgb * 255.0 + 0.5, 0, 255).astype(np.uint8)
        changed = mix >= 0.05
        normalized_pixels += int(np.count_nonzero(changed))
        strength_sum += float(mix[changed].sum())

    statistics = {
        "package_pixels": int(np.count_nonzero(package >= 13)),
        "protected_label_pixels": int(np.count_nonzero(protected >= 13)),
        "normalized_pixels": normalized_pixels,
        "mean_strength": round(strength_sum / normalized_pixels, 4)
        if normalized_pixels else 0.0,
    }
    return Image.fromarray(result, "RGBA"), statistics


def _atomic_png(image, path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    handle = tempfile.NamedTemporaryFile(prefix=".", suffix=".png", delete=False,
                                         dir=os.path.dirname(os.path.abspath(path)))
    temporary = handle.name
    handle.close()
    try:
        image.save(temporary, "PNG", optimize=True)
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
    except BaseException:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise


def _preview(image, size, background=(242, 240, 235, 255)):
    image = ImageOps.contain(image.convert("RGBA"), size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, background)
    offset = ((size[0] - image.width) // 2, (size[1] - image.height) // 2)
    canvas.alpha_composite(image, offset)
    return canvas.convert("RGB")


def comparison(pairs, path, cell=(640, 920)):
    """Write a compact before/after sheet for `(slug, source, output)` triples."""
    if not pairs:
        return None
    font = ImageFont.load_default(size=20)
    header = 58
    sheet = Image.new("RGB", (cell[0] * 2, (cell[1] + header) * len(pairs)), "#e7e4de")
    draw = ImageDraw.Draw(sheet)
    for row, (slug, source_path, output_path) in enumerate(pairs):
        with Image.open(source_path) as opened:
            before = ImageOps.exif_transpose(opened).convert("RGBA")
        with Image.open(output_path) as opened:
            after = opened.convert("RGBA")
        y = row * (cell[1] + header)
        sheet.paste(_preview(before, cell), (0, y + header))
        sheet.paste(_preview(after, cell), (cell[0], y + header))
        draw.text((16, y + 8), "BEFORE", fill="#272522", font=font)
        draw.text((cell[0] + 16, y + 8), "NORMALIZED", fill="#272522", font=font)
        draw.text((160, y + 8), slug, fill="#5a5650", font=font)
    _atomic_png(sheet, path)
    return path


def run(db_path, output_dir, *, slugs=(), categories=(), all_states=False, limit=None,
        target=(19, 39, 31), strength=DEFAULT_STRENGTH,
        label_margin=DEFAULT_LABEL_MARGIN, overwrite=False, comparison_path=None,
        comparison_limit=4):
    selected = records(db_path, slugs, categories, all_states, limit)
    os.makedirs(output_dir, exist_ok=True)
    items = []
    pairs = []
    for record in selected:
        item = {key: record[key] for key in
                ("slug", "category", "source_sha256", "package_sha256", "label_sha256")}
        target_path = os.path.join(output_dir, record["source_sha256"] + ".png")
        item["output"] = os.path.abspath(target_path)
        missing = [kind for kind in ("package", "label") if not record[kind]]
        if missing:
            item.update(status="skipped", reason="missing %s derivative" % " and ".join(missing))
            items.append(item)
            continue
        if os.path.exists(target_path) and not overwrite:
            item.update(status="present")
            items.append(item)
            if len(pairs) < comparison_limit:
                pairs.append((record["slug"], record["source"], target_path))
            continue
        try:
            with Image.open(record["source"]) as opened:
                source = ImageOps.exif_transpose(opened).convert("RGBA")
            package_mask = placed_alpha(record["package"], record["package_box"], source.size)
            label_mask = placed_alpha(record["label"], record["label_box"], source.size)
            normalized, statistics = normalize_image(
                source, package_mask, label_mask, target, strength, label_margin)
            _atomic_png(normalized, target_path)
        except (OSError, ValueError, NormalizeError) as exc:
            item.update(status="skipped", reason=str(exc))
            items.append(item)
            continue
        item.update(status="written", statistics=statistics)
        items.append(item)
        if len(pairs) < comparison_limit:
            pairs.append((record["slug"], record["source"], target_path))

    manifest = {
        "version": 1,
        "database": os.path.abspath(db_path),
        "settings": {
            "image_type": "main",
            "states": "all" if all_states else "Active",
            "slugs": list(slugs),
            "categories": list(categories),
            "target_colour": "#%02x%02x%02x" % target,
            "strength": strength,
            "label_margin": label_margin,
        },
        "summary": {
            "selected": len(selected),
            "written": sum(item["status"] == "written" for item in items),
            "present": sum(item["status"] == "present" for item in items),
            "skipped": sum(item["status"] == "skipped" for item in items),
        },
        "items": items,
    }
    manifest_path = os.path.join(output_dir, MANIFEST_NAME)
    data = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    handle = tempfile.NamedTemporaryFile(prefix=".", suffix=".json", delete=False,
                                         dir=os.path.abspath(output_dir))
    temporary = handle.name
    try:
        with handle:
            handle.write(data)
        os.chmod(temporary, 0o644)
        os.replace(temporary, manifest_path)
    except BaseException:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise
    if comparison_path:
        comparison(pairs, comparison_path)
    return manifest


def parser():
    value = argparse.ArgumentParser(
        description="Normalize bottle glass in catalogue main images without changing the store.")
    value.add_argument("--db", default=str(DEFAULT_DB), help="catalogue SQLite database")
    value.add_argument("--output", required=True, help="output directory for PNG files")
    value.add_argument("--slug", action="append", default=[], help="one wine slug; repeatable")
    value.add_argument("--category", action="append", default=[],
                       help="one exact category, for example Красное; repeatable")
    value.add_argument("--all-states", action="store_true",
                       help="include Disabled and Removed wines; Active alone is the default")
    value.add_argument("--limit", type=int, default=None)
    value.add_argument("--target-colour", type=parse_colour, default=parse_colour(DEFAULT_TARGET))
    value.add_argument("--strength", type=float, default=DEFAULT_STRENGTH)
    value.add_argument("--label-margin", type=float, default=DEFAULT_LABEL_MARGIN,
                       help="protected margin as a fraction of the source long side")
    value.add_argument("--overwrite", action="store_true")
    value.add_argument("--comparison", default=None,
                       help="optional path of a before/after PNG sheet")
    value.add_argument("--comparison-limit", type=int, default=4)
    return value


def main(argv=None):
    args = parser().parse_args(argv)
    if args.limit is not None and args.limit < 1:
        parser().error("--limit MUST be positive")
    if not 0.0 <= args.strength <= 1.0:
        parser().error("--strength MUST be between 0 and 1")
    if not 0.0 <= args.label_margin <= 0.05:
        parser().error("--label-margin MUST be between 0 and 0.05")
    if args.comparison_limit < 1:
        parser().error("--comparison-limit MUST be positive")
    try:
        result = run(args.db, args.output, slugs=args.slug, categories=args.category,
                     all_states=args.all_states, limit=args.limit,
                     target=args.target_colour, strength=args.strength,
                     label_margin=args.label_margin, overwrite=args.overwrite,
                     comparison_path=args.comparison,
                     comparison_limit=args.comparison_limit)
    except (OSError, sqlite3.Error, NormalizeError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    print(json.dumps(result["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
