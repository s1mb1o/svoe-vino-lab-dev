"""Send every annotated photo to a match backend and record the result.

The photo set of this project is the ground truth. This tool measures a
recognizer against it and writes one directory per run under `runs_dir`, so two
runs can be compared.

Run:

    python3 scripts/match_run.py --backend official-api
    python3 scripts/match_run.py --backend organizers --limit 50
    python3 scripts/match_run.py --backend official-api --dry-run

`--dataset NAME` chooses one dataset of `config.yaml`. The default is the dataset
named `default`.

`--photos-dir DIR` replaces the photo set of the project with a plain directory
of photos. Such a directory holds no ground truth, so the run records the answer
of the backend and states no correctness:

    python3 scripts/match_run.py --backend svm-siglip2-448 --photos-dir ~/photos

The run directory holds:

    run.json          what ran: the backend, the options, the counts
    queries.tsv       the manifest in the form of the jury harness
    queries.jsonl     the same rows with the truth of each photo
    predictions.jsonl the answer in the format of the organizers
    results.jsonl     the full record of every photo, with every candidate
    metrics.json      the aggregate
    summary.md        the same numbers for a human

A photo of `--photos-dir` carries the label `unlabelled`. It holds no true slug,
so the run reports the candidates, the latency, and the errors, and it reports no
share and no recall.

A `positive` photo shows the wine of its slug. A `negative` photo shows a
different wine, so the backend is wrong when it answers with that slug at rank 1.
A `variant` photo shows the wine in another bottle and stays out of the set
unless `--variants` asks for it.

A photo of the directory `__null__` carries the label `no_match`. No card of the
catalogue shows that wine, so the photo is a rejection case: the correct answer
is no answer, and every answered slug is a false match. The review tool writes
these photos; see `docs/plans/03_null-image.md`.
"""
import argparse
import collections
import concurrent.futures
import hashlib
import json
import os
import statistics
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402
import match_backends  # noqa: E402
from match_backends import EMBED_REF_KEYS, embeddings_of  # noqa: E402
from match_scoring import (  # noqa: E402
    LABELS_IN_SET, NO_MATCH, NULL_SLUG, SLA_MS, TARGET_MATCH_SHARE, UNLABELLED, f1,
    judge, metrics_of, write_summary, write_summary_unlabelled)

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}


# ---------------------------------------------------------------- the query set


def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError) as exc:
        print("warning: cannot read %s: %s" % (path, exc), file=sys.stderr)
        return default


def load_excluded():
    return (load_json(common.EXCLUDED_SLUGS_FILE, {}) or {}).get("excluded") or {}


def load_groups():
    """Return slug -> the set of the slugs of its variant group."""
    blob = load_json(common.VARIANT_GROUPS_FILE, {}) or {}
    out = {}
    for group in (blob.get("groups") or []):
        slugs = [s for s in (group.get("slugs") or []) if isinstance(s, str)]
        for slug in slugs:
            out[slug] = set(slugs)
    return out


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_queries(variants="off", only="all"):
    """Return the query rows, in a stable order.

    A photo enters the set when it holds a label of `LABELS_IN_SET` and its file
    is present. A photo stays out when its slug is excluded, when the label is
    `unusable`, when the entry is an agent proposal with no label, or when the
    entry is marked for deletion.

    A photo of `__null__` enters the set with the label `no_match` and no truth.
    It needs no label of its own: the directory is the statement. `build_null_rows`
    reads it.
    """
    labels = (load_json(common.LABEL_FILE, {}) or {}).get("labels") or {}
    excluded = load_excluded()
    groups = load_groups() if variants == "group" else {}
    rows = []
    skipped = collections.Counter()

    for slug in sorted(labels):
        if slug in excluded:
            skipped["excluded slug"] += len(labels[slug])
            continue
        # The NULL wine is read from its directory, not from the labels, because
        # a photo there needs no label. `build_null_rows` does it below.
        if slug == NULL_SLUG:
            continue
        for fname in sorted(labels[slug]):
            entry = labels[slug][fname] or {}
            label = entry.get("label")
            if label not in LABELS_IN_SET:
                skipped["no label" if not label else label] += 1
                continue
            if entry.get("delete"):
                skipped["marked for deletion"] += 1
                continue
            if label == "variant" and variants == "off":
                skipped["variant"] += 1
                continue
            if only != "all" and label != only:
                skipped["other label"] += 1
                continue
            path = os.path.join(common.PHOTO_DIR, slug, fname)
            if not os.path.isfile(path):
                skipped["file not found"] += 1
                continue
            truth = [slug]
            if label == "variant" and variants == "group":
                truth = sorted(groups.get(slug) or {slug})
            rows.append({
                "image_path": "%s/%s" % (slug, fname),
                "abs_path": path,
                "slug": slug,
                "label": label,
                "truth": truth if label in ("positive", "variant") else [],
            })

    # The photos of the NULL wine. `--only positive` and `--only negative` ask for
    # one label of the wine photos, so they take these rows away as well.
    if only in ("all", NO_MATCH):
        rows += build_null_rows(labels, excluded, skipped)

    rows.sort(key=lambda r: r["image_path"])
    for i, row in enumerate(rows, 1):
        row["query_id"] = "q-%06d" % i
    return rows, skipped


