"""Check local patch jobs, saved-query validation, and figure selection."""

import hashlib
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
        (self.evidence).mkdir(parents=True)
        (self.evidence / "gallery.json").write_text('{}')
        (self.evidence / "selection.lock.json").write_text('{}')
        (self.evidence / "queries.json").write_text('{"items": []}')
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
            images = {panel: panel+".png" for panel in ("reference", "query", "reference_weights", "query_weights")}
            for panel, name in images.items():
                (directory / name).write_bytes(("PNG "+panel).encode())
            (directory / "inspection.json").write_text(json.dumps({"status":"ready", "candidates":[{"images":images, "slug":"wine"}]}))
        with mock.patch.object(PI, "_sidecar", return_value=sidecar), mock.patch.object(PI, "_run", side_effect=run) as worker:
            self.request("&start=1")
            for thread in PI._JOBS.values():
                thread.join(5)
            code, data, _kind = self.request("&start=1")
            self.assertEqual(code, 200)
            self.assertEqual(data["status"], "ready")
            self.assertEqual(len(data["candidates"][0]["images"]), 4)
            self.assertIn("candidate=0", data["candidates"][0]["images"]["reference"])
            code, pixels, kind = self.request("&candidate=0")
            self.assertEqual((code, pixels, kind), (200, b"PNG reference", "image/png"))
            for panel in ("reference", "query", "reference_weights", "query_weights"):
                self.assertEqual(self.request("&candidate=0&panel="+panel)[1], ("PNG "+panel).encode())
            self.assertEqual(self.request("&candidate=0&panel=../secret")[0], 400)
            self.assertEqual(self.request("&candidate=0&panel=query&panel=reference")[0], 400)
            self.assertEqual(self.request("&candidate=-1")[0], 400)
            self.assertEqual(self.request("&candidate=10")[0], 400)
            worker.assert_called_once()
            self.photo.write_bytes(b"new source bytes")
            self.assertEqual(self.request()[1]["status"], "idle")

    def stored_viewer(self):
        source_sha = hashlib.sha256(self.photo.read_bytes()).hexdigest()
        directory = self.evidence / "viewer-queries" / source_sha
        directory.mkdir(parents=True)
        row = {"key":"fresh-viewer", "source_sha256":source_sha, "image":"previous/path"}
        for role in ("input", "bottle", "label", "occlusion", "rotation_base"):
            path = directory / (role+".png")
            Image.new("L", (10,20), 255).save(path)
            row[role] = str(path)
        (directory / "prepared.json").write_text(json.dumps(row))
        return row

    def test_stored_viewer_label_precedes_frozen_cohort_without_inference(self):
        row = self.stored_viewer()
        (self.evidence / "queries.json").write_text(json.dumps({"items":[
            {"source_sha256":row["source_sha256"], "key":"frozen-cohort"}]}))
        target = self.root / "prepared"
        target.mkdir()
        photo = types.SimpleNamespace(path=str(self.photo))
        with mock.patch.object(run_steps, "_cut") as cut:
            result = json.loads(PI._sidecar(photo, {}, target).read_text())
        self.assertEqual(result["key"], "fresh-viewer")
        self.assertEqual(result["image"], str(self.photo))
        self.assertEqual(result["label"], row["label"])
        cut.assert_not_called()

    def test_stored_viewer_source_mismatch_is_rejected(self):
        row = self.stored_viewer()
        directory = Path(row["label"]).parent
        row["source_sha256"] = "different-source"
        (directory / "prepared.json").write_text(json.dumps(row))
        code, value, _kind = self.request()
        self.assertEqual(code, 400)
        self.assertIn("source hash differs", value["error"])

    def test_stored_viewer_mask_bytes_invalidate_ready_result(self):
        row = self.stored_viewer()
        def run(directory, _photo, _sidecar):
            (directory / "inspection.json").write_text('{"status":"ready","candidates":[]}')
        with mock.patch.object(PI, "_run", side_effect=run):
            self.request("&start=1")
            for thread in PI._JOBS.values():
                thread.join(5)
            self.assertEqual(self.request()[1]["status"], "ready")
        Image.new("L", (10,20), 0).save(row["label"])
        self.assertEqual(self.request()[1]["status"], "idle")

    def test_missing_full_gallery_is_an_explicit_error(self):
        (self.evidence / "gallery.json").unlink()
        code, data, _kind = self.request("&start=1")
        self.assertEqual(code, 503)
        self.assertIn("not available", data["error"])

    def test_missing_cached_masks_make_no_model_request(self):
        photo = types.SimpleNamespace(path=str(self.photo), image=Image.new("RGB", (40, 30), "white"))
        target = self.root / "masks"
        target.mkdir()
        with mock.patch.object(run_steps, "_cut", return_value=(None,None,"no cached mask",None)) as cut:
            with self.assertRaisesRegex(ValueError, "standard bottle cut is absent"):
                PI._sidecar(photo, {}, target)
        self.assertEqual(cut.call_count, 2)

    def test_cached_full_label_uses_standard_model_coordinates(self):
        source = Image.new("RGBA", (40, 30), "gray")
        photo = types.SimpleNamespace(path=str(self.photo), image=source)
        target = self.root / "prepared"
        target.mkdir()
        (self.evidence / "gallery.json").write_text(json.dumps({"config": {"views": {"full": [
            {"step": "segment", "target": "package"}, {"step": "remove_background"},
            {"step": "white_background"}, {"step": "resize", "max_size": 10, "upscale": False, "aspect": "keep"}]}}}))
        package = Image.new("RGBA", (10, 20), "gray")
        label = Image.new("RGBA", (8, 10), "white")
        with mock.patch.object(run_steps, "_cut", side_effect=[([10, 0, 20, 20], package, None, None),
                                                            ([11, 5, 19, 15], label, None, None)]):
            row = json.loads(PI._sidecar(photo, {}, target).read_text())
        with Image.open(row["input"]) as image:
            self.assertEqual(image.size, (5, 10))
        with Image.open(row["label"]) as mask:
            self.assertEqual(mask.size, (5, 10))
            self.assertIsNotNone(mask.getbbox())
        self.assertEqual(row["package_box"], [10, 0, 20, 20])
        self.assertEqual(row["label_source"], "cached full-label cut")


if __name__ == "__main__":
    unittest.main()
