import copy
import os
import tempfile
import unittest
from contextlib import closing

from PIL import Image, ImageDraw

import embedding_lab  # noqa: F401  (puts pipeline/ on sys.path)
from embedding_lab import VIEWS_C_F, standard_lab

import alternatives  # noqa: E402
import dis_litert  # noqa: E402
import embeddings  # noqa: E402


def entry(**values):
    raw = {"name": "e1", "backend": "openai", "base_url": "http://127.0.0.1:1/v1",
           "model": "m", "views": copy.deepcopy(VIEWS_C_F)}
    raw.update(values)
    return raw


def steps(*items):
    return {"full": {"steps": list(items)}}


SEG = {"step": "segment", "target": "package"}
RB = {"step": "remove_background"}
WB = {"step": "white_background"}


class ConfigTest(unittest.TestCase):
    def error(self, raw):
        with self.assertRaises(embeddings.ConfigError) as caught:
            embeddings.Embedding(raw)
        return str(caught.exception)

    def test_valid_entry_fills_the_default_options(self):
        embedding = embeddings.Embedding(entry())
        self.assertEqual(embedding.views["full"][3],
                         {"step": "resize", "max_size": 64, "aspect": "keep", "upscale": False})
        self.assertEqual(embedding.batch_size, embeddings.DEFAULT_BATCH_SIZE)

    def test_default_options_give_the_same_hash(self):
        plain = embeddings.Embedding(entry(views=steps(SEG, WB, {"step": "resize", "max_size": 99})))
        explicit = embeddings.Embedding(entry(views=steps(
            SEG, WB, {"step": "resize", "max_size": 99, "aspect": "keep", "upscale": False})))
        self.assertEqual(plain.view_config_hash("full"), explicit.view_config_hash("full"))

    def test_name_and_base_url_are_not_in_the_hash(self):
        one = embeddings.Embedding(entry())
        two = embeddings.Embedding(entry(name="e2", base_url="http://10.0.0.1:5/v1", batch_size=3))
        self.assertEqual(one.view_config_hash("full"), two.view_config_hash("full"))
        three = embeddings.Embedding(entry(extra_body={"max_num_patches": 512}))
        self.assertNotEqual(one.view_config_hash("full"), three.view_config_hash("full"))

    def test_a_closeup_has_its_own_hash(self):
        embedding = embeddings.Embedding(entry())
        self.assertNotEqual(embedding.view_config_hash("label", "full"),
                            embedding.view_config_hash("label", "label"))

    def test_remove_background_needs_white_background(self):
        self.assertIn("drops the alpha channel", self.error(entry(views=steps(SEG, RB))))

    def test_variant_a_is_allowed(self):
        embeddings.Embedding(entry(views=steps(SEG)))

    def test_dis_step_fills_the_android_defaults(self):
        embedding = embeddings.Embedding(entry(views=steps({
            "step": "segment_dis", "model": "dis", "revision": "one"})))
        self.assertEqual(embedding.views["full"][0], {
            "step": "segment_dis", "model": "dis", "revision": "one",
            "threshold": 0.5, "margin": 0.04})

    def test_dis_step_checks_its_contract(self):
        cases = [
            ({"step": "segment_dis", "revision": "one"}, "needs the option `model`"),
            ({"step": "segment_dis", "model": "dis"}, "needs the option `revision`"),
            ({"step": "segment_dis", "model": "dis", "revision": "one",
              "threshold": 1}, "threshold MUST be between"),
            ({"step": "segment_dis", "model": "dis", "revision": "one",
              "margin": 0.6}, "margin MUST be"),
        ]
        for step, message in cases:
            with self.subTest(message=message):
                self.assertIn(message, self.error(entry(views=steps(step))))

    def test_step_rules(self):
        cases = [
            (steps(WB), "first step MUST be `segment`"),
            (steps(SEG, WB, RB), "directly after `segment`"),
            (steps(SEG, WB, WB), "repeated: white_background"),
            (steps(SEG, {"step": "blur"}), "unknown step"),
            (steps(SEG, {"step": "white_background", "colour": 1}), "unknown option"),
            (steps({"step": "segment"}), "needs the option `target`"),
            (steps({"step": "segment", "target": "cork"}), "target MUST be"),
            (steps(SEG, {"step": "resize", "max_size": 8}), "max_size MUST be"),
            (steps(SEG, {"step": "resize", "max_size": 64, "aspect": "fit"}), "aspect MUST be"),
            (steps(SEG, {"step": "resize", "max_size": 64, "upscale": "yes"}), "upscale MUST be"),
            ({"back": {"steps": [SEG]}}, "unknown view"),
        ]
        for views, message in cases:
            with self.subTest(message=message):
                self.assertIn(message, self.error(entry(views=views)))

    def test_entry_rules(self):
        cases = [
            (entry(name="Bad Name"), "MUST match"),
            (entry(colour=1), "unknown key"),
            (entry(backend="grpc"), "backend MUST be"),
            (entry(base_url="http://192.168.86.14:18081/ui/#/models/x"), "llama-swap UI"),
            (entry(base_url="ftp://x"), "http or https"),
            (entry(model=""), "model MUST be"),
            (entry(extra_body={"model": "x"}), "MUST NOT hold model"),
            (entry(batch_size=0), "batch_size MUST be"),
            (entry(backend="local", base_url=None, extra_body={"x": 1}), "accepts only"),
            (entry(backend="local"), "base_url is a key of the backend openai"),
        ]
        for raw, message in cases:
            with self.subTest(message=message):
                self.assertIn(message, self.error(raw))

    def test_load_settings_keeps_the_error_of_one_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "config.yaml")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("rootdir: %s\ndatabase_file: lab.sqlite3\nembedding_python: ~/py\n"
                         "embeddings:\n"
                         "  - {name: ok, backend: openai, base_url: 'http://h/v1', model: m,"
                         " views: {full: {steps: [{step: segment, target: package}]}}}\n"
                         "  - {name: bad, backend: openai}\n"
                         "  - {name: ok, backend: openai, base_url: 'http://h/v1', model: m,"
                         " views: {full: {steps: [{step: segment, target: package}]}}}\n" % tmp)
            settings = embeddings.load_settings(path)
            self.assertEqual(settings.db_path, os.path.join(tmp, "lab.sqlite3"))
            self.assertEqual(settings.python, os.path.expanduser("~/py"))
            self.assertEqual([name for name, _, _ in settings.entries], ["ok", "bad", "ok"])
            self.assertIsNotNone(settings.find("ok"))
            with self.assertRaises(embeddings.ConfigError):
                settings.find("bad")
            self.assertIn("earlier entry", settings.entries[2][2])
            with self.assertRaises(KeyError):
                settings.find("none")


