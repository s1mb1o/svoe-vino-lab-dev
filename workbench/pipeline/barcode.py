"""The barcode step of the lab pipelines: the key `barcode` of a pipeline of the backend
`embedding` (plan 42; owner message of 2026-09-26T07:22:10+0300, answers of 07:27:08).

The step decodes the test photo as it is, before the views of the pipeline. It looks up
each decoded code in the table `wine_code` of the Active wines. A hit answers the photo
with each wine of the code at score 1.0, in slug order, and the embedding does not run. A
miss asks the embedding backend, and its answer does not change.

Plan 58 (owner message of 2026-09-26T23:54:53+0300, answers of 23:59:00) adds the shared
codes. A shared code is a GTIN or a QR URL of 2 or more Active wines. Only a unique code
gives the fast exit above. A shared QR URL never decides the answer: the annotation can
miss other wines of the same URL, so the normal match runs. A unique code wins over a
shared GTIN.

Plan 64 (owner message of 2026-09-27T17:12:18+0300, answers of 17:16:05 and 19:28:52)
changes the shared GTIN. The embedding ranks every wine, and the wines of the GTIN go
first (`first`). The other wines stay below them. The cluster re-rank compares only the
wines of the GTIN (`cluster_rerank.py`).

`Decoder.scan_file` stores decoded scan stages in `data/cache/barcode/`. A cache hit
repeats the wine lookup. An incomplete scan resumes when no stored code gives a unique
hit. The cache key includes the source bytes, options, library versions, and scan
revision. `model_cache.READ` controls cache reads. Decoder failures are not stored.

The decoder is a copy of `svoe-vino-matcher/svm/pipelines/barcode.py`. It uses zxing-cpp
2.3.0; zxing-cpp 3.1.1 can stall on an excise mark beside an EAN. It scans the whole photo
first, with two binarizers. When the whole photo gives no hit, it scans overlapping tiles
at two scales. The differences from the matcher:
- The lookup reads `wine_code` (`codes.py`), not `code-map.json`. A decoded product code
  becomes its GTIN-14 with `codes.clean_gtin`, and a QR text its normal URL with
  `codes.clean_qr_url`. A value that is not valid for its kind gives no lookup.
- The formats have no `UPCE`: zxing-cpp gives the 8 compressed digits of a UPC-E, and
  these are not a GTIN.
- There is no OpenCV fallback. The control of the matcher read 0 of 3 EAN-13 with OpenCV
  (`svoe-vino-matcher/docs/barcode-decoder-measurement.md`), and zxing-cpp reads QR.

zxing-cpp is a package of `requirements-local.txt`. `Decoder` imports it, so the lab
server can check the options with no zxing-cpp. zxing-cpp 2.3.0 has no wheel for Python
3.14; install it with `pip install --no-binary zxing-cpp zxing-cpp==2.3.0`.
"""
import io
import math
import threading
import time
from contextlib import closing
from importlib.metadata import version

from PIL import Image, __version__ as PILLOW_VERSION

import codes
import derive
import embeddings
import model_cache
from embeddings import ConfigError

# The zxing-cpp formats of a product code that can hold a GTIN.
FORMATS = ("EAN13", "EAN8", "UPCA", "Code128")
QR_FORMAT = "QRCode"
# option -> default. The defaults are the defaults of the matcher, less `UPCE`.
DEFAULTS = {"formats": list(FORMATS), "qr": True, "tile_scan": True, "max_side": 1600,
            "upscale": False, "code128_gtin_only": False}
MIN_SIDE, MAX_SIDE = 64, 8192
ENGINE = "zxing-cpp"
CACHE_REVISION = 1
# The kind of a decoded code -> the kind of `wine_code`.
LOOKUP_KINDS = {"barcode": "gtin", "qr_code": "qr_url"}


def check_options(raw):
    """Check the key `barcode` of a pipeline. Return the options with each default filled
    in. Raise ConfigError."""
    if not isinstance(raw, dict):
        raise ConfigError("barcode MUST be a mapping of options; `{}` takes the defaults")
    unknown = sorted(set(raw) - set(DEFAULTS))
    if unknown:
        raise ConfigError("barcode: unknown option %s; use %s"
                          % (", ".join(unknown), ", ".join(DEFAULTS)))
    options = dict(DEFAULTS, **raw)
    formats = options["formats"]
    if (not isinstance(formats, list) or not formats
            or not all(isinstance(name, str) for name in formats)):
        raise ConfigError("barcode: formats MUST be a list with at least one format")
    other = sorted(set(formats) - set(FORMATS))
    if other:
        raise ConfigError("barcode: unknown format %s; use %s"
                          % (", ".join(other), ", ".join(FORMATS)))
    if len(set(formats)) != len(formats):
        raise ConfigError("barcode: a format MAY occur one time")
    options["formats"] = list(formats)
    for key in ("qr", "tile_scan", "upscale", "code128_gtin_only"):
        if not isinstance(options[key], bool):
            raise ConfigError("barcode: %s MUST be true or false" % key)
    side = options["max_side"]
    if isinstance(side, bool) or not isinstance(side, int) or not MIN_SIDE <= side <= MAX_SIDE:
        raise ConfigError("barcode: max_side MUST be an integer from %d to %d"
                          % (MIN_SIDE, MAX_SIDE))
    return options


