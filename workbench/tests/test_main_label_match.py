"""Main-label isolation, text ambiguity, and stale-reference safeguards."""
import base64
import io
from types import SimpleNamespace

import numpy as np
from PIL import Image, ImageDraw
import unittest
from unittest.mock import patch
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))

import embeddings
import main_label_match as main


def detection(box, area, size=(100, 200)):
    mask = Image.new("L", size)
    ImageDraw.Draw(mask).rectangle(box, fill=255)
    stream = io.BytesIO()
    mask.save(stream, format="PNG")
    return {"label": "label", "score": 0.99, "area": area, "box": box,
            "mask_png_b64": base64.b64encode(stream.getvalue()).decode()}


def test_main_cut_excludes_separate_emblem_and_gap():
    image = Image.new("RGB", (100, 200), "red")
    instances = [detection((10, 100, 90, 180), 6400), detection((20, 10, 80, 40), 1800)]
    method, cut, box = main.cut_of(image, instances)
    assert method == "seg"
    assert box[1] > 80 and box[3] < 195
    assert cut.height < 110
    assert main.cut_of(image, []) is None


def test_explicit_sugar_words():
    cases = [("БРЮТ 2016", "brut"), ("ЭКСТРА БРЮТ", "extra_brut"),
             ("extra-brut", "extra_brut"), ("Полусладкое", "semi_sweet"),
             ("Полусухое", "semi_dry"), ("сухое", "dry"),
             ("BRUT NATURE", "brut_nature"), ("1870 Victor Dravigny", None),
             ("Брют полусладкое", None)]
    for text, expected in cases:
        assert main.sugar(text) == expected, text


def test_uncertain_qualifier_does_not_turn_extra_brut_into_brut():
    words = [{"text": "ЭКСТРА", "confidence": 20}, {"text": "БРЮТ", "confidence": 99}]
    assert main.observed_sugar(words, 70) is None
    assert main.observed_sugar([{"text": "БРЮТ", "confidence": 20}], 70) is None


def candidates():
    return [{"slug": "semi", "score": .94, "rank": 1},
            {"slug": "extra", "score": .93, "rank": 2},
            {"slug": "brut", "score": .91, "rank": 3},
            {"slug": "another_brut", "score": .90, "rank": 4}]


CATALOG = {"semi": {"name": "Полусладкое"}, "extra": {"name": "Экстра брют"},
           "brut": {"name": "Брют"}, "another_brut": {"name": "Брют"}}
OPTIONS = main.check_options({"index": "experiment", "verify_text": True})


def test_text_checks_variant_without_average_or_new_candidate():
    original = candidates()
    result, trace = main.verify(original, [{"text": "БРЮТ", "confidence": 99}], CATALOG, OPTIONS)
    assert [c["slug"] for c in result] == ["brut", "another_brut", "semi", "extra"]
    assert {c["slug"]: c["score"] for c in result} == {c["slug"]: c["score"] for c in original}
    assert original == candidates()
    assert trace["applied"] and trace["observed_sugar"] == "brut"


def test_unreadable_or_conflicting_text_keeps_order():
    for words in [[], [{"text": "БРЮТ", "confidence": 20}],
                  [{"text": "БРЮТ", "confidence": 99}, {"text": "ПОЛУСЛАДКОЕ", "confidence": 99}]]:
        result, trace = main.verify(candidates(), words, CATALOG, OPTIONS)
        assert result == candidates()
        assert not trace["applied"]


def test_no_match_and_absent_catalogue_attribute_keep_order():
    result, trace = main.verify(candidates(), [{"text": "сухое", "confidence": 99}], CATALOG, OPTIONS)
    assert result == candidates() and not trace["applied"]
    result, trace = main.verify(candidates(), [{"text": "БРЮТ", "confidence": 99}], {}, OPTIONS)
    assert result == candidates() and not trace["applied"]


