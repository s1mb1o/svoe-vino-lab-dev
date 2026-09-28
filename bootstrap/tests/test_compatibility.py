from __future__ import annotations

import json
import unittest

import httpx

from scripts.check_compatibility import Settings, run_checks


class CompatibilityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            if request.url.path == "/qr/scan":
                return httpx.Response(
                    200,
                    json={
                        "count": 1,
                        "instances": [{"text": "svoe-vino-compatibility"}],
                    },
                )
            if request.url.path == "/sam/segment":
                return httpx.Response(
                    200,
                    json={
                        "count": 1,
                        "width": 320,
                        "height": 480,
                        "instances": [{"label": "wine bottle"}],
                    },
                )
            if request.url.path == "/v1/embeddings":
                return httpx.Response(
                    200,
                    json={"data": [{"embedding": [1.0] + [0.0] * 1151}]},
                )
            if request.url.path == "/custom/v1/chat/completions":
                return httpx.Response(
                    200,
                    json={
                        "choices": [
                            {"message": {"role": "assistant", "content": '{"status":"ready"}'}}
                        ]
                    },
                )
            if request.url.path == "/shield/classify":
                return httpx.Response(
                    200,
                    json={
                        "scores": {"dangerous": 0.1, "sexual": 0.2, "violence": 0.3},
                        "flagged": [],
                    },
                )
            return httpx.Response(404)

        self.client = httpx.Client(transport=httpx.MockTransport(handler))

    def tearDown(self) -> None:
        self.client.close()

    def settings(self, shield: bool = True) -> Settings:
        return Settings(
            qr_scanner_endpoint="https://models.example/qr/",
            sam3_endpoint="https://models.example/sam/",
            siglip2_endpoint="https://models.example/",
            vlm_endpoint="https://qwen.example/custom/v1/",
            vlm_model="qwen-runtime-alias",
            shieldgemma_endpoint="https://models.example/shield/" if shield else None,
            vlm_api_key="secret-value",
        )

    def test_all_configured_contracts_pass(self) -> None:
        report = run_checks(self.client, self.settings())
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["failed"], [])

        embedding_request = next(
            request for request in self.requests if request.url.path == "/v1/embeddings"
        )
        embedding_body = json.loads(embedding_request.content)
        self.assertEqual(embedding_body["model"], "siglip2-so400m-patch16-naflex")
        self.assertEqual(embedding_body["max_num_patches"], 512)

        qwen_request = next(
            request for request in self.requests if request.url.path.endswith("/chat/completions")
        )
        qwen_body = json.loads(qwen_request.content)
        self.assertEqual(qwen_body["model"], "qwen-runtime-alias")
        self.assertEqual(qwen_body["response_format"], {"type": "json_object"})
        self.assertEqual(qwen_request.headers["authorization"], "Bearer secret-value")

    def test_optional_shieldgemma_is_skipped(self) -> None:
        report = run_checks(self.client, self.settings(shield=False))
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["checks"]["shieldgemma"]["status"], "skipped")

    def test_missing_required_endpoint_fails_report(self) -> None:
        settings = self.settings()
        settings = Settings(**{**settings.__dict__, "sam3_endpoint": None})
        report = run_checks(self.client, settings)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["failed"], ["sam3"])


if __name__ == "__main__":
    unittest.main()