def is_gtin13(value):
    """Return True for 13 digits with a valid EAN-13 check digit."""
    if len(value) != 13 or not value.isascii() or not value.isdigit():
        return False
    return codes.check_digit(value[:12]) == int(value[12])


class CodeLookup:
    """The values of `wine_code` of the Active wines: (kind, value) -> the sorted slugs."""

    def __init__(self, values):
        self.values = values

    @classmethod
    def load(cls, db_path):
        """Read `wine_code` of the Active wines. Raise ConfigError and sqlite3.Error."""
        values = {}
        with closing(embeddings.open_database(db_path)) as conn:
            rows = conn.execute(
                "SELECT c.kind, c.value, c.wine_slug FROM wine_code c "
                "JOIN wine_catalog w ON w.wine_slug = c.wine_slug "
                "WHERE w.state = 'Active' AND c.kind IN ('gtin', 'qr_url')").fetchall()
        for kind, value, slug in rows:
            values.setdefault((kind, value), set()).add(slug)
        return cls({key: sorted(slugs) for key, slugs in values.items()})

    @property
    def counts(self):
        """Return kind -> the count of the values of that kind."""
        out = {kind: 0 for kind in LOOKUP_KINDS.values()}
        for kind, _value in self.values:
            out[kind] += 1
        return out

    @staticmethod
    def key(code):
        """Return the (kind, value) of `wine_code` for one decoded code, or None when the
        text is not a valid value of its kind."""
        kind = LOOKUP_KINDS[code["kind"]]
        try:
            return kind, codes.clean(kind, code["text"])
        except codes.CodeError:
            return None

    def hits(self, found):
        """Return the hit of each decoded code that `wine_code` holds, in the order of
        `found`, one hit for each stored value. A hit is a dict: `source` (the kind of
        `wine_code`), `code` (the stored value), `read` (the text as decoded), `format`,
        and `slugs`."""
        out, seen = [], set()
        for code in found:
            key = self.key(code)
            slugs = self.values.get(key) if key else None
            if slugs and key not in seen:
                seen.add(key)
                out.append({"source": key[0], "code": key[1], "read": code["text"],
                            "format": code["format"], "slugs": list(slugs)})
        return out

    def find(self, found):
        """Return the hit that decides the answer (plan 58), or None: the first hit of a
        unique code, else the first hit of a shared GTIN. A shared QR URL never decides."""
        hits = self.hits(found)
        for hit in hits:
            if is_unique(hit):
                return hit
        return next((hit for hit in hits if hit["source"] == "gtin"), None)


def is_unique(hit):
    """Return True for the hit of a code of one wine."""
    return hit is not None and len(hit["slugs"]) == 1


def shared_qr(hits):
    """Return the hits of the QR URLs of 2 or more wines."""
    return [hit for hit in hits if hit["source"] == "qr_url" and not is_unique(hit)]


def _dedupe(found):
    out, seen = [], set()
    for code in found:
        key = (code["kind"], code["text"])
        if key not in seen:
            seen.add(key)
            out.append(code)
    return out


def tiles(image):
    """Yield overlapping tiles at two scales."""
    w, h = image.size
    for count in (3, 5):
        tw = max(96, math.ceil(2 * w / (count + 1)))
        th = max(96, math.ceil(2 * h / (count + 1)))
        xs = [round(i * (w - tw) / (count - 1)) for i in range(count)]
        ys = [round(i * (h - th) / (count - 1)) for i in range(count)]
        for y in ys:
            for x in xs:
                yield image.crop((x, y, min(w, x + tw), min(h, y + th)))