def build_null_rows(labels, excluded, skipped):
    """Return the query rows of the virtual NULL wine.

    `<photo_dir>/__null__/` holds the photos that match no card of the catalogue.
    The directory is the statement, so a photo there needs no label. A photo stays
    out when the label is `unusable`, when the entry is marked for deletion, or
    when `__null__` stands in `excluded-slugs.json`.

    Every row carries the label `no_match`, the slug `__null__`, and an empty
    truth. `judge` scores it as a rejection case.
    """
    root = os.path.join(common.PHOTO_DIR, NULL_SLUG)
    if not os.path.isdir(root):
        return []
    names = [fn for fn in sorted(os.listdir(root))
             if not fn.startswith(".")
             and os.path.splitext(fn)[1].lower() in IMAGE_EXT]
    if NULL_SLUG in excluded:
        skipped["excluded slug"] += len(names)
        return []
    rows = []
    for fname in names:
        entry = (labels.get(NULL_SLUG) or {}).get(fname) or {}
        if entry.get("label") == "unusable":
            skipped["unusable"] += 1
            continue
        if entry.get("delete"):
            skipped["marked for deletion"] += 1
            continue
        rows.append({
            "image_path": "%s/%s" % (NULL_SLUG, fname),
            "abs_path": os.path.join(root, fname),
            "slug": NULL_SLUG,
            "label": NO_MATCH,
            "truth": [],
        })
    return rows


def build_dir_queries(photos_dir):
    """Return the query rows of a plain directory of photos.

    The directory holds no ground truth. Every row carries the label
    `unlabelled`, an empty truth, and an empty slug. The walk is recursive, and
    `image_path` is the path of the file against the directory.
    """
    root = os.path.abspath(os.path.expanduser(photos_dir))
    if not os.path.isdir(root):
        sys.exit("error: --photos-dir is not a directory: %s" % root)
    rows = []
    skipped = collections.Counter()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        for fname in sorted(filenames):
            if fname.startswith("."):
                skipped["hidden file"] += 1
                continue
            if os.path.splitext(fname)[1].lower() not in IMAGE_EXT:
                skipped["not an image"] += 1
                continue
            path = os.path.join(dirpath, fname)
            rows.append({
                "image_path": os.path.relpath(path, root),
                "abs_path": path,
                "slug": "",
                "label": UNLABELLED,
                "truth": [],
            })
    rows.sort(key=lambda r: r["image_path"])
    for i, row in enumerate(rows, 1):
        row["query_id"] = "q-%06d" % i
    return rows, skipped


# --------------------------------------------------------------- the repeat of a run


def load_previous(path):
    """Return `image_path` -> the row of `results.jsonl` of an earlier run.

    The key is the path of the photo, not `query_id`. A `query_id` states the place
    in one query set, and the set changes when a label changes. The path of the
    photo names the same photo in every run.
    """
    if os.path.isdir(path):
        path = os.path.join(path, "results.jsonl")
    if not os.path.exists(path):
        raise SystemExit("error: no results.jsonl in the earlier run: %s" % path)
    out = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if rec.get("image_path"):
                out[rec["image_path"]] = rec
    if not out:
        raise SystemExit("error: the earlier run holds no row: %s" % path)
    return out


def failed_before(rec, depth):
    """Answer whether this photo counts as a failure at the depth `depth`.

    `depth` is the number of candidates that count as an answer. With `depth` 1 a
    positive photo MUST stand at rank 1. With `depth` 10 the true slug MUST stand
    inside the first 10 candidates, which is the reading of "not in R@10".

    A positive or a variant photo fails when its true slug is absent or deeper
    than `depth`. A negative photo fails when its own slug DID come back inside
    `depth`, because that slug is the wrong answer. A request that failed counts
    as a failure, whatever the depth.
    """
    if rec.get("error"):
        return True
    rank = rec.get("rank_of_truth")
    if rec.get("label") == "negative":
        return rank is not None and rank <= depth
    return rank is None or rank > depth


