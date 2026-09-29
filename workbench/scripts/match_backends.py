"""Match backends for `scripts/match_run.py`.

A backend takes one photo and answers a ranked list of candidate slugs. The
photo goes as `multipart/form-data`, in the field that `field` names. This is
the form that the jury harness uses, so one backend definition serves both the
jury contract and the official API.

`backends.yaml` defines every backend. Read `docs/match-runner.md` for the keys.

The answer of a backend is parsed into a list of `{"slug": str, "score": float
or None, "rank": int}`. A backend that states no score gives `score: None`. A
missing score is never read as a score of zero.

The shape `group` is the answer of `POST /v1/group/match` of svoe-vino-matcher. It is
for the lab pipelines of the backend `svoe-vino-ru` alone (plan 83): `ask` then returns a
sixth value, the group record of the photo, and `pipeline/benchmark.py` keeps it. Read
workbench/docs/plans/83_matcher-api-pipelines.md.
"""
import datetime as dt
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

import yaml

# The keys that may hold the list of candidates in an answer.
LIST_KEYS = ("candidates", "data", "items", "results", "wines", "matches")
# The keys that may hold the score of one candidate.
SCORE_KEYS = ("score", "confidence", "similarity", "sim", "probability")

SHAPES = ("auto", "slug-object", "slug-array", "candidates", "group")
# The shape of `POST /v1/group/match`. `scripts/match_run.py` does not keep the group
# record, so `backends.yaml` refuses this shape.
GROUP_SHAPE = "group"


class BackendError(Exception):
    """The definition of a backend is wrong. The run MUST NOT start."""


def load_backends(path):
    """Return id -> spec. The file MUST hold a list under the key `backends`."""
    if not os.path.exists(path):
        raise BackendError("no backends file: %s" % path)
    with open(path, encoding="utf-8") as fh:
        blob = yaml.safe_load(fh) or {}
    items = blob.get("backends")
    if not isinstance(items, list) or not items:
        raise BackendError("%s holds no `backends:` list" % path)
    out = {}
    for item in items:
        if not isinstance(item, dict) or not item.get("id"):
            raise BackendError("every backend MUST hold an `id`")
        spec = dict(item)
        bid = str(spec["id"])
        if bid in out:
            raise BackendError("two backends hold the id %r" % bid)
        if not spec.get("url"):
            raise BackendError("backend %r holds no `url`" % bid)
        shape = str(spec.get("response") or "auto")
        if shape not in SHAPES:
            raise BackendError("backend %r: response MUST be one of %s"
                               % (bid, ", ".join(SHAPES)))
        if shape == GROUP_SHAPE:
            raise BackendError("backend %r: the response shape group is for the lab "
                               "pipelines of config.yaml alone" % bid)
        out[bid] = spec
    return out


def redact(spec):
    """Return the spec without a secret, for `run.json`.

    A header value that names an environment variable keeps the name. Any other
    header value is replaced, because it may be a token.
    """
    out = json.loads(json.dumps(spec, default=str))
    headers = out.get("headers")
    if isinstance(headers, dict):
        for name, value in list(headers.items()):
            text = str(value)
            headers[name] = text if text.startswith("env:") else "(redacted)"
    return out


def _score_of(rec):
    for key in SCORE_KEYS:
        if key in rec:
            try:
                return float(rec[key])
            except (TypeError, ValueError):
                return None
    return None


def _slug_of(rec):
    if isinstance(rec, str):
        return rec
    if isinstance(rec, dict):
        value = rec.get("slug")
        return value if isinstance(value, str) and value else None
    return None


