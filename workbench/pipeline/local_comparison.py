"""Live lab comparisons on a bottle shortlist or a local main-label catalogue.

This wrapper asks the normal bottle retriever for every current input. It never reads
historical query IDs, truth labels or saved rankings. Local caches contain only image
features, pair measurements and OCR words, identified by bytes and model contract.
"""
import atexit
import copy
from contextlib import nullcontext
import hashlib
import io
import json
import math
import os
from pathlib import Path
import select
import subprocess
import sys
import threading
import tempfile
import time

import numpy as np
from PIL import Image

import alternatives
import derive
import embeddings
import label_gate
import main_label_match
import wine_terms
import model_cache

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "work/local-comparison"
INDEX = "gx10-siglip2-so400m-patch16-naflex-p512-rot5-main-label"
LABEL_STEPS = [{"step": "segment", "target": "label"}, {"step": "remove_background"},
               {"step": "white_background"},
               {"step": "resize", "max_size": 1024, "aspect": "keep", "upscale": False}]
METHODS = ("bottle", "tesseract", "paddleocr", "lightglue-score", "superglue-score",
           "loftr-score", "dinov2-score", "dinov2-patch_score", "dinov3-score",
           "dinov3-patch_score", "lpips-score", "lpips-aligned_distance", "dists-score",
           "dists-aligned_distance", "siglip-main", "siglip-main-frozen",
           "siglip-label-gate", "siglip-main-tesseract", "siglip-gated-tesseract",
           "siglip-main-paddleocr", "siglip-gated-paddleocr")
DEFAULTS = {"method": None, "index": INDEX, "window": 10, "references": 2,
            "device": "mps", "min_confidence": 70.0, "gate": {}}
CUTOFF = main_label_match.CUTOFF


class LocalQueryModel:
    """Local p512 queries against the explicitly fixed, saved bottle catalogue."""
    def __init__(self, worker):
        self.worker = worker

    def embed(self, images):
        import build_embeddings
        vectors = []
        for data in images:
            digest = hashlib.sha256(data).hexdigest()
            path = RUNTIME / "bottle-inputs" / (digest + ".png")
            if not path.is_file() or sha(path) != digest:
                save(path, data)
            try:
                vector = self.worker.call("siglip-vector", {"path": str(path), "sha256": digest})["vector"]
            except (OSError, ValueError, RuntimeError) as exc:
                raise build_embeddings.BackendError("local query embedding failed: " + str(exc)) from exc
            vectors.append(vector)
        return np.asarray(vectors, np.float32)


def cached_segmenter():
    """Read historical SAM3 masks with either PNG encoding; no service request."""
    import embedding_run
    class Cached(embedding_run.CachedSam3):
        def _post(self, data, texts=derive.SAM3_TEXTS, return_masks=True):
            # Saved masks are fixed preprocessing inputs even in a fresh recognition run.
            params = {"threshold": str(derive.SAM3_THRESHOLD),
                      "mask_threshold": str(derive.SAM3_MASK_THRESHOLD),
                      "return_masks": "true" if return_masks else "false"}
            fields = model_cache.request_fields(self.endpoint + "/segment_multi",
                        derive.SAM3_MODEL, params, texts, [data])
            self._last.cached = False
            try:
                record = json.loads(Path(model_cache.path_of(fields)).read_text())
                if (isinstance(record, dict) and "answer" in record and
                        model_cache.canonical(record.get("request")) == model_cache.canonical(fields)):
                    self._last.cached = True
                    return record["answer"]
            except (OSError, ValueError, KeyError):
                pass
            raise derive.Sam3Unavailable("no saved segmentation input; no service request")

        def _sent_copy(self, image):
            data, scale = super()._sent_copy(image)
            compression = getattr(self, "compression", derive.PNG_COMPRESS_LEVEL)
            if compression != derive.PNG_COMPRESS_LEVEL:
                with Image.open(io.BytesIO(data)) as copy:
                    stream = io.BytesIO()
                    copy.save(stream, "PNG", compress_level=compression)
                data = stream.getvalue()
            return data, scale

        def instances(self, image, texts, masks=True):
            for compression in dict.fromkeys((derive.PNG_COMPRESS_LEVEL, 6)):
                self.compression = compression
                try:
                    return super().instances(image, texts, masks)
                except derive.Sam3Unavailable:
                    pass
            raise derive.Sam3Unavailable("no cached segmentation; local comparisons send no SAM3 request")
    return Cached()


