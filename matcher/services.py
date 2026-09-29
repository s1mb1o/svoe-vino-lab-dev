"""The async HTTP clients of the backend `cascade`: SigLIP2, SAM3, the QR scanner, and
the VLM.

One `httpx.AsyncClient` serves every call. A call ends at its deadline, a `perf_counter`
value. The cancellation of a call closes its connection, so the service sees the
disconnect. Each call maps a failure to the HTTP status of the matcher: 502 for an error
or invalid data, 504 for a timeout. The public detail texts of SigLIP2 and SAM3 are the
texts of the synchronous clients (`siglip2.py`, `group.py`).
"""

import asyncio
import json
from time import perf_counter

import httpx

from .group import MAX_SAM3_RESPONSE_BYTES, GroupMatchError, _validate_sam3
from .siglip2 import Siglip2Error, parse_vectors, request_body


MAX_JSON_BYTES = 4 * 1024 * 1024
CONNECT_SECONDS = 2.0
LIMITS = httpx.Limits(max_connections=64, max_keepalive_connections=16,
                      keepalive_expiry=2.0)
JSON_HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}


class ServiceError(RuntimeError):
    """A call of the QR scanner or of the VLM failed. `status_code` and `detail` form the
    public answer; the message is for the log."""

    def __init__(self, status_code: int, message: str, detail: str):
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


class ScanError(ServiceError):
    """The QR scanner did not give a valid answer."""


class VlmError(ServiceError):
    """The VLM did not give a valid answer."""


def _siglip2_error(status, message, detail):
    return Siglip2Error(status, message, detail)


def _sam3_error(status, message, detail):
    return GroupMatchError(status, detail)


