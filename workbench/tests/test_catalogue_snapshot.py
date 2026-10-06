"""Check snapshot parity, source freshness, corrupt caches, and fallback paths."""
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest
from unittest.mock import patch

import numpy as np

import test_embedding_run as TE
import catalogue_snapshot as snapshot
import embedding_run
import embeddings


class CatalogueSnapshotTest(TE.Temporary):
    def setUp(self):
        super().setUp()
        self.lab = TE.catalogue_lab(self.root)
        self.addCleanup(self.lab.conn.close)
        self.embedding = TE.build(self.lab)
        self.root_cache, self.key = snapshot._location(self.embedding, self.lab.db_path)

    def build(self, **options):
        return embedding_run.Catalogue(self.embedding, self.lab.db_path, **options)

    def manifest(self):
        return json.loads((self.root_cache / (self.key + ".json")).read_text())

    def test_restore_avoids_source_readers_and_preserves_ranking(self):
        original = self.build()
        query = TE.vectors_of(original, "red")
        expected = original.rank(query, 10)
        with patch.object(embeddings, "read_inputs", side_effect=AssertionError("must restore")), \
                patch.object(embeddings, "read_vectors", side_effect=AssertionError("must restore")):
            # Loaded-code identity changes under mocks. Hold the real identity for this check.
            real = self.manifest()["identity"]
            with patch.object(snapshot, "identity", return_value=real):
                restored = self.build()
        self.assertEqual(restored.rank(query, 10), expected)
        self.assertTrue(all(isinstance(matrix, np.memmap) and not matrix.flags.writeable
                            for matrix, _ in restored.views.values()))
        restored.state["items"]["current"] = -1
        self.assertGreater(self.build().state["items"]["current"], 0)

    def test_fresh_photo_process_restores_without_catalogue_readers(self):
        original = self.build()
        expected = original.rank(TE.vectors_of(original, "red"), 10)
        code = '''
import json, sys
sys.path.insert(0, sys.argv[1])
import embedding_run, embeddings
settings=embeddings.load_settings(sys.argv[2])
entry=settings.find('gw')
calls=[]
def profile(frame, event, arg):
    if event == 'call' and frame.f_code.co_name in ('read_inputs','read_index','read_vectors'):
        calls.append(frame.f_code.co_name)
sys.setprofile(profile)
catalogue=embedding_run.Catalogue(entry,settings.db_path)
sys.setprofile(None)
query={view: matrix[next(i for i,n in enumerate(numbers) if catalogue.slugs[n]=='red')]
       for view,(matrix,numbers) in catalogue.views.items()}
print(json.dumps({'calls':calls,'candidates':catalogue.rank(query,10)}))
'''
        directory = str(Path(embedding_run.__file__).parent)
        result = subprocess.run([sys.executable, "-c", code, directory, self.lab.config_path],
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["calls"], [])
        self.assertEqual(data["candidates"], expected)

    def test_oversize_snapshot_is_not_saved(self):
        with patch.object(snapshot, "MAX_ENTRY_BYTES", 1):
            value = self.build()
        self.assertTrue(value.views)
        self.assertFalse((self.root_cache / (self.key + ".json")).exists())

    def test_database_and_wal_commits_invalidate(self):
        first = self.build()
        self.lab.conn.execute("PRAGMA journal_mode=WAL")
        self.build()
        writer = sqlite3.connect(self.lab.db_path)
        self.addCleanup(writer.close)
        with writer:
            writer.execute("UPDATE wine_catalog SET state='Removed', removed_by='person' WHERE wine_slug='blue'")
        current = self.build()
        self.assertIn("blue", first.slugs)
        self.assertNotIn("blue", current.slugs)
        self.assertEqual(current.slugs, self.build(use_cache=False).slugs)

    def test_prepared_membership_and_config_changes_invalidate(self):
        self.build()
        directory = Path(embeddings.entry_dir(self.lab.db_path, self.embedding.name))
        prepared = next((directory / embeddings.IMAGES).iterdir())
        prepared.unlink()
        rebuilt = self.build()
        self.assertEqual(rebuilt.state, self.build(use_cache=False).state)
        self.embedding.views["full"][-1]["max_size"] = 32
        self.embedding._hashes.clear()
        self.assertNotIn("full", self.build().views)

    def test_corrupt_metadata_and_array_fall_back(self):
        expected = self.build().state
        pointer = self.root_cache / (self.key + ".json")
        pointer.write_text("not json")
        self.assertEqual(self.build().state, expected)
        meta = self.manifest()
        details = next(iter(meta["views"].values()))["arrays"]["matrix"]
        path = self.root_cache / meta["generation"] / details["file"]
        data = bytearray(path.read_bytes())
        data[-1] ^= 1
        path.write_bytes(data)
        self.assertEqual(self.build().state, expected)

    def test_vector_replacement_invalidates_and_corrupt_source_still_fails(self):
        self.build()
        directory = Path(embeddings.entry_dir(self.lab.db_path, self.embedding.name))
        path = directory / self.manifest()["vector_file"]
        path.write_bytes(b"invalid vector source")
        with self.assertRaises(embeddings.ConfigError):
            self.build()

    def test_failed_write_and_unstable_inputs_do_not_fail_construction(self):
        with patch.object(snapshot.tempfile, "mkdtemp", side_effect=PermissionError):
            value = self.build()
        self.assertTrue(value.views)
        self.assertFalse((self.root_cache / (self.key + ".json")).exists())
        before = snapshot.identity(self.embedding, self.lab.db_path)
        with patch.object(snapshot, "identity", return_value={"changed": True}):
            snapshot.store(value, self.embedding, self.lab.db_path, before,
                           "vectors-1.npy", None)
        self.assertFalse((self.root_cache / (self.key + ".json")).exists())

    def test_cache_bounds_and_rotated_item_references(self):
        # Duplicate one item's rows and retain the shared object used by items_of.
        value = self.build(use_cache=False)
        view = next(iter(value.views))
        matrix, numbers = value.views[view]
        value.views[view] = np.repeat(matrix, 2, axis=0), np.repeat(numbers, 2)
        value.items[view] = [item for item in value.items[view] for _ in range(2)]
        value.angles[view] = np.tile(np.array([0, 90], dtype=np.int16), len(numbers))
        before = snapshot.identity(self.embedding, self.lab.db_path)
        directory = Path(embeddings.entry_dir(self.lab.db_path, self.embedding.name))
        index = embeddings.read_index(directory)
        sig = snapshot._file(directory / index["vectors_file"])
        with patch.object(snapshot, "MAX_ENTRIES", 1):
            for _ in range(3):
                snapshot.store(value, self.embedding, self.lab.db_path, before, index["vectors_file"], sig)
        self.assertEqual(sum(p.is_dir() for p in self.root_cache.iterdir()), 1)
        restored = self.build()
        self.assertIs(restored.items[view][0], restored.items[view][1])
        query = TE.vectors_of(value, "red")
        # rows_of must be rebuilt after the synthetic duplication.
        value.rows_of = restored.rows_of
        self.assertEqual(value.rank(query, 10), restored.rank(query, 10))


if __name__ == "__main__":
    unittest.main()