def select_failures(rows, previous, depth):
    """Keep the rows that failed in the earlier run. Return the rows and a report."""
    kept, report = [], collections.Counter()
    for row in rows:
        rec = previous.get(row["image_path"])
        if rec is None:
            report["not in the earlier run"] += 1
            continue
        if failed_before(rec, depth):
            row["previous"] = {
                "query_id": rec.get("query_id"),
                "rank_of_truth": rec.get("rank_of_truth"),
                "outcome": rec.get("outcome"),
                "predicted_slug": rec.get("predicted_slug"),
                "error": rec.get("error"),
            }
            kept.append(row)
        else:
            report["passed at depth %d" % depth] += 1
    now = {r["image_path"] for r in rows}
    gone = sum(1 for image_path in previous if image_path not in now)
    if gone:
        report["in the earlier run, not in the set now"] = gone
    return kept, report


# ------------------------------------------------------------------- the scoring


def subset_block(results, parent, depth, photos_in_earlier_run):
    """Return the record of a repeat run: what it covers and what it changed.

    Every photo of a repeat run failed in the earlier run, so the shares of this
    run describe the failures only. They are NOT the shares of the whole set. The
    useful number is how many photos the repeat put right.
    """
    recovered_at_1 = recovered_at_depth = still = 0
    for r in results:
        if r["label"] == "negative":
            ok = r["rank_of_truth"] is None or r["rank_of_truth"] > depth
        else:
            ok = r["rank_of_truth"] is not None and r["rank_of_truth"] <= depth
        if r["error"]:
            ok = False
        if ok:
            recovered_at_depth += 1
        else:
            still += 1
        if r["label"] != "negative" and r["rank_of_truth"] == 1:
            recovered_at_1 += 1
    return {
        "based_on": parent,
        "rerun_depth": depth,
        "photos_in_earlier_run": photos_in_earlier_run,
        "n": len(results),
        "recovered_at_1": recovered_at_1,
        "recovered_at_depth": recovered_at_depth,
        "still_failing": still,
        "note": ("Every photo of this run failed in the earlier run. The shares of "
                 "this run describe those photos only. They are NOT the shares of "
                 "the whole set."),
    }


# -------------------------------------------------------------------- the output