class Services:
    """The clients of the four model services of one pipeline. An endpoint MAY be None
    when its stage is off."""

    def __init__(self, siglip2=None, sam3=None, scanner=None, vlm=None):
        self.siglip2_url = siglip2.rstrip("/") + "/v1/embeddings" if siglip2 else None
        self.sam3_root = sam3.rstrip("/") if sam3 else None
        self.scanner_root = scanner.rstrip("/") if scanner else None
        self.vlm_url = vlm.rstrip("/") + "/chat/completions" if vlm else None
        self.client = None

    async def start(self):
        if self.client is None:
            self.client = httpx.AsyncClient(limits=LIMITS, trust_env=False,
                                            follow_redirects=False)

    async def close(self):
        if self.client is not None:
            client, self.client = self.client, None
            await client.aclose()

    async def _post(self, url, deadline, name, error, *, retry_5xx=False, cap=MAX_JSON_BYTES,
                    **request):
        """Send one POST and return the decoded JSON answer.

        `name` starts the public detail texts, and `error(status, message, detail)` makes
        the exception of the service. A stale keep-alive connection or a refused connect
        gets one more attempt; with `retry_5xx`, an HTTP 5xx answer gets one too."""
        if self.client is None:
            raise error(503, "the HTTP client of %s is not started" % url,
                        "%s is unavailable" % name)
        for attempt in range(2):
            remaining = deadline - perf_counter()
            if remaining <= 0:
                raise error(504, "request to %s timed out" % url, "%s request timed out"
                            % name.replace(" service", ""))
            timeout = httpx.Timeout(remaining, connect=min(CONNECT_SECONDS, remaining))
            try:
                async with asyncio.timeout(remaining):
                    async with self.client.stream("POST", url, timeout=timeout,
                                                  **request) as response:
                        status = response.status_code
                        declared = response.headers.get("content-length")
                        if declared is not None and declared.isdigit() and int(declared) > cap:
                            raise error(502, "the answer of %s is too large" % url,
                                        "%s response is too large" % name.replace(" service", ""))
                        chunks, size = [], 0
                        async for chunk in response.aiter_bytes():
                            size += len(chunk)
                            if size > cap:
                                raise error(502, "the answer of %s is too large" % url,
                                            "%s response is too large"
                                            % name.replace(" service", ""))
                            chunks.append(chunk)
            except (TimeoutError, httpx.TimeoutException) as exc:
                raise error(504, "request to %s timed out" % url, "%s request timed out"
                            % name.replace(" service", "")) from exc
            except (httpx.RemoteProtocolError, httpx.ConnectError) as exc:
                if attempt == 0:
                    continue
                raise error(502, "cannot reach %s: %s" % (url, exc),
                            "%s is unavailable" % name) from exc
            except httpx.HTTPError as exc:
                raise error(502, "no valid answer from %s: %s" % (url, exc),
                            "%s is unavailable" % name) from exc
            if status >= 500 and retry_5xx and attempt == 0:
                continue
            if status != 200:
                raise error(502, "HTTP %d from %s" % (status, url),
                            "%s returned HTTP %d" % (name, status))
            try:
                return json.loads(b"".join(chunks))
            except (UnicodeDecodeError, ValueError) as exc:
                raise error(502, "the answer of %s is not JSON" % url,
                            "%s returned invalid JSON" % name) from exc
        raise error(502, "no answer from %s" % url, "%s is unavailable" % name)

    async def embed(self, pngs, *, model, extra_body, dimension, deadline):
        """Return one L2-normalized vector for each PNG. Raise Siglip2Error."""
        answer = await self._post(
            self.siglip2_url, deadline, "SigLIP2 service", _siglip2_error,
            content=request_body(pngs, model, extra_body), headers=JSON_HEADERS)
        return parse_vectors(answer, len(pngs), dimension, self.siglip2_url)

    async def segment(self, jpeg, *, nouns, threshold, width, height, deadline):
        """Return the checked SAM3 instances of `nouns` for one JPEG of `width` ×
        `height` pixels. Raise GroupMatchError."""
        answer = await self._post(
            self.sam3_root + "/segment_multi", deadline, "SAM3 service", _sam3_error,
            retry_5xx=True, cap=MAX_SAM3_RESPONSE_BYTES,
            files={"image": ("image.jpg", jpeg, "image/jpeg")},
            data={"texts": ", ".join(nouns), "threshold": str(threshold),
                  "mask_threshold": "0.5", "return_masks": "true"})
        return _validate_sam3(answer, width, height, labels=nouns)

    async def scan(self, png, *, engine, deadline):
        """Return the `instances` of one scanner answer. Raise ScanError."""
        answer = await self._post(
            self.scanner_root + "/scan", deadline, "QR scanner", ScanError,
            files={"image": ("query.png", png, "image/png")}, data={"engine": engine})
        if not isinstance(answer, dict) or not isinstance(answer.get("instances"), list):
            raise ScanError(502, "the answer of the QR scanner has no instances",
                            "QR scanner returned invalid data")
        return answer["instances"]

    async def chat(self, payload, *, deadline):
        """Return the body of one chat completion. Raise VlmError."""
        answer = await self._post(
            self.vlm_url, deadline, "VLM", VlmError,
            content=json.dumps(payload).encode("utf-8"), headers=JSON_HEADERS)
        if not isinstance(answer, dict):
            raise VlmError(502, "the VLM answer is not an object", "VLM returned invalid data")
        return answer

    async def health(self, root, name, error, *, deadline):
        """Check `GET <root>/health`. Raise the error of the service."""
        if self.client is None:
            raise error(503, "the HTTP client is not started", "%s is unavailable" % name)
        remaining = deadline - perf_counter()
        try:
            async with asyncio.timeout(max(0.0, remaining)):
                response = await self.client.get(
                    root + "/health", timeout=httpx.Timeout(max(0.001, remaining)))
        except (TimeoutError, httpx.TimeoutException) as exc:
            raise error(504, "health check of %s timed out" % root,
                        "%s request timed out" % name.replace(" service", "")) from exc
        except httpx.HTTPError as exc:
            raise error(502, "cannot reach %s: %s" % (root, exc),
                        "%s is unavailable" % name) from exc
        if response.status_code != 200:
            raise error(502, "HTTP %d from %s/health" % (response.status_code, root),
                        "%s returned HTTP %d" % (name, response.status_code))
