"""Client of the existing QR and barcode scanner service.

`Client.scan` sends one image to `POST $QR_SCANNER_ENDPOINT/scan` with
`engine=auto`. The service returns QR codes and barcodes in `instances`.

The client keeps the values that the lab database can store:
- A barcode MUST be a valid GTIN. The stored value is GTIN-14.
- A QR code MUST contain an HTTP or HTTPS URL. The stored value is a normal QR URL.

Read `docs/plans/76_scan-additional-image-codes.md`.
"""
import mimetypes
import os

import requests

import codes

ENDPOINT_ENV = "QR_SCANNER_ENDPOINT"
ENGINE = "auto"
TIMEOUT = 180


class ScanUnavailable(RuntimeError):
    """The scanner is not configured or did not give a valid answer."""


def _is_qr(value):
    """Tell whether a service format names a QR code."""
    return "".join(char for char in value.lower() if char.isalnum()) == "qrcode"


def clean_instances(instances):
    """Return the distinct storable codes of scanner `instances`.

    Each item has `kind`, `value`, `read`, and `format`. Ignore a barcode that is not a
    GTIN and a QR code that is not an HTTP or HTTPS URL.
    """
    if not isinstance(instances, list):
        raise ScanUnavailable("the scanner answer has no `instances` list")
    found = []
    seen = set()
    for item in instances:
        if not isinstance(item, dict):
            raise ScanUnavailable("the scanner answer has a non-object instance")
        text, image_format = item.get("text"), item.get("format")
        if not isinstance(text, str) or not text.strip():
            raise ScanUnavailable("a scanner instance has no text")
        if not isinstance(image_format, str) or not image_format.strip():
            raise ScanUnavailable("a scanner instance has no format")
        kind = "qr_url" if _is_qr(image_format) else "gtin"
        try:
            value = codes.clean(kind, text)
        except codes.CodeError:
            continue
        key = (kind, value)
        if key in seen:
            continue
        seen.add(key)
        found.append({"kind": kind, "value": value, "read": text,
                      "format": image_format})
    return found


class Client:
    """A client of `POST /scan` of the QR and barcode scanner service."""

    def __init__(self, endpoint=None, session=None):
        self.endpoint = (endpoint if endpoint is not None
                         else os.environ.get(ENDPOINT_ENV, "")).strip().rstrip("/")
        self.session = session or requests.Session()

    def scan(self, data, name=None):
        """Scan image bytes and return the distinct storable codes.

        Raise `ScanUnavailable` when the service is not configured, does not answer, or
        gives a malformed answer.
        """
        if not self.endpoint:
            raise ScanUnavailable("%s is not set" % ENDPOINT_ENV)
        filename = name if isinstance(name, str) and name else "additional-image"
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        try:
            response = self.session.post(
                self.endpoint + "/scan",
                files={"image": (filename, data, content_type)},
                data={"engine": ENGINE},
                timeout=TIMEOUT)
        except requests.RequestException as exc:
            raise ScanUnavailable("the scanner at %s did not answer: %s"
                                  % (self.endpoint, exc)) from exc
        if response.status_code != 200:
            raise ScanUnavailable("the scanner at %s returned HTTP %d: %s"
                                  % (self.endpoint, response.status_code,
                                     response.text[:200]))
        try:
            answer = response.json()
        except ValueError as exc:
            raise ScanUnavailable("the scanner answer is not JSON") from exc
        if not isinstance(answer, dict):
            raise ScanUnavailable("the scanner answer is not an object")
        return clean_instances(answer.get("instances"))
