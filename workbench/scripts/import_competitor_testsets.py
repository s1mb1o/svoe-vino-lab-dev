#!/usr/bin/env python3
"""Prepare and import public competitor test sets with explicit evidence tiers.

The adapters in this file intentionally name every accepted source format. The script
does not infer a target from arbitrary directory or file names.
"""

import argparse
import csv
import dataclasses
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
WORKBENCH = HERE.parent
sys.path.insert(0, str(WORKBENCH / "pipeline"))
import import_testset  # noqa: E402

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
DRAWER = "__drawer__"
NULL = "__null__"


@dataclasses.dataclass
class Record:
    competitor: str
    image: Path
    repo: Path
    source_path: str
    original_label: object
    slug: str | None
    tier: str
    reason: str
    label: str = "positive"
    source_note: str | None = None
    set_name: str | None = None


def read_tsv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def revision(repo):
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def image_info(path):
    with Image.open(path) as image:
        image.verify()
    with Image.open(path) as image:
        return image.width, image.height, image.format


def exact_image_index(repos_root):
    """Return original real-photo basename -> local image.

    kairov keeps the original file names. Kofeinix keeps full-resolution copies under
    query ids and records the original names in ground_truth.tsv. The explicit order
    avoids selecting Mishanya's thumbnails when a full source is present.
    """
    out = {}
    kairov = repos_root / "github__kairov-eng__vino"
    for folder in (kairov / "eval/queries", kairov / "eval/queries2"):
        if folder.is_dir():
            for path in sorted(folder.iterdir()):
                if path.is_file() and path.suffix.lower() in IMAGE_EXT:
                    out.setdefault(path.name, path)
                    out.setdefault(path.stem, path)
    kof = repos_root / "github__kofeinix__wine_hakaton"
    gt = kof / "eval/real/ground_truth.tsv"
    if gt.is_file():
        for row in read_tsv(gt):
            original = Path(row.get("source") or "").name
            candidate = kof / "eval/real/queries" / (row.get("image_path") or "")
            if original and candidate.is_file():
                out.setdefault(original, candidate)
                out.setdefault(Path(original).stem, candidate)
    return out


def danya_records(repos_root):
    repo = repos_root / "github__Danya213411__vino-recognition"
    root = repo / "data/test/curated_67"
    records = []
    for row in read_csv(root / "annotations.csv"):
        image = root / row["relative_path"]
        exact = row.get("label_status") == "exact" and bool(row.get("expected_slug"))
        records.append(Record(
            "danya213411", image, repo, str(image.relative_to(repo)), row,
            row.get("expected_slug") or None, "scored" if exact else "provisional",
            "human exact label on a fixed held-out set" if exact
            else "human review did not identify an exact wine_slug",
            "positive" if exact else "unusable",
        ))
    return records


def qacen_records(repos_root, images):
    repo = repos_root / "github__Qacen__skip_skpi"
    records = []
    for row in read_csv(repo / "ml/eval/rp_eval.csv"):
        image = images.get(row["file"])
        if image is None:
            continue
        slugs = [row.get("target_slug") or ""]
        slugs += [value for value in (row.get("alt_slugs") or "").split("|") if value]
        slug = next((value for value in slugs if value), None)
        exact = row.get("subset") == "exact"
        records.append(Record(
            "qacen", image, repo, str((repo / "ml/eval/rp_eval.csv").relative_to(repo)),
            row, slug, "scored" if exact else "provisional",
            "manual exact annotation of the external real-photo set" if exact
            else "annotation is probable or identifies only the same product line",
            "positive" if slug else "unusable",
            "image bytes resolved by the original file name from a public clone",
        ))
    return records


