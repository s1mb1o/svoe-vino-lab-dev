"""Tests of the runner of the embedding configurations (plan 33): `pipeline/embedding_run.py`,
and the model inputs of its runs on the Runs page (`run_routes.inputs_view`).

A fake SAM3 finds the bottle and the label of a drawn photo. The catalogue cuts come from
the functions of the catalogue (`derive.derive_image`, `alternatives.label_cut_of`) with
that fake. A fake model gives the mean colour of each model input. No test calls gx10.
"""
import base64
import contextlib
import hashlib
import io
import json
import os
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import yaml
from PIL import Image, ImageDraw

import embedding_lab  # noqa: F401  (puts pipeline/ on sys.path)
from embedding_lab import VIEWS_C_F, FakeGateway, Lab, png
import testset_fixture as FX  # noqa: E402  (puts scripts/ on sys.path)
import alternatives  # noqa: E402
import benchmark  # noqa: E402
import build_embeddings  # noqa: E402
import derive  # noqa: E402
import embedding_run  # noqa: E402
import embeddings  # noqa: E402
import import_testset as IT  # noqa: E402
import labdb  # noqa: E402
import model_cache  # noqa: E402
import run_routes  # noqa: E402

GREY = (128, 128, 128)
# slug -> (the colour of the bottle, the colour of its label). Each channel of a label
# colour is 180 or more; a bottle colour has a channel below 180.
WINES = {"red": ((200, 30, 30), (250, 250, 190)),
         "green": ((30, 200, 30), (190, 250, 250)),
         "blue": ((30, 30, 200), (250, 190, 250))}


def photo(slug, size=(80, 120), at=(30, 20), background=GREY, label=True):
    """RGB: the bottle of `slug`, 20 x 80 pixels at `at`, with a label of 16 x 20 pixels
    in its middle."""
    bottle, colour = WINES[slug]
    image = Image.new("RGB", size, background)
    draw = ImageDraw.Draw(image)
    x, y = at
    draw.rectangle((x, y, x + 19, y + 79), fill=bottle)
    if label:
        draw.rectangle((x + 2, y + 30, x + 17, y + 49), fill=colour)
    return image


def query_photo(slug, label=True):
    """The bottle of `slug` in another place of a larger photo, on another background."""
    return photo(slug, size=(100, 150), at=(40, 30), background=(90, 90, 90), label=label)


