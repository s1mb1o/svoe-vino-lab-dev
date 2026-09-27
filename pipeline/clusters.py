"""Embedding-dependent wine clusters and their files.

One embedding directory holds `clusters.json`, `cluster-notes.json`, and later
`cluster-rules.json`. The `full` and `label` vectors are separate similarity spaces.
The `combined` view is the union of their edges. Read
`docs/plans/30_embedding-clusters.md`.

Each manual pair of the table `wine_similar` (plan 62) is one more link of each view, with
`manual` in its list `by`. Read `docs/plans/62_similar-wines.md`.

Each two Active wines of one GTIN of `wine_code` (plan 64) are one more link of each view,
with `gtin` in its list `by`. So the rules build gives the wines of a shared GTIN a rule,
and the cluster re-rank of a photo with that GTIN can compare them. A QR URL gives no
link. Read `docs/plans/64_shared-gtin-rerank.md`.
"""
import collections
import contextlib
import fcntl
import hashlib
import json
import math
import os
import tempfile
import time
from contextlib import closing

import numpy as np

import embeddings
import similar_wines

VERSION = 1
CLUSTERS_FILE = "clusters.json"
NOTES_FILE = "cluster-notes.json"
RULES_FILE = "cluster-rules.json"
BUILD_LOCK = "clusters.lock"
NOTES_LOCK = "cluster-notes.json.lock"
SPACES = ("full", "label", "combined")
VECTOR_SPACES = ("full", "label")
# The value of `by` and of `signals` for a manual pair of `wine_similar` (plan 62).
MANUAL = "manual"
# The value of `by` and of `signals` for two wines of one GTIN of `wine_code` (plan 64).
GTIN = "gtin"
# The rule space of `cluster-rules.json` that each view shows. The view `combined` shows
# the `label` rules, because the matcher sends a label crop at query time (plans 43, 45).
RULE_SPACE_OF = {"full": "full", "label": "label", "combined": "label"}
DEFAULT_THRESHOLD = 0.95
# A build over one of these limits stops and keeps the old `clusters.json`. At threshold
# 0.95 the lab SigLIP 2 embedding gave 214 full links and a largest cluster of 8 wines.
# At full threshold 0.5 it gave 2,055,813 full links, one cluster of 2,045 wines, and a
# 5 GB file (2026-09-25).
MAX_LINKS = 20000
MAX_CLUSTER_SIZE = 50
# A connected component with fewer wines is not a stored cluster.
MIN_CLUSTER_SIZE = 2
# The block `clusters` of `config.yaml` sets these values for every embedding. A missing
# key takes the value of this dictionary.
CONFIG_KEY = "clusters"
CONFIG_DEFAULTS = {"full_threshold": DEFAULT_THRESHOLD, "label_threshold": DEFAULT_THRESHOLD,
                   "min_cluster_size": MIN_CLUSTER_SIZE, "max_links": MAX_LINKS,
                   "max_cluster_size": MAX_CLUSTER_SIZE}
MAX_NOTE = 4000
BLOCK = 512


class ClusterError(RuntimeError):
    """The embedding files or the requested cluster operation are not valid."""


class Busy(ClusterError):
    """Another process uses the selected embedding directory."""


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def cluster_key(slugs):
    """Return the stable key of one member set."""
    return hashlib.sha1("\n".join(sorted(slugs)).encode("utf-8")).hexdigest()[:12]


def validate_threshold(value, field="threshold"):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ClusterError("%s MUST be a number from -1 through 1" % field)
    value = float(value)
    if not math.isfinite(value) or not -1 <= value <= 1:
        raise ClusterError("%s MUST be a finite number from -1 through 1" % field)
    return value


