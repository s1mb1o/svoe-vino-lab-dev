import json
import os
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

import numpy as np
import yaml
from PIL import Image

import embedding_lab  # noqa: F401  (puts pipeline/ on sys.path)
from embedding_lab import bottle_on_grey, standard_lab

import clusters  # noqa: E402
import embeddings  # noqa: E402


def unit(values):
    values = np.asarray(values, dtype=np.float32)
    return values / np.linalg.norm(values)


class ClusterLab:
    """A standard embedding lab with a controlled vector for each item."""

    def __init__(self, root):
        self.lab = standard_lab(root, "http://127.0.0.1:9/v1")
        extra = bottle_on_grey((50, 60, 70))
        self.extra = self.lab.image("grey", "full_back", extra)
        self.settings = embeddings.load_settings(self.lab.config_path)
        self.embedding = self.settings.find("gw")
        with closing(embeddings.open_database(self.lab.db_path)) as conn:
            _, sources = embeddings.read_inputs(conn, self.lab.db_path)
        items = embeddings.plan_items(self.embedding, sources)
        directory = self.lab.entry_dir()
        images = Path(directory) / embeddings.IMAGES
        images.mkdir(parents=True)
        records, rows = [], []
        for row, key in enumerate(sorted(items)):
            digest, view = key
            item = items[key]
            vector = self.vector(digest, view)
            rows.append(vector)
            (images / embeddings.image_name(*key)).write_bytes(b"png")
            records.append({
                "source_sha256": digest, "view": view, "role": item["role"],
                "embedding_hash": item["embedding_hash"], "derivative_sha256": None,
                "image": "%s/%s" % (embeddings.IMAGES, embeddings.image_name(*key)),
                "width": 10, "height": 20, "row": row,
            })
        self.index = embeddings.write_checkpoint(directory, {
            "name": "gw", "config": self.embedding.summary(), "steps_version": 1,
            "view_config_hash": {}, "dim": 3, "updated_at": "2026-09-25T20:00:00+0300",
            "items": records, "failures": [],
        }, np.asarray(rows, dtype=np.float32))

    def vector(self, digest, view):
        # The extra full image of grey creates a full edge with transparent and shared.
        # The effective patched image creates a label edge with grey alone.
        if view == "full":
            if digest in (self.lab.transparent, self.extra):
                return unit([1, 0, 0])
            if digest == self.lab.patched:
                return unit([0, 1, 0])
            if digest == self.lab.grey:
                return unit([0.7, 0.7, 0])
            return unit([0, 0, 1])
        if digest == self.lab.transparent:
            return unit([1, 0, 0])
        if digest in (self.lab.grey, self.extra, self.lab.patched):
            return unit([0, 1, 0])
        if digest == self.lab.closeup:
            return unit([0.7, 0, 0.7])
        return unit([0, 0, 1])

    def set_clusters(self, block):
        """Write `block` as the key `clusters` of the lab `config.yaml`."""
        path = Path(self.lab.config_path)
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
        config["clusters"] = block
        path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")

    def close(self):
        self.lab.close()