def mishanya_records(repos_root):
    repo = repos_root / "github__mishanyacorleone__wines"
    labels_path = repo / "data/labels/real-photos.json"
    labels = json.loads(labels_path.read_text(encoding="utf-8"))
    images = repo / "data/reports/thumbs/queries"
    by_stem = {path.stem: path for path in images.iterdir() if path.is_file()}
    records = []
    for name, value in sorted(labels.items()):
        status = value.get("status")
        slugs = value.get("slugs") or []
        if status == "sure" and len(slugs) == 1:
            tier, slug, label = "scored", slugs[0], "positive"
            reason = "manual sure label with one exact wine_slug"
        elif status == "absent":
            tier, slug, label = "scored", None, "negative"
            reason = "manual absent-from-catalog label"
        else:
            tier = "provisional"
            slug = slugs[0] if slugs else None
            label = "positive" if slug else "unusable"
            reason = "manual label is unsure, skipped, or has multiple candidates"
        records.append(Record(
            "mishanya", by_stem.get(Path(name).stem, images / name), repo,
            str(labels_path.relative_to(repo)),
            value, slug, tier, reason, label,
        ))
    return records


def anna_records(repos_root):
    repo = repos_root / "github__annamistery__lct2026prod"
    records = []
    for pack in ("1", "2"):
        root = repo / "tmp" / pack
        document = json.loads((root / "mapping.json").read_text(encoding="utf-8"))
        for row in document.get("cases") or []:
            image = root / "queries" / row["image_path"]
            records.append(Record(
                "annamistery", image, repo, str((root / "mapping.json").relative_to(repo)),
                row, row.get("expected_slug"), "provisional",
                "owner evaluation pack was used for threshold or fusion selection",
                "positive" if row.get("expected_slug") else "unusable",
                f"source pack {pack}",
            ))
    return records


def kofeinix_records(repos_root):
    repo = repos_root / "github__kofeinix__wine_hakaton"
    gt = repo / "eval/real/ground_truth.tsv"
    records = []
    for row in read_tsv(gt):
        slug = row.get("expected_slug") or None
        image = repo / "eval/real/queries" / row["image_path"]
        records.append(Record(
            "kofeinix", image, repo, str(gt.relative_to(repo)), row, slug, "provisional",
            "development real-photo set was used to tune the submitted system",
            "positive" if slug else "negative",
        ))
    return records


def stan_records(repos_root, images):
    repo = repos_root / "github__Stanislavecddpb__svoe-vino-scanner"
    labels = repo / "eval/real/labels.tsv"
    records = []
    for row in read_tsv(labels):
        raw = row.get("slug") or ""
        slug = raw if raw not in {"-", "?"} else None
        if raw == "-":
            label = "negative"
        elif raw == "?":
            label = "unusable"
        else:
            label = "positive"
        image = images.get(row["image_path"])
        if image is None:
            continue
        records.append(Record(
            "stan", image, repo, str(labels.relative_to(repo)), row, slug, "provisional",
            "machine-assisted labels and decision rules were checked on the same corpus",
            label, "image bytes resolved by original file name from a public clone",
        ))
    return records


def enoscan_records(repos_root, images):
    repo = repos_root / "github__andrejsu__enoscan"
    labels = repo / "configs/labeled-photos.tsv"
    records = []
    for row in read_tsv(labels):
        image = (labels.parent / row["image_path"]).resolve()
        if not image.is_file():
            source_name = Path(row["image_path"])
            image = images.get(source_name.name, images.get(source_name.stem, image))
        if not image.is_file():
            continue
        slug = row.get("expected_slug") or None
        records.append(Record(
            "enoscan", image, repo, str(labels.relative_to(repo)), row, slug, "provisional",
            "development fixture used by competitor retrieval tests",
            "positive" if slug else "negative",
        ))
    return records


def unknown_image_records(competitor, repo, paths, reason):
    records = []
    for path in sorted(paths):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXT:
            continue
        source_path = str(path.relative_to(repo)) if path.is_relative_to(repo) else str(path)
        records.append(Record(
            competitor, path, repo, source_path, None, None, "provisional",
            reason, "unusable",
        ))
    return records


