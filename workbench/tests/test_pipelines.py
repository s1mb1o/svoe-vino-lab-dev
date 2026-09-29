"""Tests of the pipelines of the lab (plan 34): the key `pipeline` of `config.yaml` and
`pipeline/pipelines.py`. The tests of each backend are in `test_remote_run.py` and
`test_embedding_run.py`."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import embeddings  # noqa: E402
import pipelines  # noqa: E402

REMOTE = {"name": "remote", "backend": "svoe-vino-ru",
          "url": "https://api.example.test/v1/wines/search-by-photo"}
OTHER = {"name": "other", "backend": "svoe-vino-ru", "url": "http://127.0.0.1:9/v1/other"}
GW = {"name": "gw", "backend": "openai", "base_url": "http://x/v1", "model": "m",
      "views": {"full": {"steps": [{"step": "segment", "target": "package"}]}}}


class LoadTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.path = self.root / "config.yaml"

    def tearDown(self):
        self.directory.cleanup()

    def load(self, **keys):
        config = dict({"rootdir": str(self.root), "database_file": "lab.sqlite3"}, **keys)
        self.path.write_text(json.dumps(config), encoding="utf-8")
        return pipelines.load(str(self.path))

    def test_the_entries_keep_the_file_order_and_the_paths(self):
        settings = self.load(pipeline=[REMOTE, OTHER])
        self.assertEqual([(name, p.backend, error) for name, p, error in settings.entries],
                         [("remote", "svoe-vino-ru", None), ("other", "svoe-vino-ru", None)])
        self.assertEqual(settings.config_path, str(self.path))
        self.assertEqual(settings.db_path, str(self.root / "lab.sqlite3"))
        self.assertEqual(settings.find("remote").remote["url"], REMOTE["url"])
        self.assertEqual(settings.find("other").remote["url"], OTHER["url"])

    def test_a_file_with_no_key_pipeline_has_no_pipeline(self):
        self.assertEqual(self.load(embeddings=[]).entries, [])

    def test_the_key_pipeline_must_be_a_list(self):
        with self.assertRaisesRegex(embeddings.ConfigError, "the key `pipeline` MUST be a list"):
            self.load(pipeline={"remote": REMOTE})

    def test_a_file_with_no_database_file_is_refused(self):
        self.path.write_text(json.dumps({"pipeline": [REMOTE]}), encoding="utf-8")
        with self.assertRaisesRegex(embeddings.ConfigError, "database_file"):
            pipelines.load(str(self.path))

    def test_an_entry_that_is_not_valid_keeps_its_error(self):
        settings = self.load(pipeline=[REMOTE, {"name": "gw", "backend": "openai"}, REMOTE,
                                       dict(REMOTE, name="Bad Name"), "text"])
        self.assertEqual([name for name, _, _ in settings.entries],
                         ["remote", "gw", "remote", "Bad Name", "#5"])
        errors = [error for _, _, error in settings.entries]
        self.assertIsNone(errors[0])
        self.assertIn("the key `embeddings`", errors[1])
        self.assertIn("earlier entry", errors[2])
        self.assertIn("MUST match", errors[3])
        self.assertIn("MUST be a mapping", errors[4])
        self.assertEqual(settings.find("remote").backend, "svoe-vino-ru")
        with self.assertRaisesRegex(embeddings.ConfigError, "the key `embeddings`"):
            settings.find("gw")
        with self.assertRaises(KeyError):
            settings.find("other")

    def test_the_two_keys_do_not_share_their_entries(self):
        settings = self.load(embeddings=[GW], pipeline=[REMOTE])
        self.assertEqual([name for name, _, _ in settings.entries], ["remote"])
        self.assertEqual([name for name, _, _ in
                          embeddings.load_settings(str(self.path)).entries], ["gw"])


class MockTest(unittest.TestCase):
    def test_the_backend_mock_is_gone(self):
        # The owner removed the pipeline `mock` and its code (2026-09-26T00:26:27+0300).
        with self.assertRaisesRegex(embeddings.ConfigError,
                                    "backend MUST be one of: svoe-vino-ru, embedding"):
            pipelines.Pipeline({"name": "mock", "backend": "mock"})


class EmbeddingPipelineTest(LoadTest):
    """The backend `embedding`: a pipeline names one entry of the key `embeddings` (owner
    answer of 2026-09-26T00:12:24+0300)."""

    def test_a_pipeline_names_a_valid_embedding_entry(self):
        settings = self.load(embeddings=[GW], pipeline=[
            {"name": "gw", "backend": "embedding", "embedding": "gw"}])
        pipeline = settings.find("gw")
        self.assertEqual((pipeline.backend, pipeline.embedding, pipeline.remote),
                         ("embedding", "gw", None))
        self.assertIsNone(pipelines.Pipeline(REMOTE).embedding)

    def test_the_named_entry_must_be_a_valid_embedding_entry(self):
        broken = {"name": "broken", "backend": "grpc"}
        settings = self.load(embeddings=[GW, broken], pipeline=[
            {"name": "a", "backend": "embedding", "embedding": "other"},
            {"name": "b", "backend": "embedding", "embedding": "broken"}])
        errors = dict((name, error) for name, _, error in settings.entries)
        self.assertIn("the embedding other is not an entry of the key `embeddings`",
                      errors["a"])
        self.assertIn("the embedding broken is not valid", errors["b"])

    def test_the_entry_takes_the_key_embedding_alone(self):
        wrong = [({}, "embedding MUST be the name"), ({"embedding": "Bad Name"}, "MUST be"),
                 ({"embedding": "gw", "url": "http://y"}, "the backend embedding takes no url")]
        for keys, message in wrong:
            with self.subTest(keys=keys):
                with self.assertRaisesRegex(embeddings.ConfigError, message):
                    pipelines.Pipeline(dict({"name": "p", "backend": "embedding"}, **keys))

    def test_workers_default_to_one_and_accept_an_explicit_count(self):
        raw = {"name": "p", "backend": "embedding", "embedding": "gw"}
        self.assertEqual(pipelines.Pipeline(raw).workers, 1)
        self.assertEqual(pipelines.Pipeline(dict(raw, workers=4)).workers, 4)

    def test_workers_must_be_a_positive_integer(self):
        for value in (None, 0, -1, True, 1.5, "4"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(embeddings.ConfigError, "workers MUST be an integer"):
                    pipelines.Pipeline({"name": "p", "backend": "embedding", "embedding": "gw",
                                        "workers": value})


class QueryViewsTest(LoadTest):
    """The key `views` of a pipeline of the backend `embedding`: the steps of the test
    photo (owner answers of 2026-09-26T00:52:41+0300 and 00:57:59)."""

    AS_IS = [{"step": "white_background"}, {"step": "resize", "max_size": 1024}]

    def pipeline(self, steps, view="full"):
        return pipelines.Pipeline({"name": "p", "backend": "embedding", "embedding": "gw",
                                   "views": {view: {"steps": steps}}})

    def test_the_steps_get_their_defaults(self):
        self.assertEqual(self.pipeline(self.AS_IS).views, {"full": [
            {"step": "white_background"},
            {"step": "resize", "max_size": 1024, "aspect": "keep", "upscale": False}]})
        crop = self.pipeline([{"step": "segment", "target": "package"}] + self.AS_IS)
        self.assertEqual([step["step"] for step in crop.views["full"]],
                         ["segment", "white_background", "resize"])
        self.assertIsNone(pipelines.Pipeline(
            {"name": "p", "backend": "embedding", "embedding": "gw"}).views)

    def test_the_step_rules_of_a_test_photo(self):
        wrong = [
            ([{"step": "resize", "max_size": 1024}, {"step": "segment", "target": "package"}],
             "the first step MUST be `segment`"),
            ([{"step": "resize", "max_size": 1024}, {"step": "remove_background"},
              {"step": "white_background"}], "directly after `segment`"),
            ([], "at least one step"),
            ([{"step": "blur"}], "unknown step"),
        ]
        for steps, message in wrong:
            with self.subTest(steps=steps):
                with self.assertRaisesRegex(embeddings.ConfigError, message):
                    self.pipeline(steps)
        with self.assertRaisesRegex(embeddings.ConfigError, "unknown view: side"):
            self.pipeline(self.AS_IS, view="side")
        with self.assertRaisesRegex(embeddings.ConfigError, "the backend svoe-vino-ru takes no views"):
            pipelines.Pipeline(dict(REMOTE, views={"full": {"steps": self.AS_IS}}))

    def test_an_entry_of_embeddings_still_starts_with_segment(self):
        with self.assertRaisesRegex(embeddings.ConfigError, "the first step MUST be `segment`"):
            embeddings.check_steps("full", {"steps": self.AS_IS})

    def test_a_view_of_the_pipeline_must_be_a_view_of_the_entry(self):
        settings = self.load(embeddings=[GW], pipeline=[
            {"name": "ok", "backend": "embedding", "embedding": "gw",
             "views": {"full": {"steps": self.AS_IS}}},
            {"name": "bad", "backend": "embedding", "embedding": "gw",
             "views": {"label": {"steps": self.AS_IS}}}])
        errors = dict((name, error) for name, _, error in settings.entries)
        self.assertIsNone(errors["ok"])
        self.assertIn("the embedding gw has no view label", errors["bad"])


class ProjectConfigTest(unittest.TestCase):
    def test_the_project_config_holds_the_remote_pipeline(self):
        found = {name: (p.backend if p else None, error)
                 for name, p, error in pipelines.load().entries}
        self.assertEqual(found.get("vino-svoe-search-by-photo"), ("svoe-vino-ru", None))
        # The owner removed `mock` (00:26:27) and the pipeline of the embedding name
        # (about 01:07; the answer of 01:19:00 to the session d3).
        self.assertNotIn("mock", found)
        self.assertNotIn("gx10-siglip2-so400m-patch16-naflex-p256", found)

    def test_the_project_config_holds_the_two_basic_pipelines(self):
        settings = pipelines.load()
        for name, kinds in (("siglip2-p256", ["white_background", "resize"]),
                            ("siglip2-p256-crop", ["segment", "white_background", "resize"])):
            with self.subTest(name=name):
                pipeline = settings.find(name)
                self.assertEqual(pipeline.embedding, "gx10-siglip2-so400m-patch16-naflex-p256")
                self.assertEqual(list(pipeline.views), ["full"])
                self.assertEqual([step["step"] for step in pipeline.views["full"]], kinds)
                self.assertEqual(pipeline.views["full"][-1]["max_size"], 1024)

    def test_the_project_config_holds_the_two_android_pipelines_without_barcode(self):
        settings = pipelines.load()
        for name, embedding in (
                ("android-siglip2-base-224-dis-seg", "android-siglip2-base-224-dis-white"),
                ("android-siglip2-base-224-sam3-seg", "android-siglip2-base-224-sam3-white")):
            with self.subTest(name=name):
                pipeline = settings.find(name)
                self.assertEqual((pipeline.backend, pipeline.embedding, pipeline.workers),
                                 ("embedding", embedding, 1))
                self.assertIsNone(pipeline.barcode)
                self.assertIsNone(pipeline.views)

    def test_no_embedding_entry_of_the_project_config_has_a_pipeline_backend(self):
        _, config, _ = embeddings.read_config()
        backends = {entry.get("backend") for entry in config.get("embeddings") or []}
        self.assertTrue(backends)
        self.assertFalse(backends & set(pipelines.BACKENDS))


if __name__ == "__main__":
    unittest.main()
