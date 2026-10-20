"""Build two label galleries and evaluate the complete geometry matrix."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import numpy as np
from PIL import Image, ImageOps, ImageDraw
import support as s
from support import HERE, OUT, WB, DB, BASE_DB, NAME, PROFILES, dump, sha, stamp
import benchmark
import clusters
import embeddings
import embedding_run
import label_report


def state(phase, **values):
    dump(HERE / "status.json", {"state": phase, "updated_at": datetime.now(timezone.utc).isoformat(),
         "counters": dict(s.COUNTS), "minimum_available_gib": s.MINIMUM if np.isfinite(s.MINIMUM) else None, **values})
    print(phase, values, flush=True)
    label_report.build()


def coordination(message, final=False):
    path = s.OUT.parents[1] / "ACTIVE_WORK.md"
    text = path.read_text()
    marker = "## codex-my-failed-all-pipelines-20261017"
    start = text.index(marker)
    end = text.find("\n## ", start + len(marker))
    end = len(text) if end < 0 else end
    lines = text[start:end].splitlines()
    positions = [i for i, line in enumerate(lines) if line.startswith("- Label-only follow-up ")]
    assert len(positions) == 1
    lines[positions[0]] = "- Label-only follow-up " + message + " " + datetime.now().astimezone().isoformat()
    path.write_text(text[:start] + "\n".join(lines) + "\n" + text[end:])
    path = Path("/Users/ashmelev/Admin/GPU_TASKS.md")
    lines = path.read_text().splitlines()
    marker = "codex-my-failed2-labels-20261017;"
    for i, line in enumerate(lines):
        if marker in line:
            cells = line.split("|")
            cells[-2] = " " + message + " "
            lines[i] = "|".join(cells)
            break
    else:
        i = next(i for i, line in enumerate(lines) if line.startswith("|---------|--------|")) + 1
        lines.insert(i, "| svoe-vino-lab | gx10 resident services + mbp2023 | Eight owner-requested label experiments 7a-7h. Two 3440-source label galleries, up to 1254 label segmentations inside frozen bottle crops, and four query-label variants per image. Fixed NaFlex p512, standard pooling, serial service requests. Preserve 20 GiB reserve, shared indexes and active 6c/6d build. | "
            + datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
            + " | bounded label preparation and eight paired evaluations | " + marker
            + " internal/my-failed2-six-variants-20261017/labels-20261017 | " + message + " |")
    path.write_text("\n".join(lines) + "\n")


def load_context():
    settings = embeddings.load_settings(str(OUT / "config.yaml"))
    catalogue = embedding_run.Catalogue(settings.find(NAME), str(BASE_DB), use_cache=False)
    label_slugs = {catalogue.slugs[int(n)] for n in catalogue.views["label"][1]}
    queries = json.loads((OUT / "queries.json").read_text())
    assert len(queries) == 668
    assert all(set(q["truth"]) & label_slugs for q in queries)
    coverage = {"label_wines": len(label_slugs), "label_wine_source_rows": len(catalogue.views["label"][1]),
                "assignments_without_label_reference": 0}
    dump(HERE / "coverage.json", coverage)
    return catalogue


def prepare_query(query, item, client):
    path = HERE / "prepared-queries" / (item["id"] + ".json")
    if path.exists():
        return json.loads(path.read_text())
    package = s.package(query, item)
    angle, geometry = s.best_angle(package)
    assert abs(angle - item["best_angle"]) < 1e-6
    result = {"id": item["id"], "bottle_angle": angle, "bottle_geometry": geometry, "variants": {}}
    for rotated in (False, True):
        bottle = s.transform(package, angle) if rotated else package
        cuts = embedding_run.cuts_of(bottle, {"label"}, client)
        cut = cuts.get("label")
        key = "b" if rotated else "a"
        label_key = "e" if rotated else "c"
        if cut is None:
            for name in (key, label_key):
                result["variants"][name] = {"missing_label": True, "reason": "SAM3 found no label inside the segmented bottle."}
            continue
        label = cut[1]
        turned, label_geometry = s.label_turn(label)
        result["variants"][key] = {**s.stage(s.rgb(label)), "label_box": list(cut[0]), "label_angle": 0.}
        result["variants"][label_key] = {**s.stage(s.rgb(turned)), "label_box": list(cut[0]),
                                          "label_angle": label_geometry["angle"], "geometry": label_geometry}
    dump(path, result)
    return result


def prepare_references():
    path = HERE / "references.json"
    if path.exists():
        return json.loads(path.read_text())
    records = [r for r in json.loads((OUT / "prepared-catalogue.json").read_text()) if r["view"] == "label"]
    index = json.loads((OUT / "data/catalog/embeddings" / NAME / "index.json").read_text())
    by_source = {r["source_sha256"]: r for r in index["items"] if r["view"] == "label"}
    result = []
    for number, item in enumerate(records, 1):
        with Image.open(OUT / "inputs" / item["image"]) as source:
            source = source.convert("RGB")
        with Image.open(OUT / "inputs" / item["foreground"]) as mask:
            mask = mask.convert("L")
        baseline = embeddings.resize(source, item["resize"]) if item["resize"] else source
        with Image.open(OUT / "data/catalog/embeddings" / NAME / by_source[item["source_sha256"]]["image"]) as expected:
            expected = expected.convert("RGB")
        assert baseline.size == expected.size and baseline.tobytes() == expected.tobytes(), (item["source_sha256"], baseline.size, expected.size)
        turned, geometry = s.label_turn(source, mask)
        turned = embeddings.resize(turned, item["resize"]) if item["resize"] else turned
        result.append({"source_sha256": item["source_sha256"], "original": s.stage(baseline),
                       "iou": s.stage(turned), "geometry": geometry, "resize": item["resize"]})
        if number % 500 == 0:
            state("Prepare the two label reference galleries", done=number, total=len(records))
    assert len(result) == 3440
    dump(path, result)
    return result


def build_references(records, encoder):
    s.install_identity()
    settings = embeddings.load_settings(str(HERE / "config.yaml"))
    original_dir = OUT / "data/catalog/embeddings" / NAME
    original_index = json.loads((original_dir / "index.json").read_text())
    source_items = {r["source_sha256"]: r for r in original_index["items"] if r["view"] == "label"}
    sources = json.loads((OUT / "catalogue-sources.json").read_text())
    for profile in ("original", "iou"):
        entry = settings.find("exp-my-failed2-label7-" + profile)
        target = Path(embeddings.entry_dir(str(DB), entry.name))
        target.mkdir(parents=True, exist_ok=True)
        if not (target / "index.json").exists():
            vectors = []
            for offset in range(0, len(records), 36):
                chunk = records[offset:offset + 36]
                vectors.extend(encoder.batch([r[profile] for r in chunk]))
                state("Build the " + profile + " label reference embeddings", done=offset + len(chunk), total=len(records))
            matrix = np.asarray(vectors, np.float32)
            assert matrix.shape == (3440, 1152)
            temporary = target / "vectors-build.npy"
            np.save(temporary, matrix, allow_pickle=False)
            filename = "vectors-" + sha(temporary)[:8] + ".npy"
            temporary.replace(target / filename)
            plan = embeddings.plan_items(entry, sources)
            items = []
            for row, record in enumerate(records):
                item = copy.deepcopy(source_items[record["source_sha256"]])
                item.pop("angles", None)
                item.pop("axial_angles", None)
                item["row"] = row
                item["embedding_hash"] = plan[(record["source_sha256"], "label")]["embedding_hash"]
                item["label_geometry"] = record["geometry"] if profile == "iou" else {"angle": 0.}
                image_name = embeddings.image_name(record["source_sha256"], "label")
                image_path = target / "images" / image_name
                image_path.parent.mkdir(exist_ok=True)
                if not image_path.exists():
                    os.link(record[profile]["path"], image_path)
                item["image"] = "images/" + image_name
                item["width"], item["height"] = record[profile]["size"]
                item["prepared_image_sha256"] = record[profile]["sha256"]
                items.append(item)
            embeddings.check_rows(items, len(matrix))
            failures = [{**failure, "embedding_hash": plan[(failure["source_sha256"], "label")]["embedding_hash"]}
                        for failure in original_index["failures"] if failure["view"] == "label"
                        and (failure["source_sha256"], "label") in plan]
            index = {**copy.deepcopy(original_index), "name": entry.name, "config": entry.summary(),
                     "updated_at": embeddings.now(), "items": items, "failures": failures, "vectors_file": filename,
                     "view_config_hash": {"label": entry.view_config_hash("label")},
                     "requires_label_campaign_runner": True, "label_preparation": profile,
                     "software": {"protocol": sha(HERE / "protocol.json"), "geometry": sha(HERE / "support.py"),
                                  "max_num_patches": 512, "batch_size": 36, "standard_pooling": True}}
            dump(target / "index.json", index)
            del matrix
        state("Build the " + profile + " private label clusters")
        artifact = clusters.build_to_directory(settings, entry.name)
        dump(HERE / "clusters" / (profile + ".json"), {"embedding": entry.name, "built_at": artifact["built_at"],
             "spaces": {key: value["counts"] for key, value in artifact["spaces"].items()}, "settings": artifact["settings"]})
    return settings


def export(method, predictions):
    queries = json.loads((OUT / "queries.json").read_text())
    by_path = {r["abs_path"]: r["image_sha256"] for r in queries}
    flags = PROFILES[method]
    class Backend:
        id = "siglip2-p512-label-" + method
        top_k = 10
        spec = {"id": id, "kind": "label-geometry-experiment", **flags, "protocol": str(HERE / "protocol.json"),
                "model": "siglip2-so400m-patch16-naflex", "extra_body": {"max_num_patches": 512}, "workers": 1}
        def ask(self, path):
            row = predictions[by_path[path]]
            return [dict(c, rank=i) for i, c in enumerate(row["candidates"], 1)], row["latency_ms"], 200, None, row["trace"]
    run_dir, metrics = benchmark.run_benchmark(str(DB), "my-failed-2", Backend(), str(WB / "runs"),
        queries=(queries, {}), workers=1, configuration=Backend.id, use_cache=True, use_barcode=False,
        label="my-failed2-labels-20261017", query_scope="frozen-my-failed-2")
    metrics["latency_ms"].update(comparable=False, comparison_note="Accuracy experiment. Segmentation and vector caches can be reused. Recorded time is local ranking only.")
    dump(Path(run_dir) / "metrics.json", metrics)
    path = Path(run_dir) / "run.json"
    meta = json.loads(path.read_text())
    meta.update(campaign=str(HERE), label_geometry=flags, frozen_queries_sha256=sha(OUT / "queries.json"),
                protocol=str(HERE / "protocol.json"), label_only=True, bottle_fallback=False)
    dump(path, meta)
    dump(HERE / "results" / (method + ".json"), {"method": method, "run_dir": run_dir, "metrics": metrics})


def score(settings, prepared, encoder):
    query_vectors = {}
    for number, item in enumerate(prepared, 1):
        query_vectors[item["id"]] = {}
        for name, value in item["variants"].items():
            if not value.get("missing_label"):
                query_vectors[item["id"]][name] = encoder.batch([value])[0]
        if number % 25 == 0 or number == len(prepared):
            state("Embed the four query label variants", done=number, total=len(prepared))
    matrices = {key: embedding_run.Catalogue(settings.find("exp-my-failed2-label7-" + key), str(DB), use_cache=False)
                for key in ("original", "iou")}
    assert set(matrices["original"].slugs[int(n)] for n in matrices["original"].views["label"][1]) == set(
        matrices["iou"].slugs[int(n)] for n in matrices["iou"].views["label"][1])
    for method, flags in PROFILES.items():
        if (HERE / "results" / (method + ".json")).exists():
            continue
        key = ("e" if flags["label_rotation"] else "b") if flags["bottle_rotation"] else ("c" if flags["label_rotation"] else "a")
        catalogue = matrices["iou" if flags["reference_rotation"] else "original"]
        values = {}
        for item in prepared:
            start = time.perf_counter()
            vector = query_vectors[item["id"]].get(key)
            candidates = catalogue.rank({"label": vector}, 10) if vector is not None else []
            values[item["id"]] = {"candidates": candidates, "latency_ms": (time.perf_counter() - start) * 1000,
                 "trace": {"condition": method, "label_only": True, **flags, "bottle_angle": item["bottle_angle"] if flags["bottle_rotation"] else 0,
                           "query_label": item["variants"][key], "bottle_fallback": False}}
        dump(HERE / "predictions" / (method + ".json"), values)
        export(method, values)
        state("Score and export label conditions", done=len(list((HERE / "results").glob("*.json"))), total=8)


def audit():
    assert json.loads((HERE / "reference-pixel-check.json").read_text())["passed"]
    assert json.loads((HERE / "geometry-checks.json").read_text())["passed"]
    freeze = json.loads((OUT / "freeze.json").read_text())
    assert sha(BASE_DB) == sha(DB) == freeze["database_sha256"]
    assert sha(OUT / "queries.json") == freeze["query_manifest_sha256"]
    base = OUT / "data/catalog/embeddings" / NAME
    assert sha(base / "index.json") == freeze["index_sha256"]
    assert sha(base / freeze["vectors_file"]) == freeze["vectors_sha256"]
    assert sha(base / "clusters.json") == freeze["cluster_sha256"]
    for name, record in freeze["original_images"].items():
        path = Path(name)
        assert sha(path) == record["sha256"] and path.stat().st_mtime_ns == record["mtime_ns"]
    data = label_report.build()
    assert len(data["conditions"]) == 8
    for profile in ("original", "iou"):
        root = HERE / "data/catalog/embeddings" / ("exp-my-failed2-label7-" + profile)
        index = json.loads((root / "index.json").read_text())
        assert len(index["items"]) == 3440 and set(r["view"] for r in index["items"]) == {"label"}
        assert index["vectors_file"] == "vectors-" + sha(root / index["vectors_file"])[:8] + ".npy"
        assert (root / "clusters.json").exists()
    dump(HERE / "audit.json", {"passed": True, "conditions": 8, "assignments": 668, "distinct_images": 627,
         "label_reference_sources": 3440, "private_indexes": 2, "private_cluster_artifacts": 2,
         "frozen_sources_database_gallery_and_scoring_identities": "verified", "bottle_fallback": False,
         "counters": dict(s.COUNTS), "minimum_available_gib": s.MINIMUM, "results": data["conditions"]})


def pilot(prepared_specs, queries, client):
    chosen = [prepared_specs[i] for i in (0, len(prepared_specs) // 2, -1)]
    thumbnails = []
    for item in chosen:
        result = prepare_query(queries[item["id"]], item, client)
        for key in ("a", "b", "c", "e"):
            canvas = Image.new("RGB", (250, 260), "#e8edf5")
            spec = result["variants"][key]
            ImageDraw.Draw(canvas).text((8, 8), item["id"][:8] + " / " + key, fill="black")
            if not spec.get("missing_label"):
                with Image.open(spec["path"]) as image:
                    image = ImageOps.contain(image.convert("RGB"), (230, 220))
                canvas.paste(image, ((250 - image.width) // 2, 30 + (220 - image.height) // 2))
            else:
                ImageDraw.Draw(canvas).text((8, 80), "No label", fill="black")
            thumbnails.append(canvas)
    montage = Image.new("RGB", (1000, 780), "white")
    for i, image in enumerate(thumbnails):
        montage.paste(image, ((i % 4) * 250, (i // 4) * 260))
    montage.save(HERE / "pilot.png")
    dump(HERE / "pilot.json", {"passed": True, "images": [r["id"] for r in chosen], "counters": dict(s.COUNTS)})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--pilot", action="store_true")
    parser.add_argument("--await-reference-preflight", action="store_true")
    args = parser.parse_args()
    subprocess.Popen(["caffeinate", "-i", "-w", str(os.getpid())], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    dump(HERE / "process.json", {"pid": os.getpid(), "started_at": datetime.now(timezone.utc).isoformat(), "pilot": args.pilot})
    s.checks()
    if args.allow_network:
        s.guard(28)
        coordination("active: Prepare and run eight fixed label-only conditions through the existing SAM3 and NaFlex services. Preserve 6c and 6d. Report: http://127.0.0.1:59998/labels-20261017/report.html.")
    try:
        if args.await_reference_preflight:
            state("Wait for the full reference pixel preflight")
            began = time.monotonic()
            while not (HERE / "reference-pixel-check.json").exists():
                if time.monotonic() - began > 1800:
                    raise TimeoutError("The independent reference pixel preflight did not finish within 30 minutes.")
                time.sleep(5)
        client, encoder = s.Sam3(args.allow_network), s.Encoder(args.allow_network)
        items = json.loads((OUT / "prepared-queries.json").read_text())["queries"]
        queries = {r["image_sha256"]: r for r in json.loads((OUT / "queries.json").read_text())}
        if args.pilot:
            state("Check label segmentation and geometry on three frozen queries")
            pilot(items, queries, client)
            state("Pilot complete. Ready for the full eight conditions")
            return
        original = load_context()
        del original
        references = prepare_references()
        settings = build_references(references, encoder)
        prepared = []
        for number, item in enumerate(items, 1):
            prepared.append(prepare_query(queries[item["id"]], item, client))
            if number % 10 == 0 or number == len(items):
                state("Segment labels inside both bottle orientations", done=number, total=len(items))
        dump(HERE / "prepared-queries.json", prepared)
        score(settings, prepared, encoder)
        state("Audit the eight label conditions and original sources")
        audit()
        state("Complete", conditions=8)
        dump(HERE / "complete.json", {"completed_at": datetime.now(timezone.utc).isoformat(), "conditions": 8})
        result = "; ".join(r["method"] + ": " + str(r["top1"]) + "/668" for r in label_report.build()["conditions"])
        coordination("complete: All eight label-only conditions and two private cluster artifacts are audited. Top-1 " + result + ". Report: http://127.0.0.1:59998/labels-20261017/report.html.", final=True)
    except BaseException:
        error = traceback.format_exc()
        (HERE / "error.log").write_text(error)
        state("Stopped", error=error.splitlines()[-1], log="error.log")
        if args.allow_network:
            coordination("stopped: Inspect internal/my-failed2-six-variants-20261017/labels-20261017/error.log. Preserve the active 6c and 6d worker.")
        raise


if __name__ == "__main__":
    main()
