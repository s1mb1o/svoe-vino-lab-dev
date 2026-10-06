"""Read the run files of `runs/` for the Runs page of the lab server.

A run is one directory `runs/<run id>/` of `scripts/match_run.py` or
`pipeline/benchmark.py`: `run.json`, `metrics.json`, `results.jsonl`, and more. The lab
database does not hold the runs. This module keeps run files unchanged. It writes
disposable row summaries in `data/cache/run-index/` for the standard runs directory.
Custom runs directories use the hidden directory `.row-index-cache/`.

The functions are the run functions of `scripts/review_server.py`. Each one takes the
directory of the runs as an argument, not as a global. The old tool keeps its own copy.

The key `configuration` of `run.json` names the lab configuration of a run: one entry of
the key `embeddings` of `config.yaml`. A run with no such key has no configuration. Read
`docs/plans/23_runs-page.md`.
"""
import json
import os
from collections import OrderedDict
from threading import Lock

import summary_cache

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

_RESULT_CACHE = OrderedDict()
_QUERY_CACHE = OrderedDict()
_RESULT_CACHE_LOCK = Lock()
_MAX_CACHED_RUNS = 3
_MAX_CACHED_ROWS = 50000
_SUMMARY_KEYS = ("query_id", "image_path", "predicted_slug", "image_sha256", "slug",
                 "label", "rank_of_truth", "outcome", "latency_ms")


def _cache_directory(path):
    runs = os.path.dirname(os.path.dirname(path))
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if os.path.realpath(runs) == os.path.realpath(os.path.join(root, "runs")):
        return os.path.join(root, "data", "cache", "run-index")
    return os.path.join(runs, ".row-index-cache")


def _remember_result(path, key, result):
    with _RESULT_CACHE_LOCK:
        _RESULT_CACHE[path] = (key, result)
        _RESULT_CACHE.move_to_end(path)
        while (len(_RESULT_CACHE) > _MAX_CACHED_RUNS or
               sum(len(value[1]["rows"]) for value in _RESULT_CACHE.values())
               > _MAX_CACHED_ROWS):
            _RESULT_CACHE.popitem(last=False)


def _remember_queries(path, key, queries):
    with _RESULT_CACHE_LOCK:
        _QUERY_CACHE[path] = (key, queries)
        _QUERY_CACHE.move_to_end(path)
        while (len(_QUERY_CACHE) > _MAX_CACHED_RUNS or
               sum(len(value[1]) for value in _QUERY_CACHE.values()) > _MAX_CACHED_ROWS):
            _QUERY_CACHE.popitem(last=False)


def _save_queries(path, key, queries):
    if len(queries) <= _MAX_CACHED_ROWS:
        _remember_queries(path, key, queries)
        # Pairs preserve JSON scalar query types and the first duplicate's offset.
        summary_cache.store(_cache_directory(path), "queries-v1", path, key,
                            list(queries.items()))


def _compact_candidates(row):
    """After twin ranks are computed, filters need only the top score and rule flag."""
    candidates = row["candidates"]
    step = rule_step(row)
    row["candidates"] = ([{"score": candidates[0].get("score"), "explain": step}]
                         if candidates else [])


def _file_key(path, stat):
    return (path, stat.st_dev, stat.st_ino, stat.st_size,
            stat.st_mtime_ns, stat.st_ctime_ns)


def _saved_result_index(path, key, fh):
    """Load a checked row summary without building an absent index."""
    directory = _cache_directory(path)
    saved = summary_cache.load(directory, "rows-v2", path, key)
    migrate = saved is summary_cache.MISS
    if migrate:
        saved = summary_cache.load(directory, "rows-v1", path, key)
    if (isinstance(saved, dict) and isinstance(saved.get("rows"), list)
            and isinstance(saved.get("twins"), dict)
            and key == _file_key(path, os.fstat(fh.fileno()))):
        saved["queries"] = {}
        for offset, row in saved["rows"]:
            if migrate:
                _compact_candidates(row)
            saved["queries"].setdefault(row.get("query_id"), offset)
        if len(saved["rows"]) <= _MAX_CACHED_ROWS:
            _remember_result(path, key, saved)
        if migrate:
            summary_cache.store(directory, "rows-v2", path, key,
                                {"rows": saved["rows"], "twins": saved["twins"]})
        if len(saved["queries"]) <= _MAX_CACHED_ROWS:
            _remember_queries(path, key, saved["queries"])
        return saved
    return None


def _query_index(path, key, fh):
    with _RESULT_CACHE_LOCK:
        hit = _QUERY_CACHE.get(path)
        if hit is not None and hit[0] == key:
            _QUERY_CACHE.move_to_end(path)
            return hit[1]
    saved = summary_cache.load(_cache_directory(path), "queries-v1", path, key)
    if isinstance(saved, list) and key == _file_key(path, os.fstat(fh.fileno())):
        try:
            queries = dict(saved)
        except (TypeError, ValueError):
            pass
        else:
            _remember_queries(path, key, queries)
            return queries
    # Upgrade an existing row summary without scanning results.jsonl again.
    result = _saved_result_index(path, key, fh)
    if result is None:
        return None
    _save_queries(path, key, result["queries"])
    return result["queries"]


