"""Prepare exact baseline pixels, masks, and fixed query orientation conditions."""
from pathlib import Path
import json
import time
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageOps
from common import OUT, WB, DB, NAME, dump, stamp
import clusters
import derive
import embeddings
import embedding_run
import pipelines
from geometry import best_angle, policy_angle, transform, checks


def foreground(image):
    if image.mode == "RGBA" and image.getchannel("A").getextrema()[0] < 255:
        return image.getchannel("A")
    rgb = np.asarray(image.convert("RGB"))
    _, labels = cv2.connectedComponents((rgb.min(2) >= 245).astype(np.uint8), connectivity=4)
    border = np.unique(np.r_[labels[0], labels[-1], labels[:, 0], labels[:, -1]])
    border = border[border != 0]
    background = np.isin(labels, border)
    mask = (~background).astype(np.uint8) * 255
    if not mask.any():
        mask[:] = 255
    return Image.fromarray(mask)


def placed_label(base_size, base_box, label_cut):
    mask = Image.new("L", base_size, 0)
    if label_cut:
        box, pixels = label_cut
        alpha = foreground(pixels)
        mask.paste(alpha, (box[0] - base_box[0], box[1] - base_box[1]))
    return mask


def save_inputs(directory, image, fg, label):
    directory.mkdir(parents=True, exist_ok=True)
    for key, value in [("image", image), ("foreground", fg), ("label", label)]:
        path = directory / (key + ".png")
        value.save(path, compress_level=1)
        stamp(path)
    return {key: str((directory / (key + ".png")).relative_to(OUT / "inputs"))
            for key in ("image", "foreground", "label")}


def prepare_catalogue():
    settings = embeddings.load_settings(str(OUT / "config.yaml"))
    entry = settings.find(NAME)
    context = clusters.context(settings, NAME)
    sources = context["sources"]
    directory = Path(context["directory"])
    index = context["index"]
    vectors = embeddings.read_vectors(str(directory), index)
    plan = embeddings.plan_items(entry, sources)
    records = []
    controls = {}
    for key, (state, record) in sorted(context["status"].items()):
        if state != "current":
            continue
        digest, view = key
        item, source = plan[key], sources[digest]
        if item["steps"] and item["steps"][0]["step"] == "segment":
            cut = item["cut"]
            raw, _ = derive.open_image(cut["path"])
            image = embeddings.on_white(raw)
            fg = foreground(raw)
            if view == "label":
                label = fg.copy()
            else:
                info = source["cuts"].get("label")
                label_cut = (info["box"], derive.open_image(info["path"])[0]) if info else None
                label = placed_label(raw.size, cut["box"], label_cut)
        else:
            raw, _ = derive.open_image(source["path"])
            image, fg = raw.convert("RGB"), foreground(raw)
            label = fg.copy() if view == "label" else Image.new("L", raw.size, 0)
        resize = item["steps"][-1] if item["steps"] and item["steps"][-1]["step"] == "resize" else None
        zero = embeddings.resize(image, resize) if resize else image
        with Image.open(directory / record["image"]) as expected:
            expected = expected.convert("RGB")
            assert zero.size == expected.size and zero.tobytes() == expected.tobytes(), (digest, view, "Pixel preparation differs")
        identity = digest + "_" + view
        files = save_inputs(OUT / "inputs/gallery" / identity, image, fg, label)
        angles = record.get("angles", [0])
        r = {"id": identity, **files, "source_sha256": digest, "view": view, "row": record["row"],
             "angles": angles, "resize": resize, "label_available": label.getbbox() is not None}
        if len(controls) < 3 and view == "full":
            controls[identity] = np.asarray(vectors[record["row"]:record["row"] + len(angles)]).copy()
            r["control"] = True
        records.append(r)
        if len(records) % 100 == 0:
            dump(OUT / "preparation-progress.json", {"phase": "catalogue", "done": len(records)})
            print("CATALOGUE", len(records), flush=True)
    np.savez_compressed(OUT / "inputs/controls.npz", **controls)
    stamp(OUT / "inputs/controls.npz")
    dump(OUT / "prepared-catalogue.json", records)
    return records


