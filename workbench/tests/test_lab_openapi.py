import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import lab_openapi  # noqa: E402
import lab_server  # noqa: E402


def operations(text):
    """Convert one `METHOD /path` line per operation to an operation set."""
    return {(path, method.lower()) for method, path in
            (line.split(maxsplit=1) for line in text.splitlines() if line.strip())}


EXPECTED_OPERATIONS = operations("""
GET /
GET /docs
GET /openapi.yaml
GET /openapi.json
GET /dataset
GET /dataset/{slug}
GET /dataset/{slug}/patch
GET /dataset/{slug}/{preview}/{sha256}
GET /embedding
GET /clusters
GET /testset
GET /runs
GET /recognize
GET /health
GET /website-import.js
GET /images/{folder}/{sha256}.{extension}
GET /embeddings/{name}/images/{sha256}_{view}.png
GET /website-import/{run}/images/{sha256}.{extension}
GET /recognize/photo/{sha256}.{extension}
GET /api/dataset
POST /api/wine
GET /api/wine-index
POST /api/wine-index
POST /api/wine-state
POST /api/wine-name
POST /api/dataset-gtin
DELETE /api/dataset-gtin
POST /api/dataset-qr-url
DELETE /api/dataset-qr-url
POST /api/dataset-patch
DELETE /api/dataset-patch
POST /api/dataset-alternative
DELETE /api/dataset-alternative
POST /api/dataset-alternative-type
POST /api/dataset-alternative-cut
DELETE /api/dataset-alternative-cut
POST /api/dataset-alternative-recut
POST /api/dataset-atlas-binding
DELETE /api/dataset-atlas-binding
POST /api/dataset-atlas-binding-approve
POST /api/dataset-comment
DELETE /api/dataset-comment
POST /api/dataset-favorite
POST /api/dataset-beverage-type
POST /api/dataset-similar
DELETE /api/dataset-similar
POST /api/dataset-tag
DELETE /api/dataset-tag
POST /api/image-description
GET /api/image-description-status
GET /api/image-detail-failures
GET /api/image-description-reply
GET /api/image-label-descriptions
POST /api/image-label-description
DELETE /api/image-label-description
GET /api/embeddings
POST /api/embeddings/build-all
GET /api/embeddings/{name}
POST /api/embeddings/{name}/build
POST /api/embeddings/{name}/stop
POST /api/embeddings/{name}/open
GET /api/embeddings/{name}/log
GET /api/embedding-jobs
GET /api/clusters
POST /api/clusters/build-all
GET /api/clusters/{name}
POST /api/clusters/{name}/build
POST /api/clusters/{name}/note
GET /api/testset
POST /api/testset-label
POST /api/testset-delete
POST /api/testset-photo-comment
POST /api/testset-photo-comment-remove
POST /api/testset-photo-tag
POST /api/testset-photo-tag-remove
POST /api/testset-box
POST /api/testset-move
POST /api/testset-upload
POST /api/testset-fetch
GET /api/testset-from-run
POST /api/testset-from-run
POST /api/testset-new
POST /api/testset-rename
GET /api/runs
GET /api/run
GET /api/run-clusters
GET /api/run-inputs
GET /api/run-candidate
GET /api/run-steps
GET /api/run-configurations
GET /api/run-jobs
POST /api/run-jobs
POST /api/run-jobs/{name}/stop
GET /api/website-import
POST /api/website-import/start
POST /api/website-import/stop
GET /api/website-import/{run}/diff
POST /api/website-import/{run}/apply
GET /api/recognize
POST /api/recognize
GET /api/health
POST /api/health/check
""")


class UniqueKeyLoader(yaml.SafeLoader):
    """Load YAML and reject a mapping that repeats one key."""


def unique_mapping(loader, node, deep=False):
    answer = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in answer:
            raise ValueError("duplicate YAML key %r at line %d" %
                             (key, key_node.start_mark.line + 1))
        answer[key] = loader.construct_object(value_node, deep=deep)
    return answer


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


class LabOpenApiDocumentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (ROOT / "docs" / "lab-openapi.yaml").read_text(encoding="utf-8")
        cls.document = yaml.load(cls.raw, Loader=UniqueKeyLoader)

    def test_document_identity(self):
        self.assertEqual(self.document["openapi"], "3.1.0")
        self.assertEqual(self.document["info"]["title"], "Svoe Vino lab API")
        self.assertEqual(self.document["servers"][0]["url"],
                         "http://127.0.0.1:8168")

    def test_document_has_exact_route_inventory(self):
        actual = set()
        for path, path_item in self.document["paths"].items():
            for method in path_item:
                if method in {"get", "post", "put", "patch", "delete", "head",
                              "options", "trace"}:
                    actual.add((path, method))
        self.assertEqual(actual, EXPECTED_OPERATIONS)

    def test_operations_have_unique_ids_summaries_and_success_responses(self):
        identifiers = []
        for path, method in sorted(EXPECTED_OPERATIONS):
            operation = self.document["paths"][path][method]
            with self.subTest(method=method, path=path):
                self.assertTrue(operation.get("operationId"))
                self.assertTrue(operation.get("summary"))
                self.assertTrue(operation.get("responses"))
                self.assertTrue(any(str(code).startswith(("2", "3"))
                                    for code in operation["responses"]))
            identifiers.append(operation["operationId"])
        self.assertEqual(len(identifiers), len(set(identifiers)))

    def test_every_local_reference_resolves(self):
        references = []

        def walk(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    if key == "$ref" and isinstance(child, str) and child.startswith("#/"):
                        references.append(child)
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(self.document)
        self.assertTrue(references)
        for reference in references:
            value = self.document
            with self.subTest(reference=reference):
                for token in reference[2:].split("/"):
                    value = value[token.replace("~1", "/").replace("~0", "~")]


class LabOpenApiRouteTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.server = lab_server.make_server(
            str(Path(self.directory.name) / "unused.sqlite3"), port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = "http://127.0.0.1:%d" % self.server.server_address[1]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.directory.cleanup()

    def request(self, path, method="GET"):
        request = urllib.request.Request(self.base + path, method=method)
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, response.headers, response.read()
        except urllib.error.HTTPError as exc:
            try:
                return exc.code, exc.headers, exc.read()
            finally:
                exc.close()

    def test_yaml_route_returns_the_checked_in_file(self):
        status, headers, body = self.request("/openapi.yaml")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "application/yaml; charset=utf-8")
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(body, Path(lab_openapi.SPEC_FILE).read_bytes())

    def test_json_route_returns_the_complete_yaml_document(self):
        status, headers, body = self.request("/openapi.json")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
        self.assertEqual(json.loads(body), yaml.safe_load(Path(lab_openapi.SPEC_FILE).read_text()))

    def test_docs_route_returns_pinned_dark_aware_swagger_ui(self):
        status, headers, body = self.request("/docs")
        page = body.decode("utf-8")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn("swagger-ui-dist@5.33.0", page)
        self.assertIn('url: "/openapi.yaml"', page)
        self.assertIn("prefers-color-scheme: dark", page)
        self.assertIn('href="/dataset"', page)

    def test_head_returns_headers_without_a_body(self):
        status, headers, body = self.request("/openapi.yaml", method="HEAD")
        self.assertEqual(status, 200)
        self.assertEqual(int(headers["Content-Length"]),
                         len(Path(lab_openapi.SPEC_FILE).read_bytes()))
        self.assertEqual(body, b"")

    def test_non_read_method_returns_405(self):
        status, headers, body = self.request("/docs", method="POST")
        self.assertEqual(status, 405)
        self.assertIn("application/json", headers["Content-Type"])
        self.assertIn("answers GET alone", json.loads(body)["error"])


class LabOpenApiFailureTest(unittest.TestCase):
    def test_missing_document_returns_404_from_both_spec_routes(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = str(Path(directory) / "missing.yaml")
            with mock.patch.object(lab_openapi, "SPEC_FILE", missing):
                for route in ("/openapi.yaml", "/openapi.json"):
                    with self.subTest(route=route):
                        code, body, content_type, cache = lab_openapi.respond("GET", route)
                        self.assertEqual((code, content_type, cache),
                                         (404, lab_openapi.JSON_TYPE, "no-store"))
                        self.assertIn("not present", body["error"])

    def test_invalid_yaml_returns_500_from_json_and_raw_bytes_from_yaml(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.yaml"
            path.write_text("paths: [", encoding="utf-8")
            with mock.patch.object(lab_openapi, "SPEC_FILE", str(path)):
                code, body, _, _ = lab_openapi.respond("GET", "/openapi.yaml")
                self.assertEqual((code, body), (200, b"paths: ["))
                code, body, content_type, _ = lab_openapi.respond("GET", "/openapi.json")
                self.assertEqual((code, content_type), (500, lab_openapi.JSON_TYPE))
                self.assertIn("cannot read", body["error"])


if __name__ == "__main__":
    unittest.main()