def parse_answer(body, shape="auto"):
    """Return the ranked candidates of one answer body.

    Accepted shapes:

    - `{"slug": "..."}`                          the jury contract
    - `[{"slug": "..."}, ...]`                   the answer of the present API
    - `{"data": [...]}`, `{"items": [...]}`      a wrapped list
    - `{"candidates": [{"slug": ..., "score": ...}]}`  a list with a score

    A shape other than `auto` refuses the other forms, so a backend that changes
    its answer format fails loudly.
    """
    records = None
    if isinstance(body, dict):
        if shape in ("auto", "slug-object") and isinstance(body.get("slug"), str):
            records = [body]
        if records is None and shape in ("auto", "candidates", "slug-array"):
            for key in LIST_KEYS:
                value = body.get(key)
                if isinstance(value, list):
                    records = value
                    break
    elif isinstance(body, list) and shape in ("auto", "slug-array", "candidates"):
        records = body

    if records is None:
        raise ValueError("the answer holds no slug")

    out = []
    for rec in records:
        slug = _slug_of(rec)
        if not slug:
            continue
        item = {"slug": slug,
                "score": _score_of(rec) if isinstance(rec, dict) else None,
                "rank": len(out) + 1}
        # The reason of a re-rank, when the backend was asked with `explain=1`.
        # The report of a re-rank reads it from results.jsonl.
        if isinstance(rec, dict) and rec.get("explain") is not None:
            item["explain"] = rec["explain"]
        out.append(item)
    if not out:
        raise ValueError("the answer holds no slug")
    return out


def group_record(body):
    """Return the group record of one answer of `POST /v1/group/match`.

    The candidates of a bottle are its list `candidates`, or `[match]` for a matcher
    with no parameter `k`. The record keeps no mask, no preview, and no wine card. Raise
    ValueError for an answer that is not a group answer.
    """
    if not isinstance(body, dict) or not isinstance(body.get("bottles"), list):
        raise ValueError("the answer holds no list bottles")
    image = body.get("image") if isinstance(body.get("image"), dict) else {}
    bottles = []
    for n, bottle in enumerate(body["bottles"], 1):
        if not isinstance(bottle, dict):
            raise ValueError("bottle %d is not an object" % n)
        raw = bottle.get("candidates")
        if not isinstance(raw, list):
            raw = [bottle["match"]] if isinstance(bottle.get("match"), dict) else []
        cands = []
        for rec in raw:
            slug = _slug_of(rec)
            if slug:
                cands.append({"rank": len(cands) + 1, "slug": slug,
                              "score": _score_of(rec) if isinstance(rec, dict) else None})
        box = bottle.get("box")
        if not (isinstance(box, list) and len(box) == 4 and all(
                isinstance(v, (int, float)) and not isinstance(v, bool) for v in box)):
            box = None
        bottles.append({
            "n": n, "id": bottle.get("id"),
            "segmentation_score": bottle.get("segmentation_score"),
            "box": [float(v) for v in box] if box else None,
            "candidates": cands,
        })
    return {"image": {"width": image.get("width"), "height": image.get("height")},
            "detected_count": body.get("detected_count"),
            "truncated": body.get("truncated"), "bottles": bottles}


def group_ranked(record):
    """Return the ranked candidates of one group record: the first candidate of each
    bottle, the highest score first. Bottles with the same score keep the order of the
    answer. A slug that comes again is dropped."""
    firsts = [b["candidates"][0] for b in record["bottles"] if b["candidates"]]
    # `sorted` is stable: the bottles with the same score keep the order of the answer.
    firsts = sorted(firsts, key=lambda c: -c["score"] if c["score"] is not None
                    else float("inf"))
    ranked, seen = [], set()
    for cand in firsts:
        if cand["slug"] not in seen:
            seen.add(cand["slug"])
            ranked.append({"slug": cand["slug"], "score": cand["score"],
                           "rank": len(ranked) + 1})
    return ranked


def _multipart(path, field):
    """Return the body and the content type of one multipart form."""
    with open(path, "rb") as fh:
        data = fh.read()
    boundary = "----matchrun%s" % uuid.uuid4().hex
    name = os.path.basename(path)
    head = ("--%s\r\n"
            "Content-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\n"
            "Content-Type: application/octet-stream\r\n\r\n" % (boundary, field, name))
    body = head.encode() + data + ("\r\n--%s--\r\n" % boundary).encode()
    return body, "multipart/form-data; boundary=%s" % boundary


