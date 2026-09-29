import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
# ROOT is svoe-vino-lab/workbench; svoe-vino-matcher is a sibling of svoe-vino-lab.
WORKSPACE = ROOT.parent.parent
SPEC = importlib.util.spec_from_file_location(
    "run_model_inputs_for_tests", ROOT / "scripts" / "run_model_inputs.py")
model_inputs = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(model_inputs)


def pipeline(name, kind, **values):
    raw = {"kind": kind, **values}
    return SimpleNamespace(
        name=name,
        kind=kind,
        label=values.get("label", name),
        path=values.get("path", ""),
        settings=values.get("settings", {}),
        members=values.get("members", []),
        raw=raw,
    )


class RunModelInputsTests(unittest.TestCase):
    def test_config_selection_uses_backend_port(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config.yaml").write_text(
                "default_pipeline: p\npipelines: {p: {kind: embed}}\n"
                "server: {port: 8158}\n", encoding="utf-8")
            (root / "config.label.yaml").write_text(
                "default_pipeline: p\npipelines: {p: {kind: embed}}\n"
                "server: {port: 8164}\n", encoding="utf-8")
            path, name = model_inputs.find_matcher_config(
                root, "http://127.0.0.1:8164/v1/pipelines/p/predict")
        self.assertEqual("config.label.yaml", path.name)
        self.assertEqual("p", name)

    def test_embedding_preview_has_model_input_size(self):
        spec = pipeline(
            "siglip", "embed", path="siglip2",
            settings={"repo": "example/model", "input_size": 448})
        cfg = SimpleNamespace(
            pipelines={"siglip": spec}, resize_mode="squash",
            background=(255, 255, 255), source=WORKSPACE / "svoe-vino-matcher/config.yaml")
        collector = model_inputs._Collector(
            cfg, Image.new("RGB", (30, 60), "red"), [],
            WORKSPACE / "svoe-vino-matcher")
        collector.collect("siglip")
        self.assertEqual(1, len(collector.items))
        self.assertEqual(["Embedding"], collector.items[0]["uses"])
        self.assertEqual((448, 448),
                         (collector.items[0]["width"], collector.items[0]["height"]))

    def test_cluster_preview_marks_the_vlm_input(self):
        base = pipeline(
            "photo", "embed", path="gateway", settings={"model": "siglip2"})
        rule = pipeline(
            "rules", "cluster_rules", base={"pipeline": "photo"},
            crop={"pipeline": "photo"}, vlm={"model": "qwen", "side": 120})
        cfg = SimpleNamespace(
            pipelines={"photo": base, "rules": rule}, resize_mode="squash",
            background=(255, 255, 255), source=WORKSPACE / "svoe-vino-matcher/config.yaml")
        candidates = [{"slug": "wine", "score": 0.9,
                       "explain": {"kind": "cluster_rules"}}]
        collector = model_inputs._Collector(
            cfg, Image.new("RGB", (20, 40), "blue"), candidates,
            WORKSPACE / "svoe-vino-matcher")
        collector.collect("rules")
        vlm = next(item for item in collector.items if "VLM" in item["uses"])
        self.assertEqual("qwen", vlm["model"])
        self.assertEqual((60, 120), (vlm["width"], vlm["height"]))

    def test_barcode_hit_does_not_report_an_embedding_input(self):
        base = pipeline(
            "siglip", "embed", path="siglip2", settings={"input_size": 448})
        barcode = pipeline(
            "barcode", "barcode", base={"pipeline": "siglip"})
        cfg = SimpleNamespace(
            pipelines={"siglip": base, "barcode": barcode}, resize_mode="squash",
            background=(255, 255, 255), source=WORKSPACE / "svoe-vino-matcher/config.yaml")
        collector = model_inputs._Collector(
            cfg, Image.new("RGB", (20, 40), "green"),
            [{"slug": "wine", "score": 1.0}], WORKSPACE / "svoe-vino-matcher")
        collector.collect("barcode")
        self.assertEqual([], collector.items)
        self.assertIn("No embedding model ran.", collector.notes[0])


if __name__ == "__main__":
    unittest.main()
