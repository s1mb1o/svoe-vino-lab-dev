"""Plan 82: an entry with `rotation_step` has one vector for each angle of the view `full`.

The tests use the lab of `embedding_lab.py` and its fake gateway. The fake vector holds the
mean colour and the width and height of the image, so a 90° image gives another vector than
the 0° image of the same bottle (the bottles are plain rectangles: 180° equals 0°).
"""
import collections
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

import embedding_lab  # noqa: F401  (puts pipeline/ on sys.path)
from embedding_lab import VIEWS_C_F, FakeGateway, standard_lab

import build_embeddings  # noqa: E402
import catalog_copy  # noqa: E402
import embedding_run  # noqa: E402
import embeddings  # noqa: E402
import matcher_bundle  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from matcher.bundle import load_bundle  # noqa: E402
from matcher.catalog import load_catalog  # noqa: E402


def quiet_backend(embedding):
    """The OpenAI backend with no waits between the tries."""
    return build_embeddings.OpenAIBackend(embedding, waits=(), timeout=10)


def raw_entry(**values):
    entry = {"name": "rot", "backend": "openai", "base_url": "http://127.0.0.1:9/v1",
             "model": "fake-model", "batch_size": 2, "views": copy.deepcopy(VIEWS_C_F),
             "rotation_step": 90}
    entry.update(values)
    return entry


class ConfigTest(unittest.TestCase):
    def test_the_angles_of_the_view_full(self):
        embedding = embeddings.Embedding(raw_entry())
        self.assertEqual(embedding.rotation_step, 90)
        self.assertEqual(embedding.angles("full"), [0, 90, 180, 270])
        self.assertIsNone(embedding.angles("label"))
        self.assertIsNone(embedding.angles("full", role="label"))
        self.assertEqual(embeddings.Embedding(raw_entry(rotation_step=5)).angles("full"),
                         list(range(0, 360, 5)))
        self.assertEqual(embedding.summary()["rotation_step"], 90)

    def test_an_entry_without_the_key_keeps_its_hash_and_summary(self):
        plain = embeddings.Embedding(raw_entry(rotation_step=None))
        self.assertIsNone(plain.rotation_step)
        self.assertNotIn("rotation_step", plain.summary())
        # The hash formula of the builds before plan 82.
        expected = embeddings.sha256_json({
            "backend": plain.backend, "model": plain.model, "extra_body": plain.extra_body,
            "view": "full", "steps": plain.views["full"],
            "steps_version": embeddings.STEPS_VERSION})
        self.assertEqual(plain.view_config_hash("full"), expected)

    def test_the_rotation_is_in_the_hash_of_the_view_full_alone(self):
        plain = embeddings.Embedding(raw_entry(rotation_step=None))
        rot90 = embeddings.Embedding(raw_entry())
        rot45 = embeddings.Embedding(raw_entry(rotation_step=45))
        self.assertNotEqual(rot90.view_config_hash("full"), plain.view_config_hash("full"))
        self.assertNotEqual(rot90.view_config_hash("full"), rot45.view_config_hash("full"))
        self.assertEqual(rot90.view_config_hash("label"), plain.view_config_hash("label"))

    def test_the_rules_of_the_key(self):
        full_only = {"full": copy.deepcopy(VIEWS_C_F["full"])}
        square = {"full": {"steps": [{"step": "segment", "target": "package"},
                                     {"step": "remove_background"},
                                     {"step": "white_background"},
                                     {"step": "square_on_white"}]}}
        ignore = {"full": {"steps": [{"step": "segment", "target": "package"},
                                     {"step": "white_background"},
                                     {"step": "resize", "max_size": 64,
                                      "aspect": "ignore"}]}}
        for values in ({"rotation_step": True}, {"rotation_step": 0},
                       {"rotation_step": 181}, {"rotation_step": "5"},
                       {"rotation_step": 5.0}, {"views": {"label": VIEWS_C_F["label"]}},
                       {"views": square}, {"views": ignore}, {"batch_size": 1}):
            with self.subTest(values=values):
                with self.assertRaises(embeddings.ConfigError):
                    embeddings.Embedding(raw_entry(**values))
        self.assertEqual(embeddings.Embedding(raw_entry(views=full_only)).angles("full")[:2],
                         [0, 90])