def test_stale_supplementary_source_is_rejected():
    base = SimpleNamespace(dim=2, items={"label": [{"sha256": "a", "embedding_hash": "new"}]},
                           views={"label": (np.ones((1, 2)), np.array([0]))})
    index = {"label_preparation": main.VERSION,
             "items": [{"source_sha256": "a", "base_embedding_hash": "old", "row": 0}]}
    with patch.object(embeddings, "read_index", return_value=index), \
            patch.object(embeddings, "read_vectors", return_value=np.ones((1, 2))):
        with unittest.TestCase().assertRaisesRegex(embeddings.ConfigError, "stale"):
            main.focused_catalogue(base, Path("unused"))


def test_bad_options():
    for option in [{"index": "../x"}, {"index": "x", "window": True},
                   {"index": "x", "min_confidence": float("nan")}, {"index": "x", "verify_text": "yes"}]:
        with unittest.TestCase().assertRaises(embeddings.ConfigError):
            main.check_options(option)


def test_focus_preserves_bottle_vectors_and_base_object():
    full = (np.array([[1., 0.]], dtype=np.float32), np.array([0]))
    old = np.array([[0., 1.]], dtype=np.float32)
    base = SimpleNamespace(dim=2, items={"label": [{"sha256": "a", "embedding_hash": "base"}],
                                       "full": []},
        views={"label": (old, np.array([0])), "full": full}, angles={},
        rows_of={"label": {0: [0]}, "full": {0: [0]}}, state={})
    index = {"label_preparation": main.VERSION, "items": [{"source_sha256": "a",
        "base_embedding_hash": "base", "embedding_hash": "focus", "row": 0}]}
    fresh = np.array([[.6, .8]], dtype=np.float32)
    with patch.object(embeddings, "read_index", return_value=index), \
            patch.object(embeddings, "read_vectors", return_value=fresh):
        focus = main.focused_catalogue(base, Path("unused"))
    assert focus.views["full"] is full
    assert focus.items["label"][0]["embedding_hash"] == "focus"
    assert base.items["label"][0]["embedding_hash"] == "base"
    assert np.array_equal(base.views["label"][0], old)
    assert np.array_equal(focus.views["label"][0], fresh)


def test_query_and_historical_reconstruction_use_recorded_focus():
    import embedding_run
    import tempfile
    image = Image.new("RGB", (100, 200), "red")
    instances = [detection((10, 100, 90, 180), 6400), detection((20, 10, 80, 40), 1800)]
    segmenter = SimpleNamespace(instances=lambda *_: (instances, 1))
    steps = [{"step": "segment", "target": "label"}, {"step": "white_background"}]
    views = {"label": steps}
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "input.png"
        image.save(path)
        with patch.object(embedding_run, "CachedSam3", return_value=segmenter):
            main_inputs, _ = embedding_run.query_inputs(image, views, segmenter, label_focus=True)
            body = embedding_run.model_inputs({"views": views,
                "sam3": {"label_focus": "main", "label_mask_union": True}}, str(path))
            union = embedding_run.model_inputs({"views": views,
                "sam3": {"label_mask_union": True}}, str(path))
    assert main_inputs["label"].height < 110
    assert body["inputs"][0]["height"] == main_inputs["label"].height
    assert union["inputs"][0]["height"] > body["inputs"][0]["height"]


def test_saved_label_selection_replays_old_price_tag_and_new_real_label():
    import embedding_run
    import tempfile
    image = Image.new("RGB", (100, 200), "red")
    instances = [{"label": "bottle", "box": [10, 0, 90, 125], "score": .9},
                 detection((12, 8, 88, 124), 8816),
                 detection((0, 150, 100, 185), 3500)]
    segmenter = SimpleNamespace(instances=lambda *_: (instances, 1))
    steps = [{"step": "segment", "target": "label"}, {"step": "remove_background"},
             {"step": "white_background"}]
    spec = {"views": {"label": steps}, "sam3": {"label_focus": "main", "label_mask_union": True}}
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "input.png"
        image.save(path)
        with patch.object(embedding_run, "CachedSam3", return_value=segmenter):
            old = embedding_run.model_inputs(spec, str(path))
            current = embedding_run.model_inputs(dict(spec, sam3=dict(spec["sam3"],
                                                     label_selection_version=2)), str(path))
    assert not old["notes"] and not current["notes"]
    assert old["inputs"][0]["height"] < 60
    assert current["inputs"][0]["height"] > 100
    assert old["inputs"][0]["sha256"] != current["inputs"][0]["sha256"]


