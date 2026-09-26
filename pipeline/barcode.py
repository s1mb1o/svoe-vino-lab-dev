"""The barcode step of the lab pipelines: the key `barcode` of a pipeline of the backend
`embedding` (plan 42; owner message of 2026-09-26T07:22:10+0300, answers of 07:27:08).

The step decodes the test photo as it is, before the views of the pipeline. It looks up
each decoded code in the table `wine_code` of the Active wines. A hit answers the photo
with each wine of the code at score 1.0, in slug order, and the embedding does not run. A
miss asks the embedding backend, and its answer does not change.

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
import math
import time
from contextlib import closing

from PIL import Image

import codes
import derive
import embeddings
from embeddings import ConfigError

# The zxing-cpp formats of a product code that can hold a GTIN.
FORMATS = ("EAN13", "EAN8", "UPCA", "Code128")
QR_FORMAT = "QRCode"
# option -> default. The defaults are the defaults of the matcher, less `UPCE`.
DEFAULTS = {"formats": list(FORMATS), "qr": True, "tile_scan": True, "max_side": 1600,
            "upscale": False, "code128_gtin_only": False}
MIN_SIDE, MAX_SIDE = 64, 8192
ENGINE = "zxing-cpp"
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

    def find(self, found):
        """Return the hit of the first decoded code that `wine_code` holds, or None. A hit
        is a dict: `source` (the kind of `wine_code`), `code` (the stored value), `read`
        (the text as decoded), `format`, and `slugs`."""
        for code in found:
            key = self.key(code)
            slugs = self.values.get(key) if key else None
            if slugs:
                return {"source": key[0], "code": key[1], "read": code["text"],
                        "format": code["format"], "slugs": list(slugs)}
        return None


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
        """Return (each decoded code, the hit of `lookup` or None) of one opened photo."""
        image = self.scaled(image)
        found = self.read(image)
        hit = lookup.find(_dedupe(found))
        if self.options["tile_scan"] and hit is None:
            for tile in tiles(image):
                found.extend(self.read(tile))
                hit = lookup.find(_dedupe(found))
                if hit is not None:
                    break
        return _dedupe(found), hit


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
    decodes the photo first. A hit answers; a miss asks `inner`, an
    `embedding_run.EmbeddingBackend`. `ask` returns five values: the fifth is the step
    trace of plan 41, with the step `barcode` first. The latency of a miss holds the time of
    the decode too."""

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

    def ask(self, path):
        """Return `(candidates, latency_ms, http_status, error, trace)`."""
        started = time.perf_counter()
        step = {"id": "barcode", "start_ms": 0.0}
        found, hit, out = [], None, {}
        # A decode cannot change the answer when no code can match, as in the matcher.
        if self.lookup.values:
            try:
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
            return (self.candidates(hit), int(round(decode_ms)), 200, None,
                    {"v": 1, "steps": [step]})
        answer = self.inner.ask(path)
        cands, ms, status, error = answer[:4]
        trace = answer[4] if len(answer) > 4 else None
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
