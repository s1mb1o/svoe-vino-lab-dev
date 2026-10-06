"""Check popup freshness and live names around the checked read caches."""
import json
import os
from pathlib import Path
import types
from unittest.mock import patch

from PIL import Image

import test_embedding_run as TE
import clusters
import embedding_run
import embeddings
import run_routes
import run_steps


class RunDetailCacheTest(TE.Temporary):
    def setUp(self):
        super().setUp()
        self.lab = TE.catalogue_lab(self.root)
        self.embedding = TE.build(self.lab)
        self.embedding_dir = Path(embeddings.entry_dir(self.lab.db_path, self.embedding.name))
        embedding_run.CANDIDATE_INDEXES.clear()
        run_steps.THUMBNAILS.clear()
        run_routes.CLUSTER_HINT_INPUTS.clear()

    def test_candidate_reuse_missing_images_and_index_replacement(self):
        catalogue = embedding_run.Catalogue(self.embedding, self.lab.db_path)
        candidate = catalogue.rank(TE.vectors_of(catalogue, "red"), 1)[0]
        spec = {"embedding": self.embedding.name, "views": self.embedding.views}
        def call():
            return embedding_run.candidate_items(spec, candidate, self.lab.db_path)
        with patch.object(embeddings, "read_index", wraps=embeddings.read_index) as read, \
                patch.object(embeddings, "image_names", wraps=embeddings.image_names) as names:
            first = call()
            first["items"][0]["state"] = "changed by caller"
            self.assertEqual(call()["items"][0]["state"], "same")
            self.assertEqual((read.call_count, names.call_count), (1, 1))
            item = candidate["items"][0]
            path = self.embedding_dir / embeddings.IMAGES / embeddings.image_name(item["sha256"], item["view"])
            path.unlink()
            self.assertEqual(call()["items"][0]["state"], "gone")
            self.assertEqual(read.call_count, 2)
            source = self.embedding_dir / embeddings.INDEX
            index = embeddings.read_index(self.embedding_dir)
            for record in index["items"]:
                if record["source_sha256"] == item["sha256"] and record["view"] == item["view"]:
                    record["embedding_hash"] = "replaced"
            replacement = source.with_suffix(".new")
            replacement.write_text(json.dumps(index))
            replacement.replace(source)
            Image.new("RGB", (4, 4), "white").save(path)
            self.assertEqual(call()["items"][0]["state"], "changed")

    def test_rotated_thumbnail_reuse_replacement_and_missing_file(self):
        item = embeddings.read_index(self.embedding_dir)["items"][0]
        hit = {"sha256": item["source_sha256"], "embedding_hash": item["embedding_hash"], "angle": 90}
        view = item["view"]
        path = self.embedding_dir / embeddings.IMAGES / embeddings.image_name(hit["sha256"], view)
        def call():
            return run_steps._item_image(self.lab.db_path, self.embedding.name, hit, view)
        with patch.object(run_steps.derive, "open_image", wraps=run_steps.derive.open_image) as read:
            first = call()
            self.assertEqual(call(), first)
            self.assertEqual(read.call_count, 1)
            before = path.stat()
            replacement = path.with_suffix(".new")
            Image.new("RGB", (20, 40), "purple").save(replacement, "PNG")
            os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
            replacement.replace(path)
            self.assertNotEqual(call(), first)
            self.assertEqual(read.call_count, 2)
            path.unlink()
            self.assertTrue(call().startswith("/embeddings/"))
            self.assertEqual(read.call_count, 3)
            hit["angle"] = 0
            call()
            self.assertEqual(read.call_count, 3)

    def test_cluster_hint_reuse_live_names_and_rule_writes(self):
        runs = self.root / "runs"
        run_id = "2026-10-06T210000Z-lab-gw-my"
        run = runs / run_id
        run.mkdir(parents=True)
        (run / "run.json").write_text(json.dumps({"backend": {"kind": "embedding", "embedding": "gw"}}))
        artifact = {"version": 1, "built_at": "now", "input_hash": "old", "spaces": {
            "combined": {"clusters": [{"id": "c1", "key": "key", "kind": "mixed", "slugs": ["red", "green"]}]}}}
        (self.embedding_dir / clusters.CLUSTERS_FILE).write_text(json.dumps(artifact))
        rule_path = self.embedding_dir / clusters.RULES_FILE
        rule = {"spaces": {"label": {"key": {"mode": "sheet", "questions": [{"id": "q1"}]}}}}
        rule_path.write_text(json.dumps(rule))
        server = types.SimpleNamespace(db_path=self.lab.db_path, config_path=self.lab.config_path)
        def call():
            return run_routes.clusters_view(str(runs), server, {"id": [run_id]})[1]
        with patch.object(clusters, "load_artifact", wraps=clusters.load_artifact) as read:
            first = call()
            first["clusters"][0]["slugs"].clear()
            first["clusters"][0]["rule"]["questions"][0]["id"] = "caller"
            self.assertEqual(call()["clusters"][0]["rule"]["questions"][0]["id"], "q1")
            self.assertEqual(read.call_count, 1)
            self.lab.conn.execute("UPDATE wine_catalog SET name_patched='Current name' WHERE wine_slug='red'")
            self.lab.conn.commit()
            self.assertEqual(call()["cards"]["red"]["name"], "Current name")
            self.assertEqual(read.call_count, 1)
            rule["spaces"]["label"]["key"]["mode"] = "verdict"
            rule_path.write_text(json.dumps(rule))
            self.assertEqual(call()["clusters"][0]["rule"]["mode"], "verdict")
            (self.embedding_dir / clusters.CLUSTERS_FILE).unlink()
            self.assertFalse(call()["exists"])


if __name__ == "__main__":
    import unittest
    unittest.main()
