"""Copy all filtered comparison cases into a new set. Keep source annotations."""

import hashlib
import json
import os

import benchmark
import run_compare
import testset_from_run
import testsets
from checked_read_cache import signature

FILTER_KEYS = {"a", "b", "group", "k", "common", "q"}


def _check_runs(runs):
    try:
        changed = any(
            tuple(signature(p) for p in run["paths"]) != run["signature"]
            for run in runs
        )
    except OSError as exc:
        raise testsets.TestsetError(
            409, "A saved run changed. Refresh the preview."
        ) from exc
    if changed:
        raise testsets.TestsetError(409, "A saved run changed. Refresh the preview.")


def _rows(conn, sql, args):
    cursor = conn.execute(sql, args)
    columns = [item[0] for item in cursor.description]
    return [dict(zip(columns, row)) for row in cursor]


def prepare(runs_dir, params):
    """Read immutable run files before the database write lock."""
    try:
        return _prepare(runs_dir, params)
    except run_compare.CompareError as exc:
        raise testsets.TestsetError(exc.code, str(exc)) from exc
    except OSError as exc:
        raise testsets.TestsetError(
            409, "A saved run changed. Refresh the preview."
        ) from exc
    except (ValueError, TypeError) as exc:
        raise testsets.TestsetError(
            422, "The saved comparison data has an invalid value."
        ) from exc


def _prepare(runs_dir, params):
    if set(params) - FILTER_KEYS - {"source"}:
        raise testsets.TestsetError(400, "Unknown testset selection parameters.")
    if any(len(values) != 1 for values in params.values()):
        raise testsets.TestsetError(400, "Repeated testset selection parameters.")
    source_side = params.get("source", ["b"])[0]
    if source_side not in ("a", "b"):
        raise testsets.TestsetError(400, "Choose annotation source A or B.")
    options = run_compare.parameters({k: v for k, v in params.items() if k != "source"})
    run_sources = [run_compare.load(runs_dir, options[key]) for key in ("a_id", "b_id")]
    data = run_compare.compare(runs_dir, None, **options, all_rows=True)
    return options, run_sources, data, source_side


