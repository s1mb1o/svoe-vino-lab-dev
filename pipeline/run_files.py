"""Read the run files of `runs/` for the Runs page of the lab server.

A run is one directory `runs/<run id>/` of `scripts/match_run.py` or
`pipeline/benchmark.py`: `run.json`, `metrics.json`, `results.jsonl`, and more. The lab
database does not hold the runs. This module reads the files alone and writes nothing.

The functions are the run functions of `scripts/review_server.py`. Each one takes the
directory of the runs as an argument, not as a global. The old tool keeps its own copy.

The key `configuration` of `run.json` names the lab configuration of a run: one entry of
the key `embeddings` of `config.yaml`. A run with no such key has no configuration. Read
`docs/plans/23_runs-page.md`.
"""
import json
import os

# The orders that `/runs` offers for the photo rows. `manifest` is the order of
# `queries.tsv`, which is the order that the backend answered in.
ROW_SORTS = ("manifest", "worst", "rank", "latency_desc", "latency_asc",
             "score_desc", "score_asc", "path")


def read_json(path):
    """Return the JSON value of the file `path`, or None."""
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def run_dirs(runs_dir):
    """Return the id of every run directory, the newest first."""
    if not os.path.isdir(runs_dir):
        return []
    out = []
    for entry in os.scandir(runs_dir):
        if entry.name.startswith(".") or not entry.is_dir():
            continue
        out.append(entry.name)
    return sorted(out, reverse=True)


def run_path(runs_dir, run_id, name):
    """Return the path of one file of one run, or None.

    The function refuses a run id that holds a path separator or a parent reference,
    and a path that leaves `runs_dir`.
    """
    if not run_id or os.path.basename(run_id) != run_id or run_id in (".", ".."):
        return None
    base = os.path.realpath(runs_dir)
    path = os.path.realpath(os.path.join(base, run_id, name))
    if not path.startswith(base + os.sep):
        return None
    return path


def configuration_of(meta):
    """Return the lab configuration that `run.json` names, or None."""
    value = (meta or {}).get("configuration")
    return value if isinstance(value, str) and value else None


def test_set_of(meta):
    """Return the test set that `run.json` names in `options.set`, or None.

    `pipeline/benchmark.py` writes the key. A run of `scripts/match_run.py` has none.
    """
    value = ((meta or {}).get("options") or {}).get("set")
    return value if isinstance(value, str) and value else None


def run_head(runs_dir, run_id):
    """Return the short record of one run for the table of the runs."""
    meta = read_json(run_path(runs_dir, run_id, "run.json")) or {}
    met = read_json(run_path(runs_dir, run_id, "metrics.json")) or {}
    pos = met.get("positive") or {}
    neg = met.get("negative") or {}
    lat = met.get("latency_ms") or {}
    return {
        "id": run_id,
        "configuration": configuration_of(meta),
        "set": test_set_of(meta),
        "backend": (met.get("backend") or (meta.get("options") or {}).get("backend")
                    or "—"),
        "label": (meta.get("backend") or {}).get("label", ""),
        "started": meta.get("started") or "",
        "finished": meta.get("finished") or "",
        "dry_run": bool((meta.get("options") or {}).get("dry_run")),
        # False: the run read no record of `model_cache`, so its latency is real time (the
        # checkbox `Use caches` of the dialog `Run>`, plan 39). None: not recorded.
        "use_cache": (meta.get("use_cache") if isinstance(meta.get("use_cache"), bool)
                      else None),
        # False: the run skipped the barcode step of its pipeline (the checkbox `Disable
        # barcode fast path` of the dialog `Run>`, plan 53). True: the step ran. None: the
        # pipeline has no barcode step, or the run did not record it.
        "use_barcode": (meta.get("use_barcode") if isinstance(meta.get("use_barcode"), bool)
                        else None),
        "queries": (met.get("queries") or {}).get("total",
                                                  (meta.get("query_set") or {}).get("total")),
        "positive": pos.get("n"),
        "negative": neg.get("n"),
        "recall_at_1": pos.get("recall_at_1"),
        "match_share": pos.get("match_share", pos.get("recall_at_1")),
        "f1_at_1": (pos.get("f1_at_1") or {}).get("f1"),
        "f1_at_5": (pos.get("f1_at_5") or {}).get("f1"),
        "near_duplicate_confusion": pos.get("near_duplicate_confusion"),
        "within_sla_share": lat.get("within_sla_share"),
        "sla_ms": lat.get("sla_ms"),
        "recall_at_5": pos.get("recall_at_5"),
        "recall_at_10": pos.get("recall_at_10"),
        "false_match_at_1": neg.get("false_match_at_1"),
        "latency_median": lat.get("median"),
        "has_metrics": bool(met),
        "subset": met.get("subset") or None,
        # When the vectors that answered this run were last built. A run made before
        # that key existed has None, which the page prints as "not recorded".
        "embeddings": meta.get("embeddings"),
    }