def extra_unscored_records(repos_root, research_root):
    records = []
    kairov = repos_root / "github__kairov-eng__vino"
    records += unknown_image_records(
        "kairov", kairov, (kairov / "eval/queries2").glob("*"),
        "no public wine_slug ground truth for the extra field-photo pack",
    )
    will = repos_root / "github__willmorton200-ui__VINA"
    will_images = list((will / "eval/queries").glob("*"))
    if not will_images:
        will_images = list((
            research_root / "output/competitor-refresh-2026-09-30/sources/"
            "willmorton-vina/TZ/Датасет/Датасет/eval/queries"
        ).glob("*"))
    records += unknown_image_records(
        "willmorton", will, will_images,
        "public evaluation images have no public wine_slug ground truth",
    )
    aboba = research_root / "output/competitor-archive-2026-09-28/sources/04-abobamakers"
    records += unknown_image_records(
        "abobamakers", aboba, (aboba / "test_photo").glob("*"),
        "field-photo pack has no machine-readable ground truth in the public repository",
    )
    return records


def collect_records(repos_root, research_root):
    images = exact_image_index(repos_root)
    adapters = [
        lambda: danya_records(repos_root),
        lambda: qacen_records(repos_root, images),
        lambda: mishanya_records(repos_root),
        lambda: anna_records(repos_root),
        lambda: kofeinix_records(repos_root),
        lambda: stan_records(repos_root, images),
        lambda: enoscan_records(repos_root, images),
        lambda: extra_unscored_records(repos_root, research_root),
    ]
    records = []
    failures = []
    for adapter in adapters:
        try:
            records.extend(adapter())
        except (OSError, ValueError, KeyError, csv.Error) as exc:
            failures.append({"adapter": adapter.__code__.co_firstlineno, "error": str(exc)})
    return records, failures


def normalize_tiers(records, catalog):
    """Move unresolved positive targets out of scored and return new records."""
    out = []
    for record in records:
        record = dataclasses.replace(record)
        candidates = []
        if record.slug:
            candidates.extend(record.slug.split("|"))
        if isinstance(record.original_label, dict):
            candidates.extend(record.original_label.get("slugs") or [])
            candidates.extend((record.original_label.get("alt_slugs") or "").split("|"))
        replacement = next((slug for slug in candidates if slug in catalog), None)
        if replacement and replacement != record.slug:
            record.slug = replacement
            record.reason += "; normalized to a catalogue-resolved candidate"
        if record.tier == "scored" and record.slug and record.slug not in catalog:
            record.tier = "provisional"
            record.reason += "; target wine_slug is absent from the current catalogue"
        out.append(record)
    return out


def demote_scored_conflicts(records):
    """Demote every scored label for a source photo with conflicting public labels."""
    by_source = defaultdict(list)
    for index, record in enumerate(records):
        if record.tier == "scored":
            by_source[record.image.stem].append(index)
    conflicted = set()
    for indices in by_source.values():
        truths = {(records[index].label, records[index].slug) for index in indices}
        if len(truths) > 1:
            conflicted.update(indices)
    out = []
    for index, record in enumerate(records):
        record = dataclasses.replace(record)
        if index in conflicted:
            record.tier = "provisional"
            record.reason += "; public exact labels conflict for the same source photo"
        out.append(record)
    return out


