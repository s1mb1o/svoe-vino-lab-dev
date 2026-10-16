"""Fixture checks for startup synchronization, serialization, and matcher publication."""

import contextlib
import io
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import yaml

from embedding_lab import FakeGateway, Lab, bottle_on_transparent
import build_embeddings
import embeddings
import import_website
import website_import_routes as routes
import website_sync as sync


class WebsiteSyncTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.work = self.root / "runs"
        self.gateway = FakeGateway()
        self.addCleanup(self.gateway.close)
        self.lab = Lab(self.root / "lab", self.gateway.base_url)
        self.addCleanup(self.lab.close)
        self.lab.wine("a")
        image = bottle_on_transparent()
        self.digest = self.lab.image("a", "main", image,
                                     derivative=image.crop((20, 10, 40, 90)), box=(20, 10, 40, 90))
        self.lab.add_entry(views={"full": {"steps": [{"step": "segment", "target": "package"}]}})
        self.configure()
        self.opts = sync.options(self.lab.config_path)

    def configure(self, **values):
        path = Path(self.lab.config_path)
        config = yaml.safe_load(path.read_text())
        config["website_sync"] = {"on_startup": False, "matcher_embeddings": ["gw"],
                                  "matcher_output": "published", **values}
        path.write_text(yaml.safe_dump(config))
        return config

    def build(self):
        settings = embeddings.load_settings(self.lab.config_path)
        with contextlib.redirect_stdout(io.StringIO()):
            build_embeddings.run(settings.find("gw"), settings.db_path, self.lab.entry_dir())

    def fake_import(self, command):
        if "--prepare" in command:
            directory = Path(command[command.index("--prepare") + 1])
            sync.write_json(directory / "diff.json", {
                "conflicts": [{"id": "text:a:name", "kind": "text"}],
                "changes": [], "refused": 0, "website": 1,
                "automation_checked_at": "2026-10-16T10:00:00Z",
                "automatic_result": {"added": ["a"], "replaced": []}})

    def run_sync(self, **values):
        with contextlib.redirect_stdout(io.StringIO()):
            return sync.synchronize(self.opts, self.work, **values)

    def test_config_requires_exact_boolean_and_distinct_names(self):
        for raw in ({"on_startup": "false"}, {"matcher_embeddings": ["gw", "gw"]},
                    {"matcher_embeddings": [None]}, {"on_startup": True},
                    {"matcher_output": ""}, {"command": "anything"}):
            with self.subTest(raw=raw), self.assertRaises(sync.SyncError):
                sync.check_config({"website_sync": raw})

    def test_no_startup_by_default(self):
        with mock.patch.object(sync.subprocess, "Popen") as popen:
            self.assertIsNone(sync.start_on_launch({}, self.lab.config_path))
            self.assertIsNone(sync.start_on_launch(self.configure(), self.lab.config_path))
        popen.assert_not_called()

    def test_enabled_startup_uses_same_cli_and_custom_config(self):
        config = self.configure(on_startup=True)
        with mock.patch.object(sync, "WORK", self.work), mock.patch.object(sync.subprocess, "Popen") as popen:
            process = sync.start_on_launch(config, self.lab.config_path)
        self.assertIs(process, popen.return_value)
        command = popen.call_args.args[0]
        self.assertEqual(command[-2:], ["--config", self.lab.config_path])
        self.assertTrue(command[1].endswith("scripts/sync_website.py"))
        self.assertTrue(popen.call_args.kwargs["start_new_session"])

    def test_invalid_destination_or_embedding_stops_before_import(self):
        for values in ({"matcher_output": "data"}, {"matcher_output": "data/child"},
                       {"matcher_embeddings": ["missing"]}):
            self.configure(**values)
            with self.assertRaises(sync.SyncError):
                sync.options(self.lab.config_path)
        existing = self.lab.root / "directory"
        existing.mkdir()
        self.configure(matcher_output="directory")
        with self.assertRaises(sync.SyncError):
            sync.options(self.lab.config_path)
        self.assertTrue(existing.is_dir())

    def test_dry_run_makes_no_requests_or_run_directory(self):
        with mock.patch.object(sync, "WORK", self.work), mock.patch.object(sync, "synchronize") as run:
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(sync.main(["--config", self.lab.config_path, "--dry-run"]), 0)
        run.assert_not_called()
        self.assertFalse(self.work.exists())
        self.assertFalse(self.opts.output.exists())
        self.assertFalse(json.loads(output.getvalue())["deploy"])

    def test_operation_lock_is_shared_with_another_process(self):
        code = "import sys; sys.path.insert(0,sys.argv[1]); from website_sync import OperationLock; " \
               "lock=OperationLock(sys.argv[2]); lock.__enter__()"
        with sync.OperationLock(self.work):
            process = subprocess.run([sys.executable, "-c", code, str(sync.ROOT / "pipeline"), str(self.work)],
                                     capture_output=True, text=True)
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("already runs", process.stderr)
        with sync.OperationLock(self.work):
            pass

    def test_ui_cannot_start_while_cli_holds_lock(self):
        with sync.OperationLock(self.work), mock.patch.object(routes, "WORK", str(self.work)):
            with mock.patch.object(routes.subprocess, "Popen") as popen:
                answer = routes.start(SimpleNamespace(db_path=self.lab.db_path))
        self.assertEqual(answer[0], 409)
        popen.assert_not_called()
        self.assertEqual(list(self.work.glob("[0-9]*")), [])

    def test_child_inherits_ui_lock_until_exit(self):
        script = self.root / "fake.py"
        script.write_text("import time; time.sleep(0.2)\n")
        with mock.patch.object(routes, "WORK", str(self.work)), mock.patch.object(routes, "SCRIPT", str(script)):
            answer = routes.start(SimpleNamespace(db_path=self.lab.db_path))
            self.assertEqual(answer[0], 202)
            try:
                with self.assertRaises(sync.Busy):
                    with sync.OperationLock(self.work):
                        pass
            finally:
                process = next(iter(routes._PROCESSES.values()))
                process.wait()
                routes._running()
            with sync.OperationLock(self.work):
                pass

    def test_fixed_stage_order_and_custom_configuration(self):
        calls = []
        def run(command):
            calls.append(command)
            self.fake_import(command)
        published = mock.Mock(return_value={"published": "fixture"})
        result = self.run_sync(run_command=run, publish_catalog=published)
        self.assertTrue(result["ok"])
        self.assertEqual([Path(x[1]).stem for x in calls],
                         ["import_website", "build_embeddings", "build_clusters"])
        self.assertTrue(all(x[x.index("--config") + 1] == self.lab.config_path for x in calls))
        self.assertIn("--automatic", calls[0])
        self.assertEqual(result["pending_conflicts"], 1)
        diff = sync.read_json(self.work / result["run"] / "diff.json")
        self.assertEqual(diff["conflicts"], [{"id": "text:a:name", "kind": "text"}])
        published.assert_called_once()

    def test_stage_failure_prevents_publication_and_preserves_diff(self):
        def run(command):
            self.fake_import(command)
            if "build_embeddings.py" in command[1]:
                raise sync.SyncError("embedding service unavailable")
        publish = mock.Mock()
        with self.assertRaisesRegex(sync.SyncError, "unavailable"):
            self.run_sync(run_command=run, publish_catalog=publish)
        publish.assert_not_called()
        result = sync.read_json(next(self.work.glob("*/sync-result.json")))
        self.assertFalse(result["ok"])
        self.assertEqual(result["stage"], "build_embeddings")
        self.assertTrue(next(self.work.glob("*/diff.json")).exists())

    def test_unfinished_safe_import_prevents_publication(self):
        publish = mock.Mock()
        with self.assertRaisesRegex(sync.SyncError, "did not finish"):
            self.run_sync(run_command=lambda _: None, publish_catalog=publish)
        publish.assert_not_called()

    def test_stale_or_missing_vectors_cannot_replace_publication(self):
        previous = self.root / "previous"
        previous.mkdir()
        self.opts.output.symlink_to(previous)
        directory = self.root / "release"
        directory.mkdir()
        with self.assertRaises(sync.SyncError):
            sync.publish(self.opts, directory)
        self.assertEqual(self.opts.output.resolve(), previous)
        self.assertFalse((directory / "matcher-catalog").exists())

    def test_real_build_copy_validation_and_atomic_publication(self):
        self.build()
        directory = self.root / "release"
        directory.mkdir()
        result = sync.publish(self.opts, directory)
        self.assertEqual(result["embeddings"]["gw"]["missing"], 0)
        self.assertEqual(self.opts.output.resolve(), directory / "matcher-catalog")
        self.assertTrue((self.opts.output / "catalog.sqlite3").is_file())
        self.assertFalse((self.opts.output / "images").exists())
        self.assertEqual(sync.complete_indexes(self.opts), {"gw": 1})

    def test_snapshot_mismatch_preserves_old_publication(self):
        self.build()
        previous = self.root / "previous"
        previous.mkdir()
        self.opts.output.symlink_to(previous)
        directory = self.root / "release"
        directory.mkdir()
        original = sync.complete_indexes
        def check(opts, database=None, catalog=None):
            if database:
                raise sync.SyncError("snapshot changed")
            return original(opts)
        with mock.patch.object(sync, "complete_indexes", side_effect=check):
            with self.assertRaisesRegex(sync.SyncError, "snapshot changed"):
                sync.publish(self.opts, directory)
        self.assertEqual(self.opts.output.resolve(), previous)

    def test_stop_terminates_and_reaps_active_child(self):
        log = (self.root / "runner.log").open("w")
        self.addCleanup(log.close)
        runner = sync.Runner(log)
        runner.child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"],
                                        start_new_session=True)
        child = runner.child
        runner.stop(signal.SIGTERM, None)
        with self.assertRaises(InterruptedError):
            runner.wait()
        self.assertIsNotNone(child.poll())

    def test_new_source_after_build_blocks_publication(self):
        self.build()
        self.lab.wine("b")
        image = bottle_on_transparent((10, 20, 30))
        self.lab.image("b", "main", image,
                       derivative=image.crop((20, 10, 40, 90)), box=(20, 10, 40, 90))
        with self.assertRaisesRegex(sync.SyncError, "incomplete or stale"):
            sync.complete_indexes(self.opts)

    def test_complete_fixture_pipeline_builds_clusters_and_publishes(self):
        def run(command):
            if "--prepare" in command:
                self.fake_import(command)
            else:
                with (self.root / "children.log").open("a") as log:
                    subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT)
        result = self.run_sync(run_command=run)
        self.assertTrue(result["ok"])
        self.assertTrue((self.opts.output / "embeddings/gw/clusters.json").is_file())

    def test_all_embedding_builds_precede_cluster_builds(self):
        self.opts.names = ["first", "second"]
        commands = sync.commands(self.opts, self.root / "run")
        self.assertEqual([Path(command[1]).stem for command in commands],
                         ["import_website", "build_embeddings", "build_embeddings",
                          "build_clusters", "build_clusters"])
        self.assertEqual([command[-1] for command in commands[1:]],
                         ["first", "second", "first", "second"])

    def test_importer_passes_custom_sam3_and_vlm_configuration(self):
        path = Path(self.lab.config_path)
        config = yaml.safe_load(path.read_text())
        config["sam3"] = {"endpoint": "http://127.0.0.1:9/custom-sam3"}
        path.write_text(yaml.safe_dump(config))
        import website_image_review
        with mock.patch.object(import_website.derive, "Sam3Client") as segmenter, \
                mock.patch.object(website_image_review, "ImageReviewer") as reviewer, \
                mock.patch.object(import_website, "prepare", return_value={
                    "conflicts": [], "changes": [], "refused": 0}) as prepare:
            with contextlib.redirect_stdout(io.StringIO()):
                code = import_website.main(["--db", self.lab.db_path, "--prepare", str(self.root / "run"),
                                            "--automatic", "--config", self.lab.config_path])
        self.assertEqual(code, 0)
        segmenter.assert_called_once_with("http://127.0.0.1:9/custom-sam3")
        reviewer.assert_called_once_with(self.lab.config_path, segmenter=segmenter.return_value)
        self.assertIs(prepare.call_args.kwargs["reviewer"], reviewer.return_value)
        self.assertIs(prepare.call_args.kwargs["segmenter"], segmenter.return_value)

    def test_cli_status_is_visible_in_import_routes(self):
        self.run_sync(run_command=self.fake_import, publish_catalog=lambda *_: {"published": "fixture"})
        with mock.patch.object(routes, "WORK", str(self.work)):
            view = routes.state_view()
        self.assertEqual(view["state"], "prepared")
        self.assertTrue(view["synchronization"]["ok"])
        self.assertEqual(view["counts"]["conflicts"], 1)


if __name__ == "__main__":
    unittest.main()
