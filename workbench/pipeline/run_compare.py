"""Compare saved query snapshots and answers. Never change a run or call a model."""

from collections import Counter, defaultdict
from contextlib import closing
import json
import math
from pathlib import Path
import re
import sqlite3
from urllib.parse import quote

from checked_read_cache import CheckedReadCache, signature
import run_files

GROUPS = ("both_succeed", "regressions", "improvements", "both_fail")
FILTERS = ("differences", "all", *GROUPS, "errors", "unscored", "not_compared")
LABELS = ("positive", "variant", "no_match", "negative", "unlabelled")
CACHE = CheckedReadCache(max_entries=4, max_bytes=64 * 1024 * 1024)
MAX_ROWS = 100000


class CompareError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def _records(path):
    """Read JSONL with bounded line, file, and row sizes."""
    if path.stat().st_size > 2 * 1024**3:
        raise CompareError(422, "The run file exceeds the 2 GiB comparison limit.")
    with path.open("rb") as stream:
        count = 0
        while line := stream.readline(16 * 1024**2 + 1):
            if len(line) > 16 * 1024**2:
                raise CompareError(422, "A run record exceeds the 16 MiB limit.")
            if not line.strip():
                continue
            count += 1
            if count > MAX_ROWS:
                raise CompareError(422, "The run exceeds the 100,000 case limit.")
            try:
                row = json.loads(line)
            except (ValueError, UnicodeError) as exc:
                raise CompareError(
                    422, f"Invalid JSON in {path.name}, record {count}."
                ) from exc
            if not isinstance(row, dict):
                raise CompareError(422, f"Expected an object in {path.name}.")
            yield row


def _query(row):
    qid, sha, slug, label, truth, path = (
        row.get(key)
        for key in ("query_id", "image_sha256", "slug", "label", "truth", "image_path")
    )
    if (
        not isinstance(qid, str)
        or not qid
        or len(qid) > 200
        or not isinstance(sha, str)
        or not re.fullmatch("[a-f0-9]{64}", sha)
        or not isinstance(slug, str)
        or not slug
        or len(slug) > 1000
        or label not in LABELS
        or not isinstance(path, str)
        or not path
        or len(path) > 4096
        or not isinstance(truth, list)
        or len(truth) > 1000
        or any(not isinstance(s, str) or not s or len(s) > 1000 for s in truth)
        or (label in ("positive", "variant") and not truth)
        or (label in ("no_match", "negative", "unlabelled") and truth)
    ):
        raise CompareError(
            422, "The saved query snapshot has an invalid image identity or annotation."
        )
    return dict(
        query_id=qid,
        image_sha256=sha,
        slug=slug,
        label=label,
        truth=sorted(set(truth)),
        image_path=path,
    )


def _answer(record, query):
    if record is None:
        return {
            "error": "No saved result for this query.",
            "candidates": [],
            "outcome": "missing_result",
        }
    for key in ("image_sha256", "slug", "label", "truth", "image_path"):
        value = (
            sorted(set(record[key]))
            if key == "truth"
            and isinstance(record.get(key), list)
            and all(isinstance(v, str) for v in record[key])
            else record.get(key)
        )
        if value != query[key]:
            return {
                "error": "The saved result does not match its query snapshot.",
                "candidates": [],
                "outcome": "invalid_result",
            }
    candidates = record.get("candidates")
    if not isinstance(candidates, list) or any(
        not isinstance(c, dict) or not isinstance(c.get("slug"), str) or not c["slug"]
        for c in candidates
    ):
        return {
            "error": "Invalid saved candidates.",
            "candidates": [],
            "outcome": "invalid_result",
        }
    seen, compact = set(), []
    for candidate in candidates:
        if candidate["slug"] in seen:
            continue
        seen.add(candidate["slug"])
        score = candidate.get("score")
        compact.append(
            {
                "slug": candidate["slug"],
                "rank": len(compact) + 1,
                "score": score
                if type(score) in (int, float) and math.isfinite(score)
                else None,
            }
        )
    latency = record.get("latency_ms")
    return {
        "error": str(record["error"])[:2000] if record.get("error") else None,
        "outcome": str(record.get("outcome") or "not recorded")[:200],
        "latency_ms": latency
        if type(latency) in (int, float) and math.isfinite(latency) and latency >= 0
        else None,
        "candidates": compact,
    }


