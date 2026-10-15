"""Opt-in main-label retrieval with local, confidence-checked variant text.

The supplementary index never replaces standard bottle or label vectors. Its records
carry both their own input hash and the standard embedding hash they were derived
from; changed catalogue sources cannot silently reuse old main-label vectors.
"""
import argparse
import collections
import copy
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
from contextlib import closing
from datetime import datetime
from unittest.mock import patch

import numpy as np

import alternatives
import build_embeddings
import derive
import embeddings
import label_ocr
import variant_attributes
import wine_terms

VERSION = "main label mask v1"
DEFAULTS = {"index": None, "verify_text": False, "window": 10, "min_confidence": 70.0,
            "ocr": "tesseract"}
RULE = "largest accepted mask on the main bottle; off-bottle labels excluded; other label masks remain separate"
CUTOFF = datetime.fromisoformat("2026-09-28T12:00:00+03:00").timestamp()


def check_options(raw):
    if not isinstance(raw, dict) or set(raw) - set(DEFAULTS):
        raise embeddings.ConfigError("main_label MUST hold index, verify_text, window, min_confidence, ocr")
    out = dict(DEFAULTS, **raw)
    if not isinstance(out["index"], str) or not embeddings.NAME_RE.fullmatch(out["index"]):
        raise embeddings.ConfigError("main_label.index MUST name a supplementary index")
    if not isinstance(out["verify_text"], bool):
        raise embeddings.ConfigError("main_label.verify_text MUST be boolean")
    if out["ocr"] not in ("tesseract", "paddleocr"):
        raise embeddings.ConfigError("main_label.ocr MUST be tesseract or paddleocr")
    if isinstance(out["window"], bool) or not isinstance(out["window"], int) or out["window"] < 2:
        raise embeddings.ConfigError("main_label.window MUST be an integer >= 2")
    confidence = out["min_confidence"]
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 100:
        raise embeddings.ConfigError("main_label.min_confidence MUST be between 0 and 100")
    return out


def cut_of(image, instances, *, on_main_bottle=True):
    main = alternatives.label_instance(instances, on_main_bottle=on_main_bottle)
    if main is None:
        return None
    masked, box = alternatives.label_cut(image, main)
    return "seg", masked, box


def normalized(text):
    return variant_attributes.normalized(text)


def sugar(text):
    return variant_attributes.sugar(text)


def observed_sugar(words, minimum):
    values, _ = variant_attributes.observed(words, minimum)
    return (values["sugar"] or [None])[0]


class TextReader:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.command = shutil.which("tesseract")
        if not self.command:
            raise embeddings.ConfigError("main-label text verification requires local tesseract rus+eng")

    def read(self, data):
        digest = hashlib.sha256(data).hexdigest()
        self.directory.mkdir(parents=True, exist_ok=True)
        cached = self.directory / (digest + ".json")
        try:
            answer = json.loads(cached.read_text())
            if answer.get("version") == 1:
                return answer["words"]
        except (OSError, ValueError, KeyError):
            pass
        image = self.directory / (digest + ".png")
        embeddings.write_atomic(str(image), data)
        process = subprocess.run([self.command, str(image), "stdout", "-l", "rus+eng",
                                  "--psm", "11", "tsv"], capture_output=True, text=True,
                                 timeout=30, check=False)
        if process.returncode:
            raise RuntimeError("local label OCR failed: " + process.stderr.strip()[:300])
        words = []
        for row in csv.DictReader(io.StringIO(process.stdout), delimiter="\t"):
            text = (row.get("text") or "").strip()
            confidence = float(row.get("conf") or -1)
            if text and confidence >= 0:
                words.append({"text": text, "confidence": round(confidence, 2)})
        embeddings.write_atomic(str(cached), json.dumps({"version": 1, "words": words},
                                                       ensure_ascii=False).encode())
        return words


