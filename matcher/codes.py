"""The barcode and QR values of the backend `cascade`: normal forms and the wine lookup.

This module ports `workbench/pipeline/codes.py` (`check_digit`, `clean_gtin`,
`clean_qr_url`), the format filter of `workbench/pipeline/barcode.py` (`Decoder.read`
with the project options), `workbench/pipeline/qr_barcode.py` (`decode_instances`), and
the hit rules of `workbench/pipeline/barcode.py` (plans 42, 58, and 64 of the workbench).
The lab stored each value of the table `wine_code` in the normal form of these functions,
so a decoded value MUST pass the same function before the lookup. The matcher imports no
workbench code. `workbench/tests/test_matcher_parity.py` compares the ports.
"""

import urllib.parse


GTIN_LENGTHS = (8, 12, 13, 14)
GTIN_STORED_LENGTH = 14
QR_URL_MAX = 4096
# The kind of a decoded code -> the kind of `wine_code`.
LOOKUP_KINDS = {"barcode": "gtin", "qr_code": "qr_url"}
# The product-code formats that the cascade keeps (the lab project options `formats:
# [EAN13, Code128]`, `code128_gtin_only: true`, `qr: true`), as normalized scanner names.
FORMATS = ("ean13", "code128")


class CodeError(ValueError):
    """A value is not a valid value of its kind."""


def check_digit(digits):
    """Return the GS1 check digit of `digits`, the digits before the check digit.

    The weights are 3 and 1 in turn, from the right. The digit next to the check digit
    gets 3. Leading zeros do not change the result.
    """
    total = sum(int(digit) * (3 if position % 2 == 0 else 1)
                for position, digit in enumerate(reversed(digits)))
    return (10 - total % 10) % 10


def _no_space(value, name):
    if not isinstance(value, str):
        raise CodeError("%s MUST be a string" % name)
    clean = "".join(value.split())
    if not clean:
        raise CodeError("%s is empty" % name)
    return clean


def clean_gtin(value):
    """Check one GTIN and return its GTIN-14 form."""
    clean = _no_space(value, "GTIN")
    if not (clean.isascii() and clean.isdigit()):
        raise CodeError("GTIN MUST hold digits alone")
    if len(clean) not in GTIN_LENGTHS:
        raise CodeError("GTIN MUST have 8, 12, 13, or 14 digits; it has %d" % len(clean))
    expected = check_digit(clean[:-1])
    if int(clean[-1]) != expected:
        raise CodeError("wrong check digit %s; expected %d" % (clean[-1], expected))
    return clean.zfill(GTIN_STORED_LENGTH)


def clean_qr_url(value):
    """Check one QR URL and return its normal form.

    Remove a `URL:` prefix. Lower-case the scheme and the host, and convert the host to
    IDNA. An IPv6 host keeps its brackets. Remove a default port and the fragment. Use
    `/` for an empty path.
    """
    if not isinstance(value, str):
        raise CodeError("QR URL MUST be a string")
    text = value.strip()
    if text.startswith("URL:"):
        text = text[4:].strip()
    if not text:
        raise CodeError("QR URL is empty")
    if len(text) > QR_URL_MAX:
        raise CodeError("QR URL is longer than %d characters" % QR_URL_MAX)
    if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in text):
        raise CodeError("QR URL contains white space or a control character")
    try:
        parts = urllib.parse.urlsplit(text)
    except ValueError as exc:
        raise CodeError("QR URL is not a valid URL") from exc
    scheme = parts.scheme.lower()
    if scheme not in ("http", "https") or not parts.hostname:
        raise CodeError("QR URL MUST use http or https and name a host")
    if parts.username or parts.password:
        raise CodeError("QR URL MUST NOT contain user information")
    try:
        if ":" in parts.hostname:
            # An IPv6 literal. `hostname` drops the brackets, and IDNA does not apply.
            host = "[%s]" % parts.hostname.lower()
        else:
            host = parts.hostname.encode("idna").decode("ascii").lower()
        port = parts.port
    except (UnicodeError, ValueError) as exc:
        raise CodeError("QR URL has an invalid host or port") from exc
    default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    netloc = host if port is None or default_port else "%s:%d" % (host, port)
    return urllib.parse.urlunsplit((scheme, netloc, parts.path or "/", parts.query, ""))


CLEANERS = {"gtin": clean_gtin, "qr_url": clean_qr_url}


def clean(kind, value):
    """Check one value of `kind` and return its normal form."""
    if kind not in CLEANERS:
        raise CodeError("unknown kind %r" % (kind,))
    return CLEANERS[kind](value)


def is_gtin13(value):
    """Return True for 13 digits with a valid EAN-13 check digit."""
    if len(value) != 13 or not value.isascii() or not value.isdigit():
        return False
    return check_digit(value[:12]) == int(value[12])


def _format_name(value):
    return "".join(char for char in value.lower() if char.isalnum())


def read(instances):
    """Return the kept codes of scanner `instances` in reading order.

    Each code is `{"kind", "format", "text"}`. A QR code is kept. A barcode is kept when
    it is EAN-13, or Code 128 that holds a valid GTIN-13. The same (kind, text) is kept
    one time. Raise ValueError for a malformed instance.
    """
    if not isinstance(instances, list):
        raise ValueError("the scanner answer has no `instances` list")
    found, seen = [], set()
    for item in instances:
        if not isinstance(item, dict):
            raise ValueError("the scanner answer has a non-object instance")
        text, image_format = item.get("text"), item.get("format")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("a scanner instance has no text")
        if not isinstance(image_format, str) or not image_format.strip():
            raise ValueError("a scanner instance has no format")
        name = _format_name(image_format)
        kind = "qr_code" if name == "qrcode" else "barcode"
        text = text.strip()
        if kind == "barcode" and (name not in FORMATS
                                  or (name == "code128" and not is_gtin13(text))):
            continue
        key = (kind, text)
        if key not in seen:
            seen.add(key)
            found.append({"kind": kind, "format": image_format, "text": text})
    return found


def is_unique(hit):
    """Return True for the hit of a code of one wine."""
    return hit is not None and len(hit["slugs"]) == 1


class CodeTable:
    """The codes of the Active wines: (kind, value) -> the sorted slugs of the wines."""

    def __init__(self, values):
        self.values = values

    def key(self, code):
        """Return the (kind, value) of `wine_code` for one decoded code, or None when the
        text is not a valid value of its kind."""
        kind = LOOKUP_KINDS[code["kind"]]
        try:
            return kind, clean(kind, code["text"])
        except CodeError:
            return None

    def hits(self, found):
        """Return the hit of each decoded code that the table holds, in the order of
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
