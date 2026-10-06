"""Train sub-center ArcFace on a current, frozen DINOv3 catalogue index.

The command reads the catalogue database and cached vectors. It sends no images.
Training MUST NOT use benchmark query labels. A source and its cuts and rotations
remain in one split. Exact duplicate prepared images remain in one split too.
"""
import argparse
import collections
from contextlib import closing
import copy
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
import yaml

import arcface
import embeddings


class SubCenterArcFace(nn.Module):
    """Classify normalized features with an additive angular target margin.

    Each class has K centers. The nearest center supplies the class cosine.
    Class counts are distinct training source groups, not views or rotations.
    """

    def __init__(self, centers, counts, k=3, scale=30.0, margin_a=0.5,
                 margin_b=0.05, margin_power=0.25):
        super().__init__()
        if (k < 1 or scale <= 0 or not math.isfinite(scale)
                or margin_a < 0 or margin_b < 0 or margin_power < 0
                or centers.ndim != 2 or counts.shape != (len(centers),)
                or torch.any(counts <= 0)):
            raise ValueError("invalid ArcFace dimensions, counts, or margin settings")
        margins = margin_a * counts.float().pow(-margin_power) + margin_b
        if not torch.isfinite(margins).all() or torch.any(margins >= math.pi / 2):
            raise ValueError("ArcFace margins MUST be finite and smaller than pi/2")
        self.k, self.scale = k, scale
        self.register_buffer("margins", margins)
        initial = F.normalize(centers.float(), dim=1).repeat_interleave(k, dim=0)
        self.weight = nn.Parameter(initial + 0.05 * torch.randn_like(initial))

    def logits(self, features, labels):
        cosine = F.linear(F.normalize(features.float(), dim=1),
                          F.normalize(self.weight.float(), dim=1))
        cosine = cosine.reshape(len(features), -1, self.k).max(dim=2).values
        target = cosine.gather(1, labels[:, None]).clamp(-1 + 1e-7, 1 - 1e-7)
        margin = self.margins[labels, None]
        # cos(theta + m). The fallback preserves monotonicity near theta = pi.
        angular = target * margin.cos() - (1 - target.square()).sqrt() * margin.sin()
        angular = torch.where(target > torch.cos(math.pi - margin), angular,
                              target - torch.sin(math.pi - margin) * margin)
        return self.scale * cosine.scatter(1, labels[:, None], angular)

    def forward(self, features, labels):
        return F.cross_entropy(self.logits(features, labels), labels)