class PaddleTextReader:
    """Run the pinned local CPU worker, with cache identity separate from Tesseract."""
    def __init__(self, directory):
        self.directory = Path(directory)
        if not label_ocr.PYTHON.is_file():
            raise embeddings.ConfigError("main-label PaddleOCR requires the separate local CPU environment")
        self.identity = dict(label_ocr.IDENTITY)

    @staticmethod
    def _words(words):
        if not isinstance(words, list):
            raise ValueError("local PaddleOCR returned invalid lines")
        for word in words:
            if not isinstance(word, dict):
                raise ValueError("local PaddleOCR returned invalid line")
            confidence = word.get("confidence")
            if (not isinstance(word.get("text"), str) or isinstance(confidence, bool)
                    or not isinstance(confidence, (int, float))
                    or not math.isfinite(confidence) or not 0 <= confidence <= 100):
                raise ValueError("local PaddleOCR returned invalid text or confidence")
        return words

    def read(self, data):
        digest = hashlib.sha256(data).hexdigest()
        version = hashlib.sha256(json.dumps(self.identity, sort_keys=True).encode()).hexdigest()[:16]
        self.directory.mkdir(parents=True, exist_ok=True)
        cached = self.directory / (digest + "-" + version + ".json")
        try:
            answer = json.loads(cached.read_text())
            if (isinstance(answer, dict) and answer.get("identity") == self.identity
                    and answer.get("sha256") == digest):
                return self._words(answer["words"])
        except (OSError, ValueError, KeyError):
            pass
        image = self.directory / (digest + ".png")
        embeddings.write_atomic(str(image), data)
        process = subprocess.run([str(label_ocr.PYTHON), str(Path(label_ocr.__file__)),
                                  str(image), "--model-root", str(label_ocr.MODEL_ROOT)],
                                 capture_output=True, text=True, timeout=90, check=False)
        if process.returncode:
            raise RuntimeError("local PaddleOCR failed: " + process.stderr.strip()[-500:])
        answer = json.loads(process.stdout)
        images = answer.get("images") if isinstance(answer, dict) else None
        if (not isinstance(answer, dict) or answer.get("identity") != self.identity
                or not isinstance(images, list) or len(images) != 1):
            raise RuntimeError("local PaddleOCR returned another model or image count")
        item = images[0]
        if not isinstance(item, dict) or item.get("sha256") != digest:
            raise RuntimeError("local PaddleOCR returned another input")
        words = self._words(item.get("words"))
        embeddings.write_atomic(str(cached), json.dumps(dict(item, identity=self.identity),
                                                       ensure_ascii=False).encode())
        return words


def verify(candidates, words, catalog, options):
    """Verify distinguishing attributes without changing visual scores."""
    return variant_attributes.verify(candidates, words, catalog, options)


def focused_catalogue(base, directory):
    index = embeddings.read_index(str(directory)) or {}
    if index.get("label_preparation") != VERSION:
        raise embeddings.ConfigError("build the main-label supplementary index first")
    vectors = embeddings.read_vectors(str(directory), index)
    if vectors is None or vectors.shape[1] != base.dim:
        raise embeddings.ConfigError("main-label index has no compatible vectors")
    by_source = {r["source_sha256"]: r for r in index["items"]}
    positions, numbers, items = [], [], []
    for item, number in zip(base.items.get("label", []), base.views["label"][1]):
        record = by_source.get(item["sha256"])
        if not record or record.get("base_embedding_hash") != item["embedding_hash"]:
            raise embeddings.ConfigError("main-label index is incomplete or stale; rebuild it")
        positions.append(record["row"])
        numbers.append(number)
        items.append(dict(item, embedding_hash=record["embedding_hash"]))
    result = copy.copy(base)
    result.views = dict(base.views, label=(np.asarray(vectors[positions], dtype=np.float32),
                                         np.asarray(numbers, dtype=np.int64)))
    result.items = dict(base.items, label=items)
    result.angles = {k: v for k, v in base.angles.items() if k != "label"}
    result.rows_of = dict(base.rows_of, label=collections.defaultdict(list))
    for pos, number in enumerate(numbers):
        result.rows_of["label"][number].append(pos)
    result.state = dict(base.state, main_label_index=directory.name,
                        main_label_built_at=index.get("updated_at"))
    return result