def load(runs_dir, run_id):
    """Read a finished run with a complete saved query snapshot."""
    meta_path = run_files.run_path(runs_dir, run_id, "run.json")
    if not meta_path:
        raise CompareError(400, "Invalid run identifier.")
    paths = [
        Path(run_files.run_path(runs_dir, run_id, name) or "")
        for name in ("run.json", "queries.jsonl", "results.jsonl")
    ]
    if not paths[0].is_file():
        raise CompareError(404, "Unknown run.")
    if not all(p.is_file() for p in paths):
        raise CompareError(
            422,
            "The saved query snapshot or results are missing. Compatibility cannot be verified.",
        )

    def read():
        before = tuple(signature(p) for p in paths)
        if paths[0].stat().st_size > 1024**2:
            raise CompareError(422, "The run metadata exceeds the comparison limit.")
        meta = json.loads(paths[0].read_text())
        if not isinstance(meta, dict) or not isinstance(meta.get("options"), dict):
            raise CompareError(422, "Invalid run metadata.")
        if not meta.get("finished") or meta["options"].get("dry_run"):
            raise CompareError(409, "Compare finished, non-dry runs only.")
        if not run_files.test_set_of(meta) or meta.get("query_scope") == "drawer":
            raise CompareError(422, "This run has no scored testset snapshot.")
        queries, answers, result_ids = {}, {}, set()
        extra_results = 0
        for raw in _records(paths[1]):
            row = _query(raw)
            if row["query_id"] in queries:
                raise CompareError(
                    422, "The query snapshot has duplicate query identifiers."
                )
            queries[row["query_id"]] = row
        for row in _records(paths[2]):
            qid = row.get("query_id")
            if not isinstance(qid, str) or not qid or qid in result_ids:
                raise CompareError(
                    422, "The results have invalid or duplicate query identifiers."
                )
            result_ids.add(qid)
            if qid in queries:
                answers[qid] = _answer(row, queries[qid])
            else:
                extra_results += 1
        query_set = meta.get("query_set") or {}
        if not isinstance(query_set, dict):
            raise CompareError(422, "Invalid saved query-count metadata.")
        total = query_set.get("total")
        if total is not None and total != len(queries):
            raise CompareError(
                422, "The saved query count differs from the run metadata."
            )
        if not queries:
            raise CompareError(422, "The run has no saved queries.")
        after = tuple(signature(p) for p in paths)
        if before != after:
            raise CompareError(
                409, "The run changed while reading. Retry after it finishes."
            )
        return {
            "id": run_id,
            "set": run_files.test_set_of(meta),
            "configuration": run_files.configuration_of(meta),
            "started": meta.get("started"),
            "use_cache": meta.get("use_cache"),
            "use_barcode": meta.get("use_barcode"),
            "negative_strict": meta["options"].get("negative_strict", False),
            "extra_results": extra_results,
            "queries": queries,
            "answers": answers,
            "paths": paths,
            "signature": after,
        }

    try:
        return CACHE.get(
            (str(Path(runs_dir).resolve()), run_id), paths, read, copy_value=False
        )
    except CompareError:
        raise
    except (OSError, ValueError, TypeError) as exc:
        raise CompareError(422, "Cannot read the saved run: " + str(exc)[:300]) from exc


def align(a, b):
    """Use image bytes and wine placement. Use paths only to resolve repetitions."""
    maps = []
    for run in (a, b):
        grouped = defaultdict(list)
        for row in run["queries"].values():
            grouped[(row["image_sha256"], row["slug"])].append(row)
        maps.append(grouped)
    pairs = []
    for base in sorted(maps[0].keys() | maps[1].keys()):
        left, right = maps[0].get(base, []), maps[1].get(base, [])
        if max(len(left), len(right)) <= 1:
            pairs.append((left[0] if left else None, right[0] if right else None))
            continue
        by_path = [{row["image_path"]: row for row in side} for side in (left, right)]
        if any(len(index) != len(side) for index, side in zip(by_path, (left, right))):
            raise CompareError(
                422,
                "Repeated image assignments cannot be aligned: duplicate saved paths.",
            )
        for path in sorted(by_path[0].keys() | by_path[1].keys()):
            pairs.append((by_path[0].get(path), by_path[1].get(path)))
    return pairs