def check_options(raw):
    if not isinstance(raw, dict) or set(raw) - set(DEFAULTS):
        raise embeddings.ConfigError("local_comparison has unsupported options")
    out = dict(DEFAULTS, **raw)
    if out["method"] not in METHODS:
        raise embeddings.ConfigError("local_comparison.method MUST name a tested approach")
    if not isinstance(out["index"], str) or not embeddings.NAME_RE.fullmatch(out["index"]):
        raise embeddings.ConfigError("local_comparison.index MUST name a main-label index")
    for key, minimum, maximum in (("window", 2, 100), ("references", 1, 2)):
        value = out[key]
        if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
            raise embeddings.ConfigError("local_comparison.%s is out of range" % key)
    if out["device"] not in ("cpu", "mps"):
        raise embeddings.ConfigError("local_comparison.device MUST be cpu or mps")
    value = out["min_confidence"]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 100:
        raise embeddings.ConfigError("local_comparison.min_confidence MUST be between 0 and 100")
    out["gate"] = label_gate.check_options(out["gate"])
    return out


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    embeddings.write_atomic(str(path), data)
    os.utime(path, (CUTOFF, CUTOFF))


class Worker:
    """One lazily started model process per run; serialized IPC with bounded waits."""
    def __init__(self, device):
        self.device, self.process, self.log = device, None, None
        self.lock = threading.Lock()
        self.identity = json.loads((RUNTIME / "identity.json").read_text())
        if self.identity["device"] != device:
            raise embeddings.ConfigError("local comparison cache has another device contract")
        atexit.register(self.close)

    def call(self, method, query, references=()):
        with self.lock:
            if self.process is None:
                self.log = (RUNTIME / ("worker-%d.log" % os.getpid())).open("ab")
                env = dict(os.environ, PAIRWISE_DEVICE=self.device,
                           PYTORCH_ENABLE_MPS_FALLBACK="1", OMP_THREAD_LIMIT="1")
                self.process = subprocess.Popen(
                    [sys.executable, str(Path(__file__).with_name("local_comparison_worker.py"))],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log,
                    text=True, bufsize=1, env=env)
            request = {"method": method, "query": query, "references": list(references),
                       "use_cache": model_cache.READ}
            self.process.stdin.write(json.dumps(request) + "\n")
            self.process.stdin.flush()
            if not select.select([self.process.stdout], [], [], 240)[0]:
                self.close()
                raise RuntimeError("local comparison worker timed out")
            line = self.process.stdout.readline()
            if not line:
                raise RuntimeError("local comparison worker exited")
            answer = json.loads(line)
            if answer.get("error"):
                raise RuntimeError(answer["error"])
            if answer.get("identity") != self.identity:
                raise RuntimeError("local comparison worker identity changed")
            return answer

    def close(self):
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
            self.process = None
        if self.log is not None:
            self.log.close()
            self.log = None


def rerank(candidates, references, rows, method):
    """Keep native metric values separate from bottle cosines. Ties keep base rank."""
    field = method.split("-", 1)[1]
    higher = method.split("-", 1)[0] not in ("lpips", "dists")
    results, at = [], 0
    for c, refs in zip(candidates, references):
        measures = []
        for ref in refs:
            row = rows[at]
            at += 1
            if row.get("error"):
                return candidates, {"applied": False, "reason": "method_error", "error": row["error"]}
            value = row.get(field)
            if value is not None:
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise ValueError("invalid pair comparison value")
                measures.append((value, ref, row))
        measures.sort(key=lambda v: (-1 if higher else 1) * v[0])
        best = measures[0] if measures else (None, None, None)
        out = copy.deepcopy(c)
        out["comparison"] = {"method": method, "value": best[0], "field": field,
                             "higher_is_better": higher, "bottle_rank": c["rank"],
                             "bottle_score": c["score"], "reference": best[1],
                             "cached": best[2].get("cached") if best[2] else None}
        if best[1]:
            out["items"] = [dict(i, comparison_value=best[0]) if i["sha256"] ==
                            best[1]["source_sha256"] and i["view"] == "label" else i
                            for i in out.get("items", [])]
        results.append(out)
    if not any(c["comparison"]["value"] is not None for c in results):
        return candidates, {"applied": False, "reason": "no_valid_comparison"}
    results.sort(key=lambda c: (c["comparison"]["value"] is None,
                  (-1 if higher else 1) * (c["comparison"]["value"] or 0),
                  c["comparison"]["bottle_rank"]))
    for rank, c in enumerate(results, 1):
        c["rank"] = rank
    return results, {"applied": True, "field": field, "higher_is_better": higher,
                     "cached_pairs": sum(bool(r.get("cached")) for r in rows),
                     "fresh_pairs": sum(not r.get("cached") for r in rows),
                     "measurements": [dict(c["comparison"], slug=c["slug"]) for c in results]}


