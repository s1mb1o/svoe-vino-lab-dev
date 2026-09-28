import contextlib
import io
import json
import os
import tempfile
import unittest

import embedding_lab  # noqa: F401  (puts pipeline/ on sys.path)
from test_clusters import ClusterLab

import build_clusters  # noqa: E402
import clusters  # noqa: E402


class CommandTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fixture = ClusterLab(self.tmp.name)

    def tearDown(self):
        self.fixture.close()
        self.tmp.cleanup()

    def test_build_writes_the_embedding_scoped_artifact(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = build_clusters.main([
                "--config", self.fixture.lab.config_path,
                "--name", "gw",
                "--full-threshold", "0.96",
                "--label-threshold", "0.97",
            ])
        self.assertEqual(code, 0)
        answer = json.loads(output.getvalue())
        self.assertEqual(answer["embedding"], "gw")
        self.assertEqual(answer["settings"], {
            "full_threshold": 0.96, "label_threshold": 0.97, "min_cluster_size": 2})
        self.assertEqual(answer["file"], clusters.CLUSTERS_FILE)
        self.assertTrue(os.path.isfile(os.path.join(
            self.fixture.lab.entry_dir(), clusters.CLUSTERS_FILE)))

    def test_without_options_the_config_gives_the_thresholds(self):
        self.fixture.set_clusters({"full_threshold": 0.98})
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = build_clusters.main([
                "--config", self.fixture.lab.config_path, "--name", "gw"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["settings"], {
            "full_threshold": 0.98, "label_threshold": clusters.DEFAULT_THRESHOLD,
            "min_cluster_size": clusters.MIN_CLUSTER_SIZE})

    def test_unknown_embedding_is_an_error(self):
        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            code = build_clusters.main([
                "--config", self.fixture.lab.config_path, "--name", "absent"])
        self.assertEqual(code, 2)
        self.assertIn("config.yaml has no embedding absent", error.getvalue())


if __name__ == "__main__":
    unittest.main()
