"""Local PaddleOCR worker, isolated from the lab's Python environment.

Only explicit bootstrap mode may download public model weights. Normal recognition
requires both local models and never selects a hosted inference engine.
"""
import argparse
import contextlib
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import time

SCHEMA = 1
DETECTOR = "PP-OCRv5_mobile_det"
RECOGNIZER = "eslav_PP-OCRv5_mobile_rec"
PACKAGES = {"paddleocr": "3.7.0", "paddlepaddle": "3.3.1", "paddlex": "3.7.2"}
ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "work" / "main-label-paddle"
PYTHON = RUNTIME / "venv" / "bin" / "python"
MODEL_ROOT = RUNTIME / "models"
IDENTITY = {"schema": SCHEMA, "engine": "paddleocr", "detector": DETECTOR,
            "recognizer": RECOGNIZER, "packages": PACKAGES,
            "confidence_unit": "recognition line score * 100"}


def words_of(result):
    """Keep complete recognized lines, native scores and their detected polygons."""
    texts, scores = result["rec_texts"], result["rec_scores"]
    polygons = result.get("rec_polys")
    if len(texts) != len(scores) or (polygons is not None and len(polygons) != len(texts)):
        raise ValueError("PaddleOCR text, confidence and polygon counts differ")
    words = []
    for position, (text, score) in enumerate(zip(texts, scores)):
        if not isinstance(text, str) or isinstance(score, bool):
            raise ValueError("invalid PaddleOCR text or confidence")
        score = float(score)
        if not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("invalid PaddleOCR confidence")
        if not text.strip():
            continue
        item = {"text": text.strip(), "confidence": round(score * 100, 2)}
        if polygons is not None:
            points = [[float(v) for v in point] for point in polygons[position]]
            if len(points) != 4 or any(len(p) != 2 for p in points):
                raise ValueError("invalid PaddleOCR polygon")
            if not all(math.isfinite(v) for p in points for v in p):
                raise ValueError("invalid PaddleOCR polygon")
            item["polygon"] = points
        words.append(item)
    return words


def recognize(paths, model_root=MODEL_ROOT, bootstrap=False):
    """Run CPU models on local files; bootstrap alone may fetch model weights."""
    model_root = Path(model_root).resolve()
    cache = model_root.parent / "cache"
    os.environ["PADDLE_PDX_CACHE_HOME"] = str(cache)
    os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
    os.environ["HF_HOME"] = str(cache / "huggingface")
    os.environ["MPLCONFIGDIR"] = str(cache / "matplotlib")
    from importlib.metadata import version

    for package, expected in PACKAGES.items():
        if version(package) != expected:
            raise RuntimeError("local PaddleOCR requires %s==%s" % (package, expected))
    from paddleocr import PaddleOCR

    dirs = {}
    for kind, name in (("text_detection", DETECTOR), ("text_recognition", RECOGNIZER)):
        directory = model_root / name
        if directory.is_dir():
            dirs[kind + "_model_dir"] = str(directory)
        elif not bootstrap:
            raise RuntimeError("local PaddleOCR model missing: %s" % directory)
    model = PaddleOCR(
        device="cpu",
        text_detection_model_name=DETECTOR, text_recognition_model_name=RECOGNIZER,
        use_doc_orientation_classify=False, use_doc_unwarping=False,
        use_textline_orientation=False, enable_mkldnn=False, cpu_threads=4,
        **dirs,
    )
    if bootstrap:
        model_root.mkdir(parents=True, exist_ok=True)
        for name in (DETECTOR, RECOGNIZER):
            destination = model_root / name
            if not destination.is_dir():
                shutil.copytree(cache / "official_models" / name, destination)
    answers = []
    for path in paths:
        path = Path(path)
        started = time.perf_counter()
        predicted = list(model.predict(str(path), text_rec_score_thresh=0.0))
        if len(predicted) != 1:
            raise RuntimeError("PaddleOCR must return one result per image")
        answers.append({"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "words": words_of(predicted[0]),
                        "inference_ms": round((time.perf_counter() - started) * 1000, 1)})
    return {"identity": IDENTITY, "images": answers}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", nargs="+")
    parser.add_argument("--model-root", default=str(MODEL_ROOT))
    parser.add_argument("--bootstrap", action="store_true")
    args = parser.parse_args()
    with contextlib.redirect_stdout(sys.stderr):
        answer = recognize(args.images, args.model_root, args.bootstrap)
    print(json.dumps(answer, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