def configure(backend, options, db_path):
    import competitor_steps
    directory = Path(embeddings.entry_dir(db_path, options["index"]))
    backend.catalogue = focused_catalogue(backend.catalogue, directory)
    backend.label_focus = True
    backend.spec["main_label"] = dict(options)
    backend.spec["sam3"].update(label_focus="main", label=RULE)
    backend.spec["view_indexes"] = {"label": options["index"], "full": backend.embedding.name}
    if options["verify_text"]:
        backend.spec["ocr_normalization"] = dict(wine_terms.IDENTITY)
        backend.spec["ocr_verification"] = {"ranking_policy": variant_attributes.RANKING_POLICY}
        paddle = options.get("ocr") == "paddleocr"
        reader = (PaddleTextReader(directory / "ocr-cache-paddleocr") if paddle else
                  TextReader(directory / "ocr-cache"))
        catalog = competitor_steps.load_catalog(db_path)

        def verifier(candidates, data, trace):
            with trace.step("label-text") as step:
                if data is None:
                    step["out"] = {"applied": False, "reason": "no_usable_main_label"}
                    return candidates
                try:
                    answer, evidence = verify(candidates, reader.read(data), catalog, options)
                    if paddle:
                        evidence["ocr"] = reader.identity
                    step["out"] = evidence
                    return answer
                except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
                    step["out"] = {"applied": False, "reason": "text_reader_failed", "error": str(exc)}
                    return candidates
        backend.label_verifier = verifier
    return backend


def cached_instances(image):
    """Historical PNG compression affects SAM3 cache keys; this sends no requests."""
    import embedding_run
    client = embedding_run.CachedSam3()
    try:
        for level in dict.fromkeys((derive.PNG_COMPRESS_LEVEL, 6)):
            try:
                with patch.object(derive, "PNG_COMPRESS_LEVEL", level):
                    return client.instances(image, alternatives.DETECT_TEXTS)[0]
            except derive.Sam3Unavailable:
                continue
        raise derive.Sam3Unavailable("no cached SAM3 detection for this catalogue image")
    finally:
        client.session.close()


