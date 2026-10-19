"""Serve a labeling folder (index.html, images/, boxes.json) on this machine and keep the
reviews the page sends in reviews.json next to them.

    uv run python scripts/label_server.py out/labeling/2026-10-18 [--port 8765]

GET /reviews returns every review; POST /reviews/<image> replaces the review of that image.
"""

from __future__ import annotations

import argparse
import json
import os
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

lock = threading.Lock()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, folder: Path, **kwargs):
        self.folder = folder
        super().__init__(*args, directory=str(folder), **kwargs)

    def reviews(self) -> dict:
        path = self.folder / "reviews.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def send_json(self, code: int, body) -> None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/reviews":
            with lock:
                return self.send_json(200, self.reviews())
        if path in ("/", "/index.html"):
            # The page is written for the artifact viewer, which wraps it in a document.
            page = (self.folder / "index.html").read_text(encoding="utf-8")
            data = ('<!doctype html><html lang="ru"><head><meta charset="utf-8">'
                    '<meta name="viewport" content="width=device-width,initial-scale=1">'
                    '<style>body{margin:0}[hidden]{display:none!important}</style></head><body>'
                    + page + "</body></html>").encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
            return
        return super().do_GET()

    def do_POST(self):
        if not self.path.startswith("/reviews/"):
            return self.send_json(404, {"error": "not found"})
        name = unquote(self.path[len("/reviews/"):])
        if "/" in name or not (self.folder / "images" / name).exists():
            return self.send_json(400, {"error": "unknown image"})
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        with lock:
            reviews = self.reviews()
            reviews[name] = body
            tmp = self.folder / "reviews.json.tmp"
            tmp.write_text(json.dumps(reviews, ensure_ascii=False, indent=1), encoding="utf-8")
            os.replace(tmp, self.folder / "reviews.json")
        return self.send_json(200, {"ok": True})

    def log_message(self, fmt, *args):
        if self.command == "POST":
            super().log_message(fmt, *args)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("folder")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    folder = Path(args.folder).resolve()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), partial(Handler, folder=folder))
    print(f"http://localhost:{args.port}/ serves {folder}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
