"""ArcFace mathematics, source splits, checkpoint integrity, and retrieval parity."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock

import numpy as np
import torch

import embedding_lab  # noqa: F401
from embedding_lab import FakeGateway, bottle_on_grey, seg_derivative, standard_lab
import arcface
import build_embeddings
import embedding_run
import embeddings
import train_arcface


def save_projection(directory, dim=4, source_model="fake-model"):
    rng = np.random.default_rng(7)
    projection = arcface.Projection(rng.normal(size=(dim, 8)), np.zeros(dim), {
        "format": arcface.FORMAT, "source_model": {"model": source_model, "extra_body": {"max_num_patches": 256}}})
    path = Path(directory) / "projection.npz"
    data = projection.dumps()
    path.write_bytes(data)
    return projection, {"checkpoint": str(path), "sha256": hashlib.sha256(data).hexdigest()}


class ArcFaceMathTest(unittest.TestCase):
    def test_margin_changes_only_target_logit_and_selects_best_subcenter(self):
        loss = train_arcface.SubCenterArcFace(torch.eye(2), torch.ones(2), k=2,
                                             scale=1, margin_a=0, margin_b=0.3)
        with torch.no_grad():
            loss.weight.copy_(torch.tensor([[1., 0.], [-1., 0.], [0., 1.], [0., -1.]]))
        angle = 0.7
        features = torch.tensor([[np.cos(angle), np.sin(angle)]], dtype=torch.float32)
        logits = loss.logits(features, torch.tensor([0])).detach().numpy()[0]
        np.testing.assert_allclose(logits, [np.cos(angle + 0.3), np.sin(angle)], rtol=1e-6)

    def test_backward_is_finite_at_parallel_and_antipodal_vectors(self):
        loss = train_arcface.SubCenterArcFace(torch.eye(2), torch.tensor([1., 4.]), k=1)
        with torch.no_grad():
            loss.weight.copy_(torch.eye(2))
        features = torch.tensor([[1., 0.], [-1., 0.]], requires_grad=True)
        value = loss(features, torch.tensor([0, 0]))
        value.backward()
        self.assertTrue(torch.isfinite(value))
        self.assertTrue(torch.isfinite(features.grad).all())
        self.assertTrue(torch.isfinite(loss.weight.grad).all())
        self.assertGreater(loss.margins[0].item(), loss.margins[1].item())

    def test_bad_margin_and_counts_fail(self):
        for counts, kwargs in [(torch.zeros(2), {}), (torch.ones(2), {"k": 0}),
                               (torch.ones(2), {"margin_b": 2})]:
            with self.assertRaises(ValueError):
                train_arcface.SubCenterArcFace(torch.eye(2), counts, **kwargs)


class SplitTest(unittest.TestCase):
    def samples(self):
        return [{"wine_slug": slug, "group": group, "view": view}
                for slug, groups in [("a", ["a1", "a2", "a3"]), ("b", ["b1"])]
                for group in groups for view in ["full", "label", "full"]]

    def test_views_and_rotations_stay_together_and_singletons_stay_in_train(self):
        samples = self.samples()
        train, valid, labels, classes, counts = train_arcface.split_samples(samples)
        self.assertFalse({samples[i]["group"] for i in train} & {samples[i]["group"] for i in valid})
        self.assertTrue(all(samples[i]["wine_slug"] == "a" for i in valid))
        self.assertEqual(classes, ["a", "b"])
        np.testing.assert_array_equal(counts, [2, 1])
        repeated = train_arcface.split_samples(samples)
        np.testing.assert_array_equal(train, repeated[0])
        np.testing.assert_array_equal(valid, repeated[1])
        self.assertEqual(set(labels[train]), {0, 1})

    def test_no_source_disjoint_validation_fails(self):
        samples = [{"wine_slug": slug, "group": slug, "view": "full"} for slug in ["a", "b"]]
        with self.assertRaisesRegex(ValueError, "distinct source groups"):
            train_arcface.split_samples(samples)

    def test_recall_uses_unique_wines_and_same_view_gallery(self):
        samples = [{"wine_slug": slug, "group": group, "view": view} for slug, group, view in [
            ("a", "a1", "full"), ("a", "a1", "label"), ("b", "b1", "full"),
            ("a", "a2", "full"), ("a", "a2", "label")]]
        features = np.array([[1, 0], [0, 1], [-1, 0], [1, 0], [0, 1]], dtype=np.float32)
        metrics = train_arcface.retrieval_metrics(features, np.array([0, 0, 1, 0, 0]), samples,
                                                  np.array([0, 1, 2]), np.array([3, 4]))
        self.assertEqual(metrics["recall@1"], 1)
        self.assertEqual(metrics["source_group_weight"], 1)

    def test_small_training_run_has_finite_loss_and_exportable_weights(self):
        torch.set_num_threads(2)
        rng = np.random.default_rng(42)
        samples, features = [], []
        for label in range(3):
            for group in range(4):
                for view in ["full", "label"]:
                    feature = np.eye(6, dtype=np.float32)[label] + rng.normal(0, 0.08, 6)
                    features.append(feature)
                    samples.append({"wine_slug": str(label), "group": "%s-%s" % (label, group), "view": view})
        projection, report = train_arcface.fit(np.asarray(features), {"samples": samples},
                                                dim=3, epochs=3, batch_size=9, emit=lambda _: None)
        self.assertEqual(len(report["history"]), 4)
        json.dumps(report)  # The CLI report MUST contain JSON-native values.
        self.assertTrue(all(np.isfinite(r["loss"]) for r in report["history"][1:]))
        np.testing.assert_allclose(np.linalg.norm(projection.transform(features), axis=1), 1, rtol=1e-6)


class ProjectionIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.gateway = FakeGateway()
        self.lab = standard_lab(self.tmp.name, self.gateway.base_url)
        self.settings = embeddings.load_settings(self.lab.config_path)
        self.source = self.settings.find("gw")
        directory = self.lab.entry_dir("gw")
        Path(directory).mkdir(parents=True, exist_ok=True)
        with contextlib.redirect_stdout(io.StringIO()):
            build_embeddings.run(self.source, self.lab.db_path, directory)
        self.projection, self.spec = save_projection(self.tmp.name)

    def tearDown(self):
        self.gateway.close()
        self.lab.close()
        self.tmp.cleanup()

    def target(self, spec=None):
        raw = self.source.summary()
        raw.update(name="gw-arcface", arcface=spec or self.spec)
        raw["views"] = {view: {"steps": steps} for view, steps in self.source.views.items()}
        return embeddings.Embedding(raw)

    def test_checkpoint_roundtrip_and_pinned_model_identity(self):
        projection = arcface.Projection.load(self.spec, self.source.model, self.source.extra_body)
        features = np.arange(1, 17).reshape(2, 8)
        np.testing.assert_allclose(projection.transform(features), self.projection.transform(features))
        with self.assertRaisesRegex(ValueError, "different DINOv3"):
            arcface.Projection.load(self.spec, "other-model", self.source.extra_body)
        with self.assertRaisesRegex(ValueError, "different DINOv3"):
            arcface.Projection.load(self.spec, self.source.model, {})

    def test_changed_checkpoint_fails_before_inference(self):
        Path(self.spec["checkpoint"]).write_bytes(b"changed")
        with self.assertRaisesRegex(embeddings.ConfigError, "SHA-256"):
            build_embeddings.make_backend(self.target())

    def test_checkpoint_digest_invalidates_cached_vectors(self):
        target = self.target()
        changed = self.target(dict(self.spec, sha256="a" * 64))
        self.assertNotEqual(self.source.view_config_hash("full"), target.view_config_hash("full"))
        self.assertNotEqual(target.view_config_hash("full"), changed.view_config_hash("full"))
        self.assertEqual(target.summary()["arcface"], self.spec)
        for invalid in [{"checkpoint": "x"}, {"checkpoint": "x", "sha256": "wrong"},
                        {"checkpoint": "", "sha256": "a" * 64}]:
            with self.assertRaises(embeddings.ConfigError):
                self.target(invalid)

    def test_exported_gallery_and_live_query_use_identical_projection(self):
        target = self.target()
        before = len(self.gateway.requests)
        result = train_arcface.export_index(self.source, target, self.lab.db_path, self.projection)
        self.assertEqual(len(self.gateway.requests), before)
        self.assertEqual(result["items"], 4)
        catalogue = embedding_run.Catalogue(target, self.lab.db_path)
        source_index = embeddings.read_index(self.lab.entry_dir("gw"))
        record = next(row for row in source_index["items"] if row["source_sha256"] == self.lab.grey)
        png = (Path(self.lab.entry_dir("gw")) / record["image"]).read_bytes()
        query = build_embeddings.make_backend(target).embed([png])[0]
        source_vectors = embeddings.read_vectors(self.lab.entry_dir("gw"), source_index)
        np.testing.assert_allclose(query, self.projection.transform(source_vectors[[record["row"]]])[0],
                                   rtol=1e-6, atol=1e-7)
        rank = catalogue.rank({"full": query}, top_k=3)
        self.assertEqual(rank[0]["slug"], "grey")
        self.assertAlmostEqual(rank[0]["score"], 1, places=5)
        with self.assertRaisesRegex(ValueError, "already exists"):
            train_arcface.export_index(self.source, target, self.lab.db_path, self.projection)

    def test_training_excludes_shared_identity_and_stale_rows(self):
        _, provenance = train_arcface.collect_samples(self.source, self.lab.db_path, self.lab.entry_dir())
        self.assertEqual(provenance["ambiguous_items_excluded"], 1)
        self.assertFalse(any(row["source_sha256"] == self.lab.transparent for row in provenance["samples"]))
        self.assertFalse(any(row["source_sha256"] == self.lab.patched_main for row in provenance["samples"]))

    def test_exact_duplicate_derivatives_merge_sources_and_exclude_conflicting_ids(self):
        original = bottle_on_grey()
        original.putpixel((0, 0), (255, 0, 0))
        self.lab.wine("duplicate-grey")
        digest = self.lab.image("duplicate-grey", "main", original,
                                derivative=seg_derivative(original, (30, 20, 50, 100)),
                                box=(30, 20, 50, 100))
        with contextlib.redirect_stdout(io.StringIO()):
            build_embeddings.run(self.source, self.lab.db_path, self.lab.entry_dir())
        _, provenance = train_arcface.collect_samples(self.source, self.lab.db_path, self.lab.entry_dir())
        excluded = {self.lab.grey, digest}
        self.assertFalse(any(row["source_sha256"] in excluded for row in provenance["samples"]))

    def test_cli_writes_complete_serializable_artifacts_and_valid_index(self):
        rng = np.random.default_rng(12)
        features, samples = [], []
        for label in range(2):
            for group in range(3):
                features.append(np.eye(8)[label] + rng.normal(0, 0.03, 8))
                samples.append({"wine_slug": str(label), "group": "%s-%s" % (label, group), "view": "full"})
        provenance = {"samples": samples, "features_sha256": "a" * 64}
        output = Path(self.tmp.name) / "trained"
        with mock.patch.object(train_arcface, "collect_samples", return_value=(np.asarray(features), provenance)):
            with contextlib.redirect_stdout(io.StringIO()):
                result = train_arcface.main(["--config", self.lab.config_path, "--name", "gw",
                                             "--output-name", "gw-cli-arcface", "--output-dir", str(output),
                                             "--dim", "3", "--epochs", "1", "--export-index"])
        self.assertEqual(result, 0)
        report = json.loads((output / "report.json").read_text())
        self.assertEqual(report["export_index"]["items"], 4)
        settings = embeddings.load_settings(str(output / "config.yaml"))
        target = settings.find("gw-cli-arcface")
        arcface.Projection.load(target.arcface, target.model, target.extra_body)
        catalogue = embedding_run.Catalogue(target, self.lab.db_path)
        self.assertEqual(catalogue.views["full"][0].shape[1], 3)
        self.assertTrue((output / "training-snapshot.json").exists())

    def test_derived_config_keeps_source_and_adds_two_pipelines(self):
        config, target = train_arcface.derived_config(self.lab.config_path, self.source, "gw-arcface", self.spec)
        self.assertEqual(config["embeddings"][0]["name"], "gw")
        self.assertEqual(target.arcface, self.spec)
        self.assertEqual([row["name"] for row in config["pipeline"]], ["gw-arcface", "gw-arcface-crop"])
        self.assertEqual(config["database_file"], self.lab.db_path)

    def test_projection_rejects_wrong_shape_zero_and_nonfinite_features(self):
        for features in [np.ones((2, 3)), np.zeros((1, 8)), np.full((1, 8), np.nan)]:
            with self.assertRaises(ValueError):
                self.projection.transform(features)

    def test_local_backend_supports_dinov3_pooler_without_get_image_features(self):
        local = object.__new__(build_embeddings.LocalBackend)
        local.torch, local.device, local.extra = torch, "cpu", {}
        inputs = mock.Mock()
        inputs.to.return_value = {}
        local.processor = mock.Mock(return_value=inputs)
        local.model = mock.Mock(spec=["__call__"], return_value=types.SimpleNamespace(pooler_output=torch.ones(1, 8)))
        record = embeddings.read_index(self.lab.entry_dir())["items"][0]
        png = (Path(self.lab.entry_dir()) / record["image"]).read_bytes()
        np.testing.assert_array_equal(local.embed([png]), np.ones((1, 8)))


if __name__ == "__main__":
    unittest.main()