def side(run, query, k):
    if query is None:
        return None
    answer = run["answers"].get(query["query_id"]) or _answer(None, query)
    candidates = answer["candidates"]
    rank = next((c["rank"] for c in candidates if c["slug"] in query["truth"]), None)
    if answer.get("error"):
        state, note = "error", answer["error"]
    elif query["label"] == "negative":
        state, note = (
            "unscored",
            "A negative label forbids one wine. It does not establish a correct answer.",
        )
    elif query["label"] == "unlabelled":
        state, note = "unscored", "No expected answer was recorded."
    else:
        passed = (
            not candidates
            if query["label"] == "no_match"
            else rank is not None and rank <= k
        )
        state, note = ("pass" if passed else "fail"), ""
    fragment = (
        quote(run["id"], safe="")
        + "/"
        + "/".join(quote(p, safe="") for p in query["image_path"].split("/"))
    )
    return {
        **query,
        "status": state,
        "note": note,
        "outcome": answer["outcome"],
        "latency_ms": answer.get("latency_ms"),
        "rank_of_truth": rank,
        "candidate_count": len(candidates),
        "candidates": [dict(c) for c in candidates[: max(5, k)]],
        "truth": list(query["truth"]),
        "inspect_url": "/runs?set=" + quote(run["set"], safe="") + "#" + fragment,
    }


def _photos(db_path, rows):
    if not db_path:
        return None
    digests = sorted({row["image_sha256"] for row in rows})
    try:
        with closing(
            sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True)
        ) as conn:
            images = {}
            for start in range(0, len(digests), 500):
                batch = digests[start : start + 500]
                images.update(
                    (sha, (folder, ext))
                    for sha, folder, ext in conn.execute(
                        "SELECT sha256,folder,extension FROM image WHERE sha256 IN ("
                        + ",".join("?" for _ in batch)
                        + ")",
                        batch,
                    )
                )
            for row in rows:
                hit = images.get(row["image_sha256"])
                row["photo_url"] = (
                    "/images/"
                    + quote(hit[0], safe="")
                    + "/"
                    + row["image_sha256"]
                    + "."
                    + quote(hit[1], safe="")
                    if hit and all(isinstance(v, str) and v for v in hit)
                    else None
                )
    except sqlite3.Error:
        return "The image store is unavailable. Saved results remain comparable."
    return None