def _row_sort_key(rec, mode):
    """Return the sort key of one row for the order `mode`."""
    rank = rec.get("rank_of_truth")
    top = (rec.get("candidates") or [None])[0]
    score = (top or {}).get("score")
    lat = rec.get("latency_ms")
    path = rec.get("image_path") or ""
    if mode == "path":
        return (path,)
    if mode == "rank":
        # rank 1 first, then deeper, then the rows whose true slug never came back
        return (0, rank) if rank else (1, 0)
    if mode == "worst":
        # the most wrong first: a false match, then an absent truth, then a deep rank
        if rec.get("outcome") == "false_match_at_1":
            return (0, 0, path)
        if rec.get("label") in ("positive", "variant"):
            if rank is None:
                return (1, 0, path)
            if rank > 1:
                return (2, -rank, path)
            return (4, 0, path)
        return (3, 0, path)
    if mode in ("latency_desc", "latency_asc"):
        value = -1 if lat is None else lat
        return (-value,) if mode == "latency_desc" else (value,)
    if mode in ("score_desc", "score_asc"):
        # a row with no score stands last in both orders
        if score is None:
            return (1, 0.0)
        return (0, -score) if mode == "score_desc" else (0, score)
    return (rec.get("query_id") or "",)


# ------------------------------------------------------- the twin of a photo
#
# One photo file can stand in the set two times: `positive` for the wine that it
# shows, and `negative` for a wine that it does not show. The two rows hold the
# same `image_sha256`, because the bytes are equal. So a negative row can borrow
# the true slug of the photo from its positive twin: the true wine SHOULD stand
# above the wine that the negative label forbids.
#
# The index reads one run only. A photo whose twin was not in the run has no twin
# here. This keeps the report a report of that run and of nothing else.

_TWIN_CACHE = {}


def twin_index(runs_dir, run_id):
    """Return `image_sha256` -> {"positive": [slug...], "negative": [slug...]}.

    The lists hold the distinct slugs of the rows of this run whose photo holds these
    exact bytes. The label `variant` is left out: it states no truth about the photo.
    The result is cached by the size and the time of `results.jsonl`.
    """
    path = run_path(runs_dir, run_id, "results.jsonl")
    if not path or not os.path.exists(path):
        return {}
    try:
        st = os.stat(path)
    except OSError:
        return {}
    key = (path, st.st_mtime_ns, st.st_size)
    hit = _TWIN_CACHE.get(path)
    if hit and hit[0] == key:
        return hit[1]
    index = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            sha, slug, label = rec.get("image_sha256"), rec.get("slug"), rec.get("label")
            if not sha or not slug or label not in ("positive", "negative"):
                continue
            slot = index.setdefault(sha, {"positive": set(), "negative": set()})
            slot[label].add(slug)
    for slot in index.values():
        slot["positive"] = sorted(slot["positive"])
        slot["negative"] = sorted(slot["negative"])
    _TWIN_CACHE.clear()
    _TWIN_CACHE[path] = (key, index)
    return index


def first_rank(candidates, slug):
    """Return the first rank of `slug` in `candidates`, or None. A backend MAY answer
    one slug two times; the first place counts, as in `judge()`."""
    best = None
    for cand in candidates or ():
        if cand.get("slug") != slug:
            continue
        rank = cand.get("rank")
        if rank is None:
            continue
        if best is None or rank < best:
            best = rank
    return best