def test_candidate_details_use_each_recorded_view_index():
    import embedding_run
    import json
    import tempfile
    digest = "a" * 64
    with tempfile.TemporaryDirectory() as root:
        db_path = str(Path(root) / "catalog.sqlite3")
        for name, records in [("standard", [("full", "bottle", 80), ("label", "old", 120)]),
                              ("focused", [("label", "main", 60)])]:
            directory = Path(embeddings.entry_dir(db_path, name))
            (directory / "images").mkdir(parents=True)
            items = []
            for view, tag, width in records:
                items.append({"source_sha256": digest, "view": view,
                              "embedding_hash": tag, "width": width, "height": 100})
                (directory / "images" / embeddings.image_name(digest, view)).write_bytes(b"image")
            (directory / "index.json").write_text(json.dumps({"items": items}))
        spec = {"embedding": "standard", "views": {"full": [], "label": []},
                "view_indexes": {"full": "standard", "label": "focused"}}
        cand = {"score": .95, "full": .9, "label": .95,
                "items": [{"sha256": digest, "view": "full", "embedding_hash": "bottle", "cosine": .9},
                          {"sha256": digest, "view": "label", "embedding_hash": "main", "cosine": .95}]}
        body = embedding_run.candidate_items(spec, cand, db_path)
        full, label = body["items"]
        assert full["state"] == label["state"] == "same"
        assert full["url"].startswith("/embeddings/standard/")
        assert label["url"].startswith("/embeddings/focused/")
        assert full["width"] == 80 and label["width"] == 60
        assert not body["notes"]
        focused_index = Path(embeddings.entry_dir(db_path, "focused")) / "index.json"
        focused_index.write_text(json.dumps({"items": [{"source_sha256": digest,
            "view": "label", "embedding_hash": "replacement", "width": 60, "height": 100}]}))
        changed = embedding_run.candidate_items(spec, cand, db_path)
        assert changed["items"][0]["state"] == "same"
        assert changed["items"][1]["state"] == "changed"
        assert changed["items"][1]["url"] is None


def test_missing_supplement_does_not_use_standard_label_preview():
    import embedding_run
    import json
    import tempfile
    digest = "b" * 64
    with tempfile.TemporaryDirectory() as root:
        db_path = str(Path(root) / "catalog.sqlite3")
        directory = Path(embeddings.entry_dir(db_path, "standard"))
        (directory / "images").mkdir(parents=True)
        (directory / "images" / embeddings.image_name(digest, "label")).write_bytes(b"image")
        (directory / "index.json").write_text(json.dumps({"items": [{"source_sha256": digest,
            "view": "label", "embedding_hash": "main", "width": 100, "height": 100}]}))
        body = embedding_run.candidate_items({"embedding": "standard", "views": {"label": []},
                "view_indexes": {"label": "missing"}},
            {"label": .95, "items": [{"sha256": digest, "view": "label", "embedding_hash": "main", "cosine": .95}]}, db_path)
        assert body["items"][0]["state"] == "gone" and body["items"][0]["url"] is None


def test_ocr_option_defaults_and_invalid_engine():
    assert main.check_options({"index": "experiment"})["ocr"] == "tesseract"
    assert main.check_options({"index": "experiment", "ocr": "paddleocr"})["ocr"] == "paddleocr"
    with unittest.TestCase().assertRaises(embeddings.ConfigError):
        main.check_options({"index": "experiment", "ocr": "unknown"})


