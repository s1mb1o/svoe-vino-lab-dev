"""Measure one full-pipeline cold or warm barcode-cache run with 1 or 4 workers.

Run cold then warm for each worker count in one output directory. Model caches keep
their normal behavior. Barcode records use an isolated directory. No profile changes.
Read the benchmark plan and complete GPU preflight before running this command.
"""
import argparse
import contextlib
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
import barcode
import benchmark
import derive
import embedding_run
import embeddings
import model_cache
import pipelines
import benchmark_barcode_variants as scans

PROFILE = "barcode-rerank-siglip2-512-crop"
QUERY_KEYS = ("query_id", "image_path", "image_sha256", "slug", "label", "truth")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def query_identity(rows):
    return [{key: row[key] for key in QUERY_KEYS} for row in rows]


def catalogue_identity(db_path, set_name):
    """Fingerprint relevant live SQLite inputs, including committed WAL records."""
    with contextlib.closing(embeddings.open_database(db_path)) as conn:
        conn.execute("BEGIN")
        wines, sources = embeddings.read_inputs(conn, db_path)
        names = dict(conn.execute("SELECT wine_slug, name FROM wine_catalog"))
        groups = benchmark.load_groups(conn, set_name)
        inputs = {"wines": wines, "sources": sources, "names": names,
                  "groups": {slug: sorted(values) for slug, values in groups.items()}}
    return hashlib.sha256(model_cache.canonical(inputs).encode("utf-8")).hexdigest()


def index_identity(directory):
    directory = Path(directory)
    index = embeddings.read_index(str(directory))
    return {"index_sha256": digest(directory / embeddings.INDEX),
            "vectors_sha256": digest(directory / index["vectors_file"]),
            "prepared_images": sorted(embeddings.image_names(str(directory)))}


@contextlib.contextmanager
def barcode_cache(directory):
    """Route only barcode records. Do not mutate ROOT while query threads run."""
    original, old_read = model_cache.path_of, model_cache.READ

    def path_of(fields, key=None):
        if fields.get("model") != "barcode":
            return original(fields, key)
        key = key or model_cache.key_of(fields)
        return str(Path(directory) / "barcode" / key[:2] / (key + ".json"))

    model_cache.path_of, model_cache.READ = path_of, True
    try:
        yield
    finally:
        model_cache.path_of, model_cache.READ = original, old_read


def internal_profile(settings, name):
    """This experiment sends images only to the configured GX10 embedding service."""
    endpoint = os.environ.get("SAM3_ENDPOINT")
    if endpoint and endpoint.rstrip("/") != derive.SAM3_ENDPOINT.rstrip("/"):
        raise ValueError("SAM3_ENDPOINT differs from the production client's configured endpoint")
    pipeline = pipelines.load(settings.config_path).find(name)
    entry = settings.find(pipeline.embedding)
    if (pipeline.backend != "embedding" or entry.backend != "openai"
            or not pipeline.barcode):
        raise ValueError("bulk cache comparison requires an OpenAI embedding profile with barcode")
    for url in (entry.base_url, derive.SAM3_ENDPOINT):
        if urlparse(url).hostname != "192.168.86.14":
            raise ValueError("bulk cache comparison only permits the existing GX10 endpoints")
    if pipeline.rerank:
        import vlm_config
        _, config, _ = embeddings.read_config(settings.config_path)
        try:
            vlm = vlm_config.entry(config, pipeline.rerank["vlm"])
        except vlm_config.VlmConfigError as exc:
            raise ValueError(str(exc)) from exc
        if urlparse(vlm.endpoint).hostname != "192.168.86.14":
            raise ValueError("bulk cache comparison only permits the existing GX10 reranker")
    return pipeline, entry