def git_commit():
    try:
        out = subprocess.run(["git", "-C", common.ROOT, "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or None
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------- the run


def main():
    ap = argparse.ArgumentParser(
        description="Match every annotated photo against one backend")
    ap.add_argument("--backend", help="the id of a backend of backends.yaml")
    ap.add_argument("--list-backends", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="stop after N photos")
    ap.add_argument("--photos-dir", default="", metavar="DIR",
                    help="match the photos of this directory instead of the photo "
                         "set of the project. The directory holds no ground truth, "
                         "so the run records the candidates and states no "
                         "correctness. The walk is recursive")
    ap.add_argument("--only", choices=("all", "positive", "negative", "no_match"),
                    default="all",
                    help="run one label alone. `no_match` runs the photos of the "
                         "NULL wine, which match no card of the catalogue")
    ap.add_argument("--variants", choices=("off", "strict", "group"), default="off",
                    help="take the variant photos into the set (default: off)")
    ap.add_argument("--negative-strict", action="store_true",
                    help="count the slug anywhere in the top-k as a false match")
    ap.add_argument("--workers", type=int, default=None,
                    help="how many requests to send at the same time. The default "
                         "is the key `workers` of the backend, or 1. A value of 1 "
                         "keeps the latency comparable to the jury harness")
    ap.add_argument("--from-run", default="", metavar="RUN",
                    help="repeat only the photos that failed in this earlier run "
                         "(the directory, or its results.jsonl)")
    ap.add_argument("--rerun-depth", type=int, default=1, metavar="K",
                    help="with --from-run: how many candidates count as an answer. "
                         "1 repeats every photo that was not correct at rank 1. "
                         "10 repeats every photo that was not in the first 10. "
                         "The default is 1.")
    ap.add_argument("--dataset", default="", metavar="NAME",
                    help="the dataset of `config.yaml` to match against. The "
                         "default is the dataset named `default`")
    ap.add_argument("--label", default="", help="a word for the run directory name")
    ap.add_argument("--dry-run", action="store_true",
                    help="build the query set and the manifests, call nothing")
    args = ap.parse_args()

    # The dataset MUST be chosen before any path of `common` is read.
    try:
        common.select_dataset(args.dataset or None)
    except common.ConfigError as exc:
        sys.exit("error: %s" % exc)

    if args.list_backends:
        specs = match_backends.load_backends(common.BACKENDS_FILE)
        for bid, spec in sorted(specs.items()):
            print("%-16s %s" % (bid, spec.get("label") or ""))
            print("%-16s %s" % ("", spec.get("url")))
        return

    common.print_config()

    if args.photos_dir:
        for name, value, default in (("--from-run", args.from_run, ""),
                                     ("--only", args.only, "all"),
                                     ("--variants", args.variants, "off")):
            if value != default:
                sys.exit("error: %s needs the photo set of the project. It cannot "
                         "be used with --photos-dir." % name)
        rows, skipped = build_dir_queries(args.photos_dir)
        photos_dir = os.path.abspath(os.path.expanduser(args.photos_dir))
    else:
        photos_dir = ""
        rows, skipped = build_queries(variants=args.variants, only=args.only)

    parent = None
    if args.from_run:
        if args.rerun_depth < 1:
            sys.exit("error: --rerun-depth MUST be 1 or more")
        previous = load_previous(args.from_run)
        parent = os.path.basename(os.path.normpath(
            args.from_run[:-len("/results.jsonl")]
            if args.from_run.endswith("results.jsonl") else args.from_run))
        before = len(rows)
        rows, report = select_failures(rows, previous, args.rerun_depth)
        print("repeat of %s: %d of the %d photos of the earlier run failed at "
              "depth %d" % (parent, len(rows), len(previous), args.rerun_depth))
        for key in sorted(report):
            print("  %s: %d" % (key, report[key]))
        if before != len(previous):
            print("  note: the set holds %d photos now and held %d in the earlier run"
                  % (before, len(previous)))

    if args.limit:
        rows = rows[:args.limit]
    if not rows:
        if parent:
            sys.exit("nothing to repeat: every photo of %s passed at depth %d"
                     % (parent, args.rerun_depth))
        sys.exit("error: the query set is empty")
    counts = collections.Counter(r["label"] for r in rows)
    if photos_dir:
        print("photos directory: %s" % photos_dir)
    print("query set: %d photos (%s)" % (
        len(rows), ", ".join("%s %d" % (k, counts[k]) for k in sorted(counts))))
    if skipped:
        print("left out: %s" % ", ".join(
            "%s %d" % (k, v) for k, v in sorted(skipped.items())))
    if photos_dir:
        print("no ground truth: the run records the candidates and states no "
              "correctness")

    # State the rule for the variant photos and the count of the excluded slugs.
    # Both change the query set, and neither is visible in the counts above.
    if photos_dir:
        pass                               # a plain directory knows no variant
    elif args.variants == "off":
        print("variant photos: %d left out (--variants off)" % skipped["variant"])
    elif args.variants == "strict":
        print("variant photos: %d in the set; only the slug of the photo counts as\n"
              "                a true match (--variants strict)" % counts["variant"])
    else:
        print("variant photos: %d in the set; every slug of the variant group counts\n"
              "                as a true match (--variants group)" % counts["variant"])
    if not photos_dir:
        excluded = load_excluded()
        print("excluded slugs: %d in %s; %d photos left out"
              % (len(excluded), os.path.basename(common.EXCLUDED_SLUGS_FILE),
                 skipped["excluded slug"]))

    backend = None
    if not args.dry_run:
        if not args.backend:
            sys.exit("error: --backend is required. Use --list-backends.")
        backend = match_backends.build_backend(common.BACKENDS_FILE, args.backend)
        print("backend: %s (%s), top_k %d, timeout %.0fs"
              % (backend.id, backend.url, backend.top_k, backend.timeout))

    # How many requests go at the same time. `--workers` on the command line wins
    # over the key `workers` of the backend. The backend knows the rate that its
    # server takes; the command line knows the purpose of this one run.
    spec_workers, source = 1, "the default"
    if args.backend:
        try:
            spec = match_backends.load_backends(common.BACKENDS_FILE).get(args.backend)
            spec_workers = max(1, int((spec or {}).get("workers") or 1))
        except match_backends.BackendError:
            spec_workers = 1
    if args.workers is not None:
        workers, source = max(1, args.workers), "--workers"
    else:
        workers = spec_workers
        if spec_workers > 1:
            source = "the key `workers` of the backend %s" % args.backend
    print("requests at the same time: %d (%s)%s"
          % (workers, source, "" if workers == 1 else
             "; the latency is then NOT comparable to the jury harness"))

    stamp = time.strftime("%Y-%m-%dT%H%M%SZ", time.gmtime())
    repeat = ("repeat-d%d" % args.rerun_depth) if parent else ""
    # `dir` marks a run with no ground truth in the name of the directory, so the
    # table of the runs at `/runs` states the kind of the run at first sight.
    kind = "dir" if photos_dir else ""
    name = "-".join(x for x in (stamp, args.backend or "dry-run", kind, repeat,
                                args.label) if x)
    run_dir = os.path.join(common.RUNS_DIR, name)
    os.makedirs(run_dir, exist_ok=True)
    print("run directory: %s" % run_dir)

    print("sha256 of %d photos..." % len(rows))
    for row in rows:
        row["image_sha256"] = sha256_of(row["abs_path"])

    with open(os.path.join(run_dir, "queries.tsv"), "w", encoding="utf-8") as fh:
        fh.write("query_id\timage_path\n")
        for row in rows:
            fh.write("%s\t%s\n" % (row["query_id"], row["image_path"]))
    with open(os.path.join(run_dir, "queries.jsonl"), "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps({k: row[k] for k in (
                "query_id", "image_path", "image_sha256", "slug", "label", "truth")},
                ensure_ascii=False) + "\n")

    meta = {
        "run_id": name,
        "tool": "scripts/match_run.py",
        "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "git_commit": git_commit(),
        "options": {
            "dataset": common.DATASET,
            "backend": args.backend, "limit": args.limit, "only": args.only,
            "variants": args.variants, "negative_strict": args.negative_strict,
            "workers": workers, "dry_run": args.dry_run,
            # The page `/runs` reads this path to serve the photos of the run.
            "photos_dir": photos_dir,
        },
        "backend": match_backends.redact(backend.spec) if backend else None,
        # When the vectors this run was answered with were last built. Read
        # from the backend at creation, so the run keeps the age even after a
        # later rebuild moves the index.
        "embeddings": embeddings_of(backend),
        "config": {key: value for key, value in common.CONFIG_PATHS},
        "query_set": {"total": len(rows), **{k: counts[k] for k in sorted(counts)}},
        "left_out": dict(skipped),
        "based_on": None if not parent else {
            "run_id": parent,
            "rerun_depth": args.rerun_depth,
            "rule": ("a positive photo whose true slug was absent or deeper than "
                     "rank %d, a negative photo whose own slug came back inside "
                     "rank %d, or a request that failed"
                     % (args.rerun_depth, args.rerun_depth)),
            "photos_in_earlier_run": len(previous) if parent else None,
        },
    }
    if args.dry_run:
        meta["finished"] = meta["started"]
        with open(os.path.join(run_dir, "run.json"), "w", encoding="utf-8") as fh:
            json.dump(meta, fh, ensure_ascii=False, indent=2, sort_keys=True)
        print("dry run: the manifests are written, no request was sent")
        return

    t_start = time.time()
    results = []
    lock = threading.Lock()
    pred_fh = open(os.path.join(run_dir, "predictions.jsonl"), "w", encoding="utf-8")
    res_fh = open(os.path.join(run_dir, "results.jsonl"), "w", encoding="utf-8")

    def one(row):
        cands, ms, status, error = backend.ask(row["abs_path"])
        verdict = judge(row, cands, args.negative_strict)
        rec = {
            "query_id": row["query_id"], "image_path": row["image_path"],
            "image_sha256": row["image_sha256"], "slug": row["slug"],
            "label": row["label"], "truth": row["truth"],
            "candidates": cands, "predicted_slug": verdict["predicted_slug"],
            "rank_of_truth": verdict["rank_of_truth"], "outcome": verdict["outcome"],
            "latency_ms": ms, "http_status": status, "error": error,
        }
        if row.get("previous"):
            rec["previous"] = row["previous"]     # what the earlier run answered
        return rec

    def write(rec):
        pred_fh.write(json.dumps({
            "query_id": rec["query_id"], "image_path": rec["image_path"],
            "image_sha256": rec["image_sha256"],
            "predicted_slug": rec["predicted_slug"], "latency_ms": rec["latency_ms"],
        }, ensure_ascii=False) + "\n")
        res_fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        pred_fh.flush()
        res_fh.flush()

    def hms(seconds):
        seconds = int(round(seconds))
        return "%d:%02d:%02d" % (seconds // 3600, seconds % 3600 // 60, seconds % 60)

    done = 0
    t_chunk = t_start

    def progress():
        # One line per chunk of 25 photos, and one line at the end. `chunk` is
        # the time of the last chunk. `ETA` uses the rate of the whole run.
        nonlocal t_chunk
        now = time.time()
        elapsed, left = now - t_start, len(rows) - done
        print("  %d/%d  chunk %.1fs  elapsed %s  ETA %s"
              % (done, len(rows), now - t_chunk, hms(elapsed),
                 hms(elapsed / done * left) if done else "?"), flush=True)
        t_chunk = now

    try:
        if workers > 1:
            with concurrent.futures.ThreadPoolExecutor(workers) as pool:
                for rec in pool.map(one, rows):
                    with lock:
                        results.append(rec)
                        write(rec)
                        done += 1
                        if done % 25 == 0 or done == len(rows):
                            progress()
        else:
            for row in rows:
                rec = one(row)
                results.append(rec)
                write(rec)
                done += 1
                if done % 25 == 0 or done == len(rows):
                    progress()
    except KeyboardInterrupt:
        print("\nstopped by the user after %d photos" % done)
    finally:
        pred_fh.close()
        res_fh.close()

    wall = time.time() - t_start
    met = metrics_of(results, backend, backend.top_k, args.negative_strict,
                     wall, workers, groups=load_groups())
    met["run_id"] = name
    if parent:
        met["subset"] = subset_block(results, parent, args.rerun_depth, len(previous))
    meta["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    meta["wall_s"] = round(wall, 1)
    meta["answered"] = len(results)
    with open(os.path.join(run_dir, "run.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2, sort_keys=True)
    with open(os.path.join(run_dir, "metrics.json"), "w", encoding="utf-8") as fh:
        json.dump(met, fh, ensure_ascii=False, indent=2, sort_keys=True)
    write_summary(os.path.join(run_dir, "summary.md"), meta, met)

    if met.get("unlabelled"):
        unl = met["unlabelled"]
        print("")
        print("no ground truth: %d photo(s), %d with a candidate, %d with none, "
              "%d error(s)" % (unl["n"], unl["answered"], unl["no_answer"],
                               unl["errors"]))
        print("median top score %s, median gap to the second candidate %s" % (
            unl["top_score_median"], unl["score_margin_median"]))
        print("latency: median %s ms, p95 %s ms" % (
            met["latency_ms"]["median"], met["latency_ms"]["p95"]))
        print("written: %s" % run_dir)
        print("read the answers at http://127.0.0.1:8154/runs")
        return

    pos, neg = met["positive"], met["negative"]
    print("")
    if met.get("subset"):
        sub = met["subset"]
        print("repeat of %s at depth %d: %d photo(s) repeated, %d correct at rank 1 "
              "now, %d inside the depth, %d still failing" % (
                  sub["based_on"], sub["rerun_depth"], sub["n"],
                  sub["recovered_at_1"], sub["recovered_at_depth"],
                  sub["still_failing"]))
        print("the shares below cover the repeated photos only")
    print("match share %s (target 90-100%%), F1@1 %s, F1@5 %s, near-duplicate "
          "confusion %d" % (
              pos["match_share"],
              (pos.get("f1_at_1") or {}).get("f1"),
              (pos.get("f1_at_5") or {}).get("f1") if pos.get("f1_at_5") else None,
              pos.get("near_duplicate_confusion", 0)))
    print("within the %d ms SLA: %s of the photos" % (
        met["latency_ms"]["sla_ms"], met["latency_ms"]["within_sla_share"]))
    print("positive %d: R@1 %s  R@5 %s  R@10 %s  errors %d" % (
        pos["n"], pos["recall_at_1"], pos["recall_at_5"], pos["recall_at_10"],
        pos["errors"]))
    print("negative %d: false match at 1 %d, another slug at 1 %d, no answer %d" % (
        neg["n"], neg["false_match_at_1"], neg["other_slug_at_1"], neg["no_answer"]))
    print("latency: median %s ms, p95 %s ms" % (
        met["latency_ms"]["median"], met["latency_ms"]["p95"]))
    print("written: %s" % run_dir)


if __name__ == "__main__":
    main()
