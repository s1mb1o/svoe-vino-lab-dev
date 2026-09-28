from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi.responses import Response
from fastapi.testclient import TestClient

import gateway


class GatewayTest(unittest.TestCase):
    def setUp(self) -> None:
        gateway.configure({"sam3": "http://127.0.0.1:19001"})
        self.client = TestClient(gateway.app)

    def test_lists_active_model(self) -> None:
        with patch.object(gateway, "_readiness_failures", AsyncMock(return_value={})):
            response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["active_models"], ["sam3"])

    def test_health_fails_when_active_model_is_not_ready(self) -> None:
        failures = {"sam3": "connection refused"}
        with patch.object(gateway, "_readiness_failures", AsyncMock(return_value=failures)):
            response = self.client.get("/health")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["status"], "not-ready")
        self.assertEqual(response.json()["failures"], failures)

    def test_unknown_upstream_model_is_not_found(self) -> None:
        self.assertEqual(self.client.get("/upstream/unknown/health").status_code, 404)

    def test_embedding_request_requires_model(self) -> None:
        self.assertEqual(self.client.post("/v1/embeddings", json={"input": []}).status_code, 400)

    def test_routes_upstream_model(self) -> None:
        forwarded = AsyncMock(return_value=Response(content=b"ok", status_code=200))
        with patch.object(gateway, "_forward", forwarded):
            response = self.client.get("/upstream/sam3/health")
        self.assertEqual(response.text, "ok")
        self.assertEqual(forwarded.await_args.args[1], "http://127.0.0.1:19001/health")


if __name__ == "__main__":
    unittest.main()