def test_paddle_reader_reuses_only_its_own_model_and_input_cache():
    import hashlib
    import json
    import tempfile
    data = b"prepared image"
    words = [{"text": "БРЮТ", "confidence": 97.2}]
    identity = main.label_ocr.IDENTITY
    response = {"identity": identity, "images": [{"sha256": hashlib.sha256(data).hexdigest(), "words": words}]}
    with tempfile.TemporaryDirectory() as directory:
        with patch.object(Path, "is_file", return_value=True):
            reader = main.PaddleTextReader(directory)
        done = SimpleNamespace(returncode=0, stdout=json.dumps(response), stderr="")
        with patch.object(main.subprocess, "run", return_value=done) as run:
            assert reader.read(data) == words
            assert reader.read(data) == words
            assert run.call_count == 1
            args = run.call_args.args[0]
            assert args[0] == str(main.label_ocr.PYTHON) and "--bootstrap" not in args
        # A different model identity must never reuse the prior text.
        reader.identity = dict(identity, recognizer="other-model")
        with patch.object(main.subprocess, "run", return_value=done), \
                unittest.TestCase().assertRaisesRegex(RuntimeError, "another model"):
            reader.read(data)


def test_paddle_reader_rejects_another_input_and_malformed_confidence():
    import json
    import tempfile
    identity = main.label_ocr.IDENTITY
    with tempfile.TemporaryDirectory() as directory:
        with patch.object(Path, "is_file", return_value=True):
            reader = main.PaddleTextReader(directory)
        done = SimpleNamespace(returncode=0, stdout=json.dumps({"identity": identity,
            "images": [{"sha256": "different", "words": []}]}), stderr="")
        with patch.object(main.subprocess, "run", return_value=done), \
                unittest.TestCase().assertRaisesRegex(RuntimeError, "another input"):
            reader.read(b"image")
        for words in (None, [{}], [{"text": "БРЮТ", "confidence": float("nan")}],
                      [{"text": "БРЮТ", "confidence": True}]):
            with unittest.TestCase().assertRaises(ValueError):
                reader._words(words)


def test_both_reader_caches_use_shared_normalization_without_rewriting_raw_text():
    import hashlib
    import json
    import tempfile
    data = b"same cached input"
    digest = hashlib.sha256(data).hexdigest()
    words = [{"text": "Са8иньо бланк", "confidence": 98}]
    rows = [{"slug": "merlot", "rank": 1, "score": .95},
            {"slug": "sauvignon", "rank": 2, "score": .94}]
    catalogue = {"merlot": {"grapes": "Мерло"}, "sauvignon": {"grapes": "Совиньон Блан"}}
    with tempfile.TemporaryDirectory() as directory:
        with patch.object(main.shutil, "which", return_value="tesseract"), \
                patch.object(Path, "is_file", return_value=True):
            readers = [main.TextReader(Path(directory) / "tesseract"),
                       main.PaddleTextReader(Path(directory) / "paddle")]
        for reader in readers:
            reader.directory.mkdir()
            if isinstance(reader, main.PaddleTextReader):
                version = hashlib.sha256(json.dumps(reader.identity, sort_keys=True).encode()).hexdigest()[:16]
                path = reader.directory / (digest + "-" + version + ".json")
                path.write_text(json.dumps({"identity": reader.identity, "sha256": digest, "words": words}))
            else:
                path = reader.directory / (digest + ".json")
                path.write_text(json.dumps({"version": 1, "words": words}))
            before = path.read_bytes()
            with patch.object(main.subprocess, "run", side_effect=AssertionError("OCR cache must be reused")):
                answer, evidence = main.verify(rows, reader.read(data), catalogue, OPTIONS)
            assert answer[0]["slug"] == "sauvignon"
            assert evidence["words"] == words
            assert evidence["normalization"]["text"] == "совиньон-блан"
            assert path.read_bytes() == before


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(unittest.FunctionTestCase(value) for name, value in list(globals().items())
                              if name.startswith("test_") and callable(value))