def mask_b64(mask):
    buffer = io.BytesIO()
    Image.fromarray((mask * 255).astype(np.uint8), "L").save(buffer, "PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


class FakeSam3:
    """SAM3 of the tests. `segment` finds the pixels that differ from the corner pixel.
    `instances` answers the bottle and, with `labels`, the label: the pixels whose
    channels are all 180 or more. `down` makes each call fail."""

    endpoint = "http://fake-sam3"

    def __init__(self, endpoint=None, down=False, labels=True):
        self.down = down
        self.labels = labels
        self.calls = 0

    def _check(self):
        self.calls += 1
        if self.down:
            raise derive.Sam3Unavailable("the fake SAM3 is down")

    @staticmethod
    def _content(image):
        rgb = np.asarray(image.convert("RGB"))
        return (rgb != rgb[0, 0]).any(axis=2)

    def segment(self, image):
        self._check()
        mask = self._content(image)
        return Image.fromarray((mask * 255).astype(np.uint8), "L") if mask.any() else None

    def instances(self, image, texts, masks=True):
        self._check()
        found = [("bottle", self._content(image))]
        if self.labels:
            found.append(("label", (np.asarray(image.convert("RGB")) >= 180).all(axis=2)))
        out = []
        for noun, mask in found:
            box = derive.bounding_box(mask)
            if box is not None:
                out.append({"label": noun, "box": list(box), "score": 0.9,
                            "area": int(mask.sum()), "mask_png_b64": mask_b64(mask)})
        return out, 1.0


class ColourModel:
    """A model of the tests: the vector of an image is its mean colour. `calls` holds the
    count of the images of each request."""

    def __init__(self, width=3):
        self.width = width
        self.calls = []

    def software(self):
        return {"fake": "mean colour"}

    def embed(self, images):
        self.calls.append(len(images))
        rows = []
        for data in images:
            with Image.open(io.BytesIO(data)) as image:
                mean = np.asarray(image.convert("RGB"), dtype=np.float32).reshape(-1, 3).mean(0)
            rows.append(np.resize(mean, self.width))
        return np.asarray(rows, dtype=np.float32)


def catalogue_lab(root, base_url="http://127.0.0.1:9/v1", label_cuts=tuple(WINES)):
    """A lab with one main image for each wine of `WINES`. Its package cut and its label
    cut (for the wines of `label_cuts`) come from the functions of the catalogue."""
    lab = Lab(root, base_url)
    lab.digests = {}
    sam3 = FakeSam3()
    for slug in WINES:
        lab.wine(slug)
        image = photo(slug)
        _method, _settings, processed, box = derive.derive_image(image, sam3)
        digest = lab.image(slug, "main", image, derivative=processed, box=box)
        if slug in label_cuts:
            instances, _scale = sam3.instances(image, alternatives.DETECT_TEXTS)
            method, cut, box = alternatives.label_cut_of(image, instances)
            derived = lab.store_file(png(cut), labdb.DERIVED_FOLDER, "png")
            lab.conn.execute(
                "INSERT INTO image_derivative (source_sha256, method, settings, sha256, "
                "box_left, box_top, box_right, box_bottom, kind) "
                "VALUES (?, ?, 'test', ?, ?, ?, ?, ?, 'label')",
                (digest, method, derived) + tuple(box))
            lab.conn.commit()
        lab.digests[slug] = digest
    lab.add_entry()
    return lab


def build(lab, model=None, name="gw"):
    """Build the index of the entry `name`. Return the entry."""
    embedding = embeddings.load_settings(lab.config_path).find(name)
    directory = lab.entry_dir(name)
    os.makedirs(directory, exist_ok=True)
    with contextlib.redirect_stdout(io.StringIO()):
        build_embeddings.run(embedding, lab.db_path, directory,
                             make_backend=lambda e: model or ColourModel())
    return embedding


# The set `my`: one photo of each wine, and a photo of `red` with no label.
SET_PHOTOS = {"%s/01.png" % slug: png(query_photo(slug)) for slug in WINES}
SET_PHOTOS["red/02.png"] = png(query_photo("red", label=False))
SET_LABELS = {slug: {"01.png": {"label": "positive"}} for slug in WINES}
SET_LABELS["red"]["02.png"] = {"label": "positive"}


def add_set(lab):
    IT.import_testset(lab.db_path, "my", FX.write_set(lab.root, SET_PHOTOS, SET_LABELS),
                      lambda message: None)


def add_pipelines(lab, *entries):
    """Write the key `pipeline` of the config.yaml of `lab` (plan 34). `Lab.write_config`
    writes the key `embeddings` alone, so call this after it."""
    path = Path(lab.config_path)
    config = yaml.safe_load(path.read_text("utf-8"))
    config["pipeline"] = list(entries)
    path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")


PIPE = {"name": "gw-pipe", "backend": "embedding", "embedding": "gw"}


def vectors_of(catalogue, slug):
    """Return view -> the catalogue vector of the main image of `slug`."""
    number = catalogue.slugs.index(slug)
    out = {}
    for view, (matrix, numbers) in catalogue.views.items():
        rows = np.flatnonzero(numbers == number)
        if rows.size:
            out[view] = matrix[rows[0]]
    return out


class Temporary(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        lab = getattr(self, "lab", None)
        if lab is not None:
            lab.close()
        self.directory.cleanup()


class CatalogueTest(Temporary):
    def setUp(self):
        super().setUp()
        self.lab = catalogue_lab(self.root)
        self.embedding = build(self.lab)

    def test_the_catalogue_holds_the_current_vector_of_each_wine_and_view(self):
        catalogue = embedding_run.Catalogue(self.embedding, self.lab.db_path)
        self.assertEqual(sorted(catalogue.slugs), sorted(WINES))
        self.assertEqual({view: len(numbers) for view, (_, numbers) in catalogue.views.items()},
                         {"full": 3, "label": 3})
        state = catalogue.state
        self.assertEqual(state["items"], {"current": 6, "stale": 0, "missing": 0, "failed": 0})
        self.assertEqual((state["dim"], state["wines"]), (3, {"full": 3, "label": 3}))
        self.assertRegex(state["index_file"], r"^gw/vectors-[0-9a-f]{8}\.npy$")
        self.assertTrue(state["built_at"])

    def test_the_score_is_the_mean_of_the_best_cosine_of_each_view(self):
        catalogue = embedding_run.Catalogue(self.embedding, self.lab.db_path)
        cands = catalogue.rank(vectors_of(catalogue, "green"), 10)
        self.assertEqual([c["rank"] for c in cands], [1, 2, 3])
        self.assertEqual((cands[0]["slug"], cands[0]["score"]), ("green", 1.0))
        for cand in cands:
            self.assertEqual(set(cand), {"slug", "score", "rank", "full", "label", "items"})
            self.assertAlmostEqual(cand["score"], (cand["full"] + cand["label"]) / 2, places=3)
        self.assertEqual(len(catalogue.rank(vectors_of(catalogue, "green"), 2)), 2)

    def test_a_query_with_one_view_is_scored_by_that_view(self):
        catalogue = embedding_run.Catalogue(self.embedding, self.lab.db_path)
        cands = catalogue.rank({"full": vectors_of(catalogue, "blue")["full"]}, 10)
        self.assertEqual(cands[0]["slug"], "blue")
        self.assertEqual(set(cands[0]), {"slug", "score", "rank", "full", "items"})
        self.assertTrue(all(c["score"] == c["full"] for c in cands))

    def test_a_pipeline_gives_its_name_to_the_backend_of_its_embedding(self):
        pipeline = types.SimpleNamespace(name="pipe", embedding="gw")
        backend = embedding_run.build_pipeline_backend(pipeline, self.lab.config_path)
        self.assertEqual((backend.id, backend.spec["id"], backend.spec["embedding"]),
                         ("pipe", "pipe", "gw"))
        self.assertEqual(backend.catalogue.state["items"]["current"], 6)
        unknown = types.SimpleNamespace(name="pipe", embedding="nope")
        with self.assertRaises(embeddings.ConfigError) as caught:
            embedding_run.build_pipeline_backend(unknown, self.lab.config_path)
        self.assertIn("names the embedding nope", str(caught.exception))

    def test_an_entry_with_no_index_cannot_run(self):
        self.lab.add_entry("other")
        other = embeddings.load_settings(self.lab.config_path).find("other")
        self.assertTrue(embedding_run.index_ready(self.lab.db_path, "gw"))
        self.assertFalse(embedding_run.index_ready(self.lab.db_path, "other"))
        with self.assertRaises(embeddings.ConfigError) as caught:
            embedding_run.Catalogue(other, self.lab.db_path)
        self.assertIn(embedding_run.NO_INDEX, str(caught.exception))

    def test_an_entry_whose_steps_changed_has_no_current_vector(self):
        self.lab.add_entry(views={"full": {"steps": [
            {"step": "segment", "target": "package"}, {"step": "white_background"}]}})
        changed = embeddings.load_settings(self.lab.config_path).find("gw")
        with self.assertRaises(embeddings.ConfigError) as caught:
            embedding_run.Catalogue(changed, self.lab.db_path)
        self.assertIn("no current vector", str(caught.exception))

    def test_a_test_photo_gets_the_pixels_of_the_catalogue_image(self):
        inputs, missing = embedding_run.query_inputs(photo("red"), self.embedding.views,
                                                     FakeSam3())
        self.assertEqual((sorted(inputs), missing), (["full", "label"], {}))
        for view, image in inputs.items():
            name = embeddings.image_name(self.lab.digests["red"], view)
            with Image.open(os.path.join(self.lab.entry_dir(), embeddings.IMAGES, name)) as built:
                self.assertTrue(np.array_equal(np.asarray(image), np.asarray(built.convert("RGB"))),
                                view)


class WineWithNoLabelVectorTest(Temporary):
    def test_a_wine_with_no_label_vector_competes_with_its_full_cosine(self):
        self.lab = catalogue_lab(self.root, label_cuts=("red", "green"))
        embedding = build(self.lab)
        catalogue = embedding_run.Catalogue(embedding, self.lab.db_path)
        self.assertEqual(catalogue.state["wines"], {"full": 3, "label": 2})
        self.assertEqual(catalogue.state["items"]["failed"], 1)
        query = {"full": vectors_of(catalogue, "blue")["full"],
                 "label": vectors_of(catalogue, "red")["label"]}
        cands = {c["slug"]: c for c in catalogue.rank(query, 10)}
        self.assertEqual((cands["blue"]["label"], cands["blue"]["score"]),
                         (None, cands["blue"]["full"]))
        self.assertEqual(cands["blue"]["rank"], 1)


class RunTest(Temporary):
    def setUp(self):
        super().setUp()
        self.lab = catalogue_lab(self.root)
        self.embedding = build(self.lab)
        add_set(self.lab)
        self.runs = str(self.root / "runs")

    def run_set(self, sam3=None, model=None):
        self.model = model or ColourModel()
        self.sam3 = sam3 or FakeSam3()
        backend = embedding_run.build_backend(self.embedding, self.lab.db_path,
                                              make_model=lambda e: self.model,
                                              segmenter=self.sam3)
        run_dir, met = benchmark.run_benchmark(
            self.lab.db_path, "my", backend, self.runs, embeddings=backend.catalogue.state,
            log=lambda message: None, configuration="gw")
        with open(os.path.join(run_dir, "results.jsonl"), encoding="utf-8") as fh:
            rows = {json.loads(line)["image_path"]: json.loads(line) for line in fh}
        return run_dir, met, rows

    def test_each_photo_ranks_its_wine_first(self):
        run_dir, met, rows = self.run_set()
        self.assertEqual((met["positive"]["n"], met["positive"]["recall_at_1"]), (4, 1.0))
        for path, row in rows.items():
            self.assertEqual((row["candidates"][0]["slug"], row["error"], row["http_status"]),
                             (row["slug"], None, 200), path)
        meta = json.loads(Path(run_dir, "run.json").read_text("utf-8"))
        self.assertEqual((meta["configuration"], meta["backend"]["kind"]), ("gw", "embedding"))
        self.assertEqual(meta["backend"]["views"], json.loads(json.dumps(self.embedding.views)))
        self.assertEqual(meta["backend"]["sam3"]["endpoint"], FakeSam3.endpoint)
        self.assertEqual(meta["embeddings"]["items"]["current"], 6)
        self.assertIn("-lab-gw-my", os.path.basename(run_dir))

    def test_a_photo_with_no_label_is_scored_by_the_full_view(self):
        _, _, rows = self.run_set()
        first = rows["red/02.png"]["candidates"][0]
        self.assertEqual((first["slug"], "label" in first), ("red", False))
        self.assertEqual(sorted(self.model.calls), [1, 2, 2, 2])

    def test_sam3_that_does_not_answer_gets_no_more_requests(self):
        _, met, rows = self.run_set(sam3=FakeSam3(down=True))
        self.assertEqual(self.sam3.calls, 1)
        errors = sorted(row["error"] for row in rows.values())
        self.assertIn("the fake SAM3 is down", errors[-1])
        self.assertTrue(all(e.startswith("no request: SAM3 did not answer") for e in errors[:-1]))
        self.assertEqual(met["positive"]["recall_at_1"], 0.0)
        self.assertEqual(self.model.calls, [])

    def test_a_vector_of_another_width_is_an_error(self):
        _, _, rows = self.run_set(model=ColourModel(width=4))
        for row in rows.values():
            self.assertEqual(row["candidates"], [])
            self.assertIn("the model sent a vector of 4 values; the index holds 3", row["error"])

    # ---- the step trace of plan 41 ----

    def test_each_row_holds_the_step_trace(self):
        _, _, rows = self.run_set()
        row = rows["green/01.png"]
        trace = row["trace"]
        self.assertEqual(trace["v"], embedding_run.TRACE_VERSION)
        steps = trace["steps"]
        self.assertEqual([(s["id"], s.get("view")) for s in steps], [
            ("input", None), ("sam3-package", None), ("sam3-label", None), ("view", "full"),
            ("view", "label"), ("embed", None), ("search", "full"), ("search", "label"),
            ("score", None)])
        starts = [s["start_ms"] for s in steps]
        self.assertEqual(starts, sorted(starts))
        self.assertTrue(all(s["ms"] >= 0 and "error" not in s for s in steps))
        # The fake SAM3 does not tell about the cache.
        self.assertEqual([s["cached"] for s in steps if s["id"].startswith("sam3")], [None, None])
        self.assertEqual(steps[1]["out"]["rule"], "sam3")
        self.assertTrue(steps[2]["out"]["found"])
        # The sha256 of a view is the sha256 of the PNG that went to the model.
        expected, _ = embedding_run.query_inputs(query_photo("green"), self.embedding.views,
                                                 FakeSam3())
        for part in steps[3:5]:
            data = embeddings.png_bytes(expected[part["view"]])
            self.assertEqual(part["out"]["sha256"], hashlib.sha256(data).hexdigest())
            self.assertEqual(part["out"]["bytes"], len(data))
        self.assertEqual(steps[5]["out"], {"views": ["full", "label"], "dim": 3})
        # The top list of a space follows the cosine of that space alone.
        cands = {c["slug"]: c for c in row["candidates"]}
        for part in steps[6:8]:
            top = part["out"]["top"]
            self.assertEqual([hit["cosine"] for hit in top],
                             sorted((hit["cosine"] for hit in top), reverse=True))
            self.assertEqual(top[0]["slug"], "green")
            self.assertEqual((part["out"]["rows"], part["out"]["wines"]), (3, 3))
            for hit in top:
                self.assertEqual(hit["cosine"], cands[hit["slug"]][part["view"]])
                self.assertEqual(hit["sha256"], self.lab.digests[hit["slug"]])
                self.assertEqual(set(hit), {"slug", "cosine", "sha256", "type",
                                            "embedding_hash"})
        self.assertEqual(steps[8]["out"], {"wines": 3})

    def test_a_view_with_no_input_is_a_skipped_step(self):
        _, _, rows = self.run_set()
        steps = rows["red/02.png"]["trace"]["steps"]
        self.assertEqual(next(s for s in steps if s["id"] == "sam3-label")["out"],
                         {"found": False})
        label = next(s for s in steps if s.get("view") == "label" and s["id"] == "view")
        self.assertEqual((label["skipped"], "out" in label), ("SAM3 found no label", False))
        self.assertEqual([s.get("view") for s in steps if s["id"] == "search"], ["full"])

    def test_a_failed_step_ends_the_trace(self):
        _, _, rows = self.run_set(sam3=FakeSam3(down=True))
        steps = rows["green/01.png"]["trace"]["steps"]
        self.assertEqual([s["id"] for s in steps], ["input", "sam3-package"])
        self.assertIn("SAM3", steps[1]["error"])

    def test_a_sam3_client_that_tells_the_cache_marks_its_steps(self):
        class Cached(FakeSam3):
            def cached(self):
                return True

        _, _, rows = self.run_set(sam3=Cached())
        steps = rows["green/01.png"]["trace"]["steps"]
        self.assertEqual([s["cached"] for s in steps if s["id"].startswith("sam3")],
                         [True, True])

    def test_the_rows_of_the_run_route_hold_no_trace(self):
        run_dir, _, _ = self.run_set()
        code, body, _, _ = run_routes.run_view(self.runs, self.lab.db_path,
                                               {"id": [os.path.basename(run_dir)]},
                                               lambda conn: {})
        self.assertEqual(code, 200)
        self.assertTrue(body["rows"])
        self.assertTrue(all("trace" not in row for row in body["rows"]))

    def test_the_route_answers_the_model_inputs_of_a_query(self):
        run_dir, _, rows = self.run_set()
        run_id, query = os.path.basename(run_dir), rows["green/01.png"]["query_id"]
        with mock.patch.object(embedding_run, "CachedSam3", FakeSam3):
            code, body, _, _ = run_routes.inputs_view(self.runs, self.lab.db_path,
                                                      {"id": [run_id], "query": [query]})
        self.assertEqual(code, 200, body)
        self.assertEqual([item["pipelines"] for item in body["inputs"]], [["full"], ["label"]])
        expected, _ = embedding_run.query_inputs(query_photo("green"), self.embedding.views,
                                                 FakeSam3())
        for item in body["inputs"]:
            self.assertEqual((item["uses"], item["model"], item["mime"]),
                             (["Embedding"], "fake-model", "image/png"))
            data = base64.b64decode(item["src"].split(",", 1)[1])
            with Image.open(io.BytesIO(data)) as image:
                self.assertTrue(np.array_equal(np.asarray(image.convert("RGB")),
                                               np.asarray(expected[item["label"]])))
        self.assertEqual(body["notes"], [])

    def test_a_photo_with_no_cached_sam3_answer_gets_a_note(self):
        run_dir, _, rows = self.run_set()
        meta_path = Path(run_dir, "run.json")
        meta = json.loads(meta_path.read_text("utf-8"))
        meta["backend"]["url"] = None  # a run of the backend local has no URL
        meta_path.write_text(json.dumps(meta), encoding="utf-8")
        with mock.patch.object(model_cache, "ROOT", str(self.root / "empty-cache")):
            code, body, _, _ = run_routes.inputs_view(
                self.runs, self.lab.db_path,
                {"id": [os.path.basename(run_dir)], "query": [rows["red/01.png"]["query_id"]]})
        self.assertEqual((code, body["inputs"]), (200, []))
        self.assertIn("not in data/cache/models/sam3/", body["notes"][0])
        self.assertFalse((self.root / "empty-cache").exists())


# The steps of the test photo of a pipeline (owner answers of 2026-09-26T00:52:41+0300),
# with each default filled in, as `pipelines.Pipeline.views` holds them.
RESIZE_64 = {"step": "resize", "max_size": 64, "aspect": "keep", "upscale": False}
AS_IS = {"full": [RESIZE_64]}
CROP = {"full": [{"step": "segment", "target": "package"}, RESIZE_64]}


class PipelineViewsTest(Temporary):
    def setUp(self):
        super().setUp()
        self.lab = catalogue_lab(self.root)
        self.embedding = build(self.lab)
        add_set(self.lab)
        self.runs = str(self.root / "runs")

    def test_a_view_with_no_segment_takes_the_photo_as_it_is(self):
        image = query_photo("red")
        # A SAM3 that fails on each call: the view sends no request.
        inputs, missing = embedding_run.query_inputs(image, AS_IS, FakeSam3(down=True))
        self.assertEqual(missing, {})
        expected = embeddings.resize(image, RESIZE_64).convert("RGB")
        self.assertTrue(np.array_equal(np.asarray(inputs["full"]), np.asarray(expected)))

    def test_a_crop_view_keeps_the_background_inside_the_box(self):
        image = query_photo("red")
        sam3 = FakeSam3()
        inputs, _ = embedding_run.query_inputs(image, CROP, sam3)
        _method, _settings, _processed, box = derive.derive_image(image, FakeSam3())
        expected = embeddings.resize(image.crop(box), RESIZE_64).convert("RGB")
        self.assertTrue(np.array_equal(np.asarray(inputs["full"]), np.asarray(expected)))
        self.assertEqual(sam3.calls, 1)  # the package cut alone; no label request
        self.assertNotEqual(inputs["full"].getpixel((0, 0)), (255, 255, 255))

    def run_as_is(self):
        self.model = ColourModel()
        backend = embedding_run.build_backend(
            self.embedding, self.lab.db_path, make_model=lambda e: self.model,
            segmenter=FakeSam3(down=True), name="as-is", views=AS_IS)
        run_dir, _ = benchmark.run_benchmark(
            self.lab.db_path, "my", backend, self.runs, embeddings=backend.catalogue.state,
            log=lambda message: None, configuration="as-is")
        with open(os.path.join(run_dir, "results.jsonl"), encoding="utf-8") as fh:
            return run_dir, [json.loads(line) for line in fh]

    def test_a_pipeline_with_views_runs_its_steps_and_records_them(self):
        run_dir, rows = self.run_as_is()
        self.assertTrue(all(row["error"] is None for row in rows), rows)
        self.assertTrue(all(set(row["candidates"][0]) == {"slug", "score", "rank", "full", "items"}
                            for row in rows))
        self.assertEqual(self.model.calls, [1, 1, 1, 1])
        meta = json.loads(Path(run_dir, "run.json").read_text("utf-8"))
        self.assertEqual((meta["configuration"], meta["backend"]["views"]), ("as-is", AS_IS))
        self.assertIn("-lab-as-is-my", os.path.basename(run_dir))

    def test_the_route_makes_the_as_is_input_again_with_no_sam3_answer(self):
        run_dir, rows = self.run_as_is()
        row = next(r for r in rows if r["image_path"] == "red/01.png")
        with mock.patch.object(model_cache, "ROOT", str(self.root / "empty-cache")):
            code, body, _, _ = run_routes.inputs_view(
                self.runs, self.lab.db_path,
                {"id": [os.path.basename(run_dir)], "query": [row["query_id"]]})
        self.assertEqual((code, [item["label"] for item in body["inputs"]]), (200, ["full"]))
        data = base64.b64decode(body["inputs"][0]["src"].split(",", 1)[1])
        expected = embeddings.resize(query_photo("red"), RESIZE_64).convert("RGB")
        with Image.open(io.BytesIO(data)) as image:
            self.assertTrue(np.array_equal(np.asarray(image.convert("RGB")),
                                           np.asarray(expected)))

    def test_a_pipeline_gives_its_views_to_the_backend(self):
        crop = types.SimpleNamespace(name="crop", embedding="gw", views=CROP)
        backend = embedding_run.build_pipeline_backend(crop, self.lab.config_path)
        self.assertEqual((backend.views, backend.spec["views"]), (CROP, CROP))
        self.assertTrue(backend.scene_selection)
        self.assertEqual(backend.spec["scene_selection"], 1)
        self.assertIn("hand", backend.spec["sam3"]["package_texts"])
        plain = types.SimpleNamespace(name="pipe", embedding="gw")
        self.assertEqual(embedding_run.build_pipeline_backend(plain, self.lab.config_path).views,
                         self.embedding.views)


class CommandTest(Temporary):
    def setUp(self):
        super().setUp()
        self.gateway = FakeGateway()
        self.lab = catalogue_lab(self.root, base_url=self.gateway.base_url)
        # The index comes from the fake gateway, through `build_embeddings.OpenAIBackend`.
        os.makedirs(self.lab.entry_dir(), exist_ok=True)
        with contextlib.redirect_stdout(io.StringIO()):
            build_embeddings.run(embeddings.load_settings(self.lab.config_path).find("gw"),
                                 self.lab.db_path, self.lab.entry_dir())
        add_set(self.lab)
        add_pipelines(self.lab, PIPE)
        self.runs = str(self.root / "runs")

    def tearDown(self):
        self.gateway.close()
        super().tearDown()

    def main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(derive, "Sam3Client", FakeSam3), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = embedding_run.main(["--config", self.lab.config_path, "--runs-dir",
                                       self.runs, *args])
        return code, out.getvalue(), err.getvalue()

    def test_a_run_of_a_pipeline_goes_through_the_endpoint_of_its_embedding(self):
        built = len(self.gateway.requests)
        code, out, err = self.main("--name", "gw-pipe", "--set", "my", "--label", "probe")
        self.assertEqual(code, 0, err)
        self.assertIn("recall@1 1.0", out)
        run_dir = out.strip().splitlines()[-1].split("run: ", 1)[1]
        self.assertTrue(run_dir.endswith("-lab-gw-pipe-my-probe"))
        meta = json.loads(Path(run_dir, "run.json").read_text("utf-8"))
        self.assertEqual((meta["configuration"], meta["backend"]["id"],
                          meta["backend"]["embedding"]), ("gw-pipe", "gw-pipe", "gw"))
        self.assertEqual(meta["backend"]["url"], self.gateway.base_url + "/embeddings")
        sent = self.gateway.requests[built:]
        self.assertEqual(sorted(len(body["input"]) for body in sent), [1, 2, 2, 2])
        self.assertTrue(all((body["model"], body["max_num_patches"]) == ("fake-model", 256)
                            for body in sent))

    def test_a_name_that_is_no_pipeline_is_refused(self):
        code, _, err = self.main("--name", "gw", "--set", "my")  # an embedding entry
        self.assertEqual(code, 1)
        self.assertIn("error: config.yaml has no pipeline gw", err)
        self.assertFalse(os.path.exists(self.runs))

    def test_a_pipeline_of_another_backend_is_refused(self):
        add_pipelines(self.lab, PIPE, {"name": "r", "backend": "svoe-vino-ru",
                                       "url": "http://127.0.0.1:9/v1/wines/search-by-photo"})
        code, _, err = self.main("--name", "r", "--set", "my")
        self.assertEqual(code, 1)
        self.assertIn("the pipeline r has the backend svoe-vino-ru; this script runs the "
                      "backend embedding alone", err)

    def test_a_pipeline_of_an_invalid_embedding_is_refused(self):
        self.lab.entries.append({"name": "broken", "backend": "nothing", "views": VIEWS_C_F})
        self.lab.write_config()
        add_pipelines(self.lab, {"name": "b", "backend": "embedding", "embedding": "broken"})
        code, _, err = self.main("--name", "b", "--set", "my")
        self.assertEqual(code, 1)
        self.assertIn("error:", err)
        self.assertIn("broken", err)
        self.assertFalse(os.path.exists(self.runs))

    def test_an_unknown_set_is_an_error(self):
        code, _, err = self.main("--name", "gw-pipe", "--set", "nope")
        self.assertEqual(code, 1)
        self.assertIn("no test set", err)
        self.assertFalse(os.path.exists(self.runs))


ITEM_KEYS = {"sha256", "view", "type", "embedding_hash", "cosine"}


class CandidateItemsTest(Temporary):
    """Plan 38: each candidate records the cosine of each item of its wine, and the route
    `/api/run-candidate` answers them with the prepared image of each item."""

    def setUp(self):
        super().setUp()
        self.lab = catalogue_lab(self.root)
        # A second photo of `red` with no label, so with a package cut and no label cut:
        # the index holds its item `full` alone, and its mean colour differs from the
        # main photo. The main photo of `red` is also a photo of `green`.
        second = photo("red", size=(90, 130), at=(35, 25), label=False)
        _method, _settings, processed, box = derive.derive_image(second, FakeSam3())
        self.second = self.lab.image("red", "full_front", second, derivative=processed,
                                     box=box)
        self.lab.link("green", "full_front", self.lab.digests["red"])
        self.embedding = build(self.lab)
        self.index = {(r["source_sha256"], r["view"]): r for r in embeddings.read_index(
            self.lab.entry_dir())["items"]}
        add_set(self.lab)
        self.runs = str(self.root / "runs")

    def test_each_candidate_records_the_cosine_of_each_item_of_its_wine(self):
        catalogue = embedding_run.Catalogue(self.embedding, self.lab.db_path)
        cands = {c["slug"]: c for c in catalogue.rank(vectors_of(catalogue, "red"), 10)}
        red = cands["red"]
        self.assertEqual([(i["sha256"], i["view"], i["type"]) for i in red["items"]],
                         [(self.lab.digests["red"], "full", "main"),
                          (self.second, "full", "full_front"),
                          (self.lab.digests["red"], "label", "main")])
        self.assertEqual(red["items"][0]["cosine"], 1.0)
        for cand in cands.values():
            for item in cand["items"]:
                self.assertEqual(set(item), ITEM_KEYS)
                self.assertEqual(item["embedding_hash"],
                                 self.index[(item["sha256"], item["view"])]["embedding_hash"])
            for view in ("full", "label"):
                cosines = [i["cosine"] for i in cand["items"] if i["view"] == view]
                self.assertEqual(cosines, sorted(cosines, reverse=True))
                self.assertEqual(cand[view], cosines[0])
        # One file of two wines: the type is the type of the column of each wine.
        shared = [(i["view"], i["type"]) for i in cands["green"]["items"]
                  if i["sha256"] == self.lab.digests["red"]]
        self.assertEqual(sorted(shared), [("full", "full_front"), ("label", "full_front")])

    def test_a_view_that_the_query_does_not_have_gets_no_cosine(self):
        catalogue = embedding_run.Catalogue(self.embedding, self.lab.db_path)
        cands = catalogue.rank({"full": vectors_of(catalogue, "red")["full"]}, 10)
        for cand in cands:
            self.assertTrue(all((i["cosine"] is None) == (i["view"] == "label")
                                for i in cand["items"]), cand)

    def run_set(self, views=None):
        backend = embedding_run.build_backend(
            self.embedding, self.lab.db_path, make_model=lambda e: ColourModel(),
            segmenter=FakeSam3(), name="as-is" if views else None, views=views)
        run_dir, _ = benchmark.run_benchmark(
            self.lab.db_path, "my", backend, self.runs, embeddings=backend.catalogue.state,
            log=lambda message: None, configuration="gw")
        with open(os.path.join(run_dir, "results.jsonl"), encoding="utf-8") as fh:
            rows = {json.loads(line)["image_path"]: json.loads(line) for line in fh}
        return os.path.basename(run_dir), rows

    def ask(self, run_id, row, slug):
        return run_routes.candidate_view(self.runs, self.lab.db_path, {
            "id": [run_id], "query": [row["query_id"]], "slug": [slug]})

    def test_the_route_answers_the_items_of_a_candidate_with_their_images(self):
        run_id, rows = self.run_set()
        row = rows["red/01.png"]
        cand = next(c for c in row["candidates"] if c["slug"] == "red")
        code, body, _, _ = self.ask(run_id, row, "red")
        self.assertEqual(code, 200, body)
        self.assertEqual((body["slug"], body["score"], body["views"], body["notes"]),
                         ("red", cand["score"], {"full": cand["full"], "label": cand["label"]},
                          []))
        self.assertEqual([{k: i[k] for k in ITEM_KEYS} for i in body["items"]], cand["items"])
        for item in body["items"]:
            record = self.index[(item["sha256"], item["view"])]
            self.assertEqual(item["state"], "same")
            self.assertEqual(item["url"], "/embeddings/gw/images/%s_%s.png?v=%s" % (
                item["sha256"], item["view"], record["embedding_hash"][:16]))
            self.assertEqual((item["width"], item["height"]), (record["width"], record["height"]))
        self.assertEqual([i["best"] for i in body["items"]], [True, False, True])

    def test_an_item_whose_input_changed_after_the_run_gets_no_image(self):
        run_id, rows = self.run_set()
        path = os.path.join(self.lab.entry_dir(), embeddings.INDEX)
        index = json.loads(Path(path).read_text("utf-8"))
        for record in index["items"]:
            if record["source_sha256"] == self.second:
                record["embedding_hash"] = "0" * 64
        index["items"] = [r for r in index["items"]
                          if (r["source_sha256"], r["view"]) != (self.lab.digests["red"], "label")]
        Path(path).write_text(json.dumps(index), encoding="utf-8")
        code, body, _, _ = self.ask(run_id, rows["red/01.png"], "red")
        self.assertEqual(code, 200, body)
        self.assertEqual([(i["state"], i["url"] is None, i["cosine"] is None)
                          for i in body["items"]],
                         [("same", False, False), ("changed", True, False),
                          ("gone", True, False)])
        self.assertIn("changed after the run", body["notes"][0])

    def test_a_run_from_before_plan_38_shows_the_items_of_the_present_index(self):
        run_id, rows = self.run_set()
        path = os.path.join(self.runs, run_id, "results.jsonl")
        records = [json.loads(line) for line in Path(path).read_text("utf-8").splitlines()]
        for record in records:
            for cand in record["candidates"]:
                del cand["items"]
        Path(path).write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
        code, body, _, _ = self.ask(run_id, rows["red/01.png"], "red")
        self.assertEqual(code, 200, body)
        self.assertEqual([(i["sha256"], i["view"], i["type"], i["cosine"], i["state"], i["best"])
                          for i in body["items"]],
                         [(self.lab.digests["red"], "full", "main", None, "current", False),
                          (self.second, "full", "full_front", None, "current", False),
                          (self.lab.digests["red"], "label", "main", None, "current", False)])
        self.assertTrue(all(i["url"] for i in body["items"]))
        self.assertEqual(body["notes"], [embedding_run.OLD_RUN_NOTE])

    def test_an_as_is_run_marks_the_items_that_it_did_not_compare(self):
        run_id, rows = self.run_set(views=AS_IS)
        code, body, _, _ = self.ask(run_id, rows["red/01.png"], "red")
        self.assertEqual(code, 200, body)
        self.assertEqual(list(body["views"]), ["full"])
        self.assertEqual([(i["view"], i["cosine"] is None, i["best"]) for i in body["items"]],
                         [("full", False, True), ("full", False, False),
                          ("label", True, False)])
        self.assertEqual(body["notes"], ["The query has no view label, so the run did not "
                                         "compare these items."])

    def test_the_route_refuses_a_slug_that_is_no_candidate(self):
        run_id, rows = self.run_set()
        code, body, _, _ = self.ask(run_id, rows["red/01.png"], "nope")
        self.assertEqual((code, body["error"]), (404, "the slug is not a candidate of this query"))
        code, body, _, _ = run_routes.candidate_view(self.runs, self.lab.db_path, {
            "id": ["nope"], "query": ["q-000001"], "slug": ["red"]})
        self.assertEqual(code, 404)

    def test_a_run_of_another_backend_gets_a_note(self):
        run_id, rows = self.run_set()
        meta_path = Path(self.runs, run_id, "run.json")
        meta = json.loads(meta_path.read_text("utf-8"))
        meta["backend"]["kind"] = "remote"
        meta_path.write_text(json.dumps(meta), encoding="utf-8")
        code, body, _, _ = self.ask(run_id, rows["red/01.png"], "red")
        self.assertEqual((code, body["items"]), (200, []))
        self.assertIn("not a run of an embedding pipeline", body["notes"][0])

    def test_the_rows_of_a_run_hold_no_items(self):
        run_id, rows = self.run_set()
        self.assertTrue(all("items" in c for r in rows.values() for c in r["candidates"]))
        code, body, _, _ = run_routes.run_view(self.runs, self.lab.db_path, {"id": [run_id]},
                                               lambda conn: {})
        self.assertEqual((code, len(body["rows"])), (200, len(rows)))
        self.assertFalse(any("items" in c for r in body["rows"] for c in r["candidates"]))


if __name__ == "__main__":
    unittest.main()