def summarize(run_dir, expected, elapsed, build_ms):
    meta = json.loads((run_dir / "run.json").read_text())
    rows = scans.read_jsonl(run_dir / "results.jsonl")
    actual = scans.read_jsonl(run_dir / "queries.jsonl")
    if (query_identity(actual) != expected or len(rows) != len(expected)
            or {r["query_id"] for r in rows} != {r["query_id"] for r in expected}
            or meta.get("answered") != len(expected) or not meta.get("finished")):
        raise ValueError("run did not preserve the complete baseline query set")
    barcode_steps = [next((s for s in (r.get("trace") or {}).get("steps", [])
                          if s.get("id") == "barcode"), {}) for r in rows]
    errors = sum(bool(r.get("error")) for r in rows)
    barcode_errors = sum(bool(s.get("error")) for s in barcode_steps)
    missing_barcode = sum(not s or "cached" not in s for s in barcode_steps)
    degraded = sum(any(s.get("error") or (s.get("out") or {}).get("error")
                       for s in (r.get("trace") or {}).get("steps", [])) for r in rows)
    return {"run_id": meta["run_id"], "run_dir": str(run_dir),
            "complete": not (errors or barcode_errors or missing_barcode or degraded),
            "queries": len(rows), "unique_images": len({r["image_sha256"] for r in rows}),
            "errors": errors, "wall_s": elapsed, "build_ms": build_ms,
            "barcode_step_errors": barcode_errors, "missing_barcode_cache_state": missing_barcode,
            "degraded_queries": degraded,
            "photos_per_second": len(rows) / elapsed if elapsed else None,
            "latency_ms": scans.distribution([r["latency_ms"] for r in rows]),
            "barcode_cache_hits": sum(s.get("cached") is True for s in barcode_steps),
            "barcode_ms": scans.distribution([s["ms"] for s in barcode_steps if "ms" in s]),
            "metrics": json.loads((run_dir / "metrics.json").read_text()),
            "note": "Complete pipeline bulk timing with model-cache reads enabled. Not fresh-photo demo latency."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-run", required=True, type=Path)
    parser.add_argument("--baseline-log", required=True, type=Path)
    parser.add_argument("--stage1", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--config", type=Path, default=Path(embeddings.CONFIG_PATH))
    parser.add_argument("--name", default=PROFILE)
    parser.add_argument("--workers", type=int, choices=(1, 4), required=True)
    parser.add_argument("--phase", choices=("cold", "warm"), required=True)
    args = parser.parse_args(argv)
    try:
        from benchmark_barcode_crops import measurement_lock, require_stage1
        scans.require_finished(args.baseline_run, args.baseline_log)
        expected = query_identity(scans.read_jsonl(args.baseline_run / "queries.jsonl"))
        require_stage1(args.stage1, [r["query_id"] for r in expected],
                       baseline_run=args.baseline_run)
        with measurement_lock(args.stage1):
            output = args.output.resolve()
            production = Path(model_cache.ROOT).resolve()
            if output == production or production in output.parents or output in production.parents:
                raise ValueError("experiment output must be separate from the production cache")
            settings = embeddings.load_settings(args.config)
            pipeline, entry = internal_profile(settings, args.name)
            baseline = json.loads((args.baseline_run / "run.json").read_text())
            set_name = baseline["options"]["set"]
            with contextlib.closing(embeddings.open_database(settings.db_path)) as conn:
                current, _ = benchmark.build_queries(conn, settings.db_path, set_name)
            if query_identity(current) != expected:
                raise ValueError("current test-set photos or labels differ from baseline; freeze a paired experiment first")
            index_dir = Path(embeddings.entry_dir(settings.db_path, entry.name))
            identity = {"profile": args.name, "set": set_name, "queries": expected,
                        "config_sha256": digest(args.config), "index": index_identity(index_dir),
                        "catalogue_sha256": catalogue_identity(settings.db_path, set_name),
                        "baseline_sha256": digest(args.baseline_run / "queries.jsonl"),
                        "lookup": [[kind, code, slugs] for (kind, code), slugs in
                                   sorted(barcode.CodeLookup.load(settings.db_path).values.items())],
                        "source_sha256": {name: digest(ROOT / "pipeline" / name) for name in
                                          ("barcode.py", "model_cache.py", "derive.py", "alternatives.py",
                                           "embedding_run.py", "cluster_rerank.py", "build_embeddings.py")}}
            if pipeline.rerank:
                rules_dir = Path(embeddings.entry_dir(settings.db_path, pipeline.rerank["rules"]))
                identity["rules_sha256"] = {name: digest(rules_dir / name) if (rules_dir / name).exists() else None
                                            for name in ("clusters.json", "cluster-rules.json")}
            output.mkdir(parents=True, exist_ok=True)
            manifest = output / "manifest.json"
            if manifest.exists() and json.loads(manifest.read_text()) != identity:
                raise ValueError("experiment inputs changed; use a new paired experiment directory")
            scans.save_json(manifest, identity)
            prefix = "%s-%d" % (args.phase, args.workers)
            intent = output / (prefix + ".intent.json")
            if intent.exists():
                raise ValueError("attempt exists; reconcile its run before another whole-profile attempt")
            cache = output / "cache" / str(args.workers)
            cold = output / ("cold-%d.summary.json" % args.workers)
            if args.phase == "warm":
                if not cold.exists() or not json.loads(cold.read_text()).get("complete"):
                    raise ValueError("warm run requires a complete successful cold run")
            elif cache.exists() and any(cache.iterdir()):
                raise ValueError("cold run requires an empty isolated barcode cache")
            attempt = {"phase": args.phase, "workers": args.workers, "pid": os.getpid(),
                       "started": embeddings.now(), "status": "started"}
            scans.save_json(intent, attempt)

            def log_progress(message):
                prefix = "run directory: "
                if message.startswith(prefix):
                    attempt["run_id"] = Path(message[len(prefix):].strip()).name
                    scans.save_json(intent, attempt)
                print(message, flush=True)

            database_before = digest(settings.db_path)
            with barcode_cache(cache):
                started = time.perf_counter()
                backend = embedding_run.build_pipeline_backend(pipeline, settings.config_path)
                backend.decoder = scans.MeasuredDecoder(pipeline.barcode).configure(
                    pipeline.scanner)
                build_ms = round((time.perf_counter() - started) * 1000, 3)
                run_dir, _ = benchmark.run_benchmark(
                    settings.db_path, set_name, backend, str(ROOT / "runs"),
                    workers=args.workers, label="barcode-cache-" + prefix,
                    embeddings=backend.catalogue.state, configuration=pipeline.name,
                    use_cache=True, use_barcode=True, log=log_progress)
                summary = summarize(Path(run_dir), expected, time.perf_counter() - started, build_ms)
            summary.update(phase=args.phase, workers=args.workers, barcode_cache=str(cache))
            summary.update(native_calls=backend.decoder.calls, native_errors=backend.decoder.decode_errors)
            summary["warm_cache_misses"] = (summary["queries"] - summary["barcode_cache_hits"]
                                              if args.phase == "warm" else None)
            summary["input_drift"] = (
                catalogue_identity(settings.db_path, set_name) != identity["catalogue_sha256"]
                or index_identity(index_dir) != identity["index"]
                or digest(args.config) != identity["config_sha256"]
                or [[kind, code, slugs] for (kind, code), slugs in
                    sorted(barcode.CodeLookup.load(settings.db_path).values.items())] != identity["lookup"])
            if pipeline.rerank:
                summary["input_drift"] |= any(
                    (digest(rules_dir / name) if (rules_dir / name).exists() else None) != value
                    for name, value in identity["rules_sha256"].items())
            summary["complete"] &= not (summary["native_errors"] or summary["warm_cache_misses"]
                                         or summary["input_drift"])
            summary.update(database_sha256_before=database_before,
                           database_sha256_after=digest(settings.db_path))
            summary["database_file_changed"] = (summary["database_sha256_before"]
                                                != summary["database_sha256_after"])
            scans.save_json(output / (prefix + ".summary.json"), summary)
            attempt.update(finished=embeddings.now(),
                           status="done" if summary["complete"] else "errors",
                           run_id=summary["run_id"])
            scans.save_json(intent, attempt)
            print(json.dumps(summary, ensure_ascii=False), flush=True)
            return 0 if summary["complete"] else 1
    except (OSError, ValueError, KeyError, embeddings.ConfigError) as exc:
        print("bulk benchmark refused: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