def collect_samples(embedding, db_path, directory):
    """Read only current, unambiguous catalogue rows. Return vectors and provenance."""
    if embedding.arcface is not None:
        raise ValueError("the source index MUST contain base DINOv3 features, without arcface")
    index = embeddings.read_index(directory)
    if index is None:
        raise ValueError("build the source DINOv3 index first")
    vectors = embeddings.read_vectors(directory, index)
    with closing(embeddings.open_database(db_path)) as conn:
        wines, sources = embeddings.read_inputs(conn, db_path)
    items = embeddings.plan_items(embedding, sources)
    status = embeddings.item_status(items, index, embeddings.image_names(directory))
    owners = collections.defaultdict(set)
    for wine in wines:
        for _, digest in wine["columns"]:
            owners[digest].add(wine["slug"])

    records = [record for state, record in status.values() if state == "current"]
    parent = {record["source_sha256"]: record["source_sha256"] for record in records}

    def root(digest):
        while parent[digest] != digest:
            parent[digest] = parent[parent[digest]]
            digest = parent[digest]
        return digest

    seen = {}
    for record in records:
        digest = record["source_sha256"]
        data = (Path(directory) / record["image"]).read_bytes()
        keys = [("prepared", hashlib.sha256(data).hexdigest())]
        if record.get("derivative_sha256"):
            keys.append(("derivative", record["derivative_sha256"]))
        for key in keys:
            if key in seen:
                left, right = sorted((root(digest), root(seen[key])))
                parent[right] = left
            seen[key] = digest
    group_owners = collections.defaultdict(set)
    for digest in parent:
        group_owners[root(digest)].update(owners[digest])

    picked, samples = [], []
    ambiguous = 0
    taken = set()
    for record in records:
        group = root(record["source_sha256"])
        slugs = group_owners[group]
        if len(slugs) != 1:
            ambiguous += 1
            continue
        span = embeddings.record_rows(record, len(vectors))
        if embeddings.record_angles(record) != items[(record["source_sha256"], record["view"])].get("angles", [0]):
            raise ValueError("the source index has inconsistent rotation rows")
        for row in range(span.start, span.stop):
            if row in taken:
                raise ValueError("the source index assigns one vector row to two items")
            taken.add(row)
            picked.append(row)
            samples.append({"wine_slug": next(iter(slugs)), "source_sha256": record["source_sha256"],
                            "group": group, "view": record["view"], "row": row,
                            "embedding_hash": record["embedding_hash"]})
    if not picked:
        raise ValueError("the source index has no current unambiguous training rows")
    features = arcface.normalize(vectors[picked])
    provenance = {"source_embedding": embedding.name,
                  "source_index_sha256": hashlib.sha256((Path(directory) / embeddings.INDEX).read_bytes()).hexdigest(),
                  "features_sha256": hashlib.sha256(features.tobytes()).hexdigest(),
                  "ambiguous_items_excluded": ambiguous,
                  "current_items": len(records), "samples": samples}
    return features, provenance


def split_samples(samples, fraction=0.2, seed=42):
    """Hold out whole source groups within classes that have at least two groups."""
    if not 0 < fraction < 1:
        raise ValueError("validation fraction MUST be between 0 and 1")
    groups = collections.defaultdict(set)
    for sample in samples:
        groups[sample["wine_slug"]].add(sample["group"])
    classes = sorted(groups)
    if len(classes) < 2:
        raise ValueError("ArcFace training needs at least two wine identities")
    rng = np.random.default_rng(seed)
    held = set()
    for slug in classes:
        choices = sorted(groups[slug])
        if len(choices) >= 2:
            count = min(len(choices) - 1, max(1, round(len(choices) * fraction)))
            held.update(rng.choice(choices, size=count, replace=False).tolist())
    train = np.array([i for i, row in enumerate(samples) if row["group"] not in held], dtype=np.int64)
    valid = np.array([i for i, row in enumerate(samples) if row["group"] in held], dtype=np.int64)
    if len(valid) == 0:
        raise ValueError("validation needs at least one identity with two distinct source groups")
    class_ids = {slug: i for i, slug in enumerate(classes)}
    labels = np.array([class_ids[row["wine_slug"]] for row in samples], dtype=np.int64)
    counts = np.array([len({samples[i]["group"] for i in train if samples[i]["wine_slug"] == slug})
                       for slug in classes], dtype=np.float32)
    return train, valid, labels, classes, counts


def retrieval_metrics(features, labels, samples, train, valid):
    """Measure source-disjoint query recall against the training gallery.

    Scores use the best image cosine per wine in the same view as the query.
    All validation views of one source group receive equal total weight.
    """
    features = arcface.normalize(features)
    query_weights = collections.Counter(samples[i]["group"] for i in valid)
    hits = {1: 0.0, 5: 0.0, 10: 0.0}
    total, queries = 0.0, 0
    class_count = int(labels.max()) + 1
    for start in range(0, len(valid), 128):
        batch = valid[start:start + 128]
        similarities = features[batch] @ features[train].T
        for position, query in enumerate(batch):
            mask = np.array([samples[i]["view"] == samples[query]["view"] for i in train])
            if not np.any(labels[train[mask]] == labels[query]):
                continue
            scores = np.full(class_count, -np.inf, dtype=np.float32)
            np.maximum.at(scores, labels[train[mask]], similarities[position, mask])
            order = np.argsort(-scores, kind="stable")
            rank = int(np.flatnonzero(order == labels[query])[0]) + 1
            weight = 1.0 / query_weights[samples[query]["group"]]
            total += weight
            queries += 1
            for k in hits:
                hits[k] += weight * (rank <= k)
    if total == 0:
        raise ValueError("validation has no query with a same-view training reference")
    return {"recall@%d" % k: hits[k] / total for k in hits} | {
        "queries": queries, "source_group_weight": total,
        "skipped_queries": len(valid) - queries}