class Comparison:
    def __init__(self, backend, options, db_path):
        import competitor_steps
        self.backend, self.options = backend, options
        self.id, self.top_k, self.catalogue = backend.id, backend.top_k, backend.catalogue
        self.worker = Worker(options["device"])
        backend.model = LocalQueryModel(self.worker)
        backend.segmenter = cached_segmenter()
        backend.offline_package_fallback = True
        backend.spec.update(model_backend="local", url=None,
            model="google/siglip2-so400m-patch16-naflex (local float32 p512)",
            catalogue_origin="fixed saved rot5 bottle vectors; local query inference",
            local_comparison_contract=self.worker.identity)
        self.directory = Path(embeddings.entry_dir(db_path, options["index"]))
        self.index = embeddings.read_index(str(self.directory)) or {}
        if self.index.get("label_preparation") != main_label_match.VERSION:
            raise embeddings.ConfigError("local comparison requires a main-label supplementary index")
        self.records = {r["source_sha256"]: r for r in self.index["items"]}
        # Strictly validate the source contract against the current base catalogue.
        main_label_match.focused_catalogue(backend.catalogue, self.directory)
        self.catalog = competitor_steps.load_catalog(db_path)
        self.spec = copy.deepcopy(backend.spec)
        self.spec.update(local_comparison=dict(options, identity=self.worker.identity),
                         score="selected visual cosine; native metric or variant text may determine rank",
                         view_indexes={"full": backend.embedding.name, "label": options["index"]})
        if options["method"].endswith(("tesseract", "paddleocr")):
            self.spec["ocr_normalization"] = dict(wine_terms.IDENTITY)
            self.spec["ocr_verification"] = {"ranking_policy": main_label_match.variant_attributes.RANKING_POLICY}
        self.reference_matrix = None
        # Shared live retrieval cache: current index/owners/steps, never old run rows.
        current_index = embeddings.read_index(embeddings.entry_dir(db_path, backend.embedding.name))
        contract = {"spec": backend.spec,
            "index": {k: current_index[k] for k in ("config", "steps_version", "view_config_hash",
                       "dim", "items", "vectors_file") if k in current_index},
            "slugs": backend.catalogue.slugs,
            "items": backend.catalogue.items, "top_k": backend.top_k}
        contract["spec"] = dict(contract["spec"], id="shared-bottle", label="shared-bottle")
        self.retrieval_contract = hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest()
        self.preparation_contract = {"version": 1, "steps": LABEL_STEPS, "gate": options["gate"],
            "code": {m: sha(Path(__file__).with_name(m + ".py"))
                     for m in ("alternatives", "main_label_match", "label_gate")}}

    def bottle(self, path, first=None):
        key = hashlib.sha256((sha(path) + self.retrieval_contract).encode()).hexdigest()
        cached = RUNTIME / "bottle-cache" / (key + ".json")
        if model_cache.READ and not first:
            try:
                value = json.loads(cached.read_text())
                if value["contract"] == self.retrieval_contract:
                    trace = value["trace"]
                    for record in trace["steps"]:
                        record.update(start_ms=0, ms=0, cached=True)
                    trace["retrieval_cache"] = True
                    return value["candidates"], 0, 200, None, trace
            except (OSError, ValueError, KeyError):
                pass
        answer = self.backend.ask(path, first)
        if not first and not answer[3]:
            save(cached, json.dumps({"contract": self.retrieval_contract,
                "candidates": answer[0], "trace": answer[4]}, allow_nan=False).encode())
        return answer

    def reference(self, source):
        r = self.records[source]
        path = self.directory / r["image"]
        if sha(path) != r["input_sha256"]:
            raise embeddings.ConfigError("main-label reference pixels changed; rebuild the index")
        return {"path": str(path), "sha256": r["input_sha256"],
                "source_sha256": source, "embedding_hash": r["embedding_hash"]}

    def references(self, candidates):
        result = []
        for c in candidates:
            full = {i["sha256"]: i.get("cosine") for i in c.get("items", []) if i["view"] == "full"}
            front = [i for i in c.get("items", []) if i["view"] == "label" and
                     i.get("type") in ("main", "main_patched", "full_front", "label_front") and
                     i["sha256"] in self.records]
            front.sort(key=lambda i: (-(full.get(i["sha256"]) or -1), i["sha256"]))
            sources = list(dict.fromkeys(i["sha256"] for i in front))[:self.options["references"]]
            result.append([dict(self.reference(s), type=next(i["type"] for i in front
                                                            if i["sha256"] == s)) for s in sources])
        return result

    def prepare(self, path, trace):
        import embedding_run
        package = next((s.get("out", {}).get("box") for s in trace.steps
                        if s["id"] == "sam3-package"), None)
        key = hashlib.sha256(json.dumps(dict(self.preparation_contract, source=sha(path),
                    package_box=package), sort_keys=True).encode()).hexdigest()
        cached = RUNTIME / "label-cache" / (key + ".json")
        with trace.step("comparison-label") as step:
            if model_cache.READ:
                try:
                    value = json.loads(cached.read_text())
                    item = value.get("item")
                    if item is None or sha(item["path"]) == item["sha256"]:
                        step["cached"] = True
                        step["out"] = value["out"]
                        return item, value["quality"]
                except (OSError, ValueError, KeyError):
                    pass
            image, _ = derive.open_image(path)
            instances = None
            client = cached_segmenter()
            try:
                instances = client.instances(image, alternatives.DETECT_TEXTS)[0]
                step["cached"] = True
            except derive.Sam3Unavailable:
                pass
            finally:
                client.session.close()
            if instances is None:
                step["out"] = {"found": False, "reason": "no_cached_label_segmentation"}
                return None, {"passed": False, "reasons": ["label_unavailable:no_cached_segmentation"]}
            cut = main_label_match.cut_of(image, instances)
            if cut is None:
                step["out"] = {"found": False, "reason": "no_label"}
                quality = {"passed": False, "reasons": ["no_label"]}
                save(cached, json.dumps({"item": None, "quality": quality,
                                        "out": step["out"]}).encode())
                return None, quality
            prepared, reason = embedding_run.view_input(image, LABEL_STEPS,
                                                        {"label": (cut[2], cut[1])})
            if reason:
                raise RuntimeError(reason)
            data = embeddings.png_bytes(prepared)
            digest = hashlib.sha256(data).hexdigest()
            file = RUNTIME / "queries" / (digest + ".png")
            if not file.is_file() or sha(file) != digest:
                save(file, data)
            quality = label_gate.measure(image, prepared,
                {"instances": instances, "cut": cut, "package_box": package}, self.options["gate"])
            item = {"path": str(file), "sha256": digest}
            step["out"] = dict(item, found=True, size=list(prepared.size), box=list(cut[2]),
                               quality=quality)
            save(cached, json.dumps({"item": item, "quality": quality,
                                    "out": step["out"]}, allow_nan=False).encode())
            return item, quality

    def global_labels(self, query, trace):
        with trace.step("comparison-label-search") as step:
            candidates = self._global_labels(query)
            refs, _matrix = self.reference_matrix
            step["out"] = {"references": len(refs), "wines": len({r[0]["slug"] for r in refs}),
                           "top": candidates}
        return candidates

    def _global_labels(self, query):
        if self.reference_matrix is None:
            # These vectors were recomputed with the same local p512 processor as queries.
            local = RUNTIME / "siglip/features"
            refs = []
            for number, slug in enumerate(self.catalogue.slugs):
                seen = set()
                for pos in self.catalogue.rows_of.get("label", {}).get(number, []):
                    item = self.catalogue.items["label"][pos]
                    source = item["sha256"]
                    if source not in self.records or source in seen:
                        continue
                    seen.add(source)
                    ref = dict(self.reference(source), slug=slug, type=item["type"], number=number)
                    file = local / (ref["sha256"] + ".npy")
                    if not file.is_file():
                        imported = Path(self.worker.identity["imported_feature_root"]) / "siglip" / file.name
                        if imported.is_file():
                            file = imported
                    if not file.is_file():
                        self.worker.call("siglip-vector", ref)
                    vector = np.load(file, allow_pickle=False)
                    if vector.shape != (self.catalogue.dim,) or not np.isfinite(vector).all():
                        raise RuntimeError("invalid local reference vector")
                    refs.append((ref, vector))
            self.reference_matrix = (refs, np.stack([v for _, v in refs]))
        refs, matrix = self.reference_matrix
        vector = np.asarray(self.worker.call("siglip-vector", query)["vector"], np.float32)
        values = matrix @ vector
        best = {}
        for (ref, _), score in zip(refs, values):
            if ref["slug"] not in best or score > best[ref["slug"]][0]:
                best[ref["slug"]] = (float(score), ref)
        order = sorted(best, key=lambda slug: (-best[slug][0], slug))[:self.top_k]
        candidates = []
        for rank, slug in enumerate(order, 1):
            value, ref = best[slug]
            candidates.append({"slug": slug, "rank": rank, "score": round(value, 4),
                               "label": round(value, 4), "items": [{"sha256": ref["source_sha256"],
                                "embedding_hash": ref["embedding_hash"], "view": "label",
                                "type": ref["type"], "cosine": round(value, 4)}]})
        return candidates

    def text(self, candidates, query, engine, trace):
        import main_label_match as main
        with trace.step("label-text") as step:
            data = Path(query["path"]).read_bytes()
            directory = RUNTIME / ("ocr-" + engine)
            context = (nullcontext(directory) if model_cache.READ else
                       tempfile.TemporaryDirectory(prefix="ocr-fresh-", dir=RUNTIME))
            with context as folder:
                reader = (main.PaddleTextReader(folder) if engine == "paddleocr"
                          else main.TextReader(folder))
                words = reader.read(data)
            candidates, evidence = main.verify(candidates, words, self.catalog,
                                               {"window": self.options["window"],
                                                "min_confidence": self.options["min_confidence"]})
            evidence["engine"] = engine
            step["out"] = evidence
            return candidates

    def ask(self, path, first=None):
        import embedding_run
        started = time.perf_counter()
        candidates, _ms, status, error, previous = self.bottle(path, first)
        if error or first or self.options["method"] == "bottle":
            return candidates, _ms, status, error, previous
        trace = embedding_run.Trace()
        trace.started = started
        trace.steps = previous["steps"]
        method = self.options["method"]
        try:
            query, quality = self.prepare(path, trace)
            if query is None:
                with trace.step("local-comparison") as step:
                    step["out"] = {"applied": False, "method": method, "reason": "no_label"}
            elif method in ("tesseract", "paddleocr"):
                candidates = self.text(candidates, query, method, trace)
            elif method.startswith("siglip-") and method != "siglip-main-frozen":
                labels = self.global_labels(query, trace)
                gated = method == "siglip-label-gate" or method.startswith("siglip-gated-")
                selected = "label"
                if gated:
                    with trace.step("label-quality") as step:
                        step["out"] = quality
                    with trace.step("label-route") as step:
                        route = label_gate.choose({"full", "label"},
                            [{"cosine": c["score"]} for c in labels], quality, self.options["gate"])
                        selected = route["selected_view"]
                        step["out"] = route
                candidates = labels if selected == "label" else candidates
                if method.endswith(("tesseract", "paddleocr")) and selected == "label":
                    candidates = self.text(candidates, query, method.rsplit("-", 1)[1], trace)
            else:
                refs = self.references(candidates)
                with trace.step("local-comparison") as step:
                    if any(not r for r in refs):
                        step["out"] = {"applied": False, "method": method, "reason": "missing_reference"}
                    else:
                        engine = "siglip" if method == "siglip-main-frozen" else method.split("-", 1)[0]
                        flat = [r for group in refs for r in group]
                        rows = self.worker.call(engine, query, flat)["rows"]
                        # Update the label item identity to the actual masked reference input.
                        prepared = copy.deepcopy(candidates)
                        for c in prepared:
                            for item in c.get("items", []):
                                if item["view"] == "label" and item["sha256"] in self.records:
                                    item["embedding_hash"] = self.records[item["sha256"]]["embedding_hash"]
                        ranked, evidence = rerank(prepared, refs, rows,
                            "siglip-score" if method == "siglip-main-frozen" else method)
                        candidates = ranked if evidence["applied"] else candidates
                        step["out"] = dict(evidence, method=method)
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired,
                derive.Sam3Unavailable, embeddings.ItemError) as exc:
            with trace.step("local-comparison") as step:
                step["out"] = {"applied": False, "method": method, "reason": "comparison_failed",
                               "error": str(exc)}
        recorded = trace.value()
        if previous.get("retrieval_cache"):
            recorded["retrieval_cache"] = True
        return candidates, round((time.perf_counter() - started) * 1000), status, None, recorded
