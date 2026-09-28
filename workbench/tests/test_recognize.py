"""Tests of the runner script of the Recognize page (plan 55): `pipeline/recognize.py`.

The lab, the fake gateway, and the fake SAM3 come from `test_embedding_run.py`. No test
calls gx10.
"""
import contextlib
import io
import json
import os
from unittest import mock

import test_embedding_run as TE  # noqa: E402  (puts pipeline/ and scripts/ on sys.path)
import build_embeddings  # noqa: E402
import derive  # noqa: E402
import embedding_run  # noqa: E402
import embeddings  # noqa: E402
import recognize  # noqa: E402


class RecognizeScriptTest(TE.Temporary):
    def setUp(self):
        super().setUp()
        self.gateway = TE.FakeGateway()
        self.lab = TE.catalogue_lab(self.root, base_url=self.gateway.base_url)
        os.makedirs(self.lab.entry_dir(), exist_ok=True)
        with contextlib.redirect_stdout(io.StringIO()):
            build_embeddings.run(embeddings.load_settings(self.lab.config_path).find("gw"),
                                 self.lab.db_path, self.lab.entry_dir())
        TE.add_pipelines(self.lab, TE.PIPE)
        self.photo = str(self.root / "green.png")
        with open(self.photo, "wb") as fh:
            fh.write(TE.png(TE.query_photo("green")))

    def tearDown(self):
        self.gateway.close()
        super().tearDown()

    def main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(derive, "Sam3Client", TE.FakeSam3), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = recognize.main(["--config", self.lab.config_path, *args])
        return code, out.getvalue(), err.getvalue()

    def test_the_answer_holds_the_candidates_the_trace_and_the_spec(self):
        code, out, err = self.main("--name", "gw-pipe", "--photo", self.photo)
        self.assertEqual(code, 0, err)
        self.assertEqual(len(out.splitlines()), 1)
        answer = json.loads(out)
        self.assertEqual(set(answer), {"spec", "candidates", "latency_ms", "http_status",
                                       "error", "trace", "build_ms"})
        self.assertEqual((answer["http_status"], answer["error"]), (200, None))
        self.assertEqual(answer["candidates"][0]["slug"], "green")
        self.assertTrue(all("items" not in cand for cand in answer["candidates"]))
        self.assertEqual((answer["spec"]["id"], answer["spec"]["embedding"]), ("gw-pipe", "gw"))
        self.assertEqual([step["id"] for step in answer["trace"]["steps"]][:2],
                         ["input", "sam3-package"])
        self.assertGreaterEqual(answer["build_ms"], 0)

    def test_output_of_a_module_goes_to_stderr(self):
        real = embedding_run.build_pipeline_backend

        def noisy(*args, **kwargs):
            print("a line of a module")
            return real(*args, **kwargs)

        with mock.patch.object(embedding_run, "build_pipeline_backend", noisy):
            code, out, err = self.main("--name", "gw-pipe", "--photo", self.photo)
        self.assertEqual(code, 0, err)
        self.assertIn("a line of a module", err)
        self.assertEqual(json.loads(out)["candidates"][0]["slug"], "green")

    def test_a_failure_before_the_question_gives_the_status_1(self):
        code, out, _ = self.main("--name", "nope", "--photo", self.photo)
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out), {"error": "ConfigError: config.yaml has no pipeline nope"})

    def test_a_failure_inside_the_question_is_the_answer(self):
        code, out, err = self.main("--name", "gw-pipe", "--photo", str(self.root / "none.png"))
        self.assertEqual(code, 0, err)
        answer = json.loads(out)
        self.assertEqual(answer["candidates"], [])
        self.assertIn("Pillow cannot read the photo", answer["error"])
        self.assertIn("error", answer["trace"]["steps"][-1])