def fit(features, provenance, dim=512, epochs=30, batch_size=256, learning_rate=1e-3,
        device="cpu", seed=42, fraction=0.2, k=3, scale=30.0,
        margin_a=0.5, margin_b=0.05, margin_power=0.25, emit=print):
    """Train a projection. Select its checkpoint by held-out recall@1."""
    if (dim < 1 or dim > features.shape[1] or epochs < 1 or batch_size < 1
            or not math.isfinite(learning_rate) or learning_rate <= 0):
        raise ValueError("invalid projection dimension or training settings")
    torch.manual_seed(seed)
    samples = provenance["samples"]
    train, valid, labels, classes, counts = split_samples(samples, fraction, seed)
    features = arcface.normalize(features)
    # Initialize from training data alone. PCA avoids a random feature-space reset.
    mean = features[train].mean(axis=0)
    centered = features[train] - mean
    _, axes = np.linalg.eigh(centered.T @ centered / len(train))
    weight = axes[:, -dim:][:, ::-1].T.copy()
    head = nn.Linear(features.shape[1], dim).to(device)
    with torch.no_grad():
        head.weight.copy_(torch.from_numpy(weight).to(device))
        head.bias.copy_(torch.from_numpy(-weight @ mean).to(device))
    x = torch.from_numpy(features[train]).to(device)
    y = torch.from_numpy(labels[train]).to(device)
    with torch.no_grad():
        initial = F.normalize(head(x), dim=1)
        centers = torch.zeros((len(classes), dim), device=device)
        centers.index_add_(0, y, initial)
        centers = F.normalize(centers, dim=1)
    loss = SubCenterArcFace(centers, torch.from_numpy(counts).to(device), k=k, scale=scale,
                           margin_a=margin_a, margin_b=margin_b, margin_power=margin_power).to(device)
    optimizer = torch.optim.AdamW(list(head.parameters()) + list(loss.parameters()),
                                 lr=learning_rate, weight_decay=0.01)
    # Each wine receives the same expected sampling weight.
    frequency = np.bincount(labels[train], minlength=len(classes))
    weights = torch.from_numpy((1.0 / frequency[labels[train]]).astype(np.float64))
    generator = torch.Generator().manual_seed(seed)
    baseline = retrieval_metrics(features, labels, samples, train, valid)
    history = []
    best = None
    for epoch in range(epochs + 1):
        average = None
        if epoch:
            head.train()
            selection = torch.multinomial(weights, len(train), replacement=True, generator=generator)
            total_loss = 0.0
            for batch in selection.split(batch_size):
                ids = batch.to(device)
                optimizer.zero_grad(set_to_none=True)
                value = loss(head(x[ids]), y[ids])
                if not torch.isfinite(value):
                    raise ValueError("ArcFace training loss is not finite")
                value.backward()
                nn.utils.clip_grad_norm_(list(head.parameters()) + list(loss.parameters()), 5.0)
                optimizer.step()
                total_loss += value.item() * len(batch)
            average = total_loss / len(train)
        head.eval()
        projection = arcface.Projection(head.weight.detach().cpu().numpy().copy(),
                                        head.bias.detach().cpu().numpy().copy(), {"format": arcface.FORMAT})
        metrics = retrieval_metrics(projection.transform(features), labels, samples, train, valid)
        record = {"epoch": epoch, "loss": average, **metrics}
        history.append(record)
        emit(json.dumps(record, sort_keys=True))
        # Keep the first checkpoint at a tied score. Epoch 0 is an explicit PCA baseline.
        if best is None or metrics["recall@1"] > best[0]:
            best = (metrics["recall@1"], epoch, projection)
    report = {"baseline_dinov3": baseline, "selected_epoch": best[1],
              "selected_metrics": history[best[1]], "history": history,
              "train_rows": len(train), "validation_rows": len(valid), "classes": len(classes),
              "single_source_classes": int(sum(counts[i] == 1 and not any(labels[v] == i for v in valid)
                                               for i in range(len(classes)))),
              "settings": {"dim": dim, "epochs": epochs, "batch_size": batch_size,
                           "learning_rate": learning_rate, "device": device, "seed": seed,
                           "validation_fraction": fraction, "k": k, "scale": scale,
                           "margin_a": margin_a, "margin_b": margin_b, "margin_power": margin_power},
              "classes_by_label": classes, "train_sample_ids": train.tolist(),
              "validation_sample_ids": valid.tolist()}
    return best[2], report