def compare(
    runs_dir,
    db_path,
    a_id,
    b_id,
    *,
    group="differences",
    k=1,
    common=False,
    query="",
    offset=0,
    limit=50,
    all_rows=False,
):
    """Compare saved cases. `all_rows` is for internal testset creation only."""
    if not a_id or not b_id or a_id == b_id:
        raise CompareError(400, "Select two different runs.")
    if (
        group not in FILTERS
        or type(k) is not int
        or k not in (1, 5, 10)
        or type(common) is not bool
    ):
        raise CompareError(400, "Invalid comparison filter or rank.")
    if (
        type(offset) is not int
        or offset < 0
        or type(limit) is not int
        or not 1 <= limit <= 200
    ):
        raise CompareError(400, "Use offset >= 0 and limit from 1 to 200.")
    a, b = load(runs_dir, a_id), load(runs_dir, b_id)
    rows, changes = [], Counter()
    for left, right in align(a, b):
        same = (
            left is not None
            and right is not None
            and all(left[key] == right[key] for key in ("label", "truth"))
        )
        if left is None:
            reason = "Only in B"
            changes["only_b"] += 1
        elif right is None:
            reason = "Only in A"
            changes["only_a"] += 1
        elif not same:
            reason = "Expected answers or label changed"
            changes["changed"] += 1
        else:
            reason = ""
            changes["unchanged"] += 1
        first, second = side(a, left, k), side(b, right, k)
        if not same:
            bucket = "not_compared"
        elif "error" in (first["status"], second["status"]):
            bucket = "errors"
        elif "unscored" in (first["status"], second["status"]):
            bucket = "unscored"
        else:
            bucket = {
                (True, True): "both_succeed",
                (True, False): "regressions",
                (False, True): "improvements",
                (False, False): "both_fail",
            }[first["status"] == "pass", second["status"] == "pass"]
        identity = left or right
        rows.append(
            {
                "image_sha256": identity["image_sha256"],
                "image_path": identity["image_path"],
                "group": bucket,
                "reason": reason,
                "a": first,
                "b": second,
            }
        )
    rows.sort(
        key=lambda row: (
            (row["a"] or row["b"])["slug"],
            row["image_path"],
            row["image_sha256"],
        )
    )
    exact = not any(changes[key] for key in ("only_a", "only_b", "changed"))
    enabled = exact or (common and changes["unchanged"] > 0)
    counts = dict.fromkeys((*GROUPS, "errors", "unscored", "not_compared"), 0)
    eligible = [row for row in rows if enabled or row["group"] == "not_compared"]
    counts.update(Counter(row["group"] for row in eligible))
    counts["differences"] = counts["regressions"] + counts["improvements"]
    counts["all"] = sum(counts[g] for g in (*GROUPS, "errors", "unscored"))
    search = query.strip().casefold()

    def selected(row):
        if group == "differences":
            matches = row["group"] in ("regressions", "improvements")
        elif group == "all":
            matches = row["group"] != "not_compared"
        else:
            matches = row["group"] == group
        if not matches or not search:
            return matches
        texts = [row["image_path"], row["image_sha256"]]
        for part in (row["a"], row["b"]):
            if part:
                texts.extend([part["image_path"], part["slug"], *part["truth"]])
                run = a if part is row["a"] else b
                answer = run["answers"].get(part["query_id"], {})
                texts.extend(c["slug"] for c in answer.get("candidates", []))
        return search in " ".join(texts).casefold()

    filtered = [row for row in eligible if selected(row)]
    page = filtered if all_rows else filtered[offset : offset + limit]
    images_error = _photos(db_path, page)
    if any(
        tuple(signature(p) for p in run["paths"]) != run["signature"] for run in (a, b)
    ):
        raise CompareError(409, "A saved run changed. Refresh the comparison.")
    header_keys = (
        "id",
        "set",
        "configuration",
        "started",
        "use_cache",
        "use_barcode",
        "negative_strict",
    )
    warnings = []
    for run, name in ((a, "A"), (b, "B")):
        if run["extra_results"]:
            warnings.append(
                f"Run {name} has {run['extra_results']} results outside its query snapshot. These results are excluded."
            )
        lengths = [
            len(run["answers"].get(q["query_id"], {}).get("candidates", []))
            for q in run["queries"].values()
            if q["label"] in ("positive", "variant")
        ]
        if k > 1 and lengths and max(lengths) < k:
            warnings.append(
                f"Run {name} saved at most {max(lengths)} distinct candidates. Top {k} uses the available returned candidates."
            )
    if a["set"] != b["set"]:
        warnings.append(
            "Testset names differ. Compatibility uses saved image identities and annotations."
        )
    if any(a[key] != b[key] for key in ("use_cache", "use_barcode", "negative_strict")):
        warnings.append(
            "Run settings differ. Latency and negative-label settings require separate interpretation."
        )
    return {
        "a": {key: a[key] for key in header_keys},
        "b": {key: b[key] for key in header_keys},
        "compatibility": {
            "status": "exact"
            if exact
            else "partial"
            if changes["unchanged"]
            else "incompatible",
            "exact": exact,
            "a_cases": len(a["queries"]),
            "b_cases": len(b["queries"]),
            **{
                key: changes[key]
                for key in ("unchanged", "changed", "only_a", "only_b")
            },
        },
        "comparison_enabled": enabled,
        "common": common,
        "k": k,
        "group": group,
        "counts": counts,
        "rows": page,
        "total": len(filtered),
        "offset": offset,
        "limit": limit,
        "warnings": warnings,
        "images_error": images_error,
    }


def parameters(params):
    """Validate API parameters. Return arguments for `compare`."""
    allowed = {"a", "b", "group", "k", "common", "q", "offset", "limit"}
    if set(params) - allowed or any(len(values) != 1 for values in params.values()):
        raise CompareError(400, "Unknown or repeated comparison parameters.")

    def one(key, default=""):
        return params.get(key, [default])[0]

    try:
        rank, offset, limit = (
            int(one("k", "1")),
            int(one("offset", "0")),
            int(one("limit", "50")),
        )
    except (ValueError, TypeError) as exc:
        raise CompareError(400, "Invalid numeric comparison parameters.") from exc
    if one("common", "0") not in ("0", "1") or len(one("q")) > 1000:
        raise CompareError(400, "Invalid common-case option or search text.")
    return dict(
        a_id=one("a"),
        b_id=one("b"),
        group=one("group", "differences"),
        k=rank,
        common=one("common", "0") == "1",
        query=one("q"),
        offset=offset,
        limit=limit,
    )


def respond(runs_dir, db_path, params):
    """Validate the read-only API query and return an HTTP status and object."""
    try:
        return 200, compare(runs_dir, db_path, **parameters(params))
    except CompareError as exc:
        return exc.code, {"error": str(exc)}
    except (ValueError, TypeError):
        return 422, {"error": "The saved comparison data has an invalid value."}
    except OSError:
        return 409, {
            "error": "A saved run changed or became unavailable. Refresh the comparison."
        }