class Decoder:
    """The zxing-cpp decoder of one set of options. Raise ConfigError when this Python has
    no zxing-cpp."""

    def __init__(self, options):
        try:
            import zxingcpp
        except ModuleNotFoundError:
            raise ConfigError("the key `barcode` needs zxing-cpp 2.3.0 in this Python; "
                              "install requirements-local.txt into embedding_python")
        self.zxing = zxingcpp
        self.options = options
        self.version = version(ENGINE)
        self._last = threading.local()
        names = list(options["formats"]) + ([QR_FORMAT] if options["qr"] else [])
        formats = getattr(zxingcpp.BarcodeFormat, names[0])
        for name in names[1:]:
            formats = formats | getattr(zxingcpp.BarcodeFormat, name)
        self.formats = formats
        self.binarizers = (zxingcpp.Binarizer.LocalAverage, zxingcpp.Binarizer.FixedThreshold)

    def read(self, image):
        """Return each code of one image: a list of `{"kind", "format", "text"}`."""
        out = []
        for binarizer in self.binarizers:
            try:
                results = self.zxing.read_barcodes(image, formats=self.formats,
                                                   try_downscale=False, binarizer=binarizer)
            except Exception:  # noqa: BLE001 - the matcher skips a binarizer that raises
                self._last.failed = True
                continue
            for result in results:
                text = str(result.text or "").strip()
                if not text:
                    continue
                name = str(result.format).rsplit(".", 1)[-1]
                if (self.options["code128_gtin_only"] and name == "Code128"
                        and not is_gtin13(text)):
                    continue
                kind = "qr_code" if "qr" in name.lower() else "barcode"
                out.append({"kind": kind, "format": name, "text": text})
        return out

    def scaled(self, image):
        """Return the image as the decoder sees it: RGB on white, with its long side scaled
        down to `max_side`, or up to it with `upscale`."""
        image = embeddings.on_white(image)
        w, h = image.size
        scale = self.options["max_side"] / float(max(w, h))
        if scale < 1.0:
            image = image.resize((max(1, int(w * scale)), max(1, int(h * scale))),
                                 Image.BICUBIC)
        elif scale > 1.0 and self.options["upscale"]:
            image = image.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
        return image

    def scan(self, image, lookup):
        """Return (each decoded code, the hit of `lookup` or None) of one opened photo.
        Only a unique code stops the tile scan (plan 58)."""
        return self._scan(image, lookup, [])

    def _scan(self, image, lookup, batches):
        """Reuse stored stages. Append each new stage before the wine lookup."""
        image = self.scaled(image)

        def read_stage(number, view):
            if number == len(batches):
                batches.append(self.read(view))
            return batches[number]

        found = list(read_stage(0, image))
        hit = lookup.find(_dedupe(found))
        if self.options["tile_scan"] and not is_unique(hit):
            for number, tile in enumerate(tiles(image), 1):
                found.extend(read_stage(number, tile))
                hit = lookup.find(_dedupe(found))
                if is_unique(hit):
                    break
        return _dedupe(found), hit

    def scan_file(self, path, lookup):
        """Return (codes, current hit, cached). Resume an incomplete cached scan when
        its codes no longer identify one wine. Never store catalogue matches."""
        started = time.perf_counter()
        with open(path, "rb") as source:
            data = source.read()
        fields = model_cache.request_fields(
            "local://barcode/scan", "barcode",
            {"revision": CACHE_REVISION, "engine": ENGINE, "version": self.version,
             "pillow": PILLOW_VERSION, "options": self.options}, "", [data])
        record = model_cache.lookup(fields)
        batches = record["answer"].get("batches") if (
            record is not None and isinstance(record["answer"], dict)) else None
        total = 35 if self.options["tile_scan"] else 1
        if not _valid_batches(batches, total):
            batches = []
        found, hit = [], None
        for batch in batches:
            found = _dedupe(found + batch)
            hit = lookup.find(found)
            if is_unique(hit):
                return found, hit, True
        if len(batches) == total:
            return found, hit, True
        image, _ = derive.open_image(io.BytesIO(data))
        self._last.failed = False
        found, hit = self._scan(image, lookup, batches)
        if not self._last.failed:
            model_cache.store(fields, {"batches": batches},
                              (time.perf_counter() - started) * 1000)
        return found, hit, False


def _valid_batches(batches, total):
    """Treat a malformed cache answer as a miss."""
    return (isinstance(batches, list) and 0 < len(batches) <= total
            and all(isinstance(batch, list) and all(
                isinstance(code, dict) and isinstance(code.get("kind"), str)
                and code["kind"] in LOOKUP_KINDS
                and isinstance(code.get("text"), str) and bool(code["text"])
                and isinstance(code.get("format"), str)
                for code in batch) for batch in batches))


def _ms(value):
    return round(value, 1)


def shift_trace(trace, step, offset):
    """Return the trace of an inner answer (plan 41) with `step` first and `offset` ms added
    to the `start_ms` of each inner step. A missing trace becomes an empty trace."""
    steps = []
    for inner in (trace or {}).get("steps") or ():
        inner = dict(inner)
        if isinstance(inner.get("start_ms"), (int, float)):
            inner["start_ms"] = _ms(inner["start_ms"] + offset)
        steps.append(inner)
    return dict(trace or {}, v=1, steps=[step] + steps)


