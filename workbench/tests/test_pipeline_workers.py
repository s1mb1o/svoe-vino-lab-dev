"""Check configured worker counts and run overrides through the wrapped pipeline."""
import contextlib
import io
import json
import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import testset_fixture as FX  # noqa: E402
import barcode  # noqa: E402
import cluster_rerank  # noqa: E402
import embedding_run  # noqa: E402
import import_testset  # noqa: E402
import pipelines  # noqa: E402
import run_job  # noqa: E402
import run_jobs  # noqa: E402


class ConcurrentBackend:
    """Wait for the expected concurrent queries without an inference service."""

    def __init__(self, workers):
        self.id, self.top_k = "profile", 1
        self.spec = {"id": self.id, "workers": 1, "top_k": 1}
        self.catalogue = types.SimpleNamespace(state={})
        self.barrier = threading.Barrier(workers)
        self.lock = threading.Lock()
        self.active = self.peak = 0

    def ask(self, path):
        with self.lock:
            self.active += 1
            self.peak = max(self.peak, self.active)
        try:
            self.barrier.wait(timeout=5)
            return [{"slug": "wine-a", "score": 1.0, "rank": 1}], 1, 200, None
        finally:
            with self.lock:
                self.active -= 1


class PipelineWorkersTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.db, self.schema = FX.make_database(self.root)
        photos = {"wine-a/%d.jpg" % i: str(i).encode() for i in range(4)}
        labels = {"wine-a": {"%d.jpg" % i: {"label": "positive"} for i in range(4)}}
        import_testset.import_testset(
            self.db, "my", FX.write_set(self.root, photos, labels), lambda m: None, self.schema)
        self.config = self.root / "config.yaml"
        self.config.write_text(json.dumps({
            "rootdir": str(self.root), "database_file": self.db,
            "embeddings": [{"name": "gw", "backend": "openai", "model": "m",
                            "base_url": "http://example.test/v1", "views": {
                                "full": {"steps": [{"step": "segment", "target": "package"}]}}}],
            "vlm": [{"name": "qwen3.5-9b-nvfp4", "protocol": "openai",
                     "thinking_field": "chat_template_kwargs",
                     "endpoint": "http://example.test/v1", "model": "m"}],
            "pipeline": [{"name": "profile", "backend": "embedding", "embedding": "gw",
                          "workers": 4, "barcode": {}, "rerank": {}}],
        }), encoding="utf-8")

    def tearDown(self):
        self.directory.cleanup()

    def test_run_dialog_reports_the_configured_default(self):
        with mock.patch.object(run_jobs, "runnable", return_value=(True, None)):
            view = run_jobs.configurations_view(
                pipelines.load(str(self.config)), str(self.root / "jobs"), "my")
        self.assertEqual(view["configurations"][0]["workers"], 4)

    def test_run_dialog_preserves_an_explicit_worker_override(self):
        settings = pipelines.load(str(self.config))
        process = types.SimpleNamespace(pid=1234)
        with mock.patch.object(run_jobs, "runnable", return_value=(True, None)), \
                mock.patch.object(run_jobs, "job", return_value={"state": None}), \
                mock.patch.object(run_jobs, "_PROCESSES", {}), \
                mock.patch.object(run_jobs.subprocess, "Popen", return_value=process) as start:
            code, _ = run_jobs.start(settings, str(self.root / "jobs"), {
                "configuration": "profile", "set": "my", "workers": 2})
        self.assertEqual(code, 202)
        command = start.call_args.args[0]
        self.assertEqual(command[command.index("--workers") + 1], "2")

    def test_the_wrapped_runner_uses_four_workers_and_respects_overrides(self):
        for override, expected in ((None, 4), (2, 2), (1, 1)):
            with self.subTest(override=override):
                backend = ConcurrentBackend(expected)
                book = types.SimpleNamespace(describe=lambda: {}, trigger=lambda c, w: (None, []))
                out = io.StringIO()
                args = ["--config", str(self.config), "--name", "profile", "--set", "my",
                        "--jobs-dir", str(self.root / ("jobs-%s" % expected)),
                        "--runs-dir", str(self.root / ("runs-%s" % expected))]
                if override is not None:
                    args += ["--workers", str(override)]
                with mock.patch.object(embedding_run, "build_backend", return_value=backend), \
                        mock.patch.object(cluster_rerank, "RuleBook", return_value=book), \
                        mock.patch.object(barcode, "Decoder"), contextlib.redirect_stdout(out):
                    code = run_job.main(args)
                self.assertEqual(code, 0, out.getvalue())
                events = [json.loads(line) for line in out.getvalue().splitlines()]
                self.assertEqual(events[0]["workers"], expected)
                self.assertEqual(events[-1]["event"], "done")
                self.assertEqual(events[-1]["answered"], 4)
                self.assertEqual(backend.peak, expected)
                run_dir = self.root / ("runs-%s" % expected) / events[-1]["run_id"]
                meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
                self.assertEqual(meta["options"]["workers"], expected)
                self.assertEqual(meta["backend"]["workers"], 4)

    def test_only_the_requested_profile_changes_its_default(self):
        settings = pipelines.load()
        four = {"barcode-rerank-siglip2-512-crop",
                "barcode-rerank-siglip2-p512-crop",
                "barcode-rerank-siglip2-p1024-crop",
                "barcode-rerank-siglip2-512-seg",
                "barcode-rerank-siglip2-512-rot5-seg",
                "barcode-rerank-siglip2-p512-seg",
                "barcode-rerank-siglip2-p512-rot5-seg",
                "barcode-rerank-siglip2-p1024-seg"}
        for name in (*sorted(four), "rerank-siglip2-512-crop",
                     "barcode-siglip2-512-crop", "siglip2-512-crop"):
            with self.subTest(name=name):
                expected = 4 if name in four else 1
                self.assertEqual(settings.find(name).workers, expected)


if __name__ == "__main__":
    unittest.main()
