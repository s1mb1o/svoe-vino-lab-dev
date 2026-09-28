"""Fetch an image URL from a browser drop without letting it reach a local service.

The browser cannot read cross-origin image bytes itself.  It gives the Testset page an
address, and the lab server fetches that address.  Every HTTP(S) hop is resolved before
it is opened; loopback, private, link-local, reserved, multicast, and otherwise
non-global addresses are refused.  The caller still validates the downloaded bytes as
an image.
"""
import base64
import binascii
import ipaddress
import os
import socket
import urllib.error
import urllib.parse
import urllib.request


FETCH_TIMEOUT = 20
URL_MAX = 16384
USER_AGENT = "Mozilla/5.0 (compatible; SvoeVinoLab/1.0; image-drop)"


class RemoteImageError(ValueError):
    """The dropped address or its response is not safe to use as an image."""


def check_url(url):
    """Return a safe HTTP(S) URL, or raise ``RemoteImageError``.

    This check also runs for every redirect.  It intentionally accepts public literal
    IP addresses but refuses credentials in an address.
    """
    if not isinstance(url, str) or not url.strip():
        raise RemoteImageError("the drop holds no image address")
    url = url.strip()
    if len(url) > URL_MAX:
        raise RemoteImageError("the image address is too long")
    try:
        parts = urllib.parse.urlsplit(url)
        port = parts.port or (443 if parts.scheme.lower() == "https" else 80)
    except ValueError as exc:
        raise RemoteImageError("the image address is not valid: %s" % exc) from exc
    if parts.scheme.lower() not in ("http", "https"):
        raise RemoteImageError("only an http or https image address can be fetched")
    if not parts.hostname:
        raise RemoteImageError("the image address holds no host")
    if parts.username is not None or parts.password is not None:
        raise RemoteImageError("the image address MUST NOT hold credentials")
    try:
        answers = socket.getaddrinfo(parts.hostname, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise RemoteImageError("cannot resolve %s: %s" % (parts.hostname, exc)) from exc
    if not answers:
        raise RemoteImageError("cannot resolve %s" % parts.hostname)
    for answer in answers:
        try:
            address = ipaddress.ip_address(answer[4][0])
        except ValueError as exc:
            raise RemoteImageError("cannot check the address of %s" % parts.hostname) from exc
        if not address.is_global:
            raise RemoteImageError("the image address points at a local host: %s" % address)
    return url


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Apply ``check_url`` before urllib follows an HTTP redirect."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def source_name(url):
    """Return a useful, unquoted source name for ``testsets.upload_photo``."""
    if url.startswith("data:"):
        return "dropped-image"
    leaf = os.path.basename(urllib.parse.unquote(urllib.parse.urlsplit(url).path))
    return leaf or "dropped-image"


def _data_url(url, limit):
    head, comma, payload = url.partition(",")
    if not comma or not head[5:].lower().startswith("image/"):
        raise RemoteImageError("the data address is not an image")
    try:
        if ";base64" in head.lower():
            data = base64.b64decode(payload, validate=True)
        else:
            data = urllib.parse.unquote_to_bytes(payload)
    except (binascii.Error, ValueError) as exc:
        raise RemoteImageError("the data image is not encoded correctly") from exc
    if not data:
        raise RemoteImageError("the image address answered with an empty body")
    if len(data) > limit:
        raise RemoteImageError("the image is larger than %d bytes" % limit)
    return data, source_name(url)


def fetch_image(url, limit):
    """Return ``(bytes, source name)`` for one safe dropped image address.

    The byte signature and pixel limits are checked later by ``testsets.upload_photo``.
    Reading ``limit + 1`` bytes prevents an untrusted server from bypassing the limit by
    omitting or lying in ``Content-Length``.
    """
    if not isinstance(url, str):
        raise RemoteImageError("the drop holds no image address")
    url = url.strip()
    if url.lower().startswith("data:"):
        if len(url) > max(URL_MAX, limit * 2):
            raise RemoteImageError("the data image is too large")
        return _data_url(url, limit)
    safe = check_url(url)
    request = urllib.request.Request(safe, headers={
        "User-Agent": USER_AGENT,
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    })
    try:
        with urllib.request.build_opener(_SafeRedirectHandler()).open(
                request, timeout=FETCH_TIMEOUT) as response:
            final_url = response.geturl() if hasattr(response, "geturl") else safe
            check_url(final_url)
            declared = response.headers.get("Content-Length")
            if declared:
                try:
                    declared_size = int(declared)
                except ValueError as exc:
                    raise RemoteImageError("the image host sent an invalid size") from exc
                if declared_size > limit:
                    raise RemoteImageError("the image is larger than %d bytes" % limit)
            data = response.read(limit + 1)
    except RemoteImageError:
        raise
    except urllib.error.HTTPError as exc:
        raise RemoteImageError("the image host answered HTTP %d" % exc.code) from exc
    except urllib.error.URLError as exc:
        raise RemoteImageError("cannot fetch the image: %s" % exc.reason) from exc
    except OSError as exc:
        raise RemoteImageError("cannot fetch the image: %s" % exc) from exc
    if not data:
        raise RemoteImageError("the image address answered with an empty body")
    if len(data) > limit:
        raise RemoteImageError("the image is larger than %d bytes" % limit)
    return data, source_name(final_url)