def _selection(conn, runs_dir, params, prepared=None):
    """Return a validated preview and the source rows. Read one database snapshot."""
    options, run_sources, data, source_side = prepared or prepare(runs_dir, params)
    source = data[source_side]["set"]
    source_row = conn.execute(
        "SELECT label_note FROM test_set WHERE set_name = ?", (source,)
    ).fetchone()
    if source_row is None:
        raise testsets.TestsetError(
            409, f"The source testset {source} no longer exists."
        )
    current, _ = benchmark.build_queries(conn, "", source)
    current = {r["image_path"]: r for r in current}
    photos = {
        (r["place"], r["file_name"]): r
        for r in _rows(
            conn,
            "SELECT * FROM test_photo WHERE set_name = ? ORDER BY place, file_name",
            (source,),
        )
    }
    copied, conflicts = {}, []
    support = {}
    for item in current.values():
        if item["label"] == "positive":
            support.setdefault((item["image_sha256"], item["slug"]), item)
    for case in data["rows"]:
        saved = case[source_side]
        if saved is None:
            conflicts.append(
                f"{case['image_path']}: absent from source {source_side.upper()}"
            )
            continue
        found = current.get(saved["image_path"])
        if saved["label"] in ("variant", "unlabelled"):
            conflicts.append(
                f"{saved['image_path']}: saved label {saved['label']} cannot be validated for this copy"
            )
            continue
        if not found or any(
            found[key] != saved[key]
            for key in ("image_sha256", "slug", "label", "truth")
        ):
            conflicts.append(
                f"{saved['image_path']}: source photo or annotation changed"
            )
            continue
        place, _, file_name = saved["image_path"].rpartition("/")
        copied[(place, file_name)] = photos[(place, file_name)]
    # Keep all accepted wine slugs for each selected positive image. A search can
    # hide another positive assignment that supplies an accepted answer.
    selected_keys = set(copied)
    represented = {
        (p["sha256"], p["place"]) for p in copied.values() if p["label"] == "positive"
    }
    for row in list(copied.values()):
        saved = current[f"{row['place']}/{row['file_name']}"]
        if saved["label"] != "positive":
            continue
        for slug in saved["truth"]:
            if (row["sha256"], slug) in represented:
                continue
            item = support[(row["sha256"], slug)]
            place, _, file_name = item["image_path"].rpartition("/")
            copied[(place, file_name)] = photos[(place, file_name)]
            represented.add((row["sha256"], slug))
    keys = sorted(copied)
    comments = [
        r
        for r in _rows(
            conn,
            "SELECT * FROM test_photo_comment WHERE set_name = ? ORDER BY id",
            (source,),
        )
        if (r["place"], r["file_name"]) in copied
    ]
    groups = _rows(
        conn,
        "SELECT * FROM test_variant WHERE set_name = ? ORDER BY group_no, wine_slug",
        (source,),
    )
    places = {k[0] for k in keys}
    group_numbers = {r["group_no"] for r in groups if r["wine_slug"] in places}
    groups = [r for r in groups if r["group_no"] in group_numbers]
    _check_runs(run_sources)
    fingerprint = dict(
        filters=params,
        source=source,
        cases=[(r["image_path"], r["group"]) for r in data["rows"]],
        photos=[copied[k] for k in keys],
        comments=comments,
        groups=groups,
        source_note=source_row[0],
        runs=[r["signature"] for r in run_sources],
    )
    token = hashlib.sha256(
        json.dumps(
            fingerprint, sort_keys=True, ensure_ascii=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    enabled = data["comparison_enabled"] or options["group"] == "not_compared"
    view = dict(
        source=source,
        source_side=source_side,
        selected=data["total"],
        photos=len(keys),
        support_photos=len(set(keys) - selected_keys),
        wines=len({key[0] for key in keys if key[0] != testsets.NULL_SLUG}),
        photo_comments=len(comments),
        variant_slugs=len(groups),
        conflicts=len(conflicts),
        conflict_examples=conflicts[:5],
        can_create=enabled and bool(keys) and not conflicts,
        name=testset_from_run.proposed_name(conn, source),
        token=token,
    )
    return view, keys, copied, comments, groups, source_row[0], run_sources


def preview(conn, runs_dir, params, prepared=None):
    """Read a preview without creating a testset."""
    try:
        return _selection(conn, runs_dir, params, prepared)[0]
    except run_compare.CompareError as exc:
        raise testsets.TestsetError(exc.code, str(exc)) from exc
    except OSError as exc:
        raise testsets.TestsetError(
            409, "A saved run changed. Refresh the preview."
        ) from exc
    except (ValueError, TypeError) as exc:
        raise testsets.TestsetError(
            422, "The saved comparison data has an invalid value."
        ) from exc


def body_parameters(body):
    """Validate a write body before reading runs or taking the database lock."""
    if set(body) - FILTER_KEYS - {"source", "name", "token"}:
        raise testsets.TestsetError(400, "Unknown testset creation fields.")
    name, token = body.get("name"), body.get("token")
    if not isinstance(name, str) or not testset_from_run.NAME_RE.fullmatch(name):
        raise testsets.TestsetError(400, "Use only a-z, 0-9, `_`, and `-` in the name.")
    if not isinstance(token, str) or len(token) != 64:
        raise testsets.TestsetError(400, "Open a preview before creating the testset.")
    values = {k: v for k, v in body.items() if k not in ("name", "token")}
    if any(not isinstance(v, str) for v in values.values()):
        raise testsets.TestsetError(400, "Selection fields MUST be strings.")
    params = {k: [v] for k, v in values.items()}
    return params


def build(conn, runs_dir, body, prepared=None):
    """Create a set in the caller's write transaction. Reject stale previews."""
    params = body_parameters(body)
    name, token = body["name"], body["token"]
    values = {k: v[0] for k, v in params.items()}
    try:
        view, keys, photos, comments, groups, note, run_sources = _selection(
            conn, runs_dir, params, prepared
        )
    except run_compare.CompareError as exc:
        raise testsets.TestsetError(exc.code, str(exc)) from exc
    except OSError as exc:
        raise testsets.TestsetError(
            409, "A saved run changed. Refresh the preview."
        ) from exc
    except (ValueError, TypeError) as exc:
        raise testsets.TestsetError(
            422, "The saved comparison data has an invalid value."
        ) from exc
    if view["token"] != token:
        raise testsets.TestsetError(
            409, "The selection or source annotations changed. Refresh the preview."
        )
    if not view["can_create"]:
        raise testsets.TestsetError(
            409, "No complete selection can be copied. Review the preview conflicts."
        )
    if name in testsets.set_names(conn):
        raise testsets.TestsetError(409, f"The testset {name} already exists.")
    now = testsets.now_local()
    origin = (
        f"Created from Compare runs on {now}. Selection: "
        + json.dumps(values, sort_keys=True, ensure_ascii=True)
        + f". Selected cases: {view['selected']}. Copied photos: {view['photos']}. "
        "Wine slugs, photo annotations, photo comments, and relevant variant groups are copies. "
        "Additional positive assignments retain accepted answers. Image tags remain shared."
    )
    conn.execute(
        "INSERT INTO test_set(set_name, source_dir, edited_at, label_note) VALUES (?,?,?,?)",
        (
            name,
            os.path.realpath(runs_dir),
            now,
            origin + ("\n\n" + note if note else ""),
        ),
    )
    columns = testset_from_run._columns(conn, "test_photo")
    sql = f"INSERT INTO test_photo(set_name,{','.join(columns)}) VALUES ({','.join('?' for _ in range(len(columns) + 1))})"
    conn.executemany(sql, [(name, *(photos[key][c] for c in columns)) for key in keys])
    columns = ["place", "file_name", "created_at", "source", "text"]
    conn.executemany(
        "INSERT INTO test_photo_comment(set_name,place,file_name,created_at,source,text) VALUES (?,?,?,?,?,?)",
        [(name, *(row[c] for c in columns)) for row in comments],
    )
    conn.executemany(
        "INSERT INTO test_variant(set_name,wine_slug,group_no) VALUES (?,?,?)",
        [(name, row["wine_slug"], row["group_no"]) for row in groups],
    )
    _check_runs(run_sources)
    return dict(
        ok=True,
        set=name,
        source=view["source"],
        selected=view["selected"],
        photos=view["photos"],
        support_photos=view["support_photos"],
        photo_comments=len(comments),
        variant_slugs=len(groups),
    )