class CodeFirst:
    """A backend of `benchmark.run_benchmark` for a pipeline with the key `barcode`. It
    decodes the photo first. A unique code answers; a shared GTIN asks `inner` with
    `first`, the wines of the GTIN (plan 64); a miss asks `inner`, an
    `embedding_run.EmbeddingBackend`. `ask` returns five values: the fifth is the step
    trace of plan 41, with the step `barcode` first. The latency of an answer of `inner`
    holds the time of the decode too."""

    def __init__(self, inner, options, db_path, decoder=None, lookup=None):
        self.inner = inner
        self.options = options
        self.lookup = lookup if lookup is not None else CodeLookup.load(db_path)
        self.decoder = decoder if decoder is not None else Decoder(options)
        self.id, self.top_k = inner.id, inner.top_k
        # `run_job.build` and `embedding_run.main` read the index state of the run.
        self.catalogue = inner.catalogue
        self.spec = dict(inner.spec, barcode=dict(options, engine=ENGINE,
                                                  codes=self.lookup.counts))
        self.spec["label"] = "%s, after the code lookup" % inner.spec.get("label", self.id)

    def candidates(self, hit):
        """Return the candidates of a hit: each wine of the code at score 1.0."""
        return [{"slug": slug, "score": 1.0, "rank": rank, "source": hit["source"],
                 "code": hit["code"], "read": hit["read"], "format": hit["format"]}
                for rank, slug in enumerate(hit["slugs"][:self.top_k], 1)]

    def gtin_first(self, cands, hit):
        """Return the candidates of a match that puts the wines of a shared GTIN first
        (plan 64). The inner rank puts the ranked wines of the GTIN first. A wine of the
        GTIN that the match did not rank goes after them as a code candidate with the
        score None (plan 58). The other wines follow."""
        wines = set(hit["slugs"])
        head = 0
        while head < len(cands) and cands[head].get("slug") in wines:
            head += 1
        ranked = {c.get("slug") for c in cands}
        extra = [dict(cand, score=None) for cand in self.candidates(
            dict(hit, slugs=[s for s in hit["slugs"] if s not in ranked]))]
        out = (list(cands[:head]) + extra + list(cands[head:]))[:self.top_k]
        return [dict(cand, rank=rank) for rank, cand in enumerate(out, 1)]

    def ask(self, path):
        """Return `(candidates, latency_ms, http_status, error, trace)`."""
        started = time.perf_counter()
        step = {"id": "barcode", "start_ms": 0.0}
        found, hit, out = [], None, {}
        # A decode cannot change the answer when no code can match, as in the matcher.
        if self.lookup.values:
            try:
                if hasattr(self.decoder, "scan_file"):
                    found, hit, step["cached"] = self.decoder.scan_file(path, self.lookup)
                else:
                    image, _ = derive.open_image(path)
                    found, hit = self.decoder.scan(image, self.lookup)
            except Exception as exc:  # noqa: BLE001 - the embedding still answers the photo
                step["error"] = "%s: %s" % (type(exc).__name__, exc)
        else:
            out["skipped"] = "wine_code holds no code of an Active wine"
        decode_ms = (time.perf_counter() - started) * 1000
        step["ms"] = _ms(decode_ms)
        step["out"] = dict(out, codes=found, hit=hit)
        if hit is not None:
            step["out"]["mode"] = "answer" if is_unique(hit) else "first"
        ignored = shared_qr(self.lookup.hits(found))
        if ignored:
            step["out"]["shared_qr"] = ignored
        if is_unique(hit):
            return (self.candidates(hit), int(round(decode_ms)), 200, None,
                    {"v": 1, "steps": [step]})
        answer = (self.inner.ask(path) if hit is None
                  else self.inner.ask(path, first=hit["slugs"]))
        cands, ms, status, error = answer[:4]
        trace = answer[4] if len(answer) > 4 else None
        if hit is not None and not error:
            cands = self.gtin_first(cands, hit)
        return (cands, ms + int(round(decode_ms)), status, error,
                shift_trace(trace, step, decode_ms))


def answer_note(cand):
    """Return the note of a photo that the code lookup answered."""
    return ("The code lookup answered this photo: %s %s (read as %s %s). No embedding "
            "model ran." % (cand.get("source"), cand.get("code"), cand.get("format"),
                            cand.get("read")))


def candidate_note(cand):
    """Return the note of a candidate that the code lookup gave."""
    return ("The code lookup gave this wine: %s %s (read as %s %s). The run compared no "
            "catalogue input." % (cand.get("source"), cand.get("code"), cand.get("format"),
                                  cand.get("read")))
