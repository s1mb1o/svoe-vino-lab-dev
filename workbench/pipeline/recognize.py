"""Recognize one photo with one pipeline of the backend `embedding`, for the page
`/recognize` (plan 55).

Usage:
    python pipeline/recognize.py --name <pipeline> --photo <path> [--top-k N]
        [--config PATH]

`recognize_routes.py` starts this script with `embedding_python` (`run_jobs.interpreter`),
because a pipeline with the key `barcode` needs zxing-cpp and the backend `local` needs
torch. The script builds the backend of the pipeline as a run does
(`embedding_run.build_pipeline_backend`) and asks it one time. It writes one JSON object
to stdout:

    {"spec", "candidates", "latency_ms", "http_status", "error", "trace", "build_ms"}

`spec` is the key `backend` of a `run.json`. `trace` is the step trace of plan 41.
`build_ms` is the time of the backend build. The key `items` of a candidate (plan 38)
stays out, because the step view does not read it. The modules write their output to
stderr, so stdout holds the JSON alone.

A failure before the question (an unknown pipeline, no index, a missing package) writes
`{"error": ...}` and exits with the status 1. A failure inside the question (SAM3, the
embedding endpoint) is the answer: the trace holds the failed step, and the status is 0.

The SAM3 answers go to `data/cache/models/sam3/`, as in a run. The script writes no other file.
Read docs/plans/55_recognize-page.md.
"""
import argparse
import contextlib
import json
import sys
import time

import embedding_run
import embeddings


def recognize(name, photo, config_path=embeddings.CONFIG_PATH,
              top_k=embedding_run.DEFAULT_TOP_K):
    """Return the answer object of one photo. Raise `embeddings.ConfigError` and the
    errors of the backend build."""
    started = time.perf_counter()
    pipeline, _db_path = embedding_run.find_pipeline(name, config_path)
    backend = embedding_run.build_pipeline_backend(pipeline, config_path, top_k)
    build_ms = round((time.perf_counter() - started) * 1000, 1)
    answer = backend.ask(photo)
    cands, latency_ms, status, error = answer[:4]
    return {"spec": backend.spec,
            "candidates": [{key: value for key, value in cand.items() if key != "items"}
                           for cand in cands],
            "latency_ms": latency_ms, "http_status": status, "error": error,
            "trace": answer[4] if len(answer) > 4 else None, "build_ms": build_ms}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Recognize one photo with one pipeline of the backend embedding of "
                    "config.yaml, and write the answer and the step trace as JSON.")
    parser.add_argument("--name", required=True,
                        help="the name of a pipeline of the backend embedding")
    parser.add_argument("--photo", required=True, help="the path of the photo")
    parser.add_argument("--top-k", type=int, default=embedding_run.DEFAULT_TOP_K,
                        help="the candidates of the photo")
    parser.add_argument("--config", default=embeddings.CONFIG_PATH, help="path of config.yaml")
    args = parser.parse_args(argv)
    if args.top_k < 1:
        parser.error("--top-k MUST be 1 or more")
    out, status = sys.stdout, 0
    try:
        with contextlib.redirect_stdout(sys.stderr):
            answer = recognize(args.name, args.photo, args.config, args.top_k)
    except ImportError as exc:
        answer, status = {"error": "%s; the pipeline needs the packages of "
                                   "requirements-local.txt in embedding_python" % exc}, 1
    except Exception as exc:  # noqa: BLE001 - the page shows each failure of the build
        answer, status = {"error": "%s: %s" % (type(exc).__name__, exc)}, 1
    out.write(json.dumps(answer, ensure_ascii=False, default=str) + "\n")
    out.flush()
    return status


if __name__ == "__main__":
    sys.exit(main())