class StepTest(unittest.TestCase):
    def test_resize_keep_scales_the_long_side(self):
        image = Image.new("RGB", (200, 400))
        out = embeddings.resize(image, {"max_size": 100, "aspect": "keep", "upscale": False})
        self.assertEqual(out.size, (50, 100))

    def test_resize_ignore_squashes(self):
        image = Image.new("RGB", (200, 400))
        out = embeddings.resize(image, {"max_size": 100, "aspect": "ignore", "upscale": False})
        self.assertEqual(out.size, (100, 100))

    def test_resize_does_not_upscale_by_default(self):
        image = Image.new("RGB", (20, 40))
        keep = {"max_size": 100, "aspect": "keep", "upscale": False}
        self.assertEqual(embeddings.resize(image, keep).size, (20, 40))
        self.assertEqual(embeddings.resize(image, dict(keep, upscale=True)).size, (50, 100))

    def test_on_white(self):
        image = Image.new("RGBA", (2, 1), (0, 0, 0, 0))
        image.putpixel((1, 0), (10, 20, 30, 255))
        out = embeddings.on_white(image)
        self.assertEqual(out.mode, "RGB")
        self.assertEqual(out.getpixel((0, 0)), (255, 255, 255))
        self.assertEqual(out.getpixel((1, 0)), (10, 20, 30))

    def test_dis_mask_crops_composites_and_squares(self):
        import numpy as np

        source = Image.new("RGB", (200, 100), (10, 20, 30))
        mask = np.zeros((dis_litert.SIZE, dis_litert.SIZE), dtype=np.float32)
        mask[256:768, 256:768] = 0.5
        cropped = dis_litert.composite_mask(source, mask, margin=0)
        self.assertEqual(cropped.size, (100, 50))
        self.assertEqual(cropped.getpixel((50, 25)), (133, 138, 143))
        squared = dis_litert.square_on_white(cropped)
        self.assertEqual(squared.size, (100, 100))
        self.assertEqual(squared.getpixel((0, 0)), (255, 255, 255))

    def test_dis_mask_rejects_empty_and_complete_masks(self):
        import numpy as np

        source = Image.new("RGB", (10, 20))
        for value, message in ((0.0, "no main object"), (1.0, "complete image")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(dis_litert.DisError, message):
                    dis_litert.composite_mask(
                        source, np.full((dis_litert.SIZE, dis_litert.SIZE), value,
                                        dtype=np.float32))

    def test_dis_output_uses_reference_min_max_normalization(self):
        import numpy as np

        raw = np.linspace(0.5, 0.731, dis_litert.SIZE * dis_litert.SIZE,
                          dtype=np.float32).reshape(dis_litert.SIZE, dis_litert.SIZE)
        mask = dis_litert.normalize_mask(raw)
        self.assertAlmostEqual(float(mask.min()), 0.0)
        self.assertAlmostEqual(float(mask.max()), 1.0)
        self.assertAlmostEqual(float(mask[512, 0]), 0.5, places=3)
        with self.assertRaisesRegex(dis_litert.DisError, "flat mask"):
            dis_litert.normalize_mask(np.full_like(raw, 0.5))


class LabTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.lab = standard_lab(self.tmp.name, "http://127.0.0.1:9/v1")

    def tearDown(self):
        self.lab.close()
        self.tmp.cleanup()

    def inputs(self):
        with closing(embeddings.open_database(self.lab.db_path)) as conn:
            return embeddings.read_inputs(conn, self.lab.db_path)

    def test_inputs_hold_active_wines_and_the_patched_card(self):
        wines, sources = self.inputs()
        self.assertEqual([wine["slug"] for wine in wines],
                         ["transparent", "grey", "patched", "shared", "unprocessed"])
        patched = next(wine for wine in wines if wine["slug"] == "patched")
        self.assertEqual(patched["columns"], [("main_patched", self.lab.patched)])
        transparent = wines[0]
        self.assertEqual(transparent["columns"], [("main", self.lab.transparent),
                                                  ("label_front", self.lab.closeup)])
        self.assertEqual(sources[self.lab.closeup]["role"], "label")
        self.assertNotIn(self.lab.patched_main, sources)
        self.assertNotIn(self.lab.disabled, sources)
        self.assertIsNone(sources[self.lab.unprocessed]["cuts"]["package"])
        self.assertEqual(sources[self.lab.grey]["cuts"]["package"]["box"], (30, 20, 50, 100))

    def test_items_of_each_view(self):
        _, sources = self.inputs()
        items = embeddings.plan_items(embeddings.Embedding(entry()), sources)
        full = sorted(key[0] for key in items if key[1] == "full")
        label = sorted(key[0] for key in items if key[1] == "label")
        self.assertEqual(full, sorted([self.lab.transparent, self.lab.grey, self.lab.patched,
                                       self.lab.unprocessed]))
        self.assertEqual(label, sorted(full + [self.lab.closeup]))
        self.assertEqual(items[(self.lab.closeup, "label")]["steps"], [])

    def test_a_not_applicable_label_is_not_an_item(self):
        self.lab.conn.execute(
            "INSERT INTO image_derivative_absence VALUES (?, 'label', ?, ?)",
            (self.lab.grey, alternatives.SETTINGS_LABEL_ABSENCE,
             "the packet has no separate label"))
        self.lab.conn.commit()
        _, sources = self.inputs()
        embedding = embeddings.Embedding(entry())
        items = embeddings.plan_items(embedding, sources)
        self.assertIn((self.lab.grey, "full"), items)
        self.assertNotIn((self.lab.grey, "label"), items)
        self.assertEqual(embeddings.not_applicable_reason(
            embedding, sources[self.lab.grey], "label"),
            "the packet has no separate label")
        self.assertEqual(embeddings.not_applicable_count(embedding, sources), 1)

    def test_prepare_variant_c(self):
        _, sources = self.inputs()
        items = embeddings.plan_items(embeddings.Embedding(entry()), sources)
        image = embeddings.prepare(items[(self.lab.grey, "full")], sources[self.lab.grey]["path"])
        self.assertEqual(image.mode, "RGB")
        self.assertEqual(image.size, (16, 64))
        self.assertEqual(image.getpixel((8, 32)), (20, 90, 30))

    def test_prepare_variant_a_keeps_the_background(self):
        _, sources = self.inputs()
        embedding = embeddings.Embedding(entry(views=steps(SEG)))
        items = embeddings.plan_items(embedding, sources)
        image = embeddings.prepare(items[(self.lab.grey, "full")], sources[self.lab.grey]["path"])
        self.assertEqual(image.size, (20, 80))

    def test_prepare_fails_without_a_cut(self):
        _, sources = self.inputs()
        items = embeddings.plan_items(embeddings.Embedding(entry()), sources)
        for key, message in (((self.lab.unprocessed, "full"), embeddings.NO_CUT["package"]),
                             ((self.lab.grey, "label"), embeddings.NO_CUT["label"])):
            with self.assertRaises(embeddings.ItemError) as caught:
                embeddings.prepare(items[key], sources[key[0]]["path"])
            self.assertEqual(str(caught.exception), message)

    def test_transparent_model_input_is_an_error(self):
        # Variant A of a round bottle on a transparent canvas: the corners of the box
        # stay transparent.
        image = Image.new("RGBA", (60, 60), (0, 0, 0, 0))
        ImageDraw.Draw(image).ellipse((10, 10, 49, 49), fill=(1, 2, 3, 255))
        path = os.path.join(self.tmp.name, "round.png")
        image.save(path)
        item = {"steps": [dict(SEG)], "cut": {"sha256": "0" * 64, "path": path,
                                              "box": (10, 10, 50, 50)}}
        with self.assertRaises(embeddings.ItemError) as caught:
            embeddings.prepare(item, path)
        self.assertEqual(str(caught.exception), embeddings.TRANSPARENT_ERROR)

    def test_item_status(self):
        items = {("a", "full"): {"embedding_hash": "h1"}, ("b", "full"): {"embedding_hash": "h2"},
                 ("c", "full"): {"embedding_hash": "h3"}, ("d", "full"): {"embedding_hash": "h4"},
                 ("e", "full"): {"embedding_hash": "h5"}}
        index = {"items": [{"source_sha256": "a", "view": "full", "embedding_hash": "h1"},
                           {"source_sha256": "b", "view": "full", "embedding_hash": "old"},
                           {"source_sha256": "e", "view": "full", "embedding_hash": "h5"}],
                 "failures": [{"source_sha256": "c", "view": "full", "embedding_hash": "h3",
                               "error": "x"}]}
        status = embeddings.item_status(items, index, {"a_full.png", "b_full.png"})
        self.assertEqual({key[0]: value[0] for key, value in status.items()},
                         {"a": "current", "b": "stale", "c": "failed", "d": "missing",
                          "e": "stale"})

    def test_checkpoint_keeps_one_vector_file(self):
        directory = os.path.join(self.tmp.name, "entry")
        os.makedirs(directory)
        import numpy as np
        first = embeddings.write_checkpoint(directory, {"items": [{}]}, np.ones((1, 3)))
        second = embeddings.write_checkpoint(directory, {"items": [{}, {}]}, np.ones((2, 3)))
        names = sorted(name for name in os.listdir(directory) if name.startswith("vectors-"))
        self.assertEqual(names, [second["vectors_file"]])
        self.assertNotEqual(first["vectors_file"], second["vectors_file"])
        index = embeddings.read_index(directory)
        self.assertEqual(embeddings.read_vectors(directory, index).shape, (2, 3))


if __name__ == "__main__":
    unittest.main()
