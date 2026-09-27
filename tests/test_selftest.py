"""Tests of the self-test of one embedding (plan 67): `pipeline/selftest.py` and the
keyword `queries` of `benchmark.run_benchmark`.

The lab is `catalogue_lab` of `test_embedding_run.py`: the wines red, green, and blue with
one main image each. The tests add a `main_patched`, a label close-up, a file of two
wines, and a Removed wine. A fake SAM3 and a fake model answer; no test calls gx10.
"""
import contextlib
import hashlib
import io
import json
import os
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

import embedding_lab  # noqa: F401  (puts pipeline/ on sys.path)
from embedding_lab import FakeGateway, png
import test_embedding_run as TER  # noqa: E402
import benchmark  # noqa: E402
import build_embeddings  # noqa: E402
import derive  # noqa: E402
import embeddings  # noqa: E402
import selftest  # noqa: E402

CLOSEUP = Image.new("RGB", (40, 30), (190, 250, 250))


def dataset_lab(root, base_url="http://127.0.0.1:9/v1"):
    """`catalogue_lab` and: a `main_patched` of red (the red bottle in another place), a
    `label_back` close-up of green, the main image of blue also in the wine `blue-twin`,
    and the Removed wine `gone`."""
    lab = TER.catalogue_lab(root, base_url)
    patched = TER.photo("red", at=(40, 30), size=(100, 150))
    _method, _settings, processed, box = derive.derive_image(patched, TER.FakeSam3())
    lab.patched = lab.image("red", "main_patched", patched, folder="patched",
                            derivative=processed, box=box)
    lab.closeup = lab.image("green", "label_back", CLOSEUP, folder="additional")
    lab.wine("blue-twin")
    lab.link("blue-twin", "main", lab.digests["blue"])
    lab.wine("gone", state="Removed")
    lab.image("gone", "main", TER.photo("green", at=(10, 10)))
    return lab


class Temporary(TER.Temporary):
    def setUp(self):
        super().setUp()
        self.lab = dataset_lab(self.root)
        self.queries = selftest.read_queries(self.lab.db_path)

    def rows_of(self, slug):
        return [row for row in self.queries[0] if row["slug"] == slug]


class QueriesTest(Temporary):
    def test_each_image_of_an_active_wine_is_one_query_with_its_wine_as_the_truth(self):
        rows, skipped = self.queries
        self.assertEqual(sorted((row["slug"], row["image_type"]) for row in rows), [
            ("blue", "main"), ("blue-twin", "main"), ("green", "label_back"),
            ("green", "main"), ("red", "main"), ("red", "main_patched")])
        self.assertEqual(dict(skipped), {"removed wine": 1})
        for row in rows:
            self.assertEqual((row["label"], row["truth"]), ("positive", [row["slug"]]))
            self.assertTrue(os.path.isfile(row["abs_path"]), row)
            self.assertEqual(row["image_path"], "%s/%s-%s.png" % (
                row["slug"], row["image_type"], row["image_sha256"][:12]))
        self.assertEqual([row["query_id"] for row in rows],
                         ["q-%06d" % n for n in range(1, len(rows) + 1)])
        self.assertEqual(rows, sorted(rows, key=lambda row: row["image_path"]))

    def test_the_main_of_a_patched_wine_stays_and_a_shared_file_is_one_query_per_wine(self):
        self.assertEqual({row["image_type"] for row in self.rows_of("red")},
                         {"main", "main_patched"})
        blue, twin = self.rows_of("blue")[0], self.rows_of("blue-twin")[0]
        self.assertEqual(blue["image_sha256"], twin["image_sha256"])
        self.assertEqual((blue["truth"], twin["truth"]), (["blue"], ["blue-twin"]))


