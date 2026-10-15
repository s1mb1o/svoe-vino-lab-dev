"""Native metrics, fallback, configuration and input/cache identity contracts."""
import copy
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import embeddings
import local_comparison as local
import local_comparison_worker as worker
import pipelines


class LocalComparisonTests(unittest.TestCase):
    def setUp(self):
        self.candidates = [{"slug": "a", "score": .94, "rank": 1},
                           {"slug": "b", "score": .91, "rank": 2}]
        self.refs = [[{"source_sha256": "a", "sha256": "ra"}],
                     [{"source_sha256": "b", "sha256": "rb"}]]

    def test_distances_ascending_and_visual_scores_preserved(self):
        original = copy.deepcopy(self.candidates)
        out, evidence = local.rerank(self.candidates, self.refs,
            [{"score": .5, "cached": True}, {"score": .1, "cached": False}], "lpips-score")
        self.assertEqual([c["slug"] for c in out], ["b", "a"])
        self.assertEqual([c["score"] for c in out], [.91, .94])
        self.assertEqual(out[0]["comparison"]["value"], .1)
        self.assertEqual((evidence["cached_pairs"], evidence["fresh_pairs"]), (1, 1))
        self.assertEqual(self.candidates, original)

    def test_inliers_and_cosines_descending(self):
        for method in ("lightglue-score", "superglue-score", "loftr-score", "dinov2-score",
                       "dinov3-patch_score", "siglip-score"):
            field = method.split("-", 1)[1]
            out, _ = local.rerank(self.candidates, self.refs,
                                  [{field: 1}, {field: 2}], method)
            self.assertEqual([c["slug"] for c in out], ["b", "a"])

    def test_unaligned_reference_does_not_get_zero_distance(self):
        out, _ = local.rerank(self.candidates, self.refs,
            [{"aligned_distance": None}, {"aligned_distance": .4}], "dists-aligned_distance")
        self.assertEqual(out[0]["slug"], "b")
        self.assertIsNone(out[1]["comparison"]["value"])

    def test_multiple_references_choose_best_and_ties_keep_base_rank(self):
        refs = [[self.refs[0][0], {"source_sha256": "a2", "sha256": "ra2"}], self.refs[1]]
        out, _ = local.rerank(self.candidates, refs,
            [{"score": .5}, {"score": .1}, {"score": .1}], "lpips-score")
        self.assertEqual(out[0]["slug"], "a")
        self.assertEqual(out[0]["comparison"]["reference"]["source_sha256"], "a2")

    def test_all_missing_or_failed_values_keep_bottle_order(self):
        for rows, reason in (([{"aligned_distance": None}] * 2, "no_valid_comparison"),
                             ([{"error": "worker failed"}, {}], "method_error")):
            out, evidence = local.rerank(self.candidates, self.refs, rows,
                                         "lpips-aligned_distance")
            self.assertEqual(out, self.candidates)
            self.assertEqual(evidence["reason"], reason)
            self.assertFalse(evidence["applied"])

    def test_nonfinite_scores_rejected(self):
        for value in (float("nan"), float("inf"), True, "0.2"):
            with self.assertRaises(ValueError):
                local.rerank(self.candidates, self.refs, [{"score": value}, {"score": 1}],
                             "dinov2-score")

    def test_each_configured_approach_is_valid_and_unique(self):
        settings = pipelines.load(str(Path(__file__).resolve().parents[1] / "config.yaml"))
        entries = [p for n, p, error in settings.entries if n.startswith("lab-compare-") and not error]
        self.assertEqual(len(entries), 21)
        self.assertEqual({p.local_comparison["method"] for p in entries}, set(local.METHODS))
        self.assertTrue(all(p.workers == 1 for p in entries))

    def test_invalid_or_incompatible_options_rejected(self):
        for raw in ({"method": "unknown"}, {"method": "bottle", "references": 3},
                    {"method": "bottle", "device": "cuda"},
                    {"method": "bottle", "min_confidence": float("nan")},
                    {"method": "bottle", "window": True}):
            with self.assertRaises(embeddings.ConfigError):
                local.check_options(raw)
        for key in ("main_label", "label_gate", "competitor", "rerank", "barcode"):
            with self.assertRaisesRegex(embeddings.ConfigError, "cannot be combined"):
                pipelines.Pipeline({"name": "test", "backend": "embedding", "embedding": "model",
                                    "local_comparison": {"method": "bottle"}, key: {}})

    def test_worker_checks_actual_input_bytes_before_cache_lookup(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "input.png"
            path.write_bytes(b"changed pixels")
            engine = object.__new__(worker.Engine)
            with self.assertRaisesRegex(ValueError, "input changed"):
                engine.handle({"method": "dinov2", "query": {"path": str(path), "sha256": "wrong"}})

    def test_no_label_falls_back_with_recorded_reason(self):
        c = object.__new__(local.Comparison)
        c.options = {"method": "dinov2-score"}
        c.bottle = lambda *_: (self.candidates, 4, 200, None,
                                                     {"steps": []})
        c.prepare = lambda *_: (None, {"passed": False})
        out, _ms, status, error, trace = c.ask("input.png")
        self.assertEqual(out, self.candidates)
        self.assertEqual(status, 200)
        self.assertIsNone(error)
        self.assertEqual(trace["steps"][-1]["out"]["reason"], "no_label")

    def test_worker_error_falls_back_with_error_evidence(self):
        c = object.__new__(local.Comparison)
        c.options = {"method": "dinov2-score"}
        c.bottle = lambda *_: (self.candidates, 4, 200, None,
                                                     {"steps": []})
        c.prepare = lambda *_: ({"path": "x", "sha256": "a"}, {"passed": True})
        c.references = lambda *_: self.refs
        c.worker = SimpleNamespace(call=lambda *_: (_ for _ in ()).throw(RuntimeError("failed model")))
        out, *_rest, trace = c.ask("input.png")
        self.assertEqual(out, self.candidates)
        self.assertEqual(trace["steps"][-1]["out"]["reason"], "comparison_failed")
        self.assertIn("failed model", trace["steps"][-1]["out"]["error"])

    def test_reranking_retains_retrieval_cache_evidence(self):
        c = object.__new__(local.Comparison)
        c.options = {"method": "dinov2-score"}
        c.bottle = lambda *_: (self.candidates, 0, 200, None,
                              {"steps": [], "retrieval_cache": True})
        c.prepare = lambda *_: (None, {"passed": False})
        *_, trace = c.ask("input.png")
        self.assertTrue(trace["retrieval_cache"])

    def test_no_cache_ocr_does_not_read_shared_word_cache(self):
        import embedding_run
        import main_label_match
        c = object.__new__(local.Comparison)
        c.options = local.check_options({"method": "tesseract"})
        c.catalog = {}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / 'label.png'
            path.write_bytes(b'pixels')
            received = []
            def reader(directory):
                received.append(Path(directory))
                return SimpleNamespace(read=lambda _: [])
            with patch.object(local, 'RUNTIME', root), patch.object(local.model_cache, 'READ', False), \
                    patch.object(main_label_match, 'TextReader', reader), \
                    patch.object(main_label_match, 'verify', return_value=(self.candidates, {})):
                c.text(self.candidates, {'path': str(path)}, 'tesseract', embedding_run.Trace())
            self.assertNotEqual(received[0], root / 'ocr-tesseract')
            self.assertFalse(received[0].exists())

    def test_gate_selects_whole_bottle_ranking_and_skips_ocr(self):
        c = object.__new__(local.Comparison)
        c.options = local.check_options({"method": "siglip-gated-paddleocr"})
        c.bottle = lambda *_: (self.candidates, 4, 200, None,
                                                     {"steps": []})
        c.prepare = lambda *_: ({"path": "x"}, {"passed": False})
        c.global_labels = lambda *_: [{"slug": "other", "score": .97}, {"slug": "third", "score": .95}]
        c.text = lambda *_: self.fail("OCR must not run on bottle fallback")
        out, *_rest, trace = c.ask("input.png")
        self.assertEqual(out, self.candidates)
        self.assertEqual(trace["steps"][-1]["out"]["selected_view"], "full")

    def test_local_suite_skips_remote_index_rebuild(self):
        import rebuild_on_run
        messages = []
        p = SimpleNamespace(embedding="fixed-reference", local_comparison={"method": "bottle"})
        with patch.object(rebuild_on_run, "build") as build:
            self.assertIsNone(rebuild_on_run.before_run(p, "unused", messages.append))
        build.assert_not_called()
        self.assertIn("all query embeddings are local", messages[0])

    def test_local_encoder_sends_only_local_paths_to_worker(self):
        from PIL import Image
        import io
        stream = io.BytesIO()
        Image.new("RGB", (10, 20), "blue").save(stream, "PNG")
        received = []
        w = SimpleNamespace(call=lambda method, item: received.append((method, item)) or
                            {"vector": [1, 0]})
        with tempfile.TemporaryDirectory() as root, patch.object(local, "RUNTIME", Path(root)):
            values = local.LocalQueryModel(w).embed([stream.getvalue()])
            self.assertEqual(values.tolist(), [[1, 0]])
            method, item = received[0]
            self.assertEqual(method, "siglip-vector")
            self.assertTrue(Path(item["path"]).is_file())
            self.assertEqual(local.sha(item["path"]), item["sha256"])

    def test_uncached_package_uses_explicit_context_fallback(self):
        import embedding_run
        from PIL import Image
        def unavailable(*_args):
            raise embedding_run.derive.Sam3Unavailable("no cached mask")
        segmenter = SimpleNamespace(instances=unavailable)
        trace = embedding_run.Trace()
        cuts = embedding_run.cuts_of(Image.new("RGB", (80, 120), "blue"), {"package"},
            segmenter, trace, scene_selection=True, offline_package_fallback=True)
        self.assertIsNotNone(cuts["package"])
        self.assertEqual(trace.steps[0]["out"]["selection"]["fallback_reason"],
                         "no_cached_package_segmentation")
        with self.assertRaises(embedding_run.derive.Sam3Unavailable):
            embedding_run.cuts_of(Image.new("RGB", (80, 120)), {"package"},
                                 segmenter, scene_selection=True)

    def test_saved_segmentation_stays_fixed_when_recognition_cache_is_off(self):
        import json
        import model_cache
        from PIL import Image
        with tempfile.TemporaryDirectory() as folder, patch.object(model_cache, 'ROOT', folder):
            client = local.cached_segmenter()
            image = Image.new('RGB', (20, 30), 'blue')
            data, _ = client._sent_copy(image)
            fields = model_cache.request_fields(client.endpoint + '/segment_multi',
                local.derive.SAM3_MODEL,
                {'threshold': str(local.derive.SAM3_THRESHOLD),
                 'mask_threshold': str(local.derive.SAM3_MASK_THRESHOLD), 'return_masks': 'true'},
                ['label'], [data])
            path = Path(model_cache.path_of(fields))
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({'request': fields, 'answer': {'instances': []}}))
            with patch.object(model_cache, 'READ', False), patch.object(client.session, 'post') as post:
                self.assertEqual(client.instances(image, ['label'])[0], [])
                self.assertTrue(client.cached())
            post.assert_not_called()
            client.session.close()

    def test_main_label_steps_are_ready_for_normal_preprocessor(self):
        import embedding_run
        from PIL import Image
        image = Image.new("RGBA", (30, 60), (0, 0, 255, 255))
        cut = image.crop((5, 10, 25, 50))
        prepared, reason = embedding_run.view_input(image, local.LABEL_STEPS,
                            {"label": ((5, 10, 25, 50), cut)})
        self.assertIsNone(reason)
        self.assertEqual(prepared.size, (20, 40))
        self.assertEqual(prepared.mode, "RGB")


if __name__ == "__main__":
    unittest.main()
