"""Start selected model processes and the compatibility gateway."""

from __future__ import annotations

import argparse
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import torch
import uvicorn

import gateway


ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    service: str
    snapshot: str | None
    accelerator: bool


MODELS = {
    spec.model_id: spec
    for spec in (
        ModelSpec("qr-scanner", "qr_scanner.py", None, False),
        ModelSpec("shieldgemma-2-4b-it", "shieldgemma.py", "google--shieldgemma-2-4b-it", True),
        ModelSpec("siglip2-so400m-patch16-naflex", "siglip2.py", "google--siglip2-so400m-patch16-naflex", True),
        ModelSpec("siglip2-so400m-patch16-512", "siglip2.py", "google--siglip2-so400m-patch16-512", True),
        ModelSpec("sam3", "sam3.py", "facebook--sam3", True),
    )
}


def _device(requested: str) -> str:
    if requested != "auto":
        return requested
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _command(spec: ModelSpec, port: int, model_root: Path, device: str) -> list[str]:
    command = [
        sys.executable,
        str(ROOT / "services" / spec.service),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]
    if not spec.accelerator:
        return command
    snapshot = model_root / str(spec.snapshot)
    if not snapshot.is_dir():
        raise FileNotFoundError(
            f"model snapshot is not installed: {snapshot}. Run install_model_bundles.py first."
        )
    command.extend(["--model", str(snapshot), "--device", device])
    if spec.model_id.startswith("siglip2-"):
        command.extend(["--served-name", spec.model_id])
        if spec.model_id.endswith("naflex"):
            command.extend(["--max-num-patches", "256"])
    elif spec.model_id == "shieldgemma-2-4b-it":
        command.extend(["--served-name", spec.model_id])
        command.extend(["--dtype", "bfloat16" if device == "cuda" else "float32"])
    elif spec.model_id == "sam3":
        command.extend(
            [
                "--batch-size",
                "1",
                "--dtype",
                "fp32" if device == "cpu" else "fp16",
            ]
        )
    return command


def _wait_until_healthy(process: subprocess.Popen[bytes], url: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    last_error = "service did not answer"
    while time.monotonic() < deadline:
        code = process.poll()
        if code is not None:
            raise RuntimeError(f"model process exited with status {code}")
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if response.status == 200:
                    return
                last_error = f"health returned HTTP {response.status}"
        except (OSError, urllib.error.URLError) as exc:
            last_error = str(exc)
        time.sleep(1)
    raise TimeoutError(f"model did not become healthy within {timeout:g}s: {last_error}")


def _stop(processes: list[subprocess.Popen[bytes]]) -> None:
    for process in processes:
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
    deadline = time.monotonic() + 20
    for process in processes:
        remaining = max(0.0, deadline - time.monotonic())
        try:
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def _interrupt_on_hangup(signum: int, frame: object) -> None:
    """Run the normal cleanup path when an SSH session closes."""
    raise KeyboardInterrupt(f"received signal {signum}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", action="append", required=True, choices=sorted(MODELS))
    parser.add_argument("--with-qr", action="store_true", help="also start the CPU QR scanner")
    parser.add_argument("--model-root", type=Path, default=ROOT / "runtime" / "models")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18090)
    parser.add_argument("--device", default="auto", choices=["auto", "cuda", "mps", "cpu"])
    parser.add_argument("--load-timeout", type=float, default=1200.0)
    parser.add_argument(
        "--allow-multiple-accelerators",
        action="store_true",
        help="permit more than one accelerator model after an operator verifies memory capacity",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    if hasattr(signal, "SIGHUP"):
        signal.signal(signal.SIGHUP, _interrupt_on_hangup)
    selected = list(dict.fromkeys(arguments.model))
    if arguments.with_qr and "qr-scanner" not in selected:
        selected.append("qr-scanner")
    accelerator_count = sum(MODELS[model_id].accelerator for model_id in selected)
    if accelerator_count > 1 and not arguments.allow_multiple_accelerators:
        raise SystemExit(
            "select one accelerator model at a time, or pass --allow-multiple-accelerators after a memory check"
        )

    chosen_device = _device(arguments.device)
    environment = os.environ.copy()
    environment.update(
        {
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "TOKENIZERS_PARALLELISM": "false",
            "PYTORCH_ENABLE_MPS_FALLBACK": "1",
        }
    )
    processes: list[subprocess.Popen[bytes]] = []
    model_targets: dict[str, str] = {}
    try:
        for model_id in selected:
            spec = MODELS[model_id]
            port = _free_port()
            command = _command(spec, port, arguments.model_root.resolve(), chosen_device)
            print(f"Starting {model_id} on 127.0.0.1:{port}", flush=True)
            process = subprocess.Popen(command, cwd=ROOT, env=environment)
            processes.append(process)
            target = f"http://127.0.0.1:{port}"
            _wait_until_healthy(process, f"{target}/health", arguments.load_timeout)
            model_targets[model_id] = target
            print(f"{model_id} is ready", flush=True)
        gateway.configure(model_targets)
        print(
            f"Gateway is ready at http://{arguments.host}:{arguments.port}. "
            f"Active models: {', '.join(selected)}",
            flush=True,
        )
        uvicorn.run(gateway.app, host=arguments.host, port=arguments.port, log_level="info")
        return 0
    finally:
        _stop(processes)


if __name__ == "__main__":
    raise SystemExit(main())
