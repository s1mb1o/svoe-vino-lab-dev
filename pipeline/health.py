"""The Health page of the lab server: the state of the server, and a check of each
endpoint of `config.yaml`.

    GET  /health
    GET  /api/health
    POST /api/health/check      {"kind": "<kind>", "name": "<name>"}

The kinds of an endpoint: `vlm` (an entry of the key `vlm`), `embedding` (an entry of the
key `embeddings`), `sam3` (`sam3.endpoint`), and `remote` (the vino-svoe.ru API of
`import_website.API`).

The check is the check "Hybrid" of the owner (answer of 2026-09-26T11:02:57+0300). A real
call goes only to a model that runs on its llama-swap gateway now, and to a service that
is not a llama-swap gateway, for example a cloud entry. A model that does not run gets no
call: a request to it makes llama-swap load it, and the load can stop a model that the
watcher or a job uses. Read `docs/plans/46_health-page.md`.
"""
import base64
import difflib
import io
import json
import os
import platform
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.parse
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

import requests
from PIL import Image

import derive
import embedding_routes
import embeddings
import image_descriptions
import import_website
import lab_pages
import labdb
import pipelines
import run_jobs
import vlm_config

PAGE = "/health"
API = "/api/health"
CHECK_ROUTE = "/api/health/check"
JSON_TYPE = "application/json; charset=utf-8"
HTML_TYPE = "text/html; charset=utf-8"
NO_STORE = "no-store"
MAX_BODY = 4096
KINDS = ("vlm", "embedding", "sam3", "remote")
REMOTE_NAME = "vino-svoe.ru API"

CONNECT_TIMEOUT = 5      # s
LIST_TIMEOUT = 10        # s; one list of a gateway or of a service
CALL_TIMEOUT = 30        # s; one real call
STATUS_TIMEOUT = 3       # s; `/running` of a gateway for the status part
IMPORT_TIMEOUT = 60      # s; the import of torch and transformers in `embedding_python`
BODY_CHARS = 300         # the characters of a body in a text
LOW_DISK = 5 * 1024 ** 3  # bytes; less free space on the disk of the database gives `warn`
WATCH_WINDOW = 3600      # s; the watcher failures of this last period
WATCH_LINES = 5          # the failure lines that the status sends
LOG_TAIL = 262144        # bytes; the end of the watcher log that the status reads
# The llama-swap state of a model that answers.
READY = "ready"
# The order of the states of a wine, as in `lab_server.STATES`.
WINE_STATES = ("Active", "Disabled", "Removed")
# Each chat request of a check holds a new random token. A byte-identical repeat is a full
# hit of the prompt cache of llama.cpp. On 2026-09-26 at 11:24:33 such a repeat made
# llama.cpp 45b455e roll back one token of the recurrent state of the hybrid model
# `qwen3.5-9b`, and the server stopped in `ggml_abort` ("failed to remove sequence").
# A prompt that differs takes the checkpoint path of llama.cpp, the path of each chat.
VLM_PROMPT = "Health check %s. Reply with OK."
# One failure line of the watcher log: `<UTC time> [<sha256 prefix>] ... failed ...` or
# `<UTC time> waiting: ...`.
FAILURE_RE = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ) (?:.*\bfailed\b|waiting:)")
UPSTREAM_RE = re.compile(r"^/upstream/([^/]+)/?$")


def handles(route):
    """Tell whether a route belongs to the Health page."""
    return route in (PAGE, API, CHECK_ROUTE)


def _json(code, value):
    return code, value, JSON_TYPE, NO_STORE


def _error(code, message):
    return _json(code, {"error": message})


def now_iso(t=None):
    """Return the local time `t` (default: now) in ISO 8601 with seconds."""
    return datetime.fromtimestamp(time.time() if t is None else t).astimezone().isoformat(
        timespec="seconds")


def root_of(url):
    """Return the scheme and the host of `url`, for example `http://192.168.86.14:18081`."""
    parts = urllib.parse.urlsplit(url)
    return "%s://%s" % (parts.scheme, parts.netloc)


# The requests of a check.

class CallError(Exception):
    """One request failed or gave a wrong answer. `timed_out` is True when the service
    took the connection and gave no answer in time."""

    def __init__(self, text, timed_out=False):
        super().__init__(text)
        self.timed_out = timed_out