class BackendTest(Temporary):
    def setUp(self):
        super().setUp()
        TER.build(self.lab)
        self.sam3 = TER.FakeSam3()
        self.backend = selftest.build_backend(
            "gw", self.lab.config_path, self.queries[0],
            make_model=lambda entry: TER.ColourModel(), segmenter=self.sam3)

    def test_a_full_image_takes_the_package_cut_and_the_steps_of_the_view_full(self):
        row = next(row for row in self.rows_of("green") if row["image_type"] == "main")
        cands, _ms, status, error, trace = self.backend.ask(row["abs_path"])
        self.assertEqual((status, error), (200, None))
        ids = [step["id"] for step in trace["steps"]]
        self.assertIn("sam3-package", ids)
        self.assertNotIn("sam3-label", ids)
        self.assertEqual([step.get("view") for step in trace["steps"] if step["id"] == "view"],
                         ["full"])
        self.assertEqual(cands[0]["slug"], "green")
        # The view `label` of the index is not searched.
        self.assertTrue(all("full" in cand and "label" not in cand for cand in cands))

    def test_a_close_up_goes_in_as_it_is_with_no_sam3_request(self):
        path = next(row["abs_path"] for row in self.rows_of("green")
                    if row["image_type"] == "label_back")
        calls = self.sam3.calls
        cands, _ms, status, error, trace = self.backend.ask(path)
        self.assertEqual((status, error), (200, None))
        self.assertEqual(self.sam3.calls, calls)
        self.assertEqual([step["id"] for step in trace["steps"]],
                         ["input", "view", "embed", "search", "score"])
        view = trace["steps"][1]
        self.assertEqual(view["view"], "full")
        self.assertEqual(view["out"]["sha256"], hashlib.sha256(
            embeddings.png_bytes(CLOSEUP.convert("RGB"))).hexdigest())
        self.assertEqual(trace["steps"][3]["view"], "full")
        self.assertTrue(cands)

    def test_a_file_that_is_a_full_image_of_one_wine_and_a_close_up_of_another_is_full(self):
        self.lab.link("blue", "label_front", self.lab.digests["red"])
        rows, _ = selftest.read_queries(self.lab.db_path)
        backend = selftest.build_backend("gw", self.lab.config_path, rows,
                                         make_model=lambda entry: TER.ColourModel(),
                                         segmenter=self.sam3)
        path = next(row["abs_path"] for row in rows if row["image_type"] == "label_front")
        self.assertEqual(backend.roles[path], "full")

    def test_the_spec_names_the_self_test_and_its_steps(self):
        spec = self.backend.spec
        entry = embeddings.load_settings(self.lab.config_path).find("gw")
        self.assertEqual((spec["id"], spec["kind"], spec["embedding"], spec["workers"]),
                         ("selftest-gw", "embedding", "gw", selftest.DEFAULT_WORKERS))
        self.assertEqual(spec["views"], {"full": entry.views["full"]})
        self.assertEqual(spec["selftest"], {"set": "dataset", "view": "full", "steps": {
            "full": entry.views["full"], "label": []}})

    def test_the_run_files_have_the_set_dataset_the_configuration_and_no_barcode(self):
        runs = str(self.root / "runs")
        with contextlib.redirect_stdout(io.StringIO()):
            run_dir, met = benchmark.run_benchmark(
                self.lab.db_path, selftest.SET_NAME, self.backend, runs,
                embeddings=self.backend.catalogue.state, log=lambda message: None,
                configuration="selftest-gw", use_barcode=False, queries=self.queries)
        self.assertTrue(run_dir.endswith("-lab-selftest-gw-dataset"))
        meta = json.loads(Path(run_dir, "run.json").read_text("utf-8"))
        self.assertEqual((meta["configuration"], meta["options"]["set"], meta["use_barcode"],
                          meta["left_out"], meta["query_set"]["total"]),
                         ("selftest-gw", "dataset", False, {"removed wine": 1}, 6))
        results = [json.loads(line) for line in
                   Path(run_dir, "results.jsonl").read_text("utf-8").splitlines()]
        by_path = {row["image_path"]: row for row in results}
        # Each full image of a wine with its own file finds its wine first.
        for slug in ("red", "green"):
            for row in self.rows_of(slug):
                if row["image_type"] != "label_back":
                    self.assertEqual(by_path[row["image_path"]]["rank_of_truth"], 1, row)
        # The shared file of blue and blue-twin finds one of the two first.
        self.assertEqual(sorted(by_path[row["image_path"]]["rank_of_truth"]
                                for row in self.rows_of("blue") + self.rows_of("blue-twin")),
                         [1, 2])
        self.assertEqual(met["positive"]["n"], 6)


class ErrorTest(Temporary):
    def test_an_unknown_entry_and_an_entry_with_no_view_full_are_refused(self):
        self.lab.add_entry("label-only", views={"label": TER.VIEWS_C_F["label"]})
        for name, text in (("nope", "config.yaml has no embedding nope"),
                           ("label-only", "the embedding label-only has no view full")):
            with self.subTest(name=name):
                with self.assertRaises(embeddings.ConfigError) as caught:
                    selftest.build_backend(name, self.lab.config_path, self.queries[0],
                                           make_model=lambda entry: TER.ColourModel(),
                                           segmenter=TER.FakeSam3())
                self.assertIn(text, str(caught.exception))

    def test_run_benchmark_with_no_queries_still_reads_the_set(self):
        with self.assertRaises(benchmark.BenchmarkError):
            benchmark.run_benchmark(self.lab.db_path, "nope",
                                    mock.Mock(id="x", top_k=1, spec={"workers": 1}),
                                    str(self.root / "runs"), log=lambda message: None)


class CommandTest(TER.Temporary):
    """`selftest.py` as a script, with the index of the fake gateway."""

    def setUp(self):
        super().setUp()
        self.gateway = FakeGateway()
        self.lab = dataset_lab(self.root, base_url=self.gateway.base_url)
        os.makedirs(self.lab.entry_dir(), exist_ok=True)
        with contextlib.redirect_stdout(io.StringIO()):
            build_embeddings.run(embeddings.load_settings(self.lab.config_path).find("gw"),
                                 self.lab.db_path, self.lab.entry_dir())
        self.runs = str(self.root / "runs")

    def tearDown(self):
        self.gateway.close()
        super().tearDown()

    def main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(derive, "Sam3Client", TER.FakeSam3), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = selftest.main(["--config", self.lab.config_path, "--runs-dir", self.runs,
                                  *args])
        return code, out.getvalue(), err.getvalue()

    def test_the_script_writes_one_run_of_each_dataset_image(self):
        code, out, err = self.main("--embedding", "gw", "--label", "probe")
        self.assertEqual(code, 0, err)
        self.assertIn("images: 6, recall@1", out)
        run_dir = out.strip().splitlines()[-1].split("run: ", 1)[1]
        self.assertTrue(run_dir.endswith("-lab-selftest-gw-dataset-probe"))
        meta = json.loads(Path(run_dir, "run.json").read_text("utf-8"))
        self.assertEqual((meta["configuration"], meta["options"]["set"],
                          meta["options"]["workers"], meta["use_barcode"]),
                         ("selftest-gw", "dataset", selftest.DEFAULT_WORKERS, False))
        self.assertEqual(meta["backend"]["url"], self.gateway.base_url + "/embeddings")

    def test_an_unknown_embedding_is_an_error(self):
        code, _out, err = self.main("--embedding", "nope")
        self.assertEqual(code, 1)
        self.assertIn("error: config.yaml has no embedding nope", err)
        self.assertFalse(os.path.exists(self.runs))


if __name__ == "__main__":
    unittest.main()