def prepare(config, base_name, name):
    """Prepare identical query/reference rules, without any network or DB writes."""
    import embedding_run
    settings = embeddings.load_settings(config)
    entry = settings.find(base_name)
    root = Path(embeddings.entry_dir(settings.db_path, base_name))
    target = Path(embeddings.entry_dir(settings.db_path, name))
    index = embeddings.read_index(str(root))
    vectors = embeddings.read_vectors(str(root), index)
    with closing(embeddings.open_database(settings.db_path)) as conn:
        _, sources = embeddings.read_inputs(conn, settings.db_path)
        manual = {r[0] for r in conn.execute("SELECT source_sha256 FROM image_derivative "
                    "WHERE kind='label' AND settings LIKE ?", (derive.MANUAL_PREFIX + "%",))}
        # The legacy rule returned method=seg only for exactly one accepted label.
        # Its output is already the main mask; multi-label legacy outputs were crop.
        single = {r[0] for r in conn.execute("SELECT source_sha256 FROM image_derivative "
                    "WHERE kind='label' AND method='seg' AND settings=?",
                    (alternatives.LEGACY_SETTINGS_LABEL,))}
    planned = embeddings.plan_items(entry, sources)
    states = embeddings.item_status(planned, index, embeddings.image_names(str(root)))
    cases = []
    target.mkdir(parents=True, exist_ok=True)
    for key, (state, record) in states.items():
        if state != "current" or key[1] != "label":
            continue
        source = sources[key[0]]
        data = (root / record["image"]).read_bytes()
        old_data = data
        if source["role"] == "full" and key[0] not in manual and key[0] not in single:
            image, _ = derive.open_image(source["path"])
            cut = cut_of(image, cached_instances(image))
            if cut is None:
                raise embeddings.ConfigError("no accepted main label for " + key[0])
            _, masked, box = cut
            prepared, _ = embedding_run.view_input(image, entry.views["label"],
                                                  {"label": (box, masked)})
            data = embeddings.png_bytes(prepared)
        destination = target / record["image"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        embeddings.write_atomic(str(destination), data)
        os.utime(destination, (CUTOFF, CUTOFF))
        with derive.open_image(destination)[0] as prepared:
            size = list(prepared.size)
        digest = hashlib.sha256(data).hexdigest()
        case = {"source_sha256": key[0], "view": "label", "role": source["role"],
                "base_embedding_hash": record["embedding_hash"], "image": record["image"],
                "input_sha256": digest, "width": size[0], "height": size[1],
                "embedding_hash": embeddings.sha256_json({"base": record["embedding_hash"],
                                            "preparation": VERSION, "input_sha256": digest}),
                "row": len(cases), "base_row": record["row"], "changed": data != old_data}
        cases.append(case)
        if len(cases) % 500 == 0:
            print(json.dumps({"prepared": len(cases)}), flush=True)
    np.save(target / "base-label-vectors.npy", np.asarray(vectors[[c["base_row"] for c in cases]]),
            allow_pickle=False)
    manifest = {"name": name, "base_embedding": base_name, "label_preparation": VERSION,
                "dim": int(vectors.shape[1]), "items": cases, "config": index["config"],
                "base_index_sha256": hashlib.sha256((root / "index.json").read_bytes()).hexdigest()}
    embeddings.write_atomic(str(target / "prepare.json"), json.dumps(manifest, indent=2).encode())
    print(json.dumps({"prepared": len(cases), "changed": sum(c["changed"] for c in cases),
                      "directory": str(target)}), flush=True)


def build(config, name):
    """Compute only changed inputs; publish only the supplementary local index."""
    settings = embeddings.load_settings(config)
    directory = Path(embeddings.entry_dir(settings.db_path, name))
    manifest = json.loads((directory / "prepare.json").read_text())
    entry = settings.find(manifest["base_embedding"])
    root = Path(embeddings.entry_dir(settings.db_path, entry.name))
    expected = manifest["base_index_sha256"]
    if hashlib.sha256((root / "index.json").read_bytes()).hexdigest() != expected:
        raise embeddings.ConfigError("standard index changed during preparation; prepare again")
    matrix = np.load(directory / "base-label-vectors.npy", allow_pickle=False)
    model = build_embeddings.make_backend(entry)
    changed = [c for c in manifest["items"] if c["changed"]]
    for offset in range(0, len(changed), 30):
        batch = changed[offset:offset + 30]
        pictures = []
        for case in batch:
            path = directory / case["image"]
            data = path.read_bytes()
            assert path.stat().st_mtime <= CUTOFF
            assert hashlib.sha256(data).hexdigest() == case["input_sha256"]
            pictures.append(data)
        got = np.asarray(model.embed(pictures), dtype=np.float32)
        if got.shape != (len(batch), matrix.shape[1]) or not np.isfinite(got).all():
            raise embeddings.ConfigError("invalid supplementary embedding response")
        norms = np.linalg.norm(got, axis=1, keepdims=True)
        if (norms <= 0).any():
            raise embeddings.ConfigError("zero supplementary embedding")
        matrix[[c["row"] for c in batch]] = got / norms
        print(json.dumps({"embedded": min(offset + len(batch), len(changed)),
                          "total": len(changed)}), flush=True)
    if hashlib.sha256((root / "index.json").read_bytes()).hexdigest() != expected:
        raise embeddings.ConfigError("standard index changed before publication; prepare again")
    index = dict(manifest, updated_at=embeddings.now())
    embeddings.write_checkpoint(str(directory), index, matrix)
    print(json.dumps({"published": len(matrix), "new_vectors": len(changed),
                      "standard_index_unchanged": True}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=embeddings.CONFIG_PATH)
    parser.add_argument("--base", default="gx10-siglip2-so400m-patch16-naflex-p512-rot5")
    parser.add_argument("--index", default="gx10-siglip2-so400m-patch16-naflex-p512-rot5-main-label")
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--build", action="store_true")
    args = parser.parse_args()
    if args.prepare:
        prepare(args.config, args.base, args.index)
    if args.build:
        build(args.config, args.index)


if __name__ == "__main__":
    main()