class HttpMultipartBackend:
    """One recognizer behind an HTTP endpoint."""

    def __init__(self, spec):
        self.spec = spec
        self.id = str(spec["id"])
        self.label = str(spec.get("label") or self.id)
        self.field = str(spec.get("field") or "image")
        self.shape = str(spec.get("response") or "auto")
        self.timeout = float(spec.get("timeout_s") or 30)
        self.top_k = max(1, int(spec.get("top_k") or 1))
        # How many requests this backend takes at the same time. `--workers` on the
        # command line wins over this value.
        self.workers = max(1, int(spec.get("workers") or 1))
        self.url = self._url(spec)
        self.headers = self._headers(spec)

    @staticmethod
    def _url(spec):
        url = str(spec["url"])
        query = spec.get("query")
        if isinstance(query, dict) and query:
            join = "&" if urllib.parse.urlsplit(url).query else "?"
            url = url + join + urllib.parse.urlencode(
                {k: str(v) for k, v in query.items()})
        return url

    @staticmethod
    def _headers(spec):
        """Read the headers. A value `env:NAME` comes from the environment."""
        out = {"Accept": "application/json"}
        for name, value in (spec.get("headers") or {}).items():
            text = str(value)
            if text.startswith("env:"):
                var = text[len("env:"):]
                got = os.environ.get(var)
                if not got:
                    raise BackendError(
                        "backend %s: header %s names the environment variable %s, "
                        "and the variable is empty" % (spec.get("id"), name, var))
                out[str(name)] = got
            else:
                out[str(name)] = text
        return out

    def ask(self, path):
        """Send one photo. Return `(candidates, latency_ms, http_status, error)`.

        The function never raises for a failure of the backend. A failure gives
        an empty candidate list and a text in `error`, and the run goes on.
        The shape `group` returns two more values: no step trace (None), and the group
        record of `group_record`, also for an answer with no match (plan 83).
        """
        body, ctype = _multipart(path, self.field)
        headers = dict(self.headers)
        headers["Content-Type"] = ctype
        req = urllib.request.Request(self.url, data=body, headers=headers)
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
                status = resp.getcode()
        except urllib.error.HTTPError as exc:
            return [], self._ms(t0), exc.code, "HTTP %s" % exc.code
        except Exception as exc:  # noqa: BLE001
            return [], self._ms(t0), None, "%s: %s" % (type(exc).__name__, exc)
        ms = self._ms(t0)
        try:
            answer = json.loads(raw.decode("utf-8", "replace"))
        except ValueError:
            return [], ms, status, "the answer is not JSON"
        if self.shape == GROUP_SHAPE:
            try:
                record = group_record(answer)
            except ValueError as exc:
                return [], ms, status, str(exc), None, None
            cands = group_ranked(record)
            if not cands:
                return [], ms, status, "the answer holds no bottle with a match", None, record
            return cands[:self.top_k], ms, status, None, None, record
        try:
            cands = parse_answer(answer, self.shape)
        except ValueError as exc:
            return [], ms, status, str(exc)
        return cands[:self.top_k], ms, status, None

    @staticmethod
    def _ms(t0):
        return int(round((time.perf_counter() - t0) * 1000))


def build_backend(path, backend_id):
    """Return the backend of `backend_id` from `backends.yaml`."""
    specs = load_backends(path)
    if backend_id not in specs:
        raise BackendError("unknown backend %r. The file holds: %s"
                           % (backend_id, ", ".join(sorted(specs))))
    return HttpMultipartBackend(specs[backend_id])


# The pipeline kinds of svoe-vino-matcher that own no index. Each names the
# pipeline it sits on, under one of these keys, so the walk below reaches the
# `embed` pipeline that holds the vectors.
EMBED_REF_KEYS = ("embed", "base")


