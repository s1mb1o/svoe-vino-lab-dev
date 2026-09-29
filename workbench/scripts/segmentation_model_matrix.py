#!/usr/bin/env python3
"""Compare no segmentation, DIS, and SAM3 with six SigLIP2 SO400M image towers.

The utility freezes one catalogue and query manifest. It prepares each full-image, DIS,
or SAM3 input one time. It reuses the prepared PNG files for every model. It writes
resumable vector arrays and scores the complete matrix without changing a workbench
index.

Run from the workbench root:

    ~/.venvs/svoe-vino-lab/bin/python scripts/segmentation_model_matrix.py
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import os
import platform
import sys
import time
from contextlib import closing
from pathlib import Path

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIPELINE = os.path.join(ROOT, "pipeline")
sys.path.insert(0, PIPELINE)

import benchmark  # noqa: E402
import build_embeddings  # noqa: E402
import derive  # noqa: E402
import dis_litert  # noqa: E402
import embedding_run  # noqa: E402
import embeddings  # noqa: E402


VERSION = 1
DEFAULT_OUT = os.path.join(ROOT, "runs", "segmentation-model-matrix-2026-09-29")
SEGMENTATIONS = ("none", "dis", "sam3")
MODELS = (
    "gx10-siglip2-so400m-patch16-naflex-p256",
    "gx10-siglip2-so400m-patch16-naflex-p512",
    "gx10-siglip2-so400m-patch16-naflex-p1024",
    "gx10-siglip2-so400m-patch16-256",
    "gx10-siglip2-so400m-patch16-384",
    "gx10-siglip2-so400m-patch16-512",
)
LEVELS = (
    ("p256-vs-256", MODELS[0], MODELS[3]),
    ("p512-vs-384", MODELS[1], MODELS[4]),
    ("p1024-vs-512", MODELS[2], MODELS[5]),
)
NAFLEX = MODELS[:3]
FIXED = MODELS[3:]
TOP_K = 10


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as fh:
        json.dump(value, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(temporary, path)


def write_jsonl(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    os.replace(temporary, path)


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def model_entries(settings):
    out = {}
    for name in MODELS:
        try:
            out[name] = settings.find(name)
        except KeyError as exc:
            raise SystemExit("config.yaml has no embedding %s" % name) from exc
    return out


def dis_steps(settings):
    android = settings.find("android-siglip2-base-224-dis-white")
    first = android.views["full"][0]
    return [dict(first), {"step": "white_background"},
            {"step": "resize", "max_size": 1024, "aspect": "keep", "upscale": False}]


def sam3_steps(entries):
    steps = entries[MODELS[0]].views["full"]
    return [dict(step) for step in steps]


def none_steps():
    return [{"step": "white_background"},
            {"step": "resize", "max_size": 1024, "aspect": "keep", "upscale": False}]


def manifest_path(out):
    return os.path.join(out, "manifest.json")


def freeze_manifest(out, config, set_name):
    path = manifest_path(out)
    if os.path.exists(path):
        manifest = read_json(path)
        if manifest.get("version") != VERSION:
            raise SystemExit("the saved manifest has version %s; expected %s"
                             % (manifest.get("version"), VERSION))
        if "none" not in manifest.get("segmentations", []):
            if manifest.get("segmentations") != ["dis", "sam3"]:
                raise SystemExit("the saved manifest has an unexpected segmentation list")
            manifest["segmentations"] = list(SEGMENTATIONS)
            manifest["preprocessing"]["none"] = none_steps()
            manifest.setdefault("extensions", []).append({
                "at": now(), "segmentation": "none",
                "description": "original image, white alpha composite, long side at most 1024"})
            write_json(path, manifest)
        return manifest

    settings = embeddings.load_settings(config)
    entries = model_entries(settings)
    with closing(embeddings.open_database(settings.db_path)) as conn:
        wines, sources = embeddings.read_inputs(conn, settings.db_path)
    with closing(benchmark.open_database(settings.db_path)) as conn:
        queries, skipped = benchmark.build_queries(conn, settings.db_path, set_name)

    users = collections.defaultdict(list)
    types = collections.defaultdict(lambda: collections.defaultdict(list))
    for wine in wines:
        for image_type, digest in wine["columns"]:
            if sources[digest]["role"] != "full":
                continue
            if wine["slug"] not in users[digest]:
                users[digest].append(wine["slug"])
            types[digest][wine["slug"]].append(image_type)

    catalogue = []
    for digest in sorted(users):
        source = sources[digest]
        cut = source["cuts"].get("package")
        catalogue.append({
            "id": digest,
            "source_sha256": digest,
            "source_path": source["path"],
            "wines": users[digest],
            "image_types": dict(types[digest]),
            "sam3_package": None if cut is None else {
                "sha256": cut["sha256"], "path": cut["path"], "box": list(cut["box"])},
        })
    query_rows = [{key: row[key] for key in (
        "query_id", "image_path", "abs_path", "image_sha256", "slug", "label", "truth")}
        for row in queries]
    raw_config = Path(config).read_bytes()
    manifest = {
        "version": VERSION,
        "created_at": now(),
        "set": set_name,
        "database": os.path.abspath(settings.db_path),
        "config": os.path.abspath(config),
        "config_sha256": hashlib.sha256(raw_config).hexdigest(),
        "host": platform.node(),
        "models": {name: entries[name].summary() for name in MODELS},
        "levels": [{"name": name, "naflex": naflex, "fixed": fixed}
                   for name, naflex, fixed in LEVELS],
        "segmentations": list(SEGMENTATIONS),
        "preprocessing": {"none": none_steps(), "dis": dis_steps(settings),
                          "sam3": sam3_steps(entries)},
        "catalogue": catalogue,
        "queries": query_rows,
        "left_out": dict(skipped),
    }
    os.makedirs(out, exist_ok=True)
    write_json(path, manifest)
    write_jsonl(os.path.join(out, "catalogue.jsonl"), catalogue)
    write_jsonl(os.path.join(out, "queries.jsonl"), [
        {key: row[key] for key in row if key != "abs_path"} for row in query_rows])
    print("frozen: %d catalogue sources, %d queries" % (len(catalogue), len(query_rows)),
          flush=True)
    return manifest


def prepared_path(out, segmentation, dataset, item_id):
    return os.path.join(out, "prepared", segmentation, dataset, item_id + ".png")


def error_path(png_path):
    return png_path + ".error.json"


def save_prepared(path, image):
    data = embeddings.png_bytes(image)
    embeddings.write_atomic(path, data)
    try:
        os.unlink(error_path(path))
    except FileNotFoundError:
        pass
    return len(data), hashlib.sha256(data).hexdigest()


def save_error(path, error):
    write_json(error_path(path), {"error": str(error), "time": now()})


def catalogue_source(row):
    cut = row.get("sam3_package")
    return {"role": "full", "path": row["source_path"],
            "cuts": {"package": None if cut is None else {
                "sha256": cut["sha256"], "path": cut["path"], "box": tuple(cut["box"])}},
            "not_applicable": {"package": None}}


def prepare_catalogue_row(row, segmentation, steps, dis_segmenter=None):
    source = catalogue_source(row)
    cut = source["cuts"]["package"] if segmentation == "sam3" else None
    item = {"steps": steps, "cut": cut}
    return embeddings.prepare(item, source["path"], dis_segmenter=dis_segmenter)


def prepare_query_row(row, segmentation, steps, sam3, dis_segmenter=None):
    image, _ = derive.open_image(row["abs_path"])
    inputs, missing = embedding_run.query_inputs(
        image, {"full": steps}, sam3, scene_selection=True,
        dis_segmenter=dis_segmenter)
    if "full" not in inputs:
        raise embeddings.ItemError(missing.get("full") or "the full view has no input")
    return inputs["full"]


def prepare(out, manifest, config, datasets=("catalogue", "queries"),
            segmentations=SEGMENTATIONS, start=0, end=None, dis_threads=4):
    settings = embeddings.load_settings(config)
    entries = model_entries(settings)
    steps_of = {"none": none_steps(), "dis": dis_steps(settings),
                "sam3": sam3_steps(entries)}
    dis_segmenter = None
    if "dis" in segmentations:
        dis_spec = steps_of["dis"][0]
        dis_segmenter = dis_litert.Segmenter(dis_spec["model"], dis_spec["revision"],
                                             threads=dis_threads)
    sam3 = None
    if "sam3" in segmentations:
        endpoint = os.environ.get("SAM3_ENDPOINT")
        if not endpoint:
            raise SystemExit("SAM3_ENDPOINT MUST name the cached SAM3 service")
        sam3 = embedding_run.CachedSam3(endpoint)
    started = time.monotonic()
    totals = {"catalogue": len(manifest["catalogue"]), "queries": len(manifest["queries"])}
    for dataset in datasets:
        rows = manifest[dataset][start:end]
        for segmentation in segmentations:
            done = failed = reused = 0
            phase_started = time.monotonic()
            for row in rows:
                path = prepared_path(out, segmentation, dataset, row["id"] if dataset ==
                                     "catalogue" else row["query_id"])
                if os.path.isfile(path):
                    reused += 1
                    done += 1
                    continue
                os.makedirs(os.path.dirname(path), exist_ok=True)
                try:
                    if dataset == "catalogue":
                        image = prepare_catalogue_row(
                            row, segmentation, steps_of[segmentation], dis_segmenter)
                    else:
                        image = prepare_query_row(
                            row, segmentation, steps_of[segmentation], sam3, dis_segmenter)
                    save_prepared(path, image)
                except (OSError, ValueError, embeddings.ItemError,
                        derive.Sam3Unavailable) as exc:
                    save_error(path, exc)
                    failed += 1
                done += 1
                if done % 50 == 0 or done == len(rows):
                    print("prepare %s/%s[%d:%s]: %d/%d, failed %d, reused %d, %.1f s"
                          % (segmentation, dataset, start, "" if end is None else end,
                             done, len(rows), failed, reused,
                             time.monotonic() - phase_started), flush=True)
    write_jsonl(os.path.join(out, "prepared.jsonl"), prepared_records(out, manifest))
    write_json(os.path.join(out, "preparation.json"), preparation_summary(out, manifest,
                                                                           started))


def prepared_records(out, manifest):
    records = []
    for segmentation in SEGMENTATIONS:
        for dataset in ("catalogue", "queries"):
            for row in manifest[dataset]:
                item_id = row["id"] if dataset == "catalogue" else row["query_id"]
                path = prepared_path(out, segmentation, dataset, item_id)
                record = {"segmentation": segmentation, "dataset": dataset,
                          "id": item_id, "source_sha256": row["image_sha256"] if dataset ==
                          "queries" else row["source_sha256"]}
                if os.path.isfile(path):
                    record.update(path=os.path.relpath(path, out), bytes=os.path.getsize(path),
                                  prepared_sha256=file_sha256(path), error=None)
                else:
                    error = (read_json(error_path(path)).get("error")
                             if os.path.isfile(error_path(path)) else "missing prepared image")
                    record.update(path=None, bytes=None, prepared_sha256=None, error=error)
                records.append(record)
    return records


def preparation_summary(out, manifest, started=None):
    summary = {"finished_at": now(), "wall_s": None if started is None else
               round(time.monotonic() - started, 1), "sets": {}}
    for segmentation in SEGMENTATIONS:
        summary["sets"][segmentation] = {}
        for dataset in ("catalogue", "queries"):
            rows = manifest[dataset]
            ids = [row["id"] if dataset == "catalogue" else row["query_id"] for row in rows]
            paths = [prepared_path(out, segmentation, dataset, item_id) for item_id in ids]
            errors = [read_json(error_path(path))["error"] for path in paths
                      if not os.path.isfile(path) and os.path.isfile(error_path(path))]
            summary["sets"][segmentation][dataset] = {
                "total": len(paths), "prepared": sum(os.path.isfile(path) for path in paths),
                "failed": len(errors), "errors": dict(collections.Counter(errors))}
    return summary


def vector_path(out, segmentation, model, dataset):
    return os.path.join(out, "vectors", segmentation, model, dataset + ".npy")


def vector_dim(settings, model):
    directory = embeddings.entry_dir(settings.db_path, model)
    index = embeddings.read_index(directory)
    dim = (index or {}).get("dim")
    if not isinstance(dim, int) or dim < 1:
        raise SystemExit("the existing index of %s has no vector dimension" % model)
    return dim


def open_vectors(path, count, dim):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        matrix = np.load(path, mmap_mode="r+")
        if matrix.shape != (count, dim) or matrix.dtype != np.float32:
            raise SystemExit("%s has shape %s and dtype %s; expected (%d, %d) float32"
                             % (path, matrix.shape, matrix.dtype, count, dim))
        return matrix
    matrix = np.lib.format.open_memmap(path, mode="w+", dtype=np.float32,
                                       shape=(count, dim))
    matrix[:] = np.nan
    matrix.flush()
    return matrix


def embed_dataset(out, manifest, settings, entry, segmentation, dataset, batch_size):
    rows = manifest[dataset]
    ids = [row["id"] if dataset == "catalogue" else row["query_id"] for row in rows]
    paths = [prepared_path(out, segmentation, dataset, item_id) for item_id in ids]
    matrix = open_vectors(vector_path(out, segmentation, entry.name, dataset), len(rows),
                          vector_dim(settings, entry.name))
    backend = build_embeddings.OpenAIBackend(entry)
    wanted = [i for i, path in enumerate(paths)
              if os.path.isfile(path) and not np.isfinite(matrix[i]).all()]
    reused = sum(os.path.isfile(path) and np.isfinite(matrix[i]).all()
                 for i, path in enumerate(paths))
    started = time.monotonic()
    done = 0
    for offset in range(0, len(wanted), batch_size):
        indices = wanted[offset:offset + batch_size]
        pngs = [Path(paths[i]).read_bytes() for i in indices]
        vectors = np.asarray(backend.embed(pngs), dtype=np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        if vectors.shape[1] != matrix.shape[1] or not np.isfinite(vectors).all() or np.any(
                norms <= 0):
            raise SystemExit("%s returned invalid vectors for %s/%s"
                             % (entry.name, segmentation, dataset))
        matrix[indices] = vectors / norms
        matrix.flush()
        done += len(indices)
        if done % (batch_size * 10) == 0 or done == len(wanted):
            print("embed %s/%s/%s: %d/%d new, %d reused, %.1f s"
                  % (segmentation, entry.name, dataset, done, len(wanted), reused,
                     time.monotonic() - started), flush=True)
    return {"total": len(rows), "embedded": int(np.isfinite(matrix).all(axis=1).sum()),
            "missing": int((~np.isfinite(matrix).all(axis=1)).sum()), "new": len(wanted),
            "reused": int(reused), "wall_s": round(time.monotonic() - started, 1)}


def embed(out, manifest, config, batch_size):
    settings = embeddings.load_settings(config)
    entries = model_entries(settings)
    started = time.monotonic()
    summary = {"started_at": now(), "batch_size": batch_size, "cells": {}}
    for segmentation in SEGMENTATIONS:
        for name in MODELS:
            key = "%s/%s" % (segmentation, name)
            summary["cells"][key] = {}
            for dataset in ("catalogue", "queries"):
                summary["cells"][key][dataset] = embed_dataset(
                    out, manifest, settings, entries[name], segmentation, dataset, batch_size)
            write_json(os.path.join(out, "embedding.json"), summary)
    summary["finished_at"] = now()
    summary["wall_s"] = round(time.monotonic() - started, 1)
    write_json(os.path.join(out, "embedding.json"), summary)


def catalogue_mapping(manifest):
    wines = sorted({slug for row in manifest["catalogue"] for slug in row["wines"]})
    number = {slug: i for i, slug in enumerate(wines)}
    source_indices, wine_indices = [], []
    for source_index, row in enumerate(manifest["catalogue"]):
        for slug in row["wines"]:
            source_indices.append(source_index)
            wine_indices.append(number[slug])
    return wines, np.asarray(source_indices, dtype=np.int64), np.asarray(
        wine_indices, dtype=np.int64)


def rank_query(vector, catalogue, wines, source_indices, wine_indices, top_k=TOP_K):
    cosine = catalogue @ vector
    scores = np.full(len(wines), -np.inf, dtype=np.float32)
    np.maximum.at(scores, wine_indices, cosine[source_indices])
    found = np.flatnonzero(np.isfinite(scores))
    order = found[np.lexsort((np.asarray(wines)[found], -scores[found]))]
    positions = np.full(len(wines), -1, dtype=np.int64)
    positions[order] = np.arange(1, len(order) + 1)
    top = order[:top_k]
    return ([{"slug": wines[i], "score": round(float(scores[i]), 6), "rank": rank}
             for rank, i in enumerate(top, 1)], positions)


def result_row(query, candidates, positions, wine_number, error=None):
    predicted = candidates[0]["slug"] if candidates else None
    rank = full_rank = None
    if query["label"] == "positive" and query["slug"] in wine_number and positions is not None:
        found_rank = int(positions[wine_number[query["slug"]]])
        full_rank = found_rank if found_rank > 0 else None
        rank = full_rank if full_rank is not None and full_rank <= TOP_K else None
        outcome = "hit" if rank == 1 else "miss"
    elif query["label"] == "negative":
        if predicted is None:
            outcome = "no_answer"
        elif predicted == query["slug"]:
            outcome = "false_match_at_1"
            rank = next((cand["rank"] for cand in candidates
                         if cand["slug"] == query["slug"]), None)
        else:
            outcome = "other_slug_at_1"
            rank = next((cand["rank"] for cand in candidates
                         if cand["slug"] == query["slug"]), None)
    else:
        outcome = "no_answer" if predicted is None else "answered"
    return {"query_id": query["query_id"], "image_path": query["image_path"],
            "image_sha256": query["image_sha256"], "slug": query["slug"],
            "label": query["label"], "truth": query["truth"], "candidates": candidates,
            "predicted_slug": predicted, "rank_of_truth": rank,
            "full_rank_of_truth": full_rank, "outcome": outcome, "error": error}


def cell_metrics(rows):
    pos = [row for row in rows if row["label"] == "positive"]
    neg = [row for row in rows if row["label"] == "negative"]

    def hits(k):
        return sum(row["rank_of_truth"] is not None and row["rank_of_truth"] <= k
                   for row in pos)

    ranks = [row["rank_of_truth"] for row in pos if row["rank_of_truth"] is not None]
    rejected = sum(row["outcome"] == "other_slug_at_1" for row in neg)
    return {"queries": len(rows), "positive": {"n": len(pos),
             "hits_at_1": hits(1), "recall_at_1": hits(1) / len(pos),
             "hits_at_5": hits(5), "recall_at_5": hits(5) / len(pos),
             "hits_at_10": hits(10), "recall_at_10": hits(10) / len(pos),
             "mrr_at_10": sum(1.0 / rank for rank in ranks) / len(pos),
             "errors": sum(bool(row["error"]) for row in pos)},
            "negative": {"n": len(neg), "rejected_at_1": rejected,
             "rejection_rate_at_1": rejected / len(neg),
             "false_match_at_1": sum(row["outcome"] == "false_match_at_1" for row in neg),
             "errors": sum(bool(row["error"]) for row in neg)}}


def score_cell(out, manifest, segmentation, model):
    result_path = os.path.join(out, "results", segmentation, model + ".jsonl")
    catalogue = np.load(vector_path(out, segmentation, model, "catalogue"), mmap_mode="r")
    query_vectors = np.load(vector_path(out, segmentation, model, "queries"), mmap_mode="r")
    wines, source_indices, wine_indices = catalogue_mapping(manifest)
    wine_number = {slug: i for i, slug in enumerate(wines)}
    valid_catalogue = np.isfinite(catalogue).all(axis=1)
    keep = valid_catalogue[source_indices]
    source_indices, wine_indices = source_indices[keep], wine_indices[keep]
    rows = []
    started = time.monotonic()
    for i, query in enumerate(manifest["queries"]):
        if not np.isfinite(query_vectors[i]).all():
            p = prepared_path(out, segmentation, "queries", query["query_id"])
            error = (read_json(error_path(p))["error"] if os.path.isfile(error_path(p))
                     else "the query has no vector")
            rows.append(result_row(query, [], None, wine_number, error))
        else:
            candidates, positions = rank_query(query_vectors[i], catalogue, wines,
                                                source_indices, wine_indices)
            rows.append(result_row(query, candidates, positions, wine_number))
        if (i + 1) % 250 == 0 or i + 1 == len(manifest["queries"]):
            print("score %s/%s: %d/%d, %.1f s" % (
                segmentation, model, i + 1, len(manifest["queries"]),
                time.monotonic() - started), flush=True)
    write_jsonl(result_path, rows)
    return rows, cell_metrics(rows)


def exact_mcnemar(wins, losses):
    total = wins + losses
    if total == 0:
        return 1.0
    small = min(wins, losses)
    tail = sum(math.comb(total, i) for i in range(small + 1)) / (2.0 ** total)
    return min(1.0, 2.0 * tail)


def correct(row, metric):
    if row["error"]:
        return False
    if metric.startswith("positive_r"):
        depth = int(metric.rsplit("r", 1)[1])
        rank = row["rank_of_truth"]
        return rank is not None and rank <= depth
    if metric == "negative_rejection":
        return row["outcome"] == "other_slug_at_1"
    raise ValueError(metric)


def paired(first, second, metric, label):
    keys = [key for key, row in first.items() if row["label"] == label]
    if not keys:
        return {"n": 0, "first_rate": None, "second_rate": None, "delta": None,
                "second_wins": 0, "second_losses": 0, "exact_mcnemar_p": 1.0}
    wins = sum(correct(second[key], metric) and not correct(first[key], metric) for key in keys)
    losses = sum(correct(first[key], metric) and not correct(second[key], metric) for key in keys)
    first_rate = sum(correct(first[key], metric) for key in keys) / len(keys)
    second_rate = sum(correct(second[key], metric) for key in keys) / len(keys)
    return {"n": len(keys), "first_rate": first_rate, "second_rate": second_rate,
            "delta": second_rate - first_rate, "second_wins": wins,
            "second_losses": losses, "exact_mcnemar_p": exact_mcnemar(wins, losses)}


def pair_block(first_rows, second_rows):
    first = {row["query_id"]: row for row in first_rows}
    second = {row["query_id"]: row for row in second_rows}
    return {metric: paired(first, second, metric, "positive")
            for metric in ("positive_r1", "positive_r5", "positive_r10")} | {
                "negative_rejection": paired(first, second, "negative_rejection", "negative")}


def score(out, manifest):
    all_rows, cells = {}, {}
    started = time.monotonic()
    for segmentation in SEGMENTATIONS:
        for model in MODELS:
            key = "%s/%s" % (segmentation, model)
            all_rows[key], cells[key] = score_cell(out, manifest, segmentation, model)
    comparisons = {"sam3_vs_dis": {}, "segmentation_vs_none": {},
                   "compute_levels": {}, "naflex_vs_fixed": {}}
    for model in MODELS:
        comparisons["sam3_vs_dis"][model] = pair_block(
            all_rows["dis/%s" % model], all_rows["sam3/%s" % model])
        comparisons["segmentation_vs_none"][model] = {
            segmentation: pair_block(all_rows["none/%s" % model],
                                     all_rows["%s/%s" % (segmentation, model)])
            for segmentation in ("dis", "sam3")}
    for segmentation in SEGMENTATIONS:
        for family, models in (("naflex", NAFLEX), ("fixed", FIXED)):
            base = all_rows["%s/%s" % (segmentation, models[0])]
            for model in models[1:]:
                key = "%s/%s/%s-vs-%s" % (segmentation, family, model, models[0])
                comparisons["compute_levels"][key] = pair_block(base,
                    all_rows["%s/%s" % (segmentation, model)])
            key = "%s/%s/%s-vs-%s" % (segmentation, family, models[2], models[1])
            comparisons["compute_levels"][key] = pair_block(
                all_rows["%s/%s" % (segmentation, models[1])],
                all_rows["%s/%s" % (segmentation, models[2])])
        for level, naflex, fixed in LEVELS:
            comparisons["naflex_vs_fixed"]["%s/%s" % (segmentation, level)] = pair_block(
                all_rows["%s/%s" % (segmentation, naflex)],
                all_rows["%s/%s" % (segmentation, fixed)])
    result = {"created_at": now(), "cells": cells, "comparisons": comparisons,
              "wall_s": round(time.monotonic() - started, 1)}
    write_json(os.path.join(out, "metrics.json"), result)
    return result


def verify(out, manifest):
    problems = []
    for segmentation in SEGMENTATIONS:
        for dataset in ("catalogue", "queries"):
            rows = manifest[dataset]
            ids = [row["id"] if dataset == "catalogue" else row["query_id"] for row in rows]
            for item_id in ids:
                path = prepared_path(out, segmentation, dataset, item_id)
                if os.path.isfile(path) and os.path.getsize(path) == 0:
                    problems.append("empty prepared file: %s" % path)
        for model in MODELS:
            for dataset in ("catalogue", "queries"):
                path = vector_path(out, segmentation, model, dataset)
                if not os.path.isfile(path):
                    problems.append("missing vector file: %s" % path)
                    continue
                matrix = np.load(path, mmap_mode="r")
                expected = len(manifest[dataset])
                if len(matrix) != expected:
                    problems.append("%s has %d rows; expected %d" % (path, len(matrix), expected))
                finite = np.isfinite(matrix).all(axis=1)
                if finite.any():
                    norms = np.linalg.norm(matrix[finite], axis=1)
                    if not np.allclose(norms, 1.0, atol=2e-5):
                        problems.append("%s has non-unit vectors" % path)
    if problems:
        raise SystemExit("verification failed:\n" + "\n".join(problems[:50]))
    print("verification passed", flush=True)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=os.path.join(ROOT, "config.yaml"))
    parser.add_argument("--set", default="my", dest="set_name")
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--prepare-dataset", choices=("catalogue", "queries"),
                        action="append", help="prepare only this dataset; repeat for both")
    parser.add_argument("--prepare-segmentation", choices=SEGMENTATIONS, action="append",
                        help="prepare only this segmentation; repeat for both")
    parser.add_argument("--prepare-start", type=int, default=0,
                        help="first manifest row to prepare")
    parser.add_argument("--prepare-end", type=int,
                        help="exclusive final manifest row to prepare")
    parser.add_argument("--dis-threads", type=int, default=4,
                        help="LiteRT threads of this process")
    parser.add_argument("--phase", choices=("all", "prepare", "embed", "score", "verify"),
                        default="all")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.batch_size < 1 or args.batch_size > 16:
        raise SystemExit("--batch-size MUST be from 1 to 16")
    if args.dis_threads < 1 or args.dis_threads > 8:
        raise SystemExit("--dis-threads MUST be from 1 to 8")
    if args.prepare_start < 0 or (args.prepare_end is not None and
                                  args.prepare_end <= args.prepare_start):
        raise SystemExit("the prepare range is not valid")
    manifest = freeze_manifest(os.path.abspath(args.out), args.config, args.set_name)
    if args.phase in ("all", "prepare"):
        prepare(args.out, manifest, args.config,
                tuple(args.prepare_dataset or ("catalogue", "queries")),
                tuple(args.prepare_segmentation or SEGMENTATIONS), args.prepare_start,
                args.prepare_end, args.dis_threads)
    if args.phase in ("all", "embed"):
        embed(args.out, manifest, args.config, args.batch_size)
    if args.phase in ("all", "score"):
        score(args.out, manifest)
    if args.phase in ("all", "verify"):
        verify(args.out, manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
