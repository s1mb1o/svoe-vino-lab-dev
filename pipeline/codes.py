"""The checks and the normal forms of the values of the table `wine_code`.

The kinds:
- `gtin`: a GS1 product number of 8, 12, 13, or 14 digits with a valid check digit. The
  stored form is GTIN-14: leading zeros make 14 digits.
- `qr_url`: an http or https URL in the normal form of the old Dataset editor and of the
  matcher.

The owner chose on 2026-09-25 to keep GTINs alone: the lab has no kind `barcode`.
Schema 008 still allows `barcode` in its CHECK until the flatten. This code never
writes it.

The seed and the lab server use these functions. Each function raises `CodeError` for a
bad value. Read `docs/plans/11_wine-codes.md`.
"""
import urllib.parse

KINDS = ("gtin", "qr_url")
# The lengths of a GTIN as read: GTIN-8, GTIN-12, GTIN-13, and GTIN-14.
GTIN_LENGTHS = (8, 12, 13, 14)
GTIN_STORED_LENGTH = 14
QR_URL_MAX = 4096


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
        raise CodeError("unknown kind %r; use one of: %s" % (kind, ", ".join(KINDS)))
    return CLEANERS[kind](value)

