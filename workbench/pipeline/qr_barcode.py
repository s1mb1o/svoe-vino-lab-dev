"""Client of the existing QR and barcode scanner service.

`Client.scan` and `Client.decode` send one image to `POST <endpoint>/scan`. The
top-level key `qr_scanner` of `config.yaml` selects the endpoint and engine. Its
endpoint MAY be an HTTP(S) URL or an environment reference such as
`{env:QR_SCANNER_ENDPOINT}`. The service returns QR codes and barcodes in `instances`.

The client keeps the values that the lab database can store:
- A barcode MUST be a valid GTIN. The stored value is GTIN-14.
- A QR code MUST contain an HTTP or HTTPS URL. The stored value is a normal QR URL.

Read `docs/plans/76_scan-additional-image-codes.md`.
"""
import mimetypes
import os
import re

import requests

import codes

CONFIG_KEY = "qr_scanner"
ENV_REFERENCE = re.compile(r"^\{env:([A-Za-z_][A-Za-z0-9_]*)\}$")
ENGINE = "auto"
ENGINES = ("auto", "zxing-cpp", "zxing-cpp-sr", "boofcv-qr-cpp")
TIMEOUT = 180


class ConfigError(ValueError):
    """The `qr_scanner` configuration is not valid."""


class ScanUnavailable(RuntimeError):
    """The scanner is not configured or did not give a valid answer."""


def check_config(raw):
    """Check the top-level key `qr_scanner` of `config.yaml`.

    A missing key is allowed: an additional-image upload can still store its image and a
    recognition pipeline can still fall back to its embedding.
    """
    if raw is None:
        return {"endpoint": None, "engine": ENGINE}
    if not isinstance(raw, dict):
        raise ConfigError("qr_scanner MUST be a mapping")
    unknown = sorted(set(raw) - {"endpoint", "engine"})
    if unknown:
        raise ConfigError("qr_scanner: unknown option %s; use endpoint, engine"
                          % ", ".join(unknown))
    endpoint = raw.get("endpoint")
    if not isinstance(endpoint, str) or not endpoint.strip():
        raise ConfigError("qr_scanner.endpoint MUST be an HTTP(S) URL or {env:NAME}")
    endpoint = endpoint.strip()
    if (not ENV_REFERENCE.fullmatch(endpoint)
            and not endpoint.startswith(("http://", "https://"))):
        raise ConfigError("qr_scanner.endpoint MUST be an HTTP(S) URL or {env:NAME}")
    engine = raw.get("engine", ENGINE)
    if engine not in ENGINES:
        raise ConfigError("qr_scanner.engine MUST be one of: %s" % ", ".join(ENGINES))
    return {"endpoint": endpoint, "engine": engine}


def client_from_config(config, session=None):
    """Build a client from the complete mapping read from `config.yaml`."""
    if not isinstance(config, dict):
        raise ConfigError("config.yaml MUST hold a mapping")
    return Client(session=session, **check_config(config.get(CONFIG_KEY)))


def _resolve_endpoint(reference):
    if reference is None:
        return "", "config.yaml has no qr_scanner.endpoint"
    reference = reference.strip()
    match = ENV_REFERENCE.fullmatch(reference)
    if match:
        name = match.group(1)
        endpoint = os.environ.get(name, "").strip().rstrip("/")
        if not endpoint:
            return "", "the environment variable %s of qr_scanner.endpoint is not set" % name
    else:
        endpoint = reference.rstrip("/")
    if not endpoint.startswith(("http://", "https://")):
        return "", "the resolved qr_scanner.endpoint is not an HTTP(S) URL"
    return endpoint, None


def _is_qr(value):
    """Tell whether a service format names a QR code."""
    return "".join(char for char in value.lower() if char.isalnum()) == "qrcode"


def decode_instances(instances):
    """Return the distinct raw codes of scanner `instances` for barcode lookup."""
    if not isinstance(instances, list):
        raise ScanUnavailable("the scanner answer has no `instances` list")
    found, seen = [], set()
    for item in instances:
        if not isinstance(item, dict):
            raise ScanUnavailable("the scanner answer has a non-object instance")
        text, image_format = item.get("text"), item.get("format")
        if not isinstance(text, str) or not text.strip():
            raise ScanUnavailable("a scanner instance has no text")
        if not isinstance(image_format, str) or not image_format.strip():
            raise ScanUnavailable("a scanner instance has no format")
        code = {"kind": "qr_code" if _is_qr(image_format) else "barcode",
                "format": image_format, "text": text.strip()}
        key = (code["kind"], code["text"])
        if key not in seen:
            seen.add(key)
            found.append(code)
    return found


def clean_instances(instances):
    """Return the distinct storable codes of scanner `instances`.

    Each item has `kind`, `value`, `read`, and `format`. Ignore a barcode that is not a
    GTIN and a QR code that is not an HTTP or HTTPS URL.
    """
    found = []
    seen = set()
    for item in decode_instances(instances):
        text, image_format = item["text"], item["format"]
        kind = "qr_url" if item["kind"] == "qr_code" else "gtin"
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

    def __init__(self, endpoint=None, session=None, engine=ENGINE):
        self.endpoint_reference = endpoint
        self.endpoint, self.endpoint_error = _resolve_endpoint(endpoint)
        self.engine = engine
        self.session = session or requests.Session()

    @property
    def description(self):
        """Return a startup-safe description without an unresolved environment value."""
        if self.endpoint:
            return self.endpoint
        if self.endpoint_reference:
            return "%s (not resolved)" % self.endpoint_reference
        return "not configured"

    def _instances(self, data, name=None):
        """Send one image and return the scanner response's checked `instances`."""
        if not self.endpoint:
            raise ScanUnavailable(self.endpoint_error)
        filename = name if isinstance(name, str) and name else "image"
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        try:
            response = self.session.post(
                self.endpoint + "/scan",
                files={"image": (filename, data, content_type)},
                data={"engine": self.engine},
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
        instances = answer.get("instances")
        decode_instances(instances)
        return instances

    def decode(self, data, name=None):
        """Return raw codes for the recognition pipeline's `wine_code` lookup."""
        return decode_instances(self._instances(data, name))

    def scan(self, data, name=None):
        """Scan image bytes and return the distinct storable codes.

        Raise `ScanUnavailable` when the service is not configured, does not answer, or
        gives a malformed answer.
        """
        return clean_instances(self._instances(data, name))