def prepare_queries():
    dump(OUT / "geometry-checks.json", checks())
    pipeline = pipelines.load(str(OUT / "config.yaml")).find("siglip2-p512-rot5-seg")
    client = derive.Sam3Client()
    queries = {r["image_sha256"]: r for r in json.loads((OUT / "queries.json").read_text())}
    prepared, errors = [], []
    for number, (digest, query) in enumerate(sorted(queries.items()), 1):
        begin = time.perf_counter()
        try:
            image, _ = derive.open_image(query["abs_path"])
            cuts = embedding_run.cuts_of(image, {"package"}, client, scene_selection=True)
            box, raw = cuts["package"]
            package = raw.convert("RGBA")
            package.putalpha(foreground(raw))
            label_error = None
            try:
                label_cuts = embedding_run.cuts_of(image, {"label"}, client)
                label = placed_label(raw.size, box, label_cuts.get("label"))
            except Exception as exc:
                label = Image.new("L", raw.size, 0)
                label_error = str(exc)
            baseline, reason = embedding_run.view_input(image, pipeline.views["full"], cuts)
            assert baseline is not None, reason
            resize = pipeline.views["full"][-1]
            fg = foreground(raw).resize(baseline.size, Image.Resampling.LANCZOS)
            label = label.resize(baseline.size, Image.Resampling.LANCZOS)
            files = save_inputs(OUT / "inputs/query" / digest, baseline, fg, label)
            angle, audit = best_angle(package)
            variants = {}
            for policy in ("iou", "iou-min5", "iou-cardinal5"):
                applied = policy_angle(angle, policy)
                rotated = transform(package, applied)
                rgb = embeddings.resize(embeddings.on_white(rotated), resize)
                path = OUT / "oriented-inputs" / policy / (digest + ".png")
                path.parent.mkdir(parents=True, exist_ok=True)
                rgb.save(path, compress_level=1)
                stamp(path)
                variants[policy] = {"path": str(path), "angle": applied, "size": list(rgb.size)}
            prepared.append({"id": digest, **files, "angles": [0], "resize": None,
                "variants": variants, "best_angle": angle, "geometry": audit,
                "label_available": label.getbbox() is not None, "label_error": label_error,
                "preparation_ms": (time.perf_counter() - begin) * 1000})
        except Exception as exc:
            errors.append({"id": digest, "error": type(exc).__name__ + ": " + str(exc)})
        if number % 25 == 0 or number == len(queries):
            dump(OUT / "preparation-progress.json", {"phase": "queries", "done": number, "total": len(queries), "errors": len(errors)})
            print("QUERIES", number, len(queries), "errors", len(errors), flush=True)
    dump(OUT / "prepared-queries.json", {"queries": prepared, "errors": errors})
    return prepared, errors


def main(stage="all"):
    if stage == "queries":
        prepare_queries()
        return
    if (OUT / "prepared-queries.json").exists():
        saved = json.loads((OUT / "prepared-queries.json").read_text())
        prepared, errors = saved["queries"], saved["errors"]
    else:
        prepared, errors = prepare_queries()
    records = json.loads((OUT / "prepared-catalogue.json").read_text()) if (OUT / "prepared-catalogue.json").exists() else prepare_catalogue()
    manifest = {"records": records, "queries": [{k: v for k, v in q.items() if k not in ("variants", "geometry")} for q in prepared]}
    dump(OUT / "inputs/manifest.json", manifest)
    stamp(OUT / "inputs/manifest.json")
    dump(OUT / "preparation-complete.json", {"catalogue_items": len(records), "queries": len(prepared),
         "query_errors": errors, "vectors": sum(len(r["angles"]) for r in records),
         "label_mask_missing_catalogue": sum(not r["label_available"] for r in records if r["view"] == "full"),
         "label_mask_missing_queries": sum(not q["label_available"] for q in prepared)})


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("all", "queries"), default="all")
    main(parser.parse_args().stage)