def _causes(exc):
    """Yield `exc` and each exception in it. urllib3 puts the cause of a failed
    connection in `reason` and in the arguments, not only in `__cause__`."""
    todo, seen = [exc], set()
    while todo:
        item = todo.pop()
        if id(item) in seen:
            continue
        seen.add(id(item))
        yield item
        todo.extend(inner for inner in (item.__cause__, item.__context__,
                                        getattr(item, "reason", None), *item.args)
                    if isinstance(inner, BaseException))


def explain(exc, url, read_timeout):
    """Return the text of a request that got no answer: what failed, and why."""
    parts = urllib.parse.urlsplit(url)
    host = parts.hostname or url
    port = parts.port or (443 if parts.scheme == "https" else 80)
    if isinstance(exc, requests.exceptions.ConnectTimeout):
        return ("no connection to %s:%d in %g s: the host is down, or a firewall drops the "
                "packets" % (host, port, CONNECT_TIMEOUT))
    if isinstance(exc, requests.exceptions.ReadTimeout):
        return "connected to %s:%d, but no answer in %g s" % (host, port, read_timeout)
    causes = list(_causes(exc))
    text = " ".join(str(cause) for cause in causes)
    if isinstance(exc, requests.exceptions.SSLError):
        return "the TLS handshake with %s failed: %s" % (host, causes[-1])
    if (any(isinstance(cause, ConnectionRefusedError) for cause in causes)
            or "Connection refused" in text):
        return "connection refused: no process listens on %s:%d" % (host, port)
    if (any(isinstance(cause, socket.gaierror) for cause in causes)
            or any(type(cause).__name__ == "NameResolutionError" for cause in causes)):
        return "the host name %s does not resolve" % host
    if isinstance(exc, requests.exceptions.ConnectionError):
        return "no connection to %s:%d: %s" % (host, port, causes[-1])
    return "the request failed: %s: %s" % (type(exc).__name__, exc)


def snippet(response):
    """Return the first BODY_CHARS characters of the body, on one line."""
    text = " ".join((response.text or "").split())
    return text[:BODY_CHARS] + ("…" if len(text) > BODY_CHARS else "")


def http_error(response, key_env="", gateway_root=None):
    """Return the text of an HTTP answer that is not a success. `gateway_root` names the
    llama-swap gateway of the request, or is None."""
    code, body = response.status_code, snippet(response) or "(empty body)"
    if code == 502 and gateway_root:
        # llama-swap answers 502 when the model process closes the connection.
        return ("the gateway got no answer from the model process (HTTP 502): the process "
                "stopped or crashed during the request; its output is at GET "
                "%s/logs/stream/upstream: %s" % (gateway_root, body))
    if code in (401, 403):
        if key_env:
            return ("the service refused the key of the variable %s (HTTP %d): %s"
                    % (key_env, code, body))
        return ("the service needs a key (HTTP %d), and the entry has no `key`: %s"
                % (code, body))
    if code == 404:
        return "the service has no such route or model (HTTP 404): %s" % body
    if code == 429:
        return "the service is busy, or the quota is used up (HTTP 429): %s" % body
    if code >= 500:
        return "the service failed (HTTP %d): %s" % (code, body)
    return "HTTP %d: %s" % (code, body)


class Row:
    """The result of the check of one endpoint. Each text of the row goes through
    `clean`, so the key value of the entry never leaves the server."""

    def __init__(self, kind, name, secret=""):
        self.kind, self.name, self.secret = kind, name, secret
        self.details = []
        self.started = time.perf_counter()

    def clean(self, text):
        text = str(text)
        return text.replace(self.secret, "<redacted>") if self.secret else text

    def note(self, text):
        self.details.append(self.clean(text))

    def call(self, method, url, timeout, **kwargs):
        """Send one request and note it. Return (the response, its time in ms). Raise
        CallError when the service gives no answer. An answer of each HTTP code returns."""
        started = time.perf_counter()
        try:
            response = requests.request(method, url, timeout=(CONNECT_TIMEOUT, timeout),
                                        **kwargs)
        except requests.RequestException as exc:
            text = explain(exc, url, timeout)
            self.note("%s %s: %s (%d ms)" % (method, url, text,
                                             (time.perf_counter() - started) * 1000))
            raise CallError(text, isinstance(exc, requests.exceptions.ReadTimeout))
        ms = (time.perf_counter() - started) * 1000
        self.note("%s %s: HTTP %d in %d ms" % (method, url, response.status_code, ms))
        return response, ms

    def result(self, status, summary):
        return {"kind": self.kind, "name": self.name, "status": status,
                "summary": self.clean(summary), "details": self.details,
                "ms": round((time.perf_counter() - self.started) * 1000)}


