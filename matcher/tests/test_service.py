"""Unit tests for the configured mock matcher."""

from pathlib import Path
import tempfile
import unittest

import yaml

from matcher.service import ConfigError, load_matcher


CONFIG = Path(__file__).resolve().parent / "config.yaml"
TOKEN_CONFIG = Path(__file__).resolve().parent / "config.token.yaml"
DATA = Path(__file__).resolve().parent / "data"
OPENAPI = Path(__file__).resolve().parents[1] / "openapi.yaml"

EXPECTED = {
    "019c68d0.jpg": "tabia_pino_nuar",
    "02eef911.webp":
        "massandra-muskatel-belyy-belye-sorta-vinograda-beloe-sladkoe-16",
    "096ca74e.jpg": "donum_xxiv",
}


def valid_config():
    return {
        "matcher": {"pipeline": "test-mock"},
        "pipeline": [{
            "name": "test-mock",
            "backend": "mock",
            "answers": {},
            "unknown_slug": "",
        }],
    }


class MockMatcherTest(unittest.TestCase):
    def setUp(self):
        self.matcher = load_matcher(CONFIG)

    def test_configuration_selects_the_mock_pipeline(self):
        self.assertEqual(self.matcher.pipeline, "official-eval-mock")

    def test_test_config_uses_the_output_directory_environment_reference(self):
        self.assertEqual(
            self.matcher.output_dir,
            "{env:SVOE_VINO_MATCHER_OUTPUT_DIR}",
        )

    def test_config_without_authentication_has_no_token_environment(self):
        self.assertIsNone(self.matcher.token)
        self.assertIsNone(self.matcher.resolved_token({}))

    def test_token_config_uses_the_secret_environment_reference(self):
        matcher = load_matcher(TOKEN_CONFIG)
        self.assertEqual(
            matcher.token,
            "{env:SVOE_VINO_MATCHER_TOKEN}",
        )
        self.assertEqual(
            matcher.resolved_token({"SVOE_VINO_MATCHER_TOKEN": "test-secret"}),
            "test-secret",
        )
        self.assertNotIn("test-secret", TOKEN_CONFIG.read_text(encoding="utf-8"))

    def test_official_example_images_have_the_requested_slugs(self):
        for name, slug in EXPECTED.items():
            with self.subTest(name=name):
                self.assertEqual(
                    self.matcher.predict((DATA / name).read_bytes()), slug)

    def test_an_unknown_image_has_an_empty_slug(self):
        self.assertEqual(self.matcher.predict(b"not an official query image"), "")

    def test_openapi_document_describes_the_predict_contract(self):
        document = yaml.safe_load(OPENAPI.read_text(encoding="utf-8"))
        operation = document["paths"]["/v1/eval/predict"]["post"]
        request = operation["requestBody"]["content"]["multipart/form-data"]["schema"]
        response = operation["responses"]["200"]["content"]["application/json"]["schema"]

        self.assertEqual(document["openapi"], "3.1.0")
        self.assertEqual(operation["operationId"], "predict_image")
        self.assertEqual(request["$ref"], "#/components/schemas/Body_predict_image")
        self.assertEqual(response["$ref"], "#/components/schemas/Prediction")
        self.assertEqual(
            document["components"]["schemas"]["Body_predict_image"]["required"],
                         ["image"])
        self.assertEqual(document["components"]["schemas"]["Prediction"]["required"],
                         ["slug"])
        self.assertEqual(
            document["paths"]["/healthz"]["get"]["operationId"], "healthz")
        self.assertEqual(operation["security"], [{}, {"BearerAuth": []}])
        self.assertEqual(
            document["components"]["securitySchemes"]["BearerAuth"]["scheme"],
            "bearer",
        )
        for status in ("400", "401", "408", "413", "415", "422", "503"):
            self.assertIn(status, operation["responses"])

    def load_config(self, config):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.yaml"
            if isinstance(config, str):
                path.write_text(config, encoding="utf-8")
            else:
                path.write_text(yaml.safe_dump(config), encoding="utf-8")
            return load_matcher(path)

    def assert_config_error(self, config, pattern):
        with self.assertRaisesRegex(ConfigError, pattern):
            self.load_config(config)

    def test_config_without_output_dir_stays_supported(self):
        matcher = self.load_config(valid_config())
        self.assertIsNone(matcher.output_dir)
        self.assertIsNone(matcher.resolved_output_dir({}))

    def test_literal_output_dir_is_returned(self):
        config = valid_config()
        config["matcher"]["output_dir"] = "work/matcher-requests"
        matcher = self.load_config(config)
        self.assertEqual(
            matcher.resolved_output_dir({}),
            "work/matcher-requests",
        )

    def test_output_dir_environment_reference_is_resolved(self):
        config = valid_config()
        config["matcher"]["output_dir"] = "{env:MATCHER_TEST_OUTPUT_DIR}"
        matcher = self.load_config(config)
        self.assertEqual(
            matcher.resolved_output_dir({"MATCHER_TEST_OUTPUT_DIR": "/tmp/matcher"}),
            "/tmp/matcher",
        )

    def test_missing_output_dir_environment_variable_is_rejected(self):
        config = valid_config()
        config["matcher"]["output_dir"] = "{env:MATCHER_TEST_OUTPUT_DIR}"
        matcher = self.load_config(config)
        with self.assertRaisesRegex(ConfigError, "MATCHER_TEST_OUTPUT_DIR MUST be set"):
            matcher.resolved_output_dir({})

    def test_empty_output_dir_environment_variable_is_rejected(self):
        config = valid_config()
        config["matcher"]["output_dir"] = "{env:MATCHER_TEST_OUTPUT_DIR}"
        matcher = self.load_config(config)
        with self.assertRaisesRegex(ConfigError, "MATCHER_TEST_OUTPUT_DIR MUST be set"):
            matcher.resolved_output_dir({"MATCHER_TEST_OUTPUT_DIR": ""})

    def test_malformed_output_dir_environment_reference_is_rejected(self):
        for value in ("{env:}", "{env:9BAD}", "{env:BAD NAME}",
                      "prefix{env:GOOD}", "{env:GOOD}suffix", 12):
            with self.subTest(value=value):
                config = valid_config()
                config["matcher"]["output_dir"] = value
                self.assert_config_error(config, "exact \\{env:NAME\\} reference")

    def test_missing_or_empty_token_environment_variable_is_rejected(self):
        config = valid_config()
        config["matcher"]["token"] = "{env:MATCHER_TEST_TOKEN}"
        matcher = self.load_config(config)
        for environment in ({}, {"MATCHER_TEST_TOKEN": ""}):
            with self.subTest(environment=environment):
                with self.assertRaisesRegex(ConfigError, "MATCHER_TEST_TOKEN MUST be set"):
                    matcher.resolved_token(environment)

    def test_malformed_token_environment_reference_is_rejected(self):
        for value in ("", "MATCHER_TOKEN", "{env:}", "{env:9BAD}",
                      "{env:BAD NAME}", "prefix{env:GOOD}",
                      "{env:GOOD}suffix", 12):
            with self.subTest(value=value):
                config = valid_config()
                config["matcher"]["token"] = value
                self.assert_config_error(
                    config,
                    "token MUST be an exact \\{env:NAME\\} reference",
                )

        config = valid_config()
        config["matcher"]["token_env"] = "{env:MATCHER_TEST_TOKEN}"
        self.assert_config_error(config, "token_env was replaced by matcher.token")

    def test_broken_yaml_is_rejected(self):
        self.assert_config_error("matcher: [", "cannot read matcher configuration")

    def test_unknown_pipeline_is_rejected(self):
        config = valid_config()
        config["matcher"]["pipeline"] = "missing"
        self.assert_config_error(config, "unknown pipeline")

    def test_duplicate_pipeline_name_is_rejected(self):
        config = valid_config()
        config["pipeline"].append(dict(config["pipeline"][0]))
        self.assert_config_error(config, "duplicate pipeline name")

    def test_invalid_sha256_is_rejected(self):
        config = valid_config()
        config["pipeline"][0]["answers"] = {"not-a-sha256": "wine"}
        self.assert_config_error(config, "invalid SHA-256")

    def test_unsupported_backend_is_rejected(self):
        config = valid_config()
        config["pipeline"][0]["backend"] = "future"
        self.assert_config_error(config, "unsupported backend")


if __name__ == "__main__":
    unittest.main()