class RecordRowsTest(unittest.TestCase):
    def test_rows_and_angles_of_a_record(self):
        self.assertEqual(embeddings.record_rows({"row": 3}, 4), slice(3, 4))
        self.assertEqual(embeddings.record_angles({"row": 3}), [0])
        record = {"row": 1, "angles": [0, 90, 180]}
        self.assertEqual(embeddings.record_rows(record, 4), slice(1, 4))
        self.assertEqual(embeddings.record_angles(record), [0, 90, 180])

    def test_a_bad_record_is_a_value_error(self):
        for record in ({"row": None}, {"row": True}, {"row": -1}, {"row": 4},
                       {"row": 0, "angles": "0,90"}, {"row": 0, "angles": [0]},
                       {"row": 0, "angles": [90, 0]}, {"row": 0, "angles": [0, 0]},
                       {"row": 0, "angles": [0, 360]}, {"row": 0, "angles": [0, True]},
                       {"row": 2, "angles": [0, 90, 180]}):
            with self.subTest(record=record):
                with self.assertRaises(ValueError):
                    embeddings.record_rows(record, 4)

    def test_the_rows_cover_the_file_one_time(self):
        good = [{"row": 0, "angles": [0, 180]}, {"row": 2}, {"row": 3, "angles": [0, 90]}]
        embeddings.check_rows(good, 5)
        for records, count in (([{"row": 0, "angles": [0, 180]}, {"row": 3}], 4),
                               ([{"row": 0, "angles": [0, 180]}, {"row": 1}], 3),
                               ([{"row": 0}, {"row": 1}], 3)):
            with self.subTest(records=records):
                with self.assertRaises(ValueError):
                    embeddings.check_rows(records, count)


