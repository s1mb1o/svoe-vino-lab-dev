"""Tests of the lab configuration `mock` (plan 23): `pipeline/mock_run.py`, and the backend
`mock` of `pipeline/embeddings.py` and `pipeline/build_embeddings.py`: it builds as any
entry, with random unit vectors."""
import collections
import contextlib
import io
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import testset_fixture as FX  # noqa: E402
from embedding_lab import VIEWS_C_F, standard_lab  # noqa: E402
import benchmark as BM  # noqa: E402
import build_embeddings  # noqa: E402
import embedding_routes  # noqa: E402
import embeddings  # noqa: E402
import import_testset as IT  # noqa: E402
import mock_run as MR  # noqa: E402

PHOTOS = {"wine-a/01.jpg": b"a1", "wine-a/02.jpg": b"a2", "wine-b/01.jpg": b"b1",
          "__null__/n1.jpg": b"n1"}
# A NULL photo is a `no match` query only with the label `positive` (owner answer of
# 2026-09-25T18:05:36+0300, plan 24).
LABELS = {"wine-a": {"01.jpg": {"label": "positive"}, "02.jpg": {"label": "negative"}},
          "wine-b": {"01.jpg": {"label": "positive"}},
          "__null__": {"n1.jpg": {"label": "positive"}}}
SLUGS = ["wine-%02d" % i for i in range(40)]


def write_config(root, db, entries):
    path = Path(root) / "config.yaml"
    path.write_text(json.dumps({"rootdir": str(root), "database_file": db,
                                "embeddings": entries}), encoding="utf-8")
    return str(path)


class MockBackendTest(unittest.TestCase):
    def backend(self, seed=1, top_k=5, photos=300):
        places = {"p%d" % i: ("%064x" % i, [SLUGS[i % len(SLUGS)]]) for i in range(photos)}
        return MR.MockBackend(SLUGS, places, top_k, seed)

    def test_each_answer_holds_top_k_distinct_slugs_with_falling_scores(self):
        backend = self.backend()
        for path in backend.places:
            cands, ms, status, error = backend.ask(path)
            self.assertEqual(len(cands), 5)
            self.assertEqual([c["rank"] for c in cands], [1, 2, 3, 4, 5])
            self.assertEqual(len({c["slug"] for c in cands}), 5)
            self.assertTrue(set(c["slug"] for c in cands) <= set(SLUGS))
            scores = [c["score"] for c in cands]
            self.assertEqual(scores, sorted(scores, reverse=True))
            self.assertTrue(all(0 <= s <= 1 for s in scores))
            self.assertTrue(MR.LATENCY_MS[0] <= ms <= MR.LATENCY_MS[1])
            self.assertEqual((status, error), (200, None))

    def test_the_place_slug_gets_every_rank_and_absent(self):
        backend = self.backend()
        ranks = collections.Counter()
        for path, (_, (slug,)) in backend.places.items():
            cands = backend.ask(path)[0]
            ranks[next((c["rank"] for c in cands if c["slug"] == slug), None)] += 1
        self.assertEqual(set(ranks), {1, 2, 3, 4, 5, None})

    def test_the_same_seed_gives_the_same_answers(self):
        one, two, other = self.backend(seed=7), self.backend(seed=7), self.backend(seed=8)
        answers = [one.ask(p) for p in one.places]
        self.assertEqual(answers, [two.ask(p) for p in two.places])
        self.assertNotEqual(answers, [other.ask(p) for p in other.places])

    def test_a_small_catalogue_gives_fewer_candidates(self):
        backend = MR.MockBackend(["a", "b"], {"p": ("0" * 64, [])}, 5, 1)
        self.assertEqual(sorted(c["slug"] for c in backend.ask("p")[0]), ["a", "b"])

    def test_top_k_must_be_positive(self):
        with self.assertRaises(ValueError):
            MR.MockBackend(SLUGS, {}, 0, 1)


class MockRunTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.db, self.schema = FX.make_database(self.root)
        set_dir = FX.write_set(self.root, PHOTOS, LABELS)
        IT.import_testset(self.db, "my", set_dir, lambda m: None, self.schema)
        self.runs = self.root / "runs"

    def tearDown(self):
        self.directory.cleanup()

    def test_a_mock_run_writes_the_run_files_with_the_configuration(self):
        backend = MR.build_backend(self.db, "my", 2, 5, self.schema)
        run_dir, met = BM.run_benchmark(self.db, "my", backend, str(self.runs), workers=1,
                                        embeddings={}, log=lambda m: None,
                                        schema_dir=self.schema, configuration="mock")
        self.assertTrue(Path(run_dir).name.endswith("-lab-mock-my"))
        meta = json.loads(Path(run_dir, "run.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["configuration"], "mock")
        self.assertEqual((meta["backend"]["id"], meta["backend"]["seed"]), ("mock", 5))
        self.assertIsNone(meta["backend"]["url"])
        rows = [json.loads(line) for line in
                Path(run_dir, "results.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(rows), 4)
        for row in rows:
            self.assertEqual(len(row["candidates"]), 2)
            self.assertTrue({c["slug"] for c in row["candidates"]}
                            <= {"wine-a", "wine-b", "wine-c"})
        self.assertEqual(met["positive"]["n"], 2)

    def test_only_active_wines_are_candidates(self):
        conn = sqlite3.connect(self.db)
        with conn:
            conn.execute("UPDATE wine_catalog SET state = 'Disabled' WHERE wine_slug = 'wine-c'")
        conn.close()
        backend = MR.build_backend(self.db, "my", 3, 5, self.schema)
        self.assertEqual(backend.slugs, ["wine-a", "wine-b"])

    def test_the_place_slugs_come_from_the_positive_and_negative_rows(self):
        backend = MR.build_backend(self.db, "my", 2, 5, self.schema)
        places = sorted(slugs for _, slugs in backend.places.values())
        self.assertEqual(places, [[], ["wine-a"], ["wine-a"], ["wine-b"]])


class MockConfigurationTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def test_a_mock_entry_has_views_and_the_mock_model(self):
        entry = embeddings.Embedding({"name": "mock", "backend": "mock", "views": VIEWS_C_F})
        self.assertEqual((entry.backend, entry.model, entry.base_url),
                         ("mock", embeddings.MOCK_MODEL, None))
        self.assertEqual(sorted(entry.views), ["full", "label"])
        self.assertEqual(entry.summary()["name"], "mock")

    def test_a_mock_entry_takes_no_endpoint_model_or_extra_body(self):
        for key, value in (("model", "m"), ("base_url", "http://x/v1"),
                           ("extra_body", {"max_num_patches": 256})):
            with self.assertRaisesRegex(embeddings.ConfigError, "takes no %s" % key):
                embeddings.Embedding({"name": "mock", "backend": "mock", "views": VIEWS_C_F,
                                      key: value})

    def test_the_mock_backend_gives_seeded_unit_vectors(self):
        entry = embeddings.Embedding({"name": "mock", "backend": "mock", "views": VIEWS_C_F})
        backend = build_embeddings.make_backend(entry)
        self.assertIsInstance(backend, build_embeddings.MockBackend)
        vectors = backend.embed([b"png a", b"png b", b"png a"])
        self.assertEqual(vectors.shape, (3, build_embeddings.MOCK_DIM))
        self.assertEqual(vectors.dtype, np.float32)
        np.testing.assert_allclose(np.linalg.norm(vectors, axis=1), 1.0, rtol=1e-5)
        np.testing.assert_array_equal(vectors[0], vectors[2])
        self.assertFalse(np.allclose(vectors[0], vectors[1]))
        self.assertEqual(backend.embed([]).shape, (0, build_embeddings.MOCK_DIM))

    def test_a_mock_build_works_as_any_entry(self):
        lab = standard_lab(str(self.root), "http://127.0.0.1:9/v1")
        try:
            lab.entries.append({"name": "mock", "backend": "mock", "batch_size": 2,
                                "views": VIEWS_C_F})
            lab.write_config()
            settings = embeddings.load_settings(lab.config_path)
            entry = settings.find("mock")
            directory = lab.entry_dir("mock")
            os.makedirs(directory)
            for _ in range(2):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    counts = build_embeddings.run(entry, settings.db_path, directory)
                events = [json.loads(line)["event"] for line in out.getvalue().splitlines()]
                self.assertEqual((events[0], events[-1]), ("start", "done"))
                if _ == 0:
                    # The inputs of the fixture: 4 items build, 5 fail as for any entry.
                    self.assertEqual((counts["built"], counts["failed"]), (4, 5))
            self.assertEqual(counts["built"], 0)  # the second build makes nothing again
            index = embeddings.read_index(directory)
            vectors = embeddings.read_vectors(directory, index)
            self.assertEqual(vectors.shape, (4, build_embeddings.MOCK_DIM))
            self.assertEqual(index["dim"], build_embeddings.MOCK_DIM)
            self.assertIn("mock", index["software"])
        finally:
            lab.close()

    def test_check_configuration_needs_the_mock_entry(self):
        config = write_config(self.root, "lab.sqlite3", [])
        with self.assertRaisesRegex(embeddings.ConfigError, "no configuration mock"):
            MR.check_configuration(config)
        MR.check_configuration(write_config(self.root, "lab.sqlite3", [
            {"name": "mock", "backend": "mock", "views": VIEWS_C_F}]))

    def test_the_project_config_holds_the_mock_entry(self):
        MR.check_configuration()


if __name__ == "__main__":
    unittest.main()