def gateway(row, root, timeout=LIST_TIMEOUT):
    """Return the llama-swap state of `root`: {"models": the ids of `/v1/models`,
    "running": model -> the state of `/running`}. Return None when `root` is not a
    llama-swap gateway. Raise CallError when `root` gives no answer."""
    response, _ms = row.call("GET", root + "/running", timeout)
    try:
        running = response.json()["running"] if response.status_code == 200 else None
    except (ValueError, KeyError, TypeError):
        running = None
    if not isinstance(running, list):
        row.note("%s is not a llama-swap gateway: GET /running gives no list `running`"
                 % root)
        return None
    response, _ms = row.call("GET", root + "/v1/models", timeout)
    if response.status_code != 200:
        raise CallError("the gateway %s answers GET /v1/models: %s"
                        % (root, http_error(response)))
    try:
        models = [item["id"] for item in response.json()["data"]]
    except (ValueError, KeyError, TypeError):
        raise CallError("GET %s/v1/models gives no model list: %s" % (root, snippet(response)))
    return {"models": models,
            "running": {item.get("model"): item.get("state") for item in running
                        if isinstance(item, dict)}}


def gateway_skip(state, model, root):
    """Return (status, summary) for a model that gets no real call, or None when the
    model runs and answers."""
    if model not in state["models"]:
        close = difflib.get_close_matches(model, state["models"], n=3, cutoff=0.6)
        return "error", ("the gateway %s has no model %s (it lists %d models)%s"
                         % (root, model, len(state["models"]),
                            "; close names: %s" % ", ".join(close) if close else ""))
    run_state = state["running"].get(model)
    if run_state is None:
        return "idle", ("the gateway knows the model, and it does not run now; no call "
                        "(a call would start it)")
    if run_state != READY:
        return "warn", "the gateway reports the state %s for the model; no call" % run_state
    return None


def service_models(row, endpoint, key="", key_env=""):
    """Return the model ids of `GET <endpoint>/models`, or None when the service sends no
    such list. Raise CallError when the service refuses the key."""
    headers = {"Authorization": "Bearer " + key} if key else {}
    response, _ms = row.call("GET", endpoint.rstrip("/") + "/models", LIST_TIMEOUT,
                             headers=headers)
    if response.status_code in (401, 403):
        raise CallError(http_error(response, key_env))
    if response.status_code != 200:
        row.note("GET /models gives no list (%s); the real call decides"
                 % http_error(response))
        return None
    try:
        return [item["id"] for item in response.json()["data"]]
    except (ValueError, KeyError, TypeError):
        row.note("GET /models gives no model list; the real call decides")
        return None


def unlisted(models, model):
    """Return the note for a model that `GET /models` does not list, or ""."""
    if models is None or model in models:
        return ""
    close = difflib.get_close_matches(model, models, n=3, cutoff=0.6)
    return ("GET /models does not list the model %s (it lists %d models)%s"
            % (model, len(models), "; close names: %s" % ", ".join(close) if close else ""))


def with_listing(status, summary, note):
    """Add the note of `unlisted` to the result of a real call."""
    if not note:
        return status, summary
    return ("warn" if status == "ok" else status), "%s; %s" % (summary, note)


# The real calls.