class RotatedLab(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.gateway = FakeGateway()
        self.lab = standard_lab(self.tmp.name, self.gateway.base_url)

    def tearDown(self):
        self.gateway.close()
        self.lab.close()
        self.tmp.cleanup()

    def add(self, name="rot", **values):
        values.setdefault("rotation_step", 90)
        return self.lab.add_entry(name, **values)

    def embedding(self, name="rot"):
        return embeddings.load_settings(self.lab.config_path).find(name)

    def build(self, name="rot", stop=None, make_backend=quiet_backend, workers=1):
        """Run one build. Return (counts, events)."""
        settings = embeddings.load_settings(self.lab.config_path)
        embedding = settings.find(name)
        directory = self.lab.entry_dir(name)
        os.makedirs(directory, exist_ok=True)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            counts = build_embeddings.run(embedding, settings.db_path, directory,
                                          make_backend=make_backend, stop=stop,
                                          workers=workers)
        return counts, [json.loads(line) for line in out.getvalue().splitlines()]

    def index(self, name="rot"):
        directory = self.lab.entry_dir(name)
        index = embeddings.read_index(directory)
        return index, embeddings.read_vectors(directory, index)

    def full_records(self, index):
        return {record["source_sha256"]: record for record in index["items"]
                if record["view"] == "full"}


class RotatedInputsTest(RotatedLab):
    def item(self, digest, step=90):
        self.add(rotation_step=step)
        embedding = self.embedding()
        conn = embeddings.open_database(self.lab.db_path)
        try:
            _, sources = embeddings.read_inputs(conn, self.lab.db_path)
        finally:
            conn.close()
        return embeddings.plan_items(embedding, sources)[(digest, "full")], sources[digest]

    def test_the_first_image_is_the_image_of_prepare(self):
        for digest in (self.lab.grey, self.lab.transparent):
            with self.subTest(digest=digest):
                item, source = self.item(digest)
                images = embeddings.rotated_inputs(item, source["path"], item["angles"])
                prepared = embeddings.prepare(item, source["path"])
                self.assertEqual(len(images), 4)
                self.assertEqual(images[0].size, prepared.size)
                self.assertTrue(np.array_equal(np.asarray(images[0]), np.asarray(prepared)))

    def test_the_canvas_grows_and_the_scale_stays(self):
        item, source = self.item(self.lab.grey, step=45)
        images = embeddings.rotated_inputs(item, source["path"], item["angles"])
        # The cut is 20 x 80; the resize to 64 gives the scale 0.8 and 16 x 64 at 0°.
        self.assertEqual(images[0].size, (16, 64))
        self.assertEqual(images[2].size, (64, 16))           # 90°
        cut = embeddings.prepare(dict(item, steps=item["steps"][:-1]), source["path"])
        turned = cut.rotate(45, resample=Image.Resampling.BICUBIC, expand=True,
                            fillcolor=(255, 255, 255))
        self.assertEqual(images[1].size, (round(turned.width * 0.8),
                                          round(turned.height * 0.8)))
        self.assertTrue(all(image.mode == "RGB" for image in images))
        # The corners of the larger canvas are white.
        self.assertEqual(images[1].getpixel((0, 0)), (255, 255, 255))


class RotatedBuildTest(RotatedLab):
    def test_each_full_item_has_one_row_for_each_angle(self):
        self.add()
        counts, events = self.build()
        self.assertEqual(events[-1]["event"], "done")
        index, vectors = self.index()
        records = self.full_records(index)
        self.assertEqual(sorted(records), sorted([self.lab.transparent, self.lab.grey,
                                                  self.lab.patched]))
        for digest, record in records.items():
            with self.subTest(digest=digest):
                self.assertEqual(record["angles"], [0, 90, 180, 270])
                rows = vectors[embeddings.record_rows(record, len(vectors))]
                # values 3 and 4 are the width and the height of the image / 100.
                self.assertAlmostEqual(rows[0][3] / rows[0][4], rows[1][4] / rows[1][3])
                self.assertFalse(np.allclose(rows[0], rows[1]))
                self.assertTrue(np.allclose(rows[0], rows[2]))   # a rectangle: 180° = 0°
                self.assertTrue(np.allclose(np.linalg.norm(rows, axis=1), 1.0))
        labels = [record for record in index["items"] if record["view"] == "label"]
        self.assertTrue(labels and all("angles" not in record for record in labels))
        embeddings.check_rows(index["items"], len(vectors))
        self.assertEqual(len(vectors), 3 * 4 + len(labels))
        self.assertEqual(counts["vectors"], 12)
        # The label items go first, in batches; then each rotated item: 4 images in 2
        # requests of 2. No rotated request holds one image alone.
        sizes = [len(body["input"]) for body in self.gateway.requests]
        self.assertEqual(sizes[-6:], [2] * 6)
        self.assertEqual(sum(sizes), 12 + len(labels))

    def test_the_0_degree_image_and_vector_are_the_plain_ones(self):
        self.lab.add_entry()                       # the plain entry `gw`
        self.add()
        self.build("gw")
        self.build("rot")
        plain_index, plain_vectors = self.index("gw")
        rot_index, rot_vectors = self.index("rot")
        plain = self.full_records(plain_index)
        for digest, record in self.full_records(rot_index).items():
            with self.subTest(digest=digest):
                with open(os.path.join(self.lab.entry_dir("gw"), plain[digest]["image"]),
                          "rb") as fh:
                    plain_png = fh.read()
                with open(os.path.join(self.lab.entry_dir("rot"), record["image"]),
                          "rb") as fh:
                    self.assertEqual(fh.read(), plain_png)
                self.assertTrue(np.allclose(rot_vectors[record["row"]],
                                            plain_vectors[plain[digest]["row"]]))

    def test_a_second_build_builds_nothing_and_keeps_the_file(self):
        self.add()
        self.build()
        first, _ = self.index()
        counts, _ = self.build()
        second, vectors = self.index()
        self.assertEqual(counts["built"], 0)
        self.assertEqual(second["vectors_file"], first["vectors_file"])
        self.assertEqual(self.full_records(second), self.full_records(first))

    def test_more_workers_give_the_same_index(self):
        self.add("rot")
        self.add("rot3")
        self.build("rot")
        self.build("rot3", workers=3)
        one, one_vectors = self.index("rot")
        three, three_vectors = self.index("rot3")
        for digest, record in self.full_records(one).items():
            other = self.full_records(three)[digest]
            with self.subTest(digest=digest):
                self.assertEqual(other["angles"], record["angles"])
                self.assertTrue(np.allclose(
                    three_vectors[embeddings.record_rows(other, len(three_vectors))],
                    one_vectors[embeddings.record_rows(record, len(one_vectors))]))

    def test_a_stopped_build_continues_with_the_rest(self):
        self.add()
        stop = build_embeddings.Stop()
        calls = []

        def stopping_backend(embedding):
            backend = quiet_backend(embedding)
            original = backend.embed

            def embed(images):
                calls.append(len(images))
                result = original(images)
                # The close-up (1 image), then the first rotated item (2 + 2 images).
                if sum(calls) >= 5:
                    stop.requested = True
                return result
            backend.embed = embed
            return backend

        _, events = self.build(stop=stop, make_backend=stopping_backend)
        self.assertEqual(events[-1]["event"], "stopped")
        index, vectors = self.index()
        embeddings.check_rows(index["items"], len(vectors))
        done = len(self.full_records(index))
        self.assertLess(done, 3)
        counts, events = self.build()
        self.assertEqual(events[-1]["event"], "done")
        index, vectors = self.index()
        self.assertEqual(len(self.full_records(index)), 3)
        self.assertEqual(counts["built"], 3 - done)
        embeddings.check_rows(index["items"], len(vectors))

    def test_a_changed_step_makes_the_items_stale(self):
        self.add()
        self.build()
        self.add(rotation_step=180)
        embedding = self.embedding()
        directory = self.lab.entry_dir("rot")
        index = embeddings.read_index(directory)
        conn = embeddings.open_database(self.lab.db_path)
        try:
            _, sources = embeddings.read_inputs(conn, self.lab.db_path)
        finally:
            conn.close()
        status = embeddings.item_status(embeddings.plan_items(embedding, sources), index,
                                        embeddings.image_names(directory))
        full = {state for (digest, view), (state, _) in status.items() if view == "full"
                and digest in self.full_records(index)}
        self.assertEqual(full, {"stale"})
        counts, _ = self.build()
        index, vectors = self.index()
        self.assertEqual(counts["built"], 3)
        self.assertTrue(all(record["angles"] == [0, 180]
                            for record in self.full_records(index).values()))
        embeddings.check_rows(index["items"], len(vectors))

    def test_a_bad_record_is_built_again_alone(self):
        self.add()
        self.build()
        directory = self.lab.entry_dir("rot")
        path = os.path.join(directory, "index.json")
        with open(path, encoding="utf-8") as fh:
            index = json.load(fh)
        bad = next(record for record in index["items"] if "angles" in record)
        bad["angles"] = [0, 90, 180, 270, 45]     # one row too many: it overlaps the next
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(index, fh)
        with self.assertRaises(ValueError):
            embeddings.read_vectors(directory, index)
        requests = len(self.gateway.requests)
        counts, events = self.build()
        self.assertEqual(events[-1]["event"], "done")
        self.assertFalse(any(event["event"] == "warning" for event in events))
        self.assertLessEqual(counts["built"], 2)
        self.assertLess(len(self.gateway.requests) - requests, 4)
        index, vectors = self.index()
        embeddings.check_rows(index["items"], len(vectors))


class RotatedBundleTest(RotatedLab):
    def setUp(self):
        super().setUp()
        self.add()
        self.build()
        self.out = Path(self.tmp.name)

    def items(self, path):
        return [json.loads(line) for line in (path / "items.jsonl").read_text().splitlines()]

    def rewrite(self, path, name, rows):
        payload = path / name
        payload.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
                           encoding="utf-8")
        manifest_path = path / matcher_bundle.MANIFEST
        manifest = json.loads(manifest_path.read_text())
        manifest["files"][name] = matcher_bundle.file_record(payload)
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    def test_the_bundle_of_a_rotated_entry_is_version_3(self):
        path = self.out / "bundle"
        matcher_bundle.build_bundle(self.lab.config_path, "rot", path, include_images=True)
        summary = matcher_bundle.validate_bundle(path)
        self.assertEqual(summary["format_version"], 3)
        items = self.items(path)
        full = [item for item in items if item["view"] == "full"]
        self.assertEqual(len(full), 12)
        by_source = collections.defaultdict(list)
        for item in full:
            by_source[item["source_sha256"]].append(item["angle"])
        self.assertTrue(all(angles == [0, 90, 180, 270] for angles in by_source.values()))
        self.assertTrue(all(item["angle"] == 0 for item in items if item["view"] == "label"))
        manifest = json.loads((path / "manifest.json").read_text())
        pairs_ = {(item["source_sha256"], item["view"]) for item in items}
        self.assertEqual(manifest["counts"]["items"], len(items))
        self.assertEqual(manifest["counts"]["planned_items"],
                         len(pairs_) + manifest["counts"]["omissions"])
        self.assertEqual(manifest["counts"]["images"], len(pairs_))

    def test_a_plain_entry_stays_version_2(self):
        self.build("gw")
        path = self.out / "plain"
        matcher_bundle.build_bundle(self.lab.config_path, "gw", path)
        self.assertEqual(matcher_bundle.validate_bundle(path)["format_version"], 2)
        self.assertTrue(all("angle" not in item for item in self.items(path)))

    def test_the_validator_rejects_bad_rows_of_version_3(self):
        path = self.out / "bundle"
        matcher_bundle.build_bundle(self.lab.config_path, "rot", path)
        good = self.items(path)
        turned = next(number for number, item in enumerate(good) if item["angle"] == 90)
        changes = {
            "an angle of 360": lambda rows: rows[turned].update(angle=360),
            "no angle": lambda rows: rows[turned].pop("angle"),
            # The 90° row of an image gets the angle of its 0° row.
            "a repeated angle": lambda rows: rows[turned].update(angle=0),
        }
        for name, change in changes.items():
            with self.subTest(name=name):
                rows = copy.deepcopy(good)
                change(rows)
                self.rewrite(path, "items.jsonl", rows)
                with self.assertRaises(matcher_bundle.BundleError):
                    matcher_bundle.validate_bundle(path)

    def test_the_catalogue_copy_and_the_bundle_give_the_same_rows_and_angles(self):
        matcher_bundle.build_bundle(self.lab.config_path, "rot", self.out / "bundle")
        bundle = load_bundle(self.out / "bundle")
        result = catalog_copy.copy_catalog(self.lab.config_path, self.out / "copy",
                                           names=["rot"])
        catalog = load_catalog(result["path"], "rot")

        def rows(value, view):
            matrix, wines = value.views[view]
            return collections.Counter(
                (value.slugs[wine], matrix[row].tobytes(), int(value.angles[view][row]))
                for row, wine in enumerate(wines))

        self.assertEqual(set(catalog.views), set(bundle.views))
        for view in bundle.views:
            self.assertEqual(rows(catalog, view), rows(bundle, view))
        rng = np.random.default_rng(3)
        for vector in rng.normal(size=(10, bundle.dimension)).astype(np.float32):
            vector /= np.linalg.norm(vector)
            self.assertEqual(catalog.ranked("full", vector), bundle.ranked("full", vector))
        # A stored 90° row ranks its own wine first.
        record = self.full_records(self.index()[0])[self.lab.grey]
        vector = self.index()[1][record["row"] + 1]
        self.assertEqual(bundle.top1("full", vector)[0], "grey")


