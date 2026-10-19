#!/usr/bin/env python3
"""Measure one installed Android encoder on the 30-image Pixel 8 pilot set."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import statistics
import subprocess
import threading
import time
import urllib.parse
import urllib.error
import urllib.request
import uuid


PACKAGE = "com.alolalab.chtozavino"
PORT = 18088


class PilotError(RuntimeError):
    """The device pilot cannot continue."""


def adb(serial: str, *args: str, timeout: float = 30.0) -> str:
    result = subprocess.run(
        ["adb", "-s", serial, *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode:
        raise PilotError(result.stderr.strip() or result.stdout.strip() or "adb failed")
    return result.stdout


def pid(serial: str) -> int | None:
    value = adb(serial, "shell", "pidof", PACKAGE).strip()
    return int(value.split()[0]) if value else None


def memory(serial: str) -> dict:
    text = adb(serial, "shell", "dumpsys", "meminfo", PACKAGE, timeout=60.0)
    pss = re.search(r"TOTAL PSS:\s*(\d+)", text)
    rss = re.search(r"TOTAL RSS:\s*(\d+)", text)
    if pss is None:
        table = re.search(r"^\s*TOTAL\s+(\d+)", text, re.MULTILINE)
        pss = table
    return {
        "pss_kib": int(pss.group(1)) if pss else None,
        "rss_kib": int(rss.group(1)) if rss else None,
    }


def thermal(serial: str) -> dict:
    text = adb(serial, "shell", "dumpsys", "thermalservice", timeout=60.0)
    status = re.search(r"Thermal Status:\s*(\d+)", text)
    temperatures = []
    for value, kind, name, sensor_status in re.findall(
        r"Temperature\{mValue=([-+0-9.]+), mType=(-?\d+), "
        r"mName=([^,}]+), mStatus=(\d+)\}",
        text,
    ):
        temperatures.append({
            "name": name,
            "type": int(kind),
            "celsius": float(value),
            "status": int(sensor_status),
        })
    battery = adb(serial, "shell", "dumpsys", "battery")
    battery_temperature = re.search(r"temperature:\s*(\d+)", battery)
    return {
        "status": int(status.group(1)) if status else None,
        "battery_celsius": (
            int(battery_temperature.group(1)) / 10.0 if battery_temperature else None
        ),
        "temperatures": temperatures,
    }


def device_metadata(serial: str) -> dict:
    fields = {
        "model": "ro.product.model",
        "android": "ro.build.version.release",
        "sdk": "ro.build.version.sdk",
        "fingerprint": "ro.build.fingerprint",
    }
    values = {
        name: adb(serial, "shell", "getprop", prop).strip()
        for name, prop in fields.items()
    }
    values["serial"] = serial
    values["application_version"] = adb(
        serial,
        "shell",
        "dumpsys",
        "package",
        PACKAGE,
    ).split("versionName=", 1)[-1].splitlines()[0].strip()
    return values


def multipart_request(path: Path, query: dict[str, str], timeout: float) -> tuple[int, dict, float]:
    boundary = "----svoe-vino-" + uuid.uuid4().hex
    body = bytearray()
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(
        f'Content-Disposition: form-data; name="image"; filename="{path.name}"\r\n'.encode()
    )
    body.extend(b"Content-Type: application/octet-stream\r\n\r\n")
    body.extend(path.read_bytes())
    body.extend(f"\r\n--{boundary}--\r\n".encode())
    url = f"http://127.0.0.1:{PORT}/v1/debug/embedding?{urllib.parse.urlencode(query)}"
    request = urllib.request.Request(
        url,
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read())
            status = response.status
    except urllib.error.HTTPError as error:
        status = error.code
        data = json.loads(error.read())
    return status, data, (time.monotonic() - started) * 1000.0


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def load_selection(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as source:
        rows = [json.loads(line) for line in source if line.strip()]
    if len(rows) != 30 or len({row["query_id"] for row in rows}) != 30:
        raise PilotError("the pilot selection must contain 30 unique queries")
    return rows


def build(args) -> dict:
    selection = load_selection(Path(args.selection).resolve())
    output = Path(args.output_dir).resolve()
    if (output / "results.jsonl").exists() and not args.replace:
        raise PilotError("the output already contains results; use --replace")
    output.mkdir(parents=True, exist_ok=True)
    if args.replace:
        (output / "results.jsonl").unlink(missing_ok=True)
    adb(args.serial, "forward", f"tcp:{PORT}", f"tcp:{PORT}")
    health = json.loads(
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/healthz", timeout=30).read()
    )
    before = thermal(args.serial)
    results = []
    for row in selection:
        before_pid = pid(args.serial)
        samples = []
        stop = threading.Event()

        def sample_memory() -> None:
            while not stop.is_set():
                try:
                    samples.append({"at": time.time(), **memory(args.serial)})
                except (PilotError, subprocess.TimeoutExpired):
                    pass
                stop.wait(0.5)

        sampler = threading.Thread(target=sample_memory, daemon=True)
        sampler.start()
        try:
            status, response, wall_ms = multipart_request(
                Path(row["image_path"]),
                {
                    "k": "20",
                    "aggregation": args.aggregation,
                    "dis_accelerator": args.dis_accelerator,
                    "siglip2_accelerator": args.siglip2_accelerator,
                },
                args.timeout,
            )
        finally:
            stop.set()
            sampler.join(timeout=5.0)
        after_pid = pid(args.serial)
        after_thermal = thermal(args.serial)
        pss = [sample["pss_kib"] for sample in samples if sample.get("pss_kib")]
        rss = [sample["rss_kib"] for sample in samples if sample.get("rss_kib")]
        result = {
            **row,
            "variant": args.variant,
            "http_status": status,
            "response": response,
            "client_wall_ms": wall_ms,
            "pid_before": before_pid,
            "pid_after": after_pid,
            "process_restarted": before_pid is None or before_pid != after_pid,
            "peak_pss_kib": max(pss) if pss else None,
            "peak_rss_kib": max(rss) if rss else None,
            "thermal_after": after_thermal,
        }
        results.append(result)
        with (output / "results.jsonl").open("a", encoding="utf-8", newline="\n") as target:
            target.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    after = thermal(args.serial)
    measured_pids = sorted({row[key] for row in results for key in ("pid_before", "pid_after")
                            if row[key] is not None})
    # Capture only this application's logs. Do not clear system logs.
    logcat = "\n".join(adb(args.serial, "logcat", "-d", "-v", "threadtime",
                           f"--pid={value}", timeout=60.0) for value in measured_pids)
    (output / "logcat.txt").write_text(logcat, encoding="utf-8")
    server_latency = [
        float(row["response"]["latency_ms"])
        for row in results
        if row["http_status"] == 200 and "latency_ms" in row["response"]
    ]
    peak_pss = max((row["peak_pss_kib"] or 0 for row in results), default=0)
    max_thermal = max(
        (row["thermal_after"]["status"] or 0 for row in results),
        default=0,
    )
    finite_vectors = all(
        row["response"].get("embedding_dim") == 768
        and bool(row["response"].get("embedding_base64_f32le"))
        for row in results
        if row["http_status"] == 200
    )
    summary = {
        "variant": args.variant,
        "device": device_metadata(args.serial),
        "health": health,
        "accelerators": {
            "dis": args.dis_accelerator,
            "siglip2": args.siglip2_accelerator,
        },
        "aggregation": args.aggregation,
        "requests": len(results),
        "http_200": sum(row["http_status"] == 200 for row in results),
        "process_restarts": sum(row["process_restarted"] for row in results),
        "finite_768_vectors": finite_vectors,
        "server_latency_ms": {
            "median": statistics.median(server_latency) if server_latency else None,
            "p95": percentile(server_latency, 0.95),
            "maximum": max(server_latency) if server_latency else None,
        },
        "peak_pss_kib": peak_pss,
        "maximum_thermal_status": max_thermal,
        "thermal_before": before,
        "thermal_after": after,
    }
    summary["pilot_runtime_pass"] = all((
        summary["http_200"] == 30,
        summary["process_restarts"] == 0,
        finite_vectors,
        bool(server_latency) and max(server_latency) <= 10_000,
        bool(server_latency) and statistics.median(server_latency) <= 3_000,
        bool(server_latency) and percentile(server_latency, 0.95) <= 5_000,
        peak_pss <= 2.5 * 1024 * 1024,
        max_thermal < 3,
    ))
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--variant", required=True)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--dis-accelerator", choices=("cpu", "gpu"), default="cpu")
    parser.add_argument("--siglip2-accelerator", choices=("cpu", "gpu"), default="gpu")
    parser.add_argument("--aggregation", choices=("max", "top2-mean"), default="max")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = build(args)
    except (OSError, ValueError, PilotError, subprocess.SubprocessError) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