def derived_config(config_path, source, output_name, spec):
    """Create a separate configuration with one new embedding and two pipelines."""
    _, config, db_path = embeddings.read_config(config_path)
    config = copy.deepcopy(config)
    config["database_file"] = db_path
    if any(row.get("name") == output_name for row in config.get("embeddings", [])):
        raise ValueError("the output embedding name already exists in the source configuration")
    raw = source.summary()
    raw.update(name=output_name, arcface=spec)
    raw["views"] = {view: {"steps": steps} for view, steps in source.views.items()}
    config["embeddings"].append(raw)
    for suffix, views in [("", None), ("-crop", raw["views"])]:
        name = output_name + suffix
        if any(row.get("name") == name for row in config.get("pipeline", [])):
            raise ValueError("the output pipeline name already exists")
        row = {"name": name, "backend": "embedding", "embedding": output_name}
        if views is not None:
            row["views"] = views
        else:
            row["views"] = {view: {"steps": [{"step": "resize", "max_size": 1024}]}
                            for view in source.views}
        config.setdefault("pipeline", []).append(row)
    return config, embeddings.Embedding(raw)


def export_index(source, target, db_path, projection):
    """Transform current source vectors without new model or segmentation calls."""
    source_dir = embeddings.entry_dir(db_path, source.name)
    target_dir = embeddings.entry_dir(db_path, target.name)
    Path(target_dir).mkdir(parents=True, exist_ok=True)
    embeddings.acquire_lock(target_dir)
    try:
        if embeddings.read_index(target_dir) is not None:
            raise ValueError("the output index already exists; use a new output name")
        index = embeddings.read_index(source_dir)
        vectors = embeddings.read_vectors(source_dir, index)
        with closing(embeddings.open_database(db_path)) as conn:
            _, sources = embeddings.read_inputs(conn, db_path)
        source_items = embeddings.plan_items(source, sources)
        target_items = embeddings.plan_items(target, sources)
        status = embeddings.item_status(source_items, index, embeddings.image_names(source_dir))
        records, blocks = [], []
        position = 0
        for key, (state, record) in status.items():
            if state != "current":
                continue
            span = embeddings.record_rows(record, len(vectors))
            if embeddings.record_angles(record) != source_items[key].get("angles", [0]):
                raise ValueError("the source index has inconsistent rotation rows")
            block = projection.transform(vectors[span])
            copied = dict(record, row=position, embedding_hash=target_items[key]["embedding_hash"])
            path = Path(target_dir) / record["image"]
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(Path(source_dir) / record["image"], path)
            records.append(copied)
            blocks.append(block)
            position += len(block)
        if not blocks:
            raise ValueError("the source index has no current vectors")
        out = dict(index, name=target.name, config=target.summary(), items=records, failures=[],
                   dim=projection.weight.shape[0], updated_at=embeddings.now(),
                   view_config_hash={view: target.view_config_hash(view) for view in target.views},
                   software=dict(index.get("software", {}), arcface_sha256=target.arcface["sha256"],
                                 arcface_format=arcface.FORMAT, source_embedding=source.name))
        embeddings.write_checkpoint(target_dir, out, np.concatenate(blocks))
        return {"directory": target_dir, "items": len(records), "vectors": position}
    finally:
        embeddings.release_lock(target_dir)


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=embeddings.CONFIG_PATH)
    parser.add_argument("--name", required=True, help="source DINOv3 embedding")
    parser.add_argument("--output-name", required=True, help="new ArcFace embedding name")
    parser.add_argument("--output-dir", required=True, help="new directory for weights, report, and config")
    parser.add_argument("--dim", type=int, default=512)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--device", choices=("cpu", "cuda", "mps"), default="cpu")
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--validation-fraction", type=float, default=0.2)
    parser.add_argument("--sub-centers", type=int, default=3)
    parser.add_argument("--scale", type=float, default=30.0)
    parser.add_argument("--margin-a", type=float, default=0.5)
    parser.add_argument("--margin-b", type=float, default=0.05)
    parser.add_argument("--margin-power", type=float, default=0.25)
    parser.add_argument("--export-index", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.threads < 1:
            raise ValueError("threads MUST be positive")
        torch.set_num_threads(args.threads)
        settings = embeddings.load_settings(args.config)
        source = settings.find(args.name)
        if not embeddings.NAME_RE.fullmatch(args.output_name) or args.output_name == source.name:
            raise ValueError("output-name MUST be a new valid embedding name")
        output = Path(args.output_dir).resolve()
        if output.exists():
            raise ValueError("output-dir already exists; choose a new artifact directory")
        if args.export_index and Path(embeddings.entry_dir(settings.db_path, args.output_name), embeddings.INDEX).exists():
            raise ValueError("the output index already exists; choose a new output name")
        features, provenance = collect_samples(source, settings.db_path,
                                               embeddings.entry_dir(settings.db_path, source.name))
        projection, report = fit(features, provenance, dim=args.dim, epochs=args.epochs,
                                 batch_size=args.batch_size, learning_rate=args.learning_rate,
                                 device=args.device, seed=args.seed, fraction=args.validation_fraction,
                                 k=args.sub_centers, scale=args.scale, margin_a=args.margin_a,
                                 margin_b=args.margin_b, margin_power=args.margin_power)
        projection.metadata.update(source_model={"model": source.model, "extra_body": source.extra_body},
                                   trained_at=embeddings.now(), source_embedding=source.name,
                                   training_features_sha256=provenance["features_sha256"],
                                   selected_epoch=report["selected_epoch"])
        data = projection.dumps()
        spec = {"checkpoint": str(output / "projection.npz"), "sha256": hashlib.sha256(data).hexdigest()}
        config, target = derived_config(args.config, source, args.output_name, spec)
        output.mkdir(parents=True)
        embeddings.write_atomic(str(output / "projection.npz"), data)
        report["checkpoint"] = spec
        for name, value in [("report.json", report), ("training-snapshot.json", provenance)]:
            embeddings.write_atomic(str(output / name), (json.dumps(value, indent=2) + "\n").encode())
        embeddings.write_atomic(str(output / "config.yaml"), yaml.safe_dump(config, sort_keys=False).encode())
        if args.export_index:
            report["export_index"] = export_index(source, target, settings.db_path, projection)
            embeddings.write_atomic(str(output / "report.json"), (json.dumps(report, indent=2) + "\n").encode())
        print(json.dumps({"event": "done", "output": str(output), "selected_epoch": report["selected_epoch"],
                          "baseline": report["baseline_dinov3"], "selected": report["selected_metrics"]}))
        return 0
    except (OSError, ValueError, KeyError, embeddings.ConfigError, embeddings.Busy) as exc:
        print(json.dumps({"event": "error", "message": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