class RotatedSearchTest(RotatedLab):
    def setUp(self):
        super().setUp()
        self.add()
        self.build()
        self.catalogue = embedding_run.Catalogue(self.embedding(), self.lab.db_path)
        index, self.vectors = self.index()
        self.records = self.full_records(index)

    def test_the_catalogue_holds_each_angle_row(self):
        matrix, numbers = self.catalogue.views["full"]
        # 3 full images; the image of `transparent` is also the image of `shared`.
        self.assertEqual(len(matrix), 4 * 4)
        self.assertEqual(self.catalogue.angles["full"].tolist().count(90), 4)
        self.assertNotIn("label", self.catalogue.angles)
        self.assertEqual(self.catalogue.state["rotation_step"], 90)
        self.assertEqual(self.catalogue.state["rows"]["full"], 16)

    def test_a_rotated_query_finds_its_wine_and_its_angle(self):
        record = self.records[self.lab.grey]
        query = self.vectors[record["row"] + 1]          # the vector of 90°
        cands = self.catalogue.rank({"full": query}, top_k=3)
        self.assertEqual(cands[0]["slug"], "grey")
        self.assertEqual(cands[0]["angle"], 90)
        self.assertAlmostEqual(cands[0]["full"], 1.0, places=4)
        self.assertEqual(set(cands[0]), {"slug", "score", "rank", "full", "angle", "items"})
        # One item for each image of the wine, with the angle of its best row.
        items = cands[0]["items"]
        self.assertEqual([(item["sha256"], item["angle"]) for item in items],
                         [(self.lab.grey, 90)])

    def test_the_trace_names_the_angle_of_the_best_row(self):
        record = self.records[self.lab.patched]
        trace = embedding_run.Trace()
        self.catalogue.rank({"full": self.vectors[record["row"] + 1]}, 3, trace)
        search = next(step for step in trace.value()["steps"] if step["id"] == "search")
        top = search["out"]["top"][0]
        self.assertEqual((top["slug"], top["sha256"], top["angle"]),
                         ("patched", self.lab.patched, 90))
        self.assertEqual(search["out"]["rows"], 16)

    def test_a_query_made_from_the_rotated_input_gets_the_angle(self):
        embedding = self.embedding()
        conn = embeddings.open_database(self.lab.db_path)
        try:
            _, sources = embeddings.read_inputs(conn, self.lab.db_path)
        finally:
            conn.close()
        item = embeddings.plan_items(embedding, sources)[(self.lab.grey, "full")]
        image = embeddings.rotated_inputs(item, sources[self.lab.grey]["path"], [0, 90])[1]
        backend = quiet_backend(embedding)
        vector = backend.embed([embeddings.png_bytes(image), embeddings.png_bytes(image)])[0]
        vector = np.asarray(vector) / np.linalg.norm(vector)
        cands = self.catalogue.rank({"full": vector}, top_k=2)
        self.assertEqual((cands[0]["slug"], cands[0]["angle"]), ("grey", 90))


if __name__ == "__main__":
    unittest.main()