def add_twin(rec, index):
    """Add the field `twin` to one row of a run. Return the row.

    `twin` holds `slugs` (the slugs that the positive twin names, without the slug of
    this row), `rank` (the first rank of the best of them), `forbidden_rank` (the first
    rank of the slug of this negative row), `verdict` (`above`, `below`,
    `no_forbidden`, `absent`, or null), `conflict`, and `conflict_slugs`. A photo that
    is positive for two wines, or positive and negative for one wine, is a defect of
    the set; `conflict` marks it.
    """
    rec["twin"] = None
    slot = index.get(rec.get("image_sha256") or "")
    if not slot:
        return rec
    positive, negative = slot["positive"], slot["negative"]
    both = sorted(set(positive) & set(negative))
    conflict = len(positive) > 1 or bool(both)
    slugs = [s for s in positive if s != rec.get("slug")]
    twin = {
        "slugs": slugs,
        "rank": None,
        "forbidden_rank": None,
        "verdict": None,
        "conflict": conflict,
        "conflict_slugs": {"positive": positive, "both": both} if conflict else None,
    }
    if rec.get("label") == "negative" and slugs:
        ranks = [r for r in (first_rank(rec.get("candidates"), s) for s in slugs)
                 if r is not None]
        twin["rank"] = min(ranks) if ranks else None
        twin["forbidden_rank"] = first_rank(rec.get("candidates"), rec.get("slug"))
        if twin["rank"] is None:
            twin["verdict"] = "absent"
        elif twin["forbidden_rank"] is None:
            twin["verdict"] = "no_forbidden"
        elif twin["rank"] < twin["forbidden_rank"]:
            twin["verdict"] = "above"
        else:
            twin["verdict"] = "below"
    rec["twin"] = twin
    return rec


def rule_step(rec):
    """The `explain` record of the cluster rule step of one row, or None."""
    for cand in rec.get("candidates") or ():
        step = cand.get("explain")
        if isinstance(step, dict) and step.get("kind") == "cluster_rules":
            return step
    return None


def row_matches(rec, mode):
    """Answer whether the row passes the filter `mode`. The modes
    `negative_above_positive` and `twin_conflict` read the field `twin` of `add_twin`."""
    label, rank = rec.get("label"), rec.get("rank_of_truth")
    outcome = rec.get("outcome")
    if mode in ("all", ""):
        return True
    if mode == "error":
        return bool(rec.get("error"))
    if mode == "hit":
        return label in ("positive", "variant") and rank == 1
    if mode == "miss":
        return label in ("positive", "variant") and rank != 1
    if mode == "near":          # the truth is in the list but not at rank 1
        return label in ("positive", "variant") and rank is not None and rank > 1
    if mode == "absent":        # the truth never appeared
        return label in ("positive", "variant") and rank is None
    if mode == "rank_2_5":
        return label in ("positive", "variant") and rank is not None and 2 <= rank <= 5
    # A truth that never came back counts as a failure at every depth, which is the
    # rule of `failed_before()` in `scripts/match_run.py`.
    if mode == "after_5":
        return label in ("positive", "variant") and (rank is None or rank > 5)
    if mode == "after_10":
        return label in ("positive", "variant") and (rank is None or rank > 10)
    # A `no_match` photo matches no card of the catalogue; every answer is a false match.
    if mode == "no_match":
        return label == "no_match"
    if mode == "no_match_answered":
        return label == "no_match" and outcome == "false_match_at_1"
    if mode == "false_match":
        return label == "negative" and outcome == "false_match_at_1"
    if mode == "negative_in_topk":
        return label == "negative" and rank is not None
    if mode == "negative":
        return label == "negative"
    twin = rec.get("twin") or {}
    if mode == "negative_above_positive":
        return label == "negative" and twin.get("verdict") == "below"
    if mode == "twin_conflict":
        return bool(twin.get("conflict"))
    if mode in ("rule_acted", "rule_changed"):
        step = rule_step(rec)
        return step is not None and (mode == "rule_acted" or bool(step.get("changed")))
    return True


def run_rows(runs_dir, run_id, mode="all", query="", limit=200, offset=0,
             sort="manifest"):
    """Return (the rows of `results.jsonl` that the filter keeps, in the asked order,
    the count of all kept rows)."""
    path = run_path(runs_dir, run_id, "results.jsonl")
    if not path or not os.path.exists(path):
        return [], 0
    query = (query or "").strip().lower()
    index = twin_index(runs_dir, run_id)
    kept = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            add_twin(rec, index)
            if not row_matches(rec, mode):
                continue
            if query and query not in ((rec.get("image_path") or "") + " " +
                                       (rec.get("predicted_slug") or "")).lower():
                continue
            kept.append(rec)
    total = len(kept)
    if sort and sort != "manifest" and sort in ROW_SORTS:
        kept.sort(key=lambda rec: _row_sort_key(rec, sort))
    return kept[offset:offset + limit], total


def run_result(runs_dir, run_id, query_id):
    """Return one recorded result by query id, or None."""
    path = run_path(runs_dir, run_id, "results.jsonl")
    if not query_id or not path or not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if record.get("query_id") == query_id:
                return record
    return None