def vlm_call(row, entry, key, gateway_root=None):
    """Send one chat request of 1 token to a VLM entry. Return (status, summary).
    `gateway_root` names the llama-swap gateway of the entry, or is None."""
    payload = {"model": entry.model, "temperature": 0, "max_tokens": 1,
               "messages": [{"role": "user",
                             "content": VLM_PROMPT % uuid.uuid4().hex[:12]}]}
    if entry.thinking_field == "top_level":
        payload["enable_thinking"] = False
    else:
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    headers = {"Authorization": "Bearer " + key} if key else {}
    try:
        response, ms = row.call("POST", entry.url, CALL_TIMEOUT, json=payload,
                                headers=headers)
    except CallError as exc:
        if exc.timed_out:
            return "error", ("the model gave no answer in %g s; it can be busy with other "
                             "requests" % CALL_TIMEOUT)
        return "error", str(exc)
    if response.status_code != 200:
        return "error", http_error(response, entry.key_env, gateway_root)
    try:
        body = response.json()
        choice = body["choices"][0]
        message = choice["message"]
        if not isinstance(message, dict):
            raise TypeError("message")
    except (ValueError, KeyError, IndexError, TypeError):
        return "error", "HTTP 200, but the body is not a chat answer: %s" % snippet(response)
    # `max_tokens: 1` stops the answer after one token, so `length` is the normal reason.
    row.note("finish_reason %s; the check asks for 1 token" % choice.get("finish_reason"))
    return "ok", ("answered in %d ms (model %s): %s"
                  % (ms, body.get("model") or entry.model,
                     json.dumps(message.get("content"), ensure_ascii=False)))