def config_values(settings):
    """Return the thresholds and the limits of the block `clusters` of `config.yaml`."""
    try:
        _, config, _ = embeddings.read_config(settings.config_path)
    except embeddings.ConfigError as exc:
        raise ClusterError(str(exc)) from exc
    block = config.get(CONFIG_KEY)
    if block is None:
        block = {}
    if not isinstance(block, dict):
        raise ClusterError("the key `%s` of config.yaml MUST be a mapping" % CONFIG_KEY)
    unknown = sorted(set(block) - set(CONFIG_DEFAULTS))
    if unknown:
        raise ClusterError("%s: unknown key: %s" % (CONFIG_KEY, ", ".join(unknown)))
    values = {**CONFIG_DEFAULTS, **block}
    for key in ("full_threshold", "label_threshold"):
        values[key] = validate_threshold(values[key], "%s.%s" % (CONFIG_KEY, key))
    for key, low in (("min_cluster_size", 2), ("max_links", 1), ("max_cluster_size", 2)):
        value = values[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < low:
            raise ClusterError("%s.%s MUST be an integer of at least %d"
                               % (CONFIG_KEY, key, low))
    if values["min_cluster_size"] > values["max_cluster_size"]:
        raise ClusterError("%s.min_cluster_size MUST NOT be more than %s.max_cluster_size"
                           % (CONFIG_KEY, CONFIG_KEY))
    return values


def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as source:
            value = json.load(source)
    except FileNotFoundError:
        return default
    except (OSError, ValueError) as exc:
        raise ClusterError("cannot read %s: %s" % (path, exc)) from exc
    if not isinstance(value, dict):
        raise ClusterError("%s MUST hold one JSON object" % path)
    return value


def write_json(path, value):
    """Write one JSON object atomically."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = (json.dumps(value, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    fd, temporary = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp-clusters-")
    try:
        with os.fdopen(fd, "wb") as target:
            target.write(data)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.remove(temporary)
        except OSError:
            pass
        raise


@contextlib.contextmanager
def file_lock(directory, name, message):
    """Hold a non-blocking advisory lock in one embedding directory."""
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, name)
    with open(path, "a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Busy(message) from exc
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def _settings_entry(settings, name):
    try:
        return settings.find(name)
    except KeyError as exc:
        raise ClusterError("config.yaml has no embedding %s" % name) from exc
    except embeddings.ConfigError as exc:
        raise ClusterError("embedding %s: %s" % (name, exc)) from exc


def _index_items(index):
    """Return the stable part of the index item list for the input hash."""
    out = []
    for record in index.get("items") or []:
        if not isinstance(record, dict):
            raise ClusterError("index.json has an item that is not an object")
        out.append({key: record.get(key) for key in (
            "source_sha256", "view", "role", "embedding_hash", "row")})
    return sorted(out, key=lambda row: (
        str(row.get("source_sha256") or ""), str(row.get("view") or ""),
        -1 if not isinstance(row.get("row"), int) else row["row"]))


def _assignments(wines, items):
    """Return the current wine assignments of the planned embedding items."""
    rows = []
    for wine in wines:
        for image_type, digest in wine["columns"]:
            role = embeddings.ROLES.get(image_type)
            for view in embeddings.VIEWS:
                # A source that is a label close-up for this wine can also be a full
                # image of another wine. `read_inputs` then plans both source views.
                # Keep this wine assignment in its own observation space.
                if role == "label" and view != "label":
                    continue
                if (digest, view) in items:
                    rows.append({"slug": wine["slug"], "image_type": image_type,
                                 "source_sha256": digest, "view": view})
    return sorted(rows, key=lambda row: (
        row["slug"], row["view"], row["image_type"], row["source_sha256"]))


def _catalog(conn):
    fields = ("wine_slug", "name", "producer", "category", "color", "region", "grapes")
    return {row[0]: dict(zip(fields, row)) for row in conn.execute(
        "SELECT wine_slug, name, producer, category, color, region, grapes "
        "FROM wine_catalog WHERE state = 'Active' ORDER BY rowid")}


def _gtin_pairs(conn):
    """Return the sorted pairs (a, b) of the Active wines that have one GTIN of
    `wine_code` (plan 64). A GTIN of N wines gives N * (N - 1) / 2 pairs."""
    wines = collections.defaultdict(set)
    for value, slug in conn.execute(
            "SELECT c.value, c.wine_slug FROM wine_code c "
            "JOIN wine_catalog w ON w.wine_slug = c.wine_slug "
            "WHERE w.state = 'Active' AND c.kind = 'gtin'"):
        wines[value].add(slug)
    pairs = set()
    for slugs in wines.values():
        slugs = sorted(slugs)
        pairs.update((a, b) for i, a in enumerate(slugs) for b in slugs[i + 1:])
    return sorted(pairs)


def context(settings, name):
    """Read the current index identity and database assignments without its vectors."""
    embedding = _settings_entry(settings, name)
    directory = embeddings.entry_dir(settings.db_path, name)
    try:
        index = embeddings.read_index(directory)
    except (OSError, ValueError) as exc:
        raise ClusterError("cannot read the index of %s: %s" % (name, exc)) from exc
    if not index:
        raise ClusterError("embedding %s has no index; build the embedding first" % name)
    with closing(embeddings.open_database(settings.db_path)) as conn:
        wines, sources = embeddings.read_inputs(conn, settings.db_path)
        catalog = _catalog(conn)
        pairs = similar_wines.pairs(conn)
        gtin_pairs = _gtin_pairs(conn)
    # A manual pair counts only when both wines are in the build (plan 62).
    known = {wine["slug"] for wine in wines}
    similar = [[a, b] for a, b in pairs if a in known and b in known]
    gtin = [[a, b] for a, b in gtin_pairs if a in known and b in known]
    items = embeddings.plan_items(embedding, sources)
    names = embeddings.image_names(directory)
    status = embeddings.item_status(items, index, names)
    assignments = _assignments(wines, items)
    identity = {
        "embedding": name,
        "vectors_file": index.get("vectors_file"),
        "dim": index.get("dim"),
        "items": _index_items(index),
        "assignments": assignments,
    }
    # With no pair, the hash stays the hash of the builds before plan 62.
    if similar:
        identity["similar"] = similar
    # With no GTIN pair, the hash stays the hash of the builds before plan 64.
    if gtin:
        identity["gtin"] = gtin
    counts = collections.Counter(state for state, _ in status.values())
    return {
        "settings": settings, "embedding": embedding, "directory": directory,
        "index": index, "wines": wines, "sources": sources, "catalog": catalog,
        "items": items, "status": status, "assignments": assignments,
        "similar": similar, "input_hash": sha256_json(identity),
        "gtin": gtin,
        "status_counts": {state: counts.get(state, 0)
                          for state in ("current", "stale", "missing", "failed")},
    }


def _image_url(name, digest, view, embedding_hash):
    return "/embeddings/%s/images/%s?v=%s" % (
        name, embeddings.image_name(digest, view), embedding_hash[:16])


def current_rows(ctx, vectors):
    """Return the current vector rows, expanded to one row per wine assignment."""
    by_key = collections.defaultdict(lambda: collections.defaultdict(set))
    for assignment in ctx["assignments"]:
        key = (assignment["source_sha256"], assignment["view"])
        by_key[key][assignment["slug"]].add(assignment["image_type"])
    rows = {view: [] for view in VECTOR_SPACES}
    for key, (state, record) in sorted(ctx["status"].items()):
        if state != "current" or not isinstance(record, dict):
            continue
        digest, view = key
        if view not in rows:
            continue
        row = record.get("row")
        if not isinstance(row, int) or not 0 <= row < len(vectors):
            raise ClusterError("the current item %s/%s has an invalid vector row"
                               % (digest, view))
        for slug, image_types in sorted(by_key[key].items()):
            rows[view].append({
                "slug": slug,
                "source_sha256": digest,
                "image_types": sorted(image_types),
                "embedding_hash": record["embedding_hash"],
                "prepared_url": _image_url(
                    ctx["embedding"].name, digest, view, record["embedding_hash"]),
                "original_url": ctx["sources"][digest]["url"],
                "row": row,
                "vector": vectors[row],
            })
    return rows


def _shown_image(item):
    return {key: item[key] for key in (
        "source_sha256", "image_types", "prepared_url", "original_url")}


def _edge_record(left, right, similarity):
    if left["slug"] <= right["slug"]:
        a, b = left, right
    else:
        a, b = right, left
    return {
        "a": a["slug"], "b": b["slug"], "similarity": float(similarity),
        "a_image": _shown_image(a), "b_image": _shown_image(b),
    }


def _edge_tie_key(edge):
    return (edge["a_image"]["source_sha256"], edge["b_image"]["source_sha256"],
            edge["a_image"]["image_types"], edge["b_image"]["image_types"])


def similarity_edges(rows, threshold, block=BLOCK, max_links=MAX_LINKS, field="threshold"):
    """Return the best above-threshold image pair for each pair of wines.

    Stop with `ClusterError` when the wine pairs pass `max_links`. The check runs after
    each row, so a too-low threshold does not fill the memory."""
    threshold = validate_threshold(threshold, field)
    if not rows:
        return []
    matrix = np.asarray([row["vector"] for row in rows], dtype=np.float32)
    if matrix.ndim != 2:
        raise ClusterError("the vector matrix is not two-dimensional")
    best = {}
    for start in range(0, len(rows), block):
        stop = min(start + block, len(rows))
        similarities = matrix[start:stop] @ matrix.T
        for local, left in enumerate(rows[start:stop]):
            number = start + local
            hits = np.flatnonzero(similarities[local] >= threshold)
            for other in hits:
                if other <= number or left["slug"] == rows[other]["slug"]:
                    continue
                edge = _edge_record(left, rows[other], similarities[local, other])
                key = (edge["a"], edge["b"])
                old = best.get(key)
                if (old is None or edge["similarity"] > old["similarity"]
                        or (edge["similarity"] == old["similarity"]
                            and _edge_tie_key(edge) < _edge_tie_key(old))):
                    best[key] = edge
            if len(best) > max_links:
                raise ClusterError("%s %s gives more than %d links; raise %s"
                                   % (field, threshold, max_links, field))
    answer = []
    for key in sorted(best):
        edge = best[key]
        answer.append({**edge, "similarity": round(edge["similarity"], 6)})
    return answer


class Union:
    def __init__(self):
        self.parent = {}

    def find(self, value):
        self.parent.setdefault(value, value)
        if self.parent[value] != value:
            self.parent[value] = self.find(self.parent[value])
        return self.parent[value]

    def join(self, left, right):
        left, right = self.find(left), self.find(right)
        if left != right:
            self.parent[max(left, right)] = min(left, right)


def combined_edges(edges_by_space):
    """Merge the evidence of each vector space by wine pair."""
    merged = {}
    for space in VECTOR_SPACES:
        for edge in edges_by_space.get(space) or []:
            key = (edge["a"], edge["b"])
            record = merged.setdefault(key, {"a": key[0], "b": key[1], "spaces": {}})
            record["spaces"][space] = {
                key: value for key, value in edge.items() if key not in ("a", "b")}
    out = []
    for key in sorted(merged):
        record = merged[key]
        record["by"] = [space for space in VECTOR_SPACES if space in record["spaces"]]
        out.append(record)
    return out


def space_edges(edges, space):
    return [{"a": edge["a"], "b": edge["b"], "by": [space],
             "spaces": {space: {key: value for key, value in edge.items()
                                if key not in ("a", "b")}}}
            for edge in edges]


def manual_links(edges, pairs, by=MANUAL):
    """Add the manual pairs to the normalized link records of one view (plan 62). `by` is
    `manual`, or `gtin` for the pairs of a shared GTIN (plan 64).

    A pair that has a link gets the value of `by` at the end of its list `by`. Another
    pair gets a new link with no vector evidence."""
    by_pair = {(edge["a"], edge["b"]): edge for edge in edges}
    for a, b in pairs:
        edge = by_pair.get((a, b))
        if edge is None:
            by_pair[(a, b)] = {"a": a, "b": b, "by": [by], "spaces": {}}
        elif by not in edge["by"]:
            edge["by"] = edge["by"] + [by]
    return [by_pair[key] for key in sorted(by_pair)]


def components(edges, view, min_size=MIN_CLUSTER_SIZE):
    """Build connected components from normalized link records. A component with fewer
    than `min_size` wines is not a cluster."""
    union = Union()
    for edge in edges:
        union.join(edge["a"], edge["b"])
    groups = collections.defaultdict(list)
    for slug in union.parent:
        groups[union.find(slug)].append(slug)
    clusters = []
    for members in groups.values():
        members = sorted(members)
        if len(members) < min_size:
            continue
        member_set = set(members)
        links = [edge for edge in edges
                 if edge["a"] in member_set and edge["b"] in member_set]
        signals = [space for space in VECTOR_SPACES
                   if any(space in edge["spaces"] for edge in links)]
        # `kind` keeps its vector meaning; a cluster of manual links alone is `manual`.
        kind = (signals[0] if len(signals) == 1 else "mixed") if signals else MANUAL
        # A cluster of GTIN links alone is `gtin` (plan 64).
        if not signals and not any(MANUAL in edge["by"] for edge in links):
            kind = GTIN
        if any(MANUAL in edge["by"] for edge in links):
            signals.append(MANUAL)
        if any(GTIN in edge["by"] for edge in links):
            signals.append(GTIN)
        clusters.append({
            "key": cluster_key(members),
            "kind": kind,
            "size": len(members),
            "signals": signals,
            "slugs": members,
            "links": links,
        })
    clusters.sort(key=lambda cluster: (-cluster["size"], cluster["slugs"][0]))
    for number, cluster in enumerate(clusters, 1):
        cluster["id"] = "c%03d" % number
    sizes = collections.Counter(cluster["size"] for cluster in clusters)
    return {
        "view": view,
        "counts": {
            "links": len(edges), "clusters": len(clusters),
            "wines_in_clusters": sum(cluster["size"] for cluster in clusters),
            "largest": max((cluster["size"] for cluster in clusters), default=0),
            "sizes": {str(size): sizes[size] for size in sorted(sizes)},
        },
        "clusters": clusters,
    }


def build(ctx, vectors, full_threshold=DEFAULT_THRESHOLD,
          label_threshold=DEFAULT_THRESHOLD, max_links=MAX_LINKS,
          max_cluster_size=MAX_CLUSTER_SIZE, min_cluster_size=MIN_CLUSTER_SIZE):
    """Build one JSON artifact from a context and its vector matrix."""
    full_threshold = validate_threshold(full_threshold, "full_threshold")
    label_threshold = validate_threshold(label_threshold, "label_threshold")
    rows = current_rows(ctx, vectors)
    raw = {
        "full": similarity_edges(rows["full"], full_threshold, max_links=max_links,
                                 field="full_threshold"),
        "label": similarity_edges(rows["label"], label_threshold, max_links=max_links,
                                  field="label_threshold"),
    }
    pairs = ctx.get("similar") or []
    normalized = {space: manual_links(space_edges(raw[space], space), pairs)
                  for space in VECTOR_SPACES}
    normalized["combined"] = manual_links(combined_edges(raw), pairs)
    gtin = ctx.get("gtin") or []
    normalized = {space: manual_links(normalized[space], gtin, GTIN) for space in SPACES}
    spaces = {space: components(normalized[space], space, min_cluster_size)
              for space in SPACES}
    for space in SPACES:
        largest = spaces[space]["counts"]["largest"]
        if largest > max_cluster_size:
            raise ClusterError("the %s space has a cluster of %d wines, more than %d; "
                               "raise the threshold" % (space, largest, max_cluster_size))
    return {
        "version": VERSION,
        "embedding": ctx["embedding"].name,
        "built_at": now(),
        "input_hash": ctx["input_hash"],
        "inputs": {
            "index_file": embeddings.INDEX,
            "vectors_file": ctx["index"].get("vectors_file"),
            "updated_at": ctx["index"].get("updated_at"),
            "dim": ctx["index"].get("dim"),
            "items": len(ctx["items"]),
            "indexed_items": len(ctx["index"].get("items") or []),
            "assignments": len(ctx["assignments"]),
            "status": ctx["status_counts"],
            "space_rows": {space: len(rows[space]) for space in VECTOR_SPACES},
        },
        "settings": {"full_threshold": full_threshold,
                     "label_threshold": label_threshold,
                     "min_cluster_size": min_cluster_size},
        "spaces": spaces,
    }


def build_to_directory(settings, name, full_threshold=None, label_threshold=None):
    """Build and atomically store `clusters.json` for one configured embedding.

    The thresholds and the limits come from `config_values`. A threshold that is not
    None replaces the value of `config.yaml`."""
    values = config_values(settings)
    if full_threshold is not None:
        values["full_threshold"] = full_threshold
    if label_threshold is not None:
        values["label_threshold"] = label_threshold
    ctx = context(settings, name)
    directory = ctx["directory"]
    if embeddings.running_pid(directory):
        raise Busy("the embedding build of %s runs" % name)
    with file_lock(directory, BUILD_LOCK, "the cluster build of %s runs" % name):
        # Read the context again after the lock. A build can have finished between the
        # first check and the lock.
        ctx = context(settings, name)
        if embeddings.running_pid(directory):
            raise Busy("the embedding build of %s runs" % name)
        try:
            vectors = embeddings.read_vectors(directory, ctx["index"])
        except (OSError, ValueError) as exc:
            raise ClusterError("cannot read the vectors of %s: %s" % (name, exc)) from exc
        if vectors is None:
            raise ClusterError("embedding %s has no vector file" % name)
        artifact = build(ctx, vectors, values["full_threshold"], values["label_threshold"],
                         values["max_links"], values["max_cluster_size"],
                         values["min_cluster_size"])
        write_json(os.path.join(directory, CLUSTERS_FILE), artifact)
        return artifact


def load_artifact(directory):
    return read_json(os.path.join(directory, CLUSTERS_FILE))


def artifact_status(settings, name):
    """Return artifact metadata and its current input status."""
    embedding = _settings_entry(settings, name)
    directory = embeddings.entry_dir(settings.db_path, embedding.name)
    artifact = load_artifact(directory)
    if artifact is None:
        return {"exists": False, "directory": directory, "file":
                os.path.join(directory, CLUSTERS_FILE), "stale": None}
    answer = {
        "exists": True, "directory": directory,
        "file": os.path.join(directory, CLUSTERS_FILE),
        "built_at": artifact.get("built_at"), "input_hash": artifact.get("input_hash"),
        "settings": artifact.get("settings") or {},
    }
    try:
        ctx = context(settings, name)
    except ClusterError as exc:
        answer.update(stale=True, current_error=str(exc), current_input_hash=None)
    else:
        answer.update(stale=artifact.get("input_hash") != ctx["input_hash"],
                      current_error=None, current_input_hash=ctx["input_hash"],
                      current_status=ctx["status_counts"])
    return answer


def load_notes(directory):
    data = read_json(os.path.join(directory, NOTES_FILE), default={}) or {}
    notes = data.get("notes") or {}
    if not isinstance(notes, dict):
        raise ClusterError("%s MUST hold a `notes` object"
                           % os.path.join(directory, NOTES_FILE))
    return data, notes


def note_for(cluster, notes):
    """Return the exact or best-overlap note of one current cluster."""
    exact = notes.get(cluster["key"])
    if isinstance(exact, dict):
        return {**exact, "from_key": cluster["key"], "inherited": False}
    members = set(cluster["slugs"])
    candidates = []
    for key, note in notes.items():
        if not isinstance(note, dict):
            continue
        old = set(note.get("slugs") or [])
        overlap = len(members & old)
        if overlap:
            candidates.append((overlap, overlap / max(1, len(old)),
                               str(note.get("updated_at") or ""), key, note))
    if not candidates:
        return {"text": "", "from_key": None, "inherited": False}
    _, _, _, key, note = max(candidates)
    return {**note, "from_key": key, "inherited": True}


def set_note(directory, cluster, text):
    """Write or clear the note of one current cluster."""
    if not isinstance(text, str):
        raise ClusterError("text MUST be a string")
    if len(text) > MAX_NOTE:
        raise ClusterError("text MUST have at most %d characters" % MAX_NOTE)
    with file_lock(directory, NOTES_LOCK, "another cluster note write runs"):
        data, notes = load_notes(directory)
        stamp = now()
        notes[cluster["key"]] = {
            "slugs": list(cluster["slugs"]), "text": text, "updated_at": stamp}
        output = {
            "version": VERSION,
            "updated_at": stamp,
            "note": "Reviewer notes of the embedding-dependent clusters.",
            "notes": notes,
        }
        write_json(os.path.join(directory, NOTES_FILE), output)
    return note_for(cluster, notes)


def load_rules(directory):
    data = read_json(os.path.join(directory, RULES_FILE), default={}) or {}
    spaces = data.get("spaces") or {}
    if isinstance(spaces, dict):
        return {space: rules for space, rules in spaces.items()
                if space in VECTOR_SPACES and isinstance(rules, dict)}
    return {}


def cluster_in(artifact, space, key):
    if space not in SPACES:
        raise ClusterError("space MUST be one of: %s" % ", ".join(SPACES))
    for cluster in ((artifact.get("spaces") or {}).get(space) or {}).get("clusters") or []:
        if cluster.get("key") == key:
            return cluster
    return None


def _cut_url(item):
    """Return the URL of the segmented file of one item, or None.

    The steps `segment` and `remove_background` of a view give this file: the package or
    the label cut of `image_derivative`, with its transparent background. The step
    `white_background` puts it on white for the model, so the prepared image has no
    transparency. The page draws the cut (owner message of 2026-09-26T09:51:00+0300). An
    item with no `segment` step, such as a close-up, has no cut."""
    cut = (item or {}).get("cut")
    if not cut or not (item.get("steps") or []):
        return None
    path = cut["path"]
    return "/images/%s/%s" % (os.path.basename(os.path.dirname(path)), os.path.basename(path))


def _current_images(ctx):
    """Return wine -> current prepared images for the page."""
    assignments = collections.defaultdict(lambda: collections.defaultdict(set))
    for assignment in ctx["assignments"]:
        key = (assignment["source_sha256"], assignment["view"])
        assignments[key][assignment["slug"]].add(assignment["image_type"])
    out = collections.defaultdict(list)
    for key, (state, record) in ctx["status"].items():
        if state != "current" or not isinstance(record, dict):
            continue
        digest, view = key
        for slug, image_types in assignments[key].items():
            out[slug].append({
                "view": view, "source_sha256": digest,
                "image_types": sorted(image_types),
                "prepared_url": _image_url(
                    ctx["embedding"].name, digest, view, record["embedding_hash"]),
                "cut_url": _cut_url(ctx["items"].get(key)),
                "original_url": ctx["sources"][digest]["url"],
            })
    for images in out.values():
        images.sort(key=lambda image: (
            VECTOR_SPACES.index(image["view"]), image["image_types"],
            image["source_sha256"]))
    return out


def detail(settings, name):
    """Return one artifact with current cards, images, notes, rules, and stale status."""
    embedding = _settings_entry(settings, name)
    directory = embeddings.entry_dir(settings.db_path, embedding.name)
    artifact = load_artifact(directory)
    if artifact is None:
        return {"embedding": embedding.summary(), "status": artifact_status(settings, name),
                "artifact": None, "cards": {}}
    try:
        ctx = context(settings, name)
    except ClusterError:
        # Keep a stored artifact readable when its current index is absent or invalid.
        # `artifact_status` gives the exact current error to the page.
        ctx = None
    notes_data, notes = load_notes(directory)
    rules = load_rules(directory)
    wanted = {slug for space in (artifact.get("spaces") or {}).values()
              for cluster in space.get("clusters") or [] for slug in cluster.get("slugs") or []}
    images = _current_images(ctx) if ctx is not None else {}
    cards = {}
    for slug in sorted(wanted):
        card = dict((ctx["catalog"].get(slug) if ctx is not None else None)
                    or {"wine_slug": slug})
        card["slug"] = card.pop("wine_slug", slug)
        card["images"] = images.get(slug, [])
        cards[slug] = card
    # Add file-backed review values without changing the stored cluster artifact.
    shown = json.loads(json.dumps(artifact))
    for space_name, space in (shown.get("spaces") or {}).items():
        for cluster in space.get("clusters") or []:
            cluster["note"] = note_for(cluster, notes)
            rule = (rules.get(RULE_SPACE_OF.get(space_name)) or {}).get(cluster["key"])
            if isinstance(rule, dict):
                # A rule that stored its note is stale when the note changed (plan 45).
                note_changed = "note" in rule and (rule.get("note") or "") != (
                    cluster["note"].get("text") or "")
                cluster["rule"] = {**rule, "stale": note_changed or rule.get(
                    "input_hash") != artifact.get("input_hash")}
            else:
                cluster["rule"] = None
    return {
        "embedding": embedding.summary(),
        "status": artifact_status(settings, name),
        "artifact": shown,
        "cards": cards,
        "notes_updated_at": notes_data.get("updated_at"),
    }
