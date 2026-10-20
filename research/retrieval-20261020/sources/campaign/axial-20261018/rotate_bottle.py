#!/usr/bin/env python3
"""Rotate photographed bottle labels on cylindrical surfaces, without a 3D engine.

The complete visible label is assumed to be present in the source image.
Its photographed cylindrical distortion is inverted before the new rotation
is projected. The silhouette and glass reflections stay fixed; newly exposed
glass is approximated from nearby pixels. Positive angles move artwork right.

Dependencies: numpy, Pillow, opencv-python-headless. Python 3.10+.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageOps

PRESET_DIR = Path(__file__).resolve().parent / "presets"
ANGLE_LIMIT = 30.0


def _finite(value: Any, name: str) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def _polygon_mask(polygons: list, size: tuple[int, int], scale: tuple[float, float]) -> np.ndarray:
    """Rasterize arbitrary paper outlines with antialiased edges."""
    supersample = 4
    canvas = Image.new("L", (size[0] * supersample, size[1] * supersample))
    draw = ImageDraw.Draw(canvas)
    for polygon in polygons:
        if len(polygon) < 3:
            raise ValueError("Each polygon needs at least three points")
        points = [
            (round(_finite(x, "polygon x") * scale[0] * supersample),
             round(_finite(y, "polygon y") * scale[1] * supersample))
            for x, y in polygon
        ]
        draw.polygon(points, fill=255)
    return np.asarray(canvas.resize(size, Image.Resampling.LANCZOS)).copy()


def _make_mask(spec: dict, source: np.ndarray, reference: tuple[int, int], directory: Path) -> np.ndarray:
    h, w = source.shape[:2]
    scale = (w / reference[0], h / reference[1])
    if "mask" in spec:
        with Image.open(directory / spec["mask"]) as image:
            if image.size != reference:
                raise ValueError("A mask image must match reference_size")
            mask = np.asarray(image.convert("L").resize((w, h), Image.Resampling.LANCZOS)).copy()
    elif spec.get("polygons"):
        mask = _polygon_mask(spec["polygons"], (w, h), scale)
    else:
        raise ValueError("Each layer needs polygons or a grayscale mask file")

    # Optional extraction of ink within a small region on the capsule.
    ink = spec.get("ink")
    if ink:
        rgb = source[:, :, :3].astype(np.float32)
        keep = mask > 100
        if "min_mean" in ink:
            keep &= rgb.mean(axis=2) > ink["min_mean"]
        if "min_red_blue_ratio" in ink:
            keep &= rgb[:, :, 0] > rgb[:, :, 2] * ink["min_red_blue_ratio"]
        if "max_min_channel" in ink:
            keep &= rgb.min(axis=2) < ink["max_min_channel"]
        mask = keep.astype(np.uint8) * 255
    dilation = round(max(0, float(spec.get("dilate", 0))) * sum(scale) / 2)
    if dilation:
        mask = cv2.dilate(mask, np.ones((2 * dilation + 1, 2 * dilation + 1), np.uint8))
    # No paper may exist outside the source cutout.
    mask = np.minimum(mask, source[:, :, 3])
    if not np.any(mask > 2):
        raise ValueError(f"Empty mask for layer {spec.get('name', '(unnamed)')}")
    return mask


def _restore_glass(photo: np.ndarray, mask: np.ndarray, mode: str, margin: int) -> np.ndarray:
    """Approximate hidden glass; keep all alpha values and surrounding pixels."""
    if mode not in ("vertical", "inpaint"):
        raise ValueError("fill must be 'vertical' or 'inpaint'")
    filled = photo.copy()
    support = cv2.dilate((mask > 2).astype(np.uint8), np.ones((2 * margin + 1, 2 * margin + 1), np.uint8))
    if mode == "inpaint":
        filled[:, :, :3] = cv2.inpaint(photo[:, :, :3].copy(), support * 255, 4, cv2.INPAINT_TELEA)
        return filled

    # Extend the same vertical glass reflections through the paper region.
    # Sampling outside the expanded removal mask prevents stationary outlines.
    h, w = mask.shape
    known_glass = (support == 0) & (photo[:, :, 3] > 180)
    glass_columns = np.flatnonzero(known_glass.any(axis=0))
    for x in range(w):
        ys = np.flatnonzero(support[:, x])
        if not len(ys):
            continue
        first, last = int(ys[0]), int(ys[-1])
        above = np.arange(max(0, first - 10), max(0, first - 3))
        below = np.arange(min(h, last + 4), min(h, last + 11))
        above = above[photo[above, x, 3] > 180]
        below = below[photo[below, x, 3] > 180]
        # A label can touch the image boundary. Use the available side instead.
        if not len(above) and not len(below):
            known = np.flatnonzero((support[:, x] == 0) & (photo[:, x, 3] > 180))
            if not len(known):
                if not np.any(mask[:, x] > 2):
                    # Removal padding can extend into fully transparent columns.
                    continue
                if not len(glass_columns):
                    raise ValueError("Cannot reconstruct glass: no visible glass around the label")
                nearby_x = int(glass_columns[np.argmin(np.abs(glass_columns - x))])
                nearby_rows = np.flatnonzero(known_glass[:, nearby_x])
                nearby_y = nearby_rows[np.argmin(np.abs(nearby_rows - (first + last) / 2))]
                filled[first:last + 1, x, :3] = photo[nearby_y, nearby_x, :3]
                continue
            above = below = known[:1]
        if not len(above):
            above = below
        if not len(below):
            below = above
        upper = np.median(photo[above, x, :3], axis=0)
        lower = np.median(photo[below, x, :3], axis=0)
        t = np.linspace(0, 1, last - first + 1)[:, None]
        filled[first:last + 1, x, :3] = (1 - t) * upper + t * lower
    weight = cv2.GaussianBlur(support.astype(np.float32), (5, 5), 0.7)[:, :, None]
    filled[:, :, :3] = filled[:, :, :3] * weight + photo[:, :, :3] * (1 - weight)
    return filled


def _silhouette_profile(alpha: np.ndarray) -> np.ndarray:
    foreground = (alpha > 90).astype(np.uint8)
    if foreground.all():
        raise ValueError("Use a transparent bottle cutout, or supply an explicit profile")
    count, labels, stats, _ = cv2.connectedComponentsWithStats(foreground)
    if count < 2:
        raise ValueError("Image contains no visible bottle")
    foreground = labels == (1 + np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    h = alpha.shape[0]
    profile = np.full((h, 2), np.nan, dtype=np.float32)
    for y in range(h):
        xs = np.flatnonzero(foreground[y])
        if len(xs):
            profile[y] = [(int(xs[0]) + int(xs[-1])) / 2, (int(xs[-1]) - int(xs[0]) + 1) / 2]
    known = np.flatnonzero(np.isfinite(profile[:, 0]))
    for column in (0, 1):
        profile[:, column] = np.interp(np.arange(h), known, profile[known, column])
    return cv2.GaussianBlur(profile, (1, 9), 1.4)


def _explicit_profile(spec: dict, height: int, scale: tuple[float, float]) -> np.ndarray:
    if "points" in spec:
        points = np.asarray(spec["points"], dtype=np.float32)
        if (points.ndim != 2 or points.shape[1] != 3 or len(points) < 2
                or not np.isfinite(points).all() or np.any(np.diff(points[:, 0]) <= 0)):
            raise ValueError("profile.points must be increasing [y, center_x, radius] triples")
        y = np.arange(height)
        profile = np.column_stack([
            np.interp(y, points[:, 0] * scale[1], points[:, 1] * scale[0]),
            np.interp(y, points[:, 0] * scale[1], points[:, 2] * scale[0]),
        ])
    else:
        profile = np.tile([_finite(spec["center"], "center") * scale[0],
                           _finite(spec["radius"], "radius") * scale[0]], (height, 1))
    if np.any(profile[:, 1] <= 0):
        raise ValueError("Profile radii must be positive")
    return profile.astype(np.float32)


def _smooth_body(profile: np.ndarray, mask: np.ndarray) -> None:
    rows = np.flatnonzero(np.any(mask > 2, axis=1))
    lo, hi = int(rows[0]), int(rows[-1])
    if hi <= lo:
        return
    # Prevent pixel-sized cutout noise from creating a wavy rotated label.
    for column in (0, 1):
        fit = np.polyfit(np.arange(lo, hi + 1), profile[lo:hi + 1, column], 1)
        ys = np.arange(max(0, lo - 12), min(len(profile), hi + 13))
        weight = np.clip(np.minimum((ys - lo + 12) / 12, (hi + 12 - ys) / 12), 0, 1)
        profile[ys, column] = (1 - weight) * profile[ys, column] + weight * np.polyval(fit, ys)
    profile[:, 1] = np.maximum(profile[:, 1], 0.5)


@dataclass
class _Layer:
    texture: np.ndarray  # Premultiplied RGB plus mask coverage, float32.
    profile: np.ndarray
    distance: float
    camera_y: float
    first_row: int
    last_row: int


class BottleRotator:
    """Prepare once, then render many angles. Image coordinates are in pixels."""

    def __init__(self, image: Image.Image, calibration: dict, *, config_dir: Path = Path("."), max_height: int = 0):
        if calibration.get("version") != 1:
            raise ValueError("Unsupported calibration version; expected 1")
        reference = tuple(calibration["reference_size"])
        if len(reference) != 2 or any(not isinstance(v, int) or v <= 0 for v in reference):
            raise ValueError("reference_size must be [positive width, positive height]")
        if not calibration.get("layers"):
            raise ValueError("Calibration needs at least one layer")
        image = ImageOps.exif_transpose(image).convert("RGBA")
        if abs((image.width / image.height) / (reference[0] / reference[1]) - 1) > 0.02:
            raise ValueError("Image aspect ratio differs from this calibration; use an uncropped resize")
        if max_height < 0:
            raise ValueError("max_height cannot be negative")
        if max_height and image.height > max_height:
            image = image.resize((max(1, round(image.width * max_height / image.height)), max_height), Image.Resampling.LANCZOS)
        self.source = np.asarray(image).copy()
        self.height, self.width = self.source.shape[:2]
        scale = (self.width / reference[0], self.height / reference[1])
        specs = calibration["layers"]
        masks = [_make_mask(spec, self.source, reference, Path(config_dir)) for spec in specs]
        if "profile" in calibration:
            profile = _explicit_profile(calibration["profile"], self.height, scale)
        elif all("profile" in spec for spec in specs):
            profile = None
        else:
            profile = _silhouette_profile(self.source[:, :, 3])
            for spec, mask in zip(specs, masks):
                if spec.get("smooth_profile"):
                    _smooth_body(profile, mask)

        self.base = self.source.copy()
        self.layers: list[_Layer] = []
        for spec, mask in zip(specs, masks):
            distance = _finite(spec.get("distance", 300), "distance")
            if distance <= 1:
                raise ValueError("Camera distance must exceed one cylinder radius")
            camera_y = _finite(spec.get("camera_y", reference[1] / 2), "camera_y") * scale[1]
            layer_profile = _explicit_profile(spec["profile"], self.height, scale) if "profile" in spec else profile
            margin = max(0, round(float(spec.get("repair_margin", 5)) * sum(scale) / 2))
            self.base = _restore_glass(self.base, mask, spec.get("fill", "vertical"), margin)
            coverage = mask.astype(np.float32) / 255
            texture = np.concatenate([self.source[:, :, :3] * coverage[:, :, None], coverage[:, :, None]], axis=2).astype(np.float32)
            rows = np.flatnonzero(np.any(mask > 2, axis=1))
            # Conservative vertical bounds for any visible source/destination
            # angle. Perspective magnification is bounded by (D+1)/D.
            factor = (distance + 1) / distance
            extremes = [camera_y + (y - camera_y) * f for y in (rows[0], rows[-1]) for f in (factor, 1 / factor)]
            first = max(0, math.floor(min(extremes)) - 2)
            last = min(self.height - 1, math.ceil(max(extremes)) + 2)
            self.layers.append(_Layer(texture, layer_profile, distance, camera_y, first, last))

    @classmethod
    def from_config(cls, config: str | Path, image: str | Path | None = None, *, max_height: int = 0) -> BottleRotator:
        config = Path(config).resolve()
        calibration = json.loads(config.read_text(encoding="utf-8"))
        if image is None:
            if "image" not in calibration:
                raise ValueError("Supply an image path, or set image in the calibration")
            image = config.parent / calibration["image"]
        with Image.open(image) as source:
            return cls(source, calibration, config_dir=config.parent, max_height=max_height)

    @classmethod
    def from_preset(cls, name: str, image: str | Path | None = None, *, max_height: int = 0) -> BottleRotator:
        if name not in available_presets():
            raise ValueError(f"Unknown preset: {name}")
        return cls.from_config(PRESET_DIR / f"{name}.json", image, max_height=max_height)

    def render(self, angle: float, *, lighting: bool = True) -> Image.Image:
        """Render -30..+30 degrees; zero is pixel-identical to the prepared input."""
        angle = _finite(angle, "angle")
        if not -ANGLE_LIMIT <= angle <= ANGLE_LIMIT:
            raise ValueError("Angle must be between -30 and +30 degrees")
        if angle == 0:
            return Image.fromarray(self.source.copy())
        result = self.base[:, :, :3].astype(np.float32)
        radians = math.radians(angle)
        ca, sa = math.cos(radians), math.sin(radians)
        x = np.arange(self.width, dtype=np.float32)[None, :]
        profile_y = np.arange(self.height)
        for layer in self.layers:
            D = layer.distance
            tangent2 = D * D - 1
            tangent = math.sqrt(tangent2)
            # Row chunks bound memory independently of the image height.
            for first in range(layer.first_row, layer.last_row + 1, 128):
                last = min(first + 128, layer.last_row + 1)
                y = np.arange(first, last, dtype=np.float32)[:, None]
                center = layer.profile[first:last, 0, None]
                radius = layer.profile[first:last, 1, None]
                q = (x - center) / radius
                q2 = q * q
                # Invert x = center + R*sqrt(D²-1)*sin(phi)/(D-cos(phi)).
                cosine = (q2 * D + tangent2 * np.sqrt(np.maximum(0, 1 - q2))) / (tangent2 + q2)
                sine = q * (D - cosine) / tangent
                source_cosine = cosine * ca + sine * sa
                source_sine = sine * ca - cosine * sa
                denominator = D - source_cosine
                safe_denominator = np.maximum(denominator, 1e-6)
                source_y = layer.camera_y + (y - layer.camera_y) * (D - cosine) / safe_denominator
                source_center = np.interp(source_y, profile_y, layer.profile[:, 0])
                source_radius = np.interp(source_y, profile_y, layer.profile[:, 1])
                source_x = source_center + source_radius * tangent * source_sine / safe_denominator
                visible = ((np.abs(q) <= 1) & (source_cosine > 1 / D)
                           & (source_x >= 0) & (source_x <= self.width - 1)
                           & (source_y >= 0) & (source_y <= self.height - 1))
                map_x = np.where(visible, source_x, -1).astype(np.float32)
                map_y = np.where(visible, source_y, -1).astype(np.float32)
                sampled = cv2.remap(layer.texture, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
                coverage = sampled[:, :, 3:4]
                colors = sampled[:, :, :3]
                if lighting:
                    shade = np.clip((0.87 + 0.1 * cosine - 0.055 * sine)
                                    / np.maximum(0.87 + 0.1 * source_cosine - 0.055 * source_sine, 1e-6), 0.75, 1.25)
                    colors = np.minimum(colors * shade[:, :, None], 255 * coverage)
                result[first:last] = result[first:last] * (1 - coverage) + colors
        output = self.source.copy()
        output[:, :, :3] = np.rint(np.clip(result, 0, 255)).astype(np.uint8)
        # The bottle is a surface of revolution: its silhouette stays fixed.
        return Image.fromarray(output)


def available_presets() -> list[str]:
    return sorted(path.stem for path in PRESET_DIR.glob("*.json"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("image", nargs="?", type=Path, help="Optional replacement image (same framing as calibration)")
    config = parser.add_mutually_exclusive_group()
    config.add_argument("--preset", choices=available_presets())
    config.add_argument("--config", type=Path, help="Custom calibration JSON")
    parser.add_argument("--list-presets", action="store_true")
    angles = parser.add_mutually_exclusive_group()
    angles.add_argument("--angle", type=float)
    angles.add_argument("--angles", nargs="+", type=float, help="Batch angles, e.g. --angles -30 0 30")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--output", type=Path, help="One PNG; requires --angle")
    output.add_argument("--output-dir", type=Path, help="Batch directory; requires --angles")
    parser.add_argument("--max-height", type=int, default=0, help="Optional resize before processing; 0 keeps full resolution")
    parser.add_argument("--no-lighting", action="store_true", help="Apply geometry without approximate relighting")
    args = parser.parse_args(argv)
    if args.list_presets:
        print("\n".join(available_presets()))
        return 0
    if not (args.preset or args.config):
        parser.error("choose --preset or --config")
    if args.angle is not None:
        if args.output is None:
            parser.error("--angle requires --output")
        degrees = [args.angle]
        paths = [args.output]
    elif args.angles is not None:
        if args.output_dir is None:
            parser.error("--angles requires --output-dir")
        degrees = args.angles
        name = args.preset or args.config.stem
        paths = [args.output_dir / f"{name}_{angle:+g}deg.png" for angle in degrees]
    else:
        parser.error("choose --angle or --angles")
    try:
        if any(not math.isfinite(a) or abs(a) > ANGLE_LIMIT for a in degrees):
            raise ValueError("All angles must be finite and between -30 and +30")
        if len(set(path.resolve() for path in paths)) != len(paths):
            raise ValueError("Duplicate output names; supply distinct angles")
        if any(path.suffix.lower() != ".png" for path in paths):
            raise ValueError("Output filenames must end in .png")
        config_path = (PRESET_DIR / f"{args.preset}.json") if args.preset else args.config.resolve()
        calibration = json.loads(config_path.read_text(encoding="utf-8"))
        source_path = args.image or (config_path.parent / calibration["image"] if "image" in calibration else None)
        if source_path and source_path.resolve() in {p.resolve() for p in paths}:
            raise ValueError("Output must differ from the source image")
        rotator = BottleRotator.from_config(config_path, args.image, max_height=args.max_height)
        for angle, path in zip(degrees, paths):
            path.parent.mkdir(parents=True, exist_ok=True)
            rotator.render(angle, lighting=not args.no_lighting).save(path)
            print(path.resolve())
    except (ValueError, KeyError, OSError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