def grey_png():
    """Return a grey PNG of 64 x 64 px as a data URI."""
    buffer = io.BytesIO()
    Image.new("RGB", (64, 64), (128, 128, 128)).save(buffer, "PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def embedding_call(row, embedding, gateway_root=None):
    """Send one image to an embedding entry of the backend openai, as
    `build_embeddings.OpenAIBackend` does. Return (status, summary). `gateway_root` names
    the llama-swap gateway of the entry, or is None."""
    body = dict(embedding.extra_body, model=embedding.model, input=[grey_png()])
    try:
        response, ms = row.call("POST", embedding.base_url + "/embeddings", CALL_TIMEOUT,
                                json=body)
    except CallError as exc:
        if exc.timed_out:
            return "error", ("the model gave no answer in %g s; it can be busy with other "
                             "requests" % CALL_TIMEOUT)
        return "error", str(exc)
    if response.status_code != 200:
        return "error", http_error(response, gateway_root=gateway_root)
    try:
        vector = response.json()["data"][0]["embedding"]
        if not vector or not all(isinstance(value, (int, float)) for value in vector):
            raise TypeError("vector")
    except (ValueError, KeyError, IndexError, TypeError):
        return "error", "HTTP 200, but the body holds no vector: %s" % snippet(response)
    return "ok", "answered in %d ms: one vector of %d numbers" % (ms, len(vector))


# The checks of each kind.

def check_vlm(config, name):
    """Check the entry `name` of the key `vlm`. Raise KeyError for an unknown name."""
    try:
        entries = vlm_config.entries(config)
    except vlm_config.VlmConfigError as exc:
        return Row("vlm", name).result("error", "config.yaml: %s" % exc)
    entry = entries[name]
    key = entry.api_key()
    row = Row("vlm", name, key)
    if entry.key_env and not key:
        return row.result("error", (
            "the variable %s is not set in the environment of the lab server (pid %d); set "
            "it in the shell that starts the server, then restart the server"
            % (entry.key_env, os.getpid())))
    root = root_of(entry.endpoint)
    try:
        # The check never reads `/running` of a service with a key: a cloud service.
        state = None if entry.key_env else gateway(row, root)
        if state is not None:
            return row.result(*(gateway_skip(state, entry.model, root)
                                or vlm_call(row, entry, key, root)))
        note = unlisted(service_models(row, entry.endpoint, key, entry.key_env), entry.model)
        return row.result(*with_listing(*vlm_call(row, entry, key), note))
    except CallError as exc:
        return row.result("error", str(exc))


def check_embedding(config_path, name):
    """Check the entry `name` of the key `embeddings`. Raise KeyError for an unknown
    name."""
    settings = embeddings.load_settings(config_path)
    row = Row("embedding", name)
    try:
        embedding = settings.find(name)
    except embeddings.ConfigError as exc:
        return row.result("error", "config.yaml: %s" % exc)
    if embedding.backend == "local":
        return row.result(*local_check(row, embedding, settings.python))
    root = root_of(embedding.base_url)
    try:
        state = gateway(row, root)
        if state is not None:
            return row.result(*(gateway_skip(state, embedding.model, root)
                                or embedding_call(row, embedding, root)))
        note = unlisted(service_models(row, embedding.base_url), embedding.model)
        return row.result(*with_listing(*embedding_call(row, embedding), note))
    except CallError as exc:
        return row.result("error", str(exc))


def hf_cache_dir():
    """Return the hub directory of the Hugging Face cache of this process."""
    if os.environ.get("HF_HUB_CACHE"):
        return os.path.expanduser(os.environ["HF_HUB_CACHE"])
    if os.environ.get("HF_HOME"):
        return os.path.join(os.path.expanduser(os.environ["HF_HOME"]), "hub")
    return os.path.expanduser("~/.cache/huggingface/hub")


def hf_snapshot(model, cache=None):
    """Return (the snapshot directory of `model`, the bytes of its weight files), or None
    when the cache holds no snapshot with `config.json` and a weight file."""
    snapshots = os.path.join(cache or hf_cache_dir(), "models--" + model.replace("/", "--"),
                             "snapshots")
    try:
        with open(os.path.join(os.path.dirname(snapshots), "refs", "main"),
                  encoding="utf-8") as fh:
            names = [fh.read().strip()]
    except OSError:
        try:
            names = sorted(os.listdir(snapshots))
        except OSError:
            return None
    for name in names:
        path = os.path.join(snapshots, name)
        try:
            files = os.listdir(path)
        except OSError:
            continue
        weights = [f for f in files if f.endswith((".safetensors", ".bin"))]
        if weights and "config.json" in files:
            return path, sum(os.path.getsize(os.path.join(path, f)) for f in weights)
    return None


# The interpreter of the backend local prints the versions of its packages.
LOCAL_PROBE = ("import json, torch, transformers; print(json.dumps({'torch': "
               "torch.__version__, 'transformers': transformers.__version__, 'device': "
               "'mps' if torch.backends.mps.is_available() else 'cpu'}))")


def local_check(row, embedding, python):
    """Check an entry of the backend local with no model load. Return (status,
    summary)."""
    if not python:
        return "error", "config.yaml has no key `embedding_python`"
    if not os.path.isfile(python):
        return "error", "embedding_python %s is not a file" % python
    row.note("%s -c 'import torch, transformers'" % python)
    try:
        done = subprocess.run([python, "-c", LOCAL_PROBE], capture_output=True, text=True,
                              timeout=IMPORT_TIMEOUT, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return "error", ("the import of torch and transformers in %s took more than %g s"
                         % (python, IMPORT_TIMEOUT))
    except OSError as exc:
        return "error", "cannot start %s: %s" % (python, exc)
    if done.returncode != 0:
        lines = (done.stderr or done.stdout or "").strip().splitlines()
        return "error", ("the import of torch and transformers in %s failed (exit code %d): %s"
                         % (python, done.returncode, lines[-1] if lines else "no output"))
    try:
        versions = json.loads(done.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return "error", "%s printed no versions: %s" % (python, done.stdout.strip()[:BODY_CHARS])
    found = "torch %s, transformers %s, device %s" % (
        versions.get("torch"), versions.get("transformers"), versions.get("device"))
    row.note(found)
    snapshot = hf_snapshot(embedding.model)
    if snapshot is None:
        return "warn", ("%s; the Hugging Face cache %s has no snapshot of %s: the first build "
                        "downloads it" % (found, hf_cache_dir(), embedding.model))
    row.note("snapshot %s" % snapshot[0])
    return "ok", ("%s; the model is in the Hugging Face cache (%.1f GB); no model load"
                  % (found, snapshot[1] / 1024 ** 3))


def sam3_endpoint(config):
    """Return the SAM3 endpoint: the key `sam3.endpoint` of the configuration, else the
    service of `derive`. Raise ValueError for a value that is not a URL."""
    section = config.get("sam3")
    endpoint = section.get("endpoint") if isinstance(section, dict) else None
    if endpoint is None:
        return derive.SAM3_ENDPOINT.rstrip("/")
    if not isinstance(endpoint, str) or not endpoint.startswith(("http://", "https://")):
        raise ValueError("`sam3.endpoint` MUST be an http or https URL")
    return endpoint.strip().rstrip("/")


def check_sam3(config):
    """Check the SAM3 service: `GET <endpoint>/health`."""
    row = Row("sam3", "sam3")
    try:
        endpoint = sam3_endpoint(config)
    except ValueError as exc:
        return row.result("error", "config.yaml: %s" % exc)
    upstream = UPSTREAM_RE.match(urllib.parse.urlsplit(endpoint).path)
    root = root_of(endpoint)
    try:
        state = gateway(row, root) if upstream else None
        if state is not None:
            skip = gateway_skip(state, upstream.group(1), root)
            if skip:
                return row.result(*skip)
        try:
            response, ms = row.call("GET", endpoint + "/health", CALL_TIMEOUT)
        except CallError as exc:
            if exc.timed_out:
                return row.result("error", "the service gave no answer in %g s"
                                  % CALL_TIMEOUT)
            raise
        if response.status_code != 200:
            return row.result("error", http_error(response))
        try:
            body = response.json()
            if body.get("status") != "ok":
                raise ValueError("status")
        except (ValueError, AttributeError):
            return row.result("error", "GET /health does not answer `status: ok`: %s"
                              % snippet(response))
        return row.result("ok", "answered in %d ms: %s" % (ms, ", ".join(
            "%s %s" % (key, body[key]) for key in ("model", "device", "dtype", "workers")
            if key in body)))
    except CallError as exc:
        return row.result("error", str(exc))


def remote_users(config_path):
    """Return the users of the vino-svoe.ru API: the website import, and each pipeline of
    the backend svoe-vino-ru whose `url` starts with the API."""
    users = ["the website import"]
    try:
        settings = pipelines.load(config_path)
    except embeddings.ConfigError:
        return users
    for name, entry, _error in settings.entries:
        if (entry is not None and entry.backend == pipelines.REMOTE_BACKEND
                and entry.remote["url"].startswith(import_website.API)):
            users.append("the pipeline %s" % name)
    return users


def check_remote(config_path):
    """Check the vino-svoe.ru API with the list request of the website import. The check
    sends no photo to `search-by-photo`."""
    row = Row("remote", REMOTE_NAME)
    row.note("used by %s; the check sends no photo" % ", ".join(remote_users(config_path)))
    try:
        response, ms = row.call("GET", import_website.LIST_URL % (1, 1), CALL_TIMEOUT)
    except CallError as exc:
        if exc.timed_out:
            return row.result("error", "the API gave no answer in %g s" % CALL_TIMEOUT)
        return row.result("error", str(exc))
    if response.status_code != 200:
        return row.result("error", http_error(response))
    try:
        total = response.json()["totalItems"]
        if not isinstance(total, int):
            raise TypeError("totalItems")
    except (ValueError, KeyError, TypeError):
        return row.result("error", "HTTP 200, but the body holds no `totalItems`: %s"
                          % snippet(response))
    return row.result("ok", "answered in %d ms; the catalogue of the API holds %d wines"
                      % (ms, total))


def check(config_path, kind, name):
    """Check one endpoint. Return its row. Raise KeyError for an unknown endpoint and
    embeddings.ConfigError when `config.yaml` cannot be read."""
    if kind == "vlm":
        return check_vlm(embeddings.read_config(config_path)[1], name)
    if kind == "embedding":
        return check_embedding(config_path, name)
    if kind == "sam3" and name == "sam3":
        return check_sam3(embeddings.read_config(config_path)[1])
    if kind == "remote" and name == REMOTE_NAME:
        return check_remote(config_path)
    raise KeyError(name)


# The list of the endpoints.

def endpoint_list(config_path):
    """Return the endpoints of `config.yaml` in the order of the page. An entry that is
    not valid keeps its error. Raise embeddings.ConfigError when the file cannot be read."""
    _path, config, _db = embeddings.read_config(config_path)
    out = []
    try:
        for entry in vlm_config.entries(config).values():
            out.append({"kind": "vlm", "name": entry.name, "model": entry.model,
                        "endpoint": entry.endpoint, "key_env": entry.key_env or None,
                        "error": None})
    except vlm_config.VlmConfigError as exc:
        out.append({"kind": "vlm", "name": "vlm", "model": None, "endpoint": None,
                    "key_env": None, "error": str(exc)})
    settings = embeddings.load_settings(config_path)
    for name, embedding, error in settings.entries:
        record = {"kind": "embedding", "name": name, "model": None, "endpoint": None,
                  "key_env": None, "error": error}
        if embedding is not None:
            record.update(model=embedding.model, backend=embedding.backend,
                          endpoint=embedding.base_url or "local: %s" % settings.python)
        out.append(record)
    record = {"kind": "sam3", "name": "sam3", "model": None, "endpoint": None,
              "key_env": None, "error": None}
    try:
        record["endpoint"] = sam3_endpoint(config)
        upstream = UPSTREAM_RE.match(urllib.parse.urlsplit(record["endpoint"]).path)
        record["model"] = upstream.group(1) if upstream else None
    except ValueError as exc:
        record["error"] = str(exc)
    out.append(record)
    out.append({"kind": "remote", "name": REMOTE_NAME, "model": None,
                "endpoint": import_website.API, "key_env": None, "error": None,
                "used_by": remote_users(config_path)})
    return out


# The status part.

def _part(make, *args):
    """Return the part of `make`, or its error. A part that fails MUST NOT stop the
    other parts of the page."""
    try:
        return make(*args)
    except Exception as exc:  # noqa: BLE001 - the page shows each failure of a part
        return {"error": "%s: %s" % (type(exc).__name__, exc)}


def server_part(server, config_path):
    started = getattr(server, "started_t", None)
    host, port = server.server_address[:2]
    return {"pid": os.getpid(), "started_at": now_iso(started) if started else None,
            "uptime_s": round(time.time() - started) if started else None,
            "python": platform.python_version(), "executable": sys.executable,
            "config": os.path.abspath(config_path), "address": "http://%s:%d" % (host, port),
            "error": None}


def _read_only(db_path):
    return sqlite3.connect(Path(db_path).as_uri() + "?mode=ro", uri=True, timeout=5)


def database_part(db_path):
    """Return the state of the database file: the schema version, the wines, the disk."""
    expected = len(labdb.schema_files())
    answer = {"path": db_path, "version": None, "expected_version": expected, "size": None,
              "states": None, "free": None, "total": None, "status": "error",
              "message": None, "error": None}
    if not os.path.isfile(db_path):
        answer["message"] = ("no database at %s; create it with `python3 pipeline/labdb.py "
                             "%s`" % (db_path, db_path))
        return answer
    answer["size"] = os.path.getsize(db_path)
    usage = shutil.disk_usage(os.path.dirname(db_path))
    answer.update(free=usage.free, total=usage.total)
    with closing(_read_only(db_path)) as conn:
        version = answer["version"] = conn.execute("PRAGMA user_version").fetchone()[0]
        if version != expected:
            answer["message"] = (
                "the database has schema version %d and this code needs version %d; run "
                "`python3 pipeline/labdb.py %s`" % (version, expected, db_path)
                if version < expected else "the database has schema version %d; this code "
                "knows version %d" % (version, expected))
            return answer
        counts = dict(conn.execute("SELECT state, count(*) FROM wine_catalog GROUP BY state"))
    answer["states"] = {state: counts.pop(state, 0) for state in WINE_STATES}
    answer["states"].update(counts)
    if usage.free < LOW_DISK:
        answer.update(status="warn", message="less than %d GB is free on the disk of the "
                      "database" % (LOW_DISK // 1024 ** 3))
    else:
        answer["status"] = "ok"
    return answer


def log_failures(path, now=None):
    """Return (the last WATCH_LINES failure lines of the watcher log in the last
    WATCH_WINDOW seconds, the count of such lines). A log that cannot be read gives
    ([], 0)."""
    try:
        with open(path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            fh.seek(max(0, fh.tell() - LOG_TAIL))
            text = fh.read().decode("utf-8", "replace")
    except OSError:
        return [], 0
    cutoff = (time.time() if now is None else now) - WATCH_WINDOW
    lines = []
    for line in text.splitlines():
        match = FAILURE_RE.match(line)
        if match and datetime.strptime(match.group(1), "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc).timestamp() >= cutoff:
            lines.append(line[:BODY_CHARS * 2])
    return lines[-WATCH_LINES:], len(lines)


def watcher_part(db_path, watcher_log):
    """Return the state of the image description watcher and its recent failures."""
    with closing(_read_only(db_path)) as conn:
        answer = image_descriptions.watcher_status(conn)
    answer["recent_failures"], answer["failures_last_hour"] = log_failures(watcher_log)
    answer.setdefault("error", None)
    return answer


def jobs_part(config_path, jobs_dir):
    """Return the embedding builds and the run jobs that run now."""
    settings = embeddings.load_settings(config_path)
    return {"builds": [job for job in embedding_routes.jobs_view(settings)
                       if job.get("state") in ("running", "stopping")],
            "runs": [job for job in run_jobs.jobs_view(jobs_dir)
                     if job.get("state") in run_jobs.ACTIVE],
            "error": None}


def gateway_roots(endpoints):
    """Return the roots of the endpoints with no key, in the order of the page, each with
    the models that `config.yaml` names on it."""
    roots = {}
    for item in endpoints:
        endpoint = item.get("endpoint") or ""
        if item["error"] or item["key_env"] or item["kind"] == "remote" or not (
                endpoint.startswith(("http://", "https://"))):
            continue
        models = roots.setdefault(root_of(endpoint), set())
        if item.get("model"):
            models.add(item["model"])
    return roots


def gateways_part(endpoints):
    """Return each llama-swap gateway of the endpoints with the models that run on it.
    One `GET /running` for each root; it loads no model."""
    out = []
    for root, used in gateway_roots(endpoints).items():
        record = {"root": root, "running": None, "error": None}
        try:
            response = requests.get(root + "/running", timeout=(STATUS_TIMEOUT, STATUS_TIMEOUT))
            running = response.json()["running"] if response.status_code == 200 else None
        except requests.RequestException as exc:
            record["error"] = explain(exc, root + "/running", STATUS_TIMEOUT)
            out.append(record)
            continue
        except (ValueError, KeyError, TypeError):
            running = None
        if not isinstance(running, list):
            continue  # not a llama-swap gateway
        record["running"] = [{"model": item.get("model"), "state": item.get("state"),
                              "ttl": item.get("ttl"), "name": item.get("name"),
                              "used": item.get("model") in used}
                             for item in running if isinstance(item, dict)]
        out.append(record)
    return out


def health_view(server, config_path, watcher_log):
    """Return the answer of `GET /api/health`."""
    try:
        endpoints, config_error = endpoint_list(config_path), None
    except embeddings.ConfigError as exc:
        endpoints, config_error = [], str(exc)
    jobs_dir = getattr(server, "run_jobs_dir", None) or run_jobs.JOBS_DIR
    return {
        "time": now_iso(), "config_error": config_error, "endpoints": endpoints,
        "status": {
            "server": _part(server_part, server, config_path),
            "database": _part(database_part, server.db_path),
            "watcher": _part(watcher_part, server.db_path, watcher_log),
            "jobs": _part(jobs_part, config_path, jobs_dir),
            "gateways": _part(gateways_part, endpoints),
        },
    }


def respond(server, method, path, read_body, watcher_log):
    """Return (HTTP code, body, content type, cache) of one request. A dict body is JSON.
    `watcher_log` is the log file of the image description watcher."""
    route = urllib.parse.urlsplit(path).path
    config_path = getattr(server, "config_path", None) or embeddings.CONFIG_PATH
    if route == PAGE:
        if method not in ("GET", "HEAD"):
            return _error(405, "use GET")
        return 200, lab_pages.page("health.html"), HTML_TYPE, NO_STORE
    if route == API:
        if method not in ("GET", "HEAD"):
            return _error(405, "use GET")
        return _json(200, health_view(server, config_path, watcher_log))
    if method != "POST":
        return _error(405, "use POST")
    raw = read_body(MAX_BODY)
    try:
        body = json.loads(raw) if raw else None
    except (UnicodeDecodeError, ValueError):
        body = None
    if not isinstance(body, dict):
        return _error(400, "the body MUST be one JSON object: {\"kind\": ..., \"name\": ...}")
    kind, name = body.get("kind"), body.get("name")
    if kind not in KINDS:
        return _error(400, "`kind` MUST be one of: %s" % ", ".join(KINDS))
    if not isinstance(name, str) or not name:
        return _error(400, "the body holds no `name`")
    try:
        return _json(200, check(config_path, kind, name))
    except KeyError:
        return _error(404, "config.yaml has no %s endpoint %s" % (kind, name))
    except embeddings.ConfigError as exc:
        return _error(503, str(exc))
