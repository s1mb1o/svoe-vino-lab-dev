#!/usr/bin/env python3
"""Select a deterministic 30-image Pixel 8 encoder pilot from one baseline run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3

from PIL import Image, ImageOps


GROUP_SIZES = {
    "positive-hit": 8,
    "positive-near-miss": 5,
    "positive-ranked-miss": 4,
    "positive-absent-miss": 7,
    "negative": 5,
    "no-match": 1,
}


class SelectionError(ValueError):
    """The baseline cannot make the required pilot set."""


def classify(row: dict) -> str | None:
    if row.get("http_status") != 200 or row.get("error"):
        return None
    label = row.get("label")
    rank = row.get("rank_of_truth")
    if label == "negative":
        return "negative"
    if label == "no_match":
        return "no-match"
    if label != "positive":
        return None
    if rank == 1:
        return "positive-hit"
    if isinstance(rank, int) and rank <= 5:
        return "positive-near-miss"
    if isinstance(rank, int):
        return "positive-ranked-miss"
    return "positive-absent-miss"


def image_path(
    image_root: Path,
    catalog_root: Path,
    database: sqlite3.Connection,
    digest: str,
) -> tuple[Path, int | None, int | None]:
    record = database.execute(
        "SELECT folder, extension, width, height FROM image WHERE sha256 = ?",
        (digest,),
    ).fetchone()
    matches = []
    if record:
        folder, extension, _, _ = record
        if folder == "testset":
            candidate = image_root / f"{digest}.{extension}"
        else:
            root = catalog_root / "cuts" if folder == "cropped" else catalog_root / "images" / folder
            candidate = root / f"{digest}.{extension}"
        if candidate.is_file():
            matches = [candidate]
    if not matches:
        matches = sorted(image_root.glob(f"{digest}.*"))
    if len(matches) != 1:
        raise SelectionError(f"expected one image for {digest}; found {len(matches)}")
    return matches[0], record[2] if record else None, record[3] if record else None


def image_geometry(path: Path) -> tuple[int, int]:
    with Image.open(path) as opened:
        image = ImageOps.exif_transpose(opened)
        return image.width, image.height


def systematic_sample(rows: list[dict], count: int) -> list[dict]:
    if len(rows) < count:
        raise SelectionError(f"group has {len(rows)} rows; {count} are required")
    rows.sort(key=lambda row: (
        row["aspect_ratio"],
        row["pixel_count"],
        row.get("latency_ms") or 0,
        row["query_id"],
    ))
    if count == 1:
        return [rows[len(rows) // 2]]
    return [rows[round(index * (len(rows) - 1) / (count - 1))] for index in range(count)]


def build(args) -> list[dict]:
    results = Path(args.results).resolve()
    image_root = Path(args.image_root).resolve()
    catalog_root = Path(args.catalog_root).resolve()
    output = Path(args.output).resolve()
    groups = {name: [] for name in GROUP_SIZES}
    database = sqlite3.connect(f"file:{catalog_root / 'catalog.sqlite3'}?mode=ro", uri=True)
    try:
        with results.open(encoding="utf-8") as source:
            for line in source:
                row = json.loads(line)
                group = classify(row)
                if group is None:
                    continue
                path, width, height = image_path(
                    image_root,
                    catalog_root,
                    database,
                    row["image_sha256"],
                )
                if not width or not height:
                    width, height = image_geometry(path)
                groups[group].append({
                    "query_id": row["query_id"],
                    "image_sha256": row["image_sha256"],
                    "image_path": str(path),
                    "source_image_path": row["image_path"],
                    "label": row["label"],
                    "truth": row.get("truth") or [],
                    "baseline_predicted_slug": row.get("predicted_slug"),
                    "baseline_rank_of_truth": row.get("rank_of_truth"),
                    "baseline_outcome": row.get("outcome"),
                    "baseline_latency_ms": row.get("latency_ms"),
                    "selection_reason": group,
                    "width": width,
                    "height": height,
                    "aspect_ratio": round(width / height, 6),
                    "pixel_count": width * height,
                })
    finally:
        database.close()
    selected = []
    for group, count in GROUP_SIZES.items():
        selected.extend(systematic_sample(groups[group], count))
    if len({row["query_id"] for row in selected}) != sum(GROUP_SIZES.values()):
        raise SelectionError("the systematic sample contains a duplicate query")
    for number, row in enumerate(selected, 1):
        row["pilot_index"] = number
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as target:
        for row in selected:
            target.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return selected


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", required=True)
    parser.add_argument("--image-root", required=True)
    parser.add_argument("--catalog-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        rows = build(args)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps({"output": str(Path(args.output).resolve()), "images": len(rows)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