def _result_index(path, fh):
    """Index row filters and byte offsets. Keep full traces on disk.

    Use the open file identity to invalidate appends, rewrites, and replacements.
    The cache holds at most three runs and 50,000 row summaries in total.
    """
    key = _file_key(path, os.fstat(fh.fileno()))
    with _RESULT_CACHE_LOCK:
        hit = _RESULT_CACHE.get(path)
        if hit is not None and hit[0] == key:
            _RESULT_CACHE.move_to_end(path)
            return hit[1]
    saved = _saved_result_index(path, key, fh)
    if saved is not None:
        return saved
    directory = _cache_directory(path)
    rows, queries, twins = [], {}, {}
    fh.seek(0)
    while True:
        offset = fh.tell()
        line = fh.readline()
        if not line:
            break
        try:
            rec = json.loads(line)
        except (ValueError, UnicodeDecodeError):
            continue
        if not isinstance(rec, dict):
            continue
        summary = {field: rec.get(field) for field in _SUMMARY_KEYS}
        summary["error"] = bool(rec.get("error"))
        summary["candidates"] = []
        for candidate in rec.get("candidates") or ():
            item = {field: candidate.get(field) for field in ("slug", "rank", "score")}
            step = candidate.get("explain")
            if isinstance(step, dict) and step.get("kind") == "cluster_rules":
                item["explain"] = {"kind": "cluster_rules", "changed": step.get("changed")}
            summary["candidates"].append(item)
        rows.append((offset, summary))
        # Match the first result when the file holds a duplicate query id.
        queries.setdefault(rec.get("query_id"), offset)
        sha, slug, label = (rec.get(field) for field in ("image_sha256", "slug", "label"))
        if sha and slug and label in ("positive", "negative"):
            slot = twins.setdefault(sha, {"positive": set(), "negative": set()})
            slot[label].add(slug)
    for slot in twins.values():
        slot["positive"] = sorted(slot["positive"])
        slot["negative"] = sorted(slot["negative"])
    for _, summary in rows:
        add_twin(summary, twins)
        _compact_candidates(summary)
    result = {"rows": rows, "queries": queries, "twins": twins}
    if key == _file_key(path, os.fstat(fh.fileno())) and len(rows) <= _MAX_CACHED_ROWS:
        _remember_result(path, key, result)
        summary_cache.store(directory, "rows-v2", path, key, {"rows": rows, "twins": twins})
        _save_queries(path, key, queries)
    return result


def twin_index(runs_dir, run_id):
    """Return `image_sha256` -> {"positive": [slug...], "negative": [slug...]}.

    The lists hold the distinct slugs of the rows of this run whose photo holds these
    exact bytes. The label `variant` is left out: it states no truth about the photo.
    The result shares the bounded row index of `results.jsonl`.
    """
    path = run_path(runs_dir, run_id, "results.jsonl")
    if not path or not os.path.exists(path):
        return {}
    with open(path, "rb") as fh:
        return _result_index(path, fh)["twins"]


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
        "conflict_slugs": {"positive": list(positive), "both": both} if conflict else None,
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
    with open(path, "rb") as fh:
        index = _result_index(path, fh)
        if mode == "all" and not query and sort == "manifest":
            kept = index["rows"]
        else:
            kept = [(position, rec) for position, rec in index["rows"]
                    if row_matches(rec, mode) and
                    (not query or query in ((rec.get("image_path") or "") + " " +
                                           (rec.get("predicted_slug") or "")).lower())]
        total = len(kept)
        if sort and sort != "manifest" and sort in ROW_SORTS:
            kept.sort(key=lambda item: _row_sort_key(item[1], sort))
        rows = []
        for position, _ in kept[offset:offset + limit]:
            fh.seek(position)
            rec = json.loads(fh.readline())
            rows.append(add_twin(rec, index["twins"]))
    return rows, total


def run_result(runs_dir, run_id, query_id):
    """Return one recorded result by query id, or None."""
    path = run_path(runs_dir, run_id, "results.jsonl")
    if not query_id or not path or not os.path.isfile(path):
        return None
    with open(path, "rb") as fh:
        key = _file_key(path, os.fstat(fh.fileno()))
        with _RESULT_CACHE_LOCK:
            hit = _RESULT_CACHE.get(path)
            index = hit[1] if hit is not None and hit[0] == key else None
            if index is not None:
                _RESULT_CACHE.move_to_end(path)
        queries = index["queries"] if index is not None else _query_index(path, key, fh)
        if queries is not None:
            position = queries.get(query_id)
            if position is not None:
                fh.seek(position)
                return json.loads(fh.readline())
        else:
            # A direct trace request for an early row must not first index the run.
            for line in fh:
                try:
                    record = json.loads(line)
                except (ValueError, UnicodeDecodeError):
                    continue
                if isinstance(record, dict) and record.get("query_id") == query_id:
                    return record
    return None