def common_scored_records(records):
    """Return one audited row per original source-photo stem.

    Competitors publish the same organizer photo with different encodings and sizes.
    The source stem is the stable identity that their label files share. A label conflict
    is an importer error here. `demote_scored_conflicts` must remove it first.
    """
    groups = defaultdict(list)
    for record in records:
        if record.tier == "scored":
            groups[record.image.stem].append(record)
    common = []
    for stem, copies in sorted(groups.items()):
        truths = {(record.label, record.slug) for record in copies}
        if len(truths) != 1:
            raise ValueError(f"common scored source {stem!r} has conflicting labels")

        def quality(record):
            if not record.image.is_file():
                return (-1, record.competitor, str(record.image))
            width, height, _ = image_info(record.image)
            return (width * height, record.competitor, str(record.image))

        selected = max(copies, key=quality)
        sources = [{
            "competitor": record.competitor,
            "source_repo": str(record.repo),
            "source_path": record.source_path,
            "source_image_path": str(record.image),
            "original_label": record.original_label,
        } for record in copies]
        common.append(dataclasses.replace(
            selected,
            competitor="competitors",
            set_name="competitors-scored-common",
            reason=("deduplicated scored benchmark; selected the largest image from "
                    f"{len(copies)} public copies"),
            original_label={
                "source_stem": stem,
                "selected_original_label": selected.original_label,
                "sources": sources,
            },
            source_note=("common scored benchmark; source stem %s; %d public copies"
                         % (stem, len(copies))),
        ))
    return common


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def atomic_jsonl(path, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        for value in values:
            handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def link_or_copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if sha256(target) != sha256(source):
            raise ValueError(f"target exists with different bytes: {target}")
        return "present"
    try:
        os.link(source, target)
        return "hardlink"
    except OSError:
        shutil.copy2(source, target)
        return "copy"


def snapshot_record(record, out_root, commits):
    if not record.image.is_file():
        return None, "missing"
    width, height, image_format = image_info(record.image)
    digest = sha256(record.image)
    place = NULL if record.label == "negative" else (record.slug or DRAWER)
    suffix = record.image.suffix.lower() or ".jpg"
    file_name = f"{digest[:12]}-{record.image.stem[:80]}{suffix}"
    set_name = record.set_name or f"{record.competitor}-{record.tier}"
    target = out_root / set_name / "photo" / place / file_name
    storage = link_or_copy(record.image, target)
    source_repo = str(record.repo)
    manifest = {
        "competitor": record.competitor,
        "set_name": set_name,
        "tier": record.tier,
        "tier_reason": record.reason,
        "label": record.label,
        "normalized_slug": record.slug,
        "place": place,
        "file_name": file_name,
        "source_repo": source_repo,
        "source_commit": commits.setdefault(source_repo, revision(record.repo)),
        "source_path": record.source_path,
        "source_image_path": str(record.image),
        "source_note": record.source_note,
        "original_label": record.original_label,
        "image_sha256": digest,
        "width": width,
        "height": height,
        "image_format": image_format,
        "storage": storage,
        "file_status": "ok",
    }
    label_entry = {
        "label": record.label,
        "tier": record.tier,
        "tier_reason": record.reason,
        "source_repo": source_repo,
        "source_commit": manifest["source_commit"],
        "source_path": record.source_path,
        "source_note": record.source_note,
        "original_label": record.original_label,
        "image_sha256": digest,
    }
    return (set_name, place, file_name, manifest, label_entry), None


def prepare(records, out_root):
    # This directory is generated exclusively by this importer. Remove only the photo
    # trees of sets that this invocation will rebuild, so a changed mapping cannot leave
    # stale photos that import_testset.py would otherwise scan.
    managed_sets = {record.set_name or f"{record.competitor}-{record.tier}"
                    for record in records}
    for set_name in managed_sets:
        photo_dir = out_root / set_name / "photo"
        if photo_dir.is_dir():
            shutil.rmtree(photo_dir)
    grouped = defaultdict(list)
    failures = []
    commits = {}
    for record in records:
        try:
            row, status = snapshot_record(record, out_root, commits)
        except (OSError, ValueError) as exc:
            row, status = None, str(exc)
        if row is None:
            failures.append({
                "competitor": record.competitor,
                "source_path": record.source_path,
                "status": status,
            })
        else:
            grouped[row[0]].append(row)

    all_manifest = []
    for set_name, rows in sorted(grouped.items()):
        labels = defaultdict(dict)
        manifests = []
        for _, place, name, manifest, entry in rows:
            labels[place][name] = entry
            manifests.append(manifest)
        set_root = out_root / set_name
        note = (
            f"Competitor import. Evidence tier: {set_name.rsplit('-', 1)[-1]}. "
            "Do not combine provisional metrics with scored metrics."
        )
        atomic_json(set_root / "review-labels.json", {
            "version": 2,
            "note": note,
            "labels": {place: dict(sorted(values.items()))
                       for place, values in sorted(labels.items())},
        })
        atomic_jsonl(set_root / "manifest.jsonl", sorted(
            manifests, key=lambda row: (row["place"], row["file_name"])
        ))
        counts = Counter(row["label"] for row in manifests)
        atomic_json(set_root / "summary.json", {
            "set_name": set_name,
            "tier": set_name.rsplit("-", 1)[-1],
            "photos": len(manifests),
            "labels": dict(sorted(counts.items())),
            "benchmarkable": sum(row["label"] != "unusable" for row in manifests),
        })
        all_manifest.extend(manifests)

    by_digest = defaultdict(list)
    for row in all_manifest:
        by_digest[row["image_sha256"]].append({
            "set_name": row["set_name"], "file_name": row["file_name"]
        })
    overlap = {digest: values for digest, values in by_digest.items()
               if len({value["set_name"] for value in values}) > 1}
    atomic_json(out_root / "overlap.json", overlap)
    atomic_json(out_root / "failures.json", failures)
    return grouped, failures, overlap


def source_inventory(repos_root, records, adapter_failures, out_root):
    imported = Counter(str(record.repo.resolve()) for record in records)
    decisions = []
    repositories = {repo.resolve() for repo in repos_root.glob("github__*")}
    repositories.update(record.repo.resolve() for record in records)
    for repo in sorted(repositories):
        count = imported[str(repo)]
        if count:
            decision = "imported"
            reason = "explicit adapter found query images and usable provenance"
        else:
            decision = "not_imported"
            reason = "no inspected machine-readable query-image ground truth adapter"
        decisions.append({
            "repository": str(repo),
            "commit": revision(repo),
            "decision": decision,
            "records": count,
            "reason": reason,
        })
    atomic_json(out_root / "source-inventory.json", {
        "repositories": decisions,
        "adapter_failures": adapter_failures,
    })


def import_sets(db, out_root, grouped, force=False):
    reports = {}
    for set_name in sorted(grouped):
        report = import_testset.import_testset(
            str(db), set_name, str(out_root / set_name), force=force
        )
        reports[set_name] = {
            "photos": report.photos,
            "labels": {str(key): value for key, value in report.labels.items()},
            "written": report.written,
            "present": report.present,
            "unknown_places": report.unknown_places,
        }
    atomic_json(out_root / "import-report.json", reports)
    return reports


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repos-root", type=Path, required=True)
    parser.add_argument("--research-root", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    with sqlite3.connect(args.db) as conn:
        catalog = {row[0] for row in conn.execute("SELECT wine_slug FROM wine_catalog")}
    records, adapter_failures = collect_records(args.repos_root, args.research_root)
    records = normalize_tiers(records, catalog)
    records = demote_scored_conflicts(records)
    common = common_scored_records(records)
    grouped, failures, overlap = prepare(records + common, args.out)
    source_inventory(args.repos_root, records, adapter_failures, args.out)
    reports = {} if args.prepare_only else import_sets(args.db, args.out, grouped, args.force)
    summary = {
        "source_records": len(records),
        "records": len(records) + len(common),
        "sets": {name: len(rows) for name, rows in sorted(grouped.items())},
        "failed_files": len(failures),
        "adapter_failures": adapter_failures,
        "overlap_digests": len(overlap),
        "imported": reports,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    if adapter_failures or failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
