"""Replay original queries on the already selected production debug pipeline.

This tool does not install an APK, change settings, or create a USB forward.
It preserves each response before the next request. Reference answers stay on the host.
"""
import argparse
import base64
import datetime as dt
import hashlib
import json
import math
import re
from pathlib import Path
import statistics
import struct
import subprocess
import time
from urllib.request import ProxyHandler, Request, build_opener

ADB = "/Users/ashmelev/Library/Android/sdk/platform-tools/adb"
PACKAGE = "com.alolalab.chtozavino"


def save(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--pipeline", choices=("DIS768_CUSTOM", "STANDARD"), required=True)
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--url", default="http://127.0.0.1:18088")
    args = parser.parse_args()
    if args.limit < 1:
        raise ValueError("Limit must be positive")
    args.out.mkdir(parents=True, exist_ok=False)
    http = build_opener(ProxyHandler({}))

    def health():
        with http.open(args.url + "/healthz", timeout=30) as response:
            result = json.load(response)
        if result.get("recognition_pipeline") != args.pipeline:
            raise ValueError("Select the requested pipeline in Settings before this replay")
        return result

    def pid():
        return subprocess.check_output([ADB, "-s", args.serial, "shell", "pidof", PACKAGE], text=True).strip()

    def telemetry():
        def shell(*parts):
            return subprocess.check_output([ADB, "-s", args.serial, "shell", *parts], text=True, timeout=30)
        thermal = int(re.search(r"Thermal Status:\s*(\d+)", shell("dumpsys", "thermalservice"))[1])
        battery = int(re.search(r"temperature:\s*(\d+)", shell("dumpsys", "battery"))[1]) / 10
        pss = re.search(r"TOTAL PSS:\s*(\d+)", shell("dumpsys", "meminfo", PACKAGE))
        sample = dict(at=dt.datetime.now(dt.timezone.utc).isoformat(), thermal_status=thermal,
                      battery_celsius=battery, pss_kib=int(pss[1]) if pss else None)
        with (args.out / "telemetry.jsonl").open("a") as stream:
            stream.write(json.dumps(sample) + "\n")
        if thermal >= 4:
            raise RuntimeError("CRITICAL thermal status; preserve results and stop requests")
        return sample

    queries = json.loads(args.queries.read_text())[:args.limit]
    baseline = {row["query_id"]: row["response"]["variants"][0]["candidates"]
                for row in map(json.loads, args.baseline.read_text().splitlines())}
    state = dict(complete=False, pipeline=args.pipeline, serial=args.serial,
        started_at=dt.datetime.now(dt.timezone.utc).isoformat(), reranking=False,
        baseline=str(args.baseline), queries=str(args.queries), requests=0, errors=0)
    save(args.out / "run.json", state)
    timings = []
    disagreements = []
    maximum_error = 0.0
    hits = {str(k): 0 for k in (1, 5, 10)}
    previous_hits = dict(hits)
    try:
        state.update(health_before=health(), initial_pid=pid(), initial_telemetry=telemetry())
        with (args.out / "responses.jsonl").open("x") as responses, (args.out / "predictions.jsonl").open("x") as predictions:
            for query in queries:
                data = Path(query["abs_path"]).read_bytes()
                if hashlib.sha256(data).hexdigest() != query["image_sha256"]:
                    raise ValueError("Original query image checksum changed")
                boundary = "chtozavino-production-validation"
                body = (f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="query.jpg"\r\n'
                        'Content-Type: application/octet-stream\r\n\r\n').encode() + data + f"\r\n--{boundary}--\r\n".encode()
                request = Request(args.url + "/v1/debug/embedding?k=20&dis_accelerator=gpu&siglip2_accelerator=gpu",
                    data=body, headers={"Content-Type": "multipart/form-data; boundary=" + boundary,
                                        "Connection": "close"})
                started = time.monotonic()
                with http.open(request, timeout=180) as response:
                    result = json.load(response)
                elapsed = (time.monotonic() - started) * 1000
                record = dict(query_id=query["query_id"], image_sha256=query["image_sha256"],
                              client_ms=elapsed, response=result)
                responses.write(json.dumps(record, allow_nan=False) + "\n"); responses.flush()
                candidates = result["candidates"]
                vector = struct.unpack("<768f", base64.b64decode(result["embedding_base64_f32le"], validate=True))
                if not all(math.isfinite(value) for value in vector) or abs(sum(v * v for v in vector) - 1) > .002:
                    raise ValueError("The production embedding must be finite and normalized")
                if not candidates or not all(math.isfinite(row["score"]) for row in candidates):
                    raise ValueError("Invalid ranked result")
                expected = baseline[query["query_id"]]
                if candidates[0]["slug"] != expected[0]["slug"]:
                    disagreements.append(query["query_id"])
                expected_scores = {row["slug"]: row["score"] for row in expected}
                for row in candidates:
                    if row["slug"] in expected_scores:
                        maximum_error = max(maximum_error, abs(row["score"] - expected_scores[row["slug"]]))
                truth = set(query["truth"])
                for k in (1, 5, 10):
                    hits[str(k)] += bool(truth & {row["slug"] for row in candidates[:k]})
                    previous_hits[str(k)] += bool(truth & {row["slug"] for row in expected[:k]})
                predictions.write(json.dumps(dict(query_id=query["query_id"], image_path=query["image_path"],
                    image_sha256=query["image_sha256"], predicted_slug=candidates[0]["slug"], latency_ms=elapsed)) + "\n")
                predictions.flush(); timings.append(elapsed)
                state["requests"] = len(timings); save(args.out / "run.json", state)
                if len(timings) % 10 == 0:
                    print(f"{args.pipeline}: {len(timings)}/{len(queries)}; Top-1 changes={len(disagreements)}", flush=True)
                    telemetry()
        state.update(complete=True, final_pid=pid(), health_after=health(), top1_disagreements=disagreements,
            maximum_common_score_error=maximum_error, hits=hits, baseline_hits=previous_hits,
            median_ms=statistics.median(timings),
            p95_ms=statistics.quantiles(timings, n=100, method="inclusive")[94] if len(timings) > 1 else timings[0])
        state["passed"] = (state["initial_pid"] == state["final_pid"] and not disagreements
                           and maximum_error <= .001 and hits == previous_hits)
    except Exception as error:
        state.update(errors=state["errors"] + 1, error=repr(error), passed=False)
        raise
    finally:
        state["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        save(args.out / "run.json", state)
    print(json.dumps(state, indent=2))
    if not state["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
