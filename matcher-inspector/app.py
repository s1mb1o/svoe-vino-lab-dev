"""Read-only web interface for matcher requests and embedding bundles."""

from dataclasses import dataclass
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


REQUEST_ID = re.compile(r"^[0-9a-f]{32}$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
IMAGE_SUFFIXES = frozenset(
    {
        ".avif",
        ".bmp",
        ".gif",
        ".heic",
        ".jpeg",
        ".jpg",
        ".png",
        ".tif",
        ".tiff",
        ".webp",
    }
)
BUNDLE_FORMAT = "svoe-vino-matcher-bundle"
MAX_JSON_BYTES = 2 * 1024 * 1024
DEFAULT_LIMIT = 200


@dataclass(frozen=True)
class RequestRecord:
    """One archived matcher request."""

    date: str
    request_id: str
    directory: Path
    document: dict
    image_path: Path | None


@dataclass(frozen=True)
class BundleRecord:
    """One discovered matcher embedding bundle."""

    relative_path: str
    manifest: dict
    issues: tuple[str, ...]
    installed_bytes: int


def _read_json(path: Path) -> dict:
    """Read one small regular JSON file."""
    if path.is_symlink() or not path.is_file():
        raise ValueError("not a regular file")
    if path.stat().st_size > MAX_JSON_BYTES:
        raise ValueError("JSON file is larger than 2 MiB")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON root is not an object")
    return value


def _request_directory(root: Path, date: str, request_id: str) -> Path | None:
    """Return a confined request directory for valid archive identifiers."""
    if DATE.fullmatch(date) is None or REQUEST_ID.fullmatch(request_id) is None:
        return None
    directory = root / date / request_id
    if directory.is_symlink() or not directory.is_dir():
        return None
    return directory


def _request_image(directory: Path) -> Path | None:
    """Return the first supported regular image in one request directory."""
    images = []
    for path in directory.iterdir():
        if (
            path.name.startswith("image.")
            and path.suffix.lower() in IMAGE_SUFFIXES
            and not path.is_symlink()
            and path.is_file()
        ):
            images.append(path)
    return sorted(images, key=lambda path: path.name)[0] if images else None


def load_request(root: Path, date: str, request_id: str) -> RequestRecord | None:
    """Load one request from a confined archive path."""
    directory = _request_directory(root, date, request_id)
    if directory is None:
        return None
    try:
        document = _read_json(directory / "request.json")
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    return RequestRecord(
        date=date,
        request_id=request_id,
        directory=directory,
        document=document,
        image_path=_request_image(directory),
    )


def list_requests(root: Path, limit: int = DEFAULT_LIMIT) -> list[RequestRecord]:
    """Return the newest valid matcher requests."""
    if not root.is_dir():
        return []
    records = []
    for date_path in root.iterdir():
        if (
            date_path.is_symlink()
            or not date_path.is_dir()
            or DATE.fullmatch(date_path.name) is None
        ):
            continue
        for request_path in date_path.iterdir():
            record = load_request(root, date_path.name, request_path.name)
            if record is not None:
                records.append(record)
    records.sort(
        key=lambda record: (
            str(record.document.get("received_at") or ""),
            record.date,
            record.request_id,
        ),
        reverse=True,
    )
    return records[:limit]


def _bundle_record(root: Path, manifest_path: Path) -> BundleRecord | None:
    """Read one bundle manifest and check its declared payload files."""
    try:
        manifest = _read_json(manifest_path)
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if manifest.get("format") != BUNDLE_FORMAT:
        return None

    bundle_root = manifest_path.parent
    issues = []
    installed_bytes = manifest_path.stat().st_size
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        issues.append("manifest.files is missing or empty")
    else:
        for name, properties in sorted(files.items()):
            if (
                not isinstance(name, str)
                or Path(name).name != name
                or not isinstance(properties, dict)
            ):
                issues.append("manifest.files has an invalid entry")
                continue
            payload = bundle_root / name
            if payload.is_symlink() or not payload.is_file():
                issues.append("%s is missing" % name)
                continue
            size = payload.stat().st_size
            installed_bytes += size
            expected = properties.get("bytes")
            if isinstance(expected, int) and size != expected:
                issues.append(
                    "%s has size %d; manifest specifies %d" % (name, size, expected)
                )

    try:
        relative_path = bundle_root.relative_to(root).as_posix() or "."
    except ValueError:
        return None
    return BundleRecord(
        relative_path=relative_path,
        manifest=manifest,
        issues=tuple(issues),
        installed_bytes=installed_bytes,
    )


def list_bundles(root: Path, requests_root: Path) -> list[BundleRecord]:
    """Find matcher bundle manifests below the configured data root."""
    if not root.is_dir():
        return []
    request_path = requests_root.resolve(strict=False)
    records = []
    for current, directories, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        kept = []
        for name in directories:
            candidate = current_path / name
            if candidate.is_symlink():
                continue
            if candidate.resolve(strict=False) == request_path:
                continue
            kept.append(name)
        directories[:] = kept
        if "manifest.json" not in files:
            continue
        record = _bundle_record(root, current_path / "manifest.json")
        if record is not None:
            records.append(record)
    records.sort(key=lambda record: record.relative_path)
    return records


def _text(value, default="—") -> str:
    """Return one escaped scalar for HTML output."""
    if value is None or value == "":
        return default
    return escape(str(value))


def _format_bytes(value) -> str:
    """Format an integer byte count."""
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        return "—"
    size = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return "%d %s" % (size, unit) if unit == "B" else "%.1f %s" % (size, unit)
        size /= 1024
    return "—"


def _layout(title: str, body: str) -> str:
    """Wrap content in the shared page layout."""
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>%s · Matcher Inspector</title>
  <style>
    :root { color-scheme: light dark; --bg:#f4f5f7; --panel:#fff; --text:#17202a;
      --muted:#667085; --line:#d8dde5; --accent:#315efb; --good:#067647;
      --warn:#b54708; --code:#eef1f5; }
    @media (prefers-color-scheme: dark) { :root { --bg:#0d1117; --panel:#161b22;
      --text:#e6edf3; --muted:#9da7b3; --line:#30363d; --accent:#7da2ff;
      --good:#56d692; --warn:#ffb86b; --code:#0d1117; } }
    * { box-sizing:border-box; } body { margin:0; background:var(--bg); color:var(--text);
      font:15px/1.5 ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
    a { color:var(--accent); text-decoration:none; } a:hover { text-decoration:underline; }
    header { border-bottom:1px solid var(--line); background:var(--panel); }
    header div, main { width:min(1500px,calc(100%% - 32px)); margin:auto; }
    header div { display:flex; align-items:center; gap:22px; min-height:58px; }
    header strong { letter-spacing:.01em; } nav { display:flex; gap:16px; }
    main { padding:24px 0 48px; } h1 { font-size:26px; margin:0 0 18px; }
    h2 { font-size:19px; margin:28px 0 12px; } h3 { margin:0 0 8px; font-size:16px; }
    .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(250px,1fr)); gap:12px; }
    .card { background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:16px; }
    .metric { font-size:24px; font-weight:650; } .muted { color:var(--muted); }
    .ok { color:var(--good); } .warning { color:var(--warn); }
    .table-wrap { overflow:auto; background:var(--panel); border:1px solid var(--line);
      border-radius:10px; } table { width:100%%; border-collapse:collapse; white-space:nowrap; }
    th,td { padding:10px 12px; text-align:left; border-bottom:1px solid var(--line); }
    th { color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.04em; }
    tr:last-child td { border-bottom:0; } code,pre { font:13px/1.5 ui-monospace,SFMono-Regular,
      Menlo,Consolas,monospace; background:var(--code); } code { padding:2px 5px; border-radius:4px; }
    pre { overflow:auto; padding:14px; border-radius:8px; border:1px solid var(--line); }
    dl { display:grid; grid-template-columns:minmax(130px,220px) 1fr; gap:7px 14px; margin:0; }
    dt { color:var(--muted); } dd { margin:0; overflow-wrap:anywhere; }
    .request-layout { display:grid; grid-template-columns:minmax(300px,520px) 1fr; gap:18px; }
    .preview { display:block; max-width:100%%; max-height:70vh; margin:auto; border-radius:8px;
      object-fit:contain; background:repeating-conic-gradient(#ddd 0 25%%,#fff 0 50%%) 50%%/20px 20px; }
    details { margin-top:12px; } summary { cursor:pointer; color:var(--accent); }
    .pill { display:inline-block; border:1px solid currentColor; border-radius:999px;
      padding:1px 8px; font-size:12px; } .bundle { min-width:0; }
    .bundle pre { max-height:340px; } .empty { padding:24px; text-align:center; color:var(--muted); }
    @media (max-width:850px) { .request-layout { grid-template-columns:1fr; }
      dl { grid-template-columns:1fr; gap:2px; } dd { margin-bottom:8px; } }
  </style>
</head>
<body>
<header><div><strong>Matcher Inspector</strong><nav><a href="/">Requests and bundles</a><a href="/healthz">Health</a></nav></div></header>
<main>%s</main>
</body>
</html>""" % (escape(title), body)


def _response_fields(document: dict) -> tuple[object, object]:
    response = document.get("response")
    if not isinstance(response, dict):
        return None, None
    return response.get("status_code"), response.get("slug")


def render_home(requests: list[RequestRecord], bundles: list[BundleRecord]) -> str:
    """Render the request list and installed bundle list."""
    request_rows = []
    for record in requests:
        document = record.document
        status, slug = _response_fields(document)
        image = document.get("image") if isinstance(document.get("image"), dict) else {}
        request_rows.append(
            """<tr>
<td><a href="/requests/%s/%s"><code>%s</code></a></td>
<td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td>
</tr>"""
            % (
                record.date,
                record.request_id,
                escape(record.request_id[:12]),
                _text(document.get("received_at")),
                _text(document.get("client_ip")),
                _text(status),
                _text(slug),
                _format_bytes(image.get("size_bytes")),
            )
        )
    if request_rows:
        request_table = """<div class="table-wrap"><table>
<thead><tr><th>Request</th><th>Received UTC</th><th>Client</th><th>Status</th><th>Slug</th><th>Image</th></tr></thead>
<tbody>%s</tbody></table></div>""" % "".join(request_rows)
    else:
        request_table = '<div class="card empty">No archived requests were found.</div>'

    bundle_cards = []
    for bundle in bundles:
        manifest = bundle.manifest
        embedding = (
            manifest.get("embedding")
            if isinstance(manifest.get("embedding"), dict)
            else {}
        )
        vectors = (
            manifest.get("vectors") if isinstance(manifest.get("vectors"), dict) else {}
        )
        counts = (
            manifest.get("counts") if isinstance(manifest.get("counts"), dict) else {}
        )
        shape = vectors.get("shape")
        rows = shape[0] if isinstance(shape, list) and len(shape) >= 1 else None
        dimension = shape[1] if isinstance(shape, list) and len(shape) >= 2 else None
        views = embedding.get("views")
        view_names = ", ".join(sorted(views)) if isinstance(views, dict) else "—"
        if bundle.issues:
            state = '<span class="pill warning">Incomplete</span>'
            issues = "<ul>%s</ul>" % "".join(
                "<li>%s</li>" % escape(issue) for issue in bundle.issues
            )
        else:
            state = '<span class="pill ok">Complete</span>'
            issues = ""
        raw = escape(json.dumps(manifest, ensure_ascii=False, indent=2))
        bundle_cards.append(
            """<article class="card bundle">
<h3>%s %s</h3>
<dl>
<dt>Path</dt><dd><code>%s</code></dd>
<dt>Created</dt><dd>%s</dd>
<dt>Model</dt><dd>%s</dd>
<dt>Backend</dt><dd>%s</dd>
<dt>Vectors</dt><dd>%s × %s</dd>
<dt>Wines</dt><dd>%s</dd>
<dt>Views</dt><dd>%s</dd>
<dt>Installed size</dt><dd>%s</dd>
</dl>%s
<details><summary>Complete manifest</summary><pre>%s</pre></details>
</article>"""
            % (
                _text(embedding.get("name"), "Unnamed bundle"),
                state,
                escape(bundle.relative_path),
                _text(manifest.get("created_at")),
                _text(embedding.get("model")),
                _text(embedding.get("backend")),
                _text(rows),
                _text(dimension),
                _text(counts.get("wines")),
                escape(view_names),
                _format_bytes(bundle.installed_bytes),
                issues,
                raw,
            )
        )
    if not bundle_cards:
        bundle_cards.append(
            '<div class="card empty">No embedding bundle manifests were found.</div>'
        )

    body = """<h1>Matcher state</h1>
<div class="grid">
  <div class="card"><div class="metric">%d</div><div class="muted">latest archived requests shown</div></div>
  <div class="card"><div class="metric">%d</div><div class="muted">embedding bundles found</div></div>
</div>
<h2>Requests</h2>%s
<h2>Installed embedding bundles</h2><div class="grid">%s</div>""" % (
        len(requests),
        len(bundles),
        request_table,
        "".join(bundle_cards),
    )
    return _layout("Matcher state", body)


def render_request(record: RequestRecord) -> str:
    """Render one archived request."""
    document = record.document
    request = (
        document.get("request") if isinstance(document.get("request"), dict) else {}
    )
    image = document.get("image") if isinstance(document.get("image"), dict) else {}
    status, slug = _response_fields(document)
    preview = (
        (
            '<img class="preview" src="/requests/%s/%s/image" alt="Archived matcher input">'
            % (record.date, record.request_id)
        )
        if record.image_path
        else ('<div class="empty">No supported image file was found.</div>')
    )
    raw = escape(json.dumps(document, ensure_ascii=False, indent=2))
    body = """<h1>Request <code>%s</code></h1>
<div class="request-layout">
  <section class="card">%s</section>
  <section class="card"><h2 style="margin-top:0">Result</h2>
    <dl>
      <dt>Received UTC</dt><dd>%s</dd>
      <dt>Completed UTC</dt><dd>%s</dd>
      <dt>Duration</dt><dd>%s ms</dd>
      <dt>Client</dt><dd>%s</dd>
      <dt>HTTP status</dt><dd>%s</dd>
      <dt>Slug</dt><dd>%s</dd>
      <dt>Method and path</dt><dd>%s %s</dd>
      <dt>Original filename</dt><dd>%s</dd>
      <dt>Media type</dt><dd>%s</dd>
      <dt>Dimensions</dt><dd>%s × %s</dd>
      <dt>Size</dt><dd>%s</dd>
      <dt>SHA-256</dt><dd><code>%s</code></dd>
    </dl>
    <details open><summary>Complete request journal</summary><pre>%s</pre></details>
  </section>
</div>""" % (
        escape(record.request_id),
        preview,
        _text(document.get("received_at")),
        _text(document.get("completed_at")),
        _text(document.get("duration_ms")),
        _text(document.get("client_ip")),
        _text(status),
        _text(slug),
        _text(request.get("method")),
        _text(request.get("path")),
        _text(image.get("original_filename")),
        _text(image.get("content_type")),
        _text(image.get("width")),
        _text(image.get("height")),
        _format_bytes(image.get("size_bytes")),
        _text(image.get("sha256")),
        raw,
    )
    return _layout("Request %s" % record.request_id[:12], body)


class InspectorServer(ThreadingHTTPServer):
    """HTTP server with configured read-only roots."""

    daemon_threads = True

    def __init__(self, address, requests_root: Path, bundle_root: Path):
        self.requests_root = requests_root
        self.bundle_root = bundle_root
        super().__init__(address, InspectorHandler)


class InspectorHandler(BaseHTTPRequestHandler):
    """Serve the matcher inspector pages."""

    server_version = "MatcherInspector/1.0"

    def do_GET(self):  # noqa: N802 - BaseHTTPRequestHandler API
        """Serve one safe read-only route."""
        path = unquote(urlsplit(self.path).path)
        if path == "/healthz":
            self._send_json(
                {
                    "status": "ok",
                    "requests_root_available": self.server.requests_root.is_dir(),
                    "bundle_root_available": self.server.bundle_root.is_dir(),
                }
            )
            return
        if path == "/favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return
        if path == "/":
            requests = list_requests(self.server.requests_root)
            bundles = list_bundles(self.server.bundle_root, self.server.requests_root)
            self._send_html(render_home(requests, bundles))
            return

        parts = [part for part in path.split("/") if part]
        if len(parts) in (3, 4) and parts[0] == "requests":
            record = load_request(self.server.requests_root, parts[1], parts[2])
            if record is None:
                self._send_error(HTTPStatus.NOT_FOUND, "Request was not found.")
                return
            if len(parts) == 3:
                self._send_html(render_request(record))
                return
            if parts[3] == "image" and record.image_path is not None:
                self._send_image(record.image_path)
                return
        self._send_error(HTTPStatus.NOT_FOUND, "Page was not found.")

    def _common_headers(self, content_type: str, length: int):
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; "
            "base-uri 'none'; frame-ancestors 'none'",
        )

    def _send_html(self, content: str, status=HTTPStatus.OK):
        body = content.encode("utf-8")
        self.send_response(status)
        self._common_headers("text/html; charset=utf-8", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, content: dict, status=HTTPStatus.OK):
        body = (json.dumps(content, ensure_ascii=False) + "\n").encode("utf-8")
        self.send_response(status)
        self._common_headers("application/json; charset=utf-8", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _send_image(self, path: Path):
        body = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self._common_headers(content_type, len(body))
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, status: HTTPStatus, message: str):
        body = _layout(
            str(status.value), "<h1>%d</h1><p>%s</p>" % (status.value, escape(message))
        )
        self._send_html(body, status)


def run():
    """Start the matcher inspector HTTP service."""
    requests_root = Path(
        os.environ.get("MATCHER_INSPECTOR_REQUESTS_ROOT", "/data/requests")
    ).resolve(strict=False)
    bundle_root = Path(
        os.environ.get("MATCHER_INSPECTOR_BUNDLE_ROOT", "/data")
    ).resolve(strict=False)
    port_text = os.environ.get("MATCHER_INSPECTOR_PORT", "8080")
    try:
        port = int(port_text)
    except ValueError as exc:
        raise SystemExit("MATCHER_INSPECTOR_PORT MUST be an integer") from exc
    if not 1 <= port <= 65535:
        raise SystemExit("MATCHER_INSPECTOR_PORT MUST be from 1 through 65535")
    server = InspectorServer(("0.0.0.0", port), requests_root, bundle_root)
    print("matcher-inspector listening on 0.0.0.0:%d" % port, flush=True)
    server.serve_forever()


if __name__ == "__main__":
    run()
