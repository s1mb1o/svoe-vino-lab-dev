"""OpenAPI routes of the lab server.

`docs/lab-openapi.yaml` is the checked-in contract. This module serves that file as
YAML and JSON and supplies the Swagger UI page at `/docs`. Read
`docs/plans/80_lab-server-openapi.md`.
"""
import json
import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC_FILE = os.path.join(ROOT, "docs", "lab-openapi.yaml")
SWAGGER_UI = "5.33.0"

DOCS = "/docs"
YAML = "/openapi.yaml"
JSON = "/openapi.json"
ROUTES = frozenset((DOCS, YAML, JSON))
NO_STORE = "no-store"
JSON_TYPE = "application/json; charset=utf-8"


def handles(route):
    """Tell whether `route` belongs to the OpenAPI document."""
    return route in ROUTES


def _json(code, value):
    return code, value, JSON_TYPE, NO_STORE


def _missing():
    return _json(404, {"error": "docs/lab-openapi.yaml is not present"})


def respond(method, route):
    """Return `(code, body, content type, cache)` for one OpenAPI request."""
    if method not in ("GET", "HEAD"):
        return _json(405, {"error": "the route %s answers GET alone" % route})
    if route == DOCS:
        return 200, PAGE, "text/html; charset=utf-8", NO_STORE
    if not os.path.isfile(SPEC_FILE):
        return _missing()
    if route == YAML:
        try:
            with open(SPEC_FILE, "rb") as fh:
                return 200, fh.read(), "application/yaml; charset=utf-8", NO_STORE
        except OSError as exc:
            return _json(500, {"error": "cannot read the document: %s" % exc})
    try:
        with open(SPEC_FILE, encoding="utf-8") as fh:
            spec = yaml.safe_load(fh)
        if not isinstance(spec, dict):
            raise ValueError("the document MUST be one YAML object")
    except (OSError, ValueError, yaml.YAMLError) as exc:
        return _json(500, {"error": "cannot read the document: %s" % exc})
    # Convert once here. `lab_server.Handler` sends strings without a second JSON pass.
    return 200, json.dumps(spec, ensure_ascii=False), JSON_TYPE, NO_STORE


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Svoe Vino lab API</title>
<link rel="stylesheet"
      href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@__V__/swagger-ui.css">
<style>
:root { color-scheme: light dark; }
body { margin: 0; background: #f6f6f4; }
.swagger-ui .topbar { display: none; }
#nav {
  font: 14px/1.4 system-ui, sans-serif;
  padding: 10px 20px; border-bottom: 1px solid #d8d8d2;
}
#nav a { color: #6b4a7a; margin-right: 14px; }
@media (prefers-color-scheme: dark) {
  body { background: #15151a; }
  #nav { border-color: #34343f; }
  #nav a { color: #b28ec8; }
  #swagger-ui { filter: invert(88%) hue-rotate(180deg); }
  #swagger-ui .microlight { filter: invert(100%) hue-rotate(180deg); }
}
</style>
</head>
<body>
<div id="nav"><a href="/dataset">Dataset</a><a
  href="/embedding">Embeddings</a><a href="/clusters">Clusters</a><a
  href="/testset">Testset</a><a href="/runs">Runs</a><a
  href="/recognize">Recognize</a><a href="/health">Health</a><a
  href="/openapi.yaml">openapi.yaml</a><a href="/openapi.json">openapi.json</a></div>
<div id="swagger-ui"></div>
<script crossorigin
  src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@__V__/swagger-ui-bundle.js">
</script>
<script>
window.onload = function () {
  window.ui = SwaggerUIBundle({
    url: "/openapi.yaml",
    dom_id: "#swagger-ui",
    deepLinking: true,
    tryItOutEnabled: true,
    docExpansion: "list",
    defaultModelsExpandDepth: 0
  });
};
</script>
</body>
</html>
""".replace("__V__", SWAGGER_UI)
