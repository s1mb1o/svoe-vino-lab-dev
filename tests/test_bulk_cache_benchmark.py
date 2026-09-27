"""Verify experiment cache routing and complete-result checks without inference."""
import concurrent.futures
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import benchmark_bulk_cache as bulk


class CacheRoutingTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.old_root = bulk.model_cache.ROOT
        bulk.model_cache.ROOT = str(self.root / "production")
        self.addCleanup(setattr, bulk.model_cache, "ROOT", self.old_root)

    def test_barcode_is_isolated_model_cache_is_reused_and_globals_restore(self):
        old_path, old_read = bulk.model_cache.path_of, bulk.model_cache.READ
        fields = {"model": "sam3", "images": ["photo"]}
        codes = {"model": "barcode", "images": ["photo"]}
        bulk.model_cache.store(fields, {"regions": []}, 10)
        bulk.model_cache.store(codes, {"production": True}, 10)
        with bulk.barcode_cache(self.root / "experiment"):
            self.assertIsNotNone(bulk.model_cache.lookup(fields))
            self.assertIsNone(bulk.model_cache.lookup(codes))
            bulk.model_cache.store(codes, {"experimental": True}, 10)
            self.assertEqual(bulk.model_cache.lookup(codes)["answer"], {"experimental": True})
        self.assertEqual((bulk.model_cache.path_of, bulk.model_cache.READ), (old_path, old_read))
        self.assertEqual(bulk.model_cache.lookup(codes)["answer"], {"production": True})
        with bulk.barcode_cache(self.root / "experiment"):
            self.assertEqual(bulk.model_cache.lookup(codes)["answer"], {"experimental": True})

    def test_four_threads_do_not_change_root_or_cross_namespaces(self):
        fields = [{"model": name, "images": [str(i)]}
                  for i in range(8) for name in ("barcode", "sam3")]
        with bulk.barcode_cache(self.root / "experiment"):
            with concurrent.futures.ThreadPoolExecutor(4) as pool:
                list(pool.map(lambda f: bulk.model_cache.store(f, f["images"], 1), fields))
                paths = list(pool.map(bulk.model_cache.path_of, fields))
            for f, path in zip(fields, paths):
                expected = "experiment" if f["model"] == "barcode" else "production"
                self.assertEqual(Path(path).relative_to(self.root).parts[0], expected)
                self.assertEqual(bulk.model_cache.lookup(f)["answer"], f["images"])

    def test_exception_restores_cache_flags(self):
        old = bulk.model_cache.path_of, bulk.model_cache.READ
        with self.assertRaises(RuntimeError):
            with bulk.barcode_cache(self.root / "experiment"):
                raise RuntimeError("stop")
        self.assertEqual((bulk.model_cache.path_of, bulk.model_cache.READ), old)


