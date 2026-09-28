"""Run the bootstrap benchmark against one isolated model process at a time."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import signal
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


MODELS = (
    "qr-scanner",
    "siglip2-so400m-patch16-naflex",
    "siglip2-so400m-patch16-512",
    "shieldgemma-2-4b-it",
    "sam3",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _command(arguments: argparse.Namespace, model: str) -> list[str]:
    services = arguments.root / "services"
    models = arguments.model_root
    common = ["--host", "127.0.0.1", "--port", str(arguments.port)]
    if model == "qr-scanner":
        return [str(arguments.qr_python), str(services / "qr_scanner.py"), *common]
    if model == "sam3":
        return [
            str(arguments.python),
            str(services / "sam3.py"),
            *common,
            "--model",
            str(models / "facebook--sam3"),
            "--device",
            arguments.device,
            "--workers",
            "1",
            "--batch-size",
            "4",
            "--batch-wait-ms",
            "15",
            "--dtype",
            "fp32" if arguments.device == "cpu" else "fp16",
        ]
    if model == "shieldgemma-2-4b-it":
        return [
            str(arguments.python),
            str(services / "shieldgemma.py"),
            *common,
            "--model",
            str(models / "google--shieldgemma-2-4b-it"),
            "--served-name",
            model,
            "--device",
            arguments.device,
            "--dtype",
            "bfloat16" if arguments.device == "cuda" else "float32",
        ]
    snapshot = "google--" + model
    command = [
        str(arguments.python),
        str(services / "siglip2.py"),
        *common,
        "--model",
        str(models / snapshot),
        "--served-name",
        model,
        "--device",
        arguments.device,
    ]
    if model.endswith("naflex"):
        command.extend(["--max-num-patches", "256"])
    return command


def _wait_for_health(process: subprocess.Popen[bytes], url: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    last_error = "no response"
    while time.monotonic() < deadline:
        status = process.poll()
        if status is not None:
            raise RuntimeError(f"service exited with status {status}")
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if response.status == 200:
                    return
                last_error = f"HTTP {response.status}"
        except (OSError, urllib.error.URLError) as exc:
            last_error = str(exc)
        time.sleep(0.5)
    raise TimeoutError(f"health timeout after {timeout:g} seconds: {last_error}")


def _stop(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=10)


def _command_output(command: list[str]) -> str:
    try:
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
    except FileNotFoundError as exc:
        return str(exc)
    return completed.stdout.strip() or completed.stderr.strip()


def _gpu_snapshot(device: str) -> dict[str, str]:
    if device == "mps":
        ioreg = _command_output(
            ["ioreg", "-r", "-d", "1", "-w", "0", "-c", "AGXAccelerator"]
        )
        utilization = {
            name: match.group(1) + "%"
            for name in ("Device", "Renderer", "Tiler")
            if (
                match := re.search(
                    rf'"{name} Utilization %"=(\d+)',
                    ioreg,
                )
            )
        }
        return {
            "gpu": json.dumps(utilization, sort_keys=True),
            "memory": _command_output(["memory_pressure", "-Q"]),
        }
    if device == "cpu":
        return {"gpu": "CPU benchmark; no accelerator snapshot"}
    return {
        "gpu": _command_output(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,power.draw",
                "--format=csv,noheader",
            ]
        ),
        "compute_processes": _command_output(
            [
                "nvidia-smi",
                "--query-compute-apps=pid,process_name,used_memory",
                "--format=csv,noheader",
            ]
        ),
    }


def _run_model(arguments: argparse.Namespace, model: str, output_dir: Path) -> dict[str, Any]:
    base_url = f"http://127.0.0.1:{arguments.port}"
    command = _command(arguments, model)
    log_path = output_dir / f"{model}.service.log"
    result_path = output_dir / f"{model}.json"
    result: dict[str, Any] = {
        "model": model,
        "command": command,
        "service_log": str(log_path),
        "result_file": str(result_path),
    }
    environment = os.environ.copy()
    environment.update(
        {
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "TOKENIZERS_PARALLELISM": "false",
        }
    )
    started = time.monotonic()
    with log_path.open("wb") as log:
        process = subprocess.Popen(
            command,
            cwd=arguments.root,
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            _wait_for_health(process, f"{base_url}/health", arguments.load_timeout)
            result["load_seconds"] = round(time.monotonic() - started, 3)
            result["loaded_gpu_snapshot"] = _gpu_snapshot(arguments.device)
            benchmark = subprocess.run(
                [
                    str(arguments.python),
                    str(arguments.root / "scripts" / "benchmark.py"),
                    "--base-url",
                    base_url,
                    "--model",
                    model,
                    "--route-mode",
                    "direct",
                    "--concurrency",
                    arguments.concurrency,
                    "--requests",
                    str(arguments.requests),
                    "--warmup",
                    str(arguments.warmup),
                    "--timeout",
                    str(arguments.request_timeout),
                ],
                cwd=arguments.root,
                env=environment,
                text=True,
                capture_output=True,
                timeout=arguments.benchmark_timeout,
                check=False,
            )
            result["benchmark_exit_code"] = benchmark.returncode
            result["benchmark_stderr"] = benchmark.stderr.strip()
            if benchmark.stdout.strip():
                result["benchmark"] = json.loads(benchmark.stdout)
                result_path.write_text(benchmark.stdout, encoding="utf-8")
            if benchmark.returncode != 0:
                raise RuntimeError(
                    f"benchmark exited with status {benchmark.returncode}: {benchmark.stderr.strip()}"
                )
        except Exception as exc:  # noqa: BLE001 - save partial results and continue.
            result["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            _stop(process)
            result["service_exit_code"] = process.returncode
    time.sleep(2)
    result["after_stop_gpu_snapshot"] = _gpu_snapshot(arguments.device)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--model-root", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--qr-python", type=Path)
    parser.add_argument("--device", choices=["cuda", "mps", "cpu"], default="cuda")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model", action="append", choices=MODELS)
    parser.add_argument("--port", type=int, default=18090)
    parser.add_argument("--concurrency", default="1,2,4,8")
    parser.add_argument("--requests", type=int, default=16)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--load-timeout", type=float, default=1200)
    parser.add_argument("--request-timeout", type=float, default=900)
    parser.add_argument("--benchmark-timeout", type=float, default=3600)
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    arguments.root = arguments.root.resolve()
    arguments.model_root = arguments.model_root.resolve()
    # Keep the virtual-environment executable path. Path.resolve() follows the
    # bin/python symlink to the system interpreter and drops the environment.
    arguments.python = arguments.python.absolute()
    arguments.qr_python = (arguments.qr_python or arguments.python).absolute()
    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    output_dir = arguments.output_dir.resolve()
    selected = arguments.model or list(MODELS)
    services = arguments.root / "services"
    summary: dict[str, Any] = {
        "schema_version": 1,
        "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "root": str(arguments.root),
        "model_root": str(arguments.model_root),
        "python": str(arguments.python),
        "qr_python": str(arguments.qr_python),
        "configuration": {
            "models": selected,
            "port": arguments.port,
            "concurrency": arguments.concurrency,
            "requests": arguments.requests,
            "warmup": arguments.warmup,
            "device": arguments.device,
            "sam3_workers": 1,
            "sam3_batch_size": 4,
            "sam3_batch_wait_ms": 15,
        },
        "source_sha256": {
            name: _sha256(services / name)
            for name in ("qr_scanner.py", "sam3.py", "shieldgemma.py", "siglip2.py")
        },
        "before_gpu_snapshot": _gpu_snapshot(arguments.device),
        "models": [],
    }
    summary_path = output_dir / "summary.json"
    for model in selected:
        print(f"Benchmarking {model}", flush=True)
        result = _run_model(arguments, model, output_dir)
        summary["models"].append(result)
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if "error" in result:
            print(f"{model}: {result['error']}", flush=True)
        else:
            print(f"{model}: complete", flush=True)
    summary["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    summary["after_gpu_snapshot"] = _gpu_snapshot(arguments.device)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(summary_path)
    return 1 if any("error" in result for result in summary["models"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
