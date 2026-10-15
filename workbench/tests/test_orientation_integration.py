"""Verify the optional pipeline and the query rotation step shown in Runs."""
from pathlib import Path
import copy
import json
import sys
import unittest
from unittest import mock

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / "pipeline"),
               str(Path(__file__).resolve().parent)]
import embedding_run
import embeddings
import main_scene
import pipelines
import run_steps
import test_pipelines as TP
import test_run_steps as TS


class OrientationOptionsTest(TP.LoadTest):
    def test_opt_in_requires_a_boolean(self):
        for value in (1, "true", None):
            entry = {"name":"upright","backend":"embedding","embedding":"gw",
                     "bottle_orientation":value}
            loaded = self.load(embeddings=[TP.GW],pipeline=[entry])
            self.assertIn("bottle_orientation MUST", loaded.entries[0][2])

    def test_opt_in_requires_a_masked_package_view(self):
        entry = {"name":"upright","backend":"embedding","embedding":"gw",
                 "bottle_orientation":True}
        loaded = self.load(embeddings=[TP.GW],pipeline=[entry])
        self.assertIn("masked full package", loaded.entries[0][2])

    def test_opt_in_pipeline_selects_v5_and_default_stays_v4(self):
        raw = {"name":"upright","backend":"embedding","embedding":"gw",
               "bottle_orientation":True}
        option = pipelines.Pipeline(raw)
        settings = mock.Mock();settings.find.return_value = mock.Mock()
        backend = mock.Mock(spec=[]);backend.spec = {};backend.output_top_k = 10
        with mock.patch.object(embeddings,"load_settings",return_value=settings), \
             mock.patch.object(embedding_run,"build_backend",return_value=backend) as build:
            embedding_run.build_pipeline_backend(option,"unused")
            self.assertEqual(build.call_args.kwargs["scene_selection"],5)
        self.assertEqual(main_scene.selector_version(True),4)


class RotationStepsTest(TS.StepsTest):
    def test_v5_steps_show_recorded_rotation_and_both_crops(self):
        directory, rows = self.run_set(scene_selection=5)
        row = rows["green/01.png"]
        status, body = self.steps(Path(directory).name,row["query_id"])
        self.assertEqual(status,200)
        step = next(p for p in self.all_steps(body) if p["id"]=="bottle-orientation")
        self.assertTrue(step["result"]["used_in_saved_embedding"])
        self.assertIsInstance(step["result"]["recorded_orientation"],dict)
        self.assertEqual(len(step["artifacts"]),2)
        self.assertIn("before model resize",step["settings"]["order"])
        self.assertFalse(step["result"]["direction_confident"])
        self.assertTrue(any("No clear neck" in n for n in step["notes"]))
        search = next(p for p in self.all_steps(body) if p["id"]=="search")
        self.assertNotIn("Query bottle rotation",search["group"])

    def test_old_run_preview_is_explicit_and_does_not_change_ranking(self):
        directory, rows = self.run_set(scene_selection=4)
        row = rows["green/01.png"]
        expected = copy.deepcopy(row["candidates"])
        original = run_steps._reconstruct_inputs
        def preview(*args,**kwargs):
            result = copy.deepcopy(original(*args,**kwargs))
            cut = result["cuts"]["package"]
            artifact = {k:cut[k] for k in ("src","width","height")}
            cut["orientation"] = {"used_in_run":False,"before":artifact,"after":artifact,
                "audit":{"applied":True,"angle_degrees":-45,"neck":"top",
                         "direction_confident":True,"neck_width_ratio":.4,
                         "mask_crop_iou_before":.3,"mask_crop_iou_after":.7,"crop_area_ratio":.4}}
            return result
        with mock.patch.object(run_steps,"_reconstruct_inputs",side_effect=preview):
            status, body = self.steps(Path(directory).name,row["query_id"])
        self.assertEqual(status,200)
        part = next(p for p in self.all_steps(body) if p["id"]=="bottle-orientation")
        self.assertIn("preview only",part["name"])
        self.assertFalse(part["result"]["used_in_saved_embedding"])
        self.assertEqual(part["state"],"skipped")
        self.assertTrue(any("does not change" in n for n in part["notes"]))
        saved = [json.loads(line) for line in (Path(directory)/"results.jsonl").read_text().splitlines()]
        self.assertEqual(next(r for r in saved if r["query_id"]==row["query_id"])["candidates"],expected)


if __name__ == "__main__":
    unittest.main()
