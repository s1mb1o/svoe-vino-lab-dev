"""Match backends for `scripts/match_run.py`.

A backend takes one photo and answers a ranked list of candidate slugs. The
photo goes as `multipart/form-data`, in the field that `field` names. This is
the form that the jury harness uses, so one backend definition serves both the
jury contract and the official API.

`backends.yaml` defines every backend. Read `docs/match-runner.md` for the keys.

The answer of a backend is parsed into a list of `{"slug": str, "score": float
or None, "rank": int}`. A backend that states no score gives `score: None`. A
missing score is never read as a score of zero.
"""
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

SHAPES = ("auto", "slug-object", "slug-array", "candidates")


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
        out.append({"slug": slug,
                    "score": _score_of(rec) if isinstance(rec, dict) else None,
                    "rank": len(out) + 1})
    if not out:
        raise ValueError("the answer holds no slug")
    return out


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
