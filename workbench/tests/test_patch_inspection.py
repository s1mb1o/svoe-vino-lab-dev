"""Check local patch jobs, saved-query validation, and figure selection."""

import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import types
import unittest
from unittest import mock

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
import patch_inspection as PI  # noqa: E402
import run_steps  # noqa: E402


class PatchInspectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.db = self.root / "catalog/catalog.sqlite3"
        self.db.parent.mkdir()
        sqlite3.connect(self.db).close()
        self.photo = self.root / "query.png"
        Image.new("RGB", (40, 30), "white").save(self.photo)
        self.evidence = self.root / "evidence"
        (self.evidence / "index-tuned").mkdir(parents=True)
        (self.evidence / "tuning").mkdir()
        (self.evidence / "index-tuned/index.json").write_text('{}')
        (self.evidence / "tuning/selected.json").write_text('{}')
        for name in ("queries-fresh.json", "references-fresh.json"):
            (self.evidence / name).write_text('{"items": []}')
        self.patches = [mock.patch.object(PI, "EVIDENCE", self.evidence),
                        mock.patch.object(PI, "EXPERIMENT", self.root),
                        mock.patch.object(run_steps, "_run_data", return_value=({}, {}, {})),
                        mock.patch.object(run_steps, "Photo", return_value=types.SimpleNamespace(
                            path=str(self.photo), image=Image.new("RGB", (40, 30), "white")))]
        for patch in self.patches:
            patch.start()
        PI._JOBS.clear()

    def tearDown(self):
        for patch in reversed(self.patches):
            patch.stop()
        PI._JOBS.clear()
        self.temporary.cleanup()

    def request(self, extra=""):
        return PI.respond(self.db, "/api/run-patches?id=run&query=q-1"+extra, runs_dir=self.root)

    def test_status_read_does_not_start_inference(self):
        with mock.patch.object(PI, "_run") as run:
            code, data, _kind = self.request()
        self.assertEqual(code, 200)
        self.assertEqual(data["status"], "idle")
        run.assert_not_called()

    def test_unknown_run_cannot_resolve_image_or_start_worker(self):
        with mock.patch.object(run_steps, "_run_data", side_effect=run_steps.StepError(404, "unknown run")), mock.patch.object(PI, "_run") as run:
            code, data, _kind = self.request("&start=1")
        self.assertEqual(code, 404)
        self.assertIn("unknown run", data["error"])
        run.assert_not_called()

    def test_duplicate_or_missing_identifiers_are_rejected(self):
        for query in ("?id=run", "?id=a&id=b&query=c", "?id=&query=c"):
            code, _data, _kind = PI.respond(self.db, "/api/run-patches"+query)
            self.assertEqual(code, 400)

    def test_one_click_starts_one_worker_and_result_selects_checked_image(self):
        sidecar = self.root / "annotation.json"
        sidecar.write_text('{}')
        def run(directory, _photo, _sidecar):
            (directory / "candidate-00.png").write_bytes(b"PNG evidence")
            (directory / "inspection.json").write_text(json.dumps({"status":"ready", "candidates":[{"image":"candidate-00.png", "slug":"wine"}]}))
        with mock.patch.object(PI, "_sidecar", return_value=sidecar), mock.patch.object(PI, "_run", side_effect=run) as worker:
            self.request("&start=1")
            for thread in PI._JOBS.values():
                thread.join(5)
            code, data, _kind = self.request("&start=1")
            self.assertEqual(code, 200)
            self.assertEqual(data["status"], "ready")
            self.assertIn("candidate=0", data["candidates"][0]["src"])
            code, pixels, kind = self.request("&candidate=0")
            self.assertEqual((code, pixels, kind), (200, b"PNG evidence", "image/png"))
            self.assertEqual(self.request("&candidate=-1")[0], 400)
            self.assertEqual(self.request("&candidate=10")[0], 400)
            worker.assert_called_once()
            self.photo.write_bytes(b"new source bytes")
            self.assertEqual(self.request()[1]["status"], "idle")

    def test_missing_tuned_index_is_an_explicit_error(self):
        (self.evidence / "index-tuned/index.json").unlink()
        code, data, _kind = self.request("&start=1")
        self.assertEqual(code, 503)
        self.assertIn("not available", data["error"])

    def test_missing_cached_masks_make_no_model_request(self):
        photo = types.SimpleNamespace(path=str(self.photo), image=Image.new("RGB", (40, 30), "white"))
        target = self.root / "masks"
        target.mkdir()
        with mock.patch.object(run_steps, "_cut", return_value=(None,None,"no cached mask",None)) as cut:
            sidecar = PI._sidecar(photo, {}, target)
        self.assertEqual(json.loads(sidecar.read_text())["masks"], {})
        self.assertEqual(cut.call_count, 2)


if __name__ == "__main__":
    unittest.main()