def embeddings_of(backend, timeout_s=10):
    """Ask the backend when the embeddings it answers with were last built.

    A run states which vectors produced it. Without this, two runs of the same
    backend id are indistinguishable although a rebuild moved every vector
    between them.

    The answer is always a dictionary, never a bare timestamp or a blank. When
    the age cannot be read, `built_at` is None and `reason` says why, because
    "the backend reports no index" and "the probe failed" MUST NOT look the
    same. A `kind: remote` backend, such as the official recognizer, owns no
    index and is the ordinary case of an unknown age, not a fault.
    """
    if backend is None or not getattr(backend, "url", ""):
        return {"built_at": None, "reason": "the run has no HTTP backend"}

    import urllib.error
    import urllib.parse
    import urllib.request

    parts = urllib.parse.urlsplit(backend.url)
    base = "%s://%s" % (parts.scheme, parts.netloc)
    # `/v1/pipelines/<name>/predict` names the pipeline. `/v1/eval/predict`
    # does not, and answers with the default pipeline of the server.
    segments = [s for s in parts.path.split("/") if s]
    wanted = ""
    if len(segments) >= 3 and segments[:2] == ["v1", "pipelines"]:
        wanted = segments[2]
    query = urllib.parse.parse_qs(parts.query or "")
    if query.get("pipeline"):
        wanted = query["pipeline"][0]

    try:
        req = urllib.request.Request(base + "/v1/info",
                                     headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            info = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"built_at": None,
                "reason": "%s/v1/info did not answer: %s" % (base, exc)}

    by_name = {p.get("name"): p for p in (info.get("pipelines") or [])
               if isinstance(p, dict)}
    if not wanted:
        wanted = info.get("default_pipeline") or ""
    if wanted not in by_name:
        return {"built_at": None,
                "reason": "the server does not report a pipeline `%s`" % wanted}

    # The backend MAY pin another index with `?index=`. The run then answered
    # from THAT file, so the age of the pipeline's own index would be the wrong
    # provenance: two runs that read different vectors would record the same
    # age. `available_indexes` of the pipeline carries the build time of every
    # file the server offers.
    pinned = (query.get("index") or query.get("index_file") or [""])[0].strip()
    if pinned:
        entry = by_name[wanted]
        if not entry.get("supports_index_override"):
            return {"built_at": None, "pipeline": wanted, "index_file": pinned,
                    "reason": "the backend pins index `%s` but pipeline `%s` "
                              "owns no index" % (pinned, wanted)}
        stem = pinned[:-4] if pinned.endswith(".npz") else pinned
        for item in (entry.get("available_indexes") or []):
            name = str(item.get("index_file") or "")
            if name[:-4] != stem and name != stem:
                continue
            stamp = item.get("built_at_unix")
            out = {"index_file": name, "built_at_unix": stamp, "source": "meta",
                   "pipeline": wanted, "pinned_by_backend": True}
            out["built_at"] = (
                dt.datetime.fromtimestamp(stamp).astimezone().isoformat(
                    timespec="seconds") if stamp else None)
            if stamp is None:
                out["source"] = None
                out["reason"] = "`%s` has no build time in its sidecar" % name
            return out
        return {"built_at": None, "pipeline": wanted, "index_file": pinned,
                "reason": "the backend pins index `%s`, which pipeline `%s` "
                          "does not offer" % (pinned, wanted)}

    # Walk from the answering pipeline to the one that owns the index. An
    # ensemble reads several, so it reports every member instead of one age.
    seen, name = [], wanted
    while name and name not in seen:
        seen.append(name)
        entry = by_name.get(name) or {}
        if entry.get("embeddings"):
            out = dict(entry["embeddings"])
            out["pipeline"] = name
            if name != wanted:
                out["answering_pipeline"] = wanted
            return out
        if entry.get("members"):
            members = []
            for m in entry["members"]:
                ref = (m or {}).get("pipeline")
                block = (by_name.get(ref) or {}).get("embeddings")
                if block:
                    members.append({**block, "pipeline": ref,
                                    "weight": (m or {}).get("weight")})
            if members:
                return {"built_at": None, "pipeline": wanted,
                        "reason": "an ensemble reads the index of every member",
                        "members": members}
        nxt = ""
        for key in EMBED_REF_KEYS:
            ref = entry.get(key)
            if isinstance(ref, dict):
                ref = ref.get("pipeline")
            if ref:
                nxt = str(ref)
                break
        name = nxt
    return {"built_at": None, "pipeline": wanted,
            "reason": "pipeline `%s` reports no index" % wanted}
