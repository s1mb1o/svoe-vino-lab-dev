"""Tests of plan 78: manual wine creation and incremental index activation."""
import contextlib
import io
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import add_wine as add_wine_cli  # noqa: E402
import build_embeddings  # noqa: E402
import embeddings  # noqa: E402
import new_wine_workflow  # noqa: E402
from embedding_lab import FakeGateway, standard_lab  # noqa: E402
from test_manual_wines import form, picture  # noqa: E402
from test_patches import FakeSam3  # noqa: E402


def vectors_by_key(directory):
    index = embeddings.read_index(directory)
    vectors = embeddings.read_vectors(directory, index)
    return {(item["source_sha256"], item["view"]): vectors[item["row"]].copy()
            for item in index["items"]}


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.gateway = FakeGateway()
        self.addCleanup(self.gateway.close)
        self.lab = standard_lab(self.directory.name, self.gateway.base_url)
        self.lab.write_config(python=sys.executable)
        raw = yaml.safe_load(Path(self.lab.config_path).read_text(encoding="utf-8"))
        raw[new_wine_workflow.CONFIG_KEY] = "gw"
        Path(self.lab.config_path).write_text(
            yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
        settings = embeddings.load_settings(self.lab.config_path)
        entry = settings.find("gw")
        self.entry = embeddings.entry_dir(settings.db_path, "gw")
        Path(self.entry).mkdir(parents=True)
        with contextlib.redirect_stdout(io.StringIO()):
            build_embeddings.run(entry, settings.db_path, self.entry,
                                 checkpoint_seconds=999)
        self.old = vectors_by_key(self.entry)
        self.db = self.lab.db_path
        self.config = self.lab.config_path
        self.lab.close()

    def count(self, slug):
        with sqlite3.connect(self.db) as conn:
            return conn.execute("SELECT count(*) FROM wine_catalog WHERE wine_slug = ?",
                                (slug,)).fetchone()[0]

    def test_success_reuses_old_vectors_and_activates_the_new_items(self):
        result = new_wine_workflow.create(
            self.db, form(), config_path=self.config, segmenter=FakeSam3())
        self.assertEqual(result["index"]["state"], "active", result)
        self.assertEqual(result["index"]["name"], "gw")
        self.assertEqual(result["index"]["items"], 2)
        self.assertTrue(result["index"]["changed"])
        self.assertEqual(self.count("__my-wine"), 1)
        after = vectors_by_key(self.entry)
        for key, vector in self.old.items():
            np.testing.assert_array_equal(after[key], vector)
        self.assertGreater(len(after), len(self.old))

    def test_an_unknown_embedding_and_no_active_index_create_no_wine(self):
        with self.assertRaisesRegex(new_wine_workflow.WorkflowError,
                                    "no embedding absent"):
            new_wine_workflow.create(
                self.db, form(), config_path=self.config, embedding="absent",
                segmenter=FakeSam3())
        self.assertEqual(self.count("__my-wine"), 0)
        Path(self.entry, embeddings.INDEX).unlink()
        with self.assertRaisesRegex(new_wine_workflow.WorkflowError,
                                    "has no active index"):
            new_wine_workflow.create(
                self.db, form(), config_path=self.config, segmenter=FakeSam3())
        self.assertEqual(self.count("__my-wine"), 0)

    def test_a_build_failure_keeps_the_created_wine(self):
        def fail(*_args):
            raise embeddings.ConfigError("model unavailable")

        result = new_wine_workflow.create(
            self.db, form(), config_path=self.config, segmenter=FakeSam3(), build=fail)
        self.assertEqual(result["index"], {
            "name": "gw", "state": "failed", "error": "model unavailable"})
        self.assertIn("wine was created", " ".join(result["warnings"]).lower())
        self.assertEqual(self.count("__my-wine"), 1)

    def test_a_done_build_that_omits_the_new_item_is_failed(self):
        result = new_wine_workflow.create(
            self.db, form(), config_path=self.config, segmenter=FakeSam3(),
            build=lambda *_args: {"event": "done", "built": 0})
        self.assertEqual(result["index"]["state"], "failed")
        self.assertIn("does not contain current items", result["index"]["error"])

    def test_create_wine_then_update_index_activates_the_new_items(self):
        # Plan 84: the lab server runs the two steps apart.
        result, selected = new_wine_workflow.create_wine(
            self.db, form(), config_path=self.config, segmenter=FakeSam3())
        self.assertIsNone(result["index"])
        self.assertEqual(selected[1], "gw")
        self.assertEqual(self.count("__my-wine"), 1)
        index, warning = new_wine_workflow.update_index(selected, self.config, "__my-wine")
        self.assertIsNone(warning)
        self.assertEqual((index["state"], index["items"]), ("active", 2))


class CliTest(unittest.TestCase):
    def test_cli_reads_the_image_and_prints_the_shared_result(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "wine.png"
            image.write_bytes(picture())
            answer = {"ok": True, "slug": "__cli", "record": {"slug": "__cli"},
                      "index": {"name": "gw", "state": "active"}}
            out = io.StringIO()
            with mock.patch.object(add_wine_cli.lab_server, "read_config",
                                   return_value=({}, str(Path(directory) / "db"))), \
                    mock.patch.object(add_wine_cli.lab_server, "add_wine",
                                      return_value=answer) as create, \
                    contextlib.redirect_stdout(out):
                code = add_wine_cli.main([
                    "--slug", "cli", "--name", "CLI wine", "--producer", "P",
                    "--beverage-type", "4", "--category", "Красное", "--color", "red",
                    "--region", "R",
                    "--image", str(image), "--config", "test.yaml",
                    "--embedding", "gw"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out.getvalue()), answer)
            body = create.call_args.args[1]
            self.assertEqual((body["slug"], body["image_name"]), ("__cli", "wine.png"))
            self.assertEqual(body["beverage_type_code"], "4")
            self.assertEqual(create.call_args.kwargs["embedding"], "gw")

    def test_cli_uses_exit_one_when_the_wine_exists_but_the_index_failed(self):
        answer = {"ok": True, "slug": "__cli", "record": {"slug": "__cli"},
                  "index": {"name": "gw", "state": "failed"}}
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "wine.png"
            image.write_bytes(picture())
            with mock.patch.object(add_wine_cli.lab_server, "read_config",
                                   return_value=({}, str(Path(directory) / "db"))), \
                    mock.patch.object(add_wine_cli.lab_server, "add_wine",
                                      return_value=answer), \
                    contextlib.redirect_stdout(io.StringIO()):
                code = add_wine_cli.main([
                    "--slug", "cli", "--name", "CLI wine", "--producer", "P",
                    "--category", "Красное", "--color", "red", "--region", "R",
                    "--image", str(image)])
        self.assertEqual(code, 1)


class PageContractTest(unittest.TestCase):
    def test_add_wine_dialog_names_the_index_wait(self):
        page = (ROOT / "pipeline" / "pages" / "dataset.html").read_text(encoding="utf-8")
        self.assertIn('id="wine-index"', page)
        self.assertIn('DATA.new_wine_embedding || "is not configured"', page)
        self.assertIn('"Creating…"', page)


if __name__ == "__main__":
    unittest.main()