class SimilarityTest(unittest.TestCase):
    def test_a_shared_source_keeps_each_wine_image_role(self):
        wines = [
            {"slug": "package", "columns": [("main", "same")]},
            {"slug": "closeup", "columns": [("label_front", "same")]},
        ]
        items = {("same", "full"): {}, ("same", "label"): {}}
        assignments = {(row["slug"], row["image_type"], row["view"])
                       for row in clusters._assignments(wines, items)}
        self.assertIn(("package", "main", "full"), assignments)
        self.assertIn(("package", "main", "label"), assignments)
        self.assertIn(("closeup", "label_front", "label"), assignments)
        self.assertNotIn(("closeup", "label_front", "full"), assignments)

    def test_the_best_image_pair_wins(self):
        rows = [
            {"slug": "a", "source_sha256": "a1", "image_types": ["main"],
             "prepared_url": "/a1", "original_url": "/raw/a1", "vector": unit([1, 0])},
            {"slug": "b", "source_sha256": "b1", "image_types": ["main"],
             "prepared_url": "/b1", "original_url": "/raw/b1", "vector": unit([0.8, 0.6])},
            {"slug": "b", "source_sha256": "b2", "image_types": ["full_back"],
             "prepared_url": "/b2", "original_url": "/raw/b2", "vector": unit([1, 0])},
        ]
        edges = clusters.similarity_edges(rows, 0.95, block=2)
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]["similarity"], 1.0)
        self.assertEqual(edges[0]["b_image"]["source_sha256"], "b2")

    def test_a_wine_does_not_link_to_itself(self):
        rows = [
            {"slug": "a", "source_sha256": "a1", "image_types": ["main"],
             "prepared_url": "/a1", "original_url": "/raw/a1", "vector": unit([1, 0])},
            {"slug": "a", "source_sha256": "a2", "image_types": ["full_back"],
             "prepared_url": "/a2", "original_url": "/raw/a2", "vector": unit([1, 0])},
        ]
        self.assertEqual(clusters.similarity_edges(rows, 0.5), [])

    def test_too_many_links_stop_the_search(self):
        rows = [{"slug": slug, "source_sha256": slug + "1", "image_types": ["main"],
                 "prepared_url": "/" + slug, "original_url": "/raw/" + slug,
                 "vector": unit([1, 0])} for slug in ("a", "b", "c")]
        self.assertEqual(len(clusters.similarity_edges(rows, 0.5, max_links=3)), 3)
        with self.assertRaisesRegex(clusters.ClusterError,
                                    "full_threshold 0.5 gives more than 2 links"):
            clusters.similarity_edges(rows, 0.5, max_links=2, field="full_threshold")

    def test_threshold_rules(self):
        for value in (float("nan"), float("inf"), -1.1, 1.1, True, "0.9"):
            with self.subTest(value=value), self.assertRaises(clusters.ClusterError):
                clusters.validate_threshold(value)
        self.assertEqual(clusters.validate_threshold(-1), -1.0)
        self.assertEqual(clusters.validate_threshold(1), 1.0)


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fixture = ClusterLab(self.tmp.name)

    def tearDown(self):
        self.fixture.close()
        self.tmp.cleanup()

    def build(self):
        context = clusters.context(self.fixture.settings, "gw")
        vectors = embeddings.read_vectors(self.fixture.lab.entry_dir(), context["index"])
        return context, clusters.build(context, vectors, 0.95, 0.95)

    def test_context_uses_patched_main_and_every_additional_image(self):
        context = clusters.context(self.fixture.settings, "gw")
        assignments = {(row["slug"], row["image_type"], row["source_sha256"], row["view"])
                       for row in context["assignments"]}
        self.assertNotIn(("patched", "main", self.fixture.lab.patched_main, "full"),
                         assignments)
        self.assertIn(("patched", "main_patched", self.fixture.lab.patched, "full"),
                      assignments)
        self.assertIn(("grey", "full_back", self.fixture.extra, "full"), assignments)
        self.assertIn(("grey", "full_back", self.fixture.extra, "label"), assignments)
        self.assertIn(("transparent", "label_front", self.fixture.lab.closeup, "label"),
                      assignments)
        self.assertNotIn(("transparent", "label_front", self.fixture.lab.closeup, "full"),
                         assignments)

    def test_spaces_are_separate_and_the_combined_view_is_the_union(self):
        _, artifact = self.build()
        full = artifact["spaces"]["full"]
        label = artifact["spaces"]["label"]
        combined = artifact["spaces"]["combined"]
        self.assertEqual(full["counts"]["clusters"], 1)
        self.assertEqual(set(full["clusters"][0]["slugs"]),
                         {"grey", "shared", "transparent"})
        full_grey = next(edge for edge in full["clusters"][0]["links"]
                         if "grey" in (edge["a"], edge["b"]))
        evidence = full_grey["spaces"]["full"]
        grey_image = evidence["a_image"] if full_grey["a"] == "grey" else evidence["b_image"]
        self.assertEqual(grey_image["source_sha256"], self.fixture.extra)
        self.assertEqual(grey_image["image_types"], ["full_back"])

        label_members = [set(cluster["slugs"]) for cluster in label["clusters"]]
        self.assertIn({"grey", "patched"}, label_members)
        union = set().union(*(set(cluster["slugs"]) for cluster in combined["clusters"]))
        self.assertTrue({"grey", "patched", "shared", "transparent"} <= union)
        self.assertTrue(any(cluster["kind"] == "mixed" for cluster in combined["clusters"]))

    def test_write_and_stale_status(self):
        artifact = clusters.build_to_directory(self.fixture.settings, "gw")
        status = clusters.artifact_status(self.fixture.settings, "gw")
        self.assertTrue(status["exists"])
        self.assertFalse(status["stale"])
        stored = json.loads((Path(self.fixture.lab.entry_dir()) / clusters.CLUSTERS_FILE)
                            .read_text(encoding="utf-8"))
        self.assertEqual(stored["input_hash"], artifact["input_hash"])
        self.fixture.lab.conn.execute(
            "UPDATE wine_catalog SET state = 'Disabled' WHERE wine_slug = 'grey'")
        self.fixture.lab.conn.commit()
        self.assertTrue(clusters.artifact_status(self.fixture.settings, "gw")["stale"])

    def test_a_too_large_cluster_stops_the_build_and_keeps_the_old_file(self):
        clusters.build_to_directory(self.fixture.settings, "gw")
        path = Path(self.fixture.lab.entry_dir()) / clusters.CLUSTERS_FILE
        before = path.read_bytes()
        # The full space has one cluster of 3 wines.
        self.fixture.set_clusters({"max_cluster_size": 2})
        with self.assertRaisesRegex(clusters.ClusterError,
                                    "the full space has a cluster of 3 wines, more than 2"):
            clusters.build_to_directory(self.fixture.settings, "gw")
        self.assertEqual(path.read_bytes(), before)

    def test_config_values_have_defaults_and_checks(self):
        settings = self.fixture.settings
        self.assertEqual(clusters.config_values(settings), clusters.CONFIG_DEFAULTS)
        self.fixture.set_clusters({"full_threshold": 0.9, "max_links": 10})
        values = clusters.config_values(settings)
        self.assertEqual(values["full_threshold"], 0.9)
        self.assertEqual(values["label_threshold"], clusters.DEFAULT_THRESHOLD)
        self.assertEqual(values["max_links"], 10)
        for block, text in (([], "MUST be a mapping"), ({"other": 1}, "unknown key: other"),
                            ({"label_threshold": 2}, "clusters.label_threshold"),
                            ({"max_links": 0}, "clusters.max_links MUST"),
                            ({"max_cluster_size": 1}, "clusters.max_cluster_size MUST"),
                            ({"min_cluster_size": 1}, "clusters.min_cluster_size MUST"),
                            ({"min_cluster_size": 60}, "MUST NOT be more than"),
                            ({"max_links": True}, "clusters.max_links MUST")):
            with self.subTest(block=block):
                self.fixture.set_clusters(block)
                with self.assertRaisesRegex(clusters.ClusterError, text):
                    clusters.config_values(settings)

    def test_the_build_takes_the_thresholds_of_the_config(self):
        self.fixture.set_clusters({"full_threshold": 0.96, "label_threshold": 0.97})
        artifact = clusters.build_to_directory(self.fixture.settings, "gw")
        self.assertEqual(artifact["settings"], {"full_threshold": 0.96,
                                                "label_threshold": 0.97, "min_cluster_size": 2})
        artifact = clusters.build_to_directory(self.fixture.settings, "gw", 0.95)
        self.assertEqual(artifact["settings"], {"full_threshold": 0.95,
                                                "label_threshold": 0.97, "min_cluster_size": 2})

    def test_min_cluster_size_drops_the_smaller_clusters(self):
        before = clusters.build_to_directory(self.fixture.settings, "gw")
        self.fixture.set_clusters({"min_cluster_size": 3})
        artifact = clusters.build_to_directory(self.fixture.settings, "gw")
        self.assertEqual(artifact["settings"]["min_cluster_size"], 3)
        for space in clusters.SPACES:
            with self.subTest(space=space):
                sizes = [cluster["size"] for cluster in artifact["spaces"][space]["clusters"]]
                self.assertTrue(all(size >= 3 for size in sizes))
                self.assertEqual(sizes, [cluster["size"] for cluster in
                                         before["spaces"][space]["clusters"]
                                         if cluster["size"] >= 3])
                # The links of the space stay; only the clusters are dropped.
                self.assertEqual(artifact["spaces"][space]["counts"]["links"],
                                 before["spaces"][space]["counts"]["links"])
        self.assertEqual(artifact["spaces"]["full"]["counts"]["clusters"], 1)

    def test_notes_are_exact_then_inherited_by_member_overlap(self):
        _, artifact = self.build()
        current = artifact["spaces"]["full"]["clusters"][0]
        directory = self.fixture.lab.entry_dir()
        note = clusters.set_note(directory, current, "Check the back image.")
        self.assertFalse(note["inherited"])
        _, notes = clusters.load_notes(directory)
        changed = {"key": "other", "slugs": current["slugs"][:2]}
        inherited = clusters.note_for(changed, notes)
        self.assertTrue(inherited["inherited"])
        self.assertEqual(inherited["text"], "Check the back image.")
        cleared = clusters.set_note(directory, changed, "")
        self.assertFalse(cleared["inherited"])
        self.assertEqual(cleared["text"], "")

    def test_detail_adds_cards_notes_and_rules(self):
        artifact = clusters.build_to_directory(self.fixture.settings, "gw")
        cluster = artifact["spaces"]["full"]["clusters"][0]
        clusters.set_note(self.fixture.lab.entry_dir(), cluster, "note")
        clusters.write_json(os.path.join(self.fixture.lab.entry_dir(), clusters.RULES_FILE), {
            "version": 1, "spaces": {"full": {cluster["key"]: {
                "input_hash": artifact["input_hash"], "differences": "different text"}}}})
        detail = clusters.detail(self.fixture.settings, "gw")
        shown = detail["artifact"]["spaces"]["full"]["clusters"][0]
        self.assertEqual(shown["note"]["text"], "note")
        self.assertFalse(shown["rule"]["stale"])
        self.assertIn("grey", detail["cards"])
        self.assertTrue(detail["cards"]["grey"]["images"])

    def test_a_rule_belongs_to_one_vector_space(self):
        artifact = clusters.build_to_directory(self.fixture.settings, "gw")
        cluster = artifact["spaces"]["full"]["clusters"][0]
        clusters.write_json(os.path.join(self.fixture.lab.entry_dir(), clusters.RULES_FILE), {
            "version": 1, "spaces": {"label": {cluster["key"]: {
                "input_hash": artifact["input_hash"], "differences": "label only"}}}})
        detail = clusters.detail(self.fixture.settings, "gw")
        shown = detail["artifact"]["spaces"]["full"]["clusters"][0]
        self.assertIsNone(shown["rule"])

    def test_detail_keeps_a_stored_artifact_readable_without_the_index(self):
        clusters.build_to_directory(self.fixture.settings, "gw")
        os.remove(os.path.join(self.fixture.lab.entry_dir(), embeddings.INDEX))
        detail = clusters.detail(self.fixture.settings, "gw")
        self.assertTrue(detail["status"]["stale"])
        self.assertIn("has no index", detail["status"]["current_error"])
        self.assertIsNotNone(detail["artifact"])


if __name__ == "__main__":
    unittest.main()