class CompletionTest(unittest.TestCase):
    def test_catalogue_fingerprint_observes_live_rows_and_variant_groups(self):
        conn = mock.Mock()
        conn.execute.return_value = [("wine", "Name")]
        wines = [{"slug": "wine", "columns": [("main", "original")]}]
        sources = {"original": {"path": "/images/original.png", "cuts": {"label": None}}}
        groups = {"wine": {"wine", "other"}}
        with mock.patch.object(bulk.embeddings, "open_database", return_value=conn), \
                mock.patch.object(bulk.embeddings, "read_inputs", return_value=(wines, sources)), \
                mock.patch.object(bulk.benchmark, "load_groups", return_value=groups):
            initial = bulk.catalogue_identity("db", "my")
            self.assertEqual(initial, bulk.catalogue_identity("db", "my"))
            sources["original"]["cuts"]["label"] = {"sha256": "new-label", "box": (1, 2, 3, 4)}
            self.assertNotEqual(initial, bulk.catalogue_identity("db", "my"))
            after_cut = bulk.catalogue_identity("db", "my")
            groups["wine"].add("another")
            self.assertNotEqual(after_cut, bulk.catalogue_identity("db", "my"))
        conn.execute.assert_any_call("BEGIN")

    def test_index_identity_includes_vector_bytes_and_prepared_image_names(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.json").write_text("{}")
            (root / "vectors.npy").write_bytes(b"one")
            with mock.patch.object(bulk.embeddings, "read_index", return_value={"vectors_file": "vectors.npy"}), \
                    mock.patch.object(bulk.embeddings, "image_names", return_value={"one.png"}) as names:
                initial = bulk.index_identity(root)
                (root / "vectors.npy").write_bytes(b"two")
                self.assertNotEqual(initial, bulk.index_identity(root))
                after_vector = bulk.index_identity(root)
                names.return_value = set()
                self.assertNotEqual(after_vector, bulk.index_identity(root))

    def test_missing_or_changed_query_coverage_is_not_success(self):
        row = {"query_id": "q1", "image_path": "wine/photo.jpg", "image_sha256": "abc",
               "slug": "wine", "label": "positive", "truth": ["wine"]}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "run.json").write_text(json.dumps({"run_id": "test", "answered": 1, "finished": "now"}))
            (root / "queries.jsonl").write_text(json.dumps(row) + "\n")
            (root / "results.jsonl").write_text("")
            with self.assertRaisesRegex(ValueError, "complete baseline query set"):
                bulk.summarize(root, [row], 1, 0)
            result = dict(row, latency_ms=100, error=None, trace={"steps": [{"id": "barcode", "ms": 2, "cached": True}]})
            (root / "results.jsonl").write_text(json.dumps(result) + "\n")
            (root / "metrics.json").write_text("{}")
            summary = bulk.summarize(root, [row], 1, 10)
            self.assertTrue(summary["complete"])
            self.assertEqual(summary["barcode_cache_hits"], 1)
            result["trace"]["steps"].append({"id": "cluster_rules", "out": {"error": "VLM failed"}})
            (root / "results.jsonl").write_text(json.dumps(result) + "\n")
            summary = bulk.summarize(root, [row], 1, 10)
            self.assertFalse(summary["complete"])
            self.assertEqual(summary["degraded_queries"], 1)
            result["trace"]["steps"].pop()
            result["trace"]["steps"][0]["error"] = "decoder failed"
            (root / "results.jsonl").write_text(json.dumps(result) + "\n")
            summary = bulk.summarize(root, [row], 1, 10)
            self.assertFalse(summary["complete"])
            self.assertEqual(summary["barcode_step_errors"], 1)
            result["error"] = "model failed"
            (root / "results.jsonl").write_text(json.dumps(result) + "\n")
            self.assertFalse(bulk.summarize(root, [row], 1, 10)["complete"])

    def test_current_profile_uses_only_existing_internal_endpoints(self):
        settings = bulk.embeddings.load_settings()
        with mock.patch.object(bulk.embedding_run, "build_pipeline_backend") as build:
            pipeline, entry = bulk.internal_profile(settings, bulk.PROFILE)
        self.assertEqual(pipeline.name, bulk.PROFILE)
        self.assertEqual(entry.backend, "openai")
        build.assert_not_called()

    def test_external_sam3_is_rejected_before_backend_build(self):
        settings = bulk.embeddings.load_settings()
        with mock.patch.object(bulk.derive, "SAM3_ENDPOINT", "https://external.example/sam3"), \
                mock.patch.dict(bulk.os.environ, {"SAM3_ENDPOINT": "https://external.example/sam3"}):
            with self.assertRaisesRegex(ValueError, "GX10 endpoints"):
                bulk.internal_profile(settings, bulk.PROFILE)

    def test_sam3_environment_mismatch_is_not_silently_ignored(self):
        settings = bulk.embeddings.load_settings()
        with mock.patch.dict(bulk.os.environ, {"SAM3_ENDPOINT": "http://192.168.86.14:9999/sam3"}):
            with self.assertRaisesRegex(ValueError, "SAM3_ENDPOINT differs"):
                bulk.internal_profile(settings, bulk.PROFILE)


if __name__ == "__main__":
    unittest.main()
