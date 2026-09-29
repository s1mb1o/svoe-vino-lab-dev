"""Check narrow label preparation against a temporary database and fake processing."""
import contextlib
import datetime
import hashlib
import io
import json
import sqlite3
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import prepare_rerun_label_inputs as prep

ENDPOINT = "http://192.168.86.14:18081/upstream/sam3"


class LabelInputTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.db = self.root / "lab.sqlite3"
        self.conn = sqlite3.connect(self.db, isolation_level=None)
        self.addCleanup(self.conn.close)
        self.conn.executescript("""
            CREATE TABLE wine_catalog (wine_slug TEXT PRIMARY KEY, state TEXT, name TEXT,
                                       producer TEXT, category TEXT, region TEXT,
                                       name_patched TEXT);
            CREATE TABLE wine_image (wine_slug TEXT, image_type TEXT, sha256 TEXT, source_name TEXT);
            CREATE TABLE image (sha256 TEXT PRIMARY KEY, folder TEXT, extension TEXT, width INT, height INT);
            CREATE TABLE image_derivative (source_sha256 TEXT, kind TEXT, method TEXT, settings TEXT,
                sha256 TEXT, box_left INT, box_top INT, box_right INT, box_bottom INT,
                PRIMARY KEY (source_sha256, kind));
            CREATE TABLE image_derivative_absence (source_sha256 TEXT, kind TEXT, settings TEXT,
                reason TEXT, PRIMARY KEY (source_sha256, kind));
        """)
        self.embedding = types.SimpleNamespace(name=prep.EMBEDDING,
            views={"label": [{"step": "segment", "target": "label"}]},
            view_config_hash=lambda view, role: "fixed-view")

    def source(self, name, state="Active", image_type="main"):
        digest = hashlib.sha256(name.encode()).hexdigest()
        path = self.root / "images" / "main" / (digest + ".bin")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(name.encode())
        self.conn.execute("INSERT OR IGNORE INTO wine_catalog VALUES (?, ?, ?, '', '', '', NULL)", (name, state, name))
        self.conn.execute("INSERT INTO image VALUES (?, 'main', 'bin', 2, 2)", (digest,))
        self.conn.execute("INSERT INTO wine_image VALUES (?, ?, ?, ?)", (name, image_type, digest, name))
        return digest

    def cut(self, digest, settings="old", conn=None):
        (conn or self.conn).execute("INSERT INTO image_derivative VALUES (?, 'label', 'seg', ?, ?, 0, 0, 2, 2)",
                                   (digest, settings, digest))

    def selected(self):
        return prep.missing_active(self.conn, str(self.db), self.embedding)

    def result(self, digest, *, absent=None, unavailable=0, no_label=False):
        result = prep.derive.Derivatives("label")
        result.source_sha256, result.not_applicable = digest, absent
        result.unavailable = unavailable
        if not absent and not unavailable and not no_label:
            result.links.append((digest, "seg", prep.alternatives.SETTINGS_LABEL, digest, 0, 0, 2, 2))
        return result

    def test_selection_excludes_inactive_closeups_existing_manual_and_absence(self):
        missing = self.source("missing")
        self.source("inactive", state="Rejected")
        self.source("closeup", image_type="label_front")
        old = self.source("old-cut")
        self.cut(old)
        manual = self.source("manual-cut")
        self.cut(manual, prep.derive.MANUAL_PREFIX + "fixture")
        absent = self.source("absent")
        self.conn.execute("INSERT INTO image_derivative_absence VALUES (?, 'label', ?, 'a box')",
                          (absent, prep.alternatives.SETTINGS_LABEL_ABSENCE))
        self.assertEqual(set(self.selected()), {missing})

    def test_replaced_main_photo_is_not_selected(self):
        original = self.source("wine")
        patch = self.source("patch")
        self.conn.execute("DELETE FROM wine_image WHERE wine_slug = 'patch'")
        self.conn.execute("INSERT INTO wine_image VALUES ('wine', 'main_patched', ?, 'patch')", (patch,))
        self.assertEqual(set(self.selected()), {patch})
        self.assertNotIn(original, self.selected())

    def test_process_runs_outside_transaction_and_write_runs_inside(self):
        digest = self.source("missing")
        source = self.selected()[digest]
        processing = []
        original_write = prep.alternatives.write_processed_rows

        def process(conn, *args):
            processing.append(conn.in_transaction)
            return self.result(digest)

        def write(conn, result):
            self.assertTrue(conn.in_transaction)
            return original_write(conn, result)

        with mock.patch.object(prep.alternatives, "process_image", side_effect=process), \
                mock.patch.object(prep.alternatives, "write_processed_rows", side_effect=write):
            result = prep.process_selected(self.conn, str(self.db), self.embedding, source, object())
        self.assertEqual(processing, [False])
        self.assertEqual(result["state"], "written")
        self.assertEqual(self.selected(), {})
        self.assertFalse(self.conn.in_transaction)

    def test_concurrent_manual_cut_is_not_overwritten(self):
        digest = self.source("missing")
        source = self.selected()[digest]
        manual = prep.derive.MANUAL_PREFIX + "concurrent"

        def process(conn, *args):
            with contextlib.closing(sqlite3.connect(self.db, isolation_level=None)) as writer:
                self.cut(digest, manual, writer)
            return self.result(digest)

        with mock.patch.object(prep.alternatives, "process_image", side_effect=process), \
                mock.patch.object(prep.alternatives, "write_processed_rows") as write:
            result = prep.process_selected(self.conn, str(self.db), self.embedding, source, object())
        write.assert_not_called()
        self.assertEqual(result["state"], "skipped_concurrent_change")
        self.assertEqual(self.conn.execute("SELECT settings FROM image_derivative").fetchone()[0], manual)

    def test_concurrent_inactive_source_is_not_written(self):
        digest = self.source("missing")
        source = self.selected()[digest]

        def process(conn, *args):
            with contextlib.closing(sqlite3.connect(self.db, isolation_level=None)) as writer:
                writer.execute("UPDATE wine_catalog SET state='Rejected'")
            return self.result(digest)

        with mock.patch.object(prep.alternatives, "process_image", side_effect=process), \
                mock.patch.object(prep.alternatives, "write_processed_rows") as write:
            result = prep.process_selected(self.conn, str(self.db), self.embedding, source, object())
        write.assert_not_called()
        self.assertEqual(result["state"], "skipped_concurrent_change")

    def test_unavailable_and_no_label_do_not_write(self):
        digest = self.source("missing")
        source = self.selected()[digest]
        for result, state in ((self.result(digest, unavailable=1), "unavailable"),
                              (self.result(digest, no_label=True), "no_label")):
            with self.subTest(state=state), mock.patch.object(prep.alternatives, "process_image", return_value=result), \
                    mock.patch.object(prep.alternatives, "write_processed_rows") as write:
                answer = prep.process_selected(self.conn, str(self.db), self.embedding, source, object())
                write.assert_not_called()
                self.assertEqual(answer["state"], state)

    def test_failed_write_rolls_back(self):
        digest = self.source("missing")
        source = self.selected()[digest]

        def write(conn, result):
            self.cut(digest, "must-rollback", conn)
            raise OSError("fake write failure")

        with mock.patch.object(prep.alternatives, "process_image", return_value=self.result(digest)), \
                mock.patch.object(prep.alternatives, "write_processed_rows", side_effect=write):
            with self.assertRaisesRegex(OSError, "fake write"):
                prep.process_selected(self.conn, str(self.db), self.embedding, source, object())
        self.assertFalse(self.conn.in_transaction)
        self.assertIsNone(self.conn.execute("SELECT * FROM image_derivative").fetchone())

    def test_source_changed_during_processing_is_rejected_inside_transaction(self):
        digest = self.source("missing")
        source = self.selected()[digest]
        hash_states, real_hash = [], prep.sha256

        def process(conn, *args):
            Path(source["path"]).write_bytes(b"replaced during processing")
            return self.result(digest)

        def checked_hash(path):
            hash_states.append(self.conn.in_transaction)
            return real_hash(path)

        with mock.patch.object(prep.alternatives, "process_image", side_effect=process), \
                mock.patch.object(prep, "sha256", side_effect=checked_hash), \
                mock.patch.object(prep.alternatives, "write_processed_rows") as write:
            result = prep.process_selected(self.conn, str(self.db), self.embedding, source, object())
        self.assertEqual(result["state"], "source_changed")
        self.assertEqual(hash_states, [False, True])
        write.assert_not_called()
        self.assertFalse(self.conn.in_transaction)
        self.assertIsNone(self.conn.execute("SELECT * FROM image_derivative").fetchone())

    def test_gate_expiry_between_detection_and_fallback_blocks_second_request(self):
        digest = self.source("missing")
        source = self.selected()[digest]
        client = mock.Mock()
        client.instances.return_value = ([], 1)
        check = mock.Mock(side_effect=[None, None, ValueError("parent gate expired")])

        def process(conn, db, digest, path, kind, guarded, warnings):
            self.assertFalse(conn.in_transaction)
            guarded.instances("fake-image", "label")
            guarded.instances("fake-image", "package")
            return self.result(digest, no_label=True)

        with mock.patch.object(prep.alternatives, "process_image", side_effect=process), \
                mock.patch.object(prep.alternatives, "write_processed_rows") as write:
            with self.assertRaisesRegex(ValueError, "gate expired"):
                prep.process_selected(self.conn, str(self.db), self.embedding, source, client, check)
        client.instances.assert_called_once_with("fake-image", "label")
        self.assertEqual(check.call_count, 3)
        write.assert_not_called()
        self.assertFalse(self.conn.in_transaction)

    def test_database_acquisition_failures_close_each_acquired_resource(self):
        config = self.root / "config.yaml"
        config.write_text("fake config")
        settings = types.SimpleNamespace(db_path=str(self.db), find=lambda name: self.embedding)
        for failure in ("connect", "pragma"):
            with self.subTest(failure=failure), contextlib.ExitStack() as stack:
                readonly, writable, client = mock.Mock(), mock.Mock(), mock.Mock()
                stack.enter_context(mock.patch.object(prep.embeddings, "load_settings", return_value=settings))
                stack.enter_context(mock.patch.object(prep.embeddings, "open_database", return_value=readonly))
                stack.enter_context(mock.patch.object(prep, "missing_active", return_value={}))
                stack.enter_context(mock.patch.object(prep, "check_gate", return_value={"fake": True}))
                stack.enter_context(mock.patch.object(prep, "measurement_lock", return_value=contextlib.nullcontext()))
                stack.enter_context(mock.patch.dict(prep.os.environ, {"SAM3_ENDPOINT": ENDPOINT}))
                stack.enter_context(mock.patch.object(prep.derive, "Sam3Client", return_value=client))
                connect = stack.enter_context(mock.patch.object(prep.sqlite3, "connect", return_value=writable))
                if failure == "connect":
                    connect.side_effect = sqlite3.OperationalError("fake connect failure")
                else:
                    writable.execute.side_effect = sqlite3.OperationalError("fake pragma failure")
                stack.enter_context(contextlib.redirect_stderr(io.StringIO()))
                result = prep.main(["--config", str(config), "--execute", "--gate", str(self.root / "gate.json"),
                                    "--output", str(self.root / failure)])
                self.assertEqual(result, 2)
                readonly.close.assert_called_once()
                client.session.close.assert_called_once()
                if failure == "pragma":
                    writable.close.assert_called_once()
                else:
                    writable.close.assert_not_called()

    def test_internal_endpoint_and_fresh_bound_parent_gate(self):
        self.assertEqual(prep.internal_endpoint(ENDPOINT + "/"), ENDPOINT)
        for endpoint in (None, "https://example.com/upstream/sam3", ENDPOINT + "?redirect=external"):
            with self.assertRaises(ValueError):
                prep.internal_endpoint(endpoint)
        config = self.root / "config.yaml"
        config.write_text("fake config")
        now = datetime.datetime.now(datetime.timezone.utc)
        gate = {"recorded_at": now.isoformat(), "embedding": prep.EMBEDDING,
                "database": str(self.db.resolve()), "config_sha256": prep.sha256(config),
                "sam3_endpoint": ENDPOINT, "comparisons_complete": True,
                "no_active_measurements": True, "gpu_preflight_passed": True,
                "gpu_task_registered": True, "evidence": [str(config)]}
        path = self.root / "gate.json"
        path.write_text(json.dumps(gate))
        self.assertEqual(prep.check_gate(path, config, self.db, ENDPOINT, now), gate)
        with self.assertRaisesRegex(ValueError, "stale"):
            prep.check_gate(path, config, self.db, ENDPOINT, now + datetime.timedelta(minutes=11))
        config.write_text("changed")
        with self.assertRaisesRegex(ValueError, "does not match"):
            prep.check_gate(path, config, self.db, ENDPOINT, now)

    def test_default_dry_run_constructs_no_client_and_writes_no_rows(self):
        digest = self.source("missing")
        config = self.root / "config.yaml"
        config.write_text("fake config")
        settings = types.SimpleNamespace(db_path=str(self.db), find=lambda name: self.embedding)
        before = self.conn.total_changes
        with mock.patch.object(prep.embeddings, "load_settings", return_value=settings), \
                mock.patch.object(prep.derive, "Sam3Client") as client, \
                contextlib.redirect_stdout(io.StringIO()) as stream:
            self.assertEqual(prep.main(["--config", str(config)]), 0)
        client.assert_not_called()
        self.assertEqual(self.conn.total_changes, before)
        self.assertEqual(json.loads(stream.getvalue())["selected"][0]["sha256"], digest)

    def test_execute_rejects_external_endpoint_before_client_construction(self):
        self.source("missing")
        config = self.root / "config.yaml"
        config.write_text("fake config")
        settings = types.SimpleNamespace(db_path=str(self.db), find=lambda name: self.embedding)
        with mock.patch.object(prep.embeddings, "load_settings", return_value=settings), \
                mock.patch.dict(prep.os.environ, {"SAM3_ENDPOINT": "https://example.com/upstream/sam3"}), \
                mock.patch.object(prep.derive, "Sam3Client") as client, \
                contextlib.redirect_stderr(io.StringIO()):
            result = prep.main(["--config", str(config), "--execute", "--gate", str(self.root / "gate.json"),
                                "--output", str(self.root / "output")])
        self.assertEqual(result, 2)
        client.assert_not_called()
        self.assertFalse((self.root / "output").exists())


if __name__ == "__main__":
    unittest.main()
